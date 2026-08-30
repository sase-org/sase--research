# Renaming SASE: What Should the Project Be Called

**Question.** `sase` (Structured Agentic Software Engineering) is due for a rename. The
brief adds a thesis: the thing SASE does that nothing else does is **compact a lot of
information from multiple independent sources onto one surface** — all three ACE tabs do
this, each in its own way. Constraint: **at most seven characters, shorter is better.**

**Method.** Facts verified against the repo at `d64219f03`, PyPI's JSON API, GitHub, and
DNS on 2026-08-30. Every count below is reproducible with the command shown. This report
follows the method of [`naming_the_change_unit.md`](naming_the_change_unit/naming_the_change_unit.md):
state the constraints, verify them, then rank.

---

## Bottom line

**Rename it to `andon`.**

An andon board is the single surface in a plant that carries the live status of every
independent station, so that one supervisor can see the whole line at a glance and
intervene. That is SASE's product thesis stated as a noun — "one developer, a team of
coding agents" — and it is the brief's compaction claim exactly. The andon *cord*, which
stops the line, is the same object as ACE's kill controls.

It is also the only strong candidate that is actually **free**: unregistered on PyPI, no
DNS on `andon.sh`, and zero occurrences anywhere in `src/` or `docs/`. That matters more
than it normally would, because §3 shows this naming space is closing fast.

**If you weight instant legibility over availability, take `mosaic`** (§6.2). It is the
better *metaphor* — many pieces from different sources forming one image while each piece
stays individually legible, which is a literal description of the Artifacts pane contract
— and everyone understands it without explanation. It costs you a PyPI name-reclaim
request and a registered `mosaic.sh`.

Both are defensible. `andon` wins on the constraints that kill names; `mosaic` wins on the
constraint that sells them.

