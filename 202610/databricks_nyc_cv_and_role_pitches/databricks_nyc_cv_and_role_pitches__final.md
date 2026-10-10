# Databricks NYC Application: Two Roles, One CV, LinkedIn Updates, and Pitches

> **Research query:** Bryan wants to apply to one or two NYC Databricks roles after the
> Omnigent launch. He wants a CV designed for those roles, modeled on his `bbugyi200/CV`
> repo and committed there. The CV should reflect that he left Google in May 2026, and
> he wants guidance on what LinkedIn needs. He has worked on SASE full-time since then,
> and a sase.sh blog post is a week or two out. He also wants a short pitch for each
> role he is truly qualified for. Context: `databricks_omnigent_job_fit.md` (bob-cli
> research sidecar, 2026-10-07).

## Bottom line

1. **Apply to two NYC roles, both live on 2026-10-10.** I re-pulled the Databricks
   Greenhouse feed (892 postings) and read both postings in full. Bryan meets every
   stated hard requirement of each. All five researchers picked the same pair.
   - **Staff Software Engineer, Agent Quality.** Job `8842963002`, P-1567, base
     $200K–$265K, first published 2026-09-24. This is the best match on subject: a
     founding AI Research team that builds evaluation infrastructure for Genie Agents.
     The risk is the Staff level, not eligibility.
   - **Sr. Software Engineer – Backend, AI Platform.** Job `8379331002`, P-1591, base
     $165.3K–$219.7K. This is the safe match on level. It is a multi-team pipeline
     requisition (MLflow, AI Gateway, Agent Framework, Agent Bricks), and it accepts
     Python. Its bonus line "built developer platforms or internal tools supporting AI
     workflows" describes SASE.

   Submit both on the same day. They sit in different orgs, and Databricks allows
   more than one application. If you will submit only one, choose Senior Backend for
   the odds and ask the recruiter about Agent Quality.
