**Questions in the Agents Main deck: canonical history, answer provenance, and automatic variables**

Independent research by cdx, 2026-10-24.

The user-facing idea is good: selecting a session should reveal the decisions that shaped its work without opening a notification, hunting through a transcript, or guessing whether an agent followed a recommendation. I would implement that visibility. I would change the proposed mechanism: make Questions a first-class, read-only section of the Main deck, derived from the existing question gates. Treat automatic variables as an optional export of that model, not the primary record or the sole UI.

This report independently inspected the local sase checkout at **5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f** and its pinned sase-core checkout at **7ec12d2d7ad8e670abe26aa396259a512f330391**. No peer reports, peer transcripts, or peer findings were consulted. Findings below distinguish current behavior from proposed changes. No implementation files were changed.

**What exists today**

A question round already has a durable record. The generated skill tells the agent to put its recommended option first, then invoke the questions command. The command validates the submitted JSON, writes a handoff marker, and terminates the agent runner's process group. The host adopts that marker and creates a question gate turn. Therefore, there is no reliable “after asking, update the variables” step inside the asking agent: that agent has finished. The gate and later host processes own the answer lifecycle. [1][2]

The request payload stores the questions, option labels and descriptions, headers, and multi-select flags. The host records the request and response paths on the interrupted turn and creates a separate session member for the gate. Gate metadata also carries the gate ID, creator, session lane, bundle path, and lifecycle state. Question-specific metadata links consecutive rounds through the preceding gate's artifacts directory. These existing identities are sufficient to associate a question with its session; a new question database is unnecessary. [2][3]

A normal submitted response has the actual answers under the submit entry in **option_results**, with each answer retaining **selected** labels and **custom_feedback**. The envelope separately records **source**, **caller**, **responded_at_unix**, and **feedback**. The complete form also has **global_note**. Source is a self-reported transport string; caller is independently classified as human or agent by the submitting process. Neither field identifies a named individual. Preserve these distinctions in the new view. [4]

Recommendations are currently a convention, not a structured question field. “Put your recommended option first” appears in the skill. The question schema has no explicit recommended choice or recommended subset. A first-option policy helper exists, but **all current built-in autonomy profiles wait for human answers to questions**. It would be incorrect to label every question from an agent using an automatic profile as automatically answered. The actual response and recorded gate policy provide the evidence. [1][5]

Output variables are JSON-shaped values in a turn's agent metadata. Writes use a lock-protected metadata merge, atomic replacement, and an artifact-index refresh. The Main deck's Context rendering already includes an OUTPUT VARIABLES section. That makes variables attractive for a small initial change, and the managed artifacts variable provides a precedent for host-published output. [6][7]

There are limits to that shortcut:

- The existing variable contributor collector walks the selected row and its direct followup_agents. It does not implement the complete session traversal that includes nested runtime children. The session-turn projector already handles those overlapping links, causal ordering, and deduplication. Simply setting a variable on a gate does not establish that every selected session shape will display it. [7][8]
- Variables render as alphabetically sorted, YAML-shaped maps and lists. A large question structure includes much operational data and can dominate the Context card. Session folding can collapse the variable section, and a paged Main deck can retain the Reply card as its current page. “Stored as a variable” is not equivalent to “immediately visible.” [7][9]
- Variables are shared beyond this UI. They feed historical selectors, agent template context, and completion notifications. Automatically adding all human answer text changes those surfaces too. This is a concrete consequence of the storage choice, not a reason to block the feature. [10]
- Each variable has an 8 KiB limit per string leaf, 64 KiB encoded size, depth 8, and 1,024 total nodes; there are at most 256 variables. Question validation does not impose the same caps. Thus, valid questions cannot always be represented losslessly as output variables. [6]

**Requirements I would adjust explicitly**

