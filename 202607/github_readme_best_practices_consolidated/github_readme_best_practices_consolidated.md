# GitHub README Best Practices — Consolidated Report for the sase README

**Date:** 2026-07-17
**Inputs:** Report A (`__a`, agent `research.g.cdx`: normative/design-guidance review with live GitHub/PyPI rendering
checks), Report B (`__b`, agent `research.g.cld`: canonical-source audit, empirical literature review, eight-peer README
teardown, repo factual audit), plus lead-researcher verification of repo ground truth and two follow-up questions
neither report settled (GitHub's GIF-autoplay controls; the concrete PyPI-rendering fix).

## Executive summary

Both researchers independently reached the same headline: **keep the current README's shape and fix its omissions.**
The 2026-07-17 rewrite (`ac92d6ade`, 353 → 109 lines) put sase squarely in the landing-page archetype used by goose,
OpenHands, and aider — the right shape for a project whose docs site carries ~40 pages. Nothing in either report argues
for adding sections back.

What the README is missing is **facts, not sections**. It never says sase is Alpha, never says it is POSIX-only, never
expands its own acronym, never links the `CONTRIBUTING.md` that already exists, has no CI badge and no support route,
and ships ~7 MB of media that renders broken on PyPI. Every one of these is a small, high-confidence fix that preserves
the current minimalism. The two cheapest and best-evidenced fixes are linking `CONTRIBUTING.md` and stating Alpha
status.

The reports disagreed on three points — section ordering, GIF handling, and the PyPI fix strategy — and on one evidence
attribution. All four are resolved below (§3) with additional verification.

## 1. Ground truth (verified)

**README:** 109 lines, 552 words, 5.2 KB source. Order: `# sase` → Why sase → See it in action (3 GIFs) → Quick start →
Works with your agents → Learn more → Development → Acknowledgements → License. Zero broken links on GitHub: all 7
relative paths resolve and all 11 `sase.sh` URLs return HTTP 200.

**Media payload: ~7.03 MB per README view** (reports A and B measured identically; A quoted 6.7 MiB = same bytes):
`sase_overview.png` 1.35 MB + three GIFs (fan-out 3.84 MB / PRs 1.07 MB / observability 0.77 MB). The GIFs are
1920×1080 sources displayed at `width="830"` — ~2.3× oversized — and loop indefinitely for 20–32 s each.

**Smaller assets already exist and are unused** (lead verification, correcting B slightly):

- `docs/images/blog/` holds 1280×720 GIF variants of **fan-out (1.8 MB vs 3.84 MB)** and **observability (469 KB)**,
  plus a static still `agents_observability_still.png` (178 KB). There is **no blog-size `prs_pipeline` variant** — that
  one would need regenerating from its VHS tape.
- Every README GIF has an `.mp4` twin in `demos/out/` 1.5–2.7× smaller (fan-out 1.4 MB, PRs 693 KB, observability
  496 KB).

**Facts the README omits** (all verified in `pyproject.toml` / `INSTALL.md`):

- `Development Status :: 3 - Alpha` — no maturity statement anywhere in the README.
- `Operating System :: POSIX` — no Windows; Quick start lists only Python 3.12+, uv, and an agent CLI. `INSTALL.md`
  additionally requires `git` and a text editor (`$EDITOR` → nvim → vim).
- The acronym expansion. The README gives the pronunciation ("sassy") but never says *Structured Agentic Software
  Engineering* — the package's own `description` field.
- `CONTRIBUTING.md` (58 lines: setup, `just` workflow, tests, beads) is **referenced by zero files in the repo**.
- CI health: four workflows exist (`ci.yml`, `docs-deploy.yml`, `pr-title.yml`, `publish.yml`); the badge row (Docs,
  PyPI, pyversions, License) has no CI badge.

**PyPI rendering is broken today.** `pyproject.toml` sets `readme = "README.md"`, so this file is the PyPI long
description verbatim. PyPI does not rewrite relative URLs, and the sdist's `only-include = ["src/sase"]` excludes
`demos/` and `docs/`. Report A confirmed the breakage on the live PyPI 0.10.2 page (relative `INSTALL.md` resolves
under `pypi.org/project/sase/INSTALL.md`; the overview image hits PyPI's proxy with no valid source). The redesigned
README adds three more relative GIF paths, so the next release extends the breakage unless fixed first. Note that
`twine check` (already in the publish workflow) validates rendering syntax only — it cannot catch this.

**Community-health siblings absent:** `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR templates. `.github/` contains only
workflows.

## 2. What the evidence supports (merged)

**GitHub's own docs are the only normative source that matters for scope.** A README answers five questions — what the
project does, why it's useful, how to get started, where to get help, who maintains it — and "should only contain
information necessary for developers to get started using and contributing to your project." The current README answers
the first three and fails "where to get help" (no issues/support route) and "who maintains it" (no contributing link).
GitHub's community-health-file taxonomy puts support/security/contribution mechanics in *sibling files the README links
to* — exactly the pattern sase follows for `INSTALL.md` and `LICENSE` and drops for `CONTRIBUTING.md`.

**The empirical literature (Report B) is thin but consistent on two points:**

- **The Why/status gap.** Prana et al. (EMSE 2019, n=393, κ=0.858): only 25.7% of READMEs answer "why should I care?"
  and only 21.4% carry any status/currency signal. sase already wins on Why (`## Why sase`) and sits in the 78.6% that
  never state whether the project is production-ready — despite its own metadata declaring Alpha.
- **License and Contributing are rare, high-signal sections.** Liu et al. (IST 2022, n=11,594): Contributing appears in
  5% of READMEs yet has the second-largest effect size vs. stars (Cliff's δ=0.415); License similar (13%, δ=0.416).
  Independently, the GitHub Open Source Survey 2017 (n=5,500) rates license and contribution guidance the top documents
  in deciding whether to use (64%) or contribute to (67%) a project.

**Causality caveat (keep this honest):** Gaughan et al. (CHASE 2025) is the only study testing temporal direction and
found documentation *follows* contribution activity — "no evidence to support such causality." The defensible claim is
narrower: Contributing/License/status sections co-occur with popular projects and are rare enough to be cheap
differentiators. Also from Gaughan: median README reading time is ~15 seconds; sase's 552 words is comfortably in
one-sitting territory.

**Peer teardown (8 developer tools, read from local checkouts):** universal patterns sase already follows — name +
one-line tagline in the first 15 lines, badges after title, a visual in the first ~50 lines, minimal inline install
that links out, docs site owning reference material. The two universal patterns sase misses: a **CI badge** (consistent
across all 8 peers) and any **status statement**. Patterns worth stealing selectively: ripgrep's "Why shouldn't I use
ripgrep?" anti-sell, uv's identity-FAQ ("Is uv ready for production?", "What platforms does uv support?"), lazygit's
keypress-plus-GIF feature triples (best deployed on the `sase.sh/ace/` docs page, not the README), and ruff's
HTML-comment section markers that let the docs site embed README slices to prevent drift.

**Evidence-hygiene corrections (Report B, verified against sources):** Diátaxis says nothing about READMEs — it is a
docs-corpus framework, and the "README as front door per Diátaxis" framing is unattributable (Report A leaned on this;
drop it — GitHub's scope sentence carries the same recommendation with a real citation). Steinmacher et al. do *not*
find documentation the top newcomer barrier (socialization barriers are). No eye-tracking study of READMEs exists —
"above the fold" arguments are first-principles only.

## 3. Where the reports disagreed — resolutions

**Ordering: does Quick start move above the demo gallery?** Report A said yes (installation is pushed several viewports
down); Report B said no (Art of README's "cognitive funneling": order by disqualification speed, and demos are how a
tool-seeker decides — sase is already in funnel order). **Resolution: keep the current order; fix the demo section's
mass instead.** A's real complaint is that three full-width GIFs make Quick start ~3–4 viewports deep. Cutting the
gallery to one animated hero plus two compact linked stills brings Quick start within ~1.5–2 viewports, which resolves
A's concern without giving up B's (better-argued) ordering. GitHub's auto-generated heading TOC already gives
high-intent visitors a one-click jump to Quick start.

**GIFs: remove or downsize?** Report A said replace all three with static thumbnails linked to MP4s, citing WCAG 2.2.2
(Pause, Stop, Hide) — animations over 5 s with no pause control. Report B said just point at the existing smaller
variants. **Resolution: A's severity claim is overstated for GitHub but correct for PyPI; do a hybrid.** Follow-up
research: GitHub has shipped a "prevent animated images from playing automatically" accessibility setting since May
2022 and respects system-level `prefers-reduced-motion` by default, with play/pause controls when autoplay is off — so
GitHub-side WCAG exposure is mitigated at the platform level. PyPI has no such control, which matters because fixing
the PyPI rendering (below) would make these GIFs *start* autoplaying there. The hybrid: keep **one** demo animated
(using the smaller 1280×720 variant), render the other two as static stills linked to their MP4s with duration labels,
and have the PyPI description reference stills only. This also cuts the payload from ~7 MB to roughly 2.5 MB.

**PyPI fix: generated description or absolute URLs in the README?** Report A recommended generating a PyPI-specific
long description with rewritten absolute URLs (preserves GitHub-native relative links, which survive branches, forks,
and local clones); Report B recommended hard-coding `raw.githubusercontent.com` URLs as a one-time edit. **Resolution:
A's strategy, with a concrete tool B's simplicity argument didn't account for: `hatch-fancy-pypi-readme`.** sase
already builds with hatchling; this plugin is a metadata hook whose documented use case is regex substitutions
"replacing relative links with absolute ones" at build time. One `pyproject.toml` block, no second README to maintain,
no loss of relative-link behavior on GitHub. Verify both surfaces before the next release (`twine check` won't catch
link destinations; eyeball the rendered description or use `python -m build` + a PyPI staging preview).

**Diátaxis attribution:** resolved in B's favor (see §2). The consolidated recommendation list below cites GitHub's
scope guidance instead.

## 4. Recommended changes to `README.md`

Ordered by value-to-effort. Items 1–8 are high-confidence and cheap; 9–13 are worthwhile judgment calls; the final
group is explicitly not recommended.

1. **Link `CONTRIBUTING.md`.** One line in `## Development` (or a two-line `## Contributing` section before License).
   Cheapest fix with the strongest evidence behind it: rare (5% of READMEs), large effect size (δ=0.415), a top
   decision factor in the GitHub survey, a GitHub community-profile checklist item, and currently a complete orphan.
2. **State Alpha status near the top.** One honest sentence (uv's FAQ precedent: "Is sase ready for production?" also
   works). `pyproject.toml` already declares it; someone running `uv tool install sase` deserves to know. This is a
   credibility purchase, not a liability, and it fixes the single most common gap in the empirical corpus.
3. **Expand the acronym in text.** The H1 or lede should say *Structured Agentic Software Engineering* — currently the
   expansion exists only in the diagram image and package metadata. The project's name is its thesis; spend the four
   words. (Also helps search and image-free readers.)
4. **Complete the Quick start contract.** Add supported platforms (POSIX — Linux and macOS; no Windows) and the missing
   prerequisites (`git`, a text editor) alongside Python 3.12+/uv/provider; explain `#git:home` in one sentence; state
   what success looks like after `sase doctor` → `sase run` → `sase ace`.
5. **Fix PyPI rendering before the next release** via `hatch-fancy-pypi-readme` substitutions (see §3). All four images
   and the `INSTALL.md`/`LICENSE`/acknowledgements links currently render broken on the live PyPI page.
6. **Cut the media payload (~7 MB → ~2.5 MB) and tame the motion.** Keep one animated demo using the 1280×720 blog
   variant (fan-out: 1.8 MB); render the other two as static stills linked to their `.mp4` twins with duration labels
   (the observability still already exists; generate a PRs still/variant from its VHS tape). Nothing else needs
   regenerating.
7. **Add a CI status badge** for `ci.yml`. It is the one badge present in all eight peer READMEs and the only one that
   answers "does this currently work?" Keep the row at five badges — Art of README's badge skepticism is right beyond
   that.
8. **Add a support route.** Link GitHub Issues for bugs and questions (a "Support" line in `## Learn more` or the new
   Contributing section). This is one of GitHub's five README questions and currently unanswered.
9. **Add a text equivalent for the overview diagram.** A short caption or adjacent sentence covering what the diagram
   encodes (one prompt fans out to isolated workspaces; ACE supervises; AXE schedules; durable state tracks
   ChangeSpecs/beads/artifacts; output is reviewed PRs). W3C complex-image guidance; also future-proofs against image
   hosting rot.
10. **State development prerequisites.** The `## Development` block runs `just install` without saying `just` is
    required; one clause fixes a guaranteed first-command failure for fresh contributors.
11. **Surface the blog and the PDF handbook in `## Learn more`.** CI builds and smoke-tests `sase-handbook.pdf` on
    every deploy and the docs hero features it; the README links neither it nor the 10-post blog. Two lines.
12. **Consider a short "Why not sase?" / limits note.** ripgrep's anti-sell pattern plus CNCF's Out-of-Scope
    prescription: Alpha, POSIX-only, assumes you already pay for an agent CLI, opinionated about git workspaces. Pairs
    naturally with item 2 and disqualifies the wrong users fast.
13. **Optionally compact the provider table.** Five identical "Supported" rows repeat the lede's provider list; either
    compress to a linked sentence or keep the table only if it gains a real dimension (support tier, required plugin).
    Low stakes either way.

**Adjacent, outside the README file itself:** add `SECURITY.md` (a tool that executes agent-generated code should have
a reporting route; the README-side pointer costs one line), and check the repo's About description, topics, and social
preview image — the sidebar and link-unfurl surface is part of the same first impression and neither report covered it.
The lazygit-style keypress+GIF feature triples belong on `sase.sh/ace/`, not here. If README/docs drift becomes a
maintenance problem, ruff's section-marker embedding is the structural fix — not worth adopting preemptively.

**Not recommended** (both reports agree): a manual table of contents (GitHub auto-generates one; 2% prevalence in
11,594 READMEs); reordering sections beyond the current funnel; manufactured social proof at Alpha (revisit at 1.0 —
the dependents-graph link is the cheap honest version); restoring the pre-rewrite "Core pieces"/"Common
commands"/"Operational model" content. The README's job is to route to `sase.sh`, and it now does.

## Sources

Normative: GitHub [About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)
and [community health files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file);
[Art of README](https://github.com/hackergrrl/art-of-readme); [standard-readme spec](https://github.com/RichardLitt/standard-readme/blob/main/spec.md)
(library-scoped — borrow selectively); [makeareadme.com](https://www.makeareadme.com/);
[opensource.guide](https://opensource.guide/starting-a-project/); [JOSS checklist](https://joss.readthedocs.io/en/latest/review_checklist.html);
[CNCF project template](https://github.com/cncf/project-template/blob/main/README-template.md);
[WCAG 2.2.2 Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html);
[W3C complex images](https://www.w3.org/WAI/tutorials/images/complex/);
[PyPA PyPI-friendly README](https://packaging.python.org/en/latest/guides/making-a-pypi-friendly-readme/);
[GitHub workflow status badges](https://docs.github.com/en/actions/how-tos/monitor-workflows/add-a-status-badge).

Empirical: Prana et al. 2019 ([arXiv:1802.06997](https://arxiv.org/abs/1802.06997)); Liu, Noei & Lyons 2022
([PDF](https://enoei.github.io/papers/liu2022readme.pdf)); Gaughan et al. 2025 ([arXiv:2502.18440](https://arxiv.org/abs/2502.18440));
[GitHub Open Source Survey 2017](https://opensourcesurvey.org/2017/) (industry self-report); Steinmacher et al. 2014/2015
([PDF](https://www.ime.usp.br/~gerosa/papers/Steinmacher2014_Chapter_BarriersFacedByNewcomersToOpen.pdf)).

Lead follow-ups: [GitHub changelog — option to prevent animated images from playing automatically](https://github.blog/changelog/2022-05-18-option-to-prevent-animated-images-from-playing-automatically/)
(May 2022); [hatch-fancy-pypi-readme](https://github.com/hynek/hatch-fancy-pypi-readme) (hatchling metadata hook;
documented substitution use case is rewriting relative links to absolute for PyPI).

Peer READMEs (local checkouts via `sase repo open`): uv, ruff, aider, lazygit, bubbletea, ripgrep, OpenHands, goose.
Full per-source detail, the complete peer teardown, and the agent-context-file literature review live in the companion
reports `__a` (cdx) and `__b` (cld) in this directory.
