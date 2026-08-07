# Renaming `ChangeSpec`: Research and Recommendations

Date: 2026-08-07

## Executive Recommendation

Rename **ChangeSpec** to **Change**.

`Change` is shorter, more natural, and more accurate. A ChangeSpec is not mainly a
specification: it is a durable record of a PR-sized change as that change moves from
local work through review, submission, archival, or reversion. Gerrit already uses
*change* for almost exactly this abstraction, while Jujutsu uses it for a logical unit
that survives revisions to its concrete commit. GitHub and GitLab also describe pull
and merge requests as containers for proposed code changes. The word is generic, but
that is an acceptable price for a foundational domain noun—and preferable to inventing
a metaphor that every new user must learn.

It fits SASE's language well:

- “Create a Change for this work.”
- “This Change depends on another Change.”
- “Show active Changes.”
- “Attach this bead to the Change.”
- “Mail, submit, archive, restore, or revert the Change.”
- `sase change current`, `sase change search`, and `sase change ref add`

It also preserves **ACE** with a better expansion: **Agentic Change Explorer**.

If a more distinctive, Beads-like object name is more important than immediate
semantic clarity, the best alternative is **Patch**. If the goal is specifically to
establish a family of tactile craft metaphors, consider **Stitch**—but recognize that it
would require more explanation.

## What the Name Must Represent

