# Clan waves that explain execution without obscuring agents

Independent research and design recommendation by **cdx**, 2026-10-15.

## Decision in brief

**Build this feature. Represent waves as stable dependency layers within a clan, using foldable wave bands in the agent tree and a compact overview in clan details.** Derive the structure from actual launch dependencies for every clan type. Preserve a clean, flat presentation for one-wave clans. Treat missing structure as unknown rather than inventing waves from timestamps, names, or current statuses.

This is a good product direction because the screenshot exposes the cost of a status-only view: it answers “what is running?” but makes “what comes next, and why?” unnecessarily difficult. The principal implementation work is establishing a trustworthy generic wave model; drawing separators alone would produce an attractive but unreliable feature.

This report is independent. I inspected the supplied screenshot, project code, the research plugin's macro source, and primary external documentation. I did not read another swarm researcher's report, transcript, or findings. The layouts below are proposed text wireframes, not implemented screenshots or usability-tested results.

## 1. What exists today

### The screenshot

In `~/tmp/screenshots/20261015_124557.png`, the selected epic clan `bob-cli-7v` contains phase workers and a `.land` member. The tree places active workers above waiting workers and the completed worker at the bottom. Waiting phase suffixes are consequently displayed in reverse-looking order: `.7`, `.6`, `.5`, `.4`.

The right panel already says **7 phases · 5 waves**, but its long plan summary lists phases without a corresponding live wave structure. The bottom member-jump strip is flat. These three representations make the user mentally reconstruct the dependency graph. The screenshot's other research clan is collapsed; it provides no visible clue about its research and synthesis stages.

The left navigation column is already busy and vertically constrained. Adding five permanently expanded containers, animation, or a separate dashboard would increase the cost of finding an agent. The design should improve information hierarchy while preserving the existing direct path to member rows.

### Findings from implementation

| Finding | Evidence and implication |
|---|---|
| A clan is execution-neutral membership, not a scheduler. | `sase:docs/macros.md:2421` explicitly separates membership from waits, launch order, and execution. Wave presentation must not introduce new admission barriers. |
| Clan identity already includes a generation. | `sase:src/sase/agent/clan_membership.py:23`, `sase:src/sase/ace/tui/models/agent.py:494`. A generation distinguishes separate incarnations of a name; it is not a wave. Scope wave identities to it. |
| The left tree deliberately sorts direct member subtrees by status. | `sase:src/sase/ace/tui/models/_agent_tree_clan.py:291`. This explains the screenshot. Existing sessions and their turns are kept together; wave grouping must retain that property. |
| Clan details use a different deterministic order. | `sase:src/sase/ace/tui/widgets/prompt_panel/_agent_display_clan_roster.py:28` sorts direct members by launch time and name. A single wave projection should serve tree, detail roster, and jumps. |
| Epic dependency waves already exist in Rust. | `sase-core:crates/sase_core/src/bead/work.rs:15` has `PhaseAssignmentWire.wave`; `build_epic_work_plan_from_issues` layers dependencies. Python's `_PhaseAssignment` preserves the value. Reuse the domain concept. |
| Epic launch metadata does not currently carry that wave into clan display. | `sase:src/sase/bead/work_env.py:20` carries epic/phase/plan metadata but no wave field; generic `AgentClanContextWire` contains tribe/summary context, not topology. There is a missing data path, not just a rendering omission. |
| Authored and executable epic counts have different scopes. | `sase:src/sase/sdd/plan_waves.py:24` layers the authored plan; Rust `bead/work.rs` excludes closed phases and phases delegated to open child epics before layering executable work. Recomputing the current executable plan cannot supply permanent original wave numbers. |
| Existing clan attributes already survive cleanup. | `sase-core:crates/sase_core/src/agent_clan_record.rs` records generation-scoped summaries and tribes and applies them over member-derived context. This is a useful integration point, but its eight-generation retention limit is not automatically suitable for durable wave history. |

The screenshot's version and these checkout revisions may differ. The screenshot establishes the visible problem; code findings establish the inspected implementation seams, not a claim about every installed version.

