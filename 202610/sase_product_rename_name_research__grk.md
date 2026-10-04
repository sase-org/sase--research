# SASE product rename: name research (grk)

Date: 2026-10-04
Researcher: grk (independent swarm member)
Question: What should replace the product name `sase`, given the collision with Secure Access Service Edge, a preference for names of at most eight characters, and a higher weight on product fit than on length?

---

## Recommendation

**Rename the product.** Do not keep `sase` / "sassy" as the public name, CLI, package, or GitHub org. Do not spend the rename on another four-letter acronym, on anything still pronounced "sassy", or on a name already used by an agent/orchestration tool.

**Lock one name from the shortlist below, then execute before 1.0.** The diagnosis that `sase` is damaged is correct and is getting worse. The rename is only a good idea if the replacement is actually ownable. A later section lists ten ranked candidates. My pick is **`stichos`**.

Keep "Structured Agentic Software Engineering" as a *methodology* citation of Hassan et al. (2025). Stop using it as the product's name. The paper can stay SASE the way Agile stays Agile while the tool is named Jira.

---

## 1. What the name has to name

The public README calls **sase** "Structured Agentic Software Engineering", pronounced "sassy": a Python toolkit that coordinates existing coding-agent CLIs (Claude Code, Codex, Antigravity, Qwen, OpenCode, Muse, Grok Build) into tracked, reviewable, repeatable work. It does not replace those CLIs.

What a new user actually gets:

- Isolated numbered workspace clones, one per agent.
- A keyboard TUI (historically ACE) for supervising many runs.
- Durable records: Patches, stitches, beads, goals, artifacts, ToolRuns.
- Macros, scheduler/service host, plugins, spec-driven plans.

The coordination style is stigmergic: agents leave traces that other agents and the human follow. The in-product vocabulary is already textile and craft: **stitch, patch, strand, bead**. The job is closer to "personal multi-agent operating system / workbench" than to "spec-kit clone" or "chat orchestrator".

Naming implication: a good replacement should cover *durable, reviewable software-change coordination under one human*, not just "agents", "specs", or "diffs".

---

## 2. Why `sase` is a damaged name

### 2.1 The collision is identical in spelling and speech

Gartner coined **Secure Access Service Edge (SASE)** in 2019. Industry sources uniformly pronounce it **"sassy"**. That is the same four letters and the same spoken form as this product.

The networking category is not a dusty acronym. In 2026 it still has a Gartner Magic Quadrant for SASE Platforms (Netskope, Cato, Palo Alto, Zscaler, Cisco, Cloudflare, Fortinet, Versa, and others). Prior project research put the market in the mid-teens of billions of dollars. Cisco, IBM, Fortinet, and Barracuda all gloss SASE as pronounced "sassy".

Search for `sase`, `sase platform`, `sase docs`, or `sase orchestration` is structurally lost. This project's public surface (`sase.sh`, `pypi.org/project/sase`, `github.com/sase-org/sase`, ~5 GitHub stars on the main repo) cannot win that SERP.

### 2.2 "Agentic" no longer disambiguates

Security vendors now market **agentic SASE**: SASE platforms that police AI-agent traffic, MCP/A2A flows, and "agentic SASE operations". Palo Alto, Cisco, and Gartner's 2026 SASE writeups all use that language. Adding "agent" or "agentic" in front of SASE now *points at the wrong industry*.

### 2.3 Secondary collisions add noise

- PyPI also has `prisma-sase` (Palo Alto Prisma SASE SDK) next to this project's `sase`.
- Society of Asian Scientists and Engineers, self-addressed stamped envelope, Atomic Simulation Environment (`ase` on PyPI, CLI `ase`).
- None of these is the main problem. Gartner SASE is.

### 2.4 The product borrowed a paper's acronym that was already taken

`docs/acknowledgements.md` states the name comes from Hassan et al., 2025, *Agentic Software Engineering: Foundational Pillars and a Research Roadmap* (arXiv:2509.06216), which uses Structured Agentic Software Engineering (SASE), Agent Command Environment (ACE), and Agent Execution Environment (AEE). That is a methodology label. Using it as a *product* name is the same mistake as naming a tracker "Agile". The paper can keep SASE. The CLI should not.

There is also an identity split inside the project: public docs say Structured Agentic Software Engineering; some internal framing is "Stigmergic Agent Swarm Engine" / personal multi-agent OS. A rename is a chance to pick a *word* and stop fighting two expansions.

---

## 3. Critique of this rename plan

### 3.1 The plan is directionally right

