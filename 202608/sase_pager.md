---
create_time: 2026-08-26
updated_time: 2026-08-26
status: research
---

# One Pager, Many Documents: A Link-Traversing SASE Pager

**Research question:** What is the best way to build a custom SASE pager that replaces
the four ad-hoc paging paths in the tree, serves both `sase bead show` and the Agents
tab's `v` keymap, and turns every file path, artifact reference, bead id, and URL it
displays into a one-keypress jump with a breadcrumb trail back?

**Scope:** `sase` at `e16872c9d` (master, clean), `sase-core` unread except through the
Python binding surface. Measurements taken on this machine on 2026-08-26 against 2,422
local plan and research documents, one live `~/.sase/perf` hint trace, and the current
`sase bead show` renderer. This is design research; no runtime behavior was changed.

## Bottom line

Build **one Textual `App` — `SasePager`** — that both the CLI and ACE run, hand it a
**structured `PagerDocument` of sections rather than a string**, and let **the pager
itself discover every link** with one scanner. Add **`sase pager`** as the CLI entry
point, primarily because it is the thing you put in `$SASE_PAGER`, and secondarily
because `sase pager <ref> <ref> <path>` is a capability that does not exist today.

Four numbers decide the design:

| Measurement                                                 |                                       Value |
| ----------------------------------------------------------- | -------------------------------------------: |
| Links per plan/research document (n=2,422)                  | p50 **17**, p90 **51**, p99 **97**, max 187 |
| Links per 45-line screen (n=12,845 windows)                 |         p50 **3**, p90 10, p99 21, max **46** |
| Documents fully covered by a 51-key single-press alphabet   |                                 **90.2 %** |
| Links in one real Agents-tab `v` render (`tui_trace.jsonl`) |                       **924** and **1,154** |

The first three say the owner's requested alphabet is exactly right: single keys carry
90 % of documents end to end, screens are nowhere near saturated, and `00`–`ZZ` is a
real but rare tail. The fourth says the *current* `v` flow already has a link-density
problem the pager should not inherit — and that agent detail documents must be labelled
lazily if they ever enter the pager.

Everything below is either evidence for that shape or a decision I want the owner to
overrule if they disagree.

## 1. What exists today

### 1.1 SASE has four pagers, and none of them is a pager

| Path                                                                     | Used by                                | Mechanism                                   |
| ------------------------------------------------------------------------ | -------------------------------------- | ------------------------------------------- |
| `src/sase/cli_pager.py` `page_or_print()`                                | `sase bead show`                       | Pipes rendered ANSI into `$SASE_PAGER`/`less` |
| `src/sase/artifact_cli/read.py` `_print_or_page()`                       | `sase artifact read`                   | Its own, differently-configured `less`/`bat` |
| `src/sase/ace/tui/actions/hints/_files.py` `_view_files_with_pager()`    | ACE `v` on Agents and Patches          | `suspend()` + `bat --color=always … \| less -R` |
| `src/sase/ace/tui/graphics/_viewer_loop_media.py` `artifact_text_viewer_command()` | ACE artifact viewer, text artifacts | `bat --paging=always`, else a Python dump module |

