---
create_time: 2026-09-30 12:00:00
updated_time: 2026-09-30 12:00:00
status: review
tags:
  - research-swarm
  - xprompts
  - file-hooks
  - sase-research-artifacts
---

# Adding a linker agent to `#research_swarm`

**Question.** How should `#research_swarm` grow a publication/linker agent, drop the unused critique agent, and let the image agent's model be set explicitly?

**Bottom line.** Implement the request in `sase-research-artifacts`, not in host sase. Keep `linker` defaulting to false. Run the linker when `linker or image`. When it will run, the lead writes `<name>__final.md` and registers it; the linker writes the unsuffixed `<name>.md` that `research-highlights` already consumes. Do **not** add `final` to the hook's `agent_name_globs` — that list vetoes *agents*, and vetoing `research.*.final` would stop Highlights on the default (no-linker) path. The filename glob `!20*/*/*__*.md` already ignores `__final.md`. Remove critique entirely. Add `image_model` (default `@image`) and, as a justified extra, `linker_model` (default `@xlarge`). Have the linker wait on the image agent when `image=true`, and name the PNG `<name>_infographic.png` so it does not inherit the `__final` stem.

This is a good idea. The Highlights hook is `ops: [ADD]` only, so a later polish or image embed cannot be the file the hook sees unless the unsuffixed markdown is created *after* the image exists. A dedicated publication agent is the right layer for that. I would not fold linking into the lead, the image agent, or a host file-hook change.

## Current pipeline

`#research_swarm` lives in the `sase-research-artifacts` plugin (`src/sase_research_artifacts/xprompts/research_swarm.md`). Host sase no longer ships it as a package default. Live discovery is plugin-backed: `~/sase/xprompts/` has no override.

Default dispatch is three agents (codex + claude + lead). Authored segments today are eight: five gated researchers, the unconditional lead, opt-in image, opt-in critique.

```text
researchers ──► research.N.final ──► research.N.image      (if image=true; forks lead)
                                 └──► research.N.critique  (if critique=true; no fork)
```

Each researcher writes `<stem>__<short>.md` via `#research(suffix=…)` and registers `research:<repo-relative-path>`. The lead waits on surviving researchers, reads those registrations through a raw-protected `wait.artifacts` loop, moves drafts into `<YYYYMM>/<name>/`, and writes the unsuffixed `<name>/<name>.md`. That unsuffixed file is the Highlights target.

The lead registers its own report **only** when `critique=true`, so the critic can find it the same way. Image does not use `wait.artifacts`. It `%wait`s on the lead, `#fork`s the lead, and expands `#research/image`, which says: illustrate *this* markdown file and write `<source-stem>_infographic.png` beside it.

`research-highlights` (plugin `provider.py`) is the hook that matters:

| Filter | Value | Effect |
| --- | --- | --- |
| sidecars | `research` | research sidecar only |
| producers | `commit`, `sdd`, `finalizer` | committed files, not `sase artifact create` copies |
| ops | `ADD` | first appearance only; a later `MODIFY` is silent |
| path_globs | `20*/**/*.md` plus `!20*/*__*.md` and `!20*/*/*__*.md` | any `__suffix` at depth 1 or 2 is ignored |
| agent_name_globs | `!research.*.{cdx,cld,grk,mus,gem}` | researcher agents are vetoed; `.final`, `.image`, `.critique` are not |

The path veto is a glob, not a suffix tuple. The suffix tuple `_SWARM_RESEARCHER_SUFFIXES` feeds **only** `agent_name_globs`. Tests confirm `research.26.final` and `research.26.critique` *match* the hook; their `__*` files are dropped by the path glob instead. `__critique.md` is ignored for that reason, not because `critique` is in the agent veto list.

Bryan's `rsa` snippet already launches `#research_swarm(gemini=true,grok=true,muse=true,image=true)`. `rs` does not opt into image. User config never passes `critique=true`.

## Is the plan a good idea?

Yes. Three facts in the current design make a publication agent the right next piece, and one fact makes dropping critique cheap.

The hook fires on `ADD` of an unsuffixed markdown file. The lead writes that file as soon as synthesis finishes. The image agent starts *after* that write. Highlights therefore renders a report that cannot yet contain the infographic. Changing the hook to `MODIFY` would double-fire (lead ADD, then a later edit) and still would not restructure the prose.

A later in-place edit of `<name>.md` cannot be the Highlights event. The unsuffixed file has to be created once, at publication time. That is exactly "the lead writes a suffixed archival copy; a later agent writes the hook file."

The lead's job is already large: identify drafts, research gaps, pick a stem, move files, merge perspectives. Asking it to also wait for an image it has not launched, then rewrite itself, collides with the single-turn agent contract. A clan member that waits on the lead (and on image when needed) is the existing pattern (critique, image).

