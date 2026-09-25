# Finalizers on the Agents Tab: What Decks, Cards, and Card Blocks Should Do (Researcher cld)

- **Date:** 2026-09-25
- **Repo:** `sase-org/sase` @ `136a3e9488`. The Rust wire was read in the linked `sase-core`
  checkout.
- **Inputs:**
  - the 2026-09-10 consolidated report `agents_tab_finalizer_panel.md` and its
    researcher-B source `agents_tab_finalizer_panel__b.md`
  - the 2026-09-25 consolidated design `agent_data_card_blocks.md`
  - a fresh read of the finalizer runtime, the deck code, and this host's finalizer
    artifacts
- **Question:** How should the Agents tab make finalizers visible and debuggable, in a
  way that stays general enough for finalizers Bryan hasn't written yet? What role, if
  any, should decks, cards, and card blocks play?

---

## 0. Bottom line

**Give finalizers their own agent data deck, `∎ FINAL`.** Its cards are a **Run**
overview plus **one card per finalizer instance**. Inside an instance card, each
**card block** is **one step of that finalizer**: a subprocess, a provider operation,
or a host-owned LLM turn. Blocks are chronological, labelled by attempt, and the panel
lands on the newest one. Around the deck sit three small, always-visible signals:

| Zoom | Where | What it answers | Cost |
|---|---|---|---|
| 0 | **Node row**: `FINALIZING` status word, plus a `∎` chip only while running or after a non-success result | "Is the host landing this, and did it go wrong?" | Free: one field from the existing scan |
| 1 | **Identity header**: a responsive `Final:` lane (like `Shells:`) | "Which finalizers, in what order, which step is running, how long?" | Free: same field |
| 2 | **MAIN → Reply card**: a closing `∎ FINALIZE` phase that also **attributes host-owned LLM turns** | "How did this turn end? Which of these words were not the agent's?" | Free: same field, plus byte offsets |
| 3 | **`∎ FINAL` deck**: Run card plus instance cards, with steps as card blocks | "Why did it fail? Show me the output, the attempts, the evidence, and what the agent declared." | One debounced worker for the selected node |

The earlier recommendation for this feature was a fold section in the Context card plus
an output modal. It was right about the data and the calm rules, and I keep both. Its
*placement* predates agent data decks. Decks now exist, and a deck is strictly better
than a modal for this job:

- it does not block `j/k`;
- it can sit in a split beside the Reply;
- it inherits spread/paged, search, sticky cards and, once they land, card blocks;
- it keeps high-churn finalizer output out of the expensive MAIN document build.

The single most important non-UI decision is to model finalizers as
**run → instance → attempt → step** and to record **steps** in an additive journal. The
reason is not speculative future finalizers. Today's `commit` finalizer already hides a
multi-step story that its result wire flattens. In the example below, a 31.7 s stitch
hit a conflict, a 1 h 29 min host-owned LLM repair turn followed, then a resume, and the
wire records all of it as `attempt 1: success` (§1.2). The same step model covers
`builtin@command`, plugin providers' `describe/validate/execute/verify`, and future
LLM-backed finalizers with no per-provider TUI code.

---

## 1. What is true today (fresh evidence)

### 1.1 Still nothing on the Agents tab

- No finalizer run artifact or field is read anywhere in `src/sase/ace`. The only
  finalizer UI is `%final` completion in the prompt bar
  (`widgets/_prompt_input_bar_completion_rows_directives.py`, backed by
  `finalizers/catalog.py`).
- None of the 09-10 mechanism proposals has landed. A grep for `progress.jsonl`,
  `live_sink`, `phase_started` and `finalizer_state` finds nothing in sase or sase-core.
- `bounded_subprocess.run_bounded_subprocess` (`finalizers/bounded_subprocess.py:44`)
  still buffers output until exit.
- The Rust wire is still v2, with no `running` state and no timestamps
  (`sase-core/crates/sase_core/src/finalizer/wire.rs:4,268-303`).
- `agent_meta.json["finalizers"]` is still written once, before the turn
  (`llm_provider/_invoke.py:206-219`): `{plan_digest, selected, raw_operations}`.
- `AgentMetaWire` has no finalizer field at all (`core/agent_scan_wire_markers.py:122`),
  so today even the *selected list* is invisible to the row scan.

### 1.2 The invisible minutes got longer

I measured the 261 runs still retained on this host (a 14-day reap horizon).

| Metric | Value |
|---|---|
| Aggregate outcomes | 248 `success` / 13 `failed` (5.0%) |
| Instances ever configured | 1 (`commit`), in 261 of 261 runs |
| Runs with zero attempts (clean tree, `not_triggered`) | 26 (10%) |
| **Stitch attempt wall time** (`attempt-N.<repo>.outcome.json` `duration_seconds`, n = 187) | **p50 96 s, p75 125 s, p90 201 s, max 841 s** |
| Stitch attempts over 30 s / over 2 min | **84.5% / 30.5%** |
| Runs that needed a conflict-repair LLM turn | 25 (9.6%) |
| **Conflict-repair turn wall time** (prompt mtime → response mtime, n = 18) | **p50 89 min, p90 3 h 03 min, max 6 h 45 min** |
| Runs with a declaration-recovery LLM turn | 24 |

The 09-10 report measured a p50 of 2 s for the whole phase. The typical agent now
spends about **1.5 minutes** in the finalizer phase. One agent in ten runs a
**host-owned LLM turn lasting more than an hour**. Throughout that time its row reads
`RUNNING`.

Here is a concrete run, `ace-run/202609/25/20260925114805` (`1p.f0--code`):

```text
17:26:48  final_submission.json accepted (commit, trigger=dirty_repository)
17:27:18  before-commit hook `just fix` (commit_hooks/…json, live-logged)
17:27:20  stitch main → exit 2: rebase conflict in two PNG goldens (31.7 s)
17:27:50  conflict_repair_prompt.main.md written → host-owned LLM turn starts
18:57:58  conflict_repair_response.main.md written (≈ 90 minutes later)
18:58:06  finalizer_result.json: commit success, attempts=[{1, success}]
          final_context.json republished with trigger = not_triggered
```

Four facts from this run shape the design:

1. **The wire squashes the story.** "Attempt 1: success" hides the conflict, the
   repair turn and the resume. The only record of them is file mtimes. Its evidence
   list repeats the same `cwd/result/commit_sha/commit_tree/pushed` group twice,
   because evidence is still not deduplicated at write time.
