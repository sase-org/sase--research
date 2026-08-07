---
create_time: 2026-08-07
updated_time: 2026-08-07
status: research
---

# Renaming "ChangeSpec": Finding a Name That Earns Its Place Next to "Bead"

**Research question:** `ChangeSpec` is SASE's record for one PR-sized unit of work. It is a
compound, generic, CamelCase noun in a vocabulary that otherwise favors short, concrete, memorable
words — most notably `bead`. What should it be called instead?

**Sources:** Direct inspection of this repo at commit `4c7c635d2` — the `ChangeSpec` data model
(`src/sase/ace/changespec/models.py`), format spec (`docs/change_spec.md`), bead docs
(`docs/beads.md`), the ACE TUI surface, and a full-repo collision sweep for every candidate word.
Prior art drawn from the design vocabulary of Gerrit, Phabricator, Perforce, Sapling, Jujutsu,
Pijul, Darcs, StGit, Radicle, and Fossil.

## Bottom line

**Rename it to `weld`.**

A weld is the permanent joint where new material is fused into an existing structure. That is
precisely what a merged PR is. The word is exactly the same shape as `bead` — one syllable, four
letters — it has zero occurrences anywhere in this repo, it has no established meaning in software,
it yields a natural verb (`weld it in`) and a natural terminal status (`Welded`), and welds are
*inspected for defects* as a real engineering discipline, which maps onto mentors, hooks, and
review comments without anyone having to explain the metaphor.

