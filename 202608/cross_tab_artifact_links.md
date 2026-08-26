---
create_time: 2026-08-26
updated_time: 2026-08-26
status: research
tags:
  - ace
  - tui
  - artifact-links
  - navigation
  - keymaps
  - agents
  - axe
---

# One Link Surface For Every Tab: The Link Rail

**Research question.** ACE has three tabs (Agents, Artifacts, AXE) and a typed artifact
link graph that only one of them can see. How should a *single* link surface — one
keymap, one display location, one traversal model — be added to every tab and every
entity, so that following a link is nearly free, the display is concise and beautiful,
and the whole feature disappears completely when the selected entity has no links?

**Scope.** This report designs the user interface. It explores five candidate
interfaces, evaluates them against measured properties of the live link graph, and ends
with one recommendation plus the concrete rendering, keymap, traversal, and
invisibility contracts it implies. It does *not* design the storage layer — epic
`sase-tw` closed that — and it does not re-litigate the relation registry.

**Method.** Measured on this machine on 2026-08-26 against `sase` at `f4b827af6`
(master, clean) and `sase-core` opened with `sase repo open`. Graph numbers come from
`sase artifact link list -j -l 0` (the live project aggregate, 1,262 rows), entity
counts from `sase bead list`, `sase agent search -j -l 0`, and `sase plan search`. Pane
contracts come from `sase artifact pane show <id>`. Visual claims are read off the
committed PNG goldens in `tests/ace/tui/visual/snapshots/png/`. Where a number differs
from what a design intuition would predict, the number wins and is shown.

---

## Bottom line

Three measurements decide this design, and all three point the same way.

1. **82% of linked entities have exactly one link; 96% have three or fewer;
   1,848 of 1,852 have nine or fewer.** This is not a graph-browsing problem. It is a
   *one-chip* problem with a small tail. Any interface whose default gesture costs more
   than two keystrokes, or whose default presentation costs more than one line, is
   over-built for the data.

2. **63% of edges are cross-kind** (`plan:`→`bead:`, `agent:`→`research:`, …). Following
   a link is normally a *cross-pane, often cross-tab* move. So the surface cannot be
   pane-local, and the jump primitive must be app-level. Today it is neither: link rows
   in the existing relation panel are rendered with `key=""` and are literally
   unnavigable (`src/sase/core/artifact_relation_layout.py:258`).

3. **Only 3% of agents and 18% of beads have any link at all.** The invisible-when-empty
   requirement is not a nicety; it is the dominant case. Whatever surface is chosen must
   cost zero rows and zero footer entries the vast majority of the time.

A fourth measurement is a **prerequisite, not a design input**: the machine-local read
model every TUI consumer reads is currently 231 rows stale and contains **zero**
agent-endpoint rows. Filed as `bead:sase-ua` while measuring for this report; §1.4
gives the numbers. Until it is fixed, an Agents-tab link surface would render nothing
for all 193 agents that have links. This does not change the recommendation, but it
sequences the work.

**The recommendation: the Link Rail.** One app-owned, full-width, single-line widget
docked immediately above the `KeybindingFooter`, present in exactly the same place on
all three tabs, hidden entirely when the selection has no links. It renders numbered
chips. One new app key, `$`, acts as a *one-shot numbered-link prefix* — the same
mechanism `numbered_link_keys.py` already implements for the Memory panel's `.N`:

| Gesture | Effect | Cost |
| --- | --- | --- |
| `$1` … `$9` | Follow link *N*, switching tab and pane as needed | 2 keys |
| `$$` | Follow the lead chip (chip 1) | 2 keys |
| `$0` | Open the Links panel: every link, with its `why`, origin, and uses | 2 keys |
| `Ctrl+O` / `Ctrl+Shift+O` | Walk back / forward along the traversal trail | existing keys |

Two keystrokes reach **100%** of entities in the live graph. There is no armed mode to
remember, because the chips are always painted before the prefix is pressed — `$` is
only ever a prefix, never a toggle. The rail is the display *and* the legend *and* the
keymap, which is why it stays honest.

The three rejected alternatives are rejected for concrete reasons, not taste: extending
the per-pane `RelationPanel` (§3.1) cannot be app-level and costs up to 24 rows;
a modal-first browser (§3.2) hides the one fact you need before you decide to open it;
detail-panel chips (§3.4) are in a different place on every tab, which the brief
forbids.

---

## 1. Ground truth

### 1.1 What already exists (more than expected)

Roughly 70% of this feature is already built, in the wrong place.

| Piece | Where | Status |
| --- | --- | --- |
| Typed link store + closed relation registry | `sase-core` `artifact_link/relation.rs`, `sase/sdd/artifact_link_*` | Landed (`sase-tw`) |
| Project aggregate, mtime-keyed cache | `ace/tui/relations/artifact_links.py:48` | Landed |
| Ref → pane-target resolution, **including cross-kind** | `relations/artifact_links.py:168` `_target_for_ref` | Landed |
| Textual-free relation layout + keymap model | `core/artifact_relation_layout.py` | Landed |
| A relation panel with a collapsed one-line rail | `widgets/artifacts/relation_panel.py` | Landed, Artifacts-only |
| Cross-pane navigation primitive | `actions/artifacts_navigation.py:117` `_request_artifacts_entry` | Landed |
| Query-widening reveal for off-query targets | `panes.py:198` `reveal_entry_target` | Landed, same-pane only |
| One-shot `.N` numbered-link prefix | `modals/numbered_link_keys.py` | Landed, Memory/Glossary only |
| Bounded traversal trail + breadcrumb | `modals/memory_panel_travel.py` | Landed, Memory only |
| Letter-keyed neighbor jump modal | `modals/agent_neighbor_modal.py` (`~`, Agents tab) | Landed |
| Per-surface jumplist back/forward | `Ctrl+O` / `Ctrl+Shift+O` | Landed |
| Context-sensitive action hiding | `_app_action_availability.py` `check_app_action` | Landed |

Two of these deserve emphasis because they are the design's proof-of-concept:

- **The Memory panel already ships this exact interaction**, in miniature. Its golden
  (`memory_panel_populated_dark_120x40.png`) shows a labelled chip block —
  `PARENT [.1 agent_hood]` / `CHILDREN [.2 grandchild]` — a `TRAIL agent_hood › hub_child`
  breadcrumb, and a footer reading `Tab link · Enter / l follow · backspace / h back`.
  The Link Rail is that idea, promoted from one modal pane to the whole app.

- **The codebase has already hand-built two special-cased single-link jumps**:
  `beads_open_plan` (`L` on the Beads pane) and `plans_open_bead` (`L` on the Plan
  pane), both implemented by calling `keymap.first_link_target("plans")` /
  `first_link_target("beads")` and then `_navigate_to_relation_target`
  (`actions/_artifacts_beads_browse.py:58`, `actions/artifacts_plans.py:90`). Two
  bespoke instances of "jump to the linked thing" is the strongest possible evidence
  that the general verb is needed — and the Link Rail subsumes both.

### 1.2 The link graph, measured

`sase artifact link list -j -l 0` → 1,262 rows, 1,852 distinct nodes.

**Per-node degree, from the node's own perspective** (each row counted once for each
endpoint, with the inverse label applied on the target side):

| Links on the selected entity | Nodes | Share | Cumulative |
| --- | --- | --- | --- |
| 1 | 1,511 | 82% | 82% |
| 2–3 | 269 | 15% | 96% |
| 4–9 | 68 | 4% | **99.8%** |
| 10–25 | 4 | 0.2% | 100% |

Distinct relation labels per node: median **1**, p90 **1**, max **4**.

**Relation label frequency** (perspective-corrected, so inverses are counted
separately):

| Label | Rows | Label | Rows |
| --- | --- | --- | --- |
| `related` | 706 | `derives-from` / `derived-into` | 137 / 137 |
| `implements` / `implemented-by` | 542 / 542 | `read` / `read-by` | 88 / 88 |
| `cites` / `cited-by` | 142 / 142 | `supersedes` / `superseded-by` | 0 / 0 |

**Endpoint kinds:**

| | `bead` | `plan` | `agent` | `research` | `file` |
| --- | --- | --- | --- | --- | --- |
| as source | 334 | 542 | 230 | 151 | 5 |
| as target | 884 | 200 | 0 | 177 | 1 |
| linked nodes | 786 | 686 | 193 | 181 | 6 |
| p90 degree | 3 | 1 | 1 | 3 | 1 |
| max degree | 25 | 5 | 6 | 12 | 1 |

**Cross-kind edges: 793 / 1,262 = 63%.**

**Coverage against the full corpus** — this is what the invisibility contract is worth:

| Entity | Total | Linked | Share linked |
| --- | --- | --- | --- |
| Agents | 6,611 | 193 | **2.9%** |
| Beads | ~4,338 | 786 | **18%** |
| Plans / research docs | — | 867 | — |
| Indexed files | — | 6 | ~0% |
| Stitches, Patches, chops | — | **0** | **0%** |

**Description (`why`) length:** median 120 chars, p90 240, max 240 (the store truncates
at 240). This single number kills any design that puts the `why` in a one-line rail
verbatim — and it explains why the CLI's own table is unreadable:
`sase artifact link list bead:sase-j7` renders a 25-row table in which a single `why`
occupies sixteen wrapped lines.

### 1.3 The five concrete gaps

1. **Link rows have no key.** `build_relation_view` assigns `key=""` to every
   `RelationKind.LINK` row (`artifact_relation_layout.py:262`) and
   `_render_flat_row(..., keyed=False)` renders them without a `[k]` prefix
   (`relation_panel.py:219`). `RelationKeymap.links` is a list of
   `(relation_name, target)` pairs — it cannot answer "what does key 2 do".
2. **The collapsed rail gives links no mode key.** `_rail_mode_key` returns `""` for
   `RelationRole.LINK` (`relation_panel.py:472`), so the golden reads
   `▸ . expand · > 2 children · 1 plans` — children are keyed, plans are not.
3. **The surface is Artifacts-only.** `toggle_relation_panel` is hard-gated to the
   Artifacts tab (`_app_action_availability.py:282`), and `RelationPanel` is composed
   inside six Artifacts panes only. Agents and AXE have no link surface at all.
4. **AXE entities have no artifact identity.** The live ref-kind catalog
   (`sase-core/crates/sase_core/src/artifact_ref/kinds.rs`) is `stitch`, `patch`, `bead`,
   `agent`, `file` plus dynamic document kinds. There is no `chop:` kind, and
   `AXE_COPY_TARGETS` offers no `reference` target. The user's "chops can link to the
   agents they launched" therefore needs a decision, not just wiring (§6.3).
5. **Traversal back is per-surface.** `Ctrl+O`'s anchor stacks are keyed per tab and per
   pane (`_entry_jump_agents_anchor_stack`, `_entry_jump_forward_stack_map()`), and the
   relation origin store is `_artifacts_jump_history: dict[pane_id, target]` — one slot
   per pane, not a stack. A cross-tab link walk has nowhere to record itself.

### 1.4 A prerequisite defect found while measuring — `bead:sase-ua`

Every number in §1.2 comes from `sase artifact link list`, which reads the **store**.
Every TUI surface reads a different thing: the machine-local aggregate
`~/.sase/projects/<key>/artifact-links.json`, via `load_artifact_links_snapshot()`. They
disagree badly.

| | store | on-disk aggregate |
| --- | --- | --- |
| rows | 1,262 | 1,031 |
| `agent:`-sourced | 230 | **0** |
| `cites` | 142 | **0** |
| `read` | 88 | **0** |
| `agent:` anywhere | 230 | **0** |

The 231 missing rows were created between 2026-08-13 and 2026-08-26, 87 of them before
today — a class omission, not a lag. The rebuild logic is correct; a read-only dry run
from this workspace produces the right answer:

```
resolve_artifact_link_store().preview_aggregate()  -> 1261 rows, agent 230, cites 142, read 88
resolve_artifact_link_store().load_aggregate()     -> 1031 rows, agent 0,   cites 0,   read 0
```

The file is simply never rebuilt, and no consumer validates it. The user-visible symptom:
`sase agent search 'linked:true'` returns **0 of 12,898** although 193 catalog agents
have link rows; `relation:` and `artifact:` are equally dead. That is the whole
deliverable of phase `sase-tw.13`.

