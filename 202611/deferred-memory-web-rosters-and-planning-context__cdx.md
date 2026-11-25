# Deferred memory-web rosters: smaller instructions, deliberate discovery

Researcher: **cdx** · 2026-11-25 · Independent research for the five-researcher swarm

The proposal is sound. Make roster delivery configurable for any memory web, retain a small always-visible instruction telling agents when to retrieve it, and add an audited roster view to the existing memory-read interface. Do not add a decisions-specific feature or modify `/sase_plan` to name this web.

I recommend one adjustment to the audience requirement: **planning should require roster discovery, but decisions must remain available to implementers and agents making direct design changes.** A planner should identify the applicable records for its implementer; a direct architectural change needs discovery even when no formal plan is written. Otherwise reducing context becomes a way to bypass architectural constraints.

This report proposes a design, not an implementation. No application code, memory notes, or generated instructions were changed. I did not consult the other swarm researchers' reports, transcripts, or findings.

## 1. Evidence and magnitude

I inspected the SASE workspace, opened `sase-core` and `bob-cli` through `sase repo open`, read relevant SASE decisions through audited memory reads, and checked two primary external sources. The repository snapshots were:

| Repository | Inspected commit |
| --- | --- |
| sase | `df9ce4ef55fdcb9f2582af9143e9766c4022cd9f` |
| sase-core | `71944fb4b9011135688855bcf1c4b5f6afd94636` |
| bob-cli | `e6eb52a103656add99a1a49f2f0b3d791536abc4` |

Measurements below come from the committed generated `AGENTS.md` files, extracting the Decisions subsection and its numbered roster. They are exact UTF-8 byte counts; token estimates use bytes divided by four because a tokenizer was not installed. They are not measured provider billing tokens or complete invocation-bundle sizes.

| Project | Decisions | Whole AGENTS.md | Roster alone | Share of file | Rough roster tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| sase | 31 | 20,854 B | 7,717 B | 37.0% | ~1,929 |
| bob-cli | 77 | 35,857 B | 24,501 B | 68.3% | ~6,125 |

The complete Decisions subsections, including their introduction, are 8,278 B and 25,395 B respectively. Removing the roster and adding a short retrieval instruction would eliminate almost all of the roster contribution from ordinary agents' standing instructions. The exact net saving depends on the final wording and runtime compaction.

There is an unusually strong architectural fit: `decisions:webs-render-in-their-own-section` explicitly says its always-loaded-descriptor rule should reopen when descriptors become a real token-budget problem, using a scoped opt-out rather than reviving `type:` on web descriptors. These measurements satisfy that condition. `decisions:readable-agents-md` also requires the committed files to remain the runtime projection; that favors changing both generated files and runtime bundles together. [S1, S2]

Anthropic describes the same general approach as progressive disclosure: retain useful identifiers in initial context and retrieve detail when needed. It also notes the cost of extra exploration and the need for clear retrieval instructions. This supports the direction, but does not prove that this change improves SASE task quality; that needs a local evaluation. [Effective context engineering for AI agents](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)

## 2. What exists today

### Rendering already has most of the ingredients

`MemoryWeb` has `roster: inline | list`, but no independent delivery setting. These values describe formatting: an inline keyword catalog versus a numbered list with summaries. They should continue to mean that. [S3]

The shared renderer already produces titles, slugs, summaries, ordering, and supersession markers. Descriptors contain a managed region between `<!-- sase:strands -->` and `<!-- /sase:strands -->`. `memory_web_root_plan()` renders both the full canonical descriptor and the body used in generated instructions; runtime compilation also consumes this function. This is the natural integration point for a distinct instruction projection. [S4, S5]

One implementation trap: `strip_managed_roster_markers()` removes the marker lines, **not the roster content**. Reusing it as a hiding operation would leave every roster entry in the prompt. A projection must replace the entire managed region while preserving authored prose before and after it. It must also work when markers were absent and the renderer would normally append a roster. [S4]

