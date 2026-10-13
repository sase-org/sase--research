# Evaluation & Recommendation: Renaming Artifacts Sub-Tabs in SASE

**Researcher:** `research.4e.gem`  
**Date:** October 2026  
**Target Surface:** SASE TUI (`sase ace`) — Artifacts Tab Sub-Navigation  

---

## Executive Summary

The proposal under consideration suggests renaming the sub-tabs on the top-level **Artifacts** tab as follows:
- **"Stitch"** $\rightarrow$ **"Commits"**
- **"Patch"** $\rightarrow$ **"PRs"**
- **"Bead"** $\rightarrow$ **"Bugs"**
- **"Plan"** $\rightarrow$ **"Plans"**
- **"File"** $\rightarrow$ **"Files"**

The stated motivations are twofold:
1. **Pluralization:** Adopt plural nouns to better match tabbed navigation conventions and represent collections of items.
2. **Common Terminology:** Replace SASE-specific nomenclature ("Stitch", "Patch", "Bead") with widely recognized industry terms ("Commits", "PRs", "Bugs").

### Core Findings & Verdict

1. **Pluralization is an unequivocal win:** All top-level TUI tabs in SASE are plural (**Agents**, **Artifacts**, **Services**). Internal sub-tab identifiers are already plural (`stitches`, `patches`, `beads`, `files`). Pluralizing the visual presentation labels restores grammatical harmony across the TUI hierarchy.
2. **"Stitch" $\rightarrow$ "Commits" is an excellent change:** What the pane renders is literally a Git/Mercurial commit log via `CommitsPane`. A "stitch" in SASE refers specifically to an ordered entry inside a Patch specification, but users browsing this tab are inspecting repository commits. Calling this tab "Commits" improves clarity and matches the underlying Textual widget name.
3. **"Patch" $\rightarrow$ "PRs" is a semantic error and architectural regression:** In SASE, a Patch is the local unit of change (`<key>.sase`). A Patch begins in `WIP` or `Draft` status purely on the local machine with **no Pull Request opened**. Furthermore, SASE supports non-GitHub workflows and local-only changes. Renaming "Patch" to "PRs" misleads developers into believing an unmailed local change has been published to GitHub. SASE previously migrated *away* from `prs` to `patches` for this exact reason.
4. **"Bead" $\rightarrow$ "Bugs" is a severe category error:** Beads are SASE's universal work-tracking primitives. They encompass **Plan beads** (architectures), **Epic beads** (multi-phase initiatives), **Phase beads** (sub-tasks of epics), and typed **Task beads** (of which `bug` is merely 1 of 6 built-in types alongside `feature`, `ci`, `flake`, `memory`, and `flag`). Calling this tab "Bugs" would mislabel epics and feature work as defects. SASE previously migrated *away* from `bugs` to `beads`.
5. **Recommended Solution:** Adopt the pluralized, domain-accurate tab labels:
   $$\text{Stitch} \rightarrow \mathbf{Commits}, \quad \text{Patch} \rightarrow \mathbf{Patches}, \quad \text{Bead} \rightarrow \mathbf{Beads}, \quad \text{Plan} \rightarrow \mathbf{Plans}, \quad \text{File} \rightarrow \mathbf{Files}$$
   This satisfies the pluralization goal completely, adopts common terminology where accurate ("Commits"), preserves SASE's domain model where vital ("Patches" and "Beads"), and requires zero breaking changes to internal IDs, configs, or CLI tooling.

---

## 1. Historical Context: How SASE Arrived Here

To evaluate whether changing these tab labels is a good idea, we must understand the historical evolution of the Artifacts tab navigation in SASE.

### The August 2026 Singularization (`bd6167875c`)
Prior to August 13, 2026, the Artifacts tab labels were **already plural**: `Stitches`, `Patches`, `Beads`, `Files`, and `Plans`.