Ranked list in [§7](#7-ranked-recommendations). **Read §4.1 before deciding anything** —
this rename is roughly 10× the ChangeSpec rename and, unlike that one, it *is* a data
migration.

---

## 1. What is being named, and is the thesis true?

The brief's claim is checkable, so I checked it. Each of ACE's three tabs is a
many-sources-one-surface compactor, and in the Artifacts case the property is
*architecturally enforced* rather than incidental.

**Agents tab.** One list compacts, per run: status, provider, model, retry chain, plan
state, pending user questions, unread flag, diffs, chats, and artifact files — across
seven different agent CLIs (Claude Code, Codex, Antigravity, Qwen, OpenCode, Muse, Grok),
each with its own process, workspace, and output format. The docs already name the effect
better than I could:

> State you used to keep in your head becomes a display.
> — `docs/blog/posts/structured-agentic-software-engineering.md:277`

**Artifacts tab.** Six-plus heterogeneous sources — Agent catalog, Stitches, Patches,
Beads, configured document providers, Files — under one shell. This is the strongest
evidence for the thesis, because the unification is a contract, not a coincidence:

> Every configured Artifacts pane — Agent, Stitches, Patch, Beads, Files, every document
> provider, and a degraded provider that failed to load — renders through one shared,
> contract-driven shell.
> — `docs/artifacts_pane_visual_grammar.md:3`

Providers declare facts; the host derives capabilities through named rules; and *every*
Artifacts surface — footer, help, command palette, copy registry, conformance suite —
reads that one contract (`docs/artifacts_pane_contract.md:6`). The invariant vertical
layout (pane brief → query bar → identity header → state/count lane → content →
footer hints) means a Bead and a research document are compacted by the same grammar.

**Axe tab.** The daemon plus every background command and proc on one status surface.

**Verdict: the thesis holds**, and it is sharper than "SASE has a nice TUI." The claim is
that heterogeneous sources are forced through *one* rendering grammar so that a single
human can hold the whole system in view. A name should denote that surface, or the
instrument that produces it.

One consequence for naming: the metaphor must preserve **individual legibility**. A
mosaic keeps its tesserae distinguishable; a blend does not. Words meaning *fuse*,
*merge*, *blend*, or *melt* are wrong on the merits, not merely uninspiring.

---

## 2. The rubric

Weights are chosen from what actually kills names, informed by §3 and §4.

| # | Criterion | Weight |
|---|---|---|
| C1 | **Names the compaction** — denotes one surface (or the instrument making one) carrying many independent sources, each still legible | 30 |
| C2 | **Clear of live collisions**, weighted heavily toward agent/dev tooling | 25 |
| C3 | **Short and typeable** — ≤7 hard, ≤5 preferred; unambiguous spelling from hearing | 15 |
| C4 | **Reads as a noun** at a verb-dispatching CLI | 10 |
| C5 | **No internal vocabulary collision** | 10 |
| C6 | **Register fit and no negative connotation** | 10 |

C2 is weighted second because §3 shows the space is being consumed in real time. C4
carries the prior report's finding that `sase` dispatches 46 top-level subcommands, many
of them imperatives (`sase commit`, `sase revert`, `sase run`), so a verb-shaped project
name reads as a command on first encounter. C5 carries the finding that SASE's internal
vocabulary is unusually dense.

---

## 3. The finding that reshaped the search: this space is closing

I checked PyPI's JSON API for ~120 candidates. Two things came back.

**First, PyPI is effectively saturated for short English nouns.** Of 46 common ones
checked, 41 were registered. `radar` (2013), `plex` (2009), `loom` (2014), `folio`
(2013), `slate` (2010), `bento` (2012), `vellum` (2009) and a dozen more are dead squats
— one release, a decade stale — but registered all the same. **PyPI availability is
therefore not a usable filter.** The usable question is whether a collision is *live and
adjacent*.

**Second, and more important: names are being taken in SASE's exact niche, right now.**

| Name | Version | Summary | Last release |
|---|---|---|---|
| `weft` | 0.9.98 | "The durable task substrate for agent systems" | **2026-08-28** |
| `quoin` | 0.19.5 | "Workflow state for stateless coding agents" | **2026-08-15** |
| `abax` | 0.1.20 | "A keyboard-first statistics and data-science workstation" | **2026-08-11** |
| `tessella` | — | "A declarative framework for creating UIs in Python" | **2026-08-09** |
| `vitrine` | 0.1.0 | "Research journal and live display for AI agents" | 2026-02-14 |

Reproduce with `curl -s https://pypi.org/pypi/<name>/json`.

Four of my best independently-derived candidates were taken by directly competing
agent-infrastructure or Python-TUI projects **within the last three weeks**. `weft` — a
thread woven crosswise to bind many parallel warp threads into one fabric — was my
strongest metaphor before verification and is now unusable. `quoin` and `abax` were
likewise generated and killed.

Two conclusions. **(a)** Any candidate must be re-verified immediately before you commit;
this report's clearances have a shelf life measured in weeks. **(b)** A name that is
merely *good* and *available today* beats a name that is *perfect* and contested, because
the contest is being actively lost.

---

## 4. Verified constraints

### 4.1 The rename cost is ~10× the ChangeSpec rename, and it is a data migration

The ChangeSpec rename was tractable because it was code-and-docs only — the on-disk
format did not contain the string. **That is not true here.** Verified counts:

| Surface | Count | Command |
|---|---:|---|
| Tracked files | 9,230 | `git ls-files \| wc -l` |
| Case-insensitive `sase` occurrences | **99,459** | `git grep -oiI sase \| wc -l` |
| Files containing it | **7,677** (83%) | `git grep -liI sase \| wc -l` |
| `from sase` / `import sase` statements | 22,776 | `git grep -ohI -e '^from sase' -e '^import sase' -- src tests` |
| Distinct `SASE_*` env-var identifiers | **319** | `git grep -ohI 'SASE_[A-Z][A-Z_]*' -- src \| sort -u \| wc -l` |
| `.sase` file-extension references | 406 | `git grep -ohI '\.sase\b' -- src \| wc -l` |
| `SASE_HOME` references | 36 | `git grep -ohI SASE_HOME -- src docs` |

One measurement needs a caveat so it is not over-read: 4,248 *paths* contain `sase`, but
only **159 basenames** do. The gap is the `src/sase/` prefix, so most of that is one
directory move, not 4,248 renames.

The genuinely hard part is not the code. It is the surfaces that reach *outside* the repo:

- **`~/.sase` / `SASE_HOME`** — the on-disk state directory of every existing install.
- **`.sase`** — the ProjectSpec file extension. Every user's project files carry it.
- **319 `SASE_*` environment variables** — a public interface, in user shell configs.
- **`sase_<N>`** — the workspace directory convention, referenced by agent instructions.
- **PyPI `sase`**, plus plugins `sase-github`, `sase-telegram`, `sase-nvim`,
  `sase-research-artifacts`, and the `sase-core` Rust crate.
- **`sase-org`** on GitHub and **`sase.sh`**.
- The pronunciation gloss ("sassy") that appears in the README and the blog.

**This is a compatibility problem, not a sed problem.** Whatever the name, budget a
deprecation window: dual-read `~/.sase` and `~/.<new>`, accept both file extensions, and
honor `SASE_*` alongside `<NEW>_*`. SASE's own feature-flag machinery
(`sase/memory/sase_flags.md`) exists for exactly this and should carry it.

Nothing here argues against renaming. It argues for doing it **once**, which is a reason
to weight C2 (durable availability) as heavily as §2 does.

### 4.2 GitHub org availability should carry zero weight

Every one of 20 candidate names is already taken as a GitHub user or org — `andon`,
`docket`, `mosaic`, `radar`, `plat`, `fovea`, `atoll`, `arras`, `mullion`, `trine`,
`slate`, `plex`, `comb`, `weir`, `argus`, `quipu`, `gnomon`, `synop`, `panopt`, `bale`.
The check is sound; a control name returned 404.

This is a non-criterion, because **the project already uses a suffixed org** (`sase-org`)
despite `sase` itself being an uncontested string. `<name>-org` is available in every
case. Do not let GitHub narrow the field.

### 4.3 Internal vocabulary collisions eliminate several otherwise-good names

Word-boundary counts in `src/` + `docs/`:

| Word | Count | Why it collides |
|---|---:|---|
| `pane` | 2,699 | The Artifacts pane is core vocabulary |
| `fold` | 715 | Patch fold levels, tree fold/unfold |
| `conn` | 241 | Connection abbreviation |
| `grid` | 235 | Textual layout |
| `score` | 81 | — |
| `tile` | 77 | — |
| `dash` | 32 | — |
| `chord` | 27 | — |
| `lens` | 12 | — |

`conn` is the painful one: free on PyPI, naval-control register, four characters,
**disqualified** by 241 in-repo uses. `pane` is the cruelest — it is the most literally
correct word for "one surface in a compacted UI" and it is the single most entrenched
term in the codebase.

Every finalist in §6 was verified at **0** internal occurrences, except `ace` (§6.6),
where 4,611 occurrences are the point rather than the problem.

### 4.4 Domains: a partial result, honestly labeled

RDAP is not exposed for `.sh` — `rdap.org` returned 404 for `sase.sh`, which the project
demonstrably owns. **I could not verify registration status.** DNS resolution is a weaker
but sound one-way signal: if it resolves, it is registered and in use.

| Resolves (registered, in use) | No DNS (not in use; registration unverified) |
|---|---|
| `mosaic.sh`, `radar.sh`, `plat.sh`, `atoll.sh`, `comb.sh`, `sase.sh` (control) | **`andon.sh`**, **`docket.sh`**, `fovea.sh`, `plex.sh` |

Confirm at a registrar before committing. This is the check most likely to have changed
by the time you read this.

---

## 5. Families explored, and why most died

Roughly 120 candidates across twelve metaphor families. The instructive failures:

- **Weaving** (`weft`, `warp`, `loom`, `skein`, `plait`) — conceptually the best family:
  many parallel threads bound into one continuous surface. Destroyed by collisions.
  `weft` taken by a live agent-infrastructure package (§3); `warp` is Warp Terminal;
  `loom` is Atlassian's; `skein` is a live YARN deployer.
- **Optics** (`lens`, `prism`, `fovea`, `iris`) — `lens` is the Kubernetes IDE and has 12
  in-repo uses. `prism` **splits** light; it is backwards. Only `fovea` survived.
- **Vantage** (`mesa`, `tor`, `aerie`, `perch`, `crag`) — `mesa` was excellent (a single
  flat elevated surface; "table" in Spanish) and is dead on arrival against Mesa 3D.
  `tor` is the anonymity network.
- **Control surfaces** (`helm`, `dash`, `deck`, `conn`, `bridge`, `cockpit`) — `helm` is
  Kubernetes, `cockpit` is Red Hat's, `dash` is Plotly's, `conn` fails §4.3.
- **Tessellation** (`mosaic`, `tile`, `tessera`, `quilt`) — `tessera` names *one* tile,
  the wrong number, and is taken by a Graphite dashboard. `quilt` is a patch-management
  tool, colliding in precisely the domain where SASE just standardized on "Patch."
  `tessella` fell in §3. Only `mosaic` survived.
- **Surveillance** (`panopt`, `argus`) — `panopt` is free on PyPI and conceptually exact
  (one point from which all is visible). **Reject it anyway.** The panopticon is
  Bentham's prison and Foucault's disciplinary metaphor; naming an agent-supervision tool
  after it hands every critic their headline. `argus` is milder but shares the problem.
- **Lean manufacturing** (`andon`, `kanban`, `gemba`) — `kanban` is unownable generic
  vocabulary. `andon` is *nearly* so, which is its main weakness (§6.1), but it is far
  less worn.
- **Records** (`docket`, `ledger`, `roster`, `tally`) — `ledger` is ledger-cli plus the
  hardware wallet. Only `docket` survived.
- **Also rejected:** `delta` (SASE already has a `DELTAS` field — the prior report's
  finding), `codex` (OpenAI's agent CLI, exact domain), `hive`/`flume`/`atlas` (Apache
  and MongoDB), `sonar` (SonarQube), `gist` (GitHub), `vista` (Windows), `tableau` (the
  BI vendor), `synop` (live 2026 AI CLI, and it reads as "synopsis" — a text summary —
  rather than its true root *synoptic*, "seeing together").

---

## 6. The finalists

### 6.1 `andon` — 5 chars

The board above a production line carrying the live state of every station, so one
supervisor sees the whole line at once. The metaphor is not decorative: it is the
industrial term of art for the exact artifact SASE builds, and it encodes the *asymmetry*
SASE is built around — many autonomous workers, one human watching one surface. The andon
cord that halts the line is ACE's kill control.

- **C1 28/30.** Precisely on brief, and uniquely covers supervision *and* intervention.
  Half a point off: an andon board carries live status, while the Artifacts tab also
  compacts durable records.
- **C2 24/25.** Unregistered on PyPI; no DNS on `andon.sh`; no dev-tool collision found.
- **C3 12/15.** Five characters, trivial to type. Loses points on spelling from hearing
  ("Anden"? "Anton"?) and on looking like a person's given name.
- **C4 10/10.** Pure noun. `andon run`, `andon ace` read correctly.
- **C5 10/10.** Zero in-repo occurrences.
- **C6 7/10.** A Japanese loanword against SASE's Anglo-Saxon object register (bead,
  stitch, patch, chop, axe, ace). And like `kanban`, it is industry vocabulary you cannot
  fully own — andon-light vendors exist, though none in software.

