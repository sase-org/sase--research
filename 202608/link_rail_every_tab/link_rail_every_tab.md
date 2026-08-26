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
  - ux
---

# A Link Rail On Every Tab

**Research question.** ACE has three top-level tabs (Agents, Artifacts, AXE) and a
typed artifact-link graph that only one of them can see. How should a *single* link
surface — one keymap, one display location, one traversal model — reach every tab and
every entity, so that following a link costs almost nothing, the display is concise and
beautiful, and the whole feature vanishes when the selected entity has no links?

**Provenance.** This report consolidates two independent studies —
[`link_rail_every_tab__a.md`](link_rail_every_tab__a.md) (`research.16.cdx`, the
"Universal Links Panel") and [`link_rail_every_tab__b.md`](link_rail_every_tab__b.md)
(`research.16.cld`, the "Link Rail") — with a third pass of verification run for this
merge. Both reports independently converged on the same shape: a one-line, app-owned
rail above the footer, triggered by `$`. That convergence is the strongest signal in
this file. Where they disagreed, this report re-measured and rules.

**Method.** Measured on this machine on 2026-08-26 against `sase` at `2cbe2f17d`
(master, clean). Graph numbers come from `sase artifact link list -j -l 0`; the read
model from `~/.sase/projects/gh_sase-org__sase/artifact-links.json`; keymap facts from a
programmatic walk of `ace.keymaps` in `src/sase/default_config.yml`; performance rules
from an audited read of `sase/memory/tui_perf.md`. Every load-bearing claim from either
source report was re-checked against source. Corrections are marked **[corrected]**.

---

## Bottom line

Build the **Link Rail**: one app-owned, full-width, single-line widget docked directly
above `KeybindingFooter`, in literally the same position on all three tabs, with
`display: none` when the selection has no links. It renders numbered chips. `$` is a
**one-shot prefix, never a toggle**:

| Gesture | Effect | Cost |
| --- | --- | --- |
| `$1` … `$9` | Follow link *N*, switching tab and pane as needed | 2 keys |
| `$$` | Follow the lead chip | 2 keys |
| `$0` | Open the Links panel — every link with its `why`, origin, uses | 2 keys |
| `Ctrl+O` / `Ctrl+Shift+O` | Walk back / forward along the traversal trail | existing keys |

Two keystrokes reach **100%** of entities in the live graph. There is no armed mode to
remember, because the chips are painted *before* the prefix is pressed — the rail is
simultaneously the display, the legend, and the keymap, which is what keeps it honest.

Three measurements decide this, and all three point the same way:

1. **81.5% of linked entities have exactly one link; 99.8% have ≤9; the max is 25.**
   This is not a graph-browsing problem. It is a *one-chip* problem with a tiny tail.
2. **63% of edges are cross-kind**, so following a link is normally a cross-pane, often
   cross-tab move. The jump verb must belong to the app, not to a pane.
3. **Only 2.9% of agents and ~18% of beads have any link.** Invisible-when-empty is the
   dominant case, not an edge case.

**The one thing to fix first** is not a UI problem. The read model every TUI surface
consumes drifts continuously from the store, `sase doctor` reports it as ERROR right
now, and 61% of agent-endpoint refs are written in a spelling the agent catalog cannot
resolve (§4). A link surface that is *quietly* incomplete is worse than none, because
it teaches the user that an entity has no links.

---

## 1. The graph, measured

`sase artifact link list -j -l 0` → **1,267 rows, 1,855 linked nodes**.

Per-node degree, counting each row once for each endpoint:

| Links on the selected entity | Nodes | Share | Cumulative |
| --- | ---: | ---: | ---: |
| 1 | 1,512 | 81.5% | 81.5% |
| 2–3 | 271 | 14.6% | 96.1% |
| 4–9 | 68 | 3.7% | **99.8%** |
| 10–25 | 4 | 0.2% | 100% |

Median degree **1**, p90 **2**, max **25**. Cross-kind edges: **795 / 1,267 = 63%**.

Relations (as stored, one row each): `implements` 542, `related` 356, `cites` 142,
`derives-from` 138, `read` 89. There are **no live `supersedes` rows**, but the UI must
still treat one as high-priority when it appears.

Linked nodes by kind: bead 788, plan 686, agent 194, research 181, file 6.
**Stitches, patches, and chops have zero rows** — they will simply never show a rail
until something writes those edges. That is correct behavior, not a bug, and worth
stating so nobody files it as one.

> **Reconciling the three counts.** Report A measured 1,261 rows, B measured 1,262, this
> pass measured 1,267 — the graph grew by ~5 rows/hour while three agents worked. The
> *distribution* is stable across all three passes and is what the design rests on. No
> recommendation here depends on an exact row count.

The `why` description is median ~120 chars and truncates at 240. That single number
kills any design that puts `why` verbatim in a one-line rail, and explains why the
CLI's own table is unreadable: `sase artifact link list bead:sase-j7` wraps a 240-char
cell inside a 12-cell column across a 25-row table.

---

## 2. What already exists — about 70% of this, in the wrong place