| Proposed interpretation | Recommended requirement | Reason |
| --- | --- | --- |
| Whenever the skill is used | Whenever the host successfully creates a question request, whether invoked through the skill or directly through its supported CLI | Skill-use telemetry does not prove that valid questions were created; direct callers need the same behavior. |
| Automatically set variables | Automatically expose a canonical question projection in Main; add a bounded variable export only if machine consumers also need it | Solves the stated visibility problem without making a second mutable answer store. |
| Any questions answered so far | Show every submitted round and its durable answers; do not treat unsubmitted form edits as answers | The current gate submits one complete, validated form atomically. A session can contain answered older rounds and a pending latest round. Per-question draft persistence would be a separate feature. |
| Recommended answers | Show the first option as “recommended by option order”; show “no recommendation recorded” for free-text-only questions | No explicit recommendation field exists. For multi-select, the first option is one recommended choice, not evidence of a recommended combination. |
| How answered | Show transport, actor class, recorded time, and answer form; show automatic-policy provenance when available | “TUI” and “automatic” describe different dimensions. Matching the recommended answer does not prove automatic selection. |
| Immediately visible | In Main, show an expanded summary for the pending/latest round after selection and refresh, without a modal; retain older rounds under existing fold/navigation controls | An unbounded history cannot all fit on a screen. Do not steal focus or override a deliberately selected deck/page on every refresh. |
| Only successful answers matter | Also distinguish cancelled, timed out, failed, unavailable, and submitted-but-still-settling states | A request with no answer is not always awaiting input. An accepted answer remains an answer even if successor launch fails. |

The first version should keep the existing complete-form submission semantics. Adding partial submissions requires decisions about drafts, concurrent edits across transports, validation, and when continuation becomes permissible. That is substantially larger than improving visibility.

An explicit optional recommendation field could later support several recommended choices or an explicit “none.” It is not necessary for the initial view. If added, validate it centrally and preserve a clear fallback for older requests; do not infer recommendation status by parsing words such as “Recommended” from labels.

**Approaches compared**

| Approach | Strength | Main cost or defect | Assessment |
| --- | --- | --- | --- |
| Add “set variables” instructions to the skill | Very little code | Depends on model compliance, cannot reliably publish later answers, misses direct callers and failure/recovery paths | Reject |
| Host maintains full question variables; existing variable UI displays them | Reuses storage, indexing, and rendering | Duplicate data, bounds, collisions, session traversal gaps, weak readability, broader publication | Viable constrained version, not preferred |
| Main reads raw gate files directly during rendering | No duplicate store | Blocking I/O, duplicated parsing, inconsistent provenance and state interpretation | Reject |
| Shared typed projection, loaded off-thread, rendered as Questions in Main | Reuses authoritative records, supports complete history and purposeful display | Requires a small core API, loader integration, and UI work | Recommended |
| Shared projection plus optional managed variable export | Adds programmatic selectors without another semantic model | Still needs an export contract, boundedness, and publication rules | Add when there is a concrete consumer |

The recommended design follows a conventional read-model pattern: a view is derived from authoritative data and can be rebuilt. Microsoft's Materialized View guidance specifically distinguishes such projections from authoritative storage and discusses stale refreshes and atomic publication. The application here is modest: use the existing gate bundles and existing detail-loading machinery, not a new event bus or a separate CQRS subsystem. [11]

**A small shared model**

Add a typed question-round projection in sase-core and expose it through sase_core_rs. Shared parsing, recommendation derivation, answer matching, and provenance semantics belong there under the project's Rust backend boundary. Python should adapt I/O and render Textual/Rich content.

The following is an illustrative new wire shape, not a claim about an existing API:

~~~json
{
  "schema_version": 1,
  "gate_id": "question-request-id",
  "creator_turn": "example--0",
  "gate_turn": "example--gate",
  "round_number": 1,
  "gate_state": "answered",
  "answer_state": "answered",
  "data_state": "complete",
  "questions": [
    {
      "index": 0,
      "header": "Storage",
      "text": "Which storage engine should this use?",
      "options": [
        {"label": "SQLite", "description": "Embedded deployment"},
        {"label": "PostgreSQL", "description": "Shared server"}
      ],
      "multi_select": false,
      "recommended_indices": [0],
      "recommendation_basis": "option_order",
      "answer": {
        "selected_labels": ["PostgreSQL"],
        "custom_feedback": "Several machines need concurrent access."
      }
    }
  ],
  "submission": {
    "source": "tui",
    "caller": "human",
    "responded_at_unix": 1792800000.0,
    "policy": null
  },
  "global_note": "Keep migration work small."
}
~~~

Use **gate ID plus question index** as the question identity. The current complete-form contract preserves index order and requires each answer's question text to match its corresponding question. Duplicate text across questions or rounds must not collapse distinct entries. Preserve option and selection order. A display number is not the stable identity.

