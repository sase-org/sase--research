# Top-level GitHub README best practices and an assessment of SASE

**Research date:** 2026-07-17  
**Project snapshot:** local `master` at `d98b28462`; `README.md` last changed by `ac92d6ade`  
**Artifact reviewed:** the repository-root `README.md` (109 lines, 552 words, 5,214 bytes)

## Executive summary

The redesigned SASE README is already substantially better than the typical repository README. It is short, visually
polished, and structured like a landing page: it says what SASE is, explains the value, shows the product, offers a
copyable quick start, routes readers to deeper documentation, and includes development and license information. Its
5.2-KiB source is far below GitHub's 500-KiB README rendering limit, and it does not duplicate the full manual.

The main opportunities are not to add more product detail. They are to improve the reader's path to a first successful
run, remove accessibility and performance problems caused by three long auto-playing GIFs, make the README work on
PyPI as well as GitHub, and make project trust/support information explicit. The highest-impact changes are:

1. put the quick start before the large demo gallery;
2. replace the three indefinitely looping GIFs with static, linked thumbnails or user-controlled video;
3. solve the broken-relative-link problem created by publishing the same README verbatim on PyPI;
4. state platform and alpha-status constraints near installation; and
5. add clear support and contribution routes plus a CI status badge.

## Scope and method

This analysis combines:

- direct inspection of the current README, packaging metadata, installation guide, contribution guide, documentation
  navigation, GitHub Actions workflows, and the README's local media assets;
- rendering-context checks against the live GitHub repository and the current PyPI 0.10.2 project page; and
- guidance from GitHub, the Python Packaging Authority (PyPA), W3C Web Accessibility Initiative, the Google developer
  documentation style guide, Diátaxis, and The Good Docs Project.

The recommendations are tailored to SASE as a public, installable Python CLI/TUI with a separate documentation site.
They are not a generic template checklist. For example, a top-level table of contents is unnecessary here because
GitHub already generates an outline from headings and the README is only 109 lines long.

## What a top-level README needs to accomplish

### Answer the visitor's first questions quickly

GitHub describes five questions a README typically answers: what the project does, why it is useful, how to get
started, where to get help, and who maintains or contributes to it. GitHub also recommends limiting the README to what
developers need to start using and contributing to the project, leaving longer documentation elsewhere. See
[About the repository README file](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes).

For a developer tool, those questions translate into a practical sequence:

1. **Recognition:** Is this for me, and what problem does it solve?
2. **Qualification:** Does it support my platform, runtime, and provider?
3. **Trust:** Is it active, tested, licensed, and honest about maturity?
4. **Activation:** What is the shortest safe path to a meaningful result?
5. **Recovery:** Where do I go if setup fails or I need more detail?
6. **Participation:** How do I report a problem or contribute?

