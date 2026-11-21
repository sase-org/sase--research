# Naming the "prompt input widget": consolidated report

**Question.** What is the best glossary name for the TUI surface currently called the
"prompt input widget" — one new concise term whose entry covers the widget itself, how
its prompt stacks work, and how its property panel works?

**Consolidated verdict: name it the `Prompt Composer`, with the one-word alias
`composer` and legacy aliases `prompt bar` and `prompt input widget`.** Three of five
researchers (cdx, cld, gem) ranked Prompt Composer first; the other two (grk, mus)
ranked Prompt Bar first with Composer as their named runner-up, so Composer is the only
candidate every report placed in its top three. The lead verification pass re-ran the
contested counts and collision checks in a fresh checkout and they support Composer.
The recommended strand entry is in §6.

## 1. What is being named

All five reports agree on the anatomy, verified against `master` @ `811576c390`. One
container, three layers, plus a crowd of easy-to-confuse neighbors:

| Layer | Code | Role |
| --- | --- | --- |
| Widget | `PromptInputBar` (`src/sase/ace/tui/widgets/prompt_input_bar.py`, ~14 mixins, `dock: bottom`) | Bottom-docked authoring surface. Border title `Prompt` / `Prompt · N agents`, or `Plan Feedback` / `Coder Prompt` in those single-pane modes. |
| Stack | `PromptStackState` / `PromptStackItem` (`_prompt_stack_state.py`), `#prompt-stack` | Ordered vim-mode panes (always ≥ 1) plus shared YAML frontmatter; top-to-bottom launch order. |
| Property panel | `FrontmatterPanel` (`frontmatter_panel.py`), `#frontmatter-panel` | Structured editor for that shared frontmatter, mounted above the stack, prompt mode only. |

```text
┌ frontmatter ✎ #my_macro ⟨✓⟩ ──────────────────────────────┐  ← property panel (g=)
│ ▸ input  2 items    ▸ macros  _helper                     │     shared by all panes
└───────────────────────────────────────────────────────────┘
┏ Prompt · 3 agents ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  ← the widget
┃ ─── ▍ agent 1 ───────────────────────────── Ln 1, Col 12 ┃     parked pane (compact)
┃ ─── ▍ agent 2 ───────────────────────────── Ln 3, Col 1  ┃     parked pane (compact)
┃ ─── ▍ agent 3 ────────────────────────────────────────── ┃     active pane (grows)
┃ %wait  review the diff from agent 2 …                    ┃
┃ ─── ⇥ fix · sase.yml new ──────────────────────────────── ┃     auxiliary pane (gt/gx)
┗ [Enter] send  [Esc] normal  [^C] cancel ━━━ Ln 1, Col 7 ━┛
```

Behavioral facts the glossary entry must get right (consistent across all reports):

- **Load splits; typing does not.** Loaded text (history, `$EDITOR` return, ` @` review
  return) splits into panes at top-level `---` outside frontmatter and fences, lifting
  leading frontmatter into the panel. A typed `---` stays literal; `g-` / `Ctrl+G -`
  adds a pane. A single history item with frontmatter but no separator stays one
  verbatim pane (grk).
- **Order is arrangement, not scheduling.** `gj`/`gk` focus, `gJ`/`gK` reorder;
  whole-stack submit joins panes top-to-bottom with `---`; `g<enter>` launches only the
  active pane, re-attaching the shared frontmatter so local macros still resolve. Pane
  order alone never sequences agents — a bare `%wait` waits on the pane above (cld).
  A `#name` macro swarm stays one pane until launch, so pane ≠ agent (cdx).
- **Auxiliary panes author, not launch.** At most one pinned snippet (`gt`) or
  mini-macro (`gx`) pane rides the stack, excluded from launch, stash, and save-as
  payloads; `Enter` inside it saves the definition.
- **The property panel is a scoped header inspector.** `g=` toggles/focuses it; it
  edits macro-file fields (`name`, `description`, `tags`, `input`, `macros`, `skill`,
  `snippet`) as rows with an `a` property picker, `d`/`u`/`J`/`K` edits, and an `R`
  live-validated raw-YAML escape hatch. Ordinary panes share the stack's frontmatter;
  on a mini-macro pane the panel switches to that macro's own frontmatter scope (cdx,
  gem). It is document metadata, not app settings.
- **Not every instance has a stack or panel.** Plan Feedback and Coder Prompt reuse the
  same class as a single pane with no stack or properties, so the name must not promise
  multi-agent launching (cdx, grk, gem).

