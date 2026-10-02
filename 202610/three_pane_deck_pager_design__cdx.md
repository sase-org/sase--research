**Three-pane decks and pager: a design built around stable reading state**

Independent research by **cdx**, 2026-10-02. Repository examined: `sase` at `47907502b6932734221302dc6f4706b6034422d4`; local Textual version: **8.0.1**. I read the shared `sase-1eg` epic and its approved plan, inspected the current source and existing visual goldens, and ran two small local experiments. I did not consult any other researcher's report, chat, summary, or findings. This is a design recommendation, not an implementation or a completed usability study.

**I recommend shipping the three-pane feature, with a few explicit refinements.** Two orthogonal T-shaped layouts are a useful ceiling: they support Main + Files + Tools in Agents, and source + linked material + historical material in the pager, without turning SASE into a general window manager. Retain the proposed split-key behavior, but define it through a small, shared presentation model with stable pane identities. Add portable alternatives to the shifted Control shortcuts. Repair the existing pager teardown bug before extending it.

The core design principle is that a pane represents a reading session, while its rectangle is temporary. Rotating, swapping, resizing, and changing focus should preserve the session's document or deck, card, scroll anchor, search, folds, history, and outstanding work. Beauty follows from that stability as much as from borders and colors.

**The proposal is good, but the current wording leaves important decisions open.** Reusing `\` and `|` keeps the interaction compact, and reverse focus plus swapping makes three panes manageable. The cost is that the same key now means create, collapse, or transpose depending on state. Existing users also lose the direct two-pane rotation gesture: the opposite split key will create a third pane instead. A precise transition table and state-sensitive help are necessary.

I would not start with arbitrary recursive splitting, four panes, drag resizing, synchronized scrolling, or persistent pager sessions. Those features multiply geometry and lifecycle cases without strengthening this request. I would also avoid two separately implemented three-pane state machines; the existing duplicated two-pane logic has already diverged.

**What the current implementation establishes.** These findings come from local source inspection at the revision above; the code links are pinned to that revision.

| Finding | Evidence and implication |
| --- | --- |
| The deck and pager each have three current layout enum values: single, stacked, beside. | [Pager model](https://github.com/sase-org/sase/blob/47907502b6932734221302dc6f4706b6034422d4/src/sase/pager/split.py) and [deck model](https://github.com/sase-org/sase/blob/47907502b6932734221302dc6f4706b6034422d4/src/sase/ace/tui/widgets/decks/model.py). Adding enum values alone will not generalize identity, targeting, and rendering. |
| Both pure focus models use `1 - focused`. The deck's click handler toggles focus rather than selecting the requested index. | [Deck area](https://github.com/sase-org/sase/blob/47907502b6932734221302dc6f4706b6034422d4/src/sase/ace/tui/widgets/decks/area.py). A three-pane mouse click must select its actual pane ID. |
| Deck unsplit keeps panel 0; pager unsplit intends to keep the focused pane. | [Deck transitions](https://github.com/sase-org/sase/blob/47907502b6932734221302dc6f4706b6034422d4/src/sase/ace/tui/widgets/decks/layout.py), pager model above. Unify this around the focused pane. |
| Deck widgets are precomposed as exactly two panels; styles encode panel 0/1 and one ratio. | Deck area above and [styles](https://github.com/sase-org/sase/blob/47907502b6932734221302dc6f4706b6034422d4/src/sase/ace/tui/styles.tcss). Two independent split ratios and identity-based placement are needed. |
| Deck persistence is schema 1 and caps `MAX_PANELS` at 2. | [Persistence](https://github.com/sase-org/sase/blob/47907502b6932734221302dc6f4706b6034422d4/src/sase/ace/tui/models/agent_deck_persistence.py). Without migration, the third pane can silently disappear on restart. |
| “Other pane” is hardcoded as the complement of one of two indices. | Deck `picker.py`; pager [split host](https://github.com/sase-org/sase/blob/47907502b6932734221302dc6f4706b6034422d4/src/sase/pager/_screen_split.py). The picker and `Ctrl+W` need an explicit destination rule. |
| New-pane content differs deliberately between surfaces. | Deck `choose_new_panel()` selects the next available unshown deck; pager `PagerView.split_seed()` clones the focused reading session. Keep both policies. |
| Pager labels, history, and workers are per-view. | [PagerView](https://github.com/sase-org/sase/blob/47907502b6932734221302dc6f4706b6034422d4/src/sase/pager/view.py). Only the focused view paints body and time-band labels; focus loss clears transient arms/input. Preserve this contract. |
| `Ctrl+B` already means prompt scrolling outside Agents; `Ctrl+F` has an intentional tab-disjoint collision. | `src/sase/default_config.yml`, `ace/tui/keymaps/registry.py`, `_app_action_availability.py`. Add the analogous collision rule and availability checks for reverse deck focus. |

The approved `plan:202610/pager_split_panes.md`, read through `sase artifact read`, deliberately excluded more than two panes. It also promises stable logical reading lines across width changes, independent history clones, focus-scoped link labels, small-window refusal, and modal isolation from ACE bindings. The `sase-1eg` landing notes document fixes for source-history cancellation and stale time-band labels. A third pane should extend these guarantees, not weaken them.

**A confirmed lifecycle defect changes the implementation priority.** A bounded Textual Pilot experiment opened a pager split at 120×40, then used either the same split key or `q`. Both paths retained one entry in `screen.views`, but left `#pager-panes` with **zero children** and `screen.query(PagerView)` with **zero results**. The retained view's `parent` was `None`, even though `is_mounted` still reported `True`.

