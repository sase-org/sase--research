---
create_time: 2026-09-30
updated_time: 2026-09-30
status: draft
tags: [research_swarm, xprompts, sase-research-artifacts, highlights, linker]
---

# Adding a Linker Agent to the Research Swarm

**Question:** what is the best way to add an opt-in `linker` agent to `#research_swarm`?
The request also removes the `critique` agent and adds an `image_model` input. Is the
plan sound, and what would I change?

**Scope and method:** I worked against three commits: `sase-research-artifacts` at
`c9f41f3` (it owns `#research_swarm`, the `research-highlights` file hook, and their
tests), `sase` at `6d79158cbf` (file-hook matching, `wait.artifacts`, `#fork`, `%if`
gating), and `bob-cli` at `5b1f991` (the `bob highlights create` command the hook runs).

- I read the code and ran sase's real file-hook glob matcher against the hook's actual
  specs.
- I compared how pandoc and GitHub build heading anchors, using the pandoc 3.1.11 that
  is installed on athena.
- I sampled the research sidecar's existing reports.
- I built a prototype of the recommended template and ran it through sase's real xprompt
  expander, launch planner, and runtime `wait.artifacts` renderer. The prototype text is
  in [Recommended solution](#recommended-solution).

Headings below follow the rules this report recommends for the linker. They are plain
text and unnumbered, so every in-document link works both on GitHub and in the PDF.

## Bottom line

The plan is a good idea and its core design is right. I would ship it with the
adjustments below.

**Why it is right.** The Highlights PDF is generated once, when a hook-eligible Markdown
file is first committed (an `ADD`). Today that file is the lead's `<name>.md`. The
infographic is committed later, so it can never appear in that PDF. The linker fixes
this with the only ordering that works: first the lead writes a draft the hook ignores,
then the image agent runs, and only then is the canonical `<name>.md` written.

The evidence also supports the user's formatting instincts:

- The PDF renderer runs pandoc with `--number-sections` and `--toc`. That is why headings
  must be unnumbered and why a Markdown table of contents would be redundant.
- 68 of the 88 swarm directories created in 2026-09 have a consolidated report whose
  headings carry manual numbers such as `### 1.1` or `Part 2`. In the PDF those numbers
  are doubled.
- 231 reports have a sibling infographic, but only 5 of them embed it.

**Adjustments I recommend.** Each is explained in
[Adjusted requirements](#adjusted-requirements).

- **Do not add `final` to the hook's suffix tuple.** The `__final.md` draft is already
  excluded by the existing path glob. The tuple in `provider.py` feeds the hook's
  *agent-name* veto, so adding `final` would stop the Highlights PDF for every default
  swarm that runs without the linker. Add tests and documentation instead
  ([details](#hook-suffix-list)).
- **The linker waits on both the lead and the image agent.** `wait.artifacts` is not
  transitive, so waiting only on the image agent would hide the lead's registered report
  from the linker ([details](#wait-graph-and-failure-modes)).
- **The lead registers its `__final.md` report whenever the linker runs.** This reuses
  the registration step the critique handoff uses today.
- **Name the infographic `<name>_infographic.png`, not `<name>__final_infographic.png`.**
  Teach `#research/image` to drop a trailing `__<suffix>` from the source stem.
- **Add a `linker_model` input, defaulting to `@large`.** This matches every other
  role's per-role model input. `image_model` should default to `@image` so today's
  behavior is unchanged.
- **Define what "valid link" means.** A valid link works both on GitHub and in the PDF.
  Only mechanical repairs are allowed; no hunting for replacement sources, which would be
  new research. Repository file links are verified through `/sase_repo`, not by fetching
  github.com ([details](#link-validation-policy)).
- **Constrain the headings that links point to.** Plain-text headings are the only way
  to make GitHub's anchors and pandoc's anchors agree
  ([details](#anchor-links-across-github-and-the-pdf)).
- **Adjacent fix outside the plugin.** Add `--shift-heading-level-by=-1` to `bob-cli`'s
  pandoc call. Without it, even a perfectly unnumbered report renders in the PDF as
  "1 Title / 1.1 … / 1.2 …" ([details](#pdf-heading-levels)).

**Removing the critique agent is sound.** Two trial `__critique.md` files exist. Its
output is excluded from the Highlights PDF, so its findings never reached the reading
queue anyway. Removing it needs no migration.

## How the pipeline works today

### Swarm graph

`#research_swarm` authors eight segments in
`src/sase_research_artifacts/xprompts/research_swarm.md`:

- Five per-provider researchers (`cdx`, `cld`, `grk`, `mus`, `gem`), each gated by
  `%if(should_run=...)`.
- The lead, `research.<N>.final`, which waits on every surviving researcher.
- The optional image agent, which waits on and forks from the lead and runs
  `#research/image`.
- The optional critique agent.

The lead moves researcher drafts to `<name>/<name>__<suffix>.md` and writes
`<name>/<name>.md`. It registers its report with `sase artifact create` **only when
`critique=true`**, because the critic is the only downstream consumer that reads it
through `wait.artifacts` (lines 287–298).

### Highlights file hook

`RESEARCH_HIGHLIGHTS_HOOK_SPEC` (`provider.py:94–121`) fires only when all of these
hold:

- **Sidecar and event:** the `research` sidecar, producers `commit`, `sdd`, or
  `finalizer`, and op `ADD` only.
- **Path globs:** `20*/**/*.md`, minus `!20*/*__*.md` (drafts at the month root), minus
  `!20*/*/*__*.md` (drafts one directory down), minus the companion-page globs.
- **Agent-name veto:** `!research.*.{cdx,cld,grk,mus,gem}`, generated from
  `_SWARM_RESEARCHER_SUFFIXES`.

sase matches with `wcmatch`, where `*` does not cross `/` and any matching `!` pattern
excludes the file (`src/sase/config/file_hooks.py:529–571`). The agent name matched is
the agent whose turn committed the file (`src/sase/agent/identity.py:109–128`). The
command receives one argument, the file's absolute path
(`src/sase/file_hooks/runner.py:157–177`). On athena that command is
`bob highlights create --include-id`.

### PDF renderer

`bob highlights create` (`bob-cli/src/native/highlights_ref/create.rs:673–705`) runs:

```text
pandoc <file.md> --standalone --toc --toc-depth=3 --number-sections
  --pdf-engine=xelatex --resource-path=<dir of file.md> --metadata title=<title> ...
```

Three consequences matter for this design:

- **The input is pandoc Markdown, not GFM.** No `--from` is passed. Heading anchors
  therefore follow pandoc's `auto_identifiers` rules, not GitHub's
  ([see below](#anchor-links-across-github-and-the-pdf)).
- **Relative images resolve** from the report's directory, so
  `![...](<name>_infographic.png)` renders in the PDF.
- **Pandoc numbers sections and builds the table of contents itself.** A manual
  `### 1.1 The mechanism` under an H1 title renders as "1.2.1 1.1 The mechanism".

The marker id comes from the Markdown filename stem. Because the linker's output is
still `<name>.md`, Bob's ids and reference notes stay exactly as they are today.

## Assessment of each requirement

| Requirement | Verdict | Notes |
| --- | --- | --- |
| `linker` input, default `false` | Agree | Start opt-in; consider flipping the default after a few runs ([rollout](#rollout)). |
| Linker runs when `linker or image` | Agree | Embedding is the point of the image, and an embedded image needs a post-image writer. Document that `image=true` implies the linker. |
| Lead writes `<name>__final.md` when the linker runs | Agree | The suffix matches the convention "draft suffix = producing agent's short id" (`research.<N>.final`). Its drawback is that the file named "final" is not the final file; `__lead` would be clearer but breaks the convention. |
| Add the suffix to the hook's ignore list | **Adjust** | Already excluded by path glob; adding it to the tuple would veto the lead's PDF in default runs ([details](#hook-suffix-list)). |
| Linker creates the file the hook uses | Agree | Keeps `<name>.md` and Bob's marker id unchanged. |
| Linker preserves meaning, does no research | Agree | Add a survival inventory and a URL-set check so meaning drift is caught, not just forbidden. |
| Organized, unnumbered sections | Agree | Directly justified by `--number-sections`. Also needs the [bob-cli fix](#pdf-heading-levels) to render cleanly. |
| Embed the image when `image=true` | Agree | Fix the image filename, and let the linker find the image from both the naming convention and `wait.artifacts`. |
| All links valid | Agree, **with a defined policy** | "Valid" must mean valid on GitHub *and* in the PDF, with mechanical repairs only ([policy](#link-validation-policy)). |
| Add in-document links, no TOC | Agree, **with heading rules** | The PDF and GitHub already provide outlines. Anchors only work in both places if headings are plain text. |
| Remove the critique agent | Agree | Unused, costly (`@xlarge`), and its output never reached the PDF. No migration needed. |
| `image_model` input | Agree | Default `@image` so behavior is unchanged. |

## Adjusted requirements

### Hook suffix list

The hook already excludes `__final.md` files. I ran sase's real matcher against the
current spec:

| Path | Hook fires? | Ref inventory keeps it? |
| --- | --- | --- |
| `202609/topic/topic.md` | yes | yes |
| `202609/topic/topic__final.md` | **no** (`!20*/*/*__*.md`) | yes |
| `202609/topic__final.md` | **no** (`!20*/*__*.md`) | yes |

The obvious edit, adding `"final"` to `_SWARM_RESEARCHER_SUFFIXES`, generates
`!research.*.final`. That vetoes the lead **agent**, not a file suffix. With that veto,
`202609/topic/topic.md` stops firing when the lead commits it, which is every default
(non-linker) swarm. It keeps firing only when `research.<N>.linker` commits it. I
confirmed this with `hook_matches_event`.

**Recommendation:** leave the spec's behavior unchanged, and make the exclusion explicit
so it cannot regress:

- Add `widgets__final.md` at both depths to the candidates in `tests/test_filters.py`.
  Add agent-veto rows `("research.26.linker", True)` and `("research.26.image", True)`,
  and remove the `critique` row.
- Rename `_SWARM_RESEARCHER_SUFFIXES` to `_SWARM_RESEARCHER_AGENT_SUFFIXES`. Update the
  comment to say that `__final.md` drafts, like researcher drafts, are excluded by the
  generic `__*` path glob.
- Update the README's hook paragraph: replace the `__critique.md` sentence with
  `__final.md`.

### Linker model input

Every role already has its own model input, and the request adds `image_model`. The
linker should get `linker_model` too, defaulting to `@large`, which is SASE's
`default_model`.

The job is editorial, so it does not need `@xlarge`. It is not trivial either: the
linker must restructure 300–700 line reports without losing a caveat. That argues
against `@medium` as the default. Picking a provider different from the lead's also
gives a mild fresh-eyes benefit.

### Lead registration

The linker finds the lead's report through `wait.artifacts`, and that namespace only
lists artifacts registered with `sase artifact create`. Committed Markdown is never
auto-captured (`src/sase/core/artifact_file_defaults.py:73–163`).

The lead therefore must register `<name>/<name>__final.md` whenever `linker or image`
is true. The critique's step 5 already has the right wording; switch its condition from
`critique` to `run_linker`.

The linker should also register its own `<name>.md`. It should read the lead's report
with `sase artifact read`, so the read is audited and feeds SASE's link derivation.

### Infographic filename

The image agent forks from the lead and follows `#research/image`, which writes
`<source-stem>_infographic.png`. In linker mode the source is `<name>__final.md`, so the
image would be named `<name>__final_infographic.png`. That breaks the repository
convention of `<topic>/<topic>_infographic.png` (README) and leaks a draft name into the
published report.

Change `#research/image` so that `<source-stem>` drops any trailing `__<suffix>`
(`topic__final.md` → `topic_infographic.png`), and create the image without overwrite.
The rule is generic and keeps `#research/image` usable on its own. The linker prompt
also lists image artifacts from `wait.artifacts` (auto-captured as `kind == "image"`,
with `vcs_relpath`), so the linker finds the file even if an image agent ignores the
convention.

### Definition of a valid link

"All links valid" needs a scope and a failure policy. Otherwise an editor either quietly
deletes citations or starts researching replacements. See the
[policy](#link-validation-policy).

### Heading rules for anchors

In-document links only work in both renderers when headings are plain text. See
[the anchor section](#anchor-links-across-github-and-the-pdf).

### PDF heading levels

This is outside the plugin but directly limits what the linker can achieve. `bob-cli`
passes `--metadata title=<first H1>` **and** keeps the H1 in the body, so every report
renders like this:

```text
\maketitle                      <- title block
\section{My Title}              <- "1 My Title" (duplicate)
\subsection{Bottom line}        <- "1.1 Bottom line"
\subsection{Findings}           <- "1.2 Findings"
```

With `--shift-heading-level-by=-1`, pandoc treats the leading H1 as the title, and `##`
sections become "1 Bottom line", "2 Findings". I verified both renderings with pandoc.
This is a one-line change in `create.rs`.

The one caveat: a report with several genuine H1 sections would demote the later ones
to plain paragraphs, so check a sample of old reports first. File it as a `bob-cli`
follow-up; the linker design does not depend on it.

## Anchor links across GitHub and the PDF

GitHub builds anchors with its own slugger. The Highlights PDF uses pandoc's
`auto_identifiers`, and sase's own pager uses a third variant
(`src/sase/pager/_resolve_fragments.py:58–72`). They disagree on anything beyond plain
words. Here are pandoc 3.1.11's actual identifiers for sample headings:

| Heading | pandoc markdown (the PDF) | GFM (GitHub-style) |
| --- | --- | --- |
| `Python 3.12 support ✅` | `python-3.12-support` | `python-312-support-…` |
| `2026 roadmap — next` | `roadmap-next` | `2026-roadmap--next` |
| `` `__final` suffix `` | `final-suffix` | `__final-suffix` |
| `Bottom line` (twice) | `bottom-line`, `bottom-line-1` | `bottom-line`, `bottom-line-1` |

**The rule for the linker:** every heading that is a link target starts with a letter,
contains only letters, digits, spaces, and hyphens, and is unique. Its anchor is then
the heading lowercased with spaces replaced by hyphens, and GitHub, pandoc, and sase's
pager all agree on it.

Status emoji and version numbers that the lead often puts in headings (for example
`✅ verified`) move into the section's first line, which preserves their meaning. The
linker can check anchors deterministically when pandoc is available:

```bash
pandoc <file> -t html | grep -o '<h[1-6] id="[^"]*"'
```

Raw HTML anchors such as `<a id="x"></a>` are not a way around this. Pandoc drops raw
HTML when producing LaTeX, so those anchors vanish from the PDF.

Pandoc does render internal links as PDF hyperlinks: `[x](#bottom-line)` becomes
`\hyperref[bottom-line]{x}`, which I verified. "No TOC" is also the right call, since
the PDF gets a three-level hyperlinked TOC and GitHub shows an outline.

## Link validation policy

These are the rules I would give the linker:

- **External URLs:** make an HTTP request, for example
  `curl -fsSL -o /dev/null --max-time 20 <url>`. Treat 401, 403, and 429 as
  *unverified*, not broken, because they usually mean bot blocking or rate limits. Keep
  those links.
- **Links into repository files** (`github.com/.../blob/...`): verify them through a
  `/sase_repo` checkout (`git cat-file -e <ref>:<path>`, and a line-count check for
  `#L` anchors). Fetching repository file URLs over the web is exactly what this
  project's repo rules forbid.
- **Relative links:** resolve them from `<YYYYMM>/<name>/`. The lead has just moved the
  researcher drafts into that directory, which is the most likely source of broken
  relative links.
- **Repairs are mechanical only:** a followed redirect, a moved file, an obvious typo, or
  a renamed heading. When a link cannot be repaired, keep its text, drop the dead URL,
  and list it in the linker's final response. **Never search for replacement sources**;
  that would be research, which the linker is barred from.
- **URL-set check:** every URL in `__final.md` must appear in `<name>.md` unless it was
  listed as unrepairable. This is a cheap, deterministic guard against silently lost
  citations.

One gap is worth knowing: relative links to *other* Markdown files work on GitHub but
cannot work in the PDF, which lives under `~/bob/xlib/`. Only `http(s)` URLs, in-document
anchors, and embedded images survive into the PDF. I would accept this for sibling-draft
links, which are rare in consolidated reports, and not have the linker rewrite them as
absolute GitHub URLs. That choice is listed in [Open questions](#open-questions).

## Wait graph and failure modes

```text
cdx ─┐
cld ─┼─► final ──► image (forks final)
...  ┘      │          │
            └──────────┴──► linker   (waits on final, and on image when image=true)
```

- **`wait.artifacts` is not transitive.** A waiter sees only its own `%wait` targets,
  plus implied `#fork` targets (`src/sase/axe/run_agent_directives_flow.py:49–95`). If
  the linker waited only on `image`, it would see the image agent's PNG but not the
  lead's registered report. The prototype emits
  `%wait:research.{@1}.final {% if image %}%wait:research.{@1}.image {% endif %}`.
- **A wait on a dropped segment parks forever, silently.** `%if` gating deletes the text
  of skipped segments, and the named waits in other segments are not rewritten
  (`docs/xprompt.md:1877–1881`, `2492–2505`). The linker's image wait must therefore use
  exactly the same condition as the image segment, `image`. The prototype does.
- **An image failure now blocks publication.** Named waits release only on success.
  Today a failed image agent costs nothing, because the lead's `<name>.md` and its PDF
  already exist. With the linker, a failed image agent leaves the linker parked: there
  is no `<name>.md` and no PDF. SASE posts a "Wait dependency can never self-resolve"
  notification. Recovery means rerunning the image agent, or relaunching the linker
  without the image wait. I accept this coupling, because a PDF without the image is
  exactly what the feature exists to prevent, but document the recovery path.
- **Sidecar freshness.** `sase repo open research` fast-forwards a clean workspace clone
  (`src/sase/_linked_repo_workspaces.py:200–254`), and the lead's `done.json` is written
  after its finalizer pushes. The linker's checkout will therefore contain
  `<name>/`, the moved drafts, and the PNG. If the clone is dirty, the refresh is
  silently skipped. The lead's report is still readable through `sase artifact read`,
  and the finalizer rebases before pushing, so the worst case is a missed image
  embedding that the linker reports.
- **Latency and cost.** One more agent (`@large`) runs serially after the image agent.
  Removing the critique (`@xlarge`) roughly offsets the cost for anyone who used it.

## Alternatives considered

| Alternative | Verdict | Why |
| --- | --- | --- |
| **Separate linker agent (the proposal)** | **Recommended** | It is the only option that can embed the image before the hook's single `ADD`. A fresh context gives an editorial pass without the lead's research-saturated context. It also has clean separation from the image agent. |
| Fold formatting and link rules into the lead | Rejected as a replacement | It is cheaper, but it cannot embed the image, because the image does not exist when the lead's file triggers the hook. The lead is also the worst-placed agent to judge its own structure. *Partial adoption is worthwhile:* see [follow-ups](#follow-ups-outside-this-change). |
| Image agent edits `<name>.md` and the hook also fires on `MODIFY` | Rejected | Bob refuses an existing target without `--force`, and a regenerated PDF would duplicate entries in the Highlights library. It also changes hook semantics for every research file. |
| Deterministic post-processor script (no LLM) | Rejected as the main mechanism | It cannot restructure or add meaningful cross-references. Stripping numbers mechanically also breaks in-text references such as "see 2.3". Worth adopting later as a verification helper for anchors, URLs, and URL-set parity. |
| Linker uses `#fork:research.{@1}.final` | Rejected | Fork injects the lead's entire transcript as text (`src/sase/history/chat_fork/build.py:31–163`). That is expensive and invites re-research. The file is the contract. |
| Keep critique alongside the linker | Rejected | Unused. Its companion file is excluded from the PDF, and the linker cannot absorb its verification job without violating "no research". It is restorable from commit `59fdf94` if wanted. |
| Tri-state `linker` (null = follow `image`) | Not needed | It only matters if someone wants an image without embedding. A plain `linker or image` is simpler; revisit if that need appears. |

On naming: `linker` describes only one of the agent's four jobs (restructure, embed,
validate, cross-link). `editor` or `publisher` would describe the role better, since it
produces the published file. `linker` is still acceptable, and I would not block on it.

## Recommended solution

Implement the proposal in `sase-research-artifacts` with the
[adjustments](#adjusted-requirements) above. This is a prompt-template and test change
only; `sase` needs no code change.

### Template changes

**Frontmatter.** Delete `critique` and `critique_model`. After `lead_model`, add:

```yaml
  - name: image
    type: bool
    default: false
    description:
      Generate an infographic after the lead researcher finishes. Implies the linker
      agent, which embeds the infographic in the final report.
  - name: image_model
    type: word
    default: "@image"
    description: Model alias or provider model for the optional `<clan>.image` agent.
  - name: linker
    type: bool
    default: false
    description:
      Run a linker agent after the lead (and after the image agent when `image=true`).
      The lead then writes `<name>__final.md`, and the linker rewrites it into the
      canonical `<name>.md` with an organized structure, validated links, in-document
      links, and the embedded infographic. Always runs when `image=true`.
  - name: linker_model
    type: word
    default: "@large"
    description: Model alias or provider model for the optional `<clan>.linker` agent.
```

**Jinja prelude.** Replace the critique layout namespace with the following, placed
after the `researchers` set and before the lead's layout. The lead's layout then ends
with `"└── " ~ lead_report`.

```jinja
{%- set run_linker = linker or image -%}
{%- set lead_report = "<name>__final.md" if run_linker else "<name>.md" -%}
{%- set lns = namespace(lines=["<month-dir>/<name>/"]) -%}
{%- for r in researchers -%}
{%- set _ = lns.lines.append("├── <name>__" ~ r.short ~ ".md") -%}
{%- endfor -%}
{%- set _ = lns.lines.append("├── <name>__final.md") -%}
{%- if image -%}{%- set _ = lns.lines.append("├── <name>_infographic.png") -%}{%- endif -%}
{%- set _ = lns.lines.append("└── <name>.md") -%}
{%- set linker_layout_body = lns.lines | join("\n") -%}
```

**Lead segment.** Both branches of step 4 write `<name>/{{ lead_report }}`. The two
`{%- if critique %}` blocks collapse into one `{%- if run_linker %}` block after the
`researchers` if/else, containing:

- a paragraph telling the lead *not* to create `<name>/<name>.md`, because
  `research.{@1}.linker` publishes it (after the image agent when `image`), so the lead
  should spend its effort on substance;
- step 5, registering `research:<YYYYMM>/<name>/<name>__final.md`.

The solo branch's hard-coded layout block can reuse `layout_body`.

**Image segment.** Change `%model:@image` to `%m:{{ image_model }}`. Nothing else
changes.

**Linker segment.** This replaces the critique segment. It is the exact prototype text
that I rendered and planned:

````text
%if(should_run={{ run_linker }}) %id(linker, clan=research.{@1}) %m:{{ linker_model }}
%wait:research.{@1}.final {% if image %}%wait:research.{@1}.image {% endif %}%q({% if runners is not none %}{{ runners }}{% else %}1.5x{% endif %}, w=0.25{% if priority is not none %}, priority={{ priority }}{% endif %})

You are the linker agent for a research swarm. The lead researcher,
`research.{@1}.final`, wrote a consolidated report on the request below as
`<name>__final.md`{% if image %}, and the image agent, `research.{@1}.image`, drew an
infographic for it{% endif %}. Turn that report into the canonical `<name>.md`, the file
readers open on GitHub and that SASE renders into a Highlights PDF. You are an editor,
not a researcher: preserve the lead's meaning and intent exactly. Do not do new
research, add claims or sources, or change the recommendation.

SASE derives your plan's links from the artifacts you read this turn; use
`sase artifact read` for context you actually used.

Research request (context only; do not research it):

{{ prompt }}

The lead researcher's registered reports:

{% raw %}{% for a in wait.artifacts if a.kind == "markdown" and a.label and a.label.startswith("research:") %}
- wait_name={{ a.wait_name }} label={{ a.label }} source_path={{ a.source_path }} path={{ a.path }} ref={{ a.ref }}
{% endfor %}{% endraw %}
{% if image %}
Images from the agents you waited on:

{% raw %}{% for a in wait.artifacts if a.kind == "image" %}
- wait_name={{ a.wait_name }} vcs_relpath={{ a.vcs_relpath }} path={{ a.path }} ref={{ a.ref }}
{% endfor %}{% endraw %}
{% endif %}
Steps:

1. Identify the lead's report: exactly one entry with `wait_name` `research.{@1}.final`
   whose label has the form `research:<YYYYMM>/<name>/<name>__final.md`. If there is not
   exactly one, stop and report the missing or ambiguous input instead of guessing. Open
   the research repo with `/sase_repo`, then read the report through its canonical
   research reference (or the `ref` field's `file:<id>` reference if the original has
   moved) using `sase artifact read`. Take `<YYYYMM>/<name>/` from that label, never
   from the current date. Do not read any agent's chat transcript. Never modify, move,
   or rename `<name>__final.md` or the researcher drafts beside it.
2. Before editing, inventory everything that must survive: each finding,
   recommendation, caveat, open question, confidence or verification marker, number,
   date, version, code block, table, and link.
3. Restructure the report:
   - Copy the lead's frontmatter (set `updated_time` to today if present), then one `#`
     title, then the bottom line or recommendation so a reader can act after the first
     screen.
   - Organize the body under `##` sections and `###` subsections that follow the
     reader's questions, merging duplicated passages and moving misplaced material to
     where it belongs. Do not go deeper than `###`.
   - Do not number headings (no `1.`, `2.3`, `Part 2 —`, or similar prefixes); the PDF
     renderer numbers sections itself. Name labels such as `Option A` or `Phase 0` may
     stay.
   - Do not add a table of contents or a block of jump links; GitHub and the PDF both
     provide an outline.
   - Keep the lead's wording where it works. Tighten repetition, but never drop a claim,
     caveat, or source to save space.
{%- if image %}
   - Embed the infographic, normally `<name>_infographic.png` beside the report (or the
     image listed above), on its own line with a relative link and descriptive alt text,
     for example `![What the infographic shows](<name>_infographic.png)`. Place it
     where it best supports the text, usually right after the bottom line or the overview
     it summarizes. If no image exists in your checkout, continue without one and say so
     in your final response.
{%- endif %}
4. Validate every link carried over from the lead's report:
   - Request each external URL (for example with
     `curl -fsSL -o /dev/null --max-time 20 <url>`). Verify links into a repository's
     files through a `/sase_repo` checkout instead of fetching them.
   - Resolve relative links from `<YYYYMM>/<name>/` in your checkout; the lead moved the
     researcher drafts into that directory.
   - Fix a broken link only when the correct target is certain: a redirect, a moved
     file, an obvious typo, or a renamed heading. Treat 401, 403, and 429 responses as
     unverified, not broken, and keep those links. When a link cannot be repaired, keep
     its text, drop the dead URL, and list it in your final response. Never search for
     replacement sources.
5. Add in-document links where they help a reader move around: from a summary point to
   the section holding its evidence, from "see below" or "as discussed above" phrases,
   and from mentions of named findings, options, or phases. Link inline and sparingly.
   Give every heading you link to plain text: start with a letter; use only letters,
   digits, spaces, and hyphens; no punctuation, emoji, or code; no duplicate headings.
   Its anchor is then the heading lowercased with spaces replaced by hyphens
   (`## Bottom line` → `#bottom-line`), which GitHub and the PDF renderer resolve
   identically. When `pandoc` is installed, confirm each `#anchor` against
   `pandoc <file> -t html | grep -o '<h[1-6] id="[^"]*"'`.
6. Check your draft against the step 2 inventory and restore anything missing or
   changed. Every URL in `<name>__final.md` must appear in your draft unless you listed
   it as unrepairable.
7. Write `<YYYYMM>/<name>/<name>.md` without overwrite: if the file already exists, stop
   and report the collision visibly instead of replacing it or choosing another name.
8. After the write succeeds, register it as a durable snapshot:

   sase artifact create -p "<absolute-report-path>" -l "research:<repo-relative-report-path>"

   Use the report's actual absolute path and its path relative to the research repo
   root, for example `research:202609/<name>/<name>.md`. Do not pass `--move`. If
   registration fails, report that failure; do not report the task as fully complete.

Final layout:

{{ "```text\n" ~ linker_layout_body ~ "\n```" }}
````

Two authoring gotchas the implementer must respect:

- **Keep `%{…}` and `#anchor` examples inside inline code.** `%{` opens an alternation
  anywhere outside literal zones (`docs/xprompt.md:3085–3092`). A bare
  `-w '%{http_code}'` would fan the swarm out, which is why the prototype uses
  `curl -f`. A bare `#bottom-line` would trigger an "unknown xprompt reference" warning.
- **Leave the `{% raw %}` wrappers in place.** Without them the swarm-level render would
  consume the runtime `wait.artifacts` loops.

### Other files

- **`research_image.md`:** strip a trailing `__<suffix>` from `<source-stem>`, and write
  the image without overwrite.
- **`provider.py`:** no behavior change. Make the constant rename and comment update from
  [Hook suffix list](#hook-suffix-list), and remove "and critique" from the depth-2 glob
  comment.
- **`default_config.yml`:** the bucket description changes "the optional critique agent"
  to "the optional linker agent". The user's effective config overrides this description
  from another layer, so check that layer too.
- **Tests (`tests/test_xprompt_loading.py`):**
  - Update the input-list assertion.
  - Replace the seven critique tests with linker equivalents: opt-in adds one segment;
    `image=true` alone yields 5 segments with the linker last; the linker waits on
    `final` always and on `image` only when `image`; `linker_model` and `image_model`
    route only to their own roles; queue options carry through; the swarm `wait`
    argument does not leak into the linker; the solo lead plus linker yields 2 segments.
  - Add a runtime render test like the critique one, with a markdown `__final.md`
    artifact and an image artifact.
  - Assert the lead writes `<name>__final.md` and registers it only in linker mode.
  - Update the image test's `%model:@image` assertion.
- **`tests/test_wheel_contract.py` and `.github/workflows/publish.yml`:**
  `len(segments) == (4 if image else 3)` becomes `5 if image else 3`. The authored count
  `content.count("%q(1.5x, w=0.25") == 8` should hold, because the linker replaces the
  critique one-for-one. Re-verify the published-floor smoke's hard-coded
  `len(segments) == 4` for defaults.
- **Docs:** update `README.md`, `docs/xprompts.md` (input table, segment list, handoff
  contract, the "image implies linker" rule), `AGENTS.md`'s architecture bullet, and
  `docs/configuration.md`.

### Validation performed

I ran the prototype through the installed `sase`'s real loader, expander, launch planner,
and runtime renderer, with an isolated `SASE_HOME`:

- **Default renders are byte-identical.** Renders with default, solo, all-five
  researchers, and `priority` plus `wait` arguments match today's plugin output byte for
  byte. Non-linker users see no change.
- **Segment counts are right.** `linker=true` gives 4 segments; `image=true` gives 5
  (`… final, image, linker`); solo plus linker gives 2. Every render plans with no
  diagnostics and exactly one `%q(`.
- **Waits and models route correctly.** With `image=true, wait=…, runners=8, priority=2`,
  the linker renders `%wait:research.{@1}.final %wait:research.{@1}.image
  %q(8, w=0.25, priority=2)`, and the swarm `wait` does not leak into it. Custom
  `image_model` and `linker_model` values route only to their own segments.
- **The runtime render works.** Against fake `wait.artifacts`, the linker's two loops
  list the lead's `__final.md` report and the image's `vcs_relpath`, drop the unrelated
  artifact, and leave no stray Jinja.

I did not modify the plugin repository or run its test suite. The test list above is
derived from the existing tests.

### Rollout

1. Land the change with `linker=false` by default.
2. Run the next several swarms with `linker=true` (or `image=true`), and diff each
   `<name>.md` against its `__final.md`. Look for dropped caveats, changed numbers, and
   lost URLs, and check the anchors in the PDF.
3. If fidelity holds, consider making `linker` default to `true`. The linker's gains
   (clean PDF numbering, checked links, cross-references) apply to every report, not
   just ones with images.

## Follow-ups outside this change

- **`bob-cli`:** add `--shift-heading-level-by=-1` to the pandoc call
  ([why](#pdf-heading-levels)). This gives the linker's clean structure a clean PDF.
- **`sase`:** `derive_research_swarm_lineage` (`src/sase/artifact_links/derive/_research_lineage.py:8`)
  still only recognizes the retired `__a`/`__b` suffixes. It derives no lineage for
  `__cdx`, `__cld`, `__grk`, `__mus`, `__gem`, or the new `__final`. This defect predates
  this change and is independent of it. I did not file a bead, to avoid five swarm
  researchers filing duplicates; the lead or the user should decide.
- **Lead hygiene rules in non-linker mode (optional):** tell the lead to use unnumbered
  headings and no manual TOC even when the linker is off. This is cheap and improves
  every default PDF, but it deliberately gives up the byte-identical default render.
- **Deterministic checker (optional, later):** a small plugin console script that checks
  anchors against pandoc identifiers, external URLs, and URL-set parity between
  `__final.md` and `<name>.md`. The linker could call it instead of following prose
  instructions.

## Open questions

- **Default flip:** should `linker` default to `true` after a trial period? This depends
  on the rollout diffs.
- **Model tier:** is `@large` enough for faithful restructuring of the longest reports,
  or does fidelity justify `@xlarge`? The trial answers this too.
- **Cross-file links:** should cross-file links be rewritten as absolute GitHub URLs so
  they work in the PDF? I lean no, because they are rare and relative links are more
  robust to later reorganization.
- **Name:** keep `linker`, or rename to `editor` or `publisher` before the input becomes
  habit?
