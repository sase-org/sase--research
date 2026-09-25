# Finalizers on the Agents Tab: Consolidated Research and Recommendation

- **Lead:** consolidated from four independent reports
  ([cdx](agents_tab_finalizer_visibility__cdx.md),
  [cld](agents_tab_finalizer_visibility__cld.md),
  [mus](agents_tab_finalizer_visibility__mus.md),
  [gem](agents_tab_finalizer_visibility__gem.md)), plus the lead's own checks against
  `sase` master @ `29f18be2b` and a fresh scan of this host's finalizer artifacts
- **Date:** 2026-09-25
- **Prior context:** `202609/agents_tab_finalizer_panel/agents_tab_finalizer_panel.md`
  (called "the 09-10 report" below) and
  `202609/agent_data_card_blocks/agent_data_card_blocks.md` (card blocks, not yet built)
- **Question:** How should the Agents tab show finalizers so users can see them and
  troubleshoot them? What role should decks, cards, and card blocks play? The answer
  must not overfit to `builtin@commit`, because more finalizers are planned.

Paths are relative to `src/sase/` unless marked otherwise.

---

## 0. Bottom line

Finalizers need four zoom levels. Each maps onto a different part of the Agents tab,
and only the diagnose level needs new deck, card, or block structure.

| Zoom | User question | Surface | Structure |
|---|---|---|---|
| **Glance** | "Is it still finalizing? Did landing fail?" | Agent row | A `FINALIZING` display phase that stays in the Running bucket. A `⊛` chip appears only while finalizers run or after a non-success. |
| **In context** | "How did this turn land?" | The end of each shell's phase in the Reply card | A 1–4 line **receipt** under a `─── ⊛ FINAL ───` phase divider |
| **Diagnose** | "What ran, in what order, why, what failed, and what did it print?" | A new **`⊛ FINAL` deck** | **Card** = `Overview`, or one finalizer instance keyed by its stable id. **Card block** = one finalizer *run*, meaning one concrete shell's execution. Attempts and operations are sections inside the block. |
| **Author** | "Why wasn't my finalizer selected? What did my validator reject?" | The FINAL `Overview` card, plus a read-only `sase final` run view | Selection explanation, declaration timeline, controller cycles, drift |

All four levels sit on one provider-neutral data layer:

- a controller progress journal, which also records *why finalization was skipped*
- a uniform per-operation record across executors
- an opt-in structured step channel
- bounded live logs
- a compact `agent_meta.json` summary
- one Rust-core `FinalizerRunView` projection shared by the TUI and the CLI

**Where the researchers split, and how it resolves:**

- **Placement.** cdx and cld add a deck. gem adds a `Finalizers` card to Main. mus adds
  a fold section and no deck, card, or block. **Resolution: a deck** (§3.2). The fold
  section would now land inside the Context card. A Main card has nowhere to put runs
  or attempts, and it would pull off-thread artifact data into the Main build.
- **What a card block is.** cdx says a run, cld says an attempt (but a shell on
  sessions), gem says an instance, and mus says none. **Resolution: a run, which is
  one concrete shell.** That keeps the card-block design's single meaning (§3.4). The
  data also shows that blocks will rarely appear in v1 under *any* meaning, so FINAL
  must be excellent without them.
- **Timing.** The 09-10 report's p50 of 2.0 s is stale. The lead measures a
  **~108 s median** post-turn window, which confirms cld's re-measurement. The
  invisible window is now the typical case, not the tail.
- **A new lead finding.** In 15 days, 102 `--plan` shells sealed a finalizer plan and
  then, correctly, never ran it: a pending handoff skips finalization and writes no
  result. Every report's source-precedence rules would have rendered these as
  `not_run`, `unavailable`, or `interrupted`. The design needs an explicit, calm
  `skipped · handoff` state (§4.1, §5.3).

---

## 1. Evidence

### 1.1 Lead-verified code facts

- **Decks.** `DeckId` is `MAIN | FILES | TOOLS`. `cycle_deck_id` states that "nothing
  is skipped", so empty decks are still visited (`ace/tui/widgets/decks/model.py:11-44`).
- **Sticky cards are Main-only, with one slot per panel.** `DeckPanelState` holds a
  single `preferred_card` ("preferred Main card"). `DeckPanel.cycle_card` returns a
  sticky id only for Main (`decks/model.py:66-71`, `decks/panel.py:289-310`). The
  persisted state stores `{deck, preferred_card}` (`models/agent_deck_persistence.py`).
  A second sticky deck would overwrite Main's sticky Reply, so preferences must become
  per-deck.
- **Lifecycle fold sections now live in the Context card.** SHELLS, WAIT, MONITOR, and
  GATE are appended to `header_text`, which is passed to
  `context_card(header_text, prompt_syntax)` (`_agent_display_render.py:498`). The
  FINALIZERS fold section that the 09-10 report and mus propose would therefore render
  inside Context, the default and most-read card.
- **The TUI reads no finalizer artifact.** Inside `ace/tui`, "finalizer" appears only
  in `%final` directive completion. The only precedent is the monitor section's
  `Host final: <status>` line (`_agent_monitor_section.py:216`).
- **There is no live state.** The controller keeps `active_instance_id` and
  `active_started` in local variables (`finalizers/controller.py:147-150`). It writes
  `finalizers_drift` to `agent_meta.json`, and nothing reads it (`controller.py:86-96`).
- **The handoff skip leaves no record.** `should_skip_finalizers()` returns true when
  any pending-handoff marker exists (`.sase_{plan,questions,monitor,gate,pipe}_pending`).
  The controller then returns without writing a result (`controller_context.py:41-47`,
  `controller.py:122`, `agent/pending_handoff.py`). The markers are consumed later, so
  nothing on disk explains why the shell's sealed plan never ran.
- **Plugin limits.** A plugin provider cannot author `skipped`
  (`executor_plugin.py:149-153`).
- **CLI name collision.** `sase final show <instance>` already exists and shows a
  *configured instance* (`main/parser_final.py:137-142`). A per-agent run view needs a
  different verb.
- **Nothing is built yet.** No `CardBlock` code exists, `AgentMetaWire` has no
  finalizer field, and no finalizer-UI bead or epic exists.

### 1.2 Lead measurements (this host, last 15 days)

