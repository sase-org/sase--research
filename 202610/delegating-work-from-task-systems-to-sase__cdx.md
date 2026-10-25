# From personal tasks to delegated work: a task-system agnostic integration for SASE

Independent research by **cdx** · 2026-10-25

## Recommendation

**Yes: this is a promising direction, provided the integration preserves human ownership of commitments and treats an agent result as a reviewable claim.** The valuable feature is the complete loop: capture intent where you already think, authorize a bounded piece of work, run the appropriate workflow, return evidence to the originating context, and decide whether the outcome satisfies the commitment.

Start with two explicit opt-in workflows: a tagged task produces a result for review, and a tagged reading question produces a cited answer in its reference note. Add unsolicited clarification proposals after those loops are reliable. Build one Bob adapter behind a small provider contract, then test it against a materially different provider before calling the design general.

The main risk is **creating work for your attention faster than agents remove it**. Duplicate launches, stale answers, ambiguous completion, and excessive proposals could turn an apparently productive system into another inbox. Measure accepted outcomes and human time saved, not agents launched or tasks annotated.

This recommendation is an inference from repository inspection, existing product patterns, and interaction research. I did not run an integration prototype or measure your actual delegation success rate. I did not read another member of this research swarm's report, findings, or conversation.

## 1. Why the connection is deeper than a trigger

A personal task is often an intentionally incomplete commitment: “investigate this,” “decide whether this is worthwhile,” or “fix the thing I already understand from context.” An agent needs accessible inputs, a bounded objective, an authorized action set, and a way to assess its output. The integration must bridge those representations without requiring every captured thought to become a specification.

| Layer | Question it answers | Appropriate authority |
| --- | --- | --- |
| Personal task system | What matters, where does it belong, and what have I committed to? | Human, using native task conventions |
| Delegation record | What particular work is authorized against which version of that commitment? | Host policy plus a human action or standing authorization |
| SASE execution | Which agent/workflow should do it, what happened, and what evidence resulted? | SASE orchestration and host completion mechanisms |

A task can have several delegations: research, decide, implement, verify, revise. A delegation can require several turns or a swarm. A run can fail while the task remains valid. A successful run can establish that the task should be changed or abandoned.

The interesting expansion is from **doing tasks** to **advancing commitments**. Agents can reduce uncertainty, prepare a decision, assemble a work packet, explain a blocker, or verify an outcome even when they cannot complete the human's task. Physical errands, interpersonal conversations, and judgment-heavy choices can receive assistance without autonomous completion.

Mixed-initiative interaction research offers a useful precedent: account for uncertainty about intent, interruption costs, easy invocation and termination, and the value of a narrower useful action when intent is uncertain. This supports a spectrum from explicit execution to proposed clarification, rather than a confidence threshold that silently grants authority. [Horvitz, *Principles of Mixed-Initiative User Interfaces*][horvitz]

## 2. What the existing repositories already provide

The following are observed capabilities or contracts, not proposed features.

### Bob already has a strong semantic boundary

- **Six checkbox lanes with independent planning dimensions.** `[ ]` is Ready, `[*]` Next, `[/]` Pending/In Progress, `[?]` derived Blocked, `[x]` Done, and `[-]` Cancelled. Today, freshness, and review tiers are separate. Next and Pending are sticky; Blocked follows prerequisites, schedules, and project blocking. The checkbox cannot be the integration's entire execution state machine. [Bob task lanes][b-lanes]
- **Identity is better than a line number, but is not a universal delegation identity.** Tasks can have note-scoped block IDs. Picker references contain a line and digest; the resolver can recover a moved line by a unique digest and refuses stale/ambiguous matches. The digest covers the physical task line, not all requirements in child bullets. `capture-task-id` assigns a block ID through a checked command. [Task identity implementation][b-identity]; [ID assignment implementation][b-id-write]
- **Structured reads and useful write primitives exist.** `bob capture-targets`, `capture-tasks`, and related commands expose discovery. `bob capture '@route+block-id' ...` appends child content beneath a task, respecting structure and managed logs. This enables an evidence-return experiment, but does not itself supply crash-safe idempotent evidence upserts or an atomic “publish result and change lane” operation. [Capture contract][b-capture]
- **Bob already serves multiple frontends.** Bob Mac Capture delegates grammar, preview, completion, and vault mutation to versioned Bob interfaces. A SASE adapter should follow that boundary instead of reinterpreting task syntax in Python or an Obsidian-only implementation. [Mac Capture README][b-mac]