2. **Host-owned LLM turns write into the agent's own Reply.**
   `run_conflict_repair_turn` calls `provider.invoke(...)`
   (`finalizers/commit_repair_conflict.py:358`). The provider appends to the same
   `live_reply.md` and `tool_calls.jsonl`, because `open_live_reply_file` opens with
   `"a"` (`llm_provider/_subprocess_artifacts.py:30-36`). So today the Reply card shows
   90 minutes of repair-turn text **as if the agent had kept talking**, and the LLM
   Calls card mixes in the repair turn's tool calls. This is a correctness problem in
   the existing UI, not only a missing feature.
3. **`final_context.json` is misleading after the fact.** It is republished after the
   run and says `not_triggered` because the tree is clean by then. The truthful trigger
   is in `final_submission.json → accepted_context.requirements[].trigger`
   (`dirty_repository`), or it should be snapshotted into the journal at phase start.
4. **A live-log precedent exists one level down.** Commit hooks already write
   `commit_hooks/<stem>.json` with status `starting → running(pid) → success|failed`,
   `start_time`, `end_time` and `duration_seconds`. They also write live-appended
   `.stdout.log`/`.stderr.log` (capped at 1 MiB) and rewritten `.tail` files
   (`workflows/commit/command_hooks.py:24-29,107+`). That is exactly the shape a
   finalizer *step* needs, and it is proven in production.

### 1.3 Other channels that already exist

- **Monitor host completion already has a "finalizing" phase.**
  `record_status(... FINALIZING_STATUS)` writes `agent_meta.monitor_host_completion_status`
  through `update_meta_field` (`monitor/host_completion_state.py:271-282`). The Rust scan
  carries it and the monitor section shows `Finalizing`. That covers monitor rows only,
  but it proves the "phase field in `agent_meta`, projected by the scan" pattern. The
  finalizer controller also runs in `no_model` mode for these monitors, so a generic
  finalizer status would cover monitors for free.
- **`workflow_state.json["activity"]`** is scanned (`WorkflowStateWire.activity`,
  `agent_scan_wire_markers.py:328`) and shown as the header's `Activity:` field. Only
  the PDF step writes it, and it publishes through
  `update_agent_artifact_index_for_marker_mutation` (`axe/run_agent_exec_markers.py:105-150`).
  Two writers of one free-text field would clobber each other, so it is not the right
  home for finalizer state. Its index-refresh call is the right pattern to copy.
- **Plugin providers already return a human `message`, and the host drops it.**
  `message` is an accepted result key (`finalizers/executor_protocol.py:25-38`). Only
  `status`, `evidence` and `diagnostics` are translated (`:131-182`). That makes it a
  free, already-specified **headline channel** for third-party finalizers.
- **The declaration is rich and unused by the UI.** `final_submission.json` holds:
  - the per-instance payloads (commit: repository actions and messages; plugins: their
    payload);
  - the repository obligations with paths;
  - accepted deferrals;
  - validation results.

  `final_submission_attempts.jsonl` holds every submit attempt with `code`, `message`
  and `recorded_at`, capped at 50. For anyone authoring a finalizer that requires a
  submission, "why did my agent's declaration get rejected?" is the first debugging
  question.

---

## 2. The shape of the data, without overfitting to `commit`

### 2.1 One model: run → instance → attempt → step

| Level | Identity | Carries |
|---|---|---|
| **Run** | one agent-shell turn, or one monitor host completion (`run_id` = artifacts timestamp, `mode` = `agent_turn` or `no_model`) | the sealed plan (order, policy, provider identity); the declaration history; phase state and timing; controller cycles; drift |
| **Instance** | `instance_id` (`commit`, `check`, …), stable across runs | provider ref; `after` edges; trigger at phase start; runtime status; headline; grouped evidence; scoped diagnostics; refusal/deferral |
| **Attempt** | `#n` within an instance | status, diagnostic code, start/end. Attempts group steps; they are not a navigation level. |
| **Step** | one observable unit of work | kind, label, target, status, start/end, logs (live and canonical), summary, exit code, and for LLM steps the reply and tool-call ranges |

Step kinds are closed and small:
- `process`: a subprocess such as `just check`, `stitch create`, or a hook.
- `operation`: a plugin protocol call (`describe/validate/execute/verify`).
- `llm_turn`: a host-owned model turn (conflict repair, declaration recovery, a future
  reviewer finalizer).
- `wait`: lock or queue waits.
- `note`: informational.

### 2.2 How every provider kind maps, today and planned

| Finalizer | Steps (per attempt) | Headline | Typed evidence worth rendering |
|---|---|---|---|
| `builtin@commit` (today) | `reconcile` (machine-owned state), `checkpoint resume`, per-repo `stitch <repo>`, `conflict repair <repo>` (`llm_turn`), `resume <repo>`, `follow-up commit` | `31a37bd pushed` / `2 repos committed` / `deferred: protected_paths (3 paths)` | per-repo groups keyed by `cwd`; `commit_sha`, `commit_tree`, `pushed`, `assigned_bead_status` |
| `builtin@command`, e.g. a `check` running `just check` (the example in plan `202608/pluggable_finalizers.md`) | one `process` step: `run · just check` | `exit 0 · 2m38s` / `exit 1` | `exit_code`, `duration_seconds` |
| Plugin, e.g. a PR, Telegram notify, or doc-structure lint | `prepare` (describe plus validate, collapsed unless it failed), `execute`, `verify` | the provider's own `message` (today dropped) | `url`, `id`, `path`, and generic key/value |
| Future LLM-backed finalizer (a reviewer, a release-notes writer) | `llm_turn` step(s) | provider message or first line of the response | reply and tool-call ranges; response rendered as Markdown |
| Controller-level (not an instance) | run-level `declaration recovery` (`llm_turn`), `plan integrity` failure | n/a | shown in the Run card |

Because every row above uses the same five step kinds, the TUI never branches on
provider identity. The only provider-aware code is a **headline and evidence
presentation table** in the Rust projection (§6.4). Unknown providers fall back to the
plugin `message` and plain `kind: value` rows.

---

## 3. Where finalizers belong: evaluating the surfaces

Criteria: glanceability; troubleshooting depth; live following during minutes-long
phases; generality to N instances; session and monitor coverage; fit with the
deck/card/block invariants; performance; and the `j/k` triage loop.

