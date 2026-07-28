# Renaming `sase` to `sawi`: Consolidated Decision Research

Date: 2026-07-28

Consolidates two independent research reports ([`__a`](sawi_rename_decision__a.md), codex/gpt-5.6-sol;
[`__b`](sawi_rename_decision__b.md), claude/opus) plus lead verification. Both researchers independently recommended
against the rename. Verification confirms that conclusion — but corrects three of the arguments used to reach it, in
both directions.

---

## Recommendation

**Do not rename `sase` to `sawi`.**

But the reasoning matters, because both source reports reached the right answer partly through arguments that do not
survive checking. The case against `sawi` is **not** primarily about namespaces or domains — that part of both reports
is overstated. `sawi` is actually *fine* on namespaces: PyPI, crates.io, the `sawi-org` GitHub org, and `sawi.sh` are
all free.

The real case against `sawi` is narrower and holds firmly:

1. **"Structured Agentic Work Interface" is a materially worse expansion** than the current one — vaguer *and* less
   accurate about what the system is.
2. **The mustard pun does not survive translation.** Indonesian *sawi* is mustard **greens**, not the condiment.
3. **`sawi` means "doomed/ill-fated" in Filipino** — a live, common word, and an actively bad meaning for a
   reliability-oriented developer tool.
4. **It does not solve enough to justify ~59,000 edits.** It trades a loud collision for a quiet one without buying
   ownership.

The diagnosis behind the proposal is sound: `sase` is a genuinely damaged name. The prescription is wrong.

---

## 1. What All Three Analyses Agree On

- `sase` collides head-on with **Secure Access Service Edge** — a Gartner-coined category (2019) in the $15–17B range
  for 2026, marketed by Zscaler, Palo Alto Networks, Netskope, Cato, Cisco, Cloudflare, and Fortinet. The collision is
  identical in spelling *and* pronunciation ("sassy"), and sits in an **adjacent** field, so the target audience carries
  a strong wrong prior. Security vendors now also publish on "agentic SASE," so the `agentic` modifier no longer
  disambiguates.
- Secondary `sase` uses (Society of Asian Scientists and Engineers, Society for the Advancement of Socio-Economics,
  self-addressed stamped envelope, `haopeng/sase`, `SASE-Space`) add noise but are not commercial threats.
- `sawi` is cleaner in code search but **not** commercially clean, and — ironically — one holder (`sawi.group`) is a
  cybersecurity company, so the rename does not fully escape the category it is fleeing.
- The rename is mechanically large but largely automatable; the project is pre-1.0, so **now is the cheapest this will
  ever be**. You get roughly one rename, which is exactly why it should not be spent on a lateral move.

---

## 2. Corrections to the Source Reports

This is where consolidation changes the picture. Each item below was checked directly.

### 2.1 Both reports were wrong about the domain position — it does not regress

Both leaned hard on "you own `sase.sh`; under `sawi` you would scavenge for leftovers." Report `__b` called it "a real
regression … painful for the next decade." Two checks undo this:

| Check | Result |
| --- | --- |
| `sawi.sh` at the `.sh` registry (whois) | **`Domain not found.`** — confirmed **unregistered and available** |
| `sase.sh` creation date | **2026-05-06**, GoDaddy — roughly **three months old** |

Both reports left `sawi.sh` as "plausibly available, unconfirmed." It is available. And `sase.sh` is not an accrued
asset — it is a three-month-old commodity registration with no meaningful SEO history or link equity behind it. The
honest statement is: **`.sh`-for-`.sh` is a wash.** `sawi` loses `.com/.io/.dev/.ai/.app/.org`, but so does `sase`
(all of those are occupied for `sase` too, and `sase.ai` is listed for sale). Neither name gives a clean primary-domain
story; that is not a differentiator between them.

*Minor addition:* `sawi.org` resolves to Afternic nameservers — it is parked **for sale**, not in productive use.

### 2.2 Report `__a`'s "strongest conflict" is not supported

`__a` identified a Brazilian company launching "a proprietary platform called **SAWI OS** plus an AI-oriented product
line" and called it "the strongest conflict found." Checking the company's own pages does not support this.
`sawi.com.br` / `agenciasawi.com.br` is a **digital marketing agency in Campinas**, founded 2008 by Filipe Carpes and
Rafael Pini.
Its own about page states the name comes from **Tupi-Guarani, meaning "full of"** — reflecting "full service." It
markets a four-stage **"S.A.W.I. framework"** methodology and uses AI in service delivery. There is no "SAWI OS"
product and no agent platform.