Critique is real code with real tests, and the handoff it pioneered (`wait.artifacts` + register-the-lead) is the right handoff for a linker. Bryan does not launch it. Removing it deletes a segment, two inputs, a conditional registration path, and a pile of tests, which is the room the linker needs.

`image_model` is an obvious gap. Every other role already has a `*_model` input. The image segment is hardcoded `%model:@image`.

Caveats, not blockers:

- An extra agent on the `rsa` path (today 7 agents with image; tomorrow 8). Default `rs` stays at 3.
- Dual-mode lead output (`<name>.md` vs `<name>__final.md`) is the main template hazard. It must be driven by one Jinja flag, not copied conditionals.
- If the linker waits on image and image fails, `%wait` never releases (`done.json` outcome must be `"completed"`). Today an image failure still leaves a Highlights file. After this change, a failed image with `image=true` leaves only `__final.md`, which the hook ignores. That is a real behavior change; see adjustments.
- A linker told "do not research" can still rewrite meaning. The prompt has to treat fidelity as the success criterion.

## Adjustments to the request

These change the spec. The rest of the recommendation assumes them.

### Do not put `final` on `agent_name_globs`

The request says to add `__final` to "the list of suffixes the corresponding file hook uses to ignore certain research files." There are two lists, and they mean different things.

- **Path globs** already ignore every `__*` markdown file at the two depths the swarm writes. `<name>__final.md` is already hook-invisible. Add a test for that path (`202608/widgets/widgets__final.md` in `test_filters.py`) and a comment in `provider.py`. Do not replace the `*__*.md` glob with an explicit suffix enum; that enum would rot every time a role is added (it already omitted `final` and `critique` as *filename* suffixes because the glob covered them).
- **`agent_name_globs`** vetoes the *producing agent*. The lead's id is `research.N.final`. On the default path the lead is the agent that ADDs `<name>.md`. Vetoing `research.*.final` would stop Highlights for `rs` and every other no-linker dispatch.

When the linker runs, ignore `__final.md` via the existing path glob; let `research.N.linker` ADD `<name>.md` and match the hook. Do not veto `.linker`. Do not veto `.final` either, because the no-linker path still needs it.

### One Jinja flag, `run_linker = linker or image`

Use that flag for: whether the linker segment is authored as `should_run`, whether the lead writes `__final.md`, whether the lead registers, and whether lead/linker layout text mentions the archival file. Do not sprinkle `linker or image` through the lead body by hand.

### Do not implement the linker with `#research`

`#research` always writes under `$(sase repo path research --ensure)/$(date +%Y%m)/`. Critique already refuses that for month-boundary safety: it takes `<YYYYMM>/<name>/` from the lead's registered label. The linker must do the same. `#research(report_target=…)` also frames the job as "write this research," which fights "do not research."

Inline the linker prompt in the swarm, the way critique is inlined. A standalone `#research/link` is a reasonable follow-up, not part of this change.

### Name the infographic `<name>_infographic.png`

`#research/image` names the file from the *source stem*. If the source is `<name>__final.md`, the PNG becomes `<name>__final_infographic.png`. The README and existing reports use `<name>_infographic.png`.

Keep standalone `#research/image` unchanged. In the swarm image segment, after the fork, say: read the lead's `__final.md` (from `wait.artifacts` once the lead registers), write `<name>_infographic.png` in that directory. The linker then embeds that exact relative path.

### Linker waits on image when `image=true`

Embedding requires the PNG to exist. Same-swarm `%wait` only completes on success, so a failed image parks the linker and no hook file appears.

That coupling is still the right default: launching the linker in parallel with image races the PNG, and a time-floor wait is worse. Mitigations:

- Expand the image segment so it has an explicit source file and output path (fewer "could not find the report" failures).
- If the PNG is missing even after a successful image wait, the linker publishes without it and says so in the file; it does not stop.
- Recovery is a second `#research_swarm(linker=true, image=false)` against an already-written `__final.md` is *not* defined, so do not rely on it. Recovery is: fix/relaunch the image agent so the wait can complete, or write `<name>.md` by hand from `__final.md`. Mention this in plugin docs.

Do not `#fork` the lead (or the image agent) into the linker. Fork injects the parent's conversation. Critique correctly skipped that so the critic would not inherit the lead's framing. The linker must not inherit it either: its source of truth is the registered `__final.md` bytes plus, when present, the PNG on disk.

### Add `linker_model`, default `@xlarge`

Justified extra, same shape as `critique_model` / `lead_model`. The linker is editorial; callers who want a cheaper pass can set it. Omit this only if the extra input is unwelcome — the swarm already has many inputs, but every launched role except image already has a model knob, and this change adds `image_model` anyway.

### Lead still writes a complete report