The runners-up are `rivet` (equally clean, loses only on syllable count) and `splice` (excellent
join semantics, mild collision with `Array.splice`). The full ranking is in
[§7](#7-ranked-recommendations).

One honest caveat about `weld`, discussed at [§7.1](#71-weld--recommended): in welding jargon, a
"bead" is the deposited metal a weld pass lays down. That overlap is real. I judge it a minor cost —
the common-knowledge meaning of "weld" is simply "joining metal" — but it is the single strongest
argument against the recommendation, so it should be a deliberate choice rather than a surprise.

---

## 1. What the concept actually is

Before naming it, it is worth being precise about what is being named, because the name should
encode the properties that distinguish this thing from a bead.

From `docs/change_spec.md` and `src/sase/ace/changespec/models.py:465`, a ChangeSpec is a structured
block inside a ProjectSpec `.sase` file with these fields:

| Field | Meaning |
| --- | --- |
| `NAME` | Unique identifier, e.g. `refactor_database_layer` |
| `DESCRIPTION` | Title + body |
| `PARENT` | Name of a ChangeSpec that must land first |
| `PR` | Review URL |
| `BUG` | Link out to an issue tracker |
| `STATUS` | Lifecycle position |
| `REFS` | Artifact references |
| `COMMITS` / `DELTAS` | The actual code content and computed file changes |
| `HOOKS` / `COMMENTS` / `MENTORS` | Automation and review state |
| `TIMESTAMPS` | Audit trail of lifecycle transitions |

Its lifecycle is `WIP → Draft → Ready → Mailed → Submitted`, with `Submitted`, `Reverted`, and
`Archived` terminal and moved to `<project>-archive.sase`.

Four properties fall out of this, and they are the ones the name has to carry:

1. **It contains code.** `COMMITS` and `DELTAS` mean this is not a description of intent — it is
   the change itself, with its diff attached. This is the sharpest difference from a bead.
2. **It gets reviewed.** `MENTORS`, `COMMENTS`, and the `Ready → Mailed` transition mean it is
   subject to inspection before it is accepted.
3. **It lands permanently.** `Submitted` is terminal and means "merged into the codebase." A bead
   closes; a change *joins*.
4. **It stacks.** `PARENT` is a ChangeSpec name, not a VCS ref (`docs/change_spec.md:121`), so
   these form dependency chains — SASE's stacked-PR primitive.

Note also that `BUG` already links a change to an issue. So the bead↔change relationship is
*reference*, not containment. The two names must read as peers, not as parent and child.

## 2. Why "bead" works

`bead` is the benchmark, so the useful move is to extract *why* it succeeds and turn that into a
rubric rather than just gesturing at "it's short and nice."

- **One syllable, four letters.** Cheap to say, cheap to type, cheap to read in a dense TUI row.
- **A concrete physical object.** You can picture it. Abstract nouns (`Spec`, `Item`, `Unit`,
  `Entity`) cannot be pictured and therefore cannot be remembered.
- **It implies smallness.** A bead is inherently minor — which is exactly the claim "lightweight
  issue tracker" wants to make. The name does argumentative work for free.
- **It implies composition.** Beads string together. That pre-loads the dependency-graph idea
  before anyone reads the docs.
- **It was unclaimed.** No prior software meaning, so `bead` in a sentence about SASE
  unambiguously means SASE's thing.
- **It compounds cleanly.** "bead store", "task bead", "phase bead", `sase bead list`. The word
  survives being used as a modifier.
- **It is slightly whimsical.** This is underrated. A distinctive name is a branding asset;
  `ChangeSpec` is not memorable enough to be repeated by anyone who doesn't have to.

`ChangeSpec` fails on nearly all seven: three syllables, two morphemes, abstract, no implication of
size or composition, and `Spec` is a suffix that means almost nothing (a spec of what? specified by
whom?). It reads like an internal class name that escaped into the product, which is what it is.

## 3. Prior art: what everyone else calls this

Worth knowing what's taken and what those choices cost their owners.

| System | Term | Note |
| --- | --- | --- |
| Gerrit | **Change** (with patchsets) | Accurate, but so generic that "the change" is ambiguous in every sentence containing a change |
| Phabricator | **Revision** (`D123`), **Diff** | Two terms for one concept, a known source of confusion |
| Perforce / Google | **CL** (changelist) | An abbreviation, not a metaphor; strong internal-jargon flavor |
| Meta / Sapling | **Diff**, **stack** | Overloads the word for "textual difference" |
| Jujutsu | **change** (change ID vs. commit ID) | Distinguishes stable identity from content — conceptually close to SASE's `NAME` vs. `COMMITS` |
| Pijul | **change** | First-class, commutative changes |
| Darcs, StGit, quilt, Mercurial MQ | **patch** | The established name for a *stackable* unit of change |
| Radicle | **patch** | Same |
| Fossil | **check-in** | Compound, not adopted elsewhere |
| GitHub / GitLab | **PR** / **MR** | Abbreviations tied to a specific hosting model |

Two observations. First, **the industry has no good short concrete noun here** — it is all generic
words (`change`, `revision`), abbreviations (`CL`, `PR`), or `patch`. That is an opportunity: the
naming space for a distinctive word is genuinely open, in a way it was not for issue trackers.
Second, **`patch` is the only real incumbent**, which makes it the safe choice and the boring one.

## 4. SASE-specific constraints

### 4.1 Vocabulary already in use

SASE has an unusually dense vocabulary that a new name must not disturb: `bead`, `agent`, `clan`,
`family`, `hood`, `tribe`, `lane`, `xprompt`, `artifact`, `mentor`, `hook`, `gate`, `epic`,
`phase`, `plan`, `workspace`, `project`, `repo`, `delta`, `chop`, `snooze`, ACE, AXE.

Note the existing metaphor family: clans, families, hoods, tribes, lanes are all *social*
groupings, and they apply to agents. Beads are the SDD/issue layer. So a change-unit name is free
to open a third register — it does not have to rhyme with either.

### 4.2 Collision sweep

Every candidate was grepped case-insensitively across `src/` and `docs/`:

| Clean (0 hits) | Contested | Effectively taken |
| --- | --- | --- |
| `weld`, `rivet`, `brick`, `stitch`, `knot`, `charm`, `graft`, `scion`, `spur`, `slab`, `ply`, `cog`, `chit`, `parcel`, `pallet`, `prong`, `clasp`, `braid`, `stint`, `lap`, `forge`, `tack`, `fuse`, `bond`, `mesh`, `course` | `notch` (1), `wedge` (1), `facet` (3), `joint` (3), `rung` (9), `strand` (10), `tile` (13), `splice` (16), `slice` (19) | `seam` (23), `leg` (34), `shard` (59), `drop` (144), `batch` (147), `patch` (164), `span` (347), `link` (361), `stack` (412) |

Three of these deserve specific comment because they are otherwise attractive:

- **`rung`** is already SASE vocabulary. `src/sase/plan_show/resolve.py` is built around a
  "five-rung ladder," and `_folding_clans.py` uses "clan rung." Reusing it would be a genuine
  conflict, which is a shame — it has the best stacking imagery of any candidate.
- **`seam`** is used throughout as an *architectural* term ("compatibility seam", "the lone pure
  seam"). Taken.
- **`wedge`** appears only as `wedged` — meaning *stuck* ("a wedged lifecycle lock", "a corrupt
  file never wedges future launches"). The connotation in this codebase is actively negative.

### 4.3 Rename surface area

For cost-weighting the decision: 3,741 textual references, 237 files whose *names* contain
`changespec`/`change_spec`, a 19-file `src/sase/ace/changespec/` package, ~18 TUI modules, the
`sase changespec` CLI (`add`/`list`/`rm`/`search`/`migrate-extension`), and the ACE "PRs" tab.

**The on-disk format is unaffected.** The `.sase` block format uses `NAME:`, `STATUS:`, `PARENT:`
and so on — the literal string `ChangeSpec` never appears in stored data. This is a code-and-docs
rename, not a data migration, which materially lowers the risk of doing it.

## 5. Rubric

| # | Criterion | Weight |
| --- | --- | --- |
| C1 | **Semantic fit** — evokes a reviewable unit of change that permanently joins a codebase | 25 |
| C2 | **Distinct from `bead`** — a newcomer could never mix up which is which | 15 |
| C3 | **Namespace clean** — unclaimed in this repo and in software generally | 15 |
| C4 | **Shape** — syllables, length, CLI and TUI ergonomics | 15 |
| C5 | **Stacking fit** — supports the `PARENT` chain | 10 |
| C6 | **Inflection** — yields a natural verb and past participle for the terminal status | 10 |
| C7 | **Connotation safety** — no strong negative or misleading second meaning | 10 |

C2 carries real weight because confusing the two core nouns of the system is the worst available
failure mode — worse than a slightly awkward word.

## 6. Scores

| Candidate | C1 | C2 | C3 | C4 | C5 | C6 | C7 | **Total** |
| --- | --: | --: | --: | --: | --: | --: | --: | --: |
| **weld** | 25 | 10 | 15 | 15 | 7 | 10 | 10 | **92** |
| **rivet** | 21 | 15 | 15 | 11 | 8 | 8 | 10 | **88** |
| **splice** | 22 | 15 | 10 | 13 | 8 | 10 | 9 | **87** |
| **graft** | 24 | 14 | 9 | 14 | 7 | 10 | 6 | **84** |
| **stitch** | 23 | 6 | 14 | 13 | 9 | 10 | 9 | **84** |
| **patch** | 25 | 15 | 4 | 14 | 9 | 9 | 7 | **83** |
| **brick** | 19 | 14 | 13 | 14 | 10 | 5 | 4 | **79** |
| **rev** | 20 | 15 | 8 | 15 | 6 | 6 | 8 | **78** |
| **parcel** | 15 | 15 | 15 | 10 | 5 | 6 | 9 | **75** |
| **rung** | 16 | 15 | 5 | 15 | 10 | 3 | 9 | **73** |
| **chit** | 12 | 15 | 15 | 15 | 4 | 4 | 7 | **72** |
| **knot** | 12 | 7 | 14 | 15 | 8 | 7 | 5 | **68** |

---

## 7. Ranked recommendations

### 7.1 `weld` — recommended

**Why it wins.** The semantic fit is the best available and it is not close. A weld is not a
description of a joint, it *is* the joint — the place where new material was fused into the
existing structure and became indistinguishable from it. That is exactly the claim `Submitted`
makes. Three further properties come along free:

- **Review is built into the metaphor.** Weld inspection is a real discipline with real
  techniques. "Inspecting a weld for defects before it bears load" is what mentors, hooks, and
  review comments do. No other candidate gives you the review half of the concept for free.
- **It is bead-shaped.** One syllable, four letters. `sase weld list` sits beside `sase bead list`
  as an obvious peer.
- **It inflects perfectly.** `weld it in` for the action, `Welded` as a terminal status that is
  strictly better English than `Submitted`.

How it reads in situ:

```
sase weld list --status Ready       # the CLI
src/sase/ace/weld/                  # the package
Welds                               # the ACE tab, replacing "PRs"
WIP → Draft → Ready → Mailed → Welded
"this weld's parent hasn't landed yet"
```

**The honest caveat.** In welding jargon, a **bead** is the deposit a weld pass lays down — the
"weld bead." So a reader who knows welding will notice that SASE's two core nouns come from one
trade, and may read a containment relationship ("beads make up a weld") that SASE does not assert:
a weld *references* beads via `BUG`, it does not contain them.

I judge this a minor cost. The common-knowledge meaning of "weld" is "join metal permanently,"
which is the meaning that does the work here; "weld bead" is specialist vocabulary. And the
coincidence is arguably a feature — the two names turn out to belong to a coherent workshop
register rather than an arbitrary one. But it is the one thing that could make you prefer #2, so
decide it deliberately.

**Weakest criterion:** stacking (C5). Welds chain along a seam and multi-pass welding is real, but
the image is less vivid than bricks in a course.

### 7.2 `rivet` — the safest pick

Everything `weld` offers minus the jargon overlap, at the cost of one syllable. A rivet permanently
fastens two pieces that were separate; rivets run in rows along a joint, which handles `PARENT`
chains; and it is completely unclaimed both in this repo and in software at large. `Riveted` works
as a terminal status.

It scores lower than `weld` only because a rivet is a *fastener applied to* the structure rather
than the joint itself, so it evokes attachment more than fusion — slightly weaker for "this change
is now part of the codebase." **Choose this over `weld` if the weld-bead overlap bothers you.**

### 7.3 `splice`

Splicing joins two ropes, two lengths of film, or two strands of DNA into one continuous piece with
no seam — a strong image for merging. Great verb (`splice it in`, `spliced`). The demerits are mild
but real: 16 existing occurrences in this repo, and `Array.splice` is well-known enough in JS that
"splice" carries a faint "insert/remove at index" flavor for many developers. One syllable but six
letters.

### 7.4 `graft`

The best *conceptual* metaphor of the whole set, and the closest runner-up to `weld` on C1. A graft
is new tissue joined to a host that then grows as one — and grafts either **take** or are
**rejected**, which maps onto merge-versus-rejection more elegantly than anything else here.
Botanically precise, and git already has (deprecated) grafts, so the register is familiar.

It ranks fourth on two collisions rather than on merit: git's `.git/info/grafts` is a real if
obscure prior use, and **"graft" means political corruption** in common American English, which is
a genuinely unfortunate second meaning for a word you'd say a hundred times a day.

### 7.5 `stitch`

Excellent semantics — a stitch joins two pieces permanently and is the canonical "small unit of
work." It has the best verb of any candidate (`stitch it in`, `stitched`, and `unstitch` for
revert, which no other candidate handles as well).

It ranks fifth on one specific and serious problem: **beads and stitches are both tiny needlework
units**, so the two core nouns of the system become confusable. "Was the issue the bead or the
stitch?" is a question you do not want newcomers asking. If SASE had no `bead`, `stitch` would be
near the top of this list.

### 7.6 `patch`

The most literal, most instantly-understood option, with genuine precedent for *stacked* changes
specifically (StGit, quilt, Mercurial MQ, Darcs, Radicle). Nobody would need the concept explained.

It ranks sixth because it is both **taken and generic**: 164 existing occurrences in this repo, and
universal usage meaning "a diff file," so `sase patch list` would be permanently ambiguous with
actual patches. It also connotes something small and provisional — a bandaid — which undersells a
reviewed, mentor-checked, stacked unit of work. Safe, unmemorable, and a bit inaccurate.

### 7.7 `brick`

Has the single best stacking image available: bricks are laid in courses, each resting on the one
below, which is `PARENT` made literal. Maximally concrete and completely unclaimed here.

It ranks seventh on connotation, which is disqualifying in practice. **"Bricked" means destroyed**
in every technical context, so it cannot be the terminal status, and "we bricked it" reads as a
catastrophe rather than a success. A metaphor whose past participle inverts its meaning is not
usable for a lifecycle-bearing noun.

### 7.8 Conservative fallback: `rev` / `change` / `CL`

If you'd rather not spend a metaphor here at all, `rev` is the best of the literal options — short,
familiar from Phabricator, and unambiguous about what it denotes. But it is an abbreviation rather
than an image, so it inherits none of `bead`'s memorability, and `rev` is grep-hostile (it matches
inside "revert", "reverse", "review", "revision"). `change` is too generic to say in a sentence.
`CL` carries Google-internal flavor, and this codebase already has a legacy `cl` field
(`models.py:504`) that the rename would collide with rather than clarify.

I'd take any of the top five over these — but if the priority is zero learning curve for outside
contributors, `rev` is the one to pick.

### 7.9 Considered and rejected

| Candidate | Reason |
| --- | --- |
| `rung` | Already SASE vocabulary — `plan_show`'s five-rung ladder, clan rungs. Great stacking image, unavailable. |
| `seam`, `slice`, `stack`, `span`, `link`, `drop`, `batch`, `shard` | All in active use in this repo (19–412 hits). |
| `wedge` | Used only as `wedged` = stuck. Actively negative connotation here. |
| `knot` | String-family confusion with `bead`, plus "knotty" and "tangled" connotations. |
| `slab` | Connotes heavy and monolithic — the opposite of the lightweight claim. |
| `spur` | A railway spur branches *off* the main line; a change merges *into* it. Semantics inverted. |
| `scion` | Precise (the grafted-on piece) but obscure and pronunciation-unstable. |
| `cog` | "A cog in the machine" is diminishing, and it doesn't evoke change at all. |
| `forge` | Unclaimed here, but `forge` means "git hosting platform" in the Forgejo/Radicle world. |
| `chit`, `parcel`, `pallet` | Clean namespaces and fine shapes, but they evoke paperwork and delivery — nothing about code, review, or permanence. |
| `charm`, `clasp`, `strand`, `braid` | Jewelry/string family — same confusability problem as `stitch`, without its semantic strength. |

## 8. If you proceed

- **The data format doesn't move.** `.sase` blocks use `NAME:`/`STATUS:`/`PARENT:`; the literal
  `ChangeSpec` never appears in stored data. Code and docs only.
- **Rename the ACE tab too.** The tab is currently labeled "PRs" while the docs say "ChangeSpec" —
  two names for one thing, the Phabricator mistake. A single word fixes both at once.
- **Consider renaming the terminal status.** `Submitted` is Perforce-flavored and vague. `Welded`
  (or `Riveted`, `Spliced`) states what actually happened and reinforces the metaphor at the exact
  moment it matters.
- **Sequence it as: docs → public CLI → internal modules.** The 237 filename-level renames are
  mechanical; the judgment calls are all in the ~40 doc and help-text sites where the word carries
  conceptual weight.
- **`sase changespec migrate-extension` already exists** as precedent for a user-facing rename
  path, if a CLI alias period is wanted.
