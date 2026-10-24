# SASE Questions Deck Visibility: Output Variables vs. First-Class Deck Rendering

**Author:** researcher gem (`research.58.gem`)  
**Date:** 2026-10-24  
**Topic:** Automating visibility of `/sase_questions` Q&A in the SASE TUI Main Deck  
**Status:** Complete  

---

## Executive Summary

When a SASE agent uses the `/sase_questions` skill to pause execution and solicit user input, the asking turn immediately hands off execution via a question gate turn (`kind="question"`). Currently, when an operator inspects that agent session on the "Agents" tab in the SASE TUI, the questions, options, recommended choices, answers, and settlement provenance are either buried in notification modals or dumped as raw JSON inside gate output logs.

The user proposed:
> *"start setting sase variables automatically whenever the `/sase_questions` skill is used. The goal of this change is to make it so when the user selects an agent session on the 'Agents' tab that is associated with an agent turn that asked questions, those questions, their recommended answers, their actual answers (if any questions have been answered yet), and how the questions were answered (if any questions have been answered yet) are all immediately visible (since variables are rendered in the main deck)."*

### Core Findings & Critique

1. **The Core Motivation is High-Value; The Transport Mechanism is Problematic:**  
   Immediate visibility of question status in the session view of the TUI is a critical UX improvement. Today, sessions in `QUESTION` status provide minimal immediate context in the prompt panel without opening the notification modal or digging into gate bundles. However, using **SASE Output Variables (`sase var`)** as the transport mechanism to achieve this visibility is an architectural mismatch that introduces significant liabilities.

2. **Why Hijacking `sase var` is an Architectural Antipattern:**
   - **Domain / Semantic Conflation:** Output variables in SASE are explicitly designed for *agent-produced computational outputs and facts* passed downstream to later agents via Jinja expressions (`{{ agents["agent"].var }}`). User questions and human/system answers are *interactive gate dialogue*, not agent computational outputs. User answers are external inputs into subsequent turns.
   - **Lifecycle & Turn Immutability Violation:** When an agent executes `sase questions '<json>'`, its process group is killed via `SIGTERM` within milliseconds. At ask-time, the actual answers and how they were answered do not yet exist. Modifying variables later when the user answers requires either retroactively mutating the dead agent's `agent_meta.json` (violating turn finality) or writing to the gate turn's metadata, which distorts variable attribution.
   - **Downstream Jinja Context Pollution:** Storing verbose question texts, multi-line option descriptions, and user feedback in `output_variables` automatically exposes them to downstream agents and macro swarms. Downstream turns inspecting `agents` will ingest large blocks of redundant text, inflating token overhead and latency.
   - **Hard Limits & Failure Risks:** Output variables enforce strict limits in `sase.core.output_variable_values`: max 8 KiB per string leaf, max 65,536 bytes encoded JSON, and max 256 variables. Multi-question forms, lengthy markdown descriptions, and verbose reviewer feedback risk colliding with these limits.
   - **Suboptimal Visual UX:** Output variables render in the TUI as flat, generic YAML key-value lines via `format_var_value_lines`. They cannot render interactive-style checkboxes (`[x]`), status badges (`[Recommended]`, `[Answered via TUI]`, `[Auto-Resolved]`), or cleanly folded multi-question blocks.
   - **Redundant State Duplication:** SASE *already persists* every question, option, answer, feedback note, caller identity, and submission source canonically on disk in the gate bundle (`request.json` and `response.json`). Setting variables merely creates a duplicate, out-of-band copy that must be synchronized across every settlement vector (TUI, Telegram, mobile, `%auto`, CLI, cancellation, timeout).

3. **The Recommended Architectural Solution:**
   Instead of using output variables as a proxy for UI rendering, SASE should implement a **First-Class Questions Section / Card in the Main Deck** (in `_agent_display_header.py` or as an enhanced phase in `_agent_gate_section.py` / `_agent_session_reply_blocks.py`).
   - Reads directly from canonical gate storage (`request.json` and `response.json`) using existing helper `sase.question_gate_turn.rounds:question_rounds()`.
   - Works **retroactively for all historical question sessions** with zero data migration.
   - Provides rich, dedicated styling: question headers, clean checkbox options, `[RECOMMENDED]` badges, `[x]` selected answers, and provenance lines (`Answered by Bryan via TUI Modal at 18:02` or `Auto-resolved via %auto policy`).
   - Keeps `output_variables` clean, lightweight, and focused purely on computational outputs.