In commit `bd6167875c` (*"feat(ace): rename Artifacts sub-tab labels to singular form"*), the project deliberately renamed all visible sub-tab labels to singular:
```python
# From commit bd6167875c:
labels = {
-   "patches": "Patches",
-   "stitches": "Stitches",
-   "beads": "Beads",
-   "files": "Files",
+   "patches": "Patch",
+   "stitches": "Stitch",
+   "beads": "Bead",
+   "files": "File",
}
```
**Why was that change made?**
1. **Dynamic Document Provider Pluralization:** The previous logic naively appended `"s"` to any provider kind: `f"{label}s"`. When sidecars with non-count or collective nouns were added (notably the `@research` document provider), naive pluralization resulted in grammatically awkward labels like `"Researches"`.
2. **Terminal Real Estate:** The singular forms shaved characters off the sub-tab strip, delaying degradation into the `compact` and `micro` responsive tiers on 80-column terminals.
3. **Locking Test:** The change added `tests/ace/tui/test_artifact_tab_labels.py` with an explicit assertion:
   ```python
   assert all(not label.casefold().endswith("s") for label in labels.values())
   ```

However, singularizing the sub-tabs created a subtle UX inconsistency:
- **Top-level tabs:** Plural (**Agents**, **Artifacts**, **Services**).
- **Internal IDs:** Plural (`stitches`, `patches`, `beads`, `files`).
- **Sub-tab display labels:** Singular (**Stitch**, **Patch**, **Bead**, **Plan**, **File**).

The user's intuition that plural names "seem more appropriate" is recognizing this very dissonance.

### Earlier Terminology Migrations: `prs` $\rightarrow$ `patches` and `bugs` $\rightarrow$ `beads`
The codebase retains backward compatibility mappings in `LEGACY_ARTIFACTS_SUBTABS` (`src/sase/ace/tui/_artifact_tab_model.py`):
```python
LEGACY_ARTIFACTS_SUBTABS: dict[str, ArtifactsSubTab] = {
    "prs": "patches",
    "bugs": "beads",
    "plans": "ref:plan",
    "other": "files",
    "chats": DEFAULT_ARTIFACTS_SUBTAB,
}
```
And in `src/sase/ace/tui/actions/artifacts_navigation.py`:
```python
def action_show_artifacts_prs(self) -> None:
    """Deprecated alias for action_show_artifacts_patches."""
    self._switch_artifacts_subtab("patches")

def action_show_artifacts_bugs(self) -> None:
    """Deprecated alias routing the retired Bugs sub-tab to Beads."""
    self._switch_artifacts_subtab("beads")
```
SASE historically **did** have "prs" and "bugs" sub-tabs! They were explicitly replaced because they no longer reflected what SASE does. Reverting back to them now would be a step backward.

---

## 2. In-Depth Critique of Each Proposed Tab Rename

| Current Label | Proposed Label | Recommended Label | Semantic Fidelity | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Stitch** | **Commits** | **Commits** | Very High | **Strongly Endorsed** |
| **Patch** | **PRs** | **Patches** | Inaccurate | **Reject "PRs", Pluralize to "Patches"** |
| **Bead** | **Bugs** | **Beads** | Misleading / False | **Reject "Bugs", Pluralize to "Beads"** |
| **Plan** | **Plans** | **Plans** | Very High | **Strongly Endorsed** |
| **File** | **Files** | **Files** | Very High | **Strongly Endorsed** |

---

### A. "Stitch" $\rightarrow$ "Commits" (Rating: Excellent)

#### What the Pane Actually Displays
The pane renders `CommitsPane` (`src/sase/ace/tui/widgets/artifacts/view.py:238`). It shows the project's Git or Mercurial repository commit history: commit SHAs, commit messages, author identity, timestamp, diff previews, and branch context.

#### The SASE Glossary Definition
In SASE terminology (`glossary:stitch`):
> *"A stitch is the lightweight ordered change record inside a Patch's `STITCHES:` section... The `sase stitch create` command and real Git/Mercurial commits are still called commits."*

