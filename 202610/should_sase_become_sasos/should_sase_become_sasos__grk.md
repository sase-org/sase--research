# Should sase become sasos?

> **Research query:** Help decide whether renaming sase (Structured Agentic Software Engineering) to sasos (Structured Agentic Software Operating System) is a good idea. Recommend rename or no rename, with justification.
>
> **Researcher:** grk (independent swarm member). Date: 2026-10-04.
>
> **Input:** the 2026-10-04 shortlist consolidation at `202610/sase_rename_new_name_shortlist/sase_rename_new_name_shortlist.md`, plus independent registry, DNS, GitHub, web, and in-repo checks. Peer reports from this swarm were not consulted.

## Bottom line

**Do not rename sase to sasos.**

The diagnosis that `sase` is a damaged public name is still right. This particular replacement is the same class of mistake as `sawi`: it spends a one-shot, compounding rename on a name that does not buy ownership. `sasos` keeps the colliding four-letter stem, invents another acronym, and plants the product in the most overcrowded agent-marketing phrase of 2026 ("operating system").

Keep the *operating-layer* metaphor in prose. Put the product identifier somewhere that actually leaves `SAS*` and the acronym form.

If a rename still happens, take `handful`, `baste`, and `crewrail` through the shortlist's two-week live test. `sasos` should not be on that list.

## Recommendation

**No rename to sasos.**

Four facts decide it:

1. **It does not escape the collision you are fleeing.** `sase` → `sasos` is a one-letter insert. Same stem, same sound family, same "sassy" prior. Search, speech, typos, env vars, and tab-complete all stay tangled with Gartner SASE.
2. **It invents a new acronym.** The shortlist's own stopping rule was: keep "structured agentic software engineering" as a lowercase tagline, drop the four letters, and do not mint a replacement acronym. `sasos` does the opposite.
3. **"Software Operating System" is a real metaphor and a bad product name.** The project already calls itself an operating layer. That is accurate. Putting OS in the identifier lands you next to Agno AgentOS, Builder Methods Agent OS, rivet-dev/agentos, Microsoft's "agentic OS" backlash, Slack, Shelf, Make, Rabbit OS3, and a Wikipedia article that already defines SASOS as a kind of kernel.
4. **Clean handles are the trap, not the prize.** PyPI, npm, crates.io, `sasos.sh`, and `sasos-org` are free as of this check. `sawi` was also free. Free namespaces do not justify 100k+ identifier edits when the word itself fails.

The rest of this note is the evidence for those four facts, then a comparison against the shortlist's two gates and against keeping `sase`.

## What this rename is asking

| | Today | Proposed |
| --- | --- | --- |
| Identifier | `sase` | `sasos` |
| Expansion | Structured Agentic Software Engineering | Structured Agentic Software Operating System |
| Length | 4 | 5 |
| Form | Acronym, taught as "sassy" | Acronym, most naturally "sass-oss" / "sassy OS" |
| Edit distance | — | 1 (insert `o`) |

The product is a provider-neutral coordination layer for coding-agent CLIs: isolated workspaces, a TUI, scheduler, Patches, beads, memory, artifacts, and host-owned completion. The README pitch is *"One developer. A team of coding agents. Tracked, reviewable, repeatable work."* The first blog post is titled *"The Missing Operating Layer for Coding Agents."* The June 2026 rename research already described it as a "provider-neutral operating layer."

So the OS metaphor is not a stretch. The question is whether that metaphor should become the product's five-letter name.

## Gate 1: does sasos leave the SASE collision?

No.

### The collision that exists

Gartner coined Secure Access Service Edge in 2019. It is a category, not a company. Cisco's explainer still opens with that definition. The 2026 Gartner Magic Quadrant for SASE Platforms is live (Forest, Lerner, Watts, 28 July 2026). Gartner's own market note in that reprint projects the overall SASE market **over $18 billion in 2026**. Palo Alto, Cisco, Cloudflare, Versa, Netskope, and Zscaler all publish "What is SASE?" pages. The README currently teaches the same pronunciation the security industry uses: **"sassy"**, with the getting-started guide adding *"yes, really."*

That would be survivable if the two fields never shared vocabulary. They now do.