---

## 1. Deep Dive: Current Q&A and Main Deck Architecture

To evaluate the proposal accurately, we trace the complete lifecycle of a question turn in the SASE codebase:

```
[Agent Invocation]
  └── /sase_questions skill -> sase questions '<json>' (CLI)
        ├── Validates question schema (_validate_questions)
        ├── Writes .sase_questions_pending marker
        └── Sends SIGTERM to runner process group (kill_agent_runner_group)
              │
[AXE Execution Loop]
  └── run_agent_exec_questions.py detects marker
        ├── Calls create_question_gate_turn()
        ├── Writes request.json (questions, options, metadata) into gate bundle
        └── Creates session-attached Gate Turn member (role "gate", status "QUESTION")
              │
[Waiting / Presentation]
  ├── Session displays status "QUESTION" in TUI & Telegram
  └── Notification modal / Telegram bot / mobile app notifies user
              │
[Settlement / Resolution]
  ├── User submits answer via TUI / mobile / Telegram / CLI OR %auto auto-resolves
  ├── execute_user_question_response() -> execute_gate_selection()
  ├── Writes response.json (option_results, feedback, source, caller, timestamp)
  └── Gate turn transitions from "pending" to "answered"
              │
[Continuation]
  └── question_next_action() walks round chain via question_rounds()
        ├── Assembles merged Q&A markdown (build_merged_qa_markdown)
        └── Injects Q&A block into successor turn prompt
```

### 1.1 How `sase questions` Works Today
- **CLI (`src/sase/main/questions_command_handler.py`):**  
  The agent calls `sase questions '<json>'`. The CLI validates that the JSON is an array of question objects containing `question` (string), optional `header` (string), `options` (array of `{label, description}`), and optional `multiSelect` (boolean).  
  It writes `.sase_questions_pending` to `SASE_ARTIFACTS_DIR` and immediately terminates the runner process group via `kill_agent_runner_group()`.

- **Gate Turn Creation (`src/sase/question_gate_turn/create.py` & `src/sase/gate_turn/transaction.py`):**  
  The execution loop catches the exit, finds the pending marker, and creates a session-attached gate turn via `create_question_gate_turn()`.  
  A gate bundle directory is created containing:
  - `request.json`: Stores `payload.questions` (full question definitions) and metadata (`session_id`, `timestamp`, `auto` policy).
  - Member metadata in `agent_meta.json` with `turn_kind="gate"`, `agent_session_role="gate"`, `gate_kind="question"`, and `gate_state="pending"`.

- **Settlement & Answer Persistence (`src/sase/user_question_actions.py` & `src/sase/notification_gates/executor.py`):**  
  When an answer is submitted (via TUI question modal, Telegram, mobile, `%auto`, or CLI), `execute_user_question_response()` invokes `execute_gate_selection()`. This writes `response.json` containing:
  - `option_results[0].result.answers`: Array of `{question, selected: [...], custom_feedback: ...}`.
  - `feedback`: Reviewer note / global note.
  - `source`: The exact client surface (`"tui"`, `"telegram"`, `"mobile"`, `"auto"`, `"cli"`, `"host"`).
  - `caller`: `"human"` or `"agent"`.
  - `responded_at_unix`: Precise UNIX timestamp.

- **Successor Continuation (`src/sase/question_gate_turn/followup.py` & `rounds.py`):**  
  `question_next_action()` reads the gate bundle, reconstructs all prior rounds using `question_rounds()`, and merges them with `build_merged_qa_markdown()`. The successor turn receives the full history in its prompt.

