**Usage windows: a concise, persistent header design**

Research synthesis · September 11, 2026

Put usage at the right of the existing application header, move the existing title to the left, and simplify the cluster to one icon per provider, middle dots between that provider's windows, and two spaces between providers. Remove parentheses and halve outer padding. This gives the indicators more room, reduces punctuation, and prevents their changing width from moving unrelated controls. Preserve the current colors, icons, value strings, warning treatments, and attention ordering.

```text
🎭 62% 3d4h · fable 100% 1d8h  🤖 45% 2d5h  🛰️ 97% 1d7h
```

The mockups show text structure; the implementation retains the existing provider backgrounds and styled spans. This recommendation is supported by code inspection, width measurements, existing screenshots, and design literature. None of the three researchers conducted a user study establishing a fastest or universally preferred presentation.

**Evidence and provenance.** The two inputs were matched by dependency identity and their canonical suffixes, independently of list order:

| Input | Dependency | Original canonical research reference | Preserved report |
|---|---|---|---|
| A | `research.1u.cdx` | `research:202609/concise_usage_window_indicator_ux__a.md` | [Researcher A](usage_window_header_design__a.md) |
| B | `research.1u.cld` | `research:202609/usage_window_indicator_presentation__b.md` | [Researcher B](usage_window_header_design__b.md) |

Both reports were consumed using `sase artifact read`. Their immutable snapshot references remain `file:explicit:3e24903474eee1dd8c47c375` and `file:explicit:63c7dd84e7e19fde6bb65060`. Only the copies in this research checkout were moved; their SHA-256 digests remain `674fbf2ce63f0dacd0ba0f8850f97638e3dfd534451f6dec8bb4579466ac8506` and `ea4a40255e6d92ba7d04794b8f29a789e2b242ebbef2427276c56b46128676b6`. No predecessor transcripts were used.

My independent review used SASE commit `875447e2142f71dc04daeb49eab72c655c343be7`, its committed visual fixtures, and its actual formatter/renderer with Rich 15.0.0 and Textual 8.2.8. The audited Usage Window glossary establishes that windows are independent, potentially overlapping allowances: their percentages must not be combined, and window duration is distinct from time until reset.

