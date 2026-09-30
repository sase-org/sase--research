# Research-swarm `linker` agent: implementation research (`mus`)

Research question: how best to add a `linker` agent to the `#research_swarm`
xprompt swarm (new `linker=<true|false>` input defaulting to `false`, run when
`linker=true` OR `image=true`; lead uses a `__final` suffix when the linker will
run; linker rewrites the lead's report into the hook-consumed file with
unnumbered sections, embedded image, validated plus local links, and no fresh
research), while removing the unused `critique` agent and adding an `image_model`
input. This report critiques the plan, proposes adjustments, and ends with a
recommended solution.

All claims about current behavior below were verified against the installed
` sase-research-artifacts` plugin source
(`src/sase_research_artifacts/xprompts/research_swarm.md`,
`src/sase_research_artifacts/provider.py`,
`src/sase_research_artifacts/default_config.yml`) and its tests
(`tests/test_filters.py`, `tests/test_provider_specs.py`).

## How the swarm works today

- `research_swarm.md` declares inputs: `prompt`, `wait`, `priority`, `runners`,
  five researcher toggles (`codex`/`claude` default true; `grok`/`muse`/`gemini`
  default false) plus five per-researcher `*_model` words, `lead_model` (default
  `@xlarge`), `image` (bool, default false), `critique` (bool, default false),
  and `critique_model` (default `@xlarge`).
- Each enabled researcher (`research.<N>.<short>`) writes `<stem>__<suffix>.md`
  via `#research(suffix=<short>)` and is firewalled from its peers.
- The lead (`research.<N>.final`) waits on every researcher, moves drafts into
  `<month>/<name>/`, writes the consolidated `<name>/<name>.md` (stem equals
  parent directory, no suffix), and registers it with `sase artifact create`
  (no `--move`).
- The image agent (`research.<N>.image`, model `@image` fallback chain
  `codex/gpt-5.6-sol@xhigh | grok/grok-4.6@xhigh | agy/gemini-3.8-flash-high`)
  waits on final, `#fork`s the lead, and `#research/image` writes
  `<source-stem>_infographic.png` beside the source file.
- The critique agent waits on final, artifact-reads the lead report (never chat
  transcripts), cross-checks researcher drafts for synthesis fidelity, and writes
  `<name>__critique.md` plus its own artifact registration.
- `provider.py` splits filtering two ways on purpose: the `research` ref
  provider inventory **keeps** `__<suffix>` drafts (citing a draft is
  legitimate); the `research-highlights` file hook **excludes** them, via path
  globs `!20*/*__*.md` and `!20*/*/*__*.md` plus `agent_name_globs`
  `!research.*.{cdx,cld,grk,mus,gem}` (generated from
  `_SWARM_RESEARCHER_SUFFIXES`). The hook fires only on `ADD` from
  `commit`/`sdd`/`finalizer` producers, so the lead's `<name>.md` (written by
  `research.<N>.final`, which is deliberately *not* vetoed) produces the
  Highlights PDF, while drafts and the critique-adjacent drafts do not.
  (`test_filters.py` pins all of this.)

## Is the plan a good idea

Yes, with adjustments. The plan's core insight is sound: today the
machine-polished artifact (Highlights PDF source) is whatever raw markdown the
lead happened to write, and the lead's format discipline varies by model. A
dedicated last-mile agent that normalizes structure, repairs links, and embeds
the infographic converts an uneven draft into a reliably publishable document,
and coupling it to `image=true` is correct — an unembedded
`<name>_infographic.png` sitting beside the report is the current behavior's
most visible wart. Removing an unused agent to pay for the added complexity is
also the right budget instinct: every swarm segment is prompt surface every
future maintainer must hold in their head.

The main risk is different from what the plan assumes. The plan treats the
linker as pure polish ("NOT attempt to do its own research"), but a rewrite
agent with a link-validity mandate will inevitably *change claims*: fixing a
"broken" link by swapping in a different source, smoothing over a lead hedging
statement, or "correcting" a number while reformatting. That is silent
re-research without the critique agent's adversarial discipline — and the plan
simultaneously deletes the critique agent, the only component that re-verified
load-bearing claims against primary sources. So the swarm trades its only
checker for a rewriter that is instructed not to check. For a user who never
runs critique, the practical loss is small, but the linker prompt must be
written so that unfixable problems are *flagged in place*, never quietly
repaired (see adjustments).

