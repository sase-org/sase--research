---
create_time: 2026-08-26
updated_time: 2026-08-26
status: research
tags:
  - ace
  - artifacts
  - artifact-links
  - navigation
  - tui
  - ux
---

# Artifact Links Everywhere: A Universal Links Panel for ACE

**Research question.** How should ACE expose the artifact-link neighborhood of the
currently selected SASE entity on every top-level tab, make following a link nearly
instant, keep the interaction consistent when the destination lives on another tab or
inside a filtered Artifacts pane, and remain completely invisible when the selected
entity has no links?

**Scope.** Current `sase` source and visual snapshots on 2026-08-26; epic `sase-tj`
(Artifacts → Agent pane), epic `sase-tw` (artifact-link durability, derivation, and
typed ACE edges), their relevant phase beads and plans, the live project link
aggregate, and official interaction documentation for VS Code, Neovim, and Textual.

---

## Bottom line

Build one app-level **Links Peek Tray** at the seam between the active tab and ACE's
footer.

- Collapsed, it is a one-line **Link Rail**. It appears automatically only when the
  current entity has at least one link and summarizes the typed neighborhood from that
  entity's perspective.
- `$` expands the same widget upward into a compact tray; `$` or `Escape` collapses it.
- The tray assigns visible jump hints. `$1` follows the first link in two logical key
  presses; `j`/`k` + `Enter` handles browsing without a separate interaction model.
- A jump records a stable, cross-tab location in ACE's existing jump history.
  `Ctrl+O` returns and `Ctrl+Shift+O` goes forward, matching the keys ACE already
  teaches on all three tabs.
- The original tab stays visible while the tray is open. The tray reserves a bounded
  band at the bottom rather than dimming or covering the work surface.
- The tray shows only typed artifact-link edges. The existing Artifacts **Relations**
  panel keeps structural hierarchy/family edges; artifact links move out of it so ACE
  does not present the same graph twice.

This is the best synthesis of ACE's existing relation rail, VS Code's inline Peek,
Neovim's jump stack, and Textual's rich `OptionList`. A modal is easier to scaffold but
causes a context switch. A right sidebar is attractive on a wide terminal but damages
every existing split layout. A hint-only link mode is fast but cannot explain typed,
directional edges. The bottom peek tray is the only option that satisfies all of the
requirements without making one tab's layout the model for every other tab.

---

## 1. What exists now

### 1.1 ACE has three top-level tabs, but only one is link-aware

ACE's current top-level tab vocabulary is:

1. **Agents** — the live operational control room.
2. **Artifacts** — the queryable artifact catalog, with Agent, Stitch, Patch, Bead,
   document-provider, and File panes.
3. **AXE** — lumberjacks, chops, and background commands.

Artifact links are rendered only inside Artifacts panes. Every built-in Artifacts pane
loads an `ArtifactLinksSnapshot`, projects it into a pane-local `RelationIndex`, and
renders it through `RelationPanel`. The main Agents tab and AXE have no equivalent
selected-entity link context.

The current relation panel is good work and should be reused conceptually:

- It is snapshot-owned and performs no I/O while navigating.
- It preserves relation, inverse label, description, origin, use count, direction, and
  missing-target state.
- Its collapsed rail is concise and disappears when the relation view is empty.
- It already routes cross-pane Artifacts targets and reveals a target excluded by the
  current query rather than silently failing.
- Its structural modes (`<`, `>`, `~`) are fast and established.

But it is not the universal panel. It is mounted once per Artifacts pane, lives inside
the detail column, mixes hierarchy/family/link edges, and its `.` toggle is explicitly
disabled outside Artifacts. Stretching it across the other tabs would import an
Artifacts pane contract into Agents and AXE and would still leave no stable location
across the three layouts.

### 1.2 `sase-tj` left the correct seams

The Agent-pane plan deliberately separated:

- a stable `ArtifactEntryTarget`;
- a canonical artifact reference;
- project and source identity;
- available relations;
- open/copy locators; and
- mutation capabilities.

That separation is exactly what a universal link host needs. The plan also warned not
to flatten relation metadata, and the landed work now carries the relation slug,
inverse label, description, origin, and use count.

The important navigation precedent is also already landed: when a linked target is
filtered out, ACE changes the query through a reversible reveal lens and preserves the
exact original query and selection for return. A universal router should generalize
that behavior, not invent a separate fallback.