There is already provider-budget compaction. It first removes summaries from superseded entries and then compacts entire list rosters. That is emergency compression, not selective delivery: ordinary agents still receive irrelevant record names, and the result depends on provider capacity. An explicitly deferred roster should be excluded from the compaction candidates. [S6]

### A roster index exists, but not the required audited read

| Existing command | Current behavior | Suitable for the requested planner read? |
| --- | --- | --- |
| `sase memory read decisions -r "..."` | Reads every strand body, with normal link behavior | No: much broader than the roster |
| `sase memory read decisions:<keyword> -r "..."` | Reads selected decision bodies | Yes, after discovery |
| `sase memory read decisions.md -r "..."` | Rejects the descriptor as always loaded | No |
| `sase memory web show decisions` | Human-facing strand index; no memory-read audit | No |
| `sase memory show decisions` | Full strand content without an audit | No |

I confirmed the descriptor rejection through an actual audited-read attempt. Its error directs agents to strand reads. The existing web-index implementation is useful discovery infrastructure, but its table shortens summaries to a first sentence with a 72-character limit. It is not equivalent to the current instruction roster, and it does not use the roster renderer's supersession presentation. [S7]

### Auditing and TUI presentation need a semantic extension

`memory read` resolves a batch, constructs one audit event, appends it, and then emits the view. Identity and a nonempty reason are required. The log is currently schema 3, with `kind` values `note`, `web`, and `strand`. A full-web read resolves to the individual strand targets because their bodies were delivered. [S8]

The Rust audit reader accepts only schemas 1–3 and those three kinds. Python's wire decoder also validates kinds. A Python-only event addition could silently disappear from the TUI, or lose its new fields in the Rust round trip. [S9]

The appropriate display surface already exists: the Agents tab's **MEMORY** context lane, alongside the instructions-as-launched row and ordinary memory reads. It has timestamps, reasons, agent attribution, keyboard hints, and version chips. There is no need for a new pane. However, its current counters describe distinct read targets as “files”; a roster needs its own label and must not inflate the count into dozens of body reads. [S10]

There is another important limit: modern batch-read reports currently re-resolve selectors against available current files. A test explicitly expects current Markdown output. Blob IDs are recorded, and version pins help individual targets, but the batch report is not an immutable record of the exact output. A new roster read must not reopen tomorrow as a different roster—or as all of today's strand bodies. [S11]

## 3. Critique and requirement adjustments

### Keep discovery conditional, not exclusive

“Only planners read decisions” is too strong. Decisions explain constraints that implementers also need. bob-cli's current descriptor even states that each roster summary is a rule and requires reading the record before changing governed behavior. Removing those summaries without a replacement would weaken its existing policy. [S1]

Use three expectations instead:

1. Before writing or revising a SASE plan, read the full decisions roster, then the applicable decision bodies.
2. In the plan, cite the applicable decisions and summarize the constraints the implementer must preserve. The implementer reads those cited records rather than the entire catalog.
3. When making an architectural or policy change without a plan, or departing from a plan's design, consult the roster first. Routine work need not incur the cost automatically.

This is a project instruction, not a new global planning rule. The trigger should say “before writing or revising a SASE plan with `/sase_plan`,” not depend on an agent name, launch-time role, or a skill-use log entry. An agent can decide to plan halfway through a turn; a role predicate established at launch would miss that.

Non-negotiable execution rules still belong in core instructions or focused reference-memory triggers. In SASE, many already do: finalization, the Rust boundary, and audited repository access are examples. Before migration, check for any essential rule whose only remaining exposure would be the hidden decision roster. Do not copy all 108 summaries into another core note.

### Treat a roster as discovery, not proof of understanding

A roster read establishes that the catalog was delivered. It does not establish that all decision bodies were read, that every relevant decision was recognized, or that the agent complied. The audit and TUI should say what actually happened.

Preserve full summaries and supersession status in the on-demand roster. Defaulting to active records only is risky: partially superseded records can retain live constraints, and old records explain rejected approaches. Keep the current full catalog in the first release. Filtering or historical grouping can come later if planner scans themselves become costly.