**Total 91/100.**

### 6.2 `mosaic` — 6 chars

Many independent pieces, of different origins, composing one image on one surface — with
every piece still individually visible. That last clause is the whole argument: it is the
Artifacts pane contract restated (§1), and it is the property that separates a compacted
view from a summary.

- **C1 30/30.** The best metaphor in the set, and instantly legible without explanation.
- **C2 15/25.** The PyPI name is registered **with zero distributions** — a genuine
  reclaim candidate, but reclaims are slow and uncertain. `mosaic.sh` resolves. NCSA
  Mosaic is one of the most famous names in computing; the echo is affectionate rather
  than confusing, but it makes search results permanently noisy, and MosaicML (now
  Databricks) is recent.
- **C3 11/15.** Six characters — the longest finalist, against a stated preference for
  short — but universally spellable and pronounceable.
- **C4 10/10.** Pure noun.
- **C5 10/10.** Zero in-repo occurrences.
- **C6 10/10.** Concrete object noun; sits naturally beside bead, stitch, and patch.

**Total 86/100.**

### 6.3 `docket` — 6 chars

The single running record of every matter before a court, each with its own status,
history, and filings. It is the best fit for SASE's own tagline — "tracked, reviewable,
repeatable work" — and for the Artifacts tab specifically.

- **C1 22/30.** Compacts many independent proceedings onto one authoritative surface, but
  it names a *record*, not a rendered surface. It misses the visual claim.
