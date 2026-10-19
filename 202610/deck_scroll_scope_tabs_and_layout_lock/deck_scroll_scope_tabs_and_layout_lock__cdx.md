**Agent deck navigation: make scroll scope explicit, reserve tabs for hidden cards**

Independent research by cdx, 19 October 2026. Scope: critique and implementation guidance; no application changes. I independently inspected the SASE checkout at commit a9046529cac4783593fb9161b10ba25334517af4, its existing visual fixtures, and primary UX and platform sources. I did not consult any other report, transcript, or findings from this swarm. This is a code and design review, not a usability study or a live-session reproduction.

The proposal is a good direction. Showing card tabs only when switching cards reveals otherwise hidden content would remove a misleading signal. I would combine that change with one prominent badge explaining **what scrolling reaches**, a separate indication of **whether content is currently above or below**, and a quieter indication of **who controls layout selection**. I would not replace automatic/manual state with an unexplained lock alone.

The crucial adjustment is to frame the problem as reachability rather than a binary “scrollable or not.” A paged card can still scroll. A continuous deck can fit entirely on screen. A selected card can itself hide other blocks behind another navigation control. A deck may initially open near the newest reply, with content above. Those cases require different answers.

The present implementation explains the confusion.

| Observed behavior | Evidence in the SASE checkout | Consequence |
| --- | --- | --- |
| Card labels are assembled for Main, Files, Tools, FINAL, and RECORD and passed to the title renderer without a spread-versus-paged visibility condition. | src/sase/ace/tui/widgets/decks/panel_chrome.py, refresh_chrome(), line 464; titles.py, deck_title(), line 196 | The same tab-like visual grammar currently describes mutually exclusive cards and sections of one document. |
| Only Main and Files receive view badges. The badge combines a layout name with auto/fixed and can collapse to S/C/B plus A/F. | panel_chrome.py, _chrome_view(), line 403; view_badge.py, badge_variants(), line 89 | The most constrained split panels receive the least self-explanatory cue. Other decks do not share the same cue. |
| Fixed policies can keep their requested label when their effective content signatures are equivalent. A page-blocks preference can therefore be shown while the current card has no block paging. | view_policy.py, resolve_view(), line 152; tests/ace/tui/widgets/decks/test_deck_view_policy.py, test_resolve_fixed_vacuous_shows_requested_name() | The existing displayed view label is not a safe source for a new scroll-reachability indicator. |
| Ctrl+J/K switches cards in paged mode and jumps between card anchors in spread mode. | panel_navigation.py, cycle_card(), line 33 | Hiding spread tabs must not remove this useful shortcut. “The shortcut exists” is not the condition for showing tabs. |
| Card blocks have their own navigation and rendering mode. The existing block rail distinguishes “all N” from “page N/M.” | document_rail.py, document_block_rail_card(), line 113, and document_block_rail_cue(), line 165 | Card tabs alone cannot explain everything that scrolling will miss. Preserve and clarify block navigation. |
| Auto layout depends on measured content and viewport size; the defaults are 1.5 screens at each level, with 10% hysteresis in the deck decision. | src/sase/default_config.yml, lines 477–485; render_mode.py, decide_render_mode(), line 28 | Resize and live growth can change navigation structure. The indicator must follow the applied layout. |
| P cycles fixed layouts; returning to automatic is a command-palette action. Policies are stored per panel and per eligible deck. | widgets/_agent_detail_deck_view.py; decks/model.py, DeckViewPolicies; actions/agents/_panel_detail.py, action_cycle_deck_view(); commands/catalog.py | A lock would describe a stored preference, not a frozen viewport, content stream, or selected agent. Its explanation needs an undo path. |
| Files spread can display capped previews with an editor escape. | files_spread.py, show_pages(), line 40 | A whole-deck scroll cue cannot promise that every byte of every file is available by scrolling. |

Paths without a full prefix in this table are under src/sase/ace/tui/widgets/decks unless another path is specified. These are source observations, not newly executed test results.

I visually inspected three existing PNG fixtures under tests/ace/tui/visual/snapshots/png: agents_deck_view_fixed_spread_120x40.png, agents_deck_view_auto_page_blocks_120x40.png, and agents_deck_view_split_narrow_120x40.png. Spread and page-blocks both show Context and Reply in the border. The narrow split shows codes such as C·F and B·A, with a card count but little explanation. Scrollbar thumbs are present, so the issue is not simply absence of a scrollbar. The information needed to interpret its scope is weak. These fixtures demonstrate current presentation; they do not establish how frequently users make mistakes.

External evidence supports the direction, with limits.

The W3C tabs pattern defines tabs as alternatives that display one associated content panel at a time. Applying that convention to SASE supports removing tab styling when all sibling cards are in one continuous document. This is a semantic analogy, not a requirement to implement browser ARIA roles or adopt browser arrow-key conventions in a terminal. [W3C Tabs Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/)