| Piece | Where | Status |
| --- | --- | --- |
| Typed link store + closed relation registry | `sase-core` `artifact_link/relation.rs` | Landed (`sase-tw`) |
| Project aggregate, mtime-keyed cache | `ace/tui/relations/artifact_links.py:48` | Landed |
| Ref → pane-target resolution, **including cross-kind** | `relations/artifact_links.py:169` `_target_for_ref` | Landed |
| Textual-free relation layout + keymap model | `core/artifact_relation_layout.py` | Landed |
| Relation panel with a collapsed one-line rail | `widgets/artifacts/relation_panel.py` | Landed, Artifacts-only |
| Cross-pane navigation primitive | `actions/artifacts_navigation.py:117` | Landed |
| Query-widening reveal for off-query targets | `widgets/artifacts/panes.py:198` | Landed, same-pane only |
| One-shot `.N` numbered-link prefix | `modals/numbered_link_keys.py` | Landed, Memory/Glossary only |
| Bounded traversal trail + breadcrumb | `modals/memory_panel_travel.py` | Landed, Memory only |
| Context-sensitive action hiding | `_app_action_availability.py` `check_app_action` | Landed |
| Kind accents + icons | `_artifact_tab_model.py:52,64` | Landed |

Two of these are the design's proof-of-concept, and both were verified:

- **`numbered_link_keys.py` already implements the exact `$`-prefix contract** — arm on
  prefix, resolve on the next decimal digit, cancel on anything else, never fire while
  an `Input` has focus. It is parameterizable to `$` with a small change.
- **The codebase has already hand-built two special-cased single-link jumps.**
  `beads_open_plan` and `plans_open_bead` are both bound to `L`
  (`bindings.py:154,173`) and both call `keymap.first_link_target(...)`
  (`beads_navigation.py:268`, `plans_navigation.py:235`). Two bespoke instances of
  "jump to the linked thing" is the strongest possible evidence that the general verb is
  needed — and `$1` subsumes both.

### 2.1 Five verified gaps

1. **Link rows have no key.** `build_relation_view` assigns `key=""` to every
   `RelationKind.LINK` row (`artifact_relation_layout.py:262,268`). Confirmed.
2. **The collapsed rail gives links no mode key.** `_rail_mode_key` returns `""` for
   `RelationRole.LINK` (`relation_panel.py:~470`). Confirmed — hence the odd unkeyed
   `1 plans` segment in the goldens.
3. **The surface is Artifacts-only.** `_app_action_availability.py:282` hard-gates
   `toggle_relation_panel` to `ARTIFACTS_TAB`. Confirmed.
4. **AXE entities have no artifact identity.** No `chop:` ref kind exists (§5).
5. **Traversal back is per-surface, and one of them is not even a stack.**
   `_artifacts_jump_history` is `dict[ArtifactsPaneKey, ArtifactEntryTarget]`
   (`actions/artifacts_navigation.py:36`) — **one slot per pane**, while
   `_entry_jump_agents_anchor_stack` is a separate per-tab list. A cross-tab link walk
   has nowhere to record itself. Confirmed.

### 2.2 The layout seam is a one-line insert

`_app_layout.py` closes `Horizontal(id="main-container")` and immediately does
`yield KeybindingFooter(id="keybinding-footer")` at line 102. The rail goes between
them. This is the only location that is literally the same object on all three tabs.

---

## 3. The interface decision

Five candidates were considered across the two source reports. Scored against the
brief's own clauses:

| | A. Pane panel | B. Modal only | **C. Link Rail** | D. Detail chips | E. Row badges |
| --- | --- | --- | --- | --- | --- |
| One location on all 3 tabs | ✗ | n/a | **✓** | ✗ | ✓ |
| Displays links without a gesture | if expanded | ✗ | **✓** | ✓ | partial |
| Keystrokes to follow (median) | 3 | 2 + screen | **2** | 2 | n/a |
| Legend co-located with keys | ✓ | ✓ | **✓** | ✗ (scrolls) | n/a |
| Zero cost when no links | partial | ✓ | **✓** | ✓ | ✓ |
| Cost when links exist | ≤24 rows | full screen | **1 row** | 1–2 rows | 3 cells/row |
| Good at n=1 (81.5%) | poor | poor | **excellent** | good | poor |
| Good at n=25 (0.2%) | good | **excellent** | handoff to `$0` | poor | poor |
| Repaints inside 16 ms | ✓ | n/a | **✓** | ✗ (debounced) | risk |

The rejections are concrete, not aesthetic:

- **Extending `RelationPanel` to every tab (A)** cannot be app-level.
  `RelationPanelHostMixin` reads `self.contract`, `self.relation_index()`,
  `self.selected_entry_target()` — a pane API the Agents tree and AXE sidebar do not
  have. Making it app-level means rewriting the mixin as an app service, i.e. doing the
  rail's work anyway while keeping the pane widget. It also fuses all four relation axes,
  so `$` could never be gated independently of `<`/`>`/`~`.
- **Modal-first (B)** cannot satisfy the *display* half of the brief. A modal shows
  nothing until opened; adding a "you have links" indicator to make it discoverable
  means building the rail anyway, at which point the modal is the overflow, not the
  primary.
