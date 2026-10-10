# Databricks NYC CV, LinkedIn, and role pitches

> Independent research by `research.0s.grk` for a targeted Databricks application.
> Snapshot date: **2026-10-10**. Greenhouse board pulled the same day (892 live jobs).

## Bottom line

Apply to **exactly two** live NYC engineering roles. Both are still on the Databricks Greenhouse board today. Bryan is qualified for both.

1. **Staff Software Engineer, Agent Quality** — New York City.
   Greenhouse `8842963002` / P-1567. Base **$200,000–$265,000**.
   [Official posting](https://www.databricks.com/company/careers/engineering---pipeline/staff-software-engineer-agent-quality-8842963002).
2. **Sr. Software Engineer – Backend (AI Platform)** — New York City.
   Greenhouse `8379331002` / P-1591. Base **$165,300–$219,675**.
   [Official posting](https://www.databricks.com/company/careers/open-positions/job?gh_jid=8379331002).

Use **one** Databricks-themed CV, modeled on `BryanBugyi_Google_CV.tex` in [bbugyi200/CV](https://github.com/bbugyi200/CV). Put it in that repo as `BryanBugyi_Databricks_CV.tex` / `.pdf`. End Google at **May 2026**. Treat **SASE as the current full-time job** (Independent Software Engineer, May 2026–present). Apply this week. `https://sase.sh` is already live, including the launch essay, so the blog is not a gate.

Do **not** apply to the Omnigent Developer Advocate requisition from NYC. It is SF/Seattle only, it is a DevRel job, and the career shape is a mismatch. Name Omnigent, Agent Framework, and Unity AI Gateway in the Backend pitch and in the recruiter screen so the AI Platform pipeline can route you.

---

## What this report covers

- Re-verification of live NYC Databricks roles against the 2026-10-07 job-fit report.
- Qualification bar for each candidate role (apply vs skip).
- How a hiring panel will read the May 2026 Google exit and the SASE months.
- CV architecture: file, palette, section order, bullets, ATS notes.
- Ready-to-commit LaTeX draft.
- LinkedIn, GitHub, and Greenhouse application checklist.
- A short pitch for each of the two apply-now roles.

Shared input: `research:202610/databricks_omnigent_job_fit/databricks_omnigent_job_fit.md` in the bob-cli research sidecar (lead synthesis dated 2026-10-07). That report still lists Google as current. This CV work has to correct that.

---

## Sources used

| Source | What I took from it |
| --- | --- |
| Job-fit report (bob-cli research sidecar, 2026-10-07) | SASE↔Omnigent mapping, ranked shortlist, gaps (adoption, evals, Scala/Go) |
| Databricks Greenhouse API, 2026-10-10, 892 jobs | Live/gone check; NYC engineering inventory |
| Official postings `8842963002`, `8379331002`, `8468436002`, `8509534002` | Requirements, pay, team language |
| [NYC R&D hub post](https://www.databricks.com/en/blog/announcing-databricks-new-york-rd-hub) (2026-01-31) | NYC hub is agentic AI + LLMs + data infra |
| [Omnigent on Databricks](https://docs.databricks.com/aws/en/omnigent/); [launch post](https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents) | Product language for pitches |
| [sase.sh](https://sase.sh) and [launch essay](https://sase.sh/blog/posts/structured-agentic-software-engineering/) | Current SASE claims (providers, TUI, gates, install path) |
| GitHub API: `sase-org/sase` (5★ / 1 fork, MIT, pushed 2026-10-10); PyPI `sase==0.17.1`; `bbugyi200/funky` 671★ | Traction numbers; do not put SASE star count on the CV |
| `bbugyi200/CV`: `BryanBugyi_CV.tex`, `BryanBugyi_Google_CV.tex`, `BryanBugyi_LangChain_CV.tex` | Layout heritage; 2026 Google/LangChain variants are the model |
| Public LinkedIn `linkedin.com/in/bryan-bugyi`; GitHub profile bio | Both still present Bryan as a current Google SWE |
| [Databricks interviewing page](https://www.databricks.com/company/careers/interview-prep) | Timeline 2–3 months; recruiter → pre-onsite → 4–6 interview loop; multiple applications allowed |

I did not read peer swarm reports (`*__cdx.md`, `*__cld.md`, `*__mus.md`, `*__gem.md`).

---

## Role qualification (NYC, live on 2026-10-10)

### Apply 1 — Staff Software Engineer, Agent Quality (`8842963002`)

**Still live.** Location: New York City. Department in the feed: Engineering – Pipeline; metadata category: Research. First published 2026-09-24. Req P-1567.

The posting is a **founding seat on a new AI Research team**. The work is evaluation infrastructure for Genie Agents and the agent development platform: benchmarking, regression detection, a flywheel from production signals back into training and development.

| Requirement | Bryan |
| --- | --- |
| 6+ years building software systems | ~7.0 years employed SWE (Edgestream May 2019 → Google May 2026) plus ~5 months full-time SASE. Honest band: **7–7.5 years**. Clears 6+. Staff title is a reach on years alone; domain fit and founding-team shape carry it. |
| Strong Python; production or research infrastructure | Primary language. Bloomberg CSRE Python lead; Edgestream 1M-line Python trading stack; SASE is Python 3.12+ with a required Rust core. |
| Distributed systems / data pipelines / large-scale infra, reliability focus | Bloomberg SRE; Google Ad Manager full-stack; Edgestream production trading. Weakest of the required bullets — the CV must pull reliability language from Bloomberg and Google, not from SASE's GitHub star count. |
| Trustworthy, reproducible signals for complex applications | SASE: deterministic `fakey` provider, CI gating, persisted gates, ToolRun records, Prometheus metrics. This is the closest analogue to an eval flywheel he has shipped. |
| Ambiguous research/product boundary | SASE is a research-informed personal platform (`sase.sh` cites the coordination-layer thesis). Honest: it is not a Databricks-scale research org. |
| Nice-to-have: devtools, CI/CD, testing, observability, benchmarking | Direct hits: Edgestream pylint + test runner; Bloomberg cookiecutter + CLDR; SASE CI, telemetry, `just check`. |
| Nice-to-have: LLM/agent evals | **Gap.** SASE measures launch/stream/retry/interrupt and CI, not task-success evals (nDCG-style or LLM-as-judge). Do not claim an eval harness he has not built. |

**Verdict: apply.** This is the best *topic* match in NYC among roles that accept Python and 6 years. Recruiter should hear "founding eval infrastructure, Python, reproducible agent runs."

**Risk:** Databricks Staff often maps above Google L5. He left Google as SWE (title on the CV is not Senior/Staff). Expect a possible down-level conversation. Applying to the Senior AI Platform role at the same time is the hedge, and Databricks explicitly allows multiple applications.

### Apply 2 — Sr. Software Engineer – Backend, AI Platform (`8379331002`)

**Still live.** Location: New York City. Department: Engineering. Updated 2026-09-21. Req P-1591.

Pipeline requisition: "hiring across multiple teams" on MLflow, **AI Gateway**, Databricks Apps, **Agent Framework**, Agent Bricks, Foundation Model APIs. This is the org the 2026-10-07 job-fit report inferred as Omnigent's engineering home (from maintainer history). I treat that org mapping as **inferred**, still the right recruiter-routing target.

| Requirement | Bryan |
| --- | --- |
| 5+ years backend or infrastructure | Clears easily. |
| Scala, Go, **or Python** | Python. This is why this posting is the safe engineering door. The Staff Unity AI Gateway twin (`8468436002`) requires Scala or Go and 8+ years — skip that one. |
| Distributed systems, scalable APIs, or cloud-native infra | Bloomberg + Google. SASE is a control plane, not a multi-tenant serving stack. |
| SOA, deploy pipelines, observability | Bloomberg SRE; SASE Prometheus. |
| Bonus: developer platforms or internal tools for AI workflows | **Direct hit.** SASE is exactly that. |
| Bonus: OSS (MLflow, PyTorch, Ray) | Adjacent: `psf/black` PR #1132 (~3,500 LoC), python-boltons, funky (671★). Name black; do not pretend MLflow. |

**Verdict: apply.** Safest level match. In the Greenhouse additional-info box, ask to be routed to **Omnigent, Agent Framework, or Unity AI Gateway** engineering.

### Skip (with reasons)

These are live, and several look tempting. Qualification fails a hard requirement.

| Role | ID | Why skip |
| --- | --- | --- |
| Staff Backend, Unity AI Gateway (NYC) | `8468436002` | 8+ years **and** Scala or Go. Closest product (every coding-agent request, budgets, guardrails, MCP). Mention it to the recruiter on #2. Do not submit a CV that cannot claim Scala/Go. Base $190k–$261k. |
| Staff SWE, Fullstack – AI Product (NYC) | `8509534002` | **10+ years HTML/CSS/JS** and **10+ years** server-side web. Human-in-the-loop agent UIs are conceptually close to ACE. The years bar is not honest. Base $190.9k–$253.8k. |
| Staff SWE – AI Research Infrastructure (NYC/SF) | `8532682002` / `8552484002` | GPU fleets, cluster schedulers. |
| Staff MLE, CustomerLake (NYC) | `8614863002` | 10+ years ML/personalization; posted 2026-10-09. |
| Staff SWE, Sales Data & Agents (NYC) | `8760171002` | 10+ years plus deep CRM (Salesforce/Dynamics). |
| Sr. FDE (several NYC / Remote-NY) | e.g. `8739462002`, `8807049002` | Professional Services, customer delivery, travel. SASE is product/infra, not forward-deployed consulting. |
| Sr. Developer Advocate, Open Source — Omnigent | `8716187002` SF / `8716730002` Seattle | Only SWE-shaped requisition whose **title** names Omnigent. Location is SF or Seattle. Job is talks, meetups, contributor growth, TypeScript, "thrives in the spotlight." Apply only if DevRel and West-Coast relocation are wanted for their own sake. Zone 1 base $149.2k–$205.2k, below the two NYC engineering ranges. |
| Staff Agentic Security (US remote) | `7932280002` | 7+ years, expert Python, production agents others depend on. Platform half matches; security-domain half does not. Stretch only if a remote security seat is the goal. |

**Omnigent-named live requisitions today:** DevRel (SF, Seattle), Manager DevRel – Open Source (SF, Seattle), Staff Product Designer, Agentic Coding (MV/SF/Seattle). Zero NYC software-engineer posting names Omnigent. Engineering access is through Agent Quality, AI Platform Backend, and recruiter routing.

---

## How the panel will read the Google exit

Facts from this request, the CV repo, and public profiles:

- Google on every current CV: **June 2022 – present**.
- LinkedIn headline/experience still shows Google (public page title: "Bryan Bugyi - Google").
- GitHub bio still `{day: "SWE at Google", night: "Batman of the internet"}`.
- Actual: left Google **May 2026**; ~5 months of full-time SASE (user: "6 months unemployed").
- `https://sase.sh` is already serving docs, a handbook PDF, and the launch essay [SASE: Structured Agentic Software Engineering](https://sase.sh/blog/posts/structured-agentic-software-engineering/).

**Framing that works.** List SASE as current employment:

> Independent Software Engineer — SASE (`sase-org`) · New York, NY · May 2026 – Present

That is true. He has been the author and operator of a production-used (by him, daily) open-source control plane. Greenhouse and LinkedIn both treat a dated current role as "employed." A blank gap from May–October invites a recruiter to ask why he is unemployed; a named independent role invites "tell me about SASE," which is the interview he wants.

**Framing that fails.** "Sabbatical," "career break," or leaving Google dates open. Databricks' own interview-prep page tells candidates to reflect on achievements before applying; a present-tense Google line that is five months stale is a credibility hit on the first screen.

**Level story, said once, clearly.** Employed SWE tenure through May 2026 is seven years. Bloomberg already used Senior SWE. Google used SWE. Databricks will try to place him **Senior (IC4-ish) or Staff (IC5-ish)**. Agent Quality is posted Staff with a 6+ bar; Backend is posted Senior with a 5+ bar. Apply to both. If they down-level the Staff req, the Senior AI Platform seat is still the Omnigent-adjacent org.

**Adoption story, said once, clearly.** SASE has 5 GitHub stars. Omnigent has on the order of 10k. Present SASE as a **working system you will demo**, with design decisions and failure stories. Never as traction.

---

## CV design

### File and heritage

Model **`BryanBugyi_Google_CV.tex`** (2026 rewrite: IBM Plex Sans, single column, skill table, `\ressubheading` / `\projsubheading`). The LangChain variant is the same skeleton with a different palette. The 2010s `BryanBugyi_CV.tex` (shaded bars, LoC language table, `\today` in the header) is the wrong artifact for Greenhouse 2026.

Add a sibling pair in [bbugyi200/CV](https://github.com/bbugyi200/CV):

- `BryanBugyi_Databricks_CV.tex`
- `BryanBugyi_Databricks_CV.pdf`

Keep Batman / Google / LangChain files untouched. Databricks recruiters should receive **only** the Databricks PDF.

**Palette.** Databricks brand orange `#FF3621`, ink `#1B1918`, slate `#5C5C5C`, hairline `#E8E6E3`. Four-segment bar like the Google/LangChain variants: orange / dark / slate / light gray. Title in the PDF metadata: `Bryan Bugyi --- Databricks Resume`.

**Length.** One page. Drop Comcast (2011–2016 support) to make room for SASE-as-job. Keep Education. Shrink boltons / funky / cookie so SASE and Google/Bloomberg carry the page.

**ATS (Greenhouse).** Databricks uses Greenhouse. Single-column, selectable-text PDF, standard headings (Profile, Experience, Skills, Selected Projects, Education). No text-as-image, no multi-column skill clouds, no icons as the only label. Filename: `BryanBugyi_Databricks.pdf` when uploading.

**Keywords to appear in body text** (pulled from the two postings, written as facts, not stuffing): Python, agent evaluation, reproducible, CI/CD, testing, observability, developer platform, multi-agent, orchestration, AI Gateway, Agent Framework, coding agents, human-in-the-loop, telemetry, Linux.

### Section order

1. Header (name, title, email / phone / GitHub / LinkedIn / **sase.sh**)
2. Profile (4–5 lines)
3. Experience — **SASE current, then Google with end date, Bloomberg, Edgestream**
4. Skills
5. Selected Projects (black, funky, boltons — SASE lives in Experience)
6. Education

### Profile (draft)

Software engineer, ~7 years of production Python, Linux, and reliability work at Google, Bloomberg, and Edgestream. Since May 2026, full-time author of **SASE** ([sase.sh](https://sase.sh)): an open-source control plane over coding-agent CLIs (Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, Grok Build). Isolated workspaces, durable reviewable artifacts, typed human-approval gates, scheduled multi-agent workflows, and a Textual TUI. I want to build the same kind of layer at Databricks — agent quality infrastructure and the AI Platform that sits under Omnigent, Agent Framework, and Unity AI Gateway.

### Experience bullets (draft)

**Independent Software Engineer — SASE (sase-org)** · New York, NY · May 2026 – Present

- Architected and operate **SASE**, a Python 3.12+ CLI/TUI with a required Rust core that launches and supervises heterogeneous coding-agent CLIs behind one provider interface, plugin boundary, and config surface ([sase.sh](https://sase.sh), MIT, PyPI).
- Made agent work durable outside the transcript: numbered git workspaces claimed per run, Patches/beads/goals/artifacts, typed approval gates (plan, sudo, question, launch), and host-owned completion.
- Shipped developer-platform machinery the Agent Quality and AI Platform postings name: YAML workflows and the AXE scheduler, Prometheus telemetry, CI gating, and `fakey`, a deterministic provider that exercises launch, streaming, retry, and interrupt without model calls.
- Wrote the public architecture and launch essay at sase.sh; daily operator of the system for real engineering work on SASE itself.

**Google** · Manhattan, NY · Software Engineer · June 2022 – May 2026

- Full-stack engineer on **Google Ad Manager**: Java backend, Dart / AngularDart / Sass frontend.
- **[Bryan: add 2–3 concrete Ad Manager bullets before applying. Scale, reliability, or developer-workflow wins. The current one-liner is too thin for a four-year Google stint next to a Staff req.]**

**Bloomberg L.P.** · Manhattan, NY · SRE / Senior Software Engineer · January 2021 – May 2022

- Founding engineer, Compliance SRE; technical lead for the team's Python portfolio.
- Maintained the firm-wide Python cookiecutter.
- Authored ChangeLog Driven Release (CLDR); alpha-adopted across Compliance.

**Edgestream Partners, L.P.** · Princeton, NJ · Software Engineer · May 2019 – January 2021

- Led pylint integration into a 1M+ line Python trading codebase, including the supporting tooling.
- Large-scale work on the production team's in-house test framework and runner.
- Lead developer of the Django investor portal.

### Skills row (draft)

| Row | Content |
| --- | --- |
| Agentic systems | Multi-agent orchestration · provider adapters · human-in-the-loop gates · workspace isolation · durable artifacts · LLM/agent developer tooling |
| Quality / evals | CI/CD · test frameworks · deterministic failure fixtures · Prometheus / Grafana · reproducible pipelines |
| Primary | Python · Linux · Bash · TCP/IP |
| Working | Rust · Java · C/C++ · JavaScript · Dart |
| Tools | Git · Docker · PostgreSQL · Redis · FastAPI · Django · Pluggy · Textual · Vim |

### What not to put on the page

- SASE GitHub star count.
- "Unemployed," "career break," or an open Google end date.
- Scala, Go, Spark, Delta Lake, or MLflow as skills he does not have.
- Workspace isolation described as an OS/network sandbox (Codex approval-bypass flags exist; the job-fit report already flagged this).
- Lines-of-code for SASE. The tree is largely agent-written; sell design and failure stories.
- The Batman CV.

### Google bullets — blocking gap

I do not have Ad Manager metrics. Inventing them would be worse than a thin bullet. Before the PDF is uploaded, Bryan should add two or three lines with **system, scale, and outcome** (latency, reliability, developer time, ads-serving path — whatever is true and non-confidential). Databricks' interview-prep page also warns candidates not to bring employer confidential information; keep Google bullets at the abstraction Ad Manager already allows.

---

## Ready-to-commit LaTeX

Modeled on `BryanBugyi_Google_CV.tex`. Commit to `bbugyi200/CV` as `BryanBugyi_Databricks_CV.tex`. Fill the Google placeholder bullets before compiling the upload PDF.

```tex
% Bryan Bugyi --- Resume (Databricks / Omnigent-adjacent variant).
%
% Layout heritage: original article-class resume scaffolding by
%   (c) 2002 Matthew Boedicker <mboedick@mboedick.org>
%   (c) 2003-2007 David J. Grant <davidgrant-at-gmail.com>
%   (c) 2008 Nathaniel Johnston <nathaniel@nathanieljohnston.com>
% This work is licensed under CC BY-NC-SA 2.5
% (http://creativecommons.org/licenses/by-nc-sa/2.5/).
%
% Adapted 2026 from the Google variant (IBM Plex, single column, skill table)
% into a Databricks-flavored palette: brick orange on dark ink.

\documentclass[letterpaper,10pt]{article}

\usepackage[letterpaper,margin=0.58in,top=0.50in,bottom=0.50in]{geometry}

\usepackage[svgnames]{xcolor}
\definecolor{dborange}{HTML}{FF3621}
\definecolor{dbink}{HTML}{1B1918}
\definecolor{dbslate}{HTML}{5C5C5C}
\definecolor{dbline}{HTML}{E8E6E3}
\definecolor{dbdark}{HTML}{2B2726}

\usepackage{plex-sans}
\usepackage{plex-mono}
\usepackage{microtype}
\renewcommand{\familydefault}{\sfdefault}

\usepackage{enumitem}
\usepackage{fancyhdr}
\usepackage{multicol}
\usepackage{tabularx}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\fancyfoot[C]{{\color{dbslate}\fontsize{8pt}{9.5pt}\selectfont\thepage}}

\raggedbottom
\raggedright
\setlength{\parskip}{3pt}
\setlength{\parindent}{0pt}
\setlength{\tabcolsep}{0pt}
\frenchspacing

\newcommand{\midsep}{\,\textcolor{dbline}{\textbullet}\,}
\newcommand{\dbbar}{%
  \noindent
  \textcolor{dborange}{\rule{0.34\textwidth}{1.8pt}}%
  \textcolor{dbdark}{\rule{0.22\textwidth}{1.8pt}}%
  \textcolor{dbslate}{\rule{0.22\textwidth}{1.8pt}}%
  \textcolor{dbline}{\rule{0.22\textwidth}{1.8pt}}%
}

\newcommand{\resheading}[1]{%
  \par\addvspace{9pt}%
  \noindent
  {\bfseries\color{dborange}\fontsize{10pt}{12pt}\selectfont%
   \textls*[90]{\MakeUppercase{#1}}}%
  \hspace{0.65em}%
  {\color{dbline}\leaders\hrule height 0.45pt\hfill\kern0pt}%
  \par\nobreak\addvspace{3pt}%
}

\setlist[itemize,1]{
  label={\textcolor{dborange}{\raisebox{0.15ex}{\scriptsize\textbullet}}},
  leftmargin=1.25em,
  topsep=1pt,
  itemsep=1.4pt,
  parsep=0pt
}

\newcommand{\ressubheading}[4]{%
  \par\addvspace{3pt}%
  \noindent
  \begin{tabular*}{\textwidth}{@{}l@{\extracolsep{\fill}}r@{}}
    {\bfseries\color{dbink}\fontsize{10.4pt}{12.4pt}\selectfont #1} &
    {\color{dbslate}\fontsize{9.2pt}{11pt}\selectfont #2} \\[0.5pt]
    {\color{dbink}\fontsize{9.9pt}{11.7pt}\selectfont #3} &
    {\color{dbslate}\fontsize{8.8pt}{10.5pt}\selectfont #4}
  \end{tabular*}\par\vspace{-3pt}
}

\newcommand{\projsubheading}[4]{%
  \par\addvspace{3pt}%
  \noindent
  \begin{tabular*}{\textwidth}{@{}l@{\extracolsep{\fill}}r@{}}
    {\bfseries\color{dbink}\fontsize{10.4pt}{12.4pt}\selectfont #1} &
    {\ttfamily\color{dbslate}\fontsize{8.6pt}{10.3pt}\selectfont #2} \\[0.5pt]
    {\color{dbink}\fontsize{9.9pt}{11.7pt}\selectfont #3} &
    {\color{dbslate}\fontsize{8.8pt}{10.5pt}\selectfont #4}
  \end{tabular*}\par\vspace{-3pt}
}

\newcommand{\skillrow}[2]{%
  {\bfseries\color{dborange}\fontsize{8.8pt}{11pt}\selectfont #1} &
  {\color{dbink}\fontsize{9.5pt}{11pt}\selectfont #2} \\[1.4pt]
}

\usepackage{hyperref}
\hypersetup{
  colorlinks=true,
  urlcolor=dborange,
  linkcolor=dborange,
  citecolor=dborange,
  pdftitle={Bryan Bugyi --- Databricks Resume},
  pdfauthor={Bryan Bugyi}
}

\begin{document}
\color{dbink}

\noindent
\begin{tabular*}{\textwidth}{@{}l@{\extracolsep{\fill}}r@{}}
  {\bfseries\fontsize{27pt}{29pt}\selectfont Bryan Bugyi} &
  \begin{minipage}[b]{2.85in}
    \raggedleft
    {\color{dbslate}\fontsize{9.5pt}{12pt}\selectfont
     Software Engineer\\
     Agentic systems \& developer platforms}
  \end{minipage}
\end{tabular*}

\vspace{5pt}
\dbbar
\vspace{5pt}

\noindent
{\color{dbink}\fontsize{9.0pt}{11pt}\selectfont%
\href{mailto:bryanbugyi34@gmail.com}{bryanbugyi34@gmail.com}%
\midsep
(609)~500-7081%
\midsep
\href{https://github.com/bbugyi200}{github.com/bbugyi200}%
\midsep
\href{https://linkedin.com/in/bryan-bugyi}{linkedin.com/in/bryan-bugyi}%
\midsep
\href{https://sase.sh}{sase.sh}%
}

\resheading{Profile}
Software engineer with seven years of production Python, Linux, and reliability work at Google, Bloomberg, and Edgestream. Since May 2026, full-time author of \textbf{SASE} (\href{https://sase.sh}{sase.sh}): an open-source control plane over coding-agent CLIs, with isolated workspaces, durable reviewable artifacts, typed human-approval gates, scheduled multi-agent workflows, and a Textual TUI. I want to build that layer at Databricks --- evaluation infrastructure for agents, and the AI Platform under Omnigent, Agent Framework, and Unity AI Gateway.

\resheading{Experience}

\ressubheading{SASE (sase-org)}{New York, NY}{Independent Software Engineer}{May 2026 -- present}
\begin{itemize}
  \item Architected and operate \textbf{SASE}, a Python 3.12+ CLI/TUI with a required Rust core that launches and supervises heterogeneous coding-agent CLIs (Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, Grok Build) behind one provider interface and plugin boundary.
  \item Made agent work durable outside the chat transcript: numbered git workspaces claimed per run, Patches / beads / artifacts, typed approval gates (plan, sudo, question, launch), and host-owned completion.
  \item Shipped developer-platform machinery: YAML workflows and the AXE scheduler, Prometheus telemetry, CI gating, and \texttt{fakey}, a deterministic provider that exercises launch, streaming, retry, and interrupt paths without model calls.
\end{itemize}

\ressubheading{Google}{Manhattan, NY}{Software Engineer}{June 2022 -- May 2026}
\begin{itemize}
  \item Full-stack engineer on Google Ad Manager; Java backend, Dart / AngularDart / Sass frontend.
  \item \textit{[Add 2--3 concrete, non-confidential Ad Manager bullets: system, scale, outcome.]}
\end{itemize}

\ressubheading{Bloomberg L.P.}{Manhattan, NY}{Site Reliability Engineer / Senior Software Engineer}{January 2021 -- May 2022}
\begin{itemize}
  \item Founding engineer on Compliance SRE; technical lead across the team's Python portfolio.
  \item Maintained Bloomberg's firm-wide Python cookiecutter; authored ChangeLog Driven Release (CLDR), adopted in alpha across Compliance.
\end{itemize}

\ressubheading{Edgestream Partners, L.P.}{Princeton, NJ}{Software Engineer}{May 2019 -- January 2021}
\begin{itemize}
  \item Led \texttt{pylint} integration into a 1M+ line Python trading codebase and built the supporting tooling.
  \item Large-scale improvements to the production team's in-house testing framework and runner; lead developer of the Django investor portal.
\end{itemize}

\resheading{Skills}
\noindent
\begin{tabularx}{\textwidth}{@{}p{1.42in}@{\hspace{0.40em}}X@{}}
\skillrow{Agentic systems}{multi-agent orchestration\,$\cdot$\,provider adapters\,$\cdot$\,human-in-the-loop gates\,$\cdot$\,workspace isolation\,$\cdot$\,durable artifacts}
\skillrow{Quality / evals}{CI/CD\,$\cdot$\,test frameworks\,$\cdot$\,deterministic failure fixtures\,$\cdot$\,Prometheus / Grafana\,$\cdot$\,reproducible pipelines}
\skillrow{Primary}{Python\,$\cdot$\,Linux\,$\cdot$\,Bash\,$\cdot$\,TCP/IP}
\skillrow{Working}{Rust\,$\cdot$\,Java\,$\cdot$\,C/C++\,$\cdot$\,JavaScript\,$\cdot$\,Dart}
\skillrow{Tools}{Git\,$\cdot$\,Docker\,$\cdot$\,PostgreSQL\,$\cdot$\,Redis\,$\cdot$\,FastAPI\,$\cdot$\,Django\,$\cdot$\,Pluggy\,$\cdot$\,Textual}
\end{tabularx}

\resheading{Selected Projects}

\projsubheading{psf/black}{Python}{The uncompromising Python code formatter.}{2019--2021}
\begin{itemize}
  \item Rewrote black's string-handling logic ($\sim$3{,}500 LoC) in \href{https://github.com/psf/black/pull/1132}{PR \#1132}; closed five unrelated user-filed issues in one change.
\end{itemize}

\projsubheading{bbugyi200/funky}{Python, Shell}{Interactive, versionable shell functions.}{2017--2021}
\begin{itemize}
  \item 670+ GitHub stars; accepted external issues and code.
\end{itemize}

\projsubheading{python-boltons/*}{Python}{Libraries we think should be ``builtins''.}{2021--present}
\begin{itemize}
  \item Founder. \texttt{cc-python}, \texttt{clack}, \texttt{eris}, \texttt{hush}, \texttt{logrus}.
\end{itemize}

\resheading{Education}
\ressubheading{Rutgers University}{New Brunswick, NJ}{B.S.\ Computer Science (minor in Mathematics)}{September 2015 -- May 2019}

\end{document}
```

Compile with the same Plex fonts the Google variant already uses. Keep the PDF text-selectable.

---

## LinkedIn (and GitHub) — what has to change before apply

Public LinkedIn still presents Bryan as a **current Google employee**. Greenhouse will import that. A recruiter who opens both the PDF (Google ended May 2026) and LinkedIn (Google present) will trust neither.

Do this **before** submitting, in this order:

1. **Experience – Google.** End date **May 2026**. Description: Ad Manager, Java + Dart/AngularDart. Past tense.
2. **Experience – SASE (current).** Title: Independent Software Engineer (or Author / Principal Engineer). Company: SASE, or “Self-employed” with SASE in the title. Dates: **May 2026 – Present**. Location: **New York City Metropolitan Area** (LinkedIn still shows Mount Holly, NJ; GitHub has shown Cranford, NJ. For NYC-hub roles, metro-area is the honest targeting location). Description: 3–4 bullets matching the CV. Link `https://sase.sh` and `https://github.com/sase-org/sase`.
3. **Headline.** Something a Databricks recruiter can parse in one line, for example:
   `Software Engineer · Agentic developer platforms (SASE) · Python · ex-Google, Bloomberg`
   Drop “SWE at Google.”
4. **About.** 1,200–1,600 characters. Lead with SASE as a meta-harness / control plane over coding-agent CLIs; name isolated workspaces, gates, durable artifacts; close with NYC + Databricks Agent Quality / AI Platform. Mention Omnigent as the industrial version of the problem he already built for himself — once, without claiming he works on it.
5. **Featured.** `sase.sh` launch essay, GitHub `sase-org/sase`, black PR #1132.
6. **Open to Work.** Recruiter-only, titles: Staff Software Engineer, Senior Software Engineer, Software Engineer. Locations: New York City (on-site/hybrid). Skip the public green banner for a two-role targeted shot.
7. **Custom “Open to” / job alerts.** Databricks, New York, Software Engineer.
8. **GitHub profile bio.** Replace `{day: "SWE at Google", ...}` with the same headline idea, plus `https://sase.sh`.
9. **Contact visibility.** Email reachable to recruiters.
10. **Consistency pass.** PDF, LinkedIn, GitHub, and `bryanbugyi.com` if it still says Google. Same dates, same title, same sase.sh URL.

Databricks interviews are virtual (Google Meet) unless a recruiter says otherwise. NYC hub existence still matters for the req location; be ready to confirm hybrid/commute from NJ if that is the living situation.

---

## Pitches

Paste into Greenhouse “additional information” / cover letter. One per application. Databricks says you may apply to multiple roles; tailor each.

### Pitch — Staff Software Engineer, Agent Quality (NYC)

I am applying for Staff Software Engineer, Agent Quality in New York.

For the last five months I have been the full-time author of SASE (sase.sh), an open-source control plane over coding-agent CLIs. Before that I spent four years at Google on Ad Manager and two years as a founding Compliance SRE / Senior SWE at Bloomberg, after a Python production role at Edgestream. About seven years of employed engineering, all in New York.

Agent Quality is the seat I want. I have been building the unglamorous half of an agent platform: isolated git workspaces per run, durable records that survive the terminal, typed human-approval gates, CI, Prometheus telemetry, and a deterministic fake provider so launch/stream/retry/interrupt paths can regress without spending tokens. That is evaluation-adjacent infrastructure — reproducible signals for a messy, non-deterministic system — which is what the posting describes for Genie Agents and the agent development platform.

I do not yet have a published LLM-as-judge or golden-task eval harness. I do have the platform instincts to stand one up, and I want that to be my job. I am in NYC, I can demo SASE end to end, and I can start a conversation from the launch essay at sase.sh.

### Pitch — Sr. Software Engineer – Backend, AI Platform (NYC)

I am applying for Sr. Software Engineer – Backend on the AI Platform team in New York, and I would like to be routed toward Omnigent, Agent Framework, or Unity AI Gateway.

SASE (sase.sh) is my full-time work since leaving Google in May 2026. It is a Python/Rust control plane that wraps Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, and Grok Build: one YAML/config surface, plugin boundary, and TUI, with policies as explicit gates rather than an always-on chat. That is the same category Databricks productized as Omnigent (meta-harness, policies, sandboxes, live sessions) and as the AI Platform substrate under Agent Framework and AI Gateway.

I am a Python backend/infra engineer, not a Scala/Go one, which is why this Senior posting is the right door (Python is a listed language; the Staff Unity AI Gateway req is not). Earlier: Google Ad Manager (Java/Dart), Bloomberg founding SRE and Senior SWE on the Python Compliance stack, Edgestream production Python. Open source includes a 3,500-line rewrite of psf/black string handling.

I live in the NYC area. Happy to walk a recruiter through a SASE demo and through how I would transfer those control-plane problems onto Databricks’ managed stack.

---

## Application mechanics

1. Update LinkedIn + GitHub bio first (same day).
2. Fill Google CV bullets; compile `BryanBugyi_Databricks_CV.pdf`.
3. Apply on **databricks.com** Greenhouse links above, not LinkedIn Easy Apply. Attach the Databricks PDF. Paste the matching pitch in additional info.
4. Apply to **both** reqs the same day. Staff Agent Quality is the stretch-up; Senior AI Platform is the level-safe Omnigent-adjacent org.
5. Work authorization / NYC presence: be ready on the recruiter call. Interviews are virtual by default ([Databricks interviewing](https://www.databricks.com/company/careers/interview-prep)); the reqs are NYC.
6. Timeline: Databricks publishes **two to three months** end to end; recruiter call → hiring-manager or technical screen → 4–6 interview loop → references → hiring committee (engineering). Feedback target 48 hours after the final loop; chase at one week.
7. **Do not wait for a new blog announcement.** The launch essay is already at sase.sh. If a polished public post lands in a week, send the URL to the recruiter as a follow-up. A Staff req posted 2026-09-24 is already 16 days old.
8. Optional, parallel, not a gate: a small public eval harness over SASE runs (task suite + pass/fail + CI gate) is the single strongest interview artifact for Agent Quality. An Omnigent community contribution (Muse harness package or a runner/host bug, DCO-signed) is the referral path. Neither should delay the application.

**Recruiter one-liner** (if they ask “why Databricks / why now”):

> I left Google in May to build SASE full time — a meta-harness over coding-agent CLIs. Databricks is the company that productized that layer as Omnigent and is hiring the NYC R&D hub around agentic AI. I want to do that work on Agent Quality and the AI Platform, in New York.

---

## Implementer checklist (CV repo)

When a later agent commits to `bbugyi200/CV`:

- [ ] Add `BryanBugyi_Databricks_CV.tex` from the draft above (Google bullets filled by Bryan).
- [ ] Compile PDF with the same Plex fonts as the Google variant.
- [ ] Leave Batman / Google / LangChain files unchanged.
- [ ] Do not rewrite LinkedIn from the agent account; Bryan clicks the LinkedIn UI himself using the checklist in this report.

---

## Caveats

- Greenhouse snapshot: **2026-10-10**, 892 jobs. Re-check both `gh_jid` links on apply day.
- Omnigent team ownership of AI Platform Backend is inferred from 2026-10-07 job-fit (maintainers / MLflow history), not from the posting text.
- Google Ad Manager bullets are still under-specified; that is the one content hole Bryan has to fill.
- Comp figures are **base salary only**, as printed on the postings. Equity and bonus are extra.
- “Qualified” means the posted bars are honestly met and the work is in-domain. It is not an offer prediction.
- I did not contact Databricks or submit any application.

## Appendix: NYC engineering inventory (2026-10-10)

Live jobs whose location string includes New York and whose department is Engineering / Engineering-Pipeline / Executive Engineering-Pipeline / Research-adjacent SWE:

| ID | Title | Location |
| --- | --- | --- |
| 8842963002 | Staff Software Engineer, Agent Quality | New York City |
| 8379331002 | Sr. Software Engineer- Backend | New York City |
| 8468436002 | Staff Backend Software Engineer (Unity AI Gateway) | New York |
| 8509534002 | Staff Software Engineer, Fullstack – AI Product | New York City |
| 8532682002 / 8552484002 | Staff Software Engineer – AI Research Infrastructure | NYC / SF |
| 8384595002 | Staff Software Engineer – Frontend (NYC) | New York City |
| 8760165002 | Staff Software Engineer, Ads Measurement & Orchestration | New York City |
| 8760176002 | Staff Software Engineer, Data Collection (Tags & SDKs) | New York City |
| 8760171002 | Staff Software Engineer, Sales Data & Agents | New York City |
| 8614863002 | Staff Machine Learning Engineer, CustomerLake | New York City |
| 8709386002 | Engineering Manager, CustomerLake Profile Agents | New York City |

Only the first two are apply-now for this candidate.
