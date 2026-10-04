# Renaming sase: Is It Worth It, and What Should It Be Called?

**Date:** 2026-10-04 · **Researcher:** cld · **Question:** pick a replacement name of at most
about 8 characters for sase, and critique the rename plan itself.

> **Verdict: rename, but only to a name that is clean in two places, and do it soon.**
>
> The collision with Secure Access Service Edge is real and getting worse. That industry
> now markets "agentic SASE" and already uses "SASE agent" for its endpoint client. It
> even pronounces the acronym "sassy", the same way sase does.
>
> The surprise is on the other side. Almost every apt replacement word is **already the
> name of a tool that does nearly what sase does**: bosun, yoke, reins, jig, keel,
> braid, muster, drover, flotilla, brigade, sortie, cadre, tutti, and more. Swapping a
> cross-industry collision for a same-niche one would make things worse.
>
> **My pick is `handful`.** The runners-up are `simul` and `orderly`. If none of the
> three still feels right after a week of use, keep `sase`. Do not trade it for a
> crowded metaphor.

---

## 1. What the Name Has to Carry

### The product

The README's one-line pitch is the brief: _"One developer. A team of coding agents.
Tracked, reviewable, repeatable work."_ A good name should evoke at least two of these
three ideas:

1. **One human directing many agents in parallel.** This is the leverage, the
   supervision, and the fan-out.
2. **Structure and durability.** Work state lives outside any chat transcript: Patches,
   beads, goals, artifacts, receipts, and host-owned completion.
3. **A neutral coordination layer.** sase sits above Claude Code, Codex, Antigravity,
   Qwen Code, OpenCode, Muse, and Grok Build.

The current name also has a personality ("pronounced 'sassy' — yes, really"). A
replacement that keeps a little wit is a bonus.

### The slots the word has to fill

The name is not just a brand. It is load-bearing syntax in more than a dozen places:

| Slot                         | Today                                                         |
| ---------------------------- | ------------------------------------------------------------- |
| CLI                          | `sase run`, `sase tui`, `sase bead …`                         |
| Python dist / import         | PyPI `sase`; about 45k `import sase` / `from sase` lines      |
| Rust core                    | `sase_core` crate, PyPI `sase-core-rs`                        |
| Config / state               | `~/.config/sase/sase.yml`, `~/.sase/`                         |
| Environment variables        | 704 distinct `SASE_*` names                                   |
| Project files                | `<key>.sase`, `<key>-archive.sase`                            |
| In-repo directory            | `sase/memory/`, `sase/macros/`                                |
| Bead IDs                     | `sase-1eq`, `sase-j0`, …                                      |
| Generated skills             | 22 `sase_*` skills                                            |
| Plugins / sidecars           | `sase-github`, `sase-telegram`, `sase-nvim`, `sase--research` |
| Org / domain                 | `sase-org`, `sase.sh`                                         |
| Prose                        | "sase's TUI"                                                  |

The word therefore has to work as a lowercase command, a possessive, an environment
prefix, a file extension, and an ID prefix. You type it hundreds of times a day. Short
matters more here than for most brands, though meaning still comes first.

---

## 2. How Bad Is the SASE Collision, Really?

### Evidence that the collision is real and growing

- **It is a huge, permanent industry term.** Gartner coined SASE in 2019 and projects
  more than $18B of SASE spending in 2026. Every security vendor (Palo Alto, Cisco,
  Zscaler, Netskope, Fortinet, Cato) publishes "What is SASE?" pages. The bare word
  will never be yours.
- **The pronunciation collides exactly.** Secure Access Service Edge is pronounced
  "sassy", which is the pronunciation sase chose. Anyone who hears about sase out loud
  and searches for it lands on networking.