Nygard's original ADR rationale is useful here: the records prevent both blind acceptance and blind reversal by preserving context and consequences, and superseded records remain available. That is a reason to defer access rather than delete history. [Documenting Architecture Decisions](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)

### Make these adjustments explicit

| Adjustment to the request | Reason |
| --- | --- |
| Planner-required discovery, rather than planner-exclusive access | Direct changes and implementation still need applicable constraints |
| Change generated `AGENTS.md`/provider copies as well as invocation bundles | Native tools and fallback delivery must not reintroduce the roster |
| Add an audited roster *view*, preferably without another command family | Existing read/show semantics already separate agent consumption from human inspection |
| Preserve a read-time roster snapshot | Audit display must not substitute later content for what was delivered |
| Leave `/sase_plan` unchanged; update generic memory guidance | The feature concerns any web and any project-defined trigger |
| Do not add automatic role inference or skill hooks initially | They are a larger framework than this demonstrated problem requires |

The saved snapshot is a modest strengthening of “audit and display the read.” It is justified because the view is derived from multiple mutable files and scopes. It should be bounded to the new roster feature; repairing historical full-body batch reconstruction is separate work.

## 4. Recommended generic design

### One delivery field; keep prose as the trigger language

Add a descriptor field with the following proposed contract:

```yaml
web: true
roster: list
roster_delivery: on-demand
```

`roster_delivery` accepts `always` and `on-demand`; omission means `always` for complete backward compatibility. It controls the roster's inclusion in agent instructions. It does not control whether a human or an agent may explicitly retrieve it. `roster` retains its existing formatting meaning.

For `always`, preserve existing output. For `on-demand`:

- Keep the web's heading and authored descriptor prose in Memory Webs.
- Replace the managed roster region in instruction output with a short generated command hint.
- Keep the full managed roster in the canonical descriptor on disk for maintainers and history.
- Render the full current roster when explicitly requested, independent of delivery policy.

The descriptor's ordinary Markdown should explain **when** to read. The renderer supplies **how** to read. This avoids a second prompt field, escaped Markdown in YAML, a conditions language, and special knowledge of decisions or planning.

For these two projects, a compact authored body could say:

> Before writing or revising a SASE plan with `/sase_plan`, you MUST read this roster, then read the applicable decision records. Cite those records and their constraints in the plan. Implementers must read the records their plan cites. Before an architectural change without a plan, or a departure from its design, read the roster first. Accepted records are immutable; record changes of course through supersession.

The generated hint below it would be:

```text
Read the roster: sase memory read decisions --roster -r "<why>"
Read a record: sase memory read decisions:<keyword> -r "<why>"
```

These commands are proposed syntax, not currently available roster behavior. The generic hint should use the actual web slug and, where helpful, its existing `strand_noun`. Do not put a changing strand count or digest in the standing hint: those belong in retrieved output and would add unnecessary prompt churn.

Validate invalid delivery values as errors. Validate roster markers even for deferred webs. Require a nonempty authored body outside the managed roster for an on-demand web; a generic validator should not try to understand whether that prose names every possible trigger. The generated hint guarantees discoverability but not semantic completeness.

### Extend `read` and `show` with `-R/--roster`

Recommended interfaces:

```bash
sase memory read decisions --roster -r "Identify constraints before writing the plan"
sase memory read decisions:rust-core-required decisions:memory-links-are-authored \
  -r "Understand the decisions governing the proposed memory feature"

# Human/tool inspection, deliberately unaudited:
sase memory show decisions --roster
```

`-R` is free in the current read/show parser; `-r` already means reason. Keep default Markdown output, with the existing rich and JSON format choices. [S12]

Define the edges explicitly:

- `--roster` accepts one or more **bare web names** only.
- Reject note and strand selectors under this flag with an actionable error. Do not invent a reserved pseudo-strand such as `decisions:roster`.
- Resolve and validate the whole batch before logging or printing anything. An unknown or malformed web fails the batch.
- Reject an explicit `--depth` with `--roster`; roster reads do not traverse links or expand bodies.
- Keep the existing meaning of bare `sase memory read decisions` unchanged: full-web content.
- Allow roster reads for either delivery mode. On-demand is a prompt policy, not an access restriction.
- An empty valid web produces a labeled empty roster and one attributable read; it does not look like an unknown web.

