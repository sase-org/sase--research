# Missing records for the SASE introduction: reader questions, concrete evidence, and the human workflow

Independent research by **cdx**, 2026-11-25. Prepared for `~/bob/sase_blog_zettel.md`.

The most valuable additions are records that explain what changes in a developer's working day: what becomes easier to supervise, how a decision returns to the person, what survives an interruption, and what evidence supports calling the work finished. The album already contains much of SASE's internal vocabulary. Its larger gap is the bridge between those abstractions and a reader deciding whether to try it.

This is a recommendation report, not an edit to the vault. Suggested first-person claims below are drafting prompts for Bryan to accept or rewrite; they are not invented quotations or verified accounts of his experience. I did not consult another researcher's report, transcript, summary, or findings from this swarm.

## What I checked

- The album schema and properties through `bob records show sase_blog_zettel` and `bob props show sase_blog_zettel.md -f json`.
- All **29 existing records' claims, sections, and statuses** through `bob query`, and their bodies through `bob ref show -r sase_blog_zettel`. All are marked `seed`; one already contains a `Draft` section, so the status is not a reliable measure of writing progress.
- Bryan's annotations in `[[ref/notes/sase_blog_261019]]` and `[[ref/notes/sase_blog_261116]]`, the metadata for the earlier zettel guide, and annotations on the paper that inspired SASE. These predate this swarm.
- SASE's README and selected concept, onboarding, recovery, tools, monitor, integration, and approval documentation in the current checkout, at commit `696e0180f4a0cb971502871ef64b44504efed38d`. I also used audited glossary reads for SASE terms. This is documentation research, not a runtime acceptance test or security audit.
- Six external primary sources, checked on the web and in the Bob reference library. Library state and source dates are recorded below.

The records conform to a useful existing rule: topic-sized pieces, **one claim per record, in Bryan's voice**. Keep that rule. A list of features is raw material for a record, not yet its claim.

## Coverage and actual gaps

| Existing section | Count | Existing records |
| --- | ---: | --- |
| `intro` | 1 | `what_came_before` |
| `what` | 3 | `recursive_sase_improvement`, `sase_is_many_abstractions`, `why_a_tui` |
| `macros` | 4 | `agent_control_flow`, `layers_of_prompt_management`, `model_alias_pools`, `the_prompt_composer` |
| `the_agent_cli` | 2 | `agent_cli_installs_and_updates`, `usage_limits_and_api_costs` |
| `memory` | 2 | `memory`, `skills_should_be_procedural_memories` |
| `turn` | 3 | `finalizers`, `microsoft_ceo_thinks_model_agnostic_architecture_is_good`, `multi_provider_swarms` |
| `plan` | 5 | `artifact_links`, `audited_artifact_reads`, `bead_lifecycle`, `beads_and_birds`, `repos_vs_directories` |
| `project` | 2 | `host_owned_completion`, `monorepo_tools_are_trending` |
| `not_ready` | 2 | `ai_slop`, `sase_is_too_complex` |
| `future` | 5 | `bob_task_events`, `evals`, `files_not_tracked_by_a_vcs`, `goals`, `memory_and_docs_are_the_same` |
| Eight empty sections | 0 | `gate`, `tools`, `fleet`, `automation`, `plugins`, `how_i_use_sase`, `demos`, `close` |

These counts diagnose coverage, not a quota. Filling every section would risk turning an introduction into a reference manual. In particular, the title “SASE is many abstractions” explains the implementation's shape, but does not yet answer the reader's first question: **which recurring problem would make me want those abstractions?**

My proposed reading sequence is: recognizable problem → one ordinary task → a few mechanisms that made that task work → honest limitations → a small invitation to try it. The eventual article can draw only a sentence from a record; adding a record does not commit it to a full subsection.

## Material you already have that deserves a second look

**A recovery story with an actual lead.** In `[[ref/notes/sase_blog_261019]]`, your annotated screenshot list calls out a provider outage shorter than 30 minutes and points to `~/tmp/screenshots/20260616_140429.png`. The same annotation names `20260616_115015.png` for `%wait`, and `20260624_074728.png` for questions/retries/tales. You explicitly preferred GIFs when revisiting these. I did not open or verify the images: they are source leads from your note, not evidence that those files still exist or represent today's UI. They are unusually promising starting points for records about recovery and waiting.

