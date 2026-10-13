# Renaming the Artifacts Sub-Tabs: `Stitch/Patch/Bead/Plan/File` → `Commits/PRs/Bugs/Plans/Files`?

_Researcher: cld · 2026-10-13 · Scope: the `sase tui` Artifacts tab strip (labels only)_

## TL;DR

| Proposed rename      | Verdict                         | One-line reason                                                                                                                                                                                                         |
| -------------------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pluralize every tab  | **Yes**                         | Tabs hold collections. The top-level strip (`Agents · Artifacts · Services`), the docs, and the pane prose already use plurals. The August switch to singular had no recorded rationale.                               |
| `Stitch` → `Commits` | **Yes**                         | The pane's rows really are VCS commits. Each row's origin is `stitch`, `auto`, or `manual`. With sidecars shown, about 80% of rows are not stitches. The pane's own empty-state and detail text already say "commit". |
| `Patch` → `PRs`      | **No. Keep `Patches`.**         | A Patch is defined as "with or without a PR". The VCS layer is provider-neutral (git/hg; GitHub is a plugin). "Patch" is already ordinary software vocabulary.                                                         |
| `Bead` → `Bugs`      | **No. Keep `Beads`.**           | Only 3.5% of beads are `bug`-typed. "Bug" already has four other meanings in SASE. "Issues" and "Tasks" both collide with existing SASE terms.                                                                          |
| `Plan` → `Plans`     | **Yes**                         | Give the plan provider spec an explicit label. Do not bring back an auto-pluralizer.                                                                                                                                    |
| `File` → `Files`     | **Yes**                         | Trivial.                                                                                                                                                                                                                |

**Recommended strip:** `1 ◉ Commits │ 2 ⎇ Patches │ 3 ◈ Beads │ 4 ✎ Plans │ 5 ∴ Research │ 6 ▤ Files`

**Also recommended:**

1. **Consolidate first.** The labels are hard-coded in about 8 places today. Gather them into one table, then flip them in one change.
2. **Record a decision.** This would be the fourth relabel of this strip in about nine weeks. Each of the last two cost more than 200 PNG goldens.

---

## 1. Where things stand today

**Live strip at 120×40.** I captured it on 2026-10-13 with `sase screenshot -- -t artifacts`:

```text
1 ◉ STITCH │ 2 ⎇ Patch │ 3 ◈ Bead │ 4 ✎ Plan │ 5 ∴ Research │ 6 ▤ File
◉ Commits landed through SASE, each one a stitch inside the Patch that carries it.
```

- The Agent pane is hidden by the sunset flag `artifacts_agent_pane_retired` (commit `101c853939`, 2026-10-12).
- `Plan` and `Research` are provider-backed document tabs. `Plan` comes from the builtin plan provider; `Research` comes from the research-artifacts provider plugin.

**Identity vs. presentation.** Sub-tab **ids** are plural and serve as storage identity: `stitches`, `patches`, `beads`, `ref:plan`, `files`.

- The ids are used by persisted UI state, keymap action ids, copy-mode groups, config keys, query profiles, and `sase artifact pane show <id>`.
- **Labels** are presentation-only. A label change therefore needs no data migration.
- Legacy id aliases already exist in `src/sase/ace/tui/_artifact_tab_model.py:42`: `prs → patches`, `bugs → beads`, `plans → ref:plan`.

**Where the labels come from:**

- `fixed_descriptor()` in `src/sase/ace/tui/_artifact_tab_descriptors.py:69-75` holds the built-in labels.
- `_provider_label()` derives provider labels: a configured `label` / `ref.label` wins, otherwise the kind is title-cased.
- 17 call sites read `descriptor.label` dynamically. These include the strip, the command palette (`Show Artifacts: <label>`), Textual binding descriptions, and the quickstart rows.
- Several surfaces **hard-code their own copy** of the label instead (inventory in §6).

**The surrounding UI already uses plurals:**

- Top-level tabs are `Agents`, `Artifacts`, `Services`.
- `docs/ace.md` describes the Artifacts tab as "Browse Stitches, Patches, Beads, configured document providers, and Files".
- The pane empty states read "No stitches", "No patches", "No beads", "No plans".