- **The two vocabularies are converging.** In networking, "SASE agent" already means the
  endpoint client (Check Point's SASE Agent, the Versa SASE Client, Palo Alto's Prisma
  Access Agent). In 2026 the vendors also began selling SASE _for AI agents_: Palo
  Alto's "agentic AI with Prisma SASE" and Cisco's "AI-Aware SASE" with MCP visibility.
  My searches for `sase agent` and `sase ai agents tool` returned **only** networking
  results. The collision is moving onto your own words: agent, agentic, MCP.
- **The name is borrowed.** sase takes its name from Hassan et al.'s 2025 paper, which
  defines **SASE** as a research framework (arXiv 2509.06216). As that paper gets
  cited, "SASE" also comes to mean the academic framework, and readers may assume this
  project is its reference implementation. The paper-derived sub-names have already
  been retired: ACE became "sase's TUI" and AXE became the scheduler.
- **The spelling does not match the sound.** Every new user has to be told how to say
  it. The getting-started guide literally says "yes, really".
- **LLMs default to the networking meaning.** An assistant asked "what is sase?" will
  answer about networking. Your users talk to LLMs all day, so this is a recurring tax.
  This point is plausible but I did not test it.

### Evidence that it is less bad than it looks

- **Searches with context already work.** `sase coding agents Claude Code Codex TUI`
  returns `sase-org/sase` first, `sase cli github` returns sase-org repositories in the
  top three, and `sase.sh` returns the repository first.
- **Inside the agent-tool niche, "sase" is unique.** No other coding-agent orchestrator
  uses the name. The other namesakes are minor: a UMass complex-event-processing
  language, the Sarajevo Stock Exchange, and a small Go package.
- **Legal risk is low.** SASE is a generic industry term, not one company's trademark.
  This is not legal advice.

### Net assessment

The cost is moderate today and rising as networking vendors adopt the agent
vocabulary. A rename is justified **only if the replacement is better on both axes**:
across industries, and inside the coding-agent niche. The next section shows why the
second axis is the hard one.

---

## 3. The Surprise: The Obvious Replacements Are Already Taken

2026 is a boom year for parallel coding-agent orchestrators. Conductor, Claude Squad,
Gas Town, Vibe Kanban, Superset, Composio's Agent Orchestrator, Orca, and herdr are the
well-known ones, and there are several "awesome agent orchestrators" lists. Their
builders keep reaching for the same metaphors.

I checked about 150 candidate names against PyPI, crates.io, npm, Homebrew, Debian
packages, GitHub logins, and DNS for `.sh`, `.dev`, `.ai`, `.io`, and `.com`. I then
searched about 55 of them for AI and coding-agent namesakes. Here are the apt names
that are already taken **inside the niche**:

| Candidate     | Already used by (same niche unless noted)                                                                                                |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `bosun`       | virtengine/bosun ("control plane for autonomous software engineering"), Bosun.ai, a tmux-native Bosun for agent sessions                  |
| `jig`         | six or more coding-agent repos, including krondor-corp/jig ("worktrees for agents")                                                       |
| `reins`       | five or more agent-control repos, plus Rein Security and Reins AI                                                                         |
| `yoke`        | HECer/yoke (one worktree per story) and outrightmental/yoke; also yokecd/yoke, a Kubernetes tool applying to the CNCF sandbox             |
| `braid`       | getbraid.dev and braid.software, both commercial apps running parallel agents in worktrees                                                |
| `keel`        | several agent harnesses; also keel-hq/keel (2.7k★) and Keel.so ($13.1M raised)                                                           |
| `muster`      | giantswarm/muster (an MCP aggregator at v5), musterhq/muster, muster.tools                                                                |
| `drover`      | arniesaha/drover ("drive your coding-agent fleet"), andrebrov/drover, cloud-shuttle/drover-code                                           |
| `musher`/`mush` | musher.dev ("direct your fleet of coding agents from issue to merge")                                                                  |
| `gaffer`      | tmj-90/gaffer ("self-hosted AI coding factory", human-gated)                                                                              |
| `brigade`     | escoffier-labs/brigade, a **Python** control plane for coding agents with verification receipts and memory (`brigade-cli`)                |
| `flotilla`    | flotilla-org/flotilla ("agents, branches, PRs, and workspaces", TUI plus daemon, more than 2,400 PRs)                                      |
| `sortie`      | sortie-ai/sortie (tickets become parallel Claude Code/Codex sessions in isolated workspaces)                                              |
| `cadre`       | BlaineHeffron/cadre (schedules and coordinates Claude Code/Codex with worktrees)                                                          |
| `corral`      | five or more agent-fleet repos; also rancherlabs/corral                                                                                   |
| `tutti`       | nutthouse/tutti (per-agent worktrees plus a dashboard), tutti-os/tutti (about 2k★)                                                        |
| `bottega`     | vdaubry/bottega ("coding agent orchestration for engineering teams") and its forks                                                        |
| `kibitz`      | kibitzsh/kibitz (about 521★, watches and prompts many Claude Code and Codex sessions)                                                     |
| `posse`       | PyPI `posse`, "A shared brain for teams of coding agents", **published 2026-10-03**                                                       |
| `skep`        | PyPI `skep`, "Govern AI coding agents with sandboxing, verification, approvals, and audit trails"                                         |
| more          | `troupe`, `kelpie`, `atelier`, `galley`, `bullpen`, `pitwall`, `weft`, `kumi`, `tako`, `pulpo`, `operon`, `centaur`, `skipper` each have at least one near-identical tool |
| big names     | `conductor` (Conductor, $22M), `crew` (CrewAI), `squad` (Claude Squad), `herd` (herdr), `orca`, `swarm`, `fleet`, `foreman`, `maestro`, `warp` |

**The lesson:** in 2026, an obvious metaphor for "one person directs a team" is almost
by definition already a coding-agent orchestrator. That makes `sase` _better_ than
most replacements inside the niche. With SASE, someone searching for you lands on a
networking vendor. With `bosun` or `yoke`, they land on a **competitor**.

This changes the bar. A new name must:

1. have no namesake of note among coding-agent tools,
2. not be dominated by a single tech owner (as SASE is), and
3. still fit what sase does.

The names that pass all three gates are either oblique (a step of imagination other
builders have not taken) or unusual words.

---

## 4. Critique of the Plan

### What's right

- **The timing is the cheapest it will ever be.** The public repository has 5 stars and
  1 fork, so outside brand equity is small.
- **"Meaning over length, up to about 8 characters" is the right priority**, and short
  really does matter for a word typed this often.

### What's missing or risky

1. **The criteria omit collisions inside the niche** (see §3). Without that gate, the
   most natural shortlist (bosun, jig, reins, yoke, keel) is strictly worse than
   `sase`.
2. **The cost is large and growing fast.** In this repository alone:

   - 141,784 case-insensitive occurrences in 10,762 of 12,994 tracked files
   - 5,908 file paths containing "sase"
   - about 45k Python import lines
   - 704 distinct `SASE_*` environment variables
   - 22 generated `sase_*` skills

   Outside it sit sase-core, six linked repositories, the `sase-org` org, `sase.sh`,
   several PyPI distributions (`sase`, `sase-core-rs`, `sase-github`, …), `~/.sase`
   state on every machine (athena, apollo, the Mac), and bead IDs. For scale: the
   February 2026 rename from gai to sase touched about 520 files, so this one is
   roughly 20× bigger. About 2,000 commits landed in the last 30 days, and each adds
   more references.

   The project's rename tooling makes this feasible. It already carried the
   xprompt → macro, agent shell → turn, and ChangeSpec → Patch renames with
   token-aware rewrites, terminology guards, and legacy lookup aliases. Still, this is
   an epic, not a weekend.
