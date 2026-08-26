---
create_time: 2026-08-26
updated_time: 2026-08-26
status: research
tags: [pager, tui, textual, artifacts, links, navigation, cli, ace]
---

# A Link-Traversing SASE Pager

**Research question:** What should SASE's custom pager be; how should `sase bead show`,
the Agents-tab `v` keymap, and `sase artifact read` converge on it; what does
single-keypress link traversal cost in keys and in trust; and is a new top-level CLI
command warranted?

**Scope:** Design research, no runtime change. Evidence checked against `sase@e16872c9d`
(master, clean), the live `sase-ug` bead store, `plan:202608/link_rail_every_tab.md`, and
2,424 local plan/research documents on 2026-08-26. This report consolidates two
independent research passes (`__a`, `__b`) with a third verification pass; every
measurement below was re-run rather than inherited.

---

## Bottom line

Build **one Textual `App` — `SasePager`** in a new `src/sase/pager/` package, run
**in-process** by both the CLI and ACE, fed a **structured `PagerDocument` of sections**
rather than a string. Add **`sase pager`** as the CLI entry point. Reuse the alphabet,
allocator, and key-matcher that **already exist in this tree** rather than writing new
ones.

Four facts drove every decision:

| Fact | Consequence |
| --- | --- |
| `jump_hints.py` already implements the exact requested `0-9`/`a-z`/`A-Z`/`00-ZZ` alphabet, a prefix matcher, and the Textual shifted-key fix | The label layer is an extension, not an invention |
| Links per 45-line screen: p50 **3**, p99 18, **max 47** across 522,288 windows | A ~51-key alphabet is never exhausted on any screen in the corpus |
| Reserving vim command keys costs **3.4 points** of single-key coverage (94.7% → 91.3%) | Keeping `j k g G q y n N` is nearly free; giving them up buys almost nothing |
| `MemoryReviewTuiApp` already runs from a CLI subcommand *and* from inside ACE under `suspend()` | No subprocess, no session manifest, no new handoff protocol |

The pager is **mostly consolidation, not invention.** That changes the risk profile and
the sequencing: phase one extracts shared primitives, it does not write a viewer.

---

## 1. What exists today

### 1.1 SASE has four pagers, and none of them is a pager

| Path | Used by | Mechanism |
| --- | --- | --- |
| `src/sase/cli_pager.py` `page_or_print()` | `sase bead show` | Pipes rendered ANSI into `$SASE_PAGER`/`$PAGER`/`less` |
| `src/sase/artifact_cli/read.py:338` `_print_or_page()` | `sase artifact read` | Its own differently-configured `less -R -F` / `bat` |
| `src/sase/ace/tui/actions/hints/_files.py:271` `_view_files_with_pager()` | ACE `v` on Agents and Patches | `suspend()` + `bat --color=always … \| less -R`, via `shell=True` |
| `graphics/_viewer_loop_media.py` `artifact_text_viewer_command()` | ACE artifact viewer, text artifacts | `bat --paging=always`, else a Python dump module |

Four call sites, four flag sets, zero shared contract.

`cli_pager.py` (added 2026-08-25 in `2ed9dc7c9`) is the newest and best of them: a real
`PagerMode` (`auto`/`always`/`never`), a display-row estimator that respects wide
characters via `rich.cells.cell_len`, `SASE_AGENT` suppression, SIGINT isolation, and
`BrokenPipeError` handling. **It is the right front door and the wrong back end.** Keep
every one of those behaviors; replace only what it hands the text to.

Its structural limit is the last step, and it is the reason this cannot be done by
wrapping `less`: `handle_bead_show()` resolves a structured `ShowBatch`, renders one
concatenated `body`, and only then calls `page_or_print()`. Entity boundaries, headers,
and target metadata are already flattened. `Ctrl+N`/`Ctrl+P` cannot reliably recover them
by scraping separators back out.

### 1.2 The `v` keypath, end to end

`v` on the Agents tab runs `AgentDetail.update_display_with_hints` **off the Textual
pump** (`hints/_files.py:_render_agent_hint_document`), with a session/identity guard
that revalidates the selection after the await. It walks the agent detail document and
inserts `[N] ` markers in `bold #FFFF00` before every recognised token. Producers:
`_file_path_hints`, `_artifact_files`, `_agent_commits`, `_agent_artifact_reads`,
`_agent_memory_reads`, `_agent_glossary_reads`, `_tool_call_report_hints`,
`_agent_deltas`.

The user then types numbers into `HintInputBar` (`1-5`, `3@` to edit, `3%` to copy) and
`_finish_view_request` routes the selection: media → `view_artifact_files`, everything
else → `bat | less`. **The pager replaces only that last hop.**

Three facts about this pipeline constrain the design:

- **HTTP(S) URLs are matched only to be excluded.** `_FILE_PATH_OR_HTTP_URL_RE` yields a
  match whose group 2 is `None`, and `iter_file_path_matches` drops it. Complete typed
  artifact refs are likewise excluded from file hints by `_matches_outside_artifact_refs`.
  So `v` today hints neither URLs nor `bead:`/`plan:` refs — **the pager can add both
  without colliding with anything.**
- **Hint generation is already capped** at `PLAIN_RENDER_MAX_BYTES = 128_000` /
  `PLAIN_RENDER_MAX_LINES = 5_000` per render, with a visible
  `"hints not generated past this point"` notice (`_hint_caps.py`). Reuse
  `HintContentBudget`; do not derive a second cap.
- **`AgentHintRender` carries typed specs a text scanner cannot recover** — verified at
  `_agent_display_state.py:68`: `tool_call_reports: dict[str, SlowToolCallReportSpec]`,
  `commit_views: dict[int, CommitViewSpec]`, `glossary_reports`, `memory_reports`. A
  `CommitViewSpec` or a lazily-materialised report is not a substring. §4.3 resolves what
  this means for link ownership.

What `v` can reach today: local paths, artifact files, commits, tool-call/memory/glossary
reports, delta files. What it cannot: URLs, typed artifact refs, bare bead ids, and
**anything inside a file once opened** — `less` is a dead end. Today, `v` → a plan file →
the plan cites `bead:sase-ua` and `src/sase/relations/artifact_links.py:201` → you quit
`less`, return to the TUI, and start over. That dead end is the whole point of this work.

