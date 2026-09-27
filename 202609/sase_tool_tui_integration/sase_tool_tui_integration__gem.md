# UX Design & Architectural Integration of `sase tool` in the SASE TUI

**Researcher**: gem (`research.2t.gem`)  
**Date**: September 2026  
**Status**: Completed Research & Recommendation  
**Topic**: User Experience (UX) Architecture, Interaction Design, and TUI Integration for the `sase tool` Control Plane  

---

## Executive Summary

The `sase tool` subsystem provides a machine-local, deterministic execution ledger for project-declared named tools (`check`, `test`, `install`, `check-full`) and ad-hoc commands. It records rich execution metadata as `ToolRun` entities: multi-stage timelines (`fmt`, `lint`, `test`), system load/PSI samples, before-and-after fingerprints (dirty file counts, toolchain version probes), failure item triage (`NEW`, `KNOWN`, `FLAKY`, `UNKNOWN`), and cryptographic verdict receipts for host completion.

Integrating `sase tool` into the SASE TUI raises fundamental user-experience questions. The user's initial hypotheses were:
1. *Adding a little hammer icon with a count to agent nodes that made tool calls.*
2. *Adding a new card to the existing "Tools" deck on the Agents tab.*

**The user's intuition that neither of these feels like a great integration is spot-on.** Our research reveals two critical architectural reasons for this:
1. **The Semantic Conflation of "Tool":** There is an acute semantic clash between **LLM Tool Calling** (provider function calls like `view_file`, `replace_file_content`, and `bash` recorded in `tool_calls.jsonl` and rendered by `AgentLLMCallsPanel` in the `Tools` deck with glyph `λ`) and **SASE Named Tools** (deterministic project-owned commands like `just check` that record `ToolRun`s, mint receipts, and triage failures). Conflating the two under the single word "tool" creates severe cognitive friction.
2. **Scope Confinement & Missing Control Plane:** An Agent Data Deck on the Agents tab is strictly scoped to the *currently selected agent node*. Confining `sase tool` to an agent card makes it invisible when viewing agents that performed no verification, completely hides all tool runs launched by developers from their terminal or by background schedulers, and offers no interactive control plane to run, stop, filter, or triage project tools. Furthermore, a raw hammer count (e.g. `🔨 42` or `🔨 1`) conveys zero diagnostic signal—it fails to tell the user whether verification *passed*, *failed*, *introduced new regressions*, or is *still running*.

### The Recommended Solution: The Three-Pillar Tool UX

To deliver the best possible user experience without violating established SASE architectural invariants, we recommend a **Three-Pillar Tool UX**:

1. **Pillar 1: The Global Tool Hub (`ToolsPane` / Interactive Tool Modal & Future Tab Candidate)**
   - Provide a dedicated, project-wide tool surface accessible from anywhere in the TUI via hotkey (`T` or `g t`), `:` command line (`:tool`), and `;` command palette (`;tool run`, `;tool runs`).
   - Split layout:
     - **Upper Left (Catalog):** Project named tools (`check`, `test`, etc.) with LAST status indicator, TYPICAL duration, and 1-key quick execution (`r` run, `R` run with args, `H` hand off to background).
     - **Lower Left (Ledger):** Historical and active `ToolRun`s with live status badges (`running`, `succeeded`, `failed/1`), filterable by tool, state, and owner.
     - **Right Column (Inspector):** Comprehensive inspection view for the selected run showing stage timeline progress bars (`fmt: passed 235ms`, `lint (symvision): failed 1m`), failure triage table (`NEW` vs `KNOWN`), PSI/CPU load curves, before/after dirty diffs, and live-streamed / retained logs (`-F` / `-l`).
