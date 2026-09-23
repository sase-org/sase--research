# Agent data decks/cards: unifying the Agents-tab metadata, files, and LLM-calls panels

Research report (mus). Independent assessment of the proposal to replace the
agent metadata panel and the files/LLM-calls panels with a single "deck panel"
type hosting "agent data cards", with dynamic all-on-one-page vs. one-card-per-page
rendering, Main/Files/Tools decks, two split layouts, and six keymap additions.

## Summary

The proposal is sound in its core unification and I would accept it with
adjustments. The current detail area is three panel types with three different
interaction models: a single scrolling metadata document
([agent_detail.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/agent_detail.py:68)),
a paged file viewer with `ctrl+n/p` cycling
([_file_list.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/file_panel/_file_list.py:104)),
and a tool-call timeline with its own detail levels
([llm_calls_panel.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/llm_calls_panel.py:80)).
On top of that sit two escape hatches that exist largely because the base layout
is inflexible: the `p` view picker
([_agent_view_picker.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/actions/agents/_agent_view_picker.py:106))
and the `Z` zoom modal
([_panel_detail.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/actions/agents/_panel_detail.py:167)).
Replacing all of that with one panel type (deck panel), one content unit (card),
one paging mechanism, and a split/focus model directly removes two modals and one
layout enum. That is a real simplification, not just a rename.

The risky part is not the deck/card abstraction. It is (1) threshold-driven
dynamic pagination, (2) the keymap churn (`ctrl+n/p`, `ctrl+f`, `ctrl+s` are all
taken), and (3) splitting today's single metadata document across two cards
without breaking section navigation, inline search, and the special agent-type
displays. Each is solvable; each needs an explicit decision, listed below. The
recommended solution at the end phases the work so the unification lands first
and the dynamic pagination lands second.

This is presentation-only Textual state (layout, focus, paging), so under the
Rust core boundary it stays in this repo; no `sase-core` change and no
`sase-core-revision.txt` bump is needed.

## What exists today

### Detail-area composition

`AgentDetail.compose` mounts, top to bottom: a sticky header panel, the metadata
scroll (`#agent-prompt-scroll` hosting `AgentPromptPanel`), a hidden search
panel, the file scroll (`#agent-file-scroll` hosting `AgentFilePanel`), the
LLM-calls scroll (`#agent-llm-calls-scroll` hosting `AgentLLMCallsPanel`), and a
jump panel. Only a subset is visible at a time
([agent_detail.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/agent_detail.py:68)).

Two enums govern what is shown:

- `DetailPanelMode` (`AUTO` / `LLM_CALLS` / `INFO`) selects file vs. LLM-calls
  as the secondary content
  ([_agent_detail_panels.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/_agent_detail_panels.py:24)).
- `DetailLayoutMode` (`METADATA_ONLY` / `METADATA_LARGER` / `EQUAL` /
  `SECONDARY_LARGER` / `SECONDARY_ONLY`) sets the vertical proportion, cycled by
  `next_detail_layout_mode`
  ([_agent_detail_panels.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/_agent_detail_panels.py:32)).

The Agents tab itself is a horizontal split: node/tribe panels on the left
(`#agent-list-container`) and the detail area on the right
(`#agent-detail-container`), inside `#agents-content`
([_app_layout.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/_app_layout.py:100)).
The list column width is dynamic, clamped to 60–130 cells. This matters for the
vertical-deck proposal: there is little horizontal room to spare, which is why
the proposal's collapsible node panel is load-bearing, not decorative.

### Metadata panel contents (full inventory)

The proposal's Context/Reply split names four sections plus "anything I am
forgetting". The forgotten part is large. In render order, the metadata document
is:

1. Identity/kind header (`FAMILY`, `PROC SHELL`, `AGENT SHELL`) plus agent
   metadata fields (name, workspace, model, timestamps, status), including the
   detachable identity header variant
   ([_agent_display_header.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/prompt_panel/_agent_display_header.py:85)).
2. Runner queue section, family member roster, legacy parallel-members section,
   output variables, workflow variables.
3. Lane neighbors (for sase-agent owners).
4. `SASE CONTEXT` lanes: memory reads, glossary reads, skill uses, opened
   workspaces, bead section, plan section, deltas, linked deltas, artifact
   files/reads, bead touches
   ([_agent_context.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/prompt_panel/_agent_context.py:1)).
