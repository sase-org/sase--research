# Designing a linker stage for `#research_swarm`

## Executive conclusion

Adding a linker agent is a good idea if its purpose is defined as the swarm's publication
stage, not as another researcher. It solves a real ordering problem: when an infographic
is requested, the current lead report can be committed—and therefore matched by the
`research-highlights` hook—before the image exists or is embedded. Writing the lead's
intermediate document as `__final.md`, then having a downstream linker publish the
unsuffixed Markdown, gives the hook exactly one finished document to process.

The implementation should preserve the current fast path. With both `linker=false` and
`image=false`, the lead should continue writing `<name>.md` directly and no linker should
run. With either flag true, the lead should instead write and register
`<name>__final.md`; the linker should wait for the lead and, when applicable, the image
agent, then produce `<name>.md` without doing research of its own.

I recommend the proposed change, with five adjustments:

- Add `linker_model` as well as `image_model`. Every other swarm role has an explicit
  model contract, and silently coupling the new editorial role to `lead_model` would be
  surprising.
- Do not add `final` to the existing `_SWARM_RESEARCHER_SUFFIXES` tuple. That tuple
  generates agent-name vetoes; adding it there would suppress ordinary unsuffixed reports
  written by `research.*.final` when the linker is off. The existing path glob already
  excludes every `__*.md` file, including `__final.md`; make that fact explicit in tests
  and documentation, or introduce a separate filename-only suffix collection.
- Treat external-link verification as best-effort with explicit unresolved results.
  Local files and anchors can be validated conclusively, but network failures, bot
  protection, and authentication make “ensure every external URL is valid” impossible
  to guarantee.
- Name an infographic `<name>_infographic.png`, stripping the lead-only `__final`
  suffix. This keeps the published report and its image named as one pair.
- Record the published report as deriving from the lead's `__final` report with
  `sase artifact link add`, then snapshot the published report. The current automatic
  research-lineage derivation still knows only the historical `__a`/`__b` suffixes, so
  it should not be relied on for this relationship.

## What the code does today

The active implementation is in the `sase-research-artifacts` plugin, principally
`src/sase_research_artifacts/xprompts/research_swarm.md`.

The swarm currently authors eight possible segments: five independent researchers, one
lead, one optional image agent, and one optional critique agent. The default expansion
is codex researcher, claude researcher, and lead. The image agent waits for and forks
the lead, then expands `#research/image`; the critique agent waits for the lead without
forking it.

The lead normally writes `<month>/<name>/<name>.md`. It registers that report as an
explicit artifact only when the critique option is on, because the critique agent uses
`wait.artifacts` to find it. This is a useful existing pattern for the linker: direct
wait dependencies expose non-chat artifact metadata, while report contents remain an
explicit audited `sase artifact read`.

The image agent's generated image is also available to a direct waiter through SASE's
automatic media capture. Finalization records discovered image files as artifacts of
kind `image`, including their label and source path. Consequently, the linker can wait
on both `.final` and `.image`, identify the lead Markdown and generated image by
`wait_name` plus type/path constraints, and avoid reading either predecessor's chat.

The hook implementation is in `src/sase_research_artifacts/provider.py`. Two distinct
filters matter:

- Path globs exclude `!20*/*__*.md` and `!20*/*/*__*.md`. These already exclude
  `__final.md` at both locations used by the swarm.
- `_SWARM_RESEARCHER_SUFFIXES` generates agent-name exclusions for `.cdx`, `.cld`,
  `.grk`, `.mus`, and `.gem`. This is not a filename-suffix list even though the values
  happen to match filename suffixes.

That distinction is important. Adding `"final"` to `_SWARM_RESEARCHER_SUFFIXES` would
generate `!research.*.final`. When neither image nor linker is requested, the lead is
supposed to keep writing the publishable unsuffixed `<name>.md`; an agent veto on
`.final` would prevent the hook from seeing it. The safe choices are to leave the broad
path globs in place and add an explicit `__final` regression case, or to split agent
suffixes from filename suffixes before making the latter explicit.

The helper `#research/image` currently says to write
`<source-stem>_infographic.png`. Once the source becomes `<name>__final.md`, that literal
rule would yield `<name>__final_infographic.png`. It would work, but it exposes an
internal pipeline suffix in the user-facing asset and makes later pairing less obvious.

