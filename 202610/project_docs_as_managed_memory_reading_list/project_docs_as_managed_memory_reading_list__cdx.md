# Documentation as project memory: structured content, authority, and maintenance

Independent research by **cdx**, 2026-10-15.

## Main finding

Your idea has strong precedents in technical communication, knowledge management, and software engineering research. The most useful direction is to treat project documentation as maintained, addressable knowledge that both humans and agents can use. Its location under `docs/` need not prevent it from participating in memory discovery, version history, links, or usage tracking.

My central recommendation is to distinguish **what knowledge says**, **who maintains it**, and **how an agent receives it**. A reference page, an operating rule, a design decision, and a record of a past investigation have different purposes and maintenance requirements. Making them equally accessible does not require giving them identical editing rules or loading them all into every prompt. This is my synthesis, rather than a design tested in SASE.

The strongest immediate reading combination is **Diátaxis**, Tom Manshreck's **Documentation** chapter, and selected **Knowledge-Centered Service** articles. Mark Baker supplies the missing connection between useful page structure and reliable automation. AdDoc and Hipikat supply particularly relevant research precedents for documentation maintenance and project memory.

## What I examined in SASE

I inspected the local SASE checkout at commit `c2c2ffd4df16b172cde950effee44eaeebd96a43`, including `docs/macros.md`, `docs/memory.md`, `docs/content_layout.md`, `docs/instruction_inventory.md`, and `mkdocs.yml`. I read the canonical `macros.md` memory and the relevant memory/artifact definitions through audited `sase memory read` calls.

Three observations shape the recommendations:

- `docs/macros.md` already exists and is substantial: 4,082 lines in this checkout. The corresponding memory note also describes invocation syntax, directives, discovery, and launch rules. The issue is therefore partly deciding which representation is authoritative and how the other representation should reach it.
- SASE already distinguishes always-loaded core memory from reference memory retrieved on demand. It also has authored links, generated instruction delivery, and recorded memory reads. Much of the useful management vocabulary already exists.
- The documentation navigation is mainly organized by subject and depth—Getting Started, Basics, Beyond the Basics, Nitty Gritty, Reference. A reader-purpose taxonomy could complement that navigation without requiring a wholesale directory rearrangement.

These are bounded observations, not a complete documentation audit. I did not modify SASE documentation or memory. I did not consult the other researchers' reports, transcripts, or findings.

## The ideas worth borrowing

### 1. Give content a purpose before choosing its folder

