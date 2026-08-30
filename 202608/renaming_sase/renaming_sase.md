# Renaming SASE: A Consolidated Naming Study

**Question.** `sase` is due for a rename. The brief adds a thesis: the thing SASE does
that nothing else does is **compact information from many independent sources onto one
surface** — all three ACE tabs do this, each in its own way. Constraint: **≤7 characters,
shorter is better.**

**Sources.** Two independent researchers reported first: [`__a`](renaming_sase__a.md)
(codex/gpt-5.6-sol) and [`__b`](renaming_sase__b.md) (claude/opus). This report merges
them with a third verification pass run on 2026-08-30, ~11:17 UTC.

**The headline.** The two reports produced shortlists with **zero names in common**, so
the first job was to find out which one was wrong. Neither was. They ran *different
screens* and each was blind to what the other's screen catches. Applying both screens to
both shortlists reorders both rankings and promotes a name that appears in neither
ranking.

---

## 1. What both reports got right, and what it costs

### 1.1 The brief's thesis holds, and it is sharper than "SASE has a nice TUI"

`__b` verified this against the repo and found the strongest form of the claim: in the
Artifacts tab the unification is **architecturally enforced**, not incidental —

> Every configured Artifacts pane — Agent, Stitches, Patch, Beads, Files, every document
> provider, and a degraded provider that failed to load — renders through one shared,
> contract-driven shell.
> — `docs/artifacts_pane_visual_grammar.md:3`

`__a` independently reached the same place from outside, matching the shape to two
established category terms: a **single pane of glass** (IBM) and a **common operating
picture** (JESIP). `__a`'s addition is the better one: a common operating picture is
*updated as work results change* and exists to support action — so the name should imply
**visibility in service of control**, not display alone.

**The naming constraint that falls out of this** (`__b`, and it is the single most useful
rule in either report): the metaphor must preserve **individual legibility**. A mosaic
keeps its tesserae distinguishable; a blend does not. Names meaning *fuse*, *merge*,
*blend*, or *melt* are wrong on the merits, not merely uninspiring.

### 1.2 The rename is a data migration, not a `sed` — verified independently

`__b`'s cost table reproduces almost exactly (my counts, HEAD moved slightly since):

| Surface | `__b` | Verified | Command |
|---|---:|---:|---|
| Tracked files | 9,230 | 9,231 | `git ls-files \| wc -l` |
| `sase` occurrences (case-insens.) | 99,459 | **99,469** | `git grep -oiI sase \| wc -l` |
| Files containing it (83%) | 7,677 | **7,678** | `git grep -liI sase \| wc -l` |
| Distinct `SASE_*` env identifiers | 319 | **319** | `git grep -ohI 'SASE_[A-Z][A-Z_]*' -- src \| sort -u \| wc -l` |
| Basenames containing `sase` | 159 | **159** | — |

The 159-vs-4,248 gap is the important nuance `__b` flagged against over-reading: most
path hits are the `src/sase/` prefix, so that part is one directory move.

