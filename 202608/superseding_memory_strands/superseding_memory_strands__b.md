---
create_time: 2026-08-30
updated_time: 2026-08-30
status: research
tags: [memory, memory-webs, decisions, adr, zettelkasten, agent-context, critique]
---

# Should Memory Strands Be Able To Supersede One Another?

**Research question:** A memory web's descriptor is a hub note that points at every one
of its strands, unconditionally. The proposal is to let one strand declare that it
supersedes another, so that (a) reading the new strand renders the superseded one
inline or as a reference, and (b) the superseded strand disappears from the hub roster
and therefore from the Memory Webs section of every generated agent instruction file.
The `/sase_memory_write` skill would be updated to teach agents the capability. Is this
worth building?

**Scope:** Critique only; no behavior changed and no memory file written. Measured
against `sase` at `40cd8ce6e` (workspace `sase_26`, master, clean) on 2026-08-30, with
the linked `sase-core` checkout opened via `sase repo open`, the live memory corpus, and
the live read log (`sase memory log`: 8,989 events, 36 memory paths, 3,959 agents).

**Companions:** `202608/memory_as_source_artifacts/memory_as_source_artifacts.md` (whose
§6 already sets a falsifiable threshold for exactly this question) and
`202608/decisions_web_seed_adrs.md` (which seeded the corpus under discussion).

---

## Bottom line

**Half of this is already built and silently switched off; the other half should not be
built.**

| Sub-proposal | Verdict | Basis |
| --- | --- | --- |
| Render a superseded strand inline or as a reference when reading the superseding one | **Already shipped** — `[[…]]` / `![[…]]` + `link_rendering` landed 4 commits ago (§1) | §1 |
| Make it work in the `decisions` web | **Do it — one line, today** | §2: `decisions` has links silently disabled; a link authored today is a no-op |
| A typed `superseded_by` back-pointer with a status banner on read | **Do it, but as ADR status, not as a link type** (§6, §8) | §6: the prose convention already failed at n=1 |
| Hide superseded strands from the hub roster / agent instructions | **Do not build** | §3, §4, §5 |
| Teach agents the capability via `/sase_memory_write` | **Do it — but the gap is bigger than you think** (§7) | The skill documents *no* link mechanism at all today |

Three findings drive this.

1. **You already built the rendering half.** `link_reference`, `link_rendering`,
   `[[target]]`, `![[target]]`, and the `## Linked References` section landed in commits
   `ae83faa2e`…`40cd8ce6e`. "Render the superseded note either inline or as a reference
   when the new one is read" is a description of shipped behavior.

2. **It does not work in `decisions`, and there is a live defect proving it.**
   `sase/memory/decisions.md` declares `closure: none`, which the new parser maps to
   `link_reference: none`, which suppresses authored links entirely. The
   `![[decisions/single-turn-agents]]` link you added to `gates-never-block.md` earlier
   today (`f0a8fcefa`, "make it use an inline rendering strategy") renders as literal
   text. Verified by audited read in §2.

3. **The hiding half fails on the only real supersession in the corpus, and contradicts
   both sources you cited for it.** The corpus has exactly one supersession event; it is
   a *partial* supersession of one sentence, and the "superseded" record is still
   actively cited by a third record. Hiding it would be wrong. Separately, hub notes
   (Doto) are a *locating* device that the article never describes pruning, and ADR
   practice (Nygard, `adr-tools`) is emphatic that superseded records stay listed with a
   changed status — the status field exists precisely so a reader scanning the directory
   can tell what is still authoritative.

The idea is worth acting on. The action is a one-line frontmatter fix, an ADR `status`
render, and a documentation pass — not a supersession engine.

---

## 1. The rendering half of the proposal already exists

Four commits on the current branch built an authored-link system:

| Commit | Subject |
| --- | --- |
| `ae83faa2e` | feat(memory): add authored link scanner and resolver |
| `7c8117b17` | feat(memory): add `link_reference` and `link_rendering` frontmatter |
| `90e3a385c` | feat(memory): fold authored links into the closure walk |
| `40cd8ce6e` | feat(memory): render Linked References for show and read |

What shipped, read from `src/sase/memory/`:

- **`[[target]]`** is a reference link; **`![[target]]`** is an inline link
  (`links.py:11`, `links.py:37`). Targets resolve to a strand, a flat note, or a web
  descriptor across the whole memory universe (`link_resolve.py`).
- **`link_rendering: reference | inline`** (`notes.py:31`) makes every one of a note's
  or strand's links inline without the `!` prefix. `selector.py:401` computes
  `inline = depth != 0 and (link.inline or strand.link_rendering == "inline")`.
- **Inline links transclude**: an inline same-web target is expanded in place in the
  read output rather than listed (`selector.py:504-514`).
- **Reference links render a `## Linked References` section** with the selector, label,
  and summary of each target, plus an `Unresolved:` line
  (`link_render.py:101-127`), in Markdown, rich, and JSON.
- **Always-loaded targets are auto-demoted to references** — a `type: core` note or a
  web descriptor can never be inlined because it is already in context
  (`selector.py:363-375`), and the listing says so.

That is, feature-for-feature, the "rendered (either 'inline' or as a 'reference') when
the new note is read via the `sase memory show/read` commands" clause of the proposal.
The only thing missing from that clause is the word *supersedes* — the machinery is
relation-agnostic.

**Consequence for the critique.** The proposal should be re-scoped from "build strand
supersession" to "add a semantic on top of links that already work, and decide whether
the hub roster should react to it." Those are very different sizes.

---

## 2. Live defect: authored links are silently disabled in the `decisions` web

`_parse_descriptor_link_reference` (`src/sase/memory/web/frontmatter.py:262-282`) maps
the legacy `closure:` key onto the new axis:

```python
if has_closure:
    ...
    link_reference = "implicit" if resolved_closure == "mentions" else "none"
```

`closure: none` therefore no longer means "do not walk phrase mentions." It now
additionally means **"ignore every authored `[[…]]` link in this web."**
`_resolve_strand_links` short-circuits on it (`selector.py:390`), as does
`strand_link_spans` (`web/closure.py:194`).

Measured effective settings, parsed with the workspace's own code:

| Web | Declares | Effective `link_reference` | Authored links |
| --- | --- | --- | --- |
| `decisions` | `closure: none` | `none` | **off** |
| `glossary` | `closure: mentions` | `implicit` | on (+ phrase closure) |
| `task_types` | *(nothing)* | `explicit` (the default) | on |

So the default is permissive and the one web that declares the legacy key is the one web
where links are dead — and it is the web this proposal is about.

**This is not theoretical.** `sase/memory/decisions/gates-never-block.md` contains the
corpus's only authored link, added today across two commits (`31b7cba99`, then
`f0a8fcefa` — *"Add `!` prefix to decision file reference to make it use an inline
rendering strategy"*). An audited read of that strand returns:

```
**Reopens when.** A hosting platform ships a true suspend/resume primitive that
preserves workspace claims and provider budget across a pause, per
![[decisions/single-turn-agents]] — no such primitive exists today, ...
```

Literal `![[…]]` in the middle of a sentence, no transclusion, no Linked References
section. An agent reading this gets a syntax artifact instead of context.

**Fix:** replace `closure: none` with `link_reference: explicit` in
`sase/memory/decisions.md`. One line, no code. (`closure` and `link_reference` are
mutually exclusive — `frontmatter.py:267-268` — so it is a replacement, not an
addition.) This is the single highest-value item in this report and it is independent of
every recommendation below.

A second-order note: `closure: none` being a *trap* rather than a no-op is worth a
follow-up. It is the only spelling that silently subtracts a capability the author
almost certainly wants, and `docs/memory.md:229` still teaches `closure:` as the
canonical key while documenting nothing about `link_reference`.