### 1.3 Six-sevenths of this pager already exists, in pieces

Nearly every mechanism the brief asks for is already in `src/sase/ace/tui/`, tested and
in production:

| Requirement | Existing implementation |
| --- | --- |
| **The exact requested alphabet** | `actions/navigation/jump_hints.py:13` — `JUMP_HINT_CHARS = "0123456789abc…xyzABC…XYZ"`, `JUMP_HINT_CAPACITY = 62²`, `build_jump_hint_maps()`, `match_jump_hint()`, `normalize_jump_key()` |
| `ctrl+n`/`ctrl+p` next/prev entity | `ZoomPanelModal` (next/prev file, `zoom_panel_modal.py:110`), `CommitViewModal` (next/prev commit, `commit_view_modal.py:68`) |
| Single-key link following | `GlossaryPreviewModal` binds `1`–`9` to `follow_reference(n)` (`glossary_preview_modal.py:61`) |
| `backspace` back over a history stack | `GlossaryPreviewModal.action_go_back` (`:52`, `:98-109`); `travel_back: "backspace,h"` in `default_config.yml:346,374` |
| Bounded trail | `memory_panel_travel.py` / `snippets_panel_travel.py` — `_trail`, `_MAX_TRAIL_LENGTH = 32`, `_travel_forward`, `action_travel_back` |
| Breadcrumb rendering | `modals/trail_strip.py` `build_trail_strip()` — `TRAIL A › B › C` with middle elision, already pure and shared by two panels |
| Vim `/` `n` `N` search | `widgets/vim_search_controller.py` — a reusable controller with a documented host protocol, already re-hosted by `zoom_panel_search.py` and `_metadata_search.py` |
| One-shot key prefix | `modals/numbered_link_keys.py` |
| Multi-entity divider | `bead/cli_show_batch.py:185` `_show_divider` — `── 2/3 ────────` already renders between beads |
| Media handoff | `graphics/_viewer_launch.py:210` `view_artifact_files` — kitty graphics, mpv, tmux panes, PDF loop |
| **Standalone Textual app run from CLI *and* from ACE** | `MemoryReviewTuiApp` — `memory/cli_review.py:338` calls `.run()`; `agents/_notification_handlers.py:141` calls it inside `with app.suspend():` |
| Ad-hoc selector alphabets to retire | `artifact_files_modal_rendering.py:19`, `runners_modal.py:49`, `agent_neighbor_modal.py:25`, `property_picker_modal.py:24`, `agent_workspace_tmux_modal.py:72` — **five private copies, no shared utility** |

**`jump_hints.py` is the single most important find, and neither prior report surfaced
it.** It already ships the owner's requested alphabet verbatim, plus two things both
reports would otherwise have had to rediscover:

- `match_jump_hint()` returns `PENDING`/`COMPLETE`/`INVALID` against a pending prefix,
  pure and state-free — the exact matcher a painted-label pager needs.
- `normalize_jump_key(key, character)` exists because **Textual may report a shifted
  letter as `event.key == "a"` with `event.character == "A"`.** Any design that uses
  `A-Z` as labels — both prior reports do — is broken without this helper. It is a
  one-line landmine that is already defused in-tree.

Its one limitation is the allocation policy: `build_jump_hint_maps` is **fixed-width** —
one character for ≤62 targets, otherwise *every* label becomes two characters. §4.2
recommends extending it rather than replacing it.

### 1.4 `sase bead show` already renders graph links

Live `sase bead show -p never sase-ug` prints a `LINKS (1)` block with the derived
`← implemented-by · plan:202608/link_rail_every_tab.md` edge, its provenance line, and
its attribution. Graph links are therefore **already in bead output**; the pager does not
need to invent a rail there, only to make the block's refs pressable.

The same output also contains **~13 bare bead ids** (`sase-ug.1` … `sase-ug.10`,
`sase-ug.land`, `sase-ud.3`) that today's scanner sees none of, because
`_FILE_PATH_ALTERNATIVES` requires a `/` or an extension. Bare bead ids are the
highest-value link type in bead output and are currently invisible.

---

## 2. Measurements

All figures below were re-measured for this report using the production
`iter_file_path_matches` scanner plus typed-ref and URL patterns. They closely reproduce
report `__b`'s independent pass; where they differ slightly, the numbers here supersede.

### 2.1 Link density

Corpus: 2,424 Markdown documents under `~/.sase/plans/2026*/` and
`sase/repos/research/2026*/`; 51,694 links; 522,288 sliding 45-line windows.

| Statistic | Value |
| --- | --- |
| Links per document | p50 **15**, p90 48, p99 95, max **187** |
| Links per 45-line screen | p50 **3**, p90 9, p99 18, max **47** |
| Worst screen per document | p50 8, p90 18, p99 32, max **47** |
| Screens with zero links | **20.4 %** |
| Documents whose *worst screen* exceeds 51 links | **0.00 %** |
| Documents whose *worst screen* exceeds 62 links | **0.00 %** |

Two conclusions. First, the owner's requested alphabet is **confirmed by measurement, not
assumed**: single keys carry the overwhelming majority of documents, and `00`–`ZZ` is a
real but rare tail. Second, **no screen in the corpus needs more than 47 labels**, which
is what makes the window-scoped fallback in §4.2 always single-key.

The 20.4 % zero-link figure matters for beauty: absence is common, so a zero-link
document must cost nothing visually — no label column, no `LINKS` row, no reserved gutter.

### 2.2 The alphabet-size trade, measured

The central A-vs-B disagreement was whether to reserve bare alphanumerics for pager
commands. This table settles it. `A` is the single-key alphabet size after reserving
command keys; "docs 100 % single-key" is the share of documents fully labelled without a
two-key tail; "single-key share" is the fraction of *all 51,694 links* that get a
one-keypress label under prefix-free variable-width allocation.