And in `BUILTIN_PANE_DESCRIPTIONS["stitches"]`:
> *"Commits landed through SASE, each one a stitch inside the Patch that carries it. Rows are VCS commits across your enabled projects..."*

#### Why "Commits" is Better
- **Mental Model Alignment:** When a developer switches to this tab, they are looking for commit history. "Commits" requires zero cognitive translation.
- **Reduces Jargon:** SASE already has a steep learning curve. While "Stitch" has meaning in Patch workflow internals, using it for the general VCS history view is unnecessary gatekeeping.
- **Widget Name Consistency:** The Textual component has always been named `CommitsPane`.

---

### B. "Patch" $\rightarrow$ "PRs" (Rating: Problematic / Regressive)

#### Why "PRs" is a Bad Idea
1. **A Patch $\neq$ A PR:**
   - A Patch is SASE's local unit of change (`<key>.sase`).
   - A Patch progresses through five lifecycle states:
     $$\text{WIP} \longrightarrow \text{Draft} \longrightarrow \text{Ready} \longrightarrow \text{Mailed} \longrightarrow \text{Submitted}$$
   - When an agent or human creates a Patch, it starts in `WIP` or `Draft`. **No PR exists on GitHub or any forge.** The Patch may live locally for days across multiple agent iterations. Calling this tab "PRs" implies that every entry is an open GitHub Pull Request.
2. **False Operational Signals:**
   - If an engineer sees a tab labeled "PRs" with 10 rows, they naturally assume 10 Pull Requests are active upstream awaiting code review. In reality, 8 of them might be local agent workspace explorations.
3. **VCS / Forge Independence:**
   - SASE's design isolates VCS/forge concerns behind provider plugins (`sase-github`, `vcs_provider`). SASE can support Git repositories without GitHub (e.g., Gerrit, GitLab, plain git remotes). Naming the primary change abstraction "PRs" binds the user interface directly to GitHub's specific terminology.
4. **Historical Regression:**
   - SASE previously went through the pain of migrating from `prs` to `patches`. Undoing that architecture causes confusion and rolls back established documentation.

#### Better Approach: "Patches"
"Patch" is a standard software engineering term (used throughout Linux, Git, Mercurial, and software history). Pluralizing to **"Patches"** satisfies the pluralization requirement without compromising domain precision.

---

### C. "Bead" $\rightarrow$ "Bugs" (Rating: Severe Category Error)

#### Why "Bugs" is a Severe Category Error
1. **The Scope of Beads:**
   Beads are SASE's durable issue and work tracking system (`sase_beads.md`). Beads track:
   - **Plan Beads:** Top-level design documents and architectural initiatives (`--tier plan`).
   - **Epic Beads:** Multi-phase engineering initiatives (`--tier epic`).
   - **Phase Beads:** Sub-components executed by autonomous agents (`phase(<parent_id>)`).
   - **Task Beads:** Discrete follow-up tasks (`task(<slug>)`).
2. **Bugs are Only 1 of 6 Task Types:**
   Within task beads, the catalog defines:
   - `feature`: Out-of-scope product and tooling features.
   - `ci`: Confirmed CI build and test failures.
   - `flake`: Flaky test tracking.
   - `memory`: Documentation and agent memory maintenance.
   - `flag`: Feature flag lifecycle and retirement tracking.
   - `bug`: Actual software defects.
3. **User Confusion:**
   If the tab is labeled "Bugs":
   - Where do users expect to find Epics like "Migrate Rust Backend" or "Add Dark Theme"?
   - Seeing an architectural Epic under a tab labeled "Bugs" is completely nonsensical.
   - A user looking to triage new feature requests or review phase progress would never think to click "Bugs".
4. **Historical Regression:**
   `LEGACY_ARTIFACTS_SUBTABS["bugs"] = "beads"` already exists. SASE outgrew the concept of a simple bug tracker when Structured Agentic Software Engineering was built around epics, phases, and task beads.