- **C2 25/25.** Free on PyPI; no DNS on `docket.sh`; no dev-tool collision found. The
  cleanest availability profile in the set.
- **C3 12/15.** Six characters; completely unambiguous spelling from hearing.
- **C4 10/10.** Pure noun. `docket run` reads well.
- **C5 10/10.** Zero in-repo occurrences.
- **C6 6/10.** Legal-bureaucratic register — it connotes queues and paperwork, where SASE
  wants cockpit.

**Total 85/100.**

### 6.4 `radar` — 5 chars

A radar display is the canonical situational-awareness surface: many independent contacts,
each with bearing, range, and identity, on one periodically-swept screen. ACE's default
10-second auto-refresh *is* a sweep. It is the strongest fit for the Agents tab.

- **C1 26/30.** Excellent for live tracking; weaker for durable records.
- **C2 13/25.** PyPI squat is dead (2013), but `radar.sh` resolves and "radar" is heavily
  used in product naming and worn thin by business idiom ("on our radar").
- **C3 14/15.** Five characters, palindromic, universally spellable.
- **C4 10/10.** Pure noun.
- **C5 10/10.** Zero in-repo occurrences.
- **C6 8/10.** Good concrete-instrument register; slightly generic.

**Total 81/100.**

### 6.5 `fovea` — 5 chars

