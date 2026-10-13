# Artifacts Sub-Tab Rename: Stitch/Patch/Bead → Commits/PRs/Bugs + Pluralization

## Summary

The proposal — rename Stitch→Commits, Patch→PRs, Bead→Bugs, Plan→Plans,
File→Files — is half right and half factually wrong. The pluralization
instinct is correct: the current fixed labels are singular
(Stitch, Patch, Bead, Agent, File) while much of the surrounding copy is
already plural, and plural reads better for collection tabs. The vocabulary
swap is not justified for two of the three renames, and would partially
revert a deliberate, breaking, already-paid-for rename from August 2026.
The recommended solution is **pluralize the domain terms, do not replace
them**: Stitches, Patches, Beads, Plans, Files — as a **label-only**
change with all pane ids, artifact ref kinds, CLI verbs, and saved-state
keys left stable.

## Current state (verified in tree)

- Fixed pane ids (`src/sase/ace/tui/_artifact_tab_model.py`):
  `agents`, `stitches`, `patches`, `beads`, `files`, plus provider panes
  `ref:<kind>` (Plan lives at `ref:plan`). `DEFAULT_ARTIFACTS_SUBTAB =
  "stitches"`.
- Display labels (`src/sase/ace/tui/_artifact_tab_descriptors.py`,
  `fixed_descriptor()`): singular — `"patches": "Patch"`,
  `"stitches": "Stitch"`, `"beads": "Bead"`, `"agents": "Agent"`,
  `"files": "File"`. The strip renders `descriptor.label`
  (`src/sase/ace/tui/widgets/artifacts/view.py`, `_panel_tabs()`), so the
  user literally sees the singular forms today. The Plan provider pane
  defaults to `"Plan"` (`plans_data_models.py`).
- Surrounding copy is already plural and inconsistent with the strip:
  builtin empty states say "No stitches / No patches / No beads", the
  bead↔patch relation labels are "Patches" and "Plans"
  (`_artifact_tab_contract_adapters.py`), and `docs/ace.md` writes
  "Browse Stitches, Patches, Beads … and Files."
- The Stitches content is rendered by an internally-named `CommitsPane`
  (`widgets/artifacts/view.py`, `widgets/artifacts/commits_pane.py`), i.e.
  the codebase already treats "commits" as the colloquial rendering name
  for the stitches adapter (whose `target_prefix` is `"commit"`).
- Scale of the identifier surface: ~780 files under `src/sase` + `tests`
  mention `"stitches"`, `"patches"`, or `"beads"`. Pane ids flow into
  digit shortcuts, `show_artifacts_<subtab>` actions, command-palette
  entries, keymap overrides, saved queries and query profiles, copy
  groups, contract digests, and PNG visual-snapshot goldens.

## Why the three vocabulary swaps fail differently

### 1. Stitch → Commits: understandable, but lossy

Per the glossary (`sase/memory/glossary/stitch.md`), a stitch is "the
lightweight ordered change record inside a Patch's `STITCHES:` section" —
every tracked VCS commit has one, but a stitch need not have a commit
(proposals keep numeric-plus-letter ids such as `(2a)`), and real
Git/Mercurial commits made through the workflow are still called commits.
So "Commits" is the familiar superset name for what the pane mostly
shows, and the internal `CommitsPane` name proves the team already thinks
of it that way. But a pure "Commits" label quietly promises "every row =
one VCS commit," which is false for proposal rows, and it discards the
word the rest of the system (patch `STITCHES:` sections, `sase stitch`
CLI, stitch↔patch relations, `stitch_patch_tag` source) uses
everywhere else. Verdict: tolerable as a display label, but it buys
familiarity at the cost of breaking the one word that ties the pane to
its data model — and "Stitches" (pluralized, kept) captures 90% of the
benefit with none of the conceptual drift.

### 2. Patch → PRs: factually wrong; do not do this

