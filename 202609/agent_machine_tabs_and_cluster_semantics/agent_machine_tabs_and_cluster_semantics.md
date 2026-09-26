# Machine tabs and agent-cluster semantics

**Research synthesis · 2026-09-26**

## Decision in brief

Add `All`, `here`, and one tab per enrolled remote machine to the Agents tab. This is a useful answer to the stated scaling problem: `BY_MACHINE` currently sorts all machines into one long tree, and `machine:apollo` filters the list without leaving a visible place to return to. A compact tab strip gives each machine a stable, discoverable working view while retaining the existing unified roster.

Make **Agent Cluster** a precise umbrella for *typed groupings of agent presentation roots*, not a new mutable storage object. A clan, tribe, and view tab can share navigation, membership display, and counts; their membership and operations still differ. A session remains one agent with sequential turns. Ship machine tabs and the keymap change first. Simplify clan naming and declaration rules only in a later, separately specified core migration; do not allow a running or historical member to be silently moved between clan generations.

## Evidence and critique

The present Agents surface already has tribe side panels, `GroupingMode.BY_MACHINE` banners, a `machine:` query facet, and a retired `focus`/`fleet` sub-tab state. The unified local/remote list is the current product; the old mode must not be revived. The `PanelTabStrip` used elsewhere supplies click handling and full/compact/micro labels, but its micro tier can still overflow a narrow terminal when machine count grows. Digit keys already jump to numbered agent relations, so numbered tab shortcuts would conflict. These facts are visible in `src/sase/ace/tui/{app.py,actions/agents/_fleet_projection.py,widgets/panel_tab_strip.py}`, `models/agent_groups/`, `models/agent_panels.py`, `docs/remote_dispatch.md`, and `docs/agent_sessions.md`.

Tabs solve navigation density, not the cost of collecting a fleet roster. A large `All` view and global attention/counts still need bounded, incremental loading; merely hiding rows cannot make remote polling or history scans scale. Treat feed volume and row-render measurements as a release gate, and keep existing incomplete-history indicators honest.

Clans are more than labels. Their newest generation is an aggregate `%wait:<clan>` target, the synthetic container has summary and cascade operations, and the durable record outlives a member. Tribes are mutable labels but also support a different “next completed entity” wait/fork target. Machine membership is derived from execution ownership; choosing a tab cannot move a process to another machine. The user's wish for a common mental model is sound, but a universal **Move to cluster** operation would lie about these differences. The strongest common abstraction is a typed read model with explicit capabilities.

| Research disagreement | Resolution |
| --- | --- |
| **cdx** recommends tabs after the committed query; **grk** would rewrite `machine:` on every switch. | Keep the tab scope separate. Query text is an authored filter and can drive history loading and other lookups. Tab switching should reuse a warm roster without changing query meaning. Compose the two predicates for display; show an explicit query-conflict empty state. Change Admin Center's “show agents on machine” action to select the tab instead of injecting a new filter. |
| **grk** proposes making clan and tribe interchangeable membership policies; **gem** rejects “agent cluster” altogether. | Adopt cdx's narrower typed umbrella. Existing waits, generations, and cleanup prove interchangeability unsafe. Gem's appeal to the “corpus before mechanism” decision does not govern whether a well-defined glossary term may exist. Preserve clan/tribe names and contracts. |
| **mus** recommends retaining `[`/`]` for card blocks when detail is focused and using `,`/`.` elsewhere; the other three accept `(`/`)`. | Use the requested `(`/`)` for card blocks everywhere on Agents. Focus-dependent meaning would make tab cycling unpredictable; Artifacts Files already uses parentheses but is tab-disjoint. The Shift cost is real, so keep the clickable block rail and show the keys only when blocks exist. |
| **gem** proposes automatic `%dispatch(apollo)` when the `apollo` tab is selected. | Do not silently retarget launches from a viewing action. Show an explicit “Launch on apollo” affordance or contextual hint; a launch must still choose its target deliberately. |
| **grk/gem** propose numbered tabs. | Keep digits for agent relation jumps. Use `[`/`]`, click, and a named picker/jump target for hidden tabs. |

