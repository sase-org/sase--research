# Databricks NYC applications: role selection, CV design, LinkedIn updates, and pitches

**Researcher:** cdx  
**Verified:** October 10, 2026  
**Deliverable:** independent research and proposed application copy for the lead researcher to synthesize.

## Recommendation

Apply to **Sr. Software Engineer – Backend, AI Platform (P-1591; job 8379331002)** and **Staff Software Engineer, Agent Quality (P-1567; job 8842963002)**. Senior Backend is the stronger level match. Agent Quality is a credible second application because Bryan's Python tooling, reliability, testing, and agent infrastructure experience is relevant, but Staff-level influence and real agent evaluation remain evidence gaps. If applying to only one, choose Senior Backend and ask about agent-platform work.

Bryan is credibly qualified to apply for these two roles; the evidence does not justify promising a Staff offer or claiming that either requisition places him on Omnigent. His strongest positioning is **an experienced Python and systems engineer who builds the infrastructure around coding agents**, supported by a current, demonstrable open-source system. The CV should connect SASE to his earlier developer tooling work at Bloomberg and Edgestream.

The next concrete deliverable should be two closely related, two-page PDF resumes built from his existing LaTeX layout. End Google in May 2026, introduce full-time independent SASE development at the top of Experience, and shorten the older project catalog. Prepare a LinkedIn update at the same time. The blog is useful evidence, but finishing a publicity campaign or getting an Omnigent contribution accepted should not be a prerequisite for applying.

## Scope and evidence

This report was researched independently. I did not read reports or conversations from the current `research.0s` swarm. The CV repository was inspected read-only; **no CV changes or CV commit were made during this research turn**. The implementation specification and draft copy below are intended for the lead's subsequent CV work. LinkedIn was not edited, applications were not submitted, and outreach was not sent.

The requested `databricks_omnigent_job_fit.md` was absent from the opened SASE research checkout. I found its previously registered durable snapshot by exact-name artifact lookup and read it through `sase artifact read`:

- Input identity: `file:explicit:a536ac80ec13d53a296002a7`.
- Original label: `research:202610/databricks_omnigent_job_fit/databricks_omnigent_job_fit.md`.
- Created October 7, 2026, in the Bob CLI project; this is the user-named shared prior input, not a current swarm report.