Nielsen Norman Group's icon guidance explains that recognizing an object does not guarantee understanding its application-specific meaning, and recommends visible labels rather than relying on hover. A recognizable padlock therefore does not establish that users will interpret it as “manual deck-layout policy.” In this interface it could plausibly mean read-only content, stopped updates, a pinned agent, or disabled scrolling. That list is my design inference, not a reported SASE user finding. [NN/g, Icon Usability](https://www.nngroup.com/articles/icon-usability/)

NN/g's scrolling research emphasizes visible indications of content beyond the viewport and warns about designs that look complete prematurely. It supports an explicit overflow cue in addition to navigation structure. Its evidence concerns websites; it does not establish the best badge wording, color, or default paging threshold for a terminal application. [NN/g, Scrolling and Attention](https://www.nngroup.com/articles/scrolling-and-attention/)

Use text and shape alongside color. As design targets, use at least 4.5:1 contrast for small badge text and 3:1 for meaningful non-text indicators against adjacent colors. These are useful WCAG-derived targets, not a claim that this TUI meets WCAG or exposes equivalent assistive-technology semantics. Unfocused readable content is not the same thing as a disabled control. [W3C Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html), [Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)

Textual already supports overflow-sensitive scrollbars; SASE's deck-scroll style already reserves a stable scrollbar gutter. Build on that mechanism. A scrollbar describes movement within its current scroll container, which is why it cannot by itself reveal hidden sibling cards. [Textual overflow documentation](https://textual.textualize.io/styles/overflow/)

Unicode's width specification explicitly cautions that its width property is not a complete solution for modern terminals. A lock glyph needs testing with the supported fonts and terminal environments, plus a text fallback; one character in a string is not a safe assumption about occupied terminal cells. [Unicode UAX #11](https://www.unicode.org/reports/tr11/)

I would adjust the requirements as follows.

| Proposed requirement | Adjustment | Reason |
| --- | --- | --- |
| Show card sub-tabs only when cards are split into sub-tabs. | Show a tab strip only when at least two sibling cards exist and switching reveals a card outside the current scroll document. Apply this across deck types. | This expresses the actual navigation contract. A single card needs a title, not a one-item tab strip. |
| Show tabs when Ctrl+J/K is needed. | Use rendered reachability, not shortcut availability. Keep Ctrl+J/K in continuous mode as section jumps. | The shortcut already works in both modes. |
| Add bright badges indicating the view. | Make one text badge prominent: Scroll: deck, Scroll: card, or Scroll: block. Keep policy and exceptional status visually secondary. | The user wants to know what to do and what scrolling reaches, not decode an implementation mode. |
| Replace auto/fixed with a small lock. | Prefer Adaptive and 🔒 Manual in ordinary widths; Manual is the text fallback. Do not ship icon-only as the default. | This removes the old wording while preserving a readable distinction. A lock can reinforce a label after testing. |
| Make scrolling down to the entirety obvious. | Indicate content above as well as below; retain separate folded/truncated/loading notices. | Current landing behavior and capped file previews make a literal “everything below” promise false. |
| Fix the focused panel. | Keep truthful scope in every visible panel, with strongest emphasis on the focused one. | Users should be able to understand another panel before moving focus to it. |
| Preserve current labels for saved preferences. | Preserve the preference in state, but derive the primary badge from the rendered content. | Preference stability must not conceal the actual interaction. |

The proposed interaction is a small set of independent signals.

First, put a stable scope badge next to the deck name. In normal widths use **Scroll: deck**, **Scroll: card**, or **Scroll: block**. This labels the scope of scrolling, not an instruction that downward scrolling is currently possible. “Deck” means all cards and their currently expanded rendered content share this scroll document. “Card” means other cards require switching. “Block” means other blocks require switching, even if the selected block's body is itself many screens long.

| Actual displayed structure | Card tab strip | Primary scope badge | Other cue |
| --- | --- | --- | --- |
| Empty deck or an unresolved first load | None | Empty or Loading, as appropriate | Do not assert complete reachability. |
| One card, all its blocks inline | None | Scroll: deck | Keep the card's title in the document. |
| Multiple cards in one continuous document | None | Scroll: deck | Optional plain breadcrumb such as Reply · 2 of 2; section-jump shortcut remains available. |
| One card shown from multiple cards; all its blocks inline | Visible | Scroll: card | Card count and Ctrl+J/K switching hint. |
| Active content shows only one block from several | Visible only if sibling cards also exist | Scroll: block | Block page count and existing (/ ) navigation hints. |
| All content fits in its current scroll scope | Governed by the rows above | Scope stays unchanged | No downward arrow; show a fit/end cue only with explicit scope. |
| Search overlay is displayed | Do not imply that the hidden deck is the active scroll surface | Search results, or an equally explicit overlay cue | Overflow refers to results until the overlay closes. |

