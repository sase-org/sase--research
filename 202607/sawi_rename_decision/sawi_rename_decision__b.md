# Renaming sase to sawi Research

Date: 2026-07-28

## Recommendation

Do **not** rename `sase` to `sawi`.

The diagnosis behind the proposal is correct and important: **`sase` is a badly damaged name.** It collides head-on
with Secure Access Service Edge, a Gartner-coined enterprise security category worth $15–17B in 2026 and marketed
heavily by Cisco, Palo Alto Networks, Zscaler, Netskope, Cato Networks, Cloudflare, and Fortinet. The collision is in
an *adjacent* field, not a distant one, and it is identical in both spelling and pronunciation ("sassy"). This is close
to the worst-case naming collision available in developer tooling.

But `sawi` is the wrong fix. It is a lateral move that pays the full rename cost — roughly 59,000 occurrences across
4,599 files, plus the PyPI name, the GitHub org, the `sase.sh` domain, the `~/.sase` state directory, the `.sase` file
extension, and five sibling repos — in exchange for a name that is merely *quieter*, not *stronger*:

- **The mustard pun does not survive translation.** Indonesian *sawi* means mustard **greens** (a leafy Brassica), not
  the condiment. The condiment is *mustar* / *moster*. A mustard-bottle logo is a pun on the English gloss, one
  translation step removed from the actual word.
- **Every good domain is gone.** `sawi.com` belongs to a Swiss marketing academy founded in 1968; `.io`, `.app`,
  `.dev`, `.ai`, and `.org` all resolve to registered holders. You would trade owning `sase.sh` for scrapping over
  leftovers.
- **It still collides in tech**, including with a cybersecurity company (`sawi.group`) — the same field you are trying
  to escape.
- **"Structured Agentic Work Interface" is a weaker expansion** than "Structured Agentic Software Engineering," and it
  orphans `ACE` and `AXE`, which currently echo a named research vision.