| Surface | Verdict | Why |
|---|---|---|
| Row status word + chip | **Yes (zoom 0)** | The only thing visible for every agent at once. Must use already-scanned data. |
| Identity header lane | **Yes (zoom 1)** | Spans every deck panel and "belongs to none" (glossary: Deck Panel), so it is visible whichever deck is showing. `Shells:`/`Wait:` lanes are the exact precedent. |
| Fold section in the Context card (09-10 plan) | **No** | The Context card is now "what went *into* the agent" (the SASE CONTEXT lanes, then the prompt). Identity moved to the header panel. A lifecycle *ending* does not belong above the prompt, and the header lane already does the one-line job. |
| New card in MAIN (`Context │ Reply │ Final`) | **Tempting; reject** | See §3.1. |
| Closing phase inside the Reply card | **Yes, small (zoom 2)** | Chronological closure. The repair-turn misattribution (§1.2 fact 2) can only be fixed where that text is rendered. |
| Output modal (09-10 plan) | **Replace with the deck** | A modal blocks `j/k`, cannot be split beside the Reply, and duplicates what decks already do (paging, search, `V`, `E`). |
| New top-level tab | **No** | Finalizers have no life independent of a run. |
| **New `∎ FINAL` deck** | **Yes (zoom 3)** | See §3.2. |

### 3.1 Why not a Final card in MAIN

It is the closest alternative, and it has real charm. In spread mode the MAIN deck
would read Context → Reply → Final, top to bottom. A sticky `Final` card would give a
triage loop. But four problems decide against it:

1. **Churn in the most expensive document.** The MAIN document is rebuilt by the
   prompt-panel builders and re-measured for spread/paged (`measure_main_rows`). A
   14,000-line session Reply is a real case. Finalizer state changes at every step and,
   with live output, every second or two. Putting it in MAIN means rebuilding and
   re-measuring Context and Reply to update a log tail, against `tui_perf` rules 6 and 8.
   A separate deck updates only when it is visible.
2. **Finalizer output would flip MAIN's layout.** A failing `check` log would push MAIN
   from spread to paged, so the user's reading layout changes because of a subprocess.
3. **The data has three levels, and MAIN has one to spare.** A Final card leaves only
   blocks for instances. Steps and attempts, which is where troubleshooting happens,
   would then have no navigable level, because blocks never nest. A deck maps
   run → deck, instance → card, step → block exactly.
4. **Builder fan-out.** Every Main builder site would need a Final card: regular
   agents, sessions, attempts, hint mode, and steps (the survey found about ten
   `card_document(...)` call sites). A deck has one builder.

### 3.2 Why a deck is the right container

- **It matches the glossary definition.** A deck is "a named, ordered set of agent data
  cards about the selected sase node". MAIN is the conversation, FILES is what changed,
  TOOLS is what the *model* did. **FINAL is what the *host* did to land it.** The four
  decks are orthogonal.
- **It is rarely empty.** `commit` is a default finalizer, so nearly every agent-shell
  node has a sealed plan. Monitors with host completion have one too.
- **Split view is the killer feature for live phases.** `|` puts MAIN/Reply on the left
  and FINAL on the right, so you watch the repair turn's prose and the stitch log
  together. Each deck panel keeps its own card and block cursor.
- **The triage loop comes free.** With FINAL focused, `j/k` walks agents. A sticky
  instance card (for example `check`) stays put across nodes because card ids are
  instance ids, which are stable.
- **The machinery already exists.** `MainDeckView` renders any `MainDeckDocument`
  (a tuple of `CardPart` plus subject, partial flag and digest; `decks/main_view.py`,
  `decks/main_document.py`). A FINAL document is the same type, so FINAL gets
  spread/paged, anchors, card cycling, search and, later, card blocks by reusing it
  rather than writing a third bespoke panel like Files and Tools.

---

## 4. The roles of decks, cards, and card blocks

| Concept | Role for finalizers | Why this unit and not another |
|---|---|---|
| **Deck** `∎ FINAL` | exactly **one finalizer run**: the selected node's own run. For a session container it is the newest agent shell's run (§5.6). | "One run per deck" keeps card and block meanings invariant across node kinds. |
| **Card** `run` | the Run overview: pipeline, declaration history, cycles, drift, session roll-up | the default and landing card. It answers "what happened" before you pick an instance. |
| **Card** `<instance_id>` | one per selected instance, in plan (topological) order, with the status glyph in the tab pill | Instance ids are **data identity** and stable across runs, so the sticky preferred card works across `j/k`. That is the property card blocks lost with "one card per shell", which the blocks report rejected. |
| **Card block** | **one step** inside an instance card, chronological, with the attempt shown as a `#n` label on the step and in the rail | Steps are the real timeline. Landing on the newest block lands on the running step or on the step that failed. `[` walks back through the attempt and then into the previous attempt. |
| Block rail | the step timeline, e.g. `#1 stitch main ✗ ─ repair main ✓ ─ ▐resume main ✓▌` | Answers "how did this instance get here?" in one row. It is the same component card blocks is building, fed by step metadata instead of shell rows. |

Alternatives considered for the block unit:

| Block unit | Verdict |
|---|---|
| One block per **attempt** | Rejected as the navigable unit. 233 of the 235 instances that ran (99%) had exactly one attempt, so there would be no rail exactly when the story is richest (§1.2: one "attempt" contained a conflict, a 90-minute LLM turn and a resume). Attempt boundaries are kept as labels. |
| One block per **instance** inside a single Run card | Rejected: it leaves steps with no navigable level, and it recreates problem 3 of §3.1. |
| One block per **shell run** (sessions) | Rejected for v1. It gives blocks two meanings depending on node kind. The session roll-up is a section of the Run card instead (§5.6). |
| Nested blocks (attempt ⊃ step) | Forbidden by the card-block invariant "blocks never nest", and rightly so. |

**What finalizers teach the card-block design.** This is one small extension,
recommended for the card-blocks epic itself. Log-like blocks should land **tailed**, not
at the top. Card blocks' open question 4 recommends "land at the top" for running Reply
blocks, which is right for prose. For a running `process` step, the error is at the
bottom and the useful motion is follow. Add `BlockMeta.landing: top | tail`:
- prose (agent shells, `llm_turn`) lands `top`;
- logs (`process` steps, monitor output) land `tail` and follow while pinned.

**Before card blocks land,** FINAL renders steps inline, with the same phase-divider
style and anchor meta that card blocks will adopt as block headers. This is the same
"the split points already exist" path the blocks report uses for session Replies, so
no work is thrown away.