### Research clans already have meaningful waves

The packaged `research_swarm.md` macro supplies actual dependencies:

1. Enabled independent researchers run without dependencies on each other.
2. The lead `.final` waits for each researcher.
3. Optional `.image` and `.audio` members wait for `.final` and can run in parallel.
4. An enabled `.linker` waits for `.final` and any enabled image/audio members.

This yields two, three, or four dependency layers depending on enabled options; disabled segments must not create empty waves. The linker is enabled whenever media is enabled. With no researchers, the lead is a root rather than an empty second wave. An optional external `wait` delays research without creating an internal wave.

These facts come from **macro definitions**, not any live peer research output. See `research-plugin:src/sase_research_artifacts/xprompts/research_swarm.md:137`, `:161`, `:185`, `:269`, `:273`, and `:483`.

Custom clans authored with normal `%wait` dependencies should get the same treatment. There is no need to special-case the names `research`, `.final`, or `.cdx`.

## 2. Critique and justified requirement changes

The idea is worthwhile if “waves” means useful execution structure. I would make five explicit adjustments to the request:

1. **Support waves for every clan, but do not assume every clan has multiple waves.** A complete set of independent members forms one wave. Show `parallel · 4 agents` in compact views and `Wave 1 · 4 agents` in expanded detail, without a redundant extra tree level. Historical records with insufficient dependency information are `structure unavailable`, not a confidently inferred single wave.
2. **Define a wave as a dependency layer, not a simultaneous launch batch or an enforced barrier.** Queue capacity, rate limits, manual delays, and runner scheduling can stagger agents within one wave. New wave presentation must leave those scheduling rules intact.
3. **Show actual activity across all waves.** Do not designate a single “current wave” if more than one contains running work. A later layer can start while unrelated work in an earlier layer remains active.
4. **Separate phase waves from finalization when the producer declares that role.** For epics, keep the existing “5 phase waves” meaning and show the landing member in a trailing `Finish` band. Do not silently turn the example into “6 waves.” This is generic role metadata, not a suffix heuristic. Research synthesis remains a normal dependency wave.
5. **Use truthful counts rather than an apparent percent complete.** Agent count and wave count are not estimates of elapsed or remaining effort. Keep planned work, runtime state, and successful outcomes distinguishable.

A simple counterexample makes adjustment 3 essential:

```text
A ──> C
B

Wave 1: A, B       Wave 2: C
```

After A finishes, C may run while B continues. A strict stepper would falsely imply C is blocked until all of Wave 1 finishes. The source confirms SASE emits per-assignment dependency waits, not a wait on every earlier wave member (`work_prompt.py:177`). Argo's official DAG documentation independently illustrates why task dependencies, rather than universal stage barriers, preserve parallelism. [Argo DAG documentation](https://argo-workflows.readthedocs.io/en/latest/walk-through/dag/)

I would not add a `%wave:2` directive in the first release. It creates another authored structure that can contradict `%wait`. Automatic derivation makes custom clans work immediately; optional labels can be supplied through launch metadata later. If users mean a business stage whose members have different dependency depths, that is a separate grouping concept and should not silently redefine this one.

## 3. Design alternatives

| Approach | Strength | Cost | Decision |
|---|---|---|---|
| Add `W2` chips to every agent row | Low height cost; easy to scan once learned | Leaves members scattered; another dense annotation | Useful only as a fallback in narrow layouts or filtered results |
| Horizontal connected stepper | Elegant for small linear plans | Implies one current step and hard sequencing; overflows with many waves | Avoid as primary navigation |
| Foldable wave bands inside the clan tree | Directly associates members and structure; reuses folds | More rows and row-type plumbing | **Primary recommendation** |
| Wave overview only in the detail panel | Minimal navigation disruption | Hidden until selecting the clan; tree still loses sequence | Complement to bands, or a deliberately limited prototype |
| Gantt/timeline or full DAG | Accurate overlap/dependency detail | Time scale, routing, width, and interaction complexity | Defer; use direct blocker text for the initial release |
| Infer groups from start-time gaps | No launch metadata needed | Scheduling load and retries change the supposed structure | Reject |