5. `SLOW TOOLS` section (deliberately not a SASE CONTEXT lane; kept behind the
   debounced path because it can cost ~114 ms cold)
   ([_agent_display_header.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/prompt_panel/_agent_display_header.py:330)).
6. `ERROR` + output path + error traceback.
7. `AGENT XPROMPT` (when present), then `AGENT PROMPT`
   ([_agent_display_render.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/prompt_panel/_agent_display_render.py:418)).
8. The reply, whose heading varies by state: `AGENT REPLY` for follow-up
   consolidation and running agents, `AGENT CHAT` for DONE/FAILED agents,
   plus phase dividers, per-follow-up phases, timestamped reply chunks, merged
   attempt history, and the "Waiting for agent response…" placeholder
   ([_agent_display_render.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/prompt_panel/_agent_display_render.py:440)).
9. Orthogonal to all of the above: attempt-pinned views, workflow-agent views,
   family/proc-shell/monitor/gate/bash-python/parallel special displays,
   page/wait/shell sections, and clan-container documents — all of which branch
   before or around the XPROMPT/PROMPT/REPLY path.

Any card split must take a position on every one of these, not just the four
named sections. Concrete mapping is in the recommendation.

### Files panel paging (the model to copy)

`AgentFilePanel` keeps `_file_list` + `_current_file_index` with wraparound
`next_file` / `prev_file`, preserving the user's selected index when the list
is unchanged
([_file_list.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/file_panel/_file_list.py:58)).
App actions `action_next_agent_file` / `action_prev_agent_file` delegate to
`cycle_next_file` / `cycle_prev_file` on Agents tab
([_panel_detail.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/actions/agents/_panel_detail.py:141)).
The zoom modal reuses the same idea with its own `ctrl+n` / `ctrl+p` bindings
for next/prev file
([zoom_panel_modal.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/modals/zoom_panel_modal.py:111)).
Per-file scroll anchors are keyed per page slot so a revisited file restores
its scroll position
([_panel.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/widgets/file_panel/_panel.py:71)).
A card pager should reuse all three behaviors (wraparound, selection
preservation, per-card scroll anchors) rather than reinventing them.

### Keymap state (every proposed binding collides or needs care)

Current bindings in `src/sase/default_config.yml`:

- `ctrl+n` / `ctrl+p`: `next_agent_file` / `prev_agent_file` (file cycling).
  The proposal reassigns `ctrl+n/p` to deck cycling and moves card cycling to
  `ctrl+shift+n/p`. Feasible — `ctrl+shift+o` already exists as precedent — but
  it changes the most-used detail key. Terminal support for ctrl+shift
  sequences is good in modern emulators but not universal; needs a fallback.
- `ctrl+f`: `scroll_prompt_down` (with `ctrl+b` as its pair). The proposal
  takes `ctrl+f` for deck-focus toggle. One of the two must move.
- `ctrl+s`: `submit_branch` (gate input). Proposal takes `ctrl+s` for node
  panel collapse. Must confirm scope-disjointness (gate-input focus vs. Agents
  tab focus) or pick another key; `submit_branch` firing while collapsing the
  node panel would be bad.
- `p`: `choose_agent_view` (the picker the proposal removes). Clean removal
  candidate — but the picker also owns layout cycling, so its removal must
  coincide with deck splits landing.
- `ctrl+j` / `ctrl+k`: metadata-section cycling. Survives naturally as
  within-card section navigation.