The root cause is visible in `_screen_split.py`: the close and same-layout unsplit paths await `remove_children()` on the whole container, then keep a survivor reference without mounting it again. Existing close tests check the list length and layout, which do not prove that content remains displayed. I recorded this independent reproduction as [sase-1er](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1er/README.md). Repairing only the reference list will not be sufficient; surviving widgets must remain in the tree, and regression coverage must check rendering and continued interaction.

Reproduction outline, using the project virtual environment:

```python
app = SasePager(document_with_many_lines)
async with app.run_test(size=(120, 40)) as pilot:
    await pilot.pause()
    screen = app.screen
    await pilot.press("backslash")
    await pilot.pause()
    await pilot.press("backslash")  # repeat with "q"
    await pilot.pause()
    await pilot.pause()
    print(len(screen.views))                # 1
    print(screen.focused_view.parent)        # None
    print(len(screen.query(PagerView)))      # 0
    print(len(screen.query_one("#pager-panes").children))  # 0
```

This probe establishes the detached widget tree on the inspected revision. It is not a claim that every released build has the same defect.

**Define the geometry before assigning keys.** Use “stacked” and “beside” in user-facing descriptions. Preserve horizontal/vertical terminology as aliases, but avoid making readers infer whether an orientation describes the divider or the pane placement.

There are five layout families: single (`S`), stacked two (`H2`), beside two (`V2`), stacked three (`H3`), and beside three (`V3`). Each three-pane family has two mirrored variants because either existing pane can be split. Thus “two new views” means two families, not only two fixed physical arrangements.

For example, split the focused bottom pane of H2 to produce H3:

```text
H2                      H3                         V3
┌─────────────────┐     ┌─────────────────────┐    ┌──────────┬──────────┐
│ A               │     │ A: spans full width  │    │ A: spans │ B        │
├─────────────────┤  |  ├──────────┬──────────┤ |  │ full     ├──────────┤
│ B: focused      │ ──► │ B        │ C: new * │ ─► │ height   │ C: *     │
└─────────────────┘     └──────────┴──────────┘    └──────────┴──────────┘
```

Splitting the top pane produces a top pair and bottom spanning pane instead. The analogous left-focused V2 produces a left pair and right spanning pane. Do not relocate unrelated content merely to force one canonical picture.

Call the unsplit root child the **spanning pane**, rather than the “larger pane.” At skewed ratios it can have less area than either of the paired panes. This structural definition makes collapse predictable and independent of pixel measurements.

**The requested split-key sequence is coherent with this complete table.** The labels H/V describe the outer split, following existing SASE/Vim terminology.