- Palo Alto, 23 March 2026: *"Securing the Era of Agentic AI with Prisma SASE."* Prisma SASE is pitched as the platform "built for the agentic AI era," with agent identities, agent hijacking, and autonomous operations.
- Cisco, 10 February 2026: *"AI-Aware SASE"* with MCP visibility and policy control for agent-to-tool traffic. A later Cisco SASE paper titles a section **"MCP: The Operating System for Agentic AI."**
- Cisco's own SASE explainer now talks about connecting "users, sites, devices, and **agents**."
- PyPI already lists `prisma-sase` (6.8.1b1, "Python3 SDK for the Prisma SASE AppFabric") next to `sase` 0.17.1 ("Structured Agentic Software Engineering").

Searching `sase agent`, `sase cli`, or `sase orchestration` is structurally biased toward the wrong industry, and adding "agentic" no longer disambiguates.

### What one extra letter buys

Levenshtein distance 1 is not a rebrand. It is a typo.

| Surface | What happens under `sasos` |
| --- | --- |
| Speech | "sass-oss", "SAY-soss", or "sassy OS". The last one is the collision you are leaving, plus the Microsoft-poisoned phrase. |
| Search | Prefix match on `sas*`. Autocomplete and "did you mean sase?" will fire both ways. |
| Typing | `sase` / `sasos` mistype into each other. Muscle memory for a 4-letter CLI does not become a 5-letter CLI; it becomes a 4-letter CLI with a trailing `s` you forget. |
| Env vars | `SASE_*` (657 distinct identifiers in this checkout) become `SASOS_*`. Grep, tab-complete, and shell history stay confused for years. |
| Imports | `import sase` → `import sasos`. Every historical snippet, gist, and blog still says `sase`. |
| Beads | Shortlist rule: never rewrite historical bead IDs. You would carry `sase-1eq` forever next to `sasos-…`. |

A rename is supposed to make a stranger's first search land on you. `sasos coding agents` is still a `sas*` query in a world where SASE vendors are publishing agentic-AI pages. You would be asking every new user to hear a word that sounds like the old word, then remember an extra letter.

The July `sawi` decision already named this pattern: *you get roughly one rename, which is exactly why it should not be spent on a lateral move.* `sasos` is more lateral than `sawi`. `sawi` at least left the four letters. `sasos` keeps them and adds a fifth.

## Gate 2: is the new meaning ownable?

Two sub-questions: (a) does any dominant tech owner already have `sasos`? (b) does the *expansion* land in a category someone else owns?

### (a) Exact `sasos` namesakes

There is no coding-agent CLI named `sasos`. That is the one clean finding. The rest of the exact-name picture:

**Single Address Space Operating System.** This is the established CS meaning. Wikipedia's article is titled that way and abbreviated **SASOS**. The Spanish Wikipedia page is simply titled *Sasos*. The research lineage is real: Chase/Levy/Feeley/Lazowska 1994 (TOCS), Heiser et al. on Mungi, NICTA's Iguana, Sombrero at ASU, Opal, Nemesis, IBM i. An LLM asked "what is SASOS?" will, with high probability, retrieve this — not a coding-agent orchestrator. Shipping a product whose expansion is "Software Operating System" into a token that already means "a kind of operating system" is asking models and search engines to confuse two OS concepts.

Other exact or near uses, none dominant in coding agents, all noisy:

| Name | What it is | Risk |
| --- | --- | --- |
| SASOS | South African Surgical Outcomes Study (2014 cohort, still cited) | Medical-search noise |
| SASO | Saudi Standards, Metrology and Quality Organization (`saso.gov.sa`) | Spoken "saso" / "sasos"; certificate/compliance prior |
| SAS | SAS Institute; also Special Air Service, Scandinavian Airlines | `SAS OS` parsing |
| ASOS | UK fashion retailer, live US regs in classes 9 and 42, history of opposing OSOS, ASOPH, ASAS, PSOS, FASOS | One-letter anagram/near-twin; they litigate |
| SOS | Distress signal; `sasos` contains it | Tone, jokes |
| `saso` (npm) | Zero-config bundler, last publish 2022 | Adjacent JS identifier |
| GitHub user `sasos` | Account since 2013-05-30, 0 public repos | Bare username is taken |
| `anandj91/xv6-sasos` | 2017 academic OS repo | Confirms the CS prior |
| `Vulc4n-007/SASOS` | "Smart Agriculture and Sustainability Optimization System" | Hobby expansion collision |