| Measure | Value | Design consequence |
|---|---|---|
| Finalizer runs | 196 (179 sase, 16 bob-cli), and every one is a single `commit` instance | Be excellent at one instance, and assume nothing about the count |
| Aggregate status | 194 success, 2 failed (`controller_exception`, `finalizer_failed`) | Success earns silence |
| Attempts per instance | 174 had one, 22 had zero (11%, clean tree, `not triggered`), **0 had more than one** | Attempt history is a scaling path, not the centerpiece |
| Controller cycles | 1 in 196 of 196 runs | Show cycles only when there are more than one |
| **Post-turn window** (last `live_reply.md` write → result) | **p50 108 s**, p75 160 s, p90 265 s; 80% > 30 s, 40% > 2 min | During this window the row says `RUNNING` even though the model is done |
| Sum of commit operation durations | p50 101 s, p90 229 s | Independently confirms cld's p50 of 100 s |
| Runs with ≥1 rejected `sase final submit` | **72 of 174 (41%)**: `commit_bead_action_invalid` 68, `manifest_invalid_json` 9, `core_validation_failed` 3 | The declaration is a first-class troubleshooting surface, and any new finalizer's validator will generate it |
| Declaration recovery turns | 10 | An extra model turn inside finalization, invisible today |
| Successful commit stdout containing `⚠` | **165 of 172 (96%)**. In the last 5 h, 13 of 14 carry the same two chronic warnings | Warnings need a home, but they must never color rows |
| **Sealed plan with no result** | **184 shells**: 102 are `--plan` (handoff skip), 16 were user-killed, and the rest failed or were retried | New states: `skipped · handoff` and `not reached` |
| Multi-shell session families with ≥2 finalizer runs | 1 of 110 (70 had one run, 39 had none) | Run blocks will rarely appear today either |
| Largest current `finalizer_result.json` | 1,979 bytes. The 09-10 report's 3.32 MB file has been reaped | Keep a ceiling, but the 1 MiB vs 8 MiB debate is moot |

**Method.** The post-turn proxy runs from the last `live_reply.md` write to the result
write, so it includes declaration recovery. cld's proxy (submission → result) gives a
p50 of 139 s. `final_context.json` is republished at the start of every controller
cycle and again later, so it is **not** a phase-start marker. The corpus caveat from the
09-10 report still applies: one host and one finalizer. The direction is what matters,
and every measure points the same way.

---

## 2. Designing for finalizers that don't exist yet

Every finalizer, including ones not yet written, passes through the same stages. The
view is built on these stages, and provider-specific rendering is optional enrichment:

```text
RUN   (one per concrete shell: agent shell, or a monitor doing host completion)
 ├─ disposition  ran | skipped (handoff:<kind>) | not reached | interrupted
 ├─ plan         selected instances, after-edges, why selected, policy, drift
 ├─ declaration  context issued → submissions (accepted/rejected + code) → recovery turn?
 └─ INSTANCE     (commit | check | tasks | acme@open-pr | …)
     ├─ trigger    not_triggered | always | dirty_repository | provider_requested
     ├─ declared   this instance's accepted payload
     ├─ ATTEMPT 1..N
     │   ├─ OPERATION  subprocess | model_turn | validation | internal
     │   │   ├─ steps   optional structured progress (the step channel)
     │   │   ├─ exit · duration · timed_out · truncated
     │   │   └─ logs    stdout/stderr (live tail while running)
     │   ├─ evidence    typed kind/value
     │   └─ diagnostics attempt-scoped, deduped
     └─ outcome    status · refusal reason · deferral {reason, paths} · headline evidence
```

Stress-testing this against current and planned finalizers shows the generic model
covers them all:

| Finalizer | What the user needs to see | Covered by the generic model? |
|---|---|---|
| `builtin@commit` | Per-repo decision, steps (hook → create → push → publish), SHA, deferral paths, warnings, and any conflict-repair model turn | Yes, plus an enricher: a per-repo table and links to the existing commit viewer (`prompt_panel/_agent_commits.py`) |
| `builtin@command` (`check`, `lint`) | argv, elapsed time, live tail, exit code, failing lines | Yes. The generic renderer is enough. |
| Declaration-only (`builtin@tasks`, planned) | Declared and resolved beads, and rejections | Yes, as a zero-operation attempt with a declaration-centric card |
| Plugin (for example, open a PR) | `execute`/`verify` ladder, messages, typed evidence (a PR URL), protocol envelopes | Yes, *if* evidence is typed and plugins can emit steps (§5.1) |
| Side-effect finalizers (notify, publish, deploy) | Whether the effect happened; refusals and deferrals shown calmly | Yes. Refused and deferred are first-class states. |
| Monitor host completion | Which monitor shell ran the instances | Yes. That run's shell is the monitor. |

**Anti-overfitting rules:**

1. **Sase owns the layout. Providers own evidence, not layout.** No TUI plugin API is
   needed. Everything a plugin produces must render well with no plugin-specific code
   in sase: status, message, typed evidence, diagnostics, steps, and operation logs.
2. **Typed evidence by convention.** The convention lives in core, so every frontend
   agrees:
   - `*_sha` → a short SHA, linked to the commit viewer
   - `*_url` → a link
   - `bead_id` → a bead reference
   - `*_path` → an openable path
   - `*_seconds` → a duration
   - `exit_code` → a colored exit code

   A provider's `describe` response can add optional presentation hints (`summary`,
   `headline_evidence`, `evidence_labels`). These are sanitized data, never Rich markup
   or callbacks.
3. **Executor facts are uniform.** Attempt, operation, timing, exit status, and logs come
   from the executor layer, not the provider, so the diagnosis UI is provider-neutral by
   construction. This requires the uniform operation record in §5.1, because today the
   three executors write three incompatible attempt shapes (cld).
4. **Calm states are first class.** `refused ⊘`, `deferred ⏸`, `not triggered ○`,
   `skipped · handoff ○`, and `not run –` are distinct states and never read as errors.
   A permissions or safety finalizer will refuse far more often than `commit` does.
5. **Order comes from the plan.** The sealed plan's `after` edges define order. Render
   them as an honest indented list with `after …` labels rather than a pretty but
   misleading linear pipeline (cdx).
6. **Separate "selected for this run" from "configured".** The Overview shows
   configured-but-unselected instances dimmed, with the reason (`%final:!lint`, not
   default), plus the currently unread drift warning. When a new finalizer "doesn't
   run", this is the single most useful thing to see.
