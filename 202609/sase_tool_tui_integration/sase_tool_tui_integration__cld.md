# `sase tool` in the TUI: where ToolRuns belong, and what the best UX looks like

**Researcher:** cld (5-researcher swarm) · **Date:** 2026-09-27 · **Host:** athena · **sase
master:** `21d4e12c8c`

**Question.** Bryan wants to integrate `sase tool` into the Agents tab, and maybe other
parts of the TUI. He floated two ideas and was unsure of both:

- a new card in the **Tools** deck;
- a small **hammer icon with a count** on agent nodes that made tool runs.

What is the best UX for `sase tool` in the TUI, and where should it start?

**Method.**
- Read the `sase tool` CLI, docs, and ledger code.
- Mapped the Agents-tab deck/card stack, row renderer, identity header, monitor detail,
  Admin Center, and perf contract, using three parallel code sweeps plus spot checks of
  every load-bearing citation.
- Mined the live ToolRun ledger, read-only (1,293 runs since 2026-09-20).
- Captured the live TUI.
- Read prior consolidated research through `sase artifact read`: the `sase tool` epic
  roadmap, the `%tool` directive report, and the decks-and-cards report.

A styled mockup of the recommendation is in
[`sase_tool_tui_integration_ux__cld_mockup.png`](sase_tool_tui_integration_ux__cld_mockup.png).
Paths are relative to `src/sase/` unless noted.

---

## 0. Answer up front

**Both instincts point at real surfaces, but neither is the integration by itself.**
The ledger data says the valuable things to show are **live state** and **the triage
verdict**. Counts are not.

| Your idea | Verdict | Why |
| --- | --- | --- |
| Hammer + count on agent rows | **Keep the hammer. Drop the count. Show it only while a run is live.** | Median runs per agent is **1** (p90 3). Of 726 agents with runs in the last 7 days, 474 had exactly one. A count would print `⚒1` on nearly every coding agent and inform no decision. What a row *can't* tell you today is that an agent reading `(RUNNING)` has actually been blocked for 4 minutes inside `check`, stage 7 of 11. That is worth a chip. |
| A new card in the Tools deck | **Yes, as the drill-down home, not as the integration.** | It is the right place for the canonical per-node "Runs" view: one card block per run, linked to the LLM call that started it. But it sits two keypresses away. It does nothing for "what is this agent doing right now", for runs no agent owns, or for cross-agent failures. |

**Recommended design: one noun, one glyph, one renderer, five hosts.** In order of value:

1. **Live row chip** (`⚒ check 7/11`) that exists only while a ToolRun is live. It
   follows the precedent of the `⊛` finalizer chip and inherits up to session and monitor
   rows. When a run's heartbeat goes silent it turns red (`⚒⚠ check silent 4m`) instead
   of pretending the run is fine.
2. **Identity-header chip.** Live: `⚒ check · lint (mypy) 7/11 · 2m13s / typ 4m13s`.
   Settled: `⚒ check ✗ 3 NEW · 1 KNOWN`. The chip shows the triage verdict, not the exit
   code, and only for the *selected* node, so a red master doesn't turn the list red.
3. **Tools deck → `⚒ Runs` card.** One block per ToolRun, with a stage waterfall, triage
   items, log tail, and `v` for the full log. It shares the deck with **LLM Calls**, whose
   `sase tool run` rows link to their run (`→ ⚒ run 3 ✗ 3 NEW`) instead of duplicating
   it. The Main deck's Reply card gets a one-line per-turn run receipt, like the FINAL
   receipts.
4. **Monitor and proc nodes that own a run** show it: a Tool run row in Context, and the
   stage strip above the raw Output.
5. **Admin Center → Tools pane** (Runs · Failures · Catalog) for project-wide and
   agent-less runs. This is also the target of the `tool-run` settlement notification's
   missing action (`sase-189`).

**Start here.** Before any UI:
- Fix the one bug that blinds the TUI to monitor-owned runs: the monitor scan drops
  `tool_run_id`, so **0 of 1,599** monitor rows carry it.
- Add a slim Rust-side node-summary query (no fingerprints, agent/owner indexes) with a
  stat-only change token.

Then ship layers 1–2, which carry most of the value, before the deck card.

![mockup](sase_tool_tui_integration_ux__cld_mockup.png)

---

## 1. What exists today (verified)

### 1.1 `sase tool` is mature; the TUI knows nothing about it

**CLI and ledger.** E1 (`sase-135`), E1.5 (`sase-16h`), E2 (`sase-17p`), and E3 (`sase-18j`)
are closed; E4 (`sase-1ah`) is landing. The CLI offers:
- `list` (LAST/TYPICAL)
- `run`, including `-H` hand-off
- `runs` and `show` (`-F` follow, `-l` logs)
- `wait` and `stop`
- `failures` (signature groups)
- `receipt` / `receipts`