None of these is Gartner-SASE-scale. Together they mean the bare word is not empty. It is an OS-research term with a medical study, a Saudi standards body one letter away, and a fashion giant one transposition away.

**Trademark (unverified knockout).** I did not complete a USPTO TESS or EUIPO eSearch plus search for an exact `SASOS` mark in classes 9 and 42. Treat legal clearance as **not done**. What I did confirm: ASOS plc holds live US registrations including class 9 (downloadable software / apps) and class 42, and has opposed marks as close as **OSOS**. SAS Institute holds `SAS` in software classes. A later knockout search is required before any rename, and `sasos` is a worse candidate to take into that search than a real English word.

### (b) The expansion is already a category

"Agentic operating system" and "Agent OS" are 2026's default pitch, not a blue ocean.

Verified this session:

| Occupant | What they claim | Scale |
| --- | --- | --- |
| [Agno AgentOS](https://docs.agno.com/agent-os/introduction) | "The FastAPI for agents"; production runtime. `pip install agno`. | Active Python agent platform |
| [buildermethods/agent-os](https://github.com/buildermethods/agent-os) | Spec-driven "Agent OS" next to Claude Code / Cursor / Antigravity | **5,467** stars, updated today |
| [rivet-dev/agentos](https://github.com/rivet-dev/agentos) | "Give agents an operating system as a library" | **4,744** stars |
| [nearai/ironclaw](https://github.com/nearai/ironclaw) | "Agent OS focused on privacy, security and extensibility" | **12,638** stars |
| [openagents-org/openagents](https://github.com/openagents-org/openagents) | "The collaboration OS for AI agents" | **4,174** stars |
| PyPI `agentos` 0.2.0 | RL AgentOS CLI (agentos.org), 2022 | Exact PyPI name taken |
| npm `agentos` 0.0.0 | Placeholder, 2025-01-27 | Squatted |
| crates.io `agentos` 0.1.0 | "AI agent library" | Exact crate taken |
| Slack, Shelf, Make, Knowlee, Pancake | Marketing posts titled "What is an Agentic OS?" | Category language |
| Rabbit OS3 | "Standalone agentic operating system", Sep 2026 | Productized |
| Microsoft Windows | "evolving into an agentic OS" (Nov 2025); public backlash; Nadella still calling Copilot a "new OS" in Sep 2026 | The phrase is toxic with power users |
| arXiv 2608.03214 | *The Agent Operating System (AOS)* | Academic claim on the same words |
| arXiv 2606.21129 | *AgenticOS* | Another |

Builder Methods' Agent OS is in the same *spec-driven coding-agent* neighborhood this project occupies. Agno's AgentOS is a Python agent runtime on PyPI. Searching `sasos` will not hit them; searching **"software operating system for agents"** or **"agentic OS CLI"** will. The expansion is the part of the name you say in a README's first paragraph. That paragraph would read as a peer of products that already use those words, some with thousands of GitHub stars.

Microsoft's November 2025 "agentic OS" post is the cultural landmine. Replies were locked. Coverage in The Verge, Windows Central, Tom's Hardware, and TechSpot all ran some version of "nobody wants this." Naming a developer tool "Software Operating System" in 2026 does not make you sound like a kernel author. It makes you sound like the pitch deck every vendor is running.

## Does the expansion describe the product better?

Partly, and that is not enough.

**What is right about "operating system":**

- Scheduler (AXE), process isolation (numbered workspaces), memory, artifacts, permissions, and a syscall-like boundary to provider CLIs are OS jobs.
- The project already uses this language: "operating layer" in the first blog post, "SASE as the operating layer" in the architecture brief, "provider-neutral operating layer" in the June 2026 rename research.
- "Engineering" names the *activity*. "Operating system" names the *substrate*. The product is the substrate. That is a real improvement on "Work Interface" (`sawi`), which was vaguer and less accurate.

**What is wrong:**

- It is still an acronym. People will say `sasos` and never expand it, same as they never say "Structured Agentic Software Engineering" at the keyboard.
- "Software Operating System" is ambiguous English. An OS made of software (all of them are)? An OS for software? An OS that operates software engineering? The Hassan paper's phrase is a methodology. This phrase is a stacked-adjective pile.
- It overclaims. This is a Python host, a Rust core, a TUI, and plugins. It is not a kernel, not a process supervisor for arbitrary programs, and not the thing Brian Chesky is asking for when he says nobody has built an "AI operating system."
- It orphans the paper lineage or splits the brand. Hassan et al., arXiv:2509.06216 (v3 24 Jun 2026), presents **Structured Agentic Software Engineering (SASE)** as a vision with ACE/AEE, BriefingScripts, MRPs, CRPs. The tool borrowed that name. Switching the last word to "Operating System" either (i) pretends the paper said something it did not, or (ii) keeps SASE as the methodology name and sasos as the tool — two permanent names, which the shortlist already rejected because the colliding four letters are the problem.

The shortlist's rule is the right one: keep the methodology as a lowercase tagline, credit Hassan et al. in acknowledgements, and pick a *word* for the tool. `sasos` keeps the colliding letters and changes the wrong half of the phrase.

## Handle check (2026-10-04)

Checked directly. "Free" means HTTP 404 on the exact registry name. Domain status is DNS via 1.1.1.1. NXDOMAIN suggests but does not prove an unregistered name.

| Handle | `sasos` | Notes |
| --- | --- | --- |
| PyPI | **free** (404) | Nearby: `saso` free; `agentos` taken |
| npm | **free** (404) | `saso` taken (bundler 5.0.2, 2019–2022); `agentos` squatted 0.0.0 |
| crates.io | **free** (404) | `agentos` 0.1.0 taken ("AI agent library") |
| GitHub user `sasos` | **taken** (2013, 0 repos) | Cannot have the bare username |
| GitHub `sasos-org` | **free** (404) | Matches the `sase-org` pattern |
| `sasos.sh` | NXDOMAIN | Likely registrable |
| `sasos.dev` | NXDOMAIN | |
| `sasos.io` | NXDOMAIN | |
| `sasos.ai` | NXDOMAIN | |
| `sasos.app` | NXDOMAIN | |
| `sasos.org` | NXDOMAIN | |
| `sasos.com` | **parked** (Afternic ns3/ns4, 13.248.169.48) | For sale, not a product |

This is a better namespace position than `sase` (where `.com/.io/.dev/.ai` are occupied) and comparable to `sawi` in 2026-07, which was also free on PyPI, crates, `sawi-org`, and `sawi.sh`. The `sawi` consolidation explicitly corrected two researchers who over-weighted domains, then still recommended against the rename because the *word* failed. Same shape here. Free `.sh` is a wash against `sase.sh` (registered 2026-05-06, no meaningful SEO). You would be trading a five-month-old domain for a five-letter acronym that still sounds like SASE.

Clearance is perishable. That is an argument for reserving a *good* name the day you decide, not for taking a mediocre name because the form is empty today.

## Cost of spending the rename on this

Independent recount on this checkout (workspace 21, `git ls-files` / `git grep -i sase`):

| Metric | 2026-07-28 (sawi report) | 2026-10-04 (shortlist) | This checkout |
| ---: | ---: | ---: | ---: |
| Tracked files | 5,728 | 12,994 | 13,020 |
| Files mentioning `sase` | 4,610 | 10,762 | 10,780 |
| `sase` grep hits (lines) | 59,130 (occurrences) | 141,784 (occurrences) | 127,373 lines |
| Distinct `SASE_*` | 360 | 703 | 657 (stricter token regex) |
| Paths containing `sase` | 2,720 | 5,908 | 5,911 |

Counts differ by method (word occurrences vs matching lines; identifier regex). The shape does not: the surface has roughly **doubled in two months** and is still growing. These numbers omit sase-core, plugins, chezmoi, `~/.sase` on the machines, the GitHub org, `sase.sh`, and PyPI. The February gai→sase rename touched about 520 files. This one is an epic even with token-aware rewrite tools.

A rename of this size is justified when the new name is *ownable and more accurate*. `sasos` is slightly quieter in exact-word search and slightly longer to type. That is not a 100k-edit delta.

## How sasos scores against the shortlist's own rules

The 2026-10-04 shortlist is the right frame. Applied to `sasos` without taking its candidate ranking as given:

| Shortlist rule | `sasos` |
| --- | --- |
| No dominant tech owner | Fails softly: academic SASOS owns the OS-research meaning; ASOS plc is a litigating near-twin; Gartner SASE still owns the stem |
| No namesake among agent tools | Passes on the exact string; **fails on the expansion** (Agent OS / AgentOS is a crowded adjacent category, including a 5.5k-star spec-driven coding tool) |
| Meaning over length, up to ~8 chars | Length is fine (5). Meaning is a metaphor the README already uses, wrapped in a worse acronym |
| Do not invent a new acronym | **Fails** |
| Do not spend the rename on a lateral move | **Fails** (edit distance 1 from the name you are leaving) |
| Keep the methodology as tagline, drop the four letters | **Fails** (keeps SAS, changes the last word) |
| Do not end up with two permanent names | Risk: SASE-the-paper plus sasos-the-tool |
| CLI you type hundreds of times a day | Slightly worse than `sase`; much worse than a 5-letter real word like `baste` |
| Say-and-spell after one hearing | Ambiguous: SAS-oss vs SAY-soss vs sassy-OS. Repeats the "yes, really" problem |
| Where `sase` itself ranked | Between #3 and #4. Only `handful`, `baste`, and `crewrail` clearly beat it. `sasos` does not |

`stichos` was shortlist #4 in part because it *reads* as "stitch OS." The lead already flagged that as a catch: spelling and sound diverge, the meaning needs a gloss, and it says little about one human directing many agents. `sasos` makes the OS reading official, keeps the pronunciation problem, and adds the SASE stem. It is a worse `stichos`, not a better `sase`.

## Where keeping sase still wins, and where it does not

Keeping `sase` is not a free lunch. The public collision is real, compounding, and now entangled with "agentic" on the security side. Inside the coding-agent niche the identifier is unique. Contextual searches (`sase coding agents Claude Code`, `sase.sh`) already surface the repo. Legal risk against Gartner-category SASE is low because it is a generic industry term. Stars are still small, so outside equity to lose is small. The cost of a wrong rename is large and rising.

The shortlist's resolution still holds: **keeping sase beats a lateral move**, and a keep decision should be recorded with a reopen condition rather than left as an open question. This would be the fifth naming round in eight months (gai→sase in February, Specyard/PatchTower in June, sawi in July, the October shortlist, now sasos). The missing piece of the plan is a stopping rule, not another acronym.

If the audience is mostly you, the epic's benefit is small. If the audience is adoption — public docs, PyPI, plugin ecosystem, `sase.sh` — the collision is a permanent tax, and the right response is a name that a stranger can search. `sasos` is not that name.

## What to do instead

1. **Do not rename to sasos.** Record it. Reopen only if a candidate survives the two gates *and* is not an acronym that still starts with `sas`.
2. **Keep "operating layer" in the tagline.** "The operating layer for a handful of coding agents" is accurate, already in the docs, and does not require a product called an OS.
3. **If the rename epic opens, it should open on the shortlist finalists**, not on a newly minted acronym. Live with `handful` / `baste` / `crewrail` for two weeks. Reserve cheap handles the day a finalist is chosen. Knockout-search trademarks in classes 9 and 42. Flip user-visible identity in one release; migrate internals behind fallbacks; never rewrite historical bead IDs.
4. **Stop teaching "sassy"** even if `sase` stays. That pronunciation is how the networking category is said. Spell it, or say the letters.
5. **Do not bifurcate.** One public name. Methodology credit belongs in acknowledgements.

## Method and limits

Independent research, 2026-10-04. Required input was `sase_rename_new_name_shortlist.md`. Also used the June 2026 consolidated rename research, the July `sawi` decision, this checkout's README and first blog post, and live checks listed below. Other researchers in this swarm were not read.

**Checked directly:**

- PyPI JSON API: `sasos` 404; `saso` 404; `sase` 0.17.1; `prisma-sase` 6.8.1b1; `agentos` 0.2.0
- npm registry: `sasos` 404; `saso` 5.0.2; `agentos` 0.0.0
- crates.io API (with UA): `sasos` 404; `agentos` 0.1.0; `aos` 0.0.0
- GitHub users API: `sasos` exists (2013, 0 repos); `sasos-org` 404
- GitHub repo search: `sasos`, `AgentOS in:name`, `agent-os`
- DNS via 1.1.1.1: `sasos.{sh,dev,io,ai,app,org}` NXDOMAIN; `sasos.com` Afternic; `sase.sh` live
- In-repo: `git ls-files` / `git grep -i sase` on this workspace clone
- Web: Wikipedia SASOS, Cisco SASE explainer, Cisco 2026-02-10 AI-Aware SASE release, Palo Alto 2026-03-23 Prisma SASE agentic post, Gartner MQ reprint market note, Hassan arXiv:2509.06216, Agno AgentOS docs, Microsoft agentic-OS coverage, ASOS TTAB oppositions

**Not done:** USPTO TESS / EUIPO knockout for exact `SASOS` in 9 and 42; registrar WHOIS / pricing; social handles; live user testing; LLM-prior testing ("what is the sasos CLI?"). NXDOMAIN is not a registration guarantee. A 404 is not a right to the name.

## Sources

**Project and prior research**

- `202610/sase_rename_new_name_shortlist/sase_rename_new_name_shortlist.md`
- `202606/sase_rename_research_consolidated.md`
- `202607/sawi_rename_decision/sawi_rename_decision.md`
- `README.md` (pronunciation "sassy"; pitch)
- `docs/blog/posts/why-coding-agents-need-orchestration.md` ("The Missing Operating Layer for Coding Agents")

**The SASE collision**

- [Cisco: What is SASE](https://www.cisco.com/site/us/en/learn/topics/security/what-is-secure-access-service-edge-sase.html)
- [Cisco, 10 Feb 2026: AI Defense expansion and AI-Aware SASE](https://newsroom.cisco.com/c/r/newsroom/en/us/a/y2026/m02/cisco-redefines-security-for-the-agentic-era.html)
- [Cisco: Securing the Agentic Frontier](https://www.cisco.com/c/en/us/products/collateral/security/secure-access/securing-the-agentic-frontier.html) ("MCP: The Operating System for Agentic AI")
- [Palo Alto, 23 Mar 2026: Agentic AI with Prisma SASE](https://www.paloaltonetworks.com/blog/2026/03/agentic-ai-with-prisma-sase/)
- Gartner, Magic Quadrant for SASE Platforms, 28 July 2026 (Forest, Lerner, Watts); reprint note: overall SASE market projected over $18B in 2026
- [Hassan et al., arXiv:2509.06216](https://arxiv.org/abs/2509.06216)
- PyPI: [sase](https://pypi.org/project/sase/), [prisma-sase](https://pypi.org/project/prisma-sase/)

**SASOS / near-twins**

- [Wikipedia: Single address space operating system](https://en.wikipedia.org/wiki/Single_address_space_operating_system)
- [Acronym Finder: SASOS](https://www.acronymfinder.com/Single-Address-Space-Operating-System-(SASOS).html)
- Saudi SASO: saso.gov.sa
- ASOS plc TTAB oppositions of OSOS, ASOPH, ASAS, PSOS (USPTO TTABVUE)
- GitHub: [sasos](https://github.com/sasos), [anandj91/xv6-sasos](https://github.com/anandj91/xv6-sasos)

**"Agent OS" occupants**

- [Agno: What is AgentOS?](https://docs.agno.com/agent-os/introduction)
- [buildermethods/agent-os](https://github.com/buildermethods/agent-os) (5,467 stars)
- [rivet-dev/agentos](https://github.com/rivet-dev/agentos) (4,744)
- [nearai/ironclaw](https://github.com/nearai/ironclaw) (12,638)
- [openagents-org/openagents](https://github.com/openagents-org/openagents) (4,174)
- PyPI / npm / crates `agentos`
- [The Verge, 20 Nov 2025: Microsoft agentic OS backlash](https://www.theverge.com/tech/825022/microsoft-windows-40-year-anniversary-agentic-os-future)
- [Shelf: Agentic OS](https://shelf.io/agentic-os/), [Make: What is an Agentic Operating System?](https://www.make.com/en/blog/agentic-operating-system), [Slack: What is an Agentic OS?](https://slack.com/blog/productivity/what-is-an-agentic-os)
- [arXiv:2608.03214 AOS](https://arxiv.org/abs/2608.03214), [arXiv:2606.21129 AgenticOS](https://arxiv.org/html/2606.21129v1)

**Registries and DNS**

- PyPI, npm, crates.io JSON APIs, 2026-10-04
- `dig` against 1.1.1.1 for `sasos.{sh,dev,com,io,ai,app,org}`