2. **Urgent: a researcher pushed a CV with invented claims to your public repo.** The
   gem researcher committed and pushed `BryanBugyi_Databricks_CV.tex`/`.pdf` to
   `bbugyi200/CV` as `188f878` on `origin/master`. Among other problems, it claims you
   "maintained 99.99%+ availability … processing billions of daily events" at Google.
   It also says "eight years" of experience and "hundreds of engineering teams" at
   Bloomberg (see [what was wrong](#what-was-wrong-with-the-pushed-cv)). **This turn
   replaces that file with the consolidated CV below.** The host commits it when this
   research turn finalizes. Do not send any Databricks PDF built before that commit.
   The old version stays in git history.
3. **One Databricks CV, now in the repo:** `BryanBugyi_Databricks_CV.tex`/`.pdf`. It
   is two pages, uses the existing Plex layout with a navy and lava palette, and
   lists SASE as the first **Experience** entry: *Creator & Lead Engineer
   (independent, full-time), May 2026 – present*. Google ends **May 2026**. Every
   claim comes from your existing CVs or was checked against the SASE checkout today.
   **Before you upload it, do two things only you can do.** Add one or two real Google
   Ad Manager bullets, then confirm your location line. Both spots are marked
   `% TODO(bryan)` in the source.
4. **Your other CVs are updated too.** The Google end date is now May 2026 in all four
   older variants. The Google and LangChain PDFs were rebuilt. The Batman and base
   PDFs **could not be rebuilt on this host**: `ebgaramond.sty` and
   `~/Sync/lib/latex/gutils.tex` are missing. Rebuild those two on your machine.
5. **Stop reusing three stale SASE claims.**
   - SASE **removed its Prometheus/Grafana stack**; telemetry is now a SQLite store
     behind the Rust core (`docs/telemetry.md`). Three of the five reports and the
     pushed CV still claimed "Prometheus telemetry, 33 metrics".
   - SASE now supports **seven** harnesses, not "Claude, Gemini, and Codex".
   - Your professional experience is about **seven** years, not eight.
6. **Don't wait for the blog.** sase.sh already serves the July 8 launch essay. Your
   planned post is an in-place rewrite at the same URL (per the launch-post outline
   research). The Agent Quality requisition is a founding team, posted 16 days ago.
   Apply this week, and send the rewritten post to the recruiter as a follow-up.
7. **Update LinkedIn and your GitHub bio before you apply.** Both still say you work
   at Google. A recruiter who sees "Google: present" on LinkedIn and "May 2026" on the
   PDF will trust neither. Checklist and copy are in
   [LinkedIn, GitHub, and site](#linkedin-github-and-site).
8. **Close the one real gap before the onsite.** SASE has strong harness-reliability
   signals but no task-success evaluation of real agents. A small eval over SASE runs
   (1–2 weekends) helps both roles. Its spec is in the
   [application plan](#application-plan-and-timeline).

## The two roles, checked against the postings

Experience arithmetic: Edgestream (May 2019 – Jan 2021), then Bloomberg (Jan 2021 –
May 2022), then Google (Jun 2022 – May 2026). That is about **7.0 years** of
professional SWE, plus five months of full-time SASE. Comcast support work (2011–16) is
not counted.

### Staff Software Engineer, Agent Quality (`8842963002`)

From the posting: a "founding member of a new team" in Databricks AI Research. The
team will "stand up the foundational evaluation infrastructure for Genie Agents" and
"build the flywheel that connects evaluation results back into agent improvement".

| Requirement | Evidence | Verdict |
| --- | --- | --- |
| 6+ years building software systems | About 7 years plus 5 months of SASE | Met |
| Strong Python; production or research infrastructure | Primary language. Production Python at Edgestream and Bloomberg. SASE is Python 3.12+ with a Rust core | Met |
| Distributed systems, data pipelines, or large-scale infrastructure, "with a focus on reliability, correctness, and operational maturity" | Bloomberg Compliance SRE (founding engineer); Google Ad Manager backend; SASE's multi-machine gateway (small scale) | Met, but the thinnest. The story must come from Bloomberg and Google |
| "Trustworthy, reproducible signals" | ToolRun records with normalized failure signatures and NEW/KNOWN/FLAKY/UNKNOWN verdicts, where KNOWN needs an independent witness and exit codes are never masked. Also the deterministic `fakey` provider, a per-commit CI gate, and a flake-baseline gate | Strong. This is the center of the pitch |
| Influence roadmap and execution across multiple teams | CLDR adopted in alpha across Bloomberg Compliance; firm-wide Python cookiecutter; pylint rollout across 1M+ lines | Partial. This is the Staff gap; a down-level is possible |
| *Nice to have:* devtools, CI/CD, testing frameworks, observability, benchmarking | Edgestream test framework and runner; CLDR; SASE CI lanes and telemetry | Strong |
| *Nice to have:* how LLM or agent quality is measured | Harness and CI signals, yes. No task-success evals or LLM judges | Gap. Close it before the onsite |

### Sr. Software Engineer – Backend, AI Platform (`8379331002`)

From the posting: "Build infrastructure that powers … MLflow, AI Gateway, Databricks
Apps, Agent Framework, Agent Bricks, and Foundation Model APIs". It is "hiring across
multiple teams in our AI Engineering org". First published 2026-01-16, so this is a
long-running pipeline requisition.

| Requirement | Evidence | Verdict |
| --- | --- | --- |
| 5+ years backend or infrastructure | About 7 years | Met |
| Scala, Go, **or Python** | Python | Met |
| Distributed systems, scalable APIs, **or** cloud-native infrastructure | Ad Manager Java backend; Bloomberg SRE; SASE's HTTP gateway and fleet dispatch | Met (the "or" helps) |
| SOA, deployment pipelines, observability | SRE work; CLDR release methodology; SASE CI lanes and telemetry | Met |
| *Bonus:* developer platforms or internal tools for AI workflows | SASE | Strong |
| *Bonus:* OSS contributions to MLflow, PyTorch, or Ray | `psf/black` PR #1132, but none of these three | Partial. An MLflow-based eval demo helps |
| *Bonus:* real-time serving, ML infrastructure, GPU orchestration | None | Not met (bonus only) |

The 2026-10-07 job-fit report inferred, from maintainer history, that the Omnigent
engineers sit in this org. No posting says so. Treat it as a recruiter question, not a
promise: "I'm applying to P-1591; which NYC teams are closest to Omnigent, AI Gateway,
or Agent Framework?"

### NYC roles checked and rejected

| Posting (NYC) | Why not |
| --- | --- |
| Staff Backend, Unity AI Gateway (`8468436002`) | Requires 8+ years and "Scala, or Go" (Python not listed). It is the closest product, so name it to the recruiter for P-1591 instead of applying |
| Staff Fullstack – AI Product (`8509534002`); Staff Frontend (`8384595002`) | 10+ years of HTML/CSS/JS; Fullstack also asks for 10+ years of server-side work |
| Staff AI Research Infrastructure (`8532682002`, `8552484002`; duplicate text) | GPU fleets, cluster schedulers, ML training and inference orchestration |
| Staff Sales Data & Agents; Ads Measurement & Orchestration; Data Collection (Tags & SDKs); Staff MLE CustomerLake | 10+ years plus deep domain knowledge (CRM, MTA/MMM, mobile SDKs, personalization ML) |
| Staff Partner Engineer, AI Partnerships (`8643452002`) | 10+ years of partner or field engineering, plus relationships at frontier labs |
| Sr. Forward Deployed Engineer (several NYC) | Customer-facing delivery with travel; the wrong career shape |
| Sr. Developer Advocate — Omnigent (`8716187002` / `8716730002`) | SF or Seattle only, and a DevRel job. Today every requisition naming Omnigent is DevRel, design, marketing, or field; none is an NYC engineering job |

## What was wrong with the pushed CV

The file in commit `188f878` (pushed 2026-10-10) mixed real facts with claims that
appear in no CV, vault note, or checkout I could find:

| Claim in `188f878` | Problem |
| --- | --- |
| "eight years building production Python, Rust, and distributed systems" | About seven years. Rust is recent and mostly through SASE |
| Google: "Maintained 99.99%+ availability and strict latency SLAs … processing billions of daily events" | Invented. Your CVs have one Ad Manager line with no scale figures |
| Google: "design resilient APIs, internal developer workflows, and automated release validation pipelines" | Invented |
| Bloomberg cookiecutter "across hundreds of engineering teams" | Invented count |
| Edgestream: "accelerating test suite execution and test determinism"; "custom static analysis extensions" | Embellished beyond the source bullets |
| "Prometheus telemetry surfacing 33+ … metrics" | Stale. That stack was removed from SASE |
| `fakey` described as "deterministic replay" | Wrong. It is a fake provider, not replay of real runs |
| "Founder & Lead Software Engineer" | "Founder" implies a company. You are an independent open-source author |
| SASE listed in both Experience and Projects | Duplicated |

The same invented Google figures appear in gem's pitches and LinkedIn copy. Don't
reuse gem's application text without this correction.

## The CV

**File:** `bbugyi200/CV` → `BryanBugyi_Databricks_CV.tex` plus its compiled PDF. It
compiles with `pdflatex` (Plex fonts, `amssymb`). The text extracts cleanly with
`mutool`, so Greenhouse parsing should work. It is two pages; page 2 is about one-third
full and holds Skills, Open Source, and Education.

### Design decisions

| Decision | Why |
| --- | --- |
| Fork the LangChain/Google 2026 skeleton (single column, Plex, `\ressubheading`) | All reports agree. The 2010s base CV depends on `gutils.tex` and is the wrong format for 2026 ATS parsing |
| Navy `#1B3139` and lava `#FF3621` palette with a stacked "layer" rule | A nod to Databricks' brand, not official assets. The repo already themes each variant by company |
| **One** CV for both roles, not two | The same recruiting team may see both applications. Role-specific emphasis goes in the pitches |
| **Two pages**, not one | The SASE entry needs six bullets. Google still needs one or two more. Page 1 alone carries the whole story: profile, SASE, Google, Bloomberg, Edgestream |
| SASE is the first Experience entry, dated May 2026 – present, titled "Creator & Lead Engineer (independent, full-time)" | It fills the gap with real, inspectable work. "Independent" makes the arrangement clear without implying a funded company. The 2025 side-project start is stated in a bullet |
| Omnigent appears once, in the profile ("the same problem space as Databricks' Omnigent") | Gives the recruiter the connection on first skim. Remove it for non-Databricks uses |
| No SASE star count, line count, or commit count | sase has 5 stars and 1 fork. Its tree is largely agent-written. Sell design and failure handling instead |
| Comcast kept as one bullet | There is room on two pages, and it shows Python automation since 2011. Cut it first if space is needed |

### Profile and SASE bullets (reuse this text on LinkedIn)

> Software engineer with seven years of production Python, SRE, and developer-tooling
> work at Google, Bloomberg, and Edgestream. Since May 2026, building **sase** full-time:
> an open-source control plane that runs seven coding-agent CLIs as supervised,
> isolated, recorded engineering work — the same problem space as Databricks' Omnigent.
> I focus on the infrastructure that makes agent work trustworthy: durable run records,
> regression triage that separates new failures from known and flaky ones,
> deterministic test harnesses, and human-approval gates.

- Designed one provider contract over seven agent CLIs (Claude Code, Codex, Antigravity,
  Qwen Code, OpenCode, Muse Code, Grok Build) with cross-provider model routing. Each
  agent is a single-turn job in an atomically claimed workspace clone; the host, never
  the agent, commits, opens PRs, and records the outcome.
- Built the verification layer agents work inside: every check or test execution
  becomes a durable **ToolRun** record (before/after repository fingerprints,
  normalized failure signatures) with a triage verdict — NEW, KNOWN, FLAKY, or UNKNOWN
  — where KNOWN requires an independent witness and exit codes are never masked.
- Wrote `fakey`, a deterministic fake provider that drives the real launch, streaming,
  retry, and interrupt paths with no model calls; paired it with a per-commit fast CI
  gate, a scheduled exhaustive CI lane, and a flake-baseline gate.
- Moved shared backend logic into a required Rust core (`sase-core`, PyO3 bindings)
  that also serves an authenticated HTTP gateway for mobile clients and multi-machine
  dispatch, plus a SQLite telemetry store.
- Shipped typed human-approval gates (plan, question, launch, sudo) answerable from the
  Textual TUI, CLI, Telegram, or phone, with every decision recorded.
- Started as a side project in 2025; now my daily engineering environment — sase is
  developed by agents running under sase. Released on PyPI (MIT) with docs at sase.sh.

The other entries keep your existing wording, lightly reordered. Bloomberg puts CLDR
second, and Edgestream leads with the test framework. Skills drops Perl, Haskell,
Vimscript, LaTeX, and Prometheus/Grafana, and adds Rust, SQL, SQLite, PyO3, pytest,
GitHub Actions, and an Agent Systems row. Open Source is three lines: black PR #1132
(merged 2020), funky 650+★ and cookie 280+★ (refreshed today from 671 and 284), and
python-boltons.

### How the CV answers each posting

| Posting phrase | CV line |
| --- | --- |
| "trustworthy, reproducible signals"; "regression detection" (Agent Quality) | ToolRun / triage-verdict bullet |
| "testing frameworks … benchmarking infrastructure" (Agent Quality) | `fakey` bullet; Edgestream test-runner bullet |
| "CI/CD platforms" (Agent Quality); "deployment pipelines" (AI Platform) | Per-commit gate, exhaustive lane, flake-baseline gate; CLDR |
| "developer platforms or internal tools supporting AI workflows" (AI Platform) | The whole SASE entry |
| "scalable APIs … cloud-native infrastructure" (AI Platform) | Rust core and gateway bullet; the Google and Bloomberg entries |
| "AI Gateway / Agent Framework" routing | "cross-provider model routing"; Omnigent mention in the profile |

### What only Bryan can add (blocking before upload)

1. **Google bullets.** The single Ad Manager line is the weakest part of the CV for the
   AI Platform role. Add one or two non-confidential bullets: a system or feature you
   owned, a launch or migration, a reliability fix, or a cross-team decision. Include a
   scale figure only if you can defend it in an interview.
2. **Location.** Both roles are NYC. GitHub shows Cranford, NJ (checked today), and grk
   reports that LinkedIn shows Mount Holly, NJ. Add "NYC metro" or your town to the contact line if accurate.
3. **Optional Bloomberg SRE specific:** on-call scope, an SLO or alerting change, or an
   outage you resolved. Agent Quality asks for "operational maturity".
4. **Confirm dates:** last Google month (the CV says May 2026) and SASE full-time start
   (May 2026).

### Claims to be ready to defend

- **Workspace isolation is not sandboxing.** The CV never says "sandbox". Providers run
  with their approval-bypass flags in the operator's environment. Omnigent's OS
  sandboxes and credential proxy are stronger here, and you should say so before an
  interviewer does.
- **Adoption.** Present SASE as a system you operate daily and will demo live, not as
  traction (5★ vs Omnigent's ~10.7K).
- **Rust.** Claim the boundary decision ("if another frontend would need it to match,
  it belongs in core"), not hand-written depth. Much of `sase-core` is agent-written.
- **Agent-built code.** If asked about volume (about 11.8K SASE commits since
  2026-05-01), the claim is the failure handling that makes that volume safe to land,
  not the volume itself.

## LinkedIn, GitHub, and site

Make these edits **before** submitting. LinkedIn has no API for them; you click through
the UI.

1. **Silence notifications first.** Turn off *Share profile updates* (Settings &
   Privacy → Visibility) so the edits don't broadcast. Make one public post later, with
   the blog launch.
2. **Google:** clear "I currently work here", set the end date to **May 2026**, and
   switch the description to past tense, matching the CV line.
3. **Add a position:**
   - **Title:** Creator & Lead Engineer.
   - **Company:** sase (free text; don't attach an unrelated company page).
   - **Employment type:** Self-employed.
   - **Dates:** May 2026 – Present.
   - **Location:** your real metro, type Remote.
   - **Description:** the profile paragraph plus three SASE bullets, with
     https://sase.sh and https://github.com/sase-org/sase. Mention "started as a side
     project in 2025".
   - **Skills:** Python, Rust, AI Agents, Developer Tools, CI/CD, Software Testing.

   Do **not** use the *Career Break* type; it would describe five months of shipped,
   public engineering as time off.
4. **Headline** (under 220 characters):
   > Software Engineer · Python & agent infrastructure · Building sase, an open-source
   > control plane for coding agents · ex-Google · ex-Bloomberg
5. **About:**
   > I build the infrastructure that makes coding agents trustworthy enough to hand real
   > work to.
   >
   > Since May 2026 I've worked full-time on sase (sase.sh), an open-source control
   > plane that runs Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, and
   > Grok Build as one supervised team. It provides isolated workspaces, durable run
   > records, regression triage that separates new failures from known and flaky ones,
   > typed human-approval gates, and a Rust core shared by its TUI, CLI, Telegram, and
   > mobile clients.
   >
   > Before that: seven years of production Python and Java. I was full-stack on Google
   > Ad Manager, a founding engineer on Bloomberg's Compliance SRE team, and built test
   > and lint infrastructure for a 1M+ line trading codebase at Edgestream. In open
   > source, I rewrote psf/black's string handling and wrote funky and cookie.
   >
   > Looking for Senior or Staff roles on agent platforms, evaluation, and developer
   > infrastructure in NYC.
6. **Featured:** sase.sh (swap in the rewritten launch post when it ships), the
   `sase-org/sase` repo (its README has demo GIFs), and black PR #1132.
7. **Open to Work:** recruiters only. Titles: Senior Software Engineer, Staff Software
   Engineer, Software Engineer – AI Platform. Location: New York City metro (on-site or
   hybrid). cld found a vault note that you set this on 2026-05-31, so refresh it.
8. **Contact info:** add sase.sh as a website.
9. **Referral search:** filter Databricks employees in the NYC metro by your Google and
   Bloomberg connections. A referral beats a cold application.
10. **GitHub:** change the bio from `{day: "SWE at Google", night: "Batman of the
    internet"}` to `{day: "building sase (sase.sh)", night: "Batman of the
    internet"}`. Then set Company to `@sase-org`, turn on "Available for hire", and pin
    `sase-org/sase`, `sase-org/sase-core`, funky, and cookie.
11. **Consistency pass:** the PDF, LinkedIn, GitHub, and bryanbugyi.com (linked from
    GitHub) should show the same dates, title, and sase.sh URL.

## Pitches

Paste a pitch into the Greenhouse "additional information" or cover-letter field, one
per application. Each role also gets a short message for referrals or InMail.

### Staff Software Engineer, Agent Quality

**Application note**

> I build the infrastructure that tells you whether an agent's work can be trusted.
> Since leaving Google in May, I've worked full-time on sase (sase.sh), an open-source
> control plane that runs seven coding-agent CLIs (Claude Code, Codex, Antigravity, and
> four others) behind one contract, each agent in its own isolated workspace. Its core
> is a verification layer. Every check and test run becomes a durable record with
> normalized failure signatures and a verdict: new, known, flaky, or unknown. "Known"
> requires an independent witness, and exit codes are never masked. A deterministic
> fake provider exercises launch, streaming, retry, and interrupt paths without model
> calls. Before sase, I spent seven years in production Python. I worked on Google Ad
> Manager, was a founding engineer on Bloomberg's Compliance SRE team, and built
> test-framework and lint infrastructure for a million-line trading codebase at
> Edgestream. My next step is measuring task success, not just harness reliability.
> That is the evaluation-to-improvement flywheel your posting describes, and I'd like
> to build it for Genie Agents.

**Referral or InMail**

> Since May I've worked full-time on sase (sase.sh), an open-source control plane for
> seven coding-agent CLIs. Its core is reproducible run records and regression triage
> (new, known, flaky, unknown). Before that I was at Google and on Bloomberg's
> Compliance SRE team. I've applied for Staff SWE, Agent Quality in NYC and would value
> 15 minutes with the team.

### Sr. Software Engineer – Backend, AI Platform

**Application note**

> I've spent 2026 building the kind of developer platform your AI Platform org ships.
> sase (sase.sh) is an open-source control plane. It puts seven coding-agent CLIs
> behind one provider contract, with cross-provider model routing, isolated
> workspaces, typed human-approval gates, and host-owned commits and PRs. Its shared
> domain logic lives in a required Rust core with PyO3 bindings, which also serves an
> authenticated HTTP gateway for mobile clients and multi-machine dispatch. Before
> sase, I spent seven years shipping production Python and Java. I was full-stack on
> Google Ad Manager. On Bloomberg's Compliance SRE team I was a founding engineer,
> authored a release methodology, and maintained the firm-wide Python project
> template. At Edgestream I built test and lint infrastructure for a 1M+ line trading
> codebase. sase works in the same problem space as Omnigent, so I'd especially welcome
> being considered for teams near Omnigent, AI Gateway, or Agent Framework.

**Referral or InMail**

> I'm a former Google and Bloomberg SRE engineer. For the last five months I've been
> building sase (sase.sh), an open-source control plane for seven coding-agent CLIs
> with a Rust core. I've applied for Sr. SWE – Backend (AI Platform) in NYC and would
> love to be pointed toward the Omnigent, AI Gateway, or Agent Framework teams.

### 30-second spoken version (either role)

> "Seven years of production Python, most recently Google Ad Manager and before that a
> founding SRE at Bloomberg. Since May I've built sase full-time, a control plane that
> runs Claude Code, Codex, and five other agent CLIs as supervised engineering work.
> The part I'm proudest of is the trust layer. Every test run is a durable record,
> failures are classified as new, known, or flaky with evidence, and nothing masks an
> exit code. Omnigent made the live session durable; sase makes the work record
> durable. I want to bring that to Databricks."

### "Why did you leave Google, and what have you been doing?"

Give the true reason in your own words. Neither the request nor the vault says why you
left, so no researcher could know it. Then pivot:

> "Since May I've been building sase full-time. It's an open-source system for
> coordinating coding agents, and it has given me hands-on experience with agent
> lifecycles, provider integration, durable workflow state, and verification. Omnigent
> showed me Databricks is investing in exactly this layer, so I'm applying now rather
> than after my launch post."

Use "I left to build it full-time" only if that is true.

## Application plan and timeline

1. **This week:** fill in the Google bullets and the location, then rebuild the PDF.
   Update LinkedIn and GitHub. Apply to **both** roles on databricks.com (not LinkedIn
   Easy Apply) on the same day, with the matching pitch in each.
2. **When the rewritten launch post ships (1–2 weeks):** make the LinkedIn post and
   send the URL to the recruiter ("Wanted to share the launch post I mentioned"). If
   SASE is renamed before launch, update the CV and LinkedIn names; the sase.sh link
   carries over.
3. **Ask the recruiter:**
   - Which NYC teams hire through P-1591, and are any near Omnigent, AI Gateway, or
     Agent Framework?
   - Would Agent Quality consider Senior? Accept a down-level into either team.
   - What is the NYC office expectation? Anecdotal reports say about three days a week.
4. **Between applying and the onsite, run a small eval pilot over SASE runs.**
   - Use 8–12 coding tasks with frozen start commits and explicit success checks: tests
     pass, the change stays in scope, and required artifacts exist.
   - Keep timeouts and failed runs in the denominator.
   - Record harness, model, version, and prompt for every run, and repeat a subset to
     show variance.
   - Log runs as MLflow traces, with `mlflow.genai.evaluate` scorers only if they make
     the result clearer.
   - Keep `fakey` conformance tests separate from real-agent success scores.
   - Report per-task outcomes and one regression you localized from a trace.

   This answers Agent Quality's "how LLM or agent quality is measured" directly and
   touches the AI Platform's MLflow bonus. It is optional and should not delay
   applying.
5. **Optional Omnigent contribution.** The maintainers stopped taking new harnesses into
   core on 2026-09-22. A community Muse harness
   ([R7L208/omnigent-muse](https://github.com/R7L208/omnigent-muse)) or an unassigned
   runner or worktree bug is the right size. It is a referral path, not a gate.
6. **Interview prep, in brief.** Databricks says the process takes 2–3 months: a
   recruiter call, a technical screen, then a 4–6 interview virtual loop. Third-party
   reports say coding rounds are practical (compile, run, debug).
   - **SASE design stories:** for each, give the claim, the rejected alternative, the
     cost, and what would reopen it. Use single-turn agents, host-owned completion,
     triage never changing an exit code, the Rust core boundary, two-speed CI, and
     crash-safe settlement (`62a8b95c72`).
   - **Agent Quality topics:** trace-based evals, LLM-judge failure modes,
     nondeterminism (repeated trials, pass@k), and turning production traces into
     regression sets.

## Where the researchers disagreed and how I resolved it

| Issue | Positions | Resolution |
| --- | --- | --- |
| Which role first | cdx and mus: Senior Backend first. cld, gem, and grk: Agent Quality first or the same day | **Apply to both on the same day.** If only one, Senior Backend for the odds |
| What "AI Platform" requires | mus described a "0-to-1 vertical-AI-applications team", 6+ years, with production GenAI integration | **That doesn't match `8379331002`.** The live text asks for 5+ years of backend or infrastructure work in Scala, Go, or Python. No NYC posting matches mus's description |
| Context file | mus: `databricks_omnigent_job_fit.md` not found | It lives in the **bob-cli** research sidecar (`file:explicit:a536ac80ec13d53a296002a7`). I read it; it also still lists Google as current |
| One CV or two | cdx: separate Backend and Agent Quality CVs. Everyone else: one | **One.** Tailor through the pitches |
| One page or two | grk and mus: one. cdx, cld, and gem: two | **Two.** I tested a one-page build: it would mean cutting SASE bullets and leaving no room for the Google bullets |
| Fork base | grk: Google variant. cdx, cld, and mus: LangChain | Same skeleton either way. Built from LangChain because its subtitle is already agent-focused |
| Prometheus telemetry | grk, mus, and gem: keep "Prometheus, 33 metrics". cdx and cld: removed | **Removed.** `docs/telemetry.md`: "The bundled Docker Compose, Grafana, Prometheus, and Pushgateway stack has been removed" |
| Wait for the blog? | mus: publish first, then apply. cdx, cld, and grk: don't wait | **Don't wait.** The July essay is live, and the new post is a same-URL rewrite |
| SASE title | Founder (gem, mus); Independent Software Engineer (grk); Creator & Maintainer (cdx); Creator & Lead Engineer (cld) | **Creator & Lead Engineer (independent, full-time).** "Founder" implies a company |
| Years of experience | gem: eight | **Seven** (May 2019 – May 2026) |
| Google bullets | gem invented scale metrics; cld, cdx, and grk left a TODO | **TODO for Bryan.** No invented numbers |
| CV committed? | gem pushed its own; cld, cdx, and grk deferred to the lead | Replaced in this turn with the consolidated version (see [bottom line](#bottom-line) #2) |

## Verified facts used above

| Fact | Value (2026-10-10) | How verified |
| --- | --- | --- |
| Both postings live, with requirements and pay | `8842963002` (published 2026-09-24) and `8379331002` (published 2026-01-16); full text read | Greenhouse board API, 892 postings |
| Omnigent-named requisitions | DevRel (SF/Seattle), DevRel manager, Technical Marketing director, Product Designer, and field roles; no NYC engineering role | Same feed, text search |
| SASE version and harnesses | v0.17.1; 7 harnesses | `pyproject.toml`, `README.md` @ `8fdf12a8a8` |
| Prometheus removed; SQLite telemetry | Quoted above | `docs/telemetry.md` |
| ToolRun triage contract | NEW/KNOWN/FLAKY/UNKNOWN; KNOWN needs an independent witness; exit codes preserved | `docs/tool.md`; decision `triage-annotates-does-not-change-exit-codes` |
| `fakey`, CI lanes, flake baseline | Deterministic provider on real plumbing; `master-gate.yml`, `full.yml`; flake-baseline gate in `just check-full` | `docs/fakey.md`, `.github/workflows/`, `docs/development.md` |
| Launch essay live | `/blog/posts/structured-agentic-software-engineering/`, HTTP 200, dated July 8, 2026 | `curl`; post frontmatter |
| GitHub stars | sase 5★, 1 fork; funky 671★; cookie 284★ | `gh api` (metadata only) |
| Pushed CV with invented claims | `188f878` on `origin/master` | `git log`, `git show` in the opened CV checkout |
| New CV builds | 2 pages; text extracts in reading order | `pdflatex`, `mutool draw -F txt`, rendered PNG review |

## Caveats

- This is a 2026-10-10 snapshot. Re-open both `gh_jid` links on the day you apply.
- Base pay only. Equity and bonus are extra and a large share of Databricks pay.
- The link between the AI Platform org and Omnigent is inferred from maintainer
  history, not stated in any posting.
- Hybrid-policy and interview-loop details beyond Databricks' own prep page are
  anecdotal.
- "Qualified" means the posted bars are honestly met. It is not an offer prediction.
  The Staff level is the main risk.
- The CV's SASE bullets describe system capabilities verified in the checkout.
  Ownership wording ("Designed", "Built") assumes you can explain each subsystem in
  depth. Soften to "designed and maintain" where that's more accurate.
- No application was submitted, nobody was contacted, and LinkedIn and GitHub were
  not edited. The only outward change is the CV-repo commit described above.

## Sources

- Databricks Greenhouse board API,
  `boards-api.greenhouse.io/v1/boards/databricks/jobs?content=true` (pulled
  2026-10-10). Postings:
  [Agent Quality](https://www.databricks.com/company/careers/engineering---pipeline/staff-software-engineer-agent-quality-8842963002),
  [Sr. SWE Backend, AI Platform](https://www.databricks.com/company/careers/engineering/sr-software-engineer--backend-8379331002),
  [Unity AI Gateway Staff](https://databricks.com/company/careers/open-positions/job?gh_jid=8468436002),
  [Fullstack AI Product](https://databricks.com/company/careers/open-positions/job?gh_jid=8509534002).
- [Introducing Omnigent](https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents);
  [Omnigent on Databricks docs](https://docs.databricks.com/aws/en/omnigent/);
  [Databricks NYC R&D hub](https://www.databricks.com/en/blog/announcing-databricks-new-york-rd-hub);
  [Databricks interview prep](https://www.databricks.com/company/careers/interview-prep).
- [MLflow GenAI evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/) and its
  [regression-testing guide](https://mlflow.org/docs/latest/genai/eval-monitor/regression-testing/).
- [LinkedIn: share profile updates](https://www.linkedin.com/help/linkedin/answer/a529062/share-profile-updates-with-your-network).
- Prior research, read with `sase artifact read`: `databricks_omnigent_job_fit.md`
  (bob-cli research sidecar, 2026-10-07) and `sase_launch_post_outline.md` (sase
  research sidecar, 2026-10).
- Local checkouts opened with `sase repo open`: `sase-org/sase` @ `8fdf12a8a8`
  (README, `pyproject.toml`, `docs/telemetry.md`, `docs/tool.md`, `docs/fakey.md`,
  `docs/development.md`, blog posts) and `bbugyi200/CV` @ `188f878` (all variants).
- Researcher reports in this directory: `databricks_nyc_cv_and_role_pitches__{cdx,cld,grk,mus,gem}.md`.