3. **This would be the second rename in eight months.** A third would be costly and
   look unserious, so choose a name to keep for ten years. Secure the domain, the PyPI
   distribution name, and the GitHub org, and run a quick trademark search (USPTO and
   EUIPO, classes 9 and 42), all **before** announcing.
4. **Keep the lineage as a tagline.** "_newname_ — structured agentic software
   engineering" still credits Hassan et al. and still ranks for people who search that
   phrase. Only the brand word changes.
5. **Note your own naming trend.** Over 2026 the project retired themed sub-names: ACE
   became "sase's TUI", AXE became the scheduler, chop became job, lumberjack became
   routine, and xprompt became macro. A top-level brand is the one place a distinctive
   word belongs, because a descriptive name like "agent orchestrator" can't be owned.
   But the trend says the meaning should be readable without a backstory.
6. **Plan the migration shape up front:**
   - Ship the brand first, without breaking existing setups.
   - Install the new CLI, and keep `sase` as a deprecated alias for a few releases.
   - Read `~/.sase` and `SASE_*` as fallbacks, and keep accepting `.sase` project
     files.
   - Rename the GitHub org (GitHub redirects repository URLs after a rename).
   - Redirect `sase.sh` to the new domain with 301s.
   - Publish a final `sase` PyPI release that depends on the new distribution and
     prints a notice.
   - Leave historical bead IDs alone.

---

## 5. How I Scored the Finalists