- **Detail-panel chips (D)** are in a different place on every tab, which the brief
  forbids. Worse, detail panels are *scrollable* (chips can scroll off while their keys
  stay live — precisely the "armed mode you can't see" failure) and are **debounced at
  150 ms** by `DetailPanelDebouncer`. `tui_perf` rule 7 is explicit: *"Debounce detail
  panels, never the highlight."* Chips would lag the cursor and show the previous
  entity's links, which is a correctness bug, not a performance one.
- **Row badges (E)** are not a panel and carry no relation, target, or key. But they are
  a genuinely good *later addition on top of* the rail: the rail tells you about the
  selection, the badge tells you where to move the selection. Deferred, not rejected.

### 3.1 Resolving the two reports' central disagreement

Report A recommended `$` as a **toggle** that expands a bounded "peek tray" (up to 12
rows) reserving layout space; report B recommended `$` as a **one-shot prefix** with a
permanent one-line rail and a `$0` modal for overflow.

**B's grammar wins, and A's tray content becomes the `$0` panel's specification.**
Reasons, in order of weight:

1. **The tray is over-built for the data.** At n=1 — 81.5% of entities — A's tray
   renders a bordered box, a section heading, and one row to say one thing, while
   shrinking the active view. B's rail says the same thing in one line.
2. **The keystroke counts are identical.** A's `$1` is expand-then-digit; B's `$1` is
   prefix-then-digit. A pays a full layout reflow for the same two keys.
3. **A's own substrate choice is hazardous.** A recommends a Textual `OptionList` for
   the tray. `tui_perf` rule 12: *"`OptionList` emits `OptionHighlighted` echoes on
   programmatic `highlighted = X` assignments"* — requiring a guard flag cleared
   synchronously, or the cursor jumps. Not disqualifying, but it is new risk against
   `numbered_link_keys.py`, which is already shipped and proven.
4. **A's objection to the modal is real but is answered by the rail.** A argues a modal
   "hides the very entity whose relationships you are inspecting." True — which is
   exactly why the modal is demoted to overflow (`$0`) rather than being the primary
   surface. The rail keeps the ambient summary visible at all times.

The composition — rail primary, modal as `$0` overflow — is cheaper than either alone,
because the modal inherits the rail's index and the rail inherits the modal's ability to
say "there are more."

### 3.2 Why not make a bare `$` jump when there is exactly one link?

It would save a keystroke 81.5% of the time, which is a real prize. **Reject it anyway**,
for a verified failure mode rather than a purity argument.

`bindings.py:127-129` binds bare digits to Artifacts sub-panes:

```python
Binding("1", "show_artifacts_digit(1)", "Show Agents", show=False),
Binding("2", "show_artifacts_digit(2)", "Show Stitches", show=False),
Binding("3", "show_artifacts_digit(3)", "Show Patches", show=False),
```

So if `$` sometimes fires immediately, typing `$2` at a one-link bead would follow link 1
**and then switch to the Stitches pane**. The user lands two surfaces from where they
aimed, with no error and no undo hint. A uniform two-key grammar makes that unreachable.

Prefix-doubling (`$$`) is already the house idiom for "the default action of this mode"
— `%%`, `!!`, `,,`, `zz` — so it reads as familiar rather than clever.

### 3.3 Why `$` — with a correction

`$` is genuinely free: a programmatic walk of every value under `ace.keymaps` in
`default_config.yml` shows `dollar_sign` with **0 uses** across 109 distinct key
strings. It also joins a coherent family: `<` ancestors, `>` children, `~` family,
`$` links — the fourth and final relation axis.

**[corrected]** Report B claimed the audit "leaves only `"`, `$`, `&`, `\`, `|`
unclaimed." That overstates the scarcity. In `ace.keymaps` the unclaimed set also
includes `tilde`, `less_than_sign`, and several others — `<`, `>`, and `~` are claimed
in hardcoded panel defaults (`_DEFAULT_MODE_KEYS`), not in config. The conclusion is
unaffected — `$` is free and is the right choice — but the key space is less
constrained than B implies, so `$` is a *preference*, not a forced move.

Implementation cost is one line: `"dollar_sign": "$"` in `_KEY_DISPLAY`
(`keymaps/key_validation.py:8`), plus a `"$"` alias beside the existing `"+"`/`"-"`
friendly spellings.

---

## 4. The reliability problem that outranks the UI

Both source reports measured the graph from `sase artifact link list`, which reads the
**store**. Every TUI surface reads something else: the machine-local aggregate
`~/.sase/projects/<key>/artifact-links.json`, via `load_artifact_links_snapshot()`.
This is where the design's real risk lives, and this pass found a materially different
picture from either report.

### 4.1 The aggregate drifts continuously — **[corrected]**

Report B measured the aggregate at 1,031 rows with **zero** agent/`cites`/`read` rows —
231 rows stale — and filed `bead:sase-ua` (READY, large, `task(bug)`), calling it a
hard blocker for the Agents tab. Report A never noticed the issue at all.

Re-measured for this report, the aggregate now holds **1,267 rows with 231 agent
endpoints**, matching the store's counts and relation distribution exactly. The
catastrophic staleness B found was real, and was repaired between B's measurement and
this one. But:

```
$ sase doctor -C project.artifact_links_aggregate
ERROR  project.artifact_links_aggregate
       artifact-links aggregate is missing or stale versus sidecar links/