Filed as `bead:sase-ua` (ready), linked `related` to `sase-u9` — whose unbudgeted
rename-repair loop is the likely upstream cause — and to `sase-t0`. Recorded as a
`DISCOVERED ISSUE:` note on the in-progress epic `sase-tj`, whose workers would
otherwise misdiagnose the empty Agent-pane filters as a pane regression.

**Consequence for this design.** §6.2's Agents-tab adapter and §8's index both read the
aggregate, so both inherit the omission. Phase 1 of §10 must therefore validate the index
against the store, and the Agents tab cannot be demonstrated until `sase-ua` lands. The
Artifacts tab is unaffected for `plan:`/`bead:`/`research:` edges, which are all present.

---

## 2. Design constraints the measurements impose

- **C1 — Optimize the single chip.** 82% of the time there is one link. The resting
  presentation must be beautiful and informative at n=1 and merely survivable at n=9.
- **C2 — Two keystrokes, uniformly.** Single digits cover 99.8% of entities. A design
  needing three keystrokes for the common case is wrong; a design that costs one
  keystroke *sometimes* and two *other times* is worse than one that always costs two
  (§5.2).
- **C3 — Cross-surface is the normal case.** 63% of edges leave the current pane's kind.
  The jump verb belongs to the app, not to a pane.
- **C4 — Zero cost when absent.** 97% of agents and 82% of beads must see no row, no
  chip, no footer entry, and no help entry.
- **C5 — The `why` never fits.** Median 120 chars. It belongs in the overflow surface
  and, at most, as an elided tail on the lead chip.
- **C6 — Repaints on every highlight move.** `sase/memory/tui_perf.md` rule 7 says
  detail panels debounce but the highlight never does. A rail that lags the cursor by
  150 ms shows *the previous entity's links*, which is a correctness bug, not a
  performance one. So the rail must be cheap enough to paint synchronously inside the
  p95 < 16 ms key-to-paint budget (§8).

---

## 3. Candidate interfaces

Each candidate is shown as it would look on the Beads pane for `bead:sase-tw`, which has
three links, and is scored on the same keystroke table.

### 3.1 Candidate A — Extend the existing `RelationPanel` to every tab

Give `RelationKind.LINK` rows real keys, add a `$` role alongside `<` / `>` / `~`, and
mount a `RelationPanel` inside the Agents and AXE tabs.

```
┌─ Beads ─────────────────────────────────┐
│  ...rows...                             │
│                                         │
│ ▾ RELATIONS                    . collapse
│ CHILDREN                                │
│   [1] sase-tw.1 [C]                     │
│   [2] sase-tw.2 [C]                     │
│ RELATED                                 │
│   [a] sase-u3 — the epic whose land-ag… │
│ IMPLEMENTED-BY                          │
│   [b] 202608/artifact_link_durability…  │
└─────────────────────────────────────────┘
```

**For.** Smallest conceptual delta; reuses `build_relation_view` wholesale; one panel
for all four relation axes; the expanded tree view for bead hierarchies is genuinely
good and is preserved.

**Against.**
- It is structurally pane-local. `RelationPanelHostMixin` reads `self.contract`,
  `self.relation_index()`, `self.selected_entry_target()` — a pane API. The Agents tab's
  left panel is an agent tree with no contract and no `ArtifactEntryTarget`; the AXE
  tab's left panel is 35–80 cells wide, where a rail truncates to nothing. Making this
  app-level means rewriting the mixin as an app service anyway — i.e. doing the Link
  Rail's work while keeping the pane widget.
- **Section-per-relation is the wrong shape for this data.** Median distinct labels per
  node is 1. On 82% of entities the expanded panel renders one section heading and one
  row — two lines and a border to say one thing.
- Costs up to 24 rows (`styles.tcss:1088 max-height: 24`) against a 40-row terminal.
- Keeps four relation axes fused, so `$` can never be gated independently of `<`/`>`/`~`.
  C4 fails: an entity with children but no links still shows a link-capable panel.

**Keystrokes:** `.` expand → read → `$b`. Three, plus a mode toggle that changes layout.

### 3.2 Candidate B — Modal Link Browser (`$` opens a screen)

`$` pushes a `ModalScreen`, in the shape of the existing `AgentNeighborModal`
(`agent_neighbor_modal_60x30.png`): grouped rows, letter keys `a`–`z`,
`enter jump · j/k move · q/esc close`.

```
╭─ Links of bead:sase-tw ─────────────── 3 links ─╮
│ ── outgoing ─────────────────────────────────── │
│  a ↔ related      ◈ sase-u3                     │
│      the epic whose land-agent verification…    │
│ ── incoming ─────────────────────────────────── │
│  b ← implemented-by ✎ 202608/artifact_link_dur… │
│      derived from the plan's bead_id: field     │
│  c ← cited-by     ⬡ sase-tj.land.w3             │
│                                                 │
│  enter jump · a-c select · j/k move · q close   │
╰─────────────────────────────────────────────────╯
```

**For.** Unlimited room for the `why`, origin, uses, and dangling state; the only place
the 25-link tail is genuinely comfortable; a natural home for future multi-hop
exploration; an established, tested precedent in this repo.

**Against.**
- **It cannot satisfy the display half of the brief.** The user asked for the links to
  be *displayed* somewhere concise and identical across tabs. A modal displays nothing
  until opened. Adding a "you have links" indicator to make it discoverable means
  building the rail anyway — at which point the modal is the overflow, not the primary.
- Opening a screen to read one line is disproportionate 82% of the time.
- Modal push/pop tears down and rebuilds focus; jumping *out* of a modal into a
  different tab is an awkward sequence (dismiss → switch → select) that the existing
  `AgentNeighborModal` only avoids because it never leaves the Agents tab.

**Keystrokes:** `$` → `b`. Two — but with a full-screen context switch between them.

### 3.3 Candidate C — Link Rail above the footer + one-shot `$N` prefix

An app-owned single-line widget, always in the same place, showing numbered chips.