Carbon's progress-indicator guidance is helpful precisely at its boundary: it targets linear, known-step processes and cautions against arbitrary ordering and conditional step counts. I would borrow numbered labels and clear status treatment, but not its linear interaction model for a dynamic clan. [Carbon progress-indicator guidance](https://www.carbondesignsystem.com/building-blocks/core/components/progress-indicator/guidelines)

## 4. Proposed appearance

### A. Expanded clan in the left tree

Illustrative layout for the supplied epic, with labels shortened for the wireframe:

```text
▾ bob-cli-7v   RUNNING              5 phase waves
  ▾ Wave 1    2 active · 1 done
  │ ├ .1      DONE        Dedupe imports
  │ ├ .2      TESTING     Collection naming
  │ └ .3      RUNNING     Adapter contract
  ▸ Wave 2    1 waiting
  ▸ Wave 3    1 waiting
  ▸ Wave 4    1 waiting
  ▸ Wave 5    1 waiting
  ▸ Finish    waiting on phases
```

Wave bands should be modest separators, not additional heavy boxes. Use the current clan identity styling, thin branch guides, aligned ordinals, and a concise right-side aggregate. Reserve strong background highlighting for selection. Wave headings use normal readable contrast; future state text may be quieter without making the heading illegible.

Inside a wave, use stable authored/launch order, rather than continually sorting the whole clan on every status change. Preserve every member session subtree as one unit. Attention states remain easy to find through the clan aggregate, a `!` on affected bands, and existing next-attention navigation. The phase ID/member suffix and runtime status remain visible; descriptive titles can yield first when width runs out.

Initial fold policy: expand waves with activity or attention, collapse successful and waiting-only waves. Apply that policy once when a generation is first viewed. Thereafter honor user folds, including when work changes state. Automatically opening or closing groups during navigation would undermine the benefit of stable structure.

### B. Clan overview above the long summary

```text
CLAN  bob-cli-7v                          RUNNING
7 phases · 5 phase waves · Finish waiting

Waves  [1: 2 active, 1 done] [2: wait] [3: wait] [4: wait] [5: wait]
       Dependency layers can overlap

Wave 1
  .1  DONE        Dedupe imports
  .2  TESTING     Collection naming
  .3  RUNNING     Adapter contract
Wave 2
  .4  WAITING     after .1, .2
...
Finish
  .land WAITING   phase closure required
```

The overview is a set of independent status summaries, without a continuous filled bar or arrows that imply barrier transitions. Integrate it before the long prose summary so progress is immediately visible. Existing member jump hints continue to target agents; grouping changes where hints are displayed, not their identity.

A research clan with media enabled can read:

```text
research.4j   RUNNING       4 dependency waves
  ▾ Wave 1 · Research      3 done · 1 running
      .cdx  RUNNING
      ...
  ▸ Wave 2 · Synthesis     waiting
  ▸ Wave 3 · Media         waiting · 2 agents
  ▸ Wave 4 · Publish       waiting
```

Purpose labels are optional producer-supplied annotations. If absent, `Wave 2` is sufficient. The example illustrates a macro configuration; it is not an observation of this swarm's completion state.

### C. Collapsed, narrow, and very large cases

- Collapsed clan: `▸ research.4j  RUNNING · active W1 · 3/4 researchers done`. If several waves are active, say `active W1, W2` rather than “Wave 2 of 4.” At tighter widths, keep attention, clan identity, runtime state, and a short `W1 active`; remove optional detail first.
- One-wave clan: retain flat member rows and one compact `parallel` summary. Expanded detail explains the single wave. An eight-agent independent review should not acquire an extra fold level merely for formal consistency.
- Many waves: keep the vertical list scrollable; the compact overview shows attention/active waves and an explicit omission such as `+17 waves`. Avoid wrapping the ribbon into many lines or horizontal scrolling in the left pane. Keep the complete overview in the detail section.
- Filtered view: retain matching members' wave context, show `2 shown / 5 total`, and keep authoritative aggregate counts distinct from visible counts. A hidden blocker must not appear complete or disappear from the detail explanation.

