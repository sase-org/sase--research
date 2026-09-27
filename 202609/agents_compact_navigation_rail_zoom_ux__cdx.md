# Agents compact navigation rail and zoom-state UX

**Researcher:** cdx  
**Date:** 2026-09-27  
**Inspected SASE revision:** `092fb8bf106f624d63a6fa419e816095fce48fe8`

## Executive conclusion

The underlying idea is good: `Ctrl+S` should trade detail for space, not trade all
orientation for space. The present two-cell collapsed spine preserves only relative
position; it does not tell the user which tribes, groups, or nodes exist, and it makes
`j`/`k` navigation effectively blind. A compact semantic tree rail would be a material
improvement.

I would not implement the rail as a stack of icons alone. Tribes and most group names
are user-defined, so no universal icon vocabulary can identify them. The strongest
design is a **fixed-width, 14-cell mini-tree** that preserves the expanded sidebar's
vertical order and fold structure, combines the existing semantic glyphs with short
text tokens, and keeps the current selection visibly highlighted. It should reuse the
existing `AgentList` widgets and navigation identity rather than build a second,
synchronized sidebar model.

Zoom must be a third, visibly distinct presentation state, not a special case of
"collapsed." In zoom, the navigation column should remain completely absent, while the
focused deck gets an unmistakable gold `ZOOMED` badge and a paint-only outer focus
frame. The info row should say `ZOOMED · Z restore` and omit the misleading collapsed
node count.

## What exists now

There is a small but important discrepancy between the request and the inspected
checkout. The request describes the collapsed sidebar as completely invisible. At the
inspected revision, commit `71fff39d1` (2026-09-24) has already introduced a
`NodeSpine`:

- `src/sase/ace/tui/widgets/decks/node_spine.py` renders a two-cell `»` plus a
  proportional scrollbar thumb.
- `src/sase/ace/tui/styles.tcss` hides `#agent-list-container` for
  `.-nodes-collapsed` and shows the two-cell spine instead.
- `DeckAreaState.nodes_collapsed` is used both for an ordinary `Ctrl+S` collapse and
  while `zoom_snapshot` is active.
- `AgentInfoPanel` distinguishes the states only by adding the word `zoom` ahead of
  `nodes N/N · Ctrl+S`.
- The visual goldens `agents_decks_collapsed_single_120x40.png` and
  `agents_decks_zoomed_120x40.png` are almost identical: both show the same full-width
  deck and the same gold line at the left; only the small info-row label differs.

So the sidebar is no longer literally invisible, but it is still **semantically
invisible**. The spine represents position, not structure or identity. That does not
satisfy the intent of the proposed feature.

Several existing implementation choices are worth preserving:

- `Z` snapshots layout, panels, focus, ratio, and the pre-zoom collapse preference,
  then restores that snapshot exactly on a second `Z`.
- Zoom itself is not persisted; the effective non-zoomed deck layout is persisted.
- `Ctrl+S` while zoomed exits zoom and opens the nodes, rather than leaving an
  impossible "zoom plus sidebar" combination.
- The agent tree already has a single ordered `TreeEntry` projection, stable option
  IDs, fold registries, per-tribe `AgentList` panels, and incremental row patching.
- Existing visual vocabulary is rich: configured tribe icons, hierarchy bars and
  guides, status-bucket glyphs, workflow/proc/monitor/gate glyphs, selection chrome,
  unread and lane-count chips, and consistent accent colors.

This is presentation-only TUI behavior. It belongs in this repository's Python/Textual
layer; it does not cross the Rust core boundary.

## UX evidence and implications