Doing this as research *before* a mechanical rename is the correct order. The July 2026 `sawi` decision showed the failure mode: the collision diagnosis was sound, the proposed name was not, and both independent reports still recommended against that particular rename. You get roughly **one cheap rename**, and it is cheapest now:

- Development status is **Alpha** (`pyproject.toml`).
- `sase.sh` was registered 2026-05-06 (GoDaddy); it is not accrued SEO.
- Public GitHub gravity is still small.
- Waiting until v1.0, a real user base, and a handbook citation graph makes the same edit much more expensive.

The eight-character cap is a *good* constraint. A June 2026 consolidated rename note recommended Specyard, PatchTower, ChangeSlate, DiffYard, PatchSlate. Three of those exceed eight characters. Several overfit to "spec" or "patch" and sound like spec-kit competitors. This product is a coordination OS with SDD as one capability.

### 3.2 What would make the plan a bad idea

1. **Renaming to another unownable token.** `sawi` failed on meaning (Filipino "doomed") and on fit. `sassy` as spelling fails because Gartner SASE is *already* pronounced sassy. `sloyd` is a beautiful craft word and is registry-clean, and it is also **sloyd.ai**, an a16z/NVIDIA-backed AI 3D generator. Same spoken name, same "AI tool" neighborhood.
2. **Picking a name already used by coding-agent infrastructure.** 2026 is full of these. See the graveyard in §5.
3. **Keeping the CLI as `sase` while "rebranding" in docs only.** Two names is worse than one damaged name.
4. **Treating this as optional because the tool is personal.** The package, org, domain, and docs are already public. Every `uv tool install sase` and every HN/Twitter mention will hit the wrong SASE.

### 3.3 Cost is real and mostly automatable

A workspace-wide search (excluding `sase/repos`, `.git`, `target`) found **10,760 files** containing `sase`. High-frequency env vars include `SASE_HOME`, `SASE_ARTIFACTS_DIR`, `SASE_AGENT`, `SASE_PLAN`, `SASE_BEAD_ID`. `~/.sase` is referenced in hundreds of files. Fan-out includes `sase-core` / `sase-core-rs`, `sase-github`, `sase-telegram`, `sase-nvim`, sidecar repo names, workspace directories `sase_<N>`, and the GitHub org `sase-org`.

This is a large but scriptable migration, plus a data-dir migration and a CLI alias window. It is not a reason to keep the name. It is a reason not to rename twice.

### 3.4 Verdict on the plan

| Question | Answer |
| --- | --- |
| Is the collision worth leaving? | Yes. |
| Is "research names, then rename" the right process? | Yes. |
| Is the 8-character cap useful? | Yes. Prefer a 5–7 character *word* over an 8-character compound. |
| Should you rename before a name is locked? | No. |
| Should you rename to Specyard/PatchTower by default? | No. Those overfit SDD / "patch" and several break the length cap. |
| Should you move forward? | **Yes**, gated on an ownable word from §6. |

---

## 4. Criteria used here

1. **Product fit.** Durable coordination, isolated workspaces, reviewable change, stigmergic traces, stitch/patch craft. Higher weight than length.
2. **Length.** Hard preference ≤ 8. Bonus for shorter, especially 4–6, when fit is equal.
3. **Speech.** Must not be pronounced "sassy". Must have one obvious pronunciation.
4. **Ownability.** Exact PyPI name should be free (this is a `uv tool install` Python CLI). npm and crates.io matter for a future ecosystem; PyPI is the blocker. GitHub `name-org` should be free. `.sh` is the house TLD.
5. **Category collision.** No other coding-agent orchestrator, MCP runtime, spec-kit, or "AI work trail" product with that CLI.
6. **Language.** No live unfortunate meaning (the `sawi` test: Filipino "doomed"). Scots, German, Indonesian, etc. count.
7. **CLI mouthfeel.** `NAME run`, `NAME tui`, `NAME bead` should be easy to type daily.
8. **Not an acronym.** Four-letter expansions are how this mess started.

This is **not** trademark clearance, and DNS NXDOMAIN is not a registrar guarantee.

---

## 5. Graveyard: strong metaphors that fail in 2026

The obvious vocabulary is already claimed, often *in this category*. Independent registry and web checks (PyPI JSON, npm registry, crates.io, web search, GitHub) on 2026-10-04:

| Name | Why it dies |
| --- | --- |
| `weft` / `weave` / `warp` / `loom` | Multiple coding-agent products named Weft, including WeaveMindAI/weft (~2k stars, "language for AI orchestrations") and seanb4t/weft ("spec-driven AI dev orchestration, woven on jj + beads"). Warp.dev is an AI terminal. Loom.com is a video company. Weaveworks is CNI/GitOps. |
| `heddle` | goweft/heddle is a Python MCP runtime (`heddle run`). Same org is systematically claiming loom words. |
| `tenter` | goweft/tenter is a Python artifact scanner (`pip install tenter` documented). `tenere` is an LLM TUI. Tenten is an "AI software engineer". "On tenterhooks" is also a bad idiom for a tool you wait on. |
| `clew` / `clews` | npatten/Clew is "CLI, local, fast issue tracking for agents" and uses the Ariadne-thread myth verbatim. ClewCode is an AI coding CLI (`clew`). Several other Clew/ClewDR products exist. The myth is taken. |
| `skep` / `skeps` | PyPI `skep` 1.0.2: "Govern AI coding agents with sandboxing, verification, approvals, and audit trails." Direct hit. |
| `selvage` | PyPI `selvage` 0.4.1: LLM-based code review tool. Direct hit. Best metaphor, unusable. |
| `halyard` | PyPI: "Your AI work leaves a trail. Halyard makes that trail legible, auditable, and client-safe." Direct stigmergy hit. |
| `sloyd` / `slojd` | Registry-clean, perfect "structured craft education" metaphor, and **sloyd.ai** is a funded AI 3D generator. Spoken collision in the AI-tools neighborhood. |
| `raddle` | Perfect loom metaphor (warp-spacing bar = isolated parallel workstreams). raddle.me is a long-lived Reddit alternative. npm `raddle` exists. Search is lost. |
| `stigmer` / `stigr` / `stig` | stigmer.ai is an AI agent platform (`stigmer run`). `stig` is a Transmission TUI and a GitHub search CLI. DISA STIG dominates "stig" search. |
| `sawi` | Already rejected in-project (2026-07): worse expansion, Filipino "doomed", mustard-greens pun that does not travel. |
| `sassy` / `sass` | Gartner SASE is already "sassy". Sass is CSS. |
| `conductor` / `crew` / `swarm` / `hive` / `nest` / `fabric` / `harness` / `beads` | Category-crowded or upstream (beads, CrewAI, OpenAI Swarm, k8s, etc.). |
| `cairn` / `norn` / `clotho` / `jig` / `formic` / `twine` / `quill` | Exact PyPI names taken (and several are real packages, not stubs). |
| `ariadne` | Major Python GraphQL library. |
| `specyard` as *the* pick | Registries are clean, but it names one capability (SDD) and sits next to GitHub Spec Kit / OpenSpec / GSD. Construction "SpecYard" already exists as a specs-management SaaS listing. Fine as a fallback, weak as the brand of a multi-agent OS. |

The lesson: **loom-and-thread words are being harvested by agent tools in 2026.** A rename that walks into that field unexamined will recreate the SASE problem at smaller scale.

---

## 6. Ranked ten

Scoring is qualitative on fit / speech / ownability / length. PyPI/npm/crates checked 2026-10-04. "Free" means HTTP 404 on the exact package name. DNS "open" means `getaddrinfo` NXDOMAIN, not a purchase.

### 1. `stichos` (7) — recommended

Ancient Greek στίχος: a **line, row, verse**; in English, a manuscript line. It sits next to the product's own **stitch / patch / strand** words without stealing `stitch` (taken, and now also Google Stitch). It reads, almost unavoidably, as "stitch OS", which is an honest informal expansion and is *not* SASE.

- Speech: **STICK-oss** (lock this in the README; do not use the reconstructed Greek STEE-khoss).
- Fit: line of work, row of agents, stitch of a patch, durable manuscript line. Covers TUI supervision less directly than a "tower" name, and covers traces less directly than "cairn", but it matches the actual object model better than "spec-*" or "diff-*".
- Registries: PyPI, npm, crates.io all free.
- DNS: `stichos.sh`, `stichos.dev`, `stichos.io` NXDOMAIN. `stichos.com` resolves.
- GitHub: `github.com/stichos` is a 200 (user or leftover); **`stichos-org` is 404**, which matches the current `sase-org` pattern.
- Risks: people will type `stitchos` / `stichus`. Google Stitch and `stochos` (a mouse-control overlay from Greek στόχος, "aim") are neighbors, not twins. You will explain the word once. That is true of `mise`, `uv`, `yazi`, and `zellij` too.

CLI: `stichos run`, `stichos tui`, `stichos bead`. Package family: `stichos`, `stichos-core-rs`, `stichos-github`.

### 2. `sennit` (6)

A **braid of cordage** laid up from several strands (also spelled sinnet). Parallel agents are the strands; the product is the braid that makes them one line.

