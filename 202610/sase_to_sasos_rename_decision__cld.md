# Renaming `sase` to `sasos`: Is It Worth It?

> **Research query:** Should "sase" (Structured Agentic Software Engineering) be renamed to "sasos" (Structured
> Agentic Software Operating System)? Use the October 2026 shortlist report for context, do independent research, and
> end with a recommendation (rename or no rename) and its justification.

**Date:** 2026-10-04 · **Researcher:** cld · **Prior research consulted:**
[October shortlist](sase_rename_new_name_shortlist/sase_rename_new_name_shortlist.md) and
[July `sawi` decision](../202607/sawi_rename_decision/sawi_rename_decision.md)

## Bottom line

**Don't rename to `sasos`.** Keep `sase` for now. If you still want to get away from the SASE collision, spend the
rename on a name that passes both gates in the October shortlist, not on a near-variant of the current name. The
"operating system" idea is worth keeping, but as positioning copy, which costs nothing.

Four findings drive this:

1. **It lands on another collision, and that collision is an operating system.** _SASOS_ is the standard
   abbreviation for **Single Address Space Operating System**. It is the top result for a bare search, it has a
   Wikipedia article, and it still appears in current research (a SOSP '25 paper calls Unikraft "a SASOS"). With clean
   contexts, Codex and Claude Sonnet 5.5 both answered "single-address-space OS". No model guessed agents.
2. **It reads as "SASE OS", which leads straight back to networking.** "SASE on a single operating system" is a
   standard SASE sales pitch. Fortinet sells a "single-vendor SASE platform built on a single operating system,
   FortiOS", and Versa's Unified SASE runs on VOS, the Versa Operating System.
3. **"Operating System" overclaims, and the label is crowded and loaded with hype.** AIOS (6.4k★), buildermethods'
   Agent OS (5.5k★, built for Claude Code users), and Microsoft's "agentic OS" backlash all compete for it. The
   expansion "Software Operating System" is redundant, and it drops "Engineering", which is the most accurate word in
   the current name.
4. **It pays the full rename price for partial relief.** It costs about 142k edits in this repo, another 12.7k in
   sase-core, and 703 env-var identifiers. The July `sawi` decision rejected a rename of exactly this shape because it
   _"trades a loud collision for a quiet one without buying ownership."_ `sasos` is a better candidate than `sawi`, but
   it has the same structure.

## What `sasos` gets right (the steelman)

Taken seriously, the proposal has real strengths:

- **It does escape the Gartner category.** `sasos` is not `sase`. "sasos agent" means nothing in networking, while
  "SASE agent" already means the endpoint client.
- **Its handles are better than sase's.** PyPI, npm, crates.io, and `sasos-org` are all free. The `.sh`, `.dev`, `.io`,
  `.ai`, and `.org` domains have no DNS records, and `sasos.com` is parked with a domain marketplace.
- **No agent-tool namesake.** A GitHub search for "sasos" turns up only tiny unrelated repos.
- **It is short and keeps the identity.** At 5 characters, it keeps "Structured Agentic" and the family resemblance.
  "Sassy" becomes "sassy OS".
- **The OS metaphor fits the internals.** sase really is shaped like an OS (see the
  [table below](#the-case-for-the-metaphor)), and the July blog post already calls it "an operating layer" around agent
  CLIs.
- **Its foreign meaning is harmless.** In Hungarian, _sas_ means "eagle", so _sasos_ means roughly "with eagles".
  Unlike `sawi` ("doomed" in Filipino), I found no harmful meaning.

These strengths are why `sasos` deserves a careful answer rather than a quick no. They are not enough, though, for the
reasons below.

## What a rename has to achieve

The October shortlist set the bar. Any new name has to clear it:

1. **Gate 1: no dominant tech owner.** SASE fails this gate.
2. **Gate 2: no namesake among agent tools.**
3. **LLM-prior test:** asking "what is the ___ CLI?" should get a neutral answer, not a confident wrong product.
4. **Meaning:** the name should evoke at least two of these ideas:
   - one human directing many agents
   - structure and durability
   - a neutral layer above the agent CLIs
5. **Length:** up to about 8 characters, with a bonus for shorter names.

The shortlist also gave explicit advice that bears directly on this proposal:

> _"Keep the lineage, but drop the acronym... do not keep the four letters in the branding... Do not invent a new
> acronym either."_ and _"Do not spend the rename on a lateral move."_

`sasos` is a new acronym that keeps three of the four colliding letters. It needs to beat that advice on evidence, not
just on convenience.

## Evidence

### 1. Handles and namesakes: clean

Checked on 2026-10-04 with HTTP status checks against each registry, the `gh` API, and DNS lookups via 1.1.1.1:

| Surface | `sasos` | Notes |
| --- | --- | --- |
| PyPI | **free** (404) | `sasos-cli` and `sasos-ai` are also free |
| npm | **free** | |
| crates.io | **free** | |
| GitHub `sasos` | taken | User account created 2013-05-30 with 0 public repos (dormant) |
| GitHub `sasos-org` | **free** | Matches the current `sase-org` pattern |
| `sasos.sh` / `.dev` / `.io` / `.ai` / `.org` | **NXDOMAIN** | No DNS record, which suggests (but does not prove) they are unregistered |
| `sasos.com` | registered | Afternic nameservers; parked, probably for sale |
| `sasos.net` | registered | |
| Agent-tool namesake | **none** | GitHub repo search for "sasos": 64 hits, the largest with 7★. They include a hobby kernel ("SASos — My first os"), a beauty-products site, and "Smart Agriculture and Sustainability Optimization System". |

**Verdict:** Gate 2 passes cleanly, and the handles are better than sase's.

### 2. Collisions: smaller than SASE, but sitting right where the name points

**SASOS = Single Address Space Operating System.** This is an established systems-research term:

- It was first proposed in the early 1990s, once 64-bit address spaces made it feasible.
- Classic systems include Opal (UW), Mungi (UNSW), Angel, and Sombrero. Dartmouth ran a "SASOS project" from 1993 to
  1996.
- It is still current. The SOSP '25 paper _µFork_ builds on "the Unikraft SASOS" with CHERI.
- A bare search for `sasos` returns Wikipedia, acronym sites, and the Dartmouth project before anything else.

The magnitude is small: it is an academic concept with no commercial owner, so it technically passes Gate 1. But it is
the **dominant meaning** of the exact string, and it sits in the field the new name invokes. A search for "sasos
operating system" lands on it, and systems people, who are over-represented among the HN and lobste.rs readers you
would hope to attract, will read the name that way first.

**"SASE OS": the old collision comes back.** Anyone who already knows the word SASE will split `sasos` into SASE + OS.
That includes every security engineer, and every reader of eight months of sase docs. In networking, "SASE on one
operating system" is a familiar positioning claim:

- **Fortinet:** _"a single-vendor SASE platform built on a single operating system, FortiOS"_, sold alongside a
  _"single agent"_.
- **Versa:** Unified SASE _"running on the Versa Operating System (VOS™)"_.

So the most natural reading of the new name points back at the industry you are trying to leave. One data point
confirms it: Haiku 4.5, run on this machine with your SASE context loaded, guessed that `sasos` was "related to SASE
(Secure Access Service Edge)".

**Background noise:**

- **SASO** is the Saudi Standards, Metrology and Quality Organization, a high-volume compliance term that search
  engines fold "sasos" toward.
- **"SASOs"** is the plural form for Second Amendment Sanctuary Ordinances (US gun politics) and for Ohio's Statewide
  Arts Service Organizations.
- **SASOS** is also a leather-jacket brand.
- **The `SAS` prefix** pulls toward SAS Institute and Azure Shared Access Signatures. Sonnet guessed exactly that.

### 3. The LLM-prior test: a confident wrong product

The shortlist's procedure asks finalists to pass this test. I ran it once per model, from memory, in clean contexts:

- **Codex:** an empty `CODEX_HOME` containing only credentials.
- **Claude:** no setting sources, no tools, no skills, and a generic system prompt.

| Model | "What is SASOS?" | Guess for a dev tool named `sasos` | Same question for `sase` | Same question for `handful` |
| --- | --- | --- | --- | --- |
| Codex CLI (default model) | **Single Address Space Operating System** | A tool "for building, running, or debugging such systems" | Secure Access Service Edge; a tool to "configure, deploy, or test secure access policies" | A CLI that groups "a small set of common developer tasks" |
| Claude Sonnet 5.5 | **Single-address-space OS** ("Opal and Angel") | Tooling for "SAS (Statistical Analysis System)" or "Shared Access Signatures in Azure" | Secure Access Service Edge; a Sass/SCSS tool or network-security config | "Bundles a small set of related utilities" |
| Claude Haiku 4.5 | No reliable knowledge | "Static analysis, security operations, or ... scanning" (speculation) | not run | not run |
| Haiku 4.5, with this machine's user context loaded | n/a | "Related to SASE (Secure Access Service Edge)" | n/a | n/a |

**How to read this:**

- `sasos` swaps one confident wrong product (networking) for a smaller one (OS research), plus a pull toward "SAS".
- `handful`, the shortlist's top pick, gets the neutral answer the procedure asks for.
- No name gets "agents" before it has a body of public material behind it. But only the acronym candidates get a
  confident wrong answer.

This matters more for sase than for most tools. Developers increasingly ask an assistant "what is X?" before they ever
search for it.

### 4. Does "Operating System" describe sase?

#### The case for the metaphor

sase's internals map onto OS concepts unusually well. This mapping comes from the project glossary and decision
records:

| OS concept | sase today |
| --- | --- |
| init / service manager | The **sase service**: a per-machine host registered as a systemd user unit or launchd agent. It starts and restarts service procs in `daemon` or `oneshot` mode under restart policies. |
| Process table | **Procs**: durable records in `~/.sase/procs/procs.jsonl`, with logs, streaming, and kill |
| cron / scheduler | The **sase scheduler**, which runs routines, which run jobs |
| Process isolation | Numbered **workspaces**, one agent per workspace |
| Syscall boundary (user mode vs. kernel mode) | **Host-owned completion**: agents never commit; they submit a declaration, and host finalizers act on it |
| Non-blocking, preemptible tasks | **Single-turn agents.** Gates never block, and continuation is mechanical. |
| Admission control | **Holds** |
| Memory hierarchy | **Core memory**, which is always resident, vs. **reference memory**, which is paged in on demand |

As architecture language, this is earned. It would make a good explainer diagram.

#### The case against putting it in the name

- **It is a literal category error.** sase is a POSIX-only Python CLI and TUI that runs _on_ Linux and macOS.
  Calling it an "OS" invites the "that's not an operating system" reply from exactly the technical audience most likely
  to adopt it.
- **The label is crowded, and it currently signals hype:**
  - **AIOS**, "AI Agent Operating System" (6,447★)
  - **buildermethods/agent-os** (5,467★). It is built around Claude Code, Cursor, and Antigravity, so it targets your
    users.
  - **smartcomputer-ai/agent-os**
  - a 2026 arXiv "Agent Operating System (AOS)" reference architecture
  - Letta and MemGPT's "memory as an OS" framing

  When Windows' president posted in November 2025 that Windows is "evolving into an agentic OS", the backlash was big
  enough that replies were locked. Among developers, "agentic OS" is a skepticism trigger right now.
- **The expansion does not parse.** In "Structured Agentic Software Operating System", every OS is software. So
  "Software" is either redundant, or it means "an OS for agentic software", which is not what sase is. It also drops
  "Engineering", the most accurate word in the current name: sase is built around Patches, review, PRs, CI, and
  workspaces. `SAWI`'s "Work Interface" failed the same way. When the letters are back-filled to keep a sound, the
  sound is doing the deciding.
- **It creates a scope contradiction:**
  - If "OS" is meant to signal growth beyond software engineering (goals, research, mail, listening), then "Software"
    undercuts it.
  - If sase is still a software-engineering system (all three enabled projects are software repos), then "OS"
    overclaims.

### 5. Cost: the full rename price

Measured on 2026-10-04 with `git grep -i sase`:

| Surface | Count |
| --- | ---: |
| sase: tracked files | 13,020 |
| sase: files mentioning `sase` | 10,780 (83%) |
| sase: occurrences of `sase` | 141,905 |
| sase: distinct `SASE_*` identifiers | 703 |
| sase: tracked paths containing `sase` | 5,911 |
| sase: commits in the last 30 days | 2,019 |
| sase-core: files mentioning `sase` / occurrences | 594 / 12,712 |

These counts leave out the five other linked plugin repos, the chezmoi config repo, `~/.sase` state on athena, apollo,
and the Mac, the `sase-org` org, `sase.sh`, the PyPI dist, generated `/sase_*` skills, and the bead-ID prefix.

**`sasos` is not cheaper than any other name:**

- `sase` is not a substring of `sasos`, so every token changes.
- The resemblance helps only people who already know the name, which today means mostly you.
- **It makes the migration harder.** The shortlist's phased plan keeps read-old, write-new fallbacks running for a
  while. During that window, `SASE_HOME` and `SASOS_HOME`, `~/.sase` and `~/.sasos`, and the `sase` and `sasos`
  binaries would sit side by side, differing by two letters. That is easy to mistype and hard to catch in review, and
  `sas<Tab>` would stop completing to a single command.

### 6. Pronunciation

- **There is no settled reading.** It could be SASS-oss, SAH-sohs, SAY-sos, or sa-SOS.
- **The gloss keeps the old defect.** "Sassy OS" preserves the joke, but it also means the name still has to be
  explained, which is the "yes, really" problem again.
- **The embedded "SOS"** reads as a distress call, an odd note for a tool that sells dependability. This is minor.

### 7. Precedent: this is the `sawi` decision again

July's `sawi` proposal had the same shape: keep the `SA` prefix and back-fill a new acronym. It was rejected because:

- the expansion was worse
- the word had a bad meaning
- it _"trades a loud collision for a quiet one without buying ownership"_

`sasos` compares to `sawi` like this:

- **Better:** no bad meaning, and better handles.
- **About the same:** it still trades a loud collision for a quiet one.
- **Worse:** cost. The edit count is 2.4× what it was in July.

## Scorecard

| Criterion | `sase` (stay) | `sasos` | `handful` (shortlist #1, for reference) |
| --- | --- | --- | --- |
| Gate 1: no dominant tech owner | ❌ Gartner category, same spelling and sound | ⚠️ No owner, but SASOS dominates the bare string and the name reads as "SASE OS" | ✅ Generic word, no tech owner |
| Gate 2: no agent-tool namesake | ✅ | ✅ | ✅ |
| LLM prior | ❌ Networking | ❌ OS research or SAS | ✅ Neutral |
| Meaning carried by the word itself | ⚠️ Acronym, needs expansion | ⚠️ Acronym, and the expansion is awkward | ✅ "A handful of agents" |
| Accuracy of the expansion or tagline | ✅ Accurate | ❌ Redundant and overclaims | ✅ Tagline carries it |
| Say and spell on first hearing | ⚠️ Needs the "sassy" gloss | ⚠️ Several readings | ✅ Plain English |
| Length | 4 | 5 | 7 |
| Handles | ✅ Owns PyPI, org, `sase.sh` | ✅ All free; `.com` purchasable | ⚠️ npm taken; `handful-org` free |
| Switching cost | None | Full | Full |
| Continuity | Full | High, but only for existing users | None |

**Net:** `sasos` buys roughly half of what a full rename should buy, at the full price. If you are going to pay full
price, buy the whole fix. If you are not, don't pay at all.

## What would change this recommendation

`sasos` becomes defensible only if **all** of the following turn out true:

1. Saying the name once to 3–5 developers shows they **don't** read it as "SASE OS" or "single address space", and
   that they pronounce it consistently.
2. You conclude the "OS" positioning is where sase is going, and you are willing to defend the claim publicly. Ideally
   you would also fix the expansion; "Software" is the weak word.
3. A knockout trademark search (USPTO and EUIPO, classes 9 and 42) comes back clean. I did not run one.
4. Every shortlist finalist (`handful`, `baste`, `crewrail`) fails its two-week test, and you still want out of SASE.

Even then, compare it head-to-head against _staying_, not against `sase`'s worst case. Its edge would be a smaller
collision and better handles. Its costs would be a weaker expansion and about 155k edits.

## Recommendation: no rename (not to `sasos`)

**Do not open a sase → sasos epic.**

**Justification:**

- A rename this large should be spent once, on a name that removes the problem rather than shrinking it.
- `sasos` removes the Gartner-category collision but replaces it with three smaller ones:
  - an exact-string collision with an established operating-systems term, which is the very field the new name claims
  - a "SASE OS" reading that networking vendors already use
  - a confident wrong answer from LLMs
- It adds a descriptor ("operating system") that overclaims, is crowded, and is currently a hype trigger.
- It breaks the expansion's grammar and accuracy.
- It costs exactly as much as a clean break.
- The project's own July precedent and October guidance both warn against this shape of rename. The evidence above
  confirms those warnings rather than overturning them.

**What to do instead:**

1. **Use the OS idea where it is free.**
   - Describe sase as _"an operating layer for coding agents"_ in the README and blog. The July post already uses
     "operating layer".
   - Turn the OS-concept mapping table into an architecture explainer.

   This gets almost all of the rhetorical value with no migration and no overclaim in the name.
2. **Close the naming question on a clock**, as the shortlist recommended. Either run the 14-day procedure on
   `handful`, `baste`, and `crewrail` now, or record in the decisions memory web that "sase stays; reopen only if
   \<condition\>".
3. **Either way, record that `sasos` was considered and rejected**, with the reason: it collides with SASOS, reads as
   "SASE OS", and its expansion overclaims. That keeps it from coming back as a fifth naming round.

## Method and limits

- **Registries and handles (2026-10-04):**
  - HTTP status checks against the PyPI JSON API, the npm registry, and the crates.io API
  - the GitHub users API and repository search via `gh`
  - DNS `NS` and `A` lookups via 1.1.1.1 for `.sh`, `.dev`, `.io`, `.ai`, `.org`, `.com`, and `.net`
- **Collisions and landscape:** web searches for SASOS, "SASE OS", agent-OS projects, the Windows "agentic OS"
  backlash, and Hungarian _sas_. Star counts come from the GitHub API.
- **LLM priors:** one prompt per model, so this is anecdotal. "Clean context" means no user instructions, skills, or
  tools. The Codex model is the CLI's built-in default with an empty config.
- **Repo measurements:** `git grep` in this workspace's sase checkout and in the linked sase-core checkout only.
- **Not done:**
  - trademark searches
  - WHOIS or pricing for `sasos.com`
  - social-handle checks
  - real developer testing
- NXDOMAIN does not prove a domain is available, and a 404 from a registry grants no rights.

## Sources

**Prior project research:**

- [October 2026 shortlist](sase_rename_new_name_shortlist/sase_rename_new_name_shortlist.md)
- [July 2026 `sawi` decision](../202607/sawi_rename_decision/sawi_rename_decision.md)

**SASOS (single address space OS):**

- [Wikipedia: Single address space operating system](https://en.wikipedia.org/wiki/Single_address_space_operating_system)
- [Acronym Finder: SASOS](https://www.acronymfinder.com/Single-Address-Space-Operating-System-(SASOS).html)
- [Dartmouth SASOS project (1993–1996)](https://www.cs.dartmouth.edu/~dfk/research/project/sasos/index.html)
- [Heiser et al., "The Mungi single-address-space operating system" (1998)](https://onlinelibrary.wiley.com/doi/abs/10.1002/(SICI)1097-024X(19980725)28:9%3C901::AID-SPE181%3E3.0.CO;2-7)
- [µFork: Supporting POSIX fork Within a Single-Address-Space OS (SOSP '25)](https://arxiv.org/pdf/2509.09439)
  and its [ACM DL entry](https://dl.acm.org/doi/10.1145/3731569.3764809)

**"SASE OS" in networking:**

- [Fortinet: unified SASE at scale](https://www.fortinet.com/blog/business-and-technology/unified-sase-at-scale-fortinets-momentum-fueled-by-innovation-and-trust)
- [Fortinet: what differentiates Fortinet Unified SASE](https://www.fortinet.com/blog/business-and-technology/what-differentiates-fortinet-unified-sase-from-other-sase-solutions)
- [Versa VOS datasheet](https://versa-networks.com/documents/datasheets/versa-vos.pdf) and
  [Lumen: SASE with Versa](https://www.lumen.com/en-us/services/sase-versa.html)

**Other "SASO(S)" uses:**

- [Wikipedia: SASO](https://en.wikipedia.org/wiki/SASO)
- [Saudi Standards, Metrology and Quality Organization](https://en.wikipedia.org/wiki/Saudi_Standards,_Metrology_and_Quality_Organization)
- [Statewide Arts Service Organizations grant](https://grantexec.com/grants/8914efc1-7056-4b3e-99a0-7b1dc8acd236)
- [Sasos Collection](https://sasoscollection.com/)
- [Wiktionary: sas (Hungarian "eagle")](https://en.wiktionary.org/wiki/sas)

**The agent-OS landscape:**

- [AIOS: LLM Agent Operating System (arXiv:2403.16971)](https://arxiv.org/abs/2403.16971) and
  [agiresearch/AIOS](https://github.com/agiresearch/AIOS)
- [buildermethods/agent-os](https://github.com/buildermethods/agent-os) and
  [smartcomputer-ai/agent-os](https://github.com/smartcomputer-ai/agent-os)
- [The Agent Operating System (AOS), arXiv:2608.03214](https://arxiv.org/pdf/2608.03214)
- [O'Reilly: The open source agent toolkit in 2026](https://www.oreilly.com/radar/the-open-source-agent-toolkit-in-2026/)
  (Letta's "memory as an OS" framing)
- [Windows Latest: "agentic OS" backlash, replies closed](https://www.windowslatest.com/2025/11/14/windows-11-agentic-os-ai-upgrade-faces-backlash-microsoft-responds-by-closing-replies/)
- [Tom's Hardware: Windows boss responds to backlash](https://www.tomshardware.com/software/windows/windows-boss-posts-lacklustre-response-to-agentic-os-backlash)

**Lineage:**

- [Hassan et al., "Agentic Software Engineering: Foundational Pillars and a Research Roadmap" (arXiv:2509.06216)](https://arxiv.org/abs/2509.06216)

**In-repo:**

- `README.md` (the "pronounced 'sassy'" tagline and the "coordination layer" framing)
- `docs/blog/posts/structured-agentic-software-engineering.md` ("an operating layer around them")
- `docs/acknowledgements.md`
- glossary strands: Proc, Service Proc, Sase Service, Sase Scheduler, Routine, Job, Sase Workspace, Tool Run
