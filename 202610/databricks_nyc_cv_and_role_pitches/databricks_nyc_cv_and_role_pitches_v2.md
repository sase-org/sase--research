# Databricks NYC application follow-ups (v2)

> **Checked:** 2026-10-10. Companion update to the [original report](databricks_nyc_cv_and_role_pitches.md); it keeps the LinkedIn copy and pitches, linked below rather than pasted here.

> **Recommendation:** Prepare the personal details below, then apply to both live postings on the same day, and re-open each listing first. No application or third-party contact has been made.

## Postings (Greenhouse, re-checked 2026-10-10)

Both jobs are still listed; both have `application_deadline` null.

| Job | Title | Req | Location / offices | Updated | Pay range |
| --- | --- | --- | --- | --- | --- |
| [8842963002](https://boards-api.greenhouse.io/v1/boards/databricks/jobs/8842963002) | Staff Software Engineer, Agent Quality | P-1567 | location `New York City, New York`; offices `San Francisco, California` | 2026-09-24 | $200,000–$265,000 |
| [8379331002](https://boards-api.greenhouse.io/v1/boards/databricks/jobs/8379331002) | Sr. Software Engineer- Backend | P-1591 | location `New York City, New York`; offices `New York` | 2026-09-21 | $165,300–$219,675 |

The Agent Quality location/office split is still present: the location says New York
City but the only office is San Francisco. Open the live posting before applying and
confirm NYC placement with the recruiter; do not treat both roles as NYC-only while
the office field disagrees. Career pages show **Apply now** for both.

## Done

| Work | SHA | Bead |
| --- | --- | --- |
| Databricks CV replacement; Google ends May 2026 | `978ebc0` | before this epic |
| Base, Batman, Google, and LangChain cleanup and PDF rebuilds | `c46ba84` | `sase-1jo.1` |
| Interview-prep pack | `2fe342a` | `sase-1jo.2` |
| Eval pilot | no commit; `eval_pilot = skip` | `sase-1jo.3` |
| v2 report, first draft | `15020bd` | `sase-1jo.4` |
| v2 report brought up to this spec | this landing turn; the host commit lands after close | `sase-1jo` |

Page counts hold at 3/2/2/2 (base, Batman, Google, LangChain); the Databricks CV is
still 2 pages. The rebuild used TinyTeX packages `ebgaramond`, `fontawesome5`,
`listings`, `ulem`, and `tocloft`. Stale Prometheus, Grafana, Gemini CLI, and "33
pipeline" claims are gone. The prep pack does not invent a Google-exit reason.

## Bryan-only next steps

1. **Databricks CV.** An agent must not invent the bullets or the town: the two
`% TODO(bryan)` spots are the contact-line location comment and the Google Ad Manager
bullets in `BryanBugyi_Databricks_CV.tex` (a third comment above Bloomberg is the
optional SRE specific). Confirm May 2026 for both the Google end and the SASE start.
Then, from the CV repo root, run `pdflatex -interaction=nonstopmode
BryanBugyi_Databricks_CV.tex` twice, delete the `.aux`, `.log`, and `.out` files,
and confirm `mutool info` still shows 2 pages.
2. **LinkedIn.** There is no API, so an agent cannot edit it. Follow the checklist in
the original report section [LinkedIn GitHub and site](databricks_nyc_cv_and_role_pitches.md#linkedin-github-and-site), including the referral search.
3. **GitHub.** An agent cannot set pins (no API) or choose the public identity for
you. Live `gh api /users/bbugyi200` on 2026-10-10: bio `{day: "SWE at Google",
night: "Batman of the internet"}`, company null, hireable null, location
`Cranford, NJ`, blog `bryanbugyi.com`. Pins from the original report: `sase-org/sase`,
`sase-org/sase-core`, funky, and cookie. To update the profile after leaving Google:

```bash
gh auth refresh -h github.com -s user
gh api -X PATCH /user \
  -f bio='{day: "building sase (sase.sh)", night: "Batman of the internet"}' \
  -f company='@sase-org' \
  -F hireable=true
```

4. **bryanbugyi.com.** An agent cannot rebuild or deploy the site (missing Hugo theme
checkout, no CI). `config.toml` still has footer slug `bryan-bugyi-a3650763` while
every CV uses `linkedin.com/in/bryan-bugyi`; fix the file to the CV slug. The public
CV URL `https://github.com/bbugyi200/CV/raw/master/BryanBugyi_CV.pdf` already serves
the rebuilt base PDF from `c46ba84` on `origin/master`.
5. **Apply.** Only Bryan can submit. Apply to both roles on databricks.com (not
LinkedIn Easy Apply) on the same day, using the matching pitch in the original
[## Pitches](databricks_nyc_cv_and_role_pitches.md#pitches) section. Recheck each
listing that day. Ask the recruiter the questions in [Application plan and
timeline](databricks_nyc_cv_and_role_pitches.md#application-plan-and-timeline) item
3. When the launch post ships, send that URL as item 2 of the same section describes.
6. **Rehearse** [the interview-prep
pack](databricks_nyc_cv_and_role_pitches_interview_prep.md). Only Bryan can state why
he left Google, so do not write that answer.

## Eval pilot, skip

Optional and must not delay applying. Verbatim decision lives on `sase-1jo.3` note 1
(`eval_pilot = skip`); the carried spec: 8–12 coding tasks from already-merged
history, each frozen at the selected commit's parent, with that commit's tests as the
oracle, in a declarative manifest. Check that tests pass, the change stays in scope,
and required artifacts exist. Keep timeouts and failed runs in the denominator.
Record harness, model, version, and the exact prompt. Repeat a subset and report
variance, pass@k, and per-task outcomes. Log MLflow traces, and use
`mlflow.genai.evaluate` only when it makes the result clearer. Localize one
regression from a trace. Keep `fakey` conformance separate from real-agent
task-success scores. A future implementation belongs in `tools/agent_eval_pilot/`
after reading `tools/AGENTS.md`, adds no runtime dependency (`uv run --with mlflow`
is the optional MLflow path), may run success checks through `sase tool run`, uses a
stub launcher in unit tests and an explicitly labeled `fakey` plumbing smoke, and
sends any real launch through `/sase_run` with `/sase_monitor` for the wait. Its
README gives one real-pilot command and explains the outcome table and pass@k.

## Omnigent (re-checked 2026-10-10)

All 20 open `runner in:title` and all 8 open `worktree in:title` issues in
`omnigent-ai/omnigent` have assignees, so none are named here. Treat contribution as
optional (community Muse harness `R7L208/omnigent-muse`): see item 5 of the original
report's [Application plan and
timeline](databricks_nyc_cv_and_role_pitches.md#application-plan-and-timeline). Do
not open a PR from this report.
