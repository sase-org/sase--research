---
title: "Documentation as a source of SASE memory: selective migration and source-backed references"
researcher: cdx
date: 2026-10-15
status: research-recommendation
---

# Documentation as a source of SASE memory

**Recommendation:** Proceed with selective migration. Put shared product knowledge in canonical Markdown documentation, retain a small agent instruction and routing layer, and let selected documentation pages supply the content of existing reference-memory entries. Start with a bounded macros pilot. Do not make the docs tree always-loaded memory, apply every memory policy to ordinary documentation, or introduce another retrieval platform.

The valuable change is reducing independently maintained accounts of the same behavior while making the right material easier to find and verify. Moving files alone will not accomplish that. SASE needs explicit contracts for canonical content, discovery, agent authority, read provenance, and maintenance.

## Scope and evidence

This is independent research by researcher cdx. I did not inspect the cld, grk, or gem reports, their conversations, or their findings. I inspected SASE and opened sase-core through the required repository workflow. Canonical memory was consulted through audited reads. No source code, canonical memory, skills, or documentation was changed for this investigation.

Local observations refer to SASE commit **c2c2ffd4df16b172cde950effee44eaeebd96a43** and sase-core commit **6f422072410d95b6592e0bcda124d39e09a46b23**. The installed CLI and audited project/home memory can differ from checkout resources.

External sources are primary documentation and original research. Vendor advice is a design precedent, not experimental proof. The empirical studies below examine repository instruction files, not SASE's proposed document-backed reference reads; their results inform evaluation, not a direct estimate of this change's benefit.

## 1. What the existing system establishes

SASE already has much of the necessary infrastructure:

| Existing capability | Consequence |
| --- | --- |
| Core notes are inlined; reference notes are advertised and read on demand. | A document does not need to become always-loaded to be first class. |
| Reference reads record attribution, reasons, and content identities. | A move must preserve evidence of the document bytes actually delivered. |
| Memory webs provide keyed strands and authored links. | Documentation does not itself justify another graph or taxonomy. |
| Instruction bundles have manifests, hashes, provenance, and caches. | New sources need deliberate manifest/cache behavior. |
| MkDocs navigation, formatting, strict builds, and PDF publication already exist. | Improve this publishing system rather than replace it. |
| Model reference tables are generated from a manifest. | Deterministic generated documentation is already an accepted pattern. |
| A refresh workflow proposes an update followed by a polish pass. | Improve targeting and verification before adding another generic refresh agent. |