```

A row-level diff shows the current drift is **exactly one row** — an aggregate-only
`plan:202608/artifacts_description_visual_residue.md implements bead:sase-u6.5`.

So the correct framing is neither A's silence nor B's one-time blocker:

> **The aggregate drifts continuously during normal operation.** It re-drifted within
> minutes of being rebuilt. `sase-ua` is a live defect, but its severity is
> "the read model is never authoritative," not "the read model is empty."

Two consequences the source reports missed:

- **The blocker framing is wrong.** B sequenced `sase-ua` as phase 0, blocking the
  Agents-tab adapter. It is not blocking today — agent rows are present, and
  `sase agent search 'linked:true'` returns **76 agents, not 0** **[corrected]**. Build
  the adapter now.
- **A drift check already exists.** B recommended "adding store/aggregate drift to
  `sase artifact doctor`." It is already implemented as
  `_check_artifact_links_aggregate` in `src/sase/doctor/checks_artifact_links.py:34`,
  comparing `load_aggregate()` against `preview_aggregate()` by row signature. The work
  is not to write the check; it is to make something *run* it and to make the rail
  resilient when it fails.

The mechanism that let this hide is worth naming: `_aggregate_signature` returns
`(project_key, st_mtime_ns, st_size)` (`relations/artifact_links.py:264`). That detects
*change*, not *correctness* — which satisfies `tui_perf` rule 8 by construction, and is
exactly why a class-wide omission stayed invisible.

### 4.2 The agent ref spelling split — a new finding

Neither report diagnosed this, and it directly determines whether the Agents-tab rail
works. The store writes `agent:` refs in **three incompatible spellings**, and the split
falls cleanly along writer lines:

| Spelling | Distinct refs | Written by |
| --- | ---: | --- |
| owner-qualified with `--plan` suffix (`agent:bbugyi200.athena.000--plan`) | 111 | `cites` (113 rows) |
| dotted (`agent:sase-tj.land.w3`) | 67 | `read` (68), `cites` (29) |
| bare short id (`agent:094`) | 16 | `read` (21) |

Of 194 distinct agent refs in the store, **118 do not match any name returned by
`sase agent search`** — which is precisely why `linked:true` resolves 76 rather than
194.

`_known_target_for_ref` (`relations/artifact_links.py:201`) *does* already handle
bare-vs-owner-qualified via `current_owner_agent_name_lookup_candidates`, but it does so
by **iterating every known target per ref** — an O(n) scan on what must be an O(1)
render path, and it has no provision for the `--plan` role suffix.

**This makes B's "normalize at build time, not lookup time" mandatory rather than an
optimization, and gives it a concrete specification:** when the index is built, insert
every alias spelling of a ref as a key — bare, dotted, owner-qualified, and
role-suffixed — so the render path is one `dict.get`. Without it the Agents rail will
silently under-report on ~61% of linked agents.

### 4.3 What this means for the design

- **Test the index against the store, not the aggregate.** A repeat of `sase-ua` must
  fail the suite. This is B's phase-1 instruction and it is correct.
- **Surface drift instead of hiding it.** When the index is known-stale, the rail should
  still render what it has; the `$0` panel is the right place for a one-line
  "index stale — run `sase doctor`" note. Do not put a validation on the render path.
- **Agents are currently only ever link *sources*** — 194 distinct agent source refs and
  **zero** agent target refs. Any `launched-by` edge on an agent row would be the first
  inbound agent edge in the graph (§5).

---

## 5. Chops: resolving the reports' second disagreement

The user explicitly wants chops to link to the agents they launched. Chops have no
artifact identity, so this needs a decision, not just wiring.

- **Report A** proposed a real `chop:` ref kind plus a registered `launches` /
  `launched-by` relation, written durably at the launch boundary.
- **Report B** proposed surface-contributed *virtual* edges projected from the existing
  durable chop-agent registry, with no new ref kind and no store writes.

Both are defensible, and their strongest arguments do not actually conflict:

- A is right that a virtual-only edge is **outbound-only**, so an agent row could never
  jump *back* to the chop that launched it — and right that provenance should not vanish
  when bounded run history is pruned.
- B is right that a `chop:` kind expands a deliberately closed catalog, needs a relation
  slug the closed v1 registry lacks, requires a `sase-core` release plus a Python
  migration, and would write ~10³ machine-generated rows/month into a store whose entire
  `sase-tw` design effort was about *not* growing without payoff.

**Recommendation: B's virtual edges for v1 — but indexed in both directions**, which
defeats A's main objection without a core release.

The index is app-owned, so it can insert *both* `chop→agent` and `agent→chop` entries
from the same projection. `src/sase/axe/chop_agents.py` already carries durable
chop-agent linkage keyed by `(lumberjack_name, chop_name)` with `started_at` and
`run_id`, and `_chop_lifecycle_types.py:31` persists the `launches` roster with the
actual allocated agent name. That is machine-owned provenance — no heuristic needed. So
an agent row *can* show `← launched-by ⚙ chop` in v1.

The residual cost is honest and should be stated rather than hidden: these rows will not
appear in `sase artifact link list`, so the rail shows something the CLI does not.
Mitigate by carrying a **writability flag** on every chip — only `artifact_links`-sourced
chips are offered `add`/`rm` verbs in the `$0` panel, and the panel labels non-store rows
by source.

Promote to A's real `chop:` kind when — and only when — chops need to be link *targets*
of user-authored edges (e.g. "this bead was filed by that chop"). The rail does not
change when that happens, which is the point of doing it in this order.

Lumberjacks and background commands get no edges in v1, and therefore no rail. Correct.

---

## 6. The recommended design

### 6.1 Placement and anatomy

One new widget, `LinkRail`, yielded by `AppLayoutMixin.compose` between
`#main-container` and `KeybindingFooter` (`_app_layout.py:102`).