```
 LINKS 3 · $1 ← implemented-by  ✎ artifact_link_durability — "lands the approved design"
           · $2 ↔ rel ◈ sase-u3 · $3 ← cite ⬡ sase-tj.land.w3 · $0 all
─────────────────────────────────────────────────────────────────────────────────────
 j next · k prev · Enter view · f filter · l expand · h collapse · R refresh
```

(One rendered line; wrapped here for the page. At n=1 — the 82% case — it is:)

```
 LINKS · $1 ← implemented-by  ✎ 202608/artifact_link_durability_and_derivation
         — "derived from the plan's bead_id: frontmatter field"
```

**For.** Satisfies every clause of the brief directly: one location, one keymap, always
concise, gone when empty. Two keystrokes with no armed mode. Reuses
`numbered_link_keys.py` almost verbatim. The rail *is* the legend, so the keymap can
never drift from the display. Scales down to nothing and up to a `+N more` handoff.

**Against.** One new widget in `_app_layout.py` and one new app-level edge index (§8).
Costs one row when present. Needs a truncation policy that is provably stable (§5.5).
Coexists with the Artifacts relations rail, so the Artifacts tab briefly has two
one-line relation strips until §7's boundary is applied.

**Keystrokes:** `$1`. Two, always, with the target visible before you commit.

### 3.4 Candidate D — Link chips inside the detail panel

Render the Memory panel's chip block verbatim inside each tab's right-hand detail panel.

```
 Details
   ◈ sase-tw · Artifact links that survive…
   Status  closed
   …
   LINKS      $1 impl ✎artifact_link_durability   $2 rel ◈sase-u3   $3 cite ⬡sase-tj.land.w3
```

**For.** Proven idiom, already shipped in Memory. Sits next to the entity's own facts,
which reads naturally. Room for two lines of chips.

**Against.** **It is in a different place on every tab**, which the brief explicitly
rules out: the Agents tab's detail is `AgentDetail`, the AXE tab's is `AxeDashboard`,
and each Artifacts pane has its own detail panel with its own scroll position. Worse,
the detail panel is *scrollable* — chips can scroll off-screen, so the keys would be
live while their legend is invisible. That is precisely the "armed mode you can't see"
failure the rail is designed to avoid. Also, detail panels are debounced (rule 7), so
chips would lag the highlight (C6).

### 3.5 Candidate E — Inline row badges

Put a link count badge on each list row, e.g. `◈ sase-tw  ⋯  ⚭3`.

**For.** Zero extra rows. Makes link *density* visible across the whole list at once,
which no other candidate does. Genuinely useful for spotting hubs.

**Against.** Not a panel and carries no relation, target, or key — it answers "are there
links" and nothing else. Costs 2–3 cells on every row in lists already fighting for
width (`artifacts_beads_populated_120x40.png` shows rows truncating at `1/2 phas…`
today). Repaint cost scales with visible rows rather than with the selection.

**Verdict: not a candidate, but a good later addition** *on top of* C — the rail tells
you about the selection, the badge tells you where to move the selection.

---

## 4. Head-to-head

| | A. Pane panel | B. Modal | **C. Link Rail** | D. Detail chips | E. Badges |
| --- | --- | --- | --- | --- | --- |
| One location on all 3 tabs | ✗ | n/a | **✓** | ✗ | ✓ |
| Displays links without a gesture | ✓ (if expanded) | ✗ | **✓** | ✓ | partial |
| Keystrokes to follow (median case) | 3 | 2 + screen | **2** | 2 | n/a |
| Legend always co-located with keys | ✓ | ✓ | **✓** | ✗ (scrolls) | n/a |
| Zero cost when no links | partial | ✓ | **✓** | ✓ | ✓ |
| Cost when links exist | ≤24 rows | full screen | **1 row** | 1–2 rows | 3 cells/row |
| Good at n=1 (82%) | poor | poor | **excellent** | good | poor |
| Good at n=25 (0.2%) | good | **excellent** | handoff | poor | poor |
| Carries the `why` | ✓ | **✓** | lead chip only | partial | ✗ |
| Repaints inside 16 ms | ✓ | n/a | **✓** | ✗ (debounced) | risk |
| New app-level machinery | rewrite mixin | modal + indicator | **widget + index** | index | index |

C wins on every axis the brief names. B wins on the tail, which is 4 entities. The right
answer is therefore **C as the primary surface with B as its `$0` overflow** — and this
composition is cheaper than either alone, because the modal inherits the rail's index
and the rail inherits the modal's ability to say "there are more".

---

## 5. Recommended design — the Link Rail

### 5.1 Placement and anatomy

One new widget, `LinkRail`, yielded by `AppLayoutMixin.compose` between
`#main-container` and the `KeybindingFooter`. It is app-owned, not pane-owned, so its
identity, height, and position are literally the same object on every tab.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│  #main-container   (Agents tree | Artifacts panes | AXE lumberjacks)          │
└───────────────────────────────────────────────────────────────────────────────┘
   LinkRail            ← 1 row when the selection has links, display:none otherwise
   KeybindingFooter    ← unchanged
   status line         ← unchanged
```

Anatomy of the rendered line, left to right:

```
 LINKS 3 · $1 ← implemented-by ✎ artifact_link_durability — "lands the design" · $2 ↔ rel ◈ sase-u3 · $0 all
 └──┬──┘   └┬┘ └────┬────────┘ └┬┘ └──────┬──────────┘   └────────┬─────────┘   └── sigil chips ──┘  └─┬─┘
 header    key   perspective   kind   short target label      elided why (lead only)              overflow
           chip    label      icon+
                              accent
```

- **Header** — `LINKS` plus the count, in the *selected entity's* accent
  (`ARTIFACTS_ACCENTS`: beads `#D787FF`, agents `#0062FF`, stitches `#FFD700`, patches
  `#00D7AF`, files `#FFAF5F`, plans `#AF87FF`). Count is omitted at n=1; the single chip
  already says it.
- **Key chip** — `$N` in `bold #FFAF00`, matching the `[key]` style the relation panel
  already uses for keyed rows (`relation_panel.py:229`).
- **Direction glyph** — `→` this artifact is the source, `←` this artifact is the target,
  `↔` undirected (`related`). This is the fast scan: incoming versus outgoing without
  reading a word.