The right conclusion is not "keep `sase` forever." It is: **the rename is justified, but `sawi` is not the name to
rename to.** If you rename, rename to something you can actually own. Criteria and directions are in
[Section 9](#9-if-you-do-rename-the-bar-a-replacement-must-clear).

---

## 1. The Question

Should the project rename from `sase` (Structured Agentic Software Engineering) to `sawi` (Structured Agentic Work
Interface), potentially leveraging the Indonesian meaning of *sawi* ("mustard") for branding such as a mustard-bottle
logo?

Three things have to be true for the rename to be worth it:

1. The current name is meaningfully harmful.
2. The new name is meaningfully better, not merely different.
3. The improvement exceeds the switching cost.

Finding 1 holds strongly. Finding 2 fails. Finding 3 therefore fails.

---

## 2. Audit: Existing Usage of "sase"

### 2.1 Secure Access Service Edge — the disqualifying collision

Gartner introduced **SASE (Secure Access Service Edge)** in 2019 for the convergence of network and security services
into a cloud-delivered model (SD-WAN, SWG, CASB, NGFW, ZTNA). In 2021 Gartner added SSE (Security Service Edge) as a
subset. The category is now a mature, heavily contested enterprise market:

| Attribute | Value |
| --- | --- |
| Market size (2026) | $15–17B, projected >$30B by 2030 |
| Dominant vendors | Zscaler, Netskope, Palo Alto Networks, Cato Networks, Cisco |
| Also marketing SASE | Cloudflare, Fortinet, Check Point, Versa, Aryaka, Barracuda, BT |
| Pronunciation | "sassy" — **identical to this project's** |

This collision is severe for four compounding reasons:

- **Search is unwinnable.** Every major security vendor spends marketing budget on the term. A dev tool cannot rank.
- **The fields are adjacent, not distant.** A name clash with a Brazilian pastry would be harmless. A clash with
  enterprise infrastructure software means the exact audience — developers, platform engineers, CTOs — already has a
  strong, wrong prior. Every introduction spends its first sentence on "not the network security thing."
- **Spoken disambiguation also fails.** Both are said "sassy," so the collision persists in conference talks, podcasts,
  and hallway conversation, where a spelling difference would normally rescue you.
- **The wrong meaning is the *dominant* meaning** by orders of magnitude in commercial visibility.

### 2.2 Society of Asian Scientists and Engineers

**SASE** is also a US 501(c)(3) founded in 2007, serving 10,000+ members with chapters at many universities. It has
real GitHub presence (`UF-SASE-Web-Team`, and chapter sites at Stony Brook, BU, USF, UVA, Lamar). Not commercially
competing, but it further dilutes the term and adds noise to GitHub and social handle searches.

### 2.3 Other uses

- **Self-addressed stamped envelope** — the long-standing generic English abbreviation.
- **GitHub repos**: `SASE-Space/open-process-library` (60★, industrial automation), `haopeng/sase` (31★, a stream
  processing system from UMass), `SASE-Space/ot-openness-comparison` (29★).
- **PyPI `sase`** is yours (v0.12.0, "Structured Agentic Software Engineering", Bryan Bugyi) — one of the few assets
  you do hold cleanly.

### 2.4 What you currently own

`sase.sh` (live), `github.com/sase-org`, PyPI `sase`, npm `sase` (unregistered but reserved by absence), and Homebrew
`sase` (unclaimed). Crates.io `sase` is also free. **This is a real, non-trivial asset position.** It is the main thing
a rename would throw away.

---

## 3. Audit: Existing Usage of "sawi"

### 3.1 Organizations and companies

| Entity | Field | Notes |
| --- | --- | --- |
| **SAWI Academy** (`sawi.com`, `sawi.ch`) | Marketing / communication education | Swiss, founded **1968**. Owns the `.com`. The reference vocational school for marketing in Switzerland. |
| **sawi.group** | **Cybersecurity & hosting** | Sells "OmniD" (identity/password management) and "ServerShare" (hosting/project management). ~3 years old. |
| **Sawi Programming Group** | AI, software, consumer robotics | British, founded Jan 2023. Sourced only from EverybodyWiki — low reliability, treat as unverified and likely tiny. |
| **SAWI Foundation** / **Soyoye Akinyode Welfare Initiatives** | Nonprofits | `sawifoundation.org`, `sawi.org.ng` |
| **SAWI** (AUB) | Women's economic inclusion, MENA | Hosted at American University of Beirut |
| **Sawani** | Camel dairy, Saudi Arabia | PIF-backed, founded 2023; near-miss, not exact |
| **South Asia Water Initiative** | World Bank program | Acronym reuse |

Note the irony of `sawi.group`: it is a **cybersecurity** company. Renaming from a name owned by the security industry
to a name partly held by a (much smaller) security company does not fully escape the category you are fleeing.

### 3.2 Trademark

No active USPTO registration for the exact mark `SAWI` in software classes surfaced. The nearest hit, `SAWIS`
(Reg. 2657775, waste-management software), was **cancelled in 2009**. This is mildly favorable, but the SAWI Academy
has 58 years of continuous use in EU/CH marketing-education classes, so European clearance would not be automatic.
Direct USPTO/TESS and EUIPO searches were not completable here (Justia returned HTTP 403); treat trademark status as
**unverified**, not clear.

### 3.3 The Sawi people of Papua

The most prominent *non-vegetable* meaning of "Sawi" is the **Sawi people of Western New Guinea (Papua, Indonesia)**,
known widely in evangelical missions literature through Don Richardson's *Peace Child* (1974). The tribe is famous
specifically for having ritualized treachery: the cultural ideal Richardson documented was to "fatten a victim with
friendship" before betraying and killing him.

This is a niche association — most developers will never encounter it. But it is worth naming honestly, because the
resonance is unusually unfortunate for *this particular product*. A tool whose entire value proposition is
**trustworthy, auditable, supervised autonomous agents** would carry a name whose best-known human referent is a
society organized around betraying those who trust you. Low probability of anyone noticing; high awkwardness if they
do, particularly since the Indonesian framing is one you intend to lean into publicly.

### 3.4 Namespace availability

| Surface | `sawi` status |
| --- | --- |
| PyPI | ✅ **Free** |
| crates.io | ✅ **Free** (also `sawi_core`) |
| Homebrew | ✅ Free |
| `$PATH` command collisions | ✅ None found |
| GitHub org `sawi-org` | ✅ Free |
| GitHub user `sawi` | ❌ Taken |
| npm | ❌ **Taken** — squatted by an abandoned `create-next-app` scaffold (v1.1.4, published and last touched 2024-03-21) |
| `sawi.com` | ❌ SAWI Academy (Switzerland) |
| `sawi.io` | ❌ Live Arabic pricing/valuation site ("ساوي … اعرف وش يسوى") |
| `sawi.app` | ❌ Live |
| `sawi.dev` | ❌ Registered (DNS resolves; no HTTPS response) |
| `sawi.ai` | ❌ Registered (DNS resolves; no HTTPS response) |
| `sawi.org` | ❌ Registered |
| `sawi.sh` | ⚠️ **No A record** — plausibly available, but RDAP was inconclusive; confirm at a registrar |

GitHub repo search for `sawi` returns no exact-name project — the hits are `Sawit*` (Indonesian for oil palm),
`sawIntuitiveResearchKit`, and `SawimNE`. So the *code-search* picture for `sawi` is genuinely cleaner than for `sase`.

**But the domain picture is materially worse than what you have today.** You currently own `sase.sh` outright. Under
`sawi`, every conventional TLD is taken and your likely landing spot is `sawi.sh` (unconfirmed) or a compound like
`getsawi.com` / `sawi.tools`. Trading a clean owned domain for a scavenged one is a real regression, and it is the
kind of cost that is invisible in a naming discussion and painful for the next decade.

---

## 4. The Mustard Angle

This deserves its own section because it is the affirmative case for `sawi`, and it does not hold up as stated.

### 4.1 The translation is wrong

Indonesian ***sawi* means mustard *greens*** — the leafy Brassica vegetable, not the yellow condiment:

- *sawi hijau* / *caisim* — green mustard greens, choy sum (*Brassica rapa* subsp. *chinensis*)
- *sawi putih* — napa cabbage / Chinese cabbage
- *sawi hitam* — black mustard, whose **seeds** are processed into the condiment

The condiment itself is ***mustar*** or ***moster***, not *sawi*.

So the pun chain is: *sawi* (Indonesian) → "mustard greens" (English) → "mustard" (English) → yellow squeeze bottle.
That is two lossy hops. The consequence:

- **Indonesian speakers** — the exact audience the pun is aimed at — see a leafy green vegetable. A mustard bottle
  reads as a mistranslation, the way a logo of a pineapple would for a product named *apel*.
- **English speakers** who don't know Indonesian see an arbitrary condiment that needs a paragraph of explanation.

A pun that requires a footnote in *both* languages is not brand leverage; it is a mildly embarrassing trivia item. The
strongest branding is legible without a gloss.

### 4.2 What could actually be salvaged

If you like the botanical direction, two options are genuinely better than the bottle:

- **The mustard seed.** "The smallest of seeds that becomes the largest of plants" is one of the most widely legible
  metaphors in English, and it maps precisely onto the product: *one prompt fans out into a team of agents; small
  input, large structured outcome.* It is also botanically honest — mustard seed comes from *sawi hitam*.
- **A leafy-green mark.** Visually distinctive in a dev-tool landscape saturated with abstract geometry and gradients,
  and it is what the word actually means.

But note what this establishes: the salvageable branding rests on **mustard**, not on **sawi**. If the mustard-seed
story is the asset, that is an argument for a name that *says* mustard — not for a name that requires an Indonesian
dictionary to reach it.

---

## 5. The Provenance Problem

`sase` is not an arbitrary coinage. `docs/acknowledgements.md` records that the name comes from **"Agentic Software
Engineering: Foundational Pillars and a Research Roadmap"** (Hassan, Li, Lin, Adams, Chen, Kashiwa, Qiu; arXiv
2509.06216, Sept 2025), whose abstract defines:

- **SASE** — Structured Agentic Software Engineering, the overall vision
- **ACE** — Agent Command Environment, "a command center where humans orchestrate and mentor agent teams"
- **AEE** — Agent Execution Environment, "a digital workspace where agents perform tasks while invoking human
  expertise"

The project's architecture is built on this vocabulary: `sase ace` is the TUI command center, and `AXE` is the
background execution daemon deliberately echoing AEE. The README, the acknowledgements, and the
`why-coding-agents-need-orchestration` blog post all make the lineage explicit.

**How much weight should this carry?** Less than it first appears, but not zero.

- *Against renaming*: the name currently states a thesis. "This is a working implementation of the SASE vision" is a
  differentiated, credible position in a crowded agent-tooling market. `ACE` and `AXE` are legible as a set only
  because of it. `SAWI` orphans them into arbitrary three-letter names.
- *But*: implementing a research vision does not require **being named after it**, and separating the two is arguably
  cleaner. A distinct product name avoids implying that the paper's authors endorse or own the tool, and you can still
  say "sawi implements the SASE vision (Hassan et al., 2025)" in the first line of the README — which is *clearer*
  than the current situation, where the tool and the concept share a name and are easily conflated.

So the provenance is a genuine cost of renaming, but it is **not** by itself disqualifying. It is a reason to rename
carefully, not a reason to keep a broken name.