**In the MAIN Reply,** the `∎ FINALIZE` phase lives *inside* the agent shell's block.
For a session Reply with shell blocks, it is the tail of that shell's block; blocks
never nest, and a finalization is not a shell. The rail's status glyph for that shell
shows `FINALIZING` while it runs. For a single agent, card blocks v1 gives the Reply no
blocks, and the phase is simply the Reply's last section. A later extension could make
"agent turn | finalize" two blocks of a single-agent Reply, but only after card blocks
ship. Don't force it now.

---

## 5. The experience

### 5.1 Glyphs, colors, vocabulary (one language everywhere)

I adopt the 09-10 merged state vocabulary with two additions. Glyph, word and color
always travel together, so every state reads without color and can be found in
screenshots.

| State | Glyph | Style | Source of truth |
|---|---|---|---|
| selected (plan sealed, phase not started) | `◌` | dim | plan |
| pending (phase running, instance not started or blocked by `after`) | `◌` | dim | journal |
| running | `●` | bold `#FFD700` | journal: unmatched start and a live runner |
| success | `✓` | bold `#5FD75F` | result |
| failed | `✗` | bold `#FF5F5F` | result |
| refused | `⊘` | bold `#FF87FF` | result: a decision, not an error |
| deferred | `⏸` | bold `#FFAF5F` | result: typed reason and paths |
| not triggered / skipped | `○` | dim | trigger at phase start (never the republished `final_context.json`) |
| not run | `–` | dim | projection: planned, but the controller ended first. Shows `blocked by X`. |
| interrupted | `!` | bold `#FFAF5F` | journal ends mid-step and the runner is dead. Never shown as a forever-spinner or as `failed`. |
| unavailable | `⚠` | yellow | parse, size or integrity failure. Raw-file access is kept. |

**Deck identity.**
- Glyph: `∎` (U+220E, END OF PROOF). It means "this is how the turn ends". It is unused
  in the TUI, and it is visually distinct from `◆ ▤ λ` and from the monitor `⚙` and gate
  `⋔` glyphs. The 09-10 candidate `⛭` reads as the monitor gear at small sizes.
- Name: `FINAL`, matching `sase final` and `%final`.
- Accent: one new color, distinct from every status color. Pick it in the golden review.
- Picker key: `n` (fi*n*al). `m/f/t` are taken, `j/k/q/p` are reserved, and capitals
  already mean "show in the other panel".
- Blurb: "How the host landed this turn".
- Count noun: `finalizer`/`finalizers`.
- Position: appended to `DECK_CYCLE` after TOOLS, so existing `Ctrl+N/P` muscle memory
  is unchanged.

### 5.2 Zoom 0: the node row

```text
▶ FINALIZING   1p.f0--code        ∎ commit 1:42
▶ FINALIZING   fix-flaky-4        ∎ 2/3 check
✓ DONE         research.a.cld
✓ DONE         docs-sweep-2       ∎⏸
✗ FAILED       lint-fix-7         ∎✗ check
```

- **`FINALIZING`** replaces `RUNNING` from the moment the provider turn returns until
  the result is published. It is bucketed under **Running**, so ordering, filters and
  capacity accounting are unchanged. This is the highest value-per-line change in the
  whole design: the typical agent that has work to commit spends about 1.5 minutes here
  (§1.2).
- **The chip** appears only while running (`∎ <instance> <elapsed>`, or `∎ i/n` for
  pipelines) or after a non-success result. A `DONE` row with `∎⏸` is important: work
  was *not* committed even though the agent "succeeded". Success adds no chip; 95% of
  runs succeed, so silence is the reward.

### 5.3 Zoom 1: the `Final:` identity lane

```text
Final:  ∎ commit ● conflict repair · main · 42:10  ─▶ check ◌  ─▶ notify ◌
Final:  ∎ commit ✓ 31a37bd pushed · 1h31m  ─▶ check ✓ 2:38  ─▶ notify ✓
Final:  ∎ commit ✓ 31a37bd  ─▶ check ✗ exit 1 · 2/2 attempts  ─▶ notify – blocked by check
Final:  ∎ commit ○ not triggered · clean tree
```

- It is a responsive section (`FINAL_SECTION_ID = "final"`) with the same wrapping and
  hiding rules as `ResponsiveShellSection` (`prompt_panel/_agent_shell_section.py`).
- `─▶` is drawn only for real `after` edges; otherwise the separator is `·`.
- A `⚠ config drifted since plan sealed` suffix appears when `finalizers_drift` is set.
  It is published today and read by nothing (`finalizers/controller.py:80-98`).

### 5.4 Zoom 2: the Reply closes the story honestly

```text
─── AGENT (code) ─── 15:48:02 ────────────────────
…the agent's reply…
─── ∎ FINALIZE ─── 17:26:48 ──────────────────────
  ✓ commit   31a37bd pushed · 1h31m · conflict repair on main
  ─── ∎ commit · conflict repair turn · host-owned ─── 17:27:50 ───
  I resolved the two golden PNG conflicts by regenerating them from …
```

- The phase header and instance lines come from the scanned status field (no I/O).
- Host-owned LLM text is split out of `live_reply.md` at byte offsets that the journal
  records when each `llm_turn` step starts and ends. This uses the same offset mechanism
  as the existing `live_reply_timestamps.jsonl` turn dividers. The words stay where they
  are; only their **attribution** changes.
- This is the whole MAIN-deck footprint. Detail lives in FINAL.

### 5.5 Zoom 3: the `∎ FINAL` deck

The sketches below are illustrative. Timestamps, the 5.0 KB repair response and the
exit-2 conflict come from the real `20260925114805` run. The `check` and plugin
instances, the prose lines, the tool-call counts and the test names are invented to
show the layout.

**A settled two-finalizer run, spread (everything fits):**

```text
╭─ ∎ FINAL ┃ Run │ ✓ commit │ ✓ check ─────────────────────────────────────────╮
│ RUN · plan c21e7df · agent turn · 17:26:48 → 17:31:02 · 4m14s               │
│                                                                              │
│ PIPELINE                                                                     │
│   ✓ commit   builtin@commit    default   ▰▱  1m36s   31a37bd pushed          │
│   ✓ check    builtin@command   %final    ▰   2m38s   just check · exit 0     │
│              └ after commit                                                  │
│                                                                              │
│ DECLARATION · accepted 17:26:48 · 2nd submission                             │
│   ✗ 17:26:12  rejected   placeholder commit message                          │
│   ✓ 17:26:48  commit main  "feat(ace-tui): show a deck in the other…"        │
│               bead sase-17x.13 → close                                       │
│                                                                              │
│ ━━ ✓ commit ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ ─── ▸ #1 stitch · main ─── 17:26:49 ─── 1m36s ✓ ───                          │
│   31a37bd  tree 40876f4  pushed ✓                                            │
│ ━━ ✓ check ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ ─── ▸ #1 run · just check ─── 17:28:25 ─── 2m38s ✓ exit 0 ───                │
╰───────────────────────────────────── spread · settled ✓ · 2 finalizers ─────╯
```

