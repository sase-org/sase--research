# Bulk project onboarding from the SASE Admin Center

**Date:** 2026-09-03

**Scope:** Research and implementation recommendation

**Decision target:** How users should add and enable several VCS-backed projects on a machine, and how explicit VCS launch refs should behave when the project is not known locally.

## Executive finding

The best experience is a dedicated, provider-driven **Add Projects** modal in the Projects sub-tab. It should work like a multi-select extension of the existing `#gh:` completion: users browse or search a namespace, mark repositories into a persistent basket, review the batch, and then add it with per-project progress. The modal must be built on workspace-provider capabilities rather than GitHub concepts.

The launch behavior should change at the same time. An explicit VCS ref for a project that SASE does not yet know on this machine should stop before the mutating provider resolver runs. The error should point to **Admin Center → Projects → Add Projects**. Creating a disabled project during launch is not a good compromise: the current resolver may clone and write the project first, while the running-field claim then rejects the disabled project. That produces work followed by a confusing failure.

## What the current system implies

### The Projects tab is already an inventory manager

`src/sase/ace/tui/modals/projects_pane.py` presents Projects, Repos, and Workspaces as nested inventory tabs. The Projects view already supports filtering, persistent marks, bulk enable/disable/delete actions, aliases, and current-project selection. `project_list_controller.py` makes marks survive filtering and automatically advances after marking.

That makes this tab the right home for machine enrollment. It also argues against reusing its existing marks for discovery: those marks identify records that already exist, while Add Projects needs to select records that do not exist yet. A separate modal can use the same interaction vocabulary without mixing the two identity sets.

The current footer is already dense at ordinary terminal widths. Adding several inline actions would reduce discoverability rather than improve it. The Projects sub-tab should expose one new action, preferably `n` with the label **Add Projects**, and put the rest of the controls inside the modal. The empty state should explicitly say “Press n to add projects.” As with every ACE keymap, the binding belongs in both the application keymap and `src/sase/default_config.yml`.

### Most of the discovery model already exists

The workspace-provider boundary in `src/sase/workspace_provider/_hookspec.py` already defines generic types and hooks for:

- provider metadata (`WorkflowMetadata`);
- fast, local namespace completion (`ws_list_ref_namespaces`);
- remote repository listing for a namespace (`ws_list_repo_candidates`);
- non-mutating lookup of existing local refs (`ws_peek_ref`); and
- mutating resolution/materialization (`ws_resolve_ref`).

The `#gh:` completion is therefore not intrinsically GitHub-specific. `src/sase/xprompt/vcs_ref_completion.py` combines local projects with provider namespaces, and `vcs_repo_completion.py` caches provider results, falls back to stale cache data, and ranks prefix matches before recently pushed repositories. The ACE completion UI already handles loading, empty, and error rows and renders private, fork, and archived badges.

The GitHub plugin implements those contracts in `sase-github/src/sase_github/workspace_plugin.py`. Repository candidates come from the authenticated provider and contain description, visibility, fork/archive state, and last-push time. Namespace candidates are intentionally local-only: they are derived from known enabled projects and `github_orgs` configuration. That is fast enough for prompt completion but insufficient by itself on a pristine machine. If configuration is not synced, the modal would have no owner or organization suggestions even though authentication can enumerate them.

### “Missing state means enabled” causes the unwanted launch behavior

Project lifecycle parsing lives in `sase-core/crates/sase_core/src/project_spec.rs`. A project spec without `PROJECT_STATE` is treated as enabled for backward compatibility. The GitHub resolver creates the local checkout/project spec as part of resolving an unknown `owner/repo`; because that new spec has no explicit lifecycle state, it becomes enabled. The bare-git initialization path follows the same implicit default.

There is also a separate, deliberate behavior in `src/sase/agent/launch_projects.py`: an explicit launch of a **known disabled** project re-enables it. That behavior was introduced in commit `2559e8a3e6` and later renamed from active/inactive to enabled/disabled in `f47815df3`. It is not what causes a brand-new project to be enabled.

This distinction matters:

| Ref at launch time | Current outcome | Recommended outcome |
|---|---|---|
| Known and enabled | Launch | Launch |
| Known and disabled | Re-enable, then launch | Preserve for now; it is an explicit choice of a known project |
| Unknown to SASE on this machine | Provider may clone/create; implicit state enables it; launch | Stop before mutation and direct the user to Add Projects |