| Criterion           | Weight | What it asks                                                                                  |
| ------------------- | -----: | --------------------------------------------------------------------------------------------- |
| **Fit**             |    40% | Does it evoke one developer directing parallel agents, structure, or both?                    |
| **Collision**       |    30% | No namesake among coding-agent tools, and no single tech owner dominating search for the word |
| **Say / spell**     |    10% | Can you pronounce it from the spelling, and spell it from hearing it? (sase's weak spot)      |
| **Typing**          |    10% | Length and CLI feel                                                                           |
| **Handles**         |    10% | PyPI, crates.io, npm, GitHub, `.sh`/`.dev`                                                    |

### Availability of the finalists

These results are from registry APIs and DNS on 2026-10-04.

| Name     | Len | PyPI                         | crates | npm               | GitHub login          | `.sh`  | `.dev` | Namesake in the niche                                    |
| -------- | --: | ---------------------------- | ------ | ----------------- | --------------------- | ------ | ------ | -------------------------------------------------------- |
| handful  |   7 | **free**                     | free   | taken (Svelte utils) | dormant 2016 org (3 repos) | free\* | free\* | none found                                               |
| simul    |   5 | taken (small 2025 lib)       | taken  | taken             | taken                 | free\* | taken  | none exact; Simular ($21.5M, computer-use agents) is a near-name |
| orderly  |   7 | taken (dormant 2023)         | taken  | taken             | taken                 | taken  | taken  | none; Orderly Network (crypto) dominates searches        |
| senju    |   5 | **free**                     | free   | free              | taken (user)          | free\* | taken  | none of note; NRI's "Senju Family" IT-ops suite (Japan)  |
| navarch  |   7 | **free**                     | taken  | free              | taken (user)          | free\* | free\* | Navarch, a GPU fleet manager (infrastructure)            |
| auteur   |   6 | taken (2026 IMDb client)     | free   | taken             | taken                 | taken  | taken  | tiny repos only                                          |
| taut     |   4 | **free**                     | free   | taken             | taken (org)           | free\* | taken  | none found                                               |
| kantoku  |   7 | taken (Circus-fork process manager) | free | free         | taken (user)          | free\* | taken  | none found                                               |
| maniple  |   7 | **free**                     | free   | free              | taken (org)           | free\* | taken  | Martian-Engineering/maniple (about 49★, MCP team runner) |
| crewel   |   6 | **free**                     | free   | free              | taken (user)          | free\* | free\* | Jasowills/crewel (small); "crewel AI" searches return CrewAI |
| _sase_   |   4 | owned                        | free   | free              | owned                 | owned  | taken  | none                                                     |

\* Free here means the domain returned NXDOMAIN, so it is probably unregistered.
Confirm with a registrar, since premium pricing is possible. A taken but dormant PyPI
name can in principle be reclaimed under PEP 541, but that is slow. Plan instead on a
suffixed distribution name (for example `simul-cli`) with the bare command name.

---

## 6. Near-Misses Worth Knowing About

- **`coach`** fits best on meaning alone. The Hassan et al. paper literally recasts the
  human as an "Agent Coach and Orchestrator", and a coach is also a carriage drawn by a
  team. But it can't be owned: Coach the fashion brand and the whole "AI coach" app
  category bury it.
- **`teamster`** literally means "one who drives a team". But the Teamsters union
  (teamster.org) polices names that could look affiliated, the union campaigns against
  automation, and teamster.ai already sells AI agent teams. Naming an AI-agent tool
  this would be tone-deaf.
- **`troika`** is one driver with three horses abreast. It implies exactly three
  agents, ECMWF ships an active `troika` job-submission CLI on PyPI, and npm's
  troika-three-text is heavily used.
- **`jehu`** is clean and four letters long. But it is the biblical byword for a driver
  who "driveth furiously", the opposite of structured.
- **`agmen`** is Latin for an army column on the march, from _agere_, the same root as
  "agent". It is one letter away from `agman`, an existing agent-worktree TUI.
- **`hancho`** is Japanese for a squad leader, and the origin of "head honcho". It
  reads as Honcho, Plastic Labs' agent-memory library.

---

## 7. Ranked Top 10

### 1. `handful` (7)

_"A handful of agents."_ The word works three ways:

- **A handful** is as many as one hand can hold. That is the human-scale fleet one
  developer can actually supervise, which is sase's whole premise.
- **"A handful"** also means hard to manage, which coding agents are. This tool keeps
  them _in hand_.
- **Latin _manipulus_** ("a handful") named the Roman maniple: a small, structured
  unit able to act independently inside a larger formation. That matches parallel
  agents in isolated workspaces.

It keeps sase's wink without the sassy/SASE collision. It is plain English, so you can
say and spell it on first hearing.

- **Collision:** I found no AI or coding-agent namesake.
- **Handles:** PyPI and crates.io are free, and `handful.sh` and `handful.dev` show no
  DNS records. The GitHub login is a dormant 2016 org, so use `handful-dev`.
- **Risks:**
  - It may undersell scale ("only a handful?").
  - Critics get an easy pun ("handful is a handful").
  - It is seven letters instead of four, and the obvious short alias `hf` belongs to
    Hugging Face's CLI.

Sample usage: `handful run "+home summarize this repo"`, `handful tui`, `~/.handful/`,
`HANDFUL_HOME`, `handful-github`.

### 2. `simul` (5)

A chess **simul** (simultaneous exhibition) is one master walking a ring of boards,
making one move at each, and moving on. That is sase's daily loop exactly. The TUI is
the ring, and each agent is a board in its own workspace. SASE agents are also
single-turn, so each visit is one move and continuation is mechanical. In Latin,
_simul_ means "at the same time". This is the best fit of any name that passes the
gates.

- **Risks:** many people will read it as "simulation" (`simul run` sounds like a
  simulator) or say "sim-YOOL". Simular is a funded computer-use-agent startup with a
  near-identical name.
- **Handles:** PyPI is taken by a small 2025 library, so you'd need a dist name like
  `simul-cli`. `simul.sh` appears unregistered.

### 3. `orderly` (7)

This is the "S" of SASE as an ordinary word: methodical, tidy, structured. As a noun,
an orderly is an attendant who carries out tasks under direction, and a military
orderly carries an officer's orders. The agents are orderlies; the tool keeps the work
orderly. Anyone can say and spell it.

- **Collision:** Orderly Network, a crypto exchange that has raised about $25M and
  ships "skills" for AI agents, dominates "orderly AI agent" searches. That is another
  cross-industry collision, though far smaller than SASE. There is also vimc's
  `orderly` R package.
- **Handles:** weak. PyPI is held by a dormant 2023 package, and `orderly.sh` and
  `orderly.dev` are registered.

### 4. `senju` (5)

千手, "thousand hands", as in Senju Kannon, the thousand-armed bodhisattva who helps
everyone at once: one mind with many hands working in parallel. It is short and clean.
PyPI, crates.io, and npm are all free, and `senju.sh` appears unregistered.

- **Risks:**
  - It is opaque to most Western developers until explained.
  - It borrows a religious epithet.
  - It carries a strong Naruto association (the Senju clan; sase already has "clans").
  - NRI's "Senju Family" is an established Japanese IT-operations suite that includes
    job scheduling, which is adjacent in Japan.

### 5. `navarch` (7)

From Greek _nauarchos_, the commander of a fleet, and developers already talk about
"fleets" of agents. It is clean in the niche: Navarch is a GPU fleet manager, a
different audience. PyPI and npm are free, and `navarch.sh` and `navarch.dev` appear
unregistered.

- **Risks:** the word is obscure, people won't know whether to say "NAV-ark" or
  "NAV-arch", and "nav" reads as navigation.

### 6. `auteur` (6)

The film director whose single vision governs work made by many hands; the final cut
is theirs. It captures the "the work is still yours: tracked, reviewable" side of
sase, and the collision risk is low.

- **Risks:** it sounds pretentious, and the French spelling and pronunciation
  ("oh-TUR") trip people up.
- **Handles:** PyPI, `.sh`, and `.dev` are all taken.

### 7. `taut` (4)

From "run a taut ship": a disciplined, well-run vessel. It is the shortest clean
option. PyPI and crates.io are free, and `taut.sh` appears unregistered.

- **Risks:** it says nothing about agents or teams, it sounds like "taught", and it
  connotes tension.

### 8. `kantoku` (7)

監督 means film director, sports team manager, and construction-site supervisor: one
word for the person who directs a crew. I found no namesake in the niche.

- **Risks:** it is opaque outside Japan, and PyPI's `kantoku` is a process manager (a
  Circus fork), which is an adjacent dev tool.