| A | docs 100 % single-key | single-key share of all links |
| --: | --: | --: |
| 47 | 89.6 % | 89.3 % |
| 51 | 91.3 % | 91.2 % |
| 52 | 91.8 % | 91.7 % |
| 56 | 93.3 % | 93.2 % |
| **62** (reserve nothing) | **94.7 %** | **95.0 %** |

**The curve is flat.** Surrendering the entire vim command vocabulary to gain the last
11 label keys buys **3.4 percentage points**. That is a bad trade in a surface whose
primary activity is reading, and it is the decisive argument against report `__a`'s
"reserve no bare alphanumerics" position.

### 2.3 The current `v` render is far past single-key territory

`~/.sase/perf/view_hints_floor_trace.jsonl` records real
`widget.prompt_panel.update_display_with_hints` spans:

```
hints: 924    annotated_chars: 102,541   duration: 36.3 ms  (cache miss)
hints: 1154   annotated_chars: 128,016   duration: 43.0 ms  (family container)
```

An agent detail document produces **924–1,154 hints**: fine for a type-a-number bar,
fatal for painted labels. The pager does not inherit this today because it renders the
*selected files*, not the agent detail document. But if the agent document ever becomes a
pager document (§8, deferred), window-scoped labelling is the only workable scheme.

### 2.4 Process cost

`sase version` from a warm shell: **288 / 299 / 318 ms** wall across three runs. That is
the floor for any `SASE_PAGER="sase pager"` subprocess hop, and it is why `page_or_print`
must call the pager **in-process** when the resolved pager is SASE's own (§6). It also
retires report `__a`'s subprocess-plus-session-manifest handoff: paying ~300 ms and
inventing a serialisation format to do what `MemoryReviewTuiApp` already does with a
`with` statement is unjustified.

---

## 3. Alignment with the `sase-ug` epic

`bead:sase-ug` — "A link rail on every tab", `plan:202608/link_rail_every_tab.md`, phases
1–2 closed, 3–10 in progress — is the adjacent work. **Complementary surfaces, shared
substrate**, with three seams to share and two boundaries the prior reports drew wrongly.

| Dimension | `sase-ug` Link Rail | SASE pager |
| --- | --- | --- |
| Surface | One line above ACE's footer, on all three tabs | A full-screen document view (CLI and ACE) |
| Subject | The **selected entity** in a list | The **content being read** |
| Link source | The typed artifact-link **graph** | **Textual mentions** in the rendered bytes |
| Cardinality | p50 1, p90 2, max 26; ≤9 chips | p50 15, p90 48, max 187; inline |
| Key grammar | `$` prefix + one key | One painted key per link |
| Trail | App-level `_link_trail`, `Ctrl+O` / `Ctrl+Shift+O` | `backspace` (and `ctrl+o` for symmetry) |
| Invisibility | Hard requirement — hidden when the entity has no links | N/A — the pager is opened deliberately |

They answer different questions. The rail answers *"what is this entity linked to?"*; the
pager answers *"what does this text point at?"* A bead's rail shows its `implemented-by`
edge; the pager over that same bead shows its 13 child ids, its plan path, and its GitHub
page URL — none of which are graph edges. **Two key grammars is correct here**, because
the two surfaces have genuinely different key budgets. What must not differ is *where a
key takes you*.

### 3.1 Three seams to share

1. **Ref → destination resolution.** `sase-ug.5` (`subject`) builds an alias-keyed O(1)
   `LinkIndex` and explicitly warns against the O(n) `_known_target_for_ref` scan
   (`relations/artifact_links.py:200`). The pager must consume that index rather than
   build a second one. **Caveat both reports missed:** the plan places `LinkIndex` *on
   the ACE app*, built off-thread from a snapshot. A CLI `sase pager` invocation has no
   ACE app and therefore no index. So the seam is an **interface with two
   implementations** — `resolve_ref(ref) -> LinkTarget | None`, satisfied by the live
   `LinkIndex` inside ACE and by `artifact_cli/references.py:76`
   `resolve_cli_reference()` outside it. Resolution happens on keypress, not on paint, so
   the CLI implementation's cost is acceptable.
2. **Ref → glyph, accent, and short label.** `ARTIFACTS_ICONS` / `ARTIFACTS_ACCENTS` and
   the rail's short-label rule (`bead:sase-u3` → `sase-u3`,
   `stitch:sase-org/sase@f4b827af6` → `sase@f4b827a`) must produce identical output in
   both surfaces. `◈` in purple must mean "bead" everywhere. Assert this with one shared
   test run against both.
3. **Dangling presentation.** Dangling links still count as links: render dim with `⊘`
   and `(missing)`, toast instead of navigating, and **do not mutate the trail** — the
   same vocabulary as `relation_panel.py:236`. Likewise borrow the `⟨ …3 › ✎plan ⟩`
   breadcrumb collapse.

### 3.2 The trail must *not* be one shared object

Report `__b` recommends the pager's `backspace` walk **the same trail object** as
`sase-ug.8`. Checking the plan, that is not implementable as stated, for two reasons:

- **Incompatible payloads.** A `sase-ug` trail entry records
  `(tab, ArtifactEntryTarget, pane query digest, fold state)` — an ACE *selection*
  restore. A pager entry must record `(document identity, section identity, scroll
  offset, search state)` — a *view* restore. These are different types with different
  restore semantics.
- **A direct rule conflict.** The plan states the link trail *"clears when the user
  navigates by any other means, so it never lies about how you arrived."* Opening the
  pager is exactly such a navigation. Under the plan's own rule, entering the pager would
  clear the rail's trail.

The correct synthesis keeps one *conceptual* history without coupling two objects: **the
pager owns its own trail; when the pager's trail is exhausted, `backspace` closes the
pager and returns to ACE**, where `Ctrl+O` continues walking the rail's trail. A user who
presses `$1`, lands in the pager, follows two links, and presses `backspace` three times
ends up back where they started — with two truthful histories rather than one fragile
shared stack.

### 3.3 One overlap to declare

`sase-ug.10` (`land`) retires `beads_open_plan` and `plans_open_bead` as duplicates the
rail generalises. The pager retires the same *class* of thing at the CLI layer:
`_print_or_page`, `_view_files_with_pager`, and the `less` back end of `page_or_print`.
Both are net deletions and they do not collide — but the pager epic should say so
explicitly, so a reviewer does not read two overlapping deletion phases as one being
redundant.