Globally changing the meaning of a missing state would be unsafe because it is an established compatibility default. Changing generic project-file creation would also affect unrelated workflows. Enrollment intent should instead be explicit at the operation boundary.

## UX alternatives

| Approach | Advantages | Problems |
|---|---|---|
| Multiline ref entry | Small implementation; good for copy/paste | Poor discovery; provider syntax leaks into the primary path; typo and collision handling dominate the flow |
| One flat list of every repository | Fast when the desired repo is visible | Slow and noisy for large accounts; awkward across several providers; encourages unbounded API calls and weak cache behavior |
| Reuse the existing single-result prompt completion | Familiar and inexpensive | Reopening it once per project makes bulk onboarding tedious; selection is lost when changing namespace |
| Provider/namespace browser with a persistent basket | Scales, reuses the provider contract, supports rich completion and cross-namespace batches | Requires a purpose-built modal and explicit batch execution model |

The last option is the best base. It should still include multiline/manual refs as an escape hatch, not as the main interface.

## Proposed interaction

### Entry and layout

From the Projects sub-tab, `n` opens **Add Projects to this machine**. “Add” is preferable to “Create”: the operation does not create a remote repository; it enrolls an existing one locally and enables it.

The modal should be large enough to keep the candidate list useful at 80 columns, with a stacked fallback for narrow terminals:

```text
 Add Projects to this machine                         4 selected
 Source: GitHub                 Namespace: sase-org
 Filter repositories…

 [ ] docs-site       Public   pushed 3d ago     Documentation site
 [x] sase            Private  pushed today      SASE core application
 [x] sase-nvim       Public   pushed 2d ago      Neovim integration
 [✓] sase-github     already enabled
 [ ] old-prototype   Archived pushed 2y ago      (hidden by default)

 Space/m mark · a mark filtered · u clear · Tab change source/namespace
 Enter review · ^R refresh · Esc cancel
```

The source selector is populated from installed workspace-provider metadata and capability results. It must never contain a hard-coded GitHub branch. If exactly one provider supports repository discovery, it can be preselected. A provider that lacks browsable candidates can still participate through manual ref entry if it supports resolution.

The namespace selector should mix three generic sources:

1. fast local candidates from `ws_list_ref_namespaces`;
2. cached remote namespace discovery, when supported; and
3. a typed namespace, which is always allowed.

Selecting a namespace loads repositories asynchronously. The user can continue filtering cached results while refresh is in flight. Changing source, namespace, or filter must not discard marks; the persistent basket is the feature that makes the flow genuinely bulk-capable.

### Selection behavior

Rows should communicate lifecycle state before the user acts:

- **Unknown/unregistered:** selectable; adding materializes the project and explicitly enables it.
- **Known and disabled:** selectable, labeled “disabled”; adding re-enables it without recloning.
- **Known and enabled:** visible when useful but dimmed and non-selectable, labeled “already enabled.” It should not count toward the batch.
- **Conflict:** non-selectable with a concise reason, such as a canonical-name or destination collision.

`Space` and `m` should toggle the current row, matching both conventional checkbox UIs and the Projects tab’s mark vocabulary. `a` should mark the **filtered result set**, not every repository owned by the namespace; its footer text must say “mark filtered.” `u` clears the basket. This supports the common onboarding operation “filter to a family of repos, then add all” without creating a dangerous invisible selection.

Archived repositories should be hidden by default behind **Show archived**. Forks should remain visible and clearly badged because they are often legitimate working repos. Private repositories should be treated like normal candidates once provider authentication allows them.

Manual entry should accept one provider-native ref per line. It covers repositories outside listing limits, providers without browsing support, and users pasting a known set from another machine. Parsed refs join the same basket and go through the same review and preflight; this prevents the escape hatch from becoming a second implementation path.

### Ranking and completion quality

“Excellent completion” should optimize for likely work, not alphabetic completeness.

Namespace ordering should use:

1. exact and prefix matches against typed text;
2. namespaces represented by the current project and locally known projects;
3. explicitly configured namespaces;
4. authenticated-user and organization candidates returned by optional remote discovery; then
5. stable alphabetical order.

