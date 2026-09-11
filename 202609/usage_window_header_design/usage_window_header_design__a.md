# Concise Usage-Window Indicators for the ACE TUI

## Executive conclusion

Usage windows belong in persistent application chrome because they affect provider choice before an agent is launched. They should not, however, compete with top-level navigation, model overrides, project state, and notifications on the same already-crowded row. The strongest layout is a single right-aligned usage cluster in the existing one-line application header, above the navigation/control row.

The best text grammar is one visually bounded group per provider, one provider icon per group, no parentheses, a middle dot between windows of the same provider, and a two-cell surface break between providers:

```text
🎭 62% 3d4h · fable 100% 1d8h  🤖 45% 2d5h  🛰️ 97% 1d7h
```

This keeps every existing icon and datum intact. It changes only placement, whitespace, and structural punctuation. It also aligns the visual hierarchy with the data hierarchy: percent and countdown form a window; windows form a provider group; provider groups form the global usage cluster.

## Scope and constraints

The decision is deliberately narrow. It does not reconsider:

- which windows are selected;
- provider or warning icons;
- colors, emphasis, or badge surfaces;
- the compact window names (`fable`, `5h`, `mo`, and so on);
- percentage or countdown formatting;
- attention ordering;
- tooltip content, click behavior, or the detailed Usage view.

The presentation must remain one terminal row high, glanceable during ordinary work, resilient across terminal widths, and explicit that multiple usage windows are independent constraints rather than pieces of one total.[^1]

## Current presentation audit

At the reviewed revision, ACE renders a standard one-line Textual `Header`, followed by a separate one-line `#top-bar`. The second row contains tabs and a sequence of ambient or actionable indicators: background work, updates, model and alias overrides, provider routing and usage, project, stashed prompts, and notifications. Usage is appended to the provider-routing widget, receives at most half the top-bar width, and degrades through complete-window prefixes, `+N`, `usage N`, `N`, and finally an ellipsis.[^2]

The current grouped form is:

```text
🎭 (62% 3d4h | fable 100% 1d8h)  🤖 45% 2d5h  🛰️ 97% 1d7h
```

It has several good foundations worth preserving:

- A provider icon appears once rather than once per window.
- The weekly all-model window is the unnamed anchor; exceptional windows carry compact names.
- Each window remains an indivisible unit under width pressure.
- A continuous badge surface groups a provider's icon and values.
- Full detail remains available through a tooltip and the Usage view.
- Text still communicates the quantities when colors cannot be distinguished, consistent with the principle that color must not be the sole carrier of information.[^3]

The dissatisfaction is therefore not a content problem. It is a hierarchy and placement problem.

### The punctuation hierarchy is reversed

The strongest explicit boundary, ` | `, currently appears *between windows that belong to the same provider*. Different providers receive only a two-space gap. The badge surface partly repairs that conflict, but the reader still encounters a table-like or shell-pipe boundary at the lower level and a weaker punctuation-free transition at the higher level.

This matters because visual grouping changes what viewers compare. Experimental and synthesis work in perception shows that common region and proximity are strong grouping cues and that grouping cues can direct which values are treated as a set.[^4][^5] A study specifically examining common region, proximity, and similarity found that cooperating cues strengthen grouping while competing cues weaken it.[^6] Applied here, the punctuation should cooperate with the already-present provider surface rather than cut across it.

### Parentheses duplicate the provider surface

Parentheses appear only when a provider has two or more visible windows. They therefore cause the shape of the same provider component to change as windows appear, disappear, or overflow. They also consume two cells and imply that the enclosed windows are an aside or qualification, even though each window is an independent capacity constraint.

The provider surface, icon, and proximity already establish common region. Parentheses add a fourth grouping signal without adding meaning. General usability guidance is apt here: every extra visual unit competes with the information that matters.[^7]

### The status cluster competes with navigation and routing controls

The current row mixes top-level navigation, selected-model context, routing overrides, ambient usage, project state, and notifications. At 140–160 columns the result is workable but visually dense. At 80 columns, the usage cluster collapses after one window; at 60 columns, it becomes `usage 3` while tabs and other controls are also squeezed.

The first application-header row, meanwhile, contains a left icon and centered application title with substantial unused space at ordinary widths. Textual defines `Header` as a top-docked application-title surface and already supports an optional clock on its right, so a trailing ambient readout fits the framework's own spatial idiom.[^8] Moving usage there separates global capacity state from navigation without adding a row.