### The reference pipeline is unusually relevant

`bob ref show -f json` exposes separate quote/comment fields, page labels, block links, images, continuation pieces, section membership, own notes, and extracted tasks. This is better input for a reading assistant than grepping Markdown. [Reference query contract][b-ref]

Highlights synchronization already extracts explicit `#task` bullets from annotation comments. It attaches a backlink and processed identity `[h:: ...]`, recognizes moved/archived tasks, and preserves task status on later imports. This is a local precedent for **annotation → durable actionable item**. Its import marker is not an execution/authorization ledger. [Annotation task extraction][b-highlights]

Two details are especially consequential:

1. Editing a text-highlight comment generally preserves its `^h-...` ID: the comment is excluded from that identity hash. Editing highlighted text can mint a new ID; removed annotations can leave tombstones. A question identity therefore needs the annotation identity **and a revision of the question text**.
2. `#q` may be an alias for a section such as `# Open questions @q`. Matching tags are consumed during import, while structured section information remains. A watcher searching only rendered literal `#q` will miss valid questions. [Annotation identity and section contracts][b-highlights]

The region between `<!-- highlights:begin -->` and `<!-- highlights:end -->` can be rewritten during sync. Authored text outside it is preserved. Writing answers directly into generated comments is unsafe under the current contract. [Managed Highlights body contract][b-highlights]

### SASE has much of the execution machinery

Scheduled script jobs can produce structured launch proposals carrying workspace, model/effort, dependency, and deduplication information. Typed admission records launch progress durably; agent-originated launch requests use LaunchApproval. These are strong building blocks, but do not solve source identity, semantic changes, or evidence delivery. [Scheduler jobs][s-jobs]; [Launch architecture][s-architecture]

SASE also has an external issue mirror: it imports tracker issues into task beads using `external_ref`, bounds writes, conservatively handles upstream changes, and reconciles rare cross-machine duplicates. Reuse that experience without automatically mirroring every personal task into a bead. Personal commitments, reading questions, and execution subtasks have different lifecycles. [External issue mirror][s-mirror]

The configured home integration already sends research into Bob through a `research-highlights` file hook invoking `bob ref create --include-id -P "$SASE_FILE_HOOK_PROJECT"`. It also exposes Bob Markdown as an artifact file root and contains prompts for reviewing Highlights annotations. Task-triggered work and reliable answer return would complete more of this existing loop. **Evidence:** chezmoi revision `ea37b90d9d263068cec68e96367621c4c3b50ac9`, `home/dot_config/sase/sase.yml`, lines 5–19, 135–136, and 385–387. Configuration was inspected; these workflows were not executed.

**Maturity caveat:** SASE's accepted “Goals Host Binds” decision requires one host-bound goal per LLM turn and human settlement. The inspected goal docs and Rust actions still describe a G1 ledger with later binding/claim producers. Treat the decision as an architectural constraint, not proof that all integration APIs are shipped. Validate the deployed binding path before implementation. [Goal binding decision][s-goal-decision]; [Goal docs][s-goals]; [Rust goal actions][core-goals]

## 3. The three proposed workflows, made concrete

### A. Explicitly delegated Obsidian task

1. You add a delegation marker, for example `#sase/ready`, inside a configured scope. This is illustrative syntax, independent of Bob's Ready lane.
2. The adapter resolves identity and gathers the task block, requirements, dependencies, project context, and approved references. It records the request revision.
3. The host checks scope, dependencies, budget, review backlog, and standing authorization. Eligible authorized work queues automatically, without another approval simply because a scheduler saw it later.
4. SASE runs the workflow and captures evidence: a patch with checks, a report with open questions, or another agreed deliverable.
5. After host completion is known, the adapter rereads the task. If relevant requirements still match, it publishes evidence and moves the task to `[/]` through Bob's supported semantics. If they changed, it marks the result stale or holds the mutation for review.
6. You accept, request revision, reject, or cancel. Agent completion alone does not resolve the personal commitment.

Keep queued/active progress in integration metadata. Your requested `[/]` transition can occur when evidence is ready, without redefining Pending everywhere. A child entry saying “SASE result ready for review” distinguishes it from ordinary in-progress work. Existing Pending review can surface it; a separate universal dashboard is unnecessary initially.

Do not invent human Pomodoro activity, mark the task fresh, change priority, or add it to Today because compute ran. Those actions have meaning in Bob. If blocking conditions change before publication, native reconciliation remains authoritative. [Bob lane semantics][b-lanes]