Repository ordering should retain the existing completion policy—prefix matches first, then recent `pushed_at`, then alphabetical—and add lifecycle awareness:

1. typed prefix/substring quality;
2. selectable before already-enabled rows;
3. non-archived before archived;
4. recent provider activity; and
5. stable name order.

Do not globally hide forks or private repositories, and do not rank by a GitHub-only signal in ACE. Providers should normalize their best available activity timestamp and may supply an optional provider rank. ACE should only apply generic tie-breakers.

The existing 10-minute repository cache and stale-on-error behavior are good foundations. The modal should display when results are stale and offer `Ctrl+R` to retry. Cached candidates should appear immediately; loading should never freeze the UI.

### Review, execution, and failure recovery

`Enter` should open a review step rather than immediately cloning. It summarizes:

- projects to create and enable;
- known projects to re-enable;
- provider and destination when known;
- conflicts that must be removed from the basket; and
- the number of network materialization operations.

The final action is **Add N projects**. Execution is a batch in the UX but not a filesystem transaction. Each item should be idempotent and report its own progress: queued, resolving, cloning/materializing, registering, enabled, or failed. Use small bounded concurrency rather than launching an unbounded set of clones. A failure must not roll back successful projects; the result screen should retain failed rows and offer retry. Refresh the Projects inventory as results land or once at completion, while preserving its prior selection.

Useful empty/error states are part of the main design:

- no provider: identify that no installed provider supports project discovery;
- authentication/tool failure: show the provider’s actionable structured error;
- no namespace candidates: focus typed/manual namespace entry;
- no matching repos: distinguish an empty provider result from a local filter miss;
- stale cache: keep results usable and show the refresh action; and
- partial batch failure: show successful and failed counts without closing automatically.

## Provider and backend design

### Reuse the existing discovery contract

The modal should consume the same provider-neutral namespace and repository candidate types as xprompt completion through a shared catalog service. It should not import the GitHub plugin or shell out to `gh` itself. This immediately lets any current or future provider implementing the existing hooks appear in the modal.

Extract or wrap the reusable policy now embedded in the xprompt modules:

- namespace/repository caching;
- filtering and ranking;
- stale fallback;
- structured loading/error/empty results; and
- normalization of a candidate into a provider ref.

Both xprompt completion and the Add Projects modal should become consumers. This avoids two subtly different definitions of “likely repositories.”

The fast `ws_list_ref_namespaces` contract should remain local-only so typing `#gh:` stays instantaneous. Add an **optional async/remote namespace-discovery hook** with structured status/errors and caching. The GitHub provider can implement it with the authenticated user and organization list. The catalog merges those results with fast local namespaces. Providers that do not implement the new hook continue to work through local or typed namespaces, so this is an additive capability rather than a GitHub-shaped requirement.

It is reasonable to add optional generic candidate fields such as `activity_at` and `provider_rank`; avoid fields named for GitHub concepts. Existing `pushed_at` can be retained for compatibility and mapped into the generic ranking projection.

### Separate planning from mutation

The Textual modal should not loop over `ws_resolve_ref` and directly edit lifecycle files. Introduce a provider-neutral application service with two phases:

1. **Plan:** normalize refs, deduplicate them, compare them with one lifecycle snapshot, and classify each as already enabled, re-enable, create, or conflict.
2. **Apply one item:** materialize through the owning provider when necessary, then explicitly write enabled state and return a structured result.

The batch controller can run the per-item operation with bounded concurrency and aggregate results. Planning/classification and lifecycle transitions are shared domain behavior and should be implemented in the Rust core (`sase-core`) or exposed there through a wire API, consistent with the project’s backend boundary. Provider I/O remains behind the Python plugin registry, with a thin Python orchestration adapter.

For the first implementation, `ws_resolve_ref` can remain the provider materialization primitive so existing providers work automatically. The application service supplies the missing intent boundary and explicitly records enabled state. If resolution and registration later need different semantics, add an optional `ws_register_project(..., initial_state=...)` hook with a compatibility fallback to `ws_resolve_ref`; do not make the modal depend on a new mandatory hook immediately.

### Guard unknown launch refs before resolution