Keep absent answers as null, rather than an empty string or the recommended answer. Preserve custom feedback both with and without selected options, including “Other,” multiple selections, and comments accompanying a standard choice. Preserve each round's global note; if top-level feedback takes precedence, retain that rule explicitly while keeping the underlying records available. Do not flatten all rounds into one mutable “latest answer.”

Distinguish **answer state** from **gate execution/follow-up state**. The durable response can exist before gate settlement and continuation finish. Conversely, acceptance or an in-progress attempt is not necessarily a successful terminal answer. If showing accepted input before terminal completion becomes desirable, label it “submitted, processing” and keep it separate from a committed answer.

Retain unknown provenance as unknown. Render a stored unknown transport literally or as “other,” rather than converting it to manual. Automatic resolution should be derived from the resolution path and its policy evidence; its caller can still be agent. For human TUI answers, wording such as “Human · TUI · 14:32” is sufficient. No identity lookup is needed.

For historical records, support existing neutral gate envelopes and the legacy question_request/question_response layout through one normalizer. A missing or malformed request must not make an answered record look pending, and a missing response must not be invented from the successor's prompt. Surface “details unavailable” and keep whatever verified facts remain.

**Presentation and session ownership**

Keep the gate as the logical owner of each round. The asking turn points to that gate; the session aggregates its question gates. Do not copy the entire accumulated history into every successor, every creator, and a session container.

For the session view, reuse the existing concrete session-turn traversal to find question gates, then deduplicate by gate identity. For a concrete asking turn, show its linked round. For a gate row, show that gate's round. A successor should not acquire falsely attributed ownership merely because its prompt contains earlier Q&A. Repeated questions and inherited plan/code phases should retain their separate round identities.

A compact Main Context section could read:

~~~text
QUESTIONS · 2 rounds · 1 awaiting
Round 2 · asked by example--1
Q3  Which storage engine should this use?
    Recommended: SQLite
    Answer: Awaiting submission

Earlier: Round 1 · 2 answered · Human via TUI
~~~

After submission, replace the awaiting line with the selected answer and custom text, followed by provenance and time. Expand the pending/latest round initially; make full option descriptions and older rounds accessible through the deck's existing fold/navigation patterns. For large histories, present explicit counts and continuation controls rather than silently dropping content. A small summary can remain visible when details are folded. Do not introduce a new deck solely for questions: that would make the intended discovery harder.

The frontend should render an already-loaded model. Use the existing asynchronous detail enrichment, cache, and selection-generation checks. Revalidate the relevant request, response, cancellation, and gate-state signatures off-thread; remember that an absent response becoming present must invalidate a cached pending view. Automatic resolution currently enriches response policy after initial response publication, so a cache must also notice replacement of an existing response. [5]

Use the existing refresh pulse and incremental reload path. Never scan every historical question bundle on each selection, parse JSON on the render path, or let a late worker overwrite the newly selected session. A loaded, partial session history should be marked partial until reconciliation completes. Measure selection and refresh behavior against the repository's existing TUI performance expectations; no latency measurements were made in this research.

**Why existing question helpers cannot simply become the new UI**

The round reconstruction helper is useful evidence of ownership and response shape, but it intentionally ignores rounds without a submit result. Pending, cancelled, and timed-out questions therefore disappear from that function's output. It is tailored to building continuation prompts, not to displaying the question lifecycle. [3]

The notification summary offers a useful presentation precedent, but its model has no recommendation or response-provenance fields. Its response loader checks a top-level result object, whereas current question turns decode the submit entry inside option_results. Do not route the new view through that helper unchanged; normalize the current envelope explicitly and test its legacy compatibility. [3][12]

The merged Q&A Markdown renderer flattens round boundaries and retains only the most recent nonempty global note. A synthetic probe also found that it omits a valid free-text-only answer. That makes it unsuitable as the sole source for this richer history display. Reuse formatting ideas only after enforcing the new projection's content-preservation contract. [13]

These are implementation constraints directly relevant to the proposed feature, not a recommendation to refactor every question subsystem before shipping it.

**If automatic variables remain a hard requirement**

Use the same core projection to maintain **one host-managed variable per gate round**, for example **sase_questions**, on the gate member. The name is a proposal and needs a collision policy. Do not silently overwrite an existing user value with an incompatible shape. Document the managed name and prevent ordinary variable writes from corrupting it once adopted.

