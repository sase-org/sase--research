# Databricks NYC Application Strategy: Tailored CV, LinkedIn, and Role Pitches

Researcher: mus (`__mus`) — independent swarm report.
Date: 2026-10-10. Scope: 1–2 NYC Databricks roles, CV modeled on `bbugyi200/CV`, LinkedIn refresh, per-role pitches.

## 1. Question and bottom line

Bryan Bugyi (7 years: Edgestream 2019–2021, Bloomberg Senior SWE / founding CSRE 2021–2022, Google SWE Ad Manager 2022–May 2026, then full-time `sase` May–Oct 2026) wants to apply to one or two NYC Databricks roles motivated by the Omnigent launch, with a CV forked from his existing LaTeX CV repo, corrected employment dates, LinkedIn guidance, and an honest qualification screen plus a short pitch per recommended role.

Bottom line: apply to exactly two roles, in this order: (1) **Senior Software Engineer – AI Platform (NYC)** as the level-accurate primary, and (2) **Staff Software Engineer, Agent Quality (NYC)** as the mission-accurate stretch. Both are Python + production GenAI/agent infrastructure roles where `sase` is directly relevant. Do not apply to field/FDE, sales-data, or research-scientist postings — level or skill mismatch. Fork `BryanBugyi_LangChain_CV.tex` into a new `BryanBugyi_Databricks_CV.tex`, fix Google to `June 2022 – May 2026`, add an Independent `sase` entry for `May 2026 – present`, retarget bullets to evals / orchestration / sandboxing / telemetry, ship the `sase.sh` blog post first, then apply.

## 2. Important gap: named context file was not found

The prompt cites `databricks_omnigent_job_fit.md` in the research sidecar repo. I searched the materialized research clone for `*databricks*`, `*omnigent*`, and `*job_fit*` and grepped Markdown for `databricks_omnigent`; the only hits were the prior `omnigent_meta_harness_lessons_for_sase/` swarm directory. No file by the cited name exists in the research clone as of this session. This report therefore reconstructs fit from primary sources: the CV checkout (`gh:bbugyi200/CV`), the `sase` checkout and live `http://sase.sh` (HTTP 200, MkDocs Material, verified 2026-10-10), the `omnigent-ai/omnigent` GitHub repo, Databricks careers pages, and the Staff Agent Quality posting (a16z mirror, posted 2026-09-24).

## 3. What Omnigent is and why it matters for this application

- Announced 13 Jun 2026 (Matei Zaharia, Kasey Uhlenhuth, Corey Zumar) at Data + AI Summit 2026, Apache-2.0, copyright Databricks Inc.
- Canonical repo is `omnigent-ai/omnigent` (not `databricks/omnigent`); ~10.7k stars / ~1.7k forks at time of research. Site `omnigent.ai`.
- Architecture is a **meta-harness**: it sits above Claude Code, Codex, Cursor, Pi, and custom YAML-defined agents instead of replacing them, providing one surface to compose, govern, sandbox, share sessions, enforce policies, and collaborate in real time.
- This maps almost 1:1 to `sase`: `sase` orchestrates Claude Code, Gemini CLI, Codex (plus Antigravity/Qwen/OpenCode/Muse/Grok Build) into a managed pipeline with ACE (Textual supervision TUI), AXE daemon, YAML workflow engine, `pluggy` plugin system (Git/GitHub/Chezmoi/Telegram/Gemini/Neovim), Prometheus telemetry (33 pipeline metrics), and bead-based agent task queues. The honest framing is "independent parallel implementation of the same thesis," not "Omnigent clone."

## 4. Existing CV inventory (what to fork)

`gh:bbugyi200/CV` (origin `git@github.com:bbugyi200/CV.git`) currently holds four variants: `BryanBugyi_CV.tex` (legacy general), `BryanBugyi_Batman_CV.tex`, `BryanBugyi_Google_CV.tex`, and `BryanBugyi_LangChain_CV.tex`. The last two are the 2026 modern sans-first layouts and the only sensible fork bases.

Fork the **LangChain variant**, not the Google variant: forest/teal/leaf palette and "Agentic-AI Systems & LLM Tooling" subtitle already frame the reader correctly for Databricks; the Google variant's red/blue/yellow bar actively signals the employer just left. Both variants share the same staleness defects that the Databricks fork must fix:

- Google reads `June 2022 – present`; must become `June 2022 – May 2026`.
- No entry covers May 2026 – present full-time `sase` work; a 6-month gap currently reads as unemployment.
- Profile says "for the past year, focused on agentic-AI tooling" without stating full-time independent status or linking `sase.sh`, docs, or the forthcoming launch post.
- `sase` bullets name ACE/AXE/YAML/`pluggy`/Prometheus/beads but give no scale, eval, sandbox, or governance language Databricks screens for.
- Skills list omits evals, sandboxing, and agent-governance vocabulary entirely.

## 5. Recommended roles (NYC only, qualification-screened)