The launch path needs a non-mutating admission check before `resolve_ref_from_prompt()` invokes `ws_resolve_ref`:

1. Parse explicit VCS refs using registered workflow metadata.
2. Use the provider’s read-only `ws_peek_ref` plus the lifecycle catalog to decide whether the ref maps to a project record known to SASE on this machine.
3. If no known record exists, raise a structured `UnknownProjectRef` error before clone, project-file creation, workspace allocation, or claim.
4. Render: “`#gh:owner/repo` is not added on this machine. Open Admin Center → Projects and press n to add it, then retry.” Provider display names should come from metadata.

This check must cover every launcher, not just ACE. It belongs before the shared mutating resolver in the launch service. ACE currently catches broad `ValueError`/`RuntimeError` during ref resolution and can return `None`; the new structured error must pass through to a visible launch error rather than silently falling back to the home/current project.

Do not implement the requirement by creating the project with `PROJECT_STATE: disabled` during launch. The running-field claim rejects disabled projects, so that design performs potentially expensive setup and then fails. It also creates an easy loophole: retrying the now-known ref could trigger the existing known-disabled auto-enable behavior.

Preserve known-disabled explicit launch re-enablement in the initial change. It is an established, separate policy and selecting a known project is stronger intent than mentioning a previously unknown remote locator. If the product later wants strict “disabled means never launch” semantics, that should be a separately named lifecycle decision with its own migration and UX.

## Suggested delivery sequence

Ship the UI and launch guard together so users never lose the old implicit onboarding path without its replacement.

1. Add core lifecycle classification/planning and structured result types, with tests for unknown, disabled, enabled, duplicate, and conflicting refs.
2. Build the shared provider-candidate catalog from the existing xprompt completion code and make current completion consume it unchanged.
3. Add the Add Projects modal, review screen, bounded execution, error recovery, configurable `n` binding, help text, and narrow/wide PNG snapshots.
4. Add the cross-launcher unknown-ref admission guard and ensure structured errors are not swallowed by ACE.
5. Add optional remote namespace discovery and implement it in `sase-github`; retain typed namespace/manual refs as the universal fallback.

Tests should cover provider absence and errors, stale cache, selection persistence across filters/namespaces, mark-filtered behavior, existing lifecycle states, partial success/retry, canonical-name collisions, idempotent reruns, and the guarantee that rejecting an unknown launch ref performs no clone or project-state write.

## Decisions that should remain explicit

- **Key:** `n` is recommended because `a` already means enable in the Projects tab and `+` is less discoverable. The binding remains configurable.
- **Batch semantics:** preflight the whole basket, but apply and report items independently; no rollback of completed clones.
- **Disabled projects:** selecting them in Add Projects means re-enable. Explicit launch of a known disabled project keeps its current auto-enable behavior for now.
- **Archived projects:** hidden by default, available through a toggle. Forks and private repos remain visible.
- **Manual refs:** always available, but secondary to discovery.
- **Remote namespace discovery:** additive optional provider capability; never make prompt completion wait on it.

## Recommended solution

Implement a provider-neutral **Add Projects** modal, opened with configurable `n` from the Projects sub-tab, as a hierarchical source/namespace browser with search, rich repository rows, a persistent multi-namespace selection basket, “mark filtered,” manual multiline refs, a review step, and per-item progress/retry. Back it with a shared candidate catalog extracted from the current VCS xprompt completion machinery, preserve its recency ranking and cache behavior, and add an optional cached remote namespace-discovery hook so a newly configured machine can suggest the authenticated user and organizations without slowing prompt completion.

Put normalization, lifecycle classification, deduplication, and transition policy in the Rust core, keep provider I/O behind the existing workspace-provider hooks, and expose a thin plan/apply orchestration layer to ACE. Use `ws_resolve_ref` as the initial compatibility materializer, then explicitly record enabled state as part of the user-confirmed Add operation.

At the same release boundary, reject explicit VCS launch refs that have no local SASE project record **before** calling the mutating resolver. Show an actionable message directing the user to Add Projects, and allow that structured error to reach every launcher instead of being swallowed. Preserve the established behavior for explicitly launching a known disabled project. This produces a single understandable rule: remote refs help users find projects, but only the Admin Center’s explicit Add flow enrolls a new project on the machine.
