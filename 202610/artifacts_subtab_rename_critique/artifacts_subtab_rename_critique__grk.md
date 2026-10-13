# Artifacts sub-tab labels: keep domain terms

**Researcher:** grk (independent swarm member)
**Date:** 2026-10-13
**Question:** Should the Artifacts sub-tabs be renamed Stitch→Commits, Patch→PRs, Bead→Bugs, Plan→Plans, File→Files?
**Verdict:** Do not implement the proposed rename. Teach the existing terms; do not replace them.

---

## Recommended solution

Keep the current tab-strip labels:

| Pane id | Keep | Do not use |
| --- | --- | --- |
| `stitches` | **Stitch** | Commits |
| `patches` | **Patch** | PRs |
| `beads` | **Bead** | Bugs |
| `ref:plan` | **Plan** | Plans, unless a local config override |
| `files` | **File** | Files |

Do the learnability work with surfaces that already exist, without splitting the TUI from the CLI, glossary, and `@stitch` / `@patch` / `@bead` refs:

1. Keep command-palette alias `prs` → Patches. Add aliases `commits` → Stitches and `issues` / `bugs` → Beads so search still finds the pane under the old words.
2. Keep pressing `D` as the teaching rail. The built-in pane descriptions already say the true thing in common language ("Commits landed through SASE, each one a stitch inside the Patch that carries it.").
3. Add one dual-language line in Help / onboarding per pane (`Stitch — commits and proposals`), not a second name on the strip.
4. Leave CLI verbs, artifact-ref kinds, keymap ids, persisted sub-tab ids, and glossary keywords unchanged.

If a later change is still wanted, the only label tweak worth considering is a *second* debate about singular vs plural of the *same* nouns (`Stitches`, `Patches`, `Beads`, `Plans`, `Files`). That is a separate, smaller, cosmetic question. It was already decided in August 2026 in favor of singular, and it should not be bundled with a domain-term rollback.

---

## What the proposal is asking

The request is two independent changes packaged as one:

- **A. Domain-term replacement.** Drop Stitch / Patch / Bead from the tab strip in favor of GitHub-flavored Commits / PRs / Bugs.
- **B. Pluralization.** Show collection nouns (Plans, Files) instead of kind nouns (Plan, File).

The stated goal is "more common terminology" plus "pluralize the tab names (which seems more appropriate)." The author already flags the hard part: *I'm not sure if getting rid of the stitch/patch/bead tab names is the right call.*

That uncertainty is the right instinct. A and B should be decided separately. A is a product-vocabulary reversal. B is chrome grammar. Mixing them hides that A is the expensive, semantically false half.

---

## Current state

### Top-level vs sub-tab grammar

sase's TUI has three top-level tabs, all plural collection names: **Agents**, **Artifacts**, **Services**. Artifacts then has mutually exclusive *kind* panes. Built-in labels today are singular:

```
Agent (retired by default) · Stitch · Patch · Bead · Plan · Research · File
```

Ids stay plural (`stitches`, `patches`, `beads`, `files`). Display labels are singular (`Stitch`, `Patch`, `Bead`, `File`). Provider panes title-case the kind (`plan` → `Plan`, `research` → `Research`) unless the sidecar spec sets `label` verbatim.

Source of truth: `src/sase/ace/tui/_artifact_tab_descriptors.py` (`labels` dict) and `tests/ace/tui/test_artifact_tab_labels.py`, whose docstring is "Regression coverage locking the singular Artifacts sub-tab labels."

The test also asserts no fixed label ends with `s`. That lock is intentional, not leftover.

### What each pane actually lists

| Strip label | Pane id | What the rows are | CLI / ref |
| --- | --- | --- | --- |
| Stitch | `stitches` | VCS commits landed through SASE, each recorded as a stitch on a Patch. Proposal stitches `(2a)` are commitless until accepted. | `sase stitch`, `@stitch` |
| Patch | `patches` | Local units of change. Every SASE-managed PR has exactly one Patch; a Patch may have no `PR:` field. | `sase patch`, `@patch` |
| Bead | `beads` | Plan beads, epic/phase beads, and typed task beads (bug, feature, flake, memory, ci, flag, …). External tracker issues are mirrored *into* beads, not listed as a separate inventory. | `sase bead`, `@bead` |
| Plan | `ref:plan` | Markdown plan documents in the plans sidecar (a document provider, not a fixed pane). | `@plan` |
| File | `files` | Indexed artifact snapshots, not the working tree. | `@file` / `sase artifact` |