### 9. `maniple` (7)

The Roman maniple itself (_manipulus_, "a handful"). All handles are free.

- **Risks:** it reads as "manipulate" and is obscure. Martian-Engineering/maniple
  (about 49★) is a small MCP server that runs a team of Claude Code sessions, so it
  has a small namesake in the niche.

### 10. `crewel` (6)

"Crew" plus crewel embroidery, which is wool stitching; that echoes sase's stitches,
strands, and Patches. Every handle is free: PyPI, crates.io, npm, `.sh`, and `.dev`.

- **Risks:** it is pronounced exactly like "cruel", searches for "crewel AI" return
  CrewAI, and Jasowills/crewel is a small cross-agent orchestrator.

### Where `sase` itself would rank

Between #3 and #4. It wins on typing and handles, and it has no namesake in the niche.
It loses on the growing networking collision and the gap between spelling and sound.
**Only the top three clearly beat it.** That is why the recommendation below is
conditional.

---

## 8. Recommendation

**Move forward with the rename, but only to `handful`, `simul`, or `orderly`, and
decide within about a month.** Every month adds roughly 2,000 commits of new `sase`
references.

1. **Live with the shortlist for a week.** Run `alias handful=sase`, rewrite the README
   tagline with each candidate, and say the sentence out loud: _"I run my agents with
   \_\_\_."_
2. **Check LLM priors.** Ask two or three models "what is \_\_\_?" and "what is the
   \_\_\_ CLI?". You want neutral answers, not a confident wrong product.