**Sequencing:** do not block the pager on the whole epic. Land against the narrow
`resolve_ref` interface with a `resolve_cli_reference`-backed adapter now, and swap in
`sase-ug.5`'s `LinkIndex` when it lands.

---

## 4. Design decisions

Where the two prior reports disagreed, the decision and its evidence are stated
explicitly.

### D1 — A standalone Textual `App`, run in-process — *agreed*

`SasePager(App[PagerExit])` in a new `src/sase/pager/` package. The CLI calls
`SasePager(document, …).run()`. ACE calls it under `with self.suspend():`.

`MemoryReviewTuiApp` already proves both halves of this exact pattern in this exact tree
(`memory/cli_review.py:338`; `agents/_notification_handlers.py:141`). It buys
`VimSearchController`, Rich renderables, PNG snapshot testing via `just test-visual`, and
headless `Pilot` key tests for free. Textual 8.0.1 is already a dependency; `App.suspend()`
is the officially supported way to yield the terminal to another program, which is also
how media delegation returns cleanly (D7).

**Rejected — subprocess with a session manifest** (report `__a`). It costs ~300 ms per
open (§2.4) and invents a versioned serialisation format for typed targets that
`suspend()` + a direct call passes as live objects. The in-tree precedent makes this
strictly worse.

**Rejected — a raw-terminal ANSI loop** extending `graphics/_viewer_loop_terminal.py`. It
starts faster and owns kitty/mpv, but would need hand-built scrolling, reflow, resize, and
incremental search. Keep it for **media only**.

**Rejected — keeping `less` with a `lesskey` map or a link sidecar.** `less` cannot paint
labels, cannot own a trail, and cannot dispatch a key back to SASE. Even `less` 692's
OSC-8 jump command does not provide a typed entity graph or per-document key legends.

**Rejected — a modal inside the running ACE app.** It solves only ACE; `bead show` and
`sase pager` would need a second host, and it puts pager crashes inside the control
surface.

**Cost to hold:** Textual boot inside `suspend()` is a second alt-screen transition.
Budget **150 ms** and measure it before the ACE phase lands — `MemoryReviewTuiApp` makes
that number obtainable today rather than estimated.

### D2 — The input is a `PagerDocument` of sections, not a string — *agreed*

```python
@dataclass(frozen=True)
class PagerSection:
    identity: str                    # "bead:sase-ug", "file:/abs/path.py"
    title: str                       # rendered in the section rule
    kind: str                        # drives icon + accent
    body: RenderableType | str       # Rich renderable, or ANSI/plain text
    subject_ref: str | None = None   # this section's own artifact ref, if any
    targets: tuple[TypedTarget, ...] = ()   # caller-attached, span-bound (see D3)

@dataclass(frozen=True)
class PagerDocument:
    sections: tuple[PagerSection, ...]
    title: str
    origin: PagerOrigin              # what opened it; seeds the trail and bare-token rules
```

`ctrl+n`/`ctrl+p` needs entity boundaries; the trail needs stable identities; the header
needs a subject. A string has none of these. Every caller can build one cheaply: `sase
bead show` already renders per-bead entries and already draws `── 2/3 ──` dividers
(`cli_show_batch.py:185`); `v` already has a list of resolved paths.

**ANSI bodies are first-class.** `sase bead show` produces styled ANSI, not a renderable.
Parse with `rich.text.Text.from_ansi()`, which yields plain text for scanning *and* style
spans for rendering, so labels can be inserted at exact offsets without re-implementing
SGR parsing. `cli_pager._SGR_RE` becomes unnecessary.

### D3 — The pager owns *scanning*; callers may *attach* typed targets — *resolved*

Report `__a` said callers supply links; report `__b` said "callers never supply links".
**Both are half right, and `__b`'s version is refuted by the code.**

The pager must own the text scanner, because otherwise `bead show` and `v` grow divergent
link behavior and the same bug is fixed twice — and because `sase pager` on arbitrary
stdin gets identical behavior for free, which is most of that command's value. One
scanner, per section's plain text, in precedence order:

1. **Typed artifact refs** — `artifact_ref_operations.py:204` `scan_artifact_refs()` (the
   Rust binding). Highest precedence; already the authority on ref spans.
2. **URLs** — `_HTTP_URL_PATTERN`, currently matched only to be discarded.
3. **File paths** — `iter_file_path_matches()`, unchanged, minus artifact-ref ranges via
   the existing `_matches_outside_artifact_refs`.
4. **Context-scoped bare tokens** — bead ids in a bead document, short shas in a diff.
   Declared per `PagerOrigin`, **never globally**, precisely so a research doc that says
   `sase-core` does not become a false link (§1.4).

But the scanner **cannot** recover what `AgentHintRender` already holds: a
`CommitViewSpec`, a `SlowToolCallReportSpec`, a lazily-materialised memory/glossary
report (§1.2). Those are objects, not substrings. So the contract is:

> The pager discovers every link it can find in text. A caller may additionally attach
> already-typed targets bound to explicit spans. Attached targets win over scanned ones
> on overlap; both share one label sequence in document order.

This is the only formulation that lets `v` keep its commit and report hints while `sase
pager` on a pipe still works with no caller cooperation at all.

**Budget:** reuse `HintContentBudget` and the 128 KB / 5,000-line caps, including the
visible truncation notice. **No I/O to recognise a link:** a label's appearance derives
from the ref string alone; existence checking happens on press, not on paint. This is the
same rule the rail's plan states, and it is what keeps paint time flat.

### D4 — Keys: extend `jump_hints`, reserve the vim vocabulary, never use a timeout

**Reuse, don't rewrite.** `JUMP_HINT_CHARS`, `match_jump_hint()`, and — critically —
`normalize_jump_key()` come from `actions/navigation/jump_hints.py` unchanged. Only the
allocation policy changes.