I independently rechecked the actual job descriptions and the current Databricks Greenhouse feed. Its `updated_at` fields are modification timestamps, **not posting dates**. Both recommended jobs were in the live feed and had official detail pages with an application control on October 10. This establishes public availability at the time of research, not a guarantee that a team has an unfilled seat or that a recruiter will respond. [Senior Backend](https://www.databricks.com/company/careers/engineering/sr-software-engineer--backend-8379331002), [Agent Quality](https://www.databricks.com/company/careers/engineering---pipeline/staff-software-engineer-agent-quality-8842963002), [employer's live job feed](https://boards-api.greenhouse.io/v1/boards/databricks/jobs?content=true).

Candidate evidence came from `bbugyi200/CV` at commit `c74c1a24b4982f4d9843b9f293952ebf41dc93fe`, especially `BryanBugyi_LangChain_CV.tex`, `BryanBugyi_Google_CV.tex`, and the original `BryanBugyi_CV.tex`. I also inspected this SASE checkout at `62a8b95c721279876a885491aae8238ea92afaba`, including `README.md`, `pyproject.toml`, `docs/tool.md`, `docs/fakey.md`, `docs/telemetry.md`, and `docs/rust_backend.md`. [Existing CV source](https://github.com/bbugyi200/CV/blob/c74c1a24b4982f4d9843b9f293952ebf41dc93fe/BryanBugyi_LangChain_CV.tex).

**Authority of claims:** the user's correction controls the Google end date and current full-time SASE work. Employment accomplishments remain candidate-reported facts from the CV. Repository inspection confirms product capabilities, not commercial adoption or sole authorship of every implementation. Role-fit judgments are my assessment. Proposed benchmarks below have not been run.

## 1. Which jobs to apply for

### The two recommended applications

| Priority | Role and exact identifier | Location | Assessment | Posted local salary range |
| --- | --- | --- | --- | --- |
| 1 | [Sr. Software Engineer – Backend](https://www.databricks.com/company/careers/engineering/sr-software-engineer--backend-8379331002), P-1591, `8379331002` | New York City | Strongest documented match for level and language; infrastructure depth still needs concrete stories | $165,300–$219,675 |
| 2 | [Staff Software Engineer, Agent Quality](https://www.databricks.com/company/careers/engineering---pipeline/staff-software-engineer-agent-quality-8842963002), P-1567, `8842963002` | New York City | Credible application; Staff scope and outcome-evaluation experience need substantiation | $200,000–$265,000 |

The ranges above are salary, not total compensation; the postings separately mention possible equity and performance bonus. Compensation should not determine the choice of team before the engineering work and level are understood. Sources are the linked job descriptions.

**Senior Backend synopsis.** The AI Platform requisition covers several teams and products, including MLflow, AI Gateway, Databricks Apps, Agent Framework, Agent Bricks, and Foundation Model APIs. It asks for five or more years, strong Scala, Go **or Python**, and backend/infrastructure experience, including observability and service deployment. AI workflow tooling is a bonus. [Official posting](https://www.databricks.com/company/careers/engineering/sr-software-engineer--backend-8379331002).

**Why Bryan fits:** approximately seven years of professional SWE work through May 2026; Python as a primary language; Bloomberg SRE and release/scaffolding work; production trading-system tooling at Edgestream; Google backend/full-stack experience; and SASE as current evidence of ownership. These are mutually reinforcing experiences. The CV should document the system he owned and the engineering decisions he made instead of relying on the Google name to imply scale.

**Agent Quality synopsis.** This founding AI Research team builds evaluation infrastructure for Genie Agents and connects evaluation to improvement. The posting asks for six or more years, strong Python, dependable infrastructure, trustworthy signals, and cross-team influence. Devtools, testing, CI, observability, benchmarks, and LLM evaluation familiarity are desirable. [Official posting](https://www.databricks.com/company/careers/engineering---pipeline/staff-software-engineer-agent-quality-8842963002).

**Why Bryan fits:** Edgestream's testing framework work, Bloomberg's release tooling and Python leadership, and SASE's deterministic provider testing and durable run evidence give him a coherent quality-infrastructure story. He has enough experience for the stated tenure bar. His prior Bloomberg Senior title is useful history, but it is not proof of present Staff-level scope.

**Material uncertainty for both:** the existing Google bullet says little about ownership, scale, failures, collaboration, or impact. This is the largest weakness in the application evidence. For Agent Quality, framework regression tests and deterministic fake-agent tests do not establish expertise in measuring real agents' task success. The appropriate claim today is strong infrastructure experience adjacent to evaluation, with a clear plan to build the missing empirical evidence.

### Roles to exclude from these one or two applications

| Role | Reason to deprioritize now |
| --- | --- |
| [Staff Backend, Unity AI Gateway, `8468436002`](https://www.databricks.com/company/careers/engineering/staff-backend-software-engineer-8468436002) | Eight or more backend/infrastructure years and strong Scala or Go are stated requirements. Neither language appears in the inspected CV. The subject is attractive; the documented qualification match is weaker than Senior Backend. |
| [Staff Fullstack – AI Product NYC, `8509534002`](https://www.databricks.com/company/careers/engineering---pipeline/staff-software-engineer-fullstack---ai-product-nyc-8509534002) | Ten or more years each of HTML/CSS/JavaScript and server-side web work. Java/AngularDart experience and a Textual TUI do not demonstrate that record. |
| [Staff AI Research Infrastructure, `8532682002`](https://www.databricks.com/company/careers/executive-engineering---pipeline/staff-software-engineer---ai-research-infrastructure-8532682002) | The work centers on GPU fleets and training/inference orchestration; cluster-scheduler contributions and ML workflow knowledge are expected. SASE's subprocess scheduling is relevant context, but does not establish cluster expertise. The live feed also lists `8552484002` with the same P-1215 text; do not treat duplicate listings as distinct targets. |
| [Sr. Developer Advocate, Open Source — Omnigent, `8716187002`](https://databricks.com/company/careers/open-positions/job?gh_jid=8716187002) | Direct product connection, but SF or Seattle listings, public speaking/community-growth responsibilities, and strong TypeScript. The CV proves technical/open-source work better than advocacy leadership. Consider only if Bryan actually wants that career and location change. |

These exclusions follow the current descriptions, not a judgment that Bryan could never learn the missing skills. Applying to a job whose core requirements are unsubstantiated is inconsistent with the request to select roles for which he is really qualified.

### Omnigent is the motivation, not a promised assignment

Omnigent's layer above existing coding harnesses, its policies, and shared sessions make SASE experience relevant. Databricks' managed offering is currently documented as Beta and integrates with workspace identity and model access. [Databricks introduction](https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents), [managed product documentation](https://docs.databricks.com/aws/en/omnigent/).

I found no software-engineering title explicitly naming Omnigent in the live job feed. That does not establish that no Omnigent engineering hiring exists: team staffing can sit behind broader requisitions. The recommended backend role is an avenue to ask about placement, not evidence of a guaranteed Omnigent job. Agent Quality explicitly concerns Genie evaluation and may be an entirely separate team.

Useful recruiter questions after contact:

1. Which NYC teams are hiring through P-1591, and do any own agent runtimes, developer-facing orchestration, AI Gateway, or Omnigent?
2. Does the Agent Quality team want a Python infrastructure engineer who brings testing/devtools experience, or require an established owner of production LLM evaluation?
3. What distinguishes Senior from Staff in this team's current needs? Is leveling flexible after interview?
4. What is the NYC office attendance expectation, and where does the immediate team work?

Do not contact people or submit applications on Bryan's behalf as part of this research deliverable.

## 2. The evidence Bryan should use

| Evidence | What it supports | What it does not establish |
| --- | --- | --- |
| Bloomberg founding Compliance SRE work; Python technical leadership; shared project scaffolding; CLDR alpha | Reliability, developer platform ownership, release engineering, collaboration beyond one feature | Exact adoption counts, measured productivity improvement, company-wide architectural authority |
| Edgestream pylint rollout across a 1M+ line Python codebase; test framework/runner improvements | Retrofitting quality controls into real legacy systems; developer workflows | A measured incident or runtime reduction without additional evidence |
| Google Ad Manager backend and frontend work | Production Java and full-stack experience; product-team work | Personal ownership of Google's scale, specific latency gains, or leadership scope |
| SASE provider adapters, isolated clones, scheduled workflows, persistent outputs | Agent lifecycle/platform design; integration seams; sustained ownership | GPU cluster scheduling, OS sandboxing, enterprise tenants, or external adoption |
| SASE `fakey` provider | Repeatable subprocess, retry, interrupt, streaming, and failure tests | Quality of real LLM reasoning or generated code |
| SASE run fingerprints, failure evidence, and verdict receipts | Provenance, conservative reuse/coverage decisions, diagnostic correctness | Hermetic replay of stochastic LLM runs or a general agent evaluation benchmark |
| `psf/black` string-handling contribution | External review, Python depth, work in an established OSS project | Broad present-day contributor-community leadership |

The Black contribution is independently supported by the PR conversation: Bryan authored PR #1132, and it was merged May 8, 2020. The approximate 3,500-line scope and five resolved issues are CV claims; merged work is the stronger externally verified headline. [Black PR #1132](https://github.com/psf/black/pull/1132).

Current SASE evidence is more specific than the May CV. It uses Python with a required Rust core and supports seven real agent CLIs. The README marks it alpha. `fakey` exercises real launch plumbing without a model call. Local telemetry is now stored through Rust in SQLite, with bounded writes and rollups; the old CV's “Prometheus telemetry surfacing 33 pipeline metrics” should not be copied into a new resume as a current architecture statement without fresh verification. [README](https://github.com/sase-org/sase/blob/62a8b95c721279876a885491aae8238ea92afaba/README.md), [fake provider documentation](https://github.com/sase-org/sase/blob/62a8b95c721279876a885491aae8238ea92afaba/docs/fakey.md), [telemetry documentation](https://github.com/sase-org/sase/blob/62a8b95c721279876a885491aae8238ea92afaba/docs/telemetry.md), [run evidence documentation](https://github.com/sase-org/sase/blob/62a8b95c721279876a885491aae8238ea92afaba/docs/tool.md).

**Avoid inflated claims:** “enterprise-grade agent security,” “distributed ML platform,” “production LLM evaluation,” “many users,” and “increased productivity by X%” need evidence absent here. A private workspace clone isolates repository edits; it does not block filesystem, network, or credential access. Agent-generated line count is a poor measure of Bryan's expertise. He should be ready to explain and debug the architecture he claims ownership of.

## 3. Dates and the Google-to-SASE transition

Use **Google — Software Engineer — June 2022–May 2026**. This report interprets the user's “left Google in May” as May 2026; confirm that year and the actual last employment month before the final CV is published. The old CV and October 7 input still say Google is current and must be superseded.

Use **Independent Open-Source Development — Creator & Maintainer, SASE — May 2026–Present** if May is the correct full-time start. If the full-time work began in June, use June. The May CV dates SASE as a project to 2025; if accurate, a short parenthetical can say “project begun in 2025; full-time since May 2026.” Distinguish project inception from this full-time period.

This is meaningful engineering work and belongs in Experience. Calling the entry independent makes the arrangement legible without implying a salaried employer, consulting clients, incorporation, or funded startup. “Founder & CEO” would add unsupported company signals. A separate empty gap entry would obscure the work actually done.

Do not stretch tenure by adding the full Comcast period to SWE years. It was Tier III technical support with valuable Python automation. Use “seven years in professional software engineering, followed by full-time independent development,” or omit the number entirely. May to October is approximately five months; use exact dates instead of anchoring copy to “six months unemployed.”

Suggested interview explanation, consistent with what Bryan actually said:

> I left Google in May 2026. Since then I have been working full-time on SASE, an open-source system for coordinating coding agents. It has given me direct experience with agent lifecycles, provider integration, reliable workflow state, and verification. Omnigent made Databricks especially interesting to me because it is investing in closely related infrastructure. I am now looking for a role where I can bring that work together with my production engineering background.

Do not say the departure was a layoff, a voluntary sabbatical, or a planned startup launch unless Bryan confirms it. If asked directly why he left, he should provide the truthful reason in his own words.

## 4. CV design based on the existing repository

### Layout and files

Use `BryanBugyi_LangChain_CV.tex` as the scaffold: it is already focused on agent tooling, has readable sans-serif typography and restrained headings, and is self-contained at the source level. The Google variant is also reasonable. The original source depends on `/home/bryan/Sync/lib/latex/gutils.tex`; carrying that dependency into the new resume would make builds less portable.

Preserve the established header, company/date alignment, compact bullets, and typography. Use a subdued red accent if a Databricks-themed visual treatment is desired, with black body text and simple section rules. An employer logo or recreation of its marketing palette adds little. Keep the body in one reading column. Simplify the three-column project lists, put Education last, and use searchable text with ordinary section names.

Proposed repository outputs:

- `BryanBugyi_Databricks_Backend_CV.tex` and the corresponding PDF.
- `BryanBugyi_Databricks_AgentQuality_CV.tex` and the corresponding PDF.
- `databricks_application_notes.md` for pitches, evidence provenance, and confirmations, if Bryan wants those tracked in the CV repo.

Target two pages without reducing body text below the existing approximately 10-point size. This is a design recommendation, not a claim about a specific ATS. Check text extraction and reading order after rendering. Lead with SASE and recent employers, not the 2015–2019 education entry.

### Shared draft copy

The following is a factual, conservative content draft. It can be inserted into the existing LaTeX commands. It is not a fabricated expansion of the sparse Google history. Dates for the independent entry need the confirmation described above.

**Bryan Bugyi**  
Software Engineer | Python, Reliability & Agent Infrastructure  
Existing email, phone, GitHub and LinkedIn links | [sase.sh](https://sase.sh/)  
Add “New York City” only if Bryan currently lives there, or “Seeking NYC roles” if that is the accurate statement.

**Profile — Backend version**

Software engineer with seven years of professional experience across Google, Bloomberg, and Edgestream, specializing in Python, Linux, reliability, and developer tooling. Currently building SASE full-time: an open-source platform that coordinates coding agents across providers, records their work, and supports supervised engineering workflows. Previous work includes Python tooling leadership at Bloomberg and quality infrastructure for a million-line trading codebase.

**Experience**

**Independent Open-Source Development — Creator & Maintainer, SASE**  
May 2026–Present; project begun in 2025 if confirmed

- Built SASE, a Python CLI and Textual TUI with a required Rust core, to coordinate seven coding-agent CLIs through shared workflows and isolated Git workspaces.
- Designed durable agent and workflow records, scheduled execution, human decision gates, and reviewable artifacts that preserve work across provider runs.
- Developed deterministic fake-agent scenarios for launch, streaming, retry, and interruption tests, and run evidence that records repository state and failure outcomes.

**Google — Software Engineer — Manhattan, NY**  
June 2022–May 2026

- Developed Google Ad Manager features across Java backend services and a Dart/AngularDart/Sass frontend.

**Bloomberg L.P. — Site Reliability Engineer / Senior Software Engineer — Manhattan, NY**  
January 2021–May 2022

- Founding engineer on the Compliance SRE team; led development across the team's Python software portfolio.
- Maintained Bloomberg's shared Python project cookiecutter and authored ChangeLog Driven Release, piloted within the Compliance department.

**Edgestream Partners, L.P. — Software Engineer — Princeton, NJ**  
May 2019–January 2021

- Led pylint integration across a Python trading codebase exceeding one million lines, building tools to support the rollout.
- Improved the production team's internal testing framework and runner.
- Led development of the Django-based investor-facing web portal.

**Earlier experience:** Comcast, Tier III Technical Support, 2011–2016 — diagnosed network outages and automated recurring support workflows in Python. Keep as one line only if space permits.

**Selected Open Source**

- **Black:** authored the merged string-handling contribution in PR #1132 to the Python code formatter; original CV reports approximately 3,500 lines changed and five issues resolved. In the final CV omit this provenance clause and retain the numeric detail only if Bryan can substantiate it.
- **python-boltons:** created Python libraries for project scaffolding, configuration, error handling, secrets, and logging. Select one or two examples relevant to the interview.
- **funky / cookie:** built shell developer tools with external contributions. The existing CV reports 500+ and 250+ GitHub stars respectively; omit counts unless refreshed, since they are not needed to make the case.

**Skills**

- Primary: Python, Linux, Git, shell scripting, TCP/IP.
- Production/application experience: Java, Dart/AngularDart, Django; PostgreSQL, Redis, Docker, as supported by the existing CV.
- Agent/developer infrastructure: provider adapters, workflow orchestration, CLI/TUI tools, automated testing, release tooling, observability.
- Working knowledge: Rust, C/C++, FastAPI, Flask, Pluggy, Textual. Retain only items Bryan is prepared to discuss and use.

**Education**

Rutgers University — B.S. Computer Science, minor in Mathematics — 2019.

This draft should gain **one or two additional Google bullets**, ideally replacing less important older material. The four-year Google tenure should not look less substantial than the six-month independent period just because the old CV is sparse.

### Agent Quality variant

Keep the same employment facts and dates. Change the header emphasis to **Python, Reliability & Agent Quality Infrastructure**, and use this profile:

> Software engineer with seven years of professional experience in production systems and Python developer tooling across Google, Bloomberg, and Edgestream. Currently building SASE full-time, with deterministic agent-lifecycle tests, durable run evidence, and failure classification. Earlier work includes test-framework improvements for a large trading codebase and release/scaffolding tools for Bloomberg's Compliance SRE team. Interested in building dependable infrastructure for agent evaluation and regression analysis.

Order SASE bullets as verification/testing, durable evidence, then orchestration. Order Edgestream bullets as testing, pylint, portal. Expand the test-framework story when Bryan supplies specifics. Keep “interested in building” until a real evaluation pilot exists; do not replace it with “expert in LLM evaluation.”

Possible SASE testing bullet with a concrete mechanism:

> Built a deterministic fake-agent provider that exercises the real subprocess launch path, including retries, streaming, hangs, and interrupts, without model calls.

Possible evidence bullet:

> Implemented run provenance and failure classification that distinguish new, previously witnessed, flaky, and insufficiently evidenced failures while preserving command outcomes.

These are supported product capabilities. Before using “implemented,” confirm Bryan's actual ownership of the cited subsystem; “designed and maintained” may describe his role more precisely in an agent-assisted project.

### What to remove or rewrite

- Replace Google's “present” or “Current” everywhere a resume might be sent, including the base CV; regenerate corresponding PDFs.
- Replace language proficiency measured in lines of code with a short capability-based skills list.
- Avoid the old generic “systems-oriented skill set” paragraph; tie the profile to verified work.
- Remove the bibliography-style frontend technology footnotes from the old Google entry.
- Cut exhaustive miscellaneous projects and long lists of technologies. Keep evidence that earns interview attention.
- Put SASE in Experience once; do not repeat the same bullets under Selected Projects.
- Avoid unexplained internal acronyms such as ACE, AXE, and CLDR in the opening profile. Spell out the engineering behavior.
- Remove an automatic current-date stamp from the application header if adapting the original CV; it adds no qualification evidence.

### Implementation and commit acceptance criteria

For the lead's CV implementation turn:

1. Reopen `gh:bbugyi200/CV` with the SASE repository workflow and use its returned path. Recheck current history and existing instructions before editing; this report's commit is a research snapshot, not a guarantee of the future checkout.
2. Confirm Google end month/year, full-time SASE start, and current location. Update old employment dates as well as both new variants so the repository does not retain a sendable PDF describing Google as current.
3. Create the two source files from the existing scaffold and insert verified copy. Preserve source-license attribution when reusing the template.
4. Build with the repo's working LaTeX environment, using a temporary output directory during iteration. Inspect both pages for awkward breaks, clipped text, oversized skill rows, and inaccessible links.
5. Extract PDF text and check ordinary reading order, dates, contact details, and selectable words. Avoid treating a successful LaTeX exit alone as resume validation.
6. Commit source and final PDFs to the CV repository through the SASE-approved commit/finalizer workflow. A suitable message is `feat: add Databricks backend and agent quality resumes`. A local commit and a remote push are different outcomes; verify and accurately report each rather than saying “published” after only a commit.

I did not compile a new CV. `latexmk` and `pdflatex` were available on this host, while `pdftotext` and `pdfinfo` were not on PATH. Existing PDF files were present. The subsequent implementation must obtain a working extraction tool or another verified PDF-reading method; this report does not claim PDF render validation.

## 5. LinkedIn changes and copy

Update the public profile before submitting an application so CV, profile, and interview chronology agree. If Bryan wants to coordinate a later announcement, first turn off **Share profile updates** under Settings & Privacy → Visibility. This controls network notifications, not whether saved edits are visible to someone visiting the profile. [LinkedIn's official instructions](https://www.linkedin.com/help/linkedin/answer/a529062/share-profile-updates-with-your-network).

**Google entry:** clear “I currently work here,” enter May 2026, and save. Check that the profile introduction and headline no longer describe Google as current employment. [LinkedIn guidance on end dates](https://www.linkedin.com/help/linkedin/answer/a545775/listing-unemployed-or-retired-on-profile?lang=en).

**New experience entry:**

- Title: **Creator & Maintainer — SASE**.
- Organization: **Independent / SASE (open-source project)**, expressed in the way LinkedIn's current entry form permits without selecting an unrelated company page.
- Dates: accurate full-time start in May or June 2026 through Present; explain the earlier 2025 project start in the description if accurate.
- Employment type: leave unset if none accurately describes the arrangement. Do not imply freelance clients or incorporation.
- Description:

> Building SASE full-time, an open-source system for coordinating coding agents across providers. It combines a Python CLI and terminal interface with a Rust core, isolated Git workspaces, reusable workflows, durable run records, and human review gates. I design and operate the system for my own engineering work, with particular attention to provider integration, reliable lifecycle behavior, and verification.
>
> Code and documentation: https://sase.sh/

**Headline:**

> Software Engineer | Python & Agent Infrastructure | Creator of SASE | Former Google & Bloomberg

**About:**

> I build developer tools and reliable software systems, with a focus on Python, Linux, and the infrastructure around AI coding agents.
>
> My professional experience includes Google Ad Manager, Bloomberg's Compliance SRE team, and Edgestream's production trading systems. Across those roles, I have worked on application software, Python tooling, release processes, and testing infrastructure.
>
> Since leaving Google in May 2026, I have been developing SASE full-time. SASE coordinates coding-agent CLIs into tracked engineering workflows with isolated workspaces, persistent outputs, supervision, and verification. I am interested in NYC engineering roles where I can bring that hands-on agent-infrastructure work together with my production software background.
>
> SASE: https://sase.sh/

**Featured items:** SASE repository/documentation, a short live-system demo, the final blog version when ready, and the selected CV PDF if Bryan wants it public. Use a sanitized demo with no personal prompts, secrets, or private project identifiers. Add relevant skills such as Python, Linux, developer tools, reliability, CI/testing, and agent orchestration; avoid adding ML technologies merely for keyword matching.

**Publication status needs reconciliation:** the live SASE homepage currently links to an accessible [launch article](https://sase.sh/blog/posts/structured-agentic-software-engineering/) displaying July 8, 2026. Bryan says the intended blog release is still one or two weeks away. The public article could be a draft, an earlier edition, or a staged publication. A served URL establishes accessibility, not completion of his planned release. Use the docs/repository now, and confirm the intended post/version before announcing that release or copying its date into application materials.

## 6. Short pitches for the two roles

These are drafts Bryan can adapt for an application, referral request, or recruiter conversation. They do not claim experience missing from the CV.

### Senior Backend / AI Platform

> I'm a Python and systems engineer with seven years of professional experience at Google, Bloomberg, and Edgestream. Since leaving Google in May, I've been building SASE full-time: an open-source platform for coordinating coding agents with isolated workspaces, durable workflow state, supervision, and verification. Previously I led Python tooling work at Bloomberg and quality tooling for a million-line trading codebase. Omnigent caught my attention because I'm solving related integration and lifecycle problems. I'd like to bring that experience to a NYC AI Platform team working on agent infrastructure or developer tooling.

For a recruiter, add separately: **“I'm applying to P-1591 and would appreciate guidance on teams working closest to agent orchestration or Omnigent.”** That is a request for routing, not a claim of an advertised Omnigent assignment.

### Staff Agent Quality

> My background combines production engineering with Python testing and developer infrastructure: test-framework work at Edgestream, founding Compliance SRE and Python tooling work at Bloomberg, and Google Ad Manager engineering. I'm now building SASE full-time, including deterministic agent-lifecycle tests, durable execution evidence, and failure classification. I want to apply that foundation to the infrastructure that makes agent evaluation trustworthy and actionable. I bring practical experience operating coding-agent workflows and designing their reliability boundaries, and would welcome a discussion about the scope and leveling of the NYC Agent Quality team.

This deliberately avoids claiming a completed real-agent benchmark. Once a measured pilot exists, replace one generic sentence with its actual task count, measurement method, and result. Do not say “improved quality” unless there is a controlled before/after comparison.

**Two-sentence reusable introduction:**

> I build the engineering infrastructure around coding agents. My current project, SASE, combines that work with seven years of production software and Python tooling experience at Google, Bloomberg, and Edgestream.

## 7. Strengthen the applications without postponing them indefinitely

### Facts to collect before finalizing the CV

The lead should obtain these answers; missing metrics are a reason to omit a claim, not to invent one:

1. **Google:** What two features or systems did Bryan personally own? What did he design, implement, debug, or migrate? What defensible scale or impact can he discuss publicly? Which cross-team decisions did he drive?
2. **Bloomberg:** How many projects or teams used his Python scaffolding and CLDR work? What part did he own? Was there mentorship, standards adoption, or operational improvement he can substantiate?
3. **Edgestream:** What specifically changed in the test framework/runner? Was it speed, determinism, failure diagnostics, integration, or rollout safety? What was the pylint adoption strategy?
4. **SASE:** Which architectural decisions and subsystems does he understand deeply? How many real workflows or runs can he substantiate, with time period and definition? Which failures caused redesigns? Is external use known, or should it remain a personal daily-use claim?
5. **Chronology and logistics:** Last Google employment month/year, first full-time SASE month, project inception year, current location, and NYC office availability.

A strong Staff application needs at least one story about influence beyond Bryan's own implementation: resolving a technical disagreement, setting a reusable standard, coordinating adoption, or making other engineers effective. The existing Bloomberg facts are promising, but their scope needs detail.

### A bounded evaluation pilot for Agent Quality

This is a proposed portfolio improvement, not work performed in this report. If feasible within the publication window, build a small evaluation script and report over existing SASE runs rather than a new evaluation platform.

- Choose roughly 8–12 representative coding tasks in a small public/test repository with frozen starting commits and explicit success criteria. Keep development tasks separate from held-out assessment tasks.
- Start with objective outcomes: relevant tests pass, the requested change is present, prohibited changes are absent, and required artifacts exist. Record timeouts, interrupted runs, and missing traces separately. A failed or missing run must not silently disappear from the denominator.
- Record model/harness/version, prompts, repository revision, limits, task identity, and toolchain. These make experiments comparable; they do not make a stochastic model bit-for-bit reproducible.
- Repeat a small subset two or three times to expose variance. Report per-task outcomes and sample size; such a small pilot does not support sweeping model rankings or causal productivity claims.
- Keep infrastructure conformance tests and real-agent task-success scores separate. A deterministic fake provider is valuable for the former; it is not a substitute for the latter.
- Show one honest regression case and the trace that localized it. If comparing a workflow change, hold tasks and other settings constant and state the experiment's limitations.
- Add MLflow tracking/scoring only if it makes the result clearer and can be completed quickly. The evidence is a reliable measurement and a debuggable failure, not use of a particular library.

Three focused preparation references, checked against Bryan's reference library, are [MLflow evaluation overview](https://mlflow.org/docs/latest/genai/eval-monitor/), [evaluation examples](https://mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/eval-examples/), and [regression testing / CI](https://mlflow.org/docs/latest/genai/eval-monitor/regression-testing/). The official documentation supports custom scoring, trace-based analysis, and comparison in development workflows. None was found in the indexed `ref/` library; that does not establish that Bryan has never read them.

### Application sequence

1. Make the employment dates and current work consistent across the CV and LinkedIn.
2. Prepare both resumes, a short demonstration, and two production-engineering stories. Apply to Senior Backend once that packet is accurate; the final blog can follow.
3. Use the same period to prepare the evaluation pilot and sharpen the Staff ownership story, if possible. Apply to Agent Quality with accurate current claims even if the pilot is still explicitly a work in progress.
4. Ask for team routing and level calibration after a recruiter responds. A Senior placement in a relevant agent/platform team can be a better outcome than a Staff title in unrelated work.
5. Consider an Omnigent contribution if a small, relevant issue fits Bryan's actual expertise. Maintainer review is outside his control, so acceptance should not gate application timing. This report does not independently revalidate the prior input's September community-harness policy and does not recommend a new core harness PR.

## 8. Research limitations and handoff

The professional CV is sparse, especially at Google, so production scale, measurable impact, and Staff-level leadership are unproven rather than absent. I did not inspect private employment material or an authenticated LinkedIn profile. I did not run a SASE benchmark, audit the full implementation, verify current project star counts, or test a new PDF. The role recommendations are based on public requirements and inspectable evidence, with those limitations carried into the proposed copy.

The user-named prior report was recovered through its explicit snapshot and used as shared context. Two material corrections are necessary before its language is reused: **Google employment has ended**, and **the current SASE telemetry design differs from its Prometheus description**. Its inferred relationship between broad AI Platform hiring and Omnigent remains a recruiter question.

This turn's completed product is this independent report. The CV repository still needs the implementation, validation, and commit described above; LinkedIn still needs Bryan's edits. The report itself is to be registered using its actual source path and repo-relative artifact label, with no move, as requested.

Library check: 0 of 3 candidates already in your library (0 finished).
