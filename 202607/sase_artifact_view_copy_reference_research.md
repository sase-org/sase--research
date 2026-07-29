# Viewing, Copying, and Referencing SASE Artifacts

**Research date:** 2026-07-29  
**Scope:** SASE ACE/TUI artifact files, with a path toward consistent references for chats, plans, commits, and other artifact types

## Executive summary

SASE already has more artifact-viewing capability than the current picker reveals: agent-scoped discovery, multi-select, Markdown-content copying, path copying, text fallback, image/PDF/video rendering, zoom, and a reusable native Textual preview panel elsewhere in ACE. The main limitation is not a missing media viewer. It is that an artifact is still presented primarily as a label plus a filesystem path.

That path-centric model causes four product problems:

1. A copied path is often not a durable reference. Explicit artifacts are moved into managed storage, while the remembered source path may no longer exist.
2. The UI hides the artifact ID and most provenance, and the ID itself is derived partly from location.
3. Artifact discovery is agent-local even though ACE has a top-level Artifacts area.
4. Unknown files fall through to terminal text output; raw `cat` of an arbitrary artifact is unsafe and incorrect for binary or control-sequence-bearing content.

The best path forward is a focused artifact-file registry and resolver in the Rust core, paired with a native Artifact Inspector in ACE. The registry should give each artifact an opaque, location-independent identity, a separate content digest, rich provenance, and a versioned `sase://` reference. The inspector should reuse Textual for safe Markdown/text rendering, search, metadata, and copy actions, while retaining the existing tmux/external viewer for image, PDF, and video workflows.

This deliberately does **not** recommend restoring the former general-purpose “unified artifact graph.” SASE removed that subsystem in core commit `b455124` on 2026-05-06. The product need here is narrower: identify, resolve, inspect, copy, and open artifacts reliably.

## Research method

This analysis combined:

- A code and documentation audit of the current SASE artifact picker, preview panels, clipboard adapter, viewer process, artifact-file model, explicit artifact storage, and ACE Artifacts panes.
- A history audit of the linked `sase-core` repository, including the removed artifact graph.
- Review of existing SASE research on Markdown-to-HTML artifacts, terminal image/PDF support, and browser-served ACE.
- Comparison with official documentation for Textual, GitHub Actions artifacts, GitLab job artifacts, Weights & Biases Artifacts, VS Code terminal links, JupyterLab deep links, OSC 8 hyperlinks, and terminal clipboard transport.

The primary near-term object in this report is an **artifact file**: Markdown, text, image, PDF, video, or another file produced by or explicitly attached to an agent run. The reference design can later dispatch to other typed SASE objects without forcing them into a graph.

## Current-state audit

### What works today

The agent Artifacts picker is opened with `a` and includes chats, plans, generated media, prompt media, and explicit artifact files. It always opens, even for a single artifact, which leaves room for a consistent inspect/copy interaction. It also supports marking multiple artifacts.

Current picker actions include:

- `y`: copy the highlighted Markdown file's complete contents.
- `Y`: copy a path, preferring a workspace-relative source path when possible.
- `Enter`: open the marked or highlighted artifacts.
- `z`: open in zoom mode.
- `A`: mark all.

The external viewer handles multiple artifacts and pages. It renders images through Kitty, video through `mpv`, PDFs through `pdftoppm`, and Markdown through a PDF/PNG conversion path. Unknown suffixes are treated as text. The viewer supports next/previous artifact, next/previous page, refresh, zoom, and returning focus to ACE.

ACE also already contains a native `PreviewPanelModal` with syntax-highlighted source, line numbers, and scrolling. Chats, plans, and prompt previews use native Textual patterns, and the top-level Plans and Chats panes demonstrate the split-list/detail layout that an artifact browser needs.

### Where the model and UI diverge