#### Better Approach: "Beads"
"Bead" is SASE's signature concept (connecting individual pearls of work along a durable thread). Just as GitHub has "Issues" and Jira has "Issues/Tickets", SASE has "Beads". Pluralizing to **"Beads"** is clean, accurate, and faithful to SASE's architecture.

*(Note: If one insisted on a generic term, "Tasks" or "Issues" would be vastly preferable to "Bugs", but "Beads" remains superior because it encompasses Epics and Phases).*

---

### D. "Plan" $\rightarrow$ "Plans" (Rating: Excellent)

The plans sidecar directory is literally `plans/`. The pane displays Markdown plan documents across projects. Pluralizing to **"Plans"** is completely natural.

---

### E. "File" $\rightarrow$ "Files" (Rating: Excellent)

The underlying sub-tab ID is already `files`. The pane indexes durable artifact snapshots and files produced by agents. Pluralizing to **"Files"** is completely natural.

---

## 3. Pluralization & Document Provider Handling

One key reason commit `bd6167875c` moved to singular labels was that the provider label derivation function automatically appended `"s"`:
```python
def _provider_label(kind: str, spec: Mapping[str, Any]) -> str:
    ...
    if label.casefold().endswith("s"):
        return label
    return f"{label}s"  # <--- Turned "research" into "Researches"!
```
English mass nouns (uncountable nouns) like "Research" or "Evidence" do not take an "s". Appending `"s"` produced jarring labels.

### How to Correctly Handle Provider Pluralization

To avoid repeating the mistakes of August 2026:
1. **Explicit Spec Labels Take Precedence:**
   Document providers can declare their desired display label in `ref.pane.label` (or `ref.label`).
   For built-in plans (`src/sase/artifact_providers/_builtin.py`), declare `"label": "Plans"` explicitly in the spec:
   ```python
   def builtin_plan_ref_provider_spec() -> dict[str, Any]:
       return {
           "provider": "plan",
           "ref": {
               "kind": "plan",
               "label": "Plans",  # <--- Explicit plural label
               ...
           }
       }
   ```
2. **No Blind String Concatenation:**
   Do **not** reintroduce `f"{label}s"` in `_provider_label()`. If a sidecar provider does not specify an explicit label, use its title-cased kind directly (`kind.title()`). This allows providers like `@research` to display as **"Research"** (natural collective noun), while providers like `@rfcs` or `@notes` display as their authors intended.

---

## 4. Implementation Architecture & Impact Analysis

### Principle: Separate Display Labels from Internal Identifiers

The cleanest architectural approach is to **only modify display labels**, keeping internal IDs stable.

| Element | Internal Identifier (Keep Unchanged) | Display Label (Change to Recommended) |
| :--- | :--- | :--- |
| Commits Pane | `"stitches"` | `"Commits"` |
| Patches Pane | `"patches"` | `"Patches"` |
| Beads Pane | `"beads"` | `"Beads"` |
| Plans Pane | `"ref:plan"` | `"Plans"` |
| Files Pane | `"files"` | `"Files"` |
| Agents Pane (if restored) | `"agents"` | `"Agents"` |

#### Why Keep Internal Identifiers Stable?
Internal identifiers (`stitches`, `patches`, `beads`, `files`, `ref:plan`) are woven throughout the entire codebase:
1. **Configuration:** `default_config.yml` and `sase.schema.json` reference `ace.artifacts.panes.stitches`, `copy_group: "artifacts_stitches"`, and keymap groups.
2. **Persisted State:** User sessions cache `current_artifacts_subtab`, query history, and saved queries under these IDs.
3. **CLI Commands:** `sase artifact pane show stitches` and `sase artifact pane show beads`.
4. **Action Handlers:** `action_show_artifacts_patches()`, `action_show_artifacts_stitches()`, etc.
5. **Contract Adapters:** `BUILTIN_ADAPTERS["stitches"]`, `BUILTIN_ADAPTERS["beads"]`, etc.

