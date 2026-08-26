---
create_time: 2026-08-26
updated_time: 2026-08-26
status: research
tags: [pager, tui, textual, artifacts, links, navigation, cli, ace]
---

# A Custom SASE Pager: From Scrolling Text to Navigating Entities

**Research question:** What should SASE's custom pager be, how should the existing
`sase bead show` pager and the Agents-tab `v` flow converge on it, and is a new
top-level CLI command warranted?

**Scope:** Product and implementation design. This report does not implement the pager.
Repository evidence was checked at `sase@e16872c9d`, the research sidecar at
`2137ce7`, and the live `sase-ug` bead store on 2026-08-26.

---

## Bottom line

Build a small, standalone **Textual entity viewer**, not a more elaborate wrapper
around `less`. Call the public command **`sase view`**. Its core input should be a
structured `ViewerSession` containing one or more typed entities, their renderable
content, and precomputed outbound targets. A path, a bead, an artifact ref, a commit
diff, a generated tool report, and stdin are all entities; a pager page is merely one
rendering of an entity.

This model satisfies all three entry points without making any one of them the
architecture:

- `sase bead show` passes one entity per resolved bead to the viewer. Ctrl+N/Ctrl+P
  changes the active bead and always positions its header at the top. Non-TTY and
  `--pager never` output remain ordinary, stable stdout.
- Agents-tab `v` opens the selected agent as the root entity with the links that the
  existing hint renderer already discovered. The user follows a visible hint with one
  key instead of typing a numeric selection and Enter into a temporary input bar.
- `sase view TARGET...` provides a useful public front door for paths, typed artifact
  refs, bead IDs, and `-` for stdin. It is also the manual smoke-test and debugging
  surface for the same engine embedded by the other two flows.

The viewer should have a fixed breadcrumb/header band, one scrollable content region,
and a compact footer. Link traversal pushes a local history entry; Backspace returns
and restores the prior entity and scroll position. The initial entity collection is a
separate concept: Ctrl+N/Ctrl+P moves among siblings and resets the new entity to its
header. This separation prevents “next file” from corrupting “how did I get here?”
history.

The in-progress `sase-ug` epic is complementary. Its Link Rail owns navigation among
selected entities *inside ACE*, including cross-tab landing and the app-level
Ctrl+O/Ctrl+Shift+O trail. The pager owns navigation *inside a suspended, standalone
viewing session*. It should consume `sase-ug`'s planned canonical `LinkSubject` and
O(1) `LinkIndex` when available, but it must not duplicate the Link Rail, its `$`
grammar, or its ACE trail.

## 1. What SASE has today

### 1.1 `sase bead show` has a reusable paging decision, not a custom pager

Commit `2ed9dc7c9` added multiple-ID rendering and `src/sase/cli_pager.py`.
`page_or_print()` currently:

- preserves direct stdout when output is redirected, `TERM` is absent or `dumb`,
  `--pager never` is selected, or auto-mode output fits;
- disables automatic paging during a SASE agent run;
- resolves `SASE_PAGER`, then `PAGER`, then `less`;
- adds `less -R`, and `-F` in auto mode; and
- sends one already-concatenated string to the child process.

That is a good compatibility shell. The problem is the last step: entity boundaries,
headers, and link metadata have already been flattened. `handle_bead_show()` in
`src/sase/bead/cli_query.py` resolves a structured `ShowBatch`, renders one `body`, and
only then calls `page_or_print()`. A custom viewer cannot implement reliable
Ctrl+N/Ctrl+P entity jumps by scraping separators back out of that body.

The correct refactor is to keep the current TTY/mode decision and direct-output path,
but give the paging branch a structured batch. Direct output may continue to concatenate
the exact existing renderings.

### 1.2 Agents-tab `v` already does most of the hard discovery work

The `v` path is spread across `src/sase/ace/tui/actions/hints/_files.py`,
`_processing.py`, and the prompt-panel hint renderers. For an Agent it already:

1. defers the expensive annotated render outside Textual's serial message pump;
2. revalidates the selected agent after the await;
3. discovers ordinary paths relative to the agent's workspace;
4. carries registered artifact files and commit `CommitViewSpec` records;
5. creates lazy specs for tool-call, memory-read, and glossary-read reports;
6. excludes HTTP URLs and avoids double-counting file-like text inside typed artifact
   refs; and
7. returns mappings separate from rendered hint text.

After that careful preparation, `_view_files_with_pager()` discards the structure and
runs `bat ... | less -R` or `cat ... | less`. A mixed media selection takes a second
route through the terminal artifact viewer.

This is the best seam for the new feature. Extract the existing pure discovery/render
work into a `PagerDocument` builder. The ACE detail panel and the custom viewer should
consume the same result. Do not add another regex pass over ANSI text after launch.

The current modal input grammar supports numeric selections, ranges, `@` to open in an
editor, and `%` to copy. Direct browsing makes up-front multi-selection unnecessary,
but the useful secondary actions should remain available as punctuation prefixes:
`@` then a displayed link code opens that target in the editor; `%` then a code copies
its canonical ref/path. Bulk editing can remain in the existing flow until there is
real demand for it in the viewer.

### 1.3 The artifact viewer is valuable, but is not the text pager substrate

`src/sase/ace/tui/graphics/` already has a terminal artifact sequence loop. It handles
images through Kitty, video through `mpv`, PDF/Markdown rendering, tmux panes, zoom,
and `n`/`p` document movement. Text mode still shells out to `bat`/`less`, while the
outer sequence loop reads raw terminal keys itself.

Reuse its **media detection and rendering adapters**. Do not extend its raw `termios`
loop into the main pager. Adding reflowing text, search, asynchronous artifact
resolution, stable inline link chips, breadcrumbs, resize behavior, and accessible
help would recreate a TUI framework one feature at a time. From the custom pager,
media should be a leaf action: suspend the Textual viewer, delegate to the established
media renderer/player, then return to the same breadcrumb and document state.

### 1.4 Artifact viewing is currently split across three implementations

There are already three paging/viewing policies:

- `src/sase/cli_pager.py` for `bead show`;
- `_print_or_page()` in `src/sase/artifact_cli/read.py`, which independently chooses
  `less` or `bat`; and
- the ACE artifact-file viewer and its text/media sequence loop.

The custom viewer should become the single text-viewing engine. `sase artifact read`
should perform its audit and consumption recording first, then pass the resulting
document to that engine. `sase artifact open` can continue to be the external/native
viewer verb for binary artifacts, but text refs should eventually delegate to
`sase view` as well.

### 1.5 The `sase-ug` epic defines the cross-surface contract

Live `sase bead show -f json -p never sase-ug` reports the in-progress epic **“A link
rail on every tab”**, backed by `plan:202608/link_rail_every_tab.md`. Its phases cover:

- a convergent machine-local artifact-link read model;
- freshness-safe deletion;
- projected edges from facts SASE already owns;
- a store-versus-index truth reader;
- one canonical selected-entity subject and an O(1) index;
- the read-only Link Rail;
- the `$` jump grammar;
- a cross-surface trail;
- the `$0` details panel; and
- duplicate retirement and landing.

The [consolidated Link Rail research](link_rail_every_tab/link_rail_every_tab.md)
measured a median graph degree of 1, p90 of 2, and maximum of 26; 99.8% of linked
entities had at most nine graph links. It also established stable semantic ordering,
perspective-corrected relation labels, honest dangling targets, and “no I/O on the
render path” as contracts.

The pager should reuse those outputs, with two strict ownership boundaries:

| Concern | Owner |
| --- | --- |
| Selected ACE row → canonical ref | `sase-ug` `LinkSubject` adapter |
| O(1) graph neighborhood and ordering | `sase-ug` `LinkIndex` |
| `$N`, `$0`, and cross-tab landing | ACE Link Rail |
| Ctrl+O/Ctrl+Shift+O across ACE surfaces | ACE app-level link trail |
| Inline paths/refs inside one viewed document | custom pager session |
| Ctrl+N/Ctrl+P among the pager's supplied entities | custom pager session |
| Backspace through documents opened in the pager | custom pager session |