**Downgrade:** from "strongest conflict" to a moderate exact-name use in marketing services. Report `__b` never raised
it, which turns out to be the more defensible position. This removes the single scariest-sounding item in `__a`.

### 2.3 Report `__a`'s Filipino finding is correct — and is the most important linguistic fact in either report

`__b` missed this entirely; `__a` raised it and *understated* it. Verified: Tagalog/Filipino **`sawî`** is an adjective
meaning **ill-fated, unfortunate, unlucky, doomed**, and it is a productive root:

- **`masawî`** — to die, perish, meet with misfortune
- **`kasawian`** — misfortune, **failure**
- **`sawi sa pag-ibig`** — unlucky/heartbroken in love (idiomatic and very common)

This is not obscure vocabulary; it is everyday Filipino. For a product whose entire pitch is *dependable, auditable,
supervised* agent work, shipping under a name that reads as "failed" or "doomed" to ~100M Filipino speakers is a
materially worse problem than either the Papua tribe association or any of the corporate collisions. The tone
difference between Indonesian (`sawi` = a vegetable, neutral-positive) and Filipino (`sawî` = doomed) also means the
"lean into the Southeast Asian meaning" branding play cannot be run cleanly — the two largest audiences for that play
read the word oppositely.

### 2.4 Report `__b`'s provenance claim is confirmed verbatim

`docs/acknowledgements.md` §"Research Papers" states that
[Hassan et al., arXiv:2509.06216](https://arxiv.org/abs/2509.06216) "inspired the project's name and overall
direction," and that its **Agent Command Environment (ACE)** and **Agent Execution Environment (AEE)** "directly
informed the naming and design of the `ace` TUI and `axe` daemon." README.md and the
`why-coding-agents-need-orchestration` blog post carry the same lineage.

`__b`'s weighting is right: this is a **real** cost of renaming but **not** disqualifying. You can implement a research
vision without being named after it, and separating the two arguably reduces the current conflation of tool and
concept. `SAWI` would, however, orphan `ACE`/`AXE` into unmotivated three-letter names.

### 2.5 Trademark: treat as unverified — `__b`'s posture is correct

`__a` asserts a live US registration **5,348,204** for a stylized SAWI mark (temperature sensors, Swiss
Sawi Mess- und Regeltechnik AG). I could not confirm this — Justia returns HTTP 403 and the registration number does
not surface in search. The Swiss sensor company demonstrably exists (`sawi.ch`), but its US registration status is
unconfirmed here. `__b` found no active exact `SAWI` registration in software classes, with the nearest hit `SAWIS`
(Reg. 2657775) **cancelled in 2009**, and correctly labeled the whole area unverified.

**Correct posture:** neither report performed (or could perform) clearance. `SAWI` is not a fresh mark — a 58-year-old
Swiss academy and a Swiss industrial firm both use it — but no software-class blocker is established either. This is a
counsel question, not a research question.

### 2.6 Switching cost: independently verified, both reports accurate

Re-measured in this checkout:

| Metric | Verified | Reports said |
| --- | ---: | --- |
| Occurrences of `sase` (case-insensitive) | **59,130** | ~58,950 (both) |
| Files containing `sase` | **4,610** of 5,728 tracked (**80%**) | 4,599–4,600 |
| Tracked paths containing `sase` | **2,720** | 2,712 |
| Distinct `SASE_*` identifiers | **360** | 331 (`__b`) |
| `.sase` extension references | **3,900** | 3,787 (`__b`) |
| Occurrences of `sawi` anywhere in tree | **0** | 0 |

Small drift is just commits since. `__a`'s cross-repo total (~68,000 including `sase-core`, `sase-github`,
`sase-nvim`, `sase-telegram`, and the chezmoi config repo) is the more complete figure.

---

## 3. The Case Against `sawi`, After Corrections

With the domain and Brazil arguments removed, three things carry the decision.

### 3.1 The expansion is worse — this is the strongest argument

Both reports converged here independently, and it survives scrutiny best.

- **"Work" discards the most informative word.** The system's primitives are ChangeSpecs (PR-sized units), commits,
  hooks, review state, mentors, VCS integration, workspace clones, plans, and beads. It is emphatically a *software
  engineering* system. "Work" is aspirational positioning for a product that has not broadened — and the repo shows 53
  in-tree uses of the full "Structured Agentic Software Engineering" expansion, which is accurate today.