2. **Pillar 2: Contextual Agent Integration (Verification Badges & the `FINAL` Deck)**
   - **On the Agent Node Row:** Replace the ambiguous hammer count with a **Verification Status Chip** (e.g. `[✓ check]` green for passed/receipt, `[✗ check]` red for new failures, `[~ check]` yellow for known failures only, `[⟳ check: symvision]` cyan for active execution). This chip appears only on agents or monitor turns that actually executed verification, giving immediate high-value triage signal without visual clutter.
   - **In the Deck Panel:** Rebrand the existing `Tools` deck (`λ`) explicitly as **"LLM Calls"** to eliminate naming collisions. Place `ToolRun` verification results into the **`FINAL` deck** (glyph `⊛`, "how this node's turns landed"), where turn landing, completion verification, and verdict receipts naturally belong. An agent that ran verification displays a dedicated **Verification Card** summarizing stages and triage, with a single keypress (`Enter`) jumping directly to the full Tool Hub.
3. **Pillar 3: Interactive Execution & Triage Workflow**
   - Seamless one-touch execution of project tools from the TUI.
   - Actionable failure triage: from a `NEW` failure item in the TUI, one keystroke opens the offending file at the exact error line, and another creates or links a task bead.

---

## 1. Deconstructing the Problem: The Two Meanings of "Tool"