Publish at durable question creation, after response publication and policy enrichment, and on cancellation/timeout/failure settlement. The automatic path can answer during creation, so inspect actual persisted state instead of unconditionally writing “pending” after the creation call returns. Neither a TUI-only callback nor a continuation-launch hook covers all these cases.

Use the existing metadata merge/indexing mechanism, but account for settlement's own whole-metadata writes and locks. Updating through a separate lock and subsequently replacing metadata from an older in-memory snapshot can lose the new value. Integrate publication into an owning transaction or establish one consistent update protocol for the affected writers; do not add ad hoc writes to agent_meta.json.

Make publication idempotent by gate ID and source revision/fingerprint. A crash after response publication but before export must be repairable from the gate bundle. Reconcile on relevant loading/recovery paths; do not rerun a question command or launch another successor just to repair display data. An export failure must not turn a durably accepted answer into a reported answer failure.

Bound the export. Prefer one round over an ever-growing session-wide list, but even a single valid question can exceed the variable caps. On overflow, publish explicit truncation/availability metadata and a gate identifier or existing show command, while the Questions view loads the full canonical record. Never increase global variable limits merely to make this feature fit, silently discard answers, or reject a valid question because a display export is too large.

Fix session contributor traversal if the generic variable section is used, and avoid showing the same round twice when both a specialized section and the export are present. Also decide explicitly whether this managed value belongs in completion notifications and template context. Full human answer text should not be copied into every completion notification by accident.

This version is defensible, especially if the user also wants to query question answers through variable selectors. It is not the smallest implementation once correctness, boundedness, refresh, and readable presentation are included. Its strongest justification is programmatic reuse, not merely that variables already happen to render in Main.

**Implementation sequence and acceptance checks**

1. **Define and test the core projection.** Normalize request/response layouts, preserve the complete answer text, derive first-option recommendation provenance, and separate data availability from lifecycle state. Expose a typed binding and move sase's core revision pin to a commit containing it. This is a focused addition, not a migration of the entire question engine.
2. **Attach it to selected-session detail loading.** Use gate IDs and established turn relationships. Reuse bounded background loading and refresh machinery; include nested gate members, deduplication, cancellation, and missing historical files.
3. **Render Questions in Main Context.** Cover pending/latest visibility, answered history, provenance, folds, narrow terminals, and the concrete creator/gate/session selections. Update documented UI behavior where necessary.
4. **Add the managed variable export only if retained as a requirement.** Integrate creation, manual submission, automatic resolution, terminal settlement, and repair with the shared projector. No LLM-issued variable command is required.
5. **Update the generated skill source to explain the behavior.** The source is src/sase/macros/skills/sase_questions.md. Do not hand-edit deployed provider skills; deploy through the normal generated-skill workflow after landing. The skill should describe automatic visibility and recommendation ordering, not acquire another bookkeeping responsibility.

Useful acceptance scenarios are:

- Two questions pending; then one complete submission with a normal choice, custom text, and a global note.
- A previous answered round followed by a new pending round, shown from the session container, the asking turn, and the gate row.
- Duplicate question texts, multi-select answers, “Other,” and free text without options.
- Human TUI/mobile/CLI submissions and recorded agent or automatic answers; recommendation matches never imply automatic provenance. Telegram should be verified through its adapter in implementation; its linked repository was not opened in this research.
- A durable answer followed by failed successor launch; cancellation and timeout without answers; malformed or missing legacy files.
- A response arriving while the session remains selected; rapid selection changes while detail loads; a policy update replacing an already-present response.
- Repeated settlement/recovery and a crash between source write and optional variable update.
- Long question/answer strings, variable budget overflow, existing variable-name collisions, and no loss of unrelated metadata.
- Session projections containing overlapping follow-up/runtime links: one question round appears once, in causal order.

Use core unit/binding tests for semantic behavior, focused integration tests for gate lifecycle and repair, and TUI rendering/visual tests for the resulting section. Run the repositories' required verification through their normal guarded tooling during implementation. This research did not run full verification because it made no implementation changes.

**Verification performed for this report**

Source inspection was supplemented with pure-function probes against the workspace's Python environment. The initial system-Python attempt could not import the repository's newer Python syntax; rerunning with the workspace virtual environment succeeded. The successful probes did not create gates, submit answers, or alter agent state.

