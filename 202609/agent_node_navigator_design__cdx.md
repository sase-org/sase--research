# Agent Node Navigator for the Agents Tab

Date: 2026-09-25  
SASE source revision reviewed: `27d03a7b7224afca6a9083ea8061b9eecb34d4c9`  
Research repository revision at start: `4435b4a0ee78bbcf344bbb3a96835c78102f1c92`

## Executive conclusion

This is a good feature. The Agents tab now has enough hierarchy—tribe panels, clans,
agent sessions, shell rows, grouping banners, folds, and queries—that spatial navigation
alone is no longer sufficient. A searchable, hint-driven navigator gives the user a
second navigation model: recall a name, narrow, and jump directly. It is especially
valuable for the exact cases in the request: an agent-session shell under a collapsed
session and a clan member under a collapsed clan.

I recommend a dedicated, Agents-only modal overlay called **Node Navigator**, opened by
`"`, implemented separately from both the global backtick modal and the existing sticky
Agents jump panel. It should:

- build an immutable catalog from the complete in-memory, non-dismissed Agents roster
  before view-only hiding, folding, grouping, and query filtering;
- list clan containers, agent nodes, and meaningful shell rows, while excluding every
  non-agent workflow step (not just today's Bash/Python values);
- return a stable agent identity, never a mutable list index;
- preserve the current Agents query and hide settings by installing a small, transient
  “jump reveal” override for the selected node and its ancestors;
- reuse the existing identity-based reveal path to expand tree ancestors, grouping
  banners, and tribe panels;
- render a two-column, near-full-screen list and preview, with the query input visibly
  present but unfocused by default;
- use `Tab` to toggle query/list focus, `Ctrl+N`/`Ctrl+P` to move in either focus state,
  `Enter` to jump, and adaptive alphanumeric hints while the list owns focus;
- show a fast in-memory preview immediately, then optionally enrich it off-thread after
  the highlight has rested for 150 ms.

The most important design point is the transient reveal override. The existing reveal
code can expose fold-hidden descendants, but it cannot select a row removed by the
current Agents query or the “hide non-run agents” view. Clearing those settings as a
side effect would be surprising. A clearly indicated, one-target reveal lease makes the
jump work without destroying the user's view configuration.

## What exists today

There are three similarly named but distinct navigation surfaces:

1. Apostrophe enters in-place entry-jump mode. It annotates currently reachable rows,
   banners, and panels with hints.
2. Backtick opens `JumpAllModal`, a cross-tab overlay for Patches, Agents, and Services.
3. Full stop toggles `AgentJumpPanel`, the sticky roster/legend panel inside the Agents
   detail area.

The requested feature is closest in visual language to (2), but its data and landing
semantics are fundamentally different.

### The backtick modal only knows the rendered list

`NavigationModalMixin.action_jump_to_all_entries()` passes `self._agents` into
`JumpAllModal` and restores a numeric index on dismissal
(`src/sase/ace/tui/actions/navigation/_modals.py:14-59`). The modal copies each Agent
entry with that index and allocates hints once
(`src/sase/ace/tui/modals/jump_all_modal.py:115-196,228-230`). It has no query input,
no highlighted selection model, and no preview. Its invalid-key policy is also to close
the modal (`jump_all_modal.py:307-353`).

That is appropriate for a lightweight cross-tab switcher, but it is the wrong substrate
for hidden-node navigation. `_agents` is the post-fold/post-query list. The loader keeps
the pre-fold roster separately as `_agents_with_children`
(`src/sase/ace/tui/actions/agents/_loading_apply.py:405-434`), and even that roster can
already have the “hide non-run agents” view filter applied. The loader retains the
pre-hide rows as `capacity_agents` before projecting the visible clan tree
(`src/sase/ace/tui/actions/agents/_loading_compute.py:481-517`).

Therefore, merely adding a filter bar and preview to `JumpAllModal` would produce a
polished panel that still fails its primary requirement.

### The hard reveal work is mostly implemented

The existing member-jump path selects by the stable `Agent.identity` tuple. Its reveal
pipeline preflights against a complete roster, expands every required ancestor fold,
re-filters, expands enclosing grouping banners, opens a collapsed tribe panel, and only
then resolves the current index
(`src/sase/ace/tui/actions/navigation/_agent_reveal.py:129-353`).

`MemberJumpNavigationMixin._reveal_agent_row()` adds the UX contract around that
primitive: save jump history, roll history back if reveal fails, move focus into the
row, clear the attempt pin, acknowledge unread state, and request a structural repaint
only when needed (`src/sase/ace/tui/actions/navigation/_member_jump.py:370-493`).

This should be generalized, not duplicated. The new modal should return an identity and
call the same navigation service.

### “Hidden” has several meanings

The implementation should distinguish these layers:

| Hidden by | Present in which roster? | Existing reveal handles it? |
|---|---|---|
| Clan/session fold | `_agents_with_children` | Yes |
| Collapsed grouping banner | `_agents` but not rendered as a stop | Yes |
| Collapsed tribe panel | `_agents` | Yes |
| Active Agents query | omitted from `_agents` | No |
| “Hide non-run agents” | can be omitted even from `_agents_with_children` | No |
| Dismissal/explicit removal | no longer an Agent node | Correctly no |
| Provisional `STARTING` row | deliberately not renderable | Correctly no for v1 |

The fold filter explicitly gates session shell rows through their owning session/workflow
fold and distinguishes ordinary children from hidden internal steps
(`src/sase/ace/tui/models/_fold_filter.py:8-128`). The status-hide filter, by contrast,
is applied during the load pipeline and requires a reload when toggled
(`src/sase/ace/tui/actions/agents/_filter_actions.py:27-35`). These are not equivalent
problems.

## Scope and requirement adjustments

I would make the following adjustments explicit before implementation.

### 1. Define “any node” as any current, non-dismissed, stable Agents node

Include:

- agent clan containers;
- standalone agent nodes and agent-session container nodes;
- agent-session members / agent shells, including monitor and gate shells;
- workflow `agent` steps that represent an LLM shell;
- standalone proc-shell nodes if they are part of the loaded Agents roster.

Exclude:

- dismissed, explicitly removed, and auto-dismissed records (by definition they no
  longer have an Agent node);
- provisional `STARTING` rows, which the Agents panel intentionally refuses to render;
- workflow children that are not agents.

For the last rule, use the future-proof predicate “exclude
`is_workflow_step_child` unless `step_type == "agent"`,” rather than a literal
`{"bash", "python"}` check. Today the model distinguishes workflow-step children from
agent-session children, and identifies agent workflow steps explicitly
(`src/sase/ace/tui/models/agent.py:450-505`). This meets the stated Bash/Python
exclusion and will also avoid leaking a future non-agent step kind into the navigator.

This is a justified narrowing of “any”: dismissed records belong in revival/history
surfaces, and a provisional row cannot be a reliable landing target.

### 2. Do not mutate the user's query or hide preference

The obvious implementation—clear the Agents query and switch off
`hide_non_run_agents`—would technically reveal the target but would make a navigation
action rewrite persistent view state. I recommend a transient reveal lease instead:

- the lease stores one stable target identity;
- the view projection unions that target and the minimum ancestor chain back into the
  post-query result;
- the filter bar/info strip shows a small `JUMP REVEAL` indicator so the exception is
  not mysterious;
- the lease is replaced by the next navigator jump and cleared when the user changes a
  query/visibility setting, dismisses the target, or intentionally navigates away.

Auto-refresh may preserve the lease while the same identity remains selected. If the
identity disappears, it must clear the lease and report that the target changed.

### 3. Scope archive history separately from visual hiding

The navigator should open instantly from the current non-dismissed in-memory catalog.
It must not synchronously scan the full archive. If the current agent load is known to
be history-incomplete, an explicit `"` press may schedule the established coalesced
full-history refresh in the background, but first paint and key handling must use the
cache. The title can say `loaded catalog` until reconciliation completes.

For an initial release, I would define the guarantee as “every current node known to
the Agents roster, whether or not the current view renders it,” not “every historical
artifact ever recorded.” The latter is an artifact-browser concern and would compromise
the promised speed.

### 4. Use a modal overlay, not another persistent detail panel

The requested surface is large, transient, keyboard-modal, and needs two columns. A
`ModalScreen` matches the backtick interaction while avoiding permanent pressure on the
Agents layout. Call the class `AgentNodeNavigatorModal`; do not call it
`AgentJumpPanel`, because that name already belongs to the full-stop roster legend.

### 5. Keep the query intentionally simple

This input should fuzzy-match node names and their displayed ancestry aliases. It should
not reuse the full structured Agents query language: that would duplicate the main
filter bar and make the focus/hint mode harder to learn. Reasonable searchable aliases
are presented name, concrete agent/session name, clan name, and the displayed
breadcrumb. Status and arbitrary detail text should not silently affect matches when
the promise is “filter by node name.”

## Recommended interaction design

### Layout

Use roughly 92% of terminal width (maximum around 170 cells) and 88% of height. The
current backtick modal is 85%/130 cells by 80%
(`src/sase/ace/tui/styles.tcss:5949-5985`); the preview warrants more room. On terminals
narrower than about 100 cells, stack preview below the list or hide the enrichment body
while retaining the identity summary.

```text
╔═ ✦ Node Navigator ─ 137 nodes ─ hints active ═════════════════════╗
║ Search  Tab to type…                                               ║
╟──────────────────────────────┬─────────────────────────────────────╢
║ [0] ◈ research.8             │ research.8 › cdx                    ║
║ [1]   ◇ research.8.cld       │ AGENT SHELL · RUNNING               ║
║ [2]   ◇ research.8.cdx       │                                     ║
║ [3]   ◇ research.8.gem       │ Project   sase                      ║
║ [4]   ⚙ research.8--mon      │ Model     gpt-… · xhigh             ║
║ [5] ◆ deploy                 │ Runtime   03:42                      ║
║                              │                                     ║
║                              │ Prompt / output excerpt (deferred)  ║
╟──────────────────────────────┴─────────────────────────────────────╢
║ key jump  ^N/^P select  Enter jump  Tab search  Esc/" close       ║
╚════════════════════════════════════════════════════════════════════╝
```

Use the existing Agents colors and glyph vocabulary. Hints stay bright yellow, the
highlight gets a restrained accent bar, and the preview uses muted labels with status as
the only strong semantic color. The result count and mode (`hints active` / `typing`)
should always be visible.

### Focus and keyboard state machine

On mount, focus the `OptionList`, not the input. The highlighted row should be the
currently selected node when it exists in the catalog, otherwise the first candidate.

In list/hint mode:

- alphanumeric input is interpreted as an adaptive hint;
- `Ctrl+N` / `Ctrl+P` moves the highlight with wrap;
- `Enter` jumps to the highlighted node;
- `Tab` clears a pending hint and focuses the query input;
- `Esc` or `"` closes;
- an invalid hint clears the pending prefix and leaves the modal open.

In query mode:

- printable keys edit the query;
- `Ctrl+N` / `Ctrl+P` still moves the result highlight;
- `Enter` jumps to the highlighted result;
- `Tab` unfocuses the input and returns to hint mode;
- `Esc` closes consistently.

Do not bind `j`, `k`, or `q` as commands here: they must remain available as hint
characters. This is why the requested `Ctrl+N` / `Ctrl+P` choice is particularly good.
Those keys cycle decks in the underlying Agents screen, but modal-scoped interception is
unambiguous and should be advertised in the footer.

### Filtering and hints

Use the existing Rust fuzzy matcher through `sase.core.fuzzy_facade`; it provides match
runs for highlighting and a canonical sort key
(`src/sase/core/fuzzy_facade.py:12-38`). Empty input preserves canonical tree order.
Non-empty input ranks the best alias per node, with original tree order as the final
tiebreak.

Filtering is data-scaled work, so run it in an exclusive thread worker with a monotonic
query generation. Publish only the latest generation. While a query result is pending,
typing remains instant; if the user Tabs back early, keep hint dispatch disabled until
the current result is published. Never read files, stat paths, or hydrate Agent records
in the input handler.

Reallocate hints over the published filtered list. The existing allocator already knows
base-62 characters, case-sensitive event normalization, and prefix-free allocation
(`src/sase/ace/tui/actions/navigation/jump_hints.py:13-14,75-126`). For this feature,
generalize prefix-free allocation beyond the current two-character/3,844-target ceiling,
or add a sibling unbounded allocator without changing existing callers. Every rendered
candidate must have a hint; silently truncating the hint map violates the feature's core
contract.

When the first character of a multi-character hint is pending, visibly show it and dim
rows whose hints no longer match. Do not use a timeout. Query changes clear the pending
prefix.

### Preview

The preview should be useful before it is exhaustive.

Paint immediately from the immutable catalog snapshot:

- full ancestry breadcrumb and node kind;
- presented and concrete identity names;
- status/activity, tribe, project/Patch, workspace/machine;
- provider/model/effort and elapsed/start/stop time;
- shell-specific state (monitor/gate/proc) or clan/session member counts;
- recorded error summary when already in memory.

After the highlight rests for 150 ms, optionally hydrate a copied row and load bounded
prompt/reply/log excerpts in a thread worker. Revalidate both modal generation and
highlighted identity before applying the result. The repository already uses
`DetailPanelDebouncer` to make highlight paint immediate and coalesce expensive detail
work (`src/sase/ace/tui/util/debounce.py:21-70`); use the same pattern. Do not embed the
full `AgentDetail` widget: it owns decks, persistence, async enrichments, and selection
assumptions that are inappropriate for a transient picker.

Cancel filter and preview workers on unmount. Guard programmatic `OptionList.highlighted`
changes so the echoed `OptionHighlighted` event cannot repaint an obsolete preview.

## Data and navigation architecture

### 1. Publish a navigation catalog source at the load boundary

Add a roster specifically named for its contract, such as
`_agents_navigation_roster`. Construct it in the existing worker-side prepared-apply
pipeline after dismissal/explicit-removal filtering but before `hide_non_run_agents`,
fold filtering, grouping, and the Agents query. Project clan containers and mixed/fleet
rows there once, then publish it with the other prepared rosters.

Do not make the modal reconstruct “all nodes” by concatenating `_agents`,
`_hideable_agents`, runtime children, and fleet rows. That would duplicate projection
rules, risk identity duplicates, and inevitably drift from the loader.

The modal receives immutable `AgentNodeChoice` snapshots, not live indices:

```python
@dataclass(frozen=True, slots=True)
class AgentNodeChoice:
    identity: AgentIdentity
    kind: NodeKind
    name: str
    aliases: tuple[str, ...]
    breadcrumb: tuple[str, ...]
    status: str
    depth: int
    canonical_order: int
    preview: AgentNodePreviewSeed
```

Deduplicate by identity. Preserve tree order for an empty query. A pure catalog builder
is easy to unit-test and keeps Textual concerns out of the domain projection.

### 2. Return identity and revalidate

The modal result should be `AgentNodeNavigatorResult(identity=...)`. Never return an
index. Background refresh, query filtering, fold expansion, and panel reordering all
make an index stale. On activation, revalidate that exactly one current catalog row has
the identity before mutating any fold or selection state.

If the identity vanished, keep existing navigation state unchanged and notify “Node
changed; jump cancelled.” This matches the stale-map behavior already used by member
jump.

### 3. Generalize the reveal service

Extract the orchestration currently private to member jump into a shared
`jump_to_agent_identity(...)` path:

1. preflight the identity against `_agents_navigation_roster`;
2. install/replace a transient reveal lease if view filters exclude it;
3. rebuild the view projection without disk I/O;
4. run the existing ancestor/group/panel reveal logic;
5. select by identity, update history/unread state, and repaint selectively;
6. roll back history and the tentative lease if any step fails.

The low-level `_agent_reveal.py` code should continue to own ancestry validation and
layer expansion. The catalog/modal should not know fold keys or panel indices.

### 4. Keep jump history coherent

A Node Navigator jump should push the same Agents anchor history as apostrophe/member
jump, so `Ctrl+O` and forward jump continue to work. Store the source anchor before
installing the reveal lease. If the source row would disappear when the lease changes,
rebase it using the existing identity-based helper.

## Keymap and integration details

The configured key should be Textual's `quotation_mark`, not a raw quote. Against the
installed Textual 8.0.1, `"` normalizes to `quotation_mark`. SASE's current key validator
does not accept that name and renders it literally; `_KEY_DISPLAY` contains
`apostrophe` and `grave_accent` but no `quotation_mark`
(`src/sase/ace/tui/keymaps/key_validation.py:7-45`). Add
`"quotation_mark": '"'` there first.

Add an action such as `jump_to_agent_node` to:

- `src/sase/default_config.yml` (the default key must be updated for any keymap change);
- `AppKeymaps` and keymap metadata;
- app action availability, gated to the Agents tab, no prompt input ownership, and a
  ready navigation roster;
- command/help metadata and the Agents help guide;
- the navigation action mixin;
- modal lazy exports and `styles.tcss`.

Also update any hardcoded fallback binding used by tests/legacy config. Availability
must be tab-specific so `"` remains ordinary input inside prompt/query editors and other
tabs.

## Reliability and performance requirements

I would make these acceptance thresholds explicit:

- cached open to first paint: under 50 ms at 2,000 catalog rows;
- `Ctrl+N` / `Ctrl+P` key-to-highlight paint p95: under 16 ms;
- query keystroke handler: O(1) scheduling only, no disk or synchronous catalog scan;
- latest fuzzy result visible within 100 ms p95 at 10,000 rows on the benchmark host;
- preview metadata paints immediately; disk-enriched preview never blocks input;
- no full Agents-list rebuild when jumping to an already visible row;
- at most one structural rebuild when revealing a hidden row;
- stale identity, malformed ancestry, and a refresh during selection leave navigation
  state consistent and produce a short warning rather than an exception.

The TUI performance guidance already requires off-thread data-scaled work, immediate
highlight with debounced detail, generation revalidation, cached reads, and selective
updates. This feature should be measured with the existing `SASE_TUI_PERF` and
`SASE_TUI_TRACE` infrastructure rather than judged only by small fixtures.

## Test plan

### Pure model tests

- catalog includes a hidden clan member and every concrete agent-session shell;
- catalog includes workflow `agent` steps but excludes Bash, Python, and unknown future
  non-agent workflow steps;
- dismissed/removed/provisional rows are absent;
- identities are unique and empty-query order matches tree order;
- aliases and breadcrumbs distinguish equal leaf names;
- fuzzy ranking and match spans are deterministic;
- unbounded hint allocation is prefix-free at 62, 63, 3,844, and above 3,844 entries.

### Modal interaction tests

- list owns focus on mount; typing a hint jumps while the input remains unfocused;
- Tab toggles focus in both directions and clears a pending hint;
- printable characters edit only while the input owns focus;
- `Ctrl+N` / `Ctrl+P` wrap in both modes;
- Enter selects in both modes; Escape and `"` cancel;
- invalid hints do not close the modal;
- query generation rejects stale worker results;
- filter rebuild preserves highlighted identity when still present and otherwise selects
  the first result;
- programmatic highlight echoes do not apply stale previews;
- unmount cancels workers.

### Reveal integration tests

- visible row: identity changes with no structural rebuild;
- collapsed agent session: expands and selects a shell;
- collapsed clan plus collapsed group plus collapsed tribe panel: expands all layers and
  selects the member in one rebuild;
- main query-hidden and status-hide-hidden targets: transient reveal lands visibly while
  the committed settings remain unchanged;
- leaving the revealed row clears the lease and restores the normal projection;
- stale/ambiguous identity rolls back history and reveal state;
- auto-refresh preserves a valid selected lease and clears a vanished one;
- back/forward jump works after a navigator jump.

### Keymap, help, visual, and performance tests

- `quotation_mark` validates and displays as `"`;
- action is available only on Agents and is suppressed while an editor owns printable
  keys;
- default config, registry, command palette, and help guide agree;
- PNG snapshots cover wide, narrow/stacked, query-focused, pending-prefix, no-results,
  and enriched-preview states;
- benchmark opening/filtering/navigation on large synthetic clan/session trees.

## Suggested implementation sequence

1. **Semantics and catalog:** add the pre-view navigation roster and pure catalog
   builder; lock inclusion/exclusion behavior with tests.
2. **Keymap and modal shell:** add `quotation_mark`, the Agents-only action, focus state
   machine, list, adaptive hints, and identity result.
3. **Fast preview:** add immediate in-memory rendering, then debounced/cancelable
   off-thread enrichment.
4. **Reveal lease:** generalize identity navigation, add query/status-filter override,
   and integrate jump history.
5. **Hardening:** stale-refresh tests, visual snapshots, large-roster benchmarks, help,
   and accessibility/narrow-terminal polish.

The reveal lease should not be deferred as optional polish: without it, the headline
claim “jump to hidden nodes” is only true for folds and false for filters.

## General critique

The concept is strong, but the Agents tab already has apostrophe jump, backtick global
jump, the full-stop roster panel, the main query bar, and deck navigation. A fourth
navigation surface succeeds only if each tool has a crisp sentence:

- `'`: jump among what is on this Agents layout;
- `` ` ``: switch quickly among visible entries across tabs;
- `.`: inspect/jump within the selected container's roster;
- `"`: find any current Agents node by name and reveal it.

The quote pairing is memorable and ergonomic on common keyboards: apostrophe is
spatial/current-view jump, double quote is global-within-Agents jump. It is still a
configurable binding, which matters for non-US layouts.

I would not replace backtick with this feature. Cross-tab switching benefits from the
small, instant modal and does not need an Agent-specific preview. I would also not reuse
the main Agents query bar inside the overlay: local fuzzy recall and durable structured
filtering are different jobs.

## Recommended solution

Build a new `AgentNodeNavigatorModal` on `quotation_mark`, backed by a loader-published,
pre-view-filter navigation roster. Present a large two-column fuzzy picker whose input is
unfocused by default, whose every result has an adaptive prefix-free hint, and whose
selection works with hints, `Ctrl+N`/`Ctrl+P`, or Enter. Return a stable identity.

Land the target through a shared identity-navigation service that reuses the existing
fold/group/panel reveal machinery and adds one transient, visibly indicated reveal lease
for rows hidden by the main query or non-run filter. Exclude dismissed/provisional rows
and all non-agent workflow steps; include hidden clan members and agent-session shells.
Render preview metadata from memory immediately and enrich only after a debounced,
off-thread, generation-checked load.

That design is intuitive because the two focus modes are explicit, reliable because
indices and stale mappings never cross the modal boundary, fast because all keystroke
paths are memory-only, and visually coherent with the best existing Agents and picker
patterns without coupling the feature to the global backtick modal.