```
 LINKS 3 · $1 ← implemented-by ✎ artifact_link_durability — "lands the design" · $2 ↔ rel ◈ sase-u3 · $0 all
 └──┬──┘   └┬┘ └────┬────────┘ └┬┘ └──────┬──────────┘   └────────┬─────────┘   └── sigil chips ──┘  └─┬─┘
 header    key   perspective   kind   short target label      elided why (lead only)              overflow
           chip     label     icon+
                              accent
```

- **Header** — `LINKS` plus count, in the *selected entity's* accent. Count omitted at
  n=1; the single chip already says it.
- **Key chip** — `$N`, matching the `[key]` style the relation panel already uses.
- **Direction glyph** — `→` this entity is the source, `←` this entity is the target,
  `↔` undirected (`related`). Always **relative to the selected entity**, using the
  existing perspective-corrected label from core. This eliminates the most common
  link-graph cognitive tax: mentally reversing a directed triple. Never display the bare
  stored slug.
- **Relation label** — full word on the lead chip; four-letter sigil on the rest
  (`impl`, `cite`, `read`, `rel`, `sup`, `deriv`).
- **Kind icon + accent** — from the existing `ARTIFACTS_ICONS` / `ARTIFACTS_ACCENTS`
  (`_artifact_tab_model.py:52,64`; verified: beads `#D787FF`, agents `#0062FF`, stitches
  `#FFD700`, patches `#00D7AF`, files `#FFAF5F`, plans `#AF87FF`), painted in the
  **destination** pane's accent.

  This is the design's best idea and both reports arrived at a version of it: *the hue
  tells you where the key will take you*, so "jump to the bead" and "jump to the plan"
  are distinguishable pre-attentively at **zero cell cost**. It is also the cheapest
  possible answer to A's "destination badge" requirement — A spent 6–8 cells per row on
  a textual `→ Beads` badge to convey what the accent conveys for free.
- **Short target label** — ref with kind prefix removed and shortened:
  `bead:sase-u3` → `sase-u3`; `stitch:sase-org/sase@f4b827af6` → `sase@f4b827a`.
- **Lead-chip `why`** — only the lead chip carries an elided description, dim, in
  typographic quotes. First thing dropped under width pressure.
- **Overflow** — `$0 all` always terminates the rail; when chips do not fit it becomes
  `$0 +7 more`.

Rendered per tab at 120 cells:

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

### 6.2 Ordering and truncation must be provably stable

The one way a rail like this becomes unreliable is if a chip's key moves when the
terminal is resized.

- Chips lay out in a **fixed order**: semantic relations first (`supersedes`,
  `implements`, `derives-from`, `related`), then observational (`cites`, `read`); within
  each group by perspective label, then neighbor ref. This is the sort
  `neighborhood_footer` already uses (`sdd/artifact_link_neighborhood.py:71`), so the
  rail, the audited-read footer, and the `$0` panel all agree.
- A superseding replacement, when one ever exists, pins first and colors amber — it
  changes how the current artifact should be interpreted.
- **`$N` is assigned from that order and never from what fits.** A chip that does not fit
  is not renumbered; it is absorbed into `$0 +k more`. Pressing `$4` when chip 4 is
  off-rail still works, because the key map is complete even when the render is not.
- Degradation order under width pressure: drop the lead chip's `why` → abbreviate the
  lead label to a sigil → drop trailing chips into `+k more` → collapse the breadcrumb →
  drop the header count.
- Duplicate observational endpoints render once with `N uses`; the user should not
  navigate to identical destinations several times.

### 6.3 The invisibility contract

Three independent mechanisms, all keyed off one predicate,
`link_edges_for_selection() != ()`:

1. **Rail** — `display = False`, zero height, out of the layout entirely. Not an empty
   bordered box, not a "0 links" badge, no placeholder, no toast.
2. **Keymap** — `check_app_action(app, "follow_artifact_link", …)` returns `False`, the
   same mechanism that already hides `toggle_relation_panel` off Artifacts
   (`_app_action_availability.py:282`). An unavailable action produces no binding, so
   `$` is inert and passes through.
3. **Footer and help** — driven by action availability, so no `$ links` chip and no help
   row are emitted, and the `$0` panel is unreachable.