Four call sites, four flag sets, four behaviors, zero shared contract. `cli_pager.py`
was added on 2026-08-25 in `2ed9dc7c9` ("feat(bead): page show output and accept
multiple ids") and is the newest and best of them: it has a real `PagerMode`
(`auto`/`always`/`never`), a display-row estimator that respects wide characters via
`rich.cells.cell_len`, `SASE_AGENT` suppression, SIGINT isolation, and `BrokenPipeError`
handling. **It is the right front door and the wrong back end.** The recommendation
below keeps every one of those behaviors and replaces only what it hands the text to.

### 1.2 The `v` keypath, end to end

`v` on the Agents tab (`hints/_files.py:31`) runs `AgentDetail.update_display_with_hints`
off the Textual pump, which walks the whole agent detail document and inserts
`[N] ` markers in `bold #FFFF00` before every recognised token. Producers:

| Producer                                | Hint kind                                       |
| --------------------------------------- | ----------------------------------------------- |
| `_file_path_hints.append_text_with_file_hints` | File paths (absolute, `~/`, `./`, `.sase/`, `dir/file.ext`), `@`-prefixed |
| `_artifact_files.append_artifact_file_paths` | Registered artifact files                     |
| `_agent_commits._append_commit_group`   | Commits → `CommitViewSpec`, opened in `CommitViewModal` |
| `_agent_artifact_reads`                 | Audited artifact reads, by resolved path        |
| `_agent_memory_reads` / `_agent_glossary_reads` | Memory and glossary read reports (materialised on demand) |
| `_tool_call_report_hints`               | Slow and failed tool-call reports               |
| `_agent_deltas`                         | Changed files in a delta                        |

The user then types numbers into `HintInputBar` (`1-5`, `3@` to edit, `3%` to copy) and
`_finish_view_request` routes the selection: media → `view_artifact_files`, everything
else → `bat | less`. **The pager replaces only that last hop.** The hint pipeline, the
report materialisation, the `@`/`%` suffixes, and the media handoff all stay.

Two facts about that pipeline matter to the design:

- **HTTP(S) URLs are matched only to be excluded** (`_FILE_PATH_OR_HTTP_URL_RE` yields a
  match whose group 2 is `None`, and `iter_file_path_matches` drops it). Complete typed
  artifact refs are likewise excluded from file hints by
  `_matches_outside_artifact_refs`. So `v` today hints neither URLs nor `bead:`/`plan:`
  refs — the pager can add both without colliding with anything.
- **Hint generation is capped** at `PLAIN_RENDER_MAX_BYTES = 128_000` /
  `PLAIN_RENDER_MAX_LINES = 5_000` per render with an explicit
  `"hints not generated past this point"` notice (`_hint_caps.py`). That cap is a
  precedent the pager should honour rather than re-derive.

### 1.3 SASE has already built six-sevenths of this pager, in pieces

This is the strongest finding in the report. Nearly every mechanism the brief asks for
already exists somewhere in `src/sase/ace/tui/modals/`, tested and in production:

| Requirement                    | Existing implementation                                                                                 |
| ------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `ctrl+n` / `ctrl+p` next/prev entity | `ZoomPanelModal` (next/prev **file**, `zoom_panel_modal.py:107`) and `CommitViewModal` (next/prev **commit**, `commit_view_modal.py:67`) |
| Single-key link following      | `GlossaryPreviewModal` binds `1`–`9` to `follow_reference(n)` (`glossary_preview_modal.py:60`)          |
| `backspace` breadcrumb back    | `GlossaryPreviewModal.action_go_back` over a `_history` list; `travel_back: "backspace,h"` in `default_config.yml:346,374` |
| Bounded breadcrumb trail       | `memory_panel_travel.py` — `_trail`, `_MAX_TRAIL_LENGTH = 32`, `_travel_forward`, `action_travel_back` |
| Breadcrumb *rendering*         | `trail_strip.build_trail_strip()` — `TRAIL  A › B › C` with middle elision, already pure and shared     |
| Vim `/` `n` `N` search         | `widgets/vim_search_controller.py` — a reusable controller with a host protocol, already re-hosted twice |
| Chips painted before the key   | `glossary_preview_render.build_see_also_chips`, `relation_panel` `[key]` styling                        |
| One-shot key prefix            | `modals/numbered_link_keys.py` — arm on `.`, resolve next digit, cancel on anything else                 |
| Selector-key alphabets         | `artifact_files_modal_rendering.py`, `runners_modal.py`, `agent_neighbor_modal.py`, `property_picker_modal.py` — **four private copies, no shared utility** |
| Standalone Textual app run from CLI *and* from ACE | `MemoryReviewTuiApp` — `sase memory review` calls `.run()`; ACE calls it under `with app.suspend()` (`_notification_handlers.py:142`) |
| Media handoff                  | `graphics/view_artifact_files` — kitty graphics, mpv, tmux panes, PDF page loop                          |
| Multi-entity divider           | `bead/cli_show_batch.py:185` `_show_divider` — `── 2/3 ────────` already renders between beads          |

The pager is therefore **mostly a consolidation, not an invention.** That materially
changes the risk profile and should change the sequencing: the first phase is extracting
shared primitives from four modals, not writing a viewer.

### 1.4 What the `v` keymap can currently reach, and what it cannot

Reachable today: local files by path, artifact files, commits, tool-call/memory/glossary
reports, delta files. Not reachable: URLs, typed artifact refs (`bead:`, `plan:`,
`research:`, `agent:`, `stitch:`, `patch:`, `file:`), bare bead ids, and anything inside
a file once opened — `less` is a dead end.

That last one is the whole point of this work. Today, `v` → a plan file → the plan cites
`bead:sase-ua` and `src/sase/relations/artifact_links.py:201` → you quit `less`, go back
to the TUI, and start over. The pager makes that a keypress.

## 2. Measurements

### 2.1 Link density decides the key alphabet

Scanned all 2,422 Markdown documents under `~/.sase/plans/2026*/` and
`sase/repos/research/2026*/` with the production file-path regex plus a typed-ref
pattern, a URL pattern, and a bare-bead-id pattern:

| Statistic                        | Links per document |
| -------------------------------- | ------------------: |
| p50                              |             **17** |
| p90                              |             **51** |
| p99                              |                 97 |
| max                              |                187 |
| documents with zero links        |          (long tail) |

Per 45-line screen, over every window of every document (n=12,845): **p50 3, p90 10,
p99 21, max 46**, and **19.5 % of screens have no links at all.** Taking each document's
*worst* window: p50 9, p90 20, p99 35, max **47**. **No document in the corpus has a
single screen that exceeds a 51-key alphabet** — 0.0 % of 2,422.

With the command keys reserved below, the single-press alphabet is **51 keys**
(10 digits + 18 lowercase + 23 uppercase). Against the corpus:

- **90.2 % of documents are labelled entirely with single keys.**
- 9.8 % need a two-key tail, and only for links past the 50th.
- Reserving 3 alphabet characters as two-key prefixes yields 48 + 153 = **201 labels**,
  above the 187-link maximum in the whole corpus.

This is precisely the owner's stated expectation — "we shouldn't need to resort to
multiple keys often, but make sure we support this just in-case" — confirmed by
measurement rather than assumed.

### 2.2 The current `v` render is far past single-key territory

`~/.sase/perf/view_hints_floor_trace.jsonl` records real
`widget.prompt_panel.update_display_with_hints` spans:

```
hints: 924    annotated_chars: 102,541   duration: 36.3 ms  (cache miss)
hints: 1,154  annotated_chars: 128,016   duration: 43.0 ms  (family container)
```

An agent detail document produces **924–1,154 hints**. That is fine for the current
type-a-number bar and fatal for painted single-key labels. Two conclusions:

1. The pager renders the **selected files**, not the agent detail document, so it does
   not inherit this today.
2. If the agent detail document ever becomes a pager document (§7 argues it eventually
   should), **labels must be assigned lazily over a window**, not over the document.

### 2.3 `sase bead show` output is link-dense in a way the current scanner misses

`sase bead show sase-ug`: 42 lines, 5 file paths, 2 typed refs, 2 URLs — and **13 bare
bead ids** (`sase-ug.1`, `sase-ug.3`, …). Bare bead ids are the single highest-value
link type for bead output and today's scanner sees none of them, because
`_FILE_PATH_ALTERNATIVES` requires a `/` or an extension.

The pager needs **context-scoped bare-token recognisers**: in a bead-show document a
bare `sase-ug.3` is a bead; in a diff a bare 7–40 hex token is a stitch. This is a per
document-kind list, not a global regex, precisely so a research doc that says
`sase-core` does not become a false link.

### 2.4 Process cost

`sase version` from a cold shell: **294 ms** wall. That is the floor for any
`SASE_PAGER="sase pager"` subprocess hop. It is why `page_or_print` must call the pager
**in-process** when the resolved pager is SASE's own (§4.1), and why the subprocess form
exists only for foreign callers (`git`, `gh`, a shell pipeline).

## 3. Alignment with the `sase-ug` epic

`bead:sase-ug` — "A link rail on every tab", plan `plan:202608/link_rail_every_tab.md`,
phases 1–2 closed, 3–10 in progress — is the adjacent work, and the owner is right to
ask. My conclusion: **complementary surfaces, one shared substrate.**

| Dimension     | `sase-ug` Link Rail                                      | SASE pager                                                       |
| ------------- | -------------------------------------------------------- | ---------------------------------------------------------------- |
| Surface       | One line above ACE's footer, on all three tabs           | A full-screen document view (CLI and ACE)                        |
| Subject       | The **selected entity** in a list                        | The **content being read**                                       |
| Link source   | The typed artifact-link **graph** (store + projection)   | **Textual mentions** in the rendered bytes                       |
| Cardinality   | p50 1, p90 2, max 26 — bounded to ≤9 chips               | p50 17, p90 51, max 187 — unbounded, inline                      |
| Key grammar   | `$` prefix + digit (two keys), `$0` for the tail         | One painted key per link                                         |
| Trail         | App-level `_link_trail`, `Ctrl+O` / `Ctrl+Shift+O`       | `backspace` (and `Ctrl+O` for symmetry)                          |
| Invisibility  | Hard requirement — `display:none` when the entity has no links | N/A — the pager is opened deliberately                    |

They answer different questions. The rail answers *"what is this entity linked to?"*;
the pager answers *"what does this text point at?"* A bead's rail shows its `implements`
edge; the pager over that same bead shows its 13 child ids, its plan path, and its
GitHub page URL — none of which are graph edges.

**Three seams must be shared or SASE ends up with two divergent link systems:**

1. **Ref → destination resolution.** `sase-ug.5` (`subject`) builds the app-level,
   alias-keyed, O(1) `LinkIndex` and explicitly warns against the O(n)
   `_known_target_for_ref` scan (`relations/artifact_links.py:201`). The pager must
   consume that index, not build a second one. This is the one genuine sequencing
   dependency in the whole design.
2. **Ref → glyph, accent, and short label.** `ARTIFACTS_ICONS` / `ARTIFACTS_ACCENTS`
   (`_artifact_tab_model.py:52,64`) and the rail's short-label rule
   (`bead:sase-u3` → `sase-u3`, `stitch:sase-org/sase@f4b827af6` → `sase@f4b827a`) must
   produce identical output in both surfaces. `◈` in purple must mean "bead" everywhere.
3. **The trail.** `sase-ug.8` (`trail`) builds a bounded app-level trail whose entries
   restore what a forward hop changed. The pager's `backspace` must walk **the same
   trail object**, so a rail hop into the pager and a `backspace` out of it is one
   history, not two. A user who presses `$1` in ACE, lands in the pager, follows two
   links, and presses `backspace` three times should be back where they started.

**Two places the pager should borrow the rail's design verbatim**, because divergence
there would be gratuitous:

- **Dangling links still count as links** — render dim with `⊘` and `(missing)`, and
  emit a toast instead of navigating. Same vocabulary as `relation_panel.py:236`.
- **Breadcrumb collapse** — `⟨ …3 › ✎plan ⟩` past the last two entries.

**One place they should stay different, deliberately:** the key grammar. The rail's `$`
prefix exists because bare digits are already bound to Artifacts sub-panes
(`bindings.py:127-129`); inside the pager there is no such conflict, and the brief asks
for single keys. Two grammars is correct here because the two surfaces have different
key budgets. What must *not* differ is where a key takes you.

**Recommended sequencing:** do not block the pager on the whole epic. Land the pager's
resolution against a narrow interface (`resolve_ref(ref) -> LinkTarget | None`) that
`sase-ug.5`'s `LinkIndex` satisfies, with a thin `resolve_cli_reference`-backed adapter
until it exists. Land the pager's trail on `sase-ug.8`'s module if it is done, and
otherwise on `memory_panel_travel.py`'s shape, with a note that `sase-ug.8` absorbs it.

**One conflict to flag:** `sase-ug.10` (`land`) retires `beads_open_plan` and
`plans_open_bead` (`L` on two panes) as duplicates the rail generalises. The pager
retires the same class of thing at the CLI layer: `_print_or_page`,
`_view_files_with_pager`, and the `less` back end of `page_or_print`. Both are net
deletions; they do not collide, but the pager epic should say so explicitly so a
reviewer does not read two overlapping deletions as one being redundant.

## 4. Design decisions

### D1 — The pager is a standalone Textual `App`, run in-process

**Decision.** `SasePager(App[PagerExit])` in a new `src/sase/pager/` package. The CLI
calls `SasePager(document, …).run()` directly. ACE calls it under
`with self.suspend(): SasePager(...).run()`.

**Why.** `MemoryReviewTuiApp` already proves both halves of this exact pattern in this
exact tree — CLI launch at `memory/cli_review.py:338`, ACE-suspended launch at
`_notification_handlers.py:142`. It buys `VimSearchController`, Rich renderables, PNG
snapshot testing via `just test-visual`, and headless `Pilot` key tests for free.

**Alternative rejected — a raw-terminal ANSI loop** extending
`graphics/_viewer_loop_terminal.py`. It has `read_single_key`, tmux integration, and
native kitty graphics, and it starts faster. But it would need hand-built scrolling,
reflow, resize, and incremental search — four things Textual gives away — and it cannot
render the chip anatomy the brief asks for without becoming a small Rich layout engine.
Keep it for **media only** (D7).

**Alternative rejected — keep `less` and generate a link sidecar.** `less` cannot paint
labels, cannot own a trail, and cannot dispatch a key to SASE.

**Cost.** Textual boot inside `suspend()` is a second alt-screen transition; measure it
and hold it under 150 ms before landing. If it is felt, the fallback is to keep the
pager screen mounted inside ACE for the ACE path only — but that would fork the code,
so treat it as a last resort, not a plan.

### D2 — The unit of input is a `PagerDocument` of sections, not a string

```python
@dataclass(frozen=True)
class PagerSection:
    identity: str                    # "bead:sase-ug", "file:/abs/path.py"
    title: str                       # rendered in the section rule
    kind: str                        # drives icon + accent
    body: RenderableType | str       # Rich renderable, or ANSI/plain text
    subject_ref: str | None = None   # this section's own artifact ref, if any

@dataclass(frozen=True)
class PagerDocument:
    sections: tuple[PagerSection, ...]
    title: str
    origin: PagerOrigin              # what opened it; seeds the trail
```

**Why.** `ctrl+n`/`ctrl+p` needs entity boundaries; the trail needs stable identities;
the header needs a subject to hang a `LINKS` rail on. A string has none of these. Every
caller can build one cheaply: `sase bead show` already renders per-bead entries and
already draws `── 2/3 ──` dividers between them (`cli_show_batch.py:185`); `v` already
has a list of resolved paths.

**ANSI bodies are first-class.** `sase bead show` produces styled ANSI, not a
renderable. Parse it with `rich.text.Text.from_ansi()`, which yields plain text for
scanning *and* style spans for rendering, so link labels can be inserted at exact
offsets without re-implementing SGR parsing. `cli_pager._SGR_RE` becomes unnecessary.

### D3 — The pager owns link discovery; callers never supply links

**Decision.** One scanner, run by the pager over each section's plain text, in this
order:

1. **Typed artifact refs** — `scan_artifact_refs()` (the Rust binding, already used by
   `artifact_ref_syntax.py`). Highest precedence; already the authority on ref spans.
2. **URLs** — `_HTTP_URL_PATTERN`, currently matched only to be discarded.
3. **File paths** — `iter_file_path_matches()`, unchanged, minus artifact-ref ranges via
   the existing `_matches_outside_artifact_refs`.
4. **Context-scoped bare tokens** — bead ids in a bead document, short shas in a diff.
   Declared per `PagerOrigin`, never globally (§2.3).

**Why one scanner.** If `sase bead show` supplies its own links and `v` supplies its
own, they diverge within a release and a bug is fixed twice. Making the pager the only
producer means `sase pager` on arbitrary stdin gets identical behaviour for free, which
is most of that command's value.

**Budget.** Reuse `HintContentBudget` and the 128 KB / 5,000-line caps from
`_hint_caps.py`, including the visible `hints not generated past this point` notice. Do
not invent a second cap.

**What is deliberately not scanned:** anything requiring I/O to recognise. A link's
*label* comes from its ref string alone; existence checking is lazy and happens on
press, not on paint. This is the same rule `sase-ug`'s plan states for the rail
("Labels derive purely from the ref string… **Do not**"), and it is what keeps paint
time flat.

### D4 — Key assignment: 51 single keys, document-scoped, prefix-free overflow

**The alphabet.** `0-9`, then `a-z`, then `A-Z`, as requested, **minus the keys the
pager binds to commands.** Reserving `j k g n q y o h` and `G N Y` leaves **51 single
keys**:

```
0123456789 a b c d e f i l m p r s t u v w x z  A B C D E F H I J K L M O P Q R S T U V W X Z
```

**Why reserve rather than prefix.** The brief asks for single-keypress traversal. The
alternative — an armed prefix like the rail's `$` or `numbered_link_keys`' `.` — keeps
the whole 62-key alphabet but costs a keystroke on every jump. Reserving 11 keys costs
nothing on 90.2 % of documents (§2.1) and preserves the vim command set that
`ZoomPanelModal`, `CommitViewModal`, `GlossaryPreviewModal`, and `MemoryReviewTuiApp`
all already use. Breaking `j`/`k`/`g`/`G`/`q`/`y` in the one surface a user reads most
would be a worse trade than a shorter alphabet.

**Assignment is document-scoped and stable.** Labels are assigned in document order at
load and never change while the document is open. Scrolling never renumbers anything.
This is the opposite of the Vimium model, and it is right here because the labels are
*always painted*, not summoned by a hint mode — churning labels under a moving viewport
would be visually noisy for no benefit.

**Overflow is prefix-free, never timed.** When a document has more links than the
alphabet, reserve the *last* k alphabet characters as two-key prefixes; a reserved
prefix is never itself a label, so `a` can never be both "link 11" and "the start of
`aQ`". No ambiguity, no timeout, no mis-fire. k is chosen as the minimum that covers the
document: k=1 → 101 labels, k=2 → 151, k=3 → 201, which covers the corpus maximum of
187. The first 48–50 links — where the eye is — always stay single-key.

**Lazy fallback for pathological documents.** If a document exceeds the two-key capacity
(none in the corpus, but a 1,154-hint agent document would), fall back to
**window-scoped assignment**: label only the visible band plus one screen of overscan,
re-anchored when the viewport leaves the band, not on every line. The worst screen in
the entire corpus holds 47 links against a 51-key alphabet (§2.1), so **single keys
always win in that mode**. Ship the fallback with the first release even
though nothing triggers it, because the moment the agent detail document becomes a pager
document (§7) it is the only workable scheme.

**Rendering.** The label goes *before* the token in `bold #FFFF00` — the existing
`[N] ` convention from `_file_path_hints.py:264` — and the token itself takes the
**destination kind's** accent from `ARTIFACTS_ACCENTS`. The colour says where the key
goes before you press it, exactly as the rail's chips do.

### D5 — `ctrl+n` / `ctrl+p` scroll to a section header; they do not swap views

**Decision.** The pager is one continuous scrollable document. `ctrl+n` scrolls so the
next section's rule sits at row 0; `ctrl+p` does the reverse. At the last section,
`ctrl+n` goes to the end of the document rather than beeping.

**Why.** The owner's own phrasing — "re-draw the contents with that file's header at the
top of the screen" — is a scroll, not a mode. It also means `/` searches the whole
document, `g`/`G` mean the real top and bottom, and the mental model stays "less over a
concatenation", which is what everyone already has.

**This differs from the two existing implementations, on purpose.** `ZoomPanelModal` and
`CommitViewModal` bind the same chord to a *view swap* because their entities are
independently loaded. The pager's are already materialised, so a swap would be strictly
worse. Note the divergence in the code so a future reader does not "fix" it.

**The section rule** is the existing `_show_divider` shape, promoted from
`cli_show_batch.py` and given a glyph and accent:

```
━━ 2/3 ━ ◈ bead:sase-ug ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### D6 — The trail is a first-class, restoring, shared object

**Decision.** A bounded 32-entry trail, each entry recording `(document identity,
section identity, scroll offset, search state, label anchor)` — enough that `backspace`
restores the *view*, not just the document. Mirrors `_MAX_TRAIL_LENGTH` and
`_travel_forward`/`action_travel_back` in `memory_panel_travel.py`.

**Bindings.** `backspace` back (as asked), `ctrl+o` back and `ctrl+i` forward for vim
symmetry and for continuity with `sase-ug.8`. A failed or dangling jump does not mutate
the trail.

**Rendering.** One line under the title, built by extending `trail_strip.build_trail_strip`
with per-entry kind glyphs and accents:

```
TRAIL  ⬡ sase-ug.6.code  ›  ✎ link_rail_every_tab.md  ›  ◈ sase-ug
```

Past three entries it collapses to `⟨ …3 › ✎ plan ⟩`, matching the rail. The strip is
absent — not empty — when the trail is empty, so a first-open pager has no wasted row.

### D7 — Media is delegated, never re-implemented

A link whose target is an image, video, or PDF renders as a chip with the existing
`_ICON_BY_VIEW_MODE` glyph (`▨ ▶ ▤`). Pressing it suspends the pager and hands the spec
to `graphics.view_artifact_files`, exactly as `_finish_view_request` does today. Textual
cannot do kitty graphics or mpv; `graphics/` already does both, in a tested loop with
tmux pane handling. Do not port it.

### D8 — Search is the existing controller, re-hosted

`VimSearchController` (`widgets/vim_search_controller.py`) already provides `/`, `n`,
`N`, incremental highlight, wrap feedback, and a documented host protocol; it is already
re-hosted by `ZoomSearchMixin` and `_metadata_search.py`. Host it a third time. Copy
`_STRUCTURAL_SEARCH_EXIT_KEYS`'s idea: structural keys (`ctrl+n`, `ctrl+p`, `backspace`,
`q`) exit search mode rather than typing into it.

**Search and labels interact.** While a search is active, a link label must not shadow a
search-navigation key. Since `n`/`N` are reserved from the alphabet (D4), they do not.
This is not an accident — it is why they are reserved.

### D9 — What the pager does not do, in v1

- **No editing.** `o` opens `$EDITOR` at the link's file and line, via the existing
  `build_editor_args`; the pager itself is read-only.
- **No link authoring.** `sase-ug.9`'s `$0` panel owns `add`/`rm`. The pager does not.
- **No `read` link recording.** `sase artifact read` records a `read` row only under
  `SASE_AGENT` with a resolved agent identity (`artifact_cli/read.py:_should_record_link`).
  The pager is a human surface; recording a read because a human scrolled past a chip
  would pollute the very read model `sase-ug.1` is converging. If an agent's
  `sase artifact read` pipes through the pager, the row was already written upstream.
  `page_or_print` already declines to page under `SASE_AGENT`; keep that.
- **No transitive expansion or graph browsing.** One hop at a time; the trail is the
  history.

## 5. What it looks like

Bead document, three sections, two hops deep, 120 columns:

```
 ◈ sase-ug · A link rail on every tab                            2/3 · 41% · ⌘ 88c
 TRAIL  ⬡ sase-ug.6.code  ›  ✎ link_rail_every_tab.md  ›  ◈ sase-ug
 LINKS  $$ ← implemented-by ✎ 202608/link_rail_every_tab.md — "lands the design"
 ───────────────────────────────────────────────────────────────────────────────
 CHILDREN
   PHASES
     ✓ [a] sase-ug.1: One projection for the machine-local read model    [CLOSED]
     ✓ [b] sase-ug.2: A stale clone may not prove deletion               [CLOSED]
     ◐ [c] sase-ug.3: Projected edges from facts SASE already owns  [IN_PROGRESS]
     ◐ [d] sase-ug.4: A way to read durable truth and see the drift [IN_PROGRESS]

 PAGE
   [e] https://github.com/sase-org/sase--beads/blob/main/pages/sase-ug/README.md

 PLAN
   [f] plan:202608/link_rail_every_tab.md
   → [g] /home/bryan/.sase/plans/202608/link_rail_every_tab.md
 ───────────────────────────────────────────────────────────────────────────────
 a-z follow · ⌫ back · ^N/^P entity · / search · y copy · o edit · h keys · q quit
```

Three things to notice, all deliberate:

- The `LINKS` line is **the `sase-ug` rail, rendered inside the pager**, with the same
  `$` grammar. Graph edges and textual mentions coexist without competing: `$` for
  edges, letters for mentions. One surface, two link sources, no ambiguity.
- `[f]` and `[g]` are the *same destination* reached two ways — the logical `plan:` ref
  and the resolved path — because that is what the bead renderer already prints. The
  pager labels both rather than guessing which one the user meant.
- The footer is a legend, not decoration. It is the only documentation a user needs, and
  it changes with availability: no trail → no `⌫ back`.

A file document opened from `v`, mid-scroll, showing the section rule:

```
 ▤ 3 files · artifact_links.py                                   1/3 · 12% · ⌘ 88c
 ───────────────────────────────────────────────────────────────────────────────
    198  def _known_target_for_ref(ref: str) -> ArtifactEntryTarget | None:
    199      """Resolve a ref by scanning every known target."""
    200      for target in _all_targets():          # ← see [k] tui_perf.md rule 8
    201          if target.ref == ref:
 ━━ 2/3 ━ ▤ src/sase/ace/tui/relations/artifact_links.py ━━━━━━━━━━━━━━━━━━━━━━━━
```

A zero-link document renders no label column and no `LINKS` line at all — 19.5 % of
screens have no links (§2.1), so absence is common and must cost nothing.

## 6. The `sase <subcmd>` question

**Answer: yes — add `sase pager`.** I considered not adding it, and the argument against
is real: `sase bead show` and `v` both get the pager without a command, and a new
top-level verb costs help text, completion, docs, and tests. Three concrete capabilities
outweigh that.

**1. It is the thing you put in `$PAGER`.** `cli_pager._resolve_pager_argv()` already
reads `SASE_PAGER` then `PAGER` and execs it with the body on stdin. The moment
`sase pager` exists, `export SASE_PAGER="sase pager"` routes *every* paging SASE command
— today `sase bead show`, tomorrow whatever else adopts `page_or_print` — through the
new pager, using plumbing that already ships. No config field, no flag, no new
mechanism. That alone justifies the command, and it decides the name: `sase pager` is
honest about being a pager, which is what a `$PAGER` value must be.

**2. Multi-ref reading in one view does not exist today.**

```bash
sase pager bead:sase-ug plan:202608/link_rail_every_tab.md src/sase/cli_pager.py
```

Three heterogeneous artifacts, one document, `ctrl+n`/`ctrl+p` between them, every
mention in all three keyed. `sase artifact read` takes one ref and shells to `less`;
`sase bead show` takes many beads but only beads. This is the CLI twin of the `v` flow
and is the command's strongest standalone use.

**3. It makes foreign output navigable.**

```bash
git show --stat | sase pager
gh pr diff 1421 | sase pager
```

Every path in a diff becomes a keyed jump into `$EDITOR`. The scanner works on plain
text, so this needs no per-source integration.

**Shape**, following `cli_rules` (sorted options, a short alias for every long option, no
required options, required values as positionals):

```
sase pager [-c auto|always|never] [-l auto|never] [-p] [-t TITLE] [-w WIDTH] [REF|PATH ...]

  positional  REF|PATH   Artifact references or file paths, one section each.
                         Omit to read the document from stdin.
  -c, --color            Color output (default: auto)
  -l, --links            Link scanning and labels (default: auto)
  -p, --plain            Dump without paging; implied when stdout is not a TTY
  -t, --title TITLE      Document title for stdin input
  -w, --wrap WIDTH       Wrap prose at WIDTH columns (default: markdown.print_width)
```

**Two implementation notes.** `page_or_print` must detect that the resolved pager *is*
SASE's own and call it **in-process** rather than paying the 294 ms subprocess hop
(§2.4). And with no TTY the command must dump plain, so it is safe in a pipeline and
safe as an unconditional `$PAGER`.

**What I would not add:** `sase view` or `sase open`. Both read as verbs that would
collide with `sase artifact read` / `sase artifact open`, whose jobs (audited read,
media viewer) are different. `sase pager` names the mechanism because the mechanism is
the contract.

## 7. Recommended solution

An epic under a `beta` feature flag created with `sase flag new` — this is exactly the
case the `sase_flags` note describes, where landed phases would otherwise expose an
unfinished surface — removed in the final phase.

**Phase 1 — `primitives`.** Extract what already exists, before writing a viewer. One
`selector_keys` module (the alphabet, the prefix-free overflow, the four private copies
in `artifact_files_modal_rendering`, `runners_modal`, `agent_neighbor_modal`, and
`property_picker_modal` retired). One `link_scan` module (typed refs → URLs → paths →
context-scoped bare tokens), reusing `HintContentBudget`. One `pager_trail` module on
`memory_panel_travel.py`'s shape, sharing `trail_strip`. Net line count should be close
to flat. *Test:* the label allocator is prefix-free and stable for every corpus document
size from 0 to 200.

**Phase 2 — `document`.** `PagerDocument` / `PagerSection`, `Text.from_ansi` ingestion,
and adapters from `sase bead show` and from a list of file paths. No UI. *Test:* the
same bead renders to the same section set from the CLI and from a fixture.

**Phase 3 — `viewer`.** `SasePager(App)`: scrolling, section rules, `ctrl+n`/`ctrl+p` as
scroll-to-header, painted labels, footer legend, `VimSearchController` re-hosted. Not yet
wired to any caller. *Test:* headless `Pilot` key tests plus PNG goldens at 120×40 and
60×30 for zero-link, 3-link, 60-link (two-key tail), and dangling-link documents.

**Phase 4 — `follow`.** Link press → resolve → open. Resolution behind
`resolve_ref(ref) -> LinkTarget | None`, adapted to `resolve_cli_reference` now and to
`sase-ug.5`'s `LinkIndex` when it lands. Trail push, `backspace`/`ctrl+o` restore,
dangling `⊘` behaviour, media handoff to `graphics`. *Test:* every ref kind in both
positions; a dangling ref shows but does not navigate and does not touch the trail.

**Phase 5 — `cli`.** `sase pager`, and `page_or_print` routed in-process. `sase bead
show --pager` semantics preserved exactly, including `auto` row estimation, `SASE_AGENT`
suppression, and `$SASE_PAGER` override to a foreign pager. *Test:* the existing
`tests/test_cli_pager.py` and `tests/test_bead/test_cli_show_pager.py` pass unchanged
except where behaviour intentionally changed.

**Phase 6 — `ace`.** `v` routes to `SasePager` under `suspend()`. Selected files become
sections; media still routes to the artifact viewer; `@` (editor) and `%` (copy) keep
working. *Test:* the `agents.view_files` trace span still closes, and `SASE_TUI_PERF`
shows no regression on the Agents tab.

**Phase 7 — `land`.** Delete `_print_or_page` (`artifact_cli/read.py`), delete
`_view_files_with_pager` (`hints/_files.py`), delete the `less` back end of
`page_or_print`, point `artifact_text_viewer_command`'s text mode at the pager, remove
the flag, close the flag bead. **This phase must be a net deletion.** If it is not, the
boundary was drawn wrong.

**Deferred, and worth a separate decision later:** putting the agent detail document
*itself* in the pager, so `v` becomes "open this agent in the pager" rather than "pick
numbers, then open files". The 924–1,154-hint measurement (§2.2) says that is where the
current flow hurts most, and window-scoped labelling (D4) is the mechanism that makes it
possible. But it changes a keypath the owner uses constantly, so it should be its own
proposal with its own goldens, not a rider on this epic.

## 8. Risks

| Risk                                                                     | Severity | Mitigation                                                                                                                                     |
| ------------------------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Textual boot inside `suspend()` makes `v` feel slower than `bat \| less` | **High** | Measure before Phase 6 lands; budget 150 ms. `MemoryReviewTuiApp` already does this, so the number is obtainable today rather than estimated.  |
| The pager and the `sase-ug` rail diverge into two link systems            | **High** | One `resolve_ref` interface, one glyph/accent table, one trail object — the three seams in §3. Assert in a test that both produce the same target for the same ref. |
| Labels shift or mis-fire, so users stop trusting the keys                 | **High** | Document-scoped stable assignment (D4), prefix-free overflow, no timeouts. Test label stability across scroll, resize, and search.             |
| A false-positive bare-token link (`sase-core` read as a bead)             | Medium   | Bare-token recognisers are per-`PagerOrigin`, never global (§2.3), and resolution failure renders `⊘` rather than navigating.                  |
| The scanner is slow on a large document                                   | Medium   | Reuse the existing 128 KB / 5,000-line `HintContentBudget` and its visible truncation notice; scan off the paint path at load, never per key.  |
| Replacing four pagers regresses one caller's behaviour                    | Medium   | Phase 7 is the only deletion phase; each earlier phase leaves the old path intact behind the flag, so a regression is a flag flip away from fixed. |
| `$SASE_PAGER="sase pager"` recursing into itself                          | Low      | The in-process path never consults `$SASE_PAGER`; the subprocess path unsets it in the child env.                                              |
| Two-key labels appear more often than measured                            | Low      | 9.8 % of a 2,422-document corpus, only past link 50. If it grows, raise k or switch that document to window-scoped labelling — both already built. |

## 9. Verification

- **Label allocator:** prefix-free for every k; stable across scroll, resize, and search;
  identical for the same document across runs.
- **Scanner:** every ref kind in both endpoint positions; URLs and typed refs no longer
  swallowed by the path regex; bare-token recognisers fire only in their declared origin.
- **Parity:** the pager and the `sase-ug` rail resolve the same ref to the same target,
  glyph, and accent — one shared test, run against both.
- **Trail:** `backspace` restores scroll offset and search state, not just the document;
  a failed jump leaves it untouched; a rail hop into the pager and a `backspace` out
  walk one history.
- **Zero-link path:** no label column, no `LINKS` row, and **pixel equality with a
  document rendered by a build that has no label column at all** — the same
  strong-form assertion `sase-ug`'s plan uses for the invisible rail.
- **PNG goldens** at 120×40 and 60×30: zero-link, 3-link, 60-link (two-key tail),
  dangling link, deep trail, mid-section-rule.
- **CLI:** `tests/test_cli_pager.py` and `tests/test_bead/test_cli_show_pager.py` green;
  non-TTY dumps plain; `SASE_AGENT` still suppresses paging; a foreign `$SASE_PAGER`
  still wins.
- **Performance:** `SASE_TUI_PERF=1` shows no Agents-tab regression; pager open-to-first-
  paint measured and recorded; `tui_trace` span `pager.open` added.
- `just check-full` through `/sase_monitor` before landing.

## 10. Questions for the owner

1. **Is `sase pager` the right name?** I chose it because it must double as a `$PAGER`
   value. `sase view` reads better as a verb but invites confusion with
   `sase artifact open`.
2. **Should the pager's `LINKS` row exist before `sase-ug` lands its rail?** Rendering it
   early means two implementations for a while; omitting it means the pager ships without
   graph links. I lean toward omitting it until `sase-ug.6`, and shipping only textual
   mentions in v1.
3. **Should `v` eventually open the agent detail document itself** (§7, deferred)? It is
   the largest single UX win available and the largest change to a keypath you use
   constantly.
4. **Reserved-key set.** I reserved `j k g n q y o h G N Y`. Dropping `h` (help → `F1`)
   and `o` (edit → `ctrl+e`) would buy two more label keys and lift single-key coverage
   from 90.2 % to roughly 91 %. My call is that the vim keys are worth more than 1 %.
