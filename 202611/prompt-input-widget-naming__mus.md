# What to call the "prompt input widget" (`__mus`)

**Question:** What is the best possible name for what is now called the "prompt input
widget" — a new glossary term that describes the widget itself, the way its stacks
work, and its property panel — kept concise and useful for future agents?

**Verdict up front:** Name it the **Prompt Bar**. It is the shortest name already in
use across guides and reference docs, it maps directly onto the `PromptInputBar`
container class, and it naturally covers both sub-parts (the prompt stack and the
frontmatter/property panel) as "the bar in stack mode" / "the bar's frontmatter
panel". Aliases should retain `prompt input bar`, `prompt widget`, and
`prompt input` so old text keeps resolving. Full recommended strand entry is at the
end of this report.

Evidence below comes from this checkout (`sase_13`, `master`-adjacent November 2026
tree), the committed docs, and the live glossary web. I did not open any peer
`__cdx` / `__cld` / `__grk` / `__gem` report.

## 1. What the thing actually is (three parts, one container)

The "prompt input widget" is not one `TextArea`. It is a bottom-of-screen composite
owned by one container class with two swappable editing surfaces inside it.

**Container.** `PromptInputBar` in
`src/sase/ace/tui/widgets/prompt_input_bar.py` (a `Static` composed from ~14
`PromptInputBar*Mixin` modules: lifecycle, title, status, subtitles, frontmatter,
snippet/mini-macro panes, stack actions/rendering, `g`-prefix hints, search,
dispatch, actions, completion). Its docstring is one line: "Prompt input bar for
agent workflow, positioned at bottom of screen." It owns the border label, mode
badge, cursor readout, search pill, completion panels, `$EDITOR` handoff, stash
actions, and submit chooser. Everything below mounts inside it.

**Per-pane editor.** `PromptTextArea` in
`src/sase/ace/tui/widgets/prompt_text_area.py` is the multiline Textual `TextArea`
subclass per pane: vim INSERT/NORMAL/VISUAL/V-LINE, Markdown + macro/directive
highlighting, auto-pair, completion dispatcher (`Ctrl+T`), recursive finder
(`Ctrl+R`). One mounted `PromptTextArea` per stack item; ids are
generation-scoped (`prompt-input-g<gen>-<item_id>`).

**Stack model.** `PromptStackState` / `PromptStackItem` in
`src/sase/ace/tui/widgets/prompt_stack.py` (facade) and
`src/sase/ace/tui/widgets/_prompt_stack_state.py` (model) plus
`_prompt_stack_parsing.py`, `_prompt_stack_binding.py`, `_prompt_stack_targets.py`,
and the bar-side `_prompt_input_bar_stack_*.py` rendering/lifecycle/navigation
mixins. Semantics: ordered top-to-bottom launch order; the bottom pane is the
active/newest editable item by default (not a priority marker); the stack always
holds at least one item. `from_text` lifts leading YAML frontmatter onto the stack
and splits real top-level `---` separators (outside fences/frontmatter) into one
pane per agent segment; typed `---` during live INSERT stays literal text and new
panes come from `Ctrl+G -` / `g-`. Auxiliary pane roles (`snippet`, `mini_macro`)
ride in the same item list. Whole-stack submit joins panes top-to-bottom through
the multi-agent launch path (`%wait`, `%id`, `%model` still apply per segment);
single-pane submit re-attaches the shared prompt-level frontmatter to the launched
pane.