### B. An agent proposes clearer requirements and an execution mode

Separate **permission to examine a task scope** from **permission to execute a proposal**. A scheduled assistant can inspect an allowlisted project and propose clarification without silently opting tasks into execution.

A proposal should contain the original/proposed requirements diff, assumptions and missing inputs, workflow choice, target repository/context, effort bound, and expected output. Approval must distinguish “save clarification” from “save and delegate.” For example, “Improve PDF intake” might become “Reproduce duplicate reference creation after a rename; identify the cause and propose a fix, preserving annotation backlinks.” Making success inspectable matters more than producing a longer prompt.

Approval covers the **reviewed revision and workflow**. Accepted research does not authorize implementation; changing one agent to a swarm changes the budget. If the task changes while approval waits, regenerate the diff or establish that the approval still applies.

Use one durable approval record for the resulting launch. The task/tag update and scheduler must converge on it; otherwise the approval handler and polling watcher can each launch a copy. Rejection needs a cooldown until relevant changes, not another notification every scan.

Confidence can rank proposals. It cannot authorize them. An agent can understand “book a trip” perfectly and still lack purchase authority.

### C. Questions in Highlights annotations

This is a strong early experiment because outputs are bounded and context is captured:

1. Read structured annotations and section membership through Bob.
2. Interpret a configured question marker/section as intent, distinguishing your comment from quoted text.
3. Snapshot question, quote, reference revision, page locator, and annotation identity; preserve continuation-piece context.
4. Retrieve enough of the reference to answer faithfully. State when a PDF, image, or appendix is inaccessible rather than treating a highlight as the full source.
5. Return a short answer, source locations, and uncertainty. Separate the paper's claim from inference or outside evidence.
6. Write to a dedicated answer area **in the same note, outside the generated region**, with a question backlink and request ID.

This satisfies “answer in the same note” while surviving import. A later renderer can display linked answers beneath highlights without making the importer and agent compete over generated bytes. Writing into the PDF annotation itself is a separate Mac synchronization/PDF-coordination feature, unnecessary for the first experiment.

Useful outcomes include answered, needs an assumption, source unavailable, and source does not establish this. Several questions in one comment need sub-identities or a versioned multi-question request.

Consider **answer mode versus hint mode**. Some questions invite explanation; others are part of learning. A per-reference “hint first” default could preserve productive uncertainty instead of replacing every reading question with a solution.

## 4. Additional use cases worth testing

These are design proposals, not claims of current functionality. “Later” means test only after the basic delegation loop works; it is not a recommendation to build all of them.

| Use case | Trigger and useful output | Why deeper integration helps | Priority |
| --- | --- | --- | --- |
| Prepare tomorrow's human work | Explicitly selected task → relevant files, current state, decisions needed, and a first-action checklist | Saves context reconstruction without pretending to do the human's work | Early |
| Produce a decision brief | “Choose an approach” task → options, tradeoffs, evidence, and one recommendation | Records why a choice was made alongside the commitment it changes | Early |
| Verify a claimed outcome | Result or deployment arrives → checks against the original acceptance criteria | Separates successful execution from successful outcome | Early |
| Ask the smallest unblocking question | Unclear selected task → one precise question plus proposed defaults | Reduces back-and-forth and avoids speculative implementation | Early |
| Prepare physical or interpersonal work | Errand/conversation task → checklist, draft, comparison, or questions to ask | Helps with tasks that are fundamentally not automatable | Early, explicit only |
| Prepare the morning review | Bounded schedule → digest of completed attempts, unresolved decisions, and stale evidence | Uses the existing review ritual and controls interruptions | Early |
| Dependency-aware continuation | Accepted predecessor outcome → offer the next eligible work item | Carries context forward without confusing an agent's claim with dependency completion | Later |
| Research-to-experiment chain | Reading answer suggests a test → proposed experiment linked to question and source | Connects knowledge acquisition to implementation with traceable reasoning | Later |
| Revisit an answer when evidence changes | New source/revision → concise change analysis, not a replacement essay | Keeps decisions grounded while preserving previous answers | Later, explicit watch |
| Recurring verification | Standing “check periodically” commitment → report only material deviations | Turns recurring tasks into bounded monitors rather than repeated manual checking | Later |
| Detect overlapping work | Similar open tasks or active delegations → proposed shared investigation or duplicate link | Avoids redundant spend across Bob and issue trackers | Later, no silent merges |
| Decompose a large commitment | Approved broad task → suggested phases, acceptance criteria, and dependency edges | Makes the task executable while preserving its human-level purpose | Later |
| Rescue stalled work | Stale authorized attempt → diagnosis, smaller scope, or a targeted handoff proposal | Makes failure actionable instead of leaving a forgotten “running” marker | Later |
| Cross-system evidence routing | One patch/report satisfies several linked commitments → attach relevant evidence to each | Prevents the same work being commissioned twice across tools | Later, explicit identity mapping |
| Review backlog simplification | Approved project review → recommend tasks to combine, defer, or drop, with reasons | Can reduce obligations instead of maximizing output volume | Later, proposal only |
| Calibrate delegation preferences | Accepted/rejected outcomes → explicit recommendations for future defaults | Learns where automation helps without silently broadening permissions | Later |