An entity ACE cannot resolve to a ref — a synthetic clan banner, a workflow grouping
row, an AXE lumberjack, a background command — is presented **identically to a linkable
entity with zero edges: nothing**. Do not fabricate a ref from a row label to make the
rail appear.

**Dangling links still count as links.** The rail shows, the chip renders dim with `⊘`
and `(missing)` — the vocabulary `relation_panel.py:236` already uses — and `$N` on it
emits a toast instead of navigating. Hiding a dangling link would silently under-report
the graph, which is worse than an honest dead end.

### 6.4 Traversal, and the trail

Following a link makes the destination the selected entity, whose own rail paints
immediately — so `$1 $1 $1` walks three hops in six keys with no mode.

Going back is the one place this needs genuinely new plumbing, because §2.1.5 found
every existing back-stack is per-surface while link hops cross surfaces:

- An app-level `_link_trail`, bounded at 32, mirroring `memory_panel_travel.py`'s
  `_trail` and `_MAX_TRAIL_LENGTH`. A hop records `(tab, ArtifactEntryTarget, pane query
  digest, fold state)` — enough to restore what a forward hop widened or expanded.
- `Ctrl+O` pops the link trail when the most recent navigation event was a link hop, and
  otherwise falls through to the existing per-surface anchor stacks unchanged.
  `Ctrl+Shift+O` walks forward. **No new back key**; the vim convention ACE already
  teaches on all three tabs is preserved.
- Failed or dangling jumps do not mutate history.
- When the trail is non-empty the rail grows a leading breadcrumb chip, which is both the
  affordance and the legend:

  ```
   ⟨ ◈sase-tw › ✎artifact_link_durability ⟩  LINKS · $1 → impl ◈ sase-tw — "lands the design"
  ```

  Entries beyond the last two collapse to `⟨ …3 › ✎plan ⟩`. The trail clears when the
  user navigates by any other means, so it never lies about how you arrived.

### 6.5 A `$N` jump always lands

The highest-value reliability requirement, because 63% of jumps cross panes and every
pane has a filter query. `bead:sase-tw` is closed; the Beads pane default query is
`-status:closed`; a naive jump lands nowhere and today emits *"sase-tw is not in the
current results"* (`navigation/_tree.py:350`). Order of attempts:

1. Switch tab if needed, then `_request_artifacts_entry(target)` — already handles
   sub-pane switching and deferred selection.
2. If the target is not in the pane's results, widen the query minimally via the existing
   `reveal_entry_target` / `_change_query_for_navigation` path, which is currently
   same-pane only and must be reached on the cross-pane path too.
3. If the target is folded, expand only the ancestors needed; if it is outside a bounded
   head slice, request it by stable identity from a worker; if it is in another project
   scope, change scope under the same reversible treatment. Never report "missing" before
   resolving the target's owning project.
4. Toast exactly what changed — `query widened: -status:closed removed` — and record the
   pre-jump digest so `Ctrl+O` restores it.
5. Only then report a dead end, naming the ref it could not resolve.

**Destination policy** must be visible before `Enter` fires, and is resolved in the
snapshot so it cannot change between paint and jump: `bead:`/`patch:`/`stitch:`/`file:`
and provider documents route to their Artifacts pane; `chop:` routes to AXE. `agent:` is
the one intentional dynamic route — a loaded live agent goes to the Agents tab, anything
else to Artifacts ▸ Agent, whose registry spine is complete. If the target is already
represented in the current pane, prefer same-pane selection over a gratuitous tab switch.

### 6.6 `$0` — the Links panel

The overflow surface, a `ModalScreen` shaped like the existing `AgentNeighborModal`, with
row keys `a`–`z` so `$0` then `k` reaches the 25th link in three keystrokes. Its four
jobs are the ones the rail cannot do:

1. **The tail** — the 4 entities with 10–25 links.
2. **The `why`** — median 120 chars, each on its own indented line rather than wrapped
   into a 12-cell column.
3. **Provenance** — `origin` (`derived` / `migrated` / `manual` / `read` / `prompt_ref`),
   `uses`, `created_at`, `created_by`. Being able to see that a link was *inferred*
   rather than asserted is what makes the graph trustworthy. This is also where an
   index-stale warning belongs (§4.3).
4. **Authoring** — `add`/`rm`, folding in the existing `ArtifactLinkModal` and the
   `artifacts_link_marked` action, gated by the writability flag from §5.

Do not add a query language here in v1. Degree is tiny; direct keys beat opening a filter
input. Do not expand transitively — this is a one-hop neighborhood inspector, and every
jump naturally exposes the next hop.

---

## 7. Boundary with the existing relations rail

After this lands the Artifacts tab would have two one-line relation strips. Two is one
too many unless the split is principled. It is:

> **Structure stays in the pane. Links become app-level.**
>
> Hierarchy and family relations (`parent`/`children`/`siblings`/`versions`/
> `retry_chain`) are always same-pane, always about *this list's* shape, and benefit from
> the tree rendering. They keep `<` / `>` / `~` / `.` and the `RelationPanel`.
>
> `RelationKind.LINK` relations are 63% cross-kind, exist on all three tabs, and are
> about the artifact rather than the list. They move to the rail and `$`.