Do not tell the lead "a linker will clean this up, so notes are fine." `__final.md` is the archival synthesis and the linker's only source. If the lead gets sloppy, the linker is specified not to repair substance. The lead prompt change is the output *filename* and the registration step, not a lowering of quality.

### Remove critique completely

Do not leave `critique` / `critique_model` as no-ops. Unknown named xprompt inputs fail at expansion. Call it a breaking change in the plugin changelog: invocations that passed `critique=true` will error until those args are dropped. Bryan's snippets never pass them.

Keep the path glob that already hides leftover `__critique.md` files from old runs. No need to mention critique in `agent_name_globs`.

### Optional host follow-up, not this change

`sase.artifact_links.derive._research_lineage` still treats only `__a` / `__b` siblings as consolidation sources. It never learned `__cdx` / `__cld` / `__grk` / `__mus` / `__gem`, and it will not learn `__final` unless host sase is updated. The published unsuffixed file remains the lineage "lead" document, which is what we want. Updating that tuple is a separate, already-stale host fix.

## Alternatives considered

**Lead does the linking in the same turn.** Impossible without launching the image first. The lead cannot wait on a child it has not started. A session child of the lead (`%id(linker, session=…)`) still needs a second agent; putting it in the clan is simpler and matches image/critique.

**Image agent writes the hook file.** Mixes illustration with editing. Leaves `linker=true, image=false` with no publisher. Rejected.

**Always run the linker.** Simpler mental model (lead always writes `__final.md`, hook always comes from `.linker`, then `research.*.final` *could* be vetoed). Costs an extra agent on every `rs` dispatch. Rejected; keep the dual-mode lead.

**Change the hook to `MODIFY` or debounce until the clan is quiet.** Host file-hook work, easy to double-render, still does not restructure prose or validate links. Rejected.

**YAML workflow.** The markdown swarm already has `%if(should_run=…)`, `%wait`, `#fork`, and Jinja. A workflow adds no control flow this job needs.

**Name the agent `publisher`.** Clearer versus `sase artifact link`, and it matches "creates the hook file." Keep `linker` as requested; the job is links + structure + optional image embed. If the name feels wrong in review, renaming the id is a one-token change.

## Recommended design

### Inputs

Remove `critique` and `critique_model`.

Add:

| Name | Type | Default | Role |
| --- | --- | --- | --- |
| `linker` | bool | `false` | Opt into the publisher when there is no image |
| `image_model` | word | `@image` | Replaces hardcoded `%model:@image` |
| `linker_model` | word | `@xlarge` | Model for `research.N.linker` |

`image` stays bool default false. Compute `run_linker = linker or image` once at the top of the template.

### Authored segments (still eight)

Five researchers (unchanged), lead (unchanged id `.final`), image, linker. Linker last so its `%wait:research.{@1}.image` points at an earlier segment.

Default expansion remains 3 agents. `linker=true` → 4. `image=true` → 5 (image *and* linker). `image=true, linker=true` → still 5.

### Lead, when `run_linker`

Same draft identification, research, stem pick, and move as today. Differences:

- Write `<name>/<name>__final.md`, not `<name>/<name>.md`.
- Register that file (`sase artifact create` without `--move`) so image and linker can see it in `wait.artifacts`.
- Lead layout ends at `__final.md`. It does not create the hook file.

When `not run_linker`, keep today's unsuffixed write and skip lead registration.

### Image, when `image=true`

Keep `%wait:research.{@1}.final`, `#fork:research.{@1}.final`, same `%q` / priority / runners.

Change `%model:@image` to `%m:{{ image_model }}`.

Add a short body (fork + `#research/image` is not enough once the source is `__final.md`):

- From `wait.artifacts`, take the unique `research.{@1}.final` markdown whose label is `research:<YYYYMM>/<name>/<name>__final.md`.
- Generate `<name>_infographic.png` in that directory (topic stem, not `__final` stem).
- Do not write markdown. Do not touch `__final.md`.

### Linker, when `run_linker`

```text
%if(should_run={{ run_linker }}) %id(linker, clan=research.{@1}) %m:{{ linker_model }}
%wait:research.{@1}.final
{% if image %}%wait:research.{@1}.image {% endif %}
%q(...)
```

No `#fork`. Same queue options as every other member. Ignore the swarm's `wait=` input (researchers only, as today).

Handoff, copied from critique and retargeted:

1. Identify the lead's `__final.md` from `wait.artifacts` (`wait_name` is `research.{@1}.final`, label `research:<YYYYMM>/<name>/<name>__final.md`, stem is parent name plus `__final`). Stop if that is not unique.
2. Open the research repo; `sase artifact read` that ref. Do not read transcripts. Do not modify `__final.md` or researcher drafts.
3. If `image=true`, look beside it for `<name>_infographic.png`. Embed with a relative image tag after the title / bottom line if the file exists; if it does not, publish anyway and say the figure is missing.
4. Write `<YYYYMM>/<name>/<name>.md` using the directory from the lead label, never `$(date +%Y%m)`. Fail visibly on collision; do not pick a new stem (the stem is already chosen).
5. Register the new file as `research:<YYYYMM>/<name>/<name>.md`.