Modifying display labels in `fixed_descriptor()` gives the user 100% of the UI experience with zero breakage across persistence, configuration, or CLI contracts.

---

### Visual Grammar & Terminal Real Estate Impact

The SASE TUI uses `PanelTabStrip` (`src/sase/ace/tui/widgets/panel_tab_strip.py`), which features a 3-tier responsive ladder:
$$\text{Full} \longrightarrow \text{Compact} \longrightarrow \text{Micro}$$

Let us compare the character lengths of the different label strategies across the strip (assuming standard fixed panes + Plans + Research):

```
Current (Singular):
  1 ◉ Stitch │ 2 ⎇ Patch │ 3 ◈ Bead │ 4 ✎ Plan │ 5 ⚲ Research │ 6 ▤ File
  Total label length: 6 + 5 + 4 + 4 + 8 + 4 = 31 characters

User Proposal (Commits, PRs, Bugs, Plans, Files):
  1 ◉ Commits │ 2 ⎇ PRs │ 3 ◈ Bugs │ 4 ✎ Plans │ 5 ⚲ Research │ 6 ▤ Files
  Total label length: 7 + 3 + 4 + 5 + 8 + 5 = 32 characters (+1 char total)

Recommended Approach (Commits, Patches, Beads, Plans, Files):
  1 ◉ Commits │ 2 ⎇ Patches │ 3 ◈ Beads │ 4 ✎ Plans │ 5 ⚲ Research │ 6 ▤ Files
  Total label length: 7 + 7 + 5 + 5 + 8 + 5 = 37 characters (+6 chars total)
```

#### Responsive Behavior:
- In `full` mode, an extra 6 characters across the entire width of the terminal is negligible (easily fitting standard 80, 100, and 120 column windows).
- If the terminal shrinks below the threshold, `PanelTabStrip` smoothly reduces separator padding (`compact`), and if space is critically constrained, it drops into `micro` mode where inactive labels are hidden entirely (showing only digits and icons: `1 ◉ │ 2 ⎇ │ 3 ◈ │ 4 ✎ PLANS │ 5 ⚲ │ 6 ▤`).
- Therefore, adopting full plural labels will **not** degrade TUI responsiveness.

---

### Code Locations Requiring Updates

If the recommended solution is implemented, the changes are localized and straightforward:

1. **`src/sase/ace/tui/_artifact_tab_descriptors.py`**:
   Update `fixed_descriptor()`:
   ```python
   def fixed_descriptor(subtab: ArtifactsSubTab) -> ArtifactsTabDescriptor:
       labels = {
           "patches": "Patches",
           "stitches": "Commits",
           "beads": "Beads",
           "agents": "Agents",
           "files": "Files",
       }
       label = labels[subtab]
       ...
   ```

2. **`src/sase/artifact_providers/_builtin.py`**:
   Explicitly declare `"label": "Plans"` in `builtin_plan_ref_provider_spec()`:
   ```python
   def builtin_plan_ref_provider_spec() -> dict[str, Any]:
       return {
           "schema_version": ARTIFACT_REF_PROVIDER_SPEC_SCHEMA_VERSION,
           "provider": "plan",
           "ref": {
               "kind": "plan",
               "label": "Plans",
               ...
           }
       }
   ```

3. **`tests/ace/tui/test_artifact_tab_labels.py`**:
   Update the regression test to enforce the new plural labels:
   ```python
   _EXPECTED_FIXED_LABELS = {
       "agents": "Agents",
       "stitches": "Commits",
       "patches": "Patches",
       "beads": "Beads",
       "files": "Files",
   }
   ```

4. **Documentation and Help Modals**:
   - `docs/ace.md`: Update prose referencing sub-tabs (e.g., "Commits, Patches, Beads, configured document providers, and Files").
   - `docs/artifacts_pane_visual_grammar.md`: Align references.
   - Any visual SVG/PNG test snapshots that check tab label strings.