A paged card with no actual hidden blocks must say Scroll: card even if the saved preference is page blocks. A single-card case must not manufacture card tabs from a stale stored policy. Conversely, absence of card tabs must never suppress a genuine block-page indicator.

Second, show overflow independently. Keep the existing scrollbar and add a compact textual edge cue in the panel chrome, preferably using the existing border/subtitle space without taking another content row. Show “↓ more” only while content is below, “↑ above” while content is above, and “↑↓ more” when both directions are available. At the bottom, use “End of card” or “End of block” if sibling content remains elsewhere. “End of deck” is appropriate only for a fully settled whole-deck document. A capped file preview should retain a stronger “Preview capped · E opens file” notice rather than imply complete source content.

These states should be derived from the active scroller after layout: whether its maximum vertical offset exceeds zero and whether the current offset is above zero or below the maximum, with the framework's rounding accounted for. Recompute on viewport/content changes as well as scroll events: a new streamed line can create overflow without moving the reader. Exact line percentages are unnecessary for this change and may fluctuate as content wraps or streams.

Third, retain card identity without recreating tabs. Continuous mode needs titled card separators; an optional unboxed breadcrumb can identify the current section while its heading is offscreen. It should look like location text, such as “Reply · 2 of 2,” rather than a selected tab or mutually exclusive choice. This addresses the strongest objection to hiding tabs: losing a compact map of the document. Do not remove a FINAL status summary merely because the title strip currently carries it; preserve consequential status separately from navigation.

Conceptual sketches, with key names representing the defaults:

    MAIN  [Scroll: deck]  Adaptive       Reply · 2 of 2
      ...continuous document with titled Context and Reply sections...
      ↑ above
      Ctrl+J/K jump to card

    MAIN  [Scroll: card]  🔒 Manual
      Context | [Reply]                 Card 2 of 2
      ...Reply, including all of its inline blocks...
      ↓ more                            Ctrl+J/K switch card

    MAIN  [Scroll: block]  Adaptive
      Context | [Reply]                 Card 2 of 2
      Block 3 of 4                      ( previous / ) next
      ...current block...
      End of block

These sketches separate information to illustrate its hierarchy; they do not prescribe adding a separate physical row for every line. Reuse existing border and block-rail space. The scoped overflow cue and current card count have higher priority than a long filename or a decorative glyph.

Use a high-contrast filled or reverse-text treatment for the focused scope badge. Keep it in a fixed location and use readable words. Use one semantic treatment across all three scopes; color differences are optional reinforcement. Keep ordinary state away from warning/error colors, and avoid blinking or animation. Unfocused panels can use a quieter outline or regular text while remaining legible. There is little benefit in three equally bright badges competing with the agent's status, selection, and ZOOM indicator.

For narrow panels, compress deliberately: remove explanatory prose and policy text before the scope word, shorten card names before card counts, and use DECK/CARD/BLOCK rather than S/C/B. Full help remains available through the keyboard. Preserve ZOOM and enough navigation identity to act; if the minimum supported width cannot fit that, specify a minimum or a deliberate compact layout rather than silently dropping the only scope cue. The existing 120-column split fixture is a necessary acceptance case, not an exotic edge case.

For policy, the lock should mean exactly “manual layout preference retained for this panel and deck.” It must not imply paused output, a frozen agent selection, disabled scrolling, or an absolute guarantee that media can be spread. Adaptive means SASE chooses a layout from content and available space. A manual spread preference may still be pending or blocked; the primary badge continues to describe the rendered view and a separate status explains the mismatch.

My preferred first release uses Adaptive / 🔒 Manual, with Manual as the no-glyph fallback. In the palette, describe the available policies in full, for example “Adaptive — choose from content and size,” “Continuous deck — manual,” “Cards separately — manual,” and “Blocks separately — manual.” Existing command aliases can remain searchable. A short teaching message should explain that P selects a manual layout and identify the palette action that restores Adaptive. Do not imply that pressing P eventually cycles back to automatic; the current implementation does not.

If icon-only policy chrome is a strong personal preference, make it a tested compact variant after the scope design is working. Keep a keyboard-accessible textual explanation and discoverable reset command. I would not add a new lock/unlock key as part of the initial visual fix. A future toggle would need a separate decision about whether it pins the current effective layout or restores the last manual preference.

The implementation should be modest but explicit.

1. **Create one presentation snapshot of actual navigation.** Feed it actual card visibility, active block paging, selected card/block, overflow state, stored policy where supported, and loading/blocked/capped state. Derive both tab visibility and scope wording from this snapshot. Do not infer truth from ResolvedView.shown or from whether P is enabled. Avoid separate calculations that can let a badge disagree with the body.