Finally, SASE's current automatic research-lineage derivation in
`src/sase/artifact_links/derive/_research_lineage.py` is older than the plugin's
provider-named suffixes: it recognizes only `__a` and `__b`. The new final document
should therefore create its own explicit `derives-from` relationship rather than assume
that on-disk sibling discovery will infer it.

## Desired execution graph

The behavior should be defined by one derived template boolean, conceptually
`publish_via_linker = linker or image`.

| `linker` | `image` | Lead output | Downstream order | Hook target |
| --- | --- | --- | --- | --- |
| false | false | `<name>.md` | lead only | lead's `<name>.md` |
| true | false | `<name>__final.md` | lead → linker | linker's `<name>.md` |
| false | true | `<name>__final.md` | lead → image → linker | linker's `<name>.md` |
| true | true | `<name>__final.md` | lead → image → linker | linker's `<name>.md` |

This matrix preserves today's default cost and latency. It also ensures that
`image=true` implies exactly one linker rather than creating separate implicit and
explicit linker segments.

The dependency graph should be expressed directly:

```text
researchers ──> final ───────────────> linker
                    └──> image ──────> linker   (image=true only)
```

The linker does not need `#fork`. Its authoritative inputs are the files, not the
lead's reasoning transcript. Avoiding a fork reinforces the “no new research and no
silent reinterpretation” boundary. It should use `%wait` on `.final`, conditionally
use `%wait` on `.image`, and inspect only `wait.artifacts` metadata at runtime.

## Input and model contract

Remove `critique` and `critique_model`, and delete the critique segment and its layout
template. Add:

```yaml
- name: linker
  type: bool
  default: false
  description: Publish a structured, link-checked report from the lead's report.
- name: image_model
  type: word
  default: "@image"
  description: Model alias or provider model for `<clan>.image`.
- name: linker_model
  type: word
  default: "@xlarge"
  description: Model alias or provider model for `<clan>.linker`.
```

`image_model=@image` preserves existing behavior while making it overridable. The image
segment should change from `%model:@image` to `%m:{{ image_model }}`.

`linker_model` is an adjustment beyond the stated requirements, but it is preferable to
reusing `lead_model`. Synthesis and publication are different roles; callers may want a
very strong lead and a cheaper editor, or may want the linker on a provider that is
especially reliable at file editing. If minimizing the public input surface is more
important than that control, the acceptable fallback is `%m:{{ lead_model }}`—not an
implicit provider default.

The plugin's `@image` model alias should remain in `default_config.yml`. Its bucket and
documentation descriptions should replace references to the removed critique role with
the linker role. No new alias is required for the linker if `@xlarge` remains its
default.

## Lead contract when publication is deferred

When `publish_via_linker` is false, keep the lead instructions byte-for-byte as close to
the current path as practical: write `<name>.md`, do not add an unnecessary artifact
handoff, and let the hook process that file.

When `publish_via_linker` is true, alter only the publication portion of the lead's
task:

- Write `<name>__final.md` in the selected `<YYYYMM>/<name>/` directory.
- Preserve the same research and consolidation responsibilities as today. The suffix
  marks a pipeline intermediate, not lower-confidence content.
- Register exactly that report with its actual `research:` label after the write, using
  `sase artifact create` without `--move`.
- State in the displayed layout that `<name>__final.md` is the lead source and that the
  linker will create `<name>.md`.
- Do not create an empty placeholder `<name>.md`; the linker's ADD is what should
  trigger the hook.

The report-selection rule for the linker should be structural and fail closed: exactly
one Markdown artifact whose `wait_name` is `research.{@1}.final` and whose canonical
label is `research:<YYYYMM>/<name>/<name>__final.md`, with the filename matching its
parent stem. It should not guess from list order or current date.

## Image contract

When `image=true`, the image agent should continue to run after the lead and before the
linker. The current fork is useful because image generation benefits from the lead's
context, but the source file should also be selected explicitly from the lead's
registered artifact rather than inferred from conversational wording.

The generated path should be
`<YYYYMM>/<name>/<name>_infographic.png`, not
`<name>__final_infographic.png`. The image prompt should create it without overwrite and
report a collision rather than selecting an unrelated name. Automatic image capture at
agent finalization is sufficient for the linker's handoff; an explicit snapshot is not
necessary unless the workflow wants a stable label for images as a separate product
decision.

The linker should identify an image only among artifacts produced by
`research.{@1}.image`, require kind `image`, and require the expected basename. It
should verify that the corresponding file exists in its opened research checkout before
embedding the relative Markdown image reference. This prevents an unrelated image from
the image agent's working set from being selected by accident.

