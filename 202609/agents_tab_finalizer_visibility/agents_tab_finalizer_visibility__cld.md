# Finalizers on the Agents Tab: A FINAL Deck, Per-Finalizer Cards, Attempt Blocks, and In-Reply Receipts

- **Researcher:** cld (one of four independent researchers; peer reports were not consulted)
- **Date:** 2026-09-25
- **Repo state:** `sase` master @ `d17a7534ad`, linked `sase-core` checkout
  (`crates/sase_core/src/finalizer/`)
- **Inputs read:**
  - `202609/agents_tab_finalizer_panel/agents_tab_finalizer_panel.md` (2026-09-10
    consolidated finalizer-panel report; "the old report" below)
  - `202609/agent_data_card_blocks/agent_data_card_blocks.md` (card blocks, today)
  - `202609/agents_tab_decks_and_cards/agents_tab_decks_and_cards.md` (decks design)
  - `202608/finalizer_protocol_and_extensibility/…md` and
    `202608/builtin_tasks_finalizer/…md` (the extension model and a planned finalizer)
  - The live code, plus a fresh measurement of this host's finalizer artifacts (§3)
- **Question:** How should the Agents tab show finalizers so users can see them and
  troubleshoot them? What role should decks, cards, and card blocks play? The answer
  must generalize beyond `builtin@commit`.

Paths are relative to `src/sase/` unless marked otherwise. `rust/` means
`sase/repos/linked/sase-core/crates/sase_core/src/`.

---

## 0. Bottom line

Finalizers need **three zoom levels**, and each maps onto a different part of the
Agents tab. Only the deepest level warrants new deck/card/block structure.

| Zoom | Question | Where it lives | Structure |
|---|---|---|---|
| **Glance** | "Is it finalizing? Did it land?" | Agent row, identity header | `FINALIZING` status word; a `⊛` chip for **non-success only** |
| **In context** | "How did this turn end?" | End of each agent shell's Reply (inside that shell's card block) | A 1–4 line **finalizer receipt** under a `─── ⊛ FINAL ───` phase divider |
| **Diagnose** | "What ran, in what order, why, what failed, what did it print?" | A new **FINAL deck** (`⊛`, picker key `n`) | **Card = one finalizer instance**, plus a `Pipeline` card. **Card block = one attempt.** Section = one operation. Line = step, evidence, or diagnostic. |

The recommendation in one paragraph:

- **Add a fourth deck, FINAL.** It holds a `Pipeline` card (plan, selection
  provenance, the declaration timeline, controller cycles, drift) and **one card per
  selected finalizer instance**, keyed by instance id. `commit`, `check`, `tasks` and
  plugin instances are all peers.
- **Use card blocks for attempts,** landing on the newest. On a session container, each
  block is labelled with its shell (`--code #1`, `⚙ --mon #1`).
- **Put a compact receipt at the end of each Reply shell phase.** This is where users
  already look when a turn ends.
- **Make the row honest while the phase runs.** Today it says `RUNNING` for a median of
  about **2 minutes** after the model has finished (§3).
- **Build a provider-neutral data layer underneath**, so the view never overfits to
  `commit`:
  - a uniform per-operation record across all three executors (they disagree today)
  - a controller progress journal
  - an opt-in **step channel** that any command, plugin, or `sase stitch create` can
    write
  - bounded live logs
  - a compact finalizer summary in `agent_meta.json`
  - a Rust-core `FinalizerRunView` projection shared by the TUI and a CLI view

What changes relative to the old report:

- **Kept:** its core. That means the `FINALIZING` word, chips for non-success only, the
  progress journal, the live sink, a Rust projection with strict source precedence,
  the "calm" rules, and read-only v1.
- **Retired:** its placement. The `FINALIZERS` fold section in Context and the output
  modal both predate decks. The decks epic deleted the modal-zoom pattern it leaned on.
- **Added:** the declaration story, a "succeeded with warnings" state, and per-operation
  steps. Today's data (§3) shows these matter more than the old report could see.

---

## 1. What users actually need (jobs to be done)

Finalizers are the host-owned tail of every agent turn: plan → trigger → declaration →
execution → verification → outcome. The user needs four things from them. Only the
first is about `commit`.

1. **Glance, all agents:** "Which agents are finalizing now? Which finalizers failed or
   deferred?" This is a row-level signal that must cost zero I/O.
2. **In context, one agent:** "The reply says it's done. Did the work actually land,
   with which SHA?" This belongs inline, after the reply.
3. **Diagnose, one agent:** "Why is it still running? Why did `check` fail? Which step
   hung? What did the hook print? Was my declaration rejected, and why? Did the
   conflict-repair turn run?"
4. **Author and debug a new finalizer.** This is new, and it matters because you plan
   several:
   - "Was my instance selected? If not, why not?"
   - "What trigger did the host compute?"
   - "What payload did the agent declare, and did my validator reject it?"
   - "What did my provider's `execute` and `verify` return?"
   - "Did the config drift since the plan was sealed?"

Job 4 is what makes this more than a "commit panel". Every one of those questions can
be answered from **provider-neutral** data, which §5 derives.

---

## 2. Verified ground truth (as of `d17a7534ad`)

### 2.1 Finalizer lifecycle and extension model

- **Instances come from trusted config only:** `finalizers: {defaults, required,
  instances}`, with each instance defined by `use`, `after`, `max_attempts`, `refusal`,
  and `config` (`finalizers/config.py:26-28`). A plugin config layer cannot activate
  one (`config.py:253-266`). The shipped default is one instance, `commit:
  builtin@commit`, with `max_attempts: 2, refusal: defer`
  (`default_config.yml:1724-1734`). `sase final list` on this host confirms that
  `commit` is the only configured instance.
- **Providers:**
  - `builtin@commit`
  - `builtin@command`: argv, `cwd: primary`, a timeout capped at 1800 s,
    `submission: none` (`finalizers/providers.py:27-28,207-250`)
  - plugin providers from the `sase_finalizers` entry-point group, run out of process
    through `python -m sase.finalizers.worker_entry` and the SDK's
    `describe/validate/execute/verify` protocol (`finalizers/sdk.py:17-26`,
    `worker_entry.py:23-60`)
- **The planned-finalizer landscape** (from the 2026-08 research):
  - `local-check`/`lint` via `builtin@command`
  - `builtin@tasks`, a *declaration-only* finalizer that validates bead ids and runs no
    subprocess
  - third-party plugins, e.g. `acme-sase@task-beads`
  - Plugins are always `provider_requested` with a required submission, and they
    cannot return `skipped`, `refused`, or `deferred`
    (`finalizers/declaration_store.py:197-263`, `executor_plugin.py:149-153`).