The strongest non-obvious opportunity is **preparation**. A task such as “talk through the design with a collaborator” cannot be completed by an agent, but an agent can assemble prior decisions, conflicting requirements, and three questions. A task system supplies the timing and purpose that a generic chat assistant lacks.

Another valuable opportunity is **negative work**: discovering that no action is needed, that a task duplicates another, or that an assumption is false. The integration should reward those outcomes rather than pressuring agents to manufacture a deliverable. Recommendations to cancel or merge still belong to the human.

## 5. What other systems teach us

### Agent participation is becoming a task-system feature

Linear provides agent sessions triggered by mentions or delegation, activity events, input requests, and links to external sessions/results. Its guidance also distinguishes human delegation from automated triage and recommends frozen activity records for reconstructing input, because editable comments can change. **Lesson:** separate the task from an attempt/session, and keep the request snapshot immutable. This is evidence of a viable interaction pattern, not evidence that SASE will improve your personal productivity. [Linear agent interaction][linear]; [Linear interaction guidance][linear-best]

GitHub exposes background research, planning, implementation, and repository automations inside issue/PR workflows. Its documented review surfaces make output and validation inspectable. **Lesson:** launching from a task is already useful product behavior; SASE's opportunity is carrying the loop across personal notes, reading, non-code work, and multiple execution environments. A generic “issue launches coding agent” feature alone would be weak differentiation. [GitHub agent workflows][github-agent]

### Transport standards help, but do not define a personal commitment

A2A models tasks, messages, artifacts, and execution states, including input-required and terminal outcomes. That is useful for delegating to a remote executor. It does not establish whether Bryan accepts an answer or whether a Bob commitment is Done. [A2A specification][a2a]

The MCP Tasks extension dated 2026-07-28 supports asynchronous tool results, polling, input requests, and cancellation. Its task completion can even carry a tool result with `isError: true`; transport completion is therefore especially unsuitable as a personal-task completion signal. Use these protocols behind an execution adapter when needed, not as the authoritative human-work model. Do not design against the older 2025-11-25 shape without checking the deployed version. [MCP Tasks extension][mcp-tasks]

### Reliable observation needs reconciliation

Asana documents compact events, possible missing events, non-replayable webhooks, and fallback polling for stronger coverage. It also describes repeated changes while users edit a field. **Lesson:** a webhook or file event means “reconsider this object,” not “launch exactly once from this payload.” Debounce, reread, and periodically reconcile. Polling Bob first is a reasonable implementation choice. [Asana events][asana-events]; [Asana webhook guide][asana-webhooks]

## 6. A small architecture that can generalize

### Keep the core about delegation, not Markdown or one vendor's status names

A conceptual pipeline is:

```text
Task or annotation → provider snapshot → policy/authorization → durable delegation
    → SASE admission and workflow → evidence → provider projection → human review
```

The provider adapter owns source syntax, identity resolution, source revisions, safe writes, native status semantics, and visibility. The common layer owns authorization linkage, attempt identity, deduplication, cancellation, publication retries, and audit history. SASE continues to own execution, capacity, and finalization. Shared domain rules belong in `sase_core`; Python is orchestration/glue, while Bob-specific mutation rules belong in Bob. [SASE core boundary][core-readme]

Do not introduce a second scheduler. A bounded scheduler job can discover candidates and return proposals through existing admission. Do not allocate model work just to repeatedly rediscover that nothing changed. Cheap deterministic eligibility checks should precede expensive interpretation.

### A conceptual record, not a proposed public API

