# Auto-setting SASE variables from `/sase_questions`: research (`__mus`)

Goal: when `/sase_questions` is used, automatically set sase variables so that
selecting the agent session on the Agents tab shows the questions, their
recommended answers, their actual answers (if any), and how they were answered —
via the deck's OUTPUT VARIABLES section.

## 1. How `sase questions` works today

Entry: `src/sase/main/questions_command_handler.py` (`handle_questions_command`).

1. Guards on `SASE_AGENT` / `SASE_ARTIFACTS_DIR`, parses and validates the
   questions JSON (`_validate_questions`: requires `question` string;
   `options[]` need only `label`; `header`/`description`/`multiSelect`
   optional).
2. Writes a `.sase_questions_pending` marker into `SASE_ARTIFACTS_DIR` and
   SIGTERMs the agent runner group. **If the CLI ever returns (output, error,
   or exit code), the turn did NOT end** — the handoff only happened if the
   process was killed (per the skill text).

Runner side: `handle_questions_marker` in
`src/sase/axe/run_agent_exec_questions.py`:

- Resolves the multi-round chain parent (`resolve_question_chain_parent`:
  in-process hint, else newest terminal question gate turn in the lane whose
  follow-up agent is the creator), rebuilds `prior_rounds` via
  `question_rounds()`.
- Calls `create_question_gate_turn()` (`src/sase/question_gate_turn/create.py`)
  with `producer={"agent", "artifacts_dir": <producer dir>, ...}`.
- Records durable link fields into the **producer's** `agent_meta.json` via
  `record_workflow_metadata` (`src/sase/axe/run_agent_exec_plan.py`): the
  retained set already includes `questions_submitted_at`,
  `question_request_path`, `question_response_path`,
  `question_gate_artifacts_dir`, `question_session_id`. **So a durable
  producer → question-chain link already exists in metadata.**
- Either hands off to the gate (`handle_gate_marker`) or, on the `%auto`
  short-circuit, continues in-process with merged Q&A in the follow-up prompt.

Settlement: `execute_user_question_response` in
`src/sase/user_question_actions.py` normalizes the answer, settles the gate
turn (`answered`), and runs `_run_question_side_effects`. The settle-time
prompt rebuild hook is `question_next_action`
(`src/sase/question_gate_turn/followup.py`), which rebuilds merged Q&A across
**every round in the chain** — the only place that already handles multi-round
merge correctly.

## 2. Where the four requested data items live (source of truth)

All canonical Q&A data already lives in each round's **gate-turn bundle**,
not in the producer's artifacts dir:

| Item | Location | Notes |
|---|---|---|
| Questions (+ options, headers, multiSelect) | `request.json → payload.questions` in the gate bundle; normalized by `validate_user_questions` | Survives verbatim |
| Recommended answers | **Nowhere as data.** Pure convention from the skill: "Put your recommended option first". Recommended = `options[0]` per question, by convention only | Must be derived positionally and labelled as such |
| Actual answers | `response.json → option_results[submit].result` = `{answers[], global_note}` plus top-level `feedback`; aligned to questions by `build_qa_round` (`src/sase/main/qa_prompt.py`) | Missing entirely for timeout / cancelled / failed rounds — `question_rounds()` (`src/sase/question_gate_turn/rounds.py`) skips those rounds silently |
| How answered | A `source` string is threaded through `execute_gate_selection(..., source=...)` (`src/sase/notification_gates/executor.py`, `response_source`) and persisted with the response; submitters are the TUI question modal, mobile actions (`src/sase/integrations/_mobile_notification_actions.py`), Telegram, or `%auto` | Channel is recorded at the gate bundle, not the producer |

Rebuilding the full picture for N rounds is already implemented:
`question_rounds(head_dir)` walks `question_prev_artifacts_dir` links (cap 200),
and `build_merged_qa_markdown(rounds)` (`src/sase/main/qa_markdown.py`) renders
one `### Questions and Answers` section with monotonic Q-numbers and
`[x]`-checked options — shared by the TUI modal and follow-up prompts so they
cannot drift.

## 3. How deck OUTPUT VARIABLES rendering works

- Storage: `output_variables` map inside each run's `agent_meta.json`
  (`src/sase/core/agent_output_variables.py`;
  `set_agent_output_variables` / `update_agent_output_variable` do locked
  merges). Readable anywhere via `sase var get`.
- Deck rendering: `append_agent_output_variables_section`
  (`src/sase/ace/tui/widgets/prompt_panel/_agent_output_variables.py`) renders
  an OUTPUT VARIABLES section in the main deck panel for the selected session,
  with contributors = selected agent **plus its follow-up agents**.
- Hard limits (`src/sase/core/output_variable_values.py`): **256 variables**,
  **8 KiB per string leaf / map key**, depth 8, 1024 nodes, and (per the
  `sase_var` skill) 64 KiB encoded JSON per variable. Variables are also shown
  in the Telegram completion message — **never store secrets; question text
  would now fan out to Telegram**.
- The deck already has a separate GATE section (`_agent_gate_section.py`:
  decision, kind, status/state, branches, reviewer note, option JSON), but it
  renders for the **gate-turn row**, not for the producer agent session the
  user selects. That is the actual visibility gap: the producer session's deck
  shows nothing about its question gate(s).

## 4. Critique of the plan as stated

**The goal is sound; snapshotting full Q&A text into variables is not.**