- **"Interface" undersells the system.** `sase` is not an interface over something else. It is an orchestration
  runtime: a scheduling daemon (AXE), a durable state store, a workspace manager, a prompt language with an LSP, and a
  multi-CLI agent supervisor. "Interface" describes ACE — *one component* — and demotes the rest. The system is closer
  to a platform or environment.
- **The letters are being back-filled.** "Work Interface" reads as reverse-engineered to fit a chosen word, which is
  usually the sign that the word is doing the deciding.

Net: `SASE` names a coherent practice; `SAWI` names a UI specification. That is a downgrade in precision at the exact
moment you would be paying maximum cost.

### 3.2 The mustard angle does not work as proposed

Indonesian **`sawi` means mustard *greens*** — the leafy Brassica — not the condiment:

- *sawi hijau* / *caisim* — green mustard greens, choy sum
- *sawi putih* — napa cabbage
- *sawi hitam* — black mustard, whose **seeds** are processed into the condiment

The condiment itself is **`mustar`** / **`moster`**. So the pun chain is *sawi* → "mustard greens" → "mustard" →
yellow squeeze bottle: two lossy hops. Indonesian speakers — the audience the pun targets — see a mistranslated
vegetable. English speakers see an arbitrary condiment needing a paragraph of setup. A pun requiring a footnote in
*both* languages is trivia, not leverage. Add §2.3 and the Southeast Asian framing gets actively risky.

**What is salvageable — and it is genuinely good.** The **mustard seed** metaphor is excellent and precise for this
product: the smallest seed becoming the largest plant maps exactly onto *one prompt fanning out into a coordinated team
of agents — small input, large structured outcome*. It is botanically honest (mustard seed does come from *sawi
hitam*), instantly legible in English with no gloss, and gives an obvious, ownable visual identity.

But note what that establishes: **the asset is *mustard*, not *sawi*.** If the seed story is what you love, that argues
for a name that *says* mustard in a language your audience reads — not one that requires an Indonesian dictionary to
reach it, and that means "doomed" in Filipino.

### 3.3 It does not buy ownership

`sawi` is quieter than `sase`, not stronger. It still lands on a cybersecurity company (`sawi.group`), a 58-year-old
Swiss academy holding the `.com`, an npm squat (an abandoned 2024 `create-next-app` scaffold at v1.1.4), a taken
GitHub user handle, a Brazilian agency, a B2B payments platform, a healthcare app, and a Swiss sensor manufacturer.
Pronunciation is also ambiguous from spelling (SAH-wee / SAW-ee / SAY-wee), so it does not fix the "needs a gloss"
problem — it relocates it.

The **Sawi people of Papua** association (`__b`) is real — Don Richardson's *Peace Child* (1974) documents a culture
whose stated ideal was to "fatten a victim with friendship" before betrayal — and it is unusually on-the-nose for a
trustworthy-agents product. But it is confined to evangelical missions literature and most developers will never meet
it. Rate it a footnote, well below §2.3.

---

## 4. Cost Is Tiered, Not Monolithic

Neither report made this distinction, and it matters for any future rename. The ~59,000 occurrences are not one
undifferentiated wall:

| Tier | Surface | Cost |
| --- | --- | --- |
| **1. Brand** | README, docs, `sase.sh` site, blog, 53 expansion strings, logo | Cheap. Hours. |
| **2. Internal code** | Python/Rust identifiers, imports, 2,720 paths, tests, snapshots | Mechanical, scriptable, one PR. |
| **3. User-visible protocol** | `sase` command, `~/.sase/`, `.sase` files (3,900 refs), 360 `SASE_*` vars, `~/.config/sase/sase.yml`, PyPI, `sase-org`, generated `/sase_*` skills, `AGENTS.md`/`CLAUDE.md` shims, five sibling repos | Expensive. Needs compat aliases, state migration, deprecation shims. |

Tier 3 is the real budget, and it implies something useful: **the tiers can be decoupled.** A public product name does
not have to equal the CLI verb, the package name, or the state directory. Rebranding Tier 1 while leaving `sase` as the
command is a legitimate, much cheaper intermediate move if the collision ever becomes a live problem before you have a
name worth spending Tier 3 on. Neither report considered this option; it partially relaxes the "you only get one
rename" bind.

---

## 5. Calibration: Real Liability, Not an Emergency