**A failing `check`, paged, with card blocks** (the landing view for this node):

```text
╭─ ∎ FINAL ┃ Run │ ✓ commit │ ✗ check  3/3 ─────────────────────────────────╮
│ #1 run ✗ ─ ▐#2 run ✗▌                                    [ older · newer ] │
│ ─── ▸ #2 run · just check ─── 18:54:01 ─── 2m06s ─── ✗ exit 1 ───          │
│   argv just check · cwd primary · timeout 1800s · budget 2/2 exhausted     │
│   ⋯ 214 earlier lines · E opens attempt-2.stdout                           │
│   FAILED tests/ace/tui/test_final_deck.py::test_spread - AssertionError    │
│   error: recipe `check` failed on line 12 with exit code 1                 │
│                                                                            │
│ RESULT                                                                     │
│   ✗ command_failed   exit 1 on attempt 2 of 2                              │
│   + 1 earlier diagnostic (attempt 1)                                       │
╰─────────────────────────────────────────── paged · failed ✗ · 2 attempts ─╯
```

**The real 90-minute run, restored.** The rail tells the story the wire lost:

```text
│ #1 stitch main ✗ ─ repair main ✓ ─ ▐resume main ✓▌                         │
│ ─── ◆ #1 conflict repair · main · host-owned LLM turn ─── 17:27:50 ─── 1h29m ✓ ───
│   prompt conflict_repair_prompt.main.md · response 5.0 KB · N tool calls   │
│   I regenerated the two conflicting PNG goldens from the rebased tree …    │
```

**A plugin finalizer.** The provider's `message` becomes the headline, typed evidence
is rendered, and the protocol JSON sits at a deeper fold level:

```text
│ prepare ✓ ─ #1 execute ✓ ─ ▐#1 verify ✓▌                                   │
│ ─── ▸ #1 execute ─── 17:29:10 ─── 3.2s ✓ ───                               │
│   Posted release notes to #releases                  ← provider `message`  │
│   url  https://t.me/c/…/4182     id  4182            ← typed evidence      │
│   ▸ stderr · 12 lines                                                      │
│   ▸ request / response                               ← fold level 3        │
```

**Live, while finalizing** (land tailed and follow while pinned):

```text
╭─ ∎ FINAL ┃ Run │ ● commit │ ◌ check  2/3 ─────────────────────────────────╮
│ ▐#1 stitch main ●▌                                                         │
│ ─── ▸ #1 stitch · main ─── 17:26:49 ─── 0:42 ● ───                         │
│   🔄 Running before commit hook: just fix                                  │
│   🔄 Dispatching create_commit to VCS provider...                          │
│ ── live · following ──────────────────────────────────────── 1.4 KB ──     │
╰─────────────────────────────────── paged · finalizing ● · commit 0:42 ────╯
```

**Chrome and landing rules:**

- **Title:** `∎ FINAL ┃ Run │ ✓ commit │ ✗ check`. Tab pills carry the instance status
  glyph through a small `CardTab.badge` extension. The existing tier logic (full →
  compact → micro) applies unchanged.
- **Subtitle:** `settled ✓ · 2 finalizers · 4m14s`, or while running
  `finalizing ● · commit 0:42`, with the usual spread tag and counts.
- **Landing card:** attention-first.
  1. A **new subject** lands on the running instance.
  2. Otherwise it lands on the first failed, refused or deferred instance.
  3. Otherwise it lands on **Run**.
  4. A card the user chose explicitly with `Ctrl+J/K` stays sticky across `j/k`, as
     MAIN's does.

  This is the GitHub Actions "open the failed job" precedent. The Run content is also
  echoed by the header lane, so skipping it costs nothing.
- **Landing block:** newest. `process` steps land tailed; prose lands at the top.
- **Fold levels** use the existing fold language (`append_fold_section_heading`):
  - `z 1`: step lines only.
  - `z 2` (default): adds the output tail, headline and evidence.
  - `z 3`: adds inputs (`inputs.json`, argv, env allowlist, config snapshot) and plugin
    request/response JSON. This is the finalizer-author level.
- **Keys:** no new keys. Use `p n` (picker), `Ctrl+N/P`, `Ctrl+J/K` (instances), and
  `[`/`]` (steps, once card blocks land). **`E` on the FINAL deck opens the active
  step's canonical log file(s).** It does not open a render of the card, because the raw
  log is what you want in an editor. `V` pages the full log.
- **Cross-deck hint:** a commit step's `31a37bd` evidence carries a quiet `files ▤`
  hint. The Files deck already shows the commit diff.

### 5.6 Sessions, clans, monitors, attempts, remote rows

- **Agent session container.** FINAL shows the **newest agent shell's run**, labelled
  `RUN · from --code (shell 2 of 3)`. The Run card adds a SESSION RUNS section with one
  line per agent shell, using its roster number, label and outcome:

  ```text
  SESSION RUNS
    0 --plan   ✓ commit 8b1e2f0 (plans sidecar)     17:02
    2 --code   ● commit · stitch main · 0:42        17:26
  ```

  To inspect an older shell's run, select that shell with a JUMP digit or the tree. One
  run per deck is the invariant.
- **Session member shell or single agent:** its own run.
- **Pinned attempt view (retry lineage):** that attempt's run. Every attempt has its own
  artifacts directory.
- **Monitor with host completion (`no_model`):** its run. This subsumes the monitor
  section's `Host final: Finalizing` line into the same vocabulary.
- **Clan or tribe:** v1 shows the empty state "Finalizers run per member — select a
  member". A later **roll-up card** ("which of my six parallel agents failed to land?")
  is the natural v2 and a strong triage tool.
- **Remote or fleet rows:** the row, header and Reply signals work wherever
  `agent_meta.json` syncs. The deck shows "Finalizer details live on `<machine>`" until
  a bounded remote projection exists.