**Property panel.** `FrontmatterPanel` in
`src/sase/ace/tui/widgets/frontmatter_panel.py` ("structured editor for a prompt's
YAML frontmatter, above the prompt stack"), with editing/raw/rendering mixins
(`_frontmatter_panel_*.py`) and bar-side hosting in
`src/sase/ace/tui/widgets/_prompt_input_bar_frontmatter.py`. It is the visible
surface over the `PromptFrontmatter` model (`src/sase/macro/prompt_frontmatter.py`,
validated through the shared core engine): one row per set field, `j`/`k`
navigation, `a` add-property picker, `d` delete, `R` raw-YAML escape hatch,
`esc`/`q`/`g=` close. The bar persists the model back onto the stack's byte-stable
`frontmatter` string; `parse_multi_prompt` stays the launch source of truth. It
auto-shows on targeted macro loads and tints its border to the bar's
clean/dirty/read-only state. In docs it is called the "frontmatter panel" or
"macro frontmatter panel" (`docs/reference/tui/prompt-stacks.md`,
`docs/reference/tui/prompt-input.md`, `docs/reference/macros/multi-agent-prompts.md`);
in styles it is `#frontmatter-panel` directly above `#prompt-stack`
(`src/sase/ace/tui/styles.tcss`). Nobody in code or docs calls it a "property
panel" today — that phrase appears only in this research question — but that is
exactly what it is functionally: a property inspector for the prompt.

**Docs vocabulary today is split four ways.** `docs/reference/tui/prompt-input.md`
titles the page "Prompt input" and heads the section "Prompt Input Widget". The
blog post `docs/blog/posts/prompt-widget-and-nvim.md` says "prompt input widget"
and "prompt widget" interchangeably and names the two code halves precisely
(`PromptTextArea` = the typing surface, `prompt_input_bar.py` = the container).
Guides say "prompt bar" (`docs/guides/run-agents-in-parallel.md`,
`docs/guides/find-and-replay-prompt.md`, `docs/guides/reuse-prompt-with-macros.md`,
plus the "Editing an Existing Macro from the TUI" section's repeated "the bar").
Reference splits stacks onto their own page (`docs/reference/tui/prompt-stacks.md`:
"This page lists prompt-stack panes, stash, and trash keys in the sase TUI prompt
widget"). So code says `PromptInputBar`, docs say "prompt input (widget)", guides
say "prompt bar" — three spellings for one object.

## 2. Neighbors the new term must not collide with

From `sase/memory/glossary/` (descriptor `sase/memory/glossary.md`) and live reads
of `prompt-stash`, `raw-prompt`, `stash-trash`, `macro`, `macro-invocation`:

- **Prompt Stash / stash** — the per-user draft pile parked *outside* the widget
  (Stash tab of the Prompts overlay). The widget *stashes to* the stash; it is not
  the stash.
- **Stash Trash** — the bounded recovery bin for discarded stash rows. Further away,
  but shares the word "stash".
- **Raw Prompt** — a launch-pipeline text stage (`raw_prompt.md`), not a widget.
- **Prompts overlay / History tab** — the `@` modal the widget opens (`Ctrl+K`,
  `Ctrl+G p`); sibling, not self.
- **Agent Data Deck / Deck Panel / Node Panel** — "deck" and "panel" are already
  taken on the Agents tab with precise meanings (a deck is an ordered card set; a
  deck panel is a detail region showing one). Any "Prompt Deck" or bare "Prompt
  Panel" name inherits that collision.
- **Macro / Macro Invocation (smack)** — the prompt *language* the widget edits.
  The widget is the surface; the macro is the content.
- **Frontmatter Panel** — the established docs/code name for the property panel
  sub-part. The new umbrella term must *contain* it, not rename it.

Glossary style (from `deck-panel.md`, `node-panel.md`, `agent-data-deck.md`):
Title-Case keyword, lowercase aliases, one-paragraph-to-three-paragraph body,
`[[glossary:...]]` cross-links, behavior-first (keys, order, focus, persistence).
Two-word keywords dominate (`Prompt Stash`, `Raw Prompt`, `Deck Panel`).

## 3. Criteria

Ranked against five tests: (a) **concise** (two words beats three); (b) **covers
all three parts** without needing "and" in the keyword; (c) **maps to code**
(an agent can `rg` the alias and land in the right file); (d) **matches existing
docs** (no migration of every guide sentence); (e) **unambiguous to future
agents** (exact-phrase search hits the widget, not stash/history/macros/decks).

## 4. Ranked candidates

| Rank | Candidate | Verdict |
| ---- | --------- | ------- |
| 1 | **Prompt Bar** | Adopt. Two words; already the guides' word ("prompt bar"); trivially maps to `PromptInputBar`; stack and frontmatter panel read as "the bar's" modes. Only cost: "bar" understates the multiline richness — paid once in the body definition. |
| 2 | **Prompt Input Bar** | Strong runner-up. Exact class-name spelling; zero code-mapping cost; current docs heading "Prompt Input Widget" shortens to it naturally. Costs one word vs. #1 and reads redundantly once "Prompt Bar" exists — keep as an alias, not the keyword. |
| 3 | **Prompt Composer** | Best *novel* name. Industry-standard (mail/chat composers) for "draft + metadata + send"; conveys multi-pane drafting plus frontmatter properties better than "bar". Fatal cost: zero grounding — appears nowhere in code, docs, styles, or keymaps, so every existing sentence and every agent `rg` misses until a migration lands. |
| 4 | **Prompt Editor** | Accurate for the `$EDITOR` handoff and macro-editing loop, but collides with `$EDITOR`/whole-bar editor sessions in docs ("open the whole stack in `$EDITOR`") and suggests a modal window rather than the bottom-anchored bar. |
| 5 | **Prompt Stack** | Correct for the multi-pane sub-part only. Promoting it to the umbrella term orphans single-pane use (still a stack of one, but nobody says that) and the frontmatter panel, which sits *above* `#prompt-stack` in both DOM and styles. Keep as a section inside the entry, not the keyword. |
| 6 | **Launch Bar** | Names the submit moment well (`Enter` chooser, `g<enter>`, whole-stack `a`), but the widget spends most of its life *composing*, not launching — stash, snippets, mini-macros, macro binding/`gw`, frontmatter editing all misread under "launch". |
| 7 | **Prompt Deck** | Reject. Direct collision with `Agent Data Deck` / `Deck Panel`; "deck" already means "ordered card set in a deck panel" on the Agents tab. Reuse would force every future agent to disambiguate by tab. |
| 8 | **Prompt Console / Prompt Workbench** | Reject both. "Console" implies log/output (the widget has no output surface; output lives in decks). "Workbench" implies the whole TUI rather than the bottom bar. Both are longer than #1 with no mapping payoff. |

Notes on names not ranked: "Prompt Pane" (singular-vs-stack confusion — a pane is
one `PromptStackItem`, not the container); "Prompt Input" (docs page title, but as
a glossary keyword "input" collides with macro `input:` rows, the frontmatter
`input` sub-tree, and generic Textual `Input` — keep as alias only); "Property
Panel" / "Inspector" as the umbrella (inverts the hierarchy — the panel is a
*part* of the bar, and "inspector" appears nowhere in the codebase); "Prompt Dock"
(untethered novelty with the same migration cost as #3 and a wrong affordance —
nothing docks/undocks).

## 5. Why #1 beats #2 and #3

- **#1 vs. #2** is purely a brevity-vs-explicitness trade. Both map to code and
  docs; #2 wins exact-string `rg` ("PromptInputBar" contains "Prompt Input Bar"
  verbatim sans camel). But glossary keywords are spoken and typed by agents far
  more than `rg`-ed, and SASE's own glossary favors two-word terms. Keeping #2 as
  the first alias captures the mapping benefit at zero cost: `sase memory read
  glossary:prompt-bar` can print "aka prompt input bar" and agents searching
  either spelling land together.
- **#1 vs. #3** is grounding-vs-evocation. "Composer" evokes the *job* (compose
  multi-agent prompts + properties + send) better than "bar" evokes the *shape*.
  But a glossary term's job is retrieval, not evocation: future agents will quote
  guides ("in the prompt bar…"), read border titles ("Prompt · N agents"), and
  `rg` class names (`PromptInputBar`). A term with zero existing hits taxes every
  one of those paths. The entry body can use the word "compose/composer" once to
  give #3's intuition without paying its migration.