| Current layout | Backslash `\` | Pipe `\|` |
| --- | --- | --- |
| S | Open H2; new bottom pane takes focus | Open V2; new right pane takes focus |
| H2 | Keep only the focused pane → S | Split the focused pane beside → H3; new pane takes focus |
| V2 | Split the focused pane below → V3; new pane takes focus | Keep only the focused pane → S |
| H3 | Close the spanning pane; promote the beside pair → V2 | Transpose both split axes → V3; preserve all panes and focus |
| V3 | Transpose both split axes → H3; preserve all panes and focus | Close the spanning pane; promote the stacked pair → H2 |

“Transpose” means changing stacked to beside and beside to stacked at both nodes, preserving child order, pane identities, and each node's ratio. It is not a physical clockwise rotation with child reversal. Two transpositions restore the original tree, ratios, pane order, and focused session.

If collapsing H3/V3 removes the focused spanning pane, focus moves to its next surviving pane in the defined cycle. If the focused pane survives, retain it. The diagram therefore supports `H3 + backslash → V2(B,C)` with C still focused. The two-pane same-key collapse should keep the focused session on **both** surfaces, correcting the deck's current panel-0 behavior.

A rejected split or transpose leaves the entire state unchanged and explains what would fit. Do not silently turn a rejected third-pane creation into the old two-pane rotation; a key should have one meaning in a given state.

**Focus and swapping need one visible ordering rule.** Traverse the layout tree in child order: top before bottom for a stacked node; left before right for a beside node; complete a nested branch before moving to its sibling. Show compact ordinal badges `1`, `2`, `3` in split-pane titles so this order is visible. This remains stable when the axes transpose. In the mirrored V3 with a left pair, the cycle visits top-left, bottom-left, then the spanning right pane. That is intentionally structural order, rather than sorting rectangles by their top-left coordinates.

`Ctrl+F` focuses the next pane; `Ctrl+B` focuses the previous pane; both wrap. They do nothing in a genuine single-pane layout. Clicks select the clicked pane directly. Exactly one pane has logical focus, and actual Textual focus must agree with it.

`Ctrl+Shift+F/B` swaps the focused pane with the next/previous pane in that same cycle, also wrapping. Swap complete reading sessions between layout slots, and let focus follow the original session to its new slot. Layout ratios belong to the slots and remain unchanged. For example, moving an actively read file into the spanning slot should keep its reading anchor, search, history, and focus; it should not suddenly focus the document it displaced. With two panes, both swap directions exchange the same two sessions.

This borrows the useful separation between focus movement and moving window contents from established editor behavior. Neovim documents forward/reverse focus cycling and several exchange/rotation operations, although its exact mixed-layout exchange rules differ from the proposal here. The SASE ordering and identity rules above are my recommendation. [Neovim window documentation](https://neovim.io/doc/user/windows/#window-move-cursor)

**Deletion should normalize the tree, not choose a new preset.** `Ctrl+Shift+D` closes the focused visible pane only when at least two panes are visible. It closes a viewing session, not an agent, process, file, artifact, or source document. No confirmation is needed for this local presentation action.

Remove the leaf and promote its sibling:

- Delete a paired H3 child → H2, with its paired sibling filling that row.
- Delete H3's spanning pane → V2, with the existing pair filling the area.
- Delete a paired V3 child → V2, with its paired sibling filling that column.
- Delete V3's spanning pane → H2.
- Delete either two-pane child → S, preserving the other session.

Choose the next surviving pane in the pre-delete traversal order, wrapping if necessary. Surviving split ratios remain attached to their surviving nodes; a promoted leaf fills its new parent allocation. The pager's existing `q`, `Esc`, and exhausted `Backspace` should use this same close operation when split, while keeping their current single-pane pager exit behavior. `Ctrl+Shift+D` must never exit a single-pane pager.

For Agents zoom, retain the real tree and use a focused-pane visibility mask. Disable focus cycling, swaps, delete, and resize while explicit zoom shows only one pane; `Z` restores the arrangement. If a split key is used while zoomed, first restore the saved topology and then apply the table. This is a recommended adjustment to the current zoom/split interaction: it prevents a zoomed synthetic SINGLE state from accidentally discarding hidden sessions. Deck changes made during zoom must survive restore; this also deserves coverage around existing zoom-state work.

**“Other pane” should become “next pane,” with the target shown before following.** In three panes, pager `Ctrl+W <label>` should navigate the next pane in the shared cycle, keep focus in the source, and push history only in the destination. Doubled `Ctrl+W` should focus the next pane. In single-pane mode, retain the existing fit-aware new-split behavior.

The arm footer should say, for example, `open in pane 3 · source stays here`, and lightly mark the destination frame until the arm completes or is canceled. The deck picker's uppercase shortcut should use the same next-pane rule and show the destination's ordinal and spatial name. Do not introduce an implicit “most recently used other pane” rule; the destination could otherwise change without a visible change in layout.

Capture the destination's pane ID when the action is armed. If structural changes invalidate that ID before an asynchronous result arrives, cancel with a brief message rather than redirecting the result to whichever pane now occupies the same index. Keep the source's history generation untouched when only the destination navigates, preserving the fix documented by `sase-1eg`.

**The requested shortcuts need portable alternatives.** Textual explicitly warns that terminal and OS support varies and recommends `textual keys` to inspect actual key events. The kitty protocol separates modifier bits, while legacy encodings can merge shifted Control combinations. Those facts make a headless `pilot.press("ctrl+shift+d")` test insufficient evidence of physical-key availability. [Textual input guide](https://textual.textualize.io/guide/input/#key), [kitty keyboard protocol](https://sw.kovidgoyal.net/kitty/keyboard-protocol/)

I tested the installed Textual 8.0.1 input parser directly:

| Input bytes, expressed as escape notation | Decoded key event |
| --- | --- |
| `ESC [ 98 ; 6 u` | `ctrl+shift+b` |
| `ESC [ 102 ; 6 u` | `ctrl+shift+f` |
| `ESC [ 100 ; 6 u` | `ctrl+shift+d` |
| `ESC [ 27 ; 6 ; 98 ~` | No key event |
| `ESC [ 27 ; 6 ; 102 ~` | No key event |
| `ESC [ 27 ; 6 ; 100 ~` | No key event |

The installed Linux driver requests enhanced keyboard reporting with `ESC [ > 1 u`. A read-only query of this host's tmux 3.5a server reported **prefix `C-a`, `extended-keys off`, and `extended-keys-format xterm`**. This is evidence of a likely transport obstacle, not a physical-key end-to-end test. The current tmux manual describes extended-key forwarding and distinguishes its CSI-u and xterm formats. Default tmux configurations also intercept `Ctrl+B` as their prefix; this host's queried configuration uses `Ctrl+A` instead. [tmux manual](https://man.openbsd.org/tmux.1#extended-keys)

Keep the requested chords, but provide these two-keystroke alternatives in both surfaces:

| Action | Requested shortcut | Portable sequence |
| --- | --- | --- |
| Focus previous / next | `Ctrl+B` / `Ctrl+F` | `Ctrl+W Ctrl+B` / `Ctrl+W Ctrl+F` |
| Swap previous / next | `Ctrl+Shift+B` / `Ctrl+Shift+F` | `Ctrl+W Ctrl+P` / `Ctrl+W Ctrl+N` |
| Close focused pane | `Ctrl+Shift+D` | `Ctrl+W Ctrl+D` |

These second keys are Control events, not printable letters, so they preserve the pager's existing `Ctrl+W B/F/...` link-label alphabet. The armed sequence must intercept its second key before normal card, section, or scroll bindings. Keep the existing doubled `Ctrl+W` alias. A tmux user with the default prefix still needs pass-through or a remap for bare `Ctrl+B`; the alternative's behavior must be verified in that setup too.

Offer named pane actions in help, the deck's existing keymap system, and a menu/picker reachable with ordinary keys so no operation depends exclusively on extended reporting. Test CSI-u delivery through the actual terminal → tmux → Textual chain before making the shifted chords the only advertised path. I did not change this host's tmux configuration. A deployment configuration change would belong in its managed source, not in a one-off runtime workaround.

**Use a constrained split tree and a small shared Python presentation layer.** A useful model is:

```text
Leaf(pane_id)
Split(axis=stacked|beside, ratio=30|50|70, first=node, second=node)
PaneArea(tree, focused_id, zoomed_id=None)
```

Permit one to three leaves, depth at most two, and opposite axes for the two nodes of a three-pane tree. Those limits express exactly the requested families and mirrored variants. They exclude three equal stripes and arbitrary recursion. A flat list plus five layout enum values would still need flags for which side contains the pair, a second ratio, and special deletion cases. The bounded tree makes those relationships explicit without creating a general window manager.

Keep session payloads outside the geometry: `pane_id → DeckPanelState/widget` for Agents and `pane_id → PagerView` for the pager. Generate new IDs independently of ordinal positions. The pure transitions cover split-key presses, close, focus step, swap, transpose, and ratio changes. Content selection remains an adapter policy: deck smart selection versus pager clone.

This model is presentation-only. Existing pane state is Python/Textual state, and the approved pager epic explicitly treated it as outside the Rust backend boundary. Sharing geometry between two Textual surfaces does not make documents, agents, or history newly Python-owned domain behavior. I inspected the opened `sase-core` checkout at `015ce7f6ad1cc5ade253dc6d174ce55ae9dc30d3` and found no existing deck/pager split model in the targeted source search. I recommend a neutral presentation module, for example a new `sase/ui/` package, rather than having the pager import ACE widget internals. If implementation expands into persisted domain contracts that other frontends must share, move that domain behavior to `sase_core` and update its binding and CI revision pin.

Prefer a stable flat widget container whose layout adapter computes rectangles from the tree. Textual exposes `Layout.arrange()` and `WidgetPlacement` for this purpose. With at most three panes the adapter is small, and transposition/swapping can update placements without reparenting or remounting surviving views. A nested visual arrangement does not require a nested widget lifecycle. [Textual layout API](https://textual.textualize.io/api/layout/)

Closing should unmount only the discarded pane; creation should mount only the new pane. Rotating, swapping, resizing, zooming, and focusing should mount/unmount nothing. Route pane-local queries through direct view/panel references. Do not query repeated descendant IDs from the host, a stale-query risk already described in the approved epic. Replace duplicated `_focused_index`/split-model focus authority with one canonical focused ID and derived indices.

Apply structure changes as bounded transactions: validate candidate state and fit, prepare new content if needed, mount the new view, revalidate after any await, then publish state and layout. On failure, remove any newly mounted orphan and keep the prior arrangement. Guard or serialize concurrent structural actions and queued focus messages. Discard stale completions by pane identity plus navigation generation, not by slot number.

**Ratios and small windows need two-dimensional checks.** Preserve the outer ratio when creating the third pane and give the new inner split a 50/50 ratio. Keep both ratios through transposition. For existing grow/shrink keys, resize the focused leaf's immediate parent: the pair's internal divider for a paired pane, or the outer divider for the spanning pane. This avoids changing two dividers in one keystroke. It does mean a paired pane cannot adjust the outer divider directly; focus the spanning pane to adjust it. This limitation should be documented rather than hidden behind an unpredictable “try another ancestor” rule.

Compute fit recursively against the actual pane area's usable dimensions. The pager currently uses baseline minima of seven framed rows and 32 columns for its respective split axes. Start there, then account for visible time/trail/search chrome when specifying a five-body-row usability target. Deck toolbars may need different minima. At balanced ratios, either mixed three-pane family needs roughly **64 columns × 14 rows of pane area**, before host chrome/gutters and any extra pane chrome. That arithmetic is a lower bound, not a universal terminal-size recommendation.

The Agents stylesheet reserves **60 columns** for the node list. At 120 terminal columns, the detail area has about 60 columns before deductions, so a 32-column-per-leaf rule rejects mixed three-pane layouts while that list is expanded. The golden I inspected confirms how narrow the detail region can be. Check the detail region, not the full terminal. Recommend a toast such as `Need more deck width; Ctrl+S collapses the node list`. Do not silently change the user's sidebar preference to fit a third pane. At wider sizes or with the node rail collapsed, the layouts become much more useful.

If a stored ratio cannot fit but 50/50 can, use the balanced ratio with a brief explanation; otherwise refuse the requested creation/transposition. Grow/shrink clamps silently at fitting steps. On terminal shrink, preserve all sessions and the requested topology; clamp effective dividers where possible and compact pane chrome. Do not auto-delete panes or persist a temporary viewport-induced clamp over the user's stored ratio. Provide a clear small-window hint and retain split/close controls so the user can simplify the arrangement. An automatic hidden-pane fallback is a separate design problem and should not be required for the first version.

**The visual design should extend the existing frame language.** I inspected the existing `agents_decks_top_bottom_focus_bottom_120x40.png` and `split_beside_left_focused_120x40.png` goldens. Both already communicate focus through strong/dim accent frames; the pager also removes link badges from the unfocused pane. Preserve those strengths.

Use the current surface's border style—solid for decks, rounded for pager panes—with aligned edges, uniform gutters, and no surrounding frame around the paired group. The content frames already express the topology. Avoid extra divider captions, a permanent layout toolbar, or animated layout movement; they spend scarce rows and make moving text harder to track.

Put the ordinal and a small focus marker beside the existing deck/document title, for example `▶ 3 · FILES`. Use the section/deck accent for the frame, keep unfocused frames dim, and keep body text readable in every pane. The marker makes focus intelligible without relying solely on color. Only the focused pager pane paints actionable label badges, including time-band letters. Preserve single-pane chrome as closely as possible.

Truncate optional title details first, keep the content/deck name, and compact subtitles as space narrows. Each pane should budget its own chrome from its own height. The identity header and jump panel continue to span the entire deck area. One shared footer describes the focused pane and only currently available actions; put the complete shortcut family and state table in help. A succinct conditional footer can pair `Ctrl+B/F focus` with `Ctrl+Shift+B/F swap`, while the prefix arm provides its own compact instructions. Inspect it at 80×24 before deciding how much fits.

These T-shaped families resemble kitty's established Fat/Tall layouts, including mirrored versions. That is useful precedent for a spanning reading region plus two supporting regions, but it does not establish that SASE users prefer any particular ratio or key sequence. The proposed 50/50 defaults and visual details should be checked with real SASE content. [kitty layouts](https://sw.kovidgoyal.net/kitty/layouts/)

**Persistence and rollout are part of reliability.** Introduce a deck-state schema 2 with the tree, stable pane IDs, focused ID, per-pane preferences, and two split ratios. Accept schema 1 by generating a one- or two-leaf tree with deterministic IDs and retaining its panel order, ratio, focus, and node-collapse preference. Validate unique IDs, exact payload/leaf correspondence, allowed axes/depth, pane count, focus membership, and ratio range. Recover to a valid smaller arrangement with a warning if the topology is malformed; do not crash or quietly retain an invalid focused index. Pager arrangements remain session-local.

Continue saving through the existing coalesced off-thread persistence path. Keep Agents-tab ownership of saved layouts; a new layout model should not accidentally make per-tab panels global. Save effective edits made during zoom, not an obsolete snapshot. Concurrent-TUI persistence conflicts already have separate tracking and are not a reason to broaden this feature into a persistence rewrite.

The new meaning of the opposite two-pane split key needs a release note and revised help. If intermediate epic phases expose an incomplete feature, use the project's prescribed beta scaffolding and remove it before finished landing. If an old behavior branch must remain reachable for migration, follow the project's sunset-flag workflow; do not invent a permanent old/new-semantics preference or hand-add a flag registry entry. No flags were created by this research.

**A bounded implementation sequence makes this reviewable.**

1. Repair `sase-1er` and add mounted-tree, visible-content, and continued-interaction checks for every existing close/collapse path.
2. Extract the constrained presentation model. First adapt both existing two-pane hosts without changing behavior except explicitly chosen survivor consistency; prove their single/two-pane visuals and pager clone guarantees.
3. Add the third leaf, both mirrored T-shaped families, transpose/collapse, focus/swap/delete, and parent-local resizing. Use stable placement instead of destroying survivor widgets.
4. Generalize deck persistence, picker targeting, pager other-pane navigation, keymaps, collision rules, action availability, conditional footer, and help together. Include portable prefix alternatives.
5. Inspect three-pane views with real content, especially long replies, diffs, finalizer decks, time bands, and live streaming. Verify the supported terminal/tmux path, then land the complete behavior with updated docs and reviewed goldens.

Implementation touchpoints include `decks/model.py`, `layout.py`, `area.py`, `picker.py`, `_agent_detail_deck_layout.py`, refresh/source adapters that use `panel_index`, deck persistence, pager `split.py` and `_screen_split.py`, `_screen_host.py`, `view.py` host protocol, label arms, pager help/footer, Agents keymap dataclasses/metadata/registry, `_app_action_availability.py`, `src/sase/default_config.yml`, styles, and `docs/pager.md`/`docs/ace.md`. Search all touched areas for `1 - index`, fixed panel-0/1 assumptions, two-element unpacking, and panel-count caps. This is broader than adding two view names.

The existing `choose_new_panel()` policy should consider every visible deck, not only two. Creating the third deck should choose the next available unshown deck; if none qualifies, retain the existing focused-deck duplication fallback. Preserve the distinction between unknown availability and definitely empty decks, including FINAL's existing positive-content requirement. Pager clones should retain independent mutable history caches and omit transient input as today.

**Verification should prove sessions survive, not only that layouts have the right names.** Enumerate each permitted topology, mirrored variant, focused leaf, split key, close target, and ratio. Assert unique leaves, valid focus, exact creation/removal counts, reversible transposition, inverse focus directions, inverse swap directions, and deterministic tree normalization. Geometry checks should cover every leaf at the actual available dimensions, including integer rounding, gutters, and changing chrome.

Pilot coverage should assert that every survivor remains mounted under its expected container, visibly renders its content, retains its logical reading line after wrapping changes, and still scrolls/searches/follows links. Test deletion of each of three panes, collapse with the spanning pane focused, rapid repeated keys during async mounting, click focus after a swap, destination removal during a delayed resolver, source/destination history independence, and live updates reaching the correct identity after movement. Exercise standalone pager and ACE modal pager so all new bindings remain modal-scoped.

Add schema-1 migration and schema-2 round-trip/recovery coverage, deck picker destination tests, unshown-deck selection, and zoom restore with edited cards/decks. The decoder currently truncates to two panels, so an end-to-end restart test is particularly valuable.

Visual coverage should include both three-pane families and mirrors, each focused slot, 30/50/70 outer and inner ratios where they fit, long titles, empty panels, a history-rich pager, streaming content, expanded/collapsed node lists, and refusal at narrow widths. Check representative 80×24, 120×40, and 160×50 windows; acceptance must use measured pane-area geometry. Use reviewed targeted goldens and live captures, with the project's canonical renderer. Source snapshots should not be accepted merely because their generator exited successfully.

Preserve the established selective-update and pump-free task paths: no synchronous I/O in key/render handlers, no slow awaits on the serial pump, and no refreshing all documents merely to move focus. Benchmark focus/transpose/swap with realistic content after the implementation; no performance claim is established by this report. Run the project's normal guarded `just check` route and the required targeted visual workflow; reserve `check-full` for explicit instruction.

**Explicit adjustments to the requirements.**

1. Treat H3/V3 as mirrored layout families determined by the focused pane, rather than two fixed pictures.
2. Define “larger pane” as the structural spanning pane, irrespective of area.
3. Keep the focused session when reducing either surface from two panes to one; this changes current deck survivor semantics.
4. Define wraparound structural focus order, full-session swapping with focus following the moved session, and sibling promotion on deletion.
5. Define “other pane” as the visibly indicated next pane, including deck picker and pager `Ctrl+W` targeting.
6. Add portable prefix/menu access alongside the requested shifted shortcuts; those chords alone are insufficient on the inspected input stack.
7. Give each split its own ratio, fit-check the actual pane area recursively, and refuse creation without silently collapsing the node list.
8. Specify zoom behavior so hidden panes cannot be inadvertently deleted, and preserve pane sessions during terminal shrink.
9. Make the confirmed pager survivor-detachment repair a prerequisite, rather than copying its teardown into the new layouts.

The first two clarify the request; the remaining items fill missing behavior or change existing behavior explicitly. None adds arbitrary pane counts, synchronous scrolling, drag resizing, or pager-session persistence. An “only this pane” command could be useful later, but the requested two-pane collapse and existing deck zoom are sufficient for this initial scope.

**Recommended solution.** Implement exactly the requested one/two/three-pane split-key cycle using a shared, depth-two Python presentation tree and stable pane sessions, rendered by a small identity-based layout adapter. Preserve focused-session continuity across both surfaces, choose the next pane explicitly for cross-pane actions, close by sibling promotion, and keep two independent ratios. Retain the requested Control shortcuts with portable alternatives and verify CSI-u delivery through the real terminal/tmux path. Repair `sase-1er` first, migrate deck persistence, and finish with focused-pane accents, compact ordinal titles, aligned frames, and reviewed narrow/wide visuals. This is a worthwhile feature when reliability and spatial predictability are treated as the design's foundation.