## Design principles derived from the evidence

### 1. Persist, but stay peripheral

Provider capacity is actionable system state: it can change which provider or model should receive the next launch. Persistent visibility follows the visibility-of-system-status heuristic, which recommends timely, continuous feedback that helps users choose their next action.[^7]

Persistent does not mean visually dominant. VS Code's status-bar guidance is useful because it addresses the same kind of scarce horizontal chrome: use short labels, minimize icons and items, group the bar into stable regions, and keep secondary/contextual information on the trailing side.[^9] Although ACE is a TUI with a top rather than bottom status area, the information-density lesson transfers directly.

The usage windows should therefore be one composite header item, right aligned, with the existing urgency encoded inside it. They should not be split into unrelated widgets or given a dedicated row.

### 2. Make the provider the strongest visible group

The provider is the parent entity. All of its windows share the provider icon and current badge surface. The display should reinforce that relationship with uninterrupted surface and close spacing.

Different providers should be separated by a larger break in common region: two terminal cells styled with the existing gap surface. Apple’s layout guidance explicitly recognizes negative space, background shapes, colors, and separator lines as valid grouping tools, and warns against crowding essential information.[^10] Here, background plus whitespace is sufficient; a visible rule is unnecessary in the default design.

### 3. Use quiet punctuation only where a list truly exists

Multiple windows inside one provider are peers, so a middle dot is an appropriate list separator:

```text
🎭 62% 3d4h · fable 0% 1d8h · 5h 18% 2h9m
```

The dot is visible enough to prevent adjacent windows from merging, but it does not look like a pane boundary, table column, shell pipeline, or logical OR. It also allows the common provider surface to remain perceptually continuous. A plain comma was rejected because model lists can already contain commas; a slash was rejected because it can suggest a rate (`62%/3d4h`); parentheses and brackets were rejected because they add enclosure the surface already supplies.

### 4. Keep each window internally boring and stable

The existing internal order is good:

```text
[compact-name ] [! ] percentage countdown
```

The percentage answers “how much remains?” and the countdown answers “until reset.” Keeping them adjacent supports direct comparison without introducing a second internal separator. Adding `@`, `/`, arrows, or labels would either introduce a new icon, imply the wrong relationship, or add content outside the stated scope.

The visual system can only perform a handful of deliberate comparisons per second, and more complex relations demand serial processing.[^5] The indicator should therefore keep a repeated, predictable two-value rhythm rather than optimize individual tokens at the cost of a new grammar.

### 5. Preserve whole-window responsive disclosure

Truncating a percentage or countdown would be worse than hiding the whole window. The current complete-window prefix and `+N` disclosure are sound. Apple’s layout guidance likewise recommends indicating that additional items exist when a collection cannot be fully shown.[^10]

The placement change creates a cleaner width budget, but the fallback ladder should remain:

```text
full cluster
complete-window prefix  +N
usage N
N
…
```

The full tooltip must continue to disclose every selected and overflow window. This is particularly important when `+N` is shown and when stale, passed-reset, or unknown-reset states use neutral styling.

## Placement options

| Placement | Strengths | Weaknesses | Assessment |
|---|---|---|---|
| Existing navigation/control row | Near model and routing controls; no structural work | Most contested row; usage collapses early; mixes navigation, controls, and status | Acceptable fallback, not the best UX |
| Trailing side of existing app header | Always at the top; uses otherwise idle horizontal chrome; stable right edge; separates ambient status from navigation; adds no height | Requires a composed/custom header and collision budgeting around the title | **Best option** |
| New dedicated usage row | Maximum room and obvious grouping | Permanently costs one terminal row for secondary information | Reject |
| Footer | Conventional in some desktop tools | Violates the top-placement requirement and competes with ACE key hints and run state | Reject |

The header recommendation is not based on a claim that status must universally be top-right. VS Code, for example, uses a bottom bar.[^9] It follows from ACE's actual composition: the first row has spare capacity, the second does not, and Textual already treats the header's right side as a home for ambient information such as a clock.[^8]

### Header layout

At a wide width:

```text
?                    sase ace (v0.7.1)   🎭 62% 3d4h · fable 100% 1d8h  🤖 45% 2d5h
Agents | Artifacts | AXE                 CODEX(…)  routing  +sase  notifications
```

At a constrained width:

```text
?          sase ace (v0.7.1)                         🎭 62% 3d4h  +3
Agents | Artifacts | AXE                 CODEX(…)  +sase  notifications
```

