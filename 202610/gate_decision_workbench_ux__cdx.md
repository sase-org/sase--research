# Gate-panel decisions: clipping diagnosis and a recommended TUI workbench

Researcher: cdx. Date: 2026-10-12. Independent report for the five-researcher swarm.

This investigation uses the supplied screenshot, the available SASE checkout, a small headless rendering experiment, and primary UX/framework documentation. No other report, transcript, summary, or finding from this swarm was consulted. This deliverable is design research; the application source was left unchanged.

**The recommended direction is a decision workspace with a stable index and a dedicated detail editor, beside the plan on wide terminals.** Use full-width Decisions/Plan tabs on narrower terminals. Pin the gate outcome controls across the bottom. This gives decisions a clear visual hierarchy and enough room for their full wording, while preserving fast keyboard review and access to the plan.

The screenshot's failure is more specific than “the sidebar is too small.” Long decision widgets can grow beyond the visible width of their container. The container then clips the text without a useful continuation cue. The expanded decision is also embedded in a Button label, so the question, alternatives, rationale, selected value, and default look like one large action. Fixing the width and wrapping is necessary; a better information structure is what makes the result pleasant to review.

**What the screenshot establishes.** The supplied image is `~/tmp/screenshots/20261012_074036.png`, 2048 × 1183 pixels. It shows a Plan Review modal with an Actions/Decisions/Verdict rail on the left and a large plan document on the right. The Decisions heading reports four decisions and zero memory decisions. The expanded first decision is `root = db`; subsequent visible summaries include `dotfiles = repoint` and `conflicts = delete`.

The question, choice descriptions, and rationale in the expanded decision visibly stop at the rail boundary. Collapsed questions do too. The focused first row has a large, bright reverse-video area, making prose look like a selected button. The decisions occupy only the upper portion of a tall rail, followed by a large blank area before the docked Verdict controls. A conspicuous scrollbar competes with the content. The bottom shortcut line contains many commands and wraps. These are separate problems of clipping, hierarchy, space allocation, and discoverability.

The screenshot header identifies version `v0.17.1+2434.g87c6468fd`. The inspected checkout reports HEAD `597931b222`, with Textual 8.0.1 and Rich 14.3.3 in its existing virtual environment. Those revisions differ. The experiment below establishes the failure mechanism in the available checkout; the screenshot provides the visual evidence from the user's running application. No original gate bundle was opened, so sample wording in the wireframes is illustrative rather than a reconstruction of obscured screenshot text.

**The code explains why the text can disappear.** Relevant source references below are paths in the primary SASE repository at the inspected revision:

| Source | Finding and design implication |
| --- | --- |
| `src/sase/ace/tui/modals/plan_decision_rows.py:122` | `_expanded_row_text` includes the full question, choices, rationale, default, and memory details. Expanded prose is present in the model/renderable before layout. |
| `src/sase/ace/tui/modals/plan_decision_rows.py:110` | Collapsed memory questions use a 60-character cutoff; other collapsed questions use 80. These thresholds do not reflect the actual visible terminal width. Container clipping can occur before the intended ellipsis. |
| `src/sase/ace/tui/modals/plan_decision_rows.py:326` | Every decision is one Button, carrying either the collapsed or expanded text. Additional detail Static widgets are composed, but refresh clears and hides them in both cases. |
| `src/sase/ace/tui/styles.tcss:1779` | A plan rail with decisions has a fixed width of 50 cells. |
| `src/sase/ace/tui/styles.tcss:1783` | The decision list has automatic height capped at 16 lines. Its Button rows have automatic height and left alignment, without an explicit width constraint in this rule. |
| `src/sase/ace/tui/modals/plan_approval_modal_view.py:277` | Actions, decision header/list, and docked Verdict are composed inside an outer VerticalScroll; the decision list itself is a VerticalScroll. This allows competing scroll regions. |
| `src/sase/ace/tui/styles.tcss:2190` | The narrow layout docks the rail at the bottom at 48% height. |
| `src/sase/ace/tui/modals/plan_approval_modal.py:70` | The current wide/narrow breakpoint is 100 columns. |
| `src/sase/ace/tui/modals/plan_approval_modal_controls.py:87` | Keyboard focus movement uses `focus(scroll_visible=False)`. The subsequent decision sync scrolls the plan document; decision visibility needs an explicit policy. |
| `src/sase/ace/tui/modals/plan_approval_footer.py` | The footer assembles a long global list of navigation, editing, submission, input, copying, debug, and scrolling hints. |
| `src/sase/ace/tui/modals/notification_modal_gate.py:370` | The gate notification's Decisions block is a different, summary-oriented renderer. It currently emphasizes decision IDs and values. The redesign should cover that surface's summaries as well as the approval editor. |