**Neighbors the term must stay distinct from** (gem's list, corroborated by mus/grk):
the read-only Agents-tab `AgentPromptPanel` (`widgets/prompt_panel/`), the Prompts
overlay (History/Stash/Trash), the post-submit **Prompt Inputs** "Fill in this prompt"
panel, Prompt Stash / Stash Trash, Raw Prompt, and external `$EDITOR` / `sase-nvim`.

## 2. Verified evidence base

The lead pass re-ran the contested measurements; results match gem's report (cld's
lower counts came from a narrower docs-only scope, not a conflict):

| Phrase | `docs/` + `src/sase/` hits | Bryan's prompt history |
| --- | ---: | ---: |
| prompt bar | 176 | **0** |
| prompt input | ~175 | 23 |
| prompt stack | 78 | 0 |
| prompt input bar | 42 | 0 |
| frontmatter panel | 37 | 0 |
| prompt input widget | 30 | **26** |
| prompt widget | 20 | 0 |
| prompt editor | 9 | 0 |
| properties panel / property panel | 3 / 0 | 0 / 1 |
| prompt composer | 0 | 0 |

Three load-bearing verified facts:

1. **The docs' favorite word is not the user's.** "prompt bar" dominates docs and code
   prose (176 hits) but appears zero times in Bryan's own prompt history, where
   "prompt input widget" (26) and "property panel" (1) are his habitual phrases. This
   undercuts the strongest Prompt Bar argument ("it's already everyone's word") — it is
   the docs' word, not the operator's.
2. **"composer" is clean inside SASE.** The only internal uses are nine docstring lines
   about unrelated renderers (pager gutter composer, snippet catalog composer, monitor
   follow-up composer, hijack preview composer) — none in docs or user-facing prose.
   gem additionally probed `sase-core`'s live Rust glossary matcher
   (`validate_glossary_entries`, `compile_glossary_catalog`, `scan_glossary_spans`)
   across all 72 strands and all of `docs/`: both `Prompt Composer` and bare
   `composer` produce 0 false positives and 0 diagnostics. No other candidate with a
   safe one-word alias exists — `bar`, `pad`, `dock`, `slate`, `box` all false-match
   (`TopBar`, padding, `dock: bottom`, the MkDocs `slate` theme, search boxes).
