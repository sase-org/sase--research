# Naming the "Prompt Input Widget"

**Question.** What is the best glossary name for the TUI surface now called the "prompt
input widget", covering the widget itself, how its prompt stacks work, and its property
panel?

**Short answer.** Call it the **Prompt Composer** (alias *composer*). It is the standard
industry word for "the area where you write a message before sending it, plus the controls
around it". It does not clash with any existing SASE term. It covers every mode the widget
has, not only agent launches. And it gives a clean hierarchy: **composer → prompt stack →
pane**, with the **properties panel** sitting above the stack. The runner-up is to keep
**Prompt Bar** and just define it: no churn, but "bar" undersells what the widget has
become. A ready-to-paste glossary strand is in the last section.

---

## 1. What the widget actually is

Code facts this report relies on (paths relative to the sase repo):

| Piece | Code | What it does |
| --- | --- | --- |
| The widget | `PromptInputBar` (`src/sase/ace/tui/widgets/prompt_input_bar.py`), assembled from 14 mixins | Bottom-docked; border title `Prompt`, `Prompt · N agents`, `Plan Feedback`, or `Coder Prompt` (`_prompt_input_bar_title.py`) |
| Its model | `PromptStackState` (`_prompt_stack_state.py`): `items`, `selected_index`, `frontmatter`, `binding` | "The stack always holds at least one item" — a one-pane prompt is a stack of one |
| A pane | `PromptStackItem` + `PromptTextArea`, a vim-mode (INSERT/NORMAL/VISUAL/V-LINE) Markdown TextArea | One per agent segment, top-to-bottom = launch order; parked panes are compact under `─── ▍ agent N ───` rules |
| Auxiliary pane | `role` = `snippet` or `mini_macro`; at most one, pinned at the bottom | Excluded from `agent_items` ("items that participate in launch, stash, and save-as payloads") |
| Property panel | `FrontmatterPanel` (`frontmatter_panel.py`), border title `frontmatter`, empty state "No properties yet." | Structured editor for the stack's **shared** YAML frontmatter, mounted above the stack, prompt mode only |
| Binding | `MacroBinding` / `MacroReadonlyTarget` | When the widget is editing a macro definition: double border, `✎ #ref` chip, `gw` writes back |

Rough layout (prompt mode, three panes, properties panel shown):

```text
┌ frontmatter ✎ #my_macro ─────────────────────────────────┐   ← property panel (g=)
│ name: …   input: ▸ 2   macros: ▸ _helper                 │      shared by all panes
└──────────────────────────────────────────────────────────┘
┏ Prompt · 3 agents ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓   ← the widget
┃ ─── ▍ agent 1 ──────────────────────────── Ln 1, Col 12 ┃      parked pane (compact)
┃ ─── ▍ agent 2 ──────────────────────────── Ln 3, Col 1  ┃      parked pane (compact)
┃ ─── ▍ agent 3 ───────────────────────────────────────── ┃      active pane (full height)
┃ %wait  review the diff from agent 2 …                   ┃
┗ [Enter] send  [Esc] normal  [^C] cancel ━━ Ln 1, Col 7 ━┛
```

How the stack works, in brief:

- Text that is *loaded* (from history, from a `$EDITOR` round trip, from a ` @` review return)
  is split into panes at top-level `---` lines. A `---` you type yourself stays literal
  text; you add a pane with `g-` / `Ctrl+G -`.
- `gj`/`gk` move focus between panes, `gJ`/`gK` reorder them, and the bottom pane is
  active by default.
- `Enter` opens a submit menu (all panes, or `c` for the current one). `g<Enter>`
  launches just the selected pane and removes it from the stack. `Ctrl+C` cancels one
  pane; `Ctrl+G Ctrl+C` cancels them all.
- Pane order alone does not make agents run in sequence. A bare `%wait` in a later pane
  waits on the pane directly above it.
- `Ctrl+S` stashes the active pane; `gs` stashes the whole stack as one Prompt Stash row.

How the property panel works, in brief:

- It edits the same fields a macro `.md` file has (`name`, `description`, `tags`,
  `input`, `macros`, `skill`, `snippet`).
- `g=` shows or focuses it. It also opens on its own when loaded text carried
  frontmatter or when a macro definition is loaded for editing.
- Rows mode keys: `a` adds a property, `d` deletes, `u` undoes, `R` opens raw YAML.
  `input` and `macros` fold open into sub-trees.
- A `_helper` macro declared there gets completion in every pane right away.
- Single-pane launches re-attach the frontmatter so local macros still resolve.

## 2. The current naming mess

How often each name appears across `docs/` and `default_config.yml`:

| Phrase | Hits | Refers to |
| --- | ---: | --- |
| "prompt bar" | 56 | whole widget (also `_prompt_bar_mount_*.py`, `_hijack_prompt_bar.py`, and sase-core comments) |
| "prompt stack" | 38 | multi-pane state / feature |
| "prompt input widget" | 28 | whole widget (docs heading, blog post [08]) |
| "prompt pane" | 28 | one pane |
| "prompt editor" | 4 | whole widget (inconsistent) |
| "prompt input bar" | 2 | whole widget (code name) |

The property panel has **four** names: "**Frontmatter Panel**" (docs heading in
`reference/macros/multi-agent-prompts.md`), "macro frontmatter panel" (keymap tables),
"prompt properties panel" (`directive-composition.md`, and commits `e29bd388f1` and
`f07fe193af`: "xprompt properties panel"), and the class name `FrontmatterPanel`, whose
border title reads `frontmatter`. A glossary term is the right place to fix one canonical
name for the widget and record the rest as aliases.

## 3. What makes a good name here

These criteria come from how the existing glossary names things (Deck Panel → Agent Data
Deck → Agent Data Card → Card Block; Prompt Stash / Stash Trash; Macro (xprompt); Routine
(Lumberjack)):

1. **No clash with an existing SASE word.** The neighbourhood is crowded:
   - **Prompt Stash** and **Stash Trash** are glossary terms, and "stash" appears in the
     widget's own keymap (`Ctrl+S`, `gs`, `gS`).
   - The **Prompts overlay** (History/Stash/Trash) is a separate surface.
   - The **agent prompt panel** (`widgets/prompt_panel/`) is an Agents-tab widget.
   - **deck** is the alias for Agent Data Deck.
   - **Launch Control** (`,m`) is another surface.
   - **editor** already means `$EDITOR` (`EditorRequested`, "whole-bar editor session",
     "editor-file semantics") and the panel's raw/inline sub-editors.
   - **prompt inputs** already means macro `input:` declarations
     (`ace.prompt_inputs.*`, `src/sase/agent/prompt_inputs.py`, `InputArg`).
2. **Covers every mode, not just launching.** The same widget writes agent prompts, Plan
   Feedback, Coder Prompt replies, hijack Instruct/Edit text, and bound macro/snippet
   definitions. Launch-only names (launchpad, launcher) are wrong for half of these.
3. **Names a container, not a part.** The widget holds panes, a stack, a properties
   panel, chips, hint rows, a search panel, and a submit menu. "Panel" and "pane" are
   already its parts, and "bar" suggests a single thin strip.
4. **Future agents can guess it.** An LLM should know what it means without reading the
   glossary strand. That favours a word with strong industry use.
5. **Short, two words, easy to grep.** A "Prompt X" compound matches Prompt Stash and Raw
   Prompt, and stays unique when you search for it.
6. **Leaves room for the sub-parts.** The sub-terms (stack, pane, properties panel)
   should read naturally under it, the way card and block sit under deck.
7. **Works beyond the TUI.** The Rust-core rule assumes web, editor, and mobile frontends
   may share behaviour. A name that also fits a web or mobile UI is better than one tied
   to the terminal.

## 4. Industry precedent

Two naming families dominate:

- **"Composer"**: the writing area plus the controls around it.
  - OpenAI's Codex CLI TUI calls its input `ChatComposer`, inside a `BottomPane` that
    also hosts popups and overlays, and keeps the draft while other views cover it
    ([DeepWiki: BottomPane and input system](https://deepwiki.com/openai/codex/4.1.3-bottompane-and-input-system);
    [tui-chat-composer design note mirror](https://forge.lthn.ai/core/core-agent-ide/src/branch/dev/docs/tui-chat-composer.md)).
  - Zulip's user docs call it the "compose box"
    ([Mastering the compose box](https://chat.fhir.org/help/mastering-the-compose-box)).
  - Chat SDKs ship "Message composer" components
    ([Stream](https://getstream.io/chat/docs/sdk/react/ui/components/message-composer-ui/),
    [CometChat](https://www.cometchat.com/docs/ui-kit/react/message-composer.md)).
  - Element / matrix-react-sdk changelogs mention its "message composer".
- **"Prompt input"**: a narrower, text-field-centred name.
  - Vercel's AI Elements and shadcn ship a `PromptInput` component
    ([AI Elements](https://elements.ai-sdk.dev/components/prompt-input),
    [shadcn](https://ui.shadcn.com/docs/ai-elements/base/prompt-input.md)).
  - Gemini CLI's component is `InputPrompt`
    ([keyboard shortcuts doc](https://geminicli.com/docs/cli/keyboard-shortcuts)).
  - Gerrit's chat panel uses `prompt-box`
    ([source](https://gerrit.googlesource.com/gerrit/+/master/polygerrit-ui/app/elements/chat-panel/prompt-box.ts)).

"Composer" is the family used for the *rich* case: several parts, attachments, metadata,
popups. That is what SASE's widget is now. "Prompt input" fits a single text field, and
in SASE it also clashes with macro inputs.

## 5. Candidates scored

Scale is 1–5, higher is better. Hits are whole-word, case-insensitive matches of the
candidate's distinctive word across `src/sase` and `docs`.

| Candidate | Repo hits | No clash | All modes | Container | Agent can guess | Short | Low churn | **Total** |
| --- | ---: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **Prompt Composer** | composer: 9 | 5 | 5 | 5 | 5 | 4 | 3 | **27** |
| Prompt Bar | bar: 1818 (but "prompt bar" itself is unique) | 4 | 4 | 2 | 4 | 5 | 5 | **24** |
| Prompt Workbench | workbench: 1 | 5 | 5 | 5 | 3 | 2 | 3 | **23** |
| Prompt Slate | slate: 26 (colour names only) | 5 | 4 | 3 | 2 | 5 | 3 | **22** |
| Prompt Dock | dock: 32 (Textual CSS `dock:`) | 4 | 4 | 4 | 2 | 5 | 3 | **22** |
| Prompt Pad | pad: 89 (+ `padding` ×815) | 3 | 4 | 3 | 3 | 5 | 3 | **21** |

Notes on each:

- **Prompt Composer.**
  - The only existing "composer" in sase is a docstring calling a Rust function the
    "snippet catalog composer" (`src/sase/core/snippet_catalog_facade.py`). Linked
    sase-core has one hit, in a test-fixture note. Neither is user-facing, so the clash
    is minor.
  - The docs already use the verb: "compose multi-agent prompts directly in the prompt
    input widget" (blog), "opens `$EDITOR` for composing a prompt" (agent-launches).
  - It reads well in every mode: "compose plan feedback", "compose a macro definition".
  - Optional mnemonic: a composer writes a score with several parts. The panes are the
    parts, and the properties panel is like the key and tempo marked once at the top
    for every part.
- **Prompt Bar.** The zero-churn option: it matches the code (`PromptInputBar`,
  `_prompt_bar_*`), the most common phrase in the docs, and existing sase-core comments.
  The cost is that "bar" means a thin strip, while the widget is now a stack of panes
  with a panel above it. It is also TUI-specific.
- **Prompt Workbench.** Accurate (lots of tools around one work surface) but long. In
  prose it shrinks to "workbench", which is generic (Eclipse, MySQL Workbench).
- **Prompt Slate.** A SASE-flavoured coinage in the spirit of *stitch*, *smack*, or
  *hood*. Three meanings help it: a slate you write on, a "slate" of agents, and "slated
  to launch". It is unique in the repo, but an agent would not guess its meaning
  unaided.
- **Prompt Dock.** Describes where it sits (`dock: bottom`) and hints at a shipyard
  before launch. It clashes mildly with Textual CSS `dock`, and says little about
  editing.
- **Prompt Pad.** A writing pad is literally a stack of sheets bound at the top, which
  maps neatly onto panes plus a shared header. But "pad" is swamped by CSS padding when
  you grep, and "launch pad" brings back the launch-only problem.

### Rejected outright

| Name | Why not |
| --- | --- |
| **Prompt Stack** | The strongest code-level contender: `PromptStackState` already models the whole widget. But it is one letter from **Prompt Stash**, an existing term whose actions live in this widget's keymap ("`gs` stashes the stack"). It would also swallow the multi-pane sub-concept it currently names. Keep "prompt stack" as the sub-term. |
| **Prompt Input** | Clashes with macro *inputs* (`ace.prompt_inputs`, `prompt_inputs.py`, the panel's own `input:` rows). "Prompt input widget" survives only because of the extra word. |
| **Prompt Editor** | "editor" means `$EDITOR` throughout this widget's code and docs, plus the panel's raw/inline editors. |
| **Prompt Panel** | `widgets/prompt_panel/` is the Agents-tab agent prompt panel. The widget also *contains* panels (properties, completion, memory, snippets). |
| **Prompt Deck** | "deck" is the glossary alias for Agent Data Deck. |
| **Launchpad / Launcher** | Clashes with Launch Control and the internal "launcher" (47 hits). Wrong for Plan Feedback, Coder Prompt, hijack, and macro-editing modes. Also the name of Canonical's code forge. |
| **Prompt Console / Box / Tray / Well** | console: 3365 hits (Rich `Console`); "box" is generic; "tray" and "well" carry no meaning for agents. |

## 6. Ranked recommendation

1. **Prompt Composer** (alias *composer*): best on clashes, mode coverage, container
   meaning, and agent guessability; fits future frontends.
2. **Prompt Bar**: define the status quo if zero churn matters more than accuracy.
3. **Prompt Workbench**: accurate but wordy.
4. **Prompt Slate**: the best SASE-flavoured coinage if you want something distinctive.
5. **Prompt Dock**: reasonable; weak on editing meaning.
6. **Prompt Pad**: nice metaphor, bad grep.

Positions 3–6 are within two points of each other; positions 1 and 2 are the real
choice.

**Sub-term recommendation.** Make the sub-parts canonical inside the strand:

- **prompt stack**: the ordered panes, plus the frontmatter they share.
- **pane**: one per agent, with the snippet / mini-macro pane as the "auxiliary pane".
- **properties panel**: the user's "property panel"; it matches the commit history and
  the "No properties yet." empty state.

Record "frontmatter panel" as the code and title alias. Changing the panel's border title
from `frontmatter` to `properties` would remove the last mismatch, but that is a separate
UI change, not part of adding the glossary term.

**Adoption path.** This follows the precedent of *Macro (xprompt)* and *Routine
(Lumberjack)*: define the new name and list the old ones as aliases, so the code
(`PromptInputBar`, `FrontmatterPanel`) does not have to be renamed. Docs can move gradually
(start with the "Prompt Input Widget" heading in `reference/tui/prompt-input.md` and blog
post [08]). Adding the strand is a memory write, so it should go through
`/sase_memory_write`.

## 7. Recommended glossary entry (#1 pick)

File: `sase/memory/glossary/prompt-composer.md`. The body is about 150 words; the
glossary's mean is about 82 and its maximum about 250. The entry is longer than average
because it is meant to cover three concepts in one term.

```markdown
---
keyword: Prompt Composer
aliases:
  - composer
  - prompt bar
  - prompt input widget
---

The prompt composer is the TUI's bottom-docked prompt-writing widget (`PromptInputBar`)
for agent prompts, Plan Feedback, Coder Prompt replies, and bound macro definitions. It
holds a prompt stack: one or more vim-mode panes, one per agent, in top-to-bottom launch
order. Loaded text splits into panes at top-level `---`, but a typed `---` stays literal;
`g-` adds a pane, `gj`/`gk` focus, `gJ`/`gK` reorder, and the title reads
`Prompt · N agents`. `Enter` launches all panes or the current one; order alone never
sequences them — a bare `%wait` waits on the pane above. `gs` stashes the whole stack as
one [[glossary:prompt-stash]] row. One snippet or mini-macro pane may sit pinned at the
bottom and never launches. Above the stack, the properties panel (`FrontmatterPanel`,
titled `frontmatter`, toggled with `g=`) edits the stack's shared frontmatter with a
macro file's fields; `_` local macros declared there complete in every pane, and a
single-pane launch re-attaches it.
```

---

### Sources

- sase repo (this workspace): `src/sase/ace/tui/widgets/prompt_input_bar.py`,
  `_prompt_stack_state.py`, `_prompt_input_bar_title.py`, `_prompt_input_bar_frontmatter.py`,
  `frontmatter_panel.py`, `_frontmatter_panel_rendering.py`, `styles.tcss`;
  `docs/reference/tui/prompt-input.md`, `prompt-stacks.md`,
  `docs/reference/macros/multi-agent-prompts.md`, `directive-composition.md`,
  `docs/blog/posts/prompt-widget-and-nvim.md`; glossary strands Deck Panel, Agent Data
  Deck/Card/Block, Prompt Stash, Stash Trash, Raw Prompt, Nav Item/Section, Node Panel.
- Linked sase-core checkout: grep for name collisions only.
- [DeepWiki — Codex BottomPane and input system](https://deepwiki.com/openai/codex/4.1.3-bottompane-and-input-system)
- [Codex TUI chat-composer design note (mirror)](https://forge.lthn.ai/core/core-agent-ide/src/branch/dev/docs/tui-chat-composer.md)
- [Zulip — Mastering the compose box](https://chat.fhir.org/help/mastering-the-compose-box)
- [Stream — Message composer UI](https://getstream.io/chat/docs/sdk/react/ui/components/message-composer-ui/)
- [CometChat — Message composer](https://www.cometchat.com/docs/ui-kit/react/message-composer.md)
- [Vercel AI Elements — Prompt Input](https://elements.ai-sdk.dev/components/prompt-input)
- [shadcn AI elements — prompt input](https://ui.shadcn.com/docs/ai-elements/base/prompt-input.md)
- [Gemini CLI keyboard shortcuts (input prompt)](https://geminicli.com/docs/cli/keyboard-shortcuts)
- [Gerrit chat-panel prompt-box.ts](https://gerrit.googlesource.com/gerrit/+/master/polygerrit-ui/app/elements/chat-panel/prompt-box.ts)