7. **`commit` gets an enricher, not the schema.** Build and test the generic renderer
   first, using a plugin fixture. The projection and deck model contain no
   `commit`-specific fields.

---

## 3. Decks, cards, and card blocks

### 3.1 Where the four reports landed

| | Deck | Cards | Card blocks | Main deck |
|---|---|---|---|---|
| **cdx** | New `FINALIZERS` deck | `Overview` + one per instance | One per concrete shell run; attempts are rows | One-line summary only |
| **cld** | New `FINAL` deck | `Pipeline` + one per instance | One per attempt; one per shell run on sessions | Reply receipt per shell |
| **mus** | None ("cycle tax") | None | None in v1 | `FINALIZERS` fold section + output modal |
| **gem** | None ("dormant 95% of the run") | A `Finalizers` card in Main | One per instance | Reply footer banner + header lane |
| **Lead** | **New `⊛ FINAL` deck** | **`Overview` + one per instance** | **One per run (= shell)** | **Reply receipt per shell** |

### 3.2 Why a deck

**Against mus's fold section.** It was designed for the pre-deck layout. Today a fold
section renders inside the Context card (§1.1). Context is the default card, it is
built synchronously, and it means "what this agent was asked". Minutes of live tails
and diagnostics there bloat it and push Main into paged mode more often. The output
modal mus relies on is the pattern decks retired: the deck *is* the zoom.

**Against gem's Main card:**

1. Main is built from the agent model on the Main fan-out. Finalizer detail needs its
   own off-thread artifact loader and live refresh. That is exactly why Files and Tools
   each earned a deck.
2. If each instance is a block inside one card, runs and attempts have no home, because
   blocks never nest.
3. It adds a third card to Main's `Ctrl+J/K` cycle for every agent, and log content
   inflates Main's spread measurement.

gem's real concern is that a failure could hide behind a deck switch in single-panel
layout. Three signals that are always visible answer it: the row chip, the Reply
receipt, and `final ✗` in every deck's border subtitle.

**Against the cycle tax (mus).** The cost is real but small:

- FINAL is appended last in the cycle, and `p n` reaches it directly.
- FINAL is rarely empty. Every agent shell seals a plan (380 plans in 15 days, all
  selecting `commit`), so even mid-turn FINAL shows what will run, its trigger, and why.

**For a deck:**

- Finalization is its own data domain, with its own artifacts, loader, refresh, and
  spread/paged policy.
- It composes with the deck system for free: split (`p N` gives Reply above and FINAL
  below), zoom, search, export, and per-panel persistence.
- A panel pinned to FINAL turns `j/k` into a **finalizer triage loop**: one keypress
  per agent shows how its turn landed.

### 3.3 Cards: `Overview` plus one per instance

- **Instance ids are stable, meaningful config keys** (`commit`, `check`, `lint`). A
  user who selects the `check` card keeps landing on `check` while pressing `j/k`. This
  requires per-deck preferred cards (§5.4).
- **The tab strip doubles as a status strip:** `Overview │ commit ✓ │ check ✗ │ tasks –`.
  It scales to N finalizers with no special cases.
- **`Overview`** is the name, not cld's `Pipeline`, because the plan is a DAG. It holds
  everything that belongs to the run rather than to one instance:
  - the plan and its order
  - the selection explanation
  - the declaration timeline, since one manifest covers every instance
  - controller cycles and reactivations
  - drift
  - run-level diagnostics
  - the runs ledger
- **The default card** follows this order:
  1. the sticky preference, when present, consistent with Main
  2. otherwise, the first instance needing attention (running, failed, refused,
     deferred, or interrupted)
  3. otherwise, `Overview` if the trouble is run-level (a recovery turn, drift, or an
     integrity failure)
  4. otherwise, the first instance

### 3.4 Card blocks: one per finalizer run

A **run** is one instance's execution in one concrete shell. Each shell has its own
plan, artifacts dir, context, and runner liveness. There are three reasons to prefer
this over the alternatives.

1. **Blocks keep one meaning across the tab.** The card-block design defines a block as
   one concrete sase shell. Its id is `Agent.identity`, and its rail uses the JUMP
   roster's numbers, labels, glyphs, and status colors. If FINAL's blocks are also
   shells, then `[`/`]` means "older/newer shell" in Reply and FINAL alike. The rail
   entries match, and `BlockMeta`, landing, and following are reused unchanged.
2. **Attempts as blocks (cld) needs two meanings.** cld itself relabels blocks by shell
   on session containers, and a session with retries would need shell × attempt
   nesting, which blocks forbid. Attempts are bounded by `max_attempts` (in practice
   1–3) and read best as a compact timeline inside one run.
3. **Instances as blocks (gem) puts the growing axis on the wrong layer.** The user's
   planned finalizers grow the *instance* count. Instances belong on cards, whose
   preference persists across nodes, not on blocks, whose cursors are per-subject and
   ephemeral. It also leaves runs and attempts with no home.

**Be honest about how often blocks appear.** On this corpus no meaning of "block" would
show a rail on more than about 1% of selections: 0 instances had multiple attempts, and
only 1 of 110 sessions had 2 finalizer runs. FINAL must therefore be excellent with
**zero** blocks, which means single-run cards with attempts as sections. The run model
lets session containers adopt blocks with no redesign once card blocks ship, and once
feedback rounds and monitor host completion make multi-run sessions common. On a
session container:

- **Every** FINAL card, including `Overview`, has one block per shell that ran
  finalizers.
- Rail entries keep their roster numbers, so gaps are informative and the JUMP digits
  still match.
- Shells that were skipped for a handoff, or where the instance was not triggered, get
  no block. They appear in the `Overview`'s one-line runs ledger instead (cdx and cld
  agree).

**When to reopen this.** If a future finalizer retries routinely (for example, a flaky
`check` with `max_attempts: 3`) and users want to compare attempts side by side, add
attempt navigation *inside* the run block through hint targets. Do not promote attempts
to blocks.

### 3.5 Main gets a receipt, not a card

cld's **Reply receipt** goes at the end of each shell's phase, and at the end of a
monitor phase that did host completion:

- **It has precedent.** It is a lifecycle sub-section, just like the MONITOR and GATE
  phases that already sit in Reply.