- **Relation label** — perspective-corrected by the existing Rust
  `artifact_relation_label(slug, this_is_source)`. Full word on the **lead chip**;
  four-letter sigil on the rest: `impl`, `cite`, `read`, `rel`, `sup`, `deriv`.
- **Kind icon + accent** — `ARTIFACTS_ICONS` (`◈` bead, `⬡` agent, `◉` stitch, `⎇` patch,
  `▤` file, `✎` plan) painted in the **destination** pane's accent. This is the design's
  best idea: *the hue tells you where the key will take you*, so "jump to the bead" and
  "jump to the plan" are distinguishable pre-attentively, with zero extra cells.
- **Short target label** — the ref with its kind prefix removed and shortened:
  `bead:sase-u3` → `sase-u3`; `plan:202608/artifact_link_graph.md` →
  `202608/artifact_link_graph`; `agent:sase-tw.land` → `sase-tw.land`;
  `file:explicit:dd04080e6454…` → `explicit:dd04080e`;
  `stitch:sase-org/sase@f4b827af6` → `sase@f4b827a`. Long research paths tail-elide.
- **Lead-chip `why`** — only the lead chip carries an elided description, in
  `dim #A8A8A8` inside typographic quotes. Dropped first under width pressure.
- **Overflow** — `$0 all` always terminates the rail (it opens the Links panel); when
  chips do not fit, it becomes `$0 +7 more`.

Rendered on each tab, at 120 cells:

```
Artifacts ▸ Beads, sase-tw selected (3 links)
 LINKS 3 · $1 ← implemented-by ✎ 202608/artifact_link_durability — "lands the approved design" · $2 ↔ rel ◈ sase…

Agents, live agent sase-tj.land.w3 selected (1 link)
 LINKS · $1 → cites ✎ 202608/artifact_link_derivation.md — "expanded into the launch prompt at one hop"

AXE ▸ hooks / epic_launch_flush selected (2 launched agents)
 LINKS 2 · $1 → launched ⬡ sase-u6.1.code — "chop launch 2026-08-26T14:02Z" · $2 → launched ⬡ sase-u6.2.code

Anything with no links
 (no row: the rail is display:none and $ is not bound)
```

### 5.2 The `$` grammar, and why it is uniform

`$` is a **one-shot prefix**, not a mode. `handle_numbered_link_key`
(`modals/numbered_link_keys.py:60`) already implements exactly this contract — arm on
prefix, resolve on the next decimal digit, cancel on anything else, never fire while an
`Input` has focus — and it is already reserved against collision in `scopes.py`. The
Link Rail reuses it with `$` in place of `.`.

| Key | Action |
| --- | --- |
| `$1`–`$9` | Follow link N |
| `$$` | Follow the lead chip |
| `$0` | Open the Links panel |
| any other key after `$` | Cancel; the key falls through to normal dispatch |

**Why not make a bare `$` jump when there is exactly one link?** It would save one
keystroke 82% of the time, which is a real prize. Reject it anyway, for a concrete
failure mode rather than a purity argument: on the Artifacts tab the bare digits `1`–`6`
select sub-panes (`1 Agent`, `2 Stitch`, `3 Patch`, `4 BEAD`, `5 Plan`, `6 File` —
visible in every Artifacts golden). If `$` sometimes jumps immediately, then typing
`$2` at a one-link bead follows link 1 **and then switches to the Stitch pane**. The
user ends up two surfaces away from where they aimed, with no error and no undo hint.
A uniform two-key grammar makes that unreachable. Prefix-doubling (`$$`) is also already
the house idiom for "the default action of this mode" — `%%` copies raw, `!!` runs the
last command, `,,` repeats the last leader action, `zz` cycles folds — so `$$` reads as
familiar rather than clever.

**Why `$`?** It is unused. An audit of every value under `ace.keymaps` in
`src/sase/default_config.yml` leaves exactly five unclaimed ASCII punctuation keys:
`"`, `$`, `&`, `\`, `|`. Of those, `\` and `|` are shell-hostile and awkward to type,
`"` is a quoting character users expect to be inert, and `&` has no mnemonic here. `$`
also joins a coherent family — `<` ancestors, `>` children, `~` family, `$` links —
which is the fourth and final relation axis. Implementation cost is one line:
`"dollar_sign": "$"` in `_KEY_DISPLAY` (`keymaps/key_validation.py:7`), plus a `"$"`
alias beside the existing `"+"`/`"-"` friendly spellings.

### 5.3 Traversal and the trail

Following a link makes the destination the selected entity, whose own rail paints
immediately — so `$1 $1 $1` walks the graph three hops with six keys and no mode.

Going back is the one place this design needs genuinely new plumbing, because §1.3.5
found that every existing back-stack is per-surface while link hops cross surfaces.
Proposal:

- An app-level `_link_trail: list[LinkHop]`, bounded at 32, mirroring
  `memory_panel_travel.py`'s `_trail` and `_MAX_TRAIL_LENGTH` exactly. A `LinkHop`
  records `(tab, ArtifactEntryTarget, pane query digest)` — the query digest so a
  back-hop can restore a query that a forward hop widened (§5.6).
- `Ctrl+O` pops the link trail when the most recent navigation event was a link hop, and
  otherwise falls through to the existing per-surface anchor stacks unchanged.
  `Ctrl+Shift+O` walks forward symmetrically. **No new back key**, and the vim
  convention the jumplist already implements is preserved.
- When the trail is non-empty the rail grows a leading breadcrumb chip, which is both
  the affordance and the legend:

  ```
   ⟨ ◈sase-tw › ✎artifact_link_durability ⟩  LINKS · $1 → impl ◈ sase-tw — "lands the approved design"
  ```

  Trail entries beyond the last two collapse to `⟨ …3 › ✎plan ⟩`. The trail clears when
  the user navigates by any means other than a link hop, so it never lies about how you
  arrived.

### 5.4 The invisibility contract

The brief is emphatic, and 97% of agents depend on it. Three independent mechanisms,
all keyed off one predicate — `link_edges_for_selection() != ()`:

1. **Rail** — `display = False` and zero height. Not an empty bordered box; the widget
   is out of the layout, so the footer moves up and nothing shifts when it appears
   (Textual reflows the vertical stack, and the rail is the last thing above a fixed
   footer, so its appearance never moves the main container's height by more than its
   own row).
