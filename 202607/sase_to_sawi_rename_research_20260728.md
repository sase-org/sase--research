# SASE to SAWI Rename Research

Date: 2026-07-28

## Bottom Line

Do **not** rename SASE to SAWI.

There is a legitimate reason to reconsider the SASE name: the unqualified acronym is overwhelmingly associated with
Secure Access Service Edge, and that collision is getting worse as network-security vendors increasingly use "SASE"
and "agentic AI" together. But SAWI does not clear the bar for a disruptive rename. It is already used by commercially
active companies in digital/AI services, cybersecurity, payments, education, healthcare software, and industrial
sensors. The most concerning collisions are a Brazilian digital-intelligence company launching a proprietary
**SAWI OS** and AI products, and a developer-oriented cybersecurity company branding itself simply **Sawi**.

SAWI also gives up several assets already controlled by this project: the `sase` PyPI package, the `sase-org` GitHub
organization, the `sase.sh` documentation domain, and a name that exactly describes the current product and connects
it to the published concept of Structured Agentic Software Engineering. The mustard-green association is genuinely
fun and brandable, but a mustard bottle is not quite the literal meaning of the Indonesian word, and the same spelling
has strongly negative meanings in Tagalog/Filipino.

The strongest conclusion is therefore not "SASE is a perfect forever name." It is: **if the project needs a broader,
more ownable product name before 1.0, conduct another naming round and choose a genuinely distinctive candidate rather
than SAWI.**

## Scope and Method

This is a preliminary brand and namespace audit, not legal clearance. I:

- Searched exact and contextual uses of `SASE`, `Sase`, `SAWI`, and `Sawi`, emphasizing software, developer tooling,
  AI, cybersecurity, education, and adjacent services.
- Checked first-party company and product sites where possible.
- Checked live DNS for the obvious domains, exact package names on PyPI, npm, crates.io, and Homebrew, and exact GitHub
  handles.
- Performed a preliminary exact-mark search of public U.S. trademark records. A real clearance search would also need
  similar-looking and similar-sounding marks, common-law use, relevant international jurisdictions, and legal review
  in the intended product classes.
- Audited the tracked rename footprint in the main repository and five linked ecosystem repositories.
- Evaluated semantics, pronunciation, visual identity, expansion quality, searchability, and migration cost using my
  own judgment.

The web and namespace observations are a snapshot as of 2026-07-28. Availability can change at any time.

## What Is Wrong With `SASE`?

### The cybersecurity collision is severe