3. **Glossary style supports it.** TUI surface terms are two-word
   `<qualifier> <surface>` phrases with one-word aliases when unambiguous (`Agent Data
   Deck (deck)`, `Prompt Stash (stash)`); strands average ~90 words with a 274-word
   maximum, so a ~250-word three-part entry fits. SASE's recent renames (`xprompt →
   macro`, `chop → job`, `AXE → scheduler`) consistently chose self-describing,
   industry-grounded names and kept legacy spellings as aliases — exactly the Composer
   adoption path.

**Industry precedent** (cdx, cld, grk): "composer" is the established name for a rich
message-authoring area — Slack's message composer, Zulip's compose box, Stream and
CometChat SDK components, and OpenAI Codex CLI's own TUI `ChatComposer` — while
"prompt input" names bare text fields (Vercel AI Elements `PromptInput`, Gemini CLI
`InputPrompt`). SASE's widget is squarely in the rich-composer family: metadata header
above multiple bodies. The notable external collision is Cursor, where "Composer" is
now a model line; grk weighted this heavily, cdx and gem judged it minor because the
SASE term is always the two-word `Prompt Composer` in roster and docs, and the bare
alias only matters inside SASE prose where the matcher found zero ambiguity. The lead
assessment sides with cdx/gem: a competitor's model name does not claim the English
word for a text-authoring surface.

## 3. Why Prompt Composer beats Prompt Bar

The swarm's only real disagreement. The Bar case (grk, mus): 176 existing prose hits,
maps to `PromptInputBar`, zero-churn canonization of the status quo, and coining costs
every future agent a lookup. The Composer case (cdx, cld, gem): the resolution —

- **Retrieval is solved by aliases, not by the keyword.** Keeping `prompt bar` and
  `prompt input widget` as aliases means every existing doc sentence, the class name
  trail, and Bryan's own habit all resolve to the same strand; the matcher underlines
  all three spellings. mus's own analysis concedes aliases capture the mapping benefit
  "at zero cost".
- **"Bar" now actively misleads.** In SASE itself, `TopBar`, `TabBar`, and the filter
  bars are one-row strips; this widget is a tall stack of vim panes under a structured
  property inspector. gem's point is decisive: the glossary entry would have to spend
  its first sentence fighting its own keyword.
- **Only Composer yields a safe shorthand and clean compounds.** "open the composer",
  "composer pane", "the composer's property panel" — versus the four-noun pile-up
  "prompt bar property panel" and no usable bare "bar".
- **The user never adopted "bar".** Zero prompt-history hits after years of docs usage
  is revealed preference; canonizing it would enshrine a name the operator declines to
  use.
- **It covers every mode.** Composing applies equally to agent prompts, plan feedback,
  coder replies, and macro/snippet definitions; launch-flavored names do not.

The residual costs, honestly stated: Composer has zero existing hits, so adoption
depends entirely on the aliases until a small docs retitle pass lands; and the Cursor
echo exists. Both are bounded, one-time costs; "bar" misdescribing the widget is a
permanent one.

## 4. Ranked names

1. **Prompt Composer** (alias `composer`) — accurate for all three parts and all four
   modes, the only candidate with a collision-free one-word alias, matcher-verified
   clean, industry-grounded, clean compounds. Every report's top-3.
2. **Prompt Bar** — the conservative fallback: codifies the docs' dominant phrase and
   maps to `PromptInputBar` with zero churn. Costs: understates the widget, no safe
   shorthand, awkward compounds, and zero uptake in the user's own prompts. Keep as an
   alias regardless.
3. **Prompt Pad** — best compact metaphor (a writing pad is stacked sheets under one
   header; launch pad resonance). Cold-start confusable with Prompt Stash, "pad" is
   swamped by padding in grep, and the launch sense fails the feedback/coder modes.
4. **Prompt Dock** — literally matches `dock: bottom` geometry; names where it sits,
   not what it does; mild collisions with Textual CSS `dock` and the Services-tab
   "detail dock".
5. **Prompt Workbench** — accurate about coordinated tools but long, product-y, and it
   shrinks to the generic "workbench" in prose.
6. **Prompt Slate** — distinctive writing-surface + "slate of agents" coinage; opaque
   on cold read and `slate` collides with the MkDocs dark theme name.

**Disqualified** (candidate — fatal flaw): *Prompt Input / Prompt Input Widget* —
"input" collides with the typed-inputs cluster (`input:` fields, `<placeholder>` tags,
`ace.prompt_inputs`) and the matcher auto-derives the plural, false-matching the
post-submit **Prompt Inputs** panel; "widget" is Textual jargon. *Prompt Editor* —
"editor" means `$EDITOR`/`sase-nvim` throughout this widget's own docs (cdx alone
ranked it #2; three reports disqualify it). *Prompt Stack* — part-for-whole, one letter
from Prompt Stash, and wrong for single-pane modes. *Prompt Panel* — taken by
`AgentPromptPanel`. *Prompt Deck* — `deck` belongs to Agent Data Deck. *Launchpad /
Launch Bar* — launch is one job among several. *Prompt Drawer* — Patch `.sase` lines
are already "drawers". *Prompt Bench* — the perf harness owns `bench`. *Prompt Stage* —
collides with auto-staged inputs and git staging. *Console / Box / Bay / Tray / Shelf /
Sheet / Strip / Rail / Surface / Book / Loom / Studio / Builder / Canvas* — each either
collides with an existing SASE surface or carries no retrievable meaning.

## 5. Sub-term guidance

One new strand, not three (grk). Inside the entry, canonize the part names:

- **prompt stack** — keep; already a reference page, a code type, and 78 prose hits.
- **pane** — one `PromptStackItem` (`agent` / `snippet` / `mini_macro`); auxiliary
  panes are the non-launching kind.
- **property panel** — the prose name for `FrontmatterPanel`, with "frontmatter panel"
  recorded as the code/docs alias. This bridges the real split: code and docs say
  frontmatter (37 hits), while Bryan, the empty state ("No properties yet."), the
  `[^G =] properties` subtitle, and `AddPropertyModal` / `PropertyPickerModal` all say
  property/properties. (grk and cld preferred plural "Properties Panel"; the singular
  below matches Bryan's own phrasing and reads identically in prose.) Do not rename the
  class, CSS ids, or docs headings in the same change.

## 6. Recommended glossary entry (#1 pick)

Target file `sase/memory/glossary/prompt-composer.md`, created through
`/sase_memory_write`. gem verified this shape parses cleanly
(`parse_memory_strand`: 0 errors) and compiles against all 72 strands with 0
diagnostics and 0 false positives. Roster line: `Prompt Composer (composer, prompt
bar, prompt input widget)`.

```markdown
---
keyword: Prompt Composer
aliases:
  - composer
  - prompt bar
  - prompt input widget