The built-in `D` descriptions already speak both languages. Stitch: "Commits landed through SASE, each one a stitch inside the Patch that carries it." Patch: "SASE's unit of change: one Patch per change, with or without a PR behind it yet." Bead: "plan and epic beads, the phases beneath them, and standalone task beads."

Onboarding copy does the same: Stitch is "Trace committed work across projects." Patch is "Inspect Patches and move PRs through review." Bead is "Review task, epic, and phase work items."

The product already uses common words to *explain* the domain terms. The proposal would use common words to *replace* them.

### Compatibility aliases already in the tree

```python
LEGACY_ARTIFACTS_SUBTABS = {
    "prs": "patches",
    "bugs": "beads",
    "plans": "ref:plan",
    "other": "files",
    "chats": DEFAULT_ARTIFACTS_SUBTAB,  # retired pane
}
```

The command palette for the Patches pane still searches under `prs`. Saved UI state that says `bugs` lands on Beads. The names the proposal wants back are already the *legacy* names.

---

## Historical evidence: this is a rollback, not a new idea

The Artifacts strip has already walked the exact path the proposal wants to reverse.

### 1. Commits → Stitches (`sase-j8`, August 2026)

Epic title in the coordination notes: *"Rename sase vcs to sase stitch and the ACE Commits sub-tab to Stitches."*

- `c69d16378c` — identifier `commits` → `stitches` (DOM ids, actions, commands).
- `9c46891c5e` — visible pane label Commits → Stitches, with goldens and docs.
- `2f85bf025b` — tests still saying `commits` had gone vacuous; a golden captured minutes before the flip still rendered `1 Commits`.

The CLI verb moved with the pane: `sase stitch create` is the commit/proposal/PR dispatcher. The glossary is explicit that "the `sase stitch create` command and real Git/Mercurial commits are still called commits," while the *record* is a stitch.

### 2. PRs → Patches, and Bugs retired (`sase-jd.8`, August 2026)

Plan `plan:202608/retire_bugs_rename_prs_to_patches.md`, epic `plan:202608/external_artifact_ingestion.md`.

The epic's consequence, quoted:

> because beads become a faithful superset of tracker issues, the Artifacts tab no longer needs a separate Bugs inventory. Its sub-tabs collapse to **Stitches · Patches · Beads · Files**

Commit `b5786b57f2` (`feat(ace)!: retire the Bugs sub-tab and rename Artifacts PRs to Patches`):

- Deleted the Bugs pane, its twelve keymap actions, and its PNG goldens.
- Renamed sub-tab id `prs` → `patches`.
- Renumbered the digit keys (a silent muscle-memory break, called out as `!`).
- Kept `prs` / `bugs` as deprecated aliases so saved state and palette search kept working.

Bugs was not renamed to Beads. Bugs was *deleted* because it was the last UI that listed remote-only issues. External issues now live as chips on beads (`beads_open_bug` / `E`, `external_ref` such as `bug:sase#42`). Putting "Bugs" back on the strip would reintroduce a pane name for an inventory that no longer exists, and would collide with:

- Patch field `BUG:` (a tracker link on a Patch, not a bead)
- Artifact-ref kind `bug:`
- Task type `bug` (one of several task-bead types)
- Key `beads_open_bug`

### 3. Plural → singular (`bd6167875c`, 2026-08-13)

Two months before this research, the strip, header badges, command palette, Help modal, and copy-mode notifications were renamed *from* Stitches / Patches / Beads / Files / Plans *to* Stitch / Patch / Bead / File / Plan. Auto-appending `s` on provider kinds was dropped so Research would not become "Researchs". A regression test locked the singular forms.

Re-pluralizing Plan and File now is reversing a two-month-old, test-locked decision for a preference ("seems more appropriate") with no new evidence.

Timeline:

```text
Commits · PRs · Bugs · … · Files
        │           │
        │           └─ sase-jd.8: Bugs deleted; PRs → Patches
        └─ sase-j8:   Commits → Stitches
                │
                └─ Aug 13: Stitches/Patches/Beads/Files/Plans → singular
                        │
                        └─ today: proposal asks for Commits · PRs · Bugs · Plans · Files
```

---

## Critique of each proposed mapping

### Stitch → Commits — close for the *rows*, false for the *object*

**Grain of truth.** The Stitches adapter's `target_prefix` is `"commit"`. The pane description says rows are VCS commits. The default query (`sidecar:false merges:hide since:24h`) is a commit log. A new user looking at the list will think "this is git log."

**Why the tab still should not say Commits.**

- A stitch is the ordered change record inside a Patch's `STITCHES:` section. Numeric stitches `(1)`, `(2)` usually have commits. Proposal stitches `(2a)` are commitless until accepted (`glossary:stitch`, `docs/change_spec.md`).
- The CLI, host finalizer, and agent skills all say `sase stitch create`. Calling the tab Commits and the command stitch trains two names for one action.
- sase-j8 existed *specifically* to stop calling this pane Commits once the domain object had a name.

If the strip says Commits, a user who then reads `sase stitch create`, `@stitch:`, or a Patch's `STITCHES:` block has to re-learn. If the strip says Stitch, the `D` blurb already translates: these rows are commits.

**Adjustment:** keep Stitch. Optionally add palette alias `commits`. Optionally say "Stitch — commits and proposals" in Help.

### Patch → PRs — false, and already reversed

A Patch is SASE's local unit of change. Glossary and `docs/change_spec.md` both state: every PR SASE creates or manages is associated with exactly one Patch, **and a Patch may exist with no `PR:` field**. External PRs are *adopted as Patches* (`external_pr_mirror`); SASE-created Patches can sit in WIP/Draft for a long time before they have a GitHub PR.

Graphite's public vocabulary is "stacked PRs" / "stacked diffs" because Graphite's unit of review *is* a GitHub PR. Gerrit uses "change" + "patch set" because its unit of review is a commit under a Change-Id, and a GitHub PR is the wrong name for that. SASE is closer to Gerrit-on-GitHub than to GitHub-native PRs: the durable local object is the Patch; the PR is an optional remote projection.

Calling the tab "PRs" would:

- Hide Patches that have not been mailed yet (the ones a user most needs to find).
- Collapse the PR badge and the Patch identity, which `sase-jd`'s `patch_pr_ui` phase spent effort keeping as two signals (`PR#812` vs `external` vs no PR).
- Undo `b5786b57f2` and the `prs` → `patches` identifier rename.

The command palette already finds the pane when you type `prs`. That is the right place for the common word.

**Adjustment:** keep Patch. Do not revive "PRs" as the strip label.

### Bead → Bugs — the worst mapping, and a retired UI

Beads are not bugs. `docs/beads.md` opens: "Bead is a lightweight, git-native issue tracking system." Issue types are **plan**, **phase**, and **task**. Task types include bug, feature, flake, memory, ci, and flag. The Beads list groups under a **Tasks** banner. The `D` description lists plan, epic, phase, and standalone task beads.

`sase-jd` retired the Bugs pane because tracker issues are a *subset* of beads (every mirrored issue has a bead; many beads have no issue). Risk 8 in that epic is explicit: "Trackers hold feature requests and questions, not only bugs."

Renaming Bead → Bugs would:

- Mislabel plan/epic/phase/feature/flag work as bugs.
- Collide with `BUG:`, `bug:` refs, task type `bug`, and `beads_open_bug`.
- Recreate a name whose pane was deleted on purpose.

GitHub's Issues tab is named Issues, not Bugs, for the same reason. Linear uses Issues. Jira uses Issues. Even if SASE wanted a common word, **Issues** would be less wrong than **Bugs** — and still worse than **Bead**, because the CLI, agent instructions, and `@bead:` citations all say bead.

**Adjustment:** keep Bead. If a common-word alias is needed, use `issues` in the command palette, never Bugs on the strip.

### Plan → Plans — harmless, already supported, not worth a code change

Plan is a *provider* pane (`ref:plan`), not a fixed pane. `_provider_label()` already honors a spec `label` verbatim. The test suite documents this:

```python
assert _provider_label("plan", {"label": "Plans"}) == "Plans"
```

The builtin plan spec currently has no `label`, so the kind title-cases to `Plan`. Setting `ref.label: Plans` in the sidecar spec (or a project `sase.yml`) would pluralize that one tab without touching fixed-pane policy.

Docs and keymap comments already say "Plans sub-tab" / "Plans pane" when they mean the collection. The strip says Plan because August 2026 made every kind-tab singular, including providers, so Research would not become Researchs.

**Trap:** provider empty states are `No {label.lower()}s`. If the label is already `Plans`, that becomes "No planss". Any pluralization of a provider label has to stop naively appending `s`.

**Adjustment:** leave Plan. If someone strongly wants Plans, set the provider `label` and fix empty-state pluralization. Do not treat this as part of a Stitch/Patch/Bead rename.

### File → Files — same grammar question as Plan

File is a fixed pane. The rows are indexed artifact snapshots (`sase artifact list` is "indexed files only"). Plural Files would match how people talk about a list, and would match top-level tab grammar (Agents, Artifacts, Services). It would also reopen the singular lock and force PNG golden churn for every snapshot that shows the strip.

**Adjustment:** keep File unless the project separately reopens singular-vs-plural for every kind-tab, including Research and any future provider.

---

## Is the plan a good idea?

**No, as stated.** The common-terminology half is a vocabulary rollback that makes three of five labels lie. The pluralization half is a real but small chrome preference that was already decided the other way, recently, with tests.

### What is good in the impulse