---

## 6. Evaluating "Structured Agentic Work Interface"

Independent of collisions, the proposed expansion is weaker than the current one on three counts.

**"Work" is vaguer than "Software Engineering," and less accurate.** The product is not a general work tool. Its
primitives are ChangeSpecs (PR-sized units), commits, hooks, review state, mentors, VCS integration, workspace clones,
and beads. It is emphatically a *software engineering* system. Broadening the name to "work" is aspirational
positioning for a product that has not broadened, and it discards the single most informative word in the acronym.

**"Interface" undersells the system.** sase is not an interface over something else. It is an orchestration runtime: a
scheduling daemon (AXE), a durable state store, a workspace manager, a prompt language with an LSP, and a multi-CLI
agent supervisor. "Interface" describes ACE — one component — and demotes the rest to invisibility. If anything the
system is closer to a *platform* or *environment* than an interface.

**It breaks the internal naming logic.** `ACE` and `AXE` currently rhyme with the paper's `ACE`/`AEE`. Under SAWI they
become unmotivated. You would be left explaining three unrelated acronyms instead of one family.

Also worth noting: the letters are being reverse-engineered to fit a chosen word. That is usually a sign that the word
is doing the deciding and the expansion is being back-filled — which is exactly how you end up with "Work Interface"
instead of something true.

---

## 7. Switching Cost

Measured in this checkout:

| Surface | Count |
| --- | --- |
| Occurrences of `sase` (case-insensitive) | **58,950** |
| Files containing `sase` | **4,599** of 5,717 tracked files (80%) |
| File paths containing `sase` | 2,712 |
| Distinct `SASE_*` environment variables | **331** |
| `.sase` file-extension references | 3,787 |
| `~/.sase` state-directory references | 955 |

Beyond the repo:

- **PyPI package** `sase` (published, v0.12.0) — requires a new package, a transition release, and a deprecation shim.
- **GitHub org** `sase-org` and repo `sase-org/sase` — redirects work, but stars/issues/links carry the old identity.
- **Domain** `sase.sh` (live docs site) plus the Cloudflare worker named `sase`.
- **Sibling repos**: `sase-core` (Rust, with the `sase_core_rs` binding), `sase-github`, `sase-telegram`, `sase-nvim`,
  and the `sase--research` / `--plans` / `--beads` / `--agents` sidecars.