### Visual and accessibility rules

Reuse semantic theme colors for active, successful, waiting, attention, and failed states. Do not assign a different hue to each wave: color already carries status throughout the TUI. Pair every status with a word and/or a stable symbol; `!`, `>`, `+`, and `.` can provide an ASCII rendering when Unicode support is limited. Avoid pulse animation and wide emoji in aligned wave headings.

The intent follows W3C's guidance that meaningful distinctions must survive without color. Its non-text contrast guidance also provides a useful target for necessary group/focus indicators; this is a design reference, not a claim that a terminal application thereby conforms to WCAG. [W3C use of color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html), [W3C non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)

## 5. Interaction contract

Waves are **presentation groups, not agents**. They must not consume agent counts, acquire fabricated transcripts, or become targets for agent-only kill/retry actions.

Follow the existing grouping-banner convention: expanded headings are chrome; collapsed headings are selectable navigation items. Existing fold commands should act on the nearest applicable wave from a member and on the whole clan from its container. A collapsed heading opens an aggregate wave detail view and exposes a fold action. Mouse and keyboard must have equivalent routes; no new global wave-navigation mode is necessary initially.

Selection is keyed by member identity or `(clan generation, wave ID)`, never row index. Preserve the current agent across refresh, state updates, tab changes, and arriving members. If an explicit fold hides the selection, select that group. If a filter or dismissal removes it, fall back to its wave or clan. Do not move focus because some other agent failed.

Group headings should expose safe navigation and folding only in the first version. Bulk kill/dismiss/retry on waves requires a separate action contract and is out of scope. The existing top-level status grouping still groups the clan by its aggregate status; wave grouping is nested within that clan, independent of the outer grouping mode.