A secondary concern: `image=true` silently implying a full linker rewrite will
surprise users who only wanted a PNG. That is acceptable if documented loudly
in the `image` input description, since embedding genuinely requires
rewriting the file — but it should be a conscious, documented coupling, not a
hidden side effect.

## Adjustments to the requirements

### Do not add `final` to the hook's researcher-suffix list

The plan says the `__final` suffix "should be added to the list of suffices
the corresponding file hook uses." Implemented literally against
`_SWARM_RESEARCHER_SUFFIXES = ("cdx", "cld", "grk", "mus", "gem")`, this would
add `!research.*.final` to `agent_name_globs` — which vetoes the lead agent
entirely and **breaks Highlights generation on the default path**, where the
lead's `<name>.md` is written by `research.<N>.final` and must fire the hook.
`final` is not a researcher suffix and must never enter that tuple.

No hook change is strictly needed for correctness: the existing path globs
`!20*/*__*.md` and `!20*/*/*__*.md` already exclude *every* `__*`-suffixed file
at both depths, so `<name>__final.md` is hook-invisible wherever the lead puts
it, while the linker's suffix-free `<name>.md` remains hook-visible. I
recommend relying on that (plus a regression test pinning `__final` at both
depths) rather than adding a redundant `!20*/*/*__final.md` glob — or, if the
team wants the intent self-documenting, add the explicit glob as documentation
with a comment noting the redundancy. Either way, keep `agent_name_globs`
researcher-only, and keep the linker's agent id (`research.<N>.linker`)
un-vetoed so its `<name>.md` fires the hook.

### Give the linker an explicit wait on the image agent, not just the lead

`linker = linker_flag OR image` controls *whether* it runs, but the DAG must
also order it: linker `%wait`s on `research.<N>.final` always, and on
`research.<N>.image` when `image=true`, otherwise it will artifact-read a lead
report whose PNG does not exist yet and either stall or ship without the embed.
The template already conditions segments on inputs (`%if(should_run=...)`), so
this is a conditional second `%wait:` token, cheap to add.

### Scope "ensure all links are valid" down to what a rewriter can honestly do

"Ensure all referenced links are valid" read literally is the critique agent's
job (verify each cited source says what the report claims). A no-fresh-research
linker cannot do that without violating its own charter. Split the mandate:

- External URLs: check well-formedness and reachability (HTTP 200-class or
  known-good redirect); fix unambiguous mechanical breakage (moved pages with
  clear successors, markdown syntax errors); **flag anything semantic in place**
  (`> Link note: <url> returned 404; lead's claim in this section is unverified
  — needs a researcher pass`) rather than substituting sources.
- Internal navigation: this is the linker's real value-add — repair or add
  `#anchor` links to match the rewritten headings, using GitHub slug rules,
  and verify every anchor resolves. No table of contents, per the plan.

### Settle the infographic filename wart deliberately

`#research/image` writes `<source-stem>_infographic.png`. When the lead writes
`<name>__final.md`, the image agent (forking final) will derive
`<name>__final_infographic.png` — an ugly but functional name. Options: (a)
accept it and have the linker embed it as-is (simplest, no contract change);
(b) instruct the linker to rename it to `<name>_infographic.png` and embed the
clean name (one `mv`, but the image agent's contract and any fork-context
references must be checked). I recommend (a): the PNG is a build artifact next
to a `__final` intermediate, and renaming adds a failure mode to save
aesthetics on a filename users rarely type.

### `image_model` should default to `@image`

The `@image` alias (fallback chain across codex/grok/agy) is the current,
working behavior. `image_model: word, default: "@image"` preserves it exactly
while allowing explicit override (e.g. pinning a cheaper or higher-quality
generator). Do not default it to a single model — that would silently narrow
today's fallback chain. Note the `agy` effort-suffix restriction documented on
`gemini_model` does not apply here beyond what the alias already handles.

### Consider the name `linker` a second time

"Linker" collides with two nearby concepts: compiler linkers, and sase's own
*artifact-link* domain (the same plugin family deals in artifact references and
link tables daily). A future `grep linker` will be noisy. `polish`, `refine`,
or `finalize` describe the job better (`research.<N>.polish` reads cleanly
against `.final`). If the team keeps `linker`, do so knowingly and note the
collision in the agent's description string so searchers can disambiguate. This
report keeps the requested name.