- **Legacy runs with no plan:** the deck is empty, with "No finalizer run for this
  node". The status field is absent, so nothing else renders.

---

## 6. Mechanism (generic, additive, no wire bump)

### 6.1 A run journal with steps

Extend the 09-10 `progress.jsonl` proposal (at `<artifacts>/finalizers/progress.jsonl`,
reusing `append_jsonl_record`) from phase/instance/attempt events to **steps**:

```json
{"v":1,"ts":"…","event":"phase_started","run_id":"20260925114805","plan_digest":"c21e7df…","mode":"agent_turn","instances":["commit"],"triggers":{"commit":"dirty_repository"},"reply_offset":10740,"tool_calls_line":812}
{"v":1,"ts":"…","event":"step_started","step":"s1","instance_id":"commit","attempt":1,"kind":"process","label":"stitch","target":"main","live_log":"finalizers/commit/attempt-1.main.live.log"}
{"v":1,"ts":"…","event":"step_finished","step":"s1","status":"failed","code":"conflict","exit_code":2,"summary":"rebase conflict in 2 files"}
{"v":1,"ts":"…","event":"step_started","step":"s2","instance_id":"commit","attempt":1,"kind":"llm_turn","label":"conflict repair","target":"main","reply_offset":11203,"tool_calls_line":901}
{"v":1,"ts":"…","event":"step_finished","step":"s2","status":"success","reply_offset":15020,"tool_calls_line":1402}
{"v":1,"ts":"…","event":"instance_finished","instance_id":"commit","status":"success"}
{"v":1,"ts":"…","event":"phase_finished","status":"success","cycles":1}
```

- **Who writes it.**
  - The controller writes phase, cycle, instance and attempt events, plus the run-level
    `declaration recovery` step.
  - The host executors write plugin operation steps and command `process` steps
    automatically, so providers do nothing.
  - Commit internals call a small `step()` context manager at the few places in
    `commit_dispatch*.py`, `commit_repair_conflict.py` and
    `commit_checkpoint_recovery.py` where the story branches.
- **Rules** carried over from 09-10:
  - Writes are best-effort: an observability I/O failure never changes a verdict.
  - Readers ignore unknown events and tolerate a truncated last line.
  - `plan_digest` and `run_id` guard against stale journals.
  - Bounds: a cap on events (for example 2,000) and on bytes (256 KiB). Past the cap,
    write one `truncated` event and keep only phase and instance events.
- **Why steps and not only attempts.** The flat wire provably lost a 90-minute repair
  turn (§1.2). The plugin protocol is already four operations. The step is the only
  unit shared by commit, command, plugin and LLM finalizers.

### 6.2 A compact status projection for rows, header and Reply

Add a **sibling** key `agent_meta.json["finalizer_status"]`. Do not extend the sealed
`finalizers` plan projection, so the authenticated plan mirror stays immutable. Update
it at each phase, instance or step transition with the existing `update_meta_field`,
then call `update_agent_artifact_index_for_marker_mutation`. That is the same path
monitor host completion and PDF activity already use.

```json
"finalizer_status": {
  "phase": "running", "status": null, "started_at": "…", "finished_at": null,
  "instances": [{"id":"commit","status":"running","attempt":1,
                 "step":"conflict repair · main","step_started_at":"…"},
                {"id":"check","status":"pending","after":["commit"]}],
  "owned_turns": [{"instance_id":"commit","label":"conflict repair",
                   "reply_start":11203,"reply_end":null}]
}
```

- The field is bounded (instance list capped, labels truncated). Transitions are rare:
  a handful per run, not per log chunk.
- Mirror it as an additive `AgentMetaWire.finalizer_status` in the Rust scan and the
  Python mirror. Update `tests/test_contract_manifest.py` and bump
  `sase-core-revision.txt` (per `docs/rust_backend.md`).
- It drives four things with **zero extra file opens**: the status word, the chip, the
  `Final:` lane, and the Reply's closing phase and attribution.

### 6.3 Live output for every subprocess-backed step

Add the 09-10 `live_sink` to `run_bounded_subprocess`. It is called inside the existing
`_reader` loop (`bounded_subprocess.py:74`), and sink errors are swallowed. The sink
writes a per-step bounded `.live.log` on the monitor log contract (`logs/_bounded.py`,
2 MiB plus one rotation). The canonical `exclusive=True` attempt artifacts are
unchanged. Bind it in:

- `executor_command`: the step log is the command's output.
- `executor_plugin`: **stderr is the plugin's human log**. Stdout stays protocol-only.
  Document this in the SDK.
- The commit stitch subprocess: today its hook and dispatch progress lines are visible
  only after exit.

This also fixes a latent loss: a finalizer killed at its hard timeout currently leaves
no output.

### 6.4 One Rust projection: `FinalizerRunSnapshotWire`

It lives in `sase-core/crates/sase_core/src/finalizer/` and is exposed through
`sase_core_rs`, per `decisions:rust-core-required` and the
`rust_core_backend_boundary` litmus test: a web UI or `sase final` would need the same
answers.

- **Inputs:** plan and authority, submission plus submission attempts, journal, result,
  a stat-only inventory of step artifacts, and runner liveness supplied by the caller.
- **Owns the rules the UI must never re-derive:**
  - **Source precedence.** The authenticated plan decides selection, order and policy.
    A valid terminal result dominates. The journal decides runtime state only while
    `run_id` and `plan_digest` match and the runner is alive. Artifacts supply content,
    never status. No live runner and no result means `interrupted`.
  - **Truthful trigger:** from the journal or the accepted context, never the
    republished `final_context.json`.
  - **Every planned instance gets a disposition** (`not run` / `blocked by X`, never
    silent).
  - **Size ceiling** (1 MiB) before parsing any result, since a 3.32 MB result existed.
  - **Diagnostic and evidence dedupe.** Diagnostics are scoped to the latest attempt;
    superseded ones render dim, so `dirty_work_discarded`-style `error` rows inside
    successful runs never paint the panel red.
  - **The presentation table:** a headline per step and instance (provider `message`,
    else derived from well-known evidence kinds), evidence grouping (scope kinds such
    as `cwd` or `repo` start a group), and typed evidence hints (`sha`, `url`, `path`,
    `duration_seconds`, `exit_code`, `bool`).
- **Consumers:** the TUI worker (as a thin adapter) and a CLI view,
  `sase final run [<agent>] [-f json]`. It is the first per-run command, since
  `sase final list/show` are inventory-only. Name and flags per
  `sase/memory/cli_rules.md` at implementation time.