- **Hierarchy point.** Whichever umbrella wins, do *not* rename `FrontmatterPanel`
  in the same move. Docs, styles (`#frontmatter-panel`), keymaps (`g=`), and the
  `FrontmatterPanel.Changed/Closed/AddRequested` messages all agree on
  "frontmatter panel". The umbrella entry should bless "the bar's frontmatter
  panel (its property panel)" as the sanctioned long form and leave the class and
  docs headings untouched.

## 6. Recommended glossary strand entry for #1

Proposed file: `sase/memory/glossary/prompt-bar.md` (via the memory-write flow,
not created by this report). Frontmatter follows the `deck-panel.md` /
`prompt-stash.md` shape; body is written so the three requested facets (widget,
stacks, property panel) each have one home sentence plus cross-links.

```markdown
---
keyword: Prompt Bar
aliases:
  - prompt input bar
  - prompt widget
  - prompt input
---

A prompt bar is the TUI's bottom-anchored agent-prompt surface: the `PromptInputBar`
container plus the per-pane `PromptTextArea` editors, completion panels, cursor
readout, search pill, stash actions, `$EDITOR` handoff, and submit chooser it hosts.
In guides it is "the prompt bar"; in reference it is the "prompt input widget".

A prompt bar edits a prompt stack: one pane per agent segment, ordered
top-to-bottom for whole-stack submission, split from real top-level `---`
separators (typed `---` stays literal text; `Ctrl+G -` / `g-` adds a pane) with
shared prompt-level frontmatter re-attached to whichever pane launches. The bottom
pane is the active draft by default. Auxiliary snippet and mini-macro panes ride
in the same stack.

Its property panel is the structured frontmatter panel mounted directly above the
stack: one row per set field over the shared `PromptFrontmatter` model (`g=` /
`Ctrl+G =` to show or focus, `a` to add a property, `R` for raw YAML, `esc` / `q`
to return to the originating pane). Drafts parked outside the bar live in
[[glossary:prompt-stash]], not in the bar; the launch-pipeline text stage is
[[glossary:raw-prompt]].
```