### Treat critique removal as a breaking change, however small

`critique` defaults to false, so deletion costs dormant users nothing at
runtime — but any saved prompt, alias, or script passing `critique=true` will
hit unknown-input handling (verify whether that errors or warns before
landing). Also update the `researchers` bucket description in
`default_config.yml` ("the optional critique agent" is named there),
`docs/xprompts.md` / `docs/configuration.md`, and the swarm layout diagrams
(`critique_layout_body` gains a linker variant; the base layout needs a
`__final` + linker-final branch). Deleting the critique segment while its tests
or docs still reference it will fail CI.

## Recommended solution

1. **Inputs** (`research_swarm.md` frontmatter): add `linker: bool, default
   false` ("Rewrite the lead's report into the publishable file; implied by
   `image`") and `image_model: word, default "@image"`; delete `critique` and
   `critique_model`; extend the `image` description to state it implies the
   linker rewrite and embedding.
2. **Lead branch**: compute `linker_will_run = linker or image`. When true,
   instruct the lead to write `<name>__final.md` (same directory rules,
   collision behavior, and frontmatter conventions as today) and to register it
   as a durable snapshot (the linker discovers it through `wait.artifacts`
   exactly as critique discovery works today: match `wait_name`
   `research.<N>.final` plus label form
   `research:<YYYYMM>/<name>/<name>__final.md`). When false, the lead path is
   byte-for-byte today's behavior, including writing and registering
   `<name>.md`.
3. **Linker segment** (replaces the critique segment position): id `linker` in
   `clan=research.<N>`, model `lead_model` (same consolidation-tier reasoning;
   add a `linker_model` input only if a use case appears — YAGNI otherwise).
   Waits: final always, plus image when `image=true`. No `#fork` (artifact-read
   the `__final` report; forks drag in framing the linker must not inherit).
   Prompt orders the job: (a) read `__final` via `sase artifact read`; (b)
   rewrite preserving meaning with zero fresh research — same claims, same
   numbers, same hedging; (c) unnumbered `##` sections, no TOC; (d) repair/add
   `#anchor` jump links per GitHub slug rules, verifying each resolves; (e)
   check external URLs for reachability, fix only mechanical breakage, flag the
   rest inline; (f) if `image=true`, embed the generated PNG at the most
   topical section with a caption; (g) write suffix-free `<name>.md` in the
   lead's directory without overwrite (collision → stop and report, mirroring
   critique step 6); (h) register with `sase artifact create` (no `--move`).
   Explicit negative instructions: do not re-research, do not substitute
   sources, do not change conclusions, do not add a TOC, do not touch the
   `__final` file.
4. **Image segment**: replace `%model:@image` with `%m:{{ image_model }}`.
   Behavior otherwise unchanged; document the `<name>__final_infographic.png`
   naming consequence in the segment comment.
5. **File hook** (`provider.py`): change nothing in `agent_name_globs`
   semantics (researcher-only veto stays; `linker` and `final` stay fireable).
   Optionally add an explicit `!20*/*/*__final.md` glob with a redundancy
   comment. Add regression tests: `__final` excluded at both depths via path
   globs; linker-written `<name>.md` allowed; `research.<N>.linker` passes the
   agent veto while all five researchers are still vetoed; `final` still passes
   the veto (guards the breaking-change footgun above).
6. **Docs/config/tests**: update `default_config.yml` bucket text,
   `docs/xprompts.md`, `docs/configuration.md`, layout-diagram branches
   (linker layout mirrors the critique layout with `__final` + final `<name>.md`
   instead of `__critique.md`), and delete or rewrite critique-specific tests.
   Pre-landing, verify unknown-input handling for stale `critique=true`
   callers.

Landing order: template inputs + lead branch + linker segment + image model
swap first (all in `research_swarm.md`, one reviewable diff); hook tests
second (they should pass unchanged, proving the no-hook-change claim);
docs/config last. The highest-risk item is prompt leakage between lead and
linker roles (linker "improving" claims), so the first live trial should be a
past swarm re-run whose `<name>.md` diff can be eyeballed for semantic drift.