**Newcomers already get an explanation.** Every pane has a one-sentence description brief. It renders under the strip and also appears as the tab's hover tooltip (`src/sase/ace/tui/_artifact_tab_descriptions.py`). This matters for the jargon argument (§4).

---

## 2. History: this strip has already been relabeled three times since August

| Date       | Change                                                                                                                                                                                           | Where                                                            |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| 2026-08-10 | **Commits → Stitches** (epic `sase-j8`). Rationale: rename "before the abstraction diverges". A stitch can be a proposal like `(2a)` with no commit.                                              | `plan:202608/stitch_rename.md`; 228 PNG goldens in `9c46891c5e`  |
| 2026-08-11 | **Bugs pane retired, PRs → Patches** (`sase-jd.8`). "Bugs" was a _different_ pane that listed remote tracker issues. Those issues are now mirrored into beads.                                    | `plan:202608/retire_bugs_rename_prs_to_patches.md`; 212 PNGs in `b5786b57f2` |
| 2026-08-13 | **Plural → singular** (`bd6167875c`). The prompt was only "Can you help me stop pluralizing the sub-tab names…". No rationale was recorded.                                                      | `plan:202608/singular_artifacts_subtab_names.md`                 |
| 2026-08-26 | Agent pane moved first                                                                                                                                                                           | `4dd2995028`                                                     |
| 2026-10-12 | Agent pane retired behind a sunset flag                                                                                                                                                          | `101c853939`                                                     |

**The proposal reverses all three August decisions:**

- `Commits` was the pre-`sase-j8` label.
- `PRs` was the pre-`sase-jd.8` label.
- Plural was the pre-`bd6167875c` form.
- `Bugs` was never a name for beads. It belonged to a separate, since-deleted pane.

**None of these choices exists as a decision record** in the `decisions` web. That is how the strip can oscillate. Whatever is chosen now should be written down, with a "reopens when" condition.

---

## 3. Evidence, tab by tab

### 3.1 Pluralization: yes

**For plural:**

- **Tabs name collections.** Each tab is a list of many rows. Comparable tools use plural collection tabs: GitHub ("Issues", "Pull requests"), lazygit panels ("Files", "Branches", "Commits"), and Gerrit ("Changes").
- **Parallelism.** Microsoft Fluent 2 asks for tab labels that are parallel "grammatically and conceptually". Apple's HIG and Carbon ask for short noun labels. None of these guides mandates plural, but the parent strip here is plural, so a singular child strip is the odd one out.
- **Name and prose stop disagreeing.** The singular rename had to invent a two-category rule ("name surfaces" singular, "prose" plural). It then reworded sentences that interpolate the label, for example `f"{provider_label} documents have not loaded yet."`. With plural labels, the label and the prose agree again.
- **Help filtering works again.** The August plan knowingly broke Help-modal filtering: typing `beads` stopped matching the section title `Bead Pane`. Plural titles restore that match.

**For singular (the best case):** a singular label matches the artifact-ref kind (`@stitch:`, `@patch:`, `@bead:`, `@plan:`, `@file:`). That benefit is weak: the ref kind is already visible in copy targets and detail panels, and the plural ids carry the identity anyway.

**Provider tabs.** The August change also deleted an auto-pluralizer from `_provider_label()`. That was right: English plurals are irregular, and `Research` is a mass noun. **Do not bring the pluralizer back.** Instead:

- Give the builtin plan provider an explicit `label: Plans` in `builtin_plan_ref_provider_spec()` (`src/sase/artifact_providers/_builtin.py`).
- Leave every other provider's `label` / `ref.label` as the provider's choice. `Research` stays `Research`.
- Document a convention: a provider `label` should be the plural or mass noun for the collection.

### 3.2 `Stitch` → `Commits`: yes, it is more _accurate_, not just more common

I measured the pane's data source (`sase stitch list … -n 0 -N -f json`, last 30 days, run on athena):