| Dimension | Current behavior | Consequence |
|---|---|---|
| Discovery | Artifact files are reached from a selected agent; the top-level Artifacts tab has Commits, Plans, Chats, Bugs, and PRs, but no Files/Outputs catalog. | Users must remember which agent produced a file. Cross-agent comparison is awkward. |
| Identity | `ArtifactFileV1` contains an ID, but the picker does not show or copy it. The ID hash includes resolved path and run context. | A path relocation can change identity; users have no canonical token to cite. |
| Integrity | Explicit storage includes a 12-character SHA-derived filename component, but the model does not expose a full digest. | Integrity/deduplication information is implicit and cannot be verified or copied. |
| Paths | Explicit artifacts are moved to managed storage, while `source_path` remains recorded. `Y` may copy that former source path. | “Copy path” can copy a path that no longer exists, even though the stored artifact is healthy. |
| Metadata | The picker shows label, kind, and a truncated path. | Size, MIME type, creation time, run/agent provenance, digest, storage state, and retention are hidden. |
| Text viewing | Markdown is converted through external tools for the media viewer; unknown files fall through to terminal text. | Common text inspection is heavier than necessary, and unknown binary data is mishandled. |
| Copying | Full-content copy is restricted to Markdown. Path and content are separate fixed keys. | There is no way to copy a stable reference, Markdown link, selected excerpt, metadata, or a marked set in a chosen format. |
| Scale | The modal is 74 columns wide, capped at 28 rows, and uses one-character selector keys. | Long labels/paths are truncated; selector capacity is finite; metadata and preview cannot coexist. |
| Portability | Rich media depends on Kitty, `mpv`, `pdftoppm`, Pandoc, and a PDF engine. | The experience degrades sharply in SSH, non-Kitty, browser-served, or minimally provisioned environments. |

## Key findings

### 1. A path, a content digest, and an artifact reference are different things

A **path** says where bytes happen to be visible now. It can be relative, absolute, remote, moved, or deleted.

A **digest** says which bytes were observed. It is ideal for integrity and deduplication, but it is not enough for provenance: two agents can intentionally produce byte-identical files that remain distinct run outputs.

An **artifact reference** identifies the durable SASE record. It should continue to resolve after a storage relocation and should preserve the originating project, run, agent, and label. The reference may expose the digest, but it should not be the digest.

