# Memory history in the SASE TUI: a native inspector built on the pager

Independent research by **cdx**, 2026-10-02. Prepared for the `research.3c` swarm.

## Decision brief

**Build an integrated, two-pane history inspector within the existing Memory surface, backed by the existing Rust history service and the pager's mountable `PagerView`.** The left pane selects versions or changed subjects; the right pane previews the exact document or word diff. Keep the standalone pager as the full-screen reading surface. Start by repairing the existing entry points and freshness handling.

This is an extension of a substantial implementation, not a new history subsystem. Epic **sase-1dr is closed** and already shipped a Memory card History row, `H` for subject history, `C` for a cross-file changes feed, a timeline picker, version stepping, word diffs, and historical link resolution. The user is right that the pager owns history reading today; the TUI already has entry-point code, but those entry points are thin and, at the inspected revision, broken in a reproducible way. [Epic bead][epic] and [history documentation][history-doc].

The best next investment is making the history easy to discover, inspect, and trust while retaining one implementation of document reading. A second Markdown viewer, a Git log tab, or a new persistence system would add maintenance without addressing that interaction problem.

## Evidence and research boundaries

I investigated independently. I did not read the other four researchers' reports, chats, summaries, or findings. Inputs were the user's request, the audited epic and approved plan, existing follow-up beads created during that epic's landing, source code in the current workspace and an audited `sase-core` checkout, existing screenshot goldens, small headless Textual probes, and primary external documentation.

Inspected source revisions:

- `sase`: `45f165b6d52dddd812e249fe929c80a20520da4d`.
- `sase-core`: `926edfb8baa1d8e3ba4242156961905595d0faf9`.
- Installed Textual for the probes: **8.0.1**.
- Approved design artifact: `plan:202609/memory_history.md`, accessed through `sase artifact read`.
- Existing follow-up beads: `sase-1e5`, `sase-1e6`, `sase-1e7`, and `sase-1ea`, accessed through `sase bead read`.

The report distinguishes **observed behavior**, **source-review findings**, and **proposed behavior**. Performance numbers quoted from the epic/docs are prior measurements, not fresh benchmarks. Screenshot observations concern deterministic fixtures, not a capture of Bryan's running TUI. I did not implement product changes or run the repository's full verification gate for this research-only deliverable.

## 1. What exists, and what should be preserved

The approved epic deliberately made **time an axis of a document**. Its core model is good:

| Existing capability | Design consequence |
| --- | --- |
| Git is the committed-history store; an incremental, disposable Rust index holds metadata | Keep Git authoritative; UI state must never become a second history store. |
| Logical subjects survive renames and deletions | Select by subject identity, not current filename alone. |
| Notes, web descriptors, strands, generated notes, instructions, and shim divergence are classified | Present their different meanings rather than flattening them into filenames. |
| `now`, staged content, and committed versions are distinct | Uncommitted content must never acquire a fabricated committed ordinal. |
| The pager supports read/diff views, folds, search, anchoring, trails, historical links, and theme-aware past cues | Reuse these behaviors for the inspector preview. |
| Timeline picker rows include summaries, frontmatter changes, provenance, hidden reflows/moves, and two-point comparison | Reuse its row model and comparison semantics. |
| The changes feed groups by commit and folds generated consequences under authored work | Preserve this causal presentation in a native selectable list. |
| Home history comes from chezmoi sources and can be `TEMPLATE` or `NO VCS` | Do not label a template version as the exact deployed home instructions. |

These are documented in [Memory History][history-doc] and implemented through [HistoryService][service], the [Rust wire][core-wire], and [feed construction][core-feed]. Shared history/domain behavior belongs in `sase-core`; Python supplies scope inputs and presentation.

There are two existing Memory hosts. The normal prompt shortcut opens `MemoryPanel`, a thin modal around `MemoryPane`; the Config hub embeds the same pane. Implement the new content in the reusable pane/inspector layer so both routes behave alike. Adding a new top-level Memory History tab would work against this reuse and scatter related actions. [Memory adapter][memory-adapter], [pane implementation][memory-pane], and [Memory UI guide][memory-guide].

## 2. Concrete reliability gaps found

### 2.1 `H` and `C` currently fail at the UI-thread boundary — reproduced

Both actions run a coroutine with `run_worker`. The coroutine awaits `asyncio.to_thread(...)` to build its document, then resumes on the app thread and calls `self.app.call_from_thread(...)`. Textual refuses calls to this method from its own app thread. Both the success and error branches contain this pattern. [Handlers, lines 189–397][handlers].

I exercised the actual key bindings in a mounted `MemoryPane` through `App.run_test`, using the project's existing Memory test harness. I replaced only catalog loads and document/service construction with deterministic fixtures, leaving the action coroutine and Textual worker machinery intact. Results:

```json
{"ready": true, "selected": "sase/memory/gotchas.md"}
{"key": "H", "state": "WorkerState.ERROR", "error": "The `call_from_thread` method must run in a different thread from the app", "screen": "Screen"}
{"key": "C", "state": "WorkerState.ERROR", "error": "The `call_from_thread` method must run in a different thread from the app", "screen": "Screen"}
```

This is a UI handoff failure independent of whether Git can build the document. It is a plausible contributor to the impression that only the standalone pager supports history. That explanation is an inference; I did not inspect the user's installed/running TUI.

**Repair:** keep the coroutine, offload synchronous service work, then apply UI effects directly on the app thread after validating request identity and mount/visibility state. Alternatively, use a real thread worker and post a typed completion message. Do not mix the two conventions. Add an integration test that presses each key and observes an opened usable screen, plus tests for failure and cancellation.

Textual's [worker guide][textual-workers] distinguishes thread workers from async workers; its [API contract][textual-app] explicitly rejects `call_from_thread` from the running app thread.

### 2.2 Refresh does not invalidate successful History summaries — reproduced narrowly

`_history_renderable_for_node` returns `_history_latest[(scope, selector)]` immediately when present. The scope-load completion clears `_history_failed`, but leaves successful summaries intact. The separate cache keyed by `(scope, selector, tip)` is written by the worker but is not consulted by the rendering path. [History mixin][handlers] and [scope reload handlers][scope-loading].

A second mounted-pane probe seeded a cached summary with `tip: old-tip`, invoked the actual `action_refresh`, and waited for the fixture scope reload to finish:

```json
{"scope_refresh_finished": true, "cached_tip_after_refresh": "old-tip", "new_history_loads_scheduled": 0}
```

This demonstrates the missing invalidation path; it does not claim a measured Git-history race on Bryan's live repository.

**Repair:** explicitly expire/revalidate affected successful summaries on refresh, publish, source-editor return, and scope inventory changes. Keep old values visible with an `updating` state while a background revalidation runs. Use one effective cache, keyed by repository identity and metadata generation; clear or bound unused entries.

### 2.3 Settled failure looks like indefinite loading — source review

A failed summary becomes a `_history_failed` entry, and subsequent renders retain `…` without starting another worker until reload. Avoiding a retry storm is correct; displaying a permanent loading glyph is misleading. The existing test explicitly enshrines this behavior. [History tests][history-tests].

**Repair:** represent `loading`, `ready`, `empty`, `unavailable`, and `partial` separately. A settled failure should read `History unavailable · r retry`, retain any previous good summary, and expose a concise reason. Expected `NO VCS` is an explanation, not an error toast.

### 2.4 Discovery is incomplete — source review and visual inspection

- The History property row is deliberately omitted for web descriptor rows, even though `H` can target their history.
- The current Memory catalog is a live note/web/strand tree. Instructions and deleted subjects do not have equivalent direct browse entries there.
- Both `H history` and `C changes` footer hints depend on `has_notes`. A scope with no live notes can still have instruction history or deleted-note history.
- `C` queries all scopes in the ring, with `limit=None`, then builds a feed document before presenting it. There is no bounded native review list or visible scope control on the entry path.
- In the inspected 120×40 Memory card golden, the History summary is cramped and provenance is clipped by the property grid. The pager's past time-band golden is much clearer: fixed state pill, explicit date, meaningful change, quiet violet rail.

Sources: [pane history actions][handlers], [footer renderer][footer], [Memory card golden][card-golden], and [past time band golden][band-golden]. These are opportunities for better product design rather than evidence that the Rust history engine is missing.

## 3. The jobs the interface should make easy

| Human question | First useful interaction | Evidence that should remain visible |
| --- | --- | --- |
| “When was this rule added?” | History → filter a heading/summary → inspect changes | Version, absolute date, changed passage, agent/bead/commit when known |
| “What changed since I last looked?” | Changes → bounded recent commits → preview authored changes | Explicit scope, time window, and generated consequences |
| “Was this always core memory?” | History → promotion/demotion row | Semantic `reference → core` change and resulting loading behavior |
| “Why did AGENTS.md change?” | Instructions → change row → source note link | Render cause, source subjects at the same revision, shim identity/divergence |
| “Where did that note go?” | Include deleted → filter old name | Tombstone, historical path, last content, rename lineage |
| “Compare these two versions.” | Mark a base → choose target | A fixed, explicit older-to-newer pair |
| “What instructions did this agent see?” | Later: agent metadata → captured snapshot | Actual captured blob evidence, not a timestamp guess |

Do not claim to answer “why” beyond the available evidence. A commit subject is an author's explanation; a render cause links generated output to inputs; neither justifies an invented prose narrative.