Image failure should be fail-soft for publication: if the image agent produces no
matching image, the linker should still create the refined report without an image but
must report that the image portion is incomplete. If there are multiple matching image
artifacts or a collision at the target path, it should stop rather than guess. This
distinguishes “image requested” from “image actually generated,” which the original
requirement currently conflates.

## Linker contract

The linker prompt should make its non-research boundary unusually explicit. Its job is
editorial transformation and validation:

- Read the selected lead report through `sase artifact read`, after opening the research
  repo through `/sase_repo`.
- Do not read researcher drafts, predecessor transcripts, or external sources in order
  to add facts. Do not change the conclusion merely because it prefers a different one.
- Preserve every material claim, recommendation, qualification, uncertainty statement,
  citation, and relevant frontmatter field. It may remove repetition and reorganize
  prose, but it must not silently strengthen or weaken the lead's position.
- Use a coherent hierarchy of unique, unnumbered Markdown headings. Do not generate a
  table of contents.
- Add useful inline cross-references to other sections—for example, a recommendation can
  link to `[#risks-and-mitigations]` through normal Markdown syntax—only where a reader
  would naturally want to jump. Do not turn every heading mention into a link.
- If an image was successfully produced, embed it once with meaningful alt text at the
  first location where it helps comprehension, normally after the summary or framing
  section.
- Write `<name>.md` in the same directory without overwrite. A collision is an error;
  the linker must not choose a second stem because the lead's directory and report
  identity are already established.
- Compare the completed file against the lead using a semantic preservation checklist
  before declaring success.

Link checking should have two tiers:

- Relative file targets and in-document heading fragments are hard requirements. Repair
  them and verify every target against the final file tree and final heading set.
- External URLs should be syntax-checked and probed with redirects enabled, preferably
  using a deterministic link checker. Retry transient failures. A conclusive invalid
  result can be repaired only when the correction is evident from the original URL or a
  redirect; the linker must not research a replacement source. Authentication failures,
  rate limits, robots policy, and timeouts should be reported as unresolved rather than
  described as valid or silently deleted.

After the file is complete, the linker should add explicit provenance before taking the
snapshot:

```text
sase artifact link add \
  research:<YYYYMM>/<name>/<name>.md \
  derives-from \
  research:<YYYYMM>/<name>/<name>__final.md \
  "editorial publication of the lead research report"
```

It should then register `<name>.md` with `sase artifact create`, using the actual path
and actual repo-relative label and no `--move`. Performing the link operation first
means the immutable explicit snapshot includes the managed lineage table.

## Hook behavior

The desired hook behavior is “ignore the lead intermediate, process the linker's
unsuffixed ADD.” The current path globs already implement that behavior. The safest
minimal change is:

- Keep the two broad `__*.md` exclusion globs.
- Update their comments and README documentation to name lead intermediates as well as
  researcher drafts.
- Add `202609/widget/widget__final.md` to the hook filter test candidates and assert that
  it is filtered.
- Assert that `research.26.final` still matches the hook, because it can publish the
  unsuffixed report when no linker runs.
- Add `research.26.linker` as an allowed agent name and prove that its unsuffixed ADD
  matches.

If an explicit suffix collection is required for readability, split the concepts:

```text
_SWARM_RESEARCHER_AGENT_SUFFIXES = ("cdx", "cld", "grk", "mus", "gem")
_HIGHLIGHTS_IGNORED_FILE_SUFFIXES = (*_SWARM_RESEARCHER_AGENT_SUFFIXES, "final")
```

Only the first collection may generate `agent_name_globs`. The second may generate
filename exclusions. Replacing the current broad globs with exact generated exclusions
would narrow existing behavior for other `__<suffix>` companion files, so that change
should be intentional rather than incidental. Keeping the broad globs is simpler and
more future-proof.

## Test and documentation impact

Most changes belong in the plugin repository.

`tests/test_xprompt_loading.py` should cover:

- The revised typed-input order and defaults, including `image_model`, `linker`, and
  preferably `linker_model`, with critique inputs absent.
- Eight authored segments still exist if critique is replaced one-for-one by linker.
- Default expansion remains three agents.
- `linker=true,image=false` expands four agents.
- `image=true` expands five agents: the two default researchers, lead, image, and
  linker. `linker=true,image=true` must still expand five, proving there is no duplicate
  linker.
- The lead writes/registers `__final.md` exactly when `linker or image` is true and
  retains direct unsuffixed behavior otherwise.