The ledger is a Rust-owned SQLite store at `~/.sase/tools/runs.sqlite` (`core/tool_run.py`).

**TUI awareness: none.** Grepping `ace/` for `tool_run`, `ToolRun`, or `sase tool` finds
nothing.

**Places where ToolRun data exists but no TUI surface shows it:**
- Monitor start writes `monitor_tool_run_id` into the monitor's `agent_meta.json`
  (`monitor/start.py:411`). The scan wire has a slot for it
  (`core/agent_scan_wire_agent_session_turn.py:52,167`). But the scan result never fills
  it (`monitor/models.py:298-300` reads it from the Rust scan, which lacks it), and the
  TUI's monitor enrichment has no parameter for it
  (`ace/tui/models/_loaders/_meta_enrichment_monitor.py`).
  - `sase monitor list -a -j`: **0 of 1,599** rows have a `tool_run_id`, while 223
    monitor-owned runs were recorded in 7 days.
  - `sase monitor show srnrtrezmx4p` prints no "Tool run" row, even though its command
    was `sase tool run check` and it owns run `04349ecf…`.
- The hand-off settlement notification (`tool/notify.py:99-134`) publishes with
  `action=None` because no "open ToolRun" action exists (`sase-189`, READY).
- Monitor follow-up prompts already embed a Tool run row and a triage section
  (`monitor/followup_prompt.py:260-261,333-352`). Agents get this context; the human
  doesn't.
- Agents already cite run ids as evidence in bead notes, e.g. "Evidence:
  `sase tool run -k check` run 81ef0cb11e…" on `sase-1bc`. The ids are dead text
  everywhere they appear.

### 1.2 The surfaces a ToolRun could live on

**Decks** (`ace/tui/widgets/decks/spec.py:28-73`). There are four:

| Deck | Glyph | Contents |
| --- | --- | --- |
| MAIN | ◆ | Context / Reply, or Output for monitors and procs |
| FILES | ▤ | diffs and attached files |
| TOOLS | λ | "LLM tool-call timeline" |
| FINAL | ⊛ | finalizers |

About the Tools deck:
- Its single tab is hard-coded: `CardTab("llm-calls", "LLM Calls")`
  (`decks/panel_chrome.py:383`).
- It is **not** a card-document deck, so a second card needs chrome work or conversion.
- The deck registry is `if/elif` dispatch across ~15 touchpoints, not a plugin
  registry. Adding a **card** to an existing card-document deck, by contrast, only
  requires the builder to emit another `CardPart`.
- `Ctrl+N/P` cycles every deck without skipping empty ones (`decks/model.py:43-53`), so
  each extra deck costs every user a keypress on every node.

**LLM Calls card** (`ace/tui/widgets/llm_calls_panel.py`, `ace/tui/llm_calls/`).
- Reads `tool_calls.jsonl`.
- One timeline, with no row cursor and three global detail levels (`h/l/H/L`).
- A Bash row shows `exit N | <stdout preview>`, with a 512-char tail preview.
- A `sase tool run check` call looks like any other failed Bash call: red `fail`, `4m12s`,
  and whatever the tail happened to contain.

**Agent rows** (`ace/tui/widgets/_agent_list_render_agent*.py`).
- The left side is ragged and the runtime suffix is right-aligned. There are no fixed
  chip slots; chips append inline and vanish when empty.
- The list is clamped to 60–130 cells and hard-clips on the right.
- A row that grows >4 cells past the target forces a full rebuild
  (`_agent_list_build_patching.py:39-41`).
