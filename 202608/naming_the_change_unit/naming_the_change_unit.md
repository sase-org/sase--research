---
create_time: 2026-08-07
updated_time: 2026-08-07
status: research
---

# Naming the Change Unit: What Should Replace "ChangeSpec"

**Question.** `ChangeSpec` is SASE's record for one PR-sized unit of work. `bead` — the
name of the peer concept for issues — is short, concrete, and memorable. What should the
change unit be called instead?

**Inputs.** Two independent prior reports, preserved alongside this one:

- [`naming_the_change_unit__a.md`](naming_the_change_unit__a.md) — recommends **`Change`**,
  on a rubric that explicitly weights familiarity and industry precedent.
- [`naming_the_change_unit__b.md`](naming_the_change_unit__b.md) — recommends **`weld`**,
  on a weighted rubric that prioritizes metaphor fit and shape-match with `bead`.

Both are worth reading. This report verifies their factual claims against the repo at
`8be11ae29`, resolves the places where they disagree, corrects three material errors, and
adds two criteria neither applied.

---

## Bottom line

**Rename it to `rivet`.**

`rivet` is the only candidate that satisfies every constraint that survives verification.
It is unused anywhere in the repo (0 occurrences in 6,588 tracked files), it names a
physical *object* rather than an event — the same grammatical category as `bead`, which
turns out to matter more than either report noticed (§3) — it stays truthful across the
entire lifecycle including `WIP` and `Reverted` (§4), rivets run in rows along a joint so
the `PARENT` chain reads naturally, `Riveted` is a better terminal status than
`Submitted`, and it carries none of the jargon overlap that undermines `weld`.

Report B ranked `rivet` second and called it "the safest pick." I am promoting it to
first because B's #1 was produced by a rubric that assumed its own answer (§2.1), and
because two verified facts — the lifecycle contradiction and the object/event
distinction — cut against `weld` specifically.