```yaml
source:
  provider: bob
  account: personal-vault
  object_id: provider-resolved-stable-id
  locator: project.md#^task-id
  revision: relevant-task-block-digest
request:
  id: delegation-id
  version: 1
  objective: bounded-outcome
  workflow: research
  acceptance: [specified-reviewable-result]
  context_refs: [approved-inputs]
  authorization_id: reviewed-proposal-or-standing-policy
  workflow_digest: resolved-workflow-version
  budget: bounded-policy
execution:
  attempt_id: attempt-id
  launch_id: host-admission-id
publication:
  evidence_id: immutable-result-id
  operation_id: idempotent-write-id
review:
  decision: pending
```

The source ID is not the locator: a task can move. A request version is not an attempt: an infrastructure retry should not authorize different work. A result's publication state is not its execution state: a good result may exist while Bob is offline. These separations are worth introducing even in a modest prototype.

For a Bob MVP, require identified tasks in a limited set of notes and use an explicit association between the delegation and current locator. Do not pretend note-scoped block IDs are globally immutable. Before supporting arbitrary moves/renames, add a relocation-aware association or persistent integration ID that travels with the task through Bob's move/archive operations. Ambiguous identity should stop publication; text similarity is insufficient permission to mutate another task. [Bob identity implementation][b-identity]

Snapshot all inputs that can materially change the meaning: requirements, relevant child bullets, dependencies, reference question text, and policy/workflow version. Exclude integration-owned progress/evidence fields from the request digest so writing progress does not retrigger work. Decide explicitly which edits require renewed authorization. Typographical cleanup may not; a different destination repository or a new acceptance criterion usually does.

### Lifecycle mapping must preserve native meanings

| Common integration event | Bob projection | A provider without a review state |
| --- | --- | --- |
| Candidate discovered | No automatic lane change | No automatic completion change |
| Authorized and queued | Compact integration status | Label, property, or comment |
| Attempt running | Integration progress; keep native planning semantics | Native activity/session if available |
| Input needed | Linked question/proposal | Comment or native elicitation |
| Evidence delivered | `[/]` as requested, plus explicit result-ready marker, subject to Bob reconciliation | Keep open and add review metadata |
| Human accepts | Human-owned completion flow | Native completion action |
| Attempt fails/cancels | Show reason, preserve the commitment unless the human cancels it | Same principle |

Two parallel sets of state are sufficient: native task state and delegation state. Do not force every provider to implement a twelve-state kanban. Capability negotiation should allow structured activity for a rich provider and a small result comment for a simpler one.

A minimal adapter contract could support `list_candidates`, `get_snapshot`, `resolve_identity`, `capabilities`, `apply_proposal`, and `publish_evidence`. These names are sketches. Important capabilities include incremental listing, conditional update, idempotent append/upsert, task status mapping, annotation support, links, and cancellation observation. If a provider lacks conditional writes, use additive evidence where safe and disable unattended requirement replacement; a reread followed by a write is not a true compare-and-swap.

### Relate to goals and beads without making a shadow task manager

Bind accepted work to the SASE goal model as its host contract becomes available. Keep the external task as the authority for its native description, priority, schedule, and human completion. Store a versioned mapping and execution evidence, not a competing editable copy of every field.

Beads can still track internal implementation phases or discovered engineering work. They should not be mandatory for every reading question. One human commitment may lead to several internal work units, and several external links may refer to the same outcome. Start with simple explicit links; do not automatically infer that similar titles denote the same commitment.

The inspected plugin registry has artifact, finalizer, task-type, VCS, and workspace extension points, but no listed generic task-source provider group. A generic task provider would therefore be new work, not a configuration toggle. Also, `sase_task_types` describes bead types, not external task-system adapters. [Plugin registry][s-plugins]

## 7. Reliability and authority determine whether this stays useful

The following safeguards address concrete failure modes of the requested workflows. They are not reasons to require approval for every reversible action.