- **User-facing state**: `~/.sase/projects/`, `.sase` ChangeSpec files, `~/.config/sase/sase.yml`, the `sase` command
  itself, generated `AGENTS.md`/`CLAUDE.md` memory shims, and every generated agent skill (`/sase_repo`, `/sase_plan`,
  …).
- **Every existing installation** would need a migration path for state directories and config.

The mechanical portion is largely automatable and the project is explicitly alpha, so this is not prohibitive. But two
things follow:

1. **The cost is real enough that you get roughly one rename.** Spending it on a name that is only marginally better is
   the worst outcome available — you pay in full and still don't own your name.
2. **The cost only grows.** If a rename is ever going to happen, alpha is the cheapest moment it will ever be. This
   argues for deciding deliberately and soon, not for deferring indefinitely.

---

## 8. Head-to-Head

| Criterion | `sase` | `sawi` |
| --- | --- | --- |
| Collision with a major industry term | ❌ Catastrophic ($15–17B category) | ✅ None comparable |
| Collision in tech generally | ❌ Multiple | ⚠️ `sawi.group` (cybersecurity), npm squat |
| Institutional brand holder | ⚠️ SASE nonprofit (10k members) | ⚠️ SAWI Academy, Switzerland, est. 1968 |
| Search ownability | ❌ Unwinnable | ⚠️ Better, but competes with a school, a vegetable, and a surname |
| Domain position | ✅ **Owns `sase.sh`** | ❌ `.com/.io/.app/.dev/.ai/.org` all taken |
| PyPI / crates.io | ✅ Held / free | ✅ Free |
| npm | ✅ Free | ❌ Squatted |
| Pronunciation clarity | ⚠️ "sassy" (needs a README gloss, and the gloss collides) | ⚠️ SAH-wee / SAW-ee / SAY-wee — also needs a gloss |
| Acronym quality | ✅ Accurate and specific | ❌ Vague ("Work"), inaccurate ("Interface") |
| Research provenance / story | ✅ Ties to Hassan et al. | ❌ Severed; orphans ACE/AXE |
| Branding hook | ⚠️ None | ⚠️ Mustard — but mistranslated |
| Unintended cultural association | ✅ None | ⚠️ Sawi tribe / ritual treachery (niche) |

`sawi` wins the collision row decisively. It loses domains, npm, acronym quality, and provenance. **On net it is a
sideways move, not an upgrade** — and sideways is not worth 59,000 edits.

---

## 9. If You Do Rename: The Bar a Replacement Must Clear

The `sase` problem is real and I would not tell you to ignore it. If you pursue a rename, the candidate should clear
**all** of these before you spend the switching cost:

1. **Zero collision with any established IT/enterprise category.** Search the bare term plus "software", "platform",
   and "security". If page one is someone else's product category, stop.
2. **`.dev` or `.sh` or `.com` actually acquirable.** Verify at a registrar, not by DNS. Do not rename into a domain
   you cannot own — you already have `sase.sh`, so this is a floor, not a nice-to-have.
3. **PyPI + crates.io + npm + Homebrew all free.** You need all four; `sase-core` means crates.io matters.
4. **Unambiguous pronunciation from spelling**, with no competing common word that sounds the same.
5. **Good as a CLI verb**: short (≤5 chars), lowercase, no shift key, comfortable to type dozens of times a day.
6. **Works as a namespace and a count noun**: `<name>.sh`, `~/.<name>/`, `<name>_core`, `<NAME>_ENV_VARS`,
   `.<name>` files.
7. **Preserves the ability to say "implements the SASE vision (Hassan et al.)"** in prose — this keeps the intellectual
   lineage without requiring the name to carry it, and lets `ACE`/`AXE` keep their meaning by explicit reference.

Two directions worth exploring, given the above:

- **Lean into mustard directly, in English.** If the mustard-seed metaphor is what you actually like — small seed,
  large structured growth, one prompt to a team of agents — then a name built on that idea in a language your audience
  reads will land without a footnote and gives you an obvious, ownable visual identity. This gets you the branding
  upside that motivated `sawi` without the translation problem.
- **Coin something meaningless and ownable.** Invented names have no collisions by construction, clear every registry
  and domain check, and let the acronym backronym be dropped entirely rather than degraded to "Work Interface."

Whichever direction, run the full checklist above *before* committing, and do it while the project is still alpha.

---

## 10. Bottom Line

**Do not rename to `sawi`.** You would spend a one-time, 59,000-occurrence, cross-repo, breaking-change budget to move
from a name with a catastrophic collision and a clean domain to a name with a smaller collision, no domain, a squatted
npm package, a weaker acronym, a broken pun, and no research lineage. That is not a trade worth making.

**But treat the `sase` name as a real, unresolved liability, not a settled question.** Colliding with a multi-billion
dollar enterprise security category — in the same industry, with the same pronunciation — is a permanent tax on every
introduction, every search, and every conference mention. It will not improve on its own, and the cost of fixing it
only rises from here.

The honest summary: **your instinct to rename is right; `sawi` is just not the name.** Keep looking, hold the
candidate to the Section 9 checklist, and make the call while the project is still alpha.

---

## Sources

- [Gartner — Definition of Secure Access Service Edge (SASE)](https://www.gartner.com/en/information-technology/glossary/secure-access-service-edge-sase)
- [Palo Alto Networks — What Is SASE?](https://www.paloaltonetworks.com/cyberpedia/what-is-sase)
- [Zscaler — What is Secure Access Service Edge?](https://www.zscaler.com/resources/security-terms-glossary/what-is-sase)
- [Netify — SASE Providers and Vendors Comparison (2026)](https://www.netify.co.uk/marketplace/sase/)
- [Top 5 SASE Platforms for 2026](https://guptadeepak.com/tools/top-5-sase-platforms-2026/)
- [SASE — Society of Asian Scientists and Engineers (ProPublica Nonprofit Explorer)](https://projects.propublica.org/nonprofits/organizations/261509658)
- [Hassan et al., *Agentic Software Engineering: Foundational Pillars and a Research Roadmap*, arXiv:2509.06216](https://arxiv.org/abs/2509.06216)
- [AgentPatterns.ai — Structured Agentic Software Engineering (SASE)](https://agentpatterns.ai/agent-design/structured-agentic-software-engineering/)
- [sawi.group — cybersecurity and hosting](https://sawi.group/)
- [SAWI Academy for Marketing & Communication (TopUniversities)](https://www.topuniversities.com/universities/sawi-academy-marketing-communication)
- [SAWI Foundation](https://www.sawifoundation.org/)
- [SAWI at American University of Beirut](https://www.aub.edu.lb/sawi/Pages/default.aspx)
- [Sawani (company) — Wikipedia](https://en.wikipedia.org/wiki/Sawani_(company))
- [Sawi Group — EverybodyWiki (low reliability)](https://en.everybodywiki.com/Sawi_Group)
- [Cook Me Indonesian — How to Identify Indonesian & Other Asian Leafy Greens](https://www.cookmeindonesian.com/asian-leafy-greens/)
- [Glosbe — "mustard" in Indonesian](https://glosbe.com/en/id/mustard)
- [foragri — Potensi Biji Sawi Sebagai Mustard](https://foragri.wordpress.com/2011/04/20/potensi-biji-sawi-sebagai-mustard/)
- [Don Richardson's *Peace Child* — Light Magazine](https://lightmagazine.ca/don-carol-richardsons-peace-child/)
- [Fifty years later, 'Peace Child' tribe still following Christ — Mission Network News](https://www.mnnonline.org/news/fifty-years-later-peace-child-tribe-still-following-christ/)
- [SAWIS trademark (cancelled 2009) — Justia](https://trademarks.justia.com/760/35/sawis-76035170.html)