| Probe | Observed result |
| --- | --- |
| Submit only one answer for a two-question form | UserQuestionActionError with code incomplete_question_form |
| Validate a question containing 9,000 ASCII characters | Question validator accepts it |
| Normalize that same question as an output variable | Rejected because its question string exceeds 8,192 UTF-8 bytes |
| Validate a free-text-only answer saying “Must run offline” | Accepted |
| Render that answer through build_qa_markdown | The answer text is absent |

The probes substantiate the batch-submission, variable-bound, and renderer-reuse concerns. They do not establish end-to-end transport behavior or UI latency.

**Source notes**

The following links point to the exact revisions inspected locally. File contents were read from the authorized checkouts, not fetched from GitHub.

[1] Skill convention and handoff:
[question skill source](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/macros/skills/sase_questions.md),
[questions CLI handler](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/main/questions_command_handler.py#L45).

[2] Host adoption and gate creation:
[runner question flow](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/axe/run_agent_exec_questions.py),
[question gate creation](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/question_gate_turn/create.py#L83),
[gate member metadata](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/gate_turn/member.py).

[3] Existing reconstruction and settlement:
[round-chain reader](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/question_gate_turn/rounds.py),
[gate settlement](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/gate_turn/settlement.py).

[4] Answers and provenance:
[complete-form schema and response normalization](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/user_question_actions.py#L315),
[executor response fields and caller classification](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/notification_gates/executor.py).

[5] Automatic resolution:
[core built-in profiles](https://github.com/sase-org/sase-core/blob/7ec12d2d7ad8e670abe26aa396259a512f330391/crates/sase_core/src/autonomy/profiles.rs),
[automatic first-option helper](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/user_question_actions.py#L433),
[creation and policy response enrichment](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/notification_gates/service_creation.py).

[6] Variable storage:
[merge API](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/core/agent_output_variables.py),
[metadata lock](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/core/agent_meta_update.py),
[value limits](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/core/output_variable_values.py),
[managed artifacts precedent](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/core/created_artifacts_variable.py).

[7] Main variable display:
[contributor selection and rendering](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/ace/tui/widgets/prompt_panel/_agent_output_variables.py),
[header placement and fold behavior](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/ace/tui/widgets/prompt_panel/_agent_display_header.py).

[8] Session membership:
[concrete session-turn traversal](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/ace/tui/models/agent_session_members.py#L368).

[9] Deck structure and variable format:
[Main source delivery](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/ace/tui/widgets/_agent_detail_deck_source.py),
[card parts](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/ace/tui/widgets/decks/card_part.py),
[variable formatter](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/core/output_variable_display.py).

[10] Other consumers:
[agent variable context](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/agent/output_variable_context.py),
[completion notification variable publication](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/axe/run_agent_runner_finalize.py),
[core variable-history index](https://github.com/sase-org/sase-core/blob/7ec12d2d7ad8e670abe26aa396259a512f330391/crates/sase_core/src/agent_scan/index/output_variables.rs).

[11] External architectural background:
[Microsoft Azure Architecture Center: Materialized View pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/materialized-view), consulted 2026-10-24. This is background for the cache-versus-authority distinction; the SASE design recommendations are the researcher's inference.

[12] Existing notification read model:
[question summary](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/notifications/question_summary.py),
[notification question rendering](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/ace/tui/modals/notification_modal_question.py).

[13] Existing prompt formatter:
[merged Q&A Markdown](https://github.com/sase-org/sase/blob/5e79f6405f263f48fffc2e9f9f59ca34fa2ce23f/src/sase/main/qa_markdown.py).

**Recommended solution**

Implement a Rust-owned question projection over the existing gate records, then show it as a Questions section in the Main Context card for the session, asking turn, and question gate. Preserve every round, distinguish recommendations from answers, display recorded answer provenance, and refresh through the established background-loading path. Ship this without requiring the agent to set any variables.

If variable access is also a desired product capability, add one bounded, host-managed per-gate export from that same projection, with collision handling and repair after interrupted publication. Keep the gate records authoritative and the specialized Questions section complete. This preserves the useful intent of the proposal while avoiding variable limits, duplicated histories, and model-dependent bookkeeping as foundations for the UI.