Two-point comparison and a file-focused timeline are familiar patterns. [VS Code's official history guide][vscode-history] separates file timelines, repository history, and line attribution, and provides an explicit select-for-compare action. My design inference is to put the timeline beside the preview and make the comparison base visible. SASE should retain its own committed-history semantics; VS Code's local save journal is a different feature.

## 4. Alternatives and the design choice

| Approach | Strengths | Costs | Assessment |
| --- | --- | --- | --- |
| Repair `H`/`C`, improve the card, keep all browsing in the full-screen pager | Fastest useful release; minimal integration risk | Discovering several versions still requires picker/open cycles; little persistent list context | Ship as the prerequisite, not the complete experience. |
| Add a third column for history beside the note tree and document | Simultaneously shows files, versions, and content | At 120 columns prose becomes narrow; at 80 columns it is untenable; three selection/focus axes | Reject as the default. |
| Replace the note rail with a timeline while inspecting one subject; keep the pager preview alongside | Clear list/detail interaction; keeps readable content; preserves Memory context | Requires explicit local navigation state and a small pager-host adapter | **Recommend.** |
| Add a separate top-level History tab or a full Git graph | Makes history highly visible | Splits Memory ownership; emphasizes commits rather than policy meaning; duplicates catalog plumbing | Reject for this request. |
| Build a separate Markdown/diff renderer for Memory | Easy initial layout control | Duplicates historical links, folds, labels, anchors, search, and correctness fixes | Reject. |

The inspector is a collection-navigation surface. The document's time axis remains modeless: version keys work without entering a special editing or history mode. Moving from Notes to History changes what the rail selects, not the semantics of the document reader.

## 5. Proposed interaction design

### 5.1 Entry points and local navigation

Expose a restrained local selector: **Notes · History · Changes** in the Memory header. History is enabled when a subject is selected; Changes remains available when the live-note list is empty. Clicking the History property row also opens History. Keep the existing `H` and `C` as accelerators and add the effective keys to help/config as needed.

- **Notes** retains the current tree, metadata card, relations, editing, and publish flow.
- **History** replaces the note tree with one subject's timeline and the card with a `PagerView` preview.
- **Changes** replaces the tree with a grouped recent-changes list and previews its selected subject's change.
- A header breadcrumb always names the scope and subject. `Esc` from History/Changes returns to Notes; `Esc` from Notes follows the existing host close behavior.
- Switching back restores the original subject, scope, filter, tree expansion, scroll, and focus. Use a session snapshot, not a reset to the first row.
- While History is open, scope changes select that scope's remembered subject rather than pretending the same basename necessarily identifies the same note.

This arrangement keeps two columns at ordinary widths. It also makes History visible to someone who does not know `H`, `@`, or the punctuation keys.

### 5.2 Subject history: version list plus preview

Illustrative layout; all dates, counts, and provenance below are placeholders:

```text
 MEMORY  sase  ›  gotchas.md                          Notes  [History]  Changes
 ─────────────────────────────────────────────────────────────────────────────
 VERSIONS · 25 · 3 hidden      │ gotchas.md  [⟲ PAST · v24/25]  Sep 22 14:03 EDT
 / filter                     │ Change v23 → v24                         Read
                              │ ⇧ reference → core · § Default Keymap Config
   now   ● clean ≡ v25        │ +31w −4w · sase-1au.5 · agent… · 1a2b3c4
   v25   Sep 30  ◆ Rule edit  │ ─────────────────────────────────────────────
 ▸ v24   Sep 22  ⇧ Core       │  1│ # Default Keymap Config
   v21   Sep 14  ◆ Keys       │  2│
   v1    Aug 29  ✚ Created    │  3│ When changing keymaps, update the config…
                              │    [word changes rendered by the pager]
 · 3 reflows / moves hidden   │
                              │
 j/k version · ↵ read · = change · b compare base · ^F preview · Esc notes
```

Use one-row version summaries at a generous width, two-row compact items when the rail is narrow. Preserve ordinal, class, and date before attribution. Show the selected item's full summary/provenance in the preview; do not pack it into every rail row. A context line identifies the exact comparison pair.

**Opening History:** the preview initially shows `now` in Read view, preserving today's document. The rail starts on its `now` row. A clean now aliases the newest committed version; older stepping must skip the byte-identical duplicate as the pager already does.

**Moving the cursor:** highlight immediately; after the existing 150 ms detail debounce, preview the candidate. A committed candidate defaults to its change against its immediately preceding committed state; `Enter` opens that candidate in Read view and focuses the preview. `=` requests Change view. Choosing `now` previews Read when clean and Change against HEAD when dirty. A deliberate view toggle remains sticky within the inspector session.

Crucially, a pending row and the displayed document may differ while a worker loads. The row can say `loading preview`; the document's pill must continue to identify the content actually on screen. Never paint `v24` on a still-visible `v25` body. Once the result lands, both rail and body update atomically.

Selecting a row is preview motion and must not create a trail entry for every `j` press. Explicit open/follow actions do; Backspace in the focused preview retains the pager's document-trail semantics. A visible `Esc notes` hint provides the stable exit from the inspector.

### 5.3 Comparing arbitrary versions

Keep the existing picker interaction: `=` compares its candidate against the open version, with a footer naming both endpoints. Add a visible inspector action **Use as comparison base** with provisional rail key `b`.

- Marking a base puts an `A` marker on its row and a persistent `Compare from v8 · clear` chip above the preview.
- Choosing another row compares the two exact revisions in older-to-newer order and labels `Compare v8 → v24`.
- The cursor marks the target; the comparison-base marker remains fixed during cursor motion.
- If candidate and base are identical, show `Same version` and disable comparison.
- Clear the explicit base when changing subject/scope, and on an explicit clear action. Persist it across Read/Change toggles for that subject.
- Treat `now` and `STAGED` as separate typed endpoints even though both use ordinal 0 in the wire. Resolve ordering through existing history semantics, not `min(ordinal)` on pseudo-versions.
- A pseudo-version comparison holds the captured content digests. If external edits change them, mark the preview stale and recompute on refresh; do not silently change its bytes under an unchanged label.

`b` applies only when the rail has focus. It remains available as a pager link label when the document has focus. Ship its effective key through the same keymap/schema/help/default-config plumbing as other Memory actions; validate it against existing host bindings.

### 5.4 Changes: a review surface with a readable scope

Preserve `C`'s existing **All scopes** default, but name it prominently and offer **This scope**, **Home**, and **All scopes** choices. Never infer scope from process CWD. The currently selected Memory scope and a multi-scope changes review are different pieces of state.

```text
 MEMORY  Changes                         [All scopes ▾]  [Recent 100]  / filter
 ─────────────────────────────────────────────────────────────────────────────
 TODAY                         │ gotchas.md  [⟲ PAST · v25/25]
  14:03  sase  Clarify keys     │ Change v24 → v25 · Oct 2 14:03 EDT
   ▸ ◆ gotchas.md   +12w −3w   │ § Default Keymap Config
     ⟳ 2 generated outputs     │ ─────────────────────────────────────────────
  09:10  ⌂ Home  Tailnet rules │ Exact word diff, with context and folds
     ◆ tailnet.md   +8w        │
 YESTERDAY                     │
     ✖ old_policy.md           │
                              │
 [Load older changes]          │
```

The selectable rows are changed subjects within changesets, not only commits. Highlighting a subject previews its exact committed diff. Generated outputs stay collapsed under the authored changeset but are selectable when expanded. Their rows show a generated/cause label, not an independent authored edit. Regen-only groups remain compact and expandable.

Start with a bounded window, for example 100 changesets. The header must say `Recent 100` or `Showing 100`, rather than imply the complete history is loaded. A filter applies to the loaded window and says so. A deliberate **Search all history** action can run a broader worker with progress; full-history search should not happen on each character.

Existing `feed(scopes, since, limit, include_hidden)` can bound a first release. It has no continuation cursor or `has_more` proof today. An initial `Load older` implementation can increase the limit in batches and deduplicate by `(scope, commit, subject, version)`, showing `Older availability not yet checked` until a query proves exhaustion. If repeated prefix loads become costly, add a Rust-owned continuation contract pinned to per-scope tips; do not fake a cursor from timestamps, which can tie and be non-monotonic.

A failed Home scope should produce a visible scope diagnostic alongside successfully loaded project changes. Do not silently drop it and title the result “All scopes.” This may require a small backend result extension for per-scope outcomes.

Do not label a change “unread” or “new since last review” yet. A reliable review watermark is separately tracked by `sase-1e6` and needs an explicit human review action, not an automatic update whenever rows become visible.

### 5.5 Instructions, web descriptors, and deleted subjects

Make the inspector reachable for the full supported subject set:

- Give web descriptors the same visible History affordance as ordinary notes and strands.
- Provide an **Instructions** group/selector within Memory, populated from the existing instruction inventory/history subjects. `AGENTS.md` and identical shims share one logical subject; diverged shim versions remain visible and explained.
- Provide an explicit **Include deleted** filter/subject picker sourced from `HistoryService.subjects`, rather than trying to recover deleted notes from the current filesystem tree.
- Distinguish **web descriptor history** from **changes across this web's strands**. `H` on a web means its descriptor, preserving today's selector behavior. A future “Changes in this web” is an explicitly named collection filter.
- On a deleted subject, show a `DELETED` pill, deletion date/provenance, and `Last content before deletion`. Never call last content `now`, and do not put the deletion notice into the file body where it would corrupt line numbering.
- For instructions, prioritize render cause and source links. Home source templates get `TEMPLATE`; exact deployed per-host instruction history is later work under `sase-1ea`.

## 6. Focus and key behavior

Preserve the pager's labels and established keys by routing according to focused region. Avoid broad priority bindings on the inspector that steal typing from filters or document labels.

| Context | Keys/actions |
| --- | --- |
| Notes | Existing keys; `H` opens History; `C` opens Changes; clickable header and History row offer the same actions. |
| Version/changes rail | `j/k`, arrows, `g/G` navigate; `/` filters rows; `Enter` reads/focuses preview; `=` changes/compares; `b` sets base in a subject timeline; `.` includes hidden changes. |
| Preview | Existing pager scrolling, search, link labels, read/diff, version stepping, change navigation, copy, and trail behavior. |
| Either inspector region | `Ctrl+F` switches between rail and preview; `Esc` first dismisses transient input, then returns to Notes. |
| Full-screen reading | A visible `Open full screen` action/provisional `Z` on the rail opens the same document/pin in the existing `PagerScreen`; close restores the inspector. |

Inside the inspector, `@` should focus/open its timeline rail rather than stack a redundant picker over an already visible list. In the standalone/full-screen pager, `@` keeps the existing modal picker. Reuse the timeline component between these hosts.

The footer is focus-specific. With rail focus: `j/k versions · Enter read · = change · Ctrl+F preview · Esc notes`. With preview focus: show its version destinations/search/link actions plus `Ctrl+F versions`. Clear pending label prefixes and transient search typing on focus change as the split pager already does. Only the focused document paints jump-label badges.

Keep destructive note-management bindings out of historical preview focus. If current editing is offered, label it **Edit current source**, retaining the pager's explicit “edit now” meaning. This research recommends a read-only first inspector release; restoration is later work.

## 7. Visual design and responsive behavior

The existing violet past pill/rail is an effective foundation. Extend that vocabulary instead of inventing a second color system. The page should feel like reading policy with provenance attached, not operating a source-control dashboard.

| Role | Presentation |
| --- | --- |
| Current content | Neutral surface; explicit `NOW` text |
| Historical content | Violet `PAST` pill and thin gutter rail |
| Uncommitted/staged | Amber plus explicit state text |
| Additions/removals | Existing insert/delete palette, with textual/gutter cues as well as color |
| Selection | Cursor marker and restrained background; base selection has its own `A` marker |
| Unavailable/partial | Short explanatory state; preserve readable body and retry action |
| Scope | Project's existing accent, separate from the past-state accent |

Use semantic change first: `Promoted to core`, touched heading, word count; then author/bead; SHA is secondary. Reserve predictable spaces for ordinal, date, and state. Avoid truncating the state pill or the comparison pair. Long descriptions and provenance can shorten with a full detail reveal. Use actual terminal cell widths for emoji, CJK, combining characters, and ellipses.

The mini sparkline is orientation, not a calendar: equal version cells represent change order/volume, not elapsed time. Keep its explanation under help. Do not make anonymous sparkline cells the only way to navigate history. Reuse the pager's theme-resolved colors and readable secondary foreground; avoid applying bare `dim` to necessary state/provenance text.

As an accessibility design benchmark, text should meet at least 4.5:1 contrast, with the repository's existing 7:1 reading target where feasible. Color must have a matching label/marker. Those principles come from W3C's [contrast guidance][contrast] and [use-of-color guidance][color]; this is a terminal design benchmark, not a claim that a Textual app has been formally WCAG certified.

Proposed breakpoints are hypotheses to verify with real content, not established measurements:

| Available inspector size | Layout |
| --- | --- |
| About 110+ columns, adequate height | 32–38-column rail, one divider, at least 64-column preview; compact metadata band. |
| About 80–109 columns | Approximately 26-column compact rail, provided the preview retains at least 50 useful columns. |
| Less than that | Single region at a time: full-width version list → full-width preview; preserve cursor/filter when returning. |
| 12 rows or fewer | Compact header and footer; retain state and comparison pair, shed sparkline/provenance rows first. |

Base thresholds on the allocated widget rectangle, not the whole terminal: the Config hub consumes space. Never default to file tree + timeline + preview at 120 columns. Full-screen reading is the escape hatch for long instruction files. Independent side-by-side panes already exist in the pager; an aligned two-column diff is separate `sase-1ea` work and should wait for sufficiently wide content space.

## 8. Implementation architecture

### 8.1 Reuse the mounted document view, with an explicit host adapter

`PagerView` is already a mountable widget owning history, diff, syntax, trail, search, links, and chrome. `PagerScreen` now hosts one or two views. This makes reuse feasible. However, embedding is **not** plug-and-play: `PagerView.pager_host` currently returns `self.screen`, and expects that screen to satisfy a pager-specific protocol. A Memory pane embedded in Config has a different screen host. [PagerView][pager-view] and [screen host][pager-host].

Add a small explicit host injection seam, keeping the existing screen default for compatibility. A `MemoryHistoryInspector` implements/adapts footer painting, close/back, focus, and opening in another/full-screen view. Give it an explicit viewport/chrome budget. Keep the document view's behavior in the pager package; avoid reaching into private state dictionaries from the Memory pane.

A presentation controller owns:

```text
entry point → Memory inspector session
                  ├─ scope + subject + filters + cursor + optional compare base
                  ├─ reusable timeline / changes row widgets
                  └─ host adapter → PagerView
                                      └─ memory SectionHistoryProvider
                                              └─ HistoryService
                                                      └─ sase_core_rs
                                                              └─ Git + metadata cache
```

Extract/reuse the picker row model and lazy list rendering rather than building a second list from `git log`. Add a small public selection/event seam so punctuation-driven stepping in the preview updates the rail, and rail selection requests update the same time state. There must be one authority for the displayed pin; two independently changing cursors will drift.

### 8.2 Identity, freshness, and race handling

Store UI identities as **repository/scope identity + logical subject + exact revision/blob**. Use ordinals for display and stepping within a snapshot. Do not persist `v24` as an eternal identifier across a rewritten history/index rebuild. Re-resolve exact commit/blob evidence; if unavailable, say so.

Pseudo-version row keys need a kind discriminator (`now`, `staged`) plus digest. Caches for body and comparison need exact endpoint identities/digests. A metadata key containing only HEAD cannot detect worktree/index changes.

Every request captures a generation and selection identity. On completion, verify the generation, scope, subject, compare base, mount state, and active host before applying it. Cancel obsolete workers, but treat cancellation as insufficient: the synchronous thread may still finish. Request generations are what prevent an old result from repainting a new selection.

Show cached data immediately, schedule background revalidation, and label it `updating` or `stale` when appropriate. On failure retain the last good document with its true pin. Bound memory caches; do not retain an unbounded copy of every subject's timeline and every comparison visited.

Refresh should have two explicit contracts:

- **Inspector refresh:** revalidate lists and freshness, preserving an exact committed preview/base when still available; show newer versions without automatically moving the reader.
- **Pager `r`:** retain its documented re-sync-and-follow-HEAD behavior. If the preview exposes that command, label it accordingly; the inspector's list refresh should have its own visible action/effective binding, provisionally `R`.

This separates the user's request to update available evidence from a request to leave the past. Generated source links and file links followed from a pinned document still resolve at that pinned revision. Never fall back silently to current bytes when the historical target is absent.

### 8.3 Error and partial-state contract

| State | User-visible behavior |
| --- | --- |
| Cold indexing | Paint Memory/inspector shell immediately; show `Indexing history…`; navigation/close remain responsive. |
| No committed versions | `No committed versions` with current content; distinguish untracked/ignored. |
| No Git / Home without chezmoi | `NO VCS` plus scope-specific explanation; keep other scopes usable. |
| Shallow clone | `Partial history · shallow checkout`; no claim of the first-ever version. |
| Missing historical object | Keep prior content or show an unavailable snapshot panel; name the missing revision. |
| Corrupt cache | Core rebuilds the disposable index; show indexing/retry, never treat cache corruption as lost Git history. |
| Rewritten HEAD | Revalidate identity; retain exact historical objects only when available; explicitly flag removed pins. |
| Partial multi-scope load | Render successful scopes and name failed/omitted ones. |
| Fetch freshness unknown | Use local remote-tracking evidence only; no implicit network request and no assertion of global latest. |
| Render/classification unavailable | Fall back to a plainly labelled document/raw diff where the existing provider supports it; do not invent semantics. |

History browsing must not create agent memory-read audit records. Current ordinary strand previews already have their own audit behavior; historical rail selection must not accidentally invoke that path. Preserve this distinction with an integration test.

### 8.4 Backend changes should be narrow and justified

The first inspector can use existing timeline/version/compare/feed calls. Keep classification, renames, shim aliasing, authored-versus-generated grouping, and Git operations in Rust. Do not reproduce those rules in Python widgets.

Potential additional core contracts are a compact subject summary, per-scope feed diagnostics, and eventually stable feed continuation/search. They are needed only where the current wire is demonstrably insufficient. Note that `subjects()` currently returns subjects **with all versions**, not a lightweight summary catalog; do not repeatedly query it for a badge on every row. A new Rust binding requires the corresponding `sase-core-revision.txt` pin update in `sase`.

No new history database, save journal, branch creation, checkout switching, or background fetch is required for this feature.

## 9. Delivery sequence and verification

This is a research recommendation, not an approved implementation plan.

1. **Repair and establish trust.** Fix both thread-boundary failures, summary invalidation, settled-error states, and entry hints in empty scopes. Add real key-to-screen tests. This is useful immediately and should precede cosmetic expansion.
2. **Ship subject History.** Add the visible header/row affordances, reversible local navigation state, reusable timeline rail, host adapter, `PagerView` preview, and narrow-screen fallback. Validate ordinary notes, web descriptors, strands, dirty/staged states, and deleted subjects.
3. **Ship native Changes and Instructions reachability.** Add bounded rows, explicit scope controls, generated consequence expansion, and exact historical subject previews. Keep cold query work behind first paint.
4. **Add explicit base comparison and finish visual/performance review.** Test pair normalization, filter/focus behavior, long text, custom themes, and split/full-screen return.
5. **Extend provenance workflows separately.** Integrate `sase-1e5` for the instructions an agent actually saw; then consider `sase-1e6` review watermark and `sase-1e7` restore.

“As seen by agent” deserves special care. Launch capture stores `workspace_head`, instruction blob OIDs, and content-addressed instruction snapshots when the blob is unavailable from Git. Read events carry `blob_oid` and `included_blob_oids`. Exact viewed evidence must use these, not “nearest commit before the agent's timestamp.” A blob digest on a read event does not by itself guarantee its uncommitted contents were retained. Show `Snapshot unavailable` when bytes cannot be recovered. [Launch evidence][launch-evidence].

Restoration is attractive but adds authorization, digest-conflict checks, generated-subject restrictions, current-path mapping after rename, and publish semantics. Keep it out of the first inspector. Its eventual action should be **Restore as draft**, never a silent reset or checkout, and should use the approved memory mutation/publish path.

Meaningful acceptance checks:

- From both the modal Memory host and Config's embedded Memory, pressing `H`/`C` succeeds; document-build failure shows a useful retry state.
- A commit added while Memory is open becomes visible after refresh without reopening; unchanged refresh preserves cursor and selected exact historical content.
- Pressing `H`, moving selection, switching scope, hiding Config, or closing during a slow build never opens a stale surprise screen.
- Rapid timeline motion updates highlight immediately; the body/pill never disagree; filters and syntax caches do not show another subject's bytes.
- Two pseudo-version rows with ordinal 0 remain independently selectable and copyable.
- Renamed/deleted/recreated subjects and diverged shims retain correct identity; shallow/missing-object states remain explicit.
- A pinned link either opens the historical target or explains its absence; ordinary history viewing adds no agent read-audit event.
- Keyboard-only and mouse workflows can discover History, choose a version, inspect Change/Read, compare a pair, and return to the same note.
- Capture and inspect the actual rendered UI at 120×40, 80×24, 60×30, a very short height, and an embedded Config rectangle in dark/light/Flexoki and ANSI/custom themes. Include long paths/agent names and Unicode cell widths.
- Use deterministic fixtures for visual goldens and live `sase screenshot` for real workflow confidence; inspect the renderer's report and every changed golden group before accepting it.

Performance requirements should follow the project's audited `tui_perf` rules: no Git, filesystem reads, JSON parsing, or synchronous service calls on keystroke/render paths; slow work must be outside the serial message pump as well as outside the event loop. Use the existing 150 ms detail debounce without delaying cursor highlight, generation guards, prefetch, and bounded first loads.

Prior epic/documented measurements were approximately 6 ms p95 for warm version steps, 45–90 ms for warm sync/query, and 2.3 s for cold indexing; only the first of those met its original target. Do not turn query freshness checks into a new cost per cursor motion. Targets for the extension: first paint independent of history size; cursor-to-highlight p95 within the existing 16 ms TUI budget; prefetched version preview within the existing 30 ms history budget; no loop/pump stalls under rapid navigation. Record before/after measurements on representative real histories. [Performance section][history-doc].

Implementation verification should run focused integration tests and relevant visual selectors, then the project's required `sase tool run check`. `check-full` remains explicit-only; this research is not an instruction to run it.

## 10. Source and probe ledger

Primary local evidence:

- [sase-1dr epic][epic]: closed scope, landed phases, measurements, and known follow-ups.
- `plan:202609/memory_history.md`: audited shared approved plan; history-reading contract and deliberate non-goals.
- [Current history documentation][history-doc] and [Memory UI guide][memory-guide].
- [MemoryPane history handlers][handlers], [summary formatting][summary], [scope reload handlers][scope-loading], and [entry footer][footer].
- [Existing Memory history tests][history-tests]: bindings, formatting, scope choice, loading, and settled-unavailable placeholder tests; they do not exercise a mounted H/C screen-open flow.
- [PagerView host contract][pager-view], [PagerScreen host][pager-host], [version-pin model][pins], and [HistoryService][service].
- [Rust memory-history wire][core-wire] and [changeset/feed implementation][core-feed].
- [Launch snapshot evidence][launch-evidence].
- Visual inspection: [Memory History card golden][card-golden], [timeline picker golden][picker-golden], [past time band golden][band-golden], and [light word-diff golden][diff-golden].

External primary sources, consulted 2026-10-02:

- [VS Code: View source control history][vscode-history] — file-focused timeline and explicit pair comparison precedent.
- [Textual worker guide][textual-workers] and [App API][textual-app] — thread/async distinction and UI handoff contract.
- [W3C: Use of Color][color] and [Contrast (Minimum)][contrast] — labels in addition to color and text contrast benchmark.

The headless probes used `.venv/bin/python`, `pytest.MonkeyPatch`, `MemoryPanelTestApp`, `install_fixed_load`, `memory_note`, `scope_ref`, and `scope_snapshot` from `tests/ace/tui/modals/memory_panel_test_helpers.py`. For the H/C probe, the substituted service returned a fixed scope/feed, and document builders returned a one-section `PagerDocument`; after `pilot.press(key)`, `worker.wait()` was caught and `worker.state`/`worker.error` inspected. The entry-point source and Textual scheduling were not replaced. For the refresh probe, only catalog loaders and the `_ensure_history_load` scheduling recorder were substituted; `_history_latest` was seeded, actual `action_refresh()` was invoked, and reload completion/cache/scheduling inspected. These probes changed no product files and created no Git commits.

## Recommended solution

**Implement a native Memory history inspector with a timeline or changes rail beside the existing `PagerView`, preserving a full-screen pager escape hatch and one Rust-owned history model.** Repair `H`/`C` and stale/error summary handling first. Then make History and Changes visible in Memory, keep exact version/comparison identity explicit, include instructions and deleted subjects, and degrade to a single-region list/detail flow on small terminals.

Ship the first release as a polished read-only inspection tool. Its success criterion is that Bryan can discover a rule's history, see precisely what changed and what generated from it, and return to the same place without uncertainty about scope, revision, or freshness. Add agent snapshot provenance, review watermarks, and restore through their existing follow-up work after this foundation is verified.

[epic]: https://github.com/sase-org/sase--beads/blob/main/pages/sase-1dr/README.md
[history-doc]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/docs/memory_history.md
[memory-guide]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/docs/ace.md#memory-panel
[memory-adapter]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/src/sase/ace/tui/modals/memory_panel.py
[memory-pane]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/src/sase/ace/tui/modals/memory_pane.py
[handlers]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/src/sase/ace/tui/modals/memory_pane_history.py#L189-L397
[summary]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/src/sase/ace/tui/modals/memory_panel_history.py
[scope-loading]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/src/sase/ace/tui/modals/memory_pane_loading.py#L180-L228
[footer]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/src/sase/ace/tui/modals/memory_panel_rendering.py#L515-L570
[history-tests]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/tests/ace/tui/modals/test_memory_panel_history.py
[pager-view]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/src/sase/pager/view.py
[pager-host]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/src/sase/pager/_screen_host.py
[pins]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/src/sase/pager/history/models.py
[service]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/src/sase/memory/history/service.py
[launch-evidence]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/src/sase/axe/launch_evidence.py
[core-wire]: https://github.com/sase-org/sase-core/blob/926edfb8baa1d8e3ba4242156961905595d0faf9/crates/sase_core/src/memory_history/wire.rs
[core-feed]: https://github.com/sase-org/sase-core/blob/926edfb8baa1d8e3ba4242156961905595d0faf9/crates/sase_core/src/memory_history/feed.rs
[card-golden]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/tests/ace/tui/visual/snapshots/png/memory_panel_history_dark_120x40.png
[picker-golden]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/tests/pager/visual/snapshots/png/timeline_picker_default_dark_120x40.png
[band-golden]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/tests/pager/visual/snapshots/png/timeband_past_dark_120x40.png
[diff-golden]: https://github.com/sase-org/sase/blob/45f165b6d52dddd812e249fe929c80a20520da4d/tests/pager/visual/snapshots/png/history_past-diff_light_120x40.png
[vscode-history]: https://code.visualstudio.com/docs/sourcecontrol/history
[textual-workers]: https://textual.textualize.io/guide/workers/
[textual-app]: https://textual.textualize.io/api/app/#textual.app.App.call_from_thread
[color]: https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
[contrast]: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