The genuinely hard surfaces are the ones that reach **outside** the repo: `~/.sase` /
`SASE_HOME` (every install's state directory), `.sase` (the ProjectSpec extension in
every user's project), **319 public environment variables**, the `sase_<N>` workspace
convention, PyPI `sase` plus five plugin packages and the `sase-core` crate, `sase-org`
on GitHub, and `sase.sh`.

**This argues for doing it once, behind a deprecation window** — dual-read `~/.sase` and
`~/.<new>`, accept both extensions, honor `SASE_*` alongside `<NEW>_*`. SASE's own
feature-flag machinery exists for exactly this. It does not argue against renaming; it
argues for weighting *durable* availability heavily, which §2 does.

### 1.3 Why rename at all — `__a`'s argument, which `__b` never made

`__b` accepted the rename as given. `__a` supplied the actual justification and it is
stronger than aesthetics: **SASE already means Secure Access Service Edge** — it is in
the [NIST glossary](https://csrc.nist.gov/glossary/term/sase), Cisco and every other
network vendor market the category, and *they use the same "sassy" pronunciation*. This
is not a package-name squabble; it is a large, growing, well-funded enterprise category
that owns the term. Keep this as the decision's premise: the replacement must be a
brand, not another acronym.

---

## 2. The methodological conflict, resolved

This is where the two reports actually disagree, and resolving it is what reorders both
rankings.

| | `__a` | `__b` |
|---|---|---|
| **Screen** | Exact names on PyPI + npm + crates.io; **live product/web search** | PyPI JSON API (~120 names) + GitHub **org** names + `.sh` DNS |
| **Verdict on registries** | "Open" treated as a meaningful clearance | "PyPI availability is **not a usable filter**" — 41 of 46 common nouns registered, mostly decade-stale squats |
| **Blind to** | In-repo vocabulary collisions; rename cost; register fit | Live products on `.dev`/`.ai`/`.io`; GitHub **repo** names |

**Both halves are right, and they compose.** `__b` is correct that a dead 2013 PyPI squat
is not a reason to reject a name. `__a` is correct that the decisive question is whether
a **live, adjacent** product holds the name — and `__a`'s method is the only one of the
two that can see that.

So the working rule is: **registry status is a tiebreaker; live adjacency is a veto.**

### 2.1 `__a`'s collision table verifies completely

This was the claim most worth distrusting — twelve very specific product URLs. I fetched
every one. **All twelve resolve, and every description matches `__a`'s characterization:**

| Name | Live product | Verified title/description |
|---|---|---|
| Synopt | `synopt.dev` | "see how your team uses AI coding tools" — dashboard for Claude Code, Codex CLI, Cursor |
| Conspect | `conspect.studio` | "broadcast-grade multiview" — composites many live sources into one wall |
| Heddle | `heddle.run` | "A batteries-included declarative agent runtime" |
| Cairn | `cairn.computer` | "A desktop app for orchestrating AI coding agents" |
| Sinter | `sinter.tech` | "AI Project Brain for Founders" |
| Motet | `motet.dev` | "open-source AI runtime for multi-agent systems" |
| Reticle | `reticle.sh` | "Make your coding agent verify its own work" |
| Inlay | `inlay.dev` | AI-answer placement product |

Muster, Panopt (`.co` and `.dev`), Apercu and Sheaf likewise resolve. `__a`'s avoid-list
is trustworthy and should be treated as settled.

### 2.2 The convergent finding: the naming space is closing in real time

The two reports reached this independently, by different routes, and my pass added a
sixth data point:

- `__b` on PyPI, in SASE's exact niche: **`weft`** ("The durable task substrate for agent
  systems", released **2026-08-28 — two days before the research**), **`quoin`**
  ("Workflow state for stateless coding agents", 08-15), **`abax`** (08-11),
  **`tessella`** (08-09). `weft` was `__b`'s strongest metaphor before verification.
- `__a` on the open web: eight-plus ordinary-English metaphor names already held by
  2025–2026 agent-tooling products (§2.1).
- **Mine:** I independently derived **`cento`** — a literary work composed entirely of
  lines by other authors, which is an unusually exact description of the Artifacts tab,
  and free on all three registries. `cento.sh` is **"Cento — the command center for
  everything you build."** Taken, on the same TLD, in the same category.

Three researchers, three methods, same result. Two consequences, both load-bearing:

1. **Any clearance here has a shelf life of roughly four weeks.** Re-run the checks the
   day you commit.
2. **A merely-good available name beats a perfect contested one**, because the contest is
   being actively lost. This is the strongest single argument in favor of a rare or
   coined name over an ordinary English metaphor noun — and it is `__a`'s thesis,
   confirmed by `__b`'s data.

### 2.3 Two non-criteria, and one that both reports missed

- **GitHub org availability carries zero weight** (`__b`, correct). All 20 candidates
  were taken as users/orgs; the project already ships as `sase-org` while `sase` itself
  is uncontested. `<name>-org` is always available.
- **PyPI-only clearance carries little weight** (§2), for the squat reason.
- **Neither report checked local command-name collisions.** I did: all candidates are
  clear on PATH except **`plex`**, which on this machine is already the user's own alias
  for Plex Media Player, and `ace`/`axe`, which are the user's aliases for `sase ace`
  and `sase axe`. That independently confirms `plex` should stay dead.

---

## 3. Cross-checking: each report's shortlist under the other's screen

Neither report ran its screen on the other's candidates. This is the gap with the largest
effect on the answer.

### 3.1 `__b`'s finalists under `__a`'s live-product screen — three downgrades

| Name | `__b` availability score | What the live screen found | Effect |
|---|---|---|---|
| **`andon`** | **24/25** — "no dev-tool collision found" | **`getandon.com`: "Andon is a beautiful paper lantern-inspired device that shows you when your AI assistant is idle, working, or needs attention."** Plus `aws-solutions/amazon-virtual-andon` on GitHub. | **Downgrade.** A live product using the *identical metaphor* for the *identical purpose* — agent status at a glance. |
| **`docket`** | **25/25** — "cleanest availability profile in the set" | **`chrisguidry/docket` (143★): "a distributed background task system for Python."** Also `netvarun/docket` (708★, Docker registry) and `Docketeer` (881★, Docker/K8s dev tool). `docket.io` is a live AI marketing agent. npm and crates.io both taken. | **Downgrade hard.** Adjacent, same-language, same problem domain. The 25/25 is untenable. |
| **`mosaic`** | 15/25; "PyPI registered with **zero distributions**" — a reclaim candidate | PyPI `mosaic` has **3 releases and 2 files**, not zero — the PEP 541 reclaim argument is weaker than stated. **`mosaic.sh` is a live dev tool**: "In-app testing framework that runs inside your live web application." | **Downgrade.** Adjacent product on SASE's own TLD. |

`__b`'s screen could not have caught any of these: it checked PyPI, GitHub *orgs*, and
`.sh` DNS resolution only — never `.dev`/`.ai`/`.io`, never GitHub *repo* names, and
never what a resolving domain actually served.

### 3.2 `__a`'s finalists under `__b`'s registry screen — they hold up

| Name | PyPI | npm | crates.io | `.sh` | `.dev` | In-repo |
|---|---|---|---|---|---|---|
| `ommat` | free | free | free | — | — | 0 |
| `ommata` | free | free | free | — | — | 0 |
| `fanin` | free | **taken** | free | — | — | 0 |
| `fresnel` | taken | taken | taken | — | — | 0 |

`__a`'s clearances verify. This is the empirical vindication of its strategy: rare roots
survive the screen that ordinary nouns fail.

### 3.3 But `__a` underweights its own central cost

`__a` calls the pronunciation gloss for `ommat` "a manageable one-time cost." It is not
one-time — **it is paid by every new user, forever.** `ommat-` is not a word; it is a
bound morpheme. `ommatidium` is a word almost nobody knows, so the name has no meaning to
anyone without a gloss, and no recall hook once the gloss is forgotten. `__b` applied
exactly this objection to kill `fovea` (medical register, poor spelling-from-hearing) and
to dock `andon`; applied evenly, it costs `ommat` more than `__a` allows.

There is also a **register argument** `__a` never considered and `__b` only half-used.
SASE's object vocabulary is already a coherent Anglo-Saxon craft/textile family — verified
in-repo: `bead` (5,523), `patch` (5,486), `chop` (1,441), `web` (681), `stitch` (614),
`strand` (584). A Greek scientific root sits badly against that; `__b` correctly raised
this against `andon` as a Japanese loanword, then never applied it as a *positive* filter.

---

## 4. Applying the register filter: the name neither report ranked

If the evidence says (a) prefer a rare word over a contested common one, (b) preserve
individual legibility, and (c) fit the existing craft register — the search should target
**the weaving family**, which `__b` called "conceptually the best family" before declaring
it "destroyed by collisions": `weft` taken, `warp` is Warp Terminal, `loom` is Atlassian's,
`skein` is a live YARN deployer.

That conclusion was premature. Every casualty names a **thread or a tool**. The brief is
about the **finished surface**. One weaving word names that, and `__b` listed it in the
GitHub-org check without ever developing it as a candidate:

### `arras` — 5 chars

A rich woven wall hanging depicting multiple scenes on one continuous surface, named for
Arras, the Flemish town whose looms made them. Many threads from many sources, one
surface, **every scene still individually legible** — the constraint from §1.1, satisfied
literally rather than by analogy.

Screened on both methods:

| Check | Result |
|---|---|
| PyPI / npm / crates.io | **free / free / free** — rare for a real English word |
| `arras.sh`, `arras.dev`, `arras.org`, `getarras.com` | **no DNS** |
| Live products | `arras.io` = browser game (diep.io fan sequel); `arras.com` = marketing agency; `arras-theme` = WordPress theme. **Nothing in developer or agent tooling.** |
| In-repo occurrences | **0** |
| Local PATH collision | none |
| Length / shape | 5 chars; pure noun — `arras run`, `arras ace`, `arras patch list` |
| Register | textile — sits *inside* the existing bead / stitch / patch / strand / web family |

**Semantic reach** is better than the live-status names: a tapestry both *depicts* and
*records*, so it covers the durable Artifacts tab as naturally as the live Agents tab —
the axis on which `__b` docked `andon` and `radar`.

**Honest costs.** (1) *"Behind the arras"* — Polonius is stabbed behind one in *Hamlet* —
carries a faint connotation of concealment, which is in tension with a tool about
visibility. It is a literary association, not a common one, but it is real. (2) `arras.io`
is a moderately popular browser game, so bare-word search results will be noisy;
`arras dev` or `arras cli` disambiguates. (3) Spelling from hearing is imperfect
(*aras* / *arras*), though pronunciation ("ARR-uss") is unambiguous. (4) It is a somewhat
obscure word — but unlike `ommat` it *is* a word, with a picture attached and a
one-sentence gloss that people retain.

---

## 5. Ranked recommendations

Scored on the merged criteria: names the compaction with individual legibility · clear of
**live adjacent** collisions · semantic reach beyond the TUI · length and spellability ·
noun at a verb-dispatching CLI · zero internal-vocabulary collision · register fit.

| # | Name | Len | The case | The cost |
|---|---|---:|---|---|
| **1** | **`arras`** | 5 | One woven surface, many sources, every scene still legible; **free on all three registries and clear in dev tooling**; fits the existing bead/stitch/patch/strand register exactly | Obscure word; `arras.io` search noise; faint *Hamlet* concealment echo |
| **2** | **`ommat`** | 5 | The cleanest namespace of any candidate, and the compound-eye metaphor (many facets, one field of view) is genuinely exact; excellent hexagonal iconography | Not a word — a bound morpheme; the pronunciation gloss is paid by every new user, not once; Greek register clashes with the craft vocabulary |
| **3** | **`andon`** | 5 | Best supervision metaphor in the set — the one board a supervisor reads, and the cord that stops the line *is* ACE's kill control; covers visibility **and** intervention | **`getandon.com` is a live AI-assistant-status product on the same metaphor**; industrial vocabulary you can never fully own; loanword register |
| **4** | **`mosaic`** | 6 | The most instantly legible metaphor; needs no explanation to anyone | `mosaic.sh` is a live dev tool; PyPI reclaim weaker than reported; NCSA + MosaicML noise; longest of the leaders |
| **5** | **`fanin`** | 5 | Most exact systems description — the README already says work *fans out*; best tagline: "Fan out the work. Fan in the picture." | Generic engineering term, unownable in search; npm taken; reads as a surname; names half the loop |
| **6** | **`ommata`** | 6 | `ommat` with a real word behind it (Greek plural, "eyes"); same clean registries and iconography | Longer; still needs teaching; beetle-genus search noise |
| **7** | **`docket`** | 6 | Good register for "tracked, reviewable, repeatable work"; unambiguous spelling | **Adjacent collision: a distributed background task system for Python**; npm and crates taken; names a record, not a surface; bureaucratic tone |
| **8** | **`radar`** | 5 | ACE's 10s auto-refresh literally *is* a sweep; palindromic and universally spellable | Taken on all three registries; worn thin by business idiom; `radar.sh` resolves |
| **9** | **`fovea`** | 5 | Names *information density* more precisely than anything else | Taken everywhere; medical register; poor spelling from hearing |
| **10** | **`ace`** | 3 | See below — this is a different question, not a worse answer | See below |

**Do not use:** `weft`, `quoin`, `abax`, `tessella`, `cento`, `synopt`, `conspect`,
`heddle`, `muster`, `cairn`, `sinter`, `motet`, `reticle`, `apercu`, `precis`, `sheaf` —
all verified live in or adjacent to this niche. `panopt` is free on PyPI and conceptually
exact, and should still be rejected twice over: `panopt.co` and `panopt.dev` are live
products, and naming an agent-*supervision* tool after Bentham's prison hands every
critic their headline. `plex` additionally collides with an alias already on this machine.

### The `ace` question is prior to the ranking

`__b` is right to insist on this and `__a` reaches the compatible conclusion. If the
compaction surface is the differentiator, it already has a name, a flagship command, and
a docs section — and its acronym is **already stale**: "Agentic Change Explorer" still
encodes ChangeSpec, which was renamed to Patch, in five doc locations. It must be
re-expanded or retired regardless of what happens to `sase`.

So decide the brand architecture **before** picking from the table:

- **Keep ACE as the TUI's name** → the ranking above stands as-is, and `arras ace`,
  `ommat ace`, `andon ace` all read correctly. `__a` is right that the umbrella name can
  be chosen first and the subbrands revisited later.
- **Collapse project and surface into one** → `ace` becomes the serious candidate (3
  characters, maximum length bonus, bare command opens the TUI), and its real cost is
  §6.6 of `__b`: the Ace editor is a widely known dev tool, PyPI `ace` is live, and 4,611
  in-repo occurrences make this an *entangled* rename rather than a clean one.

### Before committing to anything

1. **Re-run every check the day you decide.** §2.2 documents six names lost in roughly
   three weeks, one of them two days before this research and one during it.
2. **Verify domain registration at a registrar.** Neither report could: RDAP is not
   exposed for `.sh` (`rdap.org` returns 404 for `sase.sh`, which the project
   demonstrably owns). DNS non-resolution is a one-way signal only — it proves *not in
   use*, not *unregistered*.
3. **Run a USPTO search in the software class.** All three of us skipped trademarks
   entirely. Worth an hour, especially for `mosaic` and `radar`.
4. **Say the finalists out loud, then test recall a day later.** *"Open the arras."*
   *"It's in the mosaic."* *"Check andon."* Put each on the README masthead and beside
   the current TUI screenshot before choosing.
5. **Budget the deprecation window from §1.2** — dual-read state directory, both file
   extensions, both env-var prefixes — and schedule the rename for a quarter that can
   absorb it. The right name next quarter beats the second-best name this week.