**A gate analogy you have already made.** Your annotation on the Agentic Software Engineering paper says its Consultation Request Pack resembles gates. Another asks whether plan frontmatter is missing the “why.” That is stronger raw material than a generic explanation of approval dialogs: a decision request should preserve enough intent and evidence for a human to answer it. The paper is already in your library, with a queued reading task blocked on finishing the v1 blog draft. This report should help you write without turning that reading into another prerequisite.

**A real provenance example.** Your October annotation identifies an agent reading four related plans and points to an image embedded in that reference note. `audited_artifact_reads` also reminds you that screenshots exist. Use this to strengthen that existing record; do not create another generic “artifacts are useful” record.

**A reader invitation you already endorsed.** The October annotations propose questions for readers at the end of the blog, potentially as GitHub poll issues. The empty `close` section can become a specific request for a workflow or failure report. No issues need to be created merely to draft this record.

## What the external research changes

**Credit the original SASE vision explicitly.** Hassan and colleagues frame agentic software engineering around goals, artifacts, human oversight, and complementary environments for people and agents. The paper presents a conceptual research vision, not a certification of this implementation. SASE's own acknowledgements credit it for the name and direction. A short attribution record would explain both the lineage and where Bryan made independent engineering choices. The arXiv page currently identifies v4, revised November 2, 2026; Bryan's stored annotation snapshot predates that revision. [Paper][e1], [SASE acknowledgements][s11].

**Distinguish fixed workflow mechanics from model judgment.** Anthropic's 2024 guidance distinguishes predefined workflow paths from model-directed agents, and argues for starting with the simplest adequate design. This gives a useful way to explain SASE's host-owned operations and prompt control flow without implying deterministic model outputs. The article now warns that its tooling landscape has changed, so use the architectural distinction as background, not as a current vendor comparison. [Building effective agents][e2].

**Continuity is an engineering problem in its own right.** Anthropic's November 2025 long-running-agent account describes fresh sessions losing context, premature declarations of completion, and the importance of explicit progress artifacts and checking behavior. That supports a record about preserving inspectable work across turns. It does not establish that SASE implements Anthropic's design or that either approach eliminates failures. [Effective harnesses][e3].

**More agents need a task-specific justification.** Anthropic's June 2025 research-system account reports benefits for broad, independently searchable questions, substantial token costs, and difficulty applying the same approach to tightly dependent coding work. Its measurements concern its own system. They do not prove a performance gain for SASE, or that five different providers outperform five runs of one model. My inference is to explain the task split and review cost alongside the swarm demonstration. [Multi-agent research system][e4].

**A credible introduction can be useful without a speedup number.** METR's July 2025 randomized study found a 19% slowdown for 16 experienced open-source developers working on 246 tasks. That result is bounded to its setting and period. Its February 2026 follow-up explicitly describes selection effects and difficulty measuring time when people use concurrent agents, making the new productivity estimate unreliable. Cite both if discussing this research; neither measures SASE. My recommendation is a transparent case study, with measured fields and missing fields labeled, rather than a causal claim from a busy dashboard. [Original study][e5], [Follow-up][e6].

For the case study, collect: the requested outcome; resulting diff or artifact; validation performed; human active minutes including review and repair; elapsed time including waits; provider/model and available usage/cost; and remaining defects or uncertainty. Human attention and accepted value would need separate observation; do not imply ToolRuns already measure them. A one-task example illustrates a workflow. Establishing a productivity effect would require an appropriate baseline and repeated observations.

## Strengthen these existing records instead of creating duplicates