Compact rails are a well-established way to retain navigation while reclaiming content
space. VS Code separates its wide Primary Side Bar from its narrow Activity Bar, and
the latter preserves destinations and contextual indicators. It also treats Zen Mode
as a separate focus mode that hides the surrounding UI rather than making it look like
an ordinary collapsed sidebar. [VS Code user interface](https://code.visualstudio.com/docs/editing/getting-started/userinterface)

JetBrains similarly keeps icon-bearing tool-window bars after a tool window is hidden,
while providing a separate "Hide All Windows/Restore Windows" focus command. It lets
users reveal names but does not confuse the tool-window stripe with the open tool
window itself. [IntelliJ IDEA tool windows](https://www.jetbrains.com/help/idea/tool-windows.html)

Apple's sidebar guidance supports hiding a sidebar to make room for detail, recommends
familiar symbols, and says compact navigation can be preferable when space is limited.
It also warns that hierarchy needs deliberate grouping and succinct labels.
[Apple Human Interface Guidelines: Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars)

The analogy has limits. VS Code and JetBrains rails contain a small, mostly fixed set
of destinations. SASE's rail would represent an arbitrary, live, hierarchical roster.
An icon-only treatment is therefore much riskier. Nielsen Norman Group's icon research
is directly applicable: recognizing the pictured object does not guarantee
understanding its meaning, and navigation icons are particularly ambiguous without
labels. [NN/g: Icon Usability](https://www.nngroup.com/articles/icon-usability/)

The accessibility consequence is also concrete. Status, selection, focus, and tribe
identity must not depend on hue alone. W3C guidance calls for an additional visual cue
when color conveys meaning and at least 3:1 contrast for meaningful UI graphics and
authored focus indicators. [WCAG use of color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color),
[WCAG non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)

The design implication is: use icons as redundant semantic cues, not as the only
labels. In a terminal, a two- or three-cell text token is cheap and dramatically
improves information scent.

## Critique of the proposed requirements

### What is right

1. **Ordinary collapse should retain context.** A user who wants a little more deck
   space normally still needs to know what is running, waiting, failed, or selected.
2. **Zoom should remain truly immersive.** A zoom command promises maximum attention
   on one deck. Keeping the rail visible in that state would weaken the command.
3. **Reuse the current icon language.** The UI already has meaningful glyphs and color
   roles. A new rail should feel like a compressed version of SASE, not a foreign
   toolbar.
4. **Make zoom unmistakable.** The current one-word status difference is too subtle,
   especially because the two states currently share the same left-edge treatment.

### Requirements I would adjust

1. **Change "every tribe, group, and node" to "every currently rendered tribe, group,
   and node."** Existing folds must remain authoritative. Showing descendants of a
   collapsed group in the compact rail would make the expanded and compact views
   disagree, defeat folding, and overwhelm large rosters. A folded subtree remains one
   represented summary row with its count.
2. **Do not require a unique icon for every group type or identity.** Status groups
   have good existing glyphs (`▶`, `…`, `⏳`, `✗`, `✓`); arbitrary project, Patch,
   name-root, machine, date, and tribe labels do not. Use a tier/fold glyph plus a short
   visible token. An invented pictogram for each dynamic grouping would be harder to
   learn than the words it replaces.
3. **Treat "collapsed" as compact, not hidden.** Update command/help text from
   "Collapse/expand node panel" to "Compact/expand node panel." Reserve "hidden" for
   zoom. This vocabulary prevents future code and documentation from conflating the
   states again.
4. **Keep focus in the mini-tree when the user compacts it from the sidebar.** The
   current code moves focus away because the list becomes `display: none`. Once the
   list remains visible and actionable, moving focus is surprising and unnecessary.
5. **Do not auto-expand on focus or hover.** Overlay expansion would cause horizontal
   jitter, cover deck content, and turn ordinary mouse movement into a layout event.
   A stable rail, an explicit expand affordance, and tooltips are more reliable.

## Options considered

| Option | Strengths | Problems | Verdict |
|---|---|---|---|
| Keep the two-cell spine and add colored ticks | Very small, low implementation cost | No identities or hierarchy; color-heavy; blind keyboard navigation | Reject |
| One icon per tribe/group/node | Clean and familiar for fixed app destinations | Dynamic names have no recognizable icons; dense; ambiguous; poor accessibility | Reject |
| Auto-overlay the full sidebar on focus/hover | Full information on demand | Layout jitter, accidental activation, covers content, difficult keyboard/mouse parity | Reject |
| Separate compact `NodeRail` widget | Can be optimized specifically for the rail | Duplicates tree, folds, selection, scrolling, and patch synchronization | Avoid |
| Compact rendering mode on the existing panel/list widgets | Same identity, order, folds, scroll and selection; lowest consistency risk | Requires a deliberate compact formatter and cache-key work | **Recommend** |

## Proposed interaction model

There should be three explicit visual modes:

| State | Node column | Deck chrome | Persistence |
|---|---:|---|---|
| Expanded | Existing dynamic 60–130 cells | Normal | Persisted |
| Compact | Fixed 14 cells | Normal | Persisted |
| Zoomed | 0 cells | Gold `ZOOMED` badge + outer frame | Transient snapshot |

State transitions should remain deterministic:

| Current state | `Ctrl+S` | `Z` |
|---|---|---|
| Expanded | Compact | Zoomed; remember Expanded |
| Compact | Expanded | Zoomed; remember Compact |
| Zoomed from Expanded | Exit zoom to Expanded | Restore Expanded |
| Zoomed from Compact | Exit zoom to Expanded | Restore Compact |

The asymmetric `Ctrl+S` behavior in zoom is intentional: that key asks to show the
nodes, so it must end zoom. The info row should make it discoverable with wording such
as `Ctrl+S show nodes`.

### Compact rail anatomy

Use a fixed width of **14 terminal cells**, including border and scrollbar. This is
small enough to recover most of the current 60-cell sidebar but large enough for a real
semantic projection. Remove horizontal padding in compact mode.

Each expanded-sidebar row maps to exactly one compact row in the same vertical order:

```text
┌ » 12/47 ┐  explicit expand target and position
│ ⌂ @d  3 │  tribe: configured icon + short token + count
│ ▾▌ sa   │  group: fold state + tier glyph + token
│ │▾▶ ru  │  subgroup: guide + fold/status glyph + token
│ │ ●cd ✓ │  agent: guide + kind/identity + status
│ │ ├⚙mo  │  monitor/proc: existing glyph
│ │ └⋔ga  │  gate: existing glyph
└─────────┘
```

This is a conceptual wireframe, not a literal glyph lock. The important grammar is
stable position: **guides → fold/kind → short identity → status**.

- **Tribes:** use the configured icon (`⌂`, `▲`, `†`, `◆`, `◉`, or a custom icon),
  followed by a one-to-three-cell token. If no icon is configured, use `@` plus the
  token. Color remains a redundant identity cue, never the only cue.
- **Groups:** reuse `▌`, `▎`, and the existing status glyphs, but add `▾`/`▸` for
  expanded/collapsed state and a short token derived from the label. Tokens should be
  the shortest unique prefixes within the visible sibling scope where practical.
- **Nodes:** reuse `⚙` for monitors/procs, `⋔` for gates, `❯` for command steps, and
  `≡` for workflows. Add only three fixed category shapes that the present list lacks:
  ordinary agent `●`, sequential session `≣`, and parallel clan `⋈`. Verify every
  glyph is one terminal cell in the canonical font stack; fall back to `A`, `S`, and
  `C` if it is not.
- **Status:** reuse the existing shape vocabulary (`▲`, `✗`, `◐`, `▶`, `…`, `⏳`,
  `✓`) and current styles. Shape plus color preserves meaning on monochrome and
  color-deficient displays.
- **Deep nesting:** render at most five one-cell ancestor guides, replacing omitted
  leading depth with `…`. Never truncate the kind, status, or final identity token.
- **Selection:** retain the current filled highlight plus thick gold left edge. A
  selected whole tribe panel keeps the existing gold outline treatment. Do not use
  color alone.
- **Labels:** when rail focus changes, show the selected item's full breadcrumb in the
  Agents info row (for example `@epic / Running / research.h.cdx`). Mouse hover may
  show the same breadcrumb as a tooltip, but the tooltip is supplemental.
- **Mouse expansion:** retain an explicit `»` click target at the top of the rail and
  make the info-row `nodes N/N` segment clickable. Do not make every row expand the
  rail; row clicks must keep their navigation meaning.

The 14-cell value should be a code constant, not user configuration in the first
version. It is easier to validate one strong composition, and this feature should not
create a new matrix of subtly broken widths before usage demonstrates a need.

### Zoom treatment

Zoom needs redundant, structural cues:

1. Add a paint-only gold outer outline around the visible zoomed deck, preserving the
   deck's own teal/green/blue/pink border inside it.
2. Prefix the deck border title with a reverse-gold `ZOOMED` badge. The word is more
   reliable than a novel maximize icon; a small glyph can accompany it but must not
   replace it.
3. Replace the current info text `zoom · Z · nodes N/N · Ctrl+S` with an explicit
   `ZOOMED · Z restore layout · Ctrl+S show nodes`. Do not display node position while
   the nodes are intentionally absent.

This treatment is visually stronger without adding motion. Animation would add little
in a terminal, complicate snapshots, and risk work on Textual's serial message pump.

## Implementation shape

### 1. Derive presentation mode without migrating persisted state

Keep `DeckAreaState.nodes_collapsed` for compatibility and derive a presentation enum:

```python
def node_panel_presentation(state: DeckAreaState) -> NodePanelPresentation:
    if is_zoomed(state):
        return NodePanelPresentation.HIDDEN
    if state.nodes_collapsed:
        return NodePanelPresentation.COMPACT
    return NodePanelPresentation.EXPANDED
```

This makes the distinction explicit while retaining the proven snapshot and persistence
behavior. Rename `_sync_nodes_collapsed_chrome()` to reflect all three modes and apply
separate CSS classes such as `-nodes-compact` and `-deck-zoomed`.

### 2. Reuse `AgentList`; do not maintain a parallel tree

In compact mode, keep `#agent-list-container` mounted and set its width to 14. Add a
compact density to the existing render pipeline:

- Generate compact `Option` content from the same `TreeEntry` sequence used by
  `_agent_list_build_rebuild.py`.
- Preserve the same option IDs, `_row_entries`, banner maps, fold registry, panel
  ordering, selection identity, and scroll anchors.
- Include density in render and panel-paint cache keys.
- Make incremental `patch_row()` use the compact formatter while compact.
- Ignore dynamic `WidthChanged` requests in compact mode so long labels can never
  expand the fixed rail.
- A density toggle may synchronously reformat the already loaded in-memory rows; it
  must not perform disk I/O, reload agents, or remount tribe panels.

This is safer than a new `NodeRail`, because the latter would need to mirror every
future change to group folds, clans, sessions, transient jump hints, marks, unread
state, and panel focus.

### 3. Keep hot navigation cheap

`j`/`k` should continue to update the highlight immediately and debounce only deck
detail. Compact navigation must not rebuild the tree per keypress. Density changes are
rare; live row changes should continue through the existing selective patch path. A
compact renderer should use only already-loaded fields and pre-resolved tribe display
configuration.

### 4. Retire or narrow `NodeSpine`

Once the compact list renders, the present full-height `NodeSpine` is redundant. Its
position computation can move into the compact header (`» 12/47`), and the widget can
be removed. If retaining it temporarily lowers migration risk, restrict it to the top
expand affordance; do not leave a second full-height scroll indicator beside the rail's
own scrollbar.

## Reliability and acceptance criteria

The feature should not be considered complete without all of the following:

### Pure/model tests

- Every currently rendered expanded `TreeEntry` produces one compact row in identical
  order and with the same selection identity.
- Folded descendants remain absent; a collapsed group produces one summary row.
- Compact text never exceeds its cell budget for long Unicode names, emoji tribe
  icons, deep hierarchy, empty panels, and colliding prefixes.
- Tokens are deterministic, and the kind/status portions are never truncated.
- Density participates in every relevant render-cache and incremental-paint key.

### State-transition tests

- Expanded ⇄ Compact round-trip preserves selected identity, focused tribe, fold
  state, deck layout, deck focus, card, and scroll.
- `Z` from Expanded restores Expanded; `Z` from Compact restores Compact.
- `Ctrl+S` from Zoom exits to Expanded and drops the zoom snapshot.
- Zooming panel 0 and panel 1 in both split orientations restores the exact ratio and
  focus.
- Restart persists Expanded/Compact but never Zoomed.

### Interaction tests

- `j`/`k`, `h`/`l`, jump hints, mark mode, whole-panel focus, and row actions target
  the same objects at both densities.
- Compacting while the list has focus retains a visible focus indicator.
- Programmatic highlight updates continue to suppress queued `OptionHighlighted`
  echoes.
- Clicking a compact row selects it; clicking `»` or the node-count affordance expands
  the rail without changing selection.

### Visual tests

Add controlled PNG goldens for:

- Compact single and split decks with multiple tribes, groups, clans, sessions,
  monitors, gates, failures, unread rows, and one user-configured tribe icon.
- Compact whole-panel focus and a deeply nested selected row.
- Zoom entered from both Expanded and Compact, proving the rail is absent and zoom
  chrome is unmistakable.
- 120×40 and a narrow 90×40 terminal, dark and light themes.

The goldens should be judged for structure, not merely updated. In particular, verify
that the outer gold zoom frame does not erase deck identity, that every essential glyph
meets contrast requirements, and that wide/emoji glyphs do not shift columns.

### Performance

- A quiet compact rail causes no additional disk reads or periodic work.
- `j`/`k` remains below the project's p95 16 ms target.
- Navigation does not trigger full agent-list rebuilds; live status changes stay on
  incremental patching when group membership is stable.

## Risks and mitigations

- **Too much information in 14 cells:** keep only hierarchy, kind, short identity,
  status, and selection. Counts belong on tribe/group summary rows, not every leaf.
- **Unfamiliar glyphs:** use only three new fixed category glyphs, pair every row with
  a short token, expose the full breadcrumb, and include a legend in Agents help.
- **Token churn when siblings appear:** use deterministic shortest prefixes and prefer
  the leaf segment of dotted names. Do not renumber existing nodes by list position.
- **Unicode width variance:** constrain all new glyphs with Rich cell measurement and
  the canonical screenshot font stack; provide ASCII-letter fallbacks.
- **Two sidebar implementations drifting:** avoid the risk by adding density to the
  existing `AgentList` instead of creating a separate navigation widget.
- **Zoom becoming visually noisy:** use one word badge and one outer frame, not a
  recolored deck body or animation.

## Sources

- SASE source and PNG visual goldens at revision
  `092fb8bf106f624d63a6fa419e816095fce48fe8`, especially
  `widgets/decks/node_spine.py`, `widgets/_agent_detail_deck_layout.py`,
  `widgets/_agent_list_build_rebuild.py`, `actions/agents/_display_panel_*`,
  `models/agent_deck_persistence.py`, `styles.tcss`, and
  `tests/ace/tui/visual/snapshots/png/agents_decks_{collapsed,zoomed}*`.
- [Apple Human Interface Guidelines: Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars)
- [VS Code: User interface](https://code.visualstudio.com/docs/editing/getting-started/userinterface)
- [IntelliJ IDEA: Tool windows](https://www.jetbrains.com/help/idea/tool-windows.html)
- [Nielsen Norman Group: Icon Usability](https://www.nngroup.com/articles/icon-usability/)
- [W3C: Understanding SC 1.4.1, Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color)
- [W3C: Understanding SC 1.4.11, Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)

## Recommended solution

Implement a three-state node-panel presentation: **Expanded**, **Compact**, and
**Zoom-hidden**. `Ctrl+S` toggles Expanded/Compact; `Z` temporarily forces Zoom-hidden
and restores the exact prior state. Compact is a fixed 14-cell semantic mini-tree built
by adding a compact density to the existing `AgentList` render pipeline. It shows every
currently rendered tribe, group, and node in the same order and fold structure, using
existing glyphs plus short visible identity tokens, strong selection chrome, and a
clickable expand affordance. Zoom shows no rail and instead adds a reverse-gold
`ZOOMED` badge, a paint-only gold outer frame, and explicit restore text.

This approach preserves the user's mental map, avoids ambiguous icon-only navigation,
keeps one source of truth for selection and folding, respects the established hot-path
performance constraints, and makes collapse versus zoom impossible to mistake.