**Reserve command keys.** The house reading-surface vocabulary is already fixed by
`ZoomPanelModal` (`zoom_panel_modal.py:96-115`): `q`/`escape` close, `j`/`k` scroll,
`g`/`G` top/bottom, `ctrl+d`/`ctrl+u` half-page, `ctrl+n`/`ctrl+p` next/prev,
`y` copy, `E` edit, `r` refresh. Reserving `j k g G q y E r n N` — 10 keys, leaving **52
single-key labels** — costs 2.9 points of coverage (§2.2) and preserves the vocabulary a
user already knows from `Z`, `CommitViewModal`, `GlossaryPreviewModal`, and
`MemoryReviewTuiApp`. Non-alphanumeric commands (`/`, `?`, `backspace`, arrows, space,
`PgUp`/`PgDn`, `[`/`]`) stay free.

Report `__a`'s alternative — reserve nothing, move every command to arrows and Ctrl
chords — breaks `j`/`k`/`g`/`G`/`q` in the one surface a user reads most, to gain
3.4 points. Rejected on the numbers.

**Assignment is document-scoped and stable.** Labels are assigned in document order at
load and never change while the document is open. Scrolling, resize, reflow, and search
never renumber anything. This is the opposite of Vimium's model, and it is right here
because the labels are *always painted* — the owner asked for them "rendered ahead of
time" — and churning labels under a moving viewport would be noise for no benefit.

**Overflow is prefix-free, never timed.** Where a document exceeds the alphabet, reserve
the *last* k alphabet characters as two-key prefixes; a reserved prefix is never itself a
label, so `a` can never be both "link 11" and "the start of `aQ`". k is the minimum that
covers the document: k=1 → 103 labels, k=2 → 154, k=3 → 205, above the corpus maximum of
187. **The first ~49 links — where the eye is — always stay single-key.**

This is a small extension to `build_jump_hint_maps`, which today is fixed-width (all
labels become two characters past 62). Fixed width has a cliff: one extra link doubles
every keystroke in the document. Add the prefix-free variable-width mode as a new
parameter, leave existing callers (`jump_all_modal`, `models_panel_*`) on the current
behavior, and consider migrating them later.

**Report `__a`'s 350 ms timeout is rejected outright.** A timing-dependent input mode
mis-fires under load, cannot be reasoned about, and needs a fake clock to test. Two
schemes already exist that are unambiguous by construction; neither needs a clock.

**Lazy window-scoped fallback, shipped but dormant.** If a document exceeds even two-key
capacity — nothing in the corpus, but a 1,154-hint agent document would — label only the
visible band plus one screen of overscan, re-anchored when the viewport leaves the band,
not per line. **The worst screen in the entire corpus holds 47 links against a 52-key
alphabet, so single keys always win in that mode.** Ship it with the first release even
though nothing triggers it; the moment the agent detail document becomes a pager document
(§8) it is the only workable scheme.

**Rendering.** The label goes *before* the token in `bold #FFFF00` — the existing `[N] `
convention from `_file_path_hints.py:264` — and the token takes the **destination kind's**
accent from `ARTIFACTS_ACCENTS`. The colour says where the key goes before you press it,
exactly as the rail's chips do. Wrapping must never separate a label from its token.

### D5 — `ctrl+n` / `ctrl+p` scrolls a section header to row 0 — *resolved*

The pager is **one continuous scrollable document**. `ctrl+n` scrolls so the next
section's rule sits at row 0; `ctrl+p` does the reverse. At the last section, `ctrl+n`
goes to the end of the document rather than beeping.

The owner's own phrasing — *"re-draw the contents with that file's header at the top of
the screen"* — is a scroll, not a mode. It also means `/` searches the whole document,
`g`/`G` mean the real top and bottom, and the mental model stays "less over a
concatenation", which is exactly what `bat f1 f2 f3 | less` does today. Report `__a`'s
view-swap model (immutable sibling collections, lazy per-entity load) is better for
enormous collections but breaks document-wide search and changes the current `v`
semantics for no user-visible gain; the 128 KB / 5,000-line budget already bounds the
concatenation.

**This deliberately differs from `ZoomPanelModal` and `CommitViewModal`**, which bind the
same chord to a *view swap* because their entities are independently loaded. Note the
divergence in the code so a future reader does not "fix" it.

The section rule is `_show_divider`'s shape, promoted from `cli_show_batch.py` and given a
glyph and accent:

```
━━ 2/3 ━ ◈ bead:sase-ug ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### D6 — The trail is first-class, restoring, and pager-owned

A bounded 32-entry trail, each entry recording `(document identity, section identity,
scroll offset, search state, label anchor)` — enough that `backspace` restores the
**view**, not just the document. Mirrors `_MAX_TRAIL_LENGTH` and
`_travel_forward`/`action_travel_back` in `memory_panel_travel.py`.

- `backspace` back (as asked); `ctrl+o` back and `ctrl+i` forward for vim symmetry.
- A failed or dangling jump does not mutate the trail.
- **History is pushed only after a target loads successfully**, so a crumb never lies
  about where the user has been. While a target is loading, show a transient footer
  status, not a provisional crumb.
- When the trail is exhausted, `backspace` exits the pager (§3.2).

Rendered by extending `modals/trail_strip.py` `build_trail_strip()` with per-entry kind
glyphs and accents, collapsing past three entries to `⟨ …3 › ✎ plan ⟩` to match the rail.
**The strip is absent — not empty — when the trail is empty**, so a first-open pager
wastes no row.

### D7 — Media is delegated, never re-implemented — *agreed*

A link whose target is an image, video, or PDF renders with the existing
`_ICON_BY_VIEW_MODE` glyph (`▨ ▶ ▤`). Pressing it suspends the pager and hands the spec to
`graphics.view_artifact_files` (`_viewer_launch.py:210`), exactly as `_finish_view_request`
does today, then resumes at the same trail entry and scroll offset. Textual cannot do
kitty graphics or mpv; `graphics/` already does both in a tested loop with tmux pane
handling. Do not port it.

### D8 — Search is the existing controller, re-hosted — *agreed*

`widgets/vim_search_controller.py` already provides `/`, `n`, `N`, incremental highlight,
wrap feedback, and a documented host protocol, already re-hosted twice. Host it a third
time. Copy `_STRUCTURAL_SEARCH_EXIT_KEYS`'s idea: structural keys (`ctrl+n`, `ctrl+p`,
`backspace`, `q`) exit search mode rather than typing into it. Because `n`/`N` are
reserved from the alphabet (D4), a label can never shadow a search-navigation key — that
is not an accident, it is why they are reserved.

### D9 — What the pager does not do in v1

- **No editing.** `E` opens `$EDITOR` at the link's file and line via the existing
  `build_editor_args`; `y` copies the canonical ref/path. The pager itself is read-only.
- **No link authoring.** `sase-ug.9`'s `$0` panel owns `add`/`rm`.
- **No `read` graph edges.** `sase artifact read` records a `read` row only under
  `SASE_AGENT` with a resolved agent identity (`artifact_cli/read.py:_should_record_link`).
  The pager is a human surface; recording a read because a human scrolled past a chip
  would pollute the very read model `sase-ug.1` is converging. `page_or_print` already
  declines to page under `SASE_AGENT`; keep that.
- **No bare-key URL launching.** Render and copy URLs, but do not spawn a browser from a
  single keypress in v1. This preserves the current `v` policy.
- **No transitive expansion.** One hop at a time; the trail is the history.
- **No `LINKS` graph rail** until `sase-ug.6` lands one to borrow. Bead output already
  carries its own `LINKS` block (§1.4), and those refs become pressable for free.

---

## 5. What it looks like

Bead document, three sections, two hops deep, 120 columns:

```
 ◈ sase-ug · A link rail on every tab                            2/3 · 41% · ⌘ 88c
 TRAIL  ⬡ sase-ug.6.code  ›  ✎ link_rail_every_tab.md  ›  ◈ sase-ug
 ───────────────────────────────────────────────────────────────────────────────
 CHILDREN
   PHASES
     ✓ [a] sase-ug.1: One projection for the machine-local read model    [CLOSED]
     ✓ [b] sase-ug.2: A stale clone may not prove deletion               [CLOSED]
     ◐ [c] sase-ug.3: Projected edges from facts SASE already owns  [IN_PROGRESS]
     ◐ [d] sase-ug.4: A way to read durable truth and see the drift [IN_PROGRESS]

 LINKS (1)
   ← implemented-by · [e] plan:202608/link_rail_every_tab.md

 PAGE
   [f] https://github.com/sase-org/sase--beads/blob/main/pages/sase-ug/README.md

 PLAN
   [g] plan:202608/link_rail_every_tab.md
   → [h] /home/bryan/.sase/plans/202608/link_rail_every_tab.md
 ───────────────────────────────────────────────────────────────────────────────
 a-z follow · ⌫ back · ^N/^P entity · / search · y copy · E edit · ? keys · q quit
