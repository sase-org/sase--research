# Can three-pane splits start before the pager performance epic (sase-1es) lands?

> **Question:** Is there a safe way to start the work in
> [`deck_and_pager_three_pane_splits.md`](deck_and_pager_three_pane_splits/deck_and_pager_three_pane_splits.md)
> before epic `sase-1es` (plan `plan:202610/pager_performance.md`) is complete?

## Bottom line

**Yes. Start everything except the pager's own split code now, and run the rollout
Agents first instead of pager first.** The Agents deck, the shared `PaneGrid` model, the
key plumbing and the terminal fix do not touch any sase-1es file. The pager half rewrites
`_screen_split.py` and `view.py`, which `sase-1es.6`, the epic's largest and riskiest
phase, is about to rewrite too. Hold the pager half until `sase-1es.6` closes. One
exception: land `sase-1er` (the pager close bug) now. It is small and ready, and this is
the only window before `sase-1es.6` starts.

## Where sase-1es stands (2026-10-02, master `6cca547014`)

| Phase | State | Pager files it changes |
| --- | --- | --- |
| .1 bench | closed | `tests/perf/` only |
| .2 scans + leak | running | `view.py` `on_mount`/`on_unmount`, `link_scan.py`, `_labels.py`, `_layout.py`, trail |
| .3 cold path | running | `pager/__init__.py`, helper moves out of ACE, adds import-weight tests |
| .4 inventory memo | running | `_linked_repo_config.py`, `repo_inventory.py` (not pager UI) |
| .5 line model | waiting on .2, .3 | new modules, Justfile `--epic-symbol` entries |
| .6 ScrollView body (large) | waiting on .5 | `_screen_widgets.py`, `view.py` (`set_pane_role`, split seed), **`_screen_split.py`**, and about 12 other `_screen_*` call sites |
| .7 search | waiting on .6 | `VimSearchController`, search row source |
| .8 gates + docs | waiting on .4, .7 | `docs/pager.md`, perf tests |

The epic's guardrails require split behavior and every pager PNG golden to stay identical,
and forbid feature flags. No phase touches `ace/tui/widgets/decks/`, `bindings.py`,
keymaps, `default_config.yml` or `styles.tcss`. Decks appear in the plan only as proposed
follow-ups.

## Overlap by three-pane rollout stage

| Three-pane stage | Collides with sase-1es? | Start now? |
| --- | --- | --- |
| 0. kitty/tmux chain (chezmoi) | No | **Yes** (needs your approval) |
| 1. `sase-1er` close-path fix | Light. It edits `close_view`/`_toggle_split`; `.6` later edits invalidation calls in the same file. The `.2` leak test opens and closes a split, so today it runs the broken teardown. | **Yes, now**, before `.6` starts |
| 2a. pure `PaneGrid` + transition table + Hypothesis tests | No. New stdlib-only file. Keep it free of Textual/ACE imports so `.3`'s `sase.pager.screen` import-weight tests stay green. | **Yes** |
| 2b. Agents adapter on 2 panes (grid render, `ctrl+b`, swap, close, aliases, move `debug_leak_snapshot`, A3 survivor) | No | **Yes** |
| 4. Agents three panels (behind the beta flag) | No | **Yes**, after 2b |
| 2c. pager adapter (grid `#pager-panes`, new keys) | **Yes.** Same functions as `.6` (`set_pane_role`, split seed, mount paths), and it moves `.6`'s pixel-parity baseline while `.6` is in flight. | No, wait for `.6` |
| 3. pager three panes | **Yes**, as above. Before the epic it would also ship slow and leaky: each pane composes the whole document into one `Static`, a third pane clones another one, and every closed pane leaks until `.2` lands. | No, wait for `.6` (and `.2`) |
| 5. land + docs | Trivial (`docs/pager.md` with `.8`) | After both |

## Risks of starting early, and their mitigations

- **Losing "pager first."** The consolidated report picked the pager as the cheapest
  surface to prove the adapter. Agents first proves `PaneGrid` on the harder surface
  (persistence, zoom, picker). That is acceptable because the exhaustive transition table
  tests the model independently of any surface. grk and gem had already proposed deck
  first.
- **Mixed behavior across surfaces.** While the flag is on, `|` on a stacked split nests
  on Agents but still rotates in the pager. Keep the flag default-off until the pager half
  lands, and remove it for both surfaces in one commit.
- **Two split models for a while.** The pager keeps `PagerSplitState` until stage 2c, so
  the "no third copy" rule holds. Port it onto `PaneGrid` in 2c instead of extending it.
- **Symvision.** If `PaneGrid` lands before any consumer, it needs its own
  `--epic-symbol` entries next to `.5`'s. Land 2a and 2b together to avoid that.
- **Open decisions block 2b.** A3 (deck same-key survivor) and A6 (`ctrl+t` turn) change
  deck behavior in stage 2b, so decide them before launching it.

## Recommendation

1. **Now:** approve the chezmoi kitty/tmux change (stage 0), and run `sase-1er` as a
   standalone bug fix so it lands before `sase-1es.6` starts.
2. **Now:** launch the three-pane epic re-sequenced as `PaneGrid` + Agents 2-pane
   adapter → Agents three panels (flag) → pager adapter → pager three panes → unflag.
   Make the pager phases depend on `sase-1es.6` (bead dependency), so they are written
   against the new ScrollView body and its `_invalidate_body_paint/layout` API, not code
   that is about to be deleted.
3. **Don't** start any pager split change while `sase-1es.5`/`.6` are open, and don't
   wait for the whole epic. `.7` and `.8` barely touch split code.

## Method

I read the consolidated three-pane report, the sase-1es plan and its phase beads, the
`sase-1er` bead, and the agent list (`.2`–`.4` running, `.5`–`.8` waiting). I checked the
pager split code (`_screen_split.py` 409 lines, `view.py` 519 lines), the deck package
(about 11.7k lines, with no pager imports) and the `sase.ace.tui.util` import cost on
master `6cca547014`.