3. **Secure everything before announcing:**
   - the domain (`.sh` and `.dev`)
   - a placeholder for the PyPI distribution
   - the GitHub org (for example `handful-dev`)
   - a USPTO and EUIPO trademark search in classes 9 and 42
4. **Then open the rename epic.** Ship the brand, the CLI, and the `sase` alias first,
   and migrate the internals (environment variables, state directories, the file
   extension) afterward behind fallbacks. Keep "Structured Agentic Software
   Engineering" as the tagline.

**If none of the three survives that week, keep `sase`.** A crowded metaphor would be a
downgrade. In that case, make "sase" plus context the brand handle ("sase agents",
`sase.sh`) everywhere, and stop teaching the "sassy" pronunciation, since that is
exactly how the networking term is said.

---

## Method and Limits

- **Registries:** I queried the PyPI JSON API (including the last release date for
  taken names), the crates.io API, the npm registry, the Homebrew formula API, the
  GitHub users API, and Debian `apt-cache`, for about 150 names. I also checked `PATH`
  for command clashes.
- **Domains:** I ran DNS NS lookups for `.sh`, `.dev`, `.ai`, `.io`, and `.com`.
  NXDOMAIN is only a proxy for "unregistered".
- **Web searches:** run on 2026-10-04, partly by three delegated sub-searches. Star
  counts come from search snippets and are approximate.
- **Not done:** trademark-database searches, social-handle checks, registrar pricing,
  and actually querying LLMs.
- **Repo measurements:** taken from this workspace's checkout only. The linked
  repositories (sase-core, plugins) were not counted.

## Sources

- sase docs in this repo: `README.md`, `docs/acknowledgements.md`,
  `docs/blog/posts/why-coding-agents-need-orchestration.md`, `docs/getting_started.md`.
