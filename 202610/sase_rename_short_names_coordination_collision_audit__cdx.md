# Renaming SASE: short names for durable coding-agent coordination

Researcher: **cdx**  
Research date: **2026-10-04**  
Scope: independent naming research, public collision screening, and critique of the rename decision. No other report or researcher findings from this swarm were consulted.

**Recommendation: move forward with choosing a new public name while SASE is still alpha. My leading candidate is Crewrail; Runclasp is the strongest alternative, particularly if a matching .com matters.** Choose the brand before undertaking an internal namespace migration. The ranked ten-name shortlist and final recommendation appear at the end.

## What the name needs to communicate

The current checkout describes SASE as a coordination layer: one developer supervises multiple coding agents, each works in an isolated workspace, and prompts, changes, reviews, goals, tool runs, and artifacts survive individual chats. The architecture explicitly keeps work state outside any one transcript. That combination is more specific than “an AI coding tool.” The useful naming territory is **a dependable working system around coding agents**.

The product’s strongest promise is that agent work becomes supervised, persistent, inspectable engineering work. A name can suggest teamwork, guided execution, or the joining of separate contributions. It should accommodate research agents and reusable workflows as well as code changes; a name restricted to generating code, creating PRs, or managing terminal windows would undersell the product.

Product grounding came from this workspace’s README.md and docs/architecture.md, plus audited reads of the artifact, agent, macro, goal, and Patch memory definitions. Public equivalents are the [SASE documentation](https://sase.sh/) and [architecture documentation](https://sase.sh/architecture/). The README identifies the product as alpha; that supports renaming sooner, but does not establish how many users would be affected.

A useful descriptor for any chosen name would be:

> Coordinate coding agents. Keep the work reviewable.

For initial announcements, “Crewrail — formerly SASE” or “Runclasp — formerly SASE” would preserve the connection. “Structured Agentic Software Engineering” can remain a description of the approach without being the product’s acronym.

## Is renaming a good idea?

### The existing collision is substantial

Secure Access Service Edge is an established networking and security **category**, rather than just one unrelated project. Cisco describes it as the convergence of networking and security delivered through a cloud architecture and says Gartner introduced the term in 2019. That is a much broader naming competitor than a small repository. [Cisco’s SASE explanation](https://www.cisco.com/site/us/en/learn/topics/security/what-is-secure-access-service-edge-sase.html)

The pronunciation also collides. SASE’s README says “sassy”; Cisco Umbrella uses the same pronunciation for Secure Access Service Edge. Lowercasing the software name or explaining its different acronym expansion does not fix spoken discovery. [Cisco Umbrella’s definition and pronunciation](https://umbrella.cisco.com/secure-access-service-edge-sase/what-is-sase)

My inference is that the existing name makes introductions and unqualified searches harder: a prospective user may assume a security product or need additional words to locate the software. I did not measure search impressions, acquisition conversion, ranking positions, or the financial value of this friction. The evidence establishes a strong category collision, not a numerical return on renaming.

### The case for doing it now

The product is still alpha, and its public promise is already clear enough to name. Renaming before more integrations, tutorials, plugin packages, and user scripts accumulate should reduce the eventual transition burden. This is a timing judgment, not an assumption that the current user base is small.

A distinctive public identity also gives the project room to communicate supervision and durable work without competing with security vendors for the same four letters. The current acronym accurately describes a methodology, but it is a weak identifier for this particular product.

If the project were destined to remain private personal infrastructure, I would place much less value on a rename. For a publicly distributed developer product, I favor it.

### The critique: a new name can recreate the same problem

Many intuitive candidates are already occupied by adjacent agent products. “Loom,” “weft,” “crew,” “harness,” and “conductor” metaphors are attractive because they fit; other builders are reaching for them too. Swapping SASE for another crowded name would incur migration cost without improving identity.

The eight-character preference is sensible for a frequent CLI command, but it should not become the entire strategy. A distinctive seven- or eight-letter compound can work better than a generic four-letter word. Shell completion and an optional personal alias make the extra keystrokes less consequential than pronunciation, recall, and search confusion.

The project should not force the new name into another elaborate acronym. A pronounceable brand plus a clear descriptor is enough. Similarly, names built around “swarm” risk emphasizing agent quantity over engineering accountability, while names built around “proof” can imply guarantees the product does not establish.

### The migration is larger than a logo edit

A read-only inventory of this checkout found **10,670 tracked text files mentioning “sase”**, excluding canonical memory files and the root AGENTS.md. Of these, 4,856 were under src/, 5,608 under tests/, and 92 under docs/. This was a case-insensitive filename count from git grep; it includes ordinary imports and test references. It is **not** the number of files that must change in a public rebrand and does not include every linked repository.

The important cost areas are the executable, package distribution, documentation domain, plugin prefixes, configuration and state locations, environment variables, generated agent instructions, and integrations. Historical references, durable artifact identities, and the Rust/Python boundary add compatibility considerations.

My preferred scope is a public brand and command transition with compatibility for existing users. Keeping the established Python module or state directory initially could be a sensible engineering choice. The discovery problem lives in the public identity; changing every historical string immediately would not improve that identity.

Preserve old commands and documentation links during a defined transition, and make the old command an alias to the same implementation. Avoid separate old/new state stores that split a user’s history. This is a migration consideration, not a request to implement a rename in this research turn.

A domain move has real operational consequences. Google recommends mapping old URLs to corresponding new URLs, using redirects, and separating a domain move from simultaneous unrelated site changes. [Google Search Central’s site-move guidance](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes)

## How I evaluated names

I considered short natural words, compounds, and coined names, then screened attractive candidates against current public uses. The decision priorities were:

1. **Product fit:** coordinated agents, human supervision, durable work, reusable execution.
2. **Distinctiveness in developer and agent software:** an exact adjacent product is a strong rejection signal.
3. **Speech and recall:** someone should have a reasonable chance of writing the name after hearing it.
4. **CLI and ecosystem usability:** lowercase letters, an ordinary command shape, and workable package/plugin forms.
5. **Room to grow:** remain appropriate for research, scheduling, reviews, and future interfaces.
6. **Length:** all final candidates are at most eight characters; shorter names receive a modest preference.

I used qualitative ranking rather than numerical scores that would imply measured brand performance. The top two are substantially stronger recommendations than the last few entries. Ten candidates are a decision set, not ten equally good launch choices.

The research combined official product websites, package-registry requests, GitHub repository metadata searches, and local inspection of selected public repositories. Repository files were inspected only after opening those repositories through sase repo open. Broad web searches sometimes failed to reveal exact software uses that repository searches subsequently found; neither kind of negative result is clearance.

## Attractive names I would reject or deprioritize

These findings are about public identity and practical confusion, not determinations of trademark rights. A small or unfinished project can still be a poor name to copy, and an existing repository name alone does not establish an enforceable mark.

| Candidate | Why it was appealing | Finding and decision |
| --- | --- | --- |
| **Warp** (4) | Fast, terminal-oriented work; textile metaphor | Already an agent development environment with third-party coding-agent support. Reject. [Warp documentation](https://docs.warp.dev/agents/) |
| **Weft** (4) | Separate threads woven into a whole | Already a desktop agent environment for Claude Code, Codex, and OpenCode, using isolated worktrees. This is especially close to SASE. Reject. [weft](https://www.weft.im/) |
| **Maestro** (7) | One human conducting several agents | Multiple adjacent products use it; one explicitly presents roles, review gates, persistent artifacts, and human approval. Reject. [Maestro](https://www.maestrodev.ai/) |
| **Taskloom** (8) | Work being woven together | Already a board that AI coding agents update. Reject. [TaskLoom](https://www.taskloom.app/) |
| **Heddle** (6) | A loom component that selects and organizes threads | Already used for a declarative agent runtime and versioned records of agent work. Reject. [heddle runtime](https://heddle.run/), [Heddle records](https://heddle.sh/) |
| **Selvage** (7) | The edge that keeps woven material from unraveling | Already an engineering harness for coding agents. Reject. [Selvage](https://selvage.run/) |
| **Crewhelm** (8) | Steering an agent team | Already an open-source agent control plane with grants, approvals, budgets, and audit trails. Reject. [Crewhelm](https://crewhelm.app/) |
| **Crewlet** (7) | A compact crew of agents | Already an engine for organized AI-agent companies, also published on PyPI. Reject. [Crewlet](https://crewlet.com/), [PyPI](https://pypi.org/project/crewlet/) |
| **Crewrig** (7) | A working rig around an agent team | Already a shared configuration layer for coding agents. Reject despite strong conceptual fit. [CrewRig](https://crewrig.org/) |
| **Runyard** (7) | A place where separate runs work together | Already an agent-swarm orchestration product that advertises code shipping, shared memory, and approvals. Reject. [Runyard](https://runyard.io/) |
| **Runweft** (7) | Weaving durable agent runs | An exact-name public scaffold proposes a local agent runtime with durable runs and artifact-bound verification. Its README is clear that it is a scaffold, not a functioning runtime. Still too close for a rename intended to improve identity. [Reviewed README](https://github.com/1deat0r/runweft/blob/3b0c1c0a8ee5cb107b85ea8e24332fa00d1322ba/README.md) |
| **Runlace** (7) | Joining runs into reusable work | One exact-name project is an MCP workflow system; another reviews local agent traces. Both are adjacent. Reject. [Workflow README](https://github.com/cycle-inc/Runlace/blob/272c6083250b2efb8ad2624cdd86e047e43a1cf3/README.md), [Trace-review README](https://github.com/mikebfox/runlace/blob/0f21b88edb0141f818908c4f9a85e028685bfc7a/README.md) |
| **Weftwise** (8) | Woven knowledge and deliberate work | Exact-name AI knowledge-management and desktop projects already exist. Reject. [Knowledge-management README](https://github.com/Nick-Hopps/weftwise/blob/66ddd8eac4df97d945dd0d11d9e27473b42e53cf/README.md), [Desktop README](https://github.com/ghreprimand/weftwise/blob/41473fbfb6312b46b2e7c52b46513d6d4b008a9b/README.md) |
| **Taskweft** (8) | Structured tasks woven into plans | Already an MCP-accessible planning package. Reject. [Hex package](https://hex.pm/packages/taskweft) |
| **Taskhelm** (8) | Steering tasks and maintaining direction | Already an AI project/task manager and an older Python task manager. Reject. [TaskHelm](https://taskhelm.com/), [PyPI](https://pypi.org/project/taskhelm/) |
| **Taskrail** (8) | Guided, observable execution | Already used for an agent execution product and an agent research service. Reject. [Paracosm Lab](https://www.paracosmlab.com/), [TaskRail service](https://taskrail.alamavar.com/) |
| **Bridle / Reins / Belay** (6 / 5 / 5) | Human control and dependable execution | All have nearby coding-agent uses. Reject this tempting cluster. [Bridle](https://bridle.io/solutions/developers), [reins](https://reins.tech/docs/), [Belay](https://belay.secblok.io/doc/) |
| **Runkeep** (7) | Retaining a durable history of runs | Exact-name Python package already exists. Reject. [PyPI](https://pypi.org/project/runkeep/) |
| **Trouply** (7) | A group working together | Its spoken form is close to Trooply, an existing AI-product brand. Deprioritize rather than “fix” the collision through spelling. [Trooply](https://trooply.ai/) |
| **Turnloom** (8) | Durable turns woven into workflows | Already a cleaning and hosting operations platform. Deprioritize. [Turnloom](https://turnloom.com/) |

**Two broader cautions apply to the final shortlist.** “Crew” is already associated with multi-agent software through CrewAI; a new compound should be presented as an independent product, with a coding-agent coordination descriptor. “Weft” is occupied by a very close product, so a new suffix or prefix should not be treated as automatically sufficient differentiation. [CrewAI’s product page](https://crewai.com/agent-management-platform), [weft’s product page](https://www.weft.im/)

Those cautions explain why Crewrail ranks above Crewweft, and why none of the weaving names is an unconditional launch recommendation. I also deprioritized Weftops: it is compact, but puts the already-occupied “Weft” identity first and can sound like an extension of that product.

## Preliminary screen of the final ten

### Package and repository observations

At **2026-10-04 14:09 UTC**, direct requests to the exact unscoped package endpoints returned HTTP 404 for all ten candidates on PyPI, npm, and crates.io. The endpoints were:

- PyPI: https://pypi.org/pypi/NAME/json
- npm: https://registry.npmjs.org/NAME
- crates.io: https://crates.io/api/v1/crates/NAME

GitHub searches used NAME in:name, with results examined for an exact case-insensitive repository name. All ten had no exact-name repository returned. The runrill search returned three CalRunrilla repositories; those are substring matches, not exact runrill names.

| Name | Characters | PyPI exact endpoint | npm exact endpoint | crates.io exact endpoint | Exact GitHub repo returned |
| --- | ---: | --- | --- | --- | --- |
| crewrail | 8 | 404 | 404 | 404 | None |
| runclasp | 8 | 404 | 404 | 404 | None |
| runspur | 7 | 404 | 404 | 404 | None |
| crewrill | 8 | 404 | 404 | 404 | None |
| turnweft | 8 | 404 | 404 | 404 | None |
| runplait | 8 | 404 | 404 | 404 | None |
| runrill | 7 | 404 | 404 | 404 | None |
| crewweft | 8 | 404 | 404 | 404 | None |
| runlark | 7 | 404 | 404 | 404 | None |
| synweft | 7 | 404 | 404 | 404 | None |

These observations mean **no package object or exact repository was found through those checks at that time**. They do not establish registration eligibility, ownership, exclusive use, or the absence of unpublished or unindexed projects. No package or domain was reserved.

For a reproducible example, the checks for the two strongest candidates are the [Crewrail PyPI endpoint](https://pypi.org/pypi/crewrail/json), [Crewrail npm endpoint](https://registry.npmjs.org/crewrail), [Crewrail crates.io endpoint](https://crates.io/api/v1/crates/crewrail), [Runclasp PyPI endpoint](https://pypi.org/pypi/runclasp/json), [Runclasp npm endpoint](https://registry.npmjs.org/runclasp), and [Runclasp crates.io endpoint](https://crates.io/api/v1/crates/runclasp). A later result can differ from this snapshot.

### Domain observations for the leading names

At **2026-10-04 14:10 UTC**, I queried registry RDAP endpoints selected through [IANA’s DNS bootstrap data](https://data.iana.org/rdap/dns.json).

| Candidate | .com RDAP result | .dev RDAP result | Practical implication |
| --- | --- | --- | --- |
| Crewrail | 200: registered March 1, 2026 | 404: no registration object | Matching .com is held by someone else; .dev needs a registrar check |
| Runclasp | 404: no registration object | 404: no registration object | Better preliminary exact-domain position |
| Runspur | 404: no registration object | 404: no registration object | Promising domain position, subject to the identity caveat below |

Sources: [Crewrail .com](https://rdap.verisign.com/com/v1/domain/crewrail.com), [Crewrail .dev](https://pubapi.registry.google/rdap/domain/crewrail.dev), [Runclasp .com](https://rdap.verisign.com/com/v1/domain/runclasp.com), [Runclasp .dev](https://pubapi.registry.google/rdap/domain/runclasp.dev), [Runspur .com](https://rdap.verisign.com/com/v1/domain/runspur.com), [Runspur .dev](https://pubapi.registry.google/rdap/domain/runspur.dev).

A direct read of [www.crewrail.com](https://www.crewrail.com/) returned a Namecheap parking page. That does not establish whether the registrant will sell or at what price. No .sh registration status was established: the IANA bootstrap response did not provide a .sh endpoint. A 404 RDAP response is not a promise that a registrar will offer the domain at an ordinary price.

Runspur also appeared in indexed Behance portfolio listings as a running-tracker design title. I could not validate a direct project page or whether it became a commercial product. Treat this as **an unresolved exact-name prior-use lead**, not a confirmed competing company and not a clean-name result. The general word “run” can also steer people toward fitness interpretations; the tagline should explicitly say coding agents.

Runlark has an indexed racehorse use. Runrill has surname and historical pottery-related results. Synweft had an isolated textile-trade description. These are reasons not to claim universal uniqueness; no corresponding agent-software brand was identified in this screen. The latter two are noisy search leads rather than confirmed product uses. [Runlark racehorse record](https://www.pedigreequery.com/runlark), [collector newsletter](https://redwingcollectors.org/wp-content/uploads/08-1998.pdf), [textile-trade listing](https://www.volza.com/p/protective-mask/export/export-from-china/hsn-code-63079010/)

## What would settle the choice

The next decision should compare **Crewrail and Runclasp**, with Runspur and Crewrill as secondary options. Test each in ordinary speech and actual product language:

- “I use Crewrail to coordinate my coding agents.”
- “Runclasp keeps the work reviewable across agent runs.”
- “Open the Crewrail dashboard.”
- “Install the Runclasp GitHub plugin.”
- Command shapes such as crewrail run, crewrail tui, runclasp run, and runclasp doctor.

These are hypothetical examples, not commands implemented by this research.

A small practical test is more useful than more word generation: give several developers the same short product description, say a name once, and later ask them to recall, spell, and explain what they think it does. Include people unfamiliar with SASE. Compare the interpretation before and after showing the descriptor. This report does not contain user-test results.

For the finalists, verify exact and similar marks in relevant markets, active developer-tool uses, package eligibility, domain purchase conditions, and matching organization/account identities. Identity risk is broader than an identical spelling. The USPTO explains that similarity can involve sound, appearance, meaning, and commercial impression, together with related goods or services. [USPTO likelihood-of-confusion guidance](https://www.uspto.gov/trademarks/search/likelihood-confusion)

The USPTO distinguishes suggestive, arbitrary, and coined identifiers from merely descriptive or generic terms. That supports choosing a distinctive product identifier and explaining the function in a subtitle. It does not establish that any candidate here is legally registrable. [USPTO guidance on strong trademarks](https://www.uspto.gov/trademarks/basics/strong-trademarks)

If a finalist reveals an exact adjacent agent product, discard it. If it needs an expensive domain acquisition to feel viable, compare that cost against the next candidate rather than treating .com ownership as mandatory for an open-source CLI. Do not invent a spelling variant solely to avoid a search result.

## Final ranked list: the ten names I would consider

1. **Crewrail — 8 characters; “CREW-rail.”**  
   **Best overall product fit.** The crew is the agent team; the rail suggests guided movement, structure, and a route to completion. It expresses the coordinating layer clearly and has straightforward spelling and pronunciation. It also works for research and recurring operations. The main drawbacks are the occupied .com and possible perceived association with CrewAI or workforce-dispatch software. No exact agent product surfaced in the searches conducted. **My first choice for a public identity if the similarity and domain checks are satisfactory.**

2. **Runclasp — 8 characters; “RUN-clasp.”**  
   **Best alternative and strongest preliminary domain position.** A clasp joins and holds things together: runs, handoffs, evidence, and review belong to a persistent whole. It gives a compact, tangible metaphor for the part SASE supplies around disposable agent turns. Ordinary spelling and a clear CLI prefix help. The weakness is that joining and retaining work is less immediately obvious than Crewrail’s teamwork metaphor. Generic runClasp function names appeared in searches; no exact product or repository was found. [Example archived development message](https://sourceforge.net/p/dlvhex/mailman/message/28810719/) **I would choose this over Crewrail if exact .com ownership is a firm preference.**

3. **Runspur — 7 characters; “RUN-spur.”**  
   **Best compact execution name.** A spur prompts forward movement; run anchors it in a developer workflow. It is short, energetic, and easy to say. It covers agents and scheduled work without binding the product to a model or UI. It says less about durable evidence, and there is an unresolved running-tracker portfolio use to investigate. **A serious candidate, with a weaker preliminary identity screen than the first two.**

4. **Crewrill — 8 characters; “CREW-rill.”**  
   **Best alternative team metaphor.** A rill is a small stream: several agents contribute streams of work that a developer coordinates. It is distinctive as a whole and can cover parallel work, continuity, and research. It needs a descriptor because many people will not know “rill,” and the double r at the word boundary makes spelling slightly less effortless. **Worth testing if you want the team signal without a rail or transport image.**

5. **Turnweft — 8 characters; “TURN-weft.”**  
   **Best expression of SASE’s durable handoff architecture.** Separate agent, monitor, and human turns are woven into a continuing workflow. That is an unusually close conceptual match. The weakness is that “turn” is architecture vocabulary rather than the user’s primary desired outcome, and Weft is already an adjacent product. **A thoughtful technical brand, conditional on resolving the Weft similarity concern.**

6. **Runplait — 8 characters; “RUN-plat” or “RUN-playt,” depending on dialect.**  
   **Best broader weaving metaphor without the exact “weft” root.** A plait joins separate strands while retaining their structure, much as SASE coordinates isolated work and produces a coherent reviewed result. It can grow beyond coding. Its main problem is oral usability: pronunciation varies, and someone may write runplate after hearing it. **A strong conceptual name that should survive a spoken spelling test before advancing.**

7. **Runrill — 7 characters; “RUN-rill.”**  
   **Best short continuity metaphor.** A persistent stream of work is a good image for runs that continue through handoffs and remain observable. It is calm and compact, though it communicates teamwork less directly than Crewrill. The repeated r sounds, unfamiliar “rill,” and existing surname uses make it less effortless than Runspur. **A viable restrained brand if the descriptor does most of the explanation.**

8. **Crewweft — 8 characters; “CREW-weft.”**  
   **Very close teamwork-and-craft fit.** It directly suggests weaving an agent team’s separate contributions into one body of work. The downside is the double w, the unfamiliar textile word, and both roots’ existing association with agent software. **Consider it for meaning, but prefer the more verbally distinct Crewrail unless testing or clearance changes the comparison.**

9. **Runlark — 7 characters; “RUN-lark.”**  
   **Best friendly, memorable option.** It is easy to say and spell, avoids heavy orchestration vocabulary, and accommodates multiple sorts of agent work. Existing racehorse usage does not establish a developer-tool collision, but it prevents claiming complete uniqueness. “Lark” can suggest casual experimentation rather than dependable engineering. **A personality-led choice whose functional fit depends heavily on the subtitle.**

10. **Synweft — 7 characters; “SIN-weft.”**  
    **Best compact coined coordination name among the remaining screened options.** “Syn” suggests synchronization, and “weft” supplies the joining metaphor. It is a more distinctive complete string than a generic orchestration word. Its weaknesses are substantial: people may write syncweft, the meaning takes explanation, and it inherits the Weft similarity question. **Keep as a reserve candidate; I would not choose it over the first four without favorable user testing.**

**Final recommendation: yes, proceed with the rename decision now, while the product is alpha. Advance Crewrail and Runclasp to final clearance and a brief spoken-name test; Crewrail is my preferred product name, with Runclasp the practical alternative if a matching .com is important. Keep the implementation scope centered on public identity and compatibility rather than an immediate rewrite of every internal namespace.**