1. **Duplication with a live source of truth.** Gate bundles already hold
   everything. A variable snapshot goes stale at exactly the interesting
   moment: set at ask-time it says "unanswered" until a second,
   settlement-time write updates it. Every missed update path (timeout,
   cancelled, failed, `%auto` in-process continuation, legacy in-flight
   fallback in `execute_user_question_response`) leaves a wrong "pending"
   snapshot in the deck.
2. **Size limits will bite.** A few questions with descriptions, custom
   feedback, or 2+ rounds easily exceed the 8 KiB leaf / 64 KiB variable
   budget, forcing lossy truncation of the very content the user wants to
   read. The gate-bundle path has no such limits.
3. **Namespace and quota pressure.** Variables share one flat 256-key map
   with the agent's own handoff values. Auto-written keys must be namespaced
   (e.g. `sase_questions`) and ideally a single key, or agents' legitimate
   variables get crowded out / collided with.
4. **"Recommended" is convention, not data.** Deriving `options[0]` as
   recommended is correct today but fragile: any agent that orders options
   differently silently mislabels. At minimum the snapshot must record that
   provenance ("first-listed = recommended by skill convention").
5. **Two writes in two processes.** Ask-time write is easy (CLI runs with
   `SASE_ARTIFACTS_DIR` set — `sase var set` works pre-handoff). Answer-time
   update must write into the *producer's* artifacts dir from settlement
   context (a different process/store); the producer run is DONE by then, so
   this is a cross-run write needing the explicit dir (available as
   `producer.artifacts_dir` in the gate request envelope) and the locked
   updater. More machinery, more failure modes.
6. **Privacy fan-out.** Producer `output_variables` surface in the Telegram
   completion message. Full question/answer text would now leave the TUI.

## 5. Options considered

- **A. Full Q&A snapshot variables** (ask-time set + settle-time update).
  Satisfies the letter of the request; pays every cost in §4.
- **B. Deck-native Q&A section (no new variables).** When the selected
  session's meta contains `question_gate_artifacts_dir` (already written
  today), the deck resolves the chain head and renders merged Q&A via the
  existing `question_rounds()` + `build_merged_qa_markdown()` — the same
  renderer the modal uses. Always fresh, no size limits, timeout/cancelled
  rounds handled uniformly (shown as unanswered), zero duplication, works for
  all historical sessions retroactively. Cost: TUI-only; doesn't help `sase
  var get` / Telegram consumers.
- **C. Pointer/status variable + deck dereference (hybrid).** Auto-set one
  small namespaced variable (e.g. `sase_questions` =
  `{"session_id","status":"pending|answered|timed_out|...","rounds":n}`,
  well under limits) at ask time, update `status` at settle time; the deck
  renders the full Q&A by dereferencing the already-stored
  `question_gate_artifacts_dir` link. Small write, no truncation, still
  "variables set automatically", and `sase var get` users get status.

## 6. Adjusted requirements

1. Require **one namespaced key** (`sase_questions`), never per-question keys.
2. Record recommended answers as derived-from-position with provenance noted,
   not as authoritative data.
3. The settle-time update must cover **all terminal states** (answered,
   timed out, cancelled, failed), not just answers — otherwise the deck lies.
4. Multi-round chains must be merged with `question_rounds()`, not by
   appending per-round variables.
5. Truncation policy is mandatory if any free text goes into a variable
   (8 KiB leaf / 64 KiB variable caps); prefer counts + links over full text.
6. Never write secrets; note the Telegram fan-out in the implementation.

## 7. Recommended solution

**Implement B (deck-native merged-Q&A section sourced from gate bundles),
plus the status half of C if cross-surface visibility is wanted.**

Concretely:

1. **TUI (core fix):** in the deck's agent-session render path (alongside
   `append_agent_output_variables_section` in `_agent_display_header.py`),
   add a QUESTIONS section: if the selected session's meta has
   `question_gate_artifacts_dir`, call `question_rounds()` and render with
   `build_merged_qa_markdown()`. Show per-round status (pending / answered /
   timed-out / cancelled) and, per question, the first-listed option tagged
   "recommended (first-listed convention)", the selected option(s), and the
   response `source` channel as "answered via …". This closes the stated gap
   for all sessions — past and future — with no agent-side writes at all.
2. **Variable (small, optional but responsive to the request):** set a single
   `sase_questions` status variable — ask-time in `handle_questions_marker`
   (`src/sase/axe/run_agent_exec_questions.py`, which has both the producer
   dir and the chain parent, unlike the bare CLI handler), status update at
   settle time in `question_next_action` (`src/sase/question_gate_turn/followup.py`,
   which already sees every round + the response) or in the gate-settlement
   callbacks, writing to `producer.artifacts_dir` from the gate envelope via
   the locked updater. Keep it to status/round-count/session-id — never the
   full Q&A text.
3. **Do not** snapshot full question/answer text into output variables (pays
   §4 costs for no benefit once (1) exists).

Hooks chosen because: `handle_questions_marker` is the first point with
producer dir + chain context (the `sase questions` CLI itself is a thin
marker writer and knows nothing of rounds); `question_next_action` is the
only existing code that already merges all rounds at settle time. Both need
branch-aware handling so non-`submit` outcomes update status rather than
leaving "pending" behind — verify whether `question_next_action` runs for
timeout/stopped/failed branches before relying on it alone.