### 1.3 `sase-tw` made the graph trustworthy enough to become UI

The graph is now non-lossy across rebuilds, reads publish durably, bead endpoints are
bidirectional, links follow renames, relation semantics survive into ACE, and the Agent
pane can filter on `relation:`, `artifact:`, and `linked:`. The retroactive sweep also
materialized the large mechanically known populations.

The current closed relation vocabulary is:

| Stored relation | Inverse label | Plane | Typical meaning |
| --- | --- | --- | --- |
| `supersedes` | `superseded-by` | semantic | replacement lineage |
| `implements` | `implemented-by` | semantic | plan fulfills bead requirements |
| `derives-from` | `derived-into` | semantic | output lineage |
| `related` | `related` | semantic, imprecise | deliberately asserted affinity |
| `cites` | `cited-by` | observational | prompt cited an artifact |
| `read` | `read-by` | observational | agent read an artifact for a reason |

The semantic/observational distinction matters in the UI. A plan that implements a
bead and an agent that happened to read a plan are both useful, but they should not be
given equal visual weight.

### 1.4 Live scale favors direct hints, not graph visualization

Measured from `sase artifact link list -j -l 0` on 2026-08-26 after the audited reads
for this report:

| Measure | Value |
| --- | ---: |
| Stored edges | **1,261** |
| Linked entities | **1,850** |
| Median degree | **1** |
| 90th-percentile degree | **2** |
| Maximum degree | **25** |
| Entities with exactly one edge | **1,509** |
| Entities with more than five edges | **25** |
| Entities with more than twenty edges | **2** |

Relation distribution:

| Relation | Edges |
| --- | ---: |
| `implements` | 542 |
| `related` | 353 |
| `cites` | 142 |
| `derives-from` | 136 |
| `read` | 88 |

Endpoint occurrences are dominated by beads (1,218), plans (742), research (326), and
agents (230); files account for six. There are no live `supersedes` rows in this
snapshot, but the UI still needs to treat one as high-priority when it appears.

These measurements settle two design questions:

1. A graph canvas would be ceremony for a population whose normal neighborhood is one
   or two edges.
2. Single-character hints cover the overwhelming majority of real neighborhoods, while
   a conventional list handles the two 20+ outliers without special machinery.

### 1.5 Chops already preserve the exact launch roster

Each `ChopRunEntry` persists `launches: list[dict]`; each successful launch contains the
actual allocated `agent_name`. The AXE result card already renders that roster, and chop
lifecycle reconciliation uses it to match launched agents to completion records.

That is strong, machine-owned provenance. No heuristic is needed to answer “which
agents did this chop launch?” What is missing is a canonical chop artifact identity and
a registered link relation that lets the same fact participate in the durable graph.

---

## 2. Design requirements and traps

The feature should satisfy these invariants.

### 2.1 One surface, not one implementation per tab

The panel must be mounted once by the app. Tabs supply a selected-entity context; they
do not own a Links widget, link keymap, loading state, or renderer. Otherwise the next
top-level tab will reproduce the pane divergence that the Artifacts contract had to
repair.

### 2.2 Zero chrome means zero chrome

When the current selection has no associated links:

- the Link Rail has `display: none` and consumes zero rows;
- `$` is unavailable and a stale invocation is a silent no-op;
- the contextual footer and command palette omit the action; and
- no empty Links panel, “0 links” badge, border, placeholder, or toast appears.

An unresolvable selected entity (a synthetic banner, AXE lumberjack, or background
command) has the same presentation as a linkable entity with zero edges: nothing.

An existing **dangling edge** is different. It is a real associated link and must remain
visible as a disabled `(missing)` row so the graph does not hide damage.

### 2.3 Direction must be relative to the selected entity

Never display only the stored slug. If the selected bead is the target of an
`implements` edge, its row reads `← implemented-by plan:…`; from the plan it reads
`→ implements bead:…`. Undirected `related` uses `↔`.

This eliminates the most common link-graph cognitive tax: making the user mentally
reverse a directed triple.

### 2.4 Traversal needs a return path

A link jump without a reliable Back operation is a trap. The destination may switch
top-level tabs, switch Artifacts panes, clear a filter, expand a fold, or select an item
that was not loaded in the bounded first slice. Returning must restore all of the
origin's visible context, not merely the previous tab name.