The width and height constraints reinforce each other. A large terminal keeps the same 50-cell decision rail. A tall terminal keeps the same 16-line decision-list cap. Increasing terminal size therefore does little for the decision text, even when unused space is available.

**A rendering experiment confirms intrinsic-width overflow.** I mounted the existing PlanApprovalModal with the application's actual stylesheet in Textual's headless test app. A synthetic `root` choice contained a long question, two long option descriptions, and a long rationale; three additional toggle decisions gave the list four rows. Unique end markers were appended to each long field.

I compared the Button's geometry with the intersection of its region, the decision viewport, and the rail's content region. Inspecting the label string alone would miss the problem: it still contains every marker.

| Terminal size, columns × rows | Rail width | Expanded Button width | Visible intersection width | Decision viewport height | Long-field end markers visible |
| --- | ---: | ---: | ---: | ---: | --- |
| 90 × 40 | 84 | 109 | 78 | 16 | 0 of 4 |
| 120 × 40 | 50 | 109 | 44 | 16 | 0 of 4 |
| 240 × 70 | 50 | 109 | 44 | 16 | 0 of 4 |

The synthetic list's virtual height was 21 rows in all three baseline cases. The expanded first Button occupied nine rows. At 120 columns, its visible question ended at “Where should the relocated legacy tree live”; the rest existed outside the viewport. The other long fields were similarly clipped.

In a temporary, in-memory CSS experiment, setting the expanded Button to `width: 100%` and `text-wrap: wrap` produced a 42-cell-wide, 17-row-tall widget in the wide layouts. Its question and descriptions wrapped, and all four field-end markers appeared within the inspected crop. At 90 columns the widget became 76 cells wide and 13 rows tall, but the bottom of the content remained outside the available visible area. This demonstrates why a width repair helps and why it still needs deliberate vertical scrolling and layout.

The measurements concern synthetic content and widget/viewport geometry. They are not a complete visual evaluation of a proposed replacement. No production gate was answered, modified, or executed during the experiment.

A compact reproduction of the baseline experiment, run from the primary checkout with its existing `.venv/bin/python`, is:

~~~python
import asyncio
from pathlib import Path

from textual.app import App
from textual.geometry import Region
from textual.widgets import Button
from sase.ace.tui.modals.plan_approval_modal import PlanApprovalModal

class StyledApp(App):
    CSS_PATH = Path.cwd() / "src/sase/ace/tui/styles.tcss"
    ENABLE_COMMAND_PALETTE = False

root = {
    "id": "root", "kind": "choice", "default": "db",
    "ask": "Where should the relocated legacy tree live after "
           "the migration finishes? QUESTION_END",
    "choices": [
        {"key": "db", "label": "~/db: matches the existing database "
         "root and shell history convention DB_LABEL_END"},
        {"key": "legacy", "label": "~/legacy: makes the preserved "
         "archival tree explicit without changing content LEGACY_LABEL_END"},
    ],
    "why": "~/.profile already calls this root $DB, so using db avoids "
           "changes to existing startup scripts. WHY_END",
}
definitions = [root] + [
    {"id": name, "kind": "toggle", "default": False,
     "ask": f"Should the migration perform the operation {name} "
            "with its complete consequences?"}
    for name in ("dotfiles", "conflicts", "old_tmp")
]