Render a title, the descriptor's authored introduction, the complete ordered roster, and a small footer explaining how to read selected strands. Do not resolve inline or implicit links in this view: even an inline link authored in the descriptor must remain a reference rather than pulling in a body. For list rosters, use the existing summary and supersession formatting; for inline rosters, preserve the existing keyword/alias format.

Compute the roster from the discovered strands, not the possibly stale managed region in the descriptor. Reuse project-over-home resolution: the project descriptor sets the effective policy, and project strands override matching home slugs while other home strands remain visible. Record the effective origins. This is already the normal read-time merge model. [S13]

The current human-facing `memory web show` can remain a searchable index. Link its help to `memory show --roster` for full roster output and to `memory read --roster` for audited agent use. Avoid simultaneously adding `memory roster`, `memory web read`, and selector aliases.

### Keep the canonical document and instruction projection separate

Use distinct operations with one shared structured roster representation:

```text
canonical descriptor -> authored prose + complete managed roster
agent instructions   -> authored prose + roster OR retrieval hint
explicit roster view -> authored prose + complete current roster
```

The policy decision must be shared by the committed projection and runtime compilation. Do not use a regex in the final instruction string as the only implementation; it would miss other consumers and make malformed markers hard to diagnose.

Keep the web section visible and included in the instruction manifest. Its instruction is delivered even though its roster is deferred. Distinguish source dependencies from delivered content: strand files may still participate in validation or invalidation, but must not imply that strand bodies—or even their roster entries—were delivered. The current manifest lists strand sources for web sections, so this deserves an explicit review. Do not promise stable bundle identity merely because text is stable: source fingerprints can still change. [S14]

## 5. Audit and TUI contract

### Model the view explicitly

Prefer preserving `kind: web` and adding a view discriminator, rather than inventing a new memory kind. The following is an illustrative schema, not a prescription to duplicate existing fields:

```json
{
  "schema_version": 4,
  "kind": "web",
  "view": "roster",
  "selectors": ["decisions"],
  "resolved_targets": ["decisions"],
  "included_targets": [],
  "roster_count": 1,
  "entry_count": 31,
  "rendered_byte_count": 8000,
  "snapshot_sha256": "<digest of the canonical roster view>",
  "snapshot_ref": "<durable content-addressed locator>"
}
```

Retain existing event identity, reason, agent/turn association, project, timestamp, and scope attribution. Old rows default to the existing content view. Preserve old `byte_count` meaning; introduce a clearly named rendered-byte field if necessary rather than silently changing past analytics.

A roster resolves to the web being discovered. Its entries are **listed entries**, not `included_targets` representing body reads. Any per-entry source versions belong in roster provenance, separate from the body-read target fields. This prevents false read counts and false version pins.

Prepare the complete canonical Markdown and structured provenance once. Persist an immutable snapshot, append the audit record referencing it, then emit the same prepared view. Identity/reason/resolution/rendering/persistence failures produce no successful audit and no unaudited content. An output pipe failing after the append cannot prove model consumption; document the event as recorded delivery, not evidence of comprehension.

A small content-addressed snapshot under SASE-owned durable state is preferable to embedding tens of kilobytes into every row returned to the TUI. Identical roster views can share storage, and the pager loads bytes lazily. Keep snapshots while their audit records are retained; do not put the only copy in an ephemeral workspace or in the current 50-report presentation cache. Capture canonical Markdown plus the source roster data needed to explain project/home provenance. A digest alone is not a snapshot.

### Evolve Rust and Python together

The Rust audit parser, query wire, Python decoding/models, and memory-log formatting must carry `view` and snapshot metadata without dropping them. Historical schemas 1–3 remain readable. A schema-4 event must not be emitted until the installed core and Python consumers support it. Ratchet `sase-core-revision.txt` after the core commit; update any separate audit-query wire-version constants and binding fixtures together. [S9, S15]