The prior `BY_MACHINE` mode remains useful on `All` and for existing saved preferences. Keep it through the first release. On a single-machine tab, suppress its redundant lone machine header while retaining status subgroups. Revisit retirement only after usage shows it is redundant.

## Proposed model and behavior

The presentation pipeline should be:

```text
authoritative local + fleet roster
  → committed Agents query
  → structural roots (clan/session/workflow remain intact)
  → active machine-tab scope
  → tribe panels
  → grouping tree and visible rows
```

`All` shows today's result. `here` shows local roots. Each enrolled remote machine gets a tab even when its feed is empty or stale, so it does not vanish at the moment it is needed. Default to `All` for existing users; hide the strip with no enrolled remote. A remote arrival updates its inactive tab's count and attention marker without moving the current cursor. A machine tab's key must come from the fleet's stable logical owner identity, not its renameable alias. The row model currently has `fleet_origin_alias`, `fleet_origin_installation_id`, and logical locator fields; implementation should specify the canonical owner-key mapping before persisting tab selection. A rename changes only the label and keeps selection. An unenrolled active machine falls back to `All` with a brief notice.

Treat a whole structural root as one tab member, just as tribe panels already inherit a root's effective tribe. Current clans are machine-owned. If a future cross-machine root appears, show it on `All` with a visible mixed-origin diagnostic until an explicit cross-host rule is designed; never split one clan across tabs silently. Count sase agents rather than rendered rows. Show `N+` for bounded or incomplete sources and a stale/offline marker with its cause available in the active header or tooltip. Keep unanswered gates or other needs-you attention visible on inactive tabs using global attention data.

Use one active Agents widget surface, not one mounted tree per machine. Cache only the tab catalog and lightweight per-tab state: selected stable node identity, focused tribe panel, fold/scroll anchor, and detail target. Switching tabs is an in-memory projection; it must not trigger a network refresh, disk parse, or remount all inactive panels. Scope session-sticky tribe-panel keys to tab plus committed query so an empty panel from `apollo` does not linger on `here`. On return, restore by identity and fall back to a nearby surviving row. Cross-tab jumps should choose the target tab, reveal its folded ancestors, and retain the previous location for jump-back. Marks stay global; any action newly scoped to the current tab must say so in its confirmation.

Render one row in the existing Agents header area: for example, `All 42 │ ⌂ here 12 │ apollo 24 !2 │ mac 6`. Reuse the existing tab-strip styling and click geometry, but add a real overflow window or picker with visible hidden-tab counts; compact/micro labels alone do not bound width. Keep tribe colors on tribe panels and use machine accents only on machine tabs. On an empty remote tab, state whether the machine has no agents, the query excludes them, or the feed is unavailable; provide a direct route to Machines diagnostics. Preserve a useful wide layout and a legible narrow terminal layout.

Selecting a machine scope does **not** edit an explicit `machine:` query. If that query excludes the selected tab, explain the conflict and offer a deliberate clear-filter action. This avoids losing a compound query when users browse tabs. It also keeps query-driven history loading and machine index pushdown independent of a fast view switch. Admin Center's existing Enter behavior should select the matching tab when tabs are available; an explicitly typed `machine:` query remains supported.

## Keymap and migration

| Agents action | Current | Recommended |
| --- | --- | --- |
| Previous/next card block | `[` / `]` | `(` / `)` |
| Previous/next machine tab | — | `[` / `]` |

The destination keys overlap Artifacts Files version stepping, but the actions are available on different main tabs. Update `src/sase/default_config.yml`, app keymap types and metadata, fallback bindings, availability and collision rules, help/footer/quickstart text, the block-rail hint, docs, glossary wording, and affected visual goldens together. The current collision allowance for card blocks versus Artifacts tabs becomes two tab-disjoint allowances: Agents tabs versus Artifacts tabs on square brackets, and Agents blocks versus Artifacts Files versions on parentheses. Detect a copied legacy `[`/`]` card-block override at config load, warn with the new keys, and avoid an Agents-tab double binding. Preserve arbitrary custom bindings unless they actually conflict under normal validation.