Concretely: filter the LINK sections out of `build_relation_view`'s output, which shrinks
the collapsed relations rail to `▸ . expand · > 2 children` and removes the unkeyed
`1 plans` segment visible in `artifacts_beads_collapsed_relations_120x40.png`. Then
**retire `beads_open_plan` / `plans_open_bead` (`L`)** — both are hand-rolled single-link
jumps that `$1` generalizes, freeing `L` on two panes and deleting `first_link_target`
plumbing from four files.

That is a net deletion, which is the strongest sign the boundary is right. Keep the
removal reversible until the universal route is proven — retain the old sections behind
the flag for one phase of A/B visual verification.

---

## 8. Performance

The rail paints on **every highlight move, undebounced** (`tui_perf` rule 7). Budget:
p95 < 16 ms key-to-paint.

- **Index.** One app-level `dict[str, tuple[LinkChip, ...]]` built off-thread from the
  already-cached `ArtifactLinksSnapshot`. 1,267 rows → ~1,855 keys plus aliases. Rebuild
  is gated by the existing mtime+size signature, satisfying rule 8 by construction.
- **Alias normalization at build time, not lookup time** (§4.2) — mandatory, not an
  optimization. All agent spellings, stitch short/full shas, and plan `@`-variants are
  inserted as keys so the render path is one `dict.get`. Never call the existing O(n)
  `_known_target_for_ref` scan from a render path.
- **Render path.** `dict.get` plus at most 9 chip renders into a `rich.Text`, `no_wrap`,
  `overflow="ellipsis"` — comparable to the collapsed relations rail, which already
  paints synchronously today.
- **Generation guards.** `tui_perf` rule 4: re-capture tab, entity, and generation after
  every await before applying. The rail must clear *immediately* on selection change — a
  stale summary from the prior row is worse than a brief absence.
- **Startup.** Rule 9: the rail must not block first paint. Before the index exists it
  renders nothing; the first successful build triggers one coalesced refresh. An
  all-projects aggregate extension must not gate startup.
- **Instrumentation.** Wrap in `tui_trace("widget.link_rail.update")` as
  `relation_panel.py:99` does, and add the rail to `bench_tui_jk.py` so a regression is
  caught rather than felt.

The genuine risk is not the lookup — it is the temptation to resolve a ref to a *label*
lazily on the render path (reading a bead title, statting a plan file). **Do not.** The
rail renders labels derived purely from the ref string; enrichment comes from the pane's
already-loaded `relation_entry_facts()` when available and is simply absent otherwise.

---

## 9. Verification

The suite that matters, beyond the obvious:

- Every ref kind in **both endpoint positions**; directed primary and inverse labels;
  symmetric `related`.
- Neighborhoods of 1, 2, 9, 10, and 25 links; duplicate observational rows converging to
  `uses`; semantic-before-activity ordering.
- **All three agent ref spellings resolve to the same row** (§4.2) — the regression test
  that would have caught `linked:true` returning 76 of 194.
- **The index matches the store, not the aggregate** — the test that would have caught
  `sase-ua`.
- Dangling target visible but disabled; jump failure leaves history untouched.
- Zero-link entity: no widget, no footer action, no help row, no command-palette entry.
- Synthetic Agents banner, AXE lumberjack, background command: no widget.
- Selection changes mid-async-refresh: no stale rail paint.
- Filtered / folded / outside-head-slice / cross-project targets each reveal and restore.
- `Ctrl+O` / `Ctrl+Shift+O` round trip across **all pairs** of top-level tabs.
- Chop launch edge survives run-history pruning and chop disable.

**Visual coverage.** The suite has 561 PNG goldens, 515 of them at 120×40, with narrow
coverage at 60×30, 70×32, 70×36, and 80×24. Add: the same collapsed rail location on all
three tabs; 1-link, 3-link, and 12-link renders; inverse-direction labels; a dangling
row; the breadcrumb; 120×40 and 60×30.

The strongest no-links assertion is not "the panel says empty" — it is **exact pixel
equality with a view that has no rail mounted at all.**

---

## 10. Phasing

Each phase is independently shippable and verifiable.

1. **Index + predicate.** App-level edge index, **alias normalization for all agent ref
   spellings** (§4.2), `link_edges_for_selection()` on all three tabs. No UI. Tested
   headlessly against the **store**.
2. **The rail, read-only.** `LinkRail` widget, rendering spec §6.1, invisibility contract
   §6.3, truncation §6.2. PNG goldens per tab, present and absent, at two widths. Still
   no keys.
3. **`$` and `$N`.** `dollar_sign` in `_KEY_DISPLAY`, the reused one-shot prefix
   generalized from `.`, the app-level jump verb, off-query landing §6.5, availability
   gating.
4. **Traversal.** `_link_trail`, breadcrumb, `Ctrl+O` / `Ctrl+Shift+O` integration.
5. **`$0` Links panel.** Overflow, `why`, provenance, index-stale note, authoring verbs.
6. **AXE chop edges** (§5, bidirectionally indexed) and **§7's boundary cleanup** —
   retire the LINK sections and the two bespoke `L` jumps.

