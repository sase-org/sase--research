# Naming SASE's prompt authoring surface

Independent research by **cdx**, 2026-11-21. SASE checkout examined: `811576c390459be26fe3492d53dbbeca1f6f3d43`.

**Recommendation: call the whole widget the Prompt Composer.** Use *composer* as a contextual shorthand, retain *prompt stack* for its ordered prompt panes, and call its metadata editor the *frontmatter panel* or *composer's properties panel*. This gives future agents one clear parent concept without replacing every existing component name.

This report independently examines current source, documentation, glossary definitions, saved visual snapshots, and external interface terminology. No other report or findings from this researcher swarm were consulted. The ranking is a reasoned naming judgment, not the result of a user study or a claim that one name is objectively optimal. The final glossary text is a proposal for the lead researcher's synthesis.

**What the name must encompass.** The existing name hides three levels that need separate references:

| Level | What it means in SASE | Recommended wording |
| --- | --- | --- |
| Entire authoring surface | The outer widget, editing controls, prompt panes, and optional metadata editor | Prompt Composer |
| Collection of prompt bodies | Ordered launchable panes, with shared prompt frontmatter | Prompt stack |
| One editable body | One prompt segment; it may expand into multiple launched agents | Prompt pane |
| Metadata editor | Structured fields and raw YAML for the relevant frontmatter scope | Frontmatter panel; the composer's properties panel |
| Temporary definition editor | A snippet or mini-macro pane alongside the prompt panes | Auxiliary pane, qualified by kind |