When the pager exits, ACE selection and the ACE link trail remain unchanged. This
keeps the histories truthful rather than joining two processes with a fragile shared
back stack.

## 2. Why the viewer should be built with Textual

### 2.1 Alternatives considered

| Alternative | Strength | Why it loses |
| --- | --- | --- |
| Generate a `lesskey` file and keep `less` | Small change; preserves familiar search and scrolling | Dynamic typed targets, asynchronous ref resolution, visible breadcrumbs, stable per-document chips, and media return all sit outside `less`'s document model. The result would be a controller wrapped around a pager, with two sources of navigation truth. |
| Extend the existing raw artifact sequence loop | Reuses media and already has document movement | It would need to grow text layout, resize, search, async workers, focus, notifications, tests, and accessibility. Text still delegates to `less`, so link traversal remains split. |
| Push a modal/screen inside the running ACE app | No subprocess handoff | It only solves ACE. `bead show` and `sase view` would need another host, and the modal would share ACE's event-loop/performance risk. It also makes an eventual crash capable of taking down the control surface. |
| Build a standalone Textual app with a typed session | One engine for CLI and ACE; existing dependency, themes, workers, testing, resize, and suspension | Requires a small session handoff protocol and careful large-document rendering. This is bounded and testable. |

The official `less` documentation describes strong backwards movement, search,
multi-file position memory, and configurable keys, all of which should inform the
baseline pager feel. It also describes `less` as a text-only pager rather than a
windowing system. Even the 2026 release's new OSC-8 jump command does not provide a
typed entity graph, per-document dynamic key legends, or breadcrumb state. See the
[official less FAQ](https://www.greenwoodsoftware.com/less/faq.html) and
[less 692 release notes](https://greenwoodsoftware.com/less/news.692.html).

Textual is already a SASE dependency and supplies the exact lifecycle pieces this
viewer needs:

- an app may temporarily yield the terminal to another application with
  `App.suspend()`, which is the right way for the pager to invoke the existing media
  viewer or an editor ([Textual App guide](https://textual.textualize.io/guide/app/#suspending));
- synchronous file/ref work can run in thread workers, with UI updates marshalled back
  to the main thread ([Textual Workers guide](https://textual.textualize.io/guide/workers/#thread-workers));
- `MarkdownViewer` supports GFM-like rendering, emits `LinkClicked` events when
  automatic opening is disabled, and already models back/forward document navigation
  ([Textual MarkdownViewer](https://textual.textualize.io/widgets/markdown_viewer/)); and
- Textual's test pilot can drive keys and terminal resizes headlessly
  ([Textual testing guide](https://textual.textualize.io/guide/testing/)).

Use `MarkdownViewer(open_links=False)` where its rendering is appropriate, but keep
history and target resolution in SASE's session model. Its built-in history knows
Markdown paths; it does not know `bead:`, `agent:`, `stitch:`, generated reports, or
media leaves.

## 3. Product model: an entity viewer that can page text

The key design decision is to model what the user is looking at before choosing how to
draw it.

```text
ViewerSession
├── collection: [PagerEntity, PagerEntity, ...]
├── active_index
├── trail: [ViewLocation, ...]
├── forward_trail: [ViewLocation, ...]
└── resolver/context

PagerEntity
├── stable identity: canonical ref, canonical path, or generated session id
├── title, kind, accent, icon
├── body source: text / Markdown / ANSI Rich text / generated loader
├── outbound PagerLinks in stable order
└── content state: scroll offset, search, loading/error

PagerLink
├── code
├── visible span(s)
├── target descriptor
├── source: inline | graph | commit | report | media
└── capabilities: view | edit | copy | external
```

An initial collection is immutable for the life of that location. Ctrl+N/Ctrl+P moves
within it. Following a link creates a new location, normally with a one-entity
collection; a grouped graph link or an explicitly supplied set may create a larger
one. Backspace pops the prior location. This yields predictable behavior in all cases:

- `sase bead show sase-a sase-b` starts with a two-bead collection.
- Ctrl+N redraws `sase-b` at its header; Ctrl+P returns to `sase-a` at its header.
- Following `plan:...` from `sase-a` pushes a one-plan location.
- Backspace restores `sase-a`, including the scroll position from which the plan was
  opened.
- Following a grouped “14 stitches” graph chip opens a 14-stitch collection; Ctrl+N
  then moves among stitches without changing the breadcrumb trail.

### 3.1 Visual anatomy

```text
╭─ SASE VIEW ─────────────────────────────────────────────── 2 / 4 ─╮
│ ⌂ agent sase-ug.7  ›  ✎ plan link_rail_every_tab  ›  λ cli_pager.py │
├─────────────────────────────────────────────────────────────────────┤
│ λ  src/sase/cli_pager.py                              Python · 201L │
│ ─────────────────────────────────────────────────────────────────── │
│ """Terminal pager support for already-rendered CLI text."""        │
│                                                                     │
│ from __future__ import annotations                                  │
│ ...                                                                 │
│ See [0] plan:202608/link_rail_every_tab.md for the cross-tab rules. │
├─────────────────────────────────────────────────────────────────────┤
│ ↑↓/Space scroll   ^N/^P entity   ⌫ back   / find   Esc close       │
╰─────────────────────────────────────────────────────────────────────╯
```

The breadcrumb and entity header are sticky. The body is the only scrolling region.
Each breadcrumb segment uses the same artifact-kind icon/accent vocabulary as ACE;
middle segments collapse to `… N` before the current and root segments disappear.
When a target is loading, the new crumb is not committed yet: show a transient status
in the footer, resolve in a worker, and push history only after success. A failed or
dangling traversal never lies about where the user has been.

The footer is contextual and minimal. Help (`?`) can show the full binding set, target
legend, and secondary actions. Do not put a permanent two-line cheat sheet around every
document.

### 3.2 Pager controls must avoid bare alphanumerics

The requested link alphabet consumes every digit and letter. That collides with the
traditional `j`, `k`, `q`, `g`, `G`, `n`, and `p` pager commands. Skipping those keys
would violate the requested ordering, while dynamically changing their meaning at link
27 or link 37 would be unreliable.

Reserve bare alphanumerics for visible link codes throughout the viewer. Use:

| Gesture | Action |
| --- | --- |
| Up/Down, mouse wheel, Ctrl+E/Ctrl+Y | Scroll by line |
| Space / Shift+Space, PgDn/PgUp | Scroll by page |
| Home/End | Top/bottom of current entity |
| Ctrl+N / Ctrl+P | Next/previous entity; redraw at header |
| Backspace | Back through successful link traversals |
| Ctrl+Right | Forward through a popped traversal, where terminals support it |
| `/` | Search current entity |
| F3 / Shift+F3 | Next/previous search match |
| `@` + code | Open target in `$EDITOR` |
| `%` + code | Copy canonical ref/path |
| `?` | Help and complete link legend |
| Esc / Ctrl+C | Close viewer |

This is less Vim-like than `less`, but it is internally consistent and leaves every
requested direct link code live. The footer makes the difference discoverable.

## 4. Link assignment and traversal

### 4.1 Stable ordering and deduplication

Codes are scoped to the active entity, not the whole session. Assign them once after
the entity's bounded discovery pass and never change them because of wrapping, resize,
scrolling, or a later background label enrichment.

Order targets as follows:

1. explicit inline links in visual document order;
2. existing Agents `v` hints in their already-rendered order;
3. commit/report/artifact-file header targets in displayed order; and
4. graph neighbors from `sase-ug`'s `LinkIndex`, preserving its semantic relation sort.

Repeated occurrences of the same canonical destination reuse one code. Each occurrence
still renders the chip ahead of the link, so the mapping is visible wherever the user
encounters it. A visually identical token that resolves differently because its base
directory differs is not deduplicated.

### 4.2 Required alphabet

Let the alphabet be:

```text
0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ
```

The first 62 unique targets receive the single characters in that order. Target 63
receives `00`, then `01` through `0Z`, `10`, and eventually `ZZ`. This supports 3,906
targets before a three-character extension would be needed. At that scale the viewer
should refuse to paint more chips and offer a searchable target palette; thousands of
inline links are not navigable merely because they have codes.

There is one unavoidable ambiguity in the requested scheme: once `00` exists, `0` is
both a complete code and the prefix of another complete code. No input parser can both
activate `0` immediately and wait to see whether the user intends `00`.

The least surprising spec-faithful behavior is:

- for 62 or fewer targets, every code fires immediately;
- for more than 62, a first alphanumeric key enters a visibly rendered pending state
  (for example `link 0…`) for roughly 350 ms;
- a valid second key within the window selects the two-character code;
- timeout selects the one-character code; Backspace/Esc cancels the pending code; and
- tests use a fake clock—never real sleeps—to prove boundary behavior.

This delay exists only on the rare entity that actually needs two-character labels.
The live artifact graph measured by `sase-ug` tops out at 26 neighbors, so graph links
do not currently trigger it. Large agent transcripts are the realistic path to the
edge case.

### 4.3 Target coverage

| Target | Source of truth | Viewer behavior |
| --- | --- | --- |
| Ordinary path mentioned by an Agent | Existing workspace-aware `v` hint mapping | Load as text/Markdown/source, or delegate as media. Missing paths render a dead-end card without changing history. |
| Registered artifact file | Existing `ArtifactFile` record and path/kind metadata | Use stored/live path policy already owned by artifact-file facades; media delegates to existing renderer. |
| `plan:`, `research:`, and plugin document refs | Canonical artifact resolver | Resolve in a bounded, non-prompting worker; load document text and graph neighbors. |
| `bead:` | Bead read view/detail renderer | Render a bead entity directly; do not require scraping its generated Markdown page. |
| `agent:` | Agent catalog and published page/cache | Render an agent summary/transcript entity with its own hints when available. |
| `patch:` | Patch parser/view model | Render the Patch entity and its paths/stitches as typed links. |
| `stitch:` / commit hint | Existing artifact entry or `CommitViewSpec` | Render metadata plus diff as one entity; preserve parent/repo context. |
| Tool-call, memory-read, glossary-read report | Existing lazy report spec | Materialize off-thread, then load the produced report as a generated entity. |
| Image/video/PDF | Existing artifact media adapter | Suspend the pager, view/play externally or through Kitty, then resume at the same location. |
| HTTP(S) URL | Markdown/text token | Render normally and make it copyable; do not bind bare-key external launches in v1. This preserves the current `v` policy and avoids surprising browser execution. |
| Internal Markdown anchor | Parsed Markdown document | Scroll within the current entity without adding a breadcrumb hop. |

Typed artifact refs must be parsed before ordinary path hints, matching the existing
Agents renderer's overlap rule. Initial CLI arguments should resolve with this
precedence: `-` stdin; an existing filesystem path; a syntactically valid typed ref
(leading `@` accepted and normalized away); then a full/shorthand bead ID. Ambiguity
must produce candidates rather than guess.

### 4.4 Resolution must never block or seize the terminal

The TUI performance memory correctly warns that ref resolvers may clone repositories,
acquire shared-store locks, or launch a subprocess that prompts. The pager is a separate
Textual app, but the reliability rule remains:

- input handlers mutate only pending UI state and schedule work;
- filesystem reads, Markdown parsing, report generation, and artifact resolution run
  in managed workers;
- every completion checks the active entity/generation before updating;
- VCS subprocesses run with terminal prompting disabled and bounded waits;
- a resolver that needs interactive credentials returns an actionable error card
  instead of borrowing the viewer's tty; and
- history is pushed only after a target has loaded successfully.

For initial `sase view` targets, resolution can happen before first paint only when it
is cheap and local. Otherwise paint the chrome and target title immediately, then load
the body. For `bead show`, the bead read has already happened; do not resolve it again.

## 5. The `sase view` command is genuinely useful

Add the command.

```text
sase view TARGET [TARGET ...]
sase view -
```

Examples:

```bash
sase view README.md pyproject.toml
sase view bead:sase-ug plan:202608/link_rail_every_tab.md
sase view @research:202608/link_rail_every_tab/link_rail_every_tab.md
git show --stat | sase view -
```

`view` is better than `pager` as the public verb:

- it names the user's intent rather than the rendering mechanism;
- it matches the existing `v` action language;
- it remains sensible for images, typed refs, commits, and generated entities that are
  not just text streams;
- it gives users a direct way to reopen a ref without remembering whether `artifact
  read`, `artifact open`, `bead show`, or a native viewer owns its kind; and
- it provides the stable manual and automated launch surface that the ACE integration
  otherwise would have to hide behind an internal module command.

Keep its first version small. `TARGET` is positional because the command cannot run
without it (except implicit stdin when stdin is not a TTY). Useful public options are
`-n/--no-links` and `-t/--title` for stdin/generated content. Do not add rendering knobs
until a real use case appears. An internal `--session-manifest` used by ACE does not
need a short alias under the CLI rules because it is a subprocess protocol, not a
public option.

When stdout is not a TTY, `sase view` writes plain entity content in argv order with
stable separators and no chrome. That makes it composable and testable. The command is
read-only: it does not create `read` graph edges on its own. If `sase artifact read`
invokes the viewer, that command performs the audit before launch.

## 6. Integration design

### 6.1 One engine, two launch modes

Expose a library entry point roughly like:

```python
def view_or_print(
    session: ViewerSession,
    *,
    mode: PagerMode,
    direct_renderer: Callable[[ViewerSession], str],
) -> ViewerResult: ...
```

From an ordinary CLI command, this can call `SaseViewerApp(session).run()` in-process.
From ACE, do **not** try to run a second Textual app inside ACE's active asyncio loop.
Textual officially supports suspending one app while another terminal application
runs. ACE should:

1. finish its existing asynchronous hint preparation;
2. write a versioned session manifest and any generated body to a mode-0700 temporary
   directory;
3. enter `with self.suspend()`;
4. launch `sase view --session-manifest <path>` without a shell;
5. delete the temporary directory in `finally`; and
6. refresh the original Agent detail after resume.

The manifest is a private, schema-versioned transport record, not the domain model and
not a public file format. It should carry canonical identities, source descriptors,
preassigned links/spans, and only the generated text that the child cannot reproduce
cheaply. Never serialize arbitrary callables or trust a manifest owned by another user.

### 6.2 `sase bead show`

Refactor `render_show_batch()` internally to retain per-bead renderings:

```text
ShowBatch
  -> tuple[RenderedBead]
  -> tuple[PagerEntity]
  -> built-in viewer (TTY + paging decision)
  -> existing concatenated bytes (direct mode)
```

Each bead entity gets:

- identity `bead:<full-id>`;
- the current rich/full rendering;
- structured children, plan, ref, artifact-neighborhood, page, and creator targets;
  and
- its own header, so changing entities does not depend on terminal-row estimates.

Preserve the current contracts: `--pager auto|always|never`, auto's TTY/height and
`SASE_AGENT` behavior, errors printed after the pager returns, color/style/wrap
semantics, and byte-stable direct output. JSON and compact formats may use the viewer
when explicitly forced, but full format is the enhanced default use case.

The built-in SASE viewer should be the default when neither pager environment variable
is set. Preserve `SASE_PAGER` and `PAGER` as explicit external overrides; an external
override intentionally gives up structured navigation. Empty `SASE_PAGER` continues to
disable paging. This keeps the recent Unix compatibility contract while ensuring that
both `bead show` and `sase view` use the same enhanced pager by default.

### 6.3 Agents-tab `v`

For the first ACE use case, change the interaction from “annotate, prompt for numbers,
then page selected files” to “open an annotated Agent entity.” Specifically:

1. preserve the current pump-free hint render and selection-generation guards;
2. extend `AgentHintRender` to return a serializable document body and typed targets,
   not only integer/path dictionaries;
3. show the existing hint chips ahead of paths/commits/reports in the pager body;
4. launch the session rooted at the selected agent;
5. use bare displayed codes to traverse immediately;
6. materialize lazy reports only when followed; and
7. delegate media leaves while keeping the pager's breadcrumb state.

This removes the temporary `HintInputBar` from the Agents `v` happy path. The Patch
`v` path can migrate later using the same builder after the Agent experience is proven.
Editor/copy prefixes preserve the high-value old actions; numeric range syntax and bulk
selection can remain legacy-only until there is evidence they are needed.

### 6.4 `sase-ug` integration timing

Do not make the pager depend on unfinished epic phases merely to ship file navigation.
Define a small `GraphLinkProvider` protocol returning already-ordered `PagerLink`
descriptors. Initially it may return nothing. Once `sase-ug`'s `subject` phase lands,
adapt its `LinkIndex` directly. No second aggregate scan, alias index, or relation sort
belongs in the pager.

If implementation overlaps the active epic, rebase integration only at these seams:

- artifact-kind icon/accent vocabulary;
- canonical target identity;
- ordered graph-neighbor snapshot; and
- dangling/missing presentation.

The pager's inline link codes remain bare (`0`, `a`, `A`, `00`); ACE's graph rail
remains `$1`, `$$`, `$0`. They occur in different applications and should not be made
artificially identical.

## 7. Performance, robustness, and beauty are the same design problem

### 7.1 Performance budgets

- First chrome paint should not wait on file content, syntax highlighting, or graph
  enrichment.
- Scrolling and link-key handling must do no I/O and target p95 under 16 ms.
- Parse each entity once per content identity/mtime; cache rendered layout by width.
- Keep link discovery bounded by the existing plain-render byte/line caps. Show a
  visible “link scan truncated” note rather than silently implying completeness.
- Use a virtualized text widget for very large plain/source documents. Do not construct
  one Textual widget per log line.
- Cancel or ignore stale workers when the active location changes.
- Preserve one scroll/search state per `ViewLocation`; Ctrl+N/Ctrl+P explicitly reset
  the destination to its header, while Backspace restores prior state.

### 7.2 Failure behavior

- A viewer startup failure falls back to the already-rendered direct output. Never lose
  command output because the UI could not start.
- A missing link target stays visible, dimmed with the same `⊘ (missing)` vocabulary
  planned by `sase-ug`; activation explains the dead end and does not push history.
- A file that changes while open offers a visible reload action; it is never silently
  replaced beneath stable hint codes.
- A file that disappears renders a tombstone card and retains the breadcrumb so the
  user can go back.
- Search and rendering operate on decoded text with replacement for invalid UTF-8;
  binary detection routes away before decoding.
- The ACE manifest launch uses argv, never `shell=True`. This also removes the current
  `quoted_files | less` shell construction from the Agents path.
- Ctrl+C and termination restore the terminal, clean temporary files, and return a
  structured result to the caller.

### 7.3 Visual rules

Beauty here should come from truthful structure, not ornament:

- one sticky chrome band, one content surface, one footer;
- artifact-kind color appears in icons/chips, not as large saturated panels;
- link chips use a consistent high-contrast capsule immediately before the target;
- breadcrumb segments show canonical short labels and expose the full ref in help;
- wrapping never moves a chip away from its target;
- resize never renumbers links;
- loading, missing, external, and media targets have distinct small glyphs; and
- terminals without color remain fully legible through glyph and text differences.

## 8. Verification strategy

### Pure model tests

- alphabet boundaries: `9 → a`, `z → A`, `Z → 00`, `0Z → 10`, final `ZZ`;
- deduplication reuses a code while preserving every visible occurrence;
- resize/layout never changes codes;
- fake-clock tests for the >62-link timeout and cancellation;
- initial collection navigation versus breadcrumb history;
- Ctrl+N/Ctrl+P resets to header; Backspace restores prior scroll/search state;
- failed and dangling resolution leaves trails untouched; and
- artifact-ref parsing wins over overlapping file-path syntax.

### Loader and resolver tests

- ordinary relative, absolute, home-relative, missing, and recycled-workspace paths;
- every builtin artifact kind and one plugin document kind;
- VCS-backed materialization with prompting disabled;
- bead and Patch renderers remain structured rather than page-scraped;
- lazy report generation and failure;
- commit diff, image, video, PDF, Markdown, source, log, and invalid UTF-8;
- HTTP links are not activated by bare codes; and
- no viewing path writes graph/audit state unless the caller is `artifact read`.

### Textual pilot and visual tests

- drive every binding, including Backspace and Ctrl+N/Ctrl+P;
- resize at 60×20, 80×24, 120×40, and a wide terminal;
- snapshots for one link, mixed link kinds, collapsed breadcrumbs, loading, missing,
  two-character pending input, monochrome, and search;
- assert the current link chip remains adjacent after reflow; and
- verify worker completion for an old generation cannot replace the active document.

### End-to-end integrations

- `sase bead show` auto/always/never, one/many/`..`, redirected stdout, missing IDs,
  external pager override, and viewer startup failure;
- Agents `v` on a live agent, family, report, commit, normal file, and mixed media;
- editor/copy prefixes and return from delegated media;
- `sase view` paths, refs, stdin, non-TTY stdout, and ambiguous shorthand; and
- terminal restoration under normal quit, Ctrl+C, child failure, and ACE shutdown.

Run the existing TUI performance instrumentation around viewer launch and measure
first chrome paint, first body paint, link activation, and scroll p95 separately. A
single aggregate startup number would hide whether resolution or rendering regressed.

## 9. Suggested implementation sequence

1. Introduce the pure session/entity/link model and base-62 code allocator, with model
   tests and no UI.
2. Build the standalone Textual shell for preloaded text/Markdown entities, local
   collection navigation, search, breadcrumbs, and Backspace.
3. Add `sase view` with path/ref/stdin loaders and non-TTY direct rendering.
4. Refactor `cli_pager.py` into the common paging decision plus built-in viewer launch;
   migrate `bead show` while proving direct output is unchanged.
5. Extract Agents hint rendering into a typed `PagerDocument`, add the secure session
   handoff, and migrate the Agents `v` path.
6. Reuse artifact media delegates and add commit/report entities.
7. Adapt the landed `sase-ug` `LinkIndex` through `GraphLinkProvider`; do not implement
   a temporary second graph index.
8. Migrate `sase artifact read` text paging and then `artifact open` text behavior,
   deleting duplicate `less` selection only after parity tests pass.
9. Evaluate Patch-tab `v` migration after real use of the Agent flow.

Feature-flag the ACE integration and built-in default separately so the viewer can be
exercised through `sase view` before it becomes the automatic `bead show` or Agent
experience. Remove both flags only after terminal restoration, direct-output parity,
and visual/performance gates pass.

## Recommended solution

Implement **`sase view` as a standalone Textual entity viewer backed by a reusable,
structured `ViewerSession` model**. Make that engine the default pager for structured
`sase bead show` output, preserving direct stdout and explicit external-pager overrides.
For the Agents tab, make `v` open the selected Agent as an annotated root entity instead
of opening a numeric input bar; reuse the existing hint discovery for paths, artifact
files, commits, and generated reports, and traverse displayed targets with the requested
`0-9`, `a-z`, `A-Z`, then `00-ZZ` codes.

Use Ctrl+N/Ctrl+P for immutable sibling collections, Backspace for a visible local
breadcrumb trail, arrows/Space/PgUp/PgDn for scrolling, and Esc/Ctrl+C for exit so every
bare alphanumeric remains available to link traversal. Resolve targets off-thread,
commit history only after successful loads, delegate media to the existing artifact
viewer under `App.suspend()`, and consume `sase-ug`'s canonical subject/index rather
than building another graph path. This yields one intuitive, reliable, and visually
coherent viewer without coupling CLI paging to ACE or duplicating the active Link Rail
epic.