| Failure or ambiguity | Required behavior |
| --- | --- |
| Two machines observe the same ready task | One authoritative dispatcher initially. Later, a transactional claim with fencing across dispatchers; Git sync and local locks alone do not provide this. |
| The same event arrives repeatedly | Deduplicate by source identity, authorized request version, and workflow. An explicit retry creates a new attempt under that request. |
| A host crashes after launch but before recording success | Reconcile the durable admission/attempt identity before launching again. Treat an unknown outcome as unknown. |
| Requirements change while an agent works | Preserve the original snapshot; classify the result against that revision and avoid silently declaring the new scope satisfied. |
| The user removes the ready tag or cancels | Revoke future admission and request cancellation of active work. Preserve partial evidence and report effects already completed. Removing a tag is not rollback. |
| Writing the result succeeds but acknowledgment is lost | Retry an idempotent operation or find its stable publication marker before appending. Do not rerun the agent. |
| The result is good but the task system is offline | Keep evidence durably and show publication pending; retry only delivery. |
| A task moves, archives, or loses its identity | Resolve through supported identity tracking; otherwise require reconciliation. Never update the nearest-looking task. |
| An agent produces a result but host finalization fails | Do not publish a successful completion claim. Distinguish partial output from verified host completion. |
| An annotation question changes but its block ID stays stable | Invalidate or supersede the old answer using the question digest; keep history accessible. |
| An answer is deleted by the user | Treat deletion/dismissal as intent, not as permission to regenerate it every scan. |
| The task contains hostile or accidental control text | Treat imported content as data. Choose workflows, credentials, and allowed writes from host policy, not text embedded in a task/PDF. |
| Agents fill the review queue | Pause new discretionary admissions and summarize pending decisions. Resource capacity includes human review capacity. |

SASE host-owned finalization already distinguishes the agent's declaration from independently checked completion. Evidence write-back should respect that boundary. A persistent publication outbox can deliver a result after verified completion without making a temporary Bob outage cause the implementation to run twice. [Host-owned completion decision][s-completion]

A result packet should contain: the original objective/version, what was delivered, evidence links, checks actually run and their outcomes, known gaps, and the requested human decision. For coding work, a commit is evidence of a change, tests are evidence about selected properties, and deployment/real-world behavior may require additional checks. For research, citations and explicit unresolved questions matter more than a generic “success” flag.

**Privacy needs an explicit route.** A private personal task should not be copied wholesale into a public research or bead repository. SASE's goal docs state that shared goal content is as public as the beads sidecar and describe local-only visibility. The adapter must carry source visibility and select storage/publication destinations accordingly. This is especially relevant when a personal task asks for research that would ordinarily use public SASE sidecars. [Goal storage and visibility][s-goals]

Use a scoped collection of tasks/references, not continuous unrestricted reading of the whole vault. External actions such as sending a message, purchasing, or publishing require their own authority; “research this task” does not authorize its most consequential implied action. Conversely, a standing authorization for bounded reading answers should not generate an extra approval dialog per answer.

## 8. Build choices and a falsifiable first experiment

### Alternatives

| Approach | Strength | Limitation | Judgment |
| --- | --- | --- | --- |
| A script watches tags, invokes SASE, and appends text | Fastest way to test whether outputs are useful | Identity, authorization, retry, and write-back rules become hidden script state | Useful disposable prototype if constrained to one writer and explicit tasks |
| Thin provider adapter plus a small delegation ledger | Preserves native semantics while sharing orchestration and reliability | Requires designing identities and state transitions | Recommended product direction |
| Mirror all tasks into beads/goals with full bidirectional field sync | Unified internal inventory | Conflicting ownership, duplicate inboxes, migrations, and schema mismatch | Avoid as a starting point |
| Use only a vendor-native agent integration | Strong native experience where available | Does not cover Bob reading context or task-system independence | Useful comparator and later adapter surface |
| Build a universal workflow engine and task graph first | Maximum apparent generality | Large cost before observing useful work; duplicates SASE machinery | Reject for this stage |

Task-system agnosticism is a property to demonstrate, not a reason to implement many integrations now. Bob first, then a small adapter conformance test against an API-backed tracker or a deliberately minimal fake provider. A second real adapter should exercise different semantics, such as no native Pending state or no atomic conditional mutation.

### Stage 0: observe and establish the baseline

Use a bounded, explicitly selected set of tasks and references. Record how much time you currently spend copying context into prompts, finding results later, and reviewing outputs. Run candidate detection without launching or writing. Confirm that tags, sections, dependencies, archived items, and question edits are classified correctly.

This should reveal whether the primary friction is initiation, context assembly, execution quality, or review. If almost all time is in difficult review, automatic initiation alone may make the experience worse.

### Stage 1: answer selected reading questions

Use one dispatcher, one configured question marker/section, and one durable answer area outside the managed region. Start with a small set, perhaps ten questions from a few references. Include a source that cannot be fully accessed, a question edited after capture, an image-based question, and a repeated sync.

Read the actual answers and check their page/source support. Re-run Highlights synchronization and verify that answers survive and are not duplicated. Test whether you prefer full answers, hints, or a collapsed answer indicator. Keep question resolution separate from whether the reference has been read.

