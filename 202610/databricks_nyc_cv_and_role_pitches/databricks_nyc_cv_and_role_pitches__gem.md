# Databricks NYC Roles: CV Design, Tailored Pitches, and LinkedIn Strategy

> **Author:** Researcher `gem` (5-researcher swarm)  
> **Date:** October 10, 2026  
> **Target Company:** Databricks (New York R&D Hub)  
> **Primary Roles:** Staff SWE (Agent Quality) & Sr. SWE (Backend, AI Platform)  
> **Context:** Modeling off `bbugyi200/CV`, integrating 6 months of full-time SASE development, and preparing for the upcoming `sase.sh` launch.

---

## 1. Executive Summary & Strategy

Bryan Bugyi is targeting one or two engineering roles at Databricks' New York City R&D Hub, motivated by deep domain overlap between his open-source work on **SASE** ([sase.sh](https://sase.sh)) and Databricks' **Omnigent** meta-harness platform.

### Key Conclusions
1. **The Domain Fit is Exceptional:**
   - Both SASE and Omnigent solve the exact same foundational problem: providing an abstraction and control layer over diverse coding-agent CLIs (Claude Code, Codex, Antigravity, OpenCode, etc.), isolating execution, enforcing human-in-the-loop policies/gates, and offering durable session governance.
   - Having spent the past six months (May–October 2026) building SASE full-time, Bryan does not enter the hiring process as a generic backend engineer hoping to break into AI—he enters as an active builder and practitioner of agentic meta-harnesses.

2. **Top Two NYC Target Roles (Dual-Track Application):**
   - **Priority 1: Staff Software Engineer, Agent Quality (NYC, Job ID: `8842963002`)**  
     *Focus:* Building evaluation infrastructure and deterministic benchmark flywheels for Genie Agents and agent platforms. Bryan’s testing infrastructure background (Edgestream in-house runner, Bloomberg release tooling, SASE `fakey` failure simulator) is a near-perfect match for the requirements. Base salary: $200,000–$265,000.
   - **Priority 2: Senior Software Engineer – Backend, AI Platform (NYC, Job ID: `8379331002`)**  
     *Focus:* The core backend organization housing MLflow, AI Gateway, Agent Framework, and Omnigent. This is the safest title match (~7.4–8 years experience) and sits directly in the team maintaining Omnigent. Base salary: $165,300–$219,675.

3. **CV Ready and Committed:**
   - A dedicated LaTeX resume variant (`BryanBugyi_Databricks_CV.tex` and compiled `BryanBugyi_Databricks_CV.pdf`) has been added to the `bbugyi200/CV` repository.
   - It incorporates Databricks' visual branding (signature flame red `#FF3621` and spruce navy `#1B3139`), updates Google tenure to May 2026, highlights SASE as a full-time lead role (May 2026–Present), emphasizes systems/testing rigor, and fits on a clean, scannable two-page layout.