- Speech: **SEN-it**.
- Fit: excellent for multi-agent coordination; slightly weaker for the TUI/OS story; still textile.
- Registries: PyPI and npm free. crates.io reported taken in the bulk scan (the Rust core today is `sase-core-rs`, so an exact crates name is not required).
- DNS: `sennit.sh`, `.dev`, `.io` NXDOMAIN. `sennit.com` resolves.
- Risks: misspellings `sinnet` / `sennet`. `sinnet.com.cn` is Beijing Sinnet, a large Chinese datacenter/cloud company — avoid the `sinnet` spelling. Obscure nautical word; you will gloss it once. Do not confuse with Senate.

### 3. `dimity` (6)

A lightweight cotton fabric with a woven stripe or check. A real, rare English word. All three registries free. `dimity.sh` and `dimity.io` NXDOMAIN.

- Speech: **DIM-i-tee**.
- Fit: textile, pretty, ownable. The metaphor is "a kind of cloth", which is thinner than stitch/braid/row.
- Risks: Dimity is also a given name (especially Australia). Nearby coding-agent names `dim` / `dimcode` / `dimi` exist; speech is different enough, search adjacency is mild. Weaker product story than #1–#2.

### 4. `specyard` (8)

Coined compound. PyPI/npm/crates all free. `specyard.sh` and `specyard.dev` NXDOMAIN; `.io` and `.com` resolve. June 2026 in-repo research ranked this first.

- Speech: **SPEC-yard**.
- Fit: names SDD, plans, and the "yard" of parallel work. Undersells TUI supervision, stigmergy, and "wraps agent CLIs" — the README's actual pitch. Sounds like a Spec Kit peer.
- Use this if you want the brand to *mean specs* and you accept the eight-character ceiling. I would not.

### 5. `oarlock` (7)

The pivot that holds an oar. The product is the fulcrum that lets one human row many agents. All three registries free. `oarlock.sh` and `.dev` NXDOMAIN.

- Speech: obvious.
- Fit: clear physical metaphor, slightly off the stitch/patch language already in the UI. A bit clunky in the mouth compared with `stichos` / `sennit`.
- Risks: nautical, ungainly, easy to understand, easy to forget.

### 6. `workjig` (7)

A manufacturing **jig** is a fixture that holds work in the right place while you operate on it. That is close to what isolated workspaces + Patch lifecycle + finalizers actually do. All three registries free. `github.com/workjig` is 404 (bare name open). `workjig.sh` / `.dev` / `.io` NXDOMAIN.

- Speech: **WORK-jig**.
- Fit: strong for "structured fixture for agent work"; weaker poetry; obviously coined.
- Risks: industrial-generic. "The jig is up" is a joke you will hear. Shorter `jig` is taken on PyPI/npm/crates.

### 7. `gunnel` (6)

Spoken form of **gunwale**: the structural rail of a boat. All three registries free. `gunnel.sh` / `.dev` / `.io` NXDOMAIN.

- Speech: **GUN-əl**.
- Fit: "the rail you hold while the rest of the boat works" is a decent OS metaphor. Distant from stitch/patch.
- Risks: also a fish. Looks informal. `gunwale` is eight letters and people cannot spell it.

### 8. `wale` (4)

A raised rib in knitted or woven fabric; also the ridge of a gunwale. **Shortest serious candidate.** PyPI free, npm taken, crates.io free. `wale.sh` NXDOMAIN.

- Speech: **WAYL** (same as whale / wail — that is the problem).
- Fit: real textile term, daily-CLI length bonus.
- Risks: homophones, npm occupancy, also means a welt from a blow. Only take this if shortness outranks everything else. For this product, it should not.

### 9. `thole` (5)

Nautical: the pin that takes the oar (cousin of oarlock). All three registries free. `thole.sh` NXDOMAIN.

- Speech: **thole** rhymes with pole.
- Fit: fulcrum, same family as oarlock, more obscure.
- **Language flag:** in Scots and northern English, *thole* is a live verb meaning **to suffer, endure, tolerate** ("I cannae thole it"). After `sawi`, that is a real demotion. Endure-as-reliability can be spun positively; "you have to thole this tool" cannot.

### 10. `roving` (6)

A slightly twisted strand of fiber ready to spin; also "wandering". All three registries free. `roving.sh` / `.dev` NXDOMAIN.

- Speech: obvious.
- Fit: agents rove across workspaces; fiber-strand continues textile language.
- Risks: common English word, so search is mushy. "Roving" also means uncommitted / unstructured, which fights "Structured" in the methodology you want to keep citing.

---

## 7. Names I would not put in the top ten but would not laugh out of the room