**If you would rather spend no metaphor budget at all, take `Change`** (Report A's pick)
and accept a real, quantified collision tax inside SASE's own codebase (§4.3). It is the
better choice if your priority is zero learning curve for outside contributors. It is the
weaker choice against the brief you actually posed, which asked for a peer to `bead`.

Ranked list in [§7](#7-ranked-recommendations).

---

## 1. What is being named

Verified against `src/sase/ace/changespec/models.py` and `docs/change_spec.md`. Both
reports describe the model accurately; this is the merged picture.

A ChangeSpec is a structured block inside a ProjectSpec `.sase` file:

| Field | Meaning |
| --- | --- |
| `NAME` | Unique identifier, e.g. `refactor_database_layer` |
| `DESCRIPTION` | Title + body |
| `PARENT` | Name of a ChangeSpec that must land first — a name, not a VCS ref |
| `PR` | Review URL (with a legacy `cl` alias still in the model) |
| `BUG` | Link out to an issue tracker |
| `STATUS` | `WIP → Draft → Ready → Mailed → Submitted`; `Submitted`, `Reverted`, `Archived` terminal |
| `REFS` | Artifact references |
| `COMMITS` / `DELTAS` | The code content and computed per-file changes |
| `HOOKS` / `COMMENTS` / `MENTORS` | Automation and review state |
| `TIMESTAMPS` | Audit trail: `COMMIT`, `STATUS`, `SYNC`, `REWORD`, `REWIND`, `RENAME`, `REBASE` |

Five properties fall out, and the name has to carry all five. The first four are Report
B's; the fifth is new here and is the one that does the most work in the analysis.

1. **It contains code.** `COMMITS`/`DELTAS` mean this is not a description of intent. It
   is the change itself, diff attached. The sharpest difference from a bead.
2. **It gets reviewed.** `MENTORS`, `COMMENTS`, and `Ready → Mailed` mean inspection
   before acceptance.
3. **It lands permanently.** `Submitted` is terminal. A bead *closes*; a change *joins*.
4. **It stacks.** `PARENT` names another ChangeSpec, so these form dependency chains —
   SASE's stacked-PR primitive.
5. **It is a stable identity over mutating content.** The `TIMESTAMPS` vocabulary
   includes `REWIND`, `REBASE`, and `RENAME`. The record survives history rewrites, gets
   re-parented, and can be `Reverted` after landing. This is precisely Gerrit's Change-Id
   and Jujutsu's change-id semantics: the identity is stable while the concrete commits
   underneath it are not.

Note that `BUG` already links a change to an issue. The bead↔change relationship is
**reference, not containment**. The two names must read as peers. Any name that invites a
containment reading is a defect, not a flourish.

**What the current name gets wrong.** `ChangeSpec` is three syllables and two morphemes;
`Spec` implies a formal specification, but the object is an evolving operational record —
it is heavier than the thing it names. It reads like an internal class name that escaped
into the product, which is what it is.

---

## 2. Where the two reports disagree

### 2.1 The rubric problem

The reports reach opposite conclusions because they weight opposite things, and Report B
was explicit about it: its criterion C1, worth 25 of 100 points, is *"evokes a reviewable
unit of change that permanently joins a codebase."*

That criterion is a description of welding. Any word meaning "permanent join" scores 25/25
by construction, and `weld` duly did. The rubric assumed its answer.

A neutral formulation of the same criterion — *"names the durable record across its whole
lifecycle"* — changes the result, because **four of the five active statuses are not
landed states**. `WIP`, `Draft`, `Ready`, and `Mailed` all precede the join; `Reverted`
undoes it. "This weld is in WIP" asserts a fusion that has not happened, and "this weld
was reverted" asserts one that was undone. Report A applied exactly this test to
`Proposal` and demoted it to fifth for being "semantically stale once the work lands."
Report B did not apply the mirror-image test to its own winner.

**The fair counter**, which is worth stating: "pull request" and "merge request" also name
an action that has not happened yet, and nobody finds that confusing. True — but those
names hedge. The noun head is *request*, which is lifecycle-neutral; only the modifier
names the goal. `weld` has no such hedge, and neither do `splice` or `stitch`.

Applying lifecycle-neutrality re-ranks Report B's own shortlist substantially:

| | Names an object that exists before the join | Names the completed join |
| --- | --- | --- |
| Survives `WIP`/`Reverted` | `rivet`, `brick`, `patch`, `graft` (scion) | — |
| Contradicts `WIP`/`Reverted` | — | `weld`, `splice`, `stitch` |

### 2.2 Fact corrections

Three claims did not survive verification.

**Report B undercounts the rename surface by ~4×.** B reports "3,741 textual references"
and "237 files whose names contain `changespec`/`change_spec`," and uses the low number to
argue the rename is cheap. The verified figures are **15,784 case-insensitive occurrences
across 1,316 of 6,588 tracked files**, and **114** tracked filenames. B's 3,741 is the
count of the CamelCase identifier `ChangeSpec` alone (3,730 today); it misses 11,752
lowercase `changespec` occurrences in module paths (`sase.ace.changespec`), the
`sase changespec` CLI, and test IDs. **Report A's figures (~15,700 / ~1,300) are correct.**

**Report B's collision sweep is correct and reproducible.** Independently re-run: `weld` 0,
`rivet` 0, `graft` 0, `brick` 1, `stitch` 0, `chit` 0, `tack` 0, `splice` 16, `rung` 9,
`slice` 19, `seam` 23. B's `patch` figure (164 in `src/` + `docs/`) also reproduces at 168.
B's disqualification of `rung` and `seam` as already-SASE vocabulary is confirmed and
correct — `rung` is `plan_show`'s five-rung ladder, `seam` is a repo-wide architectural
term.

**Report B's on-disk-format claim is correct, and it is the single most decision-relevant
cost fact.** The live ProjectSpec for this project contains zero occurrences of
`changespec`; `.sase` blocks use `NAME:`/`STATUS:`/`PARENT:`. The literal string appears
in stored data only in one golden test fixture (`tests/core_golden/myproj.sase`). **This
is a code-and-docs rename, not a data migration** — which is what makes a 15,800-reference
rename tractable at all.

### 2.3 What Report A got right that B missed entirely

**ACE stands for "Agentic ChangeSpec Explorer."** The acronym behind the flagship command
(`sase ace`) is built on the name being replaced. Report A caught this and used it as a
tiebreaker for `Change` ("Agentic Change Explorer"); Report B missed it, noting only that
the ACE *tab* should be renamed.

Size it honestly: the expansion appears in 5 doc lines, and `ACE` is already used as a
standalone proper noun ("the ACE cockpit," `sase ace`) alongside `AXE`. Re-expanding it —
"Agentic Coding Environment," "Agentic Change Explorer," or simply retiring the expansion
— is cheap. This is a genuine tiebreaker, not a constraint. It should not buy `Change` a
first-place finish on its own.

### 2.4 Where both reports are right and agree

- **The industry has no good short, concrete noun for this.** Verified across Gerrit
  (*change* + patch sets), Phabricator (*revision* `D123` + *diff* — two names for one
  concept, a known confusion), Perforce/Google (*CL*), Meta/Sapling (*diff*, *stack*),
  Jujutsu and Pijul (*change*), Darcs/StGit/quilt/Mercurial MQ/Radicle (*patch*), Fossil
  (*check-in*), GitHub/GitLab (*PR*/*MR*). It is all generic words, abbreviations, or
  `patch`. A web sweep for newer stacked-diff tooling turned up nothing better; the
  standard descriptive phrase remains the unlovely "unit of change." **The naming space
  for a distinctive word is genuinely open.**
- **The ACE tab currently reads "PRs" while the docs say "ChangeSpec"**
  (`src/sase/ace/tui/commands/catalog.py:125`). Two names for one concept — the
  Phabricator mistake. A single good word fixes both at once. Report B's observation,
  confirmed.
- **`Delta` is disqualified**: SASE already has a `DELTAS` field of `DeltaEntry` objects,
  so renaming the parent to `Delta` yields "a Delta has Deltas."

---

## 3. The criterion neither report applied: `bead` names an object

Report B derives a rubric from *why `bead` works* — one syllable, concrete, implies
smallness, implies composition, unclaimed, compounds cleanly, slightly whimsical. That
list is sound but reverse-engineered: the upstream Beads project documents no naming
etymology, and its README uses "issue" more often than "bead." The metaphor is undefended,
which means SASE is free to define the pairing rather than match it.

The structural fact that list misses is grammatical. **`bead` names an object, not an
event.** It encodes no lifecycle at all — a bead in `open` status is not "un-beaded," and a
closed one is not "beaded." The word is a pure noun for a thing that exists throughout.

That is exactly the property that makes it survive a lifecycle it does not describe, and
it is the property the peer noun should share. Sorting the shortlist this way is clarifying:

| Object nouns | Event/result nouns |
| --- | --- |
| `rivet`, `brick`, `patch`, `chit`, `parcel`, `tack`, `plank` | `weld`, `splice`, `stitch`, `graft`, `change` |

Of the object nouns, only `rivet` also carries join semantics, supports the `PARENT`
chain, is unclaimed, and has a usable past participle. `brick` fails on "bricked"
(§5), `patch` fails on collisions (§5), and the rest evoke paperwork rather than code.

This is also the cleanest answer to the containment problem from §1. A weld is *made of*
beads in welding jargon — Report B acknowledges this as its own strongest counterargument
and judges it minor. I judge it worse than B does, not because the jargon is well known,
but because it is the *only* candidate whose second meaning implies the specific wrong
relationship SASE must avoid. Rivets and beads share no trade.

---

## 4. Verified SASE-specific constraints

### 4.1 Existing vocabulary is dense

`bead`, `agent`, `clan`, `family`, `hood`, `tribe`, `lane`, `xprompt`, `artifact`,
`mentor`, `hook`, `gate`, `epic`, `phase`, `plan`, `workspace`, `project`, `repo`,
`delta`, `chop`, `snooze`, ACE, AXE.

Report B's observation is useful: clans, families, hoods, tribes, and lanes form a
*social* register and apply to agents; beads are the SDD/issue layer. A change-unit name is
free to open a third register and does not have to rhyme with either.

### 4.2 The CLI namespace already dispatches verbs — a cost both reports mis-scored

`sase` has 46 top-level subcommands, and several are imperatives that act on ChangeSpecs:
`sase commit`, `sase revert`, `sase restore`, `sase validate`, `sase launch`, `sase run`.
Nouns (`sase bead`, `sase project`, `sase changespec`) and verbs coexist at the same level.

Report A flagged that `sase change` "can momentarily look like a verb" and treated it as a
`Change`-specific weakness. Report B counted verb-ability as a *strength* (criterion C6,
"yields a natural verb"). **Both are half right, and the property is double-edged.** In a
namespace that genuinely dispatches verbs, `sase change`, `sase patch`, `sase weld`,
`sase splice`, `sase graft`, and `sase stitch` all read as imperatives on first encounter.
`sase rivet list` does not, because "rivet" is overwhelmingly a noun in ordinary use.

The inflection B wants is still available — `Riveted` as a terminal status, "rivet it in"
in prose — without the CLI ambiguity.

### 4.3 `Change` is the only finalist that collides with SASE's own code

This is the strongest verified argument against Report A's recommendation, and A did not
quantify it. Existing identifiers in `src/`:

| Identifier | Count | Current meaning |
| --- | ---: | --- |
| `change_set` | 78 | Plugin/dependency update sets |
| `change_type` | 39 | Delta kind — `"A"`, `"M"`, `"D"` |
| `change_url` | 11 | — |
| `change_status` | 10 | **The TUI action that changes a status** |
| `change_ref` | 6 | — |

Plus 1,244 bare `change`/`changes` word occurrences in `src/` and `docs/`.

`change_status` is the sharp edge. `action_change_status` and `action_bulk_change_status`
(`src/sase/ace/tui/actions/status.py:153`, `.../marking.py:102`) already mean *"change the
status of a ChangeSpec."* After the rename, `change_status` reads equally well as "a
Change's status," and `ChangeStatus` would be the new type name for exactly that. This is
resolvable — rename the actions to `set_status` — but it is 150+ identifiers of friction
that no other candidate incurs, on top of a code search for `change` that returns 1,244
unrelated hits.

Gerrit hit the same wall and solved it with machinery: Change-Ids are prefixed with an
uppercase `I` specifically to keep them distinguishable from commit IDs. That is evidence
the genericness is a real cost, not a stylistic quibble.

### 4.4 Rename surface

15,784 occurrences across 1,316 files; 114 tracked filenames; the 19-file
`src/sase/ace/changespec/` package; ~18 TUI modules; the `sase changespec` CLI
(`add`/`list`/`rm`/`search`/`migrate-extension`); the `sase bead --changespec` flag; the
ACE "PRs" tab; and `sase.sh` public docs. The on-disk format does not move (§2.2).

---

## 5. Candidate analysis

Merged from both reports, re-scored against §2.1 (lifecycle-neutrality), §3
(object-vs-event), and §4 (verified collisions).

### `rivet` — recommended

A rivet permanently fastens two pieces that were separate. It is an **object** that exists
before it is set, so it stays truthful in `WIP` and `Draft`; it is set in place at
`Submitted`; and a drilled-out rivet is an ordinary repair, so `Reverted` costs the
metaphor nothing. Rivets run in rows along a joint, which handles `PARENT` chains. Zero
occurrences repo-wide and no established meaning in software. `Riveted` works as a terminal
status. Not read as an imperative in `sase rivet list`.

```
sase rivet list --status Ready       # the CLI
src/sase/ace/rivet/                  # the package
Rivets                               # the ACE tab, replacing "PRs"
WIP → Draft → Ready → Mailed → Riveted
"this rivet's parent hasn't landed yet"
sase bead create --rivet <name>
```

**Costs, honestly.** Two syllables and five letters against `bead`'s one and four — the
one place `weld` genuinely beats it. It evokes *attachment* rather than *fusion*, so it is
a slightly weaker image for "this is now part of the codebase." "Riveting" means
engrossing, a mild and harmless second sense. And it is a coined term with no industry
precedent: every outside contributor learns it once. ACE would need a new expansion.

### `Change` — the strong plain-language alternative

Report A's case is sound and I am not overturning it, only re-ranking it. `Change` has the
closest existing semantics of any word: Gerrit's *change* is the stable review object whose
concrete versions are patch sets, and Jujutsu's *change* is the identity that survives
revision — both are exact matches for §1's fifth property. It is lifecycle-neutral,
provider-neutral, reads naturally in every required sentence, and preserves ACE as *Agentic
Change Explorer*.

Against it: §4.3's 150+ identifier collisions and 1,244 ambiguous word occurrences inside
SASE itself, the imperative reading of `sase change`, and the fact that it declines the
brief — you asked for a name inspired by `bead`, and `Change` is the plainest word
available. It buys safety with character.

Report A's mitigation (capitalize the domain term, use compounds like `ChangeStatus` and
`current_change`) is workable, and `sase changes` is available if the verb reading tests
badly. Take this option if outside-contributor legibility outranks distinctiveness.

### `graft` — best semantic mapping, blocked by a second meaning

The most elegant fit in the whole set. A graft is new tissue joined to a host that grows as
one, and grafts either **take** or are **rejected** — which maps `Submitted` and `Reverted`
better than anything else here. The scion exists before grafting, so it passes the
lifecycle test. Zero repo occurrences.

It ranks below `Change` on two collisions rather than on merit: git has (deprecated)
`.git/info/grafts`, and **"graft" means political corruption in American English**. That
second meaning is genuinely unfortunate for a word you would say a hundred times a day.

### `patch` — safest for outsiders, disqualified by Python

The most instantly understood option, with real precedent for *stacked* changes
specifically (StGit, quilt, Mercurial MQ, Darcs, Radicle), and Patchwork proves patches can
carry review state, comments, and archives as workflow objects. Object noun, lifecycle-
neutral, one syllable. On the merits it is Report A's #2 and deserves to be considered.

It is disqualified by two verified facts, both sharper than either report stated:

- **8,743 word-boundary occurrences repo-wide** (168 in `src/`+`docs/` alone). Report B
  reported 164, scoped to `src/`+`docs/`; the whole-repo number is what matters for a
  global rename.
- **1,306 of 5,647 Python files in `src/` and `tests/` already use `monkeypatch`,
  `mock.patch`, or `@patch(`.** A domain type named `Patch` living next to
  `from unittest.mock import patch` in 23% of the codebase is a permanent papercut, not a
  one-time migration cost.

Semantically it also conflates the record with its payload ("this Patch contains six
patches") and connotes small corrective work — NIST defines a patch as a component
installed to *repair* another — which undersells a reviewed, mentor-checked, stacked unit.

### `weld` — highest ceiling, two structural problems

Report B's case is real and worth restating: no other candidate gives you the review half
of the concept for free, because weld *inspection* is an actual engineering discipline that
maps onto mentors, hooks, and comments without explanation. It is exactly bead-shaped, zero
repo occurrences, and `Welded` is better English than `Submitted`.

It ranks fifth here on two counts, one of which Report B raised against itself:

1. **It names the completed join** (§2.1), so it is false for four of five active statuses
   and for `Reverted`. It is an event noun where `bead` is an object noun (§3).
2. **In welding jargon a "bead" is the deposit a weld pass lays down.** B judges this
   minor. I judge it the worst available failure mode, because it is the only second
   meaning that implies *containment* between SASE's two core nouns — precisely the
   relationship §1 says must not be implied. B's own C2 criterion ("a newcomer could never
   mix up which is which") carries 15 points for exactly this reason, and `weld` should not
   have scored 10/15 on it.

If you love the word, the fix is available: keep the workshop register and take `rivet`,
which is what B's own runner-up analysis recommends.

### Also considered

| Candidate | Verdict |
| --- | --- |
| `splice` | Excellent join image and verb, but an event noun (§3), 16 repo hits, and `Array.splice` gives it a faint "insert at index" flavor. |
| `stitch` | Strong semantics and the best revert verb (`unstitch`), but **beads and stitches are both tiny needlework units** — the confusability failure mode, worse here than for `weld`. Report A ranked it 3rd without weighing this; Report B ranked it 5th and was right to. |
| `brick` | The best stacking image available — courses of bricks are `PARENT` made literal — and effectively unclaimed. **"Bricked" means destroyed** in every technical context, so it cannot be the terminal status. A metaphor whose past participle inverts its meaning is unusable. |
| `rev` | Best of the literal short options, but an abbreviation rather than an image, and grep-hostile (matches inside *revert*, *reverse*, *review*, *revision* — all live SASE vocabulary). |
| `revision` | Proven by Phabricator, but Jujutsu and Mercurial both use it for a single commit, so a SASE Revision containing several revisions is confusing. |
| `slice`, `parcel`, `proposal` | `slice` names scope not identity (19 hits, plus the sequence-type sense); `parcel` collides with the [Parcel](https://parceljs.org/) bundler and evokes delivery, not code; `proposal` expires semantically once the work lands. |
| `changeset`, `changelist`, `diff`, `stack` | All name a different layer — an atomic revision, a Perforce CL, a computed difference, and a *collection* of dependent PRs respectively. |
| `delta` | Disqualified: SASE already has `DELTAS`/`DeltaEntry` (§2.4). |
| `rung`, `seam`, `wedge` | Unavailable. `rung` is `plan_show`'s five-rung ladder; `seam` is a repo-wide architectural term; `wedge` appears only as `wedged` = *stuck*. |
| `chit`, `tack`, `plank`, `bolt`, `plate` | All verified clean (0 hits) and well-shaped, but none evokes code, review, or permanence. Listed for completeness. |

---

## 6. Comparative summary

Directional judgments, not quantitative evidence. "Lifecycle" = truthful in `WIP` through
`Reverted` (§2.1); "Distinct from bead" = no containment or category confusion (§3);
"Namespace" = verified repo and ecosystem collisions (§4.3, §5).

| Candidate | Lifecycle | Distinct from `bead` | Namespace | Stacking | Shape | Clarity to outsiders |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **rivet** | 5 | 5 | 5 | 4 | 4 | 3 |
| **Change** | 5 | 5 | 1 | 3 | 4 | 5 |
| **graft** | 4 | 5 | 3 | 3 | 5 | 3 |
| **patch** | 5 | 5 | 1 | 5 | 5 | 5 |
| **weld** | 2 | 2 | 5 | 3 | 5 | 3 |
| **splice** | 2 | 4 | 3 | 4 | 4 | 3 |
| **stitch** | 2 | 1 | 5 | 4 | 4 | 3 |
| **brick** | 5 | 4 | 5 | 5 | 4 | 2 |

`patch` scores well everywhere except the one column that kills it. `brick` likewise. That
is the shape of this decision: there is no dominant candidate, only candidates with one
disqualifying flaw and one — `rivet` — with none.

---

## 7. Ranked recommendations

1. **`rivet`** — the only candidate with no disqualifying flaw. Object noun like `bead`,
   truthful across the whole lifecycle, zero collisions in 6,588 files, stacks naturally,
   `Riveted` beats `Submitted`, and no shared trade with `bead`. Costs one syllable against
   `weld` and a new ACE expansion. **Recommended.**
2. **`Change`** — take it if outside-contributor legibility outranks distinctiveness.
   Closest industry semantics (Gerrit, Jujutsu), preserves ACE, but it is the only finalist
   that collides with SASE's own vocabulary (150+ `change_*` identifiers, 1,244 bare-word
   uses, `action_change_status`) and it declines the brief you posed.
3. **`graft`** — the most elegant semantics in the set, including the best mapping for
   `Reverted` (grafts take or are rejected). Blocked only by "graft" = corruption in
   American English, plus git's deprecated grafts. Pick it if that second sense does not
   bother you.
4. **`patch`** — the only real incumbent and the one nobody would need explained.
   Disqualified in practice by 8,743 repo occurrences and by `unittest.mock.patch` /
   `monkeypatch` in 23% of the Python files.
5. **`weld`** — the most evocative word here, and it gives you review-inspection for free.
   Costs: it asserts a permanence the object does not have for most of its life, and it
   shares a trade with `bead` in a way that implies containment. Choose it over `rivet`
   only as a deliberate trade of accuracy for vividness.
6. **`splice`** — strong join image and verb, but an event noun with 16 existing hits and a
   JS `Array.splice` shadow.
7. **`stitch`** — excellent semantics and the best revert verb, but needlework-adjacent to
   `bead`, which is the one confusion worth avoiding above all others.
8. **`brick`** — best stacking image available; "bricked" makes it unusable.

Below the line: `rev`, `revision`, `slice`, `parcel`, `proposal`, `delta`, and anything
built from `changeset`/`changelist`.

---

## 8. If you proceed

- **The data format does not move.** `.sase` blocks use `NAME:`/`STATUS:`/`PARENT:`; the
  literal `ChangeSpec` appears in stored data only in `tests/core_golden/myproj.sase`. This
  is a code-and-docs rename. It is the fact that makes 15,784 references tractable.
- **Budget for the real surface**, not Report B's figure: 15,784 occurrences, 1,316 files,
  114 filename-level renames, the `src/sase/ace/changespec/` package, ~18 TUI modules, the
  `sase changespec` CLI, `sase bead --changespec`, and `sase.sh`.
- **Rename the ACE tab in the same change.** It reads "PRs" today
  (`catalog.py:125`) while the docs say "ChangeSpec" — one word fixes both.
- **Rename the terminal status too.** `Submitted` is Perforce-flavored and vague.
  `Riveted` states what happened and earns the metaphor at the moment it matters.
- **Decide ACE's expansion explicitly.** It is "Agentic ChangeSpec Explorer" in 5 doc
  lines today. Either re-expand it (*Agentic Change Explorer* if you pick `Change`,
  *Agentic Coding Environment* otherwise) or retire the expansion and let `ACE`/`AXE` stand
  as proper nouns.
- **Resolve `change_status` first if you pick `Change`.** Rename
  `action_change_status`/`action_bulk_change_status` to `set_status`/`bulk_set_status`
  before the rename, or the ambiguity lands in the same commit that creates it.
- **Sequence as docs → public CLI → internal modules.** The 114 filename renames are
  mechanical; the judgment calls are in the ~40 doc and help-text sites where the word
  carries conceptual weight.
- **`sase changespec migrate-extension` already exists** as precedent for a user-facing
  rename path, if you want a CLI alias period.

---

## Sources

Verified in-repo at `8be11ae29`: `src/sase/ace/changespec/models.py`, `docs/change_spec.md`,
`docs/beads.md`, `src/sase/ace/tui/commands/catalog.py`,
`src/sase/ace/tui/actions/status.py`, `src/sase/plan_show/resolve.py`, `sase --full-help`,
and a whole-repo collision sweep over 6,588 tracked files.

External, via audited checkout or documentation:
[Beads](https://github.com/steveyegge/beads) ·
[Gerrit: Changes](https://gerrit-review.googlesource.com/Documentation/concept-changes.html) ·
[Gerrit: Change-Ids](https://gerrit-review.googlesource.com/Documentation/user-changeid.html) ·
[Jujutsu glossary](https://docs.jj-vcs.dev/latest/glossary/) ·
[GitHub: About pull requests](https://docs.github.com/en/pull-requests/get-started/about-pull-requests) ·
[GitLab: Merge requests](https://docs.gitlab.com/user/project/merge_requests/) ·
[Phabricator Differential](https://secure.phabricator.com/book/phabricator/article/differential/) ·
[git-format-patch](https://git-scm.com/docs/git-format-patch) ·
[Patchwork](https://patchwork.readthedocs.io/) ·
[Understanding Mercurial](https://wiki.mercurial-scm.org/UnderstandingMercurial) ·
[Graphite: Gerrit's approach to code review](https://graphite.com/guides/gerrits-approach-to-code-review) ·
[Changesets](https://changesets.dev/) ·
[NIST: patch](https://csrc.nist.gov/glossary/term/patch) ·
[Microsoft: General Naming Conventions](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/general-naming-conventions) ·
[Google: Write for a global audience](https://developers.google.com/style/translation) ·
[Pragmatic Engineer: Stacked Diffs](https://newsletter.pragmaticengineer.com/p/stacked-diffs)