The usage cluster grows leftward from a stable right edge. The title keeps its existing center preference, but the usage cluster receives only the cells that remain after reserving the title and left header affordance. This is the same kind of explicit budget already used in the current top bar, moved to a less contested surface.

## Formatting alternatives

The following comparison uses one representative state with four windows across three providers. Widths are terminal-cell widths measured with Rich `Text.cell_len`, the same metric used by the implementation; emoji count as two cells.

| Option | Rendering | Cells | Hierarchy | Verdict |
|---|---|---:|---|---|
| Current | `🎭 (62% 3d4h \| fable 100% 1d8h)  🤖 45% 2d5h  🛰️ 97% 1d7h` | 61 | Strong inner boundary, weak outer boundary | Reject |
| Repeat provider icon for every window | `🎭 62% 3d4h  🎭 fable 100% 1d8h  🤖 45% 2d5h  🛰️ 97% 1d7h` | 59 | Every window clear, provider grouping fragmented | Reject |
| Bracket every provider | `🎭 [62% 3d4h · fable 100% 1d8h]  🤖 [45% 2d5h]  🛰️ [97% 1d7h]` | 63 | Explicit, but redundant and widest | Reject |
| Dot within, thin bar between | `🎭 62% 3d4h · fable 100% 1d8h │ 🤖 45% 2d5h │ 🛰️ 97% 1d7h` | 59 | Correct separator hierarchy | Strong runner-up |
| Dot within, surface break between | `🎭 62% 3d4h · fable 100% 1d8h  🤖 45% 2d5h  🛰️ 97% 1d7h` | 57 | Correct hierarchy with least ink | **Recommend** |

The runner-up is useful as a contingency: if visual testing shows that the unchanged badge and gap surfaces collapse into one another in a supported terminal/theme combination, introduce a neutral ` │ ` *between providers only*. It should not be the default because it consumes two additional cells in the representative case and makes a quiet ambient strip look more like a table.

### Width effects in existing scenarios

| Scenario | Current | Recommended | Saving |
|---|---:|---:|---:|
| One provider, one window | 15 | 13 | 2 cells (13%) |
| One provider, three windows | 47 | 43 | 4 cells (9%) |
| Three providers, four windows | 61 | 57 | 4 cells (7%) |
| Two visible windows plus `+2` | 37 | 33 | 4 cells (11%) |

These are useful but not transformative savings. The major responsive improvement comes from moving the cluster into the header's available width. Punctuation cleanup then makes the result calmer and delays overflow slightly.

## Detailed presentation specification

### Grammar

```text
cluster  := provider-group ("  " provider-group)*
provider-group := provider-icon " " window (" · " window)*
window   := [compact-name " "] ["! "] percentage " " countdown
overflow := rendered-prefix "  " "+" hidden-window-count
```

The grammar describes plain text only. Existing styles remain attached as they are today:

- provider icon and values stay on the current provider badge surface;
- percentage/countdown color and emphasis remain unchanged;
- rejected, zero, stale, passed, and unknown states remain unchanged;
- the middle dot uses the current neutral divider style;
- the two-cell provider gap uses the current gap style;
- `+N` and fallback counts retain the current disclosure style.

### Padding

Remove the indicator renderer's owned two-cell leading and trailing padding. The header layout should provide a single-cell safety margin between the usage cluster and the title/right edge. This separates component layout from text grammar and saves two cells even in the single-window case.

### Examples

Single default window:

```text
🎭 62% 3d4h
```

Multiple windows, one provider:

```text
🎭 62% 3d4h · fable 0% 1d8h · 5h 18% 2h9m
```

Multiple providers:

```text
🎭 62% 3d4h · fable 100% 1d8h  🤖 45% 2d5h  🛰️ 97% 1d7h
```

Existing exceptional content, unchanged:

```text
🛰️ ! 4% 3d4h  🤖 ?% 0h0m↻  🎭 88% ?
```

Partial disclosure:

```text
🎭 62% 3d4h · fable 7% 1d8h  +2
```

Count fallback:

```text
usage 4
```

### Interaction

Keep the entire cluster as one click target opening the Usage view at the current attention-leading provider. Keep the full, ordered tooltip. This follows the “one status-bar item unless necessary” principle and avoids pretending that tiny subregions in terminal chrome are independent controls.[^9]

## Validation plan