- **It costs no I/O.** It is built only from the `agent_meta` summary.
- **It joins the card-blocks world naturally.** Once card blocks land, the receipt
  becomes part of its shell's block, so landing on the newest block shows the reply
  *and* how it landed on one screen.

Skip gem's and the 09-10 report's separate detail-header lane. The receipt and the deck
subtitle already carry that signal. While finalizing, reuse the existing header
activity-chip slot instead (cld).

### 3.6 The resulting hierarchy

| Level | Finalizer meaning | Marker |
|---|---|---|
| Deck `⊛ FINAL` | This node's finalization, across all its runs | Rounded border in the FINAL accent |
| Card | `Overview`, or one instance | Tab pill with a status glyph (paged), or a heavy `━━ ⊛ commit ━━` rule (spread) |
| Card block | One run: one shell's execution | The existing phase divider, `─── ⊛ AGENT (code) ─── 09:12:40 ───`, carrying block anchor metadata |
| Section | One attempt, then one operation inside it | An `attempt n` divider, and an operation line with right-aligned exit and duration |
| Line | A step, evidence, a diagnostic, or a log tail | Indented, and dim unless in trouble |

---

## 4. The experience

### 4.1 Visual vocabulary

Every state shows glyph + word + color together, so it reads without color and can be
searched in screenshots. Running uses the roster's `▶`, so rails and tabs match Reply.

| State | Glyph | Color | Source |
|---|---|---|---|
| planned (turn still running) / waiting on `after` | `◌` | dim | plan / journal |
| declaring (declaration recovery turn) | `▶` + `declaration` | yellow | journal |
| running / retrying | `▶` (+ `attempt 2/3` gauge only when the budget is > 1) | yellow | journal, with a live runner |
| success | `✓` | green | result |
| success with warnings | `✓` + `⚠N` | green + amber count, **deck only** | warn steps or warning diagnostics in the latest attempt |
| failed | `✗` | red | result |
| refused | `⊘` | magenta | result |
| deferred | `⏸` (fallback `‖` if goldens show it wide) | amber | result `{reason, paths}` |
| not triggered | `○` | dim | `final_context.json` trigger |
| **skipped · handoff** (run-level) | `○` | dim | journal `phase_skipped` (§5.1) |
| not run · blocked by X | `–` | dim | projection: planned, but an upstream result ended the run |
| **not reached** (run-level) | `–` | dim | plan exists, but no journal and no result on a terminal agent (killed, failed, or legacy) |
| interrupted | `!` | amber | journal open, runner dead. Never a forever-spinner. |
| unavailable | `⚠` | dim amber | integrity, parse, or size failure. Say why and keep raw access. |

**Deck identity:**

- **Name `FINAL`.** It matches `%final`, `sase final`, `/sase_final`, and
  `final_context.json`, and it is short enough for compact title tiers.
- **Glyph `⊛`** (U+229B, East Asian Width "N", so single-cell). It is unused in
  `src/sase/ace`. Reject the `⛭` that the 09-10 report, mus, and gem use: it has
  *ambiguous* width, so it can render double-wide, and it reads like the monitor's `⚙`.
- **Picker key `n`** (fi**n**al), because `f` is Files. `N` means "the other panel".
- **Cycle order** appends FINAL after Tools. **Count noun:** `finalizer/finalizers`.
- **Accent.** Use one unclaimed hue. cld proposes rose `#FF87D7`; pick the final value
  from golden screenshots in both themes.
- **Naming hygiene.** Say "finalizer attempt" in help text, because "attempt" already
  means agent retries (`D`, `↻2`). A gate's "finalize proc" is not a finalizer and must
  never render with `⊛`.

### 4.2 Glance: the agent row

`FINALIZING` is a display phase inside the Running lifecycle bucket (cdx). Ordering,
filters, capacity, and actions don't change. The chip appears only while running or
after a non-success, never for success or success-with-warnings. At 96% of successes
carrying warnings, a warnings chip would be permanent noise.

```text
▶ sase-1ab--code    FINALIZING  ⊛ commit · just fix 1:42
✗ sase-1c9--code    FAILED      ⊛✗ check
✓ research.b.cld    DONE        ⊛⏸ commit
✓ sase-1d2--code    DONE                                    ← success: silence
```

- `⊛✗` on a FAILED row separates "the model turn failed" from "the work was done, but
  landing failed". Those need completely different fixes.
- `⊛⏸` on a **DONE** row matters because a DONE row with a deliberately dirty tree is
  otherwise a lie of omission.
- A session row aggregates by severity first, for example `⊛✗ 1 of 3 runs`.
- The step label (`just fix`) comes from the step channel (§5.1) once it exists.
  Before that, the row shows the instance name and elapsed time.

### 4.3 In context: the Reply receipt

The receipt is built only from the `agent_meta` summary, with one line per selected
instance in plan order. It never shows log tails.

```text
─── ⊛ FINAL ─── 07:31:40 ────────────────────────────────
  ▶ commit   create_commit · main                     1:42
  ◌ check    after commit
```

```text
─── ⊛ FINAL ─── 07:31:40 ────────────────────────────────
  ✗ check    command_failed · attempt 2/2            3m40s
             FAILED tests/ace/tui/test_final_deck.py::test_receipt
  – tasks    not run · blocked by check
             p n  open FINAL deck
```

```text
─── ⊛ FINAL ─── 07:44:02 ────────────────────────────────
  ⏸ commit   deferred · protected_paths · 2 paths
  ○ check    not triggered
```

Rules:

- **Headline evidence is chosen generically:** a SHA, then a URL, then a bead id, then
  an exit code.
- **A failed instance adds exactly one reason line,** either the first error diagnostic
  or the last non-blank stderr line, plus the `p n` hint.