Phases 1–3 alone deliver the brief. 4–6 are what make it feel finished.

`bead:sase-ua` runs in parallel, not as a gate — §4.1 corrects B's phase-0 sequencing.
It should be rescoped from "the aggregate is 231 rows stale" to "the aggregate drifts
continuously and nothing runs the existing drift check."

---

## 11. Risks

| Risk | Severity | Mitigation / trigger to revisit |
| --- | --- | --- |
| The rail silently under-reports because its read model is stale or its refs don't normalize | **High** | Both have already happened (§4.1, §4.2). Test the index against the store; alias every spelling; surface staleness in `$0`. |
| The graph grows a long tail (many entities with 10+ links) | Medium | The two-keystroke claim rests on 99.8% ≤ 9. Re-measure after `sase artifact link suggest` runs in bulk. If p99 exceeds 9, promote `$0` to primary and demote the rail to an indicator. |
| Cross-pane query widening surprises the user | Medium | Always toast the change, always restore on `Ctrl+O` (§6.5). Worth an explicit test per pane. |
| Rail appearing/disappearing causes layout jitter while scrolling a mixed list | Medium | It sits above a fixed footer, so only its own row moves. If jitter is felt, reserve the row permanently on tabs where >30% of rows are linked. |
| Two rails on Artifacts confuse rather than clarify | Medium | §7's boundary. If it still confuses after use, merge by moving hierarchy into the rail too and deleting the pane panel — deliberately deferred. |
| Chop virtual edges diverge from `sase artifact link list` | Low | Writability flag on every chip; `$0` labels non-store rows by source. |
| `$` collides with a future Textual or plugin binding | Low | Unclaimed today, validated centrally, user-overridable like every other action. |

**What would change the recommendation.** If the owner decides the `why` must be visible
without a second gesture, the rail cannot carry it beyond the lead chip, and
detail-panel chips become competitive — at the cost of the single-location requirement
*and* of `tui_perf` rule 7. That is the one genuine trade in this design, and it belongs
to the owner.

---

## 12. Open questions

1. **Should the lead chip's `why` be on by default?** It is the most informative thing on
   the rail and the first thing dropped when narrow, so it is also the least stable.
   Alternative: never show it, and let `$0` own every description.
2. **`$0` for the Links panel, or a letter?** `0` matches existing "open the picker"
   bindings, but it is the one part of the grammar a user must be told rather than shown.
   The trailing `$0 all` chip is the mitigation — is that enough?
3. **Chops as virtual sources (§5) or a real `chop:` ref kind?** This report recommends
   virtual-but-bidirectional for v1. Promote when chops must be link *targets*.
4. **Do stitches and patches deserve seeded edges?** They have relation declarations and
   zero rows. `sase artifact link suggest` could seed `stitch:`→`bead:` from commit
   trailers, which would light up the rail on two more panes — worth doing, or scope
   creep?
5. **Row badges as a later addition?** They answer "which rows are worth pressing `$`
   on", which nothing else does, at 2–3 cells per row.

---

## Appendix — reproducing the measurements

```bash
sase artifact link list -j -l 0 > /tmp/links.json   # 1,267 rows (the store)
sase doctor -C project.artifact_links_aggregate     # currently ERROR (§4.1)
sase agent search 'linked:true' -j -l 0 | jq length # 76, not 194 (§4.2)

# agent ref spellings (§4.2)
python3 -c "
import json,collections
rows=json.load(open('/tmp/links.json'))
s={r['source_ref'][6:] for r in rows if r['source_ref'].startswith('agent:')}
c=collections.Counter('--plan' if n.endswith('--plan') else 'dotted' if '.' in n else 'bare' for n in s)
print(len(s), c.most_common())"

# degree distribution (§1)
python3 -c "
import json,collections
rows=json.load(open('/tmp/links.json'))
d=collections.Counter()
for r in rows: d[r['source_ref']]+=1; d[r['target_ref']]+=1
v=sorted(d.values()); n=len(d)
print('nodes',n,'median',v[n//2],'p90',v[int(.9*n)],'max',max(v))"

# keymap audit (§3.3) — walks every value under ace.keymaps
python3 -c "
import yaml,collections
km=yaml.safe_load(open('src/sase/default_config.yml'))['ace']['keymaps']
c=collections.Counter()
def w(o):
    if isinstance(o,dict): [w(v) for v in o.values()]
    elif isinstance(o,list): [w(v) for v in o]
    elif isinstance(o,str): c[o]+=1
w(km); print('dollar_sign uses:', c.get('dollar_sign',0))"
```

Source-verified anchors used above: `_app_layout.py:102`, `bindings.py:127-129,154,173`,
`artifact_relation_layout.py:262,268`, `_app_action_availability.py:282`,
`relations/artifact_links.py:48,169,201,264`, `actions/artifacts_navigation.py:36,117`,
`doctor/checks_artifact_links.py:34`, `_artifact_tab_model.py:52,64`,
`modals/numbered_link_keys.py`, `axe/chop_agents.py`,
`axe/_chop_lifecycle_types.py:31`.