```

Four things to notice, all deliberate:

- `[e]` and `[g]` are the **same ref reached two ways** — the `LINKS` block's edge and the
  `PLAIN` block's citation — and `[h]` is its resolved path. The pager labels all three
  rather than guessing which the user meant; they share one destination but keep their own
  visible occurrence, which is what makes the mapping legible wherever you meet it.
- The trail strip occupies a row only because there *is* a trail.
- The footer is a legend, not decoration, and it changes with availability: no trail → no
  `⌫ back`.
- Bare bead ids `sase-ug.1`–`sase-ug.4` are keyed because `PagerOrigin` is a bead
  document (D3, rule 4). In a research document they would not be.

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

**A zero-link document renders no label column and no trail row at all** — 20.4 % of
screens have no links, so absence is the common case and must cost nothing.

### Visual rules

Beauty here comes from truthful structure, not ornament: one sticky chrome band, one
content surface, one contextual footer; artifact-kind colour in glyphs and chips, never as
large saturated panels; consistent high-contrast label capsules immediately before their
token; loading, missing, external, and media targets each with a distinct small glyph;
full legibility without colour, through glyph and text differences alone. `?` shows the
complete binding set and label legend — do not wrap every document in a permanent
two-line cheat sheet.

---

## 6. The `sase <subcmd>` question

**Answer: yes — add `sase pager`.** The argument against is real: `bead show` and `v` both
get the pager without a command, and a new top-level verb costs help text, completion,
docs, and tests. Three concrete capabilities outweigh it.

**1. It is the thing you put in `$PAGER`.** `cli_pager._resolve_pager_argv()` already reads
`SASE_PAGER` then `PAGER` and execs it with the body on stdin. The moment `sase pager`
exists, `export SASE_PAGER="sase pager"` routes *every* paging SASE command — today
`bead show`, tomorrow whatever else adopts `page_or_print` — through the new pager, using
plumbing that already ships. No config field, no flag, no new mechanism. **That decides
the name**: a `$PAGER` value must honestly be a pager.

**2. Multi-ref reading in one view does not exist today.**

```bash
sase pager bead:sase-ug plan:202608/link_rail_every_tab.md src/sase/cli_pager.py
```

Three heterogeneous artifacts, one document, `ctrl+n`/`ctrl+p` between them, every mention
in all three keyed. `sase artifact read` takes one ref and shells to `less`; `sase bead
show` takes many, but only beads. This is the CLI twin of the `v` flow.

**3. It makes foreign output navigable.**

```bash
git show --stat | sase pager
gh pr diff 1421 | sase pager
```

Every path in a diff becomes a keyed jump into `$EDITOR`. The scanner works on plain text,
so this needs no per-source integration.

**Shape**, following the `cli_rules` memory (options sorted, a short alias for every public
long option, no required options, required values as positionals):

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

**Three implementation notes.** `page_or_print` must detect that the resolved pager *is*
SASE's own and call it **in-process**, both to skip the ~300 ms hop (§2.4) and — more
importantly — to pass the structured `PagerDocument` instead of a flattened string; the
subprocess form exists only for foreign callers and degrades honestly to scan-only. With no
TTY the command must dump plain, so it is safe in a pipeline and safe as an unconditional
`$PAGER`. And the in-process path must never consult `$SASE_PAGER`, while the subprocess
path unsets it in the child env, so `SASE_PAGER="sase pager"` cannot recurse.

**Rejected names.** `sase view` (report `__a`) reads better as a verb but collides
conceptually with `sase artifact open` and `sase artifact read`, which already exist with
different jobs (media viewer, audited read). `sase open` has the same problem. `sase pager`
names the mechanism because **the mechanism is the contract** — it must be a valid `$PAGER`
value, and no other name can be.

---

## 7. Performance and failure behavior

**Budgets.** First chrome paint never waits on file content, syntax highlighting, or graph
enrichment. Scrolling and label handling do no I/O; target p95 under 16 ms. Parse each
section once per content identity/mtime and cache rendered layout by width. Use a
virtualised text widget for very large bodies — never one Textual widget per log line.
Cancel or ignore stale workers when the active location changes.

**Resolution must never block or seize the terminal.** The `tui_perf` memory warns that ref
resolvers may clone repositories, take shared-store locks, or launch a prompting subprocess.
So: input handlers mutate only pending UI state and schedule work; filesystem reads,
Markdown parsing, report generation, and ref resolution run in managed workers; every
completion re-checks the active generation before updating; VCS subprocesses run with
terminal prompting disabled and bounded waits; a resolver needing interactive credentials
returns an actionable error card instead of borrowing the pager's tty.

**Failure behavior.** A pager startup failure falls back to the already-rendered direct
output — never lose command output because the UI could not start. A missing target stays
visible and dimmed with `⊘ (missing)`; activation explains the dead end and does not push
history. A file that changes while open offers a visible reload rather than silently
swapping content under stable labels; a file that disappears renders a tombstone and keeps
its crumb. Search and rendering operate on decoded text with replacement for invalid UTF-8;
binary detection routes away before decoding. The ACE launch uses a direct call, which also
removes today's `shell=True` `quoted_files | less` construction. `Ctrl+C` and termination
restore the terminal and return a structured result.

---

## 8. Sequencing

An epic under a **`beta` feature flag created with `sase flag new`** — exactly the case the
`sase_flags` memory describes, where a landed phase would otherwise expose an unfinished
surface — removed in the final phase by deleting the Off branch.

| Phase | Content | Test |
| --- | --- | --- |
| 1 `primitives` | Extend `jump_hints` with prefix-free variable-width allocation. One `link_scan` module (typed refs → URLs → paths → context-scoped bare tokens) reusing `HintContentBudget`. One `pager_trail` on `memory_panel_travel.py`'s shape, sharing `trail_strip`. Retire the five private selector alphabets. **Net line count near flat.** | Allocator is prefix-free and stable for every document size 0–200; `normalize_jump_key` round-trips every `A-Z` label |
| 2 `document` | `PagerDocument`/`PagerSection`, `Text.from_ansi` ingestion, caller-attached typed targets, adapters from `sase bead show` and from a path list | The same bead renders to the same section set from the CLI and from a fixture |
| 3 `viewer` | `SasePager(App)`: scrolling, section rules, `ctrl+n`/`ctrl+p` scroll-to-header, painted labels, footer legend, `VimSearchController` re-hosted. Not yet wired to any caller | Headless `Pilot` key tests; PNG goldens at 120×40 and 60×30 for zero-link, 3-link, 60-link (two-key tail), and dangling-link documents |
| 4 `follow` | Link press → resolve → open, behind `resolve_ref()`, adapted to `resolve_cli_reference` now. Trail push, `backspace`/`ctrl+o` restore, `⊘` behaviour, media handoff | Every ref kind in both endpoint positions; a dangling ref shows but does not navigate and does not touch the trail |
| 5 `cli` | `sase pager`; `page_or_print` routed in-process when the resolved pager is SASE's own. `--pager` semantics preserved exactly, including `auto` row estimation, `SASE_AGENT` suppression, and foreign-`$SASE_PAGER` override | `tests/test_cli_pager.py` and `tests/test_bead/test_cli_show_pager.py` green except where behaviour intentionally changed; byte-stable direct output |
| 6 `ace` | `v` routes to `SasePager` under `suspend()`. Selected files become sections; typed commit/report targets attach; media still routes to `graphics`; `E`/`y` keep working | The `agents.view_files` trace span still closes; `SASE_TUI_PERF` shows no Agents-tab regression; open-to-first-paint under 150 ms |
| 7 `land` | Delete `_print_or_page`, delete `_view_files_with_pager`, delete the `less` back end of `page_or_print`, point `artifact_text_viewer_command`'s text mode at the pager, remove the flag, close the flag bead. **This phase must be a net deletion.** If it is not, the boundary was drawn wrong | Parity tests for every retired caller |
| 8 `graph` (after `sase-ug.5`) | Swap `resolve_ref` onto the live `LinkIndex`; render a `LINKS` rail only once `sase-ug.6` exists to borrow from | One shared test asserting the pager and the rail resolve the same ref to the same target, glyph, and accent |

**Deferred, worth its own decision later:** putting the agent detail document *itself* in
the pager, so `v` becomes "open this agent in the pager" rather than "pick numbers, then
open files". The 924–1,154-hint measurement (§2.3) says that is where the current flow
hurts most, and window-scoped labelling (D4) is the mechanism that makes it possible. But
it changes a keypath the owner uses constantly, so it deserves its own proposal and its own
goldens, not a rider on this epic.

---

## 9. Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Textual boot inside `suspend()` makes `v` feel slower than `bat \| less` | **High** | Measure before Phase 6 lands; budget 150 ms. `MemoryReviewTuiApp` makes the number obtainable today rather than estimated |
| The pager and the `sase-ug` rail diverge into two link systems | **High** | One `resolve_ref` interface, one glyph/accent table, one dangling vocabulary (§3.1). Assert parity in a shared test |
| Labels shift or mis-fire, so users stop trusting the keys | **High** | Document-scoped stable assignment, prefix-free overflow, **no timeouts** (D4). Test stability across scroll, resize, reflow, and search |
| `A-Z` labels silently fail on shifted keys | Medium | Route every keypress through the existing `normalize_jump_key`; assert every uppercase label in a `Pilot` test |
| A false-positive bare-token link (`sase-core` read as a bead) | Medium | Bare-token recognisers are per-`PagerOrigin`, never global (D3); resolution failure renders `⊘` rather than navigating |
| The scanner is slow on a large document | Medium | Reuse the existing 128 KB / 5,000-line budget and its visible notice; scan at load, never per key |
| Replacing four pagers regresses one caller | Medium | Phase 7 is the only deletion phase; every earlier phase leaves the old path intact behind the flag |
| `SASE_PAGER="sase pager"` recursing into itself | Low | The in-process path never consults `$SASE_PAGER`; the subprocess path unsets it in the child env |
| Two-key labels appear more often than measured | Low | 8.2 % of a 2,424-document corpus, only past link ~49. If it grows, raise k or switch that document to window-scoped labelling — both already built |

---

## 10. Verification

- **Allocator:** prefix-free for every k; stable across scroll, resize, and search;
  deterministic for the same document across runs; boundary cases at 52, 53, 103, 154, 205.
- **Scanner:** every ref kind in both endpoint positions; URLs and typed refs no longer
  swallowed by the path regex; bare-token recognisers fire only in their declared origin;
  caller-attached targets win over scanned ones on overlap.
- **Parity:** the pager and the `sase-ug` rail resolve the same ref to the same target,
  glyph, and accent — one shared test run against both.
- **Trail:** `backspace` restores scroll offset and search state, not just the document; a
  failed jump leaves it untouched; an exhausted trail exits the pager and leaves ACE's own
  trail intact.
- **Zero-link path:** no label column and no trail row, asserted by **pixel equality with a
  document rendered by a build that has no label column at all** — the same strong-form
  assertion the rail's plan uses for its invisibility contract.
- **PNG goldens** at 120×40 and 60×30: zero-link, 3-link, 60-link two-key tail, dangling
  link, deep trail, mid-section-rule, monochrome.
- **CLI:** `tests/test_cli_pager.py` and `tests/test_bead/test_cli_show_pager.py` green;
  non-TTY dumps plain; `SASE_AGENT` still suppresses paging; a foreign `$SASE_PAGER` still
  wins; direct output byte-identical.
- **Terminal restoration** under normal quit, `Ctrl+C`, child failure, and ACE shutdown.
- **Performance:** measure first chrome paint, first body paint, label activation, and
  scroll p95 **separately** — one aggregate startup number would hide whether resolution or
  rendering regressed. Add a `pager.open` `tui_trace` span.
- `just check-full` through `/sase_monitor` before landing.

---

## Recommended solution

Build **`SasePager`, one standalone Textual `App` in `src/sase/pager/`, run in-process by
both the CLI and ACE**, fed a structured `PagerDocument` of typed sections. Add **`sase
pager`** as the public command, chiefly because it is a valid `$SASE_PAGER` value and
therefore routes every paging SASE command through the new pager with plumbing that already
ships, and secondarily because multi-ref reading in one view (`sase pager bead:sase-ug
plan:… src/…`) and keyed foreign output (`git show | sase pager`) are capabilities that do
not exist today.

Make it the default back end for `sase bead show` behind `page_or_print`'s existing
TTY/mode decision, preserving `--pager auto|always|never`, `SASE_AGENT` suppression, and
byte-stable direct output; make `v` on the Agents tab open the selected files as pager
sections instead of `bat | less`, keeping the existing off-pump hint render, the typed
commit/report targets, and the media handoff to `graphics`.

For keys, **extend the allocator that already exists** — `jump_hints.py` ships the exact
requested `0-9`/`a-z`/`A-Z`/`00-ZZ` alphabet, a prefix matcher, and the Textual shifted-key
fix. Reserve the ten house command keys (`j k g G q y E r n N`), leaving 52 single-key
labels; the corpus says that costs under three points of coverage and no screen in it ever
needs more than 47 labels. Assign labels document-scoped and stable, overflow prefix-free
with the last k characters reserved as prefixes, and **never use a timeout**. Ship the
window-scoped fallback dormant, because it is what makes the agent detail document possible
later.

`ctrl+n`/`ctrl+p` scrolls the next section rule to row 0 rather than swapping views, so `/`
and `g`/`G` stay document-wide and the mental model stays "less over a concatenation".
`backspace` walks a 32-entry trail whose entries restore scroll offset and search state, is
pushed only after a target loads, and — when exhausted — exits the pager so ACE's own
`Ctrl+O` trail resumes. Render it with the existing `trail_strip`, absent rather than empty
when there is nothing to show.

Align with `sase-ug` at three seams — one `resolve_ref` interface, one glyph/accent table,
one dangling-link vocabulary — and **not** at the trail, whose payloads are structurally
incompatible and whose "clears on any other navigation" rule the pager would violate. Land
behind a `beta` flag created with `sase flag new`, sequence primitives before viewer, and
make the final phase a net deletion of `_print_or_page`, `_view_files_with_pager`, and the
`less` back end of `page_or_print`.

The result is one intuitive, reliable, beautiful reading surface — built mostly from parts
this repository has already written, tested, and shipped.

---

## Open questions for the owner

1. **`sase pager` vs `sase view`.** This report recommends `pager` because it must double
   as a `$PAGER` value and because `view`/`open` collide with `sase artifact read`/`open`.
   If you would rather have the nicer verb, `sase view` works for everything except the
   `$SASE_PAGER` route — which is the strongest single argument for the command existing.
2. **The reserved-key set.** Ten keys (`j k g G q y E r n N`) → 52 labels, 91.8 % of
   documents fully single-key. Dropping `r` and `E` buys two keys and ~0.9 points; giving
   up all ten buys 3.4 points and the vim vocabulary. Recommendation: keep all ten.
3. **Should `v` eventually open the agent detail document itself?** The largest single UX
   win available (§2.3), and the largest change to a keypath you use constantly. Proposed
   as a separate decision after the file-based flow is proven.
4. **Does the pager render a graph `LINKS` rail before `sase-ug.6` lands one?** This report
   says no — bead output already carries its own `LINKS` block, and shipping a second rail
   implementation to delete weeks later is the one place these two efforts could genuinely
   collide.