- Tabs should have strong information scent (Nielsen Norman Group, "Tabs, Used Right": users must predict a tab's contents from the label).
- Nielsen heuristic 2 ("Match between the system and the real world") says: speak the user's language, not internal jargon.
- Apple HIG: tab labels should be short nouns that describe pane contents; prefer a single word.
- UX Stack Exchange consensus on nav labels: if the destination is a *list of many*, plural is the usual choice.

Those heuristics are why "PRs" and "Commits" feel tempting. A GitHub-native developer already has those words.

### Why they do not win here

Heuristic 2 is about the *user's* language. SASE's primary users are people who already run `sase stitch create`, file beads, and read agent instructions that define Stitch, Patch, and Bead as glossary terms. For that audience, the "real world" *is* the SASE domain. GitHub's PR is one projection of a Patch, not the object.

Heuristic 4 (consistency) cuts the other way. A tab named PRs next to a command `sase patch`, a query language that says Patches, a help card titled "What is a Patch?", and an onboarding sentence that uses both Patch and PR is the dual-vocabulary tax. The current design pays that tax once, in descriptions. The proposal would pay it on every glance at the strip.

Heuristic 2 also forbids *false* familiar words. NN/G's complex-applications writeup notes that a broken real-world mapping (their coffee-cup-means-available example) stays expensive even for daily users, because they must keep translating. "Bugs" for a list of plan beads is that kind of mismatch. "PRs" for WIP Patches with no `PR:` field is too.

Apple's "one-word noun" rule is already satisfied by Stitch, Patch, Bead, Plan, File. "PRs" is an acronym for a different object. "Commits" is accurate for many rows and wrong for the type.

On pluralization: the UX.SE rule "list → plural" supports Stitches/Patches/Beads. SASE's counter-rule, locked in `test_fixed_artifact_labels_are_singular`, is that a kind-tab names the *type of artifact*, matching `@stitch` / `@patch` / `@bead`, while the top-level tab names the *collection* (Artifacts). That two-level grammar is coherent:

- Top-level: Agents, Artifacts, Services (where you are)
- Kind-tabs: Stitch, Patch, Bead, Plan, File (what kind of thing you are looking at)
- Agents views: Inbox, Archive (which *lens*, not which kind)

Prose already pluralizes when it means the collection ("the Beads pane", "No stitches match"). Chrome stays singular. That split is why copy-mode tables in `docs/ace.md` still say Stitches/Beads/Plans/Files while the strip says Stitch/Bead/Plan/File.

### Cost of doing it anyway

A display-only rename is not a one-dict change.

- **Labels** live in `_artifact_tab_descriptors.py`, `patch_onboarding.py`, command-palette `Show Artifacts: {label}`, Help, and the `D` fallback `No {label.lower()}s`.
- **Tests** lock singular forms; many contract tests pass `label="Patch"` into compilers.
- **PNG goldens:** 130 files under `tests/ace/tui/visual/snapshots/png/` match `artifact`; `sase-jd.8` had to regenerate *every* snapshot that showed the strip, including non-Artifacts tests, because the numbers and names sit in the chrome. `tui_screenshot.md` requires `just fix-tui-screenshots`, eyeballing diffs, and a UTC/host-independence check.
- **Docs** enumerate the strip in `docs/ace.md`, `docs/configuration.md`, `docs/query_language.md`, and blog/infographic prompts.
- **Digit keys** themselves would not change if only labels change, which is good; `sase-jd.8` showed that changing order *and* names at once is a `!` breaking change.
- **Provider empty states** double-pluralize if labels are already plural.
- **Research and future providers** need a policy. Auto-pluralizing is how you get "Researchs"; the August commit deleted that.
- This is presentation-only (TUI chrome), so it stays in this repo per the Rust-core boundary. It is still a user-reaching change. A feature flag is the wrong tool: flags are for temporary branches, and `sase_flags.md` says a forever user choice is a config field. A `domain | common` label config would freeze dual vocabulary in. Do not add it.

---

## Alternative approaches (ranked)

### 1. Keep labels; teach in place (recommended)

No strip change. Expand aliases and one Help line. The `D` rail already does the translation. Cost: small. Risk: low. Matches sase-j8 and sase-jd.

### 2. Dual-language chrome, still domain-first

Strip stays `Stitch`. Help, onboarding, and optionally a dim subtitle or the description summary lead with the common word. Example: `Stitch` on the tab, `commits and proposals` in the `D` summary (already true). Do not draw `Stitch / Commits` on the strip; six-plus tabs are already near Apple's "avoid more than six" guidance once Plan and Research are present, and long labels wrap.

### 3. Re-pluralize domain nouns only

`Stitches · Patches · Beads · Plans · Files`. Same objects, collection grammar. This matches UX.SE list-nav advice and the pre-August-13 strip. It fights the singular lock and the Research auto-plural trap. Reasonable if someone wants to reopen *only* grammar, with a written decision that the August 13 commit is superseded. Still not Commits/PRs/Bugs.

### 4. Common-word strip (the proposal)

`Commits · PRs · Bugs · Plans · Files`. Reject. Semantic lies, glossary split, rollback of two epics, name collisions on Bugs.

### 5. User-selectable vocabulary

`ace.artifacts.label_style: domain | common`. Reject. Two names for one product; screenshots, docs, and agent instructions cannot follow a per-user toggle; flags/config-for-taste is exactly what `sase_flags.md` tells you not to do for permanent choices.

---

## Adjusted requirements

Call-outs relative to the original request:

1. **Do not replace Stitch, Patch, or Bead** with Commits, PRs, or Bugs. The author's own doubt about dropping those names is correct; make that the requirement.
2. **Treat pluralization as a separate, optional follow-up**, defaulting to keep singular. If reopened, pluralize the *domain* nouns, not GitHub nouns, and drop the "must not end in s" assertion deliberately.
3. **Do not revive a Bugs inventory.** External issues stay on beads. Palette alias `bugs` may keep routing to Beads.
4. **Do not flag this.** Display vocabulary is not a beta. If Plan should read Plans for one project, that is already a provider `label`.
5. **Keep ids, keymaps, CLI, refs, and glossary stable** regardless of any future chrome tweak. `LEGACY_ARTIFACTS_SUBTABS` already maps the old ids.
6. **If any label changes, budget PNG goldens and empty-state pluralization** as first-class work, not cleanup. `sase-jd.8` is the template.
7. **Cover provider panes in the policy.** The request omitted Agent (retired) and Research (plugin). A rule that only mentions Plan/File will drift the first time a third provider appears.
8. **Prefer aliases and the `D` rail over renaming** as the learnability fix. That is the approach the product is already using.

---

## Implementation sketch (only if doing the recommended work)

Presentation-only, this repo:

- Command palette: in `_iter_artifacts_subtab_commands`, add aliases `commits` for `stitches` and `issues` (and keep `bugs` via the existing legacy map) for `beads`. `prs` already exists for `patches`.
- Help / `patch_onboarding.py`: one short dual-language sentence per pane, reusing the `D` summaries rather than inventing a second glossary.
- No change to `_EXPECTED_FIXED_LABELS`, no golden churn, no flag.

If Plan-as-Plans is wanted later: set `label: Plans` on the builtin plan spec, and change provider empty-state construction so it does not append `s` onto an already-plural label.

---

## Why this recommendation

SASE spent an epic renaming the CLI and the pane to Stitch, another epic deleting Bugs and renaming PRs to Patches, and a follow-up locking singular kind-tabs. Those were not leftover Graphite-era names; they were corrections so the strip, the CLI, and the artifact-ref language named the same objects.

The proposed strip puts GitHub's words on SASE's objects. Commits ≈ stitches-with-SHAs, PRs ⊂ patches, Bugs ⊂ beads. Subset names as tab titles hide the rest of the set. The teaching problem is real for a first hour; the `D` rail, onboarding, and palette aliases already solve it without making the tenth hour fight the first.

Keep Stitch, Patch, Bead, Plan, File. Teach them. Do not rename them back.

---

## Sources

### SASE (primary)

- Glossary: `glossary:stitch`, `glossary:patch`, `glossary:artifact`, `glossary:artifact-reference`, `glossary:nav-section` (via `sase memory read`).
- `src/sase/ace/tui/_artifact_tab_descriptors.py` — display labels.
- `src/sase/ace/tui/_artifact_tab_model.py` — `LEGACY_ARTIFACTS_SUBTABS`, pane ids, `artifacts_agent_pane_retired`.
- `src/sase/ace/tui/_artifact_tab_descriptions.py` — built-in `D` copy.
- `src/sase/ace/tui/_artifact_tab_contract_adapters.py` — stitches `target_prefix="commit"`.
- `src/sase/ace/tui/widgets/patch_onboarding.py` — Help labels and descriptions.
- `src/sase/ace/tui/commands/catalog.py` — palette alias `prs`.
- `tests/ace/tui/test_artifact_tab_labels.py` — singular lock.
- `src/sase/default_config.yml` — `ace.artifacts.description_mode`, stitches default query.
- `docs/change_spec.md`, `docs/beads.md`, `docs/ace.md`, `docs/artifacts_pane_contract.md`.
- `plan:202608/external_artifact_ingestion.md`, `plan:202608/retire_bugs_rename_prs_to_patches.md`.
- Commits: `c69d16378c`, `9c46891c5e`, `2f85bf025b`, `b5786b57f2`, `bd6167875c`.
- Memory: `sase_artifacts.md`, `sase_beads.md`, `sase_flags.md`, `tui_screenshot.md`.

### External (secondary, for heuristics and peer vocabulary)

- Nielsen Norman Group, [Match Between the System and the Real World](https://www.nngroup.com/articles/match-system-real-world/) (heuristic 2).
- Nielsen Norman Group, [Tabs, Used Right](https://www.nngroup.com/articles/tabs-used-right/) (information scent on tab labels).
- Nielsen Norman Group, [10 Usability Heuristics Applied to Complex Applications](https://www.nngroup.com/articles/usability-heuristics-complex-applications/) (false real-world mappings stay expensive).
- Apple HIG, [Tab views](https://developer.apple.com/design/human-interface-guidelines/tab-views) (short noun labels; avoid more than six tabs).
- UX Stack Exchange, [Plural or Singular Navigational Menu Options?](https://ux.stackexchange.com/questions/110325/plural-or-singular-navigational-menu-options) (list destinations → plural).
- Gerrit, [Changes](https://gerrit.wikimedia.org/r/Documentation/intro-gerrit-walkthrough-github.html) and [Patch Sets](https://gerrit.wikimedia.org/r/Documentation/concept-patch-sets.html) (change ≠ GitHub PR; patch set ≈ iteration of a commit).
- Graphite, [Stacked diffs](https://graphite.com/guides/stacked-diffs) (their unit of review *is* a GitHub PR; SASE's is not).