| Existing record | Recommended addition or correction |
| --- | --- |
| `evals` | Add a measurement question: does SASE reduce human effort per accepted outcome? Separate human attention, elapsed time, model usage, host compute, and downstream repair. Model benchmarks alone cannot answer that question. Keep it a measurement proposal until data exists. |
| `multi_provider_swarms` | Replace speculation about what people at frontier labs can access with an observable claim about your workflow. Treat cross-provider diversity as a hypothesis about useful disagreement, not a guarantee of independent errors. This swarm's independent investigation rule is a design choice, not an evaluation result. |
| `model_alias_pools` and `usage_limits_and_api_costs` | Add a concrete selection example and its tradeoff. Availability, cost, latency, and output quality are different concerns. Avoid freezing specific model names or prices into the article unless checked at publication. |
| `host_owned_completion` and `finalizers` | Explain who supplies the result and who performs the tracked completion operation. A predictable completion contract does not guarantee a correct patch or an approved merge. The new end-to-end story can reference both records. |
| `goals` | Recheck the placement under `future`: current project memory already defines a person-owned outcome record distinct from agent liveness. Preserve the larger aspiration, but distinguish implemented semantics from desired extensions. |
| `memory` and `memory_and_docs_are_the_same` | Give one example of stale or excessive instructions and how the current read/write policy addresses it. “Docs can replace instruction files” needs the underlying study and its conditions before publication; this investigation did not verify that existing claim. |
| `what_came_before` | The `tmux_ai_window` lead is already here. Use it for personal history; avoid asserting that most engineers pass through the same stages without evidence. I did not inspect chezmoi in this investigation. |
| `ai_slop` and `sase_is_too_complex` | Develop one concrete defect and one design change from the categories already recorded in your November annotations. Keep “a failure I encountered” separate from a general diagnosis of all agent-generated software. |

Also avoid importing unsupported absolutes from older project prose. Acknowledgements can establish inspiration; they do not empirically establish that coordination is always the bottleneck, that another tool's plans always disappear, or that a particular architecture wins universally.

## Sources and library check

The SASE links below point to the exact commit read locally, making them reproducible even as the live docs change. No other repository's source was fetched through web file URLs. Internal note links identify the shared input used, not swarm reports.