- **Where it runs.** `run_finalizers()` runs inline in the runner, right after
  `provider.invoke()` returns (`llm_provider/_invoke.py:390-401`). It can loop for up
  to 8 fixed-point cycles (`finalizers/controller.py`). It can **invoke the model
  again** for declaration recovery or commit conflict repair
  (`finalizers/owned_turn.py`, `commit_repair_conflict.py:42-43`).
- **Monitors run it too.** Monitor **host completion** runs the same controller in
  `no_model` mode on the monitor shell's own artifacts dir
  (`monitor/host_completion.py:229,379`). So a session can hold finalizer runs on
  agent shells *and* monitor shells.
- **Result wire.** Instance statuses are `pending | skipped | success | refused |
  deferred | failed` (`rust/finalizer/wire.rs:286-293`). Trigger kinds are
  `not_triggered | always | dirty_repository | provider_requested` (`:156-161`).
  Attempts carry **no timestamps**. Evidence is free-form `{kind, value}` strings.

### 2.2 Per-run artifacts (all under the agent's artifacts dir)

| File | Content |
|---|---|
| `finalizer_plan.json`, `finalizer_plan.authority.json` | Sealed plan. `authority` adds a `config_snapshot`, which is enough to explain "configured but not selected". |
| `agent_meta.json["finalizers"]` | `{plan_digest, selected, raw_operations}`, written at plan seal |
| `agent_meta.json["finalizers_drift"]` | Config drift warnings, written through `update_meta_field` (`controller.py:80-98`). **Read by nothing.** |
| `final_context.json` | Selected instances with trigger, `submission_required`, and policy |
| `final_submission.json`, `final_submission_attempts.jsonl` | Accepted declaration, plus up to 50 accepted/rejected attempts with codes |
| `final_declaration_recovery_{evidence,prompt,response}.md` | The recovery turn |
| `finalizers/<id>/attempt-N.*` | Per-attempt output. **The shape differs by executor; see below.** |
| `finalizers/<id>/conflict_repair_{prompt,response}.<repo>.md` | The model repair turn. Not attempt-scoped. |
| `finalizer_result.json` | Aggregate status, `cycles`, instances, diagnostics. Written at the end only. |

**The three executors write three incompatible attempt shapes.** This is the first
obstacle to a provider-neutral view:

| Executor | Files | Timing | Operation label |
|---|---|---|---|
| `builtin@command` | `attempt-N.{stdout,stderr,diagnostics.json}` (`executor_command.py:151-182`) | Only as a `duration_seconds` *evidence* item | none |
| plugin | `attempt-N.<op>.{stdout,stderr}`. `describe`/`validate` are overwritten non-exclusively as `<op>.*` (`executor_plugin.py:229-256`) | **none** | the op name |
| `builtin@commit` | `attempt-N.<repo-label>.{stdout,stderr,outcome.json,inputs.json}` (`commit_repair_stitch.py:129,148`) | `outcome.json.duration_seconds`, with no start time | the repo label, plus `-conflict-repair`/`-checkpoint-resume` |

**Nothing live exists yet.** There is no progress journal, no live output sink
(`bounded_subprocess.py` buffers all output until exit), no snapshot projection, and no
finalizer field in `AgentMetaWire` (Python `core/agent_scan_wire_markers.py:122`, Rust
`rust/agent_scan/wire.rs:513`). The only "finalizing" state anywhere is the monitor's
`host_completion_status="finalizing"` (`monitor/presentation.py:10,58`), which is
precedent for the idea.

### 2.3 What the Agents tab can already do

- **Decks:**
  - `DeckId` is `MAIN | FILES | TOOLS`, with `DECK_CYCLE` in that order
    (`ace/tui/widgets/decks/model.py:11-26`).
  - Each deck is a pre-composed `VerticalScroll` inside `DeckPanel.compose`
    (`decks/panel.py:89-111`).
  - The per-deck tables are glyph, name, accent, picker key, blurb, and count nouns
    (`decks/titles.py:13-49`).
  - Availability probes do no I/O (`decks/availability.py`).
- **Cards:**
  - Main's cards are `CardPart(card_id, title, …)` items: `context`, `reply` (titled
    "Output" for shells), and `summary` (`decks/card_part.py`).
  - Files has one card per file page.
  - Tools is **hard-coded** to one `LLM Calls` tab (`decks/panel_chrome.py:168`).
- **The sticky preferred card exists only for Main.** `cycle_focused_deck_card` says
  "Main choices stick" (`_agent_detail_decks.py:424`), and `DeckPanelState` holds a
  single `preferred_card` (`model.py:66-71`). A second deck that also wanted sticky
  cards would **overwrite Main's sticky `reply`**, so that model needs a small change
  (§8.4).
- **Card blocks are designed but not built.** No `CardBlock`, `block_rail`, or
  `prev_card_block` exists in code, and there is no bead or epic yet. The card-blocks
  report names "attempt history (one per attempt)" as a future use of the model (§4.2
  there).
- **Precedents to reuse:**
  - Session Reply phase dividers `render_phase_divider(label, t, accent, glyph)`
    (`prompt_panel/_agent_display_content.py:166-195`)
  - `build_monitor_phase`/`build_gate_phase`
  - ANSI-safe log rendering through `render_axe_output(…, "ansi")`
  - The header "activity" chip fed from `workflow_state.json["activity"]`
    (`models/_agent_state.py:165-168`)
  - Commit SHAs already listed in the Context card's workspace lane with an in-TUI
    commit viewer (`prompt_panel/_agent_commits.py`). **The FINAL deck must link to
    these, not duplicate them.**
- **Finalizers in the TUI today:** `%final` completion only. The TUI reads none of the
  run artifacts above. `axe/runner_reporting.py` reads `finalizer_result.json` only for
  notifications.

---

## 3. Fresh measurements (this host, runs since 2026-09-10)

The old report measured p50 = 2.0 s for the finalizer phase. **That is no longer
true.** I rescanned `~/.sase/projects/*/artifacts/*/2026*/*/*/`. That is 196 finalizer
runs, bounded by the 14-day artifact reaper. The scripts are reproducible from the
description here.

