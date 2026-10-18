# Mermaid diagram handoff for research swarms

Researcher: cdx. Research date: 2026-10-18.

The request is to let the research swarm’s image agent decide whether diagrams would help, create them without changing the lead report or writing another report, and hand them to the linker for integration. This investigation was conducted independently. No reports, transcripts, or findings from the other researchers in this swarm were consulted. This is a design recommendation, not an implementation.

The proposal is sound. Keep one publisher: the linker. Give the image agent a small, registered **JSON diagram packet** containing Mermaid source, captions, supporting passages, and explicit placement selectors against the lead’s immutable report snapshot. Zero diagrams must be a valid, explicit outcome. The linker should validate each proposal, associate it with the source content before restructuring, and embed accepted diagrams as ordinary Mermaid fences beside the corresponding final prose.

A consequential finding is that **Bob’s current Markdown-to-PDF implementation already renders Mermaid fences as vector figures**. Adding a new renderer, generating PNG copies of every diagram, or embedding SVGs is unnecessary for this workflow. The missing capability is the handoff and editorial contract.

## What the current implementation actually does

These observations come from checked-out source, rather than assumptions about a generic agent pipeline. Repository revisions and source links appear below.

- **The plugin owns the workflow.** `sase-research-artifacts` supplies `research_swarm.md`, `research_image.md`, and the research artifact and Highlights hook providers. Its image branch is optional; `image=true` implies the linker. The lead writes `<name>__final.md` when the linker runs, while the linker alone publishes `<name>.md`. [Swarm definition](https://github.com/sase-org/sase-research-artifacts/blob/17623956c379f580ad1931c927df0093d51feb91/src/sase_research_artifacts/xprompts/research_swarm.md#L81-L150).
- **The dependency graph is already suitable.** The image agent waits for and forks from the lead. The linker waits for the lead and each enabled image/audio agent. Audio runs alongside image work and uses the lead’s report. No additional agent or scheduler edge is necessary for optional Mermaid creation inside the existing image stage. [Image and linker branches](https://github.com/sase-org/sase-research-artifacts/blob/17623956c379f580ad1931c927df0093d51feb91/src/sase_research_artifacts/xprompts/research_swarm.md#L269-L312), [audio branch](https://github.com/sase-org/sase-research-artifacts/blob/17623956c379f580ad1931c927df0093d51feb91/src/sase_research_artifacts/xprompts/research_swarm.md#L483-L484).
- **Image instructions are currently minimal.** `research/image` asks for one `<stem>_infographic.png`, strips a trailing `__final` from the stem, and forbids overwriting an existing image. It has no Mermaid assessment, source-binding, placement, validation, or explicit “none needed” protocol. The configured image role uses general-purpose agents, so authoring Mermaid text is compatible with the role; it need not go through a bitmap image generator. [Image macro](https://github.com/sase-org/sase-research-artifacts/blob/17623956c379f580ad1931c927df0093d51feb91/src/sase_research_artifacts/xprompts/research_image.md), [model configuration](https://github.com/sase-org/sase-research-artifacts/blob/17623956c379f580ad1931c927df0093d51feb91/src/sase_research_artifacts/default_config.yml#L1-L14).
- **The linker does substantial editing.** It inventories the lead’s claims, reorganizes sections, merges duplication, changes heading names for portable anchors, converts tables to lists, and checks preservation of meaning. It also puts the infographic in one prescribed opening position. Consequently, placement instructions tied only to line numbers or the original heading slug are insufficient. [Linker editing contract](https://github.com/sase-org/sase-research-artifacts/blob/17623956c379f580ad1931c927df0093d51feb91/src/sase_research_artifacts/xprompts/research_swarm.md#L316-L465).
- **The linker currently receives reports and images, not diagram packets.** `_report_records` selects Markdown artifacts with `research:` labels; the image list selects `kind == "image"`. A JSON packet registered as `kind=file` needs its own narrowly filtered artifact list. Merely writing a file will not establish this handoff. [Artifact lists](https://github.com/sase-org/sase-research-artifacts/blob/17623956c379f580ad1931c927df0093d51feb91/src/sase_research_artifacts/xprompts/research_swarm.md#L129-L135), [linker inputs](https://github.com/sase-org/sase-research-artifacts/blob/17623956c379f580ad1931c927df0093d51feb91/src/sase_research_artifacts/xprompts/research_swarm.md#L294-L312).
- **An extra Markdown handoff has classification costs.** Research inventory broadly includes `20*/**/*.md`; the PDF hook excludes particular draft and companion patterns. A new `topic_diagrams.md` would need deliberate exclusions and could otherwise appear as another research document. JSON avoids that problem with the current globs. [Provider filters](https://github.com/sase-org/sase-research-artifacts/blob/17623956c379f580ad1931c927df0093d51feb91/src/sase_research_artifacts/provider.py#L36-L55), [PDF hook filters](https://github.com/sase-org/sase-research-artifacts/blob/17623956c379f580ad1931c927df0093d51feb91/src/sase_research_artifacts/provider.py#L99-L125).

Artifact infrastructure already exposes exact dependency ownership through `wait_name`, artifact identity through `ref`, and source/VCS metadata. Reuse it rather than locating candidates through a filesystem glob, current month, or predecessor conversation. [Artifact-context query contract](https://github.com/sase-org/sase/blob/7b9436bedeed0ba7a716a3a6a91ff55d776e09d6/src/sase/core/artifact_context_query_facade.py#L35-L59).

## Critique of the idea and changes to the requirements

Diagrams can help when the report describes a process with branches, asynchronous interactions, a lifecycle, or relationships readers would otherwise have to reconstruct across paragraphs. They are less helpful for a short recommendation, a simple list, a comparison already clear in prose, or a subject whose uncertainty cannot be represented faithfully. These are editorial judgments, not a claim that diagrams universally improve comprehension.

The largest substantive risk is **inventing relationships while summarizing**. An arrow can silently assert causality, ordering, dependency, or data movement. A sequence diagram can turn “may happen” into “always happens.” The image agent must justify relationships from the lead’s prose, preserve conditional language, distinguish a proposed architecture from an implemented one, and avoid turning alternatives into a single definitive workflow. Syntax validation cannot catch these errors.

I recommend the following explicit adjustments:

1. **Treat the image agent as a visual contributor, not another researcher.** It can choose a representation and simplify labels, but must not add findings or sources. Mermaid is an authored text asset. Generate it directly as code; use the image tool only for raster illustrations.
2. **Allow an operational handoff file.** “Do not create its own report” should forbid a second narrative research report, while expressly permitting one JSON packet and temporary validation previews. Otherwise the no-report rule can accidentally forbid the very artifact the linker needs.
3. **Require an assessment even when no diagram is useful.** Publish `status: none`, an empty list, and a short reason. Missing output means unknown or failed delivery, not a deliberate judgment against diagrams.
4. **Give the linker permission to reject a diagram.** Its responsibility is faithful integration, not compulsory inclusion. Unsupported meaning, ambiguous placement, redundancy, or illegibility are sufficient reasons to omit an optional diagram and disclose the omission.
5. **Allow only diagram-related prose beyond the current linker rule.** The current instruction says its only original prose is the research-query summary. Amend that to permit accepted captions/accessibility descriptions and minimal connective wording that restates the lead. Without this change, the new assignment conflicts with the existing prompt.
6. **Preserve a complete text explanation.** The diagrams should explain existing content, never become the only place a caveat or recommendation is stated. This preserves usefulness for audio, source-only renderers, and readers who cannot use the visual.
7. **Keep optional diagram failure separate from report failure.** Missing or invalid diagrams should not prevent publication of a valid lead report. Missing/ambiguous lead input or a canonical output collision should retain the existing stop behavior.

For the first release, keep `image=true`’s existing infographic obligation. Add optional Mermaid assessment within that branch; keep `image=false` unchanged. Allowing “Mermaid only” without paying for a raster infographic is a worthwhile later extension, but silently changing what `image=true` means would expand this task. A fifth participant, global block-ID system, or new artifact provider is also unnecessary.

## Handoff alternatives

| Approach | Benefit | Limitation | Assessment |
| --- | --- | --- | --- |
| Image agent edits the lead or final report | No placement transport | Violates requested ownership; interferes with linker rewriting | Reject |
| Put diagrams and instructions in final chat | Very small prompt change | Weak durable identity; awkward replay and discovery; encourages transcript reads | Reject |
| One Markdown diagram appendix | Easy for a human to read | Looks like another report; requires inventory/hook exclusions and a parsing convention | Acceptable prototype, inferior fit here |
| Separate `.mmd` files plus JSON manifest | Native source files and straightforward renderer invocation | Multiple registered files, dangling-path risks, and more partial-delivery states | Good if diagrams become reusable assets |
| One JSON packet with inline Mermaid strings | One durable snapshot; no report collision; atomic payload and metadata | Less pleasant to edit manually; requires proper JSON serialization | Recommended initial format |
| A unified diff against the lead | Precise against exact original bytes | The linker restructures the report; patch application does not solve final placement | Reject as the primary handoff |
| Linker authors diagrams itself | Removes a handoff | Adds substantive visual modeling to an editor whose prompt forbids research | Reasonable alternative if there is no image stage |

The recommended JSON file is deliberately small. It is an annotation packet for one document, not a generic annotation database. The Mermaid source lives in the packet until publication, then accepted source also appears in the final Markdown. The packet records the proposal against a specific lead version; the published document is authoritative for subsequent reader-facing edits. Do not introduce a bidirectional synchronization system between them.

## Proposed packet contract

Write `<name>_diagrams.json` beside `<name>__final.md`, using the already selected report directory and stem. Never derive its location from the current date. Create it without overwrite, validate it, and register it only when complete. A controlled retry can produce a new snapshot through an explicitly selected attempt; the consumer must not choose among multiple candidates by filename sort or modification time.

The following is an illustrative schema instance. The source hash is a placeholder, and the quoted source paragraph is hypothetical rather than a quotation from another researcher’s work.

```json
{
  "schema_version": 1,
  "source": {
    "research_ref": "research:202610/example/example__final.md",
    "sha256": "<64 lowercase hex characters of the lead snapshot bytes>"
  },
  "status": "ready",
  "reason": "The publication ownership is easier to see as a short flow.",
  "diagrams": [
    {
      "id": "publication-ownership",
      "purpose": "Show who produces the proposal and who publishes it.",
      "placement": {
        "heading_path": ["Example", "Publication"],
        "exact": "The image agent creates diagram proposals. The linker publishes the report.",
        "prefix": "",
        "suffix": "",
        "relation": "after"
      },
      "covers": [
        {
          "heading_path": ["Example", "Publication"],
          "exact": "The image agent creates diagram proposals. The linker publishes the report."
        }
      ],
      "caption": "Diagram proposals pass from the image agent to the linker for publication.",
      "mermaid": "flowchart LR\n  accTitle: Diagram publication ownership\n  accDescr: The image agent creates proposals and the linker publishes the report.\n  I[Image agent] -->|diagram proposals| L[Linker]\n  L --> R[Published report]\n",
      "validation": {
        "syntax": "passed",
        "render": "passed",
        "renderer": "<actual validator and version>",
        "visual_review": "passed"
      }
    }
  ]
}
```

Contract rules:

- `status` is `ready`, `none`, or `failed`. `ready` requires at least one usable diagram; `none` means assessment succeeded with zero proposals; `failed` means assessment or creation could not finish. A `ready` packet may also carry a short `omissions` array for rejected candidates. Unknown/malformed status is an invalid packet, never equivalent to `none`.
- Diagram IDs are unique within the packet and use a simple lowercase slug grammar. Preserve them in integration bookkeeping. List order defines proposal order when two accepted diagrams attach to the same passage.
- Each `placement` identifies one location; `covers` can identify several passages supplying the content. This distinguishes **where to put it** from **what it illustrates**. Cross-section synthesis often needs both.
- `exact` copies raw Markdown for a complete source block, excluding its surrounding blank separator lines. Headings in `heading_path` are their original visible text, without numeric slug guessing. For a table or list, select the entire logical block if a smaller slice would create an unsafe insertion boundary.
- Match Unicode text after only a defined CRLF-to-LF conversion. Do not collapse arbitrary whitespace, remove Markdown, or fuzzy-match by default. `prefix` and `suffix`, when needed, are immediately adjacent source context for disambiguation. A selector must resolve to exactly one complete block in the selected section.
- Prefer `after` for the first version. Insert at a block boundary, never within a sentence, code fence, list item, or table row. Add other operations only when there is a concrete need.
- `covers` is evidence for an editorial check, not proof that the diagram is correct. The linker must still inspect its arrows, labels, conditions, and caption against the passages.
- Validation values describe checks actually performed. Use `not_run` with a reason when a tool is unavailable; never write `passed` because the source looks plausible. A candidate lacking a successful required check is not publication-ready.
- Do not publish producer-local absolute paths or transient artifact-store paths in this public research sidecar. The packet can carry the canonical research identity and digest; exact `file:` snapshot references belong in the SASE artifact handoff metadata.

JSON is a practical choice because it has unambiguous scalar types and existing tooling. The author can draft Mermaid as ordinary multiline text and serialize it, avoiding hand-escaped strings. Separate `.mmd` files can be added later if reusable diagrams, larger bundles, or external editing become common.

## Reliable source binding and placement

The W3C Web Annotation model provides a useful precedent: quote selectors retain the selected text with preceding/following context, while position selectors are explicitly vulnerable to document edits. Borrow that idea, not its full JSON-LD stack. The proposed packet uses Markdown source blocks and rejects ambiguity, so it is a project-specific selector contract rather than an implementation of the complete W3C model. [Text quote and position selectors](https://www.w3.org/TR/annotation-model/#text-quote-selector).

There are two distinct problems:

1. **Find the intended block in the original source.** Bind the packet to the awaited lead’s immutable snapshot, check its digest, and resolve the section-plus-quote selector there. A heading is context; a line number can be a diagnostic hint. Neither is sufficient identity by itself. If the same heading and paragraph occur twice, require more context or reject placement.
2. **Carry the association through editing.** The linker should resolve proposals during its existing source inventory, before restructuring. Record each accepted diagram ID beside the source inventory item it illustrates. Move that association with the content into the final organization, including when a table becomes a list. Then place the diagram immediately after the explanatory block and confirm the surrounding context still supports it.

Do not first rewrite the whole report and then run a literal search-and-insert against its new wording. That reintroduces the exact failure the source mapping was meant to avoid. For difficult restructuring, use private working markers or an in-memory block map in the linker's scratch copy; remove scratch markers before publishing. Neither the image agent nor these bookkeeping operations should modify the lead report.

A digest catches the wrong source version; it does not solve semantic relocation. If the source snapshot differs, reject the packet instead of guessing that its content is still valid. If the snapshot matches but the linker cannot preserve a clear destination, omit that proposal and explain why.

There is a SASE-specific hashing trap: `sase artifact read` strips managed link sections **and frontmatter** before printing Markdown. Do not compare a hash of that printed body with a hash of the raw report file. Obtain the immutable artifact’s recorded digest, or hash its resolved raw snapshot bytes after the audited read, and compare the same representation at both ends. [Read transformation](https://github.com/sase-org/sase/blob/7b9436bedeed0ba7a716a3a6a91ff55d776e09d6/src/sase/artifact_cli/read.py#L179-L228).

If source offsets are ever added for deterministic insertion, bind them to the same digest and treat them as an accelerator checked against the quote. They are not a replacement for source identity or the linker's content association.

## Artifact discovery and publication

The image branch should receive an explicit list of the awaited lead’s registered reports, just as the linker already does. It should identify the unique `.final` producer and `__final.md` label, then use `sase artifact read` on the selected snapshot. The existing fork can provide conversational context, but the selected artifact defines what is being illustrated.

After exclusive creation and validation, register the packet using the existing generic file kind:

```sh
sase artifact create -p "<absolute-packet-path>" -k file \
  -l "research-diagrams:<actual-research-repo-relative-packet-path>"
```

`research-diagrams:` here is a **display-label convention**, not a proposed new canonical artifact provider. Consumers read the returned `file:...` reference. Do not pass `--move`; keep the source beside the report. An artifact registration failure is a failed handoff even if the JSON file exists.

Extend the linker’s deferred artifact list to select the exact awaited image producer, explicit snapshots of `kind=file`, and the agreed `research-diagrams:` label convention. Show `wait_name`, `label`, and `ref`, plus ordinary location metadata for recovery. Confirm one matching packet and matching source identity/digest. Never read a sibling swarm's packet, an arbitrary JSON file, or a cached manifest from a previous attempt. Validate deferred template expansion in tests, including missing image output.

The packet itself provides the assessment outcome. A small optional `diagrams` output variable may point to its artifact and summarize status, following the existing audio pattern, but it should not be a second authority for diagram content. Use one packet as the source of truth; a missing summary variable should not invalidate a valid registered packet.

The linker should:

1. Read and inventory the lead as today; read the one selected packet through its artifact reference.
2. Validate schema, source binding, unique IDs, placement matches, syntax/render evidence, and factual fidelity.
3. Associate accepted IDs with source inventory items before restructuring.
4. Insert Mermaid fences and approved captions at the resulting destinations, preserving all original claims and citations. Do not move every diagram to the opening infographic slot.
5. Prevent duplicates against existing lead diagrams and repeated proposals. Identical source can be detected mechanically; equivalent meaning requires editorial review. Use diagram IDs in a private integration log or unobtrusive comments if replay support needs them.
6. Recheck the final narrative, document opening order, links, and diagram readability. Revalidate Mermaid source if it was edited.
7. Create and register `<name>.md` without overwrite. Report accepted/omitted IDs and failures in its completion output. Do not insert internal validation logs or pending-work notices into the research narrative.

No peer chat transcript is required. The final report is still written exactly once by the linker; the lead and image packet remain preserved source artifacts.

## Rendering and accessibility findings

GitHub renders Mermaid inside a `mermaid`-labelled code fence, but its documentation advises checking the renderer version for supported syntax. Do not assume that the latest local renderer and GitHub accept every identical feature. Start with mature diagram types such as flowcharts, sequence diagrams, and state diagrams; favor short labels and compact layouts. [GitHub diagram documentation](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams).

The live configuration inspected in the chezmoi checkout invokes `bob ref create --include-id -P "$SASE_FILE_HOOK_PROJECT"` for research Highlights. The plugin README still illustrates the older `bob highlights create` name; the configured command and current Bob source are the relevant evidence for this deployment.

The inspected Bob source already:

- Collects explicitly tagged Mermaid blocks through Pandoc and renders them using a bundled Mermaid 12.2.0 and an offline browser.
- Inserts fitted vector PDFs before the ordinary code and link filters.
- Leaves source plus a visible explanatory note on a per-diagram failure, allowing the overall import to finish.
- Warns when fitting a figure requires shrinking it below half its natural size.
- Allows diagram rendering to be disabled through `BOB_HIGHLIGHTS_DIAGRAMS`.

These are existing behaviors, not proposed additions. [Bob renderer documentation](https://github.com/bobs-org/bob-cli/blob/fd3f400b142ab667ca4ba885ebe5a8d2ea9976c1/docs/highlights-create.md#L256-L293), [diagram integration](https://github.com/bobs-org/bob-cli/blob/fd3f400b142ab667ca4ba885ebe5a8d2ea9976c1/src/native/highlights_ref/create.rs#L3262-L3286), [fallback behavior](https://github.com/bobs-org/bob-cli/blob/fd3f400b142ab667ca4ba885ebe5a8d2ea9976c1/src/native/highlights_ref/diagrams.lua#L43-L69).

Therefore, publish **Mermaid fences as the canonical representation**, and reuse Bob for PDF rendering. Do not generate mandatory PNG duplicates or add a second PDF pipeline. The official Mermaid CLI remains a useful standalone validation/rendering option where already available; it can render source files and transform Markdown containing diagrams. It is not a required new production dependency for Bob. [Official CLI documentation, inspected locally](https://github.com/mermaid-js/mermaid-cli/blob/f416ac5c6e42edd3a8be6d512c1008520d0c2f97/README.md#L10-L24), [Markdown transformation](https://github.com/mermaid-js/mermaid-cli/blob/f416ac5c6e42edd3a8be6d512c1008520d0c2f97/README.md#L87-L136).

Validation has three separate purposes: a parser catches syntax problems; rendering catches layout/tool compatibility problems; visual and editorial inspection catch unreadable or misleading diagrams. Mermaid exposes `mermaid.parse` for syntax checking without rendering, so a parse pass must not be reported as a render pass. [Mermaid validation API](https://mermaid.js.org/config/usage.html#syntax-validation-without-rendering).

Use `accTitle` and `accDescr`, along with a visible caption or nearby text equivalent. Mermaid can translate those fields into accessible SVG title/description attributes. However, Bob’s current documentation explicitly excludes accessibility-title metadata from its supported PDF behavior, so those fields alone are not a promise of accessible PDF output. [Mermaid accessibility](https://mermaid.js.org/config/accessibility.html), [Bob limitations](https://github.com/bobs-org/bob-cli/blob/fd3f400b142ab667ca4ba885ebe5a8d2ea9976c1/docs/highlights-create.md#L287-L293).

Keep diagrams static and compatible with the existing strict renderer: no custom JavaScript, click actions, remote images/icon packs, or per-diagram security overrides. This matches Bob’s offline/strict implementation and avoids depending on features unavailable in PDF. Mermaid documents strict mode as encoding HTML and disabling click functionality. [Mermaid security configuration](https://mermaid.js.org/config/schema-docs/config.html#securitylevel), [Bob configuration](https://github.com/bobs-org/bob-cli/blob/fd3f400b142ab667ca4ba885ebe5a8d2ea9976c1/scripts/web_clip/diagram_render.py#L133-L169).

As an initial editorial budget, usually choose zero to three diagrams, with one clear question answered by each. This is a default for restraint, not a schema limit. Split a dense diagram or keep prose when it would shrink into unreadable labels. Do not count a successful PDF command as proof every diagram rendered: Bob intentionally allows partial rendering and reports its counts.

## Implementation scope and acceptance checks

The first change should be concentrated in the research plugin:

- Extend `research_image.md` with the assessment and packet contract. To preserve direct invocation behavior, give the shared macro an explicit mode such as `mermaid=off|auto`, defaulting to `off`, and have the swarm image branch request `auto`. This spelling is a proposal, not an existing option.
- Update the image segment in `research_swarm.md` to expose its selected source artifact; update the linker’s file-artifact input list, preservation inventory, diagram acceptance rules, and final layout description.
- Adjust the linker's “only original prose” restriction for tightly scoped captions. Preserve infographic positioning, audio parallelism, and no-overwrite publication.
- Update plugin README/default role descriptions and macro-loading tests. Add a fixture proving the JSON packet does not enter research-report inventory or trigger a Highlights PDF by itself.
- Reuse artifact identity, registration, wait context, and Bob rendering. No new artifact kind, canonical ref provider, or renderer is justified.

For a prompt-level first release, document and exercise the exact matching checks using existing tools. If deterministic selector validation or insertion becomes a supported shared backend facility, place that behavior in `sase-core` with thin caller glue, following this project’s Rust boundary. Do not quietly build a second Python Markdown domain engine inside the TUI or macro loader. A generic document-annotation service is premature.

Meaningful acceptance cases include:

- One accepted diagram and several diagrams at distinct source passages.
- `status: none`, valid empty arrays, failed generation, malformed JSON, and registration failure.
- Two headings with the same text, a repeated short quote, a unique full-block quote, and insufficient prefix/suffix context.
- Source snapshot mismatch, including differences hidden by `artifact read`’s presentation stripping.
- Linker section reordering, heading renaming, table-to-list conversion, and merged duplicate passages.
- A matching packet from a different producer, multiple competing packets, and a local report path that moved after snapshot registration.
- Existing lead Mermaid diagrams, two proposals at the same anchor, and a repeated integration attempt without duplication or overwrite.
- Syntax failure, valid but unreadable output, unsupported relationships, and unverified renderer availability.
- Image plus audio: neither side stage waits on the other; the linker integrates both without changing the lead text or making the narration depend on diagrams.
- The final PDF containing actual figures at the intended passages, readable at normal page size; render warnings/counts checked explicitly.

A bounded pilot should track how often the agent chooses diagrams, how often the linker rejects them, source-anchor failures, render failures, added runtime, and whether the figures helped the reader. There is no evidence from this investigation for a numerical quality or latency benefit. If most packets are rejected or the diagrams merely restate the infographic, reduce the scope or let the linker perform a lightweight diagram pass itself.

## Evidence and limits of this investigation

Local source revisions inspected:

- `sase-research-artifacts`: `17623956c379f580ad1931c927df0093d51feb91`.
- `sase`: `7b9436bedeed0ba7a716a3a6a91ff55d776e09d6`.
- `bob-cli`: `fd3f400b142ab667ca4ba885ebe5a8d2ea9976c1`.
- `mermaid-cli`: `f416ac5c6e42edd3a8be6d512c1008520d0c2f97`.
- Chezmoi configuration: `5fd6b53ed8b3b438c9467be56ab803a6487faa38`, `home/dot_config/sase/sase.yml`, lines 17–19. This configuration was read through its opened checkout; no private machine path is needed in the proposed packet.

Read-only checks confirmed the current artifact CLI uses `-l` and copies its source unless `--move` is supplied. A small synthetic exercise checked JSON round-tripping, an ambiguous short quote, a unique complete-block quote, and digest changes after source edits. A plain Pandoc 3.1.3 experiment produced code text from a Mermaid fence without filters; that illustrates why Bob’s existing collect/render/swap pass matters, not a defect in Bob.

I inspected Bob’s rendering code and tests but did not run a new end-to-end PDF/browser render, install Mermaid CLI, change production configuration, or implement the proposed handoff. Thus the report establishes source-level support, not the health of every installed renderer/browser or deployment. Acceptance testing should use the actual publication host. The JSON example is a contract proposal, not a validated diagram artifact from a real lead report.

## Recommended solution

**Keep the existing lead → image → linker ownership model and add one versioned, explicitly registered JSON diagram packet.** The image agent should assess the completed lead snapshot, produce only useful Mermaid diagrams, bind each to supporting source blocks and a precise insertion location, and explicitly report when none are warranted. It must leave both the lead report and canonical publication untouched.

The linker should discover that packet through the awaited image producer’s artifacts, validate it against the exact lead snapshot, carry accepted diagram associations through its existing editorial restructuring, and publish Mermaid fences with concise captions beside the corresponding content. It should omit invalid, unsupported, or ambiguously placed proposals while completing the report and reporting those omissions.

Use Bob’s existing vector Mermaid rendering for Highlights PDFs. Start with the small handoff and focused acceptance tests; keep the current infographic and audio behavior, avoid another agent or report type, and consider a Mermaid-only visual mode after a short pilot demonstrates its value.