Editorial rules for that file:

- Same meaning and intent as `__final.md`. No new investigation, no new recommendations, no "while I was here" findings. If the lead is wrong, leave it wrong and keep the wording honest; this agent is not a critic.
- Unnumbered markdown headings (`## Decision`, not `## 1. Decision`). Numbered headings in current lead reports (`agents_dynamic_tabs.md` and peers) make GFM anchors brittle and fight in-document links.
- Reorganize when the lead's order hides the answer; keep the lead's information architecture when it is already clean. A stable default shape, omitting empty parts: title, bottom line, context, findings, options, recommendation, open questions, sources.
- Check links the lead already has: relative paths in the research repo, `research:` refs, in-document heading targets. External HTTP: probe when cheap, record failures, do not block publish on a dead outbound URL.
- Turn prose cross-references ("see §2", "see Recommendation") into markdown heading links. Do not add a table of contents. Do not link every heading, only places the lead already points.
- Mirror lead frontmatter when present (`create_time`, `status`, `tags`); set `updated_time` to now. `status: final` is appropriate for the hook file if the lead had no status.

### File hook

No `agent_name_globs` change. Add a path-glob test that `__final.md` is filtered and that unsuffixed `<name>.md` is still allowed. Update the README sentence that lists ignored drafts so it names `__final.md` next to researcher suffixes. The researchers-bucket blurb in `default_config.yml` should drop critique and mention the optional linker / infographic roles.

### Docs and changelog

Plugin `docs/xprompts.md`, `docs/configuration.md`, `README.md`, `AGENTS.md`. Breaking: `critique` / `critique_model` removed. Feature: `linker`, `image_model`, `linker_model`, `__final` archival file, hook file owned by `.linker` when `run_linker`.

Host sase docs barely mention the plugin swarm (the packaged defaults were removed). No host code change required.

### Tests (plugin `tests/test_xprompt_loading.py` and `tests/test_filters.py`)

Replace every critique assertion. Minimum new coverage:

- Input list and defaults, including `linker=false`, `image_model=@image`, `linker_model=@xlarge`.
- Authored segment count still 8; last segment is linker, not critique.
- Default expansion: 3 agents, no `__final`, no lead `sase artifact create`.
- `linker=true`: 4 agents; lead mentions `__final` and registers; linker waits on `.final` only; no `#fork`; `wait.artifacts` loop present.
- `image=true`: 5 agents; linker waits on `.final` *and* `.image`; image uses `%m:@image` by default and `%m:{{ image_model }}` in the authored template; image body names `<name>_infographic.png`.
- `image_model` / `linker_model` route only to those segments.
- `run_linker` is true when only `image=true` (`linker` omitted).
- Queue / priority / runners render on the linker.
- Swarm `wait=` does not appear on the linker.
- End-to-end `wait.artifacts` render for the linker, mirroring the critique test (lead registered as `research:202609/topic/topic__final.md`).
- `__final.md` is path-filtered; `research.26.linker` would match the hook for an unsuffixed ADD (add a parametrized case next to the existing `.final` / `.critique` rows; drop the `.critique` row).

## Implementation sketch

All edits are in `sase-research-artifacts`:

1. `research_swarm.md` — inputs, `run_linker`, lead branches, image body + `image_model`, replace critique segment with linker segment.
2. `provider.py` — comments + filter tests for `__final.md` only.
3. `default_config.yml` — researchers bucket copy.
4. Docs + CHANGELOG breaking note.
5. Rewrite `test_xprompt_loading.py` / `test_filters.py` as above.

No change to `#research` or `#research/image` themselves. No change to Bryan's `rs` / `rsa` snippets: `rsa` already sets `image=true`, so it will pick up the linker automatically.

## Recommended solution

Ship this as one plugin change, not two:

1. Delete the critique agent and its inputs.
2. Add `linker` (bool, default false), `image_model` (word, default `@image`), `linker_model` (word, default `@xlarge`).
3. `run_linker = linker or image`.
4. On that path, lead writes and registers `<name>__final.md`; linker writes and registers `<name>.md`; image, if any, writes `<name>_infographic.png` and the linker embeds it.
5. Leave `research-highlights` agent vetoes as researcher-only. Rely on the existing `__*` path glob for `__final.md`, and prove it with a test.
6. Linker prompt: fidelity, unnumbered sections, real-link checks, in-document links without a TOC, no new research, no fork.
7. Accept that `image=true` plus a failed image agent means no Highlights file until the image run succeeds. Document it.

I would not wait for a host file-hook feature, would not always-on the linker, and would not ask the lead to publish the hook file on this path.