Alias notes: `prompt input bar` preserves the class-name mapping; `prompt widget`
and `prompt input` preserve the two live docs spellings so old sentences keep
resolving. No `deck`, `console`, `composer`, or `launch` alias — each is either
taken (§2) or deliberately deferred (§5). If a later pass wants the composer
intuition, add the *word* "compose" to the body, not a fourth alias.

## 7. Follow-ups (not done here)

- Memory-write pass (needs `/sase_memory_write` + `/sase_new_task` flow): create
  `glossary:prompt-bar` per §6, add `[[glossary:prompt-bar]]` back-links from
  `prompt-stash` ("parked outside the prompt bar") and any stack-adjacent strands
  the keeper approves. This report only recommends the entry; it does not write
  memory.
- Optional docs pass: retitle `docs/reference/tui/prompt-input.md`'s "Prompt Input
  Widget" heading to "Prompt Bar" with the old spelling kept as an anchor alias,
  and standardize guides on "prompt bar" where they currently mix "prompt bar" /
  "prompt input" / "prompt widget". Small, mechanical, and safe to defer until the
  term lands.
- Deliberately out of scope: renaming `PromptInputBar`, `FrontmatterPanel`, CSS
  ids, or keymaps. The term is a docs/glossary layer over stable code names.

## Sources checked

- `src/sase/ace/tui/widgets/prompt_input_bar.py` (container + mixins)
- `src/sase/ace/tui/widgets/prompt_text_area.py` (per-pane editor)
- `src/sase/ace/tui/widgets/prompt_stack.py`,
  `src/sase/ace/tui/widgets/_prompt_stack_state.py`,
  `src/sase/ace/tui/widgets/_prompt_input_bar_stack_rendering.py` (stack model +
  rendering)
- `src/sase/ace/tui/widgets/frontmatter_panel.py`,
  `src/sase/ace/tui/widgets/_prompt_input_bar_frontmatter.py`,
  `src/sase/ace/tui/styles.tcss` (`#frontmatter-panel`, `#prompt-stack`)
- `docs/reference/tui/prompt-input.md`, `docs/reference/tui/prompt-stacks.md`,
  `docs/reference/macros/multi-agent-prompts.md`,
  `docs/blog/posts/prompt-widget-and-nvim.md`,
  `docs/guides/run-agents-in-parallel.md`
- `sase/memory/glossary.md` + strands `prompt-stash.md`, `raw-prompt.md`,
  `stash-trash.md`, `deck-panel.md`, `node-panel.md`, `agent-data-deck.md`;
  live `sase memory read` for `prompt-stash`, `raw-prompt`, `macro`,
  `macro-invocation`