| Measure | Value | Why it matters |
|---|---|---|
| Runs / instances | 196 runs, all single-instance `commit` | The view must be excellent for one instance and must not assume one |
| Aggregate status | 194 success, 2 failed | Silence is still the reward for success |
| Zero-attempt instances (`not triggered`, clean tree) | 24 (12%) | Must render calmly, never as an error |
| Multi-attempt instances | 0 | Attempt blocks are a scaling mechanism, not the v1 centerpiece |
| Stitch operation time (sum of `outcome.json` durations per run, n=172) | **p50 100 s, p75 135 s, p90 231 s, p99 435 s, max 925 s**. 88% > 30 s, 35% > 2 min. | **The invisible window is now minutes at the median, not the tail** |
| Finalizer phase wall time (`final_submission.json` → `finalizer_result.json` mtime) | **p50 129 s, p75 243 s, p90 556 s.** p99 is hours (host-completion cases where submission precedes a long verify monitor) | For about two minutes after the reply is done, the row says `RUNNING` |
| Runs with ≥1 **rejected** `sase final submit` | **72 of 173 (42%)**. Codes: `commit_bead_action_invalid` 68, `manifest_invalid_json` 9, `core_validation_failed` 3, … | The **declaration** phase is a first-class troubleshooting surface. It is what a new finalizer's validator will generate. |
| Declaration recovery turns | 10 of 206 runs (5%) | An extra model turn inside finalization, invisible today |
| Conflict-repair model turns (`conflict_repair` evidence) | 18 of 196 (9%) | Another model turn inside finalization, invisible today |
| **Successful** stitches whose stdout carries `⚠` warnings | "quarantined agent-hood publication requests": **142 of 187 (76%)**. "prompt archive publication deferred": 120 (64%). "Could not drain artifact-link outbox": 45 (24%). | **"Succeeded with warnings" is the majority state.** Nobody sees these today. Some stdout contains raw ANSI (`\x1b[…m`), so it must render through the ANSI renderer. |

A concrete example from today: a sidecar-repo commit's stitch took **124.6 s**. Its
only hook record (`sase_git_fix`) took **0.1 s**. The rest was
`create_commit`/publication work, and it left no trace until exit apart from a stdout
of emoji step lines (`🔄 Running before commit hook`, `🔄 Dispatching create_commit…`,
two `⚠` warnings, `✅ create_commit completed`). Those step lines appear in **100%** of
the 187 stdout files. `sase stitch create` already *has* a step structure. It just
isn't machine-readable, so a UI would have to scrape emoji. §8.1 fixes that at the
source.

---

## 4. What changed since the 2026-09-10 report

1. **Decks and cards landed** (epic `sase-17d`, phases .1–.11 closed). The old target,
   a `FINALIZERS` fold section after `SHELLS`/`WAIT` in the metadata panel, now lands
   inside the Context card. Context means *what this agent is/was asked*, and it is
   the default card. Putting multi-minute live output and diagnostics there bloats the
   most-viewed card and pushes Main into paged mode more often.
2. **The modal-zoom pattern was deleted.** The decks cut-over removed the `Z` zoom
   modal and the `p` view picker in favor of in-place deck panels, splits and zoom. The
   old report's output `ModalScreen` should become a *deck*, which is what decks
   replaced modals with.
3. **Card blocks now exist as a design** (deck → card → block, `[`/`]`, a rail, landing
   on the newest block, "blocks never nest"). This gives an attempt timeline a native
   home.
4. **The phase got about 50× longer at the median** (§3). The case for `FINALIZING`
   and live progress is much stronger than on 09-10.
5. **The declaration story became visible in the data** (42% rejected-at-least-once).
   The old report did not cover it.

---

## 5. Designing for finalizers that don't exist yet

### 5.1 The provider-neutral anatomy

Every finalizer, including ones you haven't written, passes through the same stages.
The view should be built on these, with provider-specific rendering as optional
enrichment.

```text
RUN  (one per shell turn; a session has several)
 ├─ plan         selected instances, order (after-edges), provenance, policy, drift
 ├─ declaration  context issued → submission attempts (accepted/rejected + code) → recovery turn?
 └─ INSTANCE     (commit | check | tasks | acme@open-pr | …)
     ├─ trigger    not_triggered | always | dirty_repository | provider_requested
     ├─ declared   this instance's accepted payload (rendered by enricher, else key/value)
     ├─ ATTEMPT 1..N
     │   ├─ OPERATION  subprocess | model_turn | validation | internal
     │   │   ├─ steps      optional structured progress lines (the step channel)
     │   │   ├─ exit/duration/timed_out/truncated
     │   │   └─ logs       stdout/stderr (live tail while running)
     │   ├─ evidence   typed kind/value
     │   └─ diagnostics attempt-scoped, deduped
     └─ outcome    status, refusal reason, deferral {reason, paths}, headline evidence
```

### 5.2 Stress test against real and planned finalizers

| Finalizer | Trigger | Ops per attempt | What the user needs to see | Covered by the generic model? |
|---|---|---|---|---|
| `builtin@commit` | `dirty_repository` | 1 stitch per repo, plus optional conflict-repair **model turn** and resume/follow-up stitches | Per-repo decision and message, steps (hook → create → push → publish), SHA, deferral paths, warnings | Yes, plus an enricher (per-repo table, links to the existing commit viewer) |
| `builtin@command` (`check`, `lint`) | `always` | 1 subprocess | argv, elapsed, **live tail**, exit code, failing lines | Yes. The generic renderer is enough. |
| `builtin@tasks` (planned) | `always`, submission required | 0 subprocesses (validation only) | Which beads were declared and resolved, and what was rejected | Yes. Zero-op attempts and a declaration-centric card. An enricher resolves bead titles. |
| Plugin (e.g. an "open PR" provider) | `provider_requested` | `execute` + `verify` subprocesses | Op ladder, provider messages, typed evidence (a PR URL), diagnostics, protocol envelopes for debugging | Yes, *if* evidence is typed (§8.5) and plugins can emit steps (§8.1) |
| Monitor host completion | (same instances) `no_model` | same | Which monitor ran them, receipt status | Yes. The run's source is the monitor shell. |

The generic renderer must stand on its own, because plugin authors cannot ship TUI code.
Everything a plugin finalizer produces (status, message, typed evidence, diagnostics,
op logs, steps) must render well with no plugin-specific code in sase. Builtin enrichers
are progressive enhancement, never a dependency.

---

## 6. The role of decks, cards, and card blocks

### 6.1 Placements considered

