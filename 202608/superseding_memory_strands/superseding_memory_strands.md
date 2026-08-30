# Superseding Memory Strands: Should A Strand Retire Another?

**Research question.** A memory web's descriptor is a hub note that points at every one
of its strands, unconditionally. The proposal: let one strand declare that it supersedes
another, so that (a) reading the successor renders the superseded strand inline or as a
reference, and (b) the superseded strand drops out of the hub roster and therefore out
of the Memory Webs section of every generated agent instruction file. `/sase_memory_write`
would be updated to teach agents the capability.

**Scope.** Critique and design recommendation. No behavior changed, no memory file
written. Measured against `sase@fdb962c13` (master, clean) on 2026-08-30, against the
live memory corpus and the live audited read log.

**Provenance.** Consolidates two independent reports — `superseding_memory_strands__a.md`
(codex/gpt-5.6-sol) and `superseding_memory_strands__b.md` (claude/opus) — plus this
author's verification pass. Every load-bearing claim below was re-derived from the
working tree; where the two reports disagreed, §4 says which one the evidence supports.

---

## Bottom line

**The rendering half of the proposal already shipped and is switched off by a one-line
config bug. The hiding half should not be built — but the surface it targets is the
right one, and the correct treatment there is annotation, not removal.**

| Sub-proposal | Verdict |
| --- | --- |
| Render the superseded strand inline / as a reference on read | **Already built** (§1); dead in `decisions` because of a config default (§2) |
| Make links work in the `decisions` web | **Do it today** — one line, provably side-effect-free (§2) |
| A supersession signal agents actually see | **Do it — in the roster, as an annotation** (§5). Neither source report proposed this |
| Hide superseded strands from the roster / agent instructions | **Do not build** (§3, §6) |
| A new typed `supersedes:` frontmatter edge | **Not needed** — existing fields already express it (§5) |
| Teach agents via `/sase_memory_write` | **Do it; the gap is far larger than supersession** (§7) |

Both source reports converge on the two conclusions that matter most, and both are
correct: hiding contradicts the hub-note model and ADR practice, and the corpus's one
real supersession event is *partial*, which a hide-or-show boolean cannot express.

Where they diverge — report A recommends building a typed edge with roster hiding, report
B recommends no new mechanism at all — the evidence supports neither position exactly.
The read log (§4) shows why: **the roster is the only surface with meaningful reach, and
read-time annotation lands almost nowhere.** That reframes the design, and the resolution
in §5 needs no new syntax and no new source of truth.

---

## 1. The rendering half already exists

Four commits on the current branch built an authored-link system, all within the last
few days:

| Commit | Subject |
| --- | --- |
| `ae83faa2e` | feat(memory): add authored link scanner and resolver |
| `7c8117b17` | feat(memory): add `link_reference` and `link_rendering` frontmatter |
| `90e3a385c` | feat(memory): fold authored links into the closure walk |
| `40cd8ce6e` | feat(memory): render Linked References for show and read |

What shipped: `[[target]]` is a reference link and `![[target]]` an inline link;
`link_rendering: inline` promotes every link in a note without the `!` prefix
(`selector.py:401`); inline same-web targets transclude in place
(`selector.py:504-514`); reference links render a `## Linked References` section with
each target's selector, label, and summary (`link_render.py:101-127`) in Markdown, rich,
and JSON; and always-loaded targets are auto-demoted to references so a `type: core`
note can never be inlined twice (`selector.py:363-375`).

That is, feature for feature, the proposal's "rendered (either 'inline' or as a
'reference') when the new note is read" clause. The machinery is relation-agnostic — the
only missing word is *supersedes*.

**Consequence.** The proposal must be re-scoped from "build strand supersession" to "add
a semantic on top of links that already work, and decide what the roster does about it."
Those are very different sizes, and the second is mostly a design question, not a build.

---

## 2. The live defect: authored links are silently disabled in `decisions`

`_parse_descriptor_link_reference` (`web/frontmatter.py:262-282`) maps the legacy
`closure:` key onto the new axis:

```python
if has_closure:
    ...
    link_reference = "implicit" if resolved_closure == "mentions" else "none"
```

`closure: none` therefore no longer means only "do not walk phrase mentions." It now
additionally means **"ignore every authored `[[…]]` link in this web."** The descriptor's
effective value propagates to every strand as their default
(`frontmatter.py:346` → `392` → `443-444` → `471`), and `_resolve_strand_links`
short-circuits on it (`selector.py:390`).