## Agent Cluster: definition and future clan work

Proposed glossary wording (to add through the SASE memory workflow during implementation):

> **Agent Cluster** — A typed grouping of top-level agent presentation roots used for organization, coordination, or navigation. A clan is a generation-scoped parallel cohort, a tribe is an assignable label, and an Agents view tab is a derived scope. Their shared contract covers stable identity, projected membership, counts, and presentation. Each kind declares its own valid reassignment, wait, fork, and cleanup operations. An agent session is not a cluster: it is one agent whose turns run sequentially.

For a first release, a small TUI tab descriptor is enough. When the same identity and membership rules are needed by CLI, editor, or web clients, place the shared contract in `sase_core` and let Python render it. Avoid a broad `Cluster` table or an enum of every future tab flavor before overlap and ownership requirements exist. In particular, arbitrary saved-query or tribe-as-tab providers would permit one node in several tabs and need policies for counts, attention, marks, and bulk actions; defer them.

A later clan-focused design should remove accidental coupling **only after** it defines compatibility: hood-qualified member names, permanent reservation of the bare clan name, and the unique create-only declarer are candidates for replacement with a typed clan ID, generation record, and atomic launch-time membership. This could allow an arbitrary named *new* agent to join a clan without renaming its identity. It must preserve `%wait:<clan>` target resolution, generation snapshots, summaries, cascade cleanup, existing records, and machine ownership rules until cross-host execution is explicitly supported. Do not change a running or historical member's clan generation as a UI “move”; that would rewrite an active wait barrier or completed history. “Move to tribe” is a metadata mutation; “show in tab” is navigation; “join/create clan” is a prospective launch action. Label those verbs plainly in the UI.

## Delivery and validation

1. **Machine tabs and keymap:** define the owner-key catalog and `All`/`here`/remote scope; reuse the single roster and tribe-panel pipeline; retire the dead Focus/Fleet state; add overflow, attention, empty/error states, and the keymap migration. Keep `BY_MACHINE` for compatibility.
2. **Glossary and common presentation contract:** add the scoped Agent Cluster strand and update the card-block glossary key description through the audited memory workflow. Share a typed descriptor only where it removes duplicated presentation logic.
3. **Clan simplification separately:** specify typed identity, launch planning, durable record migration, old directive compatibility, and frozen generation semantics in `sase_core` before changing Python callers. Do not make it a prerequisite for machine tabs.

Verify local-only and many-machine terminals, aliases renamed or removed, stale and bounded feeds, empty filtered tabs, inactive needs-you state, incoming agents during navigation, cross-tab jumps, folded clans/sessions, marks and destructive action scope, old keymap overrides, and Artifacts Files parentheses. A tab switch should do no I/O; preserve the existing `j`/`k` p95 target below 16 ms and measure tab-switch paint on a loaded large fleet. Quiet refresh should not rebuild inactive widget trees or increase fleet/file-open work.

## Recommendation

Proceed with machine sub-tabs and the requested bracket migration. Keep `All` as the default and make machine membership derived, stable, and visibly health-aware. Add **Agent Cluster** as a typed presentation vocabulary that clarifies the shared grouping shape without erasing clan/tribe behavior. Treat clan mobility as a later core design with immutable historical generations. This gets the fleet-scale benefit promptly while preserving the execution guarantees users already rely on.

### Source reports

The four independent reports are preserved beside this synthesis as `__cdx`, `__grk`, `__mus`, and `__gem`. Audited source snapshots read for this report: `file:explicit:4067084b87dbe702c18563d2`, `file:explicit:a9574d256b14f4a2b4642d36`, `file:explicit:8a95cab203884eafbdee4fac`, and `file:explicit:d8ad7c849c4df9b7aac0dd97`. The synthesis also checked the current SASE TUI, keymap, query, fleet projection, and session documentation directly.