| Key | Primary source and role |
| --- | --- |
| S1 | [README][s1]: product positioning, alpha/POSIX constraints, existing demo inventory. |
| S2 | [Agents, sessions, and workspaces][s2]: isolation and continuity. |
| S3 | [How changes land][s3]: host-owned finalization and VCS workflow. |
| S4 | [Automation and human checkpoints][s4]: scheduling and explicit decisions. |
| S5 | [Recover an interrupted agent][s5]: specific restart/retry/revive behavior and limits. |
| S6 | [Run agents in parallel][s6]: independent scopes and combining overlapping changes. |
| S7 | [Named tools and ToolRuns][s7]: retained commands, output, stages, and evidence. |
| S8 | [Monitors][s8]: supervised commands, staged activation, outcome-dependent continuation. |
| S9 | [Providers and models][s9]: coding-agent CLI versus SASE responsibilities. |
| S10 | [Run your first agent][s10]: a small first task; prompt instructions are not permission enforcement. |
| S11 | [Acknowledgements][s11]: project-stated intellectual lineage. |
| S12 | [Plugins][s12]: separable integrations, including GitHub and research artifacts. |
| S13 | [Remote dispatch][s13]: explicit machine enrollment and dispatch prerequisites. |
| S14 | [Notifications][s14]: durable gate bundles and their UI/transport projections. |
| S15 | [Autonomy CLI][s15]: inspectable, scoped gate-decision policies. |
| E1 | [Agentic Software Engineering][e1], 2025, current v4 in November 2026. Already in your library: queued since 2026-10-07, `[[ref/papers/agentic_software_engineering]]`; v1-draft dependency is recorded. The older duplicate is superseded. |
| E2 | [Building effective agents][e2], December 2024. Already in your library: started since 2025-10-27, legacy record `[[ref/ai/agent_ref/build_effective_agent]]`. |
| E3 | [Effective harnesses for long-running agents][e3], November 2025. Already in your library: queued since 2026-03-15, legacy record `[[ref/ai/claude_code_ref/effective_claude_harness]]`. |
| E4 | [How we built our multi-agent research system][e4], June 2025. Queried source URL not found in `ref/`. |
| E5 | [METR's early-2025 developer study][e5], July 2025. Queried source URL not found in `ref/`. |
| E6 | [METR's experiment-design update][e6], February 2026. Queried source URL not found in `ref/`. |

The six candidates were checked in one `bob ref find` call. “Not found” means no indexed match for that query under `ref/`, not that Bryan has never read it. Anthropic's engineering URLs currently redirect to research URLs; the library checks used the original engineering URLs shown in the source links. There is no need to add three new reading tasks before writing.

Library check: 3 of 6 candidates already in your library (0 finished).

[s1]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/README.md
[s2]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/concepts/agents.md
[s3]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/concepts/landing.md
[s4]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/concepts/automation.md
[s5]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/guides/recover-interrupted-agent.md
[s6]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/guides/run-agents-in-parallel.md
[s7]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/reference/automation/tools.md
[s8]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/reference/automation/monitors.md
[s9]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/concepts/providers.md
[s10]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/start/first-run.md
[s11]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/contribute/acknowledgements.md
[s12]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/reference/integrations/plugins.md
[s13]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/reference/integrations/remote-dispatch.md
[s14]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/reference/automation/notifications.md
[s15]: https://github.com/sase-org/sase/blob/696e0180f4a0cb971502871ef64b44504efed38d/docs/reference/cli/autonomy.md
[e1]: https://arxiv.org/abs/2509.06216v4
[e2]: https://www.anthropic.com/engineering/building-effective-agents
[e3]: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
[e4]: https://www.anthropic.com/engineering/multi-agent-research-system
[e5]: https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/
[e6]: https://metr.org/blog/2026-02-24-uplift-update/

## Ranked recommendations for new records

Ranking favors first-reader understanding, direct evidence, and distance from an existing claim. It is an editorial judgment, not a measured score. Every proposed record would use `parent: "[[sase_blog_zettel]]"`, `type: "[[record]]"`, and initially `status: seed`. The section values below already exist in your schema. Start with the first five; the remaining candidates can wait until the article reveals a need for them.

1. **What I wanted to stop keeping in my head** — `what_i_wanted_to_stop_tracking`, section `intro`.

   **Proposed claim:** “SASE gives delegated work a place to keep its state, so I can spend my attention on the decisions that still need me.”

   **Why add it:** This supplies the user problem missing between `what_came_before` and `sase_is_many_abstractions`. It is about the burden of remembering which run is waiting, what changed, and what deserves review, rather than the chronology of adopting agents. The current README and agent/workspace model support the product intent, but the personal benefit needs your example. [S1][s1], [S2][s2].

   **Material to capture:** One moment when terminal tabs or chat history stopped being enough, and one question you can now answer from the work record. Name the question before naming the abstraction.

2. **One ordinary task, from intent to reviewed result** — `one_ordinary_task`, section `how_i_use_sase`.

   **Proposed claim:** “The useful unit of my SASE workflow is an outcome I can inspect and accept.”

   **Why add it:** No existing record follows a real piece of work end to end. Choose one modest bug fix or feature; show the request, any decision, the agent's change, validation, and your disposition. Keep records for `finalizers`, `host_owned_completion`, and artifacts as explanations you can link from the story. Their existence alone does not establish this personal account. [S2][s2], [S3][s3], [S7][s7].

   **Material to capture:** A real task and its evidence, including one correction if one happened. Record human review effort and elapsed time if available; explicitly label missing measurements. Do not turn the example into a speedup claim.

3. **The human's next move is part of the workflow** — `the_humans_next_move`, section `gate`.

   **Proposed claim:** “When work needs my judgment, SASE can preserve the decision and its context until I am ready to answer.”

   **Why add it:** The `gate` section is empty despite gates being a recognizable human benefit. Current documentation describes durable requests shared across interaction surfaces, and your paper annotation already connects this to consultation requests. A gate turn contains no LLM and does not keep its creator alive waiting. [S4][s4], [S14][s14]; audited `glossary:sase_gate`.

   **Material to capture:** One concrete decision with meaningful choices and consequences. Show what you were asked to judge and what answering enabled. Keep policy-driven automatic handling distinct from a manual decision; it is scoped and inspectable. [S15][s15].

4. **The demo should end at the evidence** — `a_demo_that_ends_at_the_evidence`, section `demos`.

   **Proposed claim:** “A useful SASE demo lets a viewer follow a request all the way to the result and the checks behind it.”

   **Why add it:** The existing README has fan-out, observability, and Patch-pipeline media, but the album has no demo claim. This record specifies what a reader should learn rather than simply reserving a slot for a GIF. [S1][s1].

   **Material to capture:** A proposed 60–90 second sequence: request → visible run → decision or correction → result/diff → validation → final disposition. Reuse the task in rank 2 to avoid a second story. The timing is a production target, not a claim about existing footage. Existing media were identified in the README, not played or validated in this investigation.

5. **An interrupted agent is recoverable work** — `recovering_interrupted_work`, section `turn`.

   **Proposed claim:** “An agent interruption should leave enough evidence for me to decide how to continue the work.”

   **Why add it:** Existing turn records cover finalizers and provider choice; none explains the developer experience of failure. Your outage annotation is an unusually concrete lead. Current recovery documentation distinguishes eligible update-related auto-restarts from manual retry/revive; provider errors, rate limits, kills, and post-model-turn deaths are not all automatically retried. [S5][s5].

   **Material to capture:** Revisit the outage screenshot lead, reconstruct what survived and what you did, then verify the equivalent current workflow. Avoid promises of universal crash recovery or exactly-once side effects. This is distinct from rank 7's ordinary long-command handoff.

6. **Where the name and design came from** — `where_sase_came_from`, section `what`.

   **Proposed claim:** “The SASE paper gave this project its name and direction; this implementation is my attempt to make parts of that vision useful in daily work.”

   **Why add it:** The album has historical and conceptual records, but no explicit attribution claim for the namesake paper. It would establish intellectual honesty and explain the human-command/agent-execution distinction without requiring a literature review. [S11][s11], [E1][e1].

   **Material to capture:** One paragraph naming the paper, one concept you adopted, and one practical choice you made differently. Your gate annotation is a good bridge. Keep other influences with `what_came_before` and `beads_and_birds`; avoid an exhaustive comparison with today's competing products.

7. **Waiting is work the host can own** — `waiting_without_a_live_model`, section `automation`.

   **Proposed claim:** “A long-running command can have a durable place in the workflow after the agent that launched it has finished.”

   **Why add it:** This gives `automation` a precise claim and makes the turn/session distinction tangible: a monitor executes a command, retains its state and output, and follows an outcome policy. Current SASE stages the monitor and activates it after the creator's completion; a recorded reservation is not proof the command has started. [S8][s8].

   **Material to capture:** A test command or external wait, its actual result, and whether the host completed or a follow-up was needed. Explain avoided babysitting without claiming that waiting has zero compute or provider cost. The `%wait` annotation is another source lead, not the same mechanism.

8. **Tests should leave inspectable evidence** — `inspectable_validation_evidence`, section `tools`.

   **Proposed claim:** “When an agent says a check passed, I want to inspect what ran and what it returned.”

   **Why add it:** The empty tools section is an opportunity to explain trust through an ordinary engineering question. Named tools and ToolRuns retain commands, output, stages, and execution evidence. That differs from the existing artifact record's emphasis on which contextual documents an agent consumed. [S7][s7].

   **Material to capture:** One real check record with command, result, and relevant output, plus a failure if useful. State the boundary: a passing test supports the behavior it exercised; it does not establish that the task was understood or every requirement met. Keep evaluation-program proposals in `evals`.

9. **Who should try SASE today** — `who_sase_is_for_today`, section `not_ready`.

   **Proposed claim:** “SASE's current fit is developers who already use coding-agent CLIs and want an opinionated way to supervise their work.”

   **Why add it:** `ai_slop` and `sase_is_too_complex` describe implementation problems. This answers the reader's adoption question. The README explicitly describes alpha status, POSIX-only support, authenticated agent prerequisites, and a preference for git-based workspace workflows. [S1][s1].

   **Material to capture:** A short positive fit description and the friction a first-time user should expect, including installation/authentication and learning the workflow. Give a realistic first task, not a promise of adopting the whole system immediately. Verify current installation details again when publishing.

10. **Parallel work still needs a review budget** — `parallel_work_review_budget`, section `how_i_use_sase`.

   **Proposed claim:** “I choose how much work to parallelize by what can proceed independently and what I can still review well.”

   **Why add it:** This complements `multi_provider_swarms` with a practical selection rule. SASE's own guide recommends independent tasks and sequencing dependencies; the research literature provides reasons to measure the added cost. It is a proposed personal policy until you confirm it reflects your practice. [S6][s6], [E4][e4].

   **Material to capture:** One task you split and one you kept sequential, with the reason. Include synthesis and repair effort. Different models and separate workspaces do not by themselves prevent contradictory assumptions or conflicting changes.

11. **Keep the agent CLI, own the workflow** — `keep_the_cli_own_the_workflow`, section `the_agent_cli`.

   **Proposed claim:** “SASE carries the work around an agent CLI invocation: its prompt, workspace, history, and completion workflow.”

   **Why add it:** Existing CLI records explain updates and costs, and the CEO-quote record argues for independence by authority. This gives the reader a concrete architectural boundary they can inspect. The provider CLI handles its model connection and authentication; SASE coordinates the surrounding work. [S9][s9], [S3][s3].

   **Material to capture:** A compact responsibility diagram or two-column table, using only a few responsibilities. Say which provider differences remain. Do not imply interchangeable capabilities, identical tool behavior, or that a reusable workflow is unique to SASE.

12. **Isolation needs an explicit meaning** — `what_workspace_isolation_means`, section `not_ready`.

   **Proposed claim:** “I need to distinguish keeping agents' edits separate from controlling what their processes are allowed to access.”

   **Why add it:** An introduction that uses “isolated workspaces” can unintentionally imply a security boundary. Documentation establishes separate working files and explicitly warns that a read-only prompt is not enforcement. That supports clarifying the terms; it does not substitute for auditing the provider configuration. [S2][s2], [S10][s10].

   **Material to capture:** Explain working-tree separation, approval decisions, and actual process/tool permissions separately. Document the configuration used in the demo before making stronger claims. A brief boundary statement may be enough for the introduction; a full security treatment can remain a separate article.

13. **Keep a useful process, replace an integration** — `integrations_are_replaceable`, section `plugins`.

   **Proposed claim:** “An engineering workflow should be able to keep its structure when an integration changes.”

   **Why add it:** This gives the empty plugins section a user benefit instead of an entry-point inventory. Current documentation identifies separate provider, VCS/workspace, artifact, and other extension surfaces. Treat the claim as an architectural aim with one demonstrated example, not universal portability. [S12][s12].

   **Material to capture:** Show one working extension, such as research artifacts or GitHub support, and explain the capability it adds. The creation and durable registration of this report could be an example once registration succeeds. Do not list every plugin hook in the introduction.

14. **Put work where its repository and tools are** — `work_on_the_right_machine`, section `fleet`.

   **Proposed claim:** “Remote dispatch lets me supervise work on another enrolled machine while that machine runs the agent.”

   **Why add it:** The fleet section is empty, while `why_a_tui` already mentions local files across your machines. This turns that motivation into a concrete reader benefit. The current runbook describes explicit enrollment, target credentials, and remote dispatch. [S13][s13].

   **Material to capture:** One real reason to use another machine—repository locality, installed tools, or available capacity—and the result visible from the controller. No remote launch was tested for this report. Keep platform setup out of the launch essay unless it is necessary to understand that example.

15. **Give me one workflow to improve** — `one_workflow_to_improve`, section `close`.

   **Proposed claim:** “The feedback I want first is a concrete account of where someone else's agent workflow becomes difficult to supervise.”

   **Why add it:** This fills the empty conclusion with a useful invitation, consistent with your earlier note about asking readers questions. It can attract evidence about the problem even from readers who are not ready to install alpha software.

   **Material to capture:** One small, documented first run and a short feedback prompt: what were you trying to accomplish, where did you lose track, and what evidence or control would have helped? Link the existing first-run guide and support destination; do not imply that every reader needs a fleet or a swarm. [S10][s10], [S1][s1].