| Scope                                  | Rows   | `stitch` (✦)  | `auto` (↻)    | `manual` (✎, "no SASE provenance") |
| -------------------------------------- | ------ | ------------- | ------------- | ---------------------------------- |
| Default (primary + linked repos)       | 2,723  | 2,515 (92.4%) | 67 (2.5%)     | 141 (5.2%)                         |
| `-S` (the pane's `sidecar:true` toggle) | 18,742 | 3,643 (19.4%) | 14,949 (79.8%) | 150 (0.8%)                         |

**The pane already treats "stitch" as a facet of a row, not as the row type:**

- Each row's origin is classified by `src/sase/vcs_log/_origin_style.py`.
- The empty state says "No commits match the current project scope and filters." (`_artifact_tab_contract_adapters.py:165-166`).
- The detail placeholder says "Select a commit to inspect its message and diff."
- The builtin description body says "Rows are VCS commits across your enabled projects".
- Rows group by date, repository, or **author**.
- The glossary itself says: "real Git/Mercurial commits are still called commits."

**Caveat.** `sase-j8` chose "Stitches" so the UI would carry that name before stitches diverge from commits (proposals `(2a)` have no commit). Today the pane lists commits, not commit-less proposals. **Reopen condition:** if this pane ever lists stitches that have no commit, revisit the label.

**Keep "stitch" wherever it names the real concept.** None of these change:

- the `stitches` id and the `stitches_*` keymap actions
- the `ace.artifacts.stitches` config key and the `artifacts_stitches` copy group
- `@stitch:` refs, `sase stitch`, the Patch `STITCHES:` section, and the ✦ origin glyph

The command palette already keeps `stitches` as a search alias.

**Also fix the description summary.** It currently reads "Commits landed through SASE, each one a stitch inside the Patch that carries it." That is false for `auto` and `manual` rows. Suggested replacement: "Commits across your projects; the ✦ rows were landed through SASE as stitches."

### 3.3 `Patch` → `PRs`: no; keep `Patches`

**This is the strongest of the three renames after Commits.** On athena, 315 of 315 Patch records carry a `PR:` URL. 241 of them (77%) are `PR_ORIGIN: external`, adopted by `sase patch sync-external`. In this user's GitHub projects, the pane is effectively a PR list _today_.

**Why I still recommend against it:**

1. **The model says otherwise.** A Patch is "SASE's local unit of change … with or without a PR behind it yet" (glossary and builtin pane description). WIP Patches have no PR. The status lifecycle (`WIP → Draft → Ready → Mailed → Submitted`) uses changelist vocabulary ("Mailed").
2. **"PRs" is one provider's word.** SASE's VCS layer is provider-neutral (`git`, `hg`, `--vcs-provider`), and GitHub support lives in the `sase-github` plugin. Other tools say GitLab "merge requests", Gerrit "changes", Phabricator "revisions", Google "CLs". Hard-coding GitHub vocabulary into the core TUI puts the word at the wrong layer.
3. **"Patch" is already common English for software.** Think diff/patch, `git format-patch`, Gerrit "patch sets". Unlike _bead_ and _stitch_, it does not need translating.
4. **Patch is SASE's most pervasive noun.** It appears in `sase patch`, `sase tui -t patches`, the "Patches query", `SASE_PATCH`, `@patch:`, and the Patch detail panel. A "PRs" tab whose every row opens a "Patch" creates a two-names-for-one-thing seam on the most central object.
5. **The palette already maps `prs` → Patches.** Users who think "PRs" still find the tab.

If GitHub vocabulary is wanted later, do it at the right layer: let the active VCS provider supply the noun (`PRs` / `MRs` / `CLs`). Don't hard-code it.

### 3.4 `Bead` → `Bugs`: no; keep `Beads`

Bead store composition (`sase bead list -s all -f json -n 0`):

| Slice              | Count | Share                                                                                    |
| ------------------ | ----- | ---------------------------------------------------------------------------------------- |
| All beads          | 7,478 | phase 70.5% · plan 13.3% · task 16.1%                                                    |
| `bug`-typed tasks  | 263   | **3.5% of all beads**                                                                    |
| Non-closed (657)   |       | bug 140 · flake 133 · plan 105 · ci 83 · phase 81 · feature 79 · memory 22 · untyped 13 · flag 1 |

**"Bugs" would mislabel at least 96% of rows.** It also collides with four existing meanings of "bug":

1. **The `bug` task type.** A "Bugs" tab reads like the filter `task_type:bug`.
2. **The `@bug:` artifact-ref kind.** It still parses as a historical reader ("cite the bead with @bead:<id>", `src/sase/artifact_ref_prompt.py:78`).
3. **The "Bugs" command-palette category.** It already means the external-issue actions _inside_ the Beads pane: `start_bead_issue_mode` "Beads: issue actions" and `beads_open_bug` / `beads_copy_bug`.
4. **The retired Bugs pane** (remote tracker issues). Its legacy id `bugs` already redirects to `beads`.

**Alternatives I considered:**

- **`Issues`** is the closest common term.
  - For it: beads describes itself as "AI-native issue tracking". SASE's own bead field is `issue_type`, and its projection is `issues.jsonl`. Jira's issue types (Epic/Story/Task/Bug) map well onto plan/phase/task.
  - Against it: SASE's Beads pane already uses "issue" for the _linked external tracker issue_. The UI shows "**External issue:**", "issue #N", and "mirrored local bead differs from cached issue". A tab called "Issues" whose rows can each link to "an issue" is muddled.
  - Verdict: second-best. Only viable if the external-issue UI is first renamed to "tracker issue" / "GitHub issue".
- **`Tasks`** collides with the `task` bead issue type, one of the three.
- **`Work` / `Work items`** are vague and Azure DevOps-flavored.
- **`Beads`** is precise and is SASE's ubiquitous term: `sase bead`, `@bead:`, task beads in `/sase_new_task`, notifications. It is also a recognized name in agent tooling (Steve Yegge's beads). The description brief explains it at first touch: "The work SASE tracks: plan and epic beads, the phases beneath them, and standalone task beads."

