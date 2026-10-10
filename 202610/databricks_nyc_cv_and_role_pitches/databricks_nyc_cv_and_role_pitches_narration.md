---
narration: 1
title: Databricks NYC Roles, CV, and Application Pitches
source: research:202610/databricks_nyc_cv_and_role_pitches/databricks_nyc_cv_and_role_pitches__final.md
source_blob: 03d2fbf3830cdedeb1102b07b4beb78fa1f82387
date: 2026-10-10
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## The two roles

Bryan wants a credible Databricks application built around Google, Bloomberg, Edgestream, and his independent work on SASE. The report recommends applying to 2 New York City roles on the same day. All 5 researchers chose this pair.

Staff Software Engineer, Agent Quality is the closest subject match. The team is building evaluation infrastructure for Genie Agents. Bryan meets the stated hard requirements, including experience and Python. However, Staff scope remains a risk. Cross-team influence is only partially demonstrated, and a Senior offer is possible.

Senior Software Engineer, Backend, AI Platform is the safer match on level. It asks for backend or infrastructure experience and accepts Python. Its bonus requirement for developer platforms supporting artificial intelligence workflows closely matches SASE.

If Bryan applies to only 1 role, choose Senior Backend. Ask the recruiter about teams near Omnigent, AI Gateway, or Agent Framework. The connection between Omnigent engineers and this organization is inferred, not confirmed by the posting.

Recheck both postings before applying. Meeting posted requirements does not predict an offer.

## The evidence and its limits

The strongest story is infrastructure that makes coding-agent work trustworthy. SASE runs 7 agent command-line tools under a shared provider contract. Each agent works in an isolated workspace, while the host owns commits and pull requests.

Its verification layer records check and test runs durably, with normalized failure signatures. Failures receive new, known, flaky, or unknown verdicts. Calling a failure known requires an independent witness. Triage never masks an exit code.

A deterministic fake provider exercises launch, streaming, retry, and interruption without model calls. Shared backend logic lives in a required Rust core. An authenticated gateway supports mobile clients and dispatch across machines.

For Agent Quality, lead with reproducible run records and regression triage. For AI Platform, lead with provider integration, routing, durable workflows, and the shared backend.

Keep the limits clear. Workspace isolation is not operating-system sandboxing. SASE is a system Bryan operates daily, rather than evidence of broad adoption. Much of its Rust code is agent-written. He should explain the architecture and tradeoffs he can defend.

The main interview gap is task-success evaluation. SASE measures harness reliability, but does not yet measure whether real agents complete their tasks. A small evaluation pilot would strengthen both applications. It should not delay applying.

## What to do before applying

Use the corrected 2-page Databricks curriculum vitae, or CV. It places SASE first as Creator and Lead Engineer, independent and full-time, beginning May 2026. Google now ends in May 2026.

The report flags an earlier publicly pushed CV containing invented Google scale claims and unsupported experience figures. Do not submit that earlier PDF. Confirm that the corrected version has landed.

Before uploading, add 1 or 2 real Google Ad Manager bullets and confirm the location line. Include scale figures only when defensible. Rebuild the corrected PDF. The report also says 2 older CV variants need rebuilding locally because dependencies were missing.

Update LinkedIn and GitHub before submitting. Turn off profile-update broadcasts, end Google in May 2026, and add SASE as self-employed engineering work. Refresh the headline, About section, and recruiter-only Open to Work settings. Keep dates and titles consistent across profiles and the CV.

Do not wait for the rewritten blog post. The July launch essay is already live. Apply this week with the matching role pitch, then share the new post when it ships.

Before interviews, consider 8–12 coding tasks with frozen starting commits and explicit success checks. Keep failed runs and timeouts in the denominator. Separate fake-provider conformance from real-agent success. Show outcomes, variation, and a regression localized from a trace.

Explain leaving Google truthfully. The research does not establish why Bryan left. No applications or messages were sent, and LinkedIn and GitHub were not edited.