These capabilities are documented or implemented in [memory](https://github.com/sase-org/sase/blob/c2c2ffd4df16b172cde950effee44eaeebd96a43/docs/memory.md), [instruction bundles](https://github.com/sase-org/sase/blob/c2c2ffd4df16b172cde950effee44eaeebd96a43/docs/instruction_bundles.md), [MkDocs configuration](https://github.com/sase-org/sase/blob/c2c2ffd4df16b172cde950effee44eaeebd96a43/mkdocs.yml), [model-doc generation](https://github.com/sase-org/sase/blob/c2c2ffd4df16b172cde950effee44eaeebd96a43/tools/render_model_docs), and [documentation refresh](https://github.com/sase-org/sase/blob/c2c2ffd4df16b172cde950effee44eaeebd96a43/src/sase/scripts/sase_chop_refresh_docs.py).

The macros example is concrete. The audited macros.md memory contains invocation grammar, directives, definition/discovery rules, and launch guidance. It already points to docs/macros.md for details. Meanwhile, docs/macros.md is **4,082 lines**, covers many of the same subjects, and mixes reference, procedure, explanation, and compatibility material. The problem is competing maintenance surfaces and retrieval granularity, not the absence of a manual. [Memory's repository source](https://github.com/sase-org/sase/blob/c2c2ffd4df16b172cde950effee44eaeebd96a43/sase/memory/macros.md), [existing manual](https://github.com/sase-org/sase/blob/c2c2ffd4df16b172cde950effee44eaeebd96a43/docs/macros.md).

A simple move also fails technically. The audited flat-note reader requires a flat Markdown note under the selected memory root and rejects resolved paths outside it. Symlinking into docs is not a supported shortcut. Current read kinds are note, web, and strand. [Validator](https://github.com/sase-org/sase/blob/c2c2ffd4df16b172cde950effee44eaeebd96a43/src/sase/memory/_read_log_paths.py), [event models](https://github.com/sase-org/sase/blob/c2c2ffd4df16b172cde950effee44eaeebd96a43/src/sase/memory/_read_log_models.py).

## 2. Is this a good idea?

**Yes, for shared explanatory and reference content.** A human and an agent should normally consult the same account of macro parsing, configuration precedence, and public API behavior. Shared canonical material reduces the places a behavior change must be reconciled.

**It becomes a poor idea if “documentation is memory” erases useful distinctions.**

| Material | Primary job | Recommended treatment |
| --- | --- | --- |
| Product reference and explanation | Describe how SASE works | Canonical docs; selected pages available through reference memory |
| Agent operating constraints | Govern how an agent works | Small explicit instruction/routing layer |
| Skills | Execute repeatable workflows | Existing source and generation lifecycle |
| Accepted decisions | Preserve why a choice was made | Immutable records with supersession; link from live docs |
| Research reports | Preserve investigation and uncertainty | Research artifacts; deliberate promotion of conclusions |
| Personal or machine-specific knowledge | Support private environments | Appropriate home/private scope |
| Live runtime state | Report what is happening | Query the authoritative service/store |

A documentation page can contain imperative steps without acquiring authority over the agent's session. An example command is not permission to run it. Conversely, moving a binding agent rule into a public manual must not make the rule optional because its path changed.

The key distinction is **content role versus delivery policy**. “Reference” in a documentation taxonomy describes a reader's need. “Reference memory” in SASE describes how context arrives. A how-to page can be reference memory. A core operating constraint can point to a reference manual.

Over-management has costs. If editing an explanatory page requires the complete authorization/regeneration procedure for a policy note, maintenance becomes harder. Share identity, validation, provenance, and history without treating every prose edit as an instruction-policy change.

## 3. What external evidence suggests

### Documentation types improve topics; they need not dictate the entire tree

Diátaxis distinguishes tutorials, how-to guides, reference, and explanation. Its application guidance favors small improvements and warns against imposing empty top-level structures. Use that distinction when splitting a mixed page or writing a topic; do not begin by relocating the whole site into four folders. [Application guidance](https://diataxis.fr/how-to-use-diataxis/), [framework overview](https://diataxis.fr/).

GitLab offers a complementary precedent: concept, task, reference, and troubleshooting topics, with multiple well-formed topics permitted on a page. This supports pragmatic task-sized units rather than giant manuals or a file for every paragraph. [GitLab topic types](https://docs.gitlab.com/development/documentation/topic_types/).

### Canonical documentation can feed agent instructions

GitLab identifies its documentation style guide as canonical; agent authoring files either point to it or are generated from it. Generated authoring/review material is not edited independently. This closely matches SASE's duplication problem. It does not imply that SASE needs GitLab's distillation pipeline. Prefer direct reads and deterministic projections; generated semantic summaries need a demonstrated benefit and review. [GitLab agent instruction architecture](https://docs.gitlab.com/development/documentation/ai-instruction-files-documentation/).

### More context is not automatically better

Anthropic recommends lightweight references and loading relevant information during execution. It also acknowledges navigation and latency costs. This supports short routing plus targeted reads, while cautioning that simply withholding information can make discovery worse. [Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

Empirical findings are mixed:

- Gloaguen and colleagues' September 2026 revision reports that repository context files did not generally improve success and increased average inference cost by more than 20%. It distinguishes useful non-standard practices from repository overviews that did not help. [Evaluating AGENTS.md, v3](https://arxiv.org/abs/2602.11988v3).
- Lulla and colleagues studied 124 pull requests across 10 repositories and report an association with 28.64% lower median runtime and 16.58% lower output-token consumption, with comparable completion behavior. [On the Impact of AGENTS.md Files, v2](https://arxiv.org/abs/2601.20404v2).

These settings and measures differ; the percentages should not be combined. They justify local evaluation of correctness, policy adherence, retrieval effort, input/output tokens, and runtime separately. Neither study establishes that deleting SASE memory, or loading all docs, would improve results.

### Structural checks do not establish factual accuracy

GitLab uses metadata and documentation checks for ownership, style, structure, and links. Adopt a smaller version suited to SASE's maintenance context. [Metadata](https://docs.gitlab.com/development/documentation/metadata/), [documentation testing](https://docs.gitlab.com/development/documentation/testing/).

MkDocs supports configurable link/anchor diagnostics. Strict mode makes warnings fatal, but some diagnostics, including anchor validation in the documented defaults, are informational until configured otherwise. A strict build alone does not prove every broken section link fails CI. [MkDocs validation](https://www.mkdocs.org/user-guide/configuration/#validation).

## 4. Adjustments to the proposed requirements

I recommend these explicit changes to the original idea:

1. **Replace “migrate memories to docs” with “reconcile canonical content by role.”** Some notes move, some shrink, and some stay. Generated notes require generator changes rather than relocation of generated output.
2. **Define first class as selected, discoverable, versioned, attributable, and maintainable.** It need not mean always-loaded, automatically mandatory, or eligible for every memory operation.
3. **Make agent delivery opt-in.** Docs remain browseable without enrollment in the instruction surface. Only selected pages get reference entries.
4. **Preserve task guidance independently of location.** Short descriptions still tell agents when reads are required; ordinary links provide further discovery.
5. **Keep one authored home for each maintained contract.** Avoid independent human and agent variants. Useful summaries/examples may restate facts, with links; exact tables should be generated when a stable schema exists.
6. **Evaluate behavior and maintenance cost.** Fewer lines in memory or more metadata fields are not success measures.
7. **Start with same-repository docs in this project.** Home scope, plugins, external repos, and public exports retain explicit boundaries.
8. **Separate living documentation from historical evidence.** Decisions and research do not become manuals merely because they are Markdown.

These are recommended requirement changes, not claims that the original request already demanded them.

## 5. Options and tradeoffs

| Approach | Benefit | Main cost/failure mode | Judgment |
| --- | --- | --- | --- |
| Move prose to docs; keep ordinary memory pointers | Fast cleanup, little runtime work | Auditing the pointer does not prove its target was delivered | Useful content experiment; insufficient alone for audited delivery |
| Selected reference notes obtain their bodies from docs | Reuses selectors, descriptions, skills, and audit entry point | Coordinated reader, macro, provenance, and UI work | Recommended incremental implementation |
| Discover every docs page as memory from frontmatter | Direct document enrollment | Larger catalog and broader discovery/precedence changes | Reconsider only after a selected-reference pilot |
| Generate agent excerpts from docs | Compact delivery | Independent summaries drift or omit constraints | Initially only explicit deterministic extraction |
| Replace docs/memory with a generic graph or RAG service | Broad future querying | New indexing/storage/quality problems ahead of demonstrated need | Reject now |

The second option uses a small existing control surface rather than another authoring copy. A descriptor duplicates routing metadata, not reference prose.

This respects the project's audited “No Retrieval Mechanism Before Its Corpus” decision. The macros overlap is evidence for source reuse and better units. It is not evidence for embeddings, automatic semantic capture, or another graph. The decision was reviewed through an audited read of decisions:corpus-before-mechanism.

## 6. Recommended representation: documentation-backed reference notes

Keep docs as human-readable Markdown. Keep existing memory notes as identity and delivery-control entries. Add one explicit capability: a reference note may obtain its body from a local documentation source.

This is **proposed metadata, not supported configuration today**:

~~~yaml
# sase/memory/macro_invocation.md
---
type: reference
description: Read before editing macro invocation or argument parsing.
content_source:
  path: docs/macros/invocation.md
---
~~~

The document holds the actual reference text. The descriptor supplies the selector, read trigger, and enrollment decision. It does not hold a manually maintained abridgment of the same grammar.

Initially:

- Support one complete Markdown page per descriptor.
- Limit the feature to reference notes.
- Make source content exclusive: reject an ambiguous independently authored descriptor body plus external body.
- Resolve relative to the selected descriptor's owning project, not an arbitrary working directory.
- Allow only the declared documentation root in the same repository.
- Leave unregistered pages as ordinary docs.

The existing command shape remains useful:

~~~sh
sase memory read macro_invocation.md -r "Check the argument grammar before changing parsing"
~~~

This avoids a new memory tier, another CLI family, and a collision between proposed doc: selectors and existing web selectors.

A descriptor is justified when a page needs a stable agent entry point. Do not enroll every blog post, image brief, release note, or sidebar.

### Start with complete pages

Whole pages simplify identity, links, diffs, and provenance. They also encourage splitting oversized reference material at meaningful boundaries.

Do not begin with line ranges, arbitrary heading-text matching, extraction fences scattered through prose, or recursive includes. Those create another authoring language. If real usage shows a coherent page is still too large, add stable section identifiers and Markdown-aware extraction. Missing or duplicate identifiers should error; never silently deliver a whole large file after a section disappears.

### Apply this to macros incrementally

Do not rename the memory into another copy of the existing manual. Pilot invocation and arguments:

1. Compare the relevant memory and manual sections against implementation and behavior tests.
2. Reconcile disagreements; neither prose source is automatically correct.
3. Establish one canonical invocation page; replace overlapping manual text with links or useful explanation.
4. Expose that page through a reference descriptor.
5. Reduce macros.md memory only once its remaining operating rules and routing responsibilities have explicit homes.

The old selector can remain an orientation/routing note during transition. Reading it does not prove linked references were read. Selector compatibility differs from preserving the old delivered body; intentional changes to #memory/macros expansion require documentation and verification.

## 7. Implementation contracts

Adding a source field is easy. Making it consistent across SASE is the substantive work.

### Use one resolver across access paths

Source selection must agree across audited reads, human show/preview, #memory/... expansion, and navigation/edit targets. Otherwise a running agent and launch-time prompt can receive different accounts through the same reference.

This includes Rust-owned macro catalog behavior. Core tests cover namespaced memory loading and editor navigation; a Python-only shortcut could leave expansion reading an empty adapter body. [Core memory-macro tests](https://github.com/sase-org/sase-core/blob/6f422072410d95b6592e0bcda124d39e09a46b23/crates/sase_core/src/macro_catalog/tests/memory.rs).

Follow the backend boundary: new shared resolution/validation belongs in sase-core with bindings and thin Python adapters. Update the SASE revision pin when new bindings are called. No unrelated memory rewrite is needed.

### Audit selection and delivered content

A successful read should establish:

- Requested memory identity and selected project/home origin.
- Descriptor path and content identity.
- Resolved document path and source identity.
- Exact delivered body, or its digest and a reliable recovery path.
- Agent attribution, reason, and read status.

Hashing only the descriptor creates false confidence: the document can change while the reported reference version appears unchanged. A blob OID identifies content; it does not prove uncommitted bytes were stored and remain recoverable. Use appropriate existing per-run artifact/snapshot facilities rather than permanent explicit artifacts for every read.

Keep requested references distinct from extra context. Followed links should not inflate read counts. Existing #memory/... expansion is launch composition and intentionally produces no memory-read event; preserve that distinction and capture provenance through the launch path.

### Fail visibly on invalid sources

A selected project descriptor with a missing source should fail that read. Do not silently fall back to home, reuse old cached bytes, or print only the descriptor and report success.

Validate containment and real paths. Cross-repo reads must not happen incidentally through a relative path or symlink; they have an existing audited workflow.

Documentation links remain documentation links. Wiki-like syntax in code examples must not accidentally trigger memory closure expansion. Initial document reads should not recursively include linked pages.

### Model actual cache dependencies

The instruction cache fingerprints memory trees and other known inputs; it does not generically fingerprint docs. [Cache implementation](https://github.com/sase-org/sase/blob/c2c2ffd4df16b172cde950effee44eaeebd96a43/src/sase/instructions/cache.py).

If only the descriptor description contributes to a bundle, a body-only docs edit need not invalidate that bundle. When content or derived metadata contributes to a bundle, catalog, preview, or expansion cache, it must affect that cache key. Track dependencies instead of hashing every docs asset on each launch.

### Make history and edit behavior honest

The Memory panel should identify a document-backed body. “Edit body” opens the document; routing metadata opens the descriptor. Generated output is not canonical input.

For an initial release, accurate read provenance and source-file history navigation suffice. Rich combined history can follow. Existing history derives subjects from memory roots and uses a closed kind vocabulary; a source pointer does not automatically add document lineage. [Core history contracts](https://github.com/sase-org/sase-core/blob/6f422072410d95b6592e0bcda124d39e09a46b23/crates/sase_core/src/memory_history/wire.rs).

Do not present descriptor-only history as the complete history of delivered knowledge.

### Ship support before migrating data

Older readers may ignore unknown frontmatter. A source-only note could then expand to nothing. Land reader support and bindings before authoring live source-only entries, and establish minimum installed SASE/core versions.

The global sase command and a checkout's development environment are distinct. Generated skill sources also have their own deployment procedure. Editing the repository does not update every running agent. No global installation or deployment is part of this research task.

## 8. Structure documentation for maintenance

Introduce topic groups where the content needs them. A possible macros group is:

~~~text
docs/
  macros.md                 # retain the existing landing URL during transition
  macros/
    index.md                # orientation and task map
    invocation.md           # focused grammar/reference contract
    authoring.md            # how to define a macro
    directives.md           # directive reference
    discovery.md            # precedence reference
~~~

This is an illustrative local improvement, not a mandated layout for every subsystem. Split directives further only when tasks justify it.

Use MkDocs redirects when pages move. Redirects do not automatically preserve every deep link; retain anchor aliases or explicitly map/check important old fragment links.

A small documentation contract should establish:

- One primary purpose and clear title.
- Predictable sections appropriate to the page's kind.
- Canonical reference facts distinguished from tutorial scaffolding and historical commentary.
- Ordinary Markdown navigation.
- Relevant implementation/schema/test pointers.
- Generated content explicitly marked with its generator.

Optional pilot metadata can be minimal:

~~~yaml
---
doc_kind: reference
summary: Macro invocation syntax and argument parsing.
---
~~~

Use doc_kind, avoiding confusion with memory's type: reference delivery field. The descriptor description answers “when must an agent read this?”; the document summary answers “what is here?”

Add related-code mappings only when an automation consumes them. Prefer maintained subsystem mappings to a claim that every sentence has a complete dependency graph. For a solo maintainer, repeating the same owner on every page adds little. Add ownership when there is a real routing choice.

Avoid mandatory hand-updated “last verified” dates: these can become ritual stamps. Record the revision, command, test, or schema checked when verification matters. Maintain present-tense product docs; keep release chronology in historical material. [Google's timeless documentation guidance](https://developers.google.com/style/timeless-documentation).

## 9. Make agent maintenance targeted and reviewable

The existing refresh workflow already asks an updater and a subsequent reviewer to check behavior. Improve its targeting and evidence before adding orchestration.

A maintenance task should provide:

~~~text
Changed behavior:
  A concrete before/after description, or the changed code/schema range.

Affected documentation:
  Known canonical pages and reference descriptors.

Verification evidence:
  Commands, tests, schema fields, or source locations supporting changed claims.

Expected output:
  A scoped patch; changed contracts; unresolved discrepancies.
~~~

The working loop is: identify affected topics, check authoritative behavior, update the canonical page, update routing only when necessary, regenerate deterministic derivatives, run documentation checks, and review semantic disagreements.

Related-code mappings and changed-file heuristics should suggest candidates. They should not mandate edits for every source change; many refactors change no documented contract.

Generate exact tables from CLI/schema/config sources where the source and renderer are stable. Keep rationale and procedures authored. Do not execute every shell fence: examples can be incomplete, expensive, or illustrative. Opt selected examples into existing hermetic checks when they catch meaningful regressions.

| Deterministic checks | Review judgments |
| --- | --- |
| Missing source; invalid metadata; duplicate identity; path escape | Whether text describes actual behavior |
| Broken local links and registered anchors | Whether topic boundaries help readers |
| Stale generated blocks | Whether evidence supports a changed claim |
| Macro/read resolver disagreement | Whether a normative policy changed |
| Missing navigation or intentional exclusion | Whether an omission matters |

Let CI reject broken invariants. Have agents present evidence for judgments. A green documentation build does not establish factual accuracy.

## 10. Preserve policy ownership across paths

The migration can accidentally change authorization. /sase_memory_write governs canonical memory, while ordinary docs-refresh tasks have broad documentation scope. A document-backed policy could effectively rewrite future instructions without touching the memory directory.

Use this rule:

- Informative docs remain ordinary documentation.
- Enrollment, read triggers, core/reference policy, and binding operating constraints remain explicitly managed instruction content.
- If a document source owns binding policy, mark that source/section and carry the existing memory authorization rules to it.

Guards should use effective content roles, not only path prefixes. Do not protect the entire docs tree because some pages supply reference bodies.

For the first macros pilot, retain binding operating rules in current instruction/skill sources and migrate descriptive grammar first. This minimizes authorization changes while testing source reuse.

Keep personal home material out of public exports. Keep decisions immutable except for established supersession. A live architecture overview can link to historical decisions; revising it should not rewrite those decisions.

## 11. Rollout and evaluation

This is research, not an approved implementation plan or authorization to change particular notes. A later formal plan must carry the per-note memory decisions required by /sase_memory_write.

### Establish a bounded pilot

Choose macro invocation/arguments. Record present overlap and contradictions. Prepare a canonical task-sized page and task map while preserving existing memory coverage until reader support is ready. Do not combine this with a site-generator migration, every-memory rewrite, or new search system.

If ordinary pointers/file navigation already solve the practical problem, keep that simpler arrangement until audited document delivery or consistent expansion demonstrably matters. Be explicit that pointer auditing covers only the pointer.

### Implement source-backed references

Implement shared resolution/validation, audited delivery, matching expansion, and basic navigation. Add focused behavior tests for the failure cases above. Retain meaningful selectors. Mark proposed metadata unsupported until the compatible runtime is deployed.

This stage should add no always-loaded document bodies. Use the existing default verification checks and relevant docs build; the proposal does not call for agent-initiated exhaustive verification.

### Migrate and assess

Use roughly 12–20 representative tasks as an exploratory acceptance set, not a statistically conclusive benchmark. Include:

- Finding argument-escaping rules.
- Editing directive or precedence behavior.
- Writing a valid macro.
- Distinguishing a workflow description from execution permission.
- Following a legacy entry point.
- Encountering a missing/renamed document.
- Reading an uncommitted source revision.
- Doing unrelated work that should not load macro references.

Where practical, compare baseline and proposal on the same task, snapshot, model, and tools. Repeat a subset to expose variability.

Measure correctness and adherence first, then retrieval turns, total tokens, latency, and maintenance effort. Include one controlled behavior change: count independently authored locations needing updates and check for competing normative copies.

Suggested acceptance criteria—design targets, not research findings:

- Designated critical rules remain discoverable and followed.
- Successful reads identify actual delivered content.
- Missing sources, path escapes, and incompatible expansion fail visibly.
- No increase in always-loaded document bodies.
- One canonical prose contract for the controlled behavior edit.
- No added loading obligations for unrelated work.
- Useful navigation and evidence for the human maintainer.

A small test set cannot prove there is no regression. Investigate failures and high variance before extending the rollout.

### Expand only after evidence

Review other memories by role. Candidates may include shared CLI, development/test, and public workflow explanations. Retain agent-specific constraints and read triggers. Generated artifact/bead guidance must be considered through its canonical generator, not by moving generated files.

Keep advanced extraction, automatic all-doc enrollment, global IDs, semantic search, automatic research promotion, rich unified history, and generated summaries out of the initial scope. Each needs demonstrated demand and a separate tradeoff decision.

## 12. What would change this recommendation?

I would keep a pointer-only arrangement indefinitely if audited delivery and expansion consistency do not justify their integration cost.

I would consider direct document enrollment from frontmatter if maintaining adapter descriptors becomes burdensome across many stable canonical pages. At that point the corpus might justify a common catalog.

I would consider section extraction if task-sized pages still cause large irrelevant reads. I would consider additional search only after measured failures show the task map, titles, links, and existing search tools are insufficient.

I would stop or revise migration if it hides operating rules, increases irrelevant context, produces competing summaries, or makes ordinary edits more cumbersome than the duplication it removes.

## Recommended solution

**Adopt canonical documentation with a small, opt-in agent reference layer.** Reconcile and split macros first; retain binding operating rules in explicit instructions; let selected reference notes source their body from same-repository docs through one shared, audited resolver. Reuse SASE's selectors and management surfaces while preserving distinct semantics for reads, launch expansion, history, and authorization.

Treat the first release as a bounded compatibility feature and content pilot. Improve maintenance through task-sized topics, minimal metadata, deterministic checks, and evidence-focused refresh work. Expand only after the pilot improves maintenance while preserving agent behavior. This obtains the useful part of “documentation as memory” without turning the whole manual into an instruction bundle or building another knowledge-management system.