**What the current display gets right—and where presentation gets in the way.** The renderer already keeps each window intact, groups windows beneath a shared provider icon, preserves exceptional states, and discloses hidden windows through `+N` and the detailed view. Those are valuable constraints to retain. Its conditional parentheses add two cells only when multiple windows fit, so the same group changes enclosure as the terminal narrows. The inner ` | ` separators attract attention even though provider ownership is the more important grouping. These findings are directly visible in the [renderer](https://github.com/sase-org/sase/blob/875447e2142f71dc04daeb49eab72c655c343be7/src/sase/ace/tui/widgets/_provider_usage_indicator.py).

Placement has the larger practical cost. Usage shares a widget with provider routing and shares a row with tabs, model overrides, project state, and notifications. Its budget is capped at half that row, and can be smaller after accounting for siblings. The header above already occupies one row. Moving usage into that existing space costs no additional height. See the [widget budget](https://github.com/sase-org/sase/blob/875447e2142f71dc04daeb49eab72c655c343be7/src/sase/ace/tui/widgets/provider_disables_indicator.py) and [application composition](https://github.com/sase-org/sase/blob/875447e2142f71dc04daeb49eab72c655c343be7/src/sase/ace/tui/_app_layout.py).

I inspected the committed 80-column overflow screenshot: usage, `+3`, and `+sase` crowd the control row while the title row has unused room. The 140-column real-projection screenshot contains three weekly readouts; it does **not** itself substantiate the four-window example used in both reports. The four-window measurements below therefore come from an explicit synthetic input to the real renderer, not that screenshot.

**How the evidence resolves the disagreements.** Common-region research supports treating each provider background as an enclosure; it does not prove that a particular separator is optimal. NN/G also cautions that unnecessary borders add clutter. My inference is that removing parentheses is well supported, while choosing dots over whitespace remains a design judgment worth checking with the user. A dot preserves an explicit boundary between independent windows for only one cell more than a two-space separator. It is useful when labels vary or several values have the same color. [NN/G: Common Region](https://www.nngroup.com/articles/common-region/)

Persistent capacity feedback supports choosing the next action, while unnecessary decoration competes with the values. Those general usability principles support a small, always-visible cluster. They do not establish a universal top-right convention. [Nielsen's usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)

| Decision | A | B | Consolidated judgment |
|---|---|---|---|
| Placement | Right side of existing header | First status item after tabs | Use the existing header; isolate usage from the crowded control row. |
| Provider enclosure | Existing background; no parentheses | Existing background; no punctuation | Keep the background and remove parentheses. |
| Window boundary | ` · ` | Two spaces, shrinking to one | Keep the dot: its small cost buys an explicit boundary even in dense groups. |
| Numeric alignment | Natural token widths | Four-cell percentages, five-cell countdowns | Use natural widths initially; the proposed countdown bound is incorrect and padding is costly. |
| Emphasis | Preserve existing styles | Bold only percentages; narrow the zero alarm | Preserve existing spans. Changing the extent of the inverted zero treatment would alter displayed foreground/background assignments. |
| Ordering | Preserve attention order | Stable order, urgency-based selection | Preserve existing ordering and prefix selection; changing their relationship affects which facts survive overflow and what clicking opens. |
| Width pressure | Whole windows plus existing fallback | Three spacing tiers, then fallback | Reduce fixed padding once, then retain whole-window disclosure. Avoid introducing a second changing layout grammar. |

B's strongest additional finding is that variable-width usage can move unrelated widgets to its left. Moving it to the first slot after the tabs limits that effect, but the other widgets are themselves dynamic: it cannot make usage the only item that ever moves. Header isolation addresses the causal problem more directly. It also separates usage overflow from the project chip and gives usage its own interaction area.

Microsoft's status-bar guidance supports concise labels and restrained contributions. It actually places global status on the **left**, so it should not be cited as evidence that global usage belongs on the right. The right-side recommendation here follows from SASE's available header space. Textual's Header is top-docked and already supports a right-side clock, establishing feasibility rather than a user-preference result. [VS Code status-bar guidance](https://code.visualstudio.com/api/ux-guidelines/status-bar), [Textual Header](https://textual.textualize.io/widgets/header/)

**Independent measurement corrections.** B's five-cell countdown field would overflow routinely, not for about a minute a day. Running the current formatter for each positive whole minute below one day produced 700 six-cell strings among 1,439 samples, including `10h10m` and `23h59m`. The passed-reset string `0h0m↻` is five cells. Six cells cover ordinary sub-day and weekly countdowns; longer durations can exceed even that (`100d10h` is seven). Fixed-width fields therefore need an explicit policy and cannot promise unconditional stability. [Current formatter](https://github.com/sase-org/sase/blob/875447e2142f71dc04daeb49eab72c655c343be7/src/sase/ace/tui/widgets/_usage_indicator_format.py)

B also reports that Rich counts the Grok and Muse icons as one cell. That does not reproduce in the installed environment: `Text(icon).cell_len` returns two for `🎭`, `🤖`, `🛰️`, and `♾️`. Do not introduce a blanket variation-selector width override on this evidence. Terminal width behavior still needs testing in supported terminals; Unicode explicitly warns that East Asian Width is not a complete terminal-layout solution. [Unicode UAX #11](https://www.unicode.org/reports/tr11/)

For the four-window example at the start, I constructed selected Claude weekly-all and Fable entries plus Codex and Grok weekly-all entries, then used `usage_indicator_groups` and `build_usage_indicator_segment`. The proposed strings reuse the resulting fragments, replace the separator, omit parentheses, and use one outer cell per side. Widths include those outer cells and any `+N`:

| Visible windows | Current width | Recommended width | Saving |
|---|---:|---:|---:|
| All four | 61 | 57 | 4 |
| Three plus `+1` | 52 | 48 | 4 |
| Two plus `+2` | 39 | 35 | 4 |
| One plus `+3` | 19 | 17 | 2 |

At a **60-cell usage budget**, the current renderer shows three windows and the recommendation fits four. At 38 cells it improves from one to two; at 18 it improves from `usage 4` to one window plus `+3`. These are usage budgets, not terminal widths. Other labels, reset times, and warning states change the thresholds. This table supersedes inconsistent partial-prefix widths in the source reports.

**The proposed layout, precisely.** Keep the existing two top rows. On the first, retain the existing header icon, left-align the complete application title immediately after it, and anchor usage to the right edge. On the second, retain navigation and the other controls. The title's left edge and the usage cluster's right edge stay fixed during ordinary countdown changes.

Schematic placement, with descriptive placeholders for unchanged surrounding content:

```text
[header icon] sase ace (v0.7.1)       🎭 62% 3d4h · fable 100% 1d8h  🤖 45% 2d5h
[tabs]                                  [model/routing controls] [project] [alerts]
```

Left-aligning the title is essential to the recommendation. Keeping it centered in the full terminal would reserve roughly half the header against the usage cluster and surrender much of the extra room. For illustration, reserve three cells for the existing icon area and 17 for this title. Then a width of 80 leaves 60 cells for the cluster, including its one-cell title gap and right margin; a width of 60 leaves 40. Both are useful improvements. Actual budgeting must measure the real icon region and title/subtitle, rather than hard-code those example lengths. Long title content remains reserved; usage takes its normal fallback before overlapping it.

The text rules are deliberately few:

- One provider icon, one following space, then that provider's existing window fragments.
- One space between existing tokens within a window; ` · ` between windows of the same provider.
- Two cells of the existing gap background between providers. Keep each provider's existing background and all existing value styles. Style the new dot with the existing neutral divider style.
- One outer cell per side, owned once by layout/rendering together; do not add widget padding on top of it.
- Preserve each complete window, all current compact names and disambiguation text, `!`, `?`, `?%`, `<1%`, and `↻`. No new labels, abbreviated times, percent/time slashes, bars, or repeated provider icons.

Examples of the same grammar under different states:

```text
🎭 62% 3d4h
🎭 62% 3d4h · fable 0% 1d8h · 5h 18% 2h9m
🛰️ ! 4% 3d4h  🤖 ?% 0h0m↻  🎭 88% ?
🎭 62% 3d4h · fable 100% 1d8h  +2
```

Use the largest complete prefix fitting the measured header budget, reserving space for the existing `+N` before admitting windows. When none fits, retain `usage N` → `N` → `…`, including the current empty result if no cell is available. Never wrap, split a percent/countdown pair, or rotate windows over time. Persistent visibility means a persistent location with honest overflow; arbitrarily many complete windows cannot fit in a fixed row without removing content.

The usage cluster remains one click target opening the current attention-leading provider's Usage view, with all selected and hidden window facts available in its tooltip. Moving it requires separating usage from its current routing widget. B correctly identified that their shared click handler currently prefers Usage whenever usage groups exist. The new usage region should retain that action and keep it from bubbling into a header expand/collapse action; routing remains its own control. This is a relocation requirement, not a proposal for tiny per-window click targets or new tooltip content.

**What remains to validate.** This turn produced research, not an implemented header. The measurements establish cell costs, not reduced glance time. Before implementation is accepted, compare current, dot-separated, and whitespace-only variants using the same states at 60, 80, 120, 140, 160, and 240 columns in both current themes. Include three-window providers, duplicate compact names, long titles, all exceptional states, and countdown transitions such as `10h10m` → `10h9m`.

Check that no existing color/icon/value span changes, total chrome stays two rows, controls stop moving in response to usage-only width changes, and the tooltip/click action survives every overflow state. Internal usage positions may still move as tokens or attention order change; the design does not promise otherwise. Compare short glances for provider ownership, remaining capacity, and reset time. Prefer fewer attribution mistakes over one cell saved. If unchanged provider surfaces prove insufficient in supported terminals, test ` │ ` between providers as the alternative before considering any palette change.

**Recommended solution:** adopt a single right-aligned usage cluster in the existing header, with the unchanged title fixed on the left. Preserve the provider surfaces, icons, colors, warning spans, data strings, ordering, and disclosure semantics. Remove parentheses, use ` · ` between a provider's windows and two spaces between providers, and reduce outer padding to one cell per side. This offers the clearest improvement in space and separation with a small, consistent presentation change; fixed numeric columns, new ordering rules, and multiple density tiers are unnecessary for the first version.
