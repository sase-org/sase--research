---
create_time: 2026-09-30
updated_time: 2026-09-30
status: final
tags: [research_swarm, xprompts, sase-research-artifacts, highlights, linker, file-hooks]
---

# Adding a linker agent to `#research_swarm`

**Question.** How should `#research_swarm` gain an opt-in `linker` agent that publishes
the report the `research-highlights` hook consumes? The request also removes the
`critique` agent and adds an `image_model` input. Is the plan sound, and what should
change?

**Sources.** This report merges five independent researcher reports (`__cdx`, `__cld`,
`__grk`, `__mus`, `__gem`, beside this file) with my own verification against:

- `sase-research-artifacts` at `c9f41f3`, which owns `#research_swarm`, `#research/image`,
  and the hook spec;
- `sase` at `8a00076f1f`, which owns `%wait`, input binding, and artifact capture;
- `bob-cli` at `5b1f991`, which owns the `bob highlights create` PDF renderer;
- the research sidecar corpus.

Where the reports disagreed, I checked the code and say which view held. The rulings are
collected in [Resolved disagreements between reports](#resolved-disagreements-between-reports).

## Bottom line

Build it. The plan is a good idea, and all five researchers agree. Its real value is not
the reformatting. It is a **publication barrier**:

1. The lead writes an intermediate `__final.md` that the hook ignores.
2. The image agent, if enabled, runs next.
3. Only then is the one hook-eligible `<name>.md` created.

That is the only ordering that puts an infographic into the Highlights PDF (see
[Why the linker is worth adding](#why-the-linker-is-worth-adding)). Removing critique and
exposing `image_model` are both sound.

Keep today's fast path untouched. With `linker=false` and `image=false`, the lead still
writes `<name>.md` directly and no extra agent runs.

I would ship the plan with these adjustments. Each is explained below.

- **Do not add `final` to the hook's suffix tuple.** That tuple feeds an *agent-name*
  veto. Adding `final` would stop the Highlights PDF for every default swarm.
  `__final.md` is already excluded by the hook's path glob. Pin that with a test instead
  ([details](#keep-final-out-of-the-agent-veto)).
- **The lead must register `__final.md` whenever the linker runs.** Today it registers
  only for critique ([details](#register-the-lead-report-whenever-the-linker-runs)).
- **The linker waits on the lead always, and on the image agent when `image=true`.**
  `wait.artifacts` is not transitive
  ([details](#wait-on-both-the-lead-and-the-image-agent)).
- **Accept that a failed image agent now blocks publication, and document the
  recovery.** The plan does not mention this new failure mode
  ([details](#accept-and-document-the-image-failure-coupling)).
- **Name the infographic `<name>_infographic.png`**, not `<name>__final_infographic.png`
  ([details](#name-the-infographic-after-the-topic)).
- **Add a `linker_model` input** (default `@xlarge`). Every other role has one
  ([details](#add-a-linker-model-input)).
- **Replace "ensure all links are valid" with an enforceable policy.** Repairs are
  mechanical only, unverifiable is not the same as broken, and every URL must survive
  ([details](#define-what-a-valid-link-means)).
- **Require plain-text headings for link targets**, so in-document links work both on
  GitHub and in the PDF ([details](#use-plain-text-headings-for-link-targets)).

## Why the linker is worth adding

### The hook fires once, before the image exists

`research-highlights` fires only on the `ADD` of a hook-eligible Markdown file. Today that
file is the lead's `<name>.md`. The image agent starts after the lead finishes, so its PNG
is committed later and can never reach the PDF. A later edit cannot fix this, because
`MODIFY` does not fire the hook.

The corpus shows the damage:

- The research sidecar holds **255** `*_infographic.png` files.
- **228** of them sit beside a same-stem report.
- **None** of those reports embeds its image with Markdown image syntax.

The researchers' own counts (gem "essentially none", cld "5 of 231") were close. My
stricter image-syntax check found zero.

### The PDF renderer already numbers sections and builds a TOC

`bob highlights create` (`bob-cli/src/native/highlights_ref/create.rs:674–705`) runs
pandoc with `--standalone --toc --toc-depth=3 --number-sections` and
`--resource-path=<report dir>`. This backs up two of the user's formatting rules:

- **Unnumbered headings.** A manual `## 1.1 Mechanism` renders doubly numbered.
  **69 of 88** consolidated reports created in 2026-09 have manually numbered headings.
- **No table of contents.** The PDF already gets a hyperlinked three-level TOC, and
  GitHub shows an outline. None of the 88 reports has a TOC today, so this rule guards
  against the linker adding one.

A relative `![...](<name>_infographic.png)` resolves in the PDF, because the resource path
is the report's directory. Internal `[x](#anchor)` links also render as PDF hyperlinks
(cld verified this with pandoc).

### Critique costs more than it returns

Only two `__critique.md` files exist. Their output is excluded from the Highlights PDF, so
their findings never reached the reading queue. Neither of the user's snippets (`rs`,
`rsa`) passes `critique=true`. Removing it deletes a segment, two inputs, a conditional
registration path, and a block of tests. It also frees the eighth segment slot that the
linker takes over.

### Alternatives considered

| Alternative | Verdict | Why |
| --- | --- | --- |
| Separate linker agent (the proposal) | **Recommended** | The only option that can embed the image before the hook's single `ADD`. A fresh context also gives an honest editorial pass. |
| Fold formatting and links into the lead | Rejected | The lead cannot embed an image that does not exist yet, and cannot wait on a child it has not launched. A single-turn agent cannot "come back later". |
| Image agent writes `<name>.md` | Rejected | Mixes illustration with editing, and leaves `linker=true, image=false` without a publisher. |
| Fire the hook on `MODIFY`, or debounce it | Rejected | Needs host changes, double-renders (Bob refuses an existing target without `--force`), and still does no restructuring. |
| Deterministic post-processor script | Rejected as the main mechanism, kept as a later helper | It cannot reorganize prose or place cross-links semantically. It is ideal for checking anchors and URLs ([follow-ups](#follow-ups-outside-this-change)). |
| Always run the linker | Rejected for now | Costs an extra serial agent on every `rs` dispatch. Revisit after the [rollout](#rollout). |
| Linker `#fork`s the lead | Rejected | A fork injects the lead's whole transcript. That is expensive and invites re-research and inherited framing. The file is the contract. |

## How the swarm works today

`src/sase_research_artifacts/xprompts/research_swarm.md` authors eight segments:

- five gated researchers;
- the lead, `research.<N>.final`;
- `image`, whose entire body is `#fork:research.{@1}.final #research/image` with a
  hard-coded `%model:@image`;
- `critique`.

The lead moves the drafts to `<name>/<name>__<suffix>.md` and writes `<name>/<name>.md`.
It registers that report with `sase artifact create` **only when `critique=true`**
(lines 287–298 and 313–324), because critique is its only `wait.artifacts` consumer.
(The mus report says the lead always registers. It does not.)

`RESEARCH_HIGHLIGHTS_HOOK_SPEC` (`provider.py:94–121`) has these filters:

| Filter | Value | Effect |
| --- | --- | --- |
| `sidecars` / `producers` / `ops` | `research`; `commit`, `sdd`, `finalizer`; `ADD` | First commit of a file only |
| `path_globs` | `20*/**/*.md`, `!20*/*__*.md`, `!20*/*/*__*.md`, companion-page excludes | **Any** `__*` Markdown file at depth 1 or 2 is ignored, including `__final.md` |
| `agent_name_globs` | `!research.*.{cdx,cld,grk,mus,gem}` from `_SWARM_RESEARCHER_SUFFIXES` | Vetoes the *agent* that committed the file. `.final`, `.image`, `.critique`, and a future `.linker` all pass |

The producer filter came from epic `sase-s5`. It means registering a report with
`sase artifact create` never fires the hook. Only the committed file does, once, under
its canonical basename. So the linker can register its `<name>.md` without
double-rendering the PDF.

`#research/image` is two lines long. It tells the agent to illustrate "this research
markdown file" and write `<source-stem>_infographic.png` in the same directory.

## Adjusted requirements

| Requirement | Verdict | Change |
| --- | --- | --- |
| `linker` bool, default `false` | Agree | Consider flipping the default after the [rollout](#rollout). |
| Linker runs when `linker or image` | Agree | Derive one flag, `run_linker = linker or image`, and use it everywhere. Document that `image` implies the linker. |
| Lead writes `<name>__final.md` when the linker runs | Agree | The lead must also register it ([details](#register-the-lead-report-whenever-the-linker-runs)). |
| Add `__final` to the hook's ignore-suffix list | **Adjust** | There is no filename-suffix list. The only tuple is the agent veto ([details](#keep-final-out-of-the-agent-veto)). |
| Linker creates the hook's file | Agree | It writes `<name>.md`, so Bob's marker IDs and reference notes are unchanged. |
| Linker preserves meaning and does no research | Agree, **strengthen** | Add a survival inventory and a URL-parity check so drift is caught, not just forbidden. |
| Unnumbered sections | Agree | Justified directly by `--number-sections`. |
| Embed the image when `image=true` | Agree, **adjust** | Fix the filename. Embed only an image that actually exists. Make the failure mode explicit ([details](#accept-and-document-the-image-failure-coupling)). |
| All links valid | **Adjust** | Needs a scope and a failure policy ([details](#define-what-a-valid-link-means)). |
| Local jump links, no TOC | Agree, **add heading rules** | ([details](#use-plain-text-headings-for-link-targets)) |
| Remove critique | Agree | Stale `critique=true` arguments are silently ignored, not rejected ([details](#remove-critique-cleanly)). |
| `image_model` input | Agree | Default `@image`, so behavior is unchanged. |
| *(new)* `linker_model` input | Add | ([details](#add-a-linker-model-input)) |

### Keep final out of the agent veto

All five researchers caught this, and I confirmed it in `provider.py`. The request's
"list of suffixes the file hook uses to ignore certain research files" matches the
comment on `_SWARM_RESEARCHER_SUFFIXES` ("Their drafts get no Highlights PDF"). But the
tuple generates only `agent_name_globs`.

Adding `"final"` would produce `!research.*.final`. That vetoes the lead *agent*. On the
default path, `research.<N>.final` is the agent that ADDs `<name>.md`, so every
non-linker swarm would silently lose its Highlights PDF. Filename exclusion already
happens in the generic `!20*/*/*__*.md` glob. cld ran sase's real matcher:
`topic/topic__final.md` and `topic__final.md` do not fire, and `topic/topic.md` does.

The request's intent is "ignore `__final.md`", and the hook already does that. Make it
explicit and regression-proof instead:

- Rename `_SWARM_RESEARCHER_SUFFIXES` to `_SWARM_RESEARCHER_AGENT_SUFFIXES`, and reword
  its comment so it names what the tuple actually vetoes.
- Update the depth-2 glob comment from "drafts and critique" to "researcher drafts and
  the lead's `__final.md` intermediate".
- Tests should assert:
  - `widgets__final.md` is filtered at both depths;
  - `research.26.final` and `research.26.linker` both pass the agent veto;
  - the five researcher agents are still vetoed.

  Drop the `.critique` row.
- Do **not** replace the broad `__*` glob with an enumerated suffix list. That would
  narrow today's behavior and rot every time a role is added. If you want an explicit
  list for readability, keep it separate from the agent tuple (cdx's split:
  `_HIGHLIGHTS_IGNORED_FILE_SUFFIXES` for paths, and the agent tuple only for
  `agent_name_globs`).

### Register the lead report whenever the linker runs

The linker finds the lead's report through `wait.artifacts`. That list includes only
registered Markdown, because committed Markdown is never auto-captured. Retarget the
existing critique registration step from `{% if critique %}` to `{% if run_linker %}`,
with the example label `research:202609/<name>/<name>__final.md`. Keep it out of the
default path, so the non-linker render stays byte-identical.

Do not tell the lead that "a linker will clean this up". `__final.md` is the archival
synthesis and the linker's only source. The linker is forbidden to repair substance, so
the lead's quality bar must not drop. The lead's instructions change in only three ways:

- the filename;
- the registration step;
- one sentence telling it not to create `<name>.md` (not even as a placeholder), because
  `research.{@1}.linker` publishes it.

### Wait on both the lead and the image agent

`wait.artifacts` holds only the waiter's own `%wait` targets, plus implied `#fork`
targets. If the linker waited only on `image`, it would see the PNG but not the lead's
report. Author:

```text
%wait:research.{@1}.final {% if image %}%wait:research.{@1}.image {% endif %}
```

The image wait must use exactly the same condition as the image segment's `should_run`.
`%if` gating deletes skipped segments but does not rewrite other segments' named waits. A
wait on a dropped segment would park the linker forever.

Do not `#fork` into the linker. Do not apply the swarm's `wait=` input to it either; that
input gates researchers only, as it does today.

### Accept and document the image failure coupling

This is the one real regression in the plan. None of the requirements mentions it, and
the reports split on it:

- cdx proposed "fail-soft" publication without the image.
- cld and grk said the linker parks.

The docs settle it (`docs/xprompt.md:2492–2505`). Named `%wait` dependencies release
**only** on a `done.json` outcome of `"completed"`, and no option on an agent wait
releases on failure. (Only `proc`/monitor waits do.)

**Today**, a failed image agent costs nothing: `<name>.md` and its PDF already exist.
**After the change**, with `image=true`, a failed image agent leaves the linker parked,
with no `<name>.md` and no PDF. SASE raises a red "Wait dependency can never
self-resolve" notification.

I would accept this coupling. A PDF without the image is exactly what the feature exists
to prevent, and the `@image` alias already falls back across three providers. Keep the
failure surface small, and make recovery obvious:

- **Fail soft only when the image agent completes without an image.** When the wait
  releases but no matching PNG exists, publish without it and say so in the final
  response. Never embed a path that does not exist.
- **Document the recovery** in `docs/xprompts.md`. A later *successful* run of the same
  `research.<N>.image` name releases the parked linker, per the wait docs. Alternatively,
  kill the linker and relaunch it without the image wait.
- **Warn about single-model overrides.** Setting `image_model` to one model gives up the
  alias's fallback chain.

### Name the infographic after the topic

In linker mode, the image agent's source is `<name>__final.md`. `#research/image` would
then write `<name>__final_infographic.png`. That leaks the intermediate's name into the
published report and breaks the README's `<topic>_infographic.png` convention. mus
suggested accepting the ugly name. I disagree, because the published report would embed
an asset named after a file readers should not open.

Change `#research/image` so that `<source-stem>` drops any trailing `__<suffix>`
(`topic__final.md` → `topic_infographic.png`), and create the file without overwrite.
This is cld's generic fix. It is one line, keeps the standalone xprompt consistent with
the repo convention, and avoids adding override text in the swarm that contradicts the
xprompt's literal rule. (grk and gem put the rule in the swarm segment instead. That
also works, but it leaves two conflicting instructions in one prompt.)

The linker should locate the image by two cues:

- the naming convention;
- a `kind == "image"` artifact from `research.{@1}.image` in `wait.artifacts`. Images are
  auto-captured at finalization (`src/sase/core/artifact_file_defaults.py`).

It should embed only a file it has confirmed exists in its checkout.

### Add a linker model input

Every role except image already has a `*_model` input, and the request adds
`image_model`. Four researchers recommend `linker_model`. mus preferred reusing
`lead_model` on YAGNI grounds, but coupling an editorial role to the synthesis role's
model is the more surprising contract.

On the default, the reports split between `@xlarge` (cdx, grk, gem) and `@large` (cld,
SASE's `default_model`). I recommend **`@xlarge` at launch**. Silent loss of a caveat or
number in a 300–700 line rewrite is this design's main risk, and `<name>.md` is the
artifact the user actually reads. Step down to `@large` if the [rollout](#rollout) diffs
show no fidelity loss.

### Define what a valid link means

An LLM told to "ensure" validity will either delete citations it cannot reach, or search
for replacement sources. The second is new research, which the linker is barred from.
Give it this policy:

- **Relative files and in-document anchors are hard requirements.** Resolve relative
  links from `<YYYYMM>/<name>/`. The lead just moved drafts there, which is the most
  likely source of breakage. Verify every `#anchor` against the final heading set.
- **External URLs are probed, and failures are reported honestly.** Probe with redirects
  (`curl -fsSL -o /dev/null --max-time 20 <url>`) and retry transient failures.
  401, 403, 429, and timeouts are *unverified*, not broken: keep those links.
- **Repository-file links** (`github.com/.../blob/...`) are verified through a
  `/sase_repo` checkout, not by fetching github.com. Fetching is what the project's repo
  rules forbid.
- **Repairs are mechanical only**: a followed redirect, a moved file, an obvious typo, or
  a renamed heading. For an unrepairable link, keep its text, drop the dead URL, and list
  it in the final response. **Never search for a replacement source.**
- **URL-set parity.** Every URL in `__final.md` must appear in `<name>.md` unless it was
  listed as unrepairable. This is a cheap, deterministic guard against silently lost
  citations.

Relative links to *other* Markdown files work on GitHub but not in the PDF, which lives
under `~/bob/xlib/`. They are rare in consolidated reports. Leave them relative rather
than rewriting them as absolute GitHub URLs.

### Use plain-text headings for link targets

The Highlights PDF uses pandoc's `auto_identifiers`, not GitHub's slugger. I reproduced
cld's comparison with the installed pandoc 3.1.11:

| Heading | pandoc (PDF) | GFM (GitHub) |
| --- | --- | --- |
| `Bottom line` | `bottom-line` | `bottom-line` |
| `2026 roadmap — next` | `roadmap-next` | `2026-roadmap--next` |
| `` `__final` suffix `` | `final-suffix` | `__final-suffix` |
| `Python 3.12 support ✅` | `python-3.12-support` | `python-312-support-white_check_mark` |
| `Bottom line` (again) | `bottom-line-1` | `bottom-line-1` |

The linker's rule is that any heading that is a link target:

- starts with a letter;
- contains only letters, digits, spaces, and hyphens;
- is unique.

Its anchor is then the heading lowercased with spaces replaced by hyphens, and both
renderers agree. Status emoji and version numbers move into the section's first line.
Raw `<a id>` anchors are not a workaround, because pandoc drops raw HTML when producing
LaTeX.

Add jump links inline and sparingly: from summary points to their evidence, and from "see
above/below" phrases or mentions of named options and phases. Do not link every heading
mention, and do not add a TOC or a block of jump links.

### Remove critique cleanly

Delete `critique`, `critique_model`, the critique segment, and `critique_layout_body`.

grk said stale `critique=true` arguments "fail at expansion". **They do not.**
`sase/xprompt/input_binding.py` preserves unknown named values for runtime-injected
context, and `sase xprompt expand '#research_swarm(bogus=true):: …'` exits 0 with no
warning. So removal is non-breaking at runtime. A stale `critique=true` silently does
nothing, which is harmless for this user. Still note it in the changelog.

Keep the `__*` path glob, which also hides the two legacy `__critique.md` files. Do not
pitch the linker as a replacement for critique: it is barred from verification research
by design. If adversarial review is wanted later, it should be a separate opt-in.

## Recommended solution

All changes land in `sase-research-artifacts` as one coordinated change. **No code
change in `sase` is required**: `%if`, `%wait`, `wait.artifacts`, image auto-capture,
and the hook matcher already do everything needed.

### Execution matrix

| `linker` | `image` | Agents (with default researchers) | Lead writes | Hook fires on |
| --- | --- | --- | --- | --- |
| false | false | cdx, cld, final (3) | `<name>.md`, unregistered | lead's `<name>.md` (unchanged) |
| true | false | … + linker (4) | `<name>__final.md`, registered | linker's `<name>.md` |
| false | true | … + image + linker (5) | `<name>__final.md`, registered | linker's `<name>.md` |
| true | true | … + image + linker (5) | `<name>__final.md`, registered | linker's `<name>.md` |

```text
researchers ──► final ─────────────────────► linker ──► <name>.md (hook)
                  └──► image (forks final) ──┘          (image wait only when image=true)
```

The authored segment count stays at eight, because linker replaces critique one for one.
The user's `rsa` snippet already passes `image=true`, so it picks up the linker
automatically (8 agents instead of 7). `rs` is unchanged.

### Template changes

**Inputs.** Delete `critique` and `critique_model`. After `lead_model`, add:

```yaml
  - name: image
    type: bool
    default: false
    description:
      Generate an infographic after the lead researcher finishes. Implies the linker
      agent, which embeds the infographic in the published report.
  - name: image_model
    type: word
    default: "@image"
    description: Model alias or provider model for the optional `<clan>.image` agent.
  - name: linker
    type: bool
    default: false
    description:
      Run a linker agent after the lead (and after the image agent when `image=true`).
      The lead then writes `<name>__final.md`, and the linker publishes it as
      `<name>.md` with unnumbered sections, checked links, in-document links, and the
      embedded infographic. Always runs when `image=true`.
  - name: linker_model
    type: word
    default: "@xlarge"
    description: Model alias or provider model for the optional `<clan>.linker` agent.
```

**Prelude.** Add `{%- set run_linker = linker or image -%}` and
`{%- set lead_report = "<name>__final.md" if run_linker else "<name>.md" -%}`. Replace the
critique layout namespace with a linker layout:

```text
<name>__<researcher suffixes>.md
<name>__final.md
<name>_infographic.png   (only when image=true)
<name>.md
```

The lead's layout then ends at `lead_report`. The solo-lead branch's hard-coded layout
can reuse the same variables.

**Lead segment.** Both branches of step 4 write `<name>/{{ lead_report }}`. The two
`{%- if critique %}` blocks become `{%- if run_linker %}`, and each holds the "do not
create `<name>.md`" sentence plus the registration step.

**Image segment.** Change `%model:@image` to `%m:{{ image_model }}`. The body is
otherwise unchanged; the naming fix lives in `research_image.md`.

**Linker segment.** This replaces critique. The text below is condensed from cld's
prototype. cld rendered that prototype through sase's real expander, launch planner, and
runtime `wait.artifacts` renderer:

- default renders were byte-identical to today;
- segment counts were 3 / 4 / 5 / 2 (solo + linker);
- each segment had exactly one `%q(`;
- the waits and models routed correctly.

````text
%if(should_run={{ run_linker }}) %id(linker, clan=research.{@1}) %m:{{ linker_model }}
%wait:research.{@1}.final {% if image %}%wait:research.{@1}.image {% endif %}%q({% if runners is not none %}{{ runners }}{% else %}1.5x{% endif %}, w=0.25{% if priority is not none %}, priority={{ priority }}{% endif %})

You are the linker agent for a research swarm. The lead researcher, `research.{@1}.final`,
wrote a consolidated report as `<name>__final.md`{% if image %}, and the image agent,
`research.{@1}.image`, drew an infographic for it{% endif %}. Publish that report as the
canonical `<name>.md`, the file readers open on GitHub and that SASE renders into a
Highlights PDF. You are an editor, not a researcher: preserve the lead's meaning and
intent exactly. Do not do new research, add claims or sources, resolve open questions,
or change the recommendation. If the lead is wrong, leave it wrong.

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

1. Identify exactly one entry with `wait_name` `research.{@1}.final` whose label has the
   form `research:<YYYYMM>/<name>/<name>__final.md`; otherwise stop and report the
   missing or ambiguous input. Open the research repo with `/sase_repo` and read it with
   `sase artifact read`. Take `<YYYYMM>/<name>/` from the label, never from the date. Do
   not read any chat transcript. Never modify `<name>__final.md` or the drafts beside it.
2. Before editing, inventory everything that must survive: every finding,
   recommendation, caveat, open question, confidence marker, number, date, version,
   code block, table, and link.
3. Restructure: copy the lead's frontmatter (set `updated_time` to today), one `#` title,
   then the bottom line. Organize the body under `##`/`###` sections that follow the
   reader's questions, merging duplicated passages. Do not number headings (the PDF
   renderer numbers them). Do not add a table of contents or a block of jump links.
   Keep the lead's wording where it works; never drop a claim, caveat, or source to
   save space.
{%- if image %}
   Embed the infographic (normally `<name>_infographic.png`, or the image listed above)
   once, with a relative link and descriptive alt text, where it best supports the text,
   usually after the bottom line. Embed only a file that exists in your checkout; if none
   exists, publish without it and say so in your final response.
{%- endif %}
4. Validate every link carried over: resolve relative links from `<YYYYMM>/<name>/`;
   request external URLs with `curl -fsSL -o /dev/null --max-time 20 <url>`; verify
   repository-file links through a `/sase_repo` checkout. Repair only when the correct
   target is certain (redirect, moved file, obvious typo, renamed heading). Treat 401,
   403, 429, and timeouts as unverified and keep those links. For an unrepairable link,
   keep its text, drop the dead URL, and list it in your final response. Never search
   for replacement sources.
5. Add in-document links inline and sparingly: from summary points to their evidence and
   from "see above/below" phrases or mentions of named options. Every heading you link to
   must start with a letter and contain only letters, digits, spaces, and hyphens, and
   must be unique; its anchor is the lowercased heading with spaces as hyphens. When
   `pandoc` is available, confirm anchors with `pandoc <file> -t html`.
6. Check the draft against the step 2 inventory and restore anything missing or changed.
   Every URL in `<name>__final.md` must appear unless you listed it as unrepairable.
7. Write `<YYYYMM>/<name>/<name>.md` without overwrite; on collision, stop and report it.
8. Register it: `sase artifact create -p "<absolute-report-path>" -l "research:<repo-relative-report-path>"`
   (no `--move`). If registration fails, report that; do not claim full completion.

Final layout:

{{ "```text\n" ~ linker_layout_body ~ "\n```" }}
````

Two authoring gotchas from cld's prototype:

- **Keep `%{` and `#anchor` examples inside inline code.** A bare `-w '%{http_code}'`
  opens an alternation and fans the swarm out, which is why the prompt uses `curl -f`.
  A bare `#bottom-line` triggers an unknown-xprompt warning.
- **Keep the `{% raw %}` wrappers.** Without them, the swarm-level render consumes the
  runtime `wait.artifacts` loops.

**Optional provenance.** cdx suggested that, before step 8, the linker run:

```text
sase artifact link add research:<YYYYMM>/<name>/<name>.md derives-from research:<YYYYMM>/<name>/<name>__final.md "editorial publication of the lead report"
```

That records lineage in the link graph now, because the automatic research-lineage
deriver cannot ([follow-ups](#follow-ups-outside-this-change)). The CLI syntax is valid.
Adopt it only if you want the edge before the deriver is fixed.

### Hook, config, and docs

- **`provider.py`**: no behavior change. Make the rename and comment updates from
  [Keep final out of the agent veto](#keep-final-out-of-the-agent-veto).
- **`research_image.md`**: apply the stem-stripping and no-overwrite rule from
  [Name the infographic after the topic](#name-the-infographic-after-the-topic).
- **`default_config.yml`**: change "the optional critique agent" to "the optional linker
  agent" in the `researchers` bucket description. Keep the `@image` alias. The user's
  effective config may override this description from another layer, so check it.
- **Docs**: update `README.md` (replace the `__critique.md` sentence with `__final.md`),
  `docs/xprompts.md`, `docs/configuration.md`, `AGENTS.md`, and the changelog. The
  `docs/xprompts.md` update needs:
  - the input table;
  - the segment list;
  - the publication matrix;
  - the "image implies linker" rule;
  - the image-failure recovery path.

### Tests

In `tests/test_xprompt_loading.py`, replace every critique test. Minimum coverage:

- **Inputs**: the input list and defaults include `linker=false`, `image_model=@image`,
  and `linker_model=@xlarge`, and no critique inputs.
- **Counts**: eight authored segments, with linker last. Default expansion gives 3, with
  no `__final` and no lead registration. `linker=true` gives 4. `image=true` alone gives
  5, and so does `image=true, linker=true` (no duplicate linker). Solo lead plus linker
  gives 2.
- **Waits**: the linker waits on `.final` always, and on `.image` only when `image=true`.
  It has no `#fork`. The swarm's `wait=` does not leak into it.
- **Routing**: `image_model` and `linker_model` route only to their own segments. The
  image segment no longer contains `%model:@image`.
- **Queue**: every segment keeps exactly one `%q(` with the selected runners and
  priority.
- **Runtime render**: a `wait.artifacts` render lists the `__final.md` Markdown
  artifact and, for image runs, the image artifact, and leaves no stray Jinja.

Elsewhere:

- `tests/test_filters.py` and `tests/test_provider_specs.py` get the `__final` and agent
  rows from [Keep final out of the agent veto](#keep-final-out-of-the-agent-veto).
- `tests/test_wheel_contract.py` and `.github/workflows/publish.yml` have hard-coded
  counts. `len(segments) == (4 if image else 3)` becomes `5 if image else 3`, and the
  authored `%q(1.5x, w=0.25` count stays 8. Re-check the published-floor smoke's
  default count too.

### Rollout

1. Land the change with `linker=false` by default.
2. Run the next several swarms with `linker=true` or via `rsa`. Diff each `<name>.md`
   against its `__final.md` for dropped caveats, changed numbers, and lost URLs. Check
   the anchors in the PDF.
3. If fidelity holds, consider two changes:
   - Try `linker_model=@large`.
   - Flip `linker` to default `true`. Clean numbering, checked links, and cross-links
     help every report, not only reports with images.

## Follow-ups outside this change

- **`bob-cli` heading levels.** `bob highlights create` passes `--metadata title=` and
  also keeps the body H1, so every PDF renders "1 Title / 1.1 … / 1.2 …". Adding
  `--shift-heading-level-by=-1` makes `##` sections render as "1, 2, …". cld verified
  both renderings. First check older reports that have several genuine H1s. The linker
  does not depend on this fix, but its clean structure only shows cleanly with it.
- **Stale lineage deriver in `sase`.** `src/sase/artifact_links/derive/_research_lineage.py`
  still recognizes only `_SWARM_SUFFIXES = ("__a", "__b")`. It derives nothing for
  `__cdx`, `__cld`, `__grk`, `__mus`, `__gem`, or the new `__final`. The research
  README's layout text and the `#research` xprompt's example label also still cite
  `__a`. This predates the request and is independent of it. It is already tracked as
  task bead `sase-15r`. I added a +1 noting that its fix should treat `__final.md` as
  the published report's `derives-from` source, not as a sibling draft.
- **Deterministic checker (later).** A small plugin script could check:
  - anchors against pandoc identifiers;
  - external URLs;
  - URL-set parity between `__final.md` and `<name>.md`.

  The linker would call it instead of following prose instructions. This is the hybrid
  cdx recommends: LLM judgment for structure, mechanical checks for validity.
- **Lead hygiene in non-linker mode (optional).** Telling the lead to use unnumbered
  headings would improve every default PDF. It gives up the byte-identical default
  render, so do it deliberately.
- **Standalone `#research/link` (optional).** Extracting the linker body into a reusable
  xprompt that takes a `__final.md` reference would allow re-publishing reports and
  recovering from a failed image agent. Only do this if those needs actually come up.

## Resolved disagreements between reports

| Question | Positions | Resolution |
| --- | --- | --- |
| Add `final` to the hook's suffix tuple? | All five: no | Confirmed in `provider.py`: the tuple feeds only `agent_name_globs`. |
| Does the lead register its report today? | mus: always. cld and grk: only with critique | Only with critique (`research_swarm.md:287–324`). |
| Linker model | cdx, grk, gem: `linker_model=@xlarge`. cld: `@large`. mus: reuse `lead_model` | Separate input, default `@xlarge` at launch, and try `@large` after the rollout. |
| Infographic name | Four reports: strip `__final`. mus: accept `__final_infographic.png` | Strip it, generically, in `#research/image`. |
| Image failure | cdx: fail soft. cld and grk: the linker parks | The linker parks: waits release only on `completed`. Fail soft only when the image agent completes without an image, and document the recovery. |
| Stale `critique=true` after removal | grk: errors. mus: unsure | Silently ignored (`input_binding.py`). Verified with `sase xprompt expand`. |
| Embedded infographics today | gem: "essentially none". cld: 5 of 231 | 0 of 228 with Markdown image syntax, from a direct corpus check. |
| Name `linker` | cdx, cld, grk, mus: `publisher`/`editor`/`polish` would be clearer | Keep `linker` as requested. mus's point stands: it collides with SASE's artifact-link vocabulary. Renaming now is a one-token change and costs little. |

## Open questions

- **Name.** Keep `linker`, or rename to `publisher` before the input becomes habit? I
  lean slightly toward `publisher`, but I would not block on it.
- **Default.** Should `linker` default to `true` after the trial? Decide from the rollout
  diffs.
- **Model tier.** Does `@large` preserve fidelity on the longest reports, or is
  `@xlarge` worth its cost?
- **Cross-file links.** Should sibling-file links be rewritten as absolute GitHub URLs
  so they work in the PDF? I lean no.