- `image_model` appears only on the image segment and `linker_model` only on the linker
  segment.
- The linker waits on `.final` in both modes and additionally waits on `.image` only
  when `image=true`. The caller's top-level `wait` argument must still gate researchers
  only.
- Every expanded segment retains exactly one weighted queue directive with the selected
  capacity and priority.
- A real artifact-context render gives the linker exactly the registered
  `__final.md` metadata and, for the image case, the direct image artifact metadata.
- Solo-lead mode (all researcher flags false) works with both linker-only and
  image-plus-linker paths.

`tests/test_filters.py` and `tests/test_provider_specs.py` should add the `__final`
fixture and preserve the `.final` agent allow-case. The source-coordination wheel test
and `.github/workflows/publish.yml` minimum-version smoke contain hard-coded queue and
expanded-segment counts; their image expectations must change from four to five. The
authored queue count can remain eight when critique is replaced by linker.

Documentation updates are required in `README.md`, `docs/xprompts.md`,
`docs/configuration.md`, `AGENTS.md`, and the model-bucket description in
`default_config.yml`. Remove critique examples and describe the publication matrix,
model inputs, `__final` intermediate, and image-implies-linker rule. `#research/image`
documentation should state the suffix-stripping output rule if adopted.

No change to the main SASE runtime is required for the basic workflow: direct waits
already expose Markdown and image artifacts. A later cleanup could modernize automatic
research-lineage derivation, but the explicit `derives-from` link makes this feature
independent of that stale helper and avoids expanding the implementation across
repositories.

## Critique of the plan

The strongest part of the proposal is not the Markdown reformatting; it is the explicit
publication barrier. It makes hook timing deterministic and gives image-enabled reports
a single canonical Markdown file. Keeping the lead intermediate also preserves useful
provenance and makes semantic drift auditable.

The weakest part is asking an LLM to “ensure” links are valid. An agent can improve
organization and choose meaningful image placement, but link validity should be tested
mechanically wherever possible. Without that distinction, the linker may confidently
claim success after a superficial read or may replace an inaccessible but valid source
with a weaker one, violating the no-research requirement.

There is also an unavoidable semantic-drift risk in rewriting a completed report. The
linker should not be described as “improving” the substance. Its prompt needs a strict
preservation checklist and explicit prohibitions against adding evidence, resolving
open questions, or changing recommendations. The lead's `__final` file must remain
available so a reader can inspect the source if needed.

The name “linker” understates that the role is also a structural editor and publisher.
“Publisher” would be more precise, but retaining `.linker` is reasonable if the user
interface is already decided. The prompt and documentation should consistently call it
the publication/linking stage so future changes do not turn it into a second lead.

Removing the unused critique agent is sensible and simplifies the workflow. It does
remove the only deliberately adversarial post-lead review, so the linker must not be
presented as a substitute for critique. If critical research later warrants review, it
should be a separate opt-in workflow rather than quietly expanding the linker's scope.

A fully deterministic postprocessor would be cheaper and safer for renaming files,
embedding a known image, and checking anchors, but it cannot reliably reorganize prose
or place cross-links semantically. The best design is therefore hybrid: use the linker
agent for editorial judgment, and require deterministic file, anchor, and URL checks as
part of its completion criteria.

## Recommended solution

Implement the linker as an opt-in publication stage in
`sase-research-artifacts`, with `image=true` forcing that stage. Replace the critique
inputs and segment with `linker`, `image_model=@image`, and preferably
`linker_model=@xlarge`. Derive one `publish_via_linker = linker or image` condition and
use it consistently in lead instructions, registration, layouts, and segment gating.

When the condition is false, preserve today's direct `<name>.md` lead path. When true,
have the lead create and register `<name>__final.md`; have the image agent, when enabled,
create `<name>_infographic.png`; then have the linker wait on the relevant agents, read
the lead artifact, preserve its meaning, organize it under unnumbered headings, add
useful local section links, validate links with honest failure categories, embed the
verified image, and create the unsuffixed `<name>.md` without overwrite. Add an explicit
`derives-from` artifact link and register the finished report.

Keep the hook's broad double-underscore path exclusions, explicitly test
`__final.md`, and do not add `.final` to the researcher agent-name veto list. Update the
plugin's expansion, artifact-handoff, hook, wheel-smoke, and documentation tests as one
coordinated change. This achieves the requested behavior with one canonical hook event,
retains the current no-linker fast path, and keeps research authority with the lead
rather than the publication agent.