| Option | Verdict | Reasoning |
|---|---|---|
| **A. Fold section in Context** (old report's plan) | Reject as the home. Keep only the plan hint. | Context is *pre-run* information and the default card. Minutes of live output there fights the most-read card, triggers paged mode, and puts I/O-backed live data into the synchronous Main build. |
| **B. A new Main card, `Final`** (Context \| Reply \| Final) | Reject for depth. **Adopt its good idea as the Reply receipt.** | It is cheap and sticky, but it needs *two* nested navigation levels (instances, then attempts). That violates "blocks never nest", or else crams everything into one card. Log-heavy content also inflates Main's spread measurement for every node. |
| **C. A card in the Tools deck** (LLM Calls \| Finalizers) | Reject | Tools is "the LLM tool-call timeline" with a hard-coded single tab and count noun `calls`. Mixing domains muddles the deck's meaning and its subtitle count. |
| **D. Finalization as its own block in the Reply rail** (`… ─ 2 --code ✓ ─ 3 ⊛ final ✓`) | Reject | A finalizer run is not a shell. The card-blocks invariant is one block per concrete shell, taken from the roster projection. A pseudo-shell breaks roster/rail parity and the JUMP digits. It would also land users on the finalize block instead of the reply they want. |
| **E. A new FINAL deck: cards = instances, blocks = attempts** | **Adopt** | See §6.2 |
| **F. A new top-level tab, or modal-only** | Reject | Both the old report and the decks design already ruled these out. A tab loses the selected-agent context, and modals were deliberately retired. |

### 6.2 Why a deck, why cards = instances, why blocks = attempts

- **A deck, because finalization is its own data domain.** It has its own artifacts,
  its own off-thread loader, its own live-refresh needs, and its own spread/paged
  policy. That is exactly how Files and Tools earned decks. A deck also composes with
  the rest of the deck system for free:
  - `N` in the picker puts FINAL **in the other panel**, which gives *Reply above,
    FINAL below* or *Files diff beside the commit card*.
  - `Z` zooms it.
  - `,/` searches it.
  - `E` exports the active card.
  - Deck panels keep their deck as you `j/k`. So a bottom panel pinned to FINAL becomes
    a **finalizer triage loop**: one keypress per agent shows how its turn landed.
- **Cards = instances, because instance ids are stable config keys.** `commit`,
  `check`, and `tasks` mean the same thing on every agent. So a user who picks the
  `check` card keeps seeing `check` as they `j/k` (once preferred cards are per-deck,
  §8.4). The tab strip becomes a **status strip**
  (`Pipeline │ commit ✓ │ check ✗ │ tasks –`). This scales to N finalizers with zero
  special cases and never mentions `commit` in the model.
- **A `Pipeline` card first**, for everything that belongs to the run rather than to
  one instance:
  - the plan and order
  - *why* each instance was or wasn't selected
  - the declaration timeline (one manifest covers all instances)
  - controller cycles and reactivations
  - drift
  - controller-level diagnostics

  This is the finalizer author's card (job 4).
- **Card blocks = attempts**, the atomic unit of execution with its own logs and
  verdict:
  - This is the future use the card-blocks design already named.
  - It reuses its rail, `[`/`]`, newest-block landing, and following rules unchanged.
  - On a **single-run** node, blocks read `attempt 1 ✗ ─ ▐attempt 2 ✓▌`.
  - On a **session container**, the card aggregates every shell's run of that
    instance, and blocks are labelled in the roster's vocabulary:
    `--code #1 ✗ ─ --code #2 ✓ ─ ▐⚙ --mon #1 ✓▌`. The same `[`/`]` that steps shells
    in Reply steps runs in FINAL.
  - Zero-attempt runs (`not triggered`) get no block. They appear in the card's
    one-line **runs ledger** preamble.
- **Operations are sections inside a block, and steps are lines.** Blocks never nest. A
  conflict-repair model turn is an operation of kind `model_turn`, which shows its
  prompt and response. A plugin's `execute` and `verify` are two operations.
- **Honesty about blocks.** Today 0 of 196 instances retried. So on a plain agent the
  rail almost never appears, and FINAL must be excellent **without** card blocks.
  Blocks pay off on session containers (2–3 runs are routine), with future `check`
  instances configured to retry flakes, and on clan roll-ups later. Until card blocks
  land, attempts render as stacked sections. That is literally the block-spread path,
  so no work is thrown away.

### 6.3 The resulting hierarchy

| Level | Finalizer meaning | Marker |
|---|---|---|
| Deck `⊛ FINAL` | This node's finalization (all its runs) | Rounded border in the FINAL accent |
| Card | `Pipeline`, or one instance (`commit`, `check`, …) | Tab pill with a status glyph (paged), or the heavy `━━ ⊛ commit ━━` rule (spread) |
| Card block | One attempt (`attempt 2`, or `--code #2` in sessions) | `─── ⊛ attempt 2 ─── 07:36:12 ─── 3m40s ───` divider, carrying block anchor meta |
| Section | One operation (`stitch main`, `run just check`, `execute`, `conflict repair`) | Glyph + label + right-aligned exit and duration |
| Line | Step, evidence, diagnostic, log tail | Indented, dim unless in trouble |

In **Main**, finalizers get a **receipt**, not a card and not a block. It is a
sub-section at the end of each agent (or host-completing monitor) shell's phase, so the
Reply keeps one block per shell.

---

## 7. The experience

### 7.1 Visual vocabulary

Every state shows glyph + word + color together, so it reads without color and can be
searched in screenshots. Running uses the roster's `▶`, so rails and tabs match
Reply's.

| State | Glyph | Color | Source |
|---|---|---|---|
| planned / waiting (`after` deps) | `◌` | dim | plan / journal |
| running | `▶` | yellow | journal: open attempt with a live runner |
| success | `✓` | green | result wire |
| success with warnings | `✓` + `⚠N` | green + amber suffix | warning diagnostics or `warn` steps in the latest attempt |
| failed | `✗` | red | result wire |
| refused | `⊘` | magenta | result wire |
| deferred | `⏸` (fallback `‖` if goldens show it wide) | amber | result wire + `{reason, paths}` |
| not triggered / skipped | `○` | dim | `final_context.json` trigger |
| not run (blocked) | `–` | dim | planned but controller ended first ("blocked by X") |
| interrupted | `!` | amber | journal ends mid-attempt and the runner is dead. Never a forever-spinner. |
| unavailable | `⚠` | dim amber | unreadable, oversized, or integrity failure. Show why, keep raw access. |

**Deck identity:**

- **Name `FINAL`.** It matches `%final`, `sase final`, `/sase_final`, and
  `final_context.json`.
- **Glyph `⊛`** (U+229B, circled asterisk, a "wax seal"). It is single-cell, has broad
  font coverage, and is unused in `src/sase/ace` (`⚑` is already HITL and the monitor
  follow-up error).
- **Picker key `n`** (fi**n**al; `f` is Files). Capital `N` means "other panel".
- **Cycle order** appends FINAL: Main → Files → Tools → Final. This keeps Ctrl+N
  muscle memory.
- **Count noun** is `finalizer/finalizers`.
- **Accent:** one unclaimed hue, proposed rose `#FF87D7`. Purple is agent phases, amber
  is monitors, cyan is gates, green is Files, and light blue is Tools. Status colors
  stay semantic. The final choice should come from golden screenshots in both themes.

**Naming hygiene:**

- Always say "finalizer attempt" in help text. "Attempt" also means *agent retry
  attempts* (`D`, `↻2`).
- A gate's "finalize proc" (`gate_finalize_proc_id`) is not a finalizer and must never
  render with `⊛`.

### 7.2 Glance: row and header

- **Status word `FINALIZING`** while the phase runs, bucketed under Running so
  ordering, filters, and capacity accounting don't change. It covers the p50 ≈ 2-minute
  window. It is driven by the `agent_meta` summary (§8.2), so it costs zero extra file
  opens.
- **A `⊛` chip for non-success only**, next to the existing `⚙N`/`⋔N` lane chips:
  - `⊛✗ commit` on a FAILED row. This distinguishes "model turn failed" from "work
    done, but landing failed", and the fixes are completely different.
  - `⊛⏸ commit` on a **DONE** row, because a DONE row with a deliberately dirty tree is
    otherwise a lie of omission.
  - `⊛⊘` for refused, and `⊛!` for interrupted.
- **No chip for success or success-with-warnings.** 76% of successful runs carry
  warnings, so chipping them would be permanent noise. Warnings live in the receipt and
  the deck.
- **Identity header:** while finalizing, the existing compact-row activity chip slot
  shows `⊛ commit · create_commit · 1:42`. It ticks at most once per second, only for
  the selected agent, and reuses the existing countdown cadence.

```text
▶ sase-1ab.code     FINALIZING  ⊛ commit 1:42   …
✗ sase-1c9.code     FAILED      ⊛✗ commit       …
✓ research.b.cld    DONE        ⊛⏸ commit       …
✓ sase-1d2          DONE                        …     ← success: silence
```

### 7.3 In context: the Reply receipt

The receipt goes at the end of each agent shell's Reply phase, and at the end of a
monitor phase that host-completed. Its divider comes from the existing
`render_phase_divider(…, glyph="⊛", accent=FINAL)`. It has one line per selected
instance, in plan order, with right-aligned durations. It is built **only** from the
`agent_meta` summary, so it does no I/O in the Main build. It never shows log tails,
which belong to the deck.

```text
─── ⊛ FINAL ─── 07:31:40 ────────────────────────
  ▶ commit   create_commit · main                  1:42
  ◌ check    waits for commit
```

```text
─── ⊛ FINAL ─── 07:31:40 ────────────────────────
  ✓ commit   8bb7e55 · main              ⚠ 2      2m04s
  ✓ check    exit 0                                  27s
```

```text
─── ⊛ FINAL ─── 07:31:40 ────────────────────────
  ✗ check    command_failed · attempt 2/2          3m40s
             FAILED tests/ace/tui/test_final_deck.py::test_receipt
  – tasks    not run · blocked by check
             p n  open FINAL deck
```

```text
─── ⊛ FINAL ─── 07:44:02 ────────────────────────
  ⏸ commit   deferred · protected_paths · 2 paths
  ○ check    not triggered
```

Rules:

- **Headline evidence** is chosen generically (§8.5): a SHA, then a URL, then a bead
  id, then an exit code.
- A **failed** instance adds exactly one line: the latest attempt's first error
  diagnostic message, or the last non-blank stderr line. It also adds the `p n` hint.
- **Legacy runs** (no plan) get no receipt.
- **`%final:none` runs** get no receipt either.
- In the card-blocks world, the receipt is part of its shell's block. So landing on
  the newest block shows the reply *and* how it landed, in one screen.

### 7.4 Diagnose: the FINAL deck

**Availability** comes from a no-I/O probe over the agent model:

- has content = a sealed plan with at least one selected instance
- count = number selected
- unavailable for clans/tribes (v1), plain proc shells, and legacy runs

The **subtitle switcher** entry carries status: `final ✓`, `final ▶`, `final ✗` in the
status color. So even while reading Main, the border says the finalizers failed.

**Cards:** `Pipeline`, then one card per instance in plan order. Tabs carry status
glyphs, which is a small `CardTab` extension.

- **Default card** (no preference): the first instance needing attention (running,
  failed, refused, deferred, interrupted). Otherwise `Pipeline` if the trouble is
  run-level (a recovery turn, controller diagnostics, drift, an integrity failure).
  Otherwise the first instance card.
- **Sticky preferred card:** it wins when present, consistent with Main. The status
  strip keeps other failures visible.

A spread example (the common case: one instance, fits on one page):

```text
╭─ ⊛ FINAL ┃ Pipeline │ commit ✓ ──────────────────────────────────────────╮
│ PIPELINE · 1 selected · ✓ success · 1 cycle · 2m31s                        │
│   1 ✓ commit   builtin@commit    default                           2m04s   │
│ DECLARATION                                                                │
│   07:30:58  ✗ rejected  commit_bead_action_invalid                         │
│             bead_action is required when a bead is assigned; use keep…     │
│   07:31:05  ✓ accepted  1 payload                                          │
│                                                                            │
│ ━━ ⊛ commit ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ commit · builtin@commit                            ✓ success · 1 attempt   │
│   trigger   dirty repository · 1 repo                                      │
│   declared  main  "feat(ace): add FINAL deck"  · bead sase-1ab → close     │
│ ─── ⊛ attempt 1 ─── 07:31:06 ─── 2m04s ──────────────                      │
│   ✓ stitch main                                       exit 0     1m58s     │
│       ✓ before hook sase_git_fix                                   0.1s    │
│       ✓ create_commit                                             1m51s    │
│       ⚠ prompt archive publication deferred; will retry                    │
│       ⚠ 56 quarantined agent-hood publication requests                     │
│   evidence  commit 8bb7e55 · tree 2127a48 · pushed          ↗ commit view  │
╰──────────────────────────── spread · main 2 · files 3 · tools 88 · final ✓ ─╯
```

A paged example, with a failed `check` and card blocks (after they land):

```text
╭─ ⊛ FINAL ┃ Pipeline │ commit ✓ │ check ✗  3/3 ────────────────────────────╮
│ attempt 1 ✗ ─ ▐attempt 2 ✗▌                              [ older · newer ] │
│ check · builtin@command · just check          ✗ failed · 2/2 attempts      │
│   why       %final:check · after commit                                    │
│ ─── ⊛ attempt 2 ─── 07:36:12 ─── 3m40s ──────────────                      │
│   ✗ run  just check                                   exit 1     3m40s     │
│   │ FAILED tests/ace/tui/test_final_deck.py::test_receipt - AssertionE…    │
│   │ ========== 1 failed, 4127 passed in 212.41s ==========                  │
│   diagnostics  command_failed · attempt_budget_exhausted                   │
│   logs         stdout 2,114 lines · stderr 3 lines          (v to open)    │
╰──────────────────────────────────── main 2 · files 3 · tools 88 · final ✗ ─╯
```

A session container's commit card aggregates every shell's run:

```text
│ --code #1 ✓ ─ ▐⚙ --mon #1 ✓▌                              [ older · newer ] │
│ commit · builtin@commit                              ✓ success · 3 runs     │
│   runs   --plan ○ not triggered · --code ✓ 1 attempt · ⚙ --mon ✓ 1 attempt │
│ ─── ⊛ ⚙ --mon #1 ─── 09:12:40 ─── 1m47s ─────────── (host completion) ──   │
```

A plugin finalizer uses the generic renderer with no sase code specific to it. This
example is a hypothetical `acme-sase@open-pr`:

```text
│ pr · acme-sase@open-pr                         ▶ running · attempt 1/3     │
│   why       %final:pr · after commit                                       │
│   trigger   provider requested · submission required                       │
│   declared  title "feat: FINAL deck" · draft true                          │
│ ─── ⊛ attempt 1 ─── 07:40:02 ─── 0:18 ──────────────                       │
│   ✓ execute                                           ok         12.1s     │
│       ✓ push branch bryan/final-deck                                       │
│       ✓ open pull request                                                  │
│   ▶ verify                                                        0:06     │
│       ▶ wait for required checks                                           │
│   evidence  pr_url  github.com/sase-org/sase/pull/812 ↗                    │
```

A `Pipeline` card for a multi-finalizer run with a problem. This is what makes new
finalizers debuggable:

```text
│ PIPELINE · 3 selected · ✗ failed · 2 cycles · 6m02s                        │
│   1 ✓ commit   builtin@commit     default                        2m04s     │
│   2 ✗ check    builtin@command    %final:check · after commit    3m40s     │
│   3 – tasks    builtin@tasks      default · not run (blocked by check)     │
│   ○ lint       builtin@command    configured · not selected (%final:!lint) │
│ DECLARATION   07:30:58 ✓ accepted · 2 payloads (commit, tasks)             │
│ CONTROLLER    2 cycles · commit reactivated after check (fixed point)      │
│ ⚠ config drifted since this plan was sealed: check.max_attempts 2 → 3      │
│ sase final list · sase final doctor                                        │
```

### 7.5 Live behavior (reusing the old report's "calm rules")

- **Tail gate.** No live tail for an operation until it has run about 5 s. Fast ops go
  `▶ → ✓`. The threshold is configurable.
- **Following** reuses card-block semantics. The deck lands on the newest attempt and
  follows it while you are on it. If you are reading an older attempt, a new one shows
  only as a `● 1 newer ›` marker on the rail. The view never yanks the reader. Within
  an operation, the tail follows the bottom unless the user has scrolled up.
- **Budget.** At most about 12 tail lines per running op in the card. The full log opens
  through `v` hint targets on the op's log files, or `E` exports the active card.
- **Scope.** Tail reads happen only when a panel shows FINAL, the subject is the
  selected agent, the phase is active, and its surface token drifted. A background
  agent finalizing elsewhere costs zero.
- **Sanitize.** Output goes through `render_axe_output(…, "ansi")`. Never raw Rich
  markup, and never copied into notifications or logs.

### 7.6 Keys: nothing new to learn

| Key | Effect in FINAL |
|---|---|
| `p n` / `p N` | Show FINAL here / in the other panel. The best triage layout is Reply above, FINAL below. |
| `Ctrl+N` / `Ctrl+P` | Deck cycle, now including FINAL |
| `Ctrl+J` / `Ctrl+K` | Pipeline ↔ instance cards |
| `[` / `]` | Older / newer attempt block (with card blocks) |
| `v` | Hints on op logs, prompt/response files, and commit links |
| `E` / `,/` / `Z` | Export the active card, search, zoom: unchanged deck behavior |

Read-only in v1. There are no retry, cancel, or re-run controls, because they carry
authorization and fixed-point semantics that must not be smuggled into a display
feature. That matches the old report.

---

## 8. Data and architecture

The UI above is only as good as the data under it. Every piece below is **additive**:
no finalizer wire v2 → v3 bump, and no signed-envelope change.

### 8.1 Producers (Python, `src/sase/finalizers/`)

1. **One operation record for every executor:**
   `finalizers/<id>/attempt-N.<op>.outcome.json` with `{schema_version, op, kind
   (subprocess|model_turn|validation|internal), label, argv?, started_at,
   duration_seconds, returncode?, timed_out, stdout_truncated, stderr_truncated,
   logs{stdout, stderr}, steps?}`.
   - Commit already writes most of this: add `started_at`, `kind`, and `label`.
   - Command adds it beside `diagnostics.json`, which stays for compatibility.
   - Plugin adds one per op.
   - Conflict repair becomes a `model_turn` op that references its prompt/response
     files.

   This single change is what lets one renderer serve every finalizer.
2. **Controller progress journal** `finalizers/progress.jsonl`, adopted from the old
   report and extended with op events:
   - Events: `phase_started{plan_digest, run_identity}`, `instance_started`,
     `attempt_started`, `op_started`, `op_finished`, `attempt_finished`,
     `instance_finished`, and `phase_finished`, with wall-clock timestamps.
   - The controller is the single writer, and writes are best-effort. An observability
     failure never changes a verdict.
   - An unmatched `attempt_started` plus a dead runner renders as `interrupted`.
3. **Step channel (new, the anti-overfitting piece).** The host sets
   `SASE_FINALIZER_STEPS_FILE=<…>/attempt-N.<op>.steps.jsonl` for every finalizer
   subprocess.
   - Anything may append `{"t": …, "step": "create_commit", "state":
     "start|ok|warn|fail", "detail": "…"}`.
   - The SDK gains `sase.finalizers.sdk.step(label, state="start", detail=None)`,
     which is a no-op when the variable is unset.
   - `sase stitch create` emits its existing phases as structured steps: before-hook,
     `create_commit`, sync/push, prompt-archive and agent-hood publication, after-hook.
     Its `⚠` messages become `warn` steps. That turns the opaque 124 s example into a
     legible ladder, and it makes "success with warnings" a first-class state instead
     of scraped emoji.
   - `just check`-style commands can opt in later. They work fine without it, using
     elapsed time and the live tail.
4. **Live sink.** An optional callback in `bounded_subprocess._reader` tees chunks to a
   bounded, rotating `attempt-N.<op>.live` log on the monitor log contract (adopted
   from the old report). The exclusive terminal artifacts are unchanged. A 1800 s
   hard-timeout kill no longer loses all output.

### 8.2 The row-level summary (additive `agent_meta.json` field)

Write a compact summary through the existing `update_meta_field` helper (the same one
`finalizers_drift` uses, `controller.py:86-96`), and only at transitions:

```json
"finalizer_status": {
  "phase": "executing",            // not_started | executing | settled | interrupted
  "status": null,                  // aggregate once settled
  "updated_at": "2026-09-25T20:34:01Z",
  "instances": [
    {"id": "commit", "status": "running", "attempt": 1, "max_attempts": 2,
     "op": "stitch main", "step": "create_commit", "started_at": "…",
     "headline": null, "warnings": 0, "reason": null}
  ]
}
```

- Mirror it as an additive field on `AgentMetaWire` in **both** Python and Rust
  (`rust/agent_scan/wire.rs:513`), per the Rust-core boundary, with a contract-manifest
  test.
- Keep it bounded: at most 16 instances, capped strings.
- It drives the status word, chips, header chip, Reply receipt, and FINAL availability
  and subtitle, all with **zero** extra file opens in list and render paths
  (`tui_perf` rules 1 and 8).

### 8.3 The shared projection (`sase-core`)

Add `rust/finalizer/run_view.rs` with a `FinalizerRunViewWire` projection. It
reconciles:

- the plan and its authority snapshot
- `final_context`
- submission attempts and recovery artifacts
- the journal
- operation records and steps
- the result
- live-log metadata

It exposes the result through the binding. The TUI and CLI then render one truth, and
so could any future web view: that is the "would another frontend need it to match?"
litmus test.

It owns:

- **Source precedence** (adopted from the old report):
  - The authenticated plan is authoritative for selection, order, and policy.
  - A valid terminal result dominates everything.
  - The journal is authoritative for runtime state only while run identity and
    `plan_digest` match and the runner is live.
  - Operation and live files supply content, never status.
  - A dead runner with no result is `interrupted`.
- **Selection explanation:** why each configured instance was or wasn't selected
  (default, required, `%final:x`, `!x`, `none`, or pulled in as an `after` dependency).
- **Attempt-scoped severity plus dedupe.** This prevents "red success" and bloated
  diagnostic lists.
- **A pre-parse size ceiling** on every JSON input.
- **Typed evidence** (§8.5), headline selection, and a warnings count.

Add a read-only `sase final` subcommand that renders the same projection for an agent
(name to be settled per `sase/memory/cli_rules.md`). Agents troubleshooting a
predecessor's landing get the same answer the user sees.

### 8.4 TUI changes (`src/sase/ace/tui/`)

1. **Per-deck preferred card.** Today there is one `preferred_card` per panel and only
   Main sticks. A FINAL preference would clobber Main's sticky Reply. Change it to
   `preferred_cards: {DeckId: card_id}` in `DeckPanelState`, and add the matching
   persistence field. Main's behavior is unchanged.
2. **A card-document deck base.** FINAL's content is a Rich card document, like Main
   and unlike the Files diff viewer. Extract `MainDeckView`'s spread/paged, anchor,
   search-corpus and export machinery into a reusable card-document view. FINAL then
   gets spread/paged decisions, `Ctrl+J/K`, search, `E`, and (later) card blocks for
   free.
3. **A `DeckSpec` registry (recommended prep).** A fourth deck otherwise touches about
   15 parallel tables and if/elif chains:
   - `titles.py` dicts
   - `_DECK_ACCENT_CLASS`
   - `set_deck` class lists
   - `compose`
   - `_deck_is_empty`
   - `refresh_chrome` tabs
   - availability dicts
   - the picker `_DECK_CLASS`
   - CSS

   One `DeckSpec(id, name, glyph, accent, picker_key, blurb, count_nouns, view_factory,
   availability_probe, tabs, empty_message)` record per deck removes that tax for this
   deck and the next. This is the rule of three: Files and Tools were one-offs, and
   FINAL makes the pattern real.
4. **Loader.** A `run_worker(thread=True)` fetch through the projection, with an mtime
   cache and stale-generation rejection, modeled on the LLM Calls panel
   (`widgets/llm_calls_panel.py`). A `finalizers` refresh surface token covers the
   journal, `agent_meta` and live-log mtimes for the selected agent only (rule 14: a
   quiet tick reloads nothing).
5. **Reply receipt.** Build it in the session and agent Reply builders from the model
   summary, with no I/O. In the card-blocks era it is a sub-part of the shell block
   (`render_phase_divider(…, glyph="⊛")`).
6. **Pinned agent-attempt views (`D`).** Unlike Files and Tools, FINAL should follow the
   pinned prior agent attempt when that attempt's artifacts dir resolves. A failed
   prior attempt is exactly when you want its finalizer story. Verify reachability
   during implementation.

### 8.5 Provider presentation without TUI plugins

- **Typed evidence by convention**, with no protocol change:
  - `commit_sha`/`*_sha` → short SHA plus a link to the commit viewer
  - `*_url` → a clickable link
  - `bead_id`/`*_bead` → a bead reference
  - `*_path`/`cwd` → an openable path
  - `*_seconds` → a duration
  - `exit_code` → colored
  - anything else → `kind value`

  The registry lives in Rust with the projection, so every frontend agrees.
- **Optional `describe` presentation hints.** A provider's `describe` response may add
  `presentation: {summary, headline_evidence: [kinds], evidence_labels}`. Builtins
  declare theirs in code. The instance id remains the card title, because users
  already chose meaningful ids (`check`, `lint`), so no config-schema change is needed.
  `builtin@command`'s summary is its argv (`just check`).
- **Protocol envelopes are developer detail.** A plugin op's raw JSON request and
  response render collapsed, as "protocol", reachable through `v`/`E`. The default
  view shows the provider's `message`, typed evidence, and diagnostics.

---

## 9. Delivery plan

Phases 1–3 are gated behind one `beta` flag (e.g. `ace_final_deck`, created with
`sase flag new` per `sase/memory/sase_flags.md`, with both states tested and the Off
branch deleted at the end). Phase 0 is additive data with no user-visible change.

| Phase | Size | Scope | Verification |
|---|---|---|---|
| **0. Finalizer observability data** | M | Operation records for all executors. Progress journal. Step channel env + SDK `step()`. `sase stitch create` emits steps and `warn` steps. Live sink. `agent_meta` `finalizer_status` summary. | Unit tests per executor. A raising sink with a 10 MB producer does not deadlock. A journal-write failure never changes a verdict. Exclusive artifacts are unchanged. |
| **0b. Core wire (sase-core)** | M | `AgentMetaWire.finalizer_status` (Rust scan + Python mirror). `FinalizerRunViewWire` projection with precedence, selection explanation, dedupe, size ceiling, typed evidence. Binding. `sase-core-revision.txt` pin bump. | Fixtures for every §7.1 state: digest mismatch, truncated journal, dead runner → interrupted, 4 MB result → unavailable, zero-attempt, reactivation across cycles. |
| **1. Glance** | S | `FINALIZING` word. `⊛` chips for non-success. Header activity chip. Reply receipt. | Row/receipt goldens in both themes at 120/80/60 columns. `bench_tui_jk.py` p95 unchanged. |
| **2. FINAL deck** | L | `DeckSpec` prep (optional). Card-document view extraction. Per-deck preferred cards. FINAL deck with Pipeline and instance cards (generic renderer plus commit and command enrichers). Status tabs and subtitle. Attempts as sections. Picker/palette/help/footer/keymap registration (`default_config.yml` per the gotchas note). `sase final` read-only view. | Pilot tests: landing, sticky per-deck cards, split with Reply, session aggregation, availability. PNG goldens: spread, paged, session, plugin fixture, Pipeline with unselected and drift. Idle tick reloads nothing. |
| **3. Live** | M | Refresh surface. 5 s tail gate. Following and not-following. 1 Hz elapsed for the selected agent. | An end-to-end fake finalizer that emits steps slowly, warns, retries, then passes, fails, or dies. No cross-agent tail bleed. |
| **4. Card blocks for attempts** | S | Adopt `CardBlock` for attempt blocks once card blocks land. This is the second consumer, so `BlockMeta` must stay source-agnostic: opaque id, label, glyph, status, not "shell identity". | Rail goldens: single-run retries and session runs. `[`/`]` in FINAL. |
| **5. Author tooling and polish** (each optional) | — | `describe` presentation hints. Plugin SDK docs for `step()` and typed evidence. Clan/tribe Summary column. Chronic-warning roll-up. Notification on `failed`/`refused` (never `deferred`). | — |

**Cheapest valuable slice:** Phase 0's `agent_meta` summary plus Phase 1. That kills
the invisible two minutes and surfaces failures and deferrals in the row and Reply,
before any deck work. Even Phase 1 alone should not ship without the journal, or
`FINALIZING` could stick forever after a crash.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| A fourth deck adds cycle and picker weight | Append it to the cycle. `n` picker key. Availability dims it where empty. `DeckSpec` keeps the code cost linear. |
| FINAL's sticky card clobbers Main's sticky Reply | Per-deck preferred cards (§8.4.1) |
| Warnings make every row amber | Warnings never reach row chips, only the receipt suffix and the deck |
| The UI overfits to `commit` | The generic renderer ships first and is tested with a plugin fixture that has typed evidence and steps. Enrichers are additive. There is no `commit` string in the projection or deck model. |
| Scraping stitch emoji | Forbidden. Steps come only from the step channel. |
| Forever-spinner after runner death | Journal plus liveness gives `interrupted`. Tested by truncating the journal. |
| Oversized or corrupt artifacts freeze the panel | Pre-parse ceilings in Rust. The `unavailable` state keeps raw access. |
| Live tails hurt `j/k` and idle CPU | Selected-agent, FINAL-visible, surface-token-gated reads only. No I/O in render or keystroke paths. `SASE_TUI_TRACE=1` quiet-tick check. |
| "Attempt" ambiguity with agent retry attempts | Say "finalizer attempt" in help. Blocks are labelled `attempt n` only inside `⊛` context. |
| Card blocks slip | FINAL is fully useful with attempts as sections, which is the block-spread path |

---

## 11. Open questions for Bryan

1. **Deck identity:** `⊛ FINAL`, picker `n`, rose accent? The alternative names are
   LAND or FINISH, but FINAL matches `%final`, `sase final`, and `/sase_final`.
2. **Attention vs. stickiness:** should a failing instance override a sticky preferred
   FINAL card when you `j/k`? I recommend no, for consistency with Main. The status
   tab strip and the `final ✗` subtitle carry the signal.
3. **`FINALIZING` word vs. `RUNNING` + `⊛` chip:** I recommend the word. The phase is
   now about 2 minutes at the median.
4. **Configured-but-unselected instances in Pipeline:** I recommend showing them
   (dimmed, with the reason). This is the single most useful thing when a new
   finalizer "doesn't run".
5. **Should `sase stitch create` warnings stay warnings?** 76% of successful commits
   warn about the same quarantined-publication backlog. Once surfaced, you may want to
   fix or reclassify them rather than look at them forever (see Appendix A).

---

## 12. Recommended solution

Build finalizer support as **three zoom levels over one provider-neutral data layer**:

1. **Glance.** A `FINALIZING` status word while the host finalizes, and a `⊛` chip only
   when a finalizer failed, deferred, refused, or was interrupted. Both are fed by a
   compact, additive `agent_meta.json` `finalizer_status` summary mirrored in
   `AgentMetaWire`, at zero extra I/O.
2. **In context.** A **Reply receipt**: a `─── ⊛ FINAL ───` phase divider plus one line
   per instance at the end of each agent (or host-completing monitor) shell's Reply
   phase. It shows the headline evidence, an amber warnings count, and one reason line
   on failure. It is a sub-part of that shell's card block, never its own block.
3. **Diagnose.** A new **`⊛ FINAL` deck**:
   - **Cards:** one `Pipeline` card (plan, selection explanation, declaration
     timeline, controller cycles, drift), plus **one card per finalizer instance**
     keyed by its stable instance id. The tab strip doubles as a status strip, and
     cards stick per deck.
   - **Card blocks:** one per **finalizer attempt**, labelled by shell on session
     containers, landing on the newest with card-block following.
   - **Inside each block:** operations as sections, with structured steps, exit and
     duration, typed evidence, attempt-scoped diagnostics, and a gated live tail.
   - It pairs with Reply or Files in a split, and it turns `j/k` into a finalizer
     triage loop.

Underneath:

- a uniform **operation record** across all executors
- a controller **progress journal**
- an opt-in **step channel** (`SASE_FINALIZER_STEPS_FILE` + SDK `step()`), used first
  by `sase stitch create`
- bounded **live logs**
- **typed-evidence conventions**
- a single Rust-core **`FinalizerRunView`** projection that the TUI and a read-only
  `sase final` view both render

No finalizer wire bump, no TUI plugin API, and nothing specific to `commit` in the
model. `commit` gets an enricher, and every future finalizer (`check`, `tasks`,
plugins) is a first-class card on day one.

---

## Appendix A. Side findings

1. **Chronic hidden warnings.** 142 of 187 recent successful commit stitches print
   `Primary commit succeeded, but this project already has N quarantined agent-hood
   publication requests` (N = 56 today). 120 print that prompt-archive publication was
   deferred. The related bead `sase-p0` is closed, but the condition persists. It is
   invisible because it only exists in finalizer stdout. This is the strongest
   practical argument for §8.1.3.
2. **`finalizers_drift` is written and never read** (`controller.py:80-98`). The
   Pipeline card should be its first consumer.
3. **Executor artifact inconsistency** (§2.2):
   - Plugin `describe`/`validate` outputs are overwritten non-exclusively.
   - Plugin ops have no timing.
   - Command timing exists only as evidence.
   - Commit's conflict-repair files are not attempt-scoped.
4. **`finalizer_result.json.cycles` is outside the Rust aggregate wire**, which uses
   `deny_unknown_fields`. The projection must read it from the Python artifact shape,
   not the wire struct.
5. **One preferred card per panel** means any second sticky deck would clobber Main's
   Reply (§8.4.1). Fix this before adding sticky cards anywhere else.