Diátaxis distinguishes learning a skill, performing a task, looking up facts, and understanding a subject. Its compass turns these into explicit classification questions. Its workflow also warns against imposing an empty four-part hierarchy before improving actual content. The useful unit of improvement can be a paragraph rather than an entire manual. [Diátaxis compass](https://diataxis.fr/compass/), [Diátaxis as a guide to work](https://diataxis.fr/how-to-use-diataxis/).

For SASE, I would evaluate a passage with questions such as:

| Passage's job | Appropriate treatment | Relevant example |
| --- | --- | --- |
| Describe public behavior precisely | Maintained technical reference | Argument grammar, discovery precedence, directive effects |
| Help someone achieve an outcome | Procedure with prerequisites and observable results | Define and invoke a reusable macro |
| Explain a mechanism or tradeoff | Explanation | Why expansion and directive extraction happen in a particular order |
| Constrain an agent's behavior | Explicit operating instruction | Required audited reads or the host-owned completion rule |
| Preserve why a choice was accepted | Historical decision record with supersession | Rationale behind an architectural boundary |
| Record an investigation or an individual run | Evidence/history with provenance | This report, command results, troubleshooting observations |

The last three rows extend beyond Diátaxis; they are my proposed distinctions for SASE. A general documentation taxonomy should not erase the difference between descriptive content and instructions that govern an agent.

Applied to your example, “move the macros memory into docs” is too coarse a description of the problem. Grammar and lookup material have a different job from execution constraints. The interesting design question is how one authoritative fact can remain discoverable from both the documentation site and the agent's task context.

### 2. Treat authority and delivery as separate properties

Tom Manshreck's chapter recommends canonical documents, clear ownership, source control, review, issue tracking, and periodic evaluation. It discusses freshness metadata that records who reviewed a document and when. These are useful ingredients for first-class management even when a Markdown site already builds successfully. [Documentation, Software Engineering at Google](https://abseil.io/resources/swe-book/html/ch10.html).

For SASE, I see three independent dimensions:

| Dimension | Question it answers | Example values |
| --- | --- | --- |
| Content purpose | What should the reader get from this? | Reference, explanation, procedure, operating instruction |
| Maintenance contract | What can change, and on what evidence? | Living description, generated projection, superseded historical record |
| Delivery | When should this reach an agent? | Always loaded, listed for discovery, retrieved for this task |

A human-readable page could be canonical reference knowledge and still be loaded only when needed. A short instruction could route the agent to that page without maintaining another grammar description. A generated reference table could have a different source of authority from the explanatory prose surrounding it.

The practical first-class capabilities I would look for are an identifiable subject, a useful discovery description, an owner, an observable version, a way to report an error, and an explicit retirement or supersession path. This is a design hypothesis about a shared management interface, not a proposal to impose a large metadata schema on every page.

### 3. Design pages for readers who arrive in the middle

Baker's Every Page is Page One approach emphasizes topics with a bounded purpose, enough local context, consistent patterns, and useful links. It assumes a reader may enter anywhere rather than read a manual in order. [Every Page is Page One](https://mbakeranalecta.github.io/spfe-open-toolkit/spfe-docs-essays/every-page-is-page-one.html).

My inference is that this is particularly useful for agents, which often arrive through a search result or a selected section. A useful retrieval unit should identify its subject and assumptions before giving detailed rules. References such as “as above” can become ambiguous when a section is extracted. A stable named section or coherent topic is a better maintenance boundary than an arbitrary token-sized chunk.

Self-containment does not require repeating the entire product overview. Nor does it imply one file per small fact. The useful target is the smallest coherent explanation, reference, or procedure that can be understood and reviewed in context.

Baker's separate essay on structured writing argues that repeatable content patterns enable automation and mechanical validation. For SASE, that suggests a small set of topic-specific templates: a procedure might need prerequisites, actions, and expected results, while a reference entry needs semantics and examples. A universal template with many empty fields would lose the benefit. [Creativity in Structured Writing](https://everypageispageone.com/2012/10/15/creativity-in-structured-writing/).

### 4. Connect maintenance to use and to changes

KCS's maintenance model is unusually relevant. Its articles describe capturing reusable knowledge during work, improving it when used, keeping article structure simple, and tracking confidence separately from audience and governance. These are practitioner methods developed for service organizations, rather than experiments on coding agents. [Reuse is Review](https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/030/040/020), [KCS Article Structure](https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010/020), [KCS Article State](https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010/030).

The adaptation I find most promising is a distinction between **read**, **used**, and **checked**. An agent reading a document proves access. Applying a procedure successfully supplies stronger, task-specific evidence. Reviewing a claim against implementation or an independent behavioral check supplies different evidence again. A recorded read should never automatically refresh a document's correctness claim.

Use-driven review also has a limit: rarely used documentation can still matter. An installation recovery procedure or architectural constraint may warrant review when its dependencies change even if nobody recently consulted it. Usage is one prioritization signal; dependency changes and consequence are others.

AdDoc provides a research precedent for change-driven maintenance. It recovers links between documentation and code, infers groups of code elements documented together, and recommends documentation changes when those patterns are disturbed. Its evaluation involved four Java projects. The transferable idea is to identify likely maintenance locations from a change, rather than asking an agent to reread all documentation. [Using Traceability Links to Recommend Adaptive Changes for Documentation Evolution](https://infobart.com/static/documents/tse2014.pdf).

For SASE, authored relationships to relevant subsystems, commands, configuration, or tests could be a simpler starting point than reproducing AdDoc's inference machinery. Such a relationship identifies a review candidate; it does not establish that every code change requires prose changes, or that an agent's proposed rewrite is correct.

### 5. Generate repeated facts when their semantics really match

Doherty's DITA overview distinguishes reuse by reference from copying text and explains direct references, keys, and the governance costs of reusable content. The OASIS map model separates topics from collections and their relationships. These are useful design ideas even if SASE keeps Markdown throughout. [How does OASIS DITA support content reuse?](https://acm-sigdoc-structured.org/postings/How-Does-OASIS-DITA-Support-Content-Reuse.pdf), [DITA maps](https://docs.oasis-open.org/dita/dita/v1.3/os/part1-base/archSpec/base/ditamaps.html).

I would distinguish a shared factual element—such as a list of recognized options—from separate explanations written for different readers. Reusing the former can prevent contradictions. Reusing a paragraph that assumes the wrong audience can make both outputs worse. Deep chains of text inclusion can also make ownership and review harder.

DScribe is a stronger automation example: it co-generates tests and documentation from shared template invocations. Its favorable results concern recurring API specifications, particularly exception behavior; they do not establish that arbitrary architecture prose can be verified this way. [Generating Unit Tests for Documentation](https://www.cs.mcgill.ca/~martin/papers/tse2021a.pdf).

A useful SASE principle would be: generate tables or examples where one structured source really expresses the same fact in each output; preserve authored prose for rationale, explanation, and judgment. A successful docs build checks only part of documentation quality.

### 6. Broaden memory's corpus while keeping context selective

Hipikat is the closest conceptual precedent for your first-class memory idea. It treats existing project records and the relationships among them as project memory, then recommends relevant material for a development task. Its evidence concerns human developers and Eclipse-era work, not LLM agents. [Hipikat: A Project Memory for Software Development](https://www.cs.ubc.ca/~murphy/papers/hipikat/hipikat-tse.pdf).

The implication I draw is that documents can participate in project memory while remaining ordinary project documents. Their usefulness comes from identity, connections, and accessibility, not from being copied into a specially named memory directory. Historical evidence still needs to be distinguished from the current supported behavior.

The empirical agent literature makes a separate point: merely adding context does not reliably improve outcomes.

| Study | What it actually supports | Important limit |
| --- | --- | --- |
| Gloaguen et al., *Evaluating AGENTS.md*, v3, 29 September 2026 | In SWE-bench Lite and 138 CTXbench tasks, neither generated nor developer context generally improved resolution significantly; costs increased. Generated files were often redundant with existing documentation. | Python tasks and particular model/harness configurations; not an evaluation of SASE's audited, task-specific retrieval. [Paper](https://arxiv.org/html/2602.11988v3) |
| Lulla et al., *On the Impact of AGENTS.md Files*, v2, 30 March 2026 | Paired runs over 124 PR tasks in 10 repositories reported 28.64% lower median runtime and 16.58% fewer output tokens with context files. | One Codex configuration and small code changes; efficiency results do not establish universally better correctness. [Paper](https://arxiv.org/html/2601.20404v2) |
| Khatri, *Do Context Files Help Coding Agents?*, July 2026 | Across 288 evaluated runs, 17 tasks, three repositories, and two agents, injection strategy did not measurably change correctness. | Small task sample; selective delivery also changed the available corpus in two repositories. It does not cleanly isolate delivery alone. [Paper](https://arxiv.org/html/2607.27250v1) |

These studies differ in tasks, metrics, content, and delivery. I would not average their percentages or treat them as a verdict that project knowledge is useless. The useful question for SASE is whether a particular fact or instruction helps a particular task enough to justify its retrieval and compliance costs.

A future design should be judged separately on answer accuracy, agent adherence to necessary constraints, effort spent locating knowledge, token/latency costs, and the human effort required to keep the corpus correct. A reduction in prompt size alone would not settle the matter.

## Reading selection and limits

I favored accessible primary sources with ideas that transfer to a Markdown repository. The research papers describe systems, evaluations, or taxonomies; the documentation frameworks and KCS guides are practitioner guidance. I inspected source texts and relevant methods/limitations, but did not reproduce experiments or inspect the implementations of the external systems.

Three useful sources sit outside the ranked core:

- Eric Holscher and the Write the Docs community's [Docs as Code](https://www.writethedocs.org/guide/docs-as-code/) is a concise description of shared tooling and workflow. Given SASE's existing Git/Markdown documentation, its incremental value is lower than the material on authority, structure, and maintenance.
- Aghajani et al.'s [Software Documentation Issues Unveiled](https://www.inf.usi.ch/lanza/PUBS/P/Agha2019a.pdf), ICSE 2019, organizes documentation problems across content, presentation, process, and tools. It is useful background for resisting the assumption that changing file locations solves documentation quality.
- Anthropic's [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), 29 September 2025, discusses selective retrieval and structured persistent notes. **Already in your library: started**, legacy entry added 2025-11-04, at `ref/ai/claude_code_ref/effective_ctx_engineer.md`. It is relevant background, rather than a new discovery here.

The two companion agent studies and the OASIS map specification are linked above. They serve as counterevidence and technical background, rather than adding more items to the main reading queue.

I checked all 19 candidate URLs/DOIs in one final batched `bob ref find` lookup. One matched an existing started item; 18 returned `not_found`. That means absent from the indexed `ref/` library under those identities, **not** that you have never read them. Intake was not checked. A small, capped sample of finished external references showed substantial prior interest in agent memory and harnesses; I therefore prioritized documentation-specific material over another general memory-system survey.

## Ranked articles and papers to consider reading

Rank reflects likely usefulness for your stated questions, not publication prestige. If you want a short initial queue, read **1–4**, then choose **5** for maintenance automation or **6** for the broader project-memory model.

1. **Daniele Procida — [Diátaxis](https://diataxis.fr/), especially [The compass](https://diataxis.fr/compass/) and [Diátaxis as a guide to work](https://diataxis.fr/how-to-use-diataxis/).** Living practitioner framework. The best first read for deciding what belongs in a reference, procedure, explanation, or tutorial. The workflow is as valuable as the taxonomy: improvements can start locally without a directory-wide reorganization. Read it with a few passages from the macros memory and docs beside you, asking what each passage helps its reader do. Its human learning/work distinction is useful for agents, but agent instructions and historical records still need their own treatment.

2. **Tom Manshreck — [Documentation](https://abseil.io/resources/swe-book/html/ch10.html), in *Software Engineering at Google* (2020), edited by Riona MacNamara.** The strongest practical source for what “first-class” management should entail. Focus on “Documentation Is Like Code” and “Deprecating Documents”: canonical authority, owners, normal engineering workflows, and review/freshness practices. It directly addresses the gap between having Markdown files and having a maintainable knowledge system. The organizational scale differs from SASE, so borrow the ownership and lifecycle principles without importing Google's process overhead.

3. **Consortium for Service Innovation — [Reuse is Review](https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/030/040/020), [KCS Article Structure](https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010/020), and [KCS Article State](https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010/030), from the KCS v6 Practices Guide.** Three short companion readings from a living guide first released in 2016. Best for making maintenance part of actual work: reusable knowledge, simple templates, improvement during use, and confidence distinct from visibility or editing authority. For SASE, the key adaptation is distinguishing a document read from a successful application or correctness review. Support-organization practices do not automatically transfer to coding agents.

4. **Mark Baker — [Every Page is Page One](https://mbakeranalecta.github.io/spfe-open-toolkit/spfe-docs-essays/every-page-is-page-one.html).** Freely accessible author essay summarizing his topic-based writing approach; the available page was generated in 2018. Read for bounded topics, local context, consistent patterns, and navigable relationships. This is the best bridge between a human-friendly documentation set and selective agent retrieval. The idea to test is whether a topic still makes sense when an agent reaches it directly. Do not interpret it as requiring hundreds of tiny files or eliminating all overview pages.

5. **Barthélémy Dagenais and Martin P. Robillard — [Using Traceability Links to Recommend Adaptive Changes for Documentation Evolution](https://infobart.com/static/documents/tse2014.pdf), IEEE TSE 40(11), 1126–1146 (2014); [DOI](https://doi.org/10.1109/TSE.2014.2347969).** The most directly useful research paper for scriptable maintenance. Read the worked examples, the documentation-pattern model, and limitations before the algorithmic details. It shows how relationships between documented code elements can identify likely additions, removals, and stale references. Its retrospective Java-project evaluation supports targeted recommendations, not autonomous prose correctness. For SASE, explicit subsystem-to-document relationships may capture much of the initial value with less machinery.

6. **Davor Čubranić, Gail C. Murphy, Janice Singer, and Kellogg S. Booth — [Hipikat: A Project Memory for Software Development](https://www.cs.ubc.ca/~murphy/papers/hipikat/hipikat-tse.pdf), IEEE TSE 31(6), 446–465 (2005); [DOI](https://doi.org/10.1109/TSE.2005.71).** The closest paper to your conceptual question. Its project memory comprises existing development records and typed relationships; access is driven by the current task. Focus on Section 3's model and Section 7's discussion. The useful inspiration is making already-produced knowledge accessible without requiring a second manually maintained knowledge base. The empirical work is about human newcomers, and retrieved history still requires interpretation; it does not validate an LLM retrieval architecture.

7. **Thibaud Gloaguen et al. — [Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?](https://arxiv.org/html/2602.11988v3), arXiv:2602.11988, v3 (29 September 2026).** The most useful empirical restraint on a documentation-as-memory redesign. Read the behavioral analysis, limitations, and Appendix B's documentation-removal experiment. The point is to evaluate added guidance rather than presume benefit from its existence. Use the September revision: its main finding is no general significant resolution benefit, rather than the stronger claim that context universally worsens performance. It evaluates repository context files, not every possible form of task-specific documentation retrieval. The two studies in the comparison table are worthwhile companions if you want to examine the conflicting efficiency evidence.

8. **Mathieu Nassif, Alexa Hernandez, Ashvitha Sridharan, and Martin P. Robillard — [Generating Unit Tests for Documentation](https://www.cs.mcgill.ca/~martin/papers/tse2021a.pdf), [2020 preprint](https://arxiv.org/abs/2005.08750); IEEE TSE [DOI](https://doi.org/10.1109/TSE.2021.3087087).** Read for the mechanism: one template invocation produces corresponding documentation and tests. This suggests how repeatable behavioral facts can have a maintained executable connection to their prose representation. The reported 97% generation coverage comes from a favorable evaluation of recurring specifications, not all documentation. It is inspiration for carefully chosen reference facts and examples, with much less applicability to architecture explanations or policy rationale.

9. **Stanley Doherty — [How does OASIS DITA support content reuse?](https://acm-sigdoc-structured.org/postings/How-Does-OASIS-DITA-Support-Content-Reuse.pdf), ACM SIGDOC Structured Content resource, ©2025.** A concrete primer on reuse by reference, stable keys, reusable blocks, and the costs of managing shared content. The PDF's revision table contains inconsistent 2024 ordering, so the copyright year is the least ambiguous date to cite. Read the best-practices section as carefully as the syntax examples. Borrow the distinction between identity and file location, and the caution about tangled inclusion dependencies. The [OASIS map overview](https://docs.oasis-open.org/dita/dita/v1.3/os/part1-base/archSpec/base/ditamaps.html) is a useful companion. Adopting these ideas does not require adopting XML or the DITA toolchain.

10. **Mark Baker — [Creativity in Structured Writing](https://everypageispageone.com/2012/10/15/creativity-in-structured-writing/) (15 October 2012).** A short conceptual complement to the automation papers. Its most useful move is treating good templates and validation rules as designed products of subject-matter understanding. For SASE, this encourages a few meaningful document forms that agents can follow and check, instead of cosmetic Markdown consistency alone. It is a practitioner argument, not experimental evidence, and its industrial-production framing should be tempered by the need for flexible explanatory prose.

11. **Andy Clark and David J. Chalmers — [The Extended Mind](https://consc.net/papers/extended.html), *Analysis* 58, 10–23 (1998).** Optional philosophical inspiration after the practical sources. It explores how accessible external records can participate in remembering and reasoning. Use it to sharpen what “documentation is memory” should demand: reliable access, dependable integration into activity, and a meaningful relationship between stored information and action. It is not evidence about LLMs and does not justify treating every stored document as an authoritative belief. Its value here is improving the design questions rather than supplying an implementation.

Library check: 1 of 19 candidates already in your library (0 finished).
