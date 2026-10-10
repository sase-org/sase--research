# Databricks NYC Application Kit: Two Roles, a Tailored CV, Pitches, and Profile Updates

> **Research query:** Help Bryan apply to one or two NYC Databricks roles after
> Omnigent's release. Design a CV for those roles, modeled on the existing
> `bbugyi200/CV` repo and committed there. Update the CV for leaving Google in May
> 2026, and say what LinkedIn needs. Bryan has worked on SASE full-time since then, and
> a sase.sh blog post is a week or two out. Write a short pitch for each role he is
> genuinely qualified for. Context: `databricks_omnigent_job_fit.md` (bob-cli research
> sidecar, 2026-10-07).

## Bottom line

1. **Apply to exactly two roles. Both are in NYC and both were live in the Databricks
   Greenhouse feed today (2026-10-10, 892 postings).** Bryan meets every hard
   requirement of each (details in
   [are you really qualified?](#are-you-really-qualified)):
   - **Staff Software Engineer, Agent Quality** (`8842963002`; base
     $200K–$265K). This is the better story: a founding team that builds evaluation
     infrastructure producing "trustworthy, reproducible signals". SASE's run-record and
     regression-triage layer is that same kind of work. The weak point is Staff-level
     cross-team influence, and Bryan has no formal LLM-eval suite yet.
   - **Sr. Software Engineer – Backend, AI Platform** (`8379331002`; base
     $165.3K–$219.7K). This is the safer level. It hires across MLflow, AI Gateway,
     Agent Framework, and Agent Bricks, and the Omnigent maintainers come from that org.
     Its bonus point "built developer platforms or internal tools supporting AI
     workflows" describes SASE.
2. **No other NYC posting is an honest fit.** Each of the others requires 8–10+ years,
   Scala or Go, GPU or ML-training infrastructure, or a domain such as CRM, ad
   measurement, or mobile SDKs (see [rejected](#nyc-roles-checked-and-rejected)). The
   only Omnigent-named job, the DevRel role, is SF or Seattle only.
3. **A Databricks CV variant is drafted, compiled, and checked.** It is
   `BryanBugyi_Databricks_CV.tex`, a sibling of the Batman, Google, and LangChain
   variants: the same macros and the same two-page shape, in a navy and lava palette.
   SASE moves from "Projects" to the top **Experience** entry, and Google now ends in
   **May 2026**. The full source is in
   [Appendix A](#appendix-a-bryanbugyi_databricks_cvtex). The PDF and TeX snapshots are
   `file:explicit:d0edce7849a097d298f3e4c8` and `file:explicit:5030fdba524bbb7f48fd550a`.
   **I did not commit it to `bbugyi200/CV`.** Five researchers are running in
   parallel, so one person should commit a single synthesized version. The steps are
   in [committing](#committing-it-to-bbugyi200cv).
4. **Every existing CV variant has stale facts.** All four still say Google
   "present". The themed variants describe SASE as orchestrating "Claude, Gemini, and
   Codex", which is now **seven** harnesses. They also claim "Prometheus telemetry
   surfacing 33 pipeline metrics", but **SASE removed its Prometheus and Grafana
   stack** (`docs/telemetry.md`). Telemetry is now a Rust-backed SQLite store. Fix these
   before any CV goes out.
5. **Update LinkedIn and GitHub before applying.** A Databricks recruiter will check
   both. GitHub's bio still says `{day: "SWE at Google", ...}`. Step-by-step edits are
   in [LinkedIn and GitHub](#linkedin-github-and-site-updates).
6. **Apply now; don't wait for the blog.** Agent Quality was posted 2026-09-24, and
   founding-team requisitions fill early. Use the blog launch as a reason to follow up
   with the recruiter. Before the onsite, close the one real gap: run a small
   **MLflow-based eval over SASE agent runs** (see
   [the plan](#application-plan-and-timing)).

## Are you really qualified?

Experience arithmetic: Edgestream (May 2019 – Jan 2021) + Bloomberg (Jan 2021 – May
2022) + Google (Jun 2022 – May 2026) ≈ **7.0 years** as a professional software
engineer, plus five months full-time on SASE. Comcast (2011–16) was support work and is
not counted.

### Staff Software Engineer, Agent Quality (NYC, `8842963002`)

The team is a founding team in Databricks AI Research. It will "stand up the
foundational evaluation infrastructure for Genie Agents", "build the flywheel that
connects evaluation results back into agent improvement", and shape agent-quality
infrastructure for the "agent development platform".

| Posting requirement | Bryan's evidence | Verdict |
| --- | --- | --- |
| 6+ years of industry experience | ≈7 years plus five months of SASE | **Met** |
| Strong Python; production or research infrastructure | Primary language since 2011. Production Python at Edgestream and Bloomberg. SASE is Python 3.12 with a Rust core | **Met** |
| Distributed systems, data pipelines, or large-scale infra, "with a focus on reliability, correctness, and operational maturity" | Founding Compliance SRE engineer at Bloomberg, Google Ad Manager backend, and SASE's authenticated multi-machine gateway (small scale) | **Met, but thinnest.** The scale story must come from Bloomberg and Google |
| "Pragmatic but rigorous systems that produce trustworthy, reproducible signals" | Every check or test run becomes a ToolRun record with normalized failure signatures and a verdict: NEW, KNOWN, FLAKY, or UNKNOWN. **KNOWN needs an independent witness, and exit codes are never masked.** Also the deterministic `fakey` provider, a per-SHA master gate, and a flake baseline | **Strong.** This is the center of the pitch |
| Comfort across research and product boundaries | SASE is built from agentic-coding research. Its multi-provider research swarms verify disagreements before a lead synthesizes | **Met** |
| Influence roadmap and execution across multiple teams | CLDR adopted across Bloomberg's Compliance department, a firm-wide Python cookiecutter, and a pylint rollout across 1M+ lines | **Partial.** This is the Staff-level gap. Expect a possible down-level |
| *Nice:* devtools, CI/CD, testing frameworks, observability, benchmarking | Edgestream test framework and runner, CLDR release tooling, SASE CI lanes, and SASE telemetry | **Strong** |
| *Nice:* how LLM or agent quality is measured | Operational quality signals, yes. No task-success eval suite or LLM judges yet | **Partial.** Close it before the onsite |

**Verdict: qualified. Apply.** No hard requirement is missed. The risk is level, not
eligibility.

### Sr. Software Engineer – Backend, AI Platform (NYC, `8379331002`)

The posting reads "Build infrastructure that powers … MLflow, AI Gateway, Databricks
Apps, Agent Framework, Agent Bricks, and Foundation Model APIs", and it says "hiring
across multiple teams".

| Posting requirement | Bryan's evidence | Verdict |
| --- | --- | --- |
| 5+ years of backend or infrastructure engineering | ≈7 years | **Met** |
| Scala, Go, **or Python** | Python | **Met** |
| Distributed systems, scalable APIs, **or** cloud-native infra | Ad Manager Java backend, Bloomberg SRE, and SASE's HTTP gateway and fleet dispatch | **Met** (the "or" helps) |
| Service-oriented architecture, deployment pipelines, observability | SRE work, CLDR release methodology, SASE's CI lanes and telemetry | **Met** |
| Product and ownership mindset | Designed, built, and operates SASE end to end; dogfoods it daily | **Strong** |
| *Bonus:* developer platforms or internal tools supporting AI workflows | SASE | **Strong** |
| *Bonus:* OSS contributions to MLflow, PyTorch, or Ray | psf/black PR #1132, but none to these three | **Partial.** An MLflow PR or eval demo would help |
| *Bonus:* real-time serving, ML infra, GPU; SageMaker, Vertex, Azure ML | None | Not met (bonus only) |

**Verdict: qualified. Apply,** and ask the recruiter to route you to the Omnigent, AI
Gateway, or Agent Framework teams.

### NYC roles checked and rejected

| Posting (NYC) | Why not |
| --- | --- |
| Staff Backend SWE – Unity AI Gateway (`8468436002`) | Requires **8+ years** and **"Scala, or Go"**, with Python not listed. It is the closest product, since it now routes "agents, coding assistants, and MCP servers". Name it to the recruiter; don't apply |
| Staff SWE – AI Research Infrastructure (`8552484002`, `8532682002`) | GPU training, job scheduling, and "modern ML training and inference workflows" at large distributed scale |
| Staff SWE Fullstack – AI Product (`8509534002`); Staff SWE Frontend (`8384595002`) | 10+ years of HTML/CSS/JS (Fullstack also asks 10+ years server-side) |
| Staff SWE Sales Data & Agents (`8760171002`); Ads Measurement & Orchestration (`8760165002`); Data Collection, Tags & SDKs (`8760176002`); Staff MLE CustomerLake (`8614863002`) | 10+ years plus deep domain experience: CRM data models, ad measurement (MTA, MMM), native mobile SDKs, or martech ML. Ad Manager experience helps the Ads role but doesn't close the gap |
| Staff Partner Engineer, AI Partnerships (`8643452002`) | 10+ years of field or partner engineering plus established relationships at frontier labs |
| Sr. Forward Deployed Engineer (several NYC postings) | Customer-facing delivery with travel. Not the job Bryan wants, so not evaluated in depth |
| Sr. Developer Advocate — Omnigent (`8716187002` / `8716730002`) | SF or Seattle only. Out of scope for an NYC search |

New since the 2026-10-07 report: no new engineering requisition names Omnigent. Only a
**Director, Technical Marketing** (SF, posted 2026-10-08) and the field Solutions
Architect role mention it.

## The CV

### What changed from the LangChain variant, and why

| Change | Reason |
| --- | --- |
| **SASE becomes the first Experience entry:** "Creator & Lead Engineer (full-time since May 2026)", 2025 – present | It fills the gap since May with real, inspectable work. Listed as a project, it reads like a hobby; listed as experience, it is the main qualification for both roles |
| **Google: June 2022 – May 2026** | The user's correction. Also fixed in the [other variants](#committing-it-to-bbugyi200cv) |
| Profile rewritten around **"trustworthy, reproducible"** agent infrastructure, with one line placing SASE in "the same meta-harness category as Databricks' Omnigent" | Mirrors Agent Quality's wording and gives the recruiter the Omnigent connection on first skim. Cut the Omnigent clause for non-Databricks uses |
| Six SASE bullets, each mapped to posting language (table below) | A recruiter skims for posting terms, and a hiring manager looks for design judgment. Each bullet names a mechanism, not a feature count |
| Removed stale claims: "Claude, Gemini, and Codex", Prometheus "33 pipeline metrics", and the renamed ACE and AXE names | Verified against the SASE checkout today. A panel will open the repo |
| Bloomberg reordered so CLDR, now called "release methodology and tooling", sits second. Edgestream leads with the testing framework | Matches the "deployment pipelines" and "testing frameworks" terms |
| Skills trimmed: dropped Perl, Haskell, Vimscript, and LaTeX; added Rust, SQL, SQLite, PyO3, pytest/xdist, GitHub Actions, and Tailscale; added an **Agent Systems** row | Relevance to these postings |
| Open-source section condensed. Star counts refreshed from the GitHub API: funky **671** → "650+", cookie **284** → "280+" | Still true, and slightly stronger |
| Education moved to the end | Standard for 7+ years of experience |
| Contact line adds **sase.sh** and **NYC metro** | Both roles are NYC; the docs site is the best single proof link |

The PDF text extracts cleanly with `mutool`, so Greenhouse parsing should be fine. It
compiles with `pdflatex` to two pages, with the second page about half full. That
matches the existing two-page LangChain variant.

### Posting language → CV line

| Posting phrase | CV line that answers it |
| --- | --- |
| "trustworthy, reproducible signals"; "regression detection" (Agent Quality) | ToolRun bullet: failure signatures, NEW/KNOWN/FLAKY/UNKNOWN, independent witness, unmasked exit codes |
| "testing frameworks … benchmarking infrastructure" (Agent Quality, nice-to-have) | `fakey` bullet; Edgestream test-runner bullet |
| "CI/CD platforms" (Agent Quality); "deployment pipelines" (AI Platform) | Per-SHA master gate, exhaustive lane, and flake-baseline gate; CLDR release methodology |
| "developer platforms or internal tools supporting AI workflows" (AI Platform) | The whole SASE entry, especially the provider contract and routing bullet |
| "scalable APIs … cloud-native infrastructure" (AI Platform) | Rust core bullet (HTTP gateway, fleet dispatch); Google and Bloomberg entries |
| "human in the loop" (several AI postings) | Approval-gates and autonomy-profiles bullet |
| "Agent Framework / AI Gateway" routing (AI Platform) | "cross-provider model-alias routing" |

### What only Bryan can add (marked `% TODO(bryan)` in the source)

1. **Google bullets.** The single Ad Manager line is the weakest part of the CV for the
   AI Platform role, which screens for distributed systems and scalable APIs. Add one or
   two bullets with something concrete: a service owned, a scale figure, a launch, or a
   reliability fix. I could not source these, so I didn't invent any.
2. **One SRE bullet at Bloomberg with a number.** Examples: on-call scope, SLO or
   alerting work, an outage resolved, services owned. Agent Quality asks for "operational
   maturity".

### Claims to be ready to defend

- **"About 16K commits since February 2026 were planned, executed, and verified by
  agents it supervises."** That is accurate: 15,929 commits since 2026-02-14, of which
  11,769 came after 2026-05-01. A skeptical panel will hear "AI slop". Answer the way
  the planned blog post's honesty section does: commit volume is not the claim (as the
  outline puts it, "motion isn't progress"). The claim is the failure handling that makes
  that volume safe to land. If that framing feels wrong for a CV, drop the last bullet;
  nothing else depends on it.
- **Workspace isolation is not sandboxing.** The CV says "isolated workspace clone" and
  never says "sandbox". Providers run with their bypass flags and the operator's
  environment, and Omnigent's OS sandboxes, egress proxy, and credential proxy are
  stronger here. Say so before an interviewer does.
- **Adoption:** sase has 5 GitHub stars and 1 fork, and sase-core has 1 star. Omnigent
  has about 10.7K. Present SASE as a system you run every day and can demo live, not as
  traction.
- **Rust:** sase-core has about 567K lines of `.rs` across about 1,000 files, with 1,534
  commits since 2026-04-28, and much of it was agent-written. Claim "required Rust core
  with PyO3 bindings" and be ready to explain the boundary decision ("if another frontend
  would need it to match, it belongs in core"), not to hand-write unsafe Rust on a
  whiteboard.

### Committing it to `bbugyi200/CV`

The repo's convention is one themed `.tex` plus its compiled `.pdf` per variant, added
with `feat:` commits; for example, `c74c1a2 feat: add LangChain-themed resume variant`.

1. Add `BryanBugyi_Databricks_CV.tex` from
   [Appendix A](#appendix-a-bryanbugyi_databricks_cvtex) and build it with
   `pdflatex BryanBugyi_Databricks_CV.tex`. It needs `plex-sans`, `plex-mono`, and
   `amssymb`, all already present on this machine. Commit the `.tex` and `.pdf` as
   **`feat: add Databricks-themed resume variant`**.
2. In a second commit, **`fix: end Google role in May 2026 across resume variants`**:
   - `BryanBugyi_CV.tex`: `June 2022 - Current` → `June 2022 - May 2026`.
   - `BryanBugyi_Batman_CV.tex`, `BryanBugyi_Google_CV.tex`, and
     `BryanBugyi_LangChain_CV.tex`: `June 2022 -- present` → `June 2022 -- May 2026`.
   - Rebuild all four PDFs.
3. Optional but recommended: port the new SASE Experience entry into the three themed
   variants. At minimum, replace "orchestrates Claude, Gemini, and Codex", "Prometheus
   telemetry surfacing 33 pipeline metrics", and the ACE and AXE names.

## Pitches

Each role gets three lengths: an application note (about 150 words, for Greenhouse's
cover-letter field or a recruiter email), a two-line LinkedIn message, and a 30-second
spoken version for a recruiter screen.

### Staff Software Engineer, Agent Quality

**Application note**

> I build the infrastructure that tells you whether an agent's work can be trusted.
> Since May I've worked full-time on SASE, an open-source control plane that runs seven
> coding-agent CLIs (Claude Code, Codex, Antigravity, and four others) behind one
> contract, with each agent isolated in its own workspace. Its core is a verification
> layer. Every check and test run becomes a durable record with normalized failure
> signatures and a verdict: new, known, flaky, or unknown. "Known" requires an
> independent witness, and exit codes are never masked. A deterministic fake provider
> exercises the launch, streaming, retry, and interrupt paths without model calls, and a
> per-SHA gate and flake baseline keep the signal honest. Before SASE, I spent seven
> years at Google, at Bloomberg as a founding SRE, and at Edgestream, where I worked on
> the test framework and test runner. Agent Quality's flywheel, where evaluation results
> feed back into agent improvement, is the loop I've been building for one operator. I'd
> like to build it for Genie Agents and Databricks' agent platform.

**LinkedIn / InMail (two lines)**

> I spent the last five months full-time building SASE (sase.sh), an open-source control
> plane for seven coding-agent CLIs whose core is reproducible run records and
> regression triage (new, known, flaky, unknown). Before that I was at Google and
> Bloomberg SRE. I've applied to Staff SWE, Agent Quality in NYC and would love 15
> minutes with the team.

**30 seconds, spoken**

> "Seven years of production Python, most recently Google Ad Manager and before that a
> founding SRE at Bloomberg. Since May I've built SASE full-time, a control plane that
> runs Claude Code, Codex, and five other agent CLIs as supervised engineering work. The
> part I'm proudest of is the trust layer: every test run is a durable record, failures
> are classified as new, known, or flaky with evidence, and nothing masks an exit code.
> That's the evaluation-to-improvement loop your posting describes, and I want to build
> it at Databricks scale."

### Sr. Software Engineer – Backend, AI Platform

**Application note**

> I've spent 2026 building the kind of developer platform this org ships. SASE is an
> open-source control plane that puts seven coding-agent CLIs behind one provider
> contract with cross-provider model routing, isolated workspaces, typed human-approval
> gates, and host-owned commits and PRs. Its required Rust core, with PyO3 bindings,
> holds the shared domain logic. It also ships an authenticated HTTP gateway for mobile
> clients and multi-machine dispatch, which the Python CLI, TUI, Telegram, and mobile
> clients all share. Before SASE I spent seven years shipping production Python and
> Java: full-stack on Google Ad Manager, founding engineer on Bloomberg's Compliance SRE
> team (where I authored a release methodology and maintained the firm-wide Python
> scaffolding), and test and lint infrastructure for a 1M+ line trading codebase at
> Edgestream. SASE sits in the same meta-harness category as Omnigent. I'd especially
> like to be considered for the Omnigent, AI Gateway, or Agent Framework teams.

**LinkedIn / InMail (two lines)**

> I'm an ex-Google, ex-Bloomberg SRE engineer who has spent the last five months
> building SASE (sase.sh), an open-source meta-harness for seven coding-agent CLIs with
> a Rust core. I've applied to Sr. SWE – Backend (AI Platform) in NYC and would love to
> be routed toward Omnigent, AI Gateway, or Agent Framework.

**30 seconds, spoken**

> "I've built an agent platform end to end: one provider contract over seven coding-agent
> CLIs, model routing, approval gates, durable work records, and a Rust core with an
> authenticated gateway for multi-machine dispatch. Before that, seven years of
> production Python and Java at Google and Bloomberg SRE. Omnigent made a different bet,
> making the live session durable where SASE makes the work record durable. I'd love to
> bring that perspective to Omnigent, AI Gateway, or Agent Framework."

### "Why did you leave Google, and what have you been doing?"

Use this only if it is true as worded. The vault and the request say Bryan left in May
but don't say why.

> "I left Google in May to build SASE full-time. I'd been running it on nights and
> weekends since 2025, and coding agents were moving fast enough that I wanted to go
> deep while the design space was open. It's now a released PyPI package with a Rust
> core and a docs site, and I use it for all of my engineering work. Omnigent showed me
> Databricks is investing in exactly this layer, so I'm applying now rather than after
> my launch post."

**Pitch hygiene:** don't call SASE a competitor to Omnigent. Use the framing from the
2026-10 SASE-vs-Omnigent research: same problem, different durable object. Omnigent
makes the **live session** durable; SASE makes the **work record** durable. That shows
design judgment and suggests what you would bring to the team.

## LinkedIn, GitHub, and site updates

Do these **before** submitting either application. The vault already tracks this as
`job#^update-goog-end-date` (high priority) and `job#^update-linkedin`.

### LinkedIn

1. **Turn off "Notify network"** in the edit forms while you make these changes. Make
   one public post later, with the blog launch.
2. **Google:** set the end date to **May 2026**. Add one line matching the CV.
3. **Add a position:**
   - **Title:** *Creator & Lead Engineer*.
   - **Employment type:** *Self-employed*.
   - **Company:** *sase* (free text is fine).
   - **Location:** *New York City Metropolitan Area*, location type *Remote*.
   - **Dates:** **May 2026 – Present.** The description says "started as a side project
     in 2025". The CV's "2025 – present (full-time since May 2026)" says the same thing.
   - **Description:** reuse the first three CV bullets in plain text, and link
     https://sase.sh and https://github.com/sase-org/sase.
   - **Skills:** Python, Rust, AI Agents, LLM Evaluation, Developer Tools, CI/CD.

   Don't use LinkedIn's *Career Break* type. It would describe five months of shipped,
   public engineering as time off.
4. **Headline** (under the 220-character limit):

   > Software Engineer · Agent platforms & evaluation infrastructure · Building sase, an
   > open-source control plane for coding agents · ex-Google · ex-Bloomberg
5. **About:**

   > I build the infrastructure that makes coding agents trustworthy enough to hand real
   > work to.
   >
   > Since May 2026 I've worked full-time on sase (sase.sh), an open-source control plane
   > that runs Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, and Grok
   > Build as one supervised team. It provides isolated workspaces, durable run records,
   > and regression triage that separates new failures from known and flaky ones. It
   > also has typed human-approval gates and a Rust core shared by its TUI, CLI,
   > Telegram, and mobile clients. sase is built by agents running under sase.
   >
   > Before that: seven years of production Python and Java. I was full-stack on Google
   > Ad Manager, a founding engineer on Bloomberg's Compliance SRE team, and built test
   > and lint infrastructure for a 1M+ line trading codebase at Edgestream. In open
   > source, I rewrote psf/black's string handling and wrote funky and cookie.
   >
   > Looking for Senior or Staff roles on agent platforms, evaluation, and developer
   > infrastructure in NYC.
6. **Featured:** sase.sh, the sase GitHub repo (its README has the demo GIFs), black PR
   #1132, and the launch post once it is live.
7. **Open to Work:** set it to *recruiters only*. Bryan marked himself active on
   2026-05-31, so refresh the settings:
   - **Titles:** Staff Software Engineer, Senior Software Engineer, Software Engineer –
     AI Platform, Developer Tools Engineer.
   - **Locations:** New York City Metro (on-site or hybrid) and Remote.
   - **Start:** immediately.
8. **Contact info:** add sase.sh as a website. **Banner:** consider
   `docs/images/sase_overview.png` from the SASE repo.
9. **Referral search:** filter Databricks employees in the NYC metro by your Google
   and Bloomberg connections. A referral into the NYC R&D hub beats a cold application.

### GitHub (public profile metadata, checked today)

- **Bio:** keep the joke and update the fact. Change
  `{day: "SWE at Google", night: "Batman of the internet"}` to
  `{day: "building sase (sase.sh)", night: "Batman of the internet"}`.
- **Company:** set it to `@sase-org`. The field is currently empty.
- **Hireable:** turn on "Available for hire". It is currently unset.
- **Pins:** sase-org/sase, sase-org/sase-core, funky, and cookie.
- **Profile README:** optional. There is no `bbugyi200/bbugyi200` repo yet; a
  five-line README pointing at SASE is enough.
- **Personal site:** check that bryanbugyi.com, linked from the GitHub profile, doesn't
  still say Google.

## Application plan and timing

1. **This week:** update LinkedIn and GitHub, commit the CV, then apply to **Agent
   Quality first and AI Platform the same day**. They sit in different orgs (AI Research
   and AI Engineering), so two applications is focused, not scattershot. Tell the
   recruiter about both.
2. **Don't wait for the blog.** sase.sh already serves the docs and the July post. The
   GitHub README, with its demo GIFs, is the stronger first impression anyway. When the
   rewritten launch post ships, send it to the recruiter: "Wanted to share the launch
   post I mentioned".
3. **Close the eval gap between applying and the onsite (one or two weekends).**
   - Record a dozen SASE tasks (beads with acceptance criteria) as an eval set.
   - Run them across providers, logging each run as an **MLflow trace**.
   - Score them with deterministic checks (tests pass, diff stays in scope) plus
     `mlflow.genai.evaluate` LLM-judge scorers.
   - Report regressions by provider and model version, and reuse `fakey` for harness
     self-tests.

   This answers Agent Quality's "how LLM or agent quality is measured" directly. It
   shows working MLflow 3 GenAI evaluation, an AI Platform bonus area. It may also turn
   up a real MLflow issue to fix upstream, which is the "OSS contributions to MLflow"
   bonus.
4. **Calibrate level early.** Ask the recruiter whether Agent Quality would consider
   Senior. Accept a down-level into either team; both are the right door.
5. **Logistics:** both postings say "New York City". Anecdotal reports (Blind, agency
   postings) suggest about three office days a week, with fully remote engineering rare.
   Confirm with the recruiter. Base ranges exclude equity and bonus, which are a large
   part of Databricks pay.

### Interview prep, in brief

- **Loop shape** (third-party and anecdotal): recruiter screen, then one or two coding
  screens, then a four- to five-round virtual onsite. Coding is practical (compile, run,
  debug) rather than LeetCode-style. System design covers concurrency, crash recovery,
  and distributed state. Staff loops add cross-team leadership stories.
- **SASE design stories to rehearse.** For each, give the claim, the rejected
  alternative, the cost, and the trigger that would reopen it, as the SASE decision
  records do.
  - Single-turn agents.
  - Host-owned completion.
  - Triage never changes an exit code.
  - The required Rust core boundary.
  - Two-speed CI.
  - Crash-safe settlement. The latest master commit, `62a8b95c72`
    (`fix(monitor): preserve frozen command outcomes through settlement crashes`), is a
    fresh, concrete example.
- **Agent Quality topics.**
  - Trace-based evaluation.
  - LLM-as-judge failure modes and judge alignment against expert labels.
  - Variance from nondeterministic agents: repeated trials, pass@k, confidence
    intervals.
  - Benchmark contamination.
  - Turning production traces into regression sets: the posting's "flywheel".

## Verified facts used above

| Fact | Value (2026-10-10) | How verified |
| --- | --- | --- |
| Both target postings live | `8842963002` (updated 2026-09-24), `8379331002` (updated 2026-09-21) | Greenhouse board API, 892 postings |
| SASE version, license, harnesses | v0.17.1 (2026-08-29), MIT, 7 harnesses | `pyproject.toml`, `CHANGELOG.md`, `README.md` |
| SASE commits | 15,929 since 2026-02-14; 11,769 since 2026-05-01 | `git rev-list --count` |
| sase-core | 4 crates (`sase_core`, `sase_core_py`, `sase_gateway`, `sase_macro_lsp`); about 1,000 `.rs` files and about 567K lines; 1,534 commits since 2026-04-28 | `sase repo open sase-core`, `git` |
| Prometheus removed | "The bundled Docker Compose, Grafana, Prometheus, and Pushgateway stack has been removed." | `docs/telemetry.md` |
| Triage contract | NEW/KNOWN/FLAKY/UNKNOWN; KNOWN needs an independent witness; exit code preserved | `decisions:triage-annotates-does-not-change-exit-codes` |
| GitHub stats | sase 5★, 1 fork; sase-core 1★; funky 671★; cookie 284★; bio still "SWE at Google" | `gh api` (metadata only) |
| Existing CV variants | Base, Batman, Google, LangChain; all list Google as current; LangChain compiles to 2 pages | `sase repo open gh:bbugyi200/CV`, `pdflatex` |

## Caveats

- This is a 2026-10-10 snapshot. Re-open each posting link the day you apply.
- Interview-loop and hybrid-policy details come from third-party and anonymous sources.
- I don't know why Bryan left Google or what he did there beyond the CV line. The Google
  bullets and the "why did you leave" answer need his facts.
- The Databricks palette approximates public brand colors (lava `#FF3621`, navy
  `#1B3139`). It is a stylistic nod, not official brand assets.
- No applications were submitted, no one was contacted, and nothing was changed in
  `bbugyi200/CV`, LinkedIn, or GitHub.

## Sources

- Databricks Greenhouse board API, `boards-api.greenhouse.io/v1/boards/databricks/jobs?content=true`
  (pulled 2026-10-10). Postings:
  [Agent Quality](https://databricks.com/company/careers/open-positions/job?gh_jid=8842963002),
  [Sr. SWE Backend, AI Platform](https://databricks.com/company/careers/open-positions/job?gh_jid=8379331002),
  [Unity AI Gateway Staff](https://databricks.com/company/careers/open-positions/job?gh_jid=8468436002),
  [AI Research Infrastructure](https://databricks.com/company/careers/open-positions/job?gh_jid=8552484002),
  [Fullstack AI Product](https://databricks.com/company/careers/open-positions/job?gh_jid=8509534002),
  [Sales Data & Agents](https://databricks.com/company/careers/open-positions/job?gh_jid=8760171002),
  [Ads Measurement & Orchestration](https://databricks.com/company/careers/open-positions/job?gh_jid=8760165002).
- Prior research: `databricks_omnigent_job_fit.md` (bob-cli research sidecar,
  2026-10-07); `omnigent_meta_harness_lessons_for_sase.md` and
  `sase_launch_post_outline.md` (sase research sidecar, 2026-10). All read with
  `sase artifact read`.
- [Announcing the Databricks New York R&D hub](https://www.databricks.com/en/blog/announcing-databricks-new-york-rd-hub)
  (2026-01-31); [Omnigent on Databricks docs](https://docs.databricks.com/gcp/en/omnigent/);
  [Databricks unveils Omnigent and LTAP](https://cryptobriefing.com/databricks-omnigent-ltap-summit-2026/).
- [MLflow 3 for GenAI (Databricks docs)](https://docs.databricks.com/aws/en/mlflow3/genai/);
  [MLflow cookbook: Databricks Genie](https://mlflow.org/cookbook/databricks-genie/);
  [Building an evaluation harness for Databricks Genie (codecentric)](https://www.codecentric.de/en/knowledge-hub/blog/reliable-by-design-building-an-evaluation-harness-for-databricks-genie).
- Interview loop (anecdotal): [Codemia Databricks SWE guide](https://codemia.io/guides/databricks-software-engineer);
  Glassdoor reviews ([1](https://www.glassdoor.co.in/Interview/Databricks-Interview-E954734-RVW102430837.htm),
  [2](https://www.glassdoor.co.in/Interview/Databricks-Interview-E954734-RVW102890839.htm)).
- Hybrid policy (anecdotal): [Blind thread](https://www.teamblind.com/post/databricks-on-site-or-hybrid-c0urd4ot);
  [Databricks Data Engineer (Hybrid - NYC) agency listing](https://themomproject.com/projects/databricks-data-engineer-hybrid-nyc-5104786f9e).
- LinkedIn career breaks and resume gaps: [Quartz](https://qz.com/work/2136597/linkedin-now-lets-you-explain-a-break-in-your-work-history);
  [Adweek](https://www.adweek.com/media/linkedin-looks-to-erase-the-stigma-associated-with-career-breaks-in-resumes/);
  [UW PCE](https://www.pce.uw.edu/news-features/articles/ways-approach-gaps-resume).
- Applying to several roles (third-party): [ResumeGeni: How to apply to Databricks](https://resumegeni.com/companies/databricks/how-to-apply).
- Local checkouts: `sase-org/sase` @ `62a8b95c72` (README, CHANGELOG, `docs/telemetry.md`,
  `docs/fakey.md`, `docs/development.md`, `docs/remote_dispatch.md`); `sase-org/sase-core`
  (README, crate layout); `bbugyi200/CV` @ `c74c1a2` (all four `.tex` variants). The Bob
  vault's `job.md` and 2026-10 daily notes were read without modification.

## Appendix A: `BryanBugyi_Databricks_CV.tex`

It compiles with `pdflatex` to two pages. Snapshots: `file:explicit:5030fdba524bbb7f48fd550a`
(TeX) and `file:explicit:d0edce7849a097d298f3e4c8` (PDF).

```latex
% Bryan Bugyi --- Resume (Databricks / agent-platform variant).
%
% Layout heritage: original article-class resume scaffolding by
%   (c) 2002 Matthew Boedicker <mboedick@mboedick.org>
%   (c) 2003-2007 David J. Grant <davidgrant-at-gmail.com>
%   (c) 2008 Nathaniel Johnston <nathaniel@nathanieljohnston.com>
% This work is licensed under CC BY-NC-SA 2.5
% (http://creativecommons.org/licenses/by-nc-sa/2.5/).
%
% Adapted 2026 from the LangChain variant into a Databricks-flavored palette:
% navy anchor with lava accent and a stacked "layer" rule, framed for the
% NYC Agent Quality and AI Platform (backend) roles.

\documentclass[letterpaper,10pt]{article}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Geometry
\usepackage[letterpaper,margin=0.58in,top=0.52in,bottom=0.52in]{geometry}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Palette --- "Lakehouse"
\usepackage[svgnames]{xcolor}
\definecolor{dbxnavy}{HTML}{1B3139}
\definecolor{dbxdeep}{HTML}{2C4A55}
\definecolor{dbxlava}{HTML}{FF3621}
\definecolor{dbxember}{HTML}{C22C1B}
\definecolor{dbxink}{HTML}{161E22}
\definecolor{dbxslate}{HTML}{5A6F77}
\definecolor{dbxline}{HTML}{DCE0E2}
\definecolor{dbxoat}{HTML}{EEEDE9}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Typography
\usepackage{plex-sans}
\usepackage{plex-mono}
\usepackage{microtype}
\usepackage{amssymb}
\renewcommand{\familydefault}{\sfdefault}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Layout / structure packages
\usepackage{enumitem}
\usepackage{fancyhdr}
\usepackage{tabularx}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Page style
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\fancyfoot[C]{{\color{dbxslate}\fontsize{8pt}{9.5pt}\selectfont\thepage}}

\raggedbottom
\raggedright
\setlength{\parskip}{3pt}
\setlength{\parindent}{0pt}
\setlength{\tabcolsep}{0pt}
\frenchspacing

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Small helpers
\newcommand{\midsep}{\,\textcolor{dbxline}{\textbullet}\,}
% Layer rule: three stacked strokes that thin out as they descend, a nod to
% the stacked-layer mark without reproducing it.
\newcommand{\layerbar}{%
  \noindent\textcolor{dbxlava}{\rule{\textwidth}{1.8pt}}%
  \par\vspace{1.4pt}%
  \noindent\textcolor{dbxember}{\rule{\textwidth}{0.8pt}}%
  \par\vspace{1.4pt}%
  \noindent\textcolor{dbxnavy}{\rule{\textwidth}{0.35pt}}%
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Section heading
\newcommand{\resheading}[1]{%
  \par\addvspace{9pt}%
  \noindent
  {\color{dbxlava}\rule[0.12ex]{0.55em}{0.55em}}\hspace{0.45em}%
  {\bfseries\color{dbxnavy}\fontsize{10pt}{12pt}\selectfont%
   \textls*[90]{\MakeUppercase{#1}}}%
  \hspace{0.65em}%
  {\color{dbxline}\leaders\hrule height 0.45pt\hfill\kern0pt}%
  \par\nobreak\addvspace{3pt}%
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Bullets
% Lava lozenge echoes the layered-diamond mark.
\setlist[itemize,1]{
  label={\textcolor{dbxlava}{\scriptsize$\blacklozenge$}},
  leftmargin=1.3em,
  topsep=1pt,
  itemsep=1.5pt,
  parsep=0pt
}
\setlist[itemize,2]{
  label={\textcolor{dbxslate}{\textendash}},
  leftmargin=1.15em,
  topsep=0pt,
  itemsep=0pt,
  parsep=0pt
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Custom commands
% Company / location / role / dates.
\newcommand{\ressubheading}[4]{%
  \par\addvspace{3pt}%
  \noindent
  \begin{tabular*}{\textwidth}{@{}l@{\extracolsep{\fill}}r@{}}
    {\bfseries\color{dbxink}\fontsize{10.4pt}{12.4pt}\selectfont #1} &
    {\color{dbxslate}\fontsize{9.2pt}{11pt}\selectfont #2} \\[0.5pt]
    {\color{dbxdeep}\fontsize{9.9pt}{11.7pt}\selectfont #3} &
    {\color{dbxslate}\fontsize{8.8pt}{10.5pt}\selectfont #4}
  \end{tabular*}\par\vspace{-3pt}
}

% Project / tech-stack / tagline / dates.
\newcommand{\projsubheading}[4]{%
  \par\addvspace{3pt}%
  \noindent
  \begin{tabular*}{\textwidth}{@{}l@{\extracolsep{\fill}}r@{}}
    {\bfseries\color{dbxink}\fontsize{10.4pt}{12.4pt}\selectfont #1} &
    {\ttfamily\color{dbxslate}\fontsize{8.6pt}{10.3pt}\selectfont #2} \\[0.5pt]
    {\color{dbxdeep}\fontsize{9.9pt}{11.7pt}\selectfont #3} &
    {\color{dbxslate}\fontsize{8.8pt}{10.5pt}\selectfont #4}
  \end{tabular*}\par\vspace{-3pt}
}

\newcommand{\skillrow}[2]{%
  {\bfseries\color{dbxnavy}\fontsize{8.8pt}{11pt}\selectfont #1} &
  {\color{dbxink}\fontsize{9.5pt}{11pt}\selectfont #2} \\[1.5pt]
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Hyperlinks (load last)
\usepackage{hyperref}
\hypersetup{
  colorlinks=true,
  urlcolor=dbxember,
  linkcolor=dbxember,
  citecolor=dbxember,
  pdftitle={Bryan Bugyi --- Resume},
  pdfauthor={Bryan Bugyi},
  pdfkeywords={Python, Rust, agent evaluation, AI platform, developer tooling, CI/CD, SRE}
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Document
\begin{document}
\color{dbxink}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%  HEADER
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\noindent
\begin{tabular*}{\textwidth}{@{}l@{\extracolsep{\fill}}r@{}}
  {\bfseries\color{dbxnavy}\fontsize{27pt}{29pt}\selectfont Bryan Bugyi} &
  \begin{minipage}[b]{3.1in}
    \raggedleft
    {\color{dbxslate}\fontsize{9.5pt}{12pt}\selectfont
     Software Engineer\\
     Agent Platforms \& Evaluation Infrastructure}
  \end{minipage}
\end{tabular*}

\vspace{5pt}
\layerbar
\vspace{5pt}

\noindent
{\color{dbxink}\fontsize{9.2pt}{11pt}\selectfont%
\textcolor{dbxnavy}{Email}\,\,\href{mailto:bryanbugyi34@gmail.com}{bryanbugyi34@gmail.com}%
\midsep
\textcolor{dbxnavy}{Phone}\,\,(609)~500-7081%
\midsep
\textcolor{dbxnavy}{GitHub}\,\,\href{https://github.com/bbugyi200}{bbugyi200}%
\midsep
\textcolor{dbxnavy}{LinkedIn}\,\,\href{https://linkedin.com/in/bryan-bugyi}{bryan-bugyi}%
\midsep
\textcolor{dbxnavy}{Docs}\,\,\href{https://sase.sh}{sase.sh}%
\midsep
\textcolor{dbxnavy}{NYC metro}%
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%  PROFILE
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\resheading{Profile}
Software engineer with seven years of production Python, SRE, and developer-tooling work across Google, Bloomberg, and Edgestream. Since May 2026, building \textbf{\texttt{sase}} full-time: an open-source control plane that runs seven coding-agent CLIs as supervised, isolated, \textbf{reproducible} engineering work~--- the same meta-harness category as Databricks' Omnigent. Focused on the infrastructure that makes agents trustworthy: durable run records, regression triage that separates new failures from known and flaky ones, deterministic test harnesses, and human-approval gates agents cannot route around.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%  EXPERIENCE
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\resheading{Experience}

\ressubheading{sase --- Structured Agentic Software Engineering}{Open source \midsep \href{https://github.com/sase-org/sase}{sase-org/sase}}{Creator \& Lead Engineer (full-time since May 2026)}{2025 -- present}
\begin{itemize}
  \item Designed one provider contract over seven agent CLIs (Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, Grok Build) with cross-provider model-alias routing. Each agent is a single-turn job in an atomically claimed workspace clone; the host, never the agent, commits, opens PRs, and records the outcome.
  \item Built the verification layer agents work inside: every check or test execution becomes a durable \textbf{ToolRun} (stage timeline, before/after fingerprints, normalized failure signatures) with a triage verdict~--- \texttt{NEW}, \texttt{KNOWN}, \texttt{FLAKY}, or \texttt{UNKNOWN}~--- where \texttt{KNOWN} requires an independent witness and exit codes are never masked.
  \item Wrote \texttt{fakey}, a deterministic fake provider that drives the real launch, streaming, retry, and interrupt paths with no model calls; paired it with a per-SHA master gate (timing-balanced test shards), a scheduled exhaustive CI lane, and a flake-baseline gate.
  \item Moved shared backend logic into a required Rust core (\href{https://github.com/sase-org/sase-core}{\texttt{sase-core}}, PyO3 bindings) that also ships an authenticated HTTP gateway for mobile clients and multi-machine fleet dispatch, a macro language server, and a SQLite telemetry store.
  \item Shipped typed human-approval gates (plan, question, launch, sudo) answerable from the Textual TUI, CLI, Telegram, or phone, plus autonomy profiles that move chosen checkpoints from human review to recorded automatic decisions.
  \item SASE builds SASE: $\sim$16K commits since February 2026 were planned, executed, and verified by agents it supervises, including multi-provider research swarms whose lead agent checks the evidence behind every disagreement before synthesizing.
\end{itemize}

% TODO(bryan): add one or two concrete Google bullets (service, scale, launch,
% or reliability win) --- the AI Platform backend posting screens for
% distributed systems and scalable APIs, and this entry carries that story.
\ressubheading{Google}{Manhattan, NY}{Software Engineer}{June 2022 -- May 2026}
\begin{itemize}
  \item Full-stack engineer on Google Ad Manager; Java on the backend, Dart / AngularDart / Sass on the frontend.
\end{itemize}

% TODO(bryan): if you can, add one SRE-specific bullet with a number (on-call
% scope, SLO/alerting work, an outage you fixed, services owned). Agent Quality
% screens for "reliability, correctness, and operational maturity".
\ressubheading{Bloomberg L.P.}{Manhattan, NY}{Site Reliability Engineer / Senior Software Engineer}{January 2021 -- May 2022}
\begin{itemize}
  \item Founding engineer on the Compliance SRE (CSRE) team; technical lead across the team's Python portfolio.
  \item Authored the ``ChangeLog Driven Release'' (CLDR) release methodology and tooling; adopted in alpha across the Compliance department.
  \item Maintained Bloomberg's firm-wide Python cookiecutter, shaping new-project scaffolding across the company.
\end{itemize}

\ressubheading{Edgestream Partners, L.P.}{Princeton, NJ}{Software Engineer}{May 2019 -- January 2021}
\begin{itemize}
  \item Delivered large-scale improvements to the production team's in-house testing framework and test runner.
  \item Led integration of \texttt{pylint} into a 1M+ line Python trading codebase; built the supporting tooling to make it stick.
  \item Lead developer of Edgestream's Django-based investor-facing web portal.
\end{itemize}

\ressubheading{Comcast}{Mount Laurel, NJ}{Tier III Technical Support}{2011 -- 2016}
\begin{itemize}
  \item Diagnosed large-scale network outages; automated recurring team workflows (ticketing, spreadsheet parsing, info retrieval) with Python.
\end{itemize}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%  SKILLS
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\resheading{Skills}
\noindent
\begin{tabularx}{\textwidth}{@{}p{1.45in}@{\hspace{0.45em}}X@{}}
\skillrow{Agent Systems}{agent harnesses\,$\cdot$\,provider routing\,$\cdot$\,regression triage\,$\cdot$\,flake detection\,$\cdot$\,approval gates\,$\cdot$\,multi-agent workflows\,$\cdot$\,Claude Code\,$\cdot$\,Codex\,$\cdot$\,Antigravity}
\skillrow{Primary}{Python\,$\cdot$\,Linux\,$\cdot$\,Bash\,$\cdot$\,TCP/IP networking}
\skillrow{Working}{Rust\,$\cdot$\,Java\,$\cdot$\,Dart\,$\cdot$\,C/C++\,$\cdot$\,JavaScript\,$\cdot$\,SQL}
\skillrow{Infrastructure}{GitHub Actions\,$\cdot$\,pytest / xdist\,$\cdot$\,Docker\,$\cdot$\,Git\,$\cdot$\,PostgreSQL\,$\cdot$\,SQLite\,$\cdot$\,Redis\,$\cdot$\,PyO3\,$\cdot$\,Tailscale}
\skillrow{Frameworks}{Textual\,$\cdot$\,FastAPI\,$\cdot$\,Django\,$\cdot$\,Flask\,$\cdot$\,Pluggy\,$\cdot$\,ZeroMQ}
\end{tabularx}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%  SELECTED OPEN SOURCE
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\resheading{Selected Open Source}

\projsubheading{psf/black}{Python}{The uncompromising Python code formatter.}{2019--2021}
\begin{itemize}
  \item Rewrote black's string-handling logic ($\sim$3{,}500 LoC) in \href{https://github.com/psf/black/pull/1132}{PR \#1132}; closed five unrelated user-filed issues in one shot.
\end{itemize}

\projsubheading{python-boltons/*}{Python}{Python libraries we think should be ``builtins''.}{2021--present}
\begin{itemize}
  \item Founder and lead developer: \texttt{cc-python} (cookiecutter)\,$\cdot$\,\texttt{clack} (config CLI)\,$\cdot$\,\texttt{eris} (error handling)\,$\cdot$\,\texttt{hush} (plugin secrets)\,$\cdot$\,\texttt{logrus} (logging).
\end{itemize}

\projsubheading{bbugyi200/*}{Python, Rust, Shell}{Developer tools on GitHub.}{2017--present}
\begin{itemize}
  \item \texttt{funky} (650+ stars; shell-function manager)\,$\cdot$\,\texttt{cookie} (280+ stars; templated file generator)\,$\cdot$\,\texttt{cldr} (ChangeLog Driven Releases)\,$\cdot$\,\texttt{shv} (Rust shell-history viewer).
\end{itemize}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%  EDUCATION
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\resheading{Education}
\ressubheading{Rutgers University}{New Brunswick, NJ}{B.S.\ Computer Science (minor in Mathematics)}{September 2015 -- May 2019}

\end{document}
```