---

A prompt composer is the TUI's bottom-docked prompt-authoring widget (`PromptInputBar`)
whose vim-mode panes draft agent prompts, Plan Feedback, Coder Prompt replies, and
bound macro or snippet definitions (`✎ <ref>` chip, `gw` writes back). In prompt mode
it holds a **prompt stack**: one or more panes in top-to-bottom launch order, each
holding one agent segment (a `#name` macro swarm stays one pane until launch). Loaded
text splits into panes at top-level `---`; a typed `---` stays literal and `g-` adds a
pane. `gj`/`gk` move focus, `gJ`/`gK` reorder; `Enter` opens the submit chooser and
`g<enter>` launches only the active pane — order alone never sequences agents, and a
bare `%wait` waits on the pane above. `Ctrl+S` stashes a pane and `gs` the whole stack
to the [[glossary:prompt-stash]]. At most one pinned auxiliary pane (snippet `gt`,
mini-macro `gx`) edits a definition and never launches.

Its **property panel** (`FrontmatterPanel`; docs call it the frontmatter panel; `g=`
toggles) sits above the stack and edits the stack's shared YAML frontmatter as
structured fields (`name`, `description`, `input`, `macros`, …) with an `a` property
picker and an `R` raw-YAML view. Local `_helper` macros declared there complete in
every pane, and a single-pane launch re-attaches the shared frontmatter; on a
mini-macro pane the panel switches to that macro's own frontmatter scope.

Distinct from the read-only Agents-tab prompt panel, the Prompts overlay, the
post-submit Prompt Inputs panel, and external `$EDITOR` sessions; Plan Feedback and
Coder Prompt reuse the widget without a stack or property panel.
```

**Rollout notes** (gem, grk, mus — consistent): glossary-only at first; do not rename
`PromptInputBar`, `FrontmatterPanel`, `#frontmatter-panel`, or keymaps — the strand
names those symbols so agents map from the term straight to code. Optional later docs
pass: retitle the "Prompt Input Widget" heading in `docs/reference/tui/prompt-input.md`
and standardize guide prose. After landing: `sase memory init`, then
`sase memory read glossary:composer -r "verify"`, and confirm in the TUI that "prompt
composer", "composer", "prompt bar", and "prompt input widget" underline while "Prompt
Inputs" and "top bar" stay plain. gem also checked roster ordering: `Prompt Composer`
sorts after `Macro (xprompt)`, so the pinned roster line in
`tests/_macro_terminology_docs.py` is undisturbed.

## 7. Report attribution

- **cdx** (`prompt_composer_glossary_term__cdx.md`): Composer #1; visual-snapshot
  verification; pane ≠ agent and stack-is-not-scheduling constraints; external UX
  precedent (NN/g, Slack, VS Code, Qt); Cursor-collision framing.
- **cld** (`prompt_composer_glossary_term__cld.md`): Composer #1; scored criteria
  matrix; the `%wait`-waits-on-pane-above detail; Codex `ChatComposer` precedent; the
  four-names-for-the-property-panel audit; strand word-count budget.
- **grk** (`prompt_composer_glossary_term__grk.md`): Bar #1; strongest anti-"input"/
  anti-"widget" case; load-path differences (history vs stash vs `,x`); the TUI noun
  ladder (bar/stack/pane/panel/overlay); Cursor-as-model-line caution.
- **mus** (`prompt_composer_glossary_term__mus.md`): Bar #1; fullest code anatomy
  (mixin inventory, byte-stable frontmatter persistence); the aliases-capture-mapping
  argument this consolidation turns in Composer's favor.
- **gem** (`prompt_composer_glossary_term__gem.md`): Composer #1; the decisive
  empirical layer — prompt-history usage, live Rust matcher collision probes, strand
  validation of the proposed entry, disqualification table, rollout checklist.
- **Lead verification (this report)**: re-ran phrase counts (matches gem; resolves the
  cld discrepancy as scope difference), re-grepped internal "composer" uses (9
  docstring lines, none user-facing), re-counted prompt history ("prompt input widget"
  26, "prompt bar" 0, "property panel" 1), and confirmed glossary word-count budget
  (n=72, mean 90, max 274).