The hierarchy is visible in the implementation: `PromptInputBar` contains `FrontmatterPanel` above `#prompt-stack`, which holds the text panes. The properties panel is a child of the overall widget, not a different name for the widget. The same class has feedback and approval variants without the multi-agent surface, so the general name should not promise that every instance shows a stack or properties. [Widget composition](https://github.com/sase-org/sase/blob/811576c390459be26fe3492d53dbbeca1f6f3d43/src/sase/ace/tui/widgets/_prompt_input_bar_lifecycle.py#L61).

I visually checked the repository's existing `frontmatter_panel_populated_120x40.png`, `prompt_stack_two_panes_120x40.png`, and `mini_macro_scoped_frontmatter_120x40.png` snapshots under `tests/ace/tui/visual/snapshots/png/`. They confirm the enclosing prompt border, vertically arranged bodies, and separate frontmatter area. These are saved test fixtures, not screenshots captured from a running session during this research.

Several behavioral details should constrain the terminology and definition:

- **A stack is editable arrangement, not scheduling.** Panes can be focused, reordered, launched separately, or submitted together. Whole-stack submission preserves top-to-bottom order, but order alone does not make agents wait. Calling this a queue, pipeline, or execution stack would invite the wrong model. [Stack controls and submission](https://github.com/sase-org/sase/blob/811576c390459be26fe3492d53dbbeca1f6f3d43/docs/reference/tui/prompt-stacks.md#L50).
- **A pane is not necessarily one resulting agent.** A macro swarm invocation remains one pane and expands at launch. The definition should say that a pane holds a prompt segment, allowing fan-out. [Loaded prompts and macro swarms](https://github.com/sase-org/sase/blob/811576c390459be26fe3492d53dbbeca1f6f3d43/docs/reference/tui/prompt-input.md#L31).
- **Loading and typing differ.** Loading multi-agent Markdown splits top-level `---` separators outside frontmatter and fenced code; typing `---` during live editing does not immediately create another pane. `g-` adds a pane in NORMAL mode. History, editor-return, and explicit-pane restore paths do not all parse identically. These are reference-document details, so the glossary should avoid promising a universal split-on-typing rule. [Load and editing semantics](https://github.com/sase-org/sase/blob/811576c390459be26fe3492d53dbbeca1f6f3d43/docs/reference/tui/prompt-stacks.md#L12).
- **Properties are document content.** The panel edits frontmatter such as `description`, `tags`, declared `input`, and local `macros`. It supports structured editing and a raw-YAML view. It is not the application's settings panel or a generic collection of model/provider controls; segment-local directives still live in prompt bodies. [Frontmatter panel](https://github.com/sase-org/sase/blob/811576c390459be26fe3492d53dbbeca1f6f3d43/docs/reference/macros/multi-agent-prompts.md#L29).
- **Shared properties have a meaningful exception.** Ordinary prompt panes use stack frontmatter; a mini-macro pane uses that definition's own frontmatter. A blanket definition saying every visible pane shares the same properties would be false. [Scope selection](https://github.com/sase-org/sase/blob/811576c390459be26fe3492d53dbbeca1f6f3d43/src/sase/ace/tui/widgets/_prompt_input_bar_frontmatter.py#L119).
- **The surface supports authoring for reuse.** It can edit a bound macro, write it back, save a new macro, and stage auxiliary definition panes. Those auxiliary panes are excluded from the normal launch payload. A name centered solely on sending or launching would understate this work. [Bound macro editing](https://github.com/sase-org/sase/blob/811576c390459be26fe3492d53dbbeca1f6f3d43/docs/reference/macros/multi-agent-prompts.md#L60), [payload selection and serialization](https://github.com/sase-org/sase/blob/811576c390459be26fe3492d53dbbeca1f6f3d43/src/sase/ace/tui/widgets/_prompt_stack_state.py#L216).

**What existing vocabulary rules out.** I read the relevant glossary entries through `sase memory read`: Agent Data Card, Agent Data Deck, Deck Panel, Prompt Stash, Stash Trash, Raw Prompt, Macro, Macro Swarm, and Clan Wave, including the related entries the audited read supplied.

*Deck* and *card* already describe output/detail presentation, while *stash* describes persisted drafts and *workspace* describes a numbered repository clone. Reusing these words would trade a short name for more disambiguation in every agent prompt. *Prompt Stack* is valuable as a child concept, but naming the whole widget after it would obscure the single-pane case and the properties panel. *Prompt* alone also blurs the distinction between content and its editing surface.

A targeted search of `src/sase`, `docs`, and `tests` found no established UI term **Prompt Composer**. Bare *composer* does occur in internal rendering and prompt-construction code; *workbench* also occurs around plan-approval UI. Neither is a glossary-level prohibition, but both favor keeping **Prompt** in the canonical name. *Prompt editor* already appears informally, including references to external-editor handoff, so it has familiarity but weaker scope boundaries.

**External terminology supports a functional name.** Nielsen Norman Group recommends matching users' language and familiar concepts rather than exposing internal terminology. I apply that principle here as an argument for naming the task performed—composing prompts—rather than the implementation category *input widget*. It does not by itself prove that *composer* will be more familiar to this particular user. [Match Between the System and the Real World](https://www.nngroup.com/articles/match-system-real-world/).

Slack's accessibility documentation uses *message composer* for the message-authoring area and describes an associated actions toolbar. This is useful precedent for *composer* encompassing text entry plus supporting controls. It does not establish that SASE's multi-pane behavior is common or already understood. [Use Slack with a screen reader](https://slack.com/help/articles/360000411963-Use-Slack-with-a-screen-reader).

VS Code uses *chat input box* within larger Chat views and editor surfaces. That wording shows why *input* remains appropriate for a text-entry component, but contributes little to distinguishing SASE's complete authoring surface from one body field. [Use chat in VS Code](https://code.visualstudio.com/docs/chat/chat-overview).

Qt Designer separately calls its editable metadata interface the *Property Editor*. That supports retaining an ordinary component name for properties rather than extending a creative parent metaphor to everything inside it. SASE's actual property scope must still come from its own implementation. [Qt Designer's Property Editor](https://doc.qt.io/qt-6/designer-widget-mode.html#the-property-editor).

There is a real disadvantage to *Composer*: Cursor uses it as a coding-model name, documented in its October 2025 release. Therefore use **Prompt Composer** as the full glossary name and **SASE's prompt composer** when discussing multiple tools. A bare global alias *composer* is optional and, in my view, unnecessary. This is a terminology collision assessment, not a trademark assessment. [Cursor 2.0 release](https://cursor.com/changelog/2-0).

**How the finalists compare.** I prioritize identifying the whole surface, distinguishing it from a pane and external editor, covering both launch and reusable-authoring work, and keeping the glossary inexpensive to learn. These are qualitative judgments, not measured scores.

| Candidate | Main advantage | Main cost |
| --- | --- | --- |
| Prompt Composer | Natural umbrella for assembling text, multiple segments, and metadata | Bare Composer collides with an external coding-model name |
| Prompt Editor | Immediately understandable; matches vim editing | Can mean one text area or the external editor; metadata/stack scope needs explanation |
| Prompt Workbench | Accommodates several coordinated editing tools | Sounds larger than the current widget and longer than needed |
| Prompt Studio | Broad authoring identity with room to grow | Suggests a full product or experimentation suite |
| Prompt Builder | Emphasizes assembly of reusable content | Can suggest a guided form or automatic prompt generator |
| Prompt Launchpad | Memorable and tied to agent starts | Weak description of macro editing, feedback, and save-only work |
| Prompt Canvas | Broad surface metaphor | Suggests spatial or graphical arrangement rather than ordered text panes |
| Prompt Loom | Concise, distinctive, loosely compatible with SASE's textile vocabulary | Requires teaching an otherwise unmotivated metaphor |

The practical language test favors *Prompt Composer*: “Open the prompt composer”; “Move the second pane up in the prompt stack”; “Edit the composer's frontmatter”; “Save the composer contents as a macro.” Each sentence identifies a different operation without needing additional invented nouns. *Composer stack* is unnecessary; *prompt stack* already says what is stacked. Likewise, *composition* need not become a new object type merely because the widget is a composer.

The glossary should describe stable relationships rather than reproduce the keybinding reference. One canonical term and the legacy aliases *prompt input widget* and *prompt input bar* are enough. Do not alias *prompt pane* or *prompt stack* to the parent: agents need those distinctions. The implementation anchor `PromptInputBar` belongs in the entry because it lets a future coding agent find the relevant code even before any symbol renaming. Choosing a user-facing name does not require renaming that class now.

My confidence is high that a functional, qualified name is better suited to this request than *Deck*, *Queue*, or a novel metaphor. Confidence in the ordering of *Composer* and *Editor* is moderate: the decisive preference is whether the term should emphasize assembling a complete prompt document or editing text. A preference for maximal literalness could reasonably move *Prompt Editor* to first place. No user-comprehension study was performed.

**Ranked names to consider:**

1. **Prompt Composer** — best balance of concise wording, whole-widget scope, and support for stacks, frontmatter, and reusable definitions. Recommended canonical name; *composer* works in established context.
2. **Prompt Editor** — strongest plain-language alternative, especially if immediate recognizability matters more than distinguishing the whole widget from its text area and external-editor path.
3. **Prompt Workbench** — best alternative if the coordinated toolset is the central identity; broader and heavier than the current need.
4. **Prompt Studio** — a polished authoring name, but implies more product scope than the widget currently needs.
5. **Prompt Builder** — understandable assembly language, with some risk of implying guided or automated generation.
6. **Prompt Launchpad** — the strongest launch-oriented metaphor; less suitable for editing and saving reusable definitions.
7. **Prompt Canvas** — flexible but gives the wrong spatial expectation for a vertical text stack.
8. **Prompt Loom** — the most appealing distinctive metaphor considered; its learning cost makes it a poor first choice for future-agent clarity.

**Recommended glossary entry for the #1 pick** — canonical keyword `prompt-composer`; aliases `prompt input widget`, `prompt input bar`:

> **Prompt Composer**
>
> A prompt composer is SASE's TUI surface for drafting, editing, and submitting prompts or saving reusable macros (`PromptInputBar` in code). It contains vim-style prompt panes and an optional frontmatter panel.
>
> Its **prompt stack** orders prompt panes top to bottom. Each pane holds a prompt segment, which may fan out into multiple agents. Panes can be reordered, submitted separately with shared frontmatter attached, or submitted together with `---` separators; their order alone creates no execution dependency. Auxiliary snippet and mini-macro panes edit definitions and are excluded from the launch payload.
>
> The **frontmatter panel**, also called the composer's properties panel, sits above the stack and edits YAML metadata, declared inputs, and local macros through structured fields or raw YAML. Ordinary prompt panes share the stack's frontmatter; when editing a mini-macro pane, the panel uses that macro's own scope. In NORMAL mode, `g=` opens or focuses the panel and `g-` adds a prompt pane; typing `---` does not itself split a pane during live editing.