- `J` / `K`: tribe side-panel focus. Unrelated to deck focus; keep.
- `Z`: zoom panel. Candidate for removal per proposal.
- `\` and `|`: unbound today. Textual key names to verify: `backslash` and
  `vertical_bar`.
- `AppKeymaps` is strict: every field must have a `default_config.yml` entry,
  which is the single source of truth
  ([app_keymaps.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/keymaps/app_keymaps.py:7)).
  Every new keymap needs the dataclass field + config entry + registry help
  text + footer update together.

### Consumers that assume today's structure

- Inline metadata search renders the prompt panel's content to text and
  operates on the single document
  ([_metadata_search.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_34/src/sase/ace/tui/actions/agents/_metadata_search.py:205)).
  Split cards need a defined search scope (focused card vs. all cards in deck).
- Section navigation (`next_agent_metadata_section`, section layout cache in
  `_section_navigation.py`) assumes one section document. Card paging needs a
  two-level target: card index + section within card.
- The footer (`_display_detail_footer.py`) and help modal
  (`agents_bindings.py`) enumerate today's bindings; both need deck-aware
  updates or the feature is undiscoverable.
- `V` (view metadata in pager), `E` (edit visible panel), `D` (attempt view)
  act on "the visible panel" — with two deck panels and paged cards, "visible"
  needs a definition (I recommend: focused deck panel's current card).

## Critique

### What is good

1. **One panel type is the right call.** `DetailPanelMode` + `DetailLayoutMode`
   + picker + zoom is four mechanisms for "show me the right slice of this
   agent". Decks (which deck), cards (which slice), splits (how many at once),
   focus (which one I am acting on) cover the same space with fewer concepts.
2. **Paging per card generalizes the best existing interaction.** File cycling
   with index preservation and scroll anchors is the most polished navigation
   in the detail area. Extending it to all cards is coherent.
3. **Removing the `p` picker and the zoom modal is correct in steady state.**
   Both compensate for a rigid base layout. If any two decks can sit side by
   side, zoom becomes a maximized single deck and the picker becomes deck
   cycling. But removal timing matters (below).
4. **Collapsible node panel is necessary, not optional.** With a 60-cell
   minimum list width, vertical deck splits without collapse will squeeze both
   decks into uselessness on standard 200-cell terminals.

### Concerns and adjustments

1. **Threshold-driven pagination is the highest-risk requirement.**
   Measuring "would this exceed N lines" on every selection change, resize,
   and streaming update invites layout thrash (page count flickering as
   content streams in) and measurement cost (rendering documents just to
   measure them). Adjustments:
   - Measure in rendered lines using the existing section-layout cache and
     file-panel line counts, never by rendering twice.
   - Add hysteresis: switch single-page → paged at threshold T, but switch
     back only below ~0.8T, and never auto-switch while the user is on a
     non-default card (only on agent change or explicit action).
   - Add a per-deck manual override (force single-page / force paged) so the
     threshold is a default, not a fight.
   - Freeze pagination during streaming updates; recompute on settle
     (selection change, refresh settle, resize end).
2. **`ctrl+n/p` reassignment breaks the most-practiced muscle memory.**
   Today those keys cycle files. Under the proposal, with a Files deck
   focused, `ctrl+n/p` cycles decks instead and file cycling moves to
   `ctrl+shift+n/p`. That is a defensible steady state (uniform keys), but
   expect complaints. Adjustment: keep the proposal, but when the focused
   deck shows a single card (nothing to page within the card), consider
   whether `ctrl+shift+n/p` should fall through to deck cycling — no, keep
   them strict; instead document the change in the help modal and footer from
   day one. Do not ship the remap before the Files deck supports one-card-
   per-file paging, or file cycling will feel broken in the interim.
3. **`ctrl+f` conflict must be resolved explicitly.** `ctrl+f` /
   `ctrl+b` are a scroll pair for the metadata panel. If `ctrl+f` becomes
   deck-focus toggle, `ctrl+b` is orphaned and scrollers lose their key.
   Options: (a) move prompt scrolling to `ctrl+d`/`ctrl+u`-style keys —
   but those scroll the detail; (b) use a different focus-toggle key and
   leave the scroll pair alone. I recommend (b): keep `ctrl+f`/`ctrl+b`
   scrolling, and put deck-focus toggle on `Tab`/`shift+Tab`-adjacent or a
   dedicated key — except `Tab` is tab-switching. Least-bad available
   candidate is `ctrl+o`-family or `=`/`-`-style, but this needs a keymap
   audit pass against the full Agents binding table before committing. At
   minimum, do not take `ctrl+f` without rebinding `scroll_prompt_down/up`
   in the same change.
4. **`ctrl+s` needs a scope check.** `submit_branch` on `ctrl+s` is a
   gate-input binding. If it is app-scoped rather than modal-scoped, toggling
   node collapse with the same key will misfire. Verify binding scope in
   `bindings.py`/registry; if there is any doubt, use a different key for
   node collapse (e.g. `ctrl+b` is taken… candidates like `ctrl+\` or a
   leader sequence deserve the audit). The terminal-flow-control caveat
   (`ctrl+s` = XOFF) also applies in some environments, though Textual apps
   generally handle this.
5. **Splitting the metadata document breaks search and section nav unless
   designed.** The Context/Reply split separates content that today is one
   searchable, section-navigable document. Decide: metadata search covers the
   whole Main deck (both cards) while section cycling (`ctrl+j/k`) stays
   within the current card. That preserves findability while keeping
   navigation local. Attempt-pinned, workflow, family, gate, monitor,
   proc-shell, and clan views should render as their own card content (or
   force single-card mode) rather than being shoehorned into Context/Reply.
6. **`SLOW TOOLS` lives in two places under the proposal — say so
   explicitly.** The Context card keeps a `SLOW TOOLS` digest (it is part of
   the header document) while the Tools deck hosts the full timeline. That
   duplication is fine (digest vs. detail) but should be a stated design
   decision, not an accident. The full LLM-calls panel already supports
   detail levels and throttled fetching; the Tools deck's single card is that
   panel unchanged.
7. **Do not delete the zoom modal and picker in the same change that
   introduces decks.** Sequence: (i) decks land with picker + zoom intact
   (zoom becomes "open current card fullscreen"); (ii) migrate footer/help;
   (iii) remove picker `p` and zoom `Z` once deck splits + collapse cover
   their uses. Deleting both on day one removes the only workaround if deck
   sizing has bugs.
8. **Split semantics should stay exactly as proposed (max two deck panels,
   one orientation at a time).** The toggle-back behavior (`|` with a
   vertical split → single deck) is easy to learn and bounds the layout
   state machine to: single / horizontal / vertical × which decks × focus.
   Arbitrary grids would explode focus, footer, and persistence logic. Keep
   the two-panel limit; note it as a deliberate v1 constraint.
9. **Collapsed node panel representation.** Best option: a narrow (2–4 cell)
   rail showing panel initials/counts with full keyboard access preserved
   (J/K still move; Enter re-expands on selection), rather than `display:
   none`, so focus state and unread badges survive. A fully hidden panel
   forces focus bookkeeping for a panel with no widget; a rail keeps the
   existing `_panel_group` machinery valid. Persist collapse per tab session,
   not globally.
10. **Threshold config field.** Place under `ace:` as a display setting (not
    a keymap): e.g. `agents_deck_page_threshold_lines` (int, lines). It needs
    the config-layer treatment (default, schema entry, docs) but not an
    `AppKeymaps` field. Count threshold in rendered lines, not bytes or
    cards: cards vary from a 5-line reply to a 500-line prompt, so only lines
    predict overflow. Default in the low hundreds (tune against
    `FILE_PANEL_MAX_RENDER_LINES` behavior); exact value is a tuning
    constant, not architecture.

### Glossary strands to add

Follow the existing strand format (frontmatter `keyword:`, one short
definitional paragraph; cf. `sase/memory/glossary/llm-calls.md`). Proposed:

- `agent-data-deck` — a named, ordered collection of agent data cards shown
  in one deck panel (Main, Files, Tools at v1).
- `agent-data-card` — one independently pageable unit of agent detail
  content (Context, Reply, one file, LLM-calls timeline).
- `deck-panel` — the single detail panel type; hosts one deck, renders
  single-page or one-card-per-page based on the threshold.
- `deck-layout` — single / horizontal-split / vertical-split arrangement of
  deck panels plus which deck each shows and which is focused.

## Recommended solution

### Phase 0 — scaffolding (small, reviewable)

1. Add glossary strands (`agent-data-deck`, `agent-data-card`, `deck-panel`,
   `deck-layout`) via the memory-write skill path.
2. Add `ace.agents_deck_page_threshold_lines` (int, lines) to
   `default_config.yml` + schema + docs. Default ~200–300, tunable.
3. Add keymap fields to `AppKeymaps` + config + registry + help-modal rows +
   footer, with final bindings chosen after the audit in Phase 1:
   `next/prev_deck_card` (`ctrl+shift+n/p`), `next/prev_deck`
   (`ctrl+n/p`), `deck_split_horizontal` (`\`), `deck_split_vertical` (`|`),
   `toggle_node_panel` (TBD — audit `ctrl+s`), `toggle_focused_deck_panel`
   (TBD — audit `ctrl+f`).

### Phase 1 — keymap audit (before writing widget code)

Tabulate every Agents-tab binding against the six newcomers, especially
`ctrl+n/p` (file cycling), `ctrl+f`/`ctrl+b` (prompt scroll pair),
`ctrl+s` (submit_branch scope), `Tab` (tab switching), `Z` (zoom), `p`
(picker), `J/K` (tribe panels). Lock the final six bindings and their
fallback plan for terminals that swallow ctrl+shift. This audit is the
cheapest risk reduction in the whole project.

### Phase 2 — deck model (pure logic, unit-tested)

Introduce a `DeckModel` independent of Textual: ordered decks
(Main → [Context, Reply]; Files → [one card per file]; Tools →
[LLM-calls timeline]), per-deck card measurement (lines), threshold +
hysteresis + manual override → single-page vs. paged decision, per-card
scroll anchors, card index preservation across refreshes (mirroring
`set_file_list` semantics). Unit-test the state machine without widgets:
threshold crossing both directions, streaming freeze, agent-change reset,
manual override precedence. This is where the "prefer all on one page"
policy lives and can be tested cheaply.

### Phase 3 — deck panel widget + migration

1. Build one `DeckPanel` widget replacing the three scroll containers in
   `AgentDetail.compose`; keep the header/search/jump slots.
2. Migrate content (see mapping below). Reuse `AgentFilePanel` paging,
   `AgentLLMCallsPanel` timeline, and the existing header/render builders as
   card content providers — do not rewrite renderers.
3. Implement splits (single/horizontal/vertical, max two panels), focus, and
   the `\`/`|` toggle semantics from the proposal, which are already well
   specified. Collapsible node panel as a narrow rail.
4. Redefine two-level navigation: `ctrl+shift+n/p` pages cards in the
   focused deck; `ctrl+j/k` cycles sections within the current card; search
   spans the focused deck's cards.
5. Keep `p` picker and `Z` zoom mounted but retargeted (zoom = current card
   fullscreen) during stabilization.

### Content mapping (normative)

- **Main deck, Context card (default):** identity/kind header, metadata
  fields, runner queue, workflow/output variables, family roster + neighbors,
  full `SASE CONTEXT` lanes, `SLOW TOOLS` digest, `ERROR` + traceback,
  `AGENT XPROMPT`, `AGENT PROMPT`. Special views (attempt-pinned, workflow,
  family, gate, monitor, proc-shell, clan) render here in full, forcing
  single-card display when they branch.
- **Main deck, Reply card:** `AGENT REPLY` / `AGENT CHAT` with phase
  dividers, follow-up phases, timestamped chunks, merged attempt history,
  live-reply streaming, and the waiting placeholder. The "entire Main deck
  shown if under threshold" behavior from the proposal is preserved: Context
  is the default *paged* card, but under-threshold shows both.
- **Files deck:** one card per file, reusing file-list order, index
  preservation, and scroll anchors. Under threshold: all files stacked with
  card separators; over: one per page.
- **Tools deck:** the existing LLM-calls timeline as its single card
  (detail levels unchanged); reserve the second slot for the future
  `sase tool` card with a declared extension point, not a stub UI.
- **`V`/`E`/`D`** act on the focused deck panel's current card.

### Phase 4 — removal + polish

Remove the `p` picker (freeing `p`) and the zoom modal (freeing `Z`) only
after splits + collapse + fullscreen-current-card cover their flows; update
footer, help modal, and onboarding; add screenshot/test coverage mirroring
the existing `test_agent_display_*` and file-panel suites; tune the default
threshold from real usage.

### What I would not do

- No arbitrary N-panel grids in v1; the two-panel toggle semantics are a
  feature (bounded state).
- No byte- or card-count thresholds; lines only.
- No deletion of zoom/picker before the replacement interactions are
  proven; deprecate, then delete.
- No new Rust core work: this is presentation state and stays in the TUI.

### Open questions for the implementer

1. Final keys for node-collapse and deck-focus after the audit (`ctrl+s` /
   `ctrl+f` both need clearance).
2. Exact default threshold (tune empirically; expose per-deck override).
3. Whether collapsed rail shows unread/completed badges (I lean yes, cheap
   and preserves glanceability).
4. Whether `sase tool` card reservation needs a placeholder entry in the
   Tools deck header now (I lean no — keep a code-level extension point).

## Sources consulted

All paths relative to workspace root; key files: `AgentDetail.compose`,
`DetailPanelMode`/`DetailLayoutMode`, `action_next/prev_agent_file`,
`FilePanelFileListMixin.next/prev_file`, zoom modal bindings, `choose_agent_view`
(`p`), `build_header_text` + `_agent_display_render.py` section order,
`append_agent_context_section`, `append_slow_tool_calls_section`,
`_app_layout.py` agents-content split, `_display_detail_footer.py`,
`agents_bindings.py`, `default_config.yml` app keymaps, `AppKeymaps`,
`FILE_PANEL_MAX_RENDER_LINES`, `SLOW_TOOL_CALL_THRESHOLD_MS`, and
`sase/memory/glossary/llm-calls.md` strand format. No peer swarm reports
were located, opened, or consulted.