`SASE` is the standard abbreviation for **Secure Access Service Edge**, a cloud-delivered network and security
architecture recognized by [NIST](https://csrc.nist.gov/glossary/term/sase) and marketed extensively by
[Cisco](https://www.cisco.com/site/us/en/learn/topics/security/what-is-secure-access-service-edge-sase.html),
Microsoft, IBM, Cloudflare, Fortinet, Palo Alto Networks, Cato Networks, Zscaler, Check Point, and many others. IBM and
other vendors pronounce it "sassy."

This is not a minor exact-string collision. It is a large enterprise-technology category with:

- Vendor products named "SASE platform," "single-vendor SASE," and "managed SASE."
- Dedicated domains, conference tracks, analyst reports, training, and certification material.
- Strong ownership of unqualified search results for `SASE`.
- An increasingly direct collision with this project's vocabulary. In 2026, Cisco, Palo Alto Networks, Gartner, and
  other security sources are publishing about **SASE for agentic AI**, **agentic SASE**, and securing AI agents with
  SASE. Even the modifier `agentic` no longer cleanly disambiguates the project.

The collision imposes a real tax:

- A person who hears "SASE" without context is likely to infer network security.
- Search queries such as `SASE agent`, `SASE platform`, and `SASE architecture` are contested.
- Press, podcasts, support conversations, and word-of-mouth introductions require a qualifier such as `sase.sh`,
  "the agent orchestrator," or the full expansion.
- The project is unlikely to own the bare acronym in the general technology market.

This is the best argument for renaming.

### `SASE` has many other established meanings

The acronym is also used by:

- The [Society for the Advancement of Socio-Economics](https://sase.org/about/), founded in 1989.
- The Society of Asian Scientists and Engineers, a U.S. professional and student organization founded in 2007.
- SASE Company, an established concrete surface-preparation equipment company using the name since the 1970s.
- The Sarajevo Stock Exchange, self-addressed stamped envelopes, self-amplified spontaneous emission in laser
  physics, and several scientific or engineering organizations.
- A 2006 complex-event-processing research system called SASE.
- A 2024 neural-network attention architecture called SASE.

Most of these are not close enough to cause product confusion, but together they make the acronym noisy and hard to
own.

### One external use is unusually favorable

The 2025 paper
[Agentic Software Engineering: Foundational Pillars and a Research Roadmap](https://arxiv.org/abs/2509.06216)
uses the exact expansion **Structured Agentic Software Engineering (SASE)** for a vision of disciplined, auditable
human-agent collaboration. That is the same conceptual territory and the project explicitly acknowledges the paper's
influence.

This makes SASE more than an arbitrary backronym. It connects the product to a plausible field name:

- "Software engineering" correctly describes the current product's center of gravity.
- The expansion communicates discipline and process rather than one-off agentic coding.
- The project can present itself as an implementation of, or infrastructure for, structured agentic software
  engineering.

That semantic legitimacy is a meaningful asset, even though it does not solve the cybersecurity search collision.

## Existing Commercial Uses of `SAWI`

SAWI is less globally dominated by one meaning than SASE, but it is not commercially clean.

### High-relevance collisions

#### SAWI digital intelligence and SAWI OS

[SAWI in Brazil](https://www.sawi.com.br/) is a digital strategy, marketing, data, and AI company operating since
2008. Its current positioning is "digital intelligence," it describes AI agents as part of its offering, and in 2026
it launched a proprietary platform called **SAWI OS** plus an AI-oriented product line.

This is the strongest conflict found. The company is not an agentic developer-tool orchestrator, but `SAWI OS` is
close in both name and product framing to a broad "work interface" or agent operating environment. It also operates
in software, AI, consulting, and digital infrastructure rather than an unrelated physical-goods category.

#### Sawi, "The Cybersecurity Company"

[sawi.group](https://sawi.group/) brands itself simply **Sawi** and calls itself "The Cybersecurity Company." Its
products include OmniD for identity/password management and ServerShare for managing websites and projects, and its
site explicitly targets developers.

This is smaller than the Secure Access Service Edge category, but it is a direct exact-name use in technology,
security, identity, servers, and developer tooling. Ironically, adopting SAWI would not fully escape a cybersecurity
collision.

#### The exact npm package

The exact [`sawi` npm package](https://www.npmjs.com/package/sawi) exists at version 1.1.4. Its metadata looks like a
generic Next.js scaffold rather than an established product, so it may have little marketplace significance, but it
still blocks a clean exact npm namespace.

### Medium-relevance commercial uses

- [sawi.me](https://www.sawi.me/about) is a B2B payments platform focused on accounts receivable.
- [SAWI Academy](https://sawi.com/) is a Swiss marketing, communication, sales, and multimedia education company. Its
  legal entity and primary `.com` use the exact name.
- [Sawi - For Doctors](https://play.google.com/store/apps/details?id=com.sawi.doctor) is an active healthcare app for
  physician profiles and patient bookings.
- [sawi.io](https://www.sawi.io/) is an active Arabic-language site whose title translates approximately to
  "Sawi ... know what it's worth." Whatever its exact commercial scope, the obvious `.io` is occupied.
- A U.K. company named SAWI LTD was incorporated in 2025, although its listed business activities are wholesale,
  private security, and building cleaning rather than software.

These uses would not necessarily prevent coexistence, but they weaken search isolation and make it harder to present
SAWI as a coined, ownable technology brand.

### Industrial use and registered mark

[Sawi Mess- und Regeltechnik AG](https://www.sawi.ch/) is a Swiss industrial sensor and measurement company. A stylized
SAWI mark is registered in the United States under registration number 5,348,204 for temperature sensors and
controllers, with an international registration history dating to 1996.

That registration does not automatically block a software product; trademark analysis depends on the mark,
jurisdiction, goods/services, channels, and likelihood of confusion. It does mean that SAWI is not a fresh mark, even
in technology-related Class 9 goods.

### Other institutional and technical uses

Lower-risk exact uses include:

- The World Bank's former South Asia Water Initiative (SAWI).
- The `SAWI` ticker used for an iShares MSCI ACWI SRI UCITS ETF in at least one market.
- "Sawi transform," a mathematical integral transform used in published research.
- Sawi peoples, languages, and geographic names in Papua, Afghanistan/Pakistan, and Thailand.

These are mostly search noise rather than commercial conflicts.

## Existing Namespace Audit

### Package and account names

| Namespace | `sase` | `sawi` | Consequence |
| --- | --- | --- | --- |
| PyPI | Owned by this project; version 0.12.0 at audit time | Returned 404 | SAWI could likely be claimed on PyPI, but the existing package identity and history would need migration |
| npm | Exact package returned 404 | Exact package exists at 1.1.4 | SAWI is worse if an npm presence is ever useful |
| crates.io | Exact crate returned 404 | Exact crate returned 404 | Roughly equal; availability still must be reserved |
| Homebrew core | No exact formula | No exact formula | Roughly equal; a tap can avoid dependence on the core formula name |
| GitHub exact handle | `github.com/sase` is the Society of Asian Scientists and Engineers | `github.com/sawi` is an existing user | Neither bare handle is available |
| GitHub project organization | `sase-org` is controlled by this project | `sawi-org` returned 404 | `sawi-org` might be claimable, but a 404 is not proof of availability |

SASE has poor bare-name availability, but the project already assembled a coherent namespace bundle. SAWI offers one
potentially valuable opening—PyPI—while losing npm and both exact GitHub handles.

### Domains

All of the obvious SAWI domains checked had registrations or active DNS:

- `sawi.com` — SAWI Academy.
- `sawi.dev` — registered since 2019.
- `sawi.io` — registered and active.
- `sawi.ai` — registered/parked at audit time.
- `sawi.app` — registered since 2025.
- `sawi.org` — registered/parked.
- `sawi.com.br`, `sawi.ch`, `sawi.me`, and `sawi.group` — active businesses described above.

The obvious SASE domains are also occupied:

- `sase.com`, `sase.dev`, `sase.io`, `sase.ai`, and `sase.org` are all registered.
- `sase.io` is devoted to Secure Access Service Edge.
- `sase.ai` was listed for sale.

The difference is that this project already controls and consistently uses **`sase.sh`**, which is an excellent domain
for a CLI-centered developer tool. No DNS record was found for `sawi.sh`, but that is not a reliable availability
check and should not be treated as a reservation.

SAWI therefore does not deliver the clean domain reset that might justify a rename.

## Linguistic and Cultural Evaluation

### Indonesian: a usable and potentially delightful association

The official Indonesian KBBI dictionary defines
[`sawi`](https://kbbi.kemendikdasmen.go.id/entri/sawi) primarily as a broad-leaved green vegetable, specifically
*Brassica juncea*. In ordinary English, "mustard greens" is more accurate than just "mustard." KBBI also records
secondary meanings for a fishing-boat crew member and the Sawi people of Papua.

The vegetable association has real brand potential:

- It is concrete, friendly, colorful, and much easier to illustrate than an abstract engineering acronym.
- Mustard yellow and leaf green offer a distinctive visual palette.
- A playful mascot could make a serious workflow tool feel approachable.
- "Structured workflows with a little bite" or "cut the mustard" could support memorable copy in English.
- A bottle, leaf, seed, or branching plant can be turned into workflow/agent imagery.

The idea is not inherently disrespectful. It is an everyday food word, and a thoughtful visual identity could treat
the Indonesian meaning as a pleasant multilingual layer rather than a joke at anyone's expense.

There is an important accuracy issue, however: an American yellow-mustard squeeze bottle represents a condiment made
from mustard seeds, while Indonesian `sawi` ordinarily evokes leafy mustard vegetables such as mustard greens, choy
sum, or related cabbages. A bottle logo would be a second-order English pun, not a literal illustration of the word.
That can still work, but it should be intentional. A mustard-green leaf whose veins form a workflow graph would be
more linguistically faithful.

### Filipino/Tagalog: a negative association

In Filipino/Tagalog, the closely matching word `sawî` means unfortunate, unlucky, failed, or dead/killed depending on
context. The [Filipino dictionary entry](https://diksiyonaryo.ph/word/sawi) gives senses corresponding to "failed" and
"dead," and common phrases use it for heartbreak or misfortune.

The pronunciation includes a final glottal stop and is not identical to Indonesian `sawi`, but the difference is
usually not visible in an unaccented Latin wordmark. A product named SAWI would therefore read positively or neutrally
to many Indonesian/Malay speakers and negatively to many Filipino speakers.

This is not a universal veto for a developer tool, but it materially weakens the claim that the multilingual meaning
is an uncomplicated brand advantage. Indonesia and the Philippines are both large, digitally active Southeast Asian
markets.

### English pronunciation and recall

`SASE` has an established pronunciation: "sassy." It is lively, short, and easy to repeat once heard. Its problem is
meaning, not mouthfeel.

`SAWI` could be pronounced "SAH-wee," "SAW-ee," "SAY-wee," or as the individual letters S-A-W-I by an English speaker.
It is still pronounceable, but spelling from audio is less predictable. It is also visually and aurally close to
Sawi, Savi, Savvy, Sawai, and SAI, which creates correction and transcription risk.

SAWI is attractive on the page, but it is not clearly stronger in sayability or recall.

## Does the New Expansion Fit the Product?

### What SAWI improves

**Structured Agentic Work Interface** has two strategic virtues:

1. `Work` is broader than `Software Engineering`. It leaves room for research, communication, operations, personal
   automation, and other agent-driven workflows.
2. `Interface` suggests a human control surface between people, agents, tools, and durable work state. That maps
   reasonably well to ACE and to the project's human-supervision philosophy.

If the committed roadmap is to become a general-purpose operating layer for all knowledge work, the current expansion
could become a constraint. SAWI expresses that ambition better.

### What SAWI makes less accurate

The current product is not merely an interface. It includes:

- Agent process launch, scheduling, monitoring, resumption, and archival.
- Isolated workspace allocation and repository integration.
- ChangeSpec, bead, plan, memory, notification, and artifact state.
- XPrompt templates, directives, workflows, and an LSP.
- ACE and AXE interactive/background runtimes.
- Provider, VCS, workspace, notification, and editor plugins.

"Interface" foregrounds the visible control surface while under-describing the orchestration engine, execution
environment, durable state model, automation daemon, and plugin platform. "Work" is broad but generic. The full phrase
sounds like the name of a UI specification, protocol, or dashboard rather than a complete agentic engineering system.

By contrast, **Structured Agentic Software Engineering** names the practice the product enables. It is more accurate
for the current user, feature set, and public positioning on PyPI: coordinating coding agents to make engineering work
dependable.

There is also a grammatical distinction:

- "Structured Agentic Software Engineering" is a coherent field or method.
- "Structured Agentic Work Interface" is interpretable, but it is unclear whether "structured" modifies the
  interface, agentic work, or both.

SAWI is a plausible backronym, not a notably strong category definition.

## Brand Personality and the Mustard Concept

The mustard idea is the best part of SAWI.

A good identity could use:

- Mustard yellow as a high-energy accent and leaf green for success/state.
- A squeeze path becoming a DAG or agent-family tree.
- A mustard-green leaf with terminal/workflow veins.
- Release names based on greens, seeds, heat, or cultivation.
- Copy around structure, branching, growth, bite, and cutting the mustard.

There are risks:

- A condiment bottle can read as cheap, messy, or jokey, which may fight the product's emphasis on dependable,
  auditable engineering.
- The visual pun needs explanation for most English-speaking users and is slightly inaccurate for Indonesian users.
- Existing SAWI brands already use the word without the vegetable story, so the mascot does not create legal or
  search ownership by itself.
- The negative Filipino meaning makes a Southeast-Asian-language campaign harder to present as universally charming.

This identity could be excellent for a feature codename, release theme, mascot, or internal project even if it is not
strong enough to carry the company/product rename.

## Migration Cost and Timing

The project is still pre-1.0, so **if it will ever rename, doing so soon is better than doing so after a stable release
and broader adoption**. That is the strongest timing argument in favor of acting now.

But this particular system has already made SASE part of its protocol and storage vocabulary, not just its README.
A case-insensitive tracked-file census found:

| Repository | Files containing `sase` | Text occurrences | Tracked pathnames containing `sase` |
| --- | ---: | ---: | ---: |
| Main SASE repository | 4,600 | 58,951 | 2,712 |
| `sase-core` | 130 | 2,537 | 188 |
| `sase-github` | 28 | 784 | 16 |
| `sase-nvim` | 32 | 767 | 21 |
| `sase-telegram` | 53 | 2,611 | 26 |
| Chezmoi/config repository | 153 | 2,445 | 122 |
| **Total** | **4,996** | **68,095** | **3,085** |

This is a deliberately naive substring census, not an estimate of manual edits. Generated files, tests, snapshots, and
documentation inflate it, while user machines, external links, package indexes, cached prompts, and third-party
mentions are outside it. No `sawi` substring was present in the tracked text of these six repositories.

A complete rename would touch at least:

- The `sase` executable and shell completions.
- The Python package/import namespace.
- Rust crate/binding names.
- `SASE_*` environment variables.
- `~/.sase`, `.sase`, project state, cache, artifacts, and workspace paths.
- `.sase` ChangeSpec files and file associations.
- Configuration keys, entry points, plugins, and provider identifiers.
- The GitHub organization and repository family.
- PyPI distributions and install/update behavior.
- Documentation URLs, badges, screenshots, videos, PDFs, and blog posts.
- The mobile/editor/Telegram/GitHub integrations and private user configuration.

A safe migration would require compatibility aliases and readers for old state. The old `sase` command, environment
variables, directories, config keys, and file extensions could not all disappear at once without stranding users and
automation. The marketing rename may be simple; the protocol rename is not.

This cost can be justified for a clearly superior, ownable name. SAWI is not clearly superior or ownable enough.

## Side-by-Side Judgment

| Criterion | SASE | SAWI | Winner |
| --- | --- | --- | --- |
| Fit for the current coding-agent product | Exact field/practice name | Broader, but "interface" under-describes the system | **SASE** |
| Fit for a future general-work platform | Constraining | More expansive | **SAWI** |
| Unqualified web search | Dominated by network security | Less dominated, but still noisy | **SAWI** |
| Search with `agentic` | Increasingly contested by security vendors | Currently much cleaner | **SAWI** |
| Adjacent exact-name companies | Huge category collision, few exact developer-tool companies | Exact AI/digital OS and cybersecurity/developer uses | Neither |
| Package/account ownership | Project owns PyPI, `sase-org`, and established history | PyPI open-looking; npm and bare GitHub handle occupied | **SASE** |
| Domain story | Project owns the excellent `sase.sh`; obvious alternatives occupied | Every obvious checked TLD occupied | **SASE** |
| Pronunciation | Memorable "sassy" | Pronounceable but ambiguous | **SASE** |
| Visual/mascot opportunity | Abstract | Mustard/greens concept is distinctive and fun | **SAWI** |
| Cross-language meaning | Mostly acronym noise | Positive food meaning in Indonesian; negative meaning in Filipino | **SASE** |
| Trademark posture | Crowded and weakly ownable; active unrelated exact mark | Active exact mark plus adjacent common-law commercial uses | Neither |
| Migration cost | None | Very high | **SASE** |

SAWI wins the two things that triggered the idea: it broadens the mission and improves agentic-search isolation. It
loses too many of the things a rename should improve at the same time: commercial uniqueness, namespace ownership,
semantic precision, pronunciation certainty, cross-language safety, and migration economics.

## What Would Change the Decision?

SAWI would become more defensible only if all of the following were true:

1. The non-software roadmap is committed, near-term, and important enough that "Software Engineering" is actively
   misleading.
2. Counsel clears SAWI for the relevant software, SaaS, developer-tool, and education/service classes in the intended
   markets, with particular attention to SAWI OS, sawi.group, SAWI Academy, and the sensor mark.
3. The project secures the PyPI name, a durable primary domain, the GitHub organization, and the other namespaces it
   expects to need before announcing anything.
4. Native Indonesian and Filipino speakers review the name and proposed visual identity.
5. The rename is treated as a compatibility migration, not a global search-and-replace.

Even then, I would compare SAWI against several coined alternatives before committing. A four-letter acronym is only
worth the churn if it buys substantial ownability.

## Sources and Audit References

Key first-party and authoritative sources:

- NIST, [SASE glossary entry](https://csrc.nist.gov/glossary/term/sase).
- Cisco, [What is Secure Access Service Edge?](https://www.cisco.com/site/us/en/learn/topics/security/what-is-secure-access-service-edge-sase.html).
- IBM, [What is SASE?](https://www.ibm.com/think/topics/sase).
- The SASE research paper,
  [Agentic Software Engineering: Foundational Pillars and a Research Roadmap](https://arxiv.org/abs/2509.06216).
- [SASE Company](https://sasecompany.com/).
- [Society for the Advancement of Socio-Economics](https://sase.org/about/).
- [SAWI Brazil](https://www.sawi.com.br/) and its
  [company history](https://www.sawi.com.br/quem-somos).
- [Sawi cybersecurity company](https://sawi.group/).
- [SAWI Academy legal entity](https://sawi.com/mentions-legales/).
- [Sawi B2B payments](https://www.sawi.me/about).
- [SAWI industrial sensors](https://www.sawi.ch/).
- Google Play, [Sawi - For Doctors](https://play.google.com/store/apps/details?id=com.sawi.doctor).
- KBBI, the official Indonesian dictionary,
  [`sawi`](https://kbbi.kemendikdasmen.go.id/entri/sawi).
- Diksiyonaryo.ph, Filipino dictionary,
  [`sawî`](https://diksiyonaryo.ph/word/sawi).
- USPTO-derived public records for
  [SAWI registration 5,348,204](https://trademarks.justia.com/791/97/sawi-79197963.html) and
  [SASE registration 3,105,631](https://trademarks.justia.com/766/12/sase-76612645.html).
- Live package records:
  [`sase` on PyPI](https://pypi.org/project/sase/) and
  [`sawi` on npm](https://www.npmjs.com/package/sawi).

## Recommendation

**Do not go through with the SASE-to-SAWI rename.**

Keep SASE for the moment, preserve the `sase.sh`/PyPI/GitHub namespace bundle, and continue using the full phrase
**Structured Agentic Software Engineering** wherever first-contact ambiguity matters. The cybersecurity collision is
serious enough that a broader product rename remains worth exploring before 1.0, especially if the roadmap is truly
moving beyond software engineering. But SAWI is not the right destination: it is already occupied in adjacent AI and
cybersecurity markets, lacks clean primary domains and npm/GitHub handles, introduces a negative Filipino meaning,
under-describes the product as an "interface," and does not provide enough advantage to justify a 68,000-occurrence
ecosystem migration.

If you rename, choose a more distinctive coined name that can be legally cleared and whose primary domain, package,
organization, and social namespaces can all be reserved before the first public announcement. Keep the mustard concept
as inspiration for a mascot, feature, or release theme if you love it; it is a strong creative idea attached to a weak
rename candidate.