A strong README supports this path without trying to become the tutorial, how-to collection, reference manual, and
architectural explanation all at once. Diátaxis distinguishes those four documentation needs; SASE already has a
substantial docs site for them. The README should act as a concise front door and router. See
[Diátaxis](https://diataxis.fr/) and The Good Docs Project's description of a README as the information users need to
[understand a project, engage with it, and get started](https://www.thegooddocsproject.dev/).

### Optimize for a first successful action

Installation snippets should be complete enough to copy, explicit about prerequisites, and followed by the outcome the
reader should expect. Google's procedure guidance recommends giving context before a procedure and explaining results
or output when that helps the reader proceed. See
[Procedures](https://developers.google.com/style/procedures) and
[Code samples](https://developers.google.com/style/code-samples).

For SASE, “success” is not merely that `uv tool install sase` exits with status zero. It is that `sase doctor` finds an
authenticated provider, the first safe agent run is launched, and the user can see the durable run in ACE. The current
quick start contains these commands but does not tell the reader what success looks like or explain `#git:home`.

### Provide proof without blocking the task

Screenshots and short demos can prove that a TUI exists and make an unfamiliar workflow concrete. They should support,
not delay, the primary action. A user currently encounters the architecture diagram and then three full-width animated
demos before reaching “Quick start.” On a normal GitHub page this pushes installation several viewports down.

The best compromise for SASE is one strong static visual near the top, followed later by compact, click-to-play demo
links. The README remains visually distinctive, while the quickest path to trying the tool stays near the beginning.

### Make trust and project expectations visible

Trust signals should be few and meaningful. SASE's Docs, PyPI version, supported-Python, and license badges are useful;
the missing signal is whether the current default branch passes its actual checks. GitHub explicitly supports README
workflow badges for this purpose. See
[Adding a workflow status badge](https://docs.github.com/en/actions/how-tos/monitor-workflows/add-a-status-badge).

Badges should not substitute for prose that affects adoption. The package metadata classifies SASE as “Alpha,” but the
README does not disclose that. A short status sentence near the opening or requirements would set expectations about
rapidly changing behavior more clearly than another badge.

Likewise, GitHub treats README, license, contribution guidelines, code of conduct, issue templates, and security policy
as complementary community-health material. The README need not reproduce those documents, but it should route readers
to the relevant ones. See
[About community profiles for public repositories](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories).

### Design for scanning and accessibility

Descriptive headings, short paragraphs, parallel lists, meaningful links, and text equivalents for images improve both
scanning and assistive-technology use. Google's accessibility guidance specifically recommends meaningful link text,
equivalent text for information conveyed by images, avoiding images of terminal text when possible, and checking that
a document still communicates without images or animation. See
[Write accessible documentation](https://developers.google.com/style/accessibility) and
[Cross-references and linking](https://developers.google.com/style/cross-references).

Motion is the current README's clearest accessibility problem. The three GIFs:

| Asset                | Duration |            Size | Loop behavior |
| -------------------- | -------: | --------------: | ------------- |
| Multi-model fan-out  |  31.56 s | 3,839,067 bytes | Indefinite    |
| Agents observability |  20.12 s |   774,035 bytes | Indefinite    |
| PR pipeline          |  26.32 s | 1,066,056 bytes | Indefinite    |

Together, the GIFs are about 5.4 MiB. Including the 1.3-MiB overview PNG, the README asks the browser to load about
6.7 MiB of visual assets. More importantly, each animation starts automatically, lasts more than five seconds, and has
no README-level pause control. WCAG 2.2's Pause, Stop, Hide guidance calls for a way to pause, stop, or hide this kind of
moving content; it lists animations that stop within five seconds or provide controls as sufficient approaches. See
[Understanding Success Criterion 2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html).

The architecture image is useful and has alt text, but it is a complex diagram. W3C recommends both a short
identification and an equivalent longer text description for complex images. The surrounding README explains much of
the concept, but it does not fully describe the diagram's ACE/AXE, workspace, durable-state, and output relationships.
See [Complex Images](https://www.w3.org/WAI/tutorials/images/complex/).

### Validate every rendering context

Relative repository links are a GitHub best practice because they work in branches and local clones. GitHub rewrites
them based on the current branch. However, this project also declares `readme = "README.md"` in `pyproject.toml`, so the
same Markdown becomes the long description on PyPI. PyPI does not know that `INSTALL.md`, `LICENSE`,
`docs/images/sase_overview.png`, or `demos/out/*.gif` belong to the GitHub repository.

This is already observable on the published PyPI 0.10.2 page: its relative `INSTALL.md` link resolves under
`https://pypi.org/project/sase/INSTALL.md`, and the relative overview image is sent to PyPI's image proxy without a
valid absolute source URL. The redesigned local README adds three more relative GIFs, so a future release would extend
the same breakage unless this is fixed first. The live evidence is the
[SASE project description on PyPI](https://pypi.org/project/sase/).

PyPA recommends using supported Markdown and validating built distributions with `twine check`; SASE already does the
latter in its publish workflow. `twine check` validates rendering syntax, not whether destination URLs work, so it does
not catch this class of broken link. See
[Making a PyPI-friendly README](https://packaging.python.org/en/latest/guides/making-a-pypi-friendly-readme/).

There are three viable strategies:

1. **Recommended:** keep `README.md` GitHub-native and produce a PyPI-specific long description from the same source,
   rewriting relative repository links and media to absolute URLs during a checked build step. This preserves branch
   previews and clone usability without hand-maintaining two divergent narratives.
2. Use a separately maintained `PYPI_README.md`. This is simple, but duplicated prose can drift unless CI compares or
   generates it.
3. Convert every relative README link and image to an absolute `github.com`/`raw.githubusercontent.com` URL. This is the
   smallest code change but weakens branch previews, forks, and offline-clone behavior, contrary to GitHub's relative
   link guidance.

Whichever strategy is chosen, preview both GitHub and PyPI renderings and run a link checker against the README as part
of release validation.

## Assessment of the current SASE README

### What is working well

| Area                  | Assessment                                                                                                                             |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Positioning           | The tagline is concrete and outcome-oriented: one developer, a team of agents, and work that is tracked, reviewable, and repeatable.   |
| Concision             | At 552 words, the README is a landing page rather than a second manual. This aligns with GitHub's guidance.                            |
| Value explanation     | “Why sase” names five user-relevant capabilities and closes with a crisp boundary: SASE coordinates agents rather than replacing them. |
| Visual identity       | The overview diagram is polished, explains the system at a glance, and has meaningful alt text.                                        |
| Installation path     | The quick start gives a preferred `uv tool` install, a readiness check, a safe first run, and the main TUI command.                    |
| Documentation routing | “Learn more” links to a curated set of task and concept pages instead of dumping the entire documentation navigation.                  |
| Contributor boundary  | The README gives only the basic source setup and correctly delegates the complete workflow to the development guide.                   |
| Metadata              | Version, Python support, docs, and license are visible at the top; license and acknowledgements have dedicated endings.                |
| Heading structure     | One H1 followed by clear H2 sections; no skipped levels and no need for a manually maintained table of contents.                       |

These strengths should be preserved. In particular, do not restore the former long “Core pieces,” “Common commands,”
and “Operational model” sections to the README. The recent reduction in scope is consistent with best practice.

### Gaps and opportunities

| Priority | Gap                                           | Project-specific evidence                                                                                                                                       | Consequence                                                                                |
| -------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| P0       | GitHub/PyPI portability                       | `README.md` is the package description, but it contains seven relative links or media paths. The published PyPI page already misresolves relative destinations. | Broken images and links on a primary acquisition surface.                                  |
| P0       | Uncontrolled motion                           | Three GIFs autoplay indefinitely for 20–32 seconds and total about 5.4 MiB.                                                                                     | Accessibility failure, distraction, bandwidth cost, and slow path to installation.         |
| P1       | Quick start appears too late                  | The reader passes one architecture diagram and three full-width GIFs before installation.                                                                       | High-intent visitors do more scrolling than necessary to try the tool.                     |
| P1       | Platform scope is hidden                      | README lists Python, `uv`, and a provider, while `INSTALL.md` says SASE targets POSIX/Linux/macOS and documents wheel architectures.                            | Windows and unsupported-platform users discover constraints after attempting installation. |
| P1       | Maturity is hidden                            | `pyproject.toml` declares Development Status 3 — Alpha; README does not.                                                                                        | Readers may infer greater stability than the project promises.                             |
| P1       | No explicit help route                        | The README links to docs but not the issue tracker or a support/reporting instruction.                                                                          | It does not answer GitHub's “where users can get help” question.                           |
| P1       | Contribution route is implicit                | “Development” links to the docs guide but not the repository's `CONTRIBUTING.md`; no maintainer/contributor pointer is present.                                 | Prospective contributors have no obvious policy entrance.                                  |
| P1       | CI health is absent                           | Badge row shows docs, release version, Python versions, and license; `.github/workflows/ci.yml` is the canonical test signal.                                   | The README shows availability but not current build health.                                |
| P2       | First success is not explained                | Commands are copyable, but there is no expected-result sentence and `#git:home` is unexplained.                                                                 | New users cannot quickly distinguish success from an incomplete setup.                     |
| P2       | Development prerequisite is omitted           | The source setup runs `just install`, but the section does not say that `just` is required.                                                                     | A fresh contributor can hit `command not found` on the first workflow command.             |
| P2       | Complex image lacks an equivalent description | The overview's alt text summarizes the result but not the relationships encoded in the diagram.                                                                 | Some readers cannot access the same architectural information.                             |
| P2       | Supported-agent table is redundant            | All five rows say “Supported,” and the same five providers appear in the opening paragraph and prerequisites.                                                   | Repetition consumes space without conveying compatibility differences.                     |
| P2       | Name expansion is visual/metadata-dependent   | The visible H1 is only “sase”; the full phrase appears in the diagram and package metadata rather than the first text heading or lede.                          | Slightly weaker first-contact clarity, searchability, and image-free comprehension.        |

## Suggested target structure

The goal is a better sequence, not a longer README:

1. **Hero:** `sase — Structured Agentic Software Engineering`, outcome-focused tagline, compact badge row including CI,
   and a one-sentence alpha status note.
2. **Two-sentence lede:** identify the audience and explain that SASE coordinates existing coding-agent CLIs rather
   than supplying a model itself.
3. **One static overview image:** retain the current diagram, add a short adjacent text description of the flow.
4. **Why SASE:** retain the current concise capability list.
5. **Quick start:** state POSIX/Linux/macOS, Python, `uv`, and provider requirements; show install, doctor, first run,
   and ACE; state the expected result and define `#git:home`; link to troubleshooting/full installation.
6. **See it in action:** use one static thumbnail or a compact set of three linked thumbnails with duration labels and
   click-to-play MP4 destinations. Do not embed indefinitely looping GIFs.
7. **Supported providers:** keep a compact linked list, or retain a matrix only if it communicates real differences
   such as support tier or required plugin.
8. **Documentation, support, and contributing:** route to the guided docs, issue tracker, `CONTRIBUTING.md`, and
   security-reporting instructions once a security policy exists.
9. **Development, acknowledgements, license:** keep these brief sections, adding the missing `just` prerequisite.

## Changes I recommend making to `README.md`

1. **Fix cross-surface rendering before the next release.** Keep relative links for the GitHub source, but stop
   publishing them verbatim to PyPI: generate a PyPI long description with absolute repository/media URLs, or maintain
   a checked PyPI-specific README. Verify that `INSTALL.md`, `LICENSE`, acknowledgements, the overview image, and every
   demo work on both surfaces.
2. **Remove the three embedded looping GIFs.** Replace them with static screenshots linked to the existing MP4 files
   (or another user-controlled player), label each link with what it demonstrates and its duration, and keep at most one
   visual teaser above the fold.
3. **Move “Quick start” ahead of “See it in action.”** Keep “Why sase” first if desired, but let a ready-to-try visitor
   reach installation without scrolling past the demo gallery.
4. **Make the quick-start contract complete.** Add supported platforms (POSIX; Linux and macOS), keep Python 3.12+,
   `uv`, and one authenticated provider, explain `#git:home` in one sentence, and say what a successful `sase doctor`,
   first run, and `sase ace` sequence produces.
5. **Disclose project maturity near the top.** State that SASE is alpha and that behavior/configuration may evolve;
   link to the changelog or releases for upgrade-relevant changes.
6. **Add the CI workflow badge.** Link it to `.github/workflows/ci.yml`, keep the badge row to roughly five meaningful
   signals, and avoid adding decorative or redundant badges.
7. **Add an explicit “Support and contributing” section.** Link to GitHub Issues for bugs/help, link directly to
   `CONTRIBUTING.md`, identify the maintainer/community at a useful level, and point security reports to a security
   policy once one exists.
8. **Expand the project name in text.** Change the H1 or first lede to include “Structured Agentic Software
   Engineering” so the name is clear without loading the diagram or relying on repository metadata.
9. **Add a text equivalent for the overview diagram.** A short caption or nearby paragraph should explain the flow:
   one prompt fans out to isolated provider workspaces; ACE supervises interactive runs; AXE schedules work; durable
   state records ChangeSpecs, beads, commits, and artifacts; the result is reviewed PRs and tracked runs.
10. **Fix contributor setup prerequisites.** State that development requires both `uv` and `just` before the existing
    source-install block, while continuing to delegate detailed checks and architecture to the development guide.
11. **Compact or enrich the provider table.** Replace five identical “Supported” rows with a compact linked sentence,
    unless the table is expanded to communicate meaningful compatibility differences.
12. **Keep the README concise and omit a manual table of contents.** Preserve the current separation between the
    landing page and `sase.sh`; let GitHub's generated outline handle navigation and resist reintroducing reference or
    operational detail that belongs in the docs.