2. **Keymap** — `check_app_action(app, "follow_artifact_link", …)` returns `False`,
   which is the same mechanism that already hides `toggle_relation_panel` off the
   Artifacts tab (`_app_action_availability.py:282`). An unavailable action produces no
   binding, so `$` is inert and passes through.
3. **Footer and help** — because the footer is driven by action availability and
   `conditional_footer_entries`, no `$ links` chip is emitted and no help row appears.
   The Links panel modal is likewise unreachable.

Dangling links (target purged or never resolvable to a pane) **still count as links**:
the rail shows, the chip renders dim with `⊘` and `(missing)` — the vocabulary
`relation_panel.py:236` already uses — and `$N` on it emits a toast instead of
navigating. Hiding a dangling link would silently under-report the graph, which is worse
than an honest dead end.

### 5.5 Truncation must be provably stable

The one way a rail like this becomes unreliable is if a chip's key moves when the
terminal is resized. Contract:

- Chips are laid out in a **fixed order** — semantic relations first
  (`SEMANTIC_RELATIONS` = `related`, `supersedes`, `implements`, `derives-from`), then
  observational (`cites`, `read`), and within each group by perspective label and then
  by neighbor ref. That is exactly the sort key `neighborhood_footer` already uses
  (`sdd/artifact_link_neighborhood.py:71`), so the rail, the audited-read footer, and
  the modal all agree on ordering.
- **`$N` is assigned from that order and never from what fits.** A chip that does not
  fit is not renumbered; it is absorbed into `$0 +k more`. Pressing `$4` when chip 4 is
  off-rail still works, because the key map is complete even when the render is not.
- Degradation order under width pressure, applied in this sequence: drop the lead chip's
  `why`; abbreviate the lead chip's label to a sigil; drop trailing chips into `+k more`;
  drop the breadcrumb to `⟨ …n ⟩`; drop the header count.
- At 60 cells (the narrowest tested golden) the rail still shows
  ` LINKS 3 · $1 ← impl ✎…durability · $0 +2`.

### 5.6 `$0` — the Links panel

The overflow surface, a `ModalScreen` in the shape of Candidate B. Its jobs are the
four the rail cannot do:

1. **The tail.** 4 entities have 10–25 links.
2. **The `why`.** Median 120 chars, per row, wrapped — the reason the CLI table is
   unreadable is that it wraps a 240-char cell inside a 12-cell column; the modal gives
   each `why` its own indented line instead.
3. **Provenance.** `origin` (`derived` / `migrated` / `manual` / `read` / `prompt_ref`),
   `uses`, `created_at`, `created_by`. 63% of edges are `derived`, and being able to see
   that a link was inferred rather than asserted is what makes the graph trustworthy.
4. **Authoring.** `sase artifact link add` / `rm` equivalents, folding in the existing
   `ArtifactLinkModal` and the `artifacts_link_marked` action — which today is bound to
   `unbound` and only works on non-Patch Artifacts panes.

Row keys are `a`–`z` (the `AgentNeighborModal` convention), so `$0` then `k` reaches the
25th link in three keystrokes.

### 5.7 Off-query landings

The highest-value reliability requirement, because 63% of jumps cross panes and every
pane has a filter query. `bead:sase-tw` is closed; the Beads pane default query is
`-status:closed`; so a naive jump lands nowhere and today would emit
`"sase-tw is not in the current results"` (`navigation/_tree.py:350`).

Contract: **a `$N` jump always lands.** Order of attempts:

1. Switch tab if needed, then `_request_artifacts_entry(target)` — already handles
   sub-pane switching and deferred selection (`artifacts_navigation.py:117`).
2. If the target is not in the pane's results, widen the query minimally via the
   existing `reveal_entry_target` / `_change_query_for_navigation` path, which is
   currently same-pane only and must be reached on the cross-pane path too.
3. Toast exactly what changed — `query widened: -status:closed removed` — and record the
   pre-jump query digest in the `LinkHop` so `Ctrl+O` restores it.
4. Only if all of that fails does the jump report a dead end, and then it says which ref
   it could not resolve.

---

## 6. What each surface contributes

The rail renders a typed edge set. Where those edges come from is declared per surface,
exactly as `PaneRelationDecl.source` already declares `artifact_links` beside
`bead_parent…`, `agent_family…`, and `vcs_commit…`.

### 6.1 Artifacts tab — free

Every pane already declares 12–15 relations, of which 10–11 are `artifact_links`-sourced
(`sase artifact pane show beads`). The rail consumes the same
`ArtifactLinksSnapshot`. Nothing new is needed except the app-level index (§8).

### 6.2 Agents tab — one adapter

The live Agents tab selects an agent node whose name maps to `agent:<name>` through the
existing `reference_for_agent_name`, and `_known_target_for_ref` already handles both
bare and owner-qualified spellings via `current_owner_agent_name_lookup_candidates`
(`relations/artifact_links.py:222`). The adapter is: selected agent → canonical
`agent:` ref → index lookup. 193 of 6,611 agents will show a rail; the other 6,418 show
nothing, which is the contract working.

**Blocked on `sase-ua` (§1.4).** The aggregate the index reads contains zero agent rows
today, so this adapter would be correct and still render nothing. Build it, but verify it
against the store (`sase artifact link list agent:<name>`) rather than against the
aggregate until `sase-ua` lands.

A nice consequence: a live agent's `cites` and `read` edges are exactly the artifacts it
was given and consumed, so `$1` from a running agent jumps to the plan it is
implementing. That is the single most useful hop in the whole graph and it does not
exist today.

### 6.3 AXE tab — the one real decision

Chops have no artifact identity (§1.3.4), so "a chop links to the agents it launched"
cannot be expressed in the current store. Two ways:

**Option 1 — add a `chop:` ref kind.** Register `chop:<lumberjack>/<chop>` in
`sase-core`'s kind catalog, add an AXE `reference` copy target, and write real store rows
from the chop-agent registry.

- *For:* chops become first-class — link targets, `sase artifact link add` operands,
  prompt-citable, durable.