### 3.5 `Plan` → `Plans`, `File` → `Files`: yes

- **Plan:** set the explicit provider label (§3.1).
- **Plan defaults:** update the fallback defaults that still say `"Plan"`:
  - `src/sase/ace/tui/widgets/artifacts/plans_data_models.py:92`
  - `plans_pane.py:88`
  - `plans_rendering.py:36,154`
  - `plans_list.py:168`
- **Plan prose:** reword `plans_list.py:170-172,332`. With a plural label, `f"Loading {label.casefold()} documents…"` becomes "Loading plans documents…", so use `f"Loading {label.casefold()}…"`.
- **Plan fast-startup label:** check the fast-startup descriptor in `src/sase/ace/testing/_startup.py`.
- **File:** trivial.

### 3.6 Surfaces outside the proposal

- **Agent (retired pane):** do **not** pluralize it to `Agents`. That would duplicate the top-level `Agents` tab label. Leave `Agent` until the sunset flag's removal deletes the pane. `src/sase/artifact_cli/pane.py:68,101` also says "Artifacts ▸ Agent is retired".
- **Research:** provider-owned mass noun. Leave it.

---

## 4. Is this a good idea in general?

**Partly. The instincts are right but applied too uniformly.**

**What's right:**

- Pluralize.
- Reduce jargon on the first surface a newcomer touches.

**What's wrong:** the proposal treats `stitch`, `patch`, and `bead` as equally obscure and equally mismatched. They aren't.

- _Stitch_: SASE jargon, and the common word (**commits**) is **more precise** for this pane. → rename.
- _Patch_: already common English. The common alternative (**PRs**) is **narrower** than the concept and provider-specific. → keep.
- _Bead_: jargon, but the proposed word (**Bugs**) is **wrong for ≥96% of rows** and collides four ways. The better common word (**Issues**) collides too. → keep.

**A rule worth adopting:** _a tab's label names what its rows are. Use the common word when it names the rows precisely. Keep the SASE word when the common word is narrower, wrong, or already means something else in SASE._

**Further concerns:**