A primary source of confusion when designing UI for `sase tool` is the collision of two completely distinct concepts that happen to share the word "tool":

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        THE TWO MEANINGS OF "TOOL" IN SASE                       │
├────────────────────────────────────────┬────────────────────────────────────────┤
│           LLM TOOL CALLING             │        SASE NAMED TOOLS & TOOLRUNS     │
├────────────────────────────────────────┼────────────────────────────────────────┤
│ • Provider function calling protocol   │ • Project-declared CLI commands        │
│   (e.g., view_file, run_command)       │   (e.g., just check, pytest)           │
│ • Ephemeral JSON-RPC in turn artifacts │ • Durable SQLite / JSONL ledger        │
│ • Captured in tool_calls.jsonl         │ • Managed by `src/sase/tool/`          │
│ • Presented by `AgentLLMCallsPanel`    │ • Multi-stage timeline (run_silent)    │
│ • Currently lives in `TOOLS` deck (λ)  │ • Failure triage: NEW / KNOWN / FLAKY  │
│ • Purely internal agent behavior       │ • Toolchain probes & verdict receipts  │
│ • Strictly node-local to one agent     │ • Project-wide: run by humans, CI,     │
│                                        │   monitors, procs, or agents           │
└────────────────────────────────────────┴────────────────────────────────────────┘
```

When a user in the TUI asks "what tools were run?", they might mean:
- *"What model functions did this agent invoke while thinking?"* (LLM Calls)
- *"Did `check` pass on the repository? What lint rules failed? Is there a valid receipt?"* (SASE Tool Control Plane)

Conflating these two concepts in the UI leads directly to the issues identified in the user's initial proposal.

---

## 2. Detailed Critique of the User's Initial Hypotheses

### Critique A: "Adding a little hammer icon with a count to agent nodes that made tool calls"

The user suggested adding a hammer icon (e.g., `🔨 14`) to agent nodes in the left-hand node panel. Why does this integration fail?

1. **Extreme Low Signal-to-Noise Ratio (If counting LLM tool calls):**
   Modern agent workflows make extensive use of LLM tool calling. A standard coding agent makes between 20 and 200 tool calls per turn (`view_file`, `search_web`, `replace_file_content`, `run_command`).
   - If every agent displays `🔨 48`, `🔨 112`, `🔨 87`, the icon becomes universal wallpaper. It provides zero discrimination between a healthy agent, a struggling agent, or a finished agent.
   - The node row in `_agent_list_render_agent.py` is already very dense. It renders status prefixes, selection indicators, fold annotations (`×3`), clan status chips (`format_agent_count_chip`), turn lane indicators (`_MONITOR_GLYPH`, `_GATE_GLYPH`), bead linkage glyphs (`_BEAD_LINKED_AGENT_GLYPH`), agent identity names, owner badges, and fleet connection summaries. Adding another omnipresent number creates visual fatigue.
2. **Missing Diagnostic Verdict (If counting `ToolRun` executions):**
   If the hammer instead counts executions of `sase tool run` (e.g., `🔨 1` because the agent ran `sase tool run check`):
   - A raw count gives no indication of **outcome**. Did `check` pass? Did it fail with 15 new errors? Is it still running in the background? Did it hit known baseline errors?
   - In SASE, agents execute long-running verification commands via `sase monitor start` (monitor turns). A monitor turn already appears as its own node (`<session>--mon`) in the session tree with the monitor glyph (`◷`). Adding an uninformative hammer to the parent node duplicates presence without adding meaning.
3. **Total Invisibility of Non-Agent Tool Runs:**
   A developer running `sase tool run check` in their terminal before launching an agent, or a scheduler routine running verification periodically, has **no agent node at all**. A hammer on agent nodes leaves all developer-initiated and system-initiated tool runs completely orphaned.

### Critique B: "Adding a new card to the 'Tools' deck for this"

The user also suggested adding a second card to the existing `Tools` deck (`DeckId.TOOLS`). Why is this flawed as the primary integration?

1. **Scope Mismatch: Agent Data Decks are Strictly Node-Local:**
   In SASE's TUI architecture, Agent Data Decks (`Main`, `Files`, `Tools`, `Final`) exist solely to display details about the *currently selected agent node*.
   - If the user selects an agent that only did research or edited a plan without running verification, the `Tool Runs` card would be blank or show "No tools executed by this agent".
   - If the user wants to check why `just check` failed 10 minutes ago, they would have to guess and hunt for which agent ran it. If the developer ran it themselves, it is unreachable anywhere on the Agents tab.
2. **Read-Only Inspection vs. Interactive Control Plane:**
   Agent Data Decks are passive presentation surfaces (rendered as Textual scroll panels, with spread or paged views).
   `sase tool` is an interactive control plane: users need to **run** tools, **stop** running executions (`sase tool stop`), **filter** historical runs, **stream live logs** (`sase tool show -F`), and **triage** failure signatures. cramming a full control plane into an agent detail card either overcomplicates the card or cripples the tool control plane into a static text readout.
3. **Severe Naming Ambiguity Inside the Deck:**
   The `Tools` deck currently has glyph `\u03bb` (`λ`) and blurb *"LLM tool-call timeline"*. If the deck holds two cards—`LLM Calls` and `Tool Runs`—users will constantly mix up provider function calls with project command executions.

---

## 3. Analysis of the SASE TUI Design Space

Where *should* `sase tool` live? Let's analyze the viable candidates across the TUI:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           TUI ARCHITECTURAL CANDIDATES                          │
├───────────────────┬─────────────────────────────────────────────────────────────┤
│ Candidate         │ Assessment & Architectural Fit                              │
├───────────────────┼─────────────────────────────────────────────────────────────┤
│ 1. Dedicated      │ • Ideal for comprehensive control and visibility.           │
│    Top-Level Tab  │ • Breaks the canonical 3-tab symmetry (agents, artifacts,  │
│    ("tools")      │   services) in TAB_ORDER; requires global keymap changes.   │
├───────────────────┼─────────────────────────────────────────────────────────────┤
│ 2. Services Tab   │ • Services tab already houses procs and lumberjack chops.   │
│    Sub-Section    │ • But ToolRuns are not daemons; mixing check/test with      │
│                   │   service procs overcrowds the AxeDashboard layout.         │
├───────────────────┼─────────────────────────────────────────────────────────────┤
│ 3. Artifacts Tab  │ • Verdict Receipts are immutable proof artifacts, but       │
│    Provider       │   running and stopping tools does not fit document browsing.│
├───────────────────┼─────────────────────────────────────────────────────────────┤
│ 4. Admin Center   │ • High coherence with ProcsPane, LogsPane, StatisticsPane.  │
│    Modal Pane     │ • Modal paradigm hides active verification while working    │
│    (`ToolsPane`)  │   with agents; cannot be monitored side-by-side.            │
├───────────────────┼─────────────────────────────────────────────────────────────┤
│ 5. Agents Tab     │ • Where verification results directly matter to agents.     │
│    FINAL Deck     │ • FINAL deck already models turn landing & completion;      │
│    Integration    │   ToolRun verification receipts belong here naturally!      │
├───────────────────┼─────────────────────────────────────────────────────────────┤
│ 6. Fast Runner    │ • Instant access from anywhere without navigation overhead. │
│    Palette / Cmd  │ • Complements whatever permanent inspection surface is used.│
└───────────────────┴─────────────────────────────────────────────────────────────┘
```