- The render cache key is spelled out field by field ("adding a new visible field is a
  deliberate edit here", `_agent_list_render_cache.py:191-222`).
- **Precedent:** the finalizer chip `⊛ f1 · lint` sits right after the status. It shows
  while finalization runs and persists only for trouble (failed / refused / interrupted
  / deferred), superseded by a later success (`ace/tui/models/finalizer_row_state.py`).
  That is exactly the glance contract a ToolRun chip needs.

**Glyphs.**
- Only one-cell Unicode is used; no Nerd Font glyphs.
- `⚙` is already overloaded (monitors, named procs, top-bar gears).
- `⚒` is used in exactly two places, as the AXE/chop icon in link trails
  (`ace/tui/actions/link_trail.py:27`, `ace/tui/relations/link_subject.py:29`).
- `⚗ ⛏ ⚖ ⏲` are unused.
- All of these are covered by the bundled golden fonts. `🔨` is a two-cell emoji,
  against the stated one-cell preference.

**Identity header.** Row 2 of the compact header already carries activity, wait, retry,
and `⊛ finalizing` chips (`widgets/prompt_panel/_identity_header_compact.py:278-334`).
It is selection-scoped and always visible whatever the deck.

**Main deck Reply receipts.** Each turn's Reply block gets a `⊛ FINAL` receipt with a
`p n open FINAL deck` hint when something is in trouble
(`widgets/prompt_panel/_agent_finalizer_receipt.py:96-156`). This is the pattern for
per-turn summaries that point into a deck.

**Monitor detail.** The Context card shows MONITOR TURN fields. The Output card shows
raw `live_reply.md` (`widgets/prompt_panel/_agent_monitor_section.py`). There is nothing
ToolRun-specific.

**Admin Center** (`ace/tui/modals/config_center_catalog.py:17-25`). Panes: Config, Logs,
Machines, Procs, Projects, Statistics, Updates. There is no Tools pane. Hand-off worker
procs appear in Procs, but their `tool-run:<id>` tags are not decoded.

**Tabs.** Only Agents, Artifacts, and Services (`ace/tui/tab_order.py`).

### 1.3 Data-layer facts that constrain the design

| Fact | Consequence |
| --- | --- |
| Every CLI "read" (`runs`, `show`, `list`, `failures`) first runs `reconcile_unsettled_tool_runs()` (`tool/liveness.py:192`). That writes to the store, re-reads each unsettled run's `events.jsonl`, and can publish notifications. `sase tool runs -n 1` takes ~580 ms. | The TUI must **not** reuse the CLI handlers, and must never reconcile on a render or keystroke path (tui_perf rules 1, 11). |
| `tool_run_list` rows carry both fingerprints: ~10 KB per row (50 rows ≈ 530 KB). There is no field projection, and the list request rejects unknown keys such as `owner_id`. | A TUI needs a **slim projection**. |
| There is no index on `agent`, `owner_id`, or `bead`. | Per-agent queries scan. That's fine at 1.3k runs; wrong for a 180-day ledger. |
| Attribution is `SASE_AGENT_NAME` (fallback `SASE_TOOL_RUN_AGENT`) at run time (`tool/executor_recording.py:38-48`). Monitor-owned runs record the **starter** turn, not the `--mon` member. Session promotion can stale the name. | Map runs to nodes by **both** `agent` and `(owner_kind, owner_id)`. |
| The wrapper records a load sample every **10 s** (`tool/sample.py:21`). | A free, write-free **heartbeat** (§2). |
| `tool_run_store_stats()["last_write_ts"]` costs ~8 ms. `runs.sqlite` + `-wal` mtimes are one `stat` each. | A cheap change token for the established `ace_refresh_tokens` idle-tick path (tui_perf rule 14). |
| Stages appear only when they finish. There is no "current stage" record. | Live progress is `done/expected`, where expected comes from prior complete runs of the same definition. The current stage name is inferred, not recorded (§6.3). |

---

## 2. Evidence from the live ledger

Read-only SQL over `~/.sase/tools/runs.sqlite` on athena at 2026-09-27 ~17:00 EDT. The
ledger starts 2026-09-20.

| Measure | Value | Design implication |
| --- | --- | --- |
| Runs in last 7 days | 1,248, of which `check` 1,092, ad-hoc 102, `test` 49, `install` 4, `test-visual` 1 | In practice, "tool run" means "the agent ran `check`" |
| Distinct agents with ≥1 run (7 d) | 726 | Almost every coding agent |
| Runs per agent | p50 **1**, p90 3, max 30. Distribution: 1→474, 2→149, 3→51, 4→29, 5→7, ≥6→15 | **A count is near-constant noise** |
| Inline `check` duration | p50 **3m54s**, p75 7m30s, p90 **15m39s** (n=882) | Agents sit in `(RUNNING)` for minutes with no visible reason |
| Monitor-owned `check` duration | p50 7m09s, p90 42m52s (n=178) | Monitor rows need progress too |
| Time with ≥1 ToolRun live | **54%** (1 live 27%, 2 live 14%, 3+ 13%; peak 7) | Live state is the common case, not an edge case |
| Settled `check`, last 24 h (n=160) | NEW 64 · **signaled 43 (27%)** · UNKNOWN-only 25 · KNOWN/FLAKY-only 13 · **succeeded 11 (7%)** · untriaged 4 | Exit code is meaningless on a red master; the **verdict** is the signal |
| Signaled runs' duration | p50 **539 s**, p90 542 s; 91 of 112 are inline `terminal_cause=signal` | A caller-side sync ceiling at ~9 min kills a quarter of checks. Worth surfacing as "killed at 9m", distinct from "failed" |
| Each agent's *last* check (36 h, n=158) | NEW 65 (41%) · signaled 39 (25%) · UNKNOWN 23 · KNOWN-only 12 · **succeeded 11 (7%)** | **A persistent verdict chip on rows would light up ~90% of rows** |
| Stages per `check` run | p50 **11**, max 19 | Room for a stage-progress fraction and a stage waterfall |
| Unsettled runs now | 3 live (heartbeat 6–10 s old). **`2f5ce886…` "running" for 52 h; last sample 185,260 s ago** | Reconcile keeps it "running" because its wrapper pid is alive with a zombie child. **Heartbeat age catches it** without any write |

The last two rows decide most of the design. First, the only row-level ToolRun signal
that isn't noise is **live state**, including the degenerate "live but silent" state.
Second, a verdict belongs where one node is in view (header, deck, Reply). It does not
belong in the list, where ~90% of the marks would be red or grey.

---

## 3. What users actually need, ranked

| # | Job | Frequency | Today | Best surface |
| --- | --- | --- | --- | --- |
| J1 | "Why is this agent still running? What is it doing?" | Constant (54% of wall time) | Row says `(RUNNING)`; nothing else | **Row chip**, header chip |
| J2 | "Is this run stuck, or about to be killed?" | Daily (27% signaled; 52 h zombie) | Invisible; CLI only | Row chip turns red on silent heartbeat; header shows elapsed vs TYPICAL; Admin Center Runs; stop action |
| J3 | "Did this agent's verification pass? NEW failures or only the known red?" | Every review of an agent | Buried in reply prose or the LLM-call tail | **Header chip**, Reply receipt |
| J4 | "Why did it fail?" | Often, after J3 | `sase tool show RUN` in a shell | **Tools deck → Runs card** |
| J5 | "Is master red? Which failures are shared across agents?" | Daily | `sase tool failures` | **Admin Center → Tools → Failures**, with a pivot to agents |
| J6 | "This monitor is a check; how far along is it, and what did it find?" | 223 monitor runs / 7 d | Raw log only; run id dropped | Monitor Context row, stage strip, row chip |
| J7 | "My `-H` run settled; open it." | Per human hand-off | Notification with no action | Notification action → Admin Center run detail |
| J8 | "What tools exist, how long do they take? Let me run one." | Rare for this user | `sase tool list` | Admin Center → Tools → Catalog (`r` = `-H`) |

---

## 4. Design principles

1. **A ToolRun is its own noun**, not an LLM call, a monitor, or a proc. That follows the
   glossary: "LLM Calls … is not an execution record"; "a ToolRun … is not a sase
   monitor or proc (those may own the run)". In the UI it gets:
   - one glyph, `⚒`;
   - one accent (a warm tan, distinct from monitor amber);
   - one canonical renderer;
   - one set of verbs: open, log, follow, stop, copy id.

   Every place a run appears links to that renderer.
2. **Ambient surfaces show state, not quantity.** They carry live or trouble state only;
   quiet when settled-and-unremarkable. This is the `⊛` contract.
3. **Verdict over exit code.** With 7% of checks green, render the E3 triage class:

   | Glyph | Meaning | Color |
   | --- | --- | --- |
   | `✗` | NEW | red |
   | `≈` | KNOWN/FLAKY only | amber |
   | `?` | UNKNOWN | dim |
   | `⊘` | killed or signaled | grey |
   | `✓` | pass | green |

   A raw red `failed` on every check is alarm fatigue.
4. **Honest time.** Show `elapsed / typ TYPICAL` and `done/expected` stages. Never an ETA
   (roadmap invariant "no fake precision"; forecasts are E6). Show heartbeat silence
   instead of guessing "lost". Never call reconcile from the TUI.
5. **Link, don't duplicate.** An LLM Bash call that ran `sase tool run` points at its run.
   The run points back at its call. A monitor that owns a run shows *that* run.
6. **Selection-scoped detail, list-scoped exceptions.** Verdicts go where one node is in
   view. The list only gets what changes a decision at a glance.
7. **Perf by construction.** One batched, slim, off-thread query keyed by a stat-only
   change token. Row patches, not rebuilds. Detail fetched on demand with an LRU keyed by
   `(run_id, settled)`.

---

## 5. Evaluating the two ideas, and the alternatives

### 5.1 Hammer + count on rows

**Strengths:**
- Rows are where the eye is.
- A glyph gives ToolRuns a visual identity.
- A hammer is the most legible "tool" metaphor on offer.

**Problems:**
- **Information:** a count distinguishes almost nothing (p50 1, p90 3).
- **Decision value:** knowing an agent ran `check` twice changes nothing you do. Knowing it
  is *in* `check` right now, or that its run went silent, does.
- **Noise:** nearly every coding agent row gains a chip. Width grows on 700+ rows a week
  in a list that hard-clips at 60–130 cells.
- **Glyph collision:** `⚒` is currently the AXE/chop link-trail icon (two call sites).

**Fix:** keep `⚒`, make the chip **live-only and stateful**, and move the chop/job
link-trail icon to `⏲`. "Scheduled" is a better fit for a job anyway, and "AXE" is a
retired name.

### 5.2 A new card in the Tools deck

**Strengths:**
- A deck card is the right *drill-down* home.
- The deck is the only place LLM Calls and ToolRuns can sit side by side, so the
  call ↔ run link stays inside one deck.
- It turns the one-card Tools deck into a real deck.
- It adds zero top-level cycling cost.

**Problems:**
- Opening it takes `p t` + `Ctrl+J`, so it cannot answer J1–J3 at a glance.
- It cannot host agent-less runs (J7: human `-H` runs; 21 of 1,248 runs have no agent)
  or cross-agent failures (J5).
- It needs the Tools deck converted to a multi-card deck.

**Fix:** build it, but as layer 3.

### 5.3 Other options I considered

| Option | Verdict | Reason |
| --- | --- | --- |
| **5th deck "RUNS"** | Reject | Every node pays a `Ctrl+N` stop. Runs are 1–3 per agent, a card's worth, not a deck's. The prior decks report argued for keeping the top level short. |
| **Inline runs as child nodes in the agent tree** (like monitor turns) | Reject | An inline run is *inside* a turn, not a turn. Live-only child rows churn tree membership on every start/settle, which is the most expensive UI path (tui_perf rule 6). Persistent rows bloat the tree by 1–30 per agent. Monitor-owned runs would be double-represented. |
| **Top-level "Tools" tab** | Reject | ToolRuns are overwhelmingly agent-scoped. The cross-agent view is an admin/diagnostic surface, not a daily tab. Three tabs is a deliberate budget. |
| **Persistent settled-verdict chip on rows** (the `⊛✗` analogue) | Defer, with a reopen condition | ~90% of agents' last checks are non-green (§2), so it would mark nearly every row. **Reopen** when ≥70% of agents' last checks are pass or KNOWN-only for a week; then `⚒✗` for NEW becomes a true exception. |
| **Top-bar `⚒N` live-run chip** | Defer to E7 | ≥1 run is live 54% of the time, so a bare count is ambient noise. It becomes valuable as a *capacity* meter once E7 admission exists; click → Admin Center Tools. |
| **Rename LLM Calls / rename the Tools deck** | No rename | LLM Calls already carries the rename. The deck keeps `λ TOOLS` / key `t`; its blurb becomes "Tool runs and the LLM tool-call timeline". |
| **A modal ToolRun viewer** | Not needed | The Admin Center detail pane plus the Runs card cover every entry point. `v` opens the full log in the existing pager. |

---

## 6. Recommended design, surface by surface

### 6.1 Row chip: live-only (J1, J2, J6)

```
│ 🎭 sase (RUNNING) ⚒ check 7/11 0t9                    🏃 2m13s / 30m36s
│ 🚀 sase (RUNNING) ⚒⚠ check silent 4m sase-1b2.20       🏃 14m02s
│    └─ ⚙ (CHECKING) ⚒ 3/11 my-sess--mon                 🏃 0m42s
│ 🎭 sase (DONE) 0t8                                      16:24:42 · 52m01s
```

- **Placement:** right after the status, in the same slot family as `⊛ f1 · lint`.
- **Style:** bold amber while live.
- **Stalled:** red `⚒⚠ … silent Nm` once the heartbeat is older than ~60 s (six missed
  10 s samples). Wording is "silent", not "lost".
- **Monitor rows:** the chip drops the tool name when the authored label already says it
  (`⚒ 3/11`).
- **Session containers** inherit the most severe live chip of their members, as they
  already do for monitor labels and `⊛`.
- **No count, ever.** A settled run leaves the row, unless the reopen condition in §5.3
  is met.
- **Width:** ≤ ~16 cells, only on rows with a live run (≤7 concurrent at peak, 1 at
  median). Patch the row on appear/disappear. The rebuild threshold only trips on the
  widest rows.

### 6.2 Identity header chip: selection-scoped verdict (J1–J3)

Add one chip to compact row 2 (`_identity_header_compact.py`), with the same precedence
as `⊛ finalizing`:

- **live:** `⚒ check · lint (mypy) 7/11 · 2m13s / typ 4m13s`. Amber past the tool's
  TYPICAL.
- **settled NEW:** `⚒ check ✗ 3 NEW · 1 KNOWN · 4m12s · 6m ago`
- **KNOWN only:** `⚒ check ≈ KNOWN only · 2 KNOWN · 4m05s`
- **killed:** `⚒ check ⊘ killed at 9m00s · caller signal`, showing the typed
  `terminal_cause`
- **pass:** `⚒ check ✓ 4m01s`

The chip shows the node's **latest run per tool**. When there are multiple tools it shows
the most severe one plus `+N`.

The expanded header gets a `Tool runs` field listing each tool's latest run with its id.
This makes the id selectable and copyable, and ends the "copy the command out of the
body" problem.

### 6.3 Tools deck → `⚒ Runs` card (J3, J4): the canonical per-node view

**Tab and card rules:**
- The deck title becomes `λ TOOLS ┃ ⚒ Runs 3 │ LLM Calls 57`.
- **Runs comes first when it exists.** It is the summarized, high-signal card; LLM Calls
  is the raw firehose.
- Nodes with no runs keep today's single LLM Calls card.
- Monitor and proc nodes that own a run get the Runs card, where today they get only an
  empty LLM Calls. This also covers future `%tool` units, which the `%tool` report says
  land as stand-alone proc nodes labeled `tool:check`.
- Card choice is sticky by id. When a node lacks Runs, fall back to LLM Calls, and
  restore Runs on the next node that has it (FINAL's sticky preference).

**One card block per ToolRun**, reusing the deck → card → block machinery:
- It lands on the newest run.
- `(`/`)` steps between runs.
- The block rail reads `1 ⊘ check  2 ✗ check  3 ✗ check`.
- Session containers aggregate member turns' runs, with a turn label per block, as LLM
  Calls already does per child source.

**Block anatomy** (see the mockup):

```
⚒ check  ✗ new_failures — 3 NEW · 1 KNOWN · 0 FLAKY      run 6c3d5107 · 4m12s (typ 4m13s)
  turn 0t9--code · inline · 16:21:04 · bead sase-1b2.20 · ← LLM call 16:21:03 Bash
  ▇▏▇▏▇▏▇▏█████████▏██▏▇▏██████████▏█████████████▏██▏▇      (stage waterfall: width ∝ time)
  ✓ fmt (python) 0.3s   ✓ lint (mypy) 1m03s   ✗ lint (symvision) 1m07s   ✗ test (scoped) 1m31s …
  NEW   lint (mypy)       _tree.py:622 Name "prefix_key" already defined   35 runs · 33 agents
  KNOWN lint (symvision)  intent_accept in monitor/no_new_receipt.py      44 runs · since 09-26
  LOG TAIL  last 12 lines · 1.2 MB retained (truncation stated, never hidden)
  v full log · ( ) other runs · ^J LLM Calls · sase tool show 6c3d5107… -l
```

- **The stage waterfall** is the one genuinely new visual. Stage widths are proportional
  to elapsed time and colored by stage result, so you see at once where the 4 minutes
  went and which stage broke. It needs no new data; `stages.elapsed_ms` already exists.
- **Live runs:**
  - The waterfall grows as stages finish.
  - An open, hatched segment for the in-flight stage is labeled with the *expected next
    stage*, from the last complete run with the same `definition_digest`. It is
    presented as `→ lint (mypy)?`, never as fact.
  - A 1 Hz tick runs only while the card is visible and navigation is idle, reusing
    FINAL's live-tail gate (`decks/final/live.py`).
- **Triage items** show class, stage, display, and cross-agent witness counts. That
  answers "is this mine?" without leaving the card.
- **Actions** are keyboard-first, with every key added to `src/sase/default_config.yml`
  (the core gotcha):
  - `v` opens the retained log in the pager.
  - `y` copies the run id.
  - A palette/leader "Stop tool run" (confirmed) calls the existing `tool_run_request_stop`
    path through its owner.

### 6.4 LLM Calls linkage and Main Reply receipts (J3, J4)

**LLM Calls.** A Bash row whose command is `sase tool run …` (or
`sase monitor start … sase tool run …`) gains `→ ⚒ run N ✗ 3 NEW` after the tool name. The
duration stays. At the EXPANDED level it also gets a one-line stage summary. LLM Calls
has no row cursor, so the `run N` label is the navigation handle: `Ctrl+J`/`)` lands
on that block. The join:

1. `run.agent == turn name`, `run.created_ts ∈ [call start, call end]`, and the argv
   matches.
2. Fallback: scrape `sase tool (run|show) <32 hex>` from the call's output tail. The
   compact footer prints it (`tool/executor_display.py:65-69`); verified on real rows.

No schema change is needed. Provider calls cannot export `tool_use_id` to the child, so
the time-window join is the robust primary.

**Reply receipts.** Each turn's Reply block gets a one-line `⚒` receipt per run in that
turn (at most 3 plus `+N`), styled like the `⊛ FINAL` receipt. When the latest run is NEW
or killed it adds `p t open Runs`. The Context card's existing `SLOW TOOL CALLS` section,
which is mostly `sase tool run check` calls, gains the same verdict suffix.

### 6.5 Monitor and proc nodes that own a run (J6)

- **Context card:** a `Tool run  ⚒ check ✗ 3 NEW · 04349ecf  (sase tool show …)` row among
  the MONITOR TURN fields.
- **Output card:** keeps the raw log, with the stage waterfall pinned above it.
- **Row chip** as in §6.1.

All three require the §7.1 bug fix.

### 6.6 Admin Center → Tools pane (J2, J5, J7, J8)

A new pane beside Procs and Statistics, with three views:

- **Runs** (default).
  - Live first, then recent. Filters: tool, state, agent; `A` for all projects.
  - Columns: glyph, TOOL, STATE/VERDICT, ELAPSED (`/ typ` while live), AGENT/OWNER, STAGE.
  - The 52 h zombie shows as `running · silent 51h` in red at the top.
  - The detail region uses the **same block renderer** as the Runs card.
  - Keys: `enter` opens the run, `a` jumps to the owning agent node on the Agents tab,
    `v` opens the log, `s` stops (confirmed).
- **Failures.**
  - `sase tool failures` groups: class, tool/stage, signature, runs, agents, first/last,
    owner.
  - `enter` lists the affected agents and jumps to one. This is the answer to "is
    master red and who is blocked by it".
  - The natural place to offer "file a `ci` task bead" is later, via `/sase_new_task`
    semantics.
- **Catalog.**
  - `sase tool list` LAST/TYPICAL.
  - `r` starts `sase tool run -H <tool>` as a proc-owned run. That path already exists,
    is fail-closed, and notifies once.
  - Receipts coverage (`sase tool receipt`, ~1 s) loads on demand in a worker. The
    receipts opportunity report (~7 s) is never loaded automatically.

**Notifications.** Implement `sase-189` as a real `open-tool-run` action. Route it to the
agent's Runs block when the run has an agent; otherwise route it to this pane focused on
the run.

---

## 7. Data and performance architecture

### 7.1 Prerequisite bug: the monitor scan drops `tool_run_id`

`monitor_tool_run_id` is written to `agent_meta.json` (`monitor/start.py:411`) and has a
wire slot, but the Rust scan never populates it: 0 of 1,599 monitors carry it.

The root cause is verified in sase-core:
- `AgentSessionTurnMonitorWire` (`crates/sase_core/src/agent_scan/wire.rs`) has no
  `tool_run_id` field.
- `scanner.rs:1526-1540` never reads the key.
- `sase-17p.3` added the key on the Python side only.

Fix it in sase-core's scan wire and move the pin. Then thread it through
`_meta_enrichment_monitor.py` → `Agent` fields → render-cache key. This also restores
the CLI's `sase monitor show` "Tool run" row. **Filed as `sase-1bi`** (bug, medium,
ready).

### 7.2 A slim node-summary projection in sase-core

The Rust-boundary litmus test applies: mobile, Telegram, and a web UI would all want
"agent X is in `check`, 7/11, 2m13s". Add to sase-core:

- **`tool_run_node_summaries({agents: [...], owners: [(kind, id)...], since_ts,
  per_node_limit})`**. It returns, per node, without fingerprints:
  - live runs: tool, run_id, state, running_ts, stages_done, expected_stage_count,
    typical_ms, last_heartbeat_ts, owner;
  - latest settled run per tool: state, exit, terminal_cause, verdict, NEW/KNOWN/FLAKY/
    UNKNOWN counts, duration.
- **Indexes** on `(agent, created_ts)` and `(owner_kind, owner_id)`.
- **The verdict-glance classification** (the `✗ ≈ ? ⊘ ✓` bucket) computed in core. The
  CLI (`sase tool runs`) and the TUI then can never disagree.

### 7.3 TUI loading, following established paths

- **Change token.** A stat of `runs.sqlite` + `runs.sqlite-wal` mtimes, registered as an
  `ace_refresh_tokens` surface. An idle tick with no drift reloads nothing (tui_perf rule
  14). While any run is live the token drifts every ~10 s. A reload is one batched
  projection call (~1–3 ms of SQLite) on a worker thread.
- **Row and header data.** Follow the bead-warmup pattern
  (`actions/agents/_loading_bead_warmup.py`): coalesced, deferred during j/k bursts,
  re-attached by identity, `_try_patch_agent_row`. Add the chip token to the render-cache
  key deliberately. Elapsed ticks ride the existing 1 s runtime tick.
- **Runs card detail.** `tool_run_show` + `tool_run_triage_show` per run (~1–2 ms each)
  on a worker. Cache in an LRU keyed `(run_id, settled_ts)`; settled runs are effectively
  immutable. Reject stale results by subject identity; the LLM Calls bug `sase-179` is the
  cautionary tale.
- **Never on the UI path:**
  - reconcile;
  - receipt lookup (it re-fingerprints, ~1 s);
  - the receipts report (~7 s);
  - the monitor-scan fallback in `output_paths_for_run`.

---

## 8. Phased plan (one epic, green-master-independent acceptance)

| # | Phase | Repos | Size | User-verifiable result |
| --- | --- | --- | --- | --- |
| 0 | Monitor `tool_run_id` scan fix | sase-core (+pin), sase | S | `sase monitor show <id>` prints the Tool run row; `sase monitor list -j` carries ids |
| 1 | Node-summary projection + indexes + verdict glance + TUI loader and change token | sase-core (+pin), sase | M | A bench shows the idle tick reloads nothing; a live run drifts the token every ~10 s |
| 2 | Row live chip, session and monitor inheritance, heartbeat-silent state, `⚒` glyph (chop link-trail icon → `⏲`) | sase | M | Start `sase tool run check` in an agent and watch `⚒ check k/11` advance, then vanish on settle. The 52 h zombie shows `silent` |
| 3 | Identity-header chip + expanded `Tool runs` field + Reply receipts + SLOW TOOL CALLS suffix | sase | M | Selecting any agent answers "did its last check introduce NEW failures" without opening a deck |
| 4 | Tools deck multi-card: `⚒ Runs` card with per-run blocks, waterfall, triage, log tail, `v`/`y`/stop; LLM Calls linkage | sase | L | `p t` shows Runs; `(`/`)` steps runs; LLM Calls rows point to `run N` |
| 5 | Admin Center Tools pane (Runs / Failures / Catalog) + `sase-189` notification action | sase | M | A `-H` settlement notification opens the run; Failures → agents jump works |
| 6 | Docs, glossary (LLM Calls strand's "future ToolRuns"; Agent Data Deck strand's Tools deck description; Tool Run strand's surfaces), `docs/ace.md`, keymaps, visual goldens | sase + memory | S–M | `just fix-tui-screenshots` report reviewed; glossary edits via `/sase_memory_write` |

Notes on the plan:
- **Phases 2–3 deliver most of the value** and could ship before the deck work.
- The epic carries one beta flag per project convention.
- The epic lands after the in-flight deck-views and FINAL work (`sase-1b1`, `sase-1b2`)
  settles, because phase 4 touches the same deck chrome.

---

## 9. What not to build, and when to revisit

- **No count, no persistent row verdict.** Reopen the verdict mark when ≥70% of agents'
  last checks are pass or KNOWN-only for a week.
- **No ETA.** Reopen after E6 forecasts are calibrated (≥80% interval coverage); then the
  header's `typ` becomes an honest interval.
- **No TUI-side reconcile or "lost" guessing.** Heartbeat silence is shown as silence.
  A scheduler job that reconciles and notifies on stalled runs is a separate, backend
  follow-up.
- **No top-bar chip** until E7 admission gives it a capacity meaning.
- **No child nodes for inline runs; no 5th deck; no 4th tab** (§5.3).
- **Later, on evidence:**
  - an Agents query filter (`tool:running`, `verdict:new`) once the projection exists;
  - rendering run ids in bead notes and Context as jumpable references (agents already
    cite them), which may fold into a `tool:<run-id>` artifact reference;
  - a FINAL enricher that renders `verdict_provenance` (receipt id → run).

---

## 10. Open questions for Bryan

1. **Glyph.** Take `⚒` for ToolRuns and move the chop/job link-trail icon to `⏲`
   (recommended; the hammer is the legible metaphor)? Or keep `⚒` for chops and use
   `⛏`/`⚗`?
2. **Runs before LLM Calls** in the Tools deck? I recommend it.
3. **Stop from the TUI.** Should stopping an *agent's inline* run be allowed (it makes the
   agent's command exit 143), or only proc- and monitor-owned runs?
4. **Should the killed-at-9-minutes pattern become its own signal?** It is 27% of checks
   and wastes about 9 minutes each; `sase-17g`/`sase-17e` attack its root cause. The TUI
   can make it visible (`⊘ killed at 9m00s`), but the fix is routing.

---

## Appendix A: Verification log

- Code sweeps (deck/card stack, row renderer, ToolRun APIs) with spot checks:
  - `tool/sample.py:21` (`SAMPLE_INTERVAL_SECONDS = 10.0`)
  - `decks/panel_chrome.py:383` (hard-coded LLM Calls tab)
  - `tool/executor_recording.py:38-48` (attribution)
  - `monitor/start.py:411` (`monitor_tool_run_id` write)
  - `config_center_catalog.py:17-25` (panes)
  - `tool/liveness.py:192` (reconcile)
  - `decks/spec.py:28-73` (decks)
  - `link_trail.py:27`, `link_subject.py:29` (`⚒`)
- `sase monitor list -a -j`: 1,599 rows, 0 with `tool_run_id`. `sase monitor show
  srnrtrezmx4p`: no Tool run row.
- Ledger SQL (read-only `mode=ro` URI) for every number in §2.
- Glyph coverage via `tests/ace/tui/visual/_glyph_audit.bundled_codepoints()`: `⚒ ⚗ ⛏ ⚖ ⏲`
  are bundled and 1 cell; `🔨` is 2 cells.
- Live capture with `sase screenshot`. The deck picker lists `λ TOOLS · LLM tool-call
  timeline`, and Tools shows "No LLM calls for this agent" on a clan.
- Beads read: `sase-189`, `sase-17g`, `sase-17e`, `sase-17p` (notes).
- Prior research via `sase artifact read`:
  - `research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md` (E5 "surfaces"
    sketch)
  - `research:202609/tool_launch_directive/tool_launch_directive.md` (`%tool` units as
    proc nodes)
  - `research:202609/agents_tab_decks_and_cards/agents_tab_decks_and_cards.md` (deck
    budget)