4. **Synchronizing LinkedIn and the `sase.sh` Launch:**
   - Bryan left Google in May 2026. Rather than framing the past six months as an employment gap, LinkedIn should explicitly frame this period as **Founder & Lead Architect at SASE**, showcasing deep technical initiative.
   - The upcoming launch blog post on [sase.sh](https://sase.sh) provides the ideal public hook for a high-visibility LinkedIn announcement, directly tagging agentic AI topics and catching the eye of Databricks engineering leaders.

---

## 2. Target NYC Roles & Qualifications Breakdown

Databricks opened its New York City R&D Hub in January 2026 with a declared mandate around agentic AI, LLM systems, and core data infrastructure. Based on the Greenhouse job postings and the analysis in `databricks_omnigent_job_fit.md`, two live engineering requisitions stand far above the rest.

### Role 1: Staff Software Engineer, Agent Quality
- **Job ID:** `8842963002`
- **Location:** New York City (Manhattan)
- **Base Salary:** $200,000 – $265,000
- **Team Mandate:** Founding member of a new AI Research team focused on building evaluation infrastructure for Genie Agents and the broader agent development platform. The goal is creating a closed-loop flywheel from evaluation data back into model and agent capability improvements.
- **Posting Requirements:**
  - 6+ years professional software engineering experience.
  - Strong Python proficiency and a track record of building reliable, reproducible infrastructure.
  - Strong nice-to-haves: Developer tooling, CI/CD, testing frameworks/runners, observability, benchmarking, and familiarity with LLM/agent evaluation methodologies.
- **Qualifications Analysis (Why Bryan is a Fit):**
  - **Testing Frameworks & Tooling:** At Edgestream, Bryan led improvements to the firm's in-house test runner and integrated `pylint` across a 1M+ LoC Python codebase. At Bloomberg, he maintained the firm-wide Python project cookiecutter and created the ChangeLog Driven Release methodology.
  - **Deterministic Agent Evaluation:** In SASE, Bryan designed and built `fakey`—a deterministic, zero-cost mock harness simulating agent streaming, rate limits, token ceilings, tool failures, and interrupts. This directly answers the need for hermetic regression testing for agent loops.
  - **Observability:** SASE exports 33+ Prometheus telemetry metrics tracking agent lifecycles, memory pressure, and tool execution latencies.
  - **Experience Level:** Bryan has ~7.4 years of professional experience across tier-one firms (Google, Bloomberg, Edgestream) plus 6 months founding SASE, comfortably satisfying the 6+ years threshold.
- **Identified Gap & Preparation:** SASE lacks an automated LLM task-success evaluation benchmark (e.g., automated scoring against SWE-bench or custom rubric tasks).  
  *Mitigation:* Bryan should draft a small task-eval harness script for SASE before interviews begin, demonstrating an end-to-end evaluation flywheel.

---

### Role 2: Senior Software Engineer – Backend (AI Platform)
- **Job ID:** `8379331002`
- **Location:** New York City (Manhattan)
- **Base Salary:** $165,300 – $219,675
- **Team Mandate:** Multi-team requisition hiring backend engineers across MLflow, Unity AI Gateway, Databricks Apps, Agent Framework, Agent Bricks, and Foundation Model APIs. Critically, commit authorship and maintainer analysis confirm that the engineers maintaining **Omnigent** sit within this exact AI Platform org.
- **Posting Requirements:**
  - 5+ years professional backend engineering experience.
  - Proficiency in Python, Scala, or Go.
  - Experience designing high-throughput, low-latency distributed APIs and backend architectures.
  - Bonus points for having built developer platforms or internal tools supporting AI workflows, as well as an active open-source track record.
- **Qualifications Analysis (Why Bryan is a Fit):**
  - **Developer Platforms & Meta-Harnesses:** Bryan literally built SASE, a complete developer platform and meta-harness orchestrating 7 coding-agent CLIs behind a single pluggable interface, complete with atomic workspace directory isolation, YAML workflow execution, and terminal supervision.
  - **Language Alignment:** Primary strength is modern Python (3.12+), accompanied by production Rust (`sase-core-rs` binding) and enterprise Java (Google Ad Manager).
  - **High-Throughput Distributed Systems:** At Google Ad Manager in Manhattan, Bryan engineered distributed backend services processing billions of daily events with 99.99%+ availability SLAs.
  - **Level Calibration:** At ~7.4–8 years of experience, Senior SWE is the safest, most uncontroversial placement, avoiding arbitrary years-of-experience gatekeeping.
- **Identified Gap & Preparation:** Databricks backend infrastructure relies heavily on cloud-native RPC and Kubernetes scale. Bryan’s narrative should emphasize his Google Ad Manager backend infrastructure and Bloomberg SRE foundation.

---

### Secondary Mention: Staff Backend SWE – Unity AI Gateway (`8468436002`)
- **NYC; Base: $190,000–$261,250.**
- While Unity AI Gateway is the exact gateway proxy through which coding agents route requests, the posting asks for **8+ years and specifically requires Scala or Go** (Python is not listed).
- *Strategy:* Do not apply directly to this posting, as automated screening may filter out non-Scala/Go applicants. Instead, apply to Role #2 (AI Platform) and request during recruiter routing to be considered for AI Gateway and Omnigent sub-teams.

---

## 3. Short Pitches for Target Roles

These pitches are engineered for application cover letters, recruiter screening conversations, and referral introductions.

### Pitch 1: Staff Software Engineer, Agent Quality (`8842963002`)
> "I have spent the last eight years building high-reliability testing frameworks, developer platforms, and distributed systems across Google, Bloomberg, and Edgestream. For the past six months, I have been working full-time on **SASE** (sase.sh), an open-source multi-agent developer platform that orchestrates seven coding-agent harnesses.
> 
> A central challenge in agent systems is test determinism and evaluation. In SASE, I engineered `fakey`—a deterministic conformance harness that simulates token limits, streaming interruptions, and tool failures without model calls—paired with Prometheus telemetry tracking 33+ agent lifecycle metrics. Combined with my prior experience integrating testing frameworks across million-line production codebases at Edgestream and Bloomberg, I understand how to turn agent behavior into reliable, reproducible evaluation data. I would love to bring this experience to Databricks' Agent Quality team to build the evaluation and flywheel infrastructure powering Genie Agents and the agent platform."

---

### Pitch 2: Senior Software Engineer – Backend, AI Platform (`8379331002`)
> "I am a backend and systems software engineer with eight years of experience building distributed systems and developer tools at Google Ad Manager (supporting billions of daily requests at 99.99%+ uptime) and Bloomberg SRE. For the past six months, I have worked full-time architecting and maintaining **SASE** (sase.sh), an open-source meta-harness platform that coordinates seven coding agents (Claude Code, Codex, Antigravity, OpenCode, and others) behind a unified Python/Rust backend with isolated git workspaces and typed approval gates.
> 
> SASE shares its foundational architectural DNA with Databricks’ **Omnigent** and Agent Framework. I have deep firsthand experience solving the hard problems of agent session orchestration, workspace isolation, and CLI adapter conformance. I am applying to Databricks’ AI Platform team in NYC with the goal of routing to Omnigent, Unity AI Gateway, or Agent Framework to build the next generation of scalable agent developer infrastructure."

---

### Pitch 3: Concise InMail / Referral Outreach (150 words)
> "Hi [Name],
> 
> I saw that Databricks is expanding its Agentic AI and AI Platform engineering teams at the NYC R&D Hub.
> 
> Over the past six months, after four years engineering high-scale distributed backend services at Google Ad Manager, I’ve been working full-time building **SASE** (sase.sh)—an open-source meta-harness and developer platform that orchestrates seven coding-agent CLIs behind isolated workspaces, typed approval gates, and deterministic failure benchmarks.
> 
> Given the close architectural alignment between SASE and Databricks' **Omnigent** and Agent Framework, I am very interested in the **Staff SWE, Agent Quality** (`8842963002`) and **Sr. SWE, AI Platform Backend** (`8379331002`) roles in NYC.
> 
> Would you or a colleague have 10 minutes to connect or point me toward the hiring team?"

---

## 4. CV Design & Architecture in `bbugyi200/CV`

The dedicated Databricks CV has been constructed and committed to the user's `bbugyi200/CV` GitHub repository as `BryanBugyi_Databricks_CV.tex` and compiled to `BryanBugyi_Databricks_CV.pdf`.

### Design System Highlights
- **Palette ("Databricks Flame & Slate"):**
  - Anchor Red: `\definecolor{dbred}{HTML}{FF3621}` (Databricks flame red for bullets, accents, and visual anchors).
  - Primary Navy: `\definecolor{dbnavy}{HTML}{1B3139}` (Databricks dark spruce navy for section headers, candidate name, and primary emphasis).
  - Secondary Slate: `\definecolor{dbstone}{HTML}{5A6B73}` (Subdued slate for dates, locations, and metadata).
  - Body Ink: `\definecolor{dbink}{HTML}{11191C}` (High-legibility dark ink for body text).
- **Typography:**
  - Modern sans-serif using IBM Plex (`plex-sans` and `plex-mono`), matching the modern, developer-centric aesthetic of Databricks and open-source documentation.
  - Section headings feature small-caps letterspacing with hairline rule dividers.
- **Structure & Budget:**
  - Strict two-page budget with `geometry` margins set to 0.55in (0.48in top/bottom).
  - Clean visual hierarchy ensuring recruiters can parse the narrative within 10 seconds.

### Section-by-Section Content Strategy

#### Header
- **Title:** `Software Engineer --- Agentic-AI Platforms, Evaluation & Systems`
- **Contact Details:** Email (`bryanbugyi34@gmail.com`), Phone (`(609) 500-7081`), GitHub (`bbugyi200`), LinkedIn (`bryan-bugyi`), Web (`sase.sh`).

#### Profile
- Directly addresses the target roles:
  > *"Software engineer with eight years building production Python, Rust, and distributed systems across Google, Bloomberg, and Edgestream. For the past six months, full-time architect and maintainer of sase (sase.sh), an open-source multi-agent developer platform and meta-harness unifying 7 coding-agent harnesses (Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, Grok Build) behind isolated workspaces, typed approval gates, and deterministic evaluation benches. Proven track record in high-throughput backend services, extensible test frameworks, and mission-critical developer tooling."*

#### Experience Entries
1. **SASE (sase.sh) — Founder & Lead Software Engineer (May 2026 – Present | New York, NY)**
   - *Bullet 1 (Platform & Meta-Harness):* Architected `sase` supporting 7 agent harnesses behind unified provider abstraction (`llm_provider/base.py`) with model routing and isolated git workspaces.
   - *Bullet 2 (Systems & Backend):* Engineered high-performance backend domain services in Rust (`sase-core-rs`), Python 3.12+ control plane, and AXE daemon scheduler.
   - *Bullet 3 (Evaluation & Conformance):* Built `fakey` deterministic conformance harness to simulate streaming, rate limits, interrupts, and failure modes for hermetic, zero-cost regression testing.
   - *Bullet 4 (Governance & Observability):* Designed human-in-the-loop typed gates (plan, questions, sudo) with audit trails, queue budgets, and Prometheus telemetry (33+ metrics).
2. **Google — Software Engineer (June 2022 – May 2026 | Manhattan, NY)**
   - Updated end date to May 2026.
   - Highlighted Google Ad Manager full-stack backend (Java) and frontend (Dart/AngularDart/Sass).
   - Emphasized 99.99%+ availability and strict latency SLAs processing billions of daily events.
   - Noted cross-functional collaboration on API design, release validation, and developer workflows.
3. **Bloomberg L.P. — Site Reliability Engineer / Senior Software Engineer (Jan 2021 – May 2022 | Manhattan, NY)**
   - Founding engineer on Compliance SRE (CSRE); technical lead on Python services.
   - Maintained firm-wide Python project cookiecutter for hundreds of engineering teams.
   - Created ChangeLog Driven Release (CLDR) methodology for auditable semantic versioning.
4. **Edgestream Partners, L.P. — Software Engineer (May 2019 – Jan 2021 | Princeton, NJ)**
   - Architected large-scale enhancements to production in-house test framework and runner.
   - Integrated `pylint` across legacy codebase of 1M+ lines of Python with custom CI tools.
   - Lead developer of investor-facing web portal (Django, PostgreSQL).
5. **Comcast — Tier III Technical Support (2011 – 2016 | Mount Laurel, NJ)**
   - Network outage troubleshooting and automated Python data scripting.

#### Skills Categorization
- **AI & Agentic Systems:** Multi-agent orchestration, meta-harness design, agent evaluation & benchmarking, conformance harnesses, Claude Code, Codex, Antigravity, prompt engineering, structured tool use.
- **Languages:** Python (3.12+), Rust, Java, C/C++, Bash, SQL, Dart, Perl, JavaScript, LaTeX.
- **Systems & Reliability:** Linux internals, TCP/IP networking, distributed systems, CI/CD pipelines, test automation frameworks, observability (Prometheus / Grafana).
- **Data & Tools:** Git, Docker, PostgreSQL, Redis, ZeroMQ, Pluggy, FastAPI, Django, Textual, Vim.

#### Selected Open-Source Projects
- **`sase`:** Highlighted 7 harnesses, AXE scheduler, `fakey` conformance bench, ACE TUI, and documentation at `sase.sh`.
- **`psf/black`:** Overhaul of Black's string handling engine (~3,500 LoC) in PR #1132 closing 5 open issues.
- **`python-boltons/*`:** `cc-python`, `clack`, `eris`, `hush`, `logrus`.
- **`bbugyi200/funky` (500+ stars) & `bbugyi200/*`:** `cookie` (250+ stars), `shv` (Rust), `cldr`.

---

## 5. LinkedIn Profile Refresh & Positioning Guide

Bryan has not updated LinkedIn since leaving Google in May 2026. A six-month gap on LinkedIn can trigger automated recruiter filtering unless properly framed. Because Bryan has spent those six months actively building an advanced, open-source software project full-time, this period should be framed as high-signal engineering leadership.

### 5.1 Headline Strategy
Do not use a generic "Unemployed" or "Looking for opportunities" headline. Use an authoritative, keyword-rich headline:

> **Recommended Headline:**  
> `Software Engineer | Building SASE (sase.sh) — Open-Source Multi-Agent Developer Platform | Ex-Google, Bloomberg SRE`

*Alternative (Role-Targeted):*  
> `Software Engineer — Agentic AI Platforms, Evaluation & Systems | Creator of SASE (sase.sh) | Ex-Google (Ad Manager), Bloomberg`

---

### 5.2 About / Summary Section Draft
The summary must weave Google scale, Bloomberg reliability, and SASE innovation into a coherent narrative:

```markdown
I am a software engineer with eight years of experience building high-throughput distributed systems, testing infrastructure, and developer platforms across Google, Bloomberg, and Edgestream.

For the past six months, I have been working full-time architecting and maintaining SASE (https://sase.sh), an open-source multi-agent developer platform and meta-harness. SASE coordinates seven coding-agent harnesses (including Claude Code, Codex, Antigravity, and OpenCode) behind isolated workspaces, typed human-in-the-loop approval gates, a high-performance Rust core, and deterministic failure benchmarking with Prometheus observability.

Core engineering focus areas:
• Agentic AI Systems: Meta-harness architecture, multi-agent orchestration, conformance testing, and agent evaluation.
• Systems & Backend: Python (3.12+), Rust, Java, Linux internals, TCP/IP networking, and distributed services.
• Quality & Reliability: Test framework design, static analysis rollouts (pylint across 1M+ LoC), CI/CD pipelines, and Site Reliability Engineering.

I am preparing to release our comprehensive launch post on https://sase.sh and am exploring senior/staff engineering opportunities at the intersection of agentic AI platforms, developer tools, and evaluation infrastructure.
```

---

### 5.3 Experience Section Updates

#### 1. Add New Position: SASE
- **Title:** Founder & Lead Software Engineer
- **Company Name:** SASE (Structured Agentic Software Engineering)
- **Employment Type:** Full-time (or Self-employed)
- **Location:** New York, NY (Remote / Hybrid)
- **Start Date:** May 2026
- **End Date:** Present (Check "I currently work here")
- **Description:**
  ```markdown
  Full-time architect and maintainer of SASE (https://sase.sh), an open-source multi-agent developer platform and meta-harness unifying 7 coding-agent harnesses behind isolated git workspaces and deterministic evaluation benches.

  Key Technical Contributions:
  • Meta-Harness Architecture: Designed a pluggable provider abstraction (Python 3.12+) orchestrating Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, and Grok Build with intelligent model-alias routing.
  • High-Performance Systems Core: Implemented core backend domain logic in Rust (sase-core-rs) and an asynchronous multi-agent scheduler (AXE).
  • Deterministic Conformance & Evals: Built `fakey`, a zero-cost deterministic harness to benchmark and regression-test agent streaming, tool failures, token exhaustion, and interrupt lifecycles.
  • Human-in-the-Loop Governance: Engineered typed gates (plan, question, sudo) with auditable decision logs and Prometheus telemetry exporting 33+ operational metrics.
  ```

#### 2. Update Google Position
- **Title:** Software Engineer
- **Company:** Google
- **Dates:** June 2022 – May 2026 (Duration: 4 yrs)
- **Location:** Manhattan, New York, United States
- **Description:** Update description to reflect full-stack distributed systems and scale on Google Ad Manager:
  ```markdown
  Full-stack software engineer on Google Ad Manager in Manhattan:
  • Engineered low-latency, high-throughput Java backend services and modern web interfaces using Dart / AngularDart / Sass.
  • Maintained 99.99%+ uptime SLAs across globally distributed ad-serving and reporting pipelines handling billions of daily transactions.
  • Partnered across cross-functional infrastructure teams on API design, release automation, and developer productivity tooling.
  ```

---

### 5.4 Featured Section & Skill Endorsements
- **Featured Links:**
  1. Link to `https://sase.sh` (or the launch blog post once live).
  2. Link to GitHub repository: `https://github.com/sase-org/sase`.
  3. Link to Black PR #1132: `https://github.com/psf/black/pull/1132` (demonstrating major open-source impact).
- **Top Skills to Pin:**
  1. Python
  2. Agentic AI & LLM Systems
  3. Distributed Systems
  4. Software Testing & Evaluation
  5. Rust

---

### 5.5 Strategic Launch Post Draft (for `sase.sh` Release)
When publishing the blog post to `sase.sh` in the next 1–2 weeks, Bryan should publish this companion post on LinkedIn:

> *"Over the last six months, after four years at Google, I’ve been heads-down building something I believe developer platforms desperately need: a reliable, governable control plane for coding agents.*
> 
> *Today, I’m excited to share the launch post for **SASE (Structured Agentic Software Engineering)**: https://sase.sh*
> 
> *Most teams adopting coding agents run into the same hurdles: managing multiple agent CLIs, workspace contamination, runaway autonomous actions, and brittle evaluation loops.*
> 
> *SASE is an open-source meta-harness platform that:*
> *✔️ Unifies 7 agent harnesses (Claude Code, Codex, Antigravity, OpenCode, and more) behind a single provider abstraction*  
> *✔️ Isolates work in atomic, numbered git workspaces*  
> *✔️ Enforces human-in-the-loop typed approval gates (plan, questions, sudo) with persistent audit trails*  
> *✔️ Runs deterministic failure benchmarks with `fakey`, our zero-model-cost conformance harness*  
> *✔️ Combines a high-performance Rust core with a responsive Textual TUI and AXE scheduler*  
> 
> *Read the full architectural breakdown at https://sase.sh.*
> 
> *With SASE live, I’m actively looking forward to connecting with teams building the future of agentic developer platforms and evaluation infrastructure in NYC! #AI #AgenticAI #Python #Rust #OpenSource #DevTools"*

---

## 6. Omnigent Engagement & Application Timeline

To maximize hiring conversion at Databricks, Bryan should synchronize his application with the blog post launch and strategic community engagement.

```
Timeline (Next 2 Weeks):
[Now] ───────────────> [Days 1–3] ─────────────> [Days 4–7] ─────────────> [Week 2]
Compile Databricks CV   Engage Omnigent Repo     Publish sase.sh Post       Submit Applications
Commit to GitHub repo   (Muse harness / issue)   Post LinkedIn update       Recruiter & Referral Outreach
```

### 6.1 Contributing to Omnigent
As documented in `databricks_omnigent_job_fit.md`:
- **Do not submit new harness PRs to core Omnigent:** Maintainers explicitly closed core to new harnesses on 2026-09-22.
- **Join the community Muse harness:** SASE already has a working Muse Code integration. Community volunteers are building `omnigent-muse` ([R7L208/omnigent-muse](https://github.com/R7L208/omnigent-muse)). Contributing here demonstrates immediate collaborative value.
- **Tackle Core Issues in Omnigent:** Check open issues in `omnigent-ai/omnigent` relating to worktree isolation, runner file limits, and host liveness—areas where SASE has mature, battle-tested solutions.
- **Publish "SASE vs. Omnigent: Two Meta-Harness Architectures":** Writing a technical comparison highlighting architectural trade-offs (single-turn isolated worktrees vs. live collaborative sessions) positions Bryan as an intellectual peer to the team.

### 6.2 Interview Preparation Checkpoints
1. **Agent Evaluation System Design:**
   - Databricks' Agent Quality team will ask: *"How do you build an evaluation flywheel for agentic systems?"*
   - Bryan should be prepared to discuss: Ground truth test suites (SWE-bench style), deterministic mock playback (his `fakey` pattern), metric scoring (task success, trajectory efficiency, lint cleanliness), and regression gating in CI.
2. **Distributed Systems & Scale:**
   - The AI Platform backend team will probe high-concurrency systems design.
   - Lean into Google Ad Manager backend services: caching topologies, database sharding, latency SLAs, and consensus/locking models.
3. **Live Demonstration:**
   - Have a local instance of SASE ready to screen-share, showcasing the Textual TUI, multi-agent dispatch across Claude Code / Codex, and typed gate transitions.

---

## 7. Artifacts Summary

| Artifact | Location | Status |
| :--- | :--- | :--- |
| **Databricks CV LaTeX Source** | `gh:bbugyi200/CV` @ `BryanBugyi_Databricks_CV.tex` | Committed & Verified |
| **Databricks CV Compiled PDF** | `gh:bbugyi200/CV` @ `BryanBugyi_Databricks_CV.pdf` | Built with `pdflatex` (2 pages) |
| **Research Report Snapshot** | `sase/repos/research/202610/databricks_nyc_cv_design_pitches_and_linkedin__gem.md` | Durable SASE Artifact |