async def main():
    for size in ((90, 40), (120, 40), (240, 70)):
        modal = PlanApprovalModal(
            "synthetic-plan.md", plan_content="# Synthetic plan\n",
            default_choice="tale", decision_definitions=definitions,
            request_id=f"independent-cdx-wrap-{size}",
        )
        async with StyledApp().run_test(size=size) as pilot:
            pilot.app.push_screen(modal)
            await pilot.pause()
            await pilot.pause()
            button = modal.query_one("#plan-decision-0", Button)
            rows = modal.query_one("#plan-decision-rows")
            rail = modal.query_one(".gate-review-actions")
            visible = (
                button.region.intersection(rows.content_region)
                .intersection(rail.content_region)
            )
            crop = Region(
                visible.x - button.region.x,
                visible.y - button.region.y,
                visible.width, visible.height,
            )
            text = "\n".join(s.text for s in button.render_lines(crop))
            print(size, rail.region.width, button.region.width,
                  visible.width, rows.region.height,
                  {m: m in text for m in (
                      "QUESTION_END", "DB_LABEL_END",
                      "LEGACY_LABEL_END", "WHY_END",
                  )})

asyncio.run(main())
~~~

**Useful external design evidence supports separating overview, editing, and explanation.** The sources below inform the recommendation; adapting a web design pattern to a terminal remains a design judgment.