The pit in the retina with the highest packing density of photoreceptors — the small
surface where the most information is resolved. Of every candidate, this one names
*information density* most exactly, which is the literal content of the brief.

- **C1 26/30.** Density, precisely. Slightly abstract: a fovea resolves detail rather
  than aggregating sources.
- **C2 19/25.** PyPI squat is dead (0.1.1, "research project", 2021); no DNS on
  `fovea.sh`.
- **C3 9/15.** Five characters, but spelling from hearing is poor and it is unfamiliar
  outside medicine.
- **C4 10/10.** Pure noun.
- **C5 10/10.** Zero in-repo occurrences.
- **C6 6/10.** Anatomical register, distant from bead/stitch/patch.

**Total 80/100.**

### 6.6 `ace` — 3 chars

The strategic option, and it falls directly out of the brief. If the compaction surface is
the differentiator, then the project should be named after the compaction surface — and
that already has a name, a command, and a documentation section. Renaming the project to
`ace` collapses two brands into one, maxes the length bonus at three characters, and makes
the bare command open the TUI (`ace` for the surface, `ace run "…"` to launch).

The timing argument is real: the acronym is **already stale**. "Agentic Change Explorer"
appears in five doc locations and still encodes `ChangeSpec`, which was renamed to Patch.
It has to be re-expanded or retired regardless.

- **C1 20/30.** Indirect. `ace` denotes the surface only because SASE says so; the word
  itself carries no compaction meaning.
- **C2 8/25.** The Ace editor (ajaxorg) is a widely known dev tool; PyPI `ace` is a live
  statistics package; the word is extremely generic.
- **C3 15/15.** Three characters. Unbeatable.
- **C4 9/10.** Noun.
- **C5 n/a.** 4,611 occurrences are continuity, not collision — but they mean this is an
  *entangled* rename, not a clean one, and you must answer "what is the TUI called now?"
- **C6 7/10.** Fine register; the ACE/AXE pairing is a real asset that a rename would
  disturb.