### 6.5 Two tiny contract clarifications for finalizer authors

- **`message`:** the plugin result's existing, accepted `message` becomes the displayed
  headline. There is no protocol change; `executor_protocol` just stops discarding it.
- **stderr:** plugin stderr is documented as the live human log.

Defer a structured in-band progress channel, such as GitHub-Actions-style
`::group::`/`::sase-step::` lines parsed from the live log, until a real finalizer needs
sub-steps (`decisions:corpus-before-mechanism`). The journal already gives every
provider operation-level steps for free.

---

## 7. TUI architecture

- **Generalize the MAIN document path into a card-document deck.**
  - Rename or alias `MainDeckView`/`MainDeckDocument` to a deck-agnostic
    `CardDocumentView`/`CardDocument`.
  - Parameterize `_decide_main_mode` (`decks/panel_spread.py`) and `cycle_card`
    (`decks/panel.py:289`, which is MAIN-only today) by deck.
  - FINAL is the first consumer. Card blocks, when they land in this view, then apply to
    FINAL with no extra work.
- **Make the preferred card per deck.** `DeckPanelState` has one `preferred_card`
  (`decks/model.py:71`), and `with_panel_deck` carries it across deck switches
  (`:95`). Visiting FINAL and pressing `Ctrl+J` would clobber MAIN's sticky Reply.
  - Change it to `preferred_cards: Mapping[DeckId, str]`.
  - Bump `ace_agents_deck_state.json` to schema v2 and read v1 as `{main: …}`.
- **Add `DeckId.FINAL` at every branch site the survey enumerated.** These are:
  - `model.py` enum and `DECK_CYCLE`
  - `titles.py` (glyph, name, accent, picker key, blurb, count noun)
  - `panel.py` compose (one more `VerticalScroll` holding a `CardDocumentView`),
    `set_deck` and `_deck_is_empty`
  - `panel_chrome` accents
  - `empty_state._MESSAGES`
  - `availability.probe_final_deck`: no I/O, from `finalizer_status` and the sealed
    plan count
  - `search_corpus`
  - persistence decoding
  - docs: `docs/ace.md` deck section and the glossary Agent Data Deck strand (through
    `/sase_memory_write`)
- **Loading and refresh** follow the Tools and header-enrichment precedents:
  - A thread worker calls the Rust snapshot and builds the `CardDocument` off-thread,
    with a cache keyed by mtime and size.
  - A **settled snapshot is immutable**, so cache it for good; there is no refresh after
    settle.
  - While the phase is running, add a `finalizer` surface token that **only stats the
    selected node's journal and active live log, only while FINAL or the header lane is
    visible**.
  - Respect `DetailPanelDebouncer` and `NavigationGate`, and reject stale selection
    generations. Row and header updates ride the existing scan and index path with
    `patch_row`, never a list rebuild.
- **Reply attribution** is a pure transform in the Reply builder. It splits content at
  `owned_turns[].reply_start/end`, the same offset style as turn dividers. It is applied
  in both hint and non-hint builders, including the session phase loop
  (`_agent_display_agent_session_render.py:199-262`).
- **Status word:** add `FINALIZING` to `status_buckets.py` in the Running bucket, and to
  every set that lists `RUNNING` for display, filter or query purposes. Give it a
  distinct style in `append_agent_row_status`.

---

## 8. Performance and calm rules

These are carried over from 09-10 because they are still right, and updated for decks.

1. **No new per-row I/O.** Row, lane and Reply use the scanned `finalizer_status` only.
2. **No new poller.** Refresh happens only for the selected node, only while the phase
   is running, only while visible, and only on token drift. A quiet tick reloads zero
   surfaces: check the `refresh.auto_tick` counters with `SASE_TUI_TRACE=1`.
3. **A 5-second tail gate.** Most finalizers now run for minutes, but short command
   finalizers will exist. No live tail renders until a step has run about 5 s. Fast
   steps just go `● → ✓`.
4. **Bounded everywhere.**
   - 2 MiB rotating live logs.
   - Seek-based tails: about 40 lines per step at `z 2`, and the full log only through
     `V`/`E`.
   - A 1 MiB pre-parse ceiling in Rust.
   - Journal caps.
5. **Sanitized output.** Logs go through the existing cached `render_axe_output(..., "ansi")`,
   never raw Rich markup. Nothing from a tail goes into notifications or telemetry.
6. **Follow only while pinned.** Scrolling up pauses following and shows a quiet
   `↓ N new lines`; new output never moves the reader.
7. **Read-only.** There are no retry or cancel controls. They carry authorization and
   fixed-point semantics that must not be smuggled into a display feature
   (`decisions:host-owned-completion`).

---

## 9. Delivery plan

Each phase is useful alone.

| Phase | Scope | Why this order |
|---|---|---|
| **A. Make the phase visible** | Journal with steps (controller, executors, commit branch points); `finalizer_status` plus the scan field (sase-core); `FINALIZING` and the chip; `Final:` lane; Reply `∎ FINALIZE` phase and **owned-turn attribution**; write-time evidence and diagnostic dedupe | It removes the invisible 1.5 minutes and the 90-minute misattributed repair turns for every agent, and needs no deck work. |
| **B. The FINAL deck (read-only instrument)** | Rust `FinalizerRunSnapshotWire` plus `sase final run`; card-document deck generalization; per-deck preferred cards (persistence v2); `DeckId.FINAL`; Run and instance cards; steps inline with block-ready dividers; fold levels; `E`/`V` on step logs; attention-first landing | Troubleshooting. The first non-MAIN card-document deck, and it proves the abstraction. |
| **C. Live** | `live_sink` plus per-step `.live.log`; plugin stderr log; running-phase surface token; tail gate; follow | It depends on B's view. It is the most perf-sensitive piece, so it lands alone. |
| **D. Card blocks** (after the card-blocks epic lands) | Steps become `CardBlock`s; step rail; `BlockMeta.landing = tail` for `process` steps; session Reply shell blocks show `FINALIZING` | No rework: B's dividers are the block headers. |
| **E. Polish** (each optional) | A Run-card **timeline strip** (a Gantt-style row per instance that answers "where did the minutes go"); a notification on `failed`/`refused`/`deferred-with-work-left`; clan/tribe roll-up card; an LLM Calls boundary marker for owned-turn tool calls; a Config Center finalizers view (`sase final list/doctor` parity) | Value on top of a complete feature. |

