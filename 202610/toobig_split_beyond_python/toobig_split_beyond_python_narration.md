---
narration: 1
title: Running Toobig Split Beyond Python
source: research:202610/toobig_split_beyond_python/toobig_split_beyond_python__final.md
source_blob: 1c34c446c792aedf3e0328f16a8453fe157be99f
date: 2026-10-04
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## The question and short answer

Should the automatic file splitting job expand beyond Python into Rust, JavaScript, and Swift? Yes, selectively, after changing the pipeline.

Keep Python unchanged. Give Swift and JavaScript the same 700 line trigger and a target of at most 500 lines. Their hard limit is 1000, with a warning at 850.

Rust gets a 1000 line trigger and a target of at most 700 lines. Its hard limit is 1500, with a warning at 1250. These are raw line counts, including tests and blank lines.

The reason is measured code, rather than language stereotypes. Across these repositories, lines occupy 31–40 bytes and about 8 tokens. Python spends padding on blank lines. Brace languages spend it on closing braces. Reading a line costs an agent roughly the same.

Rust has a structural exception. Inline tests occupy 33–36% of large files that contain them. Existing manual splits also support larger cohesive Rust modules. Moving substantial inline tests into separate files should be the first remedy.

These limits are starting points, not validated claims about better software. The report has medium confidence in the Rust numbers.

## The deciding reasons

Choosing thresholds is the smallest part of this expansion. Today, the scanner looks only for Python files. Every proposal invokes Python instructions and verification commands specific to SASE. Other repositories need their own scan roots, tool availability, and build checks.

The job has no proposal cap, and its pause applies across projects. At the proposed Rust trigger, SASE core would queue 146 agents. That backlog would block Python splitting too.

Line count is also only a proxy. A cohesive large file can be preferable to smaller files that always change together. Splitting can widen symbol visibility merely to make code compile. Agents must preserve the public interface and report every visibility change.

Swift needs a build host distinction. Of 18 oversized Swift files, 10 can build on Linux and 8 need macOS. Those remaining targets need Mac execution or pull requests checked by the existing macOS continuous integration.

JavaScript needs generated files excluded. Only 2 plugin entry files are generated; the others are hand edited. The largest hand edited entry file has 51,960 lines. Moving it onto the existing fragment build is probably the single highest value step. That migration should start separately.

The benefit of splitting remains uncertain. Roughly 1 commit in 6 or 7 in SASE is now a split. Those counts include manual work. Nobody has measured whether the churn pays off.

## The recommended solution

The report explicitly changes the requirement from language limits to repository profiles. Each profile needs scan rules, exclusions, thresholds, a split instruction, verification, and a build host.

Crossing the trigger should admit an assessment. Allow either splitting or retaining a cohesive file. Retention needs a committed reason and a line ceiling. Failed attempts need backoff so an unsplittable file does not recur every hour.

Start with 1 proposal per run, largest first, and separate pauses for each repository. Route files above about 5 times their target to dedicated splitting epics. Add no new hard gates until each backlog drains.

Enable Bob CLI first, then SASE core, then the Linux buildable Swift targets. Enable Bob plugins after migrating its hand edited entry files. Keep Actstat outside the routine because its Rust code is inactive.

After about six weeks, measure repeat splits, failures, visibility widening, merge conflicts, verification time, and agent token use where possible. Reassess Rust as tests move out. Scale according to measured outcomes, rather than shorter files alone.