GOV.UK's radios guidance groups a question with mutually exclusive alternatives and shows option-specific explanatory hints. It also cautions against preselected answers because users may miss a question. SASE already has meaningful effective defaults, so removing all preselection would change its workflow. The useful adaptation is to expose “Default” explicitly and distinguish it from a deliberate change. Preserve authored option order rather than importing the guidance's general alphabetical ordering rule. [GOV.UK radios](https://design-system.service.gov.uk/components/radios/)

GOV.UK cautions that accordions hide content, advises against hiding material everyone needs, and discourages using them to divide a sequence of questions. That weighs against making the answerable question and alternative consequences depend on noticing an accordion affordance. A compact index can still support navigation, provided the selected decision's complete content is plainly displayed in a dedicated editor. [GOV.UK accordion guidance](https://design-system.service.gov.uk/components/accordion/)

Nielsen Norman Group distinguishes progressive disclosure of secondary features from staged, sequential task steps. It warns that staged disclosure becomes awkward when users must move back and forth between interdependent steps. SASE decisions can affect multiple parts of a plan; a mandatory wizard would create unnecessary navigation. Keep alternatives and their relevant consequences visible in the editor; reserve disclosure for longer supporting evidence or optional tools. [NN/G progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/)

Textual provides the necessary building blocks: OptionList supports Rich-renderable options; RadioSet groups exclusive radio choices. These can support a compact index and an actual choice editor. Their defaults still require a styling and key-routing audit with the installed version. [Textual OptionList](https://textual.textualize.io/widgets/option_list/), [Textual RadioSet](https://textual.textualize.io/widgets/radioset/)

Textual documents word wrapping separately from overflow treatment. `text-overflow: fold` can break an oversized word across lines, which is useful for paths, URLs, and identifiers. `ellipsis` is useful for an overview whose complete text is readily available. The full decision editor needs wrapping and folding, plus content-driven height; an overview can use deliberate ellipsis. Rich likewise exposes wrapping and overflow controls. [Textual text-wrap](https://textual.textualize.io/styles/text_wrap/), [Textual text-overflow](https://textual.textualize.io/styles/text_overflow/), [Rich Text](https://rich.readthedocs.io/en/latest/reference/text.html)

Textual's automatic height fits content, while fractional sizing distributes remaining space. A stable scrollbar gutter reserves space so the layout does not change when scrolling becomes necessary. These are appropriate primitives for an editor that fills available height and contains naturally sized prose. [Textual height](https://textual.textualize.io/styles/height/), [Textual scrollbar gutter](https://textual.textualize.io/styles/scrollbar_gutter/)

W3C's radio pattern distinguishes group navigation and checking an option. Its toolbar variant explicitly permits navigation without changing the checked value. This is a useful interaction reference when deciding which SASE movements should browse versus edit. Web ARIA semantics do not establish terminal accessibility support; terminal behavior still requires direct testing. [W3C radio group pattern](https://www.w3.org/WAI/ARIA/apg/patterns/radio/)

**The main alternatives have different costs.**

| Candidate | Strength | Limitation | Assessment |
| --- | --- | --- | --- |
| Width/wrap repair in the existing accordion | Smallest change; improves immediate clipping | Long rows still consume the 16-line area, change size on focus, and look like large buttons | Suitable first repair |
| Improved accordion with separate prose and controls | Familiar layout; less widget replacement | Expanding a decision still moves other rows and competes with the rail's actions/verdict | Good fallback for a deliberately small scope |
| All decisions expanded in a scrolling form beside the plan | Every question and option is directly present | Long descriptions and memory evidence can produce a very long form; distant decisions become harder to compare | Strong for one or two short decisions |
| Stable index plus detail editor beside the plan | Predictable navigation, dedicated reading space, scales to long descriptions and many decisions | Requires clear focus regions and a short-height adaptation | Recommended |
| Decision editor only in a popup | Plenty of room on demand | Adds repeated entry/exit steps and hides the decision from the review overview | Optional expanded view |
| Mandatory one-decision-at-a-time wizard | Very simple individual step | Makes plan consultation and revisiting interdependent choices cumbersome | Poor fit |
| Three columns: index, editor, plan | All roles have separate space | Splits typical terminals too finely | Avoid as the default |

The recommendation uses two columns, with the index and editor stacked inside the decision column. It does not require a third narrow column or an overlay for routine reading.

**The proposed wide layout has four clear regions.** Put a modest header and utility actions at the top. The Decisions pane contains a compact index, then the complete active decision. The Plan pane remains alongside it. A full-width outcome bar stays outside every scroll container.

The following wireframe illustrates the information hierarchy. Text lengths and sample values are representative.

~~~text
┌─ Plan Review · CLAUDE(opus) ────────────────────────────────────────────────────┐
│ [Edit plan]                                   [Plan] [Decisions] [Help]         │
├─ Decisions · 4 · 1 changed ───────────────────────┬─ plan.md ────────────────────┤
│ > root          db             Default           │ ## 3. Relocate the tree     │
│   dotfiles      repoint        Default           │                             │
│   conflicts     keep           Changed           │ The relocation uses the     │
│   old_tmp       nest           Default           │ selected destination.       │
│                                                  │                             │
│ root · decision 1 of 4                            │ Active decision: root       │
│ Where should the relocated legacy tree live?      │ Selected value: db          │
│                                                  │                             │
│ ● db                         Default             │ ... plan content ...        │
│   ~/db: matches the existing $DB convention       │                             │
│                                                  │                             │
│ ○ legacy                                         │                             │
│   ~/legacy: makes the archival tree explicit      │                             │
│                                                  │                             │
│ Why this default                                 │                             │
│ ~/.profile already calls this root $DB.           │                             │
│ Using db keeps that convention.                   │                             │
│                                                  │                             │
│ [Reset to default]  [Show in plan]                │                             │
├──────────────────────────────────────────────────┴─────────────────────────────┤
│ [x] Launch coder  [x] Commit plan       4 decisions · 1 changed                  │
│ [Approve: Tale]       [Reject]       [Feedback]                Ctrl+S: submit    │
│ j/k: decision  h/l: change  Tab: region  Enter: edit  ?: help                    │
└────────────────────────────────────────────────────────────────────────────────┘
~~~

Use the entire available body height. A large blank gap beneath a tiny fixed-height decision area should disappear naturally. On wide screens, a starting decision-pane width of roughly 45% of the body, clamped to 64–88 cells and constrained by the plan's minimum readable width, gives prose room without turning it into excessively long lines. The exact sizing is a prototype parameter.

The index should be one or two stable lines per decision. Show the decision ID or an existing human label, current value, and the word “Default” or “Changed.” A second line can give a short question preview. Preserve author order. A plain focus indicator such as `>` or a thin cyan leading bar denotes the active decision. Reserve radio marks for actual choices, so focusing one decision cannot look like choosing it instead of the others.

For the four-decision example, the index can show all four decisions in a modest area. For larger sets, make it a bounded sibling scroll region, approximately 6–10 lines depending on terminal height. Allocate the remainder to the editor. The whole decision column should not itself be another scroll container.

The active editor shows, in order:

1. Decision ID and position, such as “root · decision 1 of 4.”
2. The complete question in normal foreground text.
3. Every alternative, with a selection mark, its key or label, and its full authored description beneath it.
4. “Why this default” followed by the complete rationale, when one exists.
5. Default/changed status, reset, and a route to relevant plan context.
6. Memory target, provenance, and supporting evidence for memory decisions.

All option descriptions should remain visible in the active editor. A reviewer comparing alternatives should not have to select one just to learn what it means. Longer supporting evidence may use a single explicit “Details” disclosure, while the actual question, alternatives, important warnings, and default rationale stay visible.

A toggle should use one checkbox with a meaningful action label, or an exclusive Yes/No radio group when both outcomes need explanations. The existing expanded builder renders two checkbox-like Yes/No lines; using two apparent independent checkboxes for one binary answer makes the semantics harder to read.

**A small styling vocabulary will improve appearance more than decoration.** Keep one understated border per major pane, a separator between index and editor, and one separator above the outcome controls. Avoid a full bordered card around every short index row. Use normal foreground for questions and option descriptions; dim text should be reserved for metadata. The screenshot's heavily dimmed descriptions are information the user needs to make the decision.

A focused row should have a restrained background tint and leading marker. A chosen alternative uses its radio/checkbox mark and modest bold text. A default uses the explicit “Default” label. A changed value uses “Changed” with a small gold accent. A verification warning uses an amber marker and words. These represent different states and should remain distinguishable in monochrome.

Keep emoji optional, rather than placing them in every repeated row. Render an empty memory count unobtrusively or omit it. A nonzero count can read “2 memory changes” instead of relying on a brain icon's meaning. Test both Unicode and ASCII marks with the actual terminal/font stack. Do not measure layout by Python character count: display cells, combining characters, and emoji can differ.

Descriptions and long identifiers must wrap to their actual content box. Oversized paths can fold across display lines while retaining their exact source value for copy and submission. Reserve explicit ellipsis for compact previews; the editor must provide the complete content. A mouse-only tooltip is insufficient as the sole way to recover clipped text.

**The responsive layout should protect reading space.** Begin prototyping a split layout around 140 columns, based on needing roughly 56 content cells for decisions, 64 for plan context, and the borders/padding/gap. Switch based on the actual available body width. This threshold is a proposed starting point, not a measured optimum.

| Available terminal space | Proposed behavior |
| --- | --- |
| At least about 140 columns and 32 rows | Decisions index/editor beside the plan; both get useful reading width |
| Approximately 80–139 columns | Full-width Decisions/Plan tabs; retain the outcome controls below |
| Below about 30 rows | Replace the persistent multirow index with a compact current-decision navigator and “All decisions” picker; keep the editor usable |
| Very small windows | Prioritize full-width content and reachable controls; allow vertical scrolling rather than squeezing two panes into unreadable areas |

In tabbed mode, open Decisions when the gate has decisions, and expose the Plan tab beside it. Gates without decisions can open Plan. Switching views must preserve draft values, active decision ID, focus context, and independent scroll positions. Resizing from split to tabs and back should preserve those same identities.

A compact example:

~~~text
┌─ Plan Review ────────────────────────────────────────────┐
│ [Decisions 4] [Plan]                         [Edit] [?]    │
│ root · 1 of 4 · db · Default          [All decisions]    │
├─────────────────────────────────────────────────────────┤
│ Where should the relocated legacy tree live?            │
│                                                         │
│ ● db · Default                                          │
│   ~/db: matches the existing $DB convention              │
│ ○ legacy                                                │
│   ~/legacy: makes the archival tree explicit             │
│                                                         │
│ Why this default                                        │
│ ~/.profile already calls this root $DB.                  │
│                                                         │
│ [Reset] [Show in plan]                                   │
├─────────────────────────────────────────────────────────┤
│ Launch coder + commit plan · 4 decisions · 0 changed     │
│ [Approve: Tale] [Reject] [Feedback]    Ctrl+S: submit      │
│ j/k: decision  h/l: change  Enter: edit  ?: help          │
└─────────────────────────────────────────────────────────┘
~~~

At 80 × 24, use the compact navigator even when wider layouts show the full index. The outcome bar can reflow into short, stable rows. “Show in plan” activates the Plan tab and relevant context; returning to Decisions restores the editor. This is preferable to the current small-window arrangement that permanently divides vertical space between the plan and controls.

**Keyboard behavior must distinguish browsing, editing, and executing the gate.** The existing SASE map uses j/k for controls, h/l or left/right for changing choices, Space for toggling, Enter for primary submission, Ctrl+S for branch submission, and r/R for resets. Gate bindings are currently generated with `priority=True` in `src/sase/ace/tui/keymaps/bindings.py:134`.

Textual RadioSet itself uses Enter/Space to activate a choice and arrow keys to move among choices. Dropping RadioSet into the existing modal without changing routing could leave a form-looking control where Enter executes the whole gate. This needs a deliberate UX decision and focused interaction tests. [Textual RadioSet bindings](https://textual.textualize.io/widgets/radioset/)

My preferred interaction is:

| Focus region | Input | Result |
| --- | --- | --- |
| Decision index or compact navigator | j/k, or Up/Down | Focus previous/next decision; show its editor; do not change its answer |
| Decision index | h/l, or Left/Right | Change the current decision's answer as a fast expert shortcut |
| Decision index | Enter | Enter the active decision editor |
| Choice editor | Up/Down | Move the option highlight |
| Choice editor | Space or Enter | Choose the highlighted option; remain in review |
| Toggle editor | Space | Toggle the displayed answer |
| Any region | Tab / Shift+Tab | Move through available regions in a predictable order |
| Decision region | r | Reset the active decision to its effective default |
| Decision region | R | Reset all decisions; update visible state and changed count |
| Focused content | PageUp/PageDown or Ctrl+U/Ctrl+D | Scroll that content region |
| Outcome controls | Enter | Execute the explicitly focused outcome |
| Any region | Ctrl+S | Submit the active branch with the displayed answers |
| Any region | Escape or q | Leave review without submitting; preserve the existing draft behavior |

This intentionally changes Enter from universal primary submission to context-sensitive activation. It is a tradeoff: routine choice editing becomes conventional, while the globally available fast submission moves to the already familiar Ctrl+S. The footer must describe the effective behavior for the current focus. If preserving universal Enter is a product requirement, make it an explicitly labeled mode and give decision editing another activation key; avoid letting widget defaults decide.

Existing numbered gate-branch shortcuts can remain when shown accurately. Do not simultaneously assign the same global digits to local choice selection. New region/view/help shortcuts need collision checks against declared gate actions and the configurable map.

Mouse interactions should be equally direct. Clicking an index row focuses it without changing its value. Clicking an alternative or its description selects that alternative. Wheel scrolling affects the pane beneath the pointer. Controls should not move as a side effect of changing a selection.

Keep the footer short and contextual: four or five relevant hints, plus Help. Put copying, debug, coder options, reset-all, and other less frequent commands in the help view or their explicit utility controls. The visible submit command should always show the actual outcome. Do not require another confirmation modal for ordinary submission.

**Defaults, memory decisions, and plan context need accurate state.** A default is an existing answer the gate will submit, not proof that the user reviewed it. Display “4 decisions · 1 changed,” using the effective-default comparison already supplied by the decision sheet. “Decision 2 of 4” can identify navigation position. Avoid inventing an “answered” or “reviewed” completion counter from nonempty values or from focus visits.

For a memory decision, keep its target and operation near the question. Show the actual provenance label and any verification warning plainly. An unverified quote/claim that makes the effective default Off must remain Off until the reviewer changes it. Explain that state in words. Show the authored recommendation separately only when it differs from the effective default. Reset returns to the effective default. Longer quoted evidence can be lower in the editor, but the warning and its effect must be visible without expanding evidence.

For a selected nondefault value, keep “Default: db” visible in the editor even when “legacy” is selected. Reset should immediately restore the value and remove the Changed state. Choosing the original default again should also remove Changed; track current differences rather than historical edit activity.

The current view already caches decision callout spans and tints the plan based on draft values. Preserve that useful behavior. Highlight a matching decision callout and provide “Show in plan.” Avoid scrolling the document merely because the reviewer is moving quickly through the index. Use an explicit jump or a visible “Follow decision” option; the user's manually chosen plan scroll position should remain stable by default.

When a decision has no matching callout, keep the document in place and explain that context is unavailable. When it has multiple matches, expose the count and a way to move between them. This should be based on cached spans, without reparsing or reading files on keypress.

The pending gate notification can use the same vocabulary: ID/human label, current value, Default/Changed, and a readable summary. Opening it leads to the editor. For a settled gate, show submitted values and settlement status in a read-only decision detail view. If the gate settles elsewhere while being reviewed, keep the draft visible with the settlement banner and block submission through the existing mechanism.

**A practical implementation can stay mostly within presentation code.** Consume the existing decision definitions, sheet rows, draft state, effective defaults, and gate result protocol. The current data already supplies question, choice key/label, why, value/default, changed state, and memory metadata. The initial redesign does not require new authoring fields.

Introduce a reusable DecisionsPane composed of a compact index and one DecisionEditor. Keep presentation and focus in the Textual layer. Use naturally sized Static/Label text for prose and actual controls for choices; a custom focusable choice row is reasonable if native labels do not meet wrapping requirements. Constrain every child to the parent's actual width, with suitable minimum-width overrides. Treat code suggestions as prototype guidance that needs testing in Textual 8.0.1.

The relevant file-level work would be:

- Replace the large-label decision Buttons in `plan_decision_rows.py` with an index/editor composition.
- Recompose `plan_approval_modal_view.py` around the decision workspace, document, and full-width outcome bar.
- Adjust `styles.tcss` for flexible width, available-height allocation, restrained focus, and tabs/short-height modes.
- Update `plan_approval_modal_controls.py` for explicit region focus, selected-row visibility, scoped keys, and context navigation.
- Make `plan_approval_footer.py` render contextual hints and accurate action labels.
- Align `notification_modal_gate.py` summaries with the same state vocabulary.
- Update the keymap definitions, binding routing, and `src/sase/default_config.yml` together if the recommended interaction changes are adopted.

The shared backend/domain boundary remains in Rust `sase_core`. Validation, default computation, provenance policy, frozen definitions, and submitted decision maps should keep using their existing core/binding paths. Any future schema changes, cross-client review-state semantics, or new domain rules would need the linked sase-core workflow and revision pin. Styling and pane arrangement do not require such a schema change.

Avoid adding I/O, subprocesses, validation, or plan parsing to selection handlers. Update the changed index row, active editor, count/summary, and cached document tint selectively. If context loading becomes slow, use the established detail-panel debouncing approach without delaying the focus highlight. Programmatic widget updates must suppress queued selection echoes correctly. These constraints follow the project's audited `tui_perf.md` guidance.

A useful delivery sequence is an immediate width/wrap/visibility repair, followed by the index/editor layout and responsive behavior, then aligned summaries and refined styling. The intermediate repair should remain small enough that the finished layout can reuse its overflow guarantees. This is a sequence recommendation, not a filed implementation plan.

**Acceptance should prove readable decisions and predictable interaction.** Existing render coverage in `tests/ace/tui/test_plan_decision_ace_render.py` checks layout geometry, exact rail widths, and that Verdict buttons fit. Those assertions do not establish that full decision text can be reached. A geometry-valid rail can still clip a child.

Use realistic frozen-definition fixtures and check the actual rendered content at narrow, normal, and wide sizes. Include 80 × 24, 90 × 40, 120 × 40, 140 × 40, and 240 × 70, plus both sides of the chosen breakpoint.

| Scenario | Pass condition |
| --- | --- |
| Long question, option description, rationale | Each complete field is reachable by ordinary vertical scrolling; no horizontal clipping or hidden semantic truncation |
| Long unbroken path/URL, CJK, combining characters, emoji | Text folds safely within the viewport; original values remain exact |
| Four decisions matching the screenshot's complexity | Questions/options are easy to find; the editor uses spare height; the fourth decision is keyboard-reachable |
| Twenty decisions | The index scrolls independently and retains the active row; editor and outcome controls remain usable |
| Short terminal | Compact navigator and full-width content retain meaningful reading space |
| Browsing decisions/options | Navigation alone leaves answers unchanged except for explicitly documented change shortcuts |
| Choosing or resetting an answer | Index, editor, default/changed labels, count, and submitted map agree |
| Enter in an option editor | Selects the option without answering the whole gate in the preferred interaction mode |
| Submit | Executes the displayed branch exactly once with the chosen decision inputs |
| Resize and tab/view changes | Values, focused decision identity, and relevant scroll positions survive |
| Escape and reopen | Existing draft restoration works |
| Unverified memory evidence | Warning is visible, effective default stays Off, reset returns to Off |
| Settlement elsewhere | State remains understandable and submission is disabled |
| No decisions | The review remains compact and opens the plan normally |

Add tests for both plain rendering and the real stylesheet. Assert field-tail visibility across a deliberate scroll traversal, alongside screenshots; a string in a label or SVG source alone can still be outside the viewport. Verify mouse option selection as well as keyboard paths.

For visual validation, use the project's real `sase screenshot` workflow and inspect the PNG. Maintain targeted golden coverage through the prescribed visual workflow, reading its retained report and inspecting actual differences. Confirm the running TUI version because an already-running process can still be executing its imported older code. No snapshot files were changed for this research.

For UX validation, compare the width-only repair and the proposed workspace using the same four decisions. Ask the reviewer to explain each question and alternative, change the destination, identify the default, reset one value, find the relevant plan step, and submit the intended outcome. Observe missed options, accidental submissions, repeated pane switching, and confusion between focus and chosen state. Exact widths and breakpoint values should be tuned from this comparison, not accepted solely because the wireframe looks balanced.

**Recommended solution and UX.** Build a two-pane plan review workbench: a stable decision index and a fully wrapped choice editor in the left pane, the plan in the right pane, and explicit outcome controls pinned below both. Use full-width Decisions/Plan tabs on smaller terminals and a compact navigator on short terminals. Give questions, alternatives, rationale, and verification warnings complete, scrollable presentation; use restrained focus styling and explicit Default/Changed labels. Keep j/k browsing, h/l fast changes, direct mouse selection, reset, draft restoration, and a clear Ctrl+S submission route. Make Enter edit/select within decisions and execute only the focused outcome control. The resulting review should let the user understand every decision, compare its alternatives, see how it affects the plan, and submit the displayed result without text disappearing or controls moving around.