Keep the new shared domain policy, structured roster view, validation, and audit semantics in `sase_core`, exposed through the existing binding style. Current discovery and much roster formatting happen in Python; that is the implementation's starting point, not permission to build another Python-only domain. Python can load files and adapt the existing records to the new Rust contract; Textual presentation and CLI I/O remain frontend work. A narrow boundary change is sufficient—this proposal does not require rewriting the entire memory subsystem.

### Use the existing MEMORY lane

A compact row should read like this, using the lane's existing styles and hint behavior:

```text
MEMORY  1 roster read · 2 record reads
  10:42  [3] decisions · roster · 31 entries
               Identify constraints before writing the plan
  10:43  [4] decisions:rust-core-required
               Understand the backend boundary
```

The row must visibly distinguish a roster from a full-web read without relying on color. Selecting it opens **Roster as read**, with the timestamp, reason, project, provenance, and captured roster. Offer browsing the current web separately if useful; never silently swap it in.

Do not route the hint to the descriptor's filesystem path merely because that path exists. The existing hint code favors `resolved_path`; roster events need explicit routing to the snapshot report. Do not run a snapshot hash through Git's strand-version lookup and label it “uncommitted.” Roster snapshots and committed file versions are different identities. [S10, S11]

If the snapshot is unavailable or corrupt, show the recorded metadata and “snapshot unavailable.” Do not display current full-web content under an “as read” title. Opening a report in the TUI is inspection and must not append another agent memory-read event.

Avoid a parallel telemetry dashboard or a new navigation mode. The existing lane, detail pager, CLI log, and memory-web browser already cover the required questions.

## 6. Migration and implementation boundaries

This is best delivered in dependency order, with the feature complete before either project starts emitting the new instruction.

1. **Backend contract and read support.** Add the generic delivery policy and structured roster-view contract, audit schema support, snapshot handling, bindings, and focused tests in `sase-core` and SASE. Update the core pin and compatibility checks.
2. **Projection and interface integration.** Wire the common projection into `memory init` and runtime compilation; add read/show flags; update MEMORY-lane labeling, snapshot opening, log output, and compaction handling.
3. **Generic guidance.** Update the source for `/sase_memory_read` and the generated memory explanation/README so they no longer claim every descriptor's full content always loads. Teach the generic roster command. Keep `/sase_plan` free of project-specific decisions guidance. Update docs through the project's documented writing workflow. Generated skill deployment follows the landed-source workflow, not editing installed SKILL.md copies.
4. **Project adoption.** In both `sase/memory/decisions.md` files, set `roster_delivery: on-demand` and author the planning/implementation/direct-change trigger. Preserve the canonical roster and existing record semantics. Regenerate each project's committed instruction files through `sase memory init`; do not hand-edit `AGENTS.md` or `CLAUDE.md`.
5. **Document the architectural change.** In SASE, add a decision for conditional roster delivery and mark only the affected always-loaded-roster clause of `webs-render-in-their-own-section` superseded in part, following the immutable-record convention. Its separate Memory Webs placement and prohibition on `type:` remain valid. A formal implementation plan must carry the required per-note memory decisions, including generic explanatory notes made inaccurate by this change.

The bob-cli migration must replace its present instruction to follow every visible roster summary with the new discovery rule; simply hiding its managed region leaves the prose referring to content the agent cannot see. Its decisions cover linked applications as well as bob-cli, but the current request does not authorize silently changing all linked repositories' memory configurations. Check the two requested project projections and explicitly report any additional adoption need.

Leave all unrelated webs at the default. Glossary and task-type catalogs are different retrieval situations; this feature should not move them automatically. Rollback is the explicit per-web value `always`, followed by regeneration. Audit readers and snapshots stay compatible regardless of the current delivery setting.

## 7. Tests and evaluation that matter