### Stage 2: explicitly delegate a small task set

Choose perhaps ten bounded tasks with clear acceptance criteria: a few research/decision briefs, a few code changes, and a few preparation tasks. Use `#sase/ready` or an equivalent explicit gesture with selected workflow defaults. Preserve native scheduling/dependency semantics and return evidence into Pending review.

Exercise duplicate observation, process restart, source edit during execution, source cancellation, and failure to publish. A successful happy path is insufficient evidence for background operation. Do not add cross-machine dispatch until duplicate prevention is demonstrated with one writer.

### Stage 3: proposals and a second provider

Only after direct delegation earns trust, enable a small proposal budget—for example, no more than three clarification suggestions per review period. Record accepted, edited, dismissed, and ignored proposals. Include “save clarification only.” Compare a single-agent research proposal with a swarm only for questions where independent analysis could change a meaningful decision.

Use a second provider to test whether identity, authorization, evidence, and review survive without Bob syntax. Keep advanced provider features optional rather than forcing all adapters to imitate the richest one.

These stages are a research sequence, not an approved implementation plan or time estimate.

### Measurements and provisional decision rules

The numbers below are suggested pilot criteria, not empirically justified product SLOs.

| Metric | What to measure | Proposed interpretation |
| --- | --- | --- |
| Net human time | Prompt preparation + review + repair + integration upkeep, compared with similar manual tasks | Continue only if total time and subjective friction improve |
| Useful-result rate | Results accepted without substantial redirection / all completed attempts, separately by workflow | A high blended rate must not hide a poor coding or reading category |
| Proposal value | Accepted clarifications and launches versus all suggestions shown | If most are ignored or rewritten, reduce frequency or scope |
| Review backlog | Count and age of results awaiting decisions | Stop increasing throughput when backlog grows faster than review |
| Publication integrity | Wrong-target writes, lost authored content, duplicates, stale results represented as current | Target zero in pilot; investigate every occurrence before expanding |
| Cost per accepted outcome | All attempts, retries, swarm members, verification, and synthesis | More agents are worthwhile only when decision quality or saved time improves |
| User control | Revoke/cancel latency; whether refused proposals remain quiet | The system must stop predictably and respect dismissal |
| Reading quality | Correct citations, source/inference separation, unsupported-answer rate, usefulness of hints | Evaluate learning benefit separately from answer volume |

For a small pilot, a reasonable continuation test is: no integrity failures in the deliberate failure cases, most selected outputs are useful, and median human handling time improves. A sample of twenty items can reveal obvious product problems; it cannot establish robust safety or reliability rates. Track difficult and failed examples rather than excluding them from the denominator.

## 9. Decisions to defer, and questions that matter now

**Decide early:** the scope eligible for inspection, the meaning of the delegation gesture, whether questions request hints or answers, how to show result-ready within Pending, the storage visibility policy, and how to revoke work.

**Defer:** a universal task taxonomy, automatic backlog-wide prioritization, a new dashboard, cross-machine claims, learned autonomy expansion, and full PDF annotation write-back. None is necessary to test the core value.

Remaining uncertainties:

- Does the current Bob command surface support the exact atomic evidence-plus-Pending update needed, or should Bob gain a narrow semantic operation? The inspected primitives show a good foundation, not proof of that complete transaction.
- Which deployed SASE goal-binding and claim producers are ready? The accepted policy is ahead of the inspected public ledger interface.
- What should happen if a tagged task's scope changes before admission? Approval must bind enough context to remain meaningful without requiring review for every cosmetic edit.
- How should task moves and reference renames update external associations? Existing IDs and import markers help, but end-to-end delegation identity needs explicit validation.
- Is your largest benefit better initiation, better preparation, or better review? A pilot should determine this before architecture expands.

My recommended initial product promise is: **“Delegate a bounded piece of work from the place you already manage it, and get a traceable result back there for review.”** That is narrow enough to make reliable, broad enough to cover all three proposed examples, and useful across task systems with very different interfaces.

## Research provenance

Repository inspection used local checkouts opened through `sase repo open`; canonical memory was read through audited `sase memory read`. No task, note, PDF, workflow configuration, or application code was changed. Only this report was authored. No peer research was consulted.