---

## 3. The corpus does not justify the new mechanism

`corpus-before-mechanism` is the project's own standing rule, and it was written after
three memory-retrieval features were built and deleted at real cost. It applies directly
here. The measurements:

**Corpus size.** 54 strands across three webs (`decisions` 8, `glossary` 41,
`task_types` 5) plus 17 flat notes.

**Supersession events, entire history:** **one**, and it is partial (§4).

**Strand deletions, entire history:** zero. `git log --diff-filter=D -- 'sase/memory/**/*.md'`
returns nothing.

**Strand renames, entire history:** zero. (The wider memory corpus has exactly one note
rename ever, per `memory_as_source_artifacts` §2.3.)

**Authored links in the entire corpus:** one — the dead one from §2.

**Reads.** This is the most damning number. Of 8,989 memory read events:

| Strand | Reads | Distinct agents |
| --- | --- | --- |
| `decisions:host-owned-completion` | 3 | 3 |
| `decisions:gates-never-block` | 2 (one of them this report's) | 2 |
| `decisions:memory-webs` | 2 | 2 |
| `decisions:corpus-before-mechanism` | 1 | 1 |
| `decisions:rust-core-required` | **0** | 0 |
| `decisions:single-turn-agents` | **0** | 0 |
| `decisions:two-speed-verification` | **0** | 0 |
| `decisions:webs-render-in-their-own-section` | **0** | 0 |

Half the records have never been read by anything. The whole web has ~7 organic reads
across six days, against 508 for `cli_rules.md` and 435 for `generated_skills.md`. The
`decisions` web is not yet load-bearing context; it is a corpus in its first week.

Building supersession machinery for it now optimizes a retrieval path that agents are
not yet using. That is the precise failure mode `corpus-before-mechanism` was written to
prevent, and the `memory_as_source_artifacts` report already priced the threshold:
revisit "when memory supersession becomes routine — say the `decisions` web reaching
~25 records with active supersession chains." Eight records and one partial event is not
that.

**Token argument, priced.** The stated benefit of hiding is a smaller always-loaded
roster. Measured: the `decisions` roster payload is 1,403 characters ≈ 351 tokens for 8
records, ≈ **44 tokens per record**, inside a 3,023-token `CLAUDE.md`. Hiding the one
partially-superseded record would save **1.5% of one instruction file**, and would do so
by removing a record that is still substantially correct. At the ~25-record reopen
threshold with five superseded records, the saving reaches ~220 tokens — around 5%, and
only then worth a mechanism. `webs-render-in-their-own-section` already names the honest
version of this trigger: "A project accumulates enough memory webs that unconditionally
inlining every descriptor becomes a real token-budget problem."

---

## 4. The one real supersession is the case the proposal handles worst

On 2026-08-30, `webs-render-in-their-own-section` was accepted. Its text:

> This decision supersedes **the sentence** in `memory-webs` reading "The descriptor's
> own body, not any strand body, participates in core or reference rendering."

That is a partial supersession of one sentence. Everything else in `memory-webs` is
live and load-bearing: the descriptor-plus-strand-directory shape, `web: true`, the
`web:keyword` addressing, the four rejected alternatives, the eleven-rule validator, and
its own reopen clause. It is also *still cited by a third record* —
`corpus-before-mechanism` closes with "The `memory-webs` decision itself leans on this
record."

Under the proposal, marking `memory-webs` as superseded would delete a still-authoritative
record from the hub and from every agent instruction file, in order to retire one
sentence. Not marking it means the mechanism has **zero** applications in the current
corpus.

This is the sharpest argument against building now: the first real event in the corpus
does not fit the binary the design assumes. A supersession model that cannot express
"supersedes §3 of X" will either be wrong or unused, and you cannot tell which until the
corpus produces a second event to calibrate against. Partial supersession is also the
*normal* case for ADRs — decisions get amended far more often than they get wholly
reversed.

---

## 5. Hiding contradicts both models the proposal cites

**Hub notes.** Doto's distinction is that hub notes serve a *locating* function while
structure notes serve a *developing* one: "By pointing to where particular trains of
thought can be found… hub notes make it easy to find areas of your zettelkasten you'd
like to explore." The article never discusses removing, hiding, pruning, or curating hub
entries, and never mentions superseded or outdated notes. A locating device that hides
things is a worse locating device. In a Zettelkasten, a later note that revises an
earlier one *branches from* it; both stay reachable, and the fact that the old thought
was revised is itself part of the record. Hiding is not the hub-note idea extended — it
is the opposite move.

**ADR practice.** The `decisions` web is explicitly an ADR corpus, and ADR convention on
this exact question is settled and unanimous. In Nygard's original scheme and in
`npryce/adr-tools`, superseding is a two-sided operation: the new record links to the
old, and the old record's **status** changes to `Superseded by ADR-NNNN`. The record
stays in the directory and stays in the index. The commonly stated rationale is that the
status field exists so a reader can scan the directory and know which records are still
authoritative — and that preserving the historical record demonstrates that revisiting
decisions on new evidence is healthy. `adr-tools`' `-s` flag automates the annotation,
not a removal.

Your own descriptor already encodes the convention: "if the project changes course, a
new record is written and the old one is marked superseded in prose, never edited in
place." Marked, not hidden. The proposal to drop superseded records from the roster
would make SASE the outlier against both the note-taking model it borrows from and the
engineering practice it implements.

---

## 6. What *is* a real defect: the back-pointer, and prose that nobody enforces

The proposal is right that something is broken; it has misidentified what.

**The pointer runs the wrong way.** `webs-render-in-their-own-section` knows it
supersedes part of `memory-webs`. `memory-webs` does not know it has been superseded.
An agent that reads `decisions:memory-webs` today — two agents have — receives a
sentence about descriptors participating in core/reference rendering that stopped being
true six days ago, with nothing in the output to indicate it. Discovery requires already
having read the *other* record, which is exactly backwards: you read the old record
because you did not know about the new one.

**The prose convention failed on its first and only use.** The descriptor promises the
old record is "marked superseded in prose." `memory-webs.md` contains no such mark —
verified, the file has no self-referential supersession statement. n=1, and the
convention was not followed. This is the strongest available argument for *some*
mechanism, and it is an argument about enforceability, not about scale: prose
cross-references cannot be validated by `sase doctor`, so nothing noticed. A frontmatter
field can be.

**The status field already exists and is invisible.** Every decision strand already
carries `metadata: {status: accepted, decided: <date>}`. That mapping is parsed
(`web/frontmatter.py:366`) and stored, but it is **uninterpreted**: no validation, no
rendering in `sase memory read`/`show`, and displayed only in the ACE Memory panel
(`memory_panel_web_rendering.py:149`). The ADR status field — the exact affordance
convention says to use — is already in the data and simply never reaches an agent.

There is direct precedent in this codebase for the right behavior. `sase artifact read`
already prints `warning: superseded by <refs>` when a stored `supersedes` relation
points at what you are reading (`artifact_cli/read.py:298-300`), driven by
`superseded_by_refs` in `sdd/artifact_link_neighborhood.py:82`. Memory reads should
behave the same way. Notably, `memory-webs`' own reopen clause names that mechanism as
the adopted one, and warns against "a new, parallel link syntax."

---

## 7. Costing the options

Memory-web strand modeling is Python-only — the linked `sase-core` checkout contains no
strand or web types (`glossary.rs` is the phrase matcher; there is no memory-web module).
So none of these options needs a Rust wire change. That is the good news.

| Option | Touches | Size |
| --- | --- | --- |
| **A.** Fix `decisions.md` frontmatter | 1 memory file | one line |
| **B.** Prose + `[[…]]` back-link in the superseded record | 1 memory file (after A) | one line |
| **C.** Render `metadata.status` in read/show output | `selector_render.py`, `link_render.py`, docs, skill | small |
| **D.** Typed `superseded_by:` with validation + banner + auto-reference | + `notes.py`, `web/frontmatter.py`, `web/models.py`, `web/validation.py`, `web/mutation_validate.py`, `selector.py`, `doctor/checks_config_memory_webs.py`, ACE panel | medium |
| **E.** + roster suppression / instruction-file hiding | + `web/roster.py`, bare-web read semantics, `sase memory list` reachability, 17 `memory_panel_*` modules, `sase memory init` convergence, snapshot tests | medium→large |

Option E carries costs the proposal does not account for:

- **Bare-web reads become inconsistent.** `sase memory read decisions` reads *every*
  strand. Either hidden strands still print (contradicting the hiding) or they do not
  (an agent asking for the whole web silently gets a subset).
- **Hiding is a validator hazard.** A hidden strand is still on disk, still addressable,
  still scope-merged, and still subject to the label-collision rules
  (`web/validation.py:88`). "Present but invisible" is a new state every one of those
  rules has to reason about.
- **Convergence risk.** `sase memory init --check` must stay clean while the roster is a
  function of inter-strand relations rather than of directory contents. Every ACE strand
  add/delete path (`memory_panel_strand_add.py`, `memory_panel_delete.py`) gains a way
  to change a *different* file's rendered roster.
- **It is a one-way door on the audit trail.** Once superseded records stop appearing in
  agent instructions, the corpus stops advertising that it has a history — which is the
  main thing an ADR corpus is for.

**The documentation gap is larger than the feature gap.** The proposal's final clause —
make agents aware via `/sase_memory_write` — is correct and urgent, but under-scoped.
`src/sase/xprompts/skills/sase_memory_write.md` currently says nothing about `[[…]]`
links, `![[…]]`, `link_rendering`, `link_reference`, or Linked References.
`docs/memory.md` (260 lines) mentions none of them either, and still teaches `closure:`
as the canonical spelling — the one that turns links off. An entire shipped subsystem is
undiscoverable to the agents meant to use it. Adding supersession before documenting
links means shipping a second undocumented mechanism on top of a first.

---

## 8. Recommendation

**Do not build strand supersession as designed. Do these four things instead, in order.**

**Step 1 — Unbreak links in `decisions` (one line, do it first).**
In `sase/memory/decisions.md`, replace `closure: none` with `link_reference: explicit`.
This activates the `![[decisions/single-turn-agents]]` link already authored in
`gates-never-block.md` and makes every recommendation below possible. Nothing else in
this report is worth doing before this. Route through `/sase_memory_write`.

**Step 2 — Fix the back-pointer in prose, using the links that now work.**
Add to `sase/memory/decisions/memory-webs.md` a single line in the Claim section, near
the sentence that was retired:

> *Partially superseded:* the sentence below on core/reference rendering is retired by
> `[[decisions/webs-render-in-their-own-section]]`.

Use `[[…]]`, not `![[…]]` — a reference, so the reader gets the pointer and its summary
without paying for a full transclusion of a record they may not need. This is zero code,
it fixes the only real instance of the problem, and it demonstrates the partial-supersession
case that §4 shows a boolean field cannot express. It also honors the descriptor's
existing "marked superseded in prose" convention, which is currently unhonored.

**Step 3 — Make the existing ADR status visible on read (small, high leverage).**
Render `metadata.status` in `sase memory read`/`show` output when it is anything other
than `accepted`, as a line directly under the strand heading — mirroring
`sase artifact read`'s existing `warning: superseded by …`. Add a `doctor` check that a
strand whose `status` names another record links to it. This gives you the enforceable
half of the proposal (prose is unvalidatable; a status field is not) at a fraction of
the cost, it uses a field the corpus already populates, and it matches ADR convention
exactly. Deliberately, **status changes annotate; they never hide.**

**Step 4 — Document what already exists.** Update
`src/sase/xprompts/skills/sase_memory_write.md` to teach the link system as a whole,
regenerate and deploy per `generated_skills.md`, and bring `docs/memory.md` up to date.
The section agents need is short:

> Memory files can link to each other with `[[target]]` and `![[target]]`. A `[[…]]`
> link renders the target in a `## Linked References` list — its address, keyword, and
> summary — so a reader can decide whether to read it. A `![[…]]` link renders the
> target's full body inline, so use it only when the reader always needs it; prefer
> `[[…]]`, because every inlined body is paid for on every read. Targets are memory
> selectors: `web:keyword`, `web/slug`, or a flat note name. When a decision record
> retires part of an earlier one, link back from the earlier record with `[[…]]` and say
> what was retired — the reader of the old record is the one who needs to know.

While there, add the `closure:` → `link_reference:` migration note, because a web that
declares `closure: none` gets links disabled and gets no warning.

Steps 1, 2, and 4 are a single small plan with no code beyond a docs/skill edit. Step 3
is a separate small change. Together they resolve every concrete problem this report
found, and none of them forecloses the larger design.

**Do not build:** a `supersedes` relation type parallel to `[[…]]` links (contra
`memory-webs`' reopen clause), roster suppression, or instruction-file hiding.

---

## 9. What would reopen this

Falsifiable, adopting and sharpening the thresholds `memory_as_source_artifacts` §6
already set. Revisit a typed supersession mechanism when **both** hold:

1. The `decisions` web reaches **~25 records** with **at least 3 wholly-superseded**
   records — wholly, not partially, since §4 shows partial supersession is what the
   corpus actually produces and what a boolean field cannot represent; **and**
2. The roster cost of retired records exceeds **~200 tokens** of always-loaded context
   (currently ~44/record, so ~5 retired records), *or* an agent demonstrably acts on a
   superseded record after Step 3 shipped — which would prove annotation is insufficient
   and hiding is required.

Revisit **roster suppression specifically** only if (2)'s second clause fires. An agent
reading a clearly-marked superseded record and using it anyway is the only evidence that
would justify overriding both the hub-note model and ADR convention. Until then,
annotation is the intervention with evidence behind it.

**The test that would prove this report wrong:** three months out, `decisions` strand
reads remain under ~50 total *and* two or more superseded records have accumulated
without back-links. That would mean the corpus is neither being read nor being
maintained, and the right response is to question whether the `decisions` web earns its
always-loaded roster at all — not to add machinery to it.

---

## Sources

- [The Difference Between Hub Notes and Structure Notes, Explained — Bob Doto](https://writing.bobdoto.computer/the-difference-between-hub-notes-and-structure-notes-explained/)
- [npryce/adr-tools](https://github.com/npryce/adr-tools) — the `-s` supersede flag updates both records' status
- [Documenting Architectural Decisions Within Our Repositories — Embedded Artistry](https://embeddedartistry.com/blog/2018/04/05/documenting-architectural-decisions-within-our-repositories/)
- [Architecture Decision Records: Templates and Operational Patterns — hidekazu-konishi.com](https://hidekazu-konishi.com/entry/architecture_decision_records_templates_and_operations.html)
- [8 best practices for creating architecture decision records — TechTarget](https://www.techtarget.com/searchapparchitecture/tip/4-best-practices-for-creating-architecture-decision-records)
- In-repo: `sase/memory/decisions/{memory-webs,corpus-before-mechanism,webs-render-in-their-own-section,gates-never-block}.md`;
  `src/sase/memory/{links,link_render,link_resolve,selector,notes}.py`;
  `src/sase/memory/web/{frontmatter,closure,roster,models,validation}.py`;
  `src/sase/sdd/artifact_link_neighborhood.py`; `src/sase/artifact_cli/read.py`
- Sidecar: `202608/memory_as_source_artifacts/memory_as_source_artifacts.md` §2.3, §6;
  `202608/decisions_web_seed_adrs.md`