| Risk | Required evidence |
| --- | --- |
| The feature accidentally recognizes only decisions | An arbitrary test web with a different name and trigger works identically |
| Existing projects change unexpectedly | Absent field and explicit `always` preserve legacy output |
| A roster leaks through another rendering path | Generated instructions, runtime bundles, fallback/provider copies, and budget compaction all honor deferral |
| Hiding the roster destroys human documentation | Canonical descriptor still contains the full managed roster; repeated init is idempotent |
| Stale descriptor content reaches the planner | Change a strand summary without running init; roster read shows the current summary |
| Roster reads expand bodies | Sentinel body strings, inline links, and implicit references never appear in roster output |
| Scope merging diverges | Home-only, project-only, project overrides, mixed origins, and same-root cases match existing read semantics |
| Invalid input produces partial audits | Mixed selectors, unknown webs, invalid delivery values, malformed markers, and persistence failures yield no partial result |
| Rust drops new rows or fields | Core parser and PyO3 round-trip tests cover new events plus schemas 1–3 |
| The audit overclaims reading | One roster event counts as one roster discovery; listed strands do not become body reads |
| The TUI shows later content | After read, alter/delete source files or remove the workspace; the original snapshot still opens |
| UI inspection creates extra reads | Opening a roster hint changes no audit log; missing/corrupt snapshot stays visibly unavailable |
| Adoption leaves contradictory guidance | Both project projections contain the trigger and command, no roster entries, and no claim that all roster summaries are already visible |

Use the repository's normal prescribed verification recipes during implementation, with targeted tests for these behaviors and visual checks for the lane/pager changes. This research did not run an implementation test suite because it made no product changes.

After adoption, sample ordinary tasks, new plans, replans, and direct architectural fixes. Measure actual instruction bytes/tokens, whether required roster reads precede plan work, whether plans cite applicable records, and whether implementers preserve the cited constraints. Include at least one case involving a partially superseded decision. Compare quality against the current behavior, not just prompt size.

The rough context arithmetic is favorable: if a roster costs R tokens, its retrieval hint costs H, and a fraction p of turns require discovery, the expected input-context reduction is approximately `(1 − p)R − H`, before tool-call overhead and provider caching. Planner turns retain approximately the old roster cost plus a retrieval round trip; ordinary turns get the main savings. This is a context estimate, not a billing forecast.

There is deliberately no hard enforcement of natural-language planning intent in the first release. Audit evidence makes missed reads observable, but cannot prove comprehension. If evaluation shows frequent misses, consider a separate generic project-owned prerequisite mechanism for plan validation/proposal. Do not preemptively build it into this roster feature or pretend that a prose MUST is a mechanical gate.

## 8. Alternatives considered

| Approach | Judgment |
| --- | --- |
| Shorten every summary or rely on existing compaction | Useful housekeeping, but all agents still pay; summaries lose useful constraints |
| Reintroduce `type: reference` on web descriptors | Reopens the kind/tier conflation explicitly rejected by the existing architecture |
| Add `roster: none` or `roster: deferred` | Conflates formatting with delivery and obscures how explicit retrieval should render |
| Change bare-web reads to return rosters | Breaks existing whole-web semantics and scripts; use an explicit view |
| Use `memory web show` unchanged | No audit, truncated summaries, and different presentation |
| Add `memory web read` | Defensible, but creates two different full-web/roster meanings of “read”; an explicit roster flag fits the current pair better |
| Add `decisions:roster` | Makes a derived view look like a strand and risks name collisions |
| Add a global `/sase_plan` decisions step | Violates the project-local requirement and burdens projects without that web |
| Filter by launch-time planner role | Misses agents that decide to plan during a turn and adds provider/runtime coupling |
| Add structured skill-trigger hooks now | Could give stronger enforcement later, but expands scope to a new policy framework |
| Use semantic search instead of a roster | Introduces retrieval misses and indexing work for catalogs of 31 and 77 records; defer until measured scans become a problem |
| Delete superseded records | Loses rationale and surviving constraints; preserve status and follow successors |

## 9. Source map