The recommendation is evidence-informed design, not a substitute for observing use. Before declaring it final in code, validate the following:

1. Render the existing golden scenes at 60, 80, 120, 140, 160, and 240 columns in dark and light themes.
2. Add header-title collision cases with long application subtitles, if subtitles are supported in ACE.
3. Confirm that provider surfaces and two-cell gaps remain distinct in monochrome and low-color terminal profiles. W3C guidance is web-specific, but its core perceptual safeguard applies: the hierarchy must remain readable without hue discrimination.[^3]
4. Confirm that every responsive state preserves whole windows and that the final tooltip includes hidden windows.
5. Run a five-second glance test using the questions: “Which provider is constrained?”, “How much remains?”, and “When does it reset?” Compare current and recommended renderings without explaining the punctuation.
6. Watch for update jitter: the header's right edge should stay fixed while countdown text changes; only the left edge of the usage cluster should move.

Success should mean fewer hierarchy errors, no loss of displayed facts, later overflow at equivalent width, and no additional terminal height. If the provider boundary is missed in monochrome testing, adopt the thin-bar runner-up between providers while keeping the rest of the recommendation.

## Sources

[^1]: SASE project memory, “Usage Window,” audited project definition consulted September 11, 2026. A usage window is an independently identified provider-reported allowance; overlapping percentages must not be merged.

[^2]: SASE, [`_provider_usage_indicator.py`](https://github.com/sase-org/sase/blob/875447e2142f71dc04daeb49eab72c655c343be7/src/sase/ace/tui/widgets/_provider_usage_indicator.py), [`provider_disables_indicator.py`](https://github.com/sase-org/sase/blob/875447e2142f71dc04daeb49eab72c655c343be7/src/sase/ace/tui/widgets/provider_disables_indicator.py), [`_app_layout.py`](https://github.com/sase-org/sase/blob/875447e2142f71dc04daeb49eab72c655c343be7/src/sase/ace/tui/_app_layout.py), and visual snapshot tests, local checkout at commit `875447e2142f71dc04daeb49eab72c655c343be7`, September 11, 2026.

[^3]: W3C Web Accessibility Initiative. “[Understanding Success Criterion 1.4.1: Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html).” Updated September 16, 2025.

[^4]: Stephen E. Palmer. “[Common Region: A New Principle of Perceptual Grouping](https://doi.org/10.1016/0010-0285(92)90014-S).” *Cognitive Psychology* 24(3), July 1992, pp. 436–447.

[^5]: Steven L. Franconeri, Lace M. Padilla, Priti Shah, Jeffrey M. Zacks, and Jessica Hullman. “[The Science of Visual Data Communication: What Works](https://doi.org/10.1177/15291006211051956).” *Psychological Science in the Public Interest*, 2021.

[^6]: Dolores Luna and Pedro R. Montoro. “[Interactions Between Intrinsic Principles of Similarity and Proximity and Extrinsic Principle of Common Region in Visual Perception](https://doi.org/10.1068/p7086).” *Perception* 40(12), 2011.

[^7]: Jakob Nielsen. “[10 Usability Heuristics for User Interface Design](https://www.nngroup.com/articles/ten-usability-heuristics/).” Nielsen Norman Group, April 24, 1994; reviewed January 30, 2024. See “Visibility of System Status” and “Aesthetic and Minimalist Design.”

[^8]: Textualize. “[Header](https://textual.textualize.io/widgets/header/).” Textual documentation, September 19, 2023.

[^9]: Microsoft. “[Status Bar](https://code.visualstudio.com/api/ux-guidelines/status-bar).” Visual Studio Code Extension UX Guidelines, accessed September 11, 2026.

[^10]: Apple. “[Layout](https://developer.apple.com/design/human-interface-guidelines/layout).” Human Interface Guidelines, accessed September 11, 2026.

## Recommended solution

Move the usage-window cluster to the right side of ACE's existing one-line application header, above the navigation/control row. Render it as one composite item whose provider groups retain their existing badge surfaces and colors. Within a provider, show the provider icon once, omit parentheses, and separate windows with ` · `. Between providers, use the existing two-cell gap and surface break with no punctuation. Reduce owned outer padding from two cells per side to one layout-managed cell, preserve the current complete-window overflow ladder, tooltip, click target, ordering, icons, colors, and all displayed content, and reserve ` │ ` between providers only as a tested fallback for terminals where the unchanged surfaces do not separate clearly.