- **Ubiquitous language.** A tab label is the doorway to a domain object. If the tab says "Bugs" but each row's detail, copy target, `@bead:` ref, CLI, and notifications say "bead", the user has to learn both words anyway. The common label only hides the real term until the first click. DDD's "one language across code, docs, and speech" applies to screens too. This is also why `Commits` is safe: the rows really are commits everywhere.
- **The cost of churn is real.** Each previous relabel regenerated 200+ PNG goldens. `tests/ace/tui/test_artifact_tab_labels.py` currently asserts the _opposite_ rule (`not label.casefold().endswith("s")`). Without a decision record, the next relabel is a matter of mood.
- **Labels are scattered.** About 8 hard-coded copies (§6) mean every relabel is a hunt. Consolidating them first makes this relabel, and any future one, a one-table change.

---

## 5. Requirement adjustments (called out explicitly)

| #   | Original requirement | Adjusted requirement                                                                                                                                                                       | Why                                                                     |
| --- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| R1  | `Patch` → `PRs`      | **Keep `Patches`** (plural only).                                                                                                                                                          | §3.3: model is broader than PRs; provider-neutral core; already common. |
| R2  | `Bead` → `Bugs`      | **Keep `Beads`** (plural only).                                                                                                                                                            | §3.4: 3.5% accurate; four collisions; `Issues` collides too.            |
| R3  | `Stitch` → `Commits` | **Rename the tab label only.** Keep `stitch` for the concept (id, refs, CLI, keymaps, config, Patch `STITCHES:`, ✦ origin) and update the pane description summary.                         | §3.2: rows are commits, and stitch is one origin among three.           |
| R4  | `Plan` → `Plans`     | **Use an explicit `label: Plans` in the builtin plan provider spec.** No auto-pluralizer; providers own their labels; `Research` unchanged.                                                 | §3.1: irregular plurals and mass nouns.                                 |
| R5  | (implicit)           | **Do not pluralize the retired `Agent` pane.**                                                                                                                                             | §3.6: would duplicate the top-level `Agents` tab.                       |
| R6  | (new)                | **Consolidate all hard-coded label copies into the descriptor table** before or alongside the flip.                                                                                         | §4: future relabels become one-line.                                    |
| R7  | (new)                | **Write a decision record** (e.g. `decisions:artifacts-tab-labels`) stating the rule from §4, plus reopen conditions: "pane lists commit-less stitches" and "SASE adopts provider-derived nouns". | Stop the oscillation.                                                   |
| R8  | (new, optional)      | **Per-user override `ace.artifacts.panes.<id>.label`.** It sits next to the existing `ace.artifacts.panes.<id>.description` / `description_body` keys.                                      | Lets you try `Issues` or `PRs` locally without code churn.              |

**Notes on R8:**

- Per the SASE flag policy, a choice users keep forever is a config field, not a feature flag.
- Treat R8 as optional. It adds one more thing for docs to hedge about ("the Commits pane, unless relabeled").

---

## 6. Implementation guide

### 6.1 Label inventory (what to touch)

**Derived automatically from `descriptor.label`, so no edit is needed:** the tab strip, palette `Show Artifacts: …`, Textual binding descriptions, quickstart `Jump:` / `Cycle Artifacts:` rows, and the hover descriptions.

**Hard-coded copies to consolidate (R6) or flip:**

| Surface                    | Location                                                                                                                                                       |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Built-in descriptor labels | `src/sase/ace/tui/_artifact_tab_descriptors.py:69-75`                                                                                                          |
| Help-guide onboarding copy | `src/sase/ace/tui/widgets/patch_onboarding.py:41-47` (`_ARTIFACT_LABELS`, a duplicate table)                                                                   |
| Copy-mode context label    | `src/sase/ace/tui/actions/clipboard/_artifacts.py:36-52`. This runs on a key path; read the cached fixed descriptor, never trigger provider discovery.          |
| Pane header badges         | `widgets/artifacts/commits_rendering.py:68` (`" Stitch "`), `beads_rendering.py:56`, `files_rendering.py:69`, `plans_rendering.py:36,154`                       |
| Help modal section titles  | `modals/help_modal/patches_artifact_bindings.py:80,102,146,212`, `patches_copy_bindings.py:27,69,111`, docstring in `filter_model.py:59`                        |
| Empty states               | `_artifact_tab_contract_adapters.py:165` (`"No stitches"` → `"No commits"`). Leave the others: they are already plural prose.                                  |
| Pane description           | `_artifact_tab_descriptions.py` (`"stitches"` summary, §3.2)                                                                                                   |
| Plan provider label        | `src/sase/artifact_providers/_builtin.py` (add `label`), plus the `"Plan"` fallbacks and prose listed in §3.5                                                   |
| Docs                       | `docs/ace.md:151,168` ("Stitch, Patch, and Bead are always 1, 2, 3"; "selects Stitch by default"), sections at `:327-449` and `:641`; the pane-contract and visual-grammar docs |
| Tests                      | `tests/ace/tui/test_artifact_tab_labels.py` (flip the rule), plus about 60 test files that assert strip or help text (`"2 ◉ STITCH"`, `"Bead Pane"`, `Copy Mode · …`) |
| Goldens                    | Every PNG that shows the Artifacts strip or the Help panel. Prior relabels touched 212–228 PNGs; 64 current goldens match Artifacts/Help/copy-as name patterns. |