Paths below are relative to the repository named above; line numbers refer to the inspected commits. Memory bodies were obtained through `sase memory read`, not direct canonical-file reads. The generated instruction files are the supplied/project-visible projections. No peer research was used.

- **S1 — Actual project projections:** SASE `AGENTS.md:162` through the next web heading; bob-cli `AGENTS.md:117` through its next web heading at line 471. These supply the counts, byte measurements, and current project-level decisions policies.
- **S2 — Architectural constraints, audited:** `decisions:webs-render-in-their-own-section`, `decisions:memory-webs`, `decisions:memory-links-are-authored`, `decisions:instructions-per-invocation`, and `decisions:readable-agents-md`. The web-placement decision explicitly names this token-pressure reopening condition.
- **S3 — Web model and validation:** SASE `src/sase/memory/web/models.py:45`, `frontmatter.py` (descriptor parsing), and `validation.py` (`validate_memory_webs`, `_strand_summary_blockers`).
- **S4 — Roster rendering:** SASE `src/sase/memory/web/roster.py:124`, `:192`, and `:220`; also `strip_managed_roster_markers` in that file.
- **S5 — Common initialization/runtime path:** SASE `src/sase/main/init_memory/root_planning.py:262` (`memory_web_root_plan`) and `src/sase/instructions/compile.py` (`_collect_units`).
- **S6 — Existing budget compaction:** SASE `src/sase/instructions/compaction.py:110`; `tests/instructions/test_bundle_compaction.py` is the corresponding test surface.
- **S7 — Existing human index:** SASE `src/sase/memory/web/cli.py:67` and `:236`; `src/sase/memory/selector_models.py:152` for selector shapes. Runtime `memory read decisions.md` rejection was also verified.
- **S8 — Read/audit flow:** SASE `src/sase/memory/cli_read.py:27`, `:44`; `src/sase/memory/_read_log_models.py:11`, `:53`; `_read_log_events.py` (`append_memory_read_event`, `memory_read_event_targets`).
- **S9 — Rust audit boundary:** sase-core `crates/sase_core/src/audit_query.rs:90`, `:421`; SASE `src/sase/memory/_read_log_query_facade.py` (event decoding and schema check).
- **S10 — Existing TUI location and hint routing:** SASE `src/sase/ace/tui/widgets/prompt_panel/_agent_memory_reads.py:56`, `:105`, and `_agent_memory_versions.py` (`resolve_event_chips`).
- **S11 — Historical output limitation:** SASE `src/sase/memory/memory_read_report.py:51`, `_resolve_report_view`, `_REPORT_KEEP_COUNT`; `tests/test_memory_read_report.py` (`test_build_report_uses_memory_show_command_and_current_markdown_output`).
- **S12 — CLI contract:** SASE `src/sase/main/parser_memory.py:295`; audited `cli_rules.md` requires public long flags to have short aliases and clear help.
- **S13 — Scope behavior:** SASE `src/sase/memory/web/scope.py:15` and `read_context.py`.
- **S14 — Manifest source accounting:** SASE `src/sase/instructions/sections_units.py:142`; `src/sase/amd/memory_units.py` (`_strand_files_for_web`, `_WEB_MEMORY_INTRO`).
- **S15 — Backend and migration rules:** audited `decisions:rust-core-required`, `generated_skills.md`, and the opened sase-core `AGENTS.md` instructions on wire-version updates, binding registration, and SASE's CI pin.

The external sources support the general tradeoffs, not the repository-specific implementation claims: [Anthropic's context engineering article](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) and [Nygard's original ADR article](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

## Recommended solution

**Ship generic on-demand roster delivery with `roster_delivery: always | on-demand`, defaulting to `always`; add audited `sase memory read WEB --roster` and matching unaudited `show`; preserve the exact retrieved roster for the existing MEMORY lane; and adopt the policy in the SASE and bob-cli decisions descriptors.** Keep `/sase_plan` unchanged. Require planners to discover and read applicable decisions, require implementers to read the records their plans cite, and retain discovery for direct architectural changes. This removes the recurring context cost while preserving a clear path to the decisions and an honest record of what the agent received.