Textual documents guide lines, node selection, and expand/collapse interactions as established tree affordances. SASE already renders its list through `OptionList` row-building helpers, however; the feature should extend that path rather than replace it with a second tree widget. [Textual Tree documentation](https://textual.textualize.io/widgets/tree/)

## 6. A reliable generic wave model

### Define structure once, observe activity continuously

For each clan generation, create a Rust-owned **topology manifest** from the normalized launch units and resolved dependency identities. It should contain logical work-unit IDs, membership/attempt mappings, internal edges, external blocker annotations, stable ordering, optional labels/roles, a topology revision, and completeness/provenance information.

For a valid finite internal DAG:

```text
rank(root) = 1
rank(unit) = 1 + max(rank(internal predecessors))
```

Use a deterministic topological pass with cycle diagnostics. External waits affect readiness but do not add phantom internal waves. Distinguish an explicitly empty dependency list from absent historical data. Dynamic waits such as tribe/hood/epic-follow targets require the existing resolver's semantics; do not approximate them with string prefixes or a timestamp cutoff invented by the TUI.

Store this structure before fan-out so an early scan cannot mistake a partially registered swarm for a complete one-wave clan. Record planned members even if submission later fails. A manifest is observation metadata, not a new scheduler: incomplete persistence should yield a visible `structure unavailable` fallback, while the existing launch contract remains responsible for execution.

### Preserve identities through real lifecycle events

- **Completion:** do not delete finished units from the topology and renumber remaining waves. The Rust epic work planner currently builds a residual executable graph; use the authored generation snapshot for permanent display ranks and map executable assignments to those units.
- **Retries and sessions:** a retry remains an attempt of the same logical unit in the same wave. Sequential agent/monitor/gate turns stay under the member session; they do not each create another wave. A later session turn waiting for another clan member needs an explicit blocker annotation; a static layer must not pretend to model all internal session execution.
- **Reused names:** edges bind to concrete generation/member identities. A later agent with the same spelling must not silently satisfy an older structural relation.
- **Late joins:** append members and their declared dependencies under a new topology revision. Existing ranks remain stable where the existing graph is unchanged. If a genuine graph edit changes old dependencies, expose a structural revision rather than silently relabel history. Unresolved forward targets remain provisional until bound.
- **Dismissal:** hiding a runtime row must not remove the work unit from topology or turn a failure into success. A placeholder can say `member dismissed`; deeper archived data loads on demand.
- **Partial/remote history:** topology comes from the authoritative generation context, not the currently loaded/filtered subset. An older producer that cannot provide it renders flat with a clear availability state. Stale remote state remains stale, not successfully completed.

Do not expand arbitrary aggregate clan waits into edges to every later joiner: that can introduce self-dependencies or false cycles. Freeze/resolve targets according to the wait contract. Report a genuine cycle or unresolved relation and retain access to all agents in an `Unassigned`/flat fallback. A display failure must not strand navigation.

### Keep topology, activity, and outcome separate

Use current canonical lifecycle/status projections, not a new interpretation of raw status strings. Keep the clan's existing attention precedence and single-running-member overlays such as `TESTING` and `FINALIZING`.

A wave summary can contain running, queued, dependency-waiting, awaiting-review, failed, stopped, succeeded, and unavailable counts at the same time. An attention marker supplements these counts rather than replacing all of them with “active.” Queue waits and dependency waits must remain distinguishable.

For epics, worker completion and phase-bead closure are different facts. A worker that ended while its phase remains open should read `worker done · phase open`, not a successful wave. A stopped or failed wave is settled with issues, not green “done.” Preclosed phases can be represented as already satisfied in the authored plan scope; delegated phases remain linked to their child work instead of disappearing. Mark planned-but-unlaunched units explicitly. Show `Finish` readiness against the scheduler's actual phase closure conditions.

Avoid a fabricated ETA and avoid combining “waves complete” with “percent effort complete.” The compact overview is an execution map, not a forecast.

## 7. Implementation boundaries and useful seams

This crosses the shared-backend boundary. Wave identity, topology derivation, completeness, persistence, dependency resolution, and outcome aggregation belong in **`sase_core`**, so CLI, editor, gateway, and TUI can agree. Python should adapt the Rust wire and implement presentation. Do not grow a second general graph algorithm in the TUI or extend the existing Python authored-plan helper into a competing backend.

The work naturally has three deliverable slices, each testable without redesigning the whole Agents tab:

1. **Domain and data path:** implement the generic topology wire/store and projection in `sase-core`; expose bindings. Thread the manifest through launch expansion before per-run submission, epic work generation, scan/index output, archive, and fleet transport. Update Python mirrors and the `sase-core-revision.txt` pin to include the binding commit. Additive compatibility should degrade old consumers/producers to flat display.
2. **One presentation projection:** consume that context near `_agent_tree_clan.py` while preserving real member/session relationships. Add a typed wave-group row to the list's presentation layer, not fake `Agent` objects. Extend shared row resolution, hit testing, fold keys, incremental patching, filtering, and selection restoration. Use the same wave snapshot in `_agent_display_clan.py`, the roster, and jump hints. Keep counts at the direct logical-member level.
3. **Polish and verification:** wire compact and expanded layouts into the existing fold scale; verify responsive widths, help, and theme behavior. Add optional research labels through the plugin after automatic dependency derivation works; generic user clans must already work without plugin changes.

The topology store should integrate with generation-scoped clan context and durable cleanup capture. **Do not blindly put permanent graph history under the current eight-generation summary eviction policy.** Decide retention explicitly; retain an archive-readable topology snapshot/reference and compact per-member identity metadata. Render-time history reconstruction is an unacceptable substitute.

Keep rendering pure. Compute graph structure and disk-backed enrichment off the UI loop and Textual's serial message pump, then apply a coherent snapshot through the existing coalesced refresh path. Cache topology by generation/revision, activity summaries by member state, and include both in render invalidation. Patch affected rows on activity changes; rebuild structural rows when group membership actually changes. Selection must be revalidated when asynchronous results arrive.

If implementing new bindings/options, follow the repository's wire-schema compatibility checks and current CLI conventions. If keymap configuration changes, update `src/sase/default_config.yml` and help together. Research-only work in this report does not change those files.

## 8. Verification and decision criteria

**Semantic tests** should cover an independent fan-out; chain; diamond; asymmetric branches with overlapping active waves; external/time/queue waits; disabled conditional segments; unresolved names; cycles; and a late join. Verify generation isolation, stable ranks after completion and retry, session promotion, dismissal, archived members, concurrent submissions, and partial producer failures. Test Rust/Python round trips and scan/index/fleet agreement, not only the drawing helper.

**TUI regression tests** should exercise all outer grouping modes, tab-specific folds, filters hiding blockers, a selected member surviving refresh, two active waves, error propagation, and safe action handling on a group banner. Prove that wave groups do not change agent counts or agent-action targets. Cover incremental patch and full rebuild equivalence.

**Visual fixtures** should include the supplied seven-phase/five-wave shape plus Finish; a basic two-wave research clan; media-enabled research; a one-wave custom clan; a failed early layer while later work runs; unknown history; and large/long-name clans. Check compact left-pane widths as well as 80×24, 120×40, and a wide terminal; the left pane often has much less width than the whole terminal. Inspect light/dark, monochrome/ASCII, and focused/collapsed states. Use the project's canonical PNG snapshot path with deterministic time/host fixtures.

Use the existing performance harness to compare navigation latency and refresh cost on the same fixture before/after, including many-wave clans. Acceptance: no file I/O or subprocesses on the render path, no full-list rebuild on an activity-only update, no visible selection jumps. Establish numerical budgets from that baseline instead of inventing milliseconds without measurement.

Before committing to final styling, compare the prototype against today's view on four concrete tasks: identify currently running work; identify the blocker for a waiting member; locate the next dependency layer; open a named researcher report. Add an overlap scenario and ask the user to explain why W2 is running while W1 is active. The design succeeds if the structure improves those tasks while direct agent navigation remains straightforward. A quick user review of these fixtures is more valuable than polishing an unvalidated ribbon.

No implementation, live TUI capture, benchmark, or application test run was performed for this research. The implementation conclusions have strong source support; beauty, density, fold defaults, and scanning speed remain design hypotheses to validate with a prototype.

## 9. Source record

Local source inspection used these revisions:

- **sase:** `bc4bc3e183db0b97b00f9eea9ec6b5bb57e29b8e`.
- **sase-core:** `6f422072410d95b6592e0bcda124d39e09a46b23`.
- **sase-research-artifacts:** `17623956c379f580ad1931c927df0093d51feb91`.

Code citations above are repo-relative locations at those revisions. Additional useful implementation references are `sase:src/sase/core/agent_scan_wire.py`, `sase:src/sase/ace/tui/models/fold_scale.py`, `sase:src/sase/ace/tui/widgets/_agent_list_build_rows.py`, `sase:src/sase/ace/tui/widgets/_agent_list_build.py`, `sase-core:crates/sase_core/src/agent_scan/context.rs`, and `sase-core:crates/sase_core/src/agent_scan/wire.rs:1399`. Existing wave fixtures are in `sase:tests/sdd/test_plan_waves.py`; clan cache and visual coverage provide nearby regression patterns.

The supplied screenshot was visually inspected. SASE glossary, artifact, TUI performance/screenshot, and macro reference notes were read through the audited memory interface. External references above are primary documentation, accessed 2026-10-15; they inform design choices, not evidence of measured SASE user outcomes.

## Recommended solution

**Implement generic dependency waves in Rust and display them as restrained, foldable bands inside each clan, with a compact overview before the clan's prose summary.** Derive waves from normalized launch dependencies; carry planned structure durably across runtime state, history windows, cleanup, and retries. Keep one-wave clans flat, unknown history explicit, multiple active waves visible, and epic Finish separate from authored phase-wave numbering. Preserve current member identities, session subtrees, status semantics, and navigation.

Start with the data contract and a small end-to-end prototype using epic, research, and custom-clan fixtures. Make it beautiful through alignment, whitespace, stable order, and restrained status color. Defer Gantt/DAG views, bulk wave actions, a separate wave-authoring language, and completion percentages. This solves the actual orientation problem while keeping the Agents tab an effective place to act on agents.