### 6.2 What does _not_ change, so no migration is needed

**Ids stay the same:** `stitches`, `patches`, `beads`, `ref:plan`, `files`. That leaves all of these untouched:

- pane DOM ids and CSS selectors
- keymap action ids and `default_config.yml` keys
- copy groups and query profiles
- persisted session state and saved queries
- `sase artifact pane show <id>` JSON (the `label` field changes value, but the id contract doesn't)

**Process consequences:**

- **No feature flag.** Flags exist to keep an old _branch_ reachable. A label has no branch.
- **No `sase-core` change.** The labels are TUI presentation, inside the Rust-boundary litmus test.

**Palette search keeps working:**

- Aliases already include the id (`stitches`) and `prs`.
- Add `stitch`, `commits`, `bead`, and `bugs` aliases if wanted.

**Help filter:** after the flip, typing `stitch` no longer matches the "Commits Pane" title. Keymap descriptions that mention stitches still match. If that matters, append "(stitches)" to the section description, not the title.

### 6.3 Width impact on the strip's fit ladder

The strip picks the widest tier that fits: **F**ull → **C**ompact → **M**icro. Micro hides inactive labels.

**How I measured:**

- I rendered each label set with the real `PanelTabStrip._build_content()` to get its width.
- I measured the strip's available width in the headless `AcePage` harness: 100 cols→59, 110→69, 120→79, 130→89, **140→74**, 150→84, 160→94, 180→82, 200→102.
- Live widths differ slightly because the launch-context bar has a different width there. The live 120-col capture rendered **compact**, which matches the table.

| Label set                         | full / compact / micro width | Tier at 100 · 110 · 120 · 130 · 140 · 150 · 160 · 180 · 200 cols |
| --------------------------------- | ---------------------------- | ----------------------------------------------------------------- |
| **6 tabs (with Research)**        |                              |                                                                   |
| current (singular)                | 82 / 70 / 30                 | M · M · C · F · C · F · F · F · F                                 |
| user proposal                     | 83 / 71 / 31                 | M · M · C · F · C · F · F · **C** · F                             |
| plural SASE terms                 | 89 / 77 / 32                 | M · M · C · F · **M** · **C** · F · **C** · F                     |
| **recommended**                   | 88 / 76 / 31                 | M · M · C · F · **M** · **C** · F · **C** · F                     |
| **5 tabs (no Research provider)** |                              |                                                                   |
| current                           | 65 / 55 / 26                 | C · F · F · F · F · F · F · F · F                                 |
| user proposal                     | 66 / 56 / 27                 | C · F · F · F · F · F · F · F · F                                 |
| **recommended**                   | 71 / 61 / 27                 | **M** · **C** · F · F · F · F · F · F · F                         |

**The cost.** The recommended set is 6 cells wider than today. The common 120-col and 130-col cases don't change tier. It loses a tier at 140, 150, and 180 cols with six tabs, and at 100–110 cols with five tabs. The user's proposal is almost width-neutral (+1) only because `PRs` and `Bugs` are short.

**Mitigation options, cheapest first:**

1. **Accept it.** Micro still shows digits, icons, and the active label.
2. **Look at the 140-col dip on its own merits.** At 140 cols and wider, the left `#artifacts-split-spacer` jumps from 8 to 33 cells to keep the strip optically centered against the launch-context bar. That spacer takes 25 cells from the strip, so 140 cols is _narrower_ than 130. Narrowing the spacer would recover the space.
3. **Use `PanelTab.compact_label` / `micro_label`.** These already exist but are unused by Artifacts. Avoid singular compact labels, though: they would bring the inconsistency back.

### 6.4 Suggested phasing

**Phase 0: decision record (R7).** Use `/sase_memory_write`. It is a memory change, so it goes through that skill.

**Phase 1: consolidate the labels, with no visible change (R6).**

- Make `fixed_descriptor()` the only source of built-in labels.
- Make `patch_onboarding`, clipboard, header badges, and Help titles read from it, or from a tiny shared `ARTIFACTS_LABELS` table beside `ARTIFACTS_ICONS` / `ARTIFACTS_ACCENTS` in `_artifact_tab_model.py`.
- Add a test that no other module hard-codes a tab label.

**Phase 2: flip the labels.** One change covering:

- the table values
- `label: Plans` in the builtin plan provider spec
- the plan prose rewording
- the Stitch description and empty state
- `test_artifact_tab_labels.py` (assert plural, plus the `Commits` id-to-label mapping)
- docs
- goldens via `just fix-tui-screenshots`, run under `/sase_monitor` as the TUI-screenshot memory says

Run `just check`. Run `just check-full` only when explicitly asked, per the `check-full-is-explicit` decision.

**Phase 3 (optional): `ace.artifacts.panes.<id>.label` override (R8).**

- Key the descriptor cache on `current_config_token()`. Today `fixed_descriptor()` is a bare `@cache`.
- Keep the copy-mode key path free of config reloads (see the TUI-perf memory).
- Update `sase.schema.json` and `default_config.yml` (the gotchas memory).

---

## 7. Alternatives considered

| Option                                                                                         | Pros                                                                                        | Cons                                                                                                                       | Verdict           |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| **A. Proposal as written** (`Commits/PRs/Bugs/Plans/Files`)                                    | Most "common" vocabulary; width-neutral                                                     | `Bugs` wrong for ≥96% of rows and collides four ways; `PRs` narrower than the model and GitHub-specific; reverses three August decisions with no record | Reject            |
| **B. Plural SASE terms** (`Stitches/Patches/Beads/Plans/Files`)                                | Pure revert of `bd6167875c`; zero vocabulary risk                                           | Keeps `Stitches` on a pane that is a commit timeline (up to ~80% non-stitch rows); widest set                              | Acceptable fallback |
| **C. Recommended hybrid** (`Commits/Patches/Beads/Plans/Files`)                                | Each label names its rows precisely; common word only where it is the precise word          | +6 cells; one more relabel of goldens                                                                                      | **Recommend**     |
| **D. Hybrid with `Issues`** (`Commits/Patches/Issues/Plans/Files`)                             | More newcomer-friendly than `Beads`; matches `issue_type` and beads' own README             | Collides with the Beads pane's "external issue" vocabulary; every row still says "bead"                                     | Only after renaming the external-issue UI |
| **E. Keep defaults, add a config override only**                                               | No churn for others; you can experiment                                                     | Doesn't fix the singular/plural question or the inaccurate `Stitch` label                                                  | Add-on, not a substitute |
| **F. Dual labels** (e.g. `Commits (stitches)`), or a subtitle line                              | Teaches both words                                                                          | Width-hostile; the description brief already does this job                                                                 | Reject            |

---

## 8. Open questions for Bryan

1. **Do you ever want GitHub vocabulary in the core TUI?** If yes, prefer a provider-supplied noun over hard-coding `PRs`.
2. **Would you rename the Beads pane's "external issue" wording** ("tracker issue" / "GitHub issue")? That would free `Issues` (option D).
3. **Do you want per-user label overrides (R8),** or should one set of labels serve everyone?

---

## 9. Recommended solution

Adopt **option C**:

```text
1 ◉ Commits │ 2 ⎇ Patches │ 3 ◈ Beads │ 4 ✎ Plans │ 5 ∴ Research │ 6 ▤ Files
```

1. **Pluralize every tab** to match the top-level strip and the existing prose. Do it with explicit labels, not a pluralizer. The plan provider gets `label: Plans`; `Research` is unchanged; the retired `Agent` pane is left alone.
2. **Rename `Stitch` → `Commits` for the tab label only.** The rows really are commits: 92% stitches by default, 19% with sidecars shown. Keep `stitch` for the concept (id, `@stitch:`, `sase stitch`, the ✦ origin, Patch `STITCHES:`), and correct the pane's description summary.
3. **Keep `Patches`, not `PRs`.** The model is PR-optional and VCS-neutral, and "patch" is already plain English. The palette already answers to `prs`.
4. **Keep `Beads`, not `Bugs`.** Only 3.5% of beads are bugs, "bug" already means four other things in SASE, and the description brief explains "bead" on first contact.
5. **Consolidate the about 8 hard-coded label copies into one table first,** then flip everything in one golden-regenerating change. Ids, keymaps, config, and persisted state don't change, so no flag and no migration are needed.
6. **Write a decision record** with the rule "a tab's label names what its rows are" and two reopen conditions: "the pane lists commit-less stitches" and "SASE adopts provider-derived nouns". That keeps the strip from flipping a fifth time.
7. **Optionally**, add `ace.artifacts.panes.<id>.label` so you can try `Issues` or `PRs` locally without another repo-wide relabel.

---

## Sources

**Internal evidence (this repo and its sidecars):**

- Commits `c69d16378c`, `7a4b4daa78`, `9c46891c5e` (sase-j8), `b5786b57f2` (sase-jd.8), `bd6167875c`, `4dd2995028`, `101c853939`.
- Plans `plan:202608/stitch_rename.md`, `plan:202608/retire_bugs_rename_prs_to_patches.md`, `plan:202608/external_artifact_ingestion.md`, `plan:202608/singular_artifacts_subtab_names.md`.
- Bead `sase-j8`, and the chat transcript `sase-kv.5.w1--plan` (2026-08-13).
- Glossary strands `stitch`, `patch`, `artifact`, and `artifact reference`.
- Live data: `sase stitch list`, `sase bead list`, `~/.sase/projects/*.sase`. Screenshot via `sase screenshot`; strip widths measured with `PanelTabStrip` and `AcePage`.

**External:**

- Microsoft Fluent 2, Tablist usage (parallel, brief noun labels): <https://fluent2.microsoft.design/components/web/react/tablist/usage>
- Apple Human Interface Guidelines, Tab views: <https://developer-mdn.apple.com/design/human-interface-guidelines/components/layout-and-organization/tab-views>
- Carbon Design System, Tabs usage: <https://v9.carbondesignsystem.com/components/tabs/usage>
- KDE HIG, Labels (singular for single-object commands, otherwise plural): <https://develop.kde.org/hig/style/writing/labels/>
- ILIAS tab-label guidelines (nouns, similar length): <https://docu.ilias.de/go/wiki/wpage_4153_1357>
- Beads, "AI-Native Issue Tracking" README copy: <https://r2.datahub.io/cm1z9oo5v0003md0cj3q7ngnb/main/raw/.beads/README.md>; package page <https://pkg.go.dev/github.com/steveyegge/beads@v0.62.0>
- Evans, Domain-Driven Design pattern summaries (Ubiquitous Language): <https://www.domainlanguage.com/wp-content/uploads/2016/05/PatternSummariesUnderCreativeCommons.doc>
- Apache Causeway, background on ubiquitous language: <https://causeway.apache.org/userguide/3.1.0/background-context-and-theory.html>
- lazygit panels (Status/Files/Branches/Commits/Stash): <https://www.freecodecamp.org/news/how-to-use-lazygit-to-improve-your-git-workflow/>, <https://computingforgeeks.com/?p=3280>
- Gerrit "changes" vs GitHub PRs vs Phabricator Differential: <https://graphite.com/guides/gerrit-vs-phabricator-key-differences>, <https://lists.llvm.org/pipermail/llvm-dev/2021-August/152292.html>