The current [ChangeSpec documentation](https://sase.sh/change_spec/) defines a
ChangeSpec as one structured record for a PR. Inspection of the current model shows
that the concept is slightly broader than “PR”:

- It exists before a provider PR is created (`WIP`).
- It persists across `Draft`, `Ready`, `Mailed`, and `Submitted` states.
- It can end as `Archived` or `Reverted`.
- It has an identity independent of any one commit, branch, diff, or provider URL.
- It records description, parent dependency, issue reference, commits, file deltas,
  hooks, comments, mentor runs, artifact references, and timestamps.
- It participates in dependency graphs and can be linked from plan beads.

The target concept is therefore:

> A durable, provider-neutral record of one reviewable, PR-sized unit of code change
> across its full development and review lifecycle.

This definition rules out names that denote only one representation (`Diff`, `Commit`,
`Branch`), one provider object (`Pull Request`, `Merge Request`), or one temporal phase
(`Proposal`, `Submission`).

The current name has two problems:

1. **It is heavier than the thing.** “ChangeSpec” sounds like a formal design or
   requirements specification, while the object is an evolving operational record.
2. **It does not read naturally as a common noun.** “Three ChangeSpecs” is intelligible
   but product-internal; “three changes” or “three patches” is immediate English.

The rename is mechanically substantial—there are roughly 15,700 case-insensitive
`changespec` matches in 1,300 tracked files in the current checkout—so the replacement
should be good enough to remain permanent. That cost does not favor a longer,
code-search-friendly name by itself, but it does argue against novelty for novelty's
sake.

## What Is Worth Borrowing From Beads

The inspected Beads README describes the product precisely as a graph issue tracker,
but freely uses *bead* as the count noun in commands and diagrams (“new bead”). It does
not appear to depend on a formal naming etymology. The useful lesson is how the name
behaves:

- **Concrete:** a bead is an object, not an abstract process.
- **Countable:** one bead, many beads.
- **Short and pronounceable:** easy in speech, UI labels, IDs, and documentation.
- **Composable:** beads can be linked, grouped, and arranged, echoing a dependency
  graph without overexplaining it.
- **Friendly but disciplined:** the memorable noun does not prevent the product from
  using the precise word *issue* when precision matters.

The lesson is not that every neighboring SASE concept needs to come from jewelry. It is
that a core noun should survive ordinary sentences and support a light metaphorical
halo. `Change` passes the grammar test with less personality; `Patch` and `Stitch` pass
with progressively more personality and progressively more semantic cost.

There is also a useful relationship to preserve. A **bead** represents work that needs
doing; a **Change** represents the code-and-review unit that gets landed. They are not
synonyms, and sentences such as “attach this bead to the Change” keep that distinction
clear.

## Naming Criteria

I evaluated candidates against six criteria, in descending order of importance.

1. **Semantic coverage:** Does the name cover the whole object, not just its diff,
   branch, remote PR, or review phase?
2. **Lifecycle durability:** Does it remain natural in WIP, submitted, archived, and
   reverted states?
3. **Everyday grammar:** Does it work as a singular noun, plural noun, modifier, CLI
   namespace, and code identifier?
4. **Conceptual separation:** Can users distinguish it from beads, commits, branches,
   diffs, reviews, deltas, and PRs?
5. **Provider neutrality:** Does it work for GitHub, GitLab, Gerrit, Mercurial, and local
   Git workflows?
6. **Character:** Is it memorable enough to sit beside Beads without feeling
   bureaucratic?

The rubric intentionally favors familiarity. Microsoft's naming guidance recommends
[readability over brevity](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/general-naming-conventions),
and Google's developer-writing guidance recommends familiar, unambiguous terms and
[a single word when it conveys the same idea as a phrase](https://developers.google.com/style/translation).
A short obscure word is not actually a shorter user experience if its meaning needs a
paragraph.

## Industry Terminology and What It Teaches

### `Change` has the closest existing semantics

[Gerrit](https://gerrit-review.googlesource.com/Documentation/concept-changes.html)
defines a *change* as the stable unit under review. Multiple concrete commits can share
its Change-Id and become successive patch sets; the change retains owner, project,
target branch, comments, votes, and submission behavior. This is the closest precedent
to SASE's durable record.

[Jujutsu](https://docs.jj-vcs.dev/latest/glossary/) makes a related distinction: a
*change* is a commit as it evolves over time, while a commit is one concrete snapshot.
The exact data model differs, but the conceptual boundary is valuable. A SASE Change is
also the stable identity around evolving concrete work.

GitHub says pull requests let users
[propose, review, and merge code changes](https://docs.github.com/en/pull-requests/get-started/about-pull-requests),
and GitLab says merge requests provide a central place to
[review, discuss, and track code changes](https://docs.gitlab.com/user/project/merge_requests/).
Those descriptions support *change* as the provider-neutral concept beneath both PRs
and MRs.

The disadvantage is genericness. “Change” already means an unstaged file modification,
an event, and the act of mutating something. Code search for `change` will be noisy, and
`sase change` can initially read as an imperative verb. Capitalizing the domain term in
prose and consistently using compounds such as `ChangeStatus`, `current_change`, and
“Change record” where disambiguation is necessary should contain the problem. A plural
CLI namespace (`sase changes`) is also available if command parsing in usability tests
feels too verb-like, though the singular matches the current `sase changespec` shape.

### `Patch` is the strongest concrete metaphor

`Patch` is short, tactile, and native to software. Git's
[`format-patch`](https://git-scm.com/docs/git-format-patch) format carries metadata,
message text, and a diff, and supports rerolled patch series. The
[Patchwork](https://patchwork.readthedocs.io/) tracker proves that patches can be
managed as workflow objects with review states, comments, archives, and CI results.
Outside software, a patch is a small piece used to modify or mend something. This is a
very good Beads-style dual meaning.

The semantic mismatch is that a patch usually denotes the change payload, not its
durable lifecycle record. A PR may contain multiple commits—and in email workflows,
multiple patches—so “this Patch contains six patches” can become unavoidable. *Patch*
also leans toward fixes and small corrective work even though SASE Changes can deliver
features or broad refactors. NIST's software definition, for example, centers on a
[component installed to modify or repair another component](https://csrc.nist.gov/glossary/term/patch).

`Patch` is nevertheless a strong second choice if memorability and the Beads analogy
matter more than strict model precision.

### `Revision` is proven in code review but overloaded in version control

[Phabricator Differential](https://secure.phabricator.com/book/phabricator/article/differential/)
calls its PR-like unit a *Differential Revision*. A revision holds the review
conversation while authors update its underlying diff, and accepted revisions can be
landed. This demonstrates that the word can successfully name a durable review unit.

The collision is serious, however. Jujutsu explicitly uses *revision* as a synonym for
commit, and Mercurial calls an atomic changeset a
[revision of the whole project](https://wiki.mercurial-scm.org/UnderstandingMercurial).
SASE's object can contain multiple commits and revisions, so the word would routinely
operate at two levels. It is also no shorter in speech than ChangeSpec by much.

### `Changeset`, `Changelist`, `Diff`, and `Stack` name the wrong layer

- **Changeset** is an atomic repository revision in Mercurial. The JavaScript
  [Changesets](https://changesets.dev/) project uses it for release-versioning intent.
  Neither meaning is SASE's review record.
- **Changelist** is established Perforce terminology for a collection of file
  revisions and operations. It is accurate in a narrow sense but long, VCS-specific,
  and strongly associated with `CL`, which SASE is already retiring as a legacy field.
- **Diff** names the computed difference between versions. A Change has a diff; it is
  not a diff.
- **Stack** names a collection of dependent PRs. Graphite defines a stack as
  [a sequence of pull requests](https://graphite.com/docs/cli-quick-start), so it is a
  useful name above the Change level, not at it.

These terms should not be finalists.

## Candidate Analysis

### 1. `Change`

**Best overall.** It is the only candidate with near-exact industry precedent and no
lifecycle phase problem.

Strengths:

- Six letters, one syllable, regular plural.
- Provider-neutral and representation-neutral.
- Natural before, during, and after review.
- Cleanly separates the durable identity from commits and diffs.
- Preserves ACE as **Agentic Change Explorer**.
- Improves the Beads relationship: a bead can motivate or plan a Change.

Weaknesses:

- Very generic in prose, code search, and identifiers.
- `sase change` can momentarily look like a verb.
- Requires disciplined capitalization or compounds in ambiguous documentation.

Suggested definition:

> A **Change** is SASE's durable record for one PR-sized unit of work, from WIP through
> review and landing.

### 2. `Patch`

**Best personality-first option.** It is the most natural sibling to *bead*: a small,
concrete piece that contributes to or repairs a larger whole, with an existing software
meaning.

Strengths:

- Five letters, one syllable, regular plural.
- Excellent CLI and UI noun: `sase patch`, “active Patches,” “Patch graph.”
- Immediately suggests code change and application/landing.
- Makes “Beads and Patches” a memorable product vocabulary.

Weaknesses:

- Conflates the tracked record with its raw diff or email patch.
- Awkward when one PR-sized record contains a series of patches.
- Can make feature work sound like a narrow bug fix.
- ACE would need a new expansion or would cease to match the renamed concept.

### 3. `Stitch`

**Best novel metaphor.** A stitch is one small act that joins, repairs, or constructs a
larger fabric. Beads can literally be stitched into fabric, so the craft vocabulary is
coherent without making a Change a container for beads.

Strengths:

- Six letters, one syllable, regular plural.
- Distinctive in SASE code and prose.
- Conveys small, composable, careful integration.
- Supports good visual language: stitches join work into the codebase.

Weaknesses:

- Not established software terminology; every user needs the definition once.
- “Create a Stitch” and “this Stitch was reverted” sound branded rather than natural.
- Suggests the act of joining more than the durable review record.
- Risks making the combined Beads/Stitches vocabulary feel themed rather than precise.

### 4. `Slice`

**Best scope metaphor.** Engineering teams already speak of vertical slices and small,
reviewable slices of work. It conveys that each unit should be independently useful and
bounded.

Strengths:

- Five letters, one syllable, regular plural.
- Fits PR sizing and stacked development.
- More representation-neutral than Patch.
- Distinctive enough for code and UI use.

Weaknesses:

- Describes scope, not review identity or lifecycle.
- Common programming-language term, especially for sequence types.
- “Mail a Slice” and “revert the Slice” are understandable but not idiomatic.

### 5. `Proposal`

**Best process description before landing.** GitHub explicitly describes a pull
request as a proposal to merge code changes, so the concept is immediately teachable.

Strengths:

- Clear, provider-neutral, and familiar.
- Naturally contains discussion, checks, and revisions.
- Distinguishes the unit from its concrete commits and diff.

Weaknesses:

- Eight letters and three syllables; not especially Beads-like.
- WIP work may not yet be a proposal.
- A merged or reverted “Proposal” is semantically stale: it became an actual change.
- “Submitted Proposal” creates needless ambiguity with the `Submitted` lifecycle state.

### 6. `Revision`

**Best precedent after Change.** Phabricator proves the name works for a review object,
but VCS collisions make it a weaker choice for SASE.

Strengths:

- Familiar from established code-review workflows.
- Natural count noun with a clear plural.
- Captures iterative review better than Patch.

Weaknesses:

- Commonly means one commit or repository snapshot.
- A SASE Revision containing several revisions is confusing.
- Eight letters, three syllables, and limited personality.

### 7. `Parcel`

**Best delivery metaphor.** A parcel is both a portion of a larger whole and a bundle
sent for delivery. Those meanings map pleasantly to a bounded set of changes moving
through SASE's `Mailed` and `Submitted` states.

Strengths:

- Six letters, two syllables, regular plural.
- Conveys a payload plus metadata/envelope.
- Provider-neutral and durable across transport.

Weaknesses:

- Requires explanation in a code-review context.
- Strong developer-tool collision with the
  [Parcel web build tool](https://parceljs.org/).
- “Parcel” can imply a collection of PRs rather than one PR-sized unit.

### 8. `Delta`

**Best mathematical shorthand, but a poor SASE migration.** Delta is a familiar symbol
for change and makes a compact, energetic noun.

Strengths:

- Five letters, two syllables, regular plural.
- Naturally means a difference or change.
- Strong visual identity.

Weaknesses:

- Names the content difference, not the lifecycle record.
- SASE already has a `DELTAS` section for per-file computed deltas; renaming the parent
  object to Delta would create “a Delta has Deltas.”
- Heavily overloaded across databases, data platforms, mathematics, and software.

## Comparative Matrix

Scores are directional judgments on a five-point scale, not quantitative evidence.

| Candidate | Full lifecycle | Natural grammar | Separation from nearby terms | Immediate clarity | Beads-like character | SASE-specific fit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Change** | 5 | 5 | 3 | 5 | 3 | 5 |
| **Patch** | 4 | 5 | 3 | 5 | 5 | 4 |
| **Stitch** | 3 | 4 | 5 | 2 | 5 | 3 |
| **Slice** | 3 | 4 | 3 | 3 | 4 | 3 |
| **Proposal** | 2 | 5 | 4 | 5 | 2 | 3 |
| **Revision** | 4 | 5 | 2 | 4 | 2 | 3 |
| **Parcel** | 3 | 4 | 3 | 2 | 4 | 3 |
| **Delta** | 3 | 5 | 1 | 4 | 4 | 1 |

The matrix highlights the actual decision. `Change` maximizes semantic fit and
teachability. `Patch` sacrifices some model precision for character. `Stitch` sacrifices
more immediate clarity for distinctiveness. The lower candidates do not offer a
compensating advantage large enough to justify their weaknesses.

## Recommended Terminology If `Change` Wins

Use a very small vocabulary and let the familiar word do the work:

| Surface | Recommended form |
| --- | --- |
| Domain type | `Change` |
| Plural | `Changes` |
| One-line definition | “A durable record for one PR-sized unit of work.” |
| CLI namespace | `sase change` (test `sase changes` if the verb reading bothers users) |
| Python/Rust type | `Change` |
| Common identifiers | `change_name`, `current_change`, `find_all_changes` |
| Status type | `ChangeStatus` |
| Dependency term | parent Change / child Change |
| ACE | Agentic Change Explorer |
| Relationship to Beads | “Beads track work; Changes track what lands.” |

Continue calling the provider object a **PR** or **merge request**, the code difference a
**diff**, the VCS snapshots **commits**, and the planning/issues objects **beads**. The
clean separation is:

> A bead describes work. An agent implements it in commits. A Change tracks the
> PR-sized result through review and landing.

Do not expand the replacement back into `ChangeRecord` or `TrackedChange` everywhere.
Those are useful explanatory phrases, but as canonical names they recreate the weight
that prompted this research. Capitalized `Change` is sufficient as the product-domain
term.

## Sources Consulted

- SASE, [ChangeSpec Format Documentation](https://sase.sh/change_spec/), plus the local
  model, CLI documentation, glossary, and tracked-code usage.
- Beads, [project repository](https://github.com/steveyegge/beads) and
  [documentation](https://beads.gascity.com/); repository contents were inspected via
  an audited local checkout.
- Gerrit, [Changes](https://gerrit-review.googlesource.com/Documentation/concept-changes.html).
- Jujutsu, [Glossary](https://docs.jj-vcs.dev/latest/glossary/).
- GitHub, [About pull requests](https://docs.github.com/en/pull-requests/get-started/about-pull-requests).
- GitLab, [Merge requests](https://docs.gitlab.com/user/project/merge_requests/).
- Phabricator, [Differential User Guide](https://secure.phabricator.com/book/phabricator/article/differential/).
- Git, [`git-format-patch`](https://git-scm.com/docs/git-format-patch).
- Patchwork, [documentation](https://patchwork.readthedocs.io/).
- Mercurial, [Understanding Mercurial](https://wiki.mercurial-scm.org/UnderstandingMercurial).
- Graphite, [CLI quick start and stack definition](https://graphite.com/docs/cli-quick-start).
- Changesets, [project documentation](https://changesets.dev/).
- NIST CSRC, [patch glossary entry](https://csrc.nist.gov/glossary/term/patch).
- Microsoft, [General Naming Conventions](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/general-naming-conventions).
- Google, [Write for a global audience](https://developers.google.com/style/translation).

## Ranked Recommendations

1. **Change** — the best semantic match, strongest industry precedent, most natural
   lifecycle noun, and the only option that preserves ACE cleanly as *Agentic Change
   Explorer*.
2. **Patch** — the best short, concrete, Beads-like alternative; choose it if memorable
   product vocabulary matters more than separating the review record from its payload.
3. **Stitch** — the best original craft metaphor and a coherent companion to Beads, but
   it needs teaching and describes integration better than recordkeeping.
4. **Slice** — a good name for a small reviewable scope, but a weaker name for the
   durable object that carries review state.
5. **Proposal** — immediately understandable before merge, but semantically expires
   once the work lands or is reverted.
6. **Revision** — proven by Phabricator, but too easily confused with a commit or
   repository snapshot.
7. **Parcel** — an appealing bundle-and-delivery metaphor with an adjacent developer
   tool collision and little code-review precedent.
8. **Delta** — compact and evocative, but it describes the difference rather than the
   record and directly collides with SASE's existing `DELTAS` field.