- **Warnings appear here only as a dim `⚠N` suffix.**
- **Some shells get no receipt:** those skipped for a handoff (a plan shell never lands
  work; its successor's receipt tells the story), `%final:none` runs, and legacy runs
  with no plan.

### 4.4 Diagnose: the FINAL deck

**Availability** is a no-I/O probe over the agent model. The deck has content when a
sealed plan has at least one selected instance, and its count is the number selected.
In v1 it is unavailable for clans and tribes, proc shells, and legacy runs.

**The subtitle switcher** carries status in the status color (`final ✓`, `final ▶`,
`final ✗`), so the border shows a landing failure even while you read Main or Files.

The common case is one instance that fits on one page (spread):

```text
╭─ ⊛ FINAL ┃ Overview │ commit ✓ ──────────────────────────────────────────╮
│ OVERVIEW · 1 selected · ✓ success · 2m31s · plan c21e7df7                │
│   ✓ commit   builtin@commit    default                           2m04s   │
│ DECLARATION                                                              │
│   07:30:58  ✗ rejected  commit_bead_action_invalid                       │
│             bead_action is required when a bead is assigned; use keep…   │
│   07:31:05  ✓ accepted  1 payload                                        │
│                                                                          │
│ ━━ ⊛ commit ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ commit · builtin@commit                          ✓ success · 1 attempt   │
│   trigger   dirty repository · 1 repo                                    │
│   declared  main "feat(ace): add FINAL deck" · bead sase-1ab → close     │
│ ─── attempt 1 ─── 07:31:06 ─── 2m04s ───────────────────                 │
│   ✓ stitch main                                     exit 0     1m58s     │
│       ✓ before hook  just fix                                    41s     │
│       ✓ create_commit                                          1m12s     │
│       ⚠ 2 warnings  (quarantined publication, prompt archive deferred) › │
│   evidence  commit 8bb7e55 · tree 2127a48 · pushed        ↗ commit view  │
╰───────────────────────── spread · main 2 · files 3 · tools 88 · final ✓ ─╯
```

A failed `check` on a concrete shell. There is one run, so no rail. The earlier attempt
collapses to one line, and the failing attempt expands automatically (the GitHub
Actions precedent), without ever overriding an explicit user fold:

```text
╭─ ⊛ FINAL ┃ Overview │ commit ✓ │ check ✗  3/3 ───────────────────────────╮
│ check · builtin@command · just check            ✗ failed · 2/2 attempts  │
│   why       %final:check · after commit        trigger  always           │
│ ─── attempt 1 ─── 07:32:30 ─── 3m38s ─── ✗ exit 1 ─────────────── ›      │
│ ─── attempt 2 ─── 07:36:12 ─── 3m40s ─────────────────────────────       │
│   ✗ run  just check                                  exit 1     3m40s    │
│   │ FAILED tests/ace/tui/test_final_deck.py::test_receipt - AssertionE…  │
│   │ ========== 1 failed, 4127 passed in 212.41s ==========               │
│   diagnostics  command_failed · attempt_budget_exhausted                 │
│   logs         stdout 2,114 lines · stderr 3 lines            v to open  │
╰────────────────────────────────── main 2 · files 3 · tools 88 · final ✗ ─╯
```

The `Overview` for a multi-instance run with a problem. This is the finalizer author's
card:

```text
│ OVERVIEW · 3 selected · ✗ failed · 2 cycles · 6m02s · plan 84a91c2d      │
│   ✓ commit   builtin@commit     default                        2m04s     │
│   ✗ check    builtin@command    %final:check · after commit    3m40s     │
│   – tasks    builtin@tasks      default · not run (blocked by check)     │
│   ○ lint     builtin@command    configured · not selected (%final:!lint) │
│ DECLARATION   07:30:58 ✓ accepted · 2 payloads (commit, tasks)           │
│ CONTROLLER    2 cycles · commit reactivated after check                  │
│ ⚠ config drifted since this plan was sealed: check.max_attempts 2 → 3    │
│ sase final list · sase final doctor                                      │
```

A plugin finalizer, rendered by the generic renderer with no sase code specific to it.
The example is a hypothetical `acme-sase@open-pr`:

```text
│ pr · acme-sase@open-pr                        ▶ running · attempt 1/3    │
│   why       %final:pr · after commit                                     │
│   trigger   provider requested · submission required                     │
│   declared  title "feat: FINAL deck" · draft true                        │
│ ─── attempt 1 ─── 07:40:02 ─── 0:18 ──────────────────                   │
│   ✓ execute                                            ok      12.1s     │
│       ✓ push branch bryan/final-deck                                     │
│       ✓ open pull request                                                │
│   ▶ verify                                                      0:06     │
│       ▶ wait for required checks                                         │
│   evidence  pr_url  github.com/sase-org/sase/pull/812 ↗                  │
│   protocol  execute request/response · verify request       v to open    │
```

A session container after card blocks land. Blocks are runs, the rail keeps roster
numbers, and skipped shells appear only in the ledger:

```text
╭─ ⊛ FINAL ┃ Overview │ commit ✓  2/2 ─────────────────────────────────────╮
│ 2 --code ✗ ─ ▐4 --code ✓▌                              [ older · newer ] │
│ commit · builtin@commit                             ✓ success · 2 runs   │
│   runs  0 --plan ○ skipped · plan handoff · 2 --code ✗ · 4 --code ✓      │
│ ─── ⊛ AGENT (code) #4 ─── 09:12:40 ─── 1m47s ────────────────────        │
│   …                                                                      │
```

### 4.5 Live behavior (the calm rules)

These are adopted from the 09-10 report and cld unchanged, with one lead addition.

- **5 s tail gate.** No live tail renders until an operation has run for about 5 s
  (configurable), so fast operations go straight from `▶` to `✓`.
- **Following** uses card-block semantics. The deck follows the newest run and attempt
  while you are on it. Otherwise a restrained `● 1 newer ›` marker appears, and the
  view never yanks the reader. Within a tail, scrolling up pauses follow, and returning
  to the bottom resumes it (the Grafana live-tail rule).
- **Budget.** A running operation shows at most about 12 tail lines in the card. Full
  logs open through `v` hint targets, and `E` exports the active card.
- **Scope.** Tail reads happen only when a panel shows FINAL for the selected agent, the
  phase is active, and the surface token has drifted. A background agent that is
  finalizing costs nothing.
- **Sanitize.** Output goes through `render_axe_output(…, "ansi")`, never raw Rich
  markup, and is never copied into notifications or logs. **Lead addition:** stitch
  stdout carries `\r`-separated git progress (`Compressing objects: N%…`) as well as
  raw ANSI, so the tail reader must collapse carriage returns to the last segment.

### 4.6 Keys: nothing new to learn

| Key | Effect in FINAL |
|---|---|
| `p n` / `p N` | Show FINAL here / in the other panel. The best triage layout is Reply above, FINAL below. |
| `Ctrl+N` / `Ctrl+P` | Deck cycle, now including FINAL |
| `Ctrl+J` / `Ctrl+K` | Overview ↔ instance cards |
| `[` / `]` | Older / newer run block (once card blocks land) |
| `v` | Hints on operation logs, protocol envelopes, prompt/response files, and commit links |
| `E` / `,/` / `Z` | Export, search, and zoom, with unchanged deck behavior |

v1 is **read-only**: no retry, cancel, or bypass controls. Those carry authorization and
fixed-point semantics that don't belong in a display feature. The four reports and the 09-10
report all agree on this.

---

## 5. Data and architecture

Everything below is **additive**. There is no finalizer execution-wire v2 → v3 bump.
The strict provider-facing protocol keeps rejecting unknown fields, and UI state lives
in a separate read model (cdx).

### 5.1 Producers (`src/sase/finalizers/`)

1. **The progress journal, `finalizers/progress.jsonl`.** Every report proposes it,
   including the 09-10 report.
   - **Single writer:** the controller.
   - **Events:** `phase_started{run_id, plan_digest, mode}`, `cycle_started`,
     `declaration_{started,finished}`, `recovery_turn_{started,finished}`,
     `instance_{started,finished}`, `attempt_{started,finished}`,
     `op_{started,finished}`, `phase_finished`.
   - **Lead addition: `phase_skipped{reason: "handoff:plan|questions|monitor|gate|pipe"}`**,
     written at the `should_skip_finalizers()` branch. It is one call, and it turns 102
     unexplained plans per fortnight into a calm, labelled state.
   - **Record fields:** schema version, sequence number, and wall-clock time.
   - **Safety:** writes are best-effort, with a byte ceiling that ends in an
     `observability_truncated` event. Observability I/O never changes a verdict.
2. **One operation record per executor (cld):**
   `attempt-N.<op>.outcome.json {op, kind, label, argv?, started_at, duration_seconds,
   returncode?, timed_out, *_truncated, logs, steps?}`.
   - Commit already writes most of this.
   - Command writes it next to `diagnostics.json`.
   - Plugin writes one per operation.
   - Conflict repair becomes a `model_turn` operation that references its prompt and
     response.

   This single change is what lets one renderer serve every finalizer.
3. **Step channel (cld; the anti-overfitting piece).**
   - The host sets `SASE_FINALIZER_STEPS_FILE` for every finalizer subprocess.
   - Anything can append `{t, step, state: start|ok|warn|fail, detail}`, and the SDK
     gains a `step()` helper that does nothing when the variable is unset.
   - `sase stitch create` emits its existing phases as steps. Those phases currently
     print as emoji lines: `🔄 Dispatching create_commit…` in 188 of 188 stdout files,
     and `🔄 Running before commit hook: just fix` in 93.
   - Its `⚠` lines become `warn` steps, so "success with warnings" is structured
     rather than scraped. **Never scrape emoji.**
4. **Live sink (every report).** An optional callback in `bounded_subprocess._reader` tees
   output to a bounded, rotating `attempt-N.<op>.live` using the monitor log contract.
   - The exclusive terminal artifacts don't change.
   - A sink failure is swallowed.
   - A finalizer killed at the 1,800 s hard timeout no longer loses all of its output.
   - Plugin protocol stdout is not shown as a human log unless the provider marks it as
     one.

### 5.2 Row summary (`agent_meta.json["finalizer_status"]`)

Write a new top-level key through `update_meta_field`, only at transitions:

- **Fields:** `phase` (`planned | skipped | declaring | executing | settled |
  interrupted`), `reason`, the aggregate `status`, `updated_at`, and at most 16
  `instances[]` entries of `{id, status, attempt, max_attempts, op, step, started_at,
  headline, warnings, reason}`, with capped strings.
- **Why a separate key:** the plan-seal `finalizers` block stays a stable record.
- **Wire mirror:** add it to `AgentMetaWire` in both Python
  (`core/agent_scan_wire_markers.py`) and Rust (`agent_scan/wire.rs`), with a
  contract-manifest test and a `sase-core-revision.txt` pin bump.
- **What it drives,** with **zero** extra file opens in the list and render paths: the
  status word, the chips, the header activity chip, the receipt, and FINAL's
  availability and subtitle.

### 5.3 Shared projection (`sase-core`: `finalizer/run_view.rs`)

The shared projection is `FinalizerRunView`, exposed through the binding. Any frontend
(TUI, CLI, or a future web view) would need this reconciliation to match, so it belongs
in the Rust core.

- **Inputs:** capped byte reads, done off the event loop by Python, of:
  - the plan
  - `final_context.json`
  - the submission attempts and recovery artifacts
  - the journal
  - the operation records and steps
  - the result
  - live-log metadata
  - runner identity (`process_identity`) and liveness
- **Selection explanation:** the projection may read the authority plan's
  `config_snapshot` to explain selection, but it outputs only instance ids, provider
  refs, and reasons. **It never outputs config values** (cdx's secrecy constraint,
  reconciled with cld's selection-explanation need).
- **Results:** `finalizer_result.json` is a schema-v1 artifact whose `cycles` field sits
  outside the strict aggregate wire. The projection parses the artifact shape, not the
  wire struct.

**Source precedence.** This merges the 09-10 report, cdx, and cld, plus the lead's two
new rules:

1. A plan integrity, digest, or scope mismatch → `unavailable`, never a best-effort
   success.
2. A valid terminal result with matching identity is authoritative for outcomes.
3. **A journal `phase_skipped` → the run is `skipped · handoff:<kind>`.**
4. The journal plus a live, matching runner is authoritative for the active phase,
   instance, attempt, and operation.
5. `final_context.json` supplies trigger and submission facts, and the submission
   attempts supply the declaration timeline.
6. Operation records, steps, and live logs supply content only, never status.
7. The `agent_meta` summary is a row hint, never detail truth.
8. An open journal with a dead or mismatched runner → `interrupted`.
9. **A plan with no journal and no result on a terminal agent → `not reached`.** It
   stays calm and dim, and is never `interrupted` or `failed`. This covers legacy
   runs, kills, provider failures, and handoffs made before the journal existed.
10. A planned instance never reached after an upstream terminal outcome →
    `not run · blocked by X`.

The projection also owns:

- **Dedupe with attempt-scoped severity**, so `error` rows inside a successful run
  don't paint it red.
- **DAG ordering.**
- **Typed evidence and headline selection** (§2).
- **The warnings count.**
- **A pre-parse ceiling on every JSON input** (4 MiB, with a "too large — press `E`"
  fallback).

### 5.4 TUI plumbing (`src/sase/ace/tui/`)

1. **Per-deck preferred cards.** Change the single slot to
   `preferred_cards: Mapping[DeckId, str]` in `DeckPanelState` and in the persisted
   `{deck, preferred_card}` entries, keeping the old key readable. Main's behavior is
   unchanged. **This is required before any second deck can have sticky cards.**
2. **A `DeckSpec` registry** (cld; recommended prep). A fourth deck otherwise touches
   about 15 parallel tables and if/elif chains: title dicts, accent classes, `compose`,
   `_deck_is_empty`, tabs, availability, the picker, and CSS. One record per deck keeps
   the cost linear for FINAL and for whatever comes after it.
3. **A card-document view extracted from `MainDeckView`.** FINAL is a Rich card
   document like Main, so it inherits spread/paged mode, anchors, `Ctrl+J/K`, the
   search corpus, export, and later card blocks, with nothing re-implemented.
4. **Loader.**
   - It runs as a `run_worker(thread=True)` through the projection, with an
     `(mtime_ns, size)` signature cache and stale-generation rejection, modeled on the
     LLM Calls panel.
   - A `finalizers` refresh-surface token covers the selected agent only. A quiet tick
     reloads nothing.
   - There is no artifact I/O in `compose()` or `render()`.
5. **The receipt** is built in the Reply builders from the summary. There are three
   assembly sites, and the hint twin builds one flat `Text` (card-blocks report §1.2).
6. **Pinned attempt views (`D`).** FINAL follows a pinned prior agent attempt when its
   artifacts dir resolves. A failed prior attempt is exactly when you want its landing
   story.
7. **Keymap registration** follows the decks checklist, including
   **`src/sase/default_config.yml`** (the core-memory gotcha), help, the palette, and
   the footer.

### 5.5 CLI

Add a read-only per-agent run view over the same projection, so an agent debugging a
predecessor's landing sees exactly what the user sees. `show` is taken, so the verb
might be something like `sase final status [<agent>]`. Settle the name under
`sase/memory/cli_rules.md`.

---

## 6. Delivery plan

Phases 1–3 sit behind one `beta` flag (for example `ace_final_deck`, created with
`sase flag new` under the `sase_flags` rules, with both states tested and the Off
branch removed at the end). Phase 0 is additive data with no visible change.

| Phase | Size | Scope | Key verification |
|---|---|---|---|
| **0a. Observability data** | M | The journal, including `phase_skipped` and declaration events; operation records for every executor; the `finalizer_status` summary | Per-executor unit tests. A journal-write failure never changes a verdict. The exclusive artifacts are unchanged. A handoff writes `phase_skipped`. |
| **0b. Core (sase-core)** | M | The `AgentMetaWire` field (Rust + Python); the `FinalizerRunView` projection, binding, and pin bump | Fixtures for every §4.1 state: skip, not reached, digest mismatch, truncated journal → interrupted, oversized result, zero attempts, reactivation |
| **1. Glance** | S | `FINALIZING`, the `⊛` chips, the header activity chip, the Reply receipt | Row and receipt goldens in both themes at 120/80/60 columns. `bench_tui_jk.py` p95 unchanged. |
| **2. FINAL deck** | L | `DeckSpec`, the card-document view, per-deck preferred cards, `Overview` and instance cards (generic renderer + commit and command enrichers), attempts as sections, status tabs and subtitle, key registration, the CLI run view | Pilot tests: landing, sticky per-deck cards, a Reply/FINAL split, availability. Goldens: spread, paged, a plugin fixture, and an Overview with unselected instances and drift. The idle tick reloads nothing. |
| **3. Live** | M | The live sink, the step channel with `stitch` steps and warn steps, the tail gate, following, 1 Hz elapsed time for the selected agent | An end-to-end fake finalizer that emits steps slowly, warns, retries, then passes, fails, or dies. No tail bleeds across agents. |
| **4. Run blocks** | S | Adopt `CardBlock` on session containers once card blocks land. `BlockMeta` must stay source-agnostic. | Rail goldens. `[`/`]` in FINAL. |
| **5. Polish** (each optional) | — | `describe` presentation hints; SDK docs for `step()` and typed evidence; notifications on `failed`/`refused` (never `deferred`); clan/tribe roll-ups | — |

**Cheapest valuable slice:** 0a + 0b + 1. That makes the ~2-minute window legible and
puts failures and deferrals in the row and the Reply before any deck work begins. Don't
ship Phase 1 without the journal, or a crash could leave `FINALIZING` stuck forever.

---

## 7. Risks and tests

| Risk | Mitigation |
|---|---|
| The UI overfits to `commit` | The generic renderer ships first and is tested against a plugin fixture with typed evidence and steps. Enrichers are additive, and there are no commit fields in the projection or deck model. |
| Handoff-skipped plans render as errors | `phase_skipped`, plus the `not reached` fallback. Fixtures cover a plan shell and a killed shell. |
| A forever-spinner after the runner dies | Journal + liveness → `interrupted`. Tested by truncating the journal. |
| Warnings turn everything amber | Warnings never reach row chips. The receipt shows only a dim count, and detail lives in the deck. |
| A FINAL sticky card overwrites Main's Reply | Per-deck preferred cards (§5.4.1) |
| Live tails hurt `j/k` or idle CPU | Reads are limited to the selected agent, while FINAL is visible, and gated by the surface token. No I/O in render or keystroke paths. |
| Oversized or corrupt artifacts freeze the panel | Pre-parse ceilings in Rust, and an `unavailable` state that keeps raw access |
| Card blocks slip | FINAL is complete with single-run cards, and run blocks are Phase 4 |
| A fourth deck adds weight to the cycle and picker | FINAL is appended last, has the `n` picker key, and is dimmed when unavailable. `DeckSpec` keeps the code cost linear. |

---

## 8. Resolved disagreements (summary)

| Question | Positions | Resolution and why |
|---|---|---|
| Placement | deck (cdx, cld) / Main card (gem) / fold section (mus) | **Deck.** The fold section now sits in Context, and a Main card has no room for runs or attempts (§3.2). |
| Block meaning | run (cdx) / attempt (cld) / instance (gem) / none (mus) | **Run.** One meaning across the tab, no nesting, and the growing axis stays on cards (§3.4). |
| Main presence | receipt (cld) / footer (gem) / summary line (cdx) / header lane (gem, 09-10) | **Receipt per shell.** No header lane; reuse the activity-chip slot. |
| First card name | `Overview` (cdx) / `Pipeline` (cld) | **`Overview`.** The plan is a DAG, not a pipeline. |
| Chip glyph | `⛭` (09-10, cdx, mus, gem) / `⊛` (cld) | **`⊛`.** `⛭` has ambiguous width and looks like `⚙` (§4.1). |
| p50 phase length | 2.0 s (09-10, gem) / ~100 s (cld) | **~100–110 s** (lead re-measurement, §1.2) |
| Result size ceiling | 1 MiB (09-10, mus, gem) / 8 MiB (cdx) | **4 MiB with a fallback.** The 3.32 MB file is gone, and today's max is 2 KB. |
| Live output | modal (09-10, mus, gem) / in-card tail + `v`/`E` (cdx, cld) | **In-card tail.** The deck replaces the modal. |
| Structured steps | none (09-10, cdx, mus, gem) / step channel (cld) | **Step channel in Phase 3.** It is the only non-scraping route to "success with warnings" and plugin progress. |
| Unconsumed planned runs | `not_run` / `unavailable` / `interrupted` (all) | **`skipped · handoff` or `not reached`** (lead, §5.3) |

---

## 9. Open questions for Bryan

1. **Deck identity:** `⊛ FINAL`, picker key `n`, rose accent? (The alternative name is
   `FINALIZERS`.)
2. **Configured-but-unselected instances in `Overview`:** show them dimmed with the
   reason? Recommended: yes.
3. **Attention vs. stickiness:** should a failing instance override a sticky FINAL card
   as you `j/k`? Recommended: no, consistent with Main. The status strip and the
   subtitle carry the signal.
4. **Chronic stitch warnings:** fix them at the source or reclassify them before FINAL
   ships? Otherwise "success with warnings" describes 96% of runs and stops carrying any
   information (Appendix A.1).
5. **Receipt for handoff-skipped shells:** omit it (recommended), or show a dim
   `○ skipped · plan handoff` line?

---

## 10. Recommended solution

Build finalizer support as **four zoom levels over one provider-neutral data layer**:

1. **Glance.** A `FINALIZING` display phase that stays in the Running bucket, and a `⊛`
   chip only while finalizers run or after a failure, deferral, refusal, or
   interruption. Both are fed by an additive `agent_meta.json["finalizer_status"]`
   summary mirrored in `AgentMetaWire`, at zero extra I/O.
2. **In context.** A **Reply receipt**: a `─── ⊛ FINAL ───` phase divider with one line
   per instance at the end of each shell's phase. It shows the headline evidence, a dim
   warnings count, and exactly one reason line on failure. Once card blocks land, it
   becomes part of that shell's block.
3. **Diagnose.** A new **`⊛ FINAL` deck**:
   - **Cards:** an `Overview` card (plan, selection explanation, declaration timeline,
     cycles, drift, runs ledger), then **one card per finalizer instance**, keyed by its
     stable id. The tab strip doubles as a status strip, and cards stick per deck.
   - **Card blocks:** one per **run**, meaning one concrete shell's execution. This
     keeps the card-block design's single meaning, so `[`/`]` means older/newer shell
     everywhere.
   - **Inside a run:** attempts are sections (the latest or failing one expanded), and
     each attempt holds operations with structured steps, exit and duration, typed
     evidence, attempt-scoped diagnostics, and a gated live tail.
   - FINAL must be excellent with zero blocks, because today's data almost never
     produces more than one.
4. **Author.** The `Overview` card, plus a read-only `sase final` run view over the same
   projection, answers "why didn't my finalizer run?" and "what did my validator
   reject?".

**Underneath:**

- a controller **progress journal** that also records **handoff skips**
- a uniform **operation record** across executors
- an opt-in **step channel** (`SASE_FINALIZER_STEPS_FILE` + SDK `step()`), used first by
  `sase stitch create`
- bounded **live logs**
- **typed-evidence conventions** with optional `describe` presentation hints
- one Rust-core **`FinalizerRunView`** projection with explicit source precedence

There is no execution-wire bump, no TUI plugin API, and nothing commit-specific in the
model. `commit` is simply the first enricher, and every future finalizer (`check`,
`tasks`, plugins, notifiers) is a first-class card on day one.

---

## Appendix A. Side findings

1. **Chronic hidden stitch warnings are live right now.** In the last 5 hours, 13 of 14
   commit stitches printed both of these warnings:
   - "56 quarantined agent-hood publication requests". This is the open bug
     `sase-10x` (hood publication hard-stuck on the owner-manifest byte limit), which
     the lead corroborated with a `+1`.
   - "prompt archive publication was deferred … referenced-by write-back failed:
     artifact-link legacy index writes are fenced; use link events". The fence came
     from the `sase-yy.6` cutover (`a8d99d295`), but the referenced-by write-back still
     takes the legacy path. The lead recorded this as a `DISCOVERED ISSUE` on the
     in-progress epic `sase-yy.8.6`.

   Both persist after `sase-196` closed today. A third warning, "Could not drain
   artifact-link read outbox", appeared in 45 of 188 runs over 15 days but not in the
   last 5 hours. Nobody sees any of these warnings, because they exist only in finalizer
   stdout.
2. **Handoff skips leave no finalizer record** (§1.1). This happened to 102 plan shells
   in 15 days. `phase_skipped` fixes it for free.
3. **`finalizers_drift` is written and never read.** The `Overview` card should be its
   first consumer.
4. **Commit evidence includes an ambiguous `result` kind** whose value duplicates the
   short SHA, next to `commit_sha`. The generic renderer should prefer typed kinds;
   consider renaming or dropping it.
5. **Stitch stdout contains `\r` git progress and raw ANSI** (§4.5).
6. **`sase-193`** (the phase bead stays closed when declaration recovery fails and the
   work is never committed) is exactly the failure class that the declaration timeline
   and row chip would have made visible.
7. **The executor artifact shapes are inconsistent** (cld):
   - plugin `describe`/`validate` outputs are overwritten non-exclusively
   - plugin operations have no timing
   - command timing exists only as evidence
   - commit's conflict-repair files are not attempt-scoped