- *Against:* expands a deliberately closed catalog; needs a relation slug for "launched"
  that the closed v1 registry does not have (`related` would be a lie, `cites` worse);
  writes ~10³ machine-generated rows/month into a store whose whole `sase-tw` design
  effort was about *not* growing without payoff; and it is a `sase-core` release plus a
  Python migration for a feature whose value is one hop.

**Option 2 — surface-contributed virtual edges (recommended).** The AXE surface declares
an edge source `chop_launches` that projects the existing durable chop-agent registry
(`sase/axe/chop_agents.py`, keyed by `(lumberjack_name, chop_name)` and already carrying
`started_at`, `run_id`, and the launched agent identity) into `RelationEdge`s pointing at
`agent:` targets.

- *For:* zero new ref kinds, zero new relation slugs, zero store writes, no `sase-core`
  release. `RelationEdge` is already source-agnostic. The rail renders it identically,
  and `$1` jumps into Artifacts ▸ Agent — which is a genuinely great gesture: from "this
  chop ran" to "here is the agent it produced" in two keys.
- *Against:* chops are link *sources* only, not targets; a user cannot author a link on a
  chop; and the rail now shows rows that `sase artifact link list` will not show, so the
  boundary needs stating.

**Recommendation: Option 2, with the boundary made explicit** — the rail's chips carry a
writability flag, and only `artifact_links`-sourced chips are offered `rm`/`add` verbs in
the Links panel. If chops later need to be link *targets* (e.g. "this bead was filed by
that chop"), promote to Option 1 then, with the rail already in place and unchanged.

Lumberjacks and bgcmds get no edges in v1 and therefore no rail — correctly.

### 6.4 Kinds with zero coverage

Stitches and Patches have `artifact_links` relations declared but **zero rows** in the
live graph. They will simply never show a rail until something writes `stitch:` or
`patch:` edges. That is fine and is worth stating so nobody mistakes it for a bug — and
it is a good argument for `sase artifact link suggest`, which already proposes edges from
hard evidence and could seed this.

---

## 7. Boundary with the existing relations rail

After this lands, the Artifacts tab would have two one-line relation strips: the
pane-local collapsed relations rail at the bottom of the left list
(`▸ . expand · > 2 children`) and the app-level Link Rail above the footer. Two is one
too many unless the split is principled. It is:

> **Structure stays in the pane. Links become app-level.**
>
> Hierarchy and family relations (`parent`/`children`/`siblings`/`versions`/`retry_chain`)
> are always same-pane, always about *this list's* shape, and benefit from the tree
> rendering. They keep `<` / `>` / `~` / `.` and the `RelationPanel`.
>
> `RelationKind.LINK` relations are 63% cross-kind, exist on all three tabs, and are
> about the artifact rather than the list. They move to the rail and `$`.

Concretely: delete the LINK sections from `build_relation_view`'s output (or filter them
at the panel), which shrinks the relations rail to
`▸ . expand · > 2 children` and removes the odd unkeyed `1 plans` segment visible in
`artifacts_beads_collapsed_relations_120x40.png`. And **retire `beads_open_plan` /
`plans_open_bead` (`L`)** — both are hand-rolled single-link jumps that `$1` generalizes,
freeing `L` on two panes and deleting `first_link_target` plumbing from four files.

That is a net simplification, which is the strongest sign the boundary is the right one.

---

## 8. Performance

C6 says the rail paints on every highlight move, undebounced. Budget: p95 < 16 ms
key-to-paint (`sase/memory/tui_perf.md`).