- **Flags.** Phase A is a complete, independently correct improvement, so it needs no
  flag. If B must land in more than one change, scaffold it with one `beta` flag created
  by `sase flag new` (`sase/memory/sase_flags.md`), and remove it by deleting the Off
  branch before the epic lands. An empty-ish FINAL deck in `Ctrl+N` is exactly the
  "partial feature reaching users" case.
- **Tests.**
  - Projection fixtures for every §5.1 state. Include:
    - digest mismatch
    - a truncated journal
    - runner death mid-step (`interrupted`)
    - the 3.32 MB duplicate-diagnostic shape
    - the conflict-repair run
    - `not_triggered` after a clean tree, where the republished-context trap must not
      fire
    - a multi-instance `after` chain with an early failure (`not run`, `blocked by`)
    - a plugin with `message` and typed evidence
  - PNG goldens at 120/80/60 columns for:
    - spread settled, paged failed, and running-tailed
    - session Run card
    - empty states
    - the row, lane and Reply phase
  - Perf benches:
    - `SASE_TUI_PERF=1 pytest -s -m slow tests/ace/tui/bench_tui_jk.py`, in SINGLE and
      LEFT_RIGHT; p95 < 16 ms unchanged.
    - Quiet-tick trace counters.
  - An end-to-end fake `builtin@command` finalizer that prints slowly, fails once,
    retries, and then passes, fails or dies.

---

## 10. Risks and open questions

**Risks**

| Risk | Mitigation |
|---|---|
| Four decks make `Ctrl+N` longer | Append after TOOLS. The picker (`p n`) is two keys. FINAL is non-empty for nearly every agent node, so the cycle stop is rarely wasted. |
| Journal and status writes race other `agent_meta` writers | Use the existing `update_meta_field` locking path. A few writes per run. Best-effort. |
| Attribution offsets are wrong if a provider rewrites `live_reply.md` | Offsets are validated against file size. On mismatch, fall back to a closing phase with no split, never a wrong split. |
| Steps become noisy for plugins (describe and validate every attempt) | Collapse `describe`+`validate` into one `prepare` step unless it failed. |
| Card blocks slip | B works without them (inline steps). D is pure upside. |

**Open questions for Bryan**

1. **Deck identity:** `∎ FINAL` with picker key `n`? The alternatives are the name
   `LAND` or the 09-10 `⛭` glyph, which I argue against.
2. **Landing card:** attention-first (running or failed instance) or always `Run`? I
   recommend attention-first plus stickiness for explicit choices.
3. **`E` on FINAL opens the step's raw log** instead of exporting the rendered card. Is
   that acceptable as a per-deck deviation from card blocks' "V/E stay card-wide"?
4. **Should card blocks adopt `BlockMeta.landing = top | tail` in its own epic** (so
   monitor output blocks benefit too), or only in FINAL's Phase D?
5. **Notify on finalizer failure** by default? I recommend `failed`/`refused` and
   `deferred`-with-work-left, never `not triggered`.
6. **Is `check` the next real finalizer?** If so, dogfood Phase B/C against a real
   `builtin@command` `check` instance. The deck is most compelling with a real pipeline,
   and it is the fastest way to catch overfitting to `commit`.

---

## 11. Recommended solution

Build finalizer support as **one generic data model shown at four zoom levels, with a
dedicated deck as the instrument.**

1. **Model finalizers as run → instance → attempt → step, and record steps.**
   - Add an additive, bounded, best-effort `finalizers/progress.jsonl` journal. The
     controller and host executors emit steps automatically for every provider kind;
     commit adds a handful of branch-point steps.
   - Publish a compact `agent_meta.finalizer_status` projection (phase, per-instance
     status, active step, and owned-turn reply offsets). Carry it through the Rust scan
     as an additive `AgentMetaWire` field.
   - There is no v2 → v3 wire bump.
   - Reconcile everything in one sase-core `FinalizerRunSnapshotWire`, shared by the TUI
     and a new `sase final run` view. It owns source precedence, the truthful trigger,
     "every instance gets a disposition", the size ceiling, dedupe, attempt scoping, and
     the headline/evidence presentation table. The plugin's existing `message` becomes
     its headline.
2. **Zoom 0 (row):** a `FINALIZING` status word in the Running bucket, plus a `∎` chip
   only while running or after a non-success result.
3. **Zoom 1 (identity header):** a responsive `Final:` lane that shows the pipeline with
   `─▶` edges, the active step and its elapsed time, headlines, and the drift warning.
4. **Zoom 2 (MAIN → Reply):** a closing `∎ FINALIZE` phase that **attributes host-owned
   LLM turns** (conflict repair, declaration recovery, future reviewer finalizers)
   instead of letting them masquerade as the agent's reply. This is MAIN's entire
   footprint: **no Final card in MAIN.**
5. **Zoom 3 (the `∎ FINAL` deck):**
   - **Deck** = exactly one finalizer run: the selected node's, or the newest agent
     shell's for a session container, with a session roll-up.
   - **Cards** = `Run` plus one card per instance, keyed by stable instance id, with
     status glyphs in the tabs. Landing is attention-first and explicit choices stay
     sticky.
   - **Card blocks** = the instance's **steps**, chronological, labelled by attempt,
     landing on the newest. Log steps land tailed and follow; prose lands at the top.
   - Built by generalizing the MAIN card-document view, so spread/paged, search, sticky
     cards and card blocks come for free. Preferred cards become per-deck.
6. **Deliver in order:**
   - A (visible phase and honest Reply)
   - B (read-only deck)
   - C (live output via the bounded-subprocess sink and the plugin stderr log)
   - D (card-block step rail)
   - E (timeline strip, notifications, clan roll-up)

   Keep it read-only throughout, and apply the 09-10 calm rules: success is silent,
   there is a 5 s tail gate, refresh is selected-node only, and everything is bounded.

Why this is the right shape:

- It uses each container for what it is good at: rows for glance, the header for
  always-visible state, MAIN for the story, a deck for the instrument.
- Its deck → card → block mapping is exactly the data's run → instance → step
  hierarchy.
- It keeps high-churn finalizer output out of the expensive MAIN document.
- Nothing in the TUI knows what `commit` is. A `check`, a PR publisher, a Telegram
  notifier, or an LLM reviewer finalizer each appears as a correctly labelled, timed,
  tail-able, debuggable card the day it is configured.