### 1.2 How the Main Deck Renders an Agent Session Today
- **Prompt Panel Structure (`src/sase/ace/tui/widgets/prompt_panel/_agent_display_agent_session_render.py`):**  
  When the user selects an agent session on the "Agents" tab, the TUI renders a `card_document`:
  1. `context_card`: Contains `header_text` (identity, metadata, runner queue, OUTPUT VARIABLES, and WORKFLOW VARIABLES).
  2. `reply_card`: Contains turn reply blocks (the initial agent turn's streamed output, followed by `build_gate_phase` for the gate turn, followed by subsequent turns).

- **How Output Variables are Rendered (`src/sase/ace/tui/widgets/prompt_panel/_agent_output_variables.py`):**  
  `append_agent_output_variables_section()` iterates over `_output_variable_contributors(agent)`, which inspects `(agent, *agent.followup_agents)`. For any member that has non-empty `output_variables`, it renders the variables using YAML block formatting (`format_var_value_lines` from `sase.core.output_variable_display`).

- **What the Gate Turn Renders in the Deck Today (`src/sase/ace/tui/widgets/prompt_panel/_agent_gate_section.py`):**  
  Currently, `build_gate_phase()` renders:
  - Phase divider: `GATE TURN` with status glyph.
  - Decision metadata: Kind (`question`), Status (`QUESTION → ANSWERED`), State (`pending` / `answered`), Elapsed time, Deadline, Gate ID.
  - Gate Output: If settled, it dumps raw JSON of `option_results` via `lazy_renderable(json.dumps(option_results, indent=2), "json")`.  
  **Crucially:** While pending, the questions and options are NOT visible in the deck at all; and while answered, they appear only as an unstyled, raw JSON array of option results.

---

## 2. In-Depth Critique of the Proposed Plan

The user’s proposal is to automatically set SASE variables (`sase var`) whenever `/sase_questions` is used, so that selecting the agent session on the "Agents" tab displays the Q&A state immediately in the main deck's "OUTPUT VARIABLES" section.

### 2.1 The Appeal of the Plan
- **Zero TUI Code Required:** The TUI already renders `output_variables` prominently in the header of the main deck. Populating variables makes text appear in the main deck without modifying any Textual widgets.
- **CLI Accessibility:** Variables can be queried out-of-band with `sase var get` and `sase var list`.
- **Session Aggregation:** `_output_variable_contributors` in the TUI already aggregates variables across all turns in a session (`(agent, *agent.followup_agents)`).

### 2.2 Critical Flaws and Architectural Tensions

#### Flaw 1: Domain & Semantic Mismatch ("Output Variables" vs. "Interactive Dialogue")
SASE Output Variables are explicitly defined in documentation and skills as:
> *"Attach named JSON-shaped output variables to the current SASE agent run... to publish a small JSON-shaped value for a later SASE agent"* (`sase_var/SKILL.md`).

Output variables represent *facts produced by the agent* (e.g. `report_path`, `exit_code`, `build_status`, `artifacts`).  
Questions and user responses are an *interactive negotiation between the agent and a human operator*. Specifically:
- The question is a *request for guidance*.
- The answer is an *input provided by a human (or policy)*.
- Attributing a human user's answer as an "agent output variable" is a conceptual confusion. It abuses the variable system as a generic UI rendering bridge.

#### Flaw 2: Lifecycle Asymmetry & Turn Immutability
When the agent executes `/sase_questions`:
1. The agent process is killed via `SIGTERM` within ~100ms.
2. At this moment, only the question text and options exist. The answer, submission source, and reviewer notes **do not exist yet**.
3. When the user eventually answers (minutes or hours later), which entity sets the variables?
   - **Option A (Mutate the asking agent):** The asking agent is dead and its turn is marked `DONE`. Retroactively editing an old turn's `agent_meta.json` violates SASE's core architectural principle of immutable, single-turn execution records.
   - **Option B (Set on the Gate Turn):** The gate turn member can write to its own `output_variables`. But gate turns are non-LLM synthetic turns whose role is managing the gate, not authoring agent variables. Furthermore, in the TUI, multi-member attribution displays:
     ```
     q: questions: ...
     ```
     which exposes internal turn mechanics to the user.

#### Flaw 3: Downstream Context Window Pollution
Variables saved in `agent_meta.json` are exposed to subsequent agents in Jinja templates via `{{ agents["name"].key }}` or globally via `agents`.  
If an agent asks three detailed questions with paragraphs of background options, and these are stored in `output_variables`:
- Downstream agents that inspect `agents` will consume thousands of prompt tokens ingesting raw Q&A schemas.
- Downstream continuation agents *already* receive a clean, curated markdown synthesis of Q&A via `sase.question_gate_turn.followup:question_next_action` and `build_merged_qa_markdown()`. Adding questions to `output_variables` creates redundant prompt bloat.

#### Flaw 4: Variable System Hard Resource Limits
SASE enforces strict structural and volumetric limits on output variables (`src/sase/core/output_variable_values.py`):
- `MAX_OUTPUT_VARIABLES = 256`
- `MAX_OUTPUT_VARIABLE_VALUE_BYTES = 8_192` (per string leaf)
- `MAX_OUTPUT_VARIABLE_DEPTH = 8`
- `MAX_OUTPUT_VARIABLE_NODES = 1_024`
- `MAX_OUTPUT_VARIABLE_ENCODED_BYTES = 65_536`

In complex workflows, multi-question rounds with detailed option descriptions, reviewer comments, and free-form `custom_feedback` can easily approach or exceed node and byte caps, leading to unexpected runtime validation failures during gate settlement.

#### Flaw 5: Suboptimal TUI Deck UX & Formatting
The prompt panel renders output variables via `format_var_value_lines` into plain YAML text. This results in:
- No visual distinction between questions and answers.
- No checkboxes (`[x]` vs `[ ]`).
- No badges for `[RECOMMENDED]` vs selected options.
- Long text blocks rendered as escaped or indented YAML strings rather than readable markdown.
- Cluttering the "OUTPUT VARIABLES" section, pushing actual output variables (like generated artifact paths or test results) far down the screen.

#### Flaw 6: State Duplication & Synchronization Risk
The gate bundle already stores:
- `request.json` -> questions, headers, options, multiSelect.
- `response.json` -> selected answers, custom feedback, source (`"tui"`, `"telegram"`, `"mobile"`, `"auto"`), caller (`"human"`), timestamp.

Writing to `output_variables` introduces a secondary, denormalized copy. If a gate times out, is cancelled, or is manually cleared, the variables must be carefully updated to reflect that state; otherwise, the main deck will display contradictory information (e.g. gate marked `TIMED OUT` while variables show `status: "pending"`).

---

## 3. Detailed Comparison: Two Approaches

| Dimension | Approach A: SASE Output Variables (`sase var`) | Approach B: First-Class Questions Deck Section (Recommended) |
| :--- | :--- | :--- |
| **Data Source** | Denormalized copy in `agent_meta.json["output_variables"]` | Canonical gate bundle (`request.json` + `response.json`) |
| **Historical Data** | ✗ Forward-only (or requires database migration script) | ✓ **Works instantly for all past runs** |
| **Downstream Jinja Context**| ✗ Pollutes Jinja `agents` context with large Q&A blobs | ✓ Lean; Q&A reaches successor prompt via existing markdown hook |
| **UX & Visual Styling** | ✗ Generic YAML key-value lines; no checkboxes or badges | ✓ **Rich formatting**: `[x]` checkboxes, `[RECOMMENDED]` badges, source tags |
| **Resource Limits** | ✗ Bound by 8 KiB leaf / 65 KiB JSON caps | ✓ Bound only by terminal viewport / scroll |
| **Turn Immutability** | ✗ Modifies metadata post-mortem or on gate turn | ✓ Pure read-time projection of immutable gate files |
| **Code Surface Affected** | `questions_command_handler.py`, `user_question_actions.py`, `executor.py` | `_agent_display_header.py` or `_agent_gate_section.py` |

---

## 4. Implementation Blueprint for Approach A (If Variables ARE Used)

If Bryan decides to proceed with setting variables—either as a short-term patch or because programmatic access via `sase var get` is explicitly desired—the implementation must avoid the worst failure modes.

### 4.1 Recommended Variable Schema
Do NOT pollute the variable namespace with multiple top-level keys like `question_1`, `question_2`, `answers`. Instead, use a single reserved top-level key: `questions` (or `user_questions`).

```json
{
  "questions": [
    {
      "index": 1,
      "header": "Database Engine",
      "question": "Which database engine should we adopt?",
      "recommended": "PostgreSQL",
      "multi_select": false,
      "status": "answered",
      "actual": ["PostgreSQL"],
      "custom_feedback": null,
      "source": "tui",
      "answered_by": "human",
      "answered_at": "2026-10-24T18:02:15Z"
    }
  ]
}
```

#### Field Specifications:
- `header`: Short label if provided; falls back to `null`.
- `question`: Full question prompt text.
- `recommended`: The first option's label (`options[0]["label"]`), matching the `/sase_questions` convention.
- `status`: `"pending"` (initial), `"answered"`, `"timed_out"`, or `"cancelled"`.
- `actual`: Array of selected label strings. When pending, `null`.
- `custom_feedback`: String provided in "Other" or reviewer notes; otherwise `null`.
- `source`: How it was answered: `"tui"`, `"telegram"`, `"mobile"`, `"auto"`, `"cli"`, or `"host"`. When pending, `null`.
- `answered_by`: `"human"` or `"agent"`. When pending, `null`.
- `answered_at`: ISO 8601 timestamp or `null`.

### 4.2 Where to Hook the Mutation Points

#### Mutation Point 1: Ask-Time (Initial State)
- **Location:** `src/sase/question_gate_turn/create.py:create_question_gate_turn()`
- **Action:** When creating the gate-turn member (`creation.record.artifacts_dir`), initialize `output_variables` on that gate turn:
  ```python
  from sase.core.agent_output_variables import set_agent_output_variables

  initial_questions = []
  for idx, q in enumerate(questions, start=1):
      options = q.get("options", [])
      recommended = options[0].get("label") if options else None
      initial_questions.append({
          "index": idx,
          "header": q.get("header"),
          "question": q.get("question"),
          "recommended": recommended,
          "multi_select": bool(q.get("multiSelect", False)),
          "status": "pending",
          "actual": None,
          "custom_feedback": None,
          "source": None,
          "answered_by": None,
          "answered_at": None,
      })

  set_agent_output_variables(
      creation.record.artifacts_dir,
      {"questions": initial_questions},
  )
  ```
  *Why on the gate turn?* Because the asking agent is already in the process of being terminated by SIGTERM. The gate turn is the durable entity that lives through the wait period.

#### Mutation Point 2: Settle-Time (Interactive Answer Submission)
- **Location:** `src/sase/user_question_actions.py:execute_user_question_response()`
- **Action:** Immediately after `execute_gate_selection()` succeeds, retrieve `gate_turn.artifacts_dir` and update the `questions` variable:
  ```python
  from sase.core.agent_output_variables import update_agent_output_variable
  from sase.core.time import local_now_iso

  def _apply_answers(current_val):
      if not isinstance(current_val, list):
          return current_val
      # Merge answers from normalized response_json into question entries
      # Set status="answered", source=source, answered_by=response_caller, etc.
      ...
      return updated_questions

  update_agent_output_variable(gate_turn.artifacts_dir, "questions", _apply_answers)
  ```

#### Mutation Point 3: Auto-Resolution (%auto Short-Circuit)
- **Location:** `src/sase/axe/run_agent_exec_questions.py:_continue_after_auto_answered_question()`
- **Action:** When `%auto` answers synchronously without a human wait, update the gate turn's `output_variables` with `status: "answered"`, `source: "auto"`, `answered_by: "agent"`.

#### Mutation Point 4: Cancellation or Timeout
- **Location:** `src/sase/gate_turn/settlement.py:settle_gate_turn()`
- **Action:** When `gate_state` transitions to `"timeout"` or `"stopped"`, update `questions` with `status: "timed_out"` or `"cancelled"`.

---

## 5. Implementation Blueprint for Approach B: First-Class Deck Rendering (Recommended)

The superior approach directly achieves Bryan's goal—**immediate visibility of questions, recommended choices, answers, and provenance in the main deck**—without polluting the output variable namespace or duplicating state.

### 5.1 Where to Integrate in the TUI

There are two natural locations in the prompt panel deck:

#### Option 1: Dedicated Section in the Context Card Header (Above Output Variables)
- **Location:** `src/sase/ace/tui/widgets/prompt_panel/_agent_display_header.py`
- **Method:** Add `append_agent_questions_section(header_text, agent, ...)` immediately preceding `append_agent_output_variables_section()`.
- **Behavior:**
  1. Inspects `agent` and its session members for any `kind == "question"` gate turns.
  2. If found, reads `request.json` and `response.json` (or calls `question_rounds()`).
  3. Renders a dedicated header: `QUESTIONS & ANSWERS`.

#### Option 2: Enhanced Gate Phase in the Reply Card (Most Natural Flow)
- **Location:** `src/sase/ace/tui/widgets/prompt_panel/_agent_gate_section.py:build_gate_phase()`
- **Behavior:**
  Currently, `build_gate_phase` handles all gates generically and dumps raw `Option JSON: [...]`.  
  When `agent.gate_kind == "question"`:
  - Replace the generic raw JSON dump with a styled Q&A block.
  - While pending, render the questions, options, and recommended answers.
  - While answered, render the selected options, reviewer feedback, and resolution source.

### 5.2 Visual Design & Rich Formatting

Instead of YAML lines, the user sees a crisp, human-engineered block in the deck:

```
────────────────────────────────────────────────────────────────────────
QUESTIONS & ANSWERS · Round 1 [ANSWERED via TUI modal]
────────────────────────────────────────────────────────────────────────
Q1: Database Engine Selection
  > Which database engine should we adopt for the new storage tier?

  [x] PostgreSQL — Relational, mature, robust JSONB support [RECOMMENDED]
  [ ] SQLite — Embedded, zero-configuration
  [ ] Other

  Reviewer Note: "Approved for PG 16+. Do not use SQLite for this tier."
  Answered by: human via TUI modal · 2026-10-24 18:02:15 EDT
────────────────────────────────────────────────────────────────────────
```

And when still pending:

```
────────────────────────────────────────────────────────────────────────
QUESTIONS & ANSWERS · Round 1 [PENDING USER INPUT · 12m left]
────────────────────────────────────────────────────────────────────────
Q1: Database Engine Selection
  > Which database engine should we adopt for the new storage tier?

  [ ] PostgreSQL — Relational, mature, robust JSONB support [RECOMMENDED]
  [ ] SQLite — Embedded, zero-configuration
  [ ] Other
────────────────────────────────────────────────────────────────────────
```

### 5.3 Implementation Details
1. **Helper Function (`src/sase/question_gate_turn/display.py`):**
   ```python
   def format_question_deck_text(bundle_path: Path | str) -> Text:
       """Render rich deck lines directly from request.json and response.json."""
       request = _read_bundle_json(bundle_path, "request.json")
       response = _read_bundle_json(bundle_path, "response.json")
       # Parse questions, options, recommended answer (options[0])
       # If response exists, extract selected, feedback, source, caller, timestamp
       # Return styled Rich Text
   ```
2. **Hooking into the Deck:**
   In `_agent_display_header.py` (or `_agent_gate_section.py`):
   ```python
   if agent.gate_kind == "question" and agent.gate_bundle_path:
       text.append_text(format_question_deck_text(agent.gate_bundle_path))
   ```

### 5.4 Why Approach B is Unconditionally Superior
1. **Immediate Retroactive Compatibility:** Works for every session that has ever run in SASE history. You immediately gain visibility into all past question sessions without running any data migration scripts.
2. **Zero Invalidation / Synchronization Bugs:** Because it reads directly from `request.json` and `response.json`, it can never get out of sync with the true gate state.
3. **Pristine Downstream Contexts:** Downstream agents and macro swarms do not have their Jinja context windows polluted with verbose question structures.
4. **Rich Styling:** Native support for checkboxes, colored badges, italicized reviewer notes, and markdown quote blocks that look beautiful in the Textual TUI.

---

## 6. Adjustments to Requirements

Based on this research, the following refinements to the original requirements are recommended:

1. **Clarify the Core Requirement (Visibility vs. Variable Storage):**  
   The user's stated goal is: *"to make it so when the user selects an agent session on the 'Agents' tab... those questions, their recommended answers, their actual answers... and how the questions were answered... are all immediately visible (since variables are rendered in the main deck)."*  
   *Adjustment:* Decouple the **goal** (immediate visibility in the main deck) from the **assumed mechanism** (`sase var`). The requirement should be framed as: **"Display full Q&A status prominently in the main deck for question sessions"**, allowing the UI to render from canonical gate storage rather than forcing data into `sase var`.

2. **Formalize Recommended Answer Semantics:**  
   The SASE question skill documentation already dictates: *"Put your recommended option first in every question's options list"*.  
   *Adjustment:* Explicitly codify that `options[0]` is treated as the recommended choice across both UI rendering and any variable models, adding a distinct `[RECOMMENDED]` visual cue.

3. **Capture Complete Resolution Provenance ("How Answered"):**  
   The requirement to show "how the questions were answered" must capture two distinct dimensions:
   - **Resolution Surface (`source`):** `"tui"` (TUI modal), `"telegram"`, `"mobile"`, `"cli"` (`sase gate answer`), or `"auto"` (`%auto` policy).
   - **Caller Identity (`caller`):** `"human"` vs. `"agent"`.  
   *Adjustment:* Both fields are already recorded in `response.json` by `executor.py` and should be formatted into a human-readable provenance line (e.g., `Answered by human via Telegram` or `Auto-resolved via %auto`).

4. **Multi-Question & Multi-Round Handling:**  
   A single session can ask multiple questions at once, and can even execute `/sase_questions` across multiple consecutive rounds.  
   *Adjustment:* The deck view must cleanly enumerate questions as `Q1`, `Q2`, etc., and handle multiple rounds sequentially without visual clutter.

---

## 7. Recommended Solution & Action Plan

### Recommended Verdict
Do **not** use `sase var` as the mechanism for displaying Q&A in the main deck. Instead:
1. **Primary Solution (The Right Architecture):** Implement a dedicated **Questions Section in the TUI Main Deck** that reads directly from the canonical gate bundle (`request.json` and `response.json`).
2. **Secondary / Complementary (Only If Programmatic Access is Needed):** If CLI users or downstream tools specifically need `sase var get questions`, implement the clean schema described in Section 4 on the **Gate Turn Member** at gate creation and settlement time.

### Implementation Roadmap (Primary Solution)

1. **Step 1: Create Deck Q&A Formatter (`src/sase/question_gate_turn/deck_render.py`)**  
   Create a focused formatting module that takes a gate bundle path, reads `request.json` and `response.json`, and returns a styled `rich.text.Text` object containing questions, options, recommendations, answers, and provenance.

2. **Step 2: Mount in Main Deck (`src/sase/ace/tui/widgets/prompt_panel/_agent_display_header.py`)**  
   In `_agent_display_header.py`, check if the session contains a question gate turn. If present, append the rendered Questions section to `header_text` (or render it directly inside `_agent_gate_section.py` for the gate turn phase).

3. **Step 3: Add Status and Provenance Badges**  
   Add clear visual indicators:
   - Pending: `[PENDING USER INPUT]` in yellow/amber with remaining countdown.
   - Answered: `[ANSWERED via TUI]` in green/cyan.
   - Auto-resolved: `[AUTO-ANSWERED (%auto)]` in purple/cyan.
   - Timed out / Cancelled: `[TIMED OUT]` / `[CANCELLED]` in red/dim.

4. **Step 4: Verify Across Surfaces**  
   Run VHS tests or launch the TUI on historical question sessions to verify that questions, recommended options, actual selections, and reviewer notes appear clearly and crisply.