- **Index.** One app-level `dict[str, tuple[LinkChip, ...]]` built off-thread from the
  already-cached `ArtifactLinksSnapshot`. 1,262 rows → 1,852 keys. Build cost is a
  single pass; memory is trivial. Rebuild is gated by the snapshot's existing mtime+size
  signature (`relations/artifact_links.py:255`), so rule 8 ("cache disk reads keyed by
  mtime; render paths never stat/glob") is satisfied by construction. Note that this
  signature detects *change*, not *correctness* — which is precisely how `sase-ua`
  (§1.4) stayed invisible for thirteen days, and an argument for adding a drift check to
  `sase artifact doctor` rather than to the render path.
- **Key normalization at build time, not lookup time.** `agent:` refs have bare and
  owner-qualified spellings; `stitch:` refs have short and full shas; `plan:` refs may
  arrive with or without `@`. All variants are inserted as aliases when the index is
  built, so the render path is one `dict.get`.
- **Render path.** `dict.get` + at most 9 chip renders into a `rich.Text`, `no_wrap`,
  `overflow="ellipsis"`. Comparable to the existing collapsed rail, which already paints
  synchronously today.
- **Instrumentation.** Wrap in `tui_trace("widget.link_rail.update")` as
  `relation_panel.py:99` does, and add the rail to the `bench_tui_jk.py` capture so a
  regression is caught rather than felt.
- **Startup.** The rail must not block first paint (rule 9). Before the index exists it
  renders nothing, and the first successful build triggers one coalesced refresh.

The genuine risk is not the lookup — it is the temptation to resolve a ref to a *label*
lazily on the render path (reading a bead title, statting a plan file). Do not. The rail
renders labels derived purely from the ref string; enrichment (bead status glyph, agent
state) comes from the pane's already-loaded `relation_entry_facts()` when available and
is simply absent otherwise.

---

## 9. Risks, and what would change the recommendation

| Risk | Severity | Mitigation / trigger to revisit |
| --- | --- | --- |
| The graph grows a long tail (many entities with 10+ links) | Medium | The whole two-keystroke claim rests on 99.8% ≤ 9. Re-measure after `sase artifact link suggest` is run in bulk. If p99 exceeds 9, promote the Links panel to primary and demote the rail to an indicator. |
| The rail's row appearing/disappearing causes layout jitter while scrolling a mixed list | Medium | Rail sits above a fixed footer, so only its own row moves. If jitter is felt, reserve the row permanently on tabs where >30% of rows are linked. Verify with a PNG golden per tab in both states. |
| Two rails on Artifacts confuse rather than clarify | Medium | §7's boundary. If it still confuses after use, merge by moving hierarchy into the rail too and deleting the pane panel — a bigger change deliberately deferred. |
| `$` collides with a future Textual or plugin binding | Low | `$` is unclaimed today and validated centrally; the keymap is user-overridable like every other action. |
| Chop virtual edges diverge from `sase artifact link list` | Low | Writability flag on every chip; the Links panel labels non-store rows by source. |
| Cross-pane query widening surprises the user | Medium | Always toast the change and always restore on `Ctrl+O` (§5.7). This is the one behavior worth an explicit test per pane. |
| The rail silently under-reports because its read model is stale | **High** | This already happened: `sase-ua` (§1.4) hid 231 rows for 13 days without a single symptom until someone diffed store against aggregate. Test the index against the store, and add store/aggregate drift to `sase artifact doctor`. A link surface that is *quietly* incomplete is worse than none, because it teaches the user that an entity has no links. |

**What would change the recommendation.** If the owner decides the `why` must be visible
without a second gesture, the rail cannot carry it beyond the lead chip and Candidate D
(detail-panel chips, two lines) becomes competitive — at the cost of the single-location
requirement. That is the one genuine trade in this design and it belongs to the owner.

---

## 10. Suggested phasing

Each phase is independently shippable and independently verifiable.

0. **`bead:sase-ua`.** Not part of this feature, but the Agents tab cannot be
   demonstrated until the aggregate carries agent rows again (§1.4).
1. **Index + predicate.** App-level link edge index, ref-spelling normalization,
   `link_edges_for_selection()` on all three tabs. No UI. Tested headlessly against the
   **store**, not only the aggregate, so a repeat of `sase-ua` fails the suite.
2. **The rail, read-only.** `LinkRail` widget, rendering spec §5.1, invisibility
   contract §5.4, truncation §5.5. PNG goldens per tab, present and absent, at 120×40
   and 60×30. Still no keys.
3. **`$` and `$N`.** `dollar_sign` in `_KEY_DISPLAY`, the reused one-shot prefix, the
   app-level jump verb, off-query landing §5.7, availability gating.
4. **Traversal.** `_link_trail`, breadcrumb, `Ctrl+O` / `Ctrl+Shift+O` integration.
5. **`$0` Links panel.** Overflow, `why`, provenance, and the folded-in authoring verbs.
6. **AXE chop edges** (§6.3 Option 2) and **§7's boundary cleanup** — retire the LINK
   sections from the relations rail and the two bespoke `L` jumps.

Phases 1–3 alone deliver the brief. 4–6 are the polish that makes it feel finished.

---

## 11. Open questions for the owner

1. **`$0` for the Links panel, or a letter?** `0` matches three existing "open the
   picker" bindings (`select_subtab`, `select_view`, `start_saved_query_mode`), but it is
   the one part of the grammar a user must be told rather than shown. The rail's
   trailing `$0 all` chip is the mitigation — is that enough?
2. **Should the lead chip's `why` be on by default?** It is the most informative thing on
   the rail and the first thing dropped when narrow, so it is also the least stable.
   Alternative: never show it, and let `$0` own every description.
3. **Chops as virtual sources (§6.3 Option 2) or a real `chop:` ref kind (Option 1)?**
   The report recommends Option 2 as v1, but Option 1 is the answer if chops should ever
   be link *targets*.
4. **Do stitches and patches deserve seeded edges?** They have relation declarations and
   zero rows. `sase artifact link suggest` could seed `stitch:`→`bead:` from commit
   trailers, which would light up the rail on the Stitch pane — worth doing, or scope
   creep?
5. **Row badges (Candidate E) as a later addition?** They answer "which rows are worth
   pressing `$` on", which nothing else does, at 2–3 cells per row.

---

## Appendix A — Reproducing the measurements

```bash
sase artifact link list -j -l 0 > /tmp/links.json      # 1,262 rows (the store)
sase artifact link list bead:sase-j7                    # the 25-link tail
sase artifact pane show beads                           # 15 declared relations
sase bead list                                          # 20 shown, 4,318 hidden
sase agent search -l 0 -j | jq length                   # 6,611 in the current scope
sase artifact link relation list                        # closed v1 registry
```

The 193-linked-agents figure comes from the store, by counting distinct `agent:` refs in
`/tmp/links.json` — **not** from `sase agent search 'linked:true'`, which returns 0
because of `sase-ua` (§1.4):

```bash
python3 -c "
import json
rows=json.load(open('/tmp/links.json'))
print(len({r['source_ref'] for r in rows if r['source_ref'].startswith('agent:')}))"   # 193
```

Degree distribution (the table in §1.2) is computed by counting each row once per
endpoint and applying the registry inverse on the target side, which is what
`_labeled_neighbors` (`sdd/artifact_link_neighborhood.py:39`) does for the audited-read
footer.

## Appendix B — Files this design touches

| File | Change |
| --- | --- |
| `ace/tui/_app_layout.py` | Yield `LinkRail` between `#main-container` and the footer |
| `ace/tui/widgets/link_rail.py` | New: rendering, truncation, chip model |
| `ace/tui/relations/link_index.py` | New: app-level ref→chips index with alias normalization |
| `ace/tui/keymaps/key_validation.py` | `"dollar_sign": "$"` in `_KEY_DISPLAY`, `"$"` alias |
| `ace/tui/keymaps/app_keymaps.py`, `default_config.yml` | `follow_artifact_link: "$"` under `ace.keymaps.app` |
| `ace/tui/_app_action_availability.py` | Gate `$` on a non-empty edge set (all three tabs) |
| `ace/tui/modals/numbered_link_keys.py` | Generalize the prefix key from `.` to a parameter |
| `ace/tui/actions/navigation/_tree.py` | Cross-pane `reveal_entry_target` on the link path |
| `ace/tui/actions/artifacts_navigation.py` | Query-widening + digest capture for `LinkHop` |
| `ace/tui/actions/navigation/_entry_jump_dispatch.py` | Link trail before per-surface anchors |
| `core/artifact_relation_layout.py` | Drop LINK sections from the pane view (§7) |
| `ace/tui/widgets/artifacts/relation_panel.py` | Remove the unkeyed link rail segments |
| `axe/…` | Project `chop_agents` records into `RelationEdge`s (§6.3) |
| `tests/ace/tui/visual/…` | Goldens per tab, rail present and absent, 120×40 and 60×30 |