- Hassan et al., _Agentic Software Engineering: Foundational Pillars and a Research
  Roadmap_ — [arXiv 2509.06216](https://arxiv.org/abs/2509.06216)
- SASE market and pronunciation:
  [Secure access service edge (Wikipedia)](https://en.wikipedia.org/wiki/Secure_access_service_edge),
  [IBM: What is SASE](https://www.ibm.com/think/topics/sase),
  [Light Reading: SASE market](https://www.lightreading.com/sd-wan/bolstered-by-security-demand-sase-market-to-surpass-13b-by-2026-report),
  [Gartner: Forecast Analysis, SASE](https://www.gartner.com/en/documents/6152891),
  [SDxCentral: Gartner SASE 2026 rankings](https://www.sdxcentral.com/news/gartner-sase-2026-rankings-netskope-leads-cato-networks-leaps-and-palo-alto-networks-falls/)
- "SASE agent" and "agentic SASE":
  [Check Point: Using the SASE Agent](https://sc1.checkpoint.com/documents/Infinity_Portal/WebAdminGuides/EN/SASE-Admin-Guide/Content/Topics-SASE-AG/Devices/Using-Agent.htm),
  [Versa SASE Client](https://versa-networks.com/products/versa-sase-client/),
  [Prisma Access Agent](https://www.paloaltonetworks.com/sase/prisma-access-agent),
  [Palo Alto: Agentic AI with Prisma SASE](https://www.paloaltonetworks.com/blog/2026/03/agentic-ai-with-prisma-sase/),
  [Cisco: AI-Aware SASE](https://investor.cisco.com/news/news-details/2026/Cisco-Redefines-Security-for-the-Agentic-Era-with-AI-Defense-Expansion-and-AI-Aware-SASE/default.aspx),
  [Prisma SASE Python SDK](https://pypi.org/project/prisma-sase)
- Orchestrator landscape:
  [Tembo: AI agent orchestration tools](https://www.tembo.io/blog/ai-agent-orchestration-tools),
  [Augment: open-source agent orchestrators](https://www.augmentcode.com/tools/open-source-agent-orchestrators),
  [Nimbalyst: parallel agent tools 2026](https://nimbalyst.com/blog/best-agent-management-tools-2026/),
  [awesome-agent-orchestrators](https://github.com/andyrewlee/awesome-agent-orchestrators)
- Namesakes cited in §3:
  [virtengine/bosun](https://github.com/virtengine/bosun),
  [bosun-ai](https://github.com/bosun-ai),
  [krondor-corp/jig](https://github.com/krondor-corp/jig),
  [katulevskiy/reins](https://github.com/katulevskiy/reins),
  [HECer/yoke](https://github.com/HECer/yoke),
  [yokecd/yoke](https://github.com/yokecd/yoke),
  [getbraid.dev](https://getbraid.dev/),
  [braid.software](https://braid.software/),
  [keel-hq/keel](https://github.com/keel-hq/keel),
  [Keel.so fundraise](https://keel.so/blog/announcing-our-fundraise),
  [giantswarm/muster](https://github.com/giantswarm/muster),
  [musterhq/muster](https://github.com/musterhq/muster),
  [arniesaha/drover](https://github.com/arniesaha/drover),
  [musher-dev](https://github.com/musher-dev),
  [tmj-90/gaffer](https://github.com/tmj-90/gaffer),
  [escoffier-labs/brigade](https://github.com/escoffier-labs/brigade),
  [flotilla-org/flotilla](https://github.com/flotilla-org/flotilla),
  [sortie-ai/sortie](https://github.com/sortie-ai/sortie),
  [BlaineHeffron/cadre](https://github.com/BlaineHeffron/cadre),
  [corral-sh/corral](https://github.com/corral-sh/corral),
  [nutthouse/tutti](https://github.com/nutthouse/tutti),
  [vdaubry/bottega](https://github.com/vdaubry/bottega),
  [kibitzsh/kibitz](https://github.com/kibitzsh/kibitz),
  [Evansbee/troupe_agent_orchestrator](https://github.com/Evansbee/troupe_agent_orchestrator),
  [ObserverMoment/kelpie](https://github.com/ObserverMoment/kelpie),
  [97kim/Atelier](https://github.com/97kim/Atelier),
  [shinpr/galley](https://github.com/shinpr/galley),
  [billroy/bullpen](https://github.com/billroy/bullpen),
  [danvoulez/pitwall](https://github.com/danvoulez/pitwall),
  [weftlabs/weft-cli](https://github.com/weftlabs/weft-cli),
  [Nathan-W123/Kumi](https://github.com/Nathan-W123/Kumi),
  [tako-dev/cli](https://github.com/tako-dev/cli),
  [darioblanco/pulpo](https://github.com/darioblanco/pulpo),
  [operonapp.dev](https://www.operonapp.dev/),
  [paradigmxyz/centaur](https://github.com/paradigmxyz/centaur),
  [SkipLabs Skipper](https://skiplabs.io/blog/press_release)
- Finalist conflicts:
  [Simular funding](https://www.simular.ai/articles/simular-raises-21-5m-to-build-autonomous-computer-agents),
  [Orderly Network](https://orderly.network/docs/home),
  [NRI Senju Family](https://senjufamily.nri.com/sen/),
  [NavarchProject/navarch](https://github.com/NavarchProject/navarch),
  [Martian-Engineering/maniple](https://github.com/Martian-Engineering/maniple),
  [Jasowills/crewel](https://github.com/Jasowills/crewel),
  [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI),
  [pejmanjohn/auteur](https://github.com/pejmanjohn/auteur),
  [ecmwf/troika](https://github.com/ecmwf/troika),
  [teamster.ai](https://www.teamster.ai/),
  [IBT licensed insignia](https://teamster.org/about/vendors-licensed-use-ibt-insignia/),
  [HonestMajority/agman](https://github.com/HonestMajority/agman),
  [plastic-labs/honcho](https://github.com/plastic-labs/honcho),
  [Conductor and the 2026 ecosystem](https://rustman.org/wiki/conductor-parallel-agents/)
