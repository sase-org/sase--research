---
title: "Artifacts sub-tab names: familiar language without losing domain meaning"
researcher: cdx
date: 2026-10-13
source_revision: "sase@1a638eac95b42c13014dd76c384dbfb56f5b323f"
scope: "Independent terminology and implementation research; no application changes"
---

# Artifacts sub-tab names: familiar language without losing domain meaning

The direction is good: collection names should be easy to recognize, and plural labels fit panes that list many records. I recommend **Commits · Changes · Issues · Plans · Files**, with the underlying SASE vocabulary retained in references, commands, and contextual explanations. The proposed **PRs** and **Bugs** labels are too narrow for the existing panes. This is a presentation change with a small copy audit, rather than a rename of the underlying domain model.

This report independently examines the current SASE checkout, its audited reference memory, and public design guidance. It does not consult any other researcher in this swarm. Findings about existing behavior come from source inspection; the preference for “Changes” over “Patches” is a design judgment, not a measured usability result. No live user study or application modification was performed.

The main question is whether a label helps someone predict the contents before opening the pane. A familiar word can make that prediction worse when it denotes only a subset of the records. Nielsen Norman Group recommends language familiar to the intended users and warns that designers cannot assume their interpretation matches users’ understanding. Carbon likewise recommends short, specific tab labels that communicate the contents of the view. Those principles support simplification, but do not establish that every SASE term should be replaced or that plural nouns are universally superior. [NN/G: Match Between the System and the Real World](https://www.nngroup.com/articles/match-system-real-world/), [Carbon: Tabs guidelines](https://www.carbondesignsystem.com/building-blocks/core/components/tabs/guidelines)

For Bryan, who already understands SASE, the immediate benefit is consistency and scanning rather than learning a new model. For a developer encountering SASE for the first time, recognizable collection names should reduce the amount of glossary knowledge needed to find an artifact. The cost is learning how those names map to CLI commands and canonical references. A concise explanation within the pane can carry that mapping without requiring jargon in the tab strip.

The category boundaries matter more than the spelling changes:

| Current label | Proposed label | What the existing pane represents | Assessment and recommendation |
| --- | --- | --- | --- |
| Stitch | Commits | Actual VCS commit records, with messages, diffs, repository context, origin information, and filters | Accept **Commits**. It describes the current pane better than the broader stitch concept. |
| Patch | PRs | SASE change records with their own lifecycle, commits, hooks, comments, and mentors; a PR is optional | Use **Changes**. **Patches** is an accurate, conservative alternative. Do not call all these records PRs. |
| Bead | Bugs | Local work tracking with tasks, plan/epic records, phases, flags, and optional external tracker issue information | Use **Issues**. Bugs are only part of the inventory. |
| Plan | Plans | Plan documents, including proposals and archived documents, exposed through a document provider | Accept **Plans**. Keep the distinction between a plan document and its execution-tracking bead. |
| File | Files | Indexed artifact files and snapshots, rather than a general repository file browser | Accept **Files**, with the existing explanation of indexing and capture scope. |

There is an important asymmetry in the first two rows. Audited glossary memory defines a stitch as an ordered change record inside a Patch. Commits have numeric stitches in the tracked workflow, but proposals can have numeric-plus-letter IDs without a commit. It would therefore be incorrect to rename the entire stitch domain “commit.” The current Artifacts Stitch pane, however, is implemented as a commit browser: its collector returns a VCS log result, constructs an index from commit rows, and renders a commit timeline. A source-level distinction between SASE, automatic, and manual commit origins also exists. The label **Commits** describes this concrete view without claiming every stitch elsewhere is a commit. Sources: audited `glossary:stitch`; `commits_collection.py:195`, `commits_pane.py`, and `vcs_log/_origin_style.py` in the source inventory below.

If non-commit stitch proposals are ever added as first-class rows to this pane, its scope and label should be reconsidered then. That possibility does not justify retaining the less recognizable label for the current commit view. Within a selected Patch’s detail, a proposal’s stitch ID and the STITCHES section can keep their precise meanings.

A Patch and a PR also are not interchangeable. The glossary explicitly allows a Patch with no PR field, and the built-in pane description says it covers changes with or without a PR. A local WIP change that has never been uploaded belongs here. Calling the tab **PRs** would make a user wonder why that row is present, or where local work should be found. A draft PR remains a real PR; describing a local-only Patch as “a draft PR” would not resolve the distinction. GitHub documents pull requests as proposals to merge changes and distinguishes a created draft pull request from other local work. [GitHub: Pull requests](https://docs.github.com/en/pull-requests/reference/pull-requests)

**Changes** is my preferred replacement because it covers the whole lifecycle and reads naturally for local work as well as uploaded reviews. Its weakness is breadth: commits are also changes, so the noun alone does not establish the granularity. The pane’s brief should say that these are SASE change records, each grouping commits and review/workflow state. **Patches** avoids introducing another mapping and is already recognizable to many developers, though some may expect exported diff files. Neither choice is as misleading as PRs.

I would choose **Patches** over **Changes** if preserving a single domain term across the interface and CLI matters more to Bryan than reducing navigation jargon, or if a short navigation trial shows people interpret Changes as a list of individual commits. The research establishes the PR mismatch firmly; it does not establish one universally optimal replacement for Patch.

**Bugs** is the weakest part of the original proposal. The bead snapshot loader explicitly collects tasks, plan/epic records, phases, and flags; external issue caches and their links can also participate. Task types in loaded project instructions include features, CI failures, flaky tests, and memory maintenance in addition to defects. A person trying to find an approved epic or feature should not have to guess that it lives under Bugs. Renaming the pane without changing its contents would communicate the wrong scope.

**Issues** is a useful broad developer term and covers both local work records and connected tracker issues. GitHub itself uses issues for ideas, feedback, tasks, bugs, and hierarchical work, so the term need not imply a defect. SASE’s internal loader already uses Issue and IssueType models, although backend naming alone is not a UX argument. Keep local bead IDs and external tracker numbers visibly distinct, and preserve whether a selected row is a Task, Epic, Phase, or Flag. “Issues” should not imply that every row was created on GitHub. [GitHub: About issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/learning-about-issues/about-issues)

**Work items** is a defensible alternative if Issues sounds too tied to an external tracker. It is broader and more explicit, but takes more terminal space. **Tasks** is shorter, yet overlaps with an existing bead subtype and underspecifies epics and phases. **Beads** is the conservative option when precise command correspondence is the priority, with the largest terminology burden for new users. These tradeoffs favor Issues for the requested goal.

**Plans** and **Files** are straightforward improvements. A plan document belongs under Plans; the bead that tracks its implementation belongs under Issues, with a relation connecting them. The existing Files description should continue explaining that this is an artifact index, not every file in the repositories. A report may have both a document-provider entry and an explicit file snapshot: these views represent different access paths and provenance, rather than mutually exclusive filesystem folders. Renaming should preserve that behavior.

A plural convention should mean “name collections naturally,” not “every label must end with s.” **Research** is already a natural collection label. Appending s would damage it, and other provider labels may be mass nouns, already plural, or deliberately customized. The policy should set explicit defaults for known panes and preserve provider-authored names.

Several implementation details make a search-and-replace insufficient:

1. **The code already separates display labels from stable identities.** `fixed_descriptor()` sets singular built-in labels in one mapping, while descriptors retain IDs such as `stitches`, `patches`, `beads`, and `files`. Plans has the provider ID `ref:plan`. `ArtifactsView._panel_tabs()` supplies descriptor labels to the shared tab strip. Change the labels while keeping these IDs, widget selectors, query histories, selection state, keymap action names, and canonical references stable.

2. **Plans uses the document-provider path.** `_provider_label()` considers explicit spec labels before deriving a title from the kind. The presentation compiler can further supply `ref.pane.label`. The built-in plan provider currently does not supply a label, so it falls back to Plan. Make the unconfigured plan fallback Plans in the TUI resolver, including its degraded fallback, while preserving the existing precedence of explicit provider labels. This avoids changing the provider wire contract or globally guessing plurals. A deliberate override saying Plan should remain a deliberate override.

3. **The label is also used as if it were a singular entity name.** `compile_provider_contract()` generates empty-state copy by appending s; `plans_rendering.build_plan_detail_placeholder()` generates a heading the same way; document help generates “Refresh {label}s” and “Open selected {label}.” A label-only change to Plans would produce “planss” in generated copy and “Open selected plans” for a single document. These are source-inspection consequences, not claims of a live reproduction. Treat the collection label and single-object noun separately.

4. **Some visible headers bypass the descriptor.** Commit and file renderers hard-code “Stitch” and “File”; the bead renderer passes `label="Bead"` to the shell; PatchInfoPanel renders “Patch:”. Built-in help sections include “Stitch Pane,” “Patch Pane,” “Bead Pane,” and “File Pane.” A new tab above an old pane identity would look unfinished. Route collection headers through the compiled display label, preserving single-object terms where they explain the selected artifact.

5. **Relation labels are independent text.** The built-in adapters declare destinations such as Patches and Beads, and providers can author their own relation labels. Update host-owned collection destination names to Changes and Issues where they name these panes. Preserve relationship semantics and target IDs; do not rewrite arbitrary provider-authored phrases.

6. **Singular names are explicitly pinned by existing tests.** `test_artifact_tab_labels.py` asserts the current mapping, rejects labels ending in s, and expects the plan fallback to be Plan. Those requirements should be updated intentionally. Existing discovery, digit, navigation, description, and visual coverage provide useful checks beyond spelling assertions.

There is also historical naming evidence that could otherwise be confusing. `LEGACY_ARTIFACTS_SUBTABS` maps `prs` to `patches` and `bugs` to `beads`. These are compatibility aliases for pane IDs; their existence does not prove that the contents currently consist only of PRs or bugs. Reference compatibility is separate again: `docs/artifact_references.md` says historical `@commit:` canonicalizes to `@stitch:`, while new authoring keeps the established canonical reference vocabulary. A tab rename does not require reopening those protocol decisions.

The original list also omits the legacy **Agent** sub-tab. The current source can retire that pane through `artifacts_agent_pane_retired`, with history available in the Agents tab’s Archive. Do not revive it for naming consistency. If the non-retired state still needs support, pluralizing its displayed collection name to Agents is reasonable; address its potentially confusing overlap with the top-level Agents tab as a separate product decision.

I would adjust the requirements explicitly as follows:

- **Replace Patch → PRs with Patch → Changes.** The collection must include local-only changes. Patches is the acceptable conservative fallback.
- **Replace Bead → Bugs with Bead → Issues.** Preserve all current record categories and tracker integration.
- **Keep Stitch → Commits, Plan → Plans, and File → Files.**
- **Limit the rename to presentation and the copy needed to make it coherent.** Domain types, commands, references, IDs, configuration keys, storage, filters, and data scope retain their identities.
- **Apply the collection convention to known labels, not through automatic English inflection.** Provider-specific names and explicit overrides keep their existing precedence.
- **Include visible pane headers, navigation/help text, and built-in relation destinations in acceptance criteria.** Keep canonical terminology where an object’s identity or command syntax requires it.
- **Preserve tab order, icons, colors, digit assignments, and default selection.** A naming change should not also change navigation.
- **Handle the legacy Agent pane only if it is present.** Its retirement behavior remains independent.

This gives a coherent implementation without committing to a global vocabulary migration. A full rename of stitch/patch/bead would reach durable references, immutable history, prompts, command APIs, integrations, and generated pages. That is a much larger product decision with little additional benefit for someone trying to choose a tab.

A small amount of bridge copy should preserve the useful domain distinctions. Suggested pane briefs are:

| Display label | Suggested brief |
| --- | --- |
| Commits | VCS commits across your projects, with messages, diffs, and SASE provenance. |
| Changes | SASE change records (Patches), with commits and review state; a PR is optional. |
| Issues | Tracked work and linked tracker issues, including tasks, epics, phases, and flags. |
| Plans | Plan documents and proposals, linked to the work that implements them. |
| Files | Indexed artifact files, explicit snapshots, and automatic captures. |

The expanded Changes description can explain what a Patch carries. The expanded Issues description can explain that local work records are called beads and use `bead:` references. Canonical references should remain visible and copyable exactly as they are. For individual actions, “Open selected commit,” “Open selected change,” “Open selected issue,” “Open selected plan,” and “Open selected document” are natural. It remains appropriate for documentation to show literal commands such as `sase bead` and literal fields such as STITCHES.

Do not put “Commits (Stitches)” and “Issues (Beads)” permanently in every tab label. That spends scarce horizontal space on explanations the existing pane brief can provide. Do not require mouse tooltips for essential distinctions: this is a keyboard-oriented terminal interface, and the brief is already part of the layout. Keep essential scope explanations understandable when the description is expanded, and make the short label usable even when descriptions are off.

For the five named panes, the original singular words occupy 22 text cells; Commits, Changes, Issues, Plans, and Files occupy 30. The eight-cell increase excludes icons, numbering, separators, and optional provider tabs. The plural SASE-specific set Stitches, Patches, Beads, Plans, Files also totals 30, so keeping jargon does not save space in that comparison. This arithmetic does not prove the strip fits a particular terminal. The shared PanelTabStrip measures cell widths and click ranges and has a density/reflow mechanism; verify the actual Artifacts configuration at narrow widths and with extra provider tabs.

The implementation can remain in Python/Textual presentation code. Put built-in defaults in the existing descriptor construction path, carry labels through the pane contract to visible collection headers, and audit display-copy call sites. For the known built-ins, explicit single-object nouns are sufficient. Generic document actions can say “Open selected document,” “Copy reference,” and “Refresh documents,” while their collection headings use the provider label verbatim. Generic empty text such as “No matching documents” avoids grammatical assumptions. No new provider schema field or Rust backend change is required for this approach. If a later product change introduces shared label/identity resolution outside presentation, apply the project’s Rust boundary then.

Verification should focus on preserving meaning and navigation:

- A commit from the existing inventory remains findable under Commits, including manual and automatic origins where enabled.
- A local WIP Patch with no PR stays visible under Changes.
- Non-bug tasks, an epic with phases, and flag records remain under Issues with their category markers intact.
- Plans remains the document pane; linked execution records still navigate to the Issues pane.
- Files remains the artifact index and does not start behaving like a repository file browser.
- IDs, reference copies, stored selection/query state, keyboard cycling, and digit shortcuts continue to work.
- Plan and custom document-provider empty/loading/help states contain no doubled plurals, and provider-authored labels such as Research or Release notes remain intact.
- Tab-strip labels, collection headers, help headings, and host-owned relation destinations agree.
- Narrow layouts and mouse hit targets remain usable; relevant visual expectations are inspected before accepting golden changes.

Use the existing navigation/provider/help coverage and relevant visual fixtures for implementation verification. Do not create a large test suite that merely duplicates the new label dictionary. Follow the project’s required lint/test and visual-verification memory when implementing; this research changed no application source and ran no application test suite.

A brief navigation trial would help resolve the remaining preference uncertainty. Ask Bryan and a few developers unfamiliar with SASE to locate a commit diff, a local change with no PR, a feature task, an epic phase, an approval proposal, and a generated report using the proposed strip. Observe wrong first choices and requests for explanation. Give special attention to whether Changes is mistaken for individual commits and whether Issues is assumed to mean external tracker records only. This is a suggested validation step, not a prerequisite for completing the straightforward naming cleanup.

For traceability, the local evidence below refers to the SASE source revision in the frontmatter. Paths are relative to that repository, not to this research repository.

| Source | Evidence used |
| --- | --- |
| `src/sase/ace/tui/_artifact_tab_descriptors.py:66` | Fixed singular labels, immutable descriptor construction, label/ID separation. |
| `src/sase/ace/tui/_artifact_tab_descriptors.py:296` | Provider label precedence and title-case fallback. |
| `src/sase/ace/tui/_artifact_tab_model.py:28` | Stable IDs, default selection, legacy aliases, and Agent-pane retirement. |
| `src/sase/ace/tui/artifact_tabs.py:135` | Fixed/provider composition and position-based shortcut assignment. |
| `src/sase/ace/tui/_artifact_tab_descriptions.py` | Current scope descriptions for commits, Patches, beads, files, and plans. |
| `src/sase/ace/tui/widgets/artifacts/commits_collection.py:195` | VCS-log collection and indexing of commit rows. |
| `src/sase/vcs_log/_origin_style.py` | Stitch, automatic, and manual commit origins. |
| `src/sase/ace/tui/widgets/artifacts/beads_data.py:93` | Task, epic, phase, flag, and external issue snapshot data. |
| `src/sase/artifact_providers/_builtin.py:13` | Built-in plan provider lacks an explicit display label. |
| `src/sase/ace/tui/_artifact_tab_presentation.py:87` | Existing `ref.pane.label` override path. |
| `src/sase/ace/tui/_artifact_tab_contract.py:234` | Empty-state generation appends s to provider labels. |
| `src/sase/ace/tui/widgets/artifacts/plans_rendering.py:154` | Document placeholder assumes a singular provider label. |
| `src/sase/ace/tui/modals/help_modal/patches_artifact_bindings.py:258` | Document help mixes collection and single-object uses of the label. |
| `src/sase/ace/tui/widgets/artifacts/{commits_rendering,beads_rendering,files_rendering}.py` | Hard-coded pane identity names outside descriptors. |
| `src/sase/ace/tui/widgets/patch_info_panel.py:168` | Specialized Patch identity/position header. |
| `src/sase/ace/tui/_artifact_tab_contract_adapters.py` | Host-owned relation labels and stable destination IDs. |
| `src/sase/ace/tui/widgets/artifacts/view.py:197` | Tab strip receives resolved descriptor labels. |
| `src/sase/ace/tui/widgets/panel_tab_strip.py` | Cell-width measurement, hit ranges, and reflow support. |
| `tests/ace/tui/test_artifact_tab_labels.py` | Existing singular-label assertions and verbatim configured labels. |
| `docs/artifact_references.md:54` | Reference canonicalization and compatibility boundaries. |
| `docs/artifacts_pane_contract.md`, `docs/artifacts_pane_visual_grammar.md` | Shared pane contracts, description slot, and presentation boundaries. |
| Audited memory: `tui.md`, `sase_artifacts.md`, `sase_beads.md`, `glossary:stitch`, `glossary:patch`, `glossary:artifact` | Domain definitions, read/write rules, and artifact scope. |

**Recommended solution:** ship **Commits · Changes · Issues · Plans · Files** as the default collection labels, preserve canonical SASE terms and stable identities, and update the small set of affected headers, help strings, relation names, and document-label grammar in the same change. Keep Patches as the conservative alternative to Changes if the navigation trial favors command correspondence. Do not ship PRs or Bugs for these unfiltered collections.