---

## 5. Comparison Matrix

| Evaluation Dimension | Current State | User's Proposal | Recommended Solution |
| :--- | :--- | :--- | :--- |
| **Visible Labels** | Stitch, Patch, Bead, Plan, File | Commits, PRs, Bugs, Plans, Files | Commits, Patches, Beads, Plans, Files |
| **Grammatical Consistency** | ❌ Mixed (Top tabs plural, sub-tabs singular) | ⚠️ Mostly plural (PRs is plural acronym) | ✅ Uniformly plural |
| **VCS Commit Clarity** | ⚠️ Jargon ("Stitch") | ✅ Obvious ("Commits") | ✅ Obvious ("Commits") |
| **Local Change Accuracy** | ✅ Accurate ("Patch") | ❌ Inaccurate (calls local draft a "PR") | ✅ Accurate ("Patches") |
| **Task / Epic Accuracy** | ✅ Accurate ("Bead") | ❌ Inaccurate (calls Epics & Features "Bugs") | ✅ Accurate ("Beads") |
| **Document Providers** | ✅ Clean ("Research") | ⚠️ Risk of awkward pluralization | ✅ Declarative / natural collective nouns |
| **Breaking Changes** | None | High (if IDs change) / Low (if labels only) | Zero breaking changes |
| **Implementation Complexity** | N/A | High cognitive debt | Trivial (< 5 files modified) |

---

## 6. Recommended Actionable Roadmap

If you decide to proceed, here is the concrete step-by-step roadmap:

### Phase 1: Presentation Layer Updates
1. Modify `fixed_descriptor()` in `src/sase/ace/tui/_artifact_tab_descriptors.py` to map:
   - `"stitches"` $\rightarrow$ `"Commits"`
   - `"patches"` $\rightarrow$ `"Patches"`
   - `"beads"` $\rightarrow$ `"Beads"`
   - `"files"` $\rightarrow$ `"Files"`
   - `"agents"` $\rightarrow$ `"Agents"`
2. Update `builtin_plan_ref_provider_spec()` in `src/sase/artifact_providers/_builtin.py` to specify `"label": "Plans"`.
3. Verify that `_provider_label()` leaves provider labels without explicit overrides in natural form (no forced `"s"`).

### Phase 2: Test Suite & Documentation Alignment
1. Invert the assertion in `tests/ace/tui/test_artifact_tab_labels.py` from requiring singular to requiring the explicit plural mapping.
2. Run `just check` to catch any unit tests or modal filter tests asserting `"Stitch"` or `"Bead Pane"` (e.g. `test_help_modal_filter.py`).
3. Update `docs/ace.md`, `docs/artifacts_pane_contract.md`, and `docs/artifacts_pane_visual_grammar.md` to reflect the updated labels.

### Phase 3: Verification
1. Run `sase artifact pane show stitches` and `sase artifact pane show beads` to ensure CLI diagnostic descriptions remain clear and accurate.
2. Launch `sase tui` (or run Textual headless visual tests) to verify responsive ladder transitions (`full` $\rightarrow$ `compact` $\rightarrow$ `micro`).

---

## Conclusion

Getting rid of the names **"Patch"** and **"Bead"** in favor of **"PRs"** and **"Bugs"** is **not the right call**: it misrepresents local unmailed changes as GitHub PRs, and it misrepresents high-level architectural Epics and Features as simple defects.

However, the user's instincts regarding **"Commits"** and **Pluralization** are spot-on. The ideal synthesis is:
$$\mathbf{Commits} \quad \big| \quad \mathbf{Patches} \quad \big| \quad \mathbf{Beads} \quad \big| \quad \mathbf{Plans} \quad \big| \quad \mathbf{Files}$$

This delivers maximum clarity, professional polish, and complete architectural integrity.