### Insights from the Design Space Analysis:
1. **No single location solves all needs.** `sase tool` has a **global operational aspect** (running tests, browsing project history, inspecting repo-wide failure signatures) AND a **contextual agent aspect** (did this specific agent's patch pass verification?).
2. Therefore, the optimal solution must be **bifurcated**:
   - A **Global Tool Control Surface** for running, browsing, and triaging project tools.
   - A **Contextual Agent Surface** on the Agents tab for verification status and receipts.

---

## 4. The Recommended Architecture: The Three-Pillar Tool UX

We recommend implementing the integration across three cohesive pillars:

```
                                THREE-PILLAR TOOL UX
                                
   ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
   │       PILLAR 1        │   │       PILLAR 2        │   │       PILLAR 3        │
   │   GLOBAL TOOL HUB     │   │   AGENTS TAB CONTEXT  │   │  INTERACTIVE CONTROL  │
   ├───────────────────────┤   ├───────────────────────┤   ├───────────────────────┤
   │ • Dedicated Tools Hub │   │ • Verification Status │   │ • Quick Runner Palette│
   │   (ToolsPane modal /  │   │   Chips on agent rows │   │   (hotkey 'T' or ';') │
   │   candidate 4th tab)  │   │   ([✓ check], [✗])    │   │ • Live stage progress │
   │ • Catalog + Ledger +  │   │ • Verification Card   │   │ • Stop/Wait controls  │
   │   Stage Inspector +   │   │   in FINAL deck (⊛)   │   │ • 1-click jump from   │
   │   Triage Signatures   │   │ • Rebrand λ to "Calls"│   │   failure to bead/code│
   └───────────────────────┘   └───────────────────────┘   └───────────────────────┘
```

---

### Pillar 1: The Global Tool Hub (`ToolsPane`)

The Global Tool Hub is the definitive home for `sase tool` in the TUI. It provides a full two-column master-detail control surface.

#### Layout Specification
- **Left Column (Navigation & List):**
  - **Upper Nav Section: Tool Catalog (`tools:` in `sase.yml`)**
    - Rows: `check`, `test`, `install`, `check-full`, `test-visual`.
    - Columns: Tool name, LAST status chip (`✓ pass`, `✗ fail/1`, `⟳ run`), TYPICAL duration (e.g., `4m 13s (n=30)`), receipt badge (`[receipt: 1h42m left]`).
    - Actions on selected catalog tool:
      - `Enter` or `r`: Run tool in background (`-H`) as a monitored execution.
      - `R`: Run with extra arguments prompt.
      - `f`: View grouped failure signatures for this tool (`sase tool failures -t <tool>`).
  - **Lower Nav Section: Recorded ToolRuns Ledger (`sase tool runs`)**
    - Chronological list of runs with filter chips: `All`, `Failed`, `Running`, `Active Project`.
    - Rows show: Run ID (short 8-char prefix), Tool name, State (`succeeded`, `failed/1`, `signaled`, `running`), Duration, Owner (agent name, monitor ID, or CLI).
- **Right Column (ToolRun Detail & Inspection):**
  When a ToolRun is selected, the right pane renders three collapsible/tabbed view sections:
  1. **Summary & Fingerprints:**
     - Run ID, ARGV, duration, exit code, terminal cause, settled by.
     - Git dirty count before and after (`6 -> 6`).
     - Toolchain probe versions (`python 3.14.7`, `just 1.58.0`, `ruff 0.16.9`, `mypy 2.3.1`, `symvision 0.1.0`).
     - Verdict receipt status (Minted, Expired, or Refused with reason).
  2. **Interactive Stage Timeline (`stages: run_silent`):**
     - Renders each stage with duration, status, and progress bar:
       ```
       ✓ fmt (python)               235ms  ████
       ✓ fmt (markdown)             11.9s  ████████████
       ✓ lint (keep-sorted)         246ms  ████
       ✓ lint (ruff)                261ms  ████
       ✓ lint (mypy)                45.6s  ████████████████████
       ✗ lint (symvision)           1m 00s ████████████████████████  [5 NEW FAILURES]
       - test (skipped)                 —
       ```
  3. **Triage & Failure Signatures:**
     - Displays the structured failure items extracted by triage.
     - Classifies each item clearly:
       - `[NEW]` (red): Regression introduced in this run.
       - `[KNOWN]` (yellow): Pre-existing baseline failure with independent witnesses.
       - `[FLAKY]` (purple): Known intermittent failure.
     - Pressing `Enter` on a failure item jumps directly to the source file and line. Pressing `b` opens `/sase_new_task` with the failure pre-filled.
  4. **Retained Log Stream (`-l` / `-F`):**
     - View stdout and stderr with search (`,/`) and live follow mode toggle (`F`).

#### Placement Strategy: Modal First, Top-Level Tab Path
To avoid disrupting the existing 3-tab order (`TAB_ORDER = ("agents", "artifacts", "services")`) and breaking external automation or user muscle memory:
- **Phase A (Initial Landing):** Implement as an instant-access full-screen modal or Admin Center pane (`ToolsPane`), bound globally to `g t` (goto tools) and `;tools`.
- **Phase B (Evolutionary Promotion):** Once tested, evaluate promoting to a 4th top-level tab (`("agents", "artifacts", "tools", "services")`) behind a feature flag (`FeatureFlag.tui_tools_tab`).

---

### Pillar 2: Contextual Agents Tab Integration

Rather than polluting the agent node with an ambiguous hammer count or cramming a control plane into an agent card, integrate verification where it delivers maximum cognitive value:

#### 1. Verification Outcome Chips on Agent Nodes (Left Column)
Instead of:
`● (running) 4m · gemini-3.8-flash 🔨 42`  *(Ambiguous! Does 42 mean file reads or tests?)*

Render an **authoritative Verification Status Chip** only when verification has been performed or is actively running:

```
● (running) 4m · gemini-3.8-flash [⟳ check: lint]
○ (done) 12m · claude-3.7-sonnet  [✓ check]  ○sase-1bd.3
▲ (failed) 8m · gpt-5             [✗ check: 2 new]
```

- **Semantics:**
  - `[⟳ <tool>: <stage>]` (cyan): Agent or its monitor turn is currently running a `ToolRun`. Shows the current active stage.
  - `[✓ <tool>]` (green): Tool run succeeded or minted a covering verdict receipt (`pass` or `no_new_failures`).
  - `[~ <tool>]` (yellow): Tool run completed with KNOWN baseline failures only (`no_new_failures`).
  - `[✗ <tool>: N new]` (red): Tool run failed with N regressions (`new_failures`).
- **Clean Fallback:** Agents that performed no verification display no badge, keeping the list uncluttered.
- **Click / Key Action:** When an agent row is highlighted, pressing `g v` (goto verification) or `Enter` on the badge opens the ToolRun Inspector for that exact run.

#### 2. Rebrand the `TOOLS` Deck to "LLM CALLS"
In `src/sase/ace/tui/widgets/decks/spec.py`:
- Rename `DeckId.TOOLS` display name from `TOOLS` to `CALLS` or `LLM CALLS`.
- Keep glyph `\u03bb` (`λ`) and picker key `t`.
- Blurb: *"LLM prompt tool-call timeline"*.
- This instantly eliminates the semantic confusion between LLM provider function calling and project command execution.

#### 3. Place ToolRun Verification into the `FINAL` Deck
The `FINAL` deck (`DeckId.FINAL`, glyph `⊛`, blurb *"how this node's turns landed"*) is already the designated home for turn completion, landing outcomes, and finalizers.
- In SASE, `just check` is the gating verification before host completion (`builtin@commit`).
- Add a dedicated **Verification Card** to the `FINAL` deck:
  - Header: Shows covering receipt status (`Covered by receipt #a8f2c (48m remaining)` or `No valid receipt`).
  - ToolRun Summary: Run ID, exit code, duration, dirty git fingerprint.
  - Stage Summary: Stages executed, duration per stage, failure points.
  - Triage Verdict: `no_new_failures` vs `new_failures`.
  - Action hint: Press `Enter` to inspect full ToolRun in the Tools Hub.

---

### Pillar 3: Interactive Execution & Fast Runner Flow

Developers need to trigger tools quickly while monitoring agents.

#### 1. The Quick Tool Runner Palette
- Pressing `t` from the normal TUI mode (or `;tool run`) opens a lightweight, centered runner popup:
  ```
  ┌── Run Project Tool ───────────────────────────────────────────┐
  │ > check                                                       │
  ├───────────────────────────────────────────────────────────────┤
  │ [1] check        Run the repository scoped check. (4m 13s)   │
  │ [2] test         Run just test; extra pytest args allowed     │
  │ [3] check-full   Run the exhaustive repository check.         │
  │ [4] install      Install development dependencies.            │
  │ [5] test-visual  Run visual and screenshot tests.             │
  │ [0] ad-hoc...    Run arbitrary argv through sase tool run --  │
  ├───────────────────────────────────────────────────────────────┤
  │ Enter: Run in background (-H)   Ctrl+E: Run with extra args   │
  └───────────────────────────────────────────────────────────────┘
  ```
- Triggering a run creates a durable `ToolRun` reservation, hands it off to a background proc or monitor, and posts a discreet status toast: `Started ToolRun 9443436 (check)`.
- When the run settles, a non-intrusive notification informs the user: `ToolRun 9443436 (check) succeeded (4m 12s) · Receipt minted`.

---

## 5. Visual Wireframes & ASCII Schematics

### Mockup 1: Agents Tab with Verification Outcome Badge & Rebranded Decks

```
╭─ Agents ───────────────────────────────────────────────────────╮╭─ MAIN (auto) ─── FILES ─── CALLS ─── FINAL (⊛) ───────────╮
│ @default                                                       ││ Context  Reply                                            │
│   ● (running) 4m · gemini-3.8-flash [⟳ check: lint]            ││ ───────────────────────────────────────────────────────── │
│   ○ (done) 12m · claude-3.7-sonnet  [✓ check]  ○sase-1bd.3     ││ SASE Turn: research.2t.gem (Turn 1)                        │
│   ▲ (failed) 8m · gpt-5             [✗ check: 2 new]           ││ Model:     gemini-3.8-flash (High)                        │
│                                                                ││ Status:    RUNNING (in verification monitor)              │
│                                                                ││                                                           │
│                                                                ││ [Prompt Context & Live Reply Output...]                    │
│                                                                ││                                                           │
│                                                                ││                                                           │
╰────────────────────────────────────────────────────────────────╯╰───────────────────────────────────────────────────────────╯
```

### Mockup 2: The `FINAL` Deck Verification Card

```
╭─ FINAL (⊛) ────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Overview  Verification  Receipts                                                                                           │
│ ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── │
│ VERIFICATION OF RECORD                                                                                                     │
│ Run ID:       67109407508077cb56247e98a12d4a8b                                                                             │
│ Tool:         check (`just check`)                                                                                         │
│ Outcome:      FAILED (exit code 1)                                                                                         │
│ Duration:     4m 13s (typical: 4m 13s)                                                                                     │
│ Fingerprint:  Dirty files: 6 -> 6 (mutated_input: false)                                                                   │
│                                                                                                                            │
│ TRIAGE VERDICT: new_failures (has 5 new failure items)                                                                     │
│                                                                                                                            │
│ STAGES                                                                                                                     │
│   ✓ fmt (python)               235ms  ██                                                                                   │
│   ✓ fmt (markdown)             11.9s  ██████                                                                               │
│   ✓ lint (ruff)                261ms  ██                                                                                   │
│   ✓ lint (mypy)                45.6s  ████████████████████                                                                 │
│   ✗ lint (symvision)           1m 00s ██████████████████████████  [NEW FAILURES]                                           │
│                                                                                                                            │
│ NEW FAILURES (5)                                                                                                           │
│   • lint (symvision): Error: --epic-symbol 'sase-1bd.3(UpdateFailure)': bead is closed.                                    │
│   • lint (symvision): Error: --epic-symbol 'sase-1bd.3(settle_update_attempt)': bead is closed.                             │
│   • lint (symvision): Error: --epic-symbol 'sase-1bd.3(dismiss_update_failure)': bead is closed.                            │
│                                                                                                                            │
│ Press <Enter> to open full ToolRun Inspector · Press <l> to view logs · Press <b> to file bead                             │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Mockup 3: The Dedicated Global Tool Hub (`ToolsPane`)

```
╭─ Tools Hub ────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ NAMED TOOLS                     │ TOOL RUN: 67109407 (check) · FAILED/1 · 4m 13s                                           │
│  [✓] check         4m 13s (n=30)│ ──────────────────────────────────────────────────────────────────────────────────────── │
│  [✗] check-full    failed/1     │ ARGV:       just check                                                                   │
│  [✓] install       1m 11s (n=4) │ LAUNCH:     handoff (owner: monitor research.2t.gem--mon)                                │
│  [✓] test          15m 37s (n=3)│ TOOLCHAIN:  python=3.14.7  just=1.58.0  ruff=0.16.9  mypy=2.3.1  symvision=0.1.0        │
│  [!] test-visual   signaled     │                                                                                          │
│                                 │ STAGE TIMELINE                                                                           │
│ ─────────────────────────────── │   ✓ fmt (python)               235ms                                                     │
│ RECENT RUNS                     │   ✓ fmt (markdown)             11.9s                                                     │
│  ⟳ 94434363 check      running  │   ✓ lint (ruff)                261ms                                                     │
│  ✗ 67109407 check      4m 13s   │   ✓ lint (mypy)                45.6s                                                     │
│  ✓ b6f33d52 check      4m 10s   │   ✗ lint (symvision)           1m 00s  [5 new failures]                                  │
│  ✓ a12ef389 test       15m 37s  │                                                                                          │
│  ✓ 88bc1120 install    1m 11s   │ TRIAGE ITEMS                                                                             │
│                                 │   CLASS  STAGE             ITEM SUMMARY                                                  │
│                                 │   NEW    lint (symvision)  --epic-symbol 'sase-1bd.3(UpdateFailure)': bead is closed.   │
│                                 │   NEW    lint (symvision)  --epic-symbol 'sase-1bd.3(settle_update_attempt)': closed.    │
│                                 │   KNOWN  lint (symvision)  RunViewLog in src/sase/core/finalizer_run_view.py (13 seen) │
│                                 │                                                                                          │
│                                 │ [Logs: stdout.log (48KB) · stderr.log (12KB) · events.jsonl]                             │
╰─────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────╯
```

---

## 6. Comparison of Alternatives

| Feature / Criterion | User Proposal A: Hammer Icon on Agent | User Proposal B: Card in "Tools" Deck | Recommended Proposal: Three-Pillar Architecture |
| :--- | :--- | :--- | :--- |
| **Semantic Clarity** | **Poor**: Conflates LLM tool calls with named tools. | **Poor**: Tools deck blurb is "LLM tool-call timeline". | **Excellent**: Explicit separation between "LLM Calls" and "Named Tools". |
| **Information Density** | **Noisy**: Adds clutter without state or outcome. | **Muddled**: Crammed into a passive text scroll panel. | **High Value**: Verification badge gives immediate pass/fail/progress status. |
| **Non-Agent Tool Visibility** | **Zero**: Terminal/CI/scheduler runs are invisible. | **Zero**: Only shows runs tied to current agent. | **Complete**: Global Tool Hub indexes all project and machine runs. |
| **Control & Interactivity** | **None**: Pure display glyph. | **Passive**: Cannot run, stop, or triage tools. | **Rich**: 1-key runner, live follow, stop control, and bead creation. |
| **Triage & Receipt Integration** | **None**: No room for stages or verdicts. | **Clunky**: Triage tables do not fit card spread. | **Native**: Direct stage timeline, NEW vs KNOWN classification, and receipts. |
| **Architectural Invariants** | Fits visually, but degrades node readability. | Fits deck model, but violates agent data locality. | Preserves all SASE architectural invariants and deck conventions. |

---

## 7. Concrete Implementation Roadmap

### Phase 1: Core TUI Data Bridge (`src/sase/ace/tui/models/` & `data_providers/`)
1. Create `src/sase/ace/tui/models/tool_runs.py`:
   - Define immutable dataclasses: `ToolRunSummary`, `ToolRunDetail`, `ToolStageEntry`, `TriageItemEntry`.
   - Wrap `sase.core.tool_run` (`tool_run_list`, `tool_run_show`) and `sase.tool.query` with non-blocking, worker-thread fetchers.
2. Add agent association query:
   - Query `tool_run_list({"agent": agent.identity, "project": ...})` to resolve the latest `ToolRun` for any selected agent or monitor turn.

### Phase 2: Agents Tab Badges & Deck Clarification
1. In `src/sase/ace/tui/widgets/_agent_list_render_agent.py`:
   - Inspect the agent's cached verification state.
   - If a verification `ToolRun` exists, append the formatted status chip (`[✓ check]`, `[✗ check]`, `[⟳ check: stage]`) right before the identity name block.
2. In `src/sase/ace/tui/widgets/decks/spec.py`:
   - Clarify `DeckId.TOOLS` name and blurb: change display name to `CALLS` or `LLM CALLS` to permanently disambiguate provider calls from project tools.
3. In `src/sase/ace/tui/widgets/decks/final/`:
   - Add a `VerificationCard` to the `FINAL` deck (`DeckId.FINAL`), rendering the latest `ToolRun` for the selected node, stage breakdown, triage verdict, and covering receipt status.

### Phase 3: The Global Tool Hub (`ToolsPane` & `ToolRunnerModal`)
1. Create `src/sase/ace/tui/modals/tools_pane.py`:
   - Two-column Textual widget implementing the Catalog, Runs Ledger, Stage Timeline, and Triage Table.
   - Register in `ConfigCenterModal` (`src/sase/ace/tui/modals/config_center_catalog.py`) as a dedicated `Tools` tab.
2. Create `src/sase/ace/tui/modals/tool_runner_modal.py`:
   - Quick popup palette for running catalog tools (`check`, `test`) in the background (`-H`).
3. Wire global keybindings in `src/sase/default_config.yml`:
   - Map `g t` and `:tool` to open the Tools Hub.
   - Map `t` (in normal mode) or `;tool` to open the Quick Tool Runner.

---

## Conclusion & Summary Recommendation

The user's initial hesitation was completely justified:
- A **hammer icon with a count** on agent nodes adds noise without signal, conflates LLM calls with project commands, and tells the user nothing about whether verification succeeded or failed.
- Adding a **card to the "Tools" deck** traps a project-level control plane inside an agent-scoped inspection view and confuses provider function calling with build/test execution.

By adopting the **Three-Pillar Tool UX**:
1. Project tools gain a first-class, dedicated control hub (**Pillar 1**).
2. Agents tab gains high-signal verification badges and places execution receipts where they logically belong—in the `FINAL` deck (**Pillar 2**).
3. Developers gain instantaneous execution, live stage tracking, and one-click failure triage (**Pillar 3**).

This design honors SASE's core architectural tenets, eliminates terminology collision, and elevates `sase tool` into an intuitive, powerful component of the interactive developer experience.