| Web | Declares | Effective `link_reference` | Authored links |
| --- | --- | --- | --- |
| `decisions` | `closure: none` | `none` | **off** |
| `glossary` | `closure: mentions` | `implicit` | on (+ phrase closure) |
| `task_types` | *(nothing)* | `explicit` (the default) | on |

The default is permissive; the one web that declares the legacy key is the one web where
links are dead — and it is the web this proposal is about.

**Verified live, not inferred.** `decisions/gates-never-block.md` holds the corpus's only
authored link, added earlier today (`31b7cba99`, then `f0a8fcefa` — *"Add `!` prefix to
decision file reference to make it use an inline rendering strategy"*). An audited
`sase memory read decisions:gates-never-block` returns:

```
preserves workspace claims and provider budget across a pause, per
![[decisions/single-turn-agents]] — no such primitive exists today, so blocking is not a
live alternative to reopen this decision toward.
```

Literal `![[…]]` mid-sentence. No transclusion, no Linked References section. An agent
reading this record gets a syntax artifact where context was intended.

**The fix is one line, and it is provably surgical.** Replace `closure: none` with
`link_reference: explicit` in `sase/memory/decisions.md`. The two keys are mutually
exclusive (`frontmatter.py:267-268`), so this is a replacement, not an addition. Neither
source report checked whether the swap has side effects; it does not:
`_closure_for_link_reference` returns `"mentions"` only for `implicit`, and `"none"` for
everything else (`frontmatter.py:244-245`). So `link_reference: explicit` yields closure
mode `none` — **identical** mention-closure behavior to today, differing only in whether
authored links are honored. There is no reason to defer this.

A follow-up worth filing: `closure: none` is a *trap* rather than a no-op — it is the
only spelling that silently subtracts a capability the author almost certainly wants, and
`docs/memory.md:229` still teaches `closure:` as canonical while documenting nothing
about `link_reference`.

---

## 3. Hiding contradicts both models the proposal cites

Both source reports reached this independently, and it holds.

**Hub notes.** Doto's distinction is that hub notes serve a *locating* function and
structure notes a *developing* one: hub notes point at where trains of thought can be
found. The article never discusses removing, pruning, or curating hub entries, and never
mentions superseded notes. A locating device that hides things is a worse locating
device. In a Zettelkasten a later note that revises an earlier one *branches from* it;
both stay reachable, and the fact of revision is itself part of the record.

Report A adds a fair caveat: SASE's descriptor already carries an exhaustive,
automatically generated roster of every strand, which makes it more *index* than Doto's
selective hub even before supersession exists. The honest framing is that the generated
Memory Webs section is an **active policy index**, not a zettelkasten exploration
surface. That reframing justifies caring about currency — but it does not license
deletion, because an index that omits retired entries stops advertising that a history
exists.

**ADR practice.** The `decisions` web is explicitly an ADR corpus, and convention here is
settled. In Nygard's original scheme and in `npryce/adr-tools`, superseding is two-sided:
the new record links to the old, and the old record's **status** changes to
`Superseded by ADR-NNNN`. The record stays in the directory and stays in the index — the
status field exists precisely so a reader scanning the index can tell what is still
authoritative. `adr-tools`' `-s` flag automates the *annotation*, not a removal.

**The descriptor already encodes the convention.** `sase/memory/decisions.md`: a record
"is immutable once accepted: if the project changes course, a new record is written and
the old one is marked superseded in prose, never edited in place." Marked, not hidden.
Dropping superseded records from the roster would make SASE an outlier against the
note-taking model it borrows from, the engineering practice it implements, and its own
written policy.

---

## 4. What the read log shows — and why it reframes the whole design

This is the finding that neither source report drew out, and it changes the answer.

Measured from `sase memory log` (8,991 read events, 36 memory paths, 3,960 agents):

| Memory path | Reads |
| --- | --- |
| `sase_beads.md` | 2,528 |
| `tui_perf.md` | 1,545 |
| `symvision.md` | 1,350 |
| … | … |
| `decisions:gates-never-block` | 3 |
| `decisions:host-owned-completion` | 3 |
| `decisions:memory-webs` | 2 |
| `decisions:corpus-before-mechanism` | 1 |
| `decisions:rust-core-required` | **0** |
| `decisions:single-turn-agents` | **0** |
| `decisions:two-speed-verification` | **0** |
| `decisions:webs-render-in-their-own-section` | **0** |

**Nine reads total across the entire `decisions` web, ever** — and at least two of those
nine are this research effort's own audited reads. Half the records have never been read
by anything. The web has never been read whole. Meanwhile all 3,960 agents receive the
roster in `CLAUDE.md` on every single turn.

Two consequences follow, and they cut in opposite directions from the two source reports:

1. **Report B's read-time status banner lands almost nowhere.** It is correct, cheap, and
   worth doing — but as the *primary* fix for "an agent acts on a stale decision" it
   cannot work, because agents are not reading strands. They are reading roster bullets.
   An annotation on a surface with ~1.5 reads/day does not protect a corpus consumed
   ~3,960 times/day through a different surface.

2. **Report A is right that the roster is the surface that matters, and wrong about what
   to do there.** Hiding is the one treatment that destroys information on the only
   surface with reach. The roster is exactly where the signal belongs — as an annotation.

The token argument, priced, confirms that economics cannot decide this. The `decisions`
roster payload is 1,399 characters ≈ 349 tokens for 8 records — **≈43 tokens per
record**, inside a 3,023-token `CLAUDE.md`. Hiding one record saves ~1.4% of one
instruction file. Annotating one record costs ~10 tokens, or ~0.3%. At this corpus size
the entire token question is noise, which means the decision must be made on correctness
and reversibility. There, annotation wins outright: **hiding is a one-way door on the
audit trail; annotation is not.**

---

## 5. The corpus's one real supersession — and the design it dictates

Both reports identified this correctly, and it is the sharpest constraint on the design.

On 2026-08-30, `webs-render-in-their-own-section` was accepted. Its text:

> This decision supersedes **the sentence** in `memory-webs` reading "The descriptor's
> own body, not any strand body, participates in core or reference rendering."

That is a supersession of *one sentence*. Everything else in `memory-webs` is live and
load-bearing — the descriptor-plus-strand-directory shape, `web: true`, `web:keyword`
addressing, four rejected alternatives, the eleven-rule validator. It is also still cited
by a third record: `corpus-before-mechanism` closes with "The `memory-webs` decision
itself leans on this record."

So under the original proposal, marking `memory-webs` superseded would delete a
still-authoritative record from every agent instruction file in order to retire one
sentence. Not marking it leaves the mechanism with **zero** applications in the current
corpus. Neither branch is acceptable, and partial supersession is the *normal* ADR case —
decisions get amended far more often than wholly reversed.

**Corpus scale, verified.** 54 strands (`decisions` 8, `glossary` 41, `task_types` 5)
plus 17 flat notes. Strand deletions in all history: **zero**. Renames: **zero**.
Supersession events: **one, partial**. Authored links: **one, the dead one from §2**.
Seven of eight decision records were created on 2026-08-24; the web is six days old.
`corpus-before-mechanism` — the project's own standing rule, written after three memory
features were built and deleted at real cost — applies directly.

### The pointer runs the wrong way, and prose failed at n=1

The proposal is right that *something* is broken; it has misidentified what.
`webs-render-in-their-own-section` knows what it supersedes. `memory-webs` does not know
it has been superseded — verified, the file carries no such mark. Two agents have read
`memory-webs` and received a retired sentence with nothing flagging it.

This is an **enforceability** problem, not a scale problem, and the distinction matters
for the reopen clause (§6). Prose cross-references cannot be validated by `sase doctor`,
so nothing noticed the convention was not followed on its first and only use.

### The resolution: no new syntax is required

This is where the two reports' disagreement dissolves. Report A proposes a new top-level
`supersedes:` frontmatter field. Report B proposes using the existing `metadata.status`.
The evidence favors B's substrate, for a reason B did not state: **`metadata` is a
free-form `dict[str, Any]`** (`web/models.py:36,59`; `frontmatter.py:222` validates only
that it is a mapping). Every decision strand already carries
`metadata: {status: accepted, decided: <date>}`.

That means a *scoped* supersession is expressible **today, with zero parser change**:

```yaml
metadata:
  status: superseded-in-part
  superseded_by: decisions/webs-render-in-their-own-section
  superseded_scope: the sentence on core/reference rendering
```

This matters beyond convenience. `memory-webs`' own reopen clause reads: "at which point
the existing `supersedes` / `superseded-by` artifact relations are the adopted mechanism
— **not a new, parallel link syntax**." Report A's new frontmatter edge is precisely a
new parallel link syntax; A acknowledges the conflict and argues past it, but does not
price the consequence — **A's plan cannot be implemented without first writing a new
decision record superseding `memory-webs`' reopen clause**, which would itself become the
corpus's second supersession event. A mechanism whose prerequisite is a use of itself is
a signal to look for a cheaper encoding. The `metadata` route is that encoding: it adds
no syntax, so the reopen clause does not bar it.

Report A's §5 is nonetheless correct on a point B did not address, and it should be
adopted: **do not make the artifact link store authoritative for memory.** Artifact-link
truth lives in per-artifact JSON under document sidecars with a machine-local aggregate,
while `sase memory init` renders instructions deterministically from committed memory
files. Coupling them would make the same primary commit render different agent
instructions depending on which sidecars are present, and would break atomicity between
an edge and the files that define its endpoints. Shared *vocabulary*, not shared
*persistence*.

---

## 6. What to build, and what it costs

`ordered_web_strands` (`web/lookup.py:27`) has exactly two callers — `catalog.py:81` and
`roster.py:69`. Report B priced roster suppression at "medium→large" and report A at
"medium"; in pure LOC both overstate it, since the roster is a single filter point. But
B's real objection was never LOC, and it stands: hiding creates a "present but invisible"
state that every one of the eleven validator rules must reason about, makes bare-web
reads inconsistent (`sase memory read decisions` reads every strand —
`test_bare_web_selector_reads_every_strand`), and adds a way for an ACE strand edit to
silently change a *different* file's rendered roster while `sase memory init --check`
must stay clean.

Annotation has none of those properties. `render_strand_roster` (`roster.py:69-84`)
builds each bullet as `- **{keyword}** (`{slug}`) - {summary}`; adding a marker derived
from `metadata.status` is a few lines at one site, changes no strand's visibility, and
leaves every validator invariant intact.

| Step | Touches | Size |
| --- | --- | --- |
| **1.** `decisions.md` → `link_reference: explicit` | 1 memory file | one line |
| **2.** Scoped back-pointer in `memory-webs.md` | 1 memory file (after 1) | one line, no code |
| **3.** Roster annotation from `metadata.status` | `web/roster.py`, a `doctor` check, snapshot tests | small |
| **4.** Render status on read/show | `selector_render.py`, `link_render.py` | small |
| **5.** Document the link system | `sase_memory_write.md`, `docs/memory.md` | docs only |
| ~~6.~~ Roster suppression / instruction hiding | — | **do not build** |

**The documentation gap is the largest gap in this report.**
`src/sase/xprompts/skills/sase_memory_write.md` is 49 lines and mentions `[[…]]`,
`![[…]]`, `link_rendering`, `link_reference`, and Linked References **zero times** —
verified by grep. `docs/memory.md` mentions none of them either and still teaches
`closure:` as canonical, i.e. it teaches the spelling that turns links off. An entire
shipped subsystem is undiscoverable to the agents meant to use it. Adding supersession
before documenting links would ship a second undocumented mechanism on top of a first.

A second, smaller staleness in the same skill: it advises preferring `type: reference`
over `type: core`, but `webs-render-in-their-own-section` (accepted 2026-08-30) holds
that web descriptors declare no `type:` at all and that it is stripped on convergence.
The tier advice no longer applies to descriptors, so the skill needs a pass regardless of
this proposal.

---

## 7. Recommendation

**Proceed — but build annotation, not supersession machinery, and put it in the roster.**

Do these in order. Steps 1, 2, and 5 involve no new code.

**Step 1 — Unbreak links in `decisions` (do first).** In `sase/memory/decisions.md`,
replace `closure: none` with `link_reference: explicit`. Proven side-effect-free in §2.
This activates the `![[decisions/single-turn-agents]]` link already authored in
`gates-never-block.md`. Nothing else here is worth doing first. Route through
`/sase_memory_write`.

**Step 2 — Fix the back-pointer, and make it scoped.** Add to
`sase/memory/decisions/memory-webs.md` a line near the retired sentence:

> *Partially superseded:* the sentence below on core/reference rendering is retired by
> `[[decisions/webs-render-in-their-own-section]]`.

Use `[[…]]`, not `![[…]]` — a reference gives the pointer and its summary without
transcluding a full record the reader may not need. This honors the descriptor's existing
"marked superseded in prose" convention, which is currently unhonored, and it is the
first actual test of that convention.

**Step 3 — Annotate the roster (the one piece of new mechanism worth building).** Render
a supersession marker on a strand's roster bullet, derived from `metadata.status`. The
marker must carry *scope*, because partial supersession is the only kind this corpus has
produced:

```
- **Memory Webs** (`memory-webs`) - *[partly superseded by `webs-render-in-their-own-section`]*
  A keyed memory collection is a flat descriptor note plus a sibling strand directory…
```

Add a `sase doctor` check that a strand whose `status` names another record actually
links to it, and that the named target exists. This is the enforceable half of the
proposal — prose is unvalidatable, a frontmatter field is not — and it lands on the only
surface agents actually read (§4). **Annotation never hides.**

**Step 4 — Render status on read.** Mirror `sase artifact read`'s existing
`warning: superseded by …` (`artifact_cli/read.py:298-300`, driven by `superseded_by_refs`
in `sdd/artifact_link_neighborhood.py:82`) in `sase memory read`/`show`. One caveat the
source reports missed: the artifact version prints to **stderr**, which an agent capturing
stdout may never see. Mirror the behavior, not the stream — put it in the rendered body.

**Step 5 — Document what already exists.** Update `sase_memory_write.md` to teach the
link system as a whole, regenerate and deploy per `generated_skills.md`, and bring
`docs/memory.md` up to date, including the `closure:` → `link_reference:` migration note
and the §2 trap. Add supersession authoring guidance in the same pass: use
`metadata.status` plus a `[[…]]` back-link on the *older* record; never delete or edit an
accepted body beyond adding the mark; state what was retired; and remember that marking a
record changes always-loaded agent instructions.

**Do not build:** roster suppression or hiding from agent instruction files; a typed
`supersedes:` frontmatter edge parallel to `[[…]]` links (barred by `memory-webs`' reopen
clause, and unnecessary per §5); or any coupling of `sase memory init` to the artifact
link store.

---

## 8. What would reopen this

The governing reopen clause fires when a web's "strand count or supersession rate
outgrows prose cross-references." That trigger has **not** been met — and for a sharper
reason than corpus size: prose was never actually tried. `memory-webs.md` carries no mark
at all. You cannot conclude that a convention was outgrown when it has zero successful
uses. Step 2 is that first use; Step 3 makes it enforceable. Revisit only after both have
been in place long enough to fail.

Revisit a **typed supersession mechanism** when both hold:

1. The `decisions` web reaches ~25 records with **at least 3 wholly**-superseded records
   — wholly, not partially, since §5 shows partial is what this corpus produces and what
   a boolean cannot represent; **and**
2. `metadata.status` has demonstrably become unwieldy as free-form text — e.g. `doctor`
   cannot validate a case that matters, or two records disagree about the same edge.

Revisit **roster suppression specifically** only if an agent demonstrably acts on a
clearly-annotated superseded record after Step 3 ships. That is the single piece of
evidence that would justify overriding both the hub-note model and ADR convention, and
nothing weaker should.

**The test that would falsify this report:** three months out, `decisions` strand reads
remain under ~50 total *and* two or more superseded records have accumulated without
back-links. That would mean the corpus is neither read nor maintained, and the right
response is to question whether the `decisions` web earns its always-loaded roster at
all — not to add machinery to it.

---

## Sources

**External.**
[The Difference Between Hub Notes and Structure Notes, Explained — Bob Doto](https://writing.bobdoto.computer/the-difference-between-hub-notes-and-structure-notes-explained/);
[Documenting Architecture Decisions — Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions);
[npryce/adr-tools](https://github.com/npryce/adr-tools) (the `-s` flag annotates both
records, it does not remove);
[AWS Prescriptive Guidance — ADR process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html);
[RFC Editor — RFC series relationships](https://www.rfc-editor.org/series/rfc/).

**In-repo (verified this turn).** `sase/memory/decisions.md`;
`sase/memory/decisions/{memory-webs,webs-render-in-their-own-section,gates-never-block,corpus-before-mechanism}.md`;
`src/sase/memory/{selector,notes,links,link_render,link_resolve,selector_render}.py`;
`src/sase/memory/web/{frontmatter,roster,lookup,models,closure,validation}.py`;
`src/sase/ace/tui/modals/memory_panel_web_rendering.py`;
`src/sase/sdd/artifact_link_neighborhood.py`; `src/sase/artifact_cli/read.py`;
`src/sase/xprompts/skills/sase_memory_write.md`; `docs/memory.md`;
`tests/memory/test_memory_selector.py`; `sase memory log`; `git log`.

**Companion reports.** `superseding_memory_strands__a.md`,
`superseding_memory_strands__b.md`, and (cited by both)
`202608/memory_as_source_artifacts/memory_as_source_artifacts.md`,
`202608/decisions_web_seed_adrs.md`.