- `batten` (6): loom batten + "batten down". PyPI free, npm taken.
- `patchos` (7): too startup-compound, and "patch" leans security (the industry you are fleeing).
- `stichos` misspellings as official names (`stitchos`, `sticos`): worse.
- Dual brand (`sase` CLI, other public name): worse.

---

## 8. How to migrate if you pick a name

1. **Lock speech, spelling, and org** in one note: e.g. `stichos` / STICK-oss / `stichos-org` / `stichos.sh`.
2. **Register** PyPI, GitHub org, `.sh` (and `.dev` if NXDOMAIN) *before* announcing.
3. Keep **`sase` as a CLI alias** for at least one major version; print a one-line deprecation on stdin TTY.
4. Migrate **`~/.sase` → `~/.stichos`** (or whatever) with a copy-then-cut, not a surprise.
5. Rename env vars (`SASE_*`) in lockstep; accept old vars for a window.
6. Leave `sase.sh` as a redirect. It is three months old; it is not a cathedral.
7. Keep **ACE** as the TUI's historical nickname if you want the paper link; it is not the product name. AXE is already documented as a former scheduler name.
8. Cite Hassan et al. as the SASE *methodology* in acknowledgements. Stop expanding the product as SASE.

Do not half-rename Python package vs CLI vs org. The current stack is aligned (`sase` everywhere). Keep it aligned.

---

## 9. Direct answer to "should I move forward?"

**Yes.** Rename the product, the CLI, the package, and the org, before 1.0, to a distinctive word that is not an acronym and is not pronounced "sassy".

**No** if the only candidates you like are `sawi`, `sloyd`, `weft`, `clew`, `sassy`, or another four-letter expansion. In that case keep `sase` until a better word exists. A lateral move wastes the one cheap rename.

My concrete pick: **`stichos`**, with **`sennit`** as the runner-up if you want six letters and a braid metaphor, and **`dimity`** if you want a rare English fabric word that is pretty and empty in the registries.

---

## Sources

Product and in-repo:

- `README.md`, `pyproject.toml`, `docs/acknowledgements.md`, `sase/memory/sase.md`
- Glossary (stitch, patch, bead, artifact, workspace, ACE/AXE)
- Prior in-repo notes used only as *shared project history*, not as this swarm's peer reports: `202606/sase_rename_research_consolidated.md` (Specyard-first list; several names now over-length or SDD-overfit), `202607/sawi_rename_decision/sawi_rename_decision.md` (collision diagnosis held; `sawi` rejected)

External (fetched 2026-10-04):

- Gartner SASE pronunciation and category: [Gartner/Andrew Lerner 2019](https://web.archive.org/web/20230901152205/https://blogs.gartner.com/andrew-lerner/2019/12/23/say-hello-sase-secure-access-service-edge/), [Cisco What is SASE](https://www.cisco.com/site/us/en/learn/topics/security/what-is-secure-access-service-edge-sase.html), [IBM SASE](https://www.ibm.com/think/topics/sase), [SDxCentral 2026 MQ recap](https://www.sdxcentral.com/news/gartner-sase-2026-rankings-netskope-leads-cato-networks-leaps-and-palo-alto-networks-falls/)
- Agentic SASE: [Cisco "Securing the Agentic Frontier"](https://www.cisco.com/c/en/us/products/collateral/security/secure-access/securing-the-agentic-frontier.html)
- Hassan et al. SASE: [arXiv:2509.06216](https://arxiv.org/abs/2509.06216), [sase.sh acknowledgements](https://sase.sh/acknowledgements/)
- Orchestrator category crowding: [Augment "9 Open-Source Agent Orchestrators" (2026)](https://www.augmentcode.com/tools/open-source-agent-orchestrators); GitHub Weft repos as cited in §5
- Adjacent product hits: [sloyd.ai](https://www.sloyd.ai/), [goweft/heddle](https://github.com/goweft/heddle), [goweft/tenter](https://github.com/goweft/tenter), [npatten/Clew](https://github.com/npatten/Clew), [stigmer](https://github.com/stigmer/stigmer), PyPI pages for `skep`, `selvage`, `halyard`
- Registries: PyPI JSON API, npm registry, crates.io API for the candidate list in this note
- DNS: local `getaddrinfo` for `.sh` / `.dev` / `.io` / `.com`
- GitHub existence: HTTP HEAD on `github.com/<name>` and `github.com/stichos-org`

Checks that this note does **not** include: USPTO/EU trademark search, registrar WHOIS for NXDOMAIN hosts, npm/crates ownership of every "taken" hit, or a full mechanical rename plan.
