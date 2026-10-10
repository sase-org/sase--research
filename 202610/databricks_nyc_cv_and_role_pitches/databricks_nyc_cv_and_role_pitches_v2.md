# Databricks NYC application follow-ups (v2)

> **Checked:** 2026-10-10. Companion update to the [original report](databricks_nyc_cv_and_role_pitches.md).
>
> **Recommendation:** Prepare the remaining personal details, then apply to both live NYC postings on the same day. Re-open the listings immediately before applying. The Staff Agent Quality fit is strong on evaluation infrastructure but carries a Staff-level scope risk; the Senior Backend role is the safer level match. No application or third-party contact has been made.

## Postings re-verified

Both Databricks career pages showed **Apply now** when checked on 2026-10-10.

| Role | Current posting | Current requirements and fit |
| --- | --- | --- |
| Staff Software Engineer – Agent Quality (P-1567), NYC | [Posting 8842963002](https://www.databricks.com/company/careers/engineering---pipeline/staff-software-engineer-agent-quality-8842963002) · $200,000–$265,000 base range | Calls for 6+ years, production/research Python, reliable distributed systems or infrastructure, reproducible evaluation signals, and influence across teams. SASE's ToolRun records, failure triage, deterministic `fakey`, and CI are relevant. The posting centers on building Genie Agent evaluation infrastructure. The task-success gap remains real: SASE has no eval of real-agent task completion, and the final decision was to skip the pilot. Staff-level cross-team influence is the main qualification risk. |
| Sr. Software Engineer – Backend, AI Platform (P-1591), NYC | [Posting 8379331002](https://www.databricks.com/company/careers/engineering/sr-software-engineer--backend-8379331002) · $165,300–$219,675 base range | Calls for 5+ years in backend/infrastructure, Scala, Go, or Python, distributed systems/scalable APIs/cloud infrastructure, and service architecture, deployment pipelines, and observability. SASE is relevant developer tooling for AI workflows. The posting hires across AI Platform teams and names MLflow, AI Gateway, Databricks Apps, Agent Framework, Agent Bricks, and Foundation Model APIs. ML infrastructure, GPU orchestration, and contributions to MLflow/PyTorch/Ray are bonuses, not stated requirements. |

These checks confirm the role IDs, NYC locations, listed requirements, and application availability. They are not an offer prediction. The career pages do not establish that either team is connected to Omnigent; ask the recruiter rather than assuming.

## Work completed

- **CV cleanup:** The base, Batman, Google, and LangChain CV sources and PDFs were updated. The base CV now includes the approved SASE entry; Google dates end May 2026 in all four PDFs. The missing `gutils.tex` dependency was removed from base and Batman. All four PDFs rebuilt successfully, page counts held at 3/2/2/2, text and stale-claim scans passed, and rendered pages were reviewed. TinyTeX packages `ebgaramond`, `fontawesome5`, `listings`, `ulem`, and `tocloft` were installed.
- **Interview preparation:** [`interview-prep pack`](databricks_nyc_cv_and_role_pitches_interview_prep.md) contains six SASE design-story cards and an Agent Quality brief on trace evaluation, judge failure modes, repeated trials/pass@k, and production traces as regression sets. It deliberately does not invent a reason for leaving Google.
- **Agent-eval pilot:** Not built, by final reviewer decision (`eval_pilot = skip`). No real runs or task-success measurements exist. This remains optional and must not delay applying.

## Bryan's remaining actions

1. **Finish the CV details before upload.** Add one or two accurate, non-confidential Google Ad Manager bullets and confirm the May 2026 Google end date and May 2026 SASE full-time start. Confirm the contact location is accurate for NYC roles. Optionally add a specific Bloomberg SRE/on-call example if useful and defensible. Review the final PDF; do not add unsupported scale claims.
2. **Make the public profiles consistent.** LinkedIn still needs the Google end date and past-tense description, a SASE position, current headline/About/location, and the planned profile cleanup. GitHub still needs the Google-era bio/company/hireability details updated. These changes require Bryan's accounts and judgment. Check that dates, title, location, and `sase.sh` agree with the CV.
3. **Apply and handle recruiter conversations.** Once the CV and profiles are ready, submit to both roles on Databricks' site if still live, using the role-specific pitches in the original report. Recheck each listing on the application day. Ask about NYC team placement and whether Agent Quality would consider Senior. No application, referral request, or recruiter message has been sent.
4. **Answer personal questions in your own words.** Only Bryan can state why he left Google. Confirm the work arrangement and any ownership claims he plans to make in the CV or interview.
5. **Optional after applying:** If the onsite is scheduled and the pilot still seems useful, build it without delaying the applications. Use 8–12 coding tasks from real merged history, frozen at each selected commit's parent, with that commit's tests as oracle. Record explicit test/scope/artifact checks and keep failures/timeouts in the denominator; capture harness, model, version, and exact prompt; repeat a subset and report variance, pass@k, and per-task outcomes. MLflow traces/scorers are optional; localize one regression if the data supports it. Keep these task-success results separate from `fakey` conformance. The full deferred requirements are recorded on phase `sase-1jo.3`.

The original report retains the detailed role comparison, CV wording, pitches, LinkedIn/GitHub checklists, and application timeline. Its source research was a 2026-10-10 snapshot; recheck external facts at the point of use.