Only the two below survive a "really qualified" screen. Both are NYC, Python-heavy, production-agent-platform roles.

### 5.1 Primary: Senior Software Engineer – AI Platform (NYC)

Why it fits: 0-to-1 vertical-AI-applications team in the NYC engineering office, described as startup-like with Databricks resources. Minimums are ~6+ years building/operating large-scale production backend/platform systems plus hands-on production GenAI/LLM integration. Bryan has 7 years, Python/Linux/distributed-systems depth, Django/FastAPI/ZeroMQ/PostgreSQL/Redis/Docker production history, Bloomberg founding-team and Google Ad Manager production experience, and a year of production agentic-system building with `sase`. Full-stack scope (dynamic user-centric experiences) matches his Ad Manager Java/Dart/AngularDart/Sass plus Edgestream Django portal history. Level match is exact: Senior, not Staff.

### 5.2 Stretch: Staff Software Engineer, Agent Quality (NYC, P-1567, USD 200–265k)

Why it fits despite Staff scope: founding member of a new team building evaluation infrastructure for Genie Agents — benchmarking, regression detection, quality measurement, and the flywheel from production signals back into training/iteration. Requirements are 6+ years, strong Python, distributed systems/data pipelines at scale with reliability/correctness rigor, ability to build trustworthy reproducible signals across research/product boundaries. Nice-to-haves read like Bryan's resume: devtools, CI/CD, testing frameworks, observability/benchmarking, LLM/agent eval familiarity. His differentiators are unusually on-point: large-scale test-runner improvements at Edgestream, firm-wide Python cookiecutter + CLDR release methodology at Bloomberg, `black` string-logic rewrite (~3,500 LoC, 5 issues closed), `pluggy` plugin architecture + 33-metric Prometheus telemetry + bead queues in `sase`. Risk is level: he has never held Staff; Bloomberg Senior is the highest title. Apply anyway as a second application with a Staff-scope narrative (founding teams, firm-wide standards, cross-team influence), but expect leveling scrutiny.

### 5.3 Roles considered and rejected

- Forward Deployed / Field / Sales Data & Agents: sales-embedded, customer-facing delivery; wrong motion for a platform/tooling engineer.
- GenAI Research Scientist: requires large-scale LLM pre-training/fine-tuning/RLHF publication record; not Bryan's profile.
- Federal FDE / remote-only / non-NYC postings: out of stated geography.
- Any role demanding Scala/Spark/Delta Lake depth as a hard requirement: Bryan's Spark/Data-platform depth is thinner than his Python/agent-tooling depth; the two picks above do not hinge on it.

## 6. CV design: `BryanBugyi_Databricks_CV.tex`

Create one new file in `bbugyi200/CV`, copied from `BryanBugyi_LangChain_CV.tex` (keep the LangChain layout/palette; only change `pdftitle` to `Bryan Bugyi --- Databricks Resume`). Do not edit the Google/LangChain variants in place — a company-targeted fork preserves them. Suggested build + commit from a checkout of `gh:bbugyi200/CV`:

- Copy, edit, then `pdflatex BryanBugyi_Databricks_CV.tex` (or the repo's usual LaTeX build) and commit `BryanBugyi_Databricks_CV.tex` + PDF together.
- Commit message: `feat: add Databricks-targeted resume variant`.

Content changes (all in the `.tex`, in order):

1. Header subtitle: `Software Engineer / Agentic-AI Developer Tooling` (matches Databricks vocabulary; drop "LLM Tooling" phrasing).
2. Profile (rewrite): "Software engineer with seven years shipping production Python, Linux, and distributed-systems work across Google, Bloomberg, and Edgestream. Since May 2026, full-time independent work on `sase` (sase.sh) — a multi-agent software-engineering toolkit orchestrating Claude, Gemini, and Codex with supervised agents, structured workflows, sandboxing, telemetry, and eval-oriented regression tracking. Seeking NYC agent-platform work; Omnigent's meta-harness thesis matches what I build daily."
3. Experience — Google: `June 2022 – May 2026` (Manhattan, NY). Add one second bullet quantifying Ad Manager scope (requests/users/scale if disclosable) to counter the current single-bullet thinness.
4. Experience — new entry above Google: `Independent — sase: Structured Agentic Software Engineering | Brooklyn/NYC Remote | May 2026 – present`. Three bullets: (a) full-time architect of ACE/AXE/YAML engine + `pluggy` integrations + 33-metric Prometheus telemetry + bead queues; (b) eval/governance work — benchmarking harnesses, regression detection, sandbox policy enforcement, reproducible multi-agent runs (name the concrete mechanisms, even if lightweight); (c) shipped docs at `sase.sh` + launch blog post (title + date once published; before that, "launch post in review, available on request").
5. Bloomberg/Edgestream/Comcast: keep, but trim Comcast to one line if space is needed — at 7 years experience it is optional context, not a selling point.
6. Skills — add one row: `Agent Infra: evaluation harnesses / benchmarking / sandboxing / policy enforcement / multi-agent orchestration / telemetry (Prometheus)`. Keep Primary as Python/Linux/TCP-IP/Bash; add `pytest`-family testing and CI language if true.
7. Selected Projects — reorder: `sase` first (expand governance/sandboxing/eval sentence), `psf/black` second (keep ~3,500 LoC + 5-issues-closed proof of code-quality judgment), `python-boltons` third, collapse `funky`/`cookie`/misc into one line with stars. Every bullet must end with evidence (metric, link, or adoption fact).
8. Length: one page is strongly preferred for Databricks SWE screening; two pages only if the `sase` eval content genuinely needs it.

What NOT to do: do not claim Omnigent contributions, Databricks internals (Spark/Delta/Lakehouse depth beyond what is true), ML-training/RLHF expertise, or a Staff title never held. Do not use the Google color bar for a Databricks application.

## 7. LinkedIn refresh (guidance, not automation)

LinkedIn has no API for these edits; make them by hand in this order:

- Headline: `Software Engineer — Agentic-AI Developer Tooling | Python, Multi-Agent Orchestration, Evals & DevTools | ex-Google`.
- About: 3–4 sentences mirroring the new Profile, ending with `Building sase (sase.sh); launch post [title] — [month] 2026. Seeking NYC agent-platform roles.`
- Experience: end `Google — Software Engineer` at May 2026 (keep Manhattan location); add `Founder / Independent — sase`, May 2026 – Present, with the same three CV bullets shortened plus `sase.sh` and GitHub links.
- Featured: pin `sase.sh`, the launch post, and the `sase` repo (or `omnigent-ai/omnigent` comparison write-up if one is published).
- Skills: add `LLM evaluation`, `AI agent orchestration`, `Developer tools`, `Python`, `Distributed systems`; request 2–3 endorsements from Bloomberg/Google or OSS collaborators.
- Open To Work (recruiter-only): `Senior/Staff Software Engineer, AI Platform / Agent Infrastructure, Greater NYC, onsite/hybrid`.

## 8. Timing: blog post before applications

`sase.sh` already resolves (verified live). Publish the launch post in the stated 1–2 week window first, then apply: the post is the only public proof of the May–Oct 2026 full-time `sase` claim and the strongest attachment for both roles. Sequence: (a) finish + deploy post to `sase.sh`; (b) commit Databricks CV with the post title/URL; (c) update LinkedIn; (d) submit AI Platform first, Agent Quality second 2–3 days later with a tailored pitch each. In the application "links" field, use `sase.sh` + post URL + GitHub, in that order.

## 9. Short pitches (paste-ready, honest)

### Pitch 1 — Senior SWE, AI Platform (NYC)

> I spent seven years shipping production Python and distributed systems at Google (Ad Manager), Bloomberg (founding Compliance SRE, firm-wide Python tooling), and Edgestream (1M+ line trading system), and since May I have worked full-time on `sase` (sase.sh), a multi-agent toolkit that orchestrates Claude, Gemini, and Codex with supervised agents, structured YAML workflows, sandboxing, and Prometheus telemetry I use daily. That is the same 0-to-1 problem as your NYC AI Platform team: turning GenAI capability into reliable vertical product engineers and users trust. I would bring Python depth, production-ops judgment, and a year of hard-won multi-agent failure modes to the role.

### Pitch 2 — Staff SWE, Agent Quality (NYC)

> I build the infrastructure that makes agents trustworthy. At Bloomberg I owned the Python portfolio and firm-wide scaffolding/release methodology; at Edgestream I hardened a 1M+ line test framework; on `psf/black` I closed five issues with one ~3,500-line string-logic rewrite. On `sase` I built the eval-adjacent core I would bring to Genie Agents: repeatable multi-agent runs, regression tracking, telemetry-backed quality signals, and the dev loop connecting signals back into fixes. I have not held a Staff title, but I have done Staff-shaped work — founding teams and setting org-wide standards — and agent quality is the Staff-scope problem I am already solving independently.

## 10. Verification, limits, and follow-ups

- Verified this session: CV `.tex` contents and git history, `sase` README thesis, `sase.sh` liveness (HTTP 200), `omnigent-ai/omnigent` identity and star/fork scale, Staff Agent Quality posting text (pay band, P-1567, requirements/nice-to-haves).
- Not verified: the missing `databricks_omnigent_job_fit.md` (lead should supply or retract the pointer); exact current req IDs for the AI Platform NYC posting (Greenhouse IDs rotate — re-pull on apply day); Bryan's quantifiable Google Ad Manager scope and the final blog-post title/URL (both needed before the CV ships).
- Suggested follow-ups: lead synthesizer reconciles the four swarm reports on role choice; a second pass diffs the committed Databricks PDF against this spec; LinkedIn edits confirmed by screenshot rather than self-report.