ACE already teaches `Ctrl+O` / `Ctrl+Shift+O` for back/forward jump history. Link
navigation should extend that stack with stable locations rather than create
“link-back” keys.

### 2.5 The keystroke path must be I/O-free

Selection movement and `$` may read an in-memory neighborhood index only. Aggregate
loads, project discovery, canonical resolution, and large target-catalog extension run
off the event loop. Every result carries a selection generation; after any await, the
current tab, entity, and generation are re-read before applying it.

The rail must clear immediately when selection changes. A stale summary from the prior
row is worse than a brief absence.

---

## 3. Interaction precedents

### 3.1 VS Code: peek before committing to a jump

VS Code distinguishes **Go to** from **Peek**. Peek embeds a result list inline because
quick inspection should not force a large context switch; selecting a result can then
open it in the outer editor. Its navigation history provides an explicit route back.
The useful idea for ACE is not the editor styling—it is the separation of lightweight
inspection from committed navigation and the preservation of history.

Source: [VS Code Code Navigation](https://code.visualstudio.com/docs/editing/editingevolved)
and [Tips and Tricks](https://code.visualstudio.com/docs/editing/tips-and-tricks).

### 3.2 Neovim: jumps are cheap because return is first-class

Neovim's tag stack remembers both the destination and the location jumped from;
`CTRL-T`/`:pop` walks backward. Quickfix uses one window-local list with a highlighted
current entry and next/previous traversal. The lesson is that an edge list and a
location stack are complementary: the list makes selection cheap, while the stack
makes exploration safe.

Sources: [Neovim tag stack](https://neovim.io/doc/user/tagsrch/) and
[Neovim quickfix](https://neovim.io/doc/user/quickfix/).

### 3.3 Textual: a rich list is native; a modal changes input ownership

Textual's `OptionList` already provides highlighted selection, up/down, paging,
home/end, `Enter`, rich renderables, separators, and stable option IDs. It is a better
substrate than a custom `Static` with hand-written cursor logic.

`ModalScreen`, by contrast, takes binding precedence and dims the screen underneath.
That is valuable for a decision that must block the application, but wrong for a panel
whose purpose is to inspect the current context. Textual layers can place a widget
above another, but the recommended tray should reserve bounded layout space so it does
not conceal rows or detail text.

Sources: [Textual OptionList](https://textual.textualize.io/widgets/option_list/),
[Screen and ModalScreen API](https://textual.textualize.io/api/screen/), and
[Textual layout layers](https://textual.textualize.io/guide/layout/).

---

## 4. Interface alternatives

### Option A — centered modal chooser

`$` opens a modal containing the current artifact reference, grouped links, and an
`OptionList`. `Enter` jumps; `Escape` closes.

**Strengths**

- One component can open over every tab with little host-layout work.
- Focus and key handling are unambiguous.
- Long descriptions and many rows have room.
- Narrow terminals are straightforward.

**Weaknesses**

- Dimming hides the very entity whose relationships the user is inspecting.
- It feels like a decision dialog instead of navigation.
- The concise always-in-one-place summary still needs a second widget.
- Repeated graph exploration becomes open → choose → close → context switch.
- It visually overweights the median one-link case.

**Verdict:** useful as a fallback for a tiny terminal, but not the primary UI.

### Option B — persistent right-side link inspector

Every top-level view gives a right column to a link inspector. `$` focuses or collapses
it.

**Strengths**

- Relationships and entity detail remain visible together.
- Plenty of room for target metadata and descriptions.
- Familiar IDE inspector shape.

**Weaknesses**

- Agents and Artifacts already use valuable split layouts; AXE uses a sidebar plus a
  report canvas. A universal right column would squeeze all three differently.
- On 70-column snapshots, the inspector would dominate or require a different location,
  violating the same-location goal.
- A permanently reserved column is wasteful when 1,509 linked entities have one edge
  and many selections have none.
- “Hidden when empty” would make the main content width jump on normal `j`/`k`
  navigation.

**Verdict:** rich but structurally hostile to the current application.

### Option C — bottom Link Rail expanding into a Peek Tray

A one-row rail is mounted above the global footer and only shown for a non-empty
neighborhood. `$` expands it upward into a bounded `OptionList`; the active tab remains
visible above it.

**Strengths**

- Exactly the same location on Agents, Artifacts, and AXE.
- The collapsed state satisfies concise ambient awareness; the expanded state satisfies
  rich inspection.
- Opening does not dim, replace, or horizontally squeeze the current context.
- `$` then a displayed hint is a two-keystroke jump.
- It naturally reuses the successful collapsed/expanded relation-rail visual language.
- Empty state truly consumes no space.
- Full-width rows give long refs and descriptions more room than a side panel.

**Weaknesses**

- Expanding temporarily reduces the active view's height.
- The app needs one new host-level layout seam.
- Extremely short terminals need a capped-height policy.

**Verdict:** best fit. Its costs are bounded and its strengths map directly to every
requirement.

### Option D — hint-only link mode

`$` enters a transient mode, paints `[1]`, `[2]`, … hints in the footer, and the next
key jumps immediately. There is no expanded list.

**Strengths**

- Fastest possible path and almost no layout cost.
- Excellent for the median one-link entity.

**Weaknesses**

- Cannot show description, direction, origin, uses, status, or destination surface
  without becoming an unreadable footer.
- Cross-tab targets have no visible object to annotate.
- Discoverability is poor and dangling targets are awkward.
- It does not really provide the requested panel.

**Verdict:** use its direct-hint idea inside Option C, not as the whole interface.

### Comparison

| Requirement | Modal | Right inspector | Peek Tray | Hint-only |
| --- | --- | --- | --- | --- |
| Same location on every tab | yes | visually yes, spatially costly | **yes** | yes |
| Concise ambient summary | separate widget needed | too large | **native collapsed state** | cramped |
| Current entity remains visible | dimmed | yes | **yes** | yes |
| Two-key direct traversal | possible | possible | **native** | native |
| Typed relation detail | strong | strong | **strong** | weak |
| Zero footprint when empty | yes | causes width change | **yes** | yes |
| Narrow-terminal behavior | strong | poor | **strong with capped height** | strong |
| Fits current ACE layouts | acceptable | poor | **strong** | acceptable |

---

## 5. The recommended UI in detail

### 5.1 Collapsed Link Rail

The rail occupies one row immediately above the global keybinding footer. It has no
border and uses the selected pane/tab accent only for the `LINKS` label; direction and
relation colors are stable across tabs.

For one or two links, show actual targets:

```text
↗ LINKS 2   → implements  ◇ sase-tw   ·   ← read-by  ⬡ research.16.cdx      $ open
```

For a larger neighborhood, summarize relation buckets and preserve direction:

```text
↗ LINKS 12   → implements 1   ·   ↔ related 3   ·   ← read-by 8              $ open
```

Rules:

- Pin `← superseded-by …` first and color it amber/red; it changes how the current
  artifact should be interpreted.
- Semantic relations precede observational relations.
- Use the target's short display label, not a raw path, when resolution succeeded.
- Render a count only when a bucket has more than one row.
- Truncate at relation/target boundaries; never cut a canonical ref into misleading
  fragments.
- At narrow widths, collapse to `↗ 12 LINKS · 4 semantic · 8 activity   $`.
- The rail is clickable; clicking it is equivalent to `$`.

The leading `↗` is decoration, not direction. Per-row arrows carry direction. This
avoids trying to make one global icon mean inbound and outbound simultaneously.

### 5.2 Expanded Peek Tray

At 120×40:

```text
╭─ LINKS 6 · agent:ci_watch.fix ─────────────────────────────────────── $ close ─╮
│ SEMANTIC                                                                       │
│ [1] → implements      ◇ sase-tw       Artifact links that survive…   → Beads │
│ [2] ↔ related         ▤ link-repair   Repair evidence and residue    → Research
│ ACTIVITY                                                                       │
│ [3] → read            ▱ artifact-link-durability…  2 uses            → Plans │
│ [4] ← launched-by     ⚙ reports/ci_watch  run 20260826T…             → AXE   │
╰─ 1–9 jump · j/k move · Enter follow · Ctrl+O back · Esc close ───────────────╯
```

At 70×36, remove secondary description and destination prose before removing the
relation:

```text
╭─ LINKS 6 · ci_watch.fix ──────────────────────────────╮
│ [1] → implements    ◇ sase-tw                 Beads  │
│ [2] ↔ related       ▤ link-repair          Research  │
│ [3] → read          ▱ artifact-link…          Plans  │
╰─ 1–9 · j/k · Enter · Ctrl+O back · Esc ─────────────╯
```

The tray's maximum height is the smaller of 12 rows and one third of the terminal.
Above that, its `OptionList` scrolls. It reserves layout space; it does not overlay the
active view. If the terminal is too short to leave a usable active view, only then may
the same component render as a full-width bottom sheet on a top Textual layer—still
anchored at the bottom and without dimming.

### 5.3 Row anatomy

Each selectable row has, in order:

1. **Direct hint** — `[1]` through `[9]`, then adaptive lowercase hints for remaining
   visible rows. Hints are assigned from the displayed sort and never stored as
   identity.
2. **Direction** — `→`, `←`, or `↔` from the selected entity's perspective.
3. **Perspective label** — `implements`, `implemented-by`, `read`, `read-by`, etc.
4. **Kind glyph** — reuse the Artifacts sub-tab glyph vocabulary.
5. **Target label** — resolved short label, with canonical ref available in tooltip/copy
   metadata.
6. **One concise detail** — description first; otherwise use count; otherwise status.
7. **Destination badge** — `Agents`, `Agent`, `Beads`, `Plans`, `AXE`, etc., so a tab
   switch is never surprising.

Do not show every stored field. `origin` is a small right-edge badge only when it adds
information (`manual`, `derived`, `migrated`). `read`/`prompt_ref` origins are redundant
with their relation labels. Timestamps belong in the destination detail view, not every
link row.

### 5.4 Grouping and ordering

Use two conceptual planes:

1. **Semantic** — `supersedes`, `implements`, `derives-from`, `related`.
2. **Activity** — `launches`, `cites`, `read`.

If all rows belong to one plane or there are at most two total rows, omit section
headers. Within a plane:

1. superseding replacement;
2. directed semantic edges;
3. undirected related edges;
4. launch provenance;
5. citations;
6. reads;
7. target kind, target label, stable ref.

For duplicate observational endpoints, render one row with `N uses`; the user should
not navigate identical destinations several times.

### 5.5 Keys

| Context | Key | Action |
| --- | --- | --- |
| Any tab, selected entity has links | `$` | Expand and focus Links tray |
| Tray open | `$` or `Escape` | Collapse tray and restore prior focus |
| Tray open | `1`–`9` / shown hint | Follow that target immediately |
| Tray open | `j` / `k`, arrows | Move highlight |
| Tray open | `Enter` | Follow highlighted target |
| After any link jump | `Ctrl+O` | Return to previous stable location |
| After returning | `Ctrl+Shift+O` | Move forward again |

Why `$`:

- It is unbound in the current ACE default keymap.
- It is a single logical normal-mode key and works identically in every top-level tab.
- `.` is already the Artifacts Relations toggle (and overlaps Patch reverted-state
  behavior); `L` is already a pane-local “linked plan” action; `@` has heavy prompt and
  artifact-ref editing semantics.
- The user already proposed `$`, so selecting it avoids spending a more mnemonic but
  already loaded key.

The help label should be **Links**, not “Link Mode” or “Artifact Link Panel.” The user
cares about the objects, not the implementation.

### 5.6 Focus behavior

Opening the tray freezes the underlying selection. The highlighted tray row receives
focus; the active entity remains visibly highlighted above. Closing restores the exact
prior focus.

Do not let underlying `j`/`k` navigation change the origin while the tray is open. If a
background refresh deletes or replaces the origin entity, close the tray and issue one
informational toast: `Link origin is no longer available`.

---

## 6. Navigation semantics

### 6.1 A stable, cross-tab location stack

Define a host-owned `TuiLocation`, conceptually:

```text
TuiLocation
  surface        top-level tab
  pane           Artifacts pane or AXE/Agents sub-surface
  entity_target  stable identity, never row index
  view_state     query/reveal token, project scope, fold/banner identity
  scroll_hint    best-effort only
```

Every successful link jump pushes the origin to the same back stack used by
`Ctrl+O`. A new jump clears the forward stack. Failed or dangling jumps do not mutate
history.

This should replace duplicated per-surface anchor records over time, but the Links
feature need not rewrite every existing jump in its first change. An adapter can push
and restore the existing Agents, Artifacts, and AXE stable targets behind one host API.

### 6.2 Deterministic destination policy

The panel must show where `Enter` will go before it goes there.

| Ref kind | Preferred TUI destination |
| --- | --- |
| `agent:` | Main Agents tab for a loaded live concrete agent; otherwise Artifacts → Agent, whose registry spine is complete |
| `patch:` | Artifacts → Patch |
| `stitch:` | Artifacts → Stitch |
| `bead:` | Artifacts → Bead |
| provider document (`plan:`, `research:`, …) | Matching Artifacts document pane |
| `file:` | Artifacts → File |
| `chop:` | AXE, with the owning lumberjack expanded and chop selected |

If the target is already represented in the current pane, prefer same-pane selection
to avoid a gratuitous tab switch. The resolved destination is part of the tray snapshot,
so it cannot change between highlight and `Enter` without a generation change.

An `agent:` ref is the one intentional dynamic route. The Agents tab is the best place
to operate on a live agent; the Artifacts Agent pane is the complete historical
catalog and can resolve dismissed, name-only, and container rows. The destination badge
makes that choice explicit.

### 6.3 Filtered, folded, and not-yet-loaded targets

Use the existing reveal behavior everywhere:

- **Filtered out:** install a temporary exact-target reveal while preserving the
  original query and selection in the location stack.
- **Folded:** expand only the ancestors required to expose the target; record fold state
  for return.
- **Outside a bounded head slice:** request the target by stable identity from a worker,
  then apply only if the route generation and selected destination still match.
- **Wrong project scope:** temporarily change scope with the same reversible-location
  treatment; never report “missing” before resolving the target's owning project.
- **Truly missing:** keep the row disabled and visually dimmed. Do not clear filters in a
  speculative attempt to make it appear.

### 6.4 Open/return sequence

```text
selected entity
    │
    ├─ no links ───────────────► no rail, no action
    │
    └─ links ─► Link Rail ─$─► Peek Tray ─hint/Enter─► resolve destination
                                                        │
                          dangling/error ◄──────────────┤
                                                        │ success
                                                        ▼
                              push origin ─► reveal/select target
                                                   │
                                                Ctrl+O
                                                   ▼
                                         restore exact origin
```

---

## 7. Selected-entity contract

The host needs one Textual-free contract rather than special cases in the widget:

```text
SelectedEntityLinkContext
  canonical_ref     canonical graph identity, or none
  route_target      stable current TUI location target
  display_label     compact origin label
  project_key       aggregate/project scope hint
  generation        selection + snapshot generation
```

Each top-level surface contributes an adapter.

### 7.1 Artifacts adapter

Use each pane's existing `selected_entry_target()` and canonical reference copy
resolution. Do not infer a ref from display text. Group banners and empty/degraded rows
return no context.

Once the universal tray lands, remove `RelationKind.LINK` sections backed by
`artifact_links` from the Artifacts `RelationPanel`. Keep hierarchy and family
relations there, including the domain-specific Plan↔Bead shortcuts. This yields a clean
division:

- `.` — structure inside the current artifact collection;
- `$` — typed artifact graph across all collections and tabs.

### 7.2 Agents adapter

Use the same canonicalization as `reference_for_agent_row`. Concrete prompt-referenceable
agents return `agent:<canonical-global-name>`.

Synthetic clan banners, workflow grouping banners, and family rows for which the main
Agents tab currently refuses an agent reference return no context. Do not fabricate a
ref from a label merely to make the rail appear. The Artifacts Agent pane remains the
complete resolver for real family/container identities in the registry.

### 7.3 AXE adapter

- Chop row: return its canonical `chop:` identity.
- Lumberjack row: none in v1.
- Background-command row: none in v1.
- Empty AXE view: none.

The adapter reads the already-loaded `ChopSnapshot`; opening the tray never reads chop
run JSON. Cycling AXE's `Run N/M` detail does not change the origin identity—the selected
entity is the chop. Run-specific provenance belongs in link descriptions and target
details.

---

## 8. Making chops real graph citizens

### 8.1 Add a canonical `chop:` artifact kind

Use a project-scoped canonical identity such as:

```text
chop:<project>/<lumberjack>/<resolved-chop-identity>
```

The exact escaping of components and generated `for_each` target keys belongs in
`sase-core`; do not build it with string concatenation in the TUI. `chop` is a
non-sidecar artifact kind: its authoritative record is AXE config plus durable run
state, not a Markdown companion file.

The identity names the stable configured/resolved chop, not one retained run. That
matches what AXE selects and avoids links becoming unreachable when bounded run-history
entries are pruned.

### 8.2 Add `launches` / `launched-by`

Register one directed relation:

```text
launches
  inverse: launched-by
  source:  chop
  target:  agent
  writer:  derived
  plane:   activity/provenance
```

Positive direction:

```text
chop:sase/reports/ci_watch launches agent:ci_fix.sase
```

The row description should name the run and carry the structured proposal reason when
available. Repeated evidence converges by endpoint identity and increments/updates
`uses`; it does not create duplicate rows.

Write the row at the successful launch boundary, through the same durable publication
outbox pattern that made reads reliable. Do not derive it only at render time from the
ten retained runs. A virtual-only edge would be outbound-only, would disappear with
retention, and would prevent an Agent-row neighborhood from reliably jumping back to
the chop that launched it.

### 8.3 Lifecycle rule

An old launch edge remains valid history even if the chop is later disabled or removed.
The destination may become unavailable in AXE; the tray then shows a disabled
`launched-by … (chop unavailable)` row rather than deleting provenance. This follows the
link graph's existing rule: a rebuild may delete only what it can prove should no longer
be an asserted fact. “This launch happened” does not become false when config changes.

---

## 9. Implementation shape

### 9.1 Core/backend

Shared semantics belong in `sase-core`:

- canonical `chop:` parsing/formatting;
- `launches` relation registry entry and inverse label;
- a perspective-oriented neighborhood wire that returns relation, perspective label,
  direction, neighbor ref, description, origin, and uses;
- relation-aware deduplication and deterministic semantic/activity ordering; and
- canonical cross-project row identity.

The CLI footer, `artifact link list`, ACE, and future web/editor frontends should agree
on what one neighborhood contains. Python should not reimplement inverse-direction or
deduplication rules.

### 9.2 ACE host

Mount one `LinksPeekTray` beside the global footer, backed by:

- `LinkRail` for the collapsed Rich `Text` summary;
- Textual `OptionList` for expanded rows;
- a `SelectedEntityLinkContextProvider` registry keyed by top-level tab;
- a `TuiArtifactRouter` keyed by artifact-ref kind; and
- a generation-guarded `LinkNeighborhoodController`.

The controller accepts already-loaded aggregate snapshots and builds a ref→rows map
once per source signature. It must never scan all 1,261 rows on each `j`/`k`; lookup is
O(degree).

### 9.3 Snapshot ownership

- Artifacts panes already carry `ArtifactLinksSnapshot`; publish the active snapshot to
  the host rather than load another copy.
- The main Agents and AXE workers should add the same snapshot handle to their existing
  collected data. They already refresh off-thread and have generation/coalescing rules.
- Cross-project agent and chop contexts need an all-known-project snapshot assembled in
  the worker, cached by aggregate signature.
- On tab switch, show cached link state immediately and schedule normal background
  revalidation. Do not put a new load on startup's critical path.

### 9.4 Recommended sequence

1. **Neighborhood wire and host contract** — no UI; parity tests against CLI
   perspective labels and sorting.
2. **Link Rail + Peek Tray** — Artifacts adapter first, while the old link sections are
   temporarily retained for A/B visual verification.
3. **Router + cross-tab location stack** — all existing ref kinds; filtered/folded/
   bounded targets and back/forward restoration.
4. **Agents and AXE adapters** — no chop links yet; prove zero-chrome behavior on
   unreferenceable rows.
5. **`chop:` + `launches` durability** — write at launch, backfill retained run rosters,
   add inbound Agent→AXE routing.
6. **Remove duplicate Artifacts link sections and polish** — keep structural Relations,
   refresh help and visual snapshots once.

This sequence keeps the relation-panel removal reversible until the universal route is
proven.

---

## 10. Reliability and verification

### 10.1 Behavioral matrix

At minimum, test:

- every current ref kind in both endpoint positions;
- directed primary and inverse labels plus symmetric `related`;
- one, two, nine, ten, and 25-link neighborhoods;
- duplicated observational rows converging to `uses`;
- semantic-before-activity ordering and superseded warning priority;
- dangling target visible but disabled;
- current entity with zero links: no widget, no footer action, no command;
- synthetic Agents row, AXE lumberjack, and background command: no widget;
- current selection changes during an async refresh: no stale rail paint;
- active Agent route vs dismissed Agent-pane fallback;
- filtered target reveal and exact query restoration;
- folded target reveal and exact fold restoration;
- target outside bounded first slice;
- cross-project target;
- jump failure leaves history untouched;
- `Ctrl+O` / `Ctrl+Shift+O` round trip across all pairs of top-level tabs; and
- chop launch edge survives run-history pruning/config disable.

### 10.2 Performance budgets

- No synchronous I/O, subprocess, stat, glob, or provider resolution in selection,
  render, `$`, direct-hint, or `Enter` paths.
- Ordinary tab `j`/`k` p95 remains below the established **16 ms** target with the rail
  enabled.
- Cached neighborhood lookup and collapsed-rail render should target **<1 ms p95** for
  degree ≤25.
- Opening the tray from cached data should paint within one refresh frame.
- An all-project aggregate extension must not gate startup first paint.

### 10.3 Visual coverage

PNG snapshots should cover:

- Agents / Artifacts / AXE with the same collapsed rail location;
- one-link, two-link, and 12-link summaries;
- expanded mixed semantic/activity tray;
- inverse-direction labels;
- superseded warning;
- dangling target;
- 120×40 and 70×36;
- no-links states proving the layout is pixel-identical to the pre-feature view; and
- AXE chop with `launched` targets plus Agent row with inbound `launched-by`.

The strongest no-links visual assertion is not “the panel says empty”; it is exact pixel
equality with a view that has no Links feature mounted visibly.

---

## 11. Decisions to avoid

- Do not make `$` jump immediately when there is one link. Predictable “open the panel”
  behavior is worth the second `Enter`, and `$1` is still two keys for experts.
- Do not expand transitively. This is a one-hop neighborhood inspector, not a graph
  browser; every jump naturally exposes the next hop.
- Do not hide observational links by default. Separate and visually subordinate them,
  but they are often the most valuable path from an artifact back to the agent that
  used it.
- Do not make the Links tray another query language in v1. Degree is tiny; direct hints
  and list navigation are faster than opening a filter input.
- Do not put the panel inside each tab or Artifacts pane.
- Do not duplicate artifact links in both Relations and Links after migration.
- Do not infer canonical refs from row labels.
- Do not index by current row number, `current_idx`, or `artifacts_dir`; use stable refs
  and route targets.
- Do not build chop links as ephemeral TUI-only edges.
- Do not reserve permanent screen space for an empty or unknown neighborhood.

---

## 12. Recommendation

Implement **Option C: the universal bottom Links Peek Tray**, with the hint-speed idea
from Option D inside it.

The final interface should be:

1. A one-line Link Rail at the content/footer seam, automatically present only for a
   non-empty neighborhood.
2. `$` as the single global toggle on Agents, Artifacts, and AXE.
3. A full-width, non-modal, layout-reserving tray grouped into semantic and activity
   links, with direction labels relative to the selected entity.
4. Visible direct hints so `$1` follows the first link in two keys, plus `j`/`k` and
   `Enter` for ordinary browsing.
5. Destination badges and deterministic routing: active agents to Agents, historical
   agents to Artifacts → Agent, document/bead/patch/stitch/file refs to their Artifacts
   pane, and `chop:` refs to AXE.
6. Link jumps integrated into ACE's existing `Ctrl+O` / `Ctrl+Shift+O` back/forward
   history, restoring exact query, fold, scope, and selection context.
7. A new durable `chop:` artifact identity and `launches` / `launched-by` derived
   relation written at the launch boundary.
8. The existing Artifacts Relations panel retained for hierarchy and family only;
   typed artifact-link rows move exclusively to Links.

This design is fast in the common one-edge case, informative in the 25-edge worst case,
stable across all current layouts, honest about missing targets, and truly absent when
there is nothing to show. It also makes the graph feel like one coherent navigation
layer over ACE rather than an Artifacts-pane feature that other tabs happen to borrow.