| Repository | Inspected revision | Main scope |
| --- | --- | --- |
| `sase-org/sase` | `db31bf43dc5e84f704c5200cb28ec1aec506d4e5` | Scheduler/admission, goals, plugin registry, external issue mirror |
| `sase-org/sase-core` | `7c0a7b8f25d0418047b48a2573b4b64145fcbde0` | Goal wire/action maturity and backend ownership |
| `bobs-org/bob-cli` | `4e3a39150c37f83a0134baf6a61035992af42430` | Lanes, task identity, capture, references, Highlights |
| `bobs-org/bob-plugins` | `a61d9072250cdab402fbf4c494e22248199d3cd6` | Existing Pending review and task-card surfaces |
| `bobs-org/bob-mac-capture` | `461f46c285745e9ec2fbe3324cfae1123de1f057` | Thin-client boundary and reference integration context |
| Configured `chezmoi` linked repository | `ea37b90d9d263068cec68e96367621c4c3b50ac9` | Existing research publication hook and annotation prompts |

External sources were checked on 2026-10-25. They demonstrate patterns and contracts; vendor documentation is not independent evidence of productivity gains. This was architectural/product research, not an exhaustive API audit. Citations below resolve to inspected repository revisions or primary documentation; proposed records and workflows are explicitly conceptual.

[b-lanes]: https://github.com/bobs-org/bob-cli/blob/4e3a39150c37f83a0134baf6a61035992af42430/docs/concepts/tasks-and-lanes.md
[b-identity]: https://github.com/bobs-org/bob-cli/blob/4e3a39150c37f83a0134baf6a61035992af42430/src/native/note_tasks.rs
[b-id-write]: https://github.com/bobs-org/bob-cli/blob/4e3a39150c37f83a0134baf6a61035992af42430/src/native/capture_task_id.rs
[b-capture]: https://github.com/bobs-org/bob-cli/blob/4e3a39150c37f83a0134baf6a61035992af42430/docs/capture.md
[b-ref]: https://github.com/bobs-org/bob-cli/blob/4e3a39150c37f83a0134baf6a61035992af42430/docs/ref.md
[b-highlights]: https://github.com/bobs-org/bob-cli/blob/4e3a39150c37f83a0134baf6a61035992af42430/docs/highlights-ref-sync.md
[b-mac]: https://github.com/bobs-org/bob-mac-capture/blob/461f46c285745e9ec2fbe3324cfae1123de1f057/README.md
[s-jobs]: https://github.com/sase-org/sase/blob/db31bf43dc5e84f704c5200cb28ec1aec506d4e5/docs/reference/automation/scheduler-jobs.md
[s-architecture]: https://github.com/sase-org/sase/blob/db31bf43dc5e84f704c5200cb28ec1aec506d4e5/docs/contribute/architecture.md
[s-mirror]: https://github.com/sase-org/sase/blob/db31bf43dc5e84f704c5200cb28ec1aec506d4e5/docs/reference/automation/scheduler-default-routines.md
[s-goals]: https://github.com/sase-org/sase/blob/db31bf43dc5e84f704c5200cb28ec1aec506d4e5/docs/reference/work-units/goals.md
[s-goal-decision]: https://github.com/sase-org/sase/blob/db31bf43dc5e84f704c5200cb28ec1aec506d4e5/sase/memory/decisions/goals-host-binds.md
[s-completion]: https://github.com/sase-org/sase/blob/db31bf43dc5e84f704c5200cb28ec1aec506d4e5/sase/memory/decisions/host-owned-completion.md
[s-plugins]: https://github.com/sase-org/sase/blob/db31bf43dc5e84f704c5200cb28ec1aec506d4e5/docs/reference/integrations/plugins.md
[core-goals]: https://github.com/sase-org/sase-core/blob/7c0a7b8f25d0418047b48a2573b4b64145fcbde0/crates/sase_core/src/goal/actions.rs
[core-readme]: https://github.com/sase-org/sase-core/blob/7c0a7b8f25d0418047b48a2573b4b64145fcbde0/AGENTS.md
[horvitz]: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/chi99horvitz.pdf
[linear]: https://linear.app/developers/agent-interaction
[linear-best]: https://linear.app/developers/agent-best-practices
[github-agent]: https://docs.github.com/en/copilot/concepts/copilot-surfaces/copilot-on-github
[a2a]: https://a2a-protocol.org/latest/specification/
[mcp-tasks]: https://modelcontextprotocol.github.io/ext-tasks/specification/2026-07-28/tasks.html
[asana-events]: https://developers.asana.com/reference/events
[asana-webhooks]: https://developers.asana.com/jd/docs/webhooks-guide