**Total ~72/100** — but it scores differently than the others, because most of its value
is strategic rather than linguistic. **Do not dismiss it without deciding the brand
question first** (§8).

### 6.7 Shorter also-rans

`plat` (4) — a surveyor's single sheet compacting many parcels; 0 in-repo, dead 2016
squat; but `plat.sh` resolves, it reads as a typo of "plot," and the metaphor is static.
`plex` (4) — from *plectere*, "to braid," the root of multiplex; conceptually exact and
`plex.sh` has no DNS, but Plex is a large consumer brand. `comb` (4) — honeycomb is the
densest packing on a plane, and "comb through" is a second on-brief meaning; but "kohm"
is mis-said and mis-read as hair care, and `comb.sh` resolves. `atoll` (5) — free on
PyPI, pleasant, but the metaphor is a ring enclosing a lagoon, which is a boundary, not
a compaction; it sounds better than it argues.

---

## 7. Ranked recommendations

| # | Name | Len | Score | The one-line case | The one-line cost |
|---|---|---:|---:|---|---|
| 1 | **`andon`** | 5 | 91 | The board where one supervisor reads every station at a glance — the brief, stated as a noun | Loanword register; ambiguous spelling from hearing |
| 2 | **`mosaic`** | 6 | 86 | Many sources, one image, every piece still legible — the pane contract restated | PyPI reclaim needed; `mosaic.sh` taken; NCSA echo |
| 3 | **`docket`** | 6 | 85 | Cleanest availability in the set; the running record of every tracked matter | Names a record, not a surface; legal register |
| 4 | **`radar`** | 5 | 81 | Many contacts on one swept surface; ACE's refresh *is* the sweep | Worn thin as a brand word; `radar.sh` taken |
| 5 | **`fovea`** | 5 | 80 | Names information density more exactly than anything else | Hard to spell from hearing; medical register |
| 6 | **`ace`** | 3 | ~72 | Collapse the brand into the surface that is already the differentiator; 3 chars | Ace editor; generic; entangled rather than clean rename |
| 7 | **`plat`** | 4 | 70 | Shortest clean noun; one sheet, many parcels | Reads as a typo; static metaphor; `plat.sh` taken |
| 8 | **`plex`** | 4 | 68 | Literally "many signals, one channel"; `plex.sh` clear | The Plex brand |
| 9 | **`comb`** | 4 | 65 | Densest packing on a plane, plus "comb through" | Pronunciation; hair care |
| 10 | **`atoll`** | 5 | 60 | Free on PyPI; short and pleasant | The metaphor is a boundary, not a compaction |

**Shortlist to actually sit with: `andon`, `mosaic`, `docket`.** They are the three that
survive every hard constraint, and they represent three different bets — `andon` bets on
the supervision metaphor, `mosaic` on the visual one, `docket` on the record. Say each one
out loud in a sentence you would actually write: *"Open andon."* *"It's in the mosaic."*
*"Check the docket."*

---

## 8. What I could not settle, and what would change the ranking

1. **Domain registration is unverified** (§4.4). If `andon.sh` turns out to be registered
   and parked at a high price, `docket` moves to first — it has the same clean profile and
   a better register for the money you would otherwise spend.
2. **The brand question is prior to the name question.** If ACE remains the TUI's name,
   the project name and the surface name stay split, and §6.6 is moot. If you intend to
   collapse them, that decision reframes everything — decide it first, then name.
3. **Shelf life.** §3 shows four strong candidates taken in three weeks. Re-run the PyPI
   and DNS checks the day you commit; do not trust this report's clearances beyond ~4
   weeks.
4. **I did not check trademarks** — only PyPI, GitHub, and DNS. For `mosaic` and `radar`
   especially, a USPTO search in the software class is worth an hour before committing.
5. **The cost in §4.1 may argue for patience, not for a different name.** 99,459
   occurrences across 83% of tracked files, 319 public environment variables, and a
   user-facing state directory and file extension mean this should happen once, behind a
   deprecation window, at a moment when the schedule can absorb it. The right name chosen
   next quarter beats the second-best name chosen this week.