2. **Separate card metadata from tab presentation.** Keep all CardTab/card metadata for navigation and counts. Change titles.py and panel_chrome.py so a spread document gets identity, scope, and optional location text without selected-tab styling or an orphan separator. Special-case visibility rather than erasing the card list passed to action logic.

3. **Audit every deck host.** Main and Files support manual policy today; that does not mean only they deserve a reachability cue. FINAL and RECORD use document hosts. Tools switches Runs versus LLM Calls through separate hosts, and its Runs document is explicitly paged. Resolve those hosts' actual visible units instead of assuming that a missing generic mode means continuous. Do not add manual-layout controls to currently unsupported decks just to make badges uniform.

4. **Preserve transitions and performance.** Reuse existing anchor-preserving transitions and 10% hysteresis. Do not reset a reader's card, block, scroll offset, or following state when chrome changes. Show a new scope only when the matching content is applied. Keep partial paints for the same subject stable; never present an old subject's whole-deck cue as proof that a new loading subject is complete. Use cached state and existing watchers, with no filesystem reads or full rendering measurements on each scroll event.

5. **Keep geometry stable.** The current tabs are border-title text, so removing them need not change viewport height. Retain that advantage. An extra conditional status row would change the auto-layout threshold and could create the very transitions the badge is trying to explain. Keep the existing stable scrollbar gutter; do not add competing nested scroll containers.

6. **Update the explanatory surfaces together.** Change the conditional footer descriptions from generic “cards” to “jump to card” or “switch card” as appropriate. Source displayed keys from the live keymap registry, including remapped or unbound keys. Update help and palette text. Any new configuration or binding defaults belong in src/sase/default_config.yml; the initial design needs neither.

This is primarily Textual presentation and can stay in this repository under the project's backend boundary. If implementation expands into shared domain rules, artifact semantics, or cross-frontend persistence behavior, that expansion belongs in sase-core. Do not use a display fix as a reason to duplicate backend behavior in Python.

I would validate the proposed semantics before polishing glyphs.

Use the existing policy, title, chrome, document-scroll, and split-panel test families for focused assertions. Verify that continuous mode hides the strip while Ctrl+J/K still reaches card anchors; paged mode retains all card navigation; and a page-blocks preference on a blockless card does not mislabel scroll scope. Include empty and one-card decks, one-block cards, media-blocked/pending Files spread, file truncation, Tools with one versus two outer cards, and FINAL/RECORD layouts. Test top, middle, bottom, no-overflow, resize, streaming growth, and search overlays.

Visual checks should include single, two-, and three-panel arrangements; both focused and unfocused chrome; ZOOM; long card/file names; light/dark and low-color presentations; and fallback glyph rendering. Keep actual key bindings in test fixtures explicit. A screenshot alone cannot prove anchor preservation or that Ctrl+J/K still works, so combine visual checks with interaction assertions.

For a small formative evaluation, show current and proposed states in counterbalanced order to the owner and a few users unfamiliar with the new labels. Before letting them navigate, ask what scrolling will reach, how to reach another card or older block, whether output continues when the lock appears, and how to restore adaptation. Then let them perform the tasks. Record wrong navigation attempts, task completion, and interpretations of the lock. A “noticeable” badge that still suggests frozen content has failed. This evaluation is proposed, not performed; the exact wording and salience remain medium-confidence choices.

I would not change the automatic paging thresholds, force all decks into one endless document, or automatically advance to another card at its scroll boundary in the first implementation. Those approaches change navigation and reading behavior substantially. Continuous-only rendering also needs a separate feasibility decision for media and large or specialized deck content. A hidden-tab-only patch is a useful first increment, but it leaves paged scrolling and block paging insufficiently explained. A brighter existing badge alone preserves the misleading tab structure and requested-versus-effective ambiguity.

The evidence strongly supports separating actual scroll scope, current overflow, and saved layout policy. Confidence is high in the observed implementation issues and the tab-semantics correction; confidence is moderate in the exact proposed copy and lock treatment, pending direct testing. This report makes no claim of measured usability improvement.

My recommended solution is to **hide card tabs whenever all sibling cards share one scroll document; retain section-jump shortcuts and plain location text; show a prominent, truthful Scroll: deck/card/block badge; and pair it with a directional overflow cue derived from the current viewport**. Keep policy secondary as Adaptive / 🔒 Manual, with a readable fallback and clear reset command. Preserve the current rendering choices and reading anchors while making their consequences visible. This retains the strongest part of the original plan and corrects the two largest risks: equating paging with “cannot scroll,” and asking a small lock to explain a complex state by itself.