This separation is established in artifact systems. The GitHub Actions artifact API exposes a stable artifact ID alongside name, size, timestamps, expiry state, workflow-run provenance, download URL, and SHA-256 digest ([GitHub REST API](https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28)). Weights & Biases likewise distinguishes artifact ID, content digest, manifest, metadata, size, version, state, TTL, and aliases such as `latest` ([W&B Artifact API](https://docs.wandb.ai/models/ref/python/experiments/artifact), [W&B aliases](https://docs.wandb.ai/models/registry/aliases)).

SASE should adopt the distinction without adopting either product's remote service model.

### 2. SASE has the pieces for a substantially better native inspector

Textual has a first-party `MarkdownViewer` with a rendered document, highlighted code blocks, tables, browser-like navigation, and optional table of contents ([Textual MarkdownViewer](https://textual.textualize.io/widgets/markdown_viewer/)). SASE already has a syntax-highlighted, line-numbered source preview and split-pane artifact layouts.

The shortest route to a good text experience is therefore:

- Render Markdown natively by default.
- Toggle between rendered and source views.
- Search within the artifact and navigate matches.
- Show metadata and reference actions alongside the preview.
- Use the existing external/tmux viewer for file types where terminal-native rendering remains valuable.

This is also consistent with the existing SASE Markdown-to-HTML research: native Rich/Textual Markdown is the right immediate terminal preview, while browser HTML is a separate sharing surface.

### 3. The existing media viewer should become a capability-dependent backend

The image/PDF/video viewer is useful and should remain. It is not a strong default shell for Markdown, text, JSON, logs, or unknown files because it introduces external process and terminal-protocol dependencies into the most common inspection path.

A native inspector can choose a backend by capability:

| Kind | Default preview | Secondary action |
|---|---|---|
| Markdown | Native rendered Textual view | Source view; external viewer; editor |
| Plain text, source, JSON, logs | Safe native source view with line numbers and search | Editor; external pager |
| Image | Metadata plus thumbnail when the terminal supports it | Existing Kitty/external viewer |
| PDF | Metadata plus first-page thumbnail when available | Existing page viewer; external app |
| Video/audio | Metadata and optional poster/duration | Existing `mpv` path |
| Unknown/binary | Metadata, detected type, safe byte summary; never raw terminal output | Open externally; reveal/copy stored path |

GitLab provides a useful conceptual separation: browse an artifact collection, preview supported formats, and download the underlying artifact are distinct actions ([GitLab job artifacts](https://docs.gitlab.com/ci/jobs/job_artifacts/)). SASE's equivalent should be inspect, open with the best available renderer, and reveal/export the stored file.

### 4. Raw fallback output is a safety issue, not merely a rough edge

The current unknown-file path ultimately invokes `bat` when available and otherwise raw `cat`. Arbitrary output can contain ANSI, OSC, or other terminal control sequences. MITRE classifies failure to neutralize escape/control sequences as CWE-150 and notes that crafted terminal sequences can move the cursor, clear the screen, fabricate prompts, or cause terminal-dependent behavior ([MITRE CWE-150](https://cwe.mitre.org/data/definitions/150.html)).

The safe default should be an application-owned text renderer after:

1. A bounded byte read.
2. MIME/signature and UTF-8/text plausibility checks.
3. Control-character neutralization, preserving ordinary tab/newline behavior.
4. A visible truncation state for large files.

Unknown binary data should never be printed directly to the user's terminal. This guardrail should be implemented before the larger redesign.

### 5. Clipboard transport and copied representation are separate concerns

The current `ClipboardAdapter` chooses `pbcopy`, `wl-copy`, `xclip`, or `xsel`. Textual also provides `App.copy_to_clipboard()`, designed to work through supported terminal environments ([Textual App API](https://textual.textualize.io/api/app/)). It should be the in-app first attempt, with the existing platform commands as fallbacks.

Terminal clipboard mechanisms often travel via OSC 52 and can work across SSH without X forwarding, but support and security policy vary across terminal/tmux configurations ([tmux clipboard guidance](https://github.com/tmux/tmux/wiki/Clipboard)). SASE should only initiate clipboard writes in response to an explicit user action, apply reasonable size limits, and report whether copying succeeded and which representation was copied.

Even perfect clipboard transport does not solve representation. Users need to choose whether they are copying content, a durable reference, a human-readable Markdown link, a source path, or a stored path.

### 6. Durable deep links make references useful outside the picker

Stable links should restore context, not merely identify bytes. GitHub permalinks can target exact lines in an exact version ([GitHub permanent links](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-a-permanent-link-to-a-code-snippet)); JupyterLab URLs can open a specific file in a named workspace ([JupyterLab URLs](https://jupyterlab.readthedocs.io/en/4.1.x/user/urls.html)); and VS Code terminal link detection recognizes file paths with line and column information ([VS Code terminal basics](https://code.visualstudio.com/docs/terminal/basics)).

SASE references should be able to carry an optional location:

- Text/Markdown: `#L12-L18`
- PDF: `#page=3`
- Video/audio: `#t=92.5`
- Markdown heading: a normalized heading anchor

OSC 8 can make rendered references clickable while remaining harmless text in terminals that do not support it ([OSC 8 hyperlink specification](https://iterm2.com/feature-reporting/Hyperlinks_in_Terminal_Emulators.html)). It is a worthwhile enhancement, but keyboard-driven resolver actions must remain the primary mechanism because file locations and terminal hosts can differ.

## Recommended target design

### Product model

Treat every artifact file as a durable record with one canonical reference and zero or more present-day locations:

```text
Agent `a` ───────────────┐
Artifacts → Files ───────┼──> artifact query/resolver ──> Artifact Inspector
CLI / pasted reference ──┘              │                       │
                                        ├── metadata             ├── native preview
                                        ├── stored location      ├── external/media open
                                        ├── source state         └── Copy as…
                                        └── provenance
```

The same inspector should open:

- Filtered to one agent from the current `a` action.
- From a future global Files/Outputs subtab.
- From a pasted or clicked `sase://` reference.
- From CLI `show` or `open` commands.

### A narrow core registry and resolver

Artifact discovery and identity are backend behavior that future CLI, web, editor, and TUI clients need to agree on. Under SASE's current architecture boundary, that belongs in `sase-core`, exposed to Python through the existing binding/adaptor pattern.

The minimal record should include:

| Field | Purpose |
|---|---|
| `artifact_id` | Opaque, immutable, location-independent record identity |
| `schema_version` | Safe evolution of serialized metadata and references |
| `sha256` | Full content-integrity/deduplication digest |
| `label` | Human-facing name, independently editable if desired |
| `kind` and `mime_type` | Renderer selection and safe fallback |
| `size_bytes` | Preview and copy limits; user context |
| `created_at` | Ordering and provenance |
| `project`, `run_id`, `agent_id`, `agent_name`, `workflow` | Origin and query dimensions |
| `explicit` | User-created versus discovered/default artifact |
| `stored_location` | SASE-managed durable location |
| `source_location` and `source_state` | Original context, explicitly marked present/missing/unknown |
| `availability` and optional `expires_at` | Present, missing, expired, remote-only, or corrupt |

Recommended identity behavior:

- Mint an artifact ID once; do not recompute it from path.
- Create a new record/version if the bytes of an existing mutable source change.
- Permit identical digests across different artifact IDs when provenance differs.
- Verify a stored artifact against its digest when practical.
- Preserve existing V1 records through a deterministic migration/alias layer, so old IDs and current paths still resolve.

This is a registry/index plus resolver, not an object graph. Other artifact nouns can later implement the same typed resolver interface without sharing the artifact-file schema.

### Canonical references

Use a versioned, typed, compact URI:

```text
sase://artifact/v1/file/af_01K4...
sase://artifact/v1/file/af_01K4...#L12-L18
```

Properties:

- `v1` freezes the parsing contract.
- `file` leaves room for typed dispatch such as `chat`, `plan`, or `commit`.
- The opaque ID survives file moves and label changes.
- The optional fragment targets a stable location within immutable content.
- Resolution returns structured metadata and availability errors, not just a path.

This is a **local SASE reference**, not a promise that every recipient can fetch the bytes. Public or team sharing should be an explicit publish/export operation with a separate authenticated URL or portable bundle.

The CLI surface can extend the existing noun:

```text
sase artifact-file list [filters]
sase artifact-file show <reference-or-id> [--json]
sase artifact-file open <reference-or-id>
sase artifact-file path <reference-or-id> --stored|--source
sase artifact-file cat <reference-or-id> [--range 12:18]
sase artifact-file reference <reference-or-id> [--markdown]
```

Accepting a raw ID and current file path as compatibility inputs will make adoption incremental. Output should prefer the canonical URI.

### Native Artifact Inspector

Replace the fixed-width picker with a responsive inspector:

- **Wide terminal:** filterable list on the left, preview and metadata on the right.
- **Narrow terminal:** stacked list and preview screens with the same actions.
- **Agent entry point:** list starts filtered to that agent.
- **Global entry point:** list spans indexed artifact files with project/agent/kind/time filters.

Core interactions:

- Rendered/source toggle for Markdown.
- `/` search, with next/previous result.
- Table of contents for longer Markdown.
- Safe syntax-highlighted text with line numbers.
- Metadata drawer/card with canonical reference, digest, size, MIME, origin, creation time, source path state, and stored path.
- `e` to open in the configured editor at the selected line.
- `o` to use the best media/external backend.
- `y` to open **Copy as…**.
- Current fast keys may remain as accelerators to avoid breaking muscle memory.
- Marking applies copy/open/export actions to a set.

Preview work should be lazy and cancellable. List population must not eagerly convert PDFs, hash large files, or read entire artifacts. Metadata known at registration time should make the first screen cheap.

### Unified “Copy as…” action

A single palette avoids adding a key for every representation and makes path semantics explicit:

1. **SASE reference** — canonical URI; recommended default.
2. **Markdown link** — `[Label](sase://artifact/v1/file/…)`.
3. **Selected excerpt with reference** — quoted/indented text plus `#Lx-Ly`.
4. **Full text contents** — only for text-like artifacts and within a configurable size limit.
5. **Source path** — labeled as present or missing; relative to the workspace when valid.
6. **Stored path** — the managed, currently resolvable location.
7. **Metadata JSON** — useful for scripts and issue reports.

For multiple marked artifacts, the same palette should produce:

- A Markdown list of references or links.
- A newline-separated path list.
- Concatenated text with clear artifact boundaries and references.
- A JSON array of records.

Copy success feedback should name the representation and count, for example: “Copied 3 SASE references.” A failure should leave the generated text visible/selectable instead of discarding it.

### Global Files/Outputs catalog

Add a sixth top-level Artifacts subtab, tentatively **Files** or **Outputs**, backed by the registry rather than repeated scans. It should support:

- Fuzzy label/path search.
- Structured filters such as `agent:`, `kind:`, `project:`, `run:`, and `since:`.
- Sorting by creation time, size, agent, and label.
- Grouping by run/agent or kind.
- Availability indicators for stored, source-only, missing, expired, or corrupt content.
- The same marks, inspector, copy, open, and export actions as the agent-scoped view.

“Files” is precise and consistent with the current model. “Outputs” may be friendlier but risks excluding user-attached inputs. If product language should encompass both, **Artifact Files** is the least ambiguous label.

## Alternatives considered

### Only polish the current picker

Widening the modal, adding metadata rows, and adding more copy keys would be inexpensive. It would not solve path-based identity, cross-agent discovery, source/stored ambiguity, resolver access from the CLI, or safe handling of unknown content. These changes are worthwhile only as a transitional step.

### Make the external/tmux viewer the primary experience

This preserves strong image/PDF/video support but leaves text inspection dependent on subprocesses and terminal capabilities. It also does not create a natural home for search, structured metadata, source/rendered toggles, or copy variants. Keep this as a rendering backend.

### Make a browser/HTML viewer the primary experience

HTML is excellent for shareable rich Markdown and future remote ACE access. It is not the best first move for a terminal-first product: it adds service lifecycle, authentication, URL routing, host/browser coordination, and remote-path questions before identity is settled. A web viewer becomes much easier and safer after the resolver exists.

### Restore the unified artifact graph

A graph could model relationships among runs, agents, commits, plans, chats, and files, but it would reintroduce a large abstraction for a narrower UX problem. The previous graph implementation was deliberately removed from `sase-core`. A focused typed registry/resolver provides the necessary identity and provenance now, while leaving room for relationship APIs later if demonstrated use cases justify them.

### Use content-addressed IDs only

This makes relocation and deduplication easy but collapses distinct provenance when two agents produce identical bytes. Content hashes should be first-class integrity fields, not the sole record identity.

## Delivery sequence

### Phase 0: safety and semantic cleanup

- Stop raw terminal output for unknown artifacts.
- Add bounded text detection, control neutralization, and binary fallback metadata.
- Label copied paths as source versus stored.
- Refuse or clearly warn when copying a missing source path.
- Add `--`/argument-boundary hygiene to external renderer invocations.

### Phase 1: registry, identity, and resolver

- Add the narrow artifact-file record/resolver to `sase-core`.
- Mint location-independent IDs and expose SHA-256, MIME, size, provenance, and availability.
- Index all current artifact-file sources, including chats, plans, media, and explicit artifacts.
- Add V1/path compatibility and the read-only CLI surface.
- Define and test `sase://artifact/v1/file/...` parsing.

### Phase 2: inspector and copying

- Build the responsive native inspector from existing PreviewPanel and Artifacts-pane patterns.
- Integrate Textual Markdown rendering, source view, search, and metadata.
- Add the Copy as… palette and marked-set formatting.
- Try Textual clipboard transport first, then current platform adapters.
- Preserve the current agent `a` entry point and key accelerators.

### Phase 3: global catalog

- Add Artifacts → Files/Artifact Files.
- Add filters, sorting, grouping, and availability states.
- Reuse the inspector and actions without a second implementation.

### Phase 4: precise links and sharing

- Add line, heading, page, and time anchors.
- Add editor-at-location and OSC 8 clickable links where supported.
- Add explicit bundle export and, if demand warrants it, authenticated web publishing.
- Explore inline thumbnails/posters only after capability detection and fallback behavior are solid.

## Validation and success measures

The design should be tested against the cases that currently expose path and terminal assumptions:

- An explicit artifact whose original source was moved into managed storage.
- Two byte-identical artifacts from different agents.
- A stored artifact relocated without changing its record identity.
- A missing, expired, or corrupt stored object.
- Markdown with headings, tables, long code blocks, and line-range references.
- Very large text and binary files.
- A file containing ANSI/OSC/control-sequence bytes.
- Filenames beginning with `-`, non-UTF-8 names, and spaces.
- SSH plus tmux, with and without OSC 52 clipboard support.
- Narrow terminals and terminals without Kitty graphics.
- Multi-select copying across multiple agents.

Suggested measurable outcomes:

- A small local Markdown/text artifact becomes inspectable without a subprocess and without reading the whole file.
- Copying a canonical reference requires at most two deliberate actions from the inspector.
- Every retained artifact reference resolves after process restart, regardless of source-path existence.
- Unknown binary bytes are never emitted directly to the terminal.
- Copy feedback always says what was copied; path feedback distinguishes source from stored.
- The agent-scoped and global views use the same renderer, actions, and reference format.

## Ranked recommended improvements

1. **Introduce a focused artifact-file registry, durable ID, and `sase://` resolver.** This is the foundation for every reliable view, copy, deep-link, CLI, and future web workflow. Put it in `sase-core`, keep the content digest separate from record identity, migrate existing V1/path references, and explicitly avoid rebuilding a general artifact graph. **Impact: very high. Effort: medium-high.**

2. **Build a safe native Artifact Inspector for Markdown and text.** Reuse Textual's Markdown rendering and SASE's existing source preview/split-pane patterns; add search, rendered/source toggle, metadata, and responsive layout. As an immediate first patch, eliminate raw `cat` fallback for arbitrary artifacts. Keep the current media viewer as a capability-dependent backend. **Impact: very high, including a security/correctness fix. Effort: medium.**

3. **Replace ambiguous fixed copy actions with a unified “Copy as…” palette.** Make canonical reference the default, then offer Markdown link, selected excerpt with anchored reference, full contents, explicitly named source/stored paths, and metadata JSON. Support marked sets, retain current keys as accelerators, and use Textual clipboard transport with platform fallbacks and clear success feedback. **Impact: high. Effort: low-medium after items 1–2.**

4. **Add a global Artifacts → Artifact Files catalog.** Let users search and filter across agents, runs, projects, kinds, and time, then open the same inspector. This solves the current requirement to remember the producing agent and makes artifacts a first-class ACE surface. **Impact: high. Effort: medium; depends on item 1.**

5. **Add precise anchors and deep-link integrations.** Support line ranges, Markdown headings, PDF pages, and media timestamps; open editors at a location and render OSC 8 links when supported. Treat keyboard/CLI resolution as authoritative so SSH and remote paths still work. **Impact: medium-high. Effort: medium; depends on items 1–2.**

6. **Add capability-aware inline thumbnails and richer media metadata.** Provide image/PDF thumbnails and video posters when the terminal supports them, while retaining current external/tmux rendering and a clean metadata-only fallback. Do not make graphics-protocol support a prerequisite for artifact inspection. **Impact: medium. Effort: medium-high.**

7. **Add explicit publish/share and portable bundle workflows.** Once durable identity and safe rendering exist, offer self-contained bundles or authenticated web URLs for recipients who do not share the local SASE store. Keep publication opt-in and visibly distinct from copying a local `sase://` reference. **Impact: medium. Effort: high; best treated as a later layer rather than the core artifact UX.**