Both reports use language like "catastrophic" and "permanent tax." The collision is real and permanent, but the
urgency framing deserves tempering: this is a pre-1.0, single-developer project. Losing a Google ranking contest to
Zscaler's marketing budget costs nothing today, and developer tools are overwhelmingly discovered through GitHub, HN,
social, and word of mouth — channels where an exact repo/org name and a clear one-line description do the work, not
bare-acronym SEO.

So the correct reading is: **the `sase` collision is a genuine liability that will not improve on its own, and the cost
of fixing it only rises — but it is not bleeding right now.** That is an argument for deciding deliberately before 1.0,
not for renaming reactively to the first available alternative. Which is precisely the trap `sawi` represents.

---

## 6. Head-to-Head (Post-Correction)

| Criterion | `sase` | `sawi` |
| --- | --- | --- |
| Major industry-category collision | ❌ Severe ($15–17B, same pronunciation, adjacent field) | ✅ None comparable |
| Other tech collisions | ❌ Multiple (noise) | ⚠️ `sawi.group` (cybersecurity), npm squat |
| Institutional holder | ⚠️ SASE nonprofit (10k members) | ⚠️ SAWI Academy (CH, est. 1968), holds `.com` |
| Search ownability | ❌ Unwinnable | ⚠️ Better, not ownable |
| **`.sh` domain** | ✅ Owns `sase.sh` (but only since 2026-05-06) | ✅ **`sawi.sh` confirmed free** — *a wash* |
| Other TLDs | ❌ All occupied | ❌ All occupied |
| PyPI / crates.io / GitHub org | ✅ Held / free / held | ✅ **All free** (`sawi-org` available) |
| npm | ✅ Free | ❌ Squatted |
| Pronunciation from spelling | ⚠️ Needs a gloss; the gloss collides | ⚠️ Needs a gloss (3+ readings) |
| **Acronym accuracy** | ✅ **Accurate and specific** | ❌ **Vague ("Work"), wrong ("Interface")** |
| Research provenance | ✅ Ties to Hassan et al.; ACE/AXE cohere | ❌ Severed; orphans ACE/AXE |
| Branding hook | ⚠️ None | ⚠️ Mustard — but mistranslated |
| **Cross-language safety** | ✅ Acronym noise only | ❌ **Filipino `sawî` = doomed / failed** |
| Trademark posture | Crowded, weakly ownable | Unverified; not a fresh mark |
| Switching cost | None | ~59,130 occurrences, 80% of files |

`sawi` wins one row decisively (the category collision) and ties the domain row that both reports scored against it.
It loses acronym accuracy, cross-language safety, npm, and provenance. **Net: sideways.** Sideways does not justify
59,000 edits.

---

## 7. If You Do Rename: The Bar, and a Concrete Starting Point

A replacement should clear **all** of these before you spend the switching cost:

1. **No collision with an established IT/enterprise category.** Search the bare term plus "software," "platform," and
   "security." If page one is someone else's category, stop.
2. **A primary domain you can actually buy** — verified at a registrar, not by DNS.
3. **PyPI + crates.io + npm + Homebrew all free.** All four; `sase-core` means crates.io matters.
4. **Unambiguous pronunciation from spelling**, with no common homophone.
5. **Good CLI verb:** short (≤5–6 chars), lowercase, no shift key, comfortable to type dozens of times a day.
6. **Works as a namespace and count noun:** `<name>.sh`, `~/.<name>/`, `<name>_core`, `<NAME>_ENV_VARS`, `.<name>`
   files.
7. **No hostile meaning in a major world language** — the `sawi`/Filipino lesson. Check Tagalog, Indonesian/Malay,
   Spanish, Portuguese, Hindi, and Mandarin transliteration at minimum.
8. **Preserves the ability to say "implements the SASE vision (Hassan et al., 2025)"** in prose — keeping the lineage
   without the name carrying it, so `ACE`/`AXE` retain meaning by explicit reference.

**Illustrative sweep — not a recommendation.** Since the mustard-seed metaphor is the part worth keeping, here is what
the English/botanical direction looks like against criteria 2–3 (checked 2026-07-28; crates.io rate-limited, so that
column is unverified):

| Candidate | PyPI | npm | GitHub user | `.sh` | `.dev` | Note |
| --- | --- | --- | --- | --- | --- | --- |
| `sinapis` | free | free | taken | **free** | **free** | Botanical genus of mustard — literally "mustard," no translation hop |
| `kolza` | free | free | taken | free | free | Rapeseed/Brassica; distinctive, low collision |
| `brassa` | free | free | taken | free | free | Coined, Brassica-adjacent |
| `dijon` | free | taken | taken | free | free | Instantly legible, but heavy place/Grey Poupon associations |