Per the glossary (`sase/memory/glossary/patch.md`), a Patch is "SASE's
local unit of change" and "a Patch may exist without a PR, represented by
an absent `PR:` field," with lifecycle WIP → Draft → Ready → Mailed →
Submitted. Labeling the pane "PRs" mislabels every local-only patch —
exactly the patches users spend most time in — and implies remote-only
semantics the pane does not have. This is also a reversion: commit
`b5786b57f2` ("retire the Bugs sub-tab and rename Artifacts PRs to
Patches," Aug 2026) deliberately renamed the `prs` sub-tab id to
`patches` end to end as a breaking change, precisely to stop calling
local change units PRs. Undoing the label half of that decision keeps
all of the confusion and none of the migration benefit. Verdict: reject.

### 3. Bead → Bugs: seriously wrong; do not do this

A bead is not a bug. Beads span `plan`, `phase`, and typed `task` beads,
and the task catalog (`sase/memory/task_types`, `sase bead create -T`)
has five agent-creatable types: bug, CI failure, feature, flaky test,
memory — bug is one of five. Renaming the pane "Bugs" tells the user the
pane contains defect reports when it mostly contains plans, phases,
features, flakes, and CI failures. It also resurrects a pane the project
deliberately killed: the same `b5786b57f2` change deleted the remote-only
Bugs pane outright (twelve keymap actions, copy targets, PNG goldens)
because "the Beads pane's external-issue chip and the issue mirror
already cover that." The legacy alias table still maps `"bugs" →
"beads"` for saved-state compatibility — reviving "Bugs" as the visible
label while `"bugs"` remains a deprecated alias for `"beads"` is a
predictable support trap. Verdict: reject unambiguously.

### 4. Plan → Plans, File → Files: correct direction, wrong scope as proposed

Pluralizing collections is right, and "Plans"/"Files" match user
expectations and the docs' existing plural usage. But pluralizing only
these two while also swapping the other three vocabularies leaves the
strip conceptually incoherent (three familiar-git terms + two plurals,
no shared convention). If pluralization is the goal, apply it uniformly
to the kept domain terms.

## Implementation analysis: label-only vs. id rename

There are two completely different changes hiding inside "rename the
sub-tabs," with order-of-magnitude different costs:

- **Label-only (display string).** Touch `fixed_descriptor()` labels,
  the Plan provider default label, hardcoded empty-state titles, the
  `docs/ace.md` + pane-contract/visual-grammar docs, help-modal copy,
  and regenerate PNG goldens showing the strip. Keep every id
  (`stitches`, `patches`, `beads`, `files`, `ref:plan`), every artifact
  ref kind (`stitch:`, `patch:`, `bead:`, `plan:`, `file:`), every CLI
  verb (`sase stitch/patch/bead/artifact`), every
  `show_artifacts_<subtab>` action and keymap override, and the
  `LEGACY_ARTIFACTS_SUBTABS` alias table untouched. Saved queries,
  saved UI state, and user keymaps keep working. This is a small,
  reviewable diff plus golden regeneration.
- **Id rename (pane ids / ref kinds / CLI).** Requires migrating persisted
  sub-tab selections, saved queries per pane id, keymap override keys,
  command ids (with another round of deprecated aliases like
  `action_show_artifacts_prs`), contract/copy-group names, the provider
  `ref:<kind>` namespace, tests asserting digit→pane mapping (the last
  rename fixed "roughly two dozen test files" for exactly this), and
  another silent number-key meaning change. Nothing in the proposal's
  goal (friendlier words, plurals) requires any of this. Strongly
  discourage: all pain, no user-visible gain over label-only.

A middle path worth naming explicitly is **dual labeling** — primary
domain term with the familiar term in the pane description/brief,
empty state, or help text (e.g. strip shows "Patches"; the pane brief
reads "Local change units; a Patch becomes a PR when mailed"). That
teaches the vocabulary instead of forking it, and the descriptor model
already supports it (`description`/`description_body` are first-class
fields next to `label`). Recommend doing this for Patches at minimum.

## Gotchas the implementer must handle

1. **Auto-pluralization bug.** Provider-pane empty states are generated
   as `f"No {label.lower()}s"` (`_artifact_tab_contract.py`). If the
   Plan label becomes the already-plural "Plans," that generator emits
   "No planss" unless it is fixed (pluralize at render from a singular
   base, or store singular + plural forms). Builtin panes use hardcoded
   strings and are unaffected, but any shared helper must be audited.
2. **Strip width.** The tab strip shows icon + label + digit for up to
   six panes (Agent when unretired, four fixed, providers, Files last
   with the highest digit). Pluralization adds ~1 character per tab;
   safe, but verify against the narrow-terminal snapshot tests rather
   than assuming.
3. **Number keys do not move.** Digit shortcuts are positional
   (`assign_artifacts_digit_shortcuts`), Files always highest. A
   label-only change keeps 1=Stitches/Agent-first, 2, 3… stable — call
   this out in the changelog, because the previous rename silently
   remapped every number key and users still remember.
4. **"Bugs" and "PRs" stay reserved as legacy aliases.** `bugs → beads`
   and `prs → patches` remain in `LEGACY_ARTIFACTS_SUBTABS`, and
   `show_artifacts_bugs` / `show_artifacts_prs` remain as compat
   actions. Do not mint new panes or commands under those names.
5. **Docs and goldens are the long tail.** The strip appears in
   `docs/ace.md`, the pane-contract and visual-grammar docs, the
   quickstart ("Cycle Artifacts: …"), and every PNG snapshot of the tab
   strip. Budget the change as docs+goldens+~a dozen test touch-ups,
   not as a two-line label edit.

## Adjustments to the requirements (explicit)

1. **Reject** Stitch→Commits, Patch→PRs, Bead→Bugs as visible labels.
   (Commits is the only one I would even accept as a label, and I still
   prefer keeping Stitches for model coherence.)
2. **Accept, and generalize**, the pluralization ask: pluralize all kept
   labels, not just Plan/File.
3. **Constrain** the change to display labels + descriptions + docs +
   goldens. Explicitly out of scope: pane ids, ref kinds, CLI verbs,
   command/action ids, saved-query keys, keymap override keys.
4. **Add** a one-line mapping subtitle for the two domain terms new
   users trip on (Patches ≈ local PRs; Stitches ≈ ordered commit
   records), rather than renaming the concepts away.

## Recommended solution

Ship **pluralized domain labels, label-only**:

| Pane id (unchanged) | Old label | New label |
|---|---|---|
| `stitches` | Stitch | Stitches |
| `patches` | Patch | Patches |
| `beads` | Bead | Beads |
| `ref:plan` | Plan | Plans |
| `files` | File | Files |
| `agents` (when unretired) | Agent | Agents |

Concretely: change the five literals in `fixed_descriptor()` and the
Plan provider default; fix the provider empty-state pluralizer for
already-plural labels; add pane-brief subtitles mapping Patches→PRs and
Stitches→commits for onboarding ("Patches — local change units, mailed
as PRs"); update `docs/ace.md`, pane-contract docs, and help-modal copy;
regenerate visual snapshots; changelog-note that ids, commands, refs,
saved queries, keymaps, and number-key assignments are unchanged. Do not
touch `stitch:`/`patch:`/`bead:` ref kinds or the `sase stitch/patch/bead`
CLI surface — the user's hesitation about "getting rid of the
stitch/patch/bead tab names" is well founded, and on the evidence the
answer is: keep the names, fix the number.
