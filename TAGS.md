# Research tags

This is the shared vocabulary for topic tags in this research repository. Keep tag
definitions here, across monthly directories, and keep each report's membership in
its YAML frontmatter. The README links here so the vocabulary is discoverable without
opening a particular report.

## Frontmatter convention

Use a `tags` list of lowercase, hyphen-separated names. For example:

```yaml
---
tags:
  - pypi-release-reliability
---
```

Add `tags` to existing frontmatter without replacing other fields. If a report has no
frontmatter, add a block before its title. Preserve existing tags and avoid duplicates.
Define new tags here before using them; reuse an existing tag when its scope fits.

Tags describe subject matter, not approval, implementation status, or whether a
report's recommendations are still current. A critique or superseded proposal can
still belong to the same topic.

## `pypi-release-reliability`

**Purpose:** Collect research informing SASE's plans to make PyPI releases dependable
and routine: admit trustworthy changes, qualify a specific release candidate, publish
the artifacts that were tested, and ensure users can install and use the result.

**Include** reports or standalone follow-ups with substantive evidence,
recommendations, or explanations about any part of that effort:

- Merge discipline, protected `master`, GitHub merge queues, landing proof, ruleset
  setup, and the effect of the proposed queue on testing an agent's changes.
- CI and release qualification, including the distinction between admission checks
  and release checks, flaky tests, stale evidence, and recovery from a broken base.
- Exact-commit releases, build-once publishing, artifact provenance, release cadence,
  and diagnosing blocked releases.
- Installability, dependency availability and retention, clean-install smoke checks,
  and keeping the documented first-run experience aligned with the shipped version.
- Comparisons and reading lists that directly inform these plans, including the Gas
  Town and Gas City merge-discipline findings and the Google release-engineering
  comparison. A broader report qualifies when a substantial section addresses this
  effort, as the documentation-redesign report does for PyPI installation and release
  alignment.

**Exclude** incidental mentions of PyPI, versions, CI, or releases; general agent
orchestration, documentation, and installation research without a substantive
connection to these release-reliability plans; and image, PDF, or audio assets.

**Filename rule:** Apply the tag to canonical reports and standalone notes. Never tag
a file whose name ends in `__<id>.md`, regardless of the identifier. This excludes
`__cld.md`, `__cdx.md`, `__gem.md`, `__grk.md`, `__mus.md`, `__a.md`, `__b.md`, and
`__final.md`, among others. Use the unsuffixed canonical report when one exists.

**Starting points:**

- [Original merge-queue and exact-SHA release proposal](202610/merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md)
- [Reassessed requirements and four-epic delivery](202610/merge_queue_fence_reassessment_and_epic_split/merge_queue_fence_reassessment_and_epic_split.md)
- [Plain-language explanation](202610/merge_queue_fence_reassessment_explained.md)
- [Google release-engineering comparison](202610/google_release_engineering_vs_sase_release_plan/google_release_engineering_vs_sase_release_plan.md)

The initial backfill on 2026-10-18 covers relevant reports added October 11–18.
The tag itself has no date limit; reuse it for future research on the same effort.
Older research has not been exhaustively backfilled.

To find tagged reports from the repository root:

```sh
rg -l '^  - pypi-release-reliability$' --glob '*.md' --glob '!TAGS.md' .
```