`sinapis` is the interesting one: it delivers the mustard identity you actually want, in a form that needs no gloss in
either direction, and it is clear on every surface checked. It fails criterion 5 on length, though — seven characters
is a lot for a verb typed dozens of times daily, so a short alias would be needed.

Run the full checklist before committing, and do it while the project is still alpha.

---

## 8. Bottom Line

**Do not rename to `sawi`.** You would spend a one-time, ~59,000-occurrence, cross-repo, breaking-change budget to move
from a name with a loud collision to one with a quieter collision, a weaker and less accurate acronym, a squatted npm
package, a pun that breaks in translation, no research lineage, and a meaning of "doomed" in a major regional language.
The domain and namespace arguments that both source reports leaned on turn out to be a wash — which makes the
remaining case narrower but, if anything, clearer: **`sawi` is not better, it is just quieter.**

**Keep treating `sase` as an unresolved liability, not a settled question.** The collision with a multi-billion-dollar
security category — same industry, same pronunciation — is a permanent tax on every introduction. It will not improve
on its own, and it is cheapest to fix now.

**The synthesis: your instinct to rename is right; `sawi` is just not the name.** And if the mustard idea is what you
actually love — the smallest seed becoming the largest plant, one prompt becoming a team of agents — that is a strong
hook worth building on. It argues for an English or botanical mustard name, not for an Indonesian one.

---

## Sources

**`sase` collision**
[Gartner — SASE definition](https://www.gartner.com/en/information-technology/glossary/secure-access-service-edge-sase) ·
[NIST glossary](https://csrc.nist.gov/glossary/term/sase) ·
[Cisco](https://www.cisco.com/site/us/en/learn/topics/security/what-is-secure-access-service-edge-sase.html) ·
[Palo Alto Networks](https://www.paloaltonetworks.com/cyberpedia/what-is-sase) ·
[Zscaler](https://www.zscaler.com/resources/security-terms-glossary/what-is-sase) ·
[Netify vendor comparison](https://www.netify.co.uk/marketplace/sase/) ·
[Society of Asian Scientists and Engineers](https://projects.propublica.org/nonprofits/organizations/261509658) ·
[Society for the Advancement of Socio-Economics](https://sase.org/about/)

**`sawi` usage**
[Agência Sawi — about page (Tupi-Guarani origin)](https://www.agenciasawi.com.br/sobre-nos/) ·
[sawi.com.br](https://www.sawi.com.br/) ·
[sawi.group — cybersecurity](https://sawi.group/) ·
[SAWI Academy](https://www.topuniversities.com/universities/sawi-academy-marketing-communication) ·
[Sawi Mess- und Regeltechnik AG](https://www.sawi.ch/) ·
[sawi.me — B2B payments](https://www.sawi.me/about) ·
[`sawi` on npm](https://www.npmjs.com/package/sawi) ·
[SAWIS trademark, cancelled 2009](https://trademarks.justia.com/760/35/sawis-76035170.html)

**Linguistics**
[KBBI (official Indonesian dictionary) — `sawi`](https://kbbi.kemendikdasmen.go.id/entri/sawi) ·
[Cook Me Indonesian — Asian leafy greens](https://www.cookmeindonesian.com/asian-leafy-greens/) ·
[Glosbe — "mustard" in Indonesian](https://glosbe.com/en/id/mustard) ·
[tagalog.com — root `sawi`](https://www.tagalog.com/dictionary/root-word-sawi) ·
[Diksiyonaryo.ph — `sawî`](https://diksiyonaryo.ph/word/sawi) ·
[Wiktionary — `sawi`](https://en.wiktionary.org/wiki/sawi) ·
[Sawi people](https://en.wikipedia.org/wiki/Sawi_people) ·
[Don Richardson's *Peace Child*](https://lightmagazine.ca/don-carol-richardsons-peace-child/)

**Provenance**
[Hassan et al., arXiv:2509.06216](https://arxiv.org/abs/2509.06216) · `docs/acknowledgements.md` §Research Papers

**Direct verification (2026-07-28):** `.sh` registry whois for `sawi.sh` / `sase.sh`; DNS for
`sawi.{com,dev,io,ai,app,org}`; PyPI, npm, crates.io, and GitHub REST API for `sase` / `sawi` / `sawi-org`;
`git grep` census of this checkout.
