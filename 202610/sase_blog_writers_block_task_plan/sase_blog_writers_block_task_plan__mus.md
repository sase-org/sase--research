# From Blog Draft to Obsidian Tasks: Splitting `sase_blog_contents.md` Into Actionable Work

Researcher: mus (independent report, 5-researcher swarm)

## 1. What the draft actually contains

The draft (`~/bob/sase_blog_contents.md`, frontmatter `parent: [[sase_blog]]`,
`type: [[article]]`) has three layers, and each layer wants a different kind of task:

1. **Finished prose (keep, don't task).** Two intro paragraphs are written: the
   pride/confessional hook ("take back some control from this thing that seemed like
   it was coming for a core part of my identity") and the SASE definition paragraph
   (meta-harness wrapping Claude/Codex/Muse/Grok/+3, "prototype gone wild" joke with
   ~17K commits / ~2.9M lines / ~1 user). No task needed except a later voice/polish
   pass.
2. **Four footnote TODOs (quick wins, each a ~15-minute task).** `[1]` pronunciation /
   acronym / Secure-Access-name-collision note; `[2]` Omnigent-as-meta-harness-example
   link; `[a]` missing links; `[b]` stale commit/line counts. These are closable,
   unambiguous, and independent — classic writer's-block antidote.
3. **Seven empty sections (the real blockage).** `1.1` Gates→Plans→Epics through `1.7`
   Routines and Jobs are all bare `TODO`, two with sub-TODOs (`1.3.1` skills/memory/
   provider-interface/NOT-hooks; `1.3.2` tribes/clans/families/hoods/panels). A bare
   "write section 1.x" task is too big to start — that size mismatch is the writer's
   block, not a lack of ideas.

## 2. What already exists in the vault (do not duplicate)

Verified via vault reads (not manual parsing):

- **Project structure is already built.** `sase_blog` (main project, 14 tasks, 2 open)
   owns the launch goal; `sase_pre_blog` (sub-project) is the pre-launch gate, blocked
   on `sase_blog__v1-draft`; `sase_blog_blockers` is canceled; `done/sase_blog_done`
   archives history. New tasks belong **inside this structure**, not in a new project.
- **The critical path is known and short.** `read-blog-notes` [x] →
   `write-introduction` [*] (in progress) → `v1-draft` [?] → `pre_blog#^prj` → release.
   The introduction's five dependencies include two references I confirmed **finished**
   via the reference library: `solving_code_review_at_anthropic` (read 2026-10-23;
   Bryan's own comment: reviewer-noise problem "feels like the problem I was having
   with mentors" — directly usable in the intro) and `redesigning_source_control`
   (read 2026-10-21; comments on sparse/virtualized checkouts and "Changesets are what
   'patches' should be!" — intro-ready material). The third ref,
   `structured_agentic_software_engineering`, is still `started`. So the intro is
   **unblocked on material** even where its checkboxes lag — worth one task to confirm
   and close out.
- **There is a ~20-item untriaged backlog hiding in `sase_blog.md`'s Requirements
   section** (GasTown term-mapping, AI-slop definition + categories incl. "prompt
   debt", candidate quotes, 3 AI diagrams, TUI screenshots, citations, alternations/
   "vibe evals", token-type explanation, stashed-prompt examples, "no weasels; just
   work" closer). Plus legacy outline material in `sase_blog_0_legacy_notes.md`
   (xprompts determinism, AXE/chops, beads/SDD, ChangeSpecs, pluggability, Neovim/PIW,
   telegram/mobile, future work). These are **not tasks yet** — they are the raw ore
   the spike task refines.
- **Two dead ends to avoid repeating** (from the done archive): a canceled
   "research how to get past writer's block" task (don't re-file it — this report is
   its replacement) and a canceled per-section-zettel project ("One post needs no
   zettel project"). Keep section work as tasks, not new notes.

## 3. Task-design constraints (Bryan's vault conventions)

- Every task lives on a project note as `- [ ] #task <text> [id:: <project>__<slug>]
   ^<slug>`, with `DEPENDS ON` / `BLOCKS` links, `fresh`/`scheduled`/`priority`
   fields, and `#ref`/`#prj` tags where applicable. New sections' tasks go on
   `sase_blog` (content work) so `v1-draft` can depend on them; launch-gate work stays
   on `sase_pre_blog`.
- Untriaged ideas enter as **Requirements bullets** on `sase_blog.md` first, then get
   promoted to tasks by the spike — this matches how the existing ~20 requirements got
   there.
- Reading tasks use the `#ref` pattern (`bob ref today <REF>` pulls one into the
   Pomodoro); propose `bob ref create <URL> -L` lines for missing captures (Omnigent)
   rather than creating refs directly. Never edit the vault from research — propose
   task text the human pastes.

## 4. Recommended strategy: "Quick wins → Spike → Section chains → Assembly"

**Do not create all section tasks now.** The sections are too vague — pre-writing
seven full task chains reproduces the blockage in task form. Instead, four waves:

### Wave 1 — Quick wins (file immediately, 4 tasks, no dependencies)

Each footnote TODO becomes one closable task on `sase_blog`: pronunciation/acronym
collision note; Omnigent link (+ `bob ref create` for Omnigent); audit-and-add-links
pass; refresh commit/line counts. Purpose: four checkmarks in one sitting to break the
block, plus the counts/links tasks feed every later section.

### Wave 2 — The spike (exactly ONE planning task, time-boxed)

File a single task like `sase_blog__section-spike`: "For each of §1.1–1.7, write one
thesis sentence + 3–5 bullet outline + source pointers (legacy notes, ref library,
code), and promote matching Requirements bullets to per-section tasks." Exit criteria
are explicit: **(a)** a thesis sentence per section, **(b)** the per-section task
chains below filled in, **(c)** Requirements bullets either linked to a section task
or left with a reason. Time-box it (one Pomodoro per section, max). This is the
"spike that produces more tasks" — and the *only* task allowed to produce tasks, so
planning stays bounded instead of becoming procrastination.

### Wave 3 — Per-section chains (produced by the spike, not by you now)

Uniform shape per section so starting is mechanical: `outline → draft → voice pass`.
Suggested order follows dependency, not document order: `1.5` Xprompts first (the
deterministic-prompt-language idea underpins Gates §1.1 and control flow), then `1.1`
Gates→Plans→Epics, `1.2` Beads, `1.4` VCS/workspaces (pairs with the finished
redesigning-source-control annotations), `1.3` Agent CLIs (+1.3.1/+1.3.2 as sub-tasks),
`1.6` Project mgmt, `1.7` Routines/Jobs last (least load-bearing for the narrative).
Each draft task `DEPENDS ON` its outline; all seven chains `BLOCK` `v1-draft`. The
GasTown term-mapping requirement becomes one sub-task per section rather than one big
task (small = started).

### Wave 4 — Assembly (file now as blocked placeholders, 4 tasks)

`v1-draft` assembly (already exists — add the seven chains as its dependencies once
the spike names them); voice/humor pass (slop definition, quotes, devil/halo emoji,
"no weasels" closer); media pass (3 AI diagrams, TUI screenshots, alternations
figure); podcast-listen pass (already exists as a task — keep it; Bryan's own workflow
uses episode-listening as final QA). These stay blocked and out of sight until Wave 3
moves.

## 5. Concrete starter set (paste-ready task text)

On `sase_blog`, no dependencies (Wave 1):

- `- [ ] #task Add pronunciation + acronym + Secure-Access-name-collision footnote.
   [id:: sase_blog__footnote-name] ^footnote-name`
- `- [ ] #task Add Omnigent meta-harness link + capture ref (propose: `bob ref create
   <omnigent-url> -L`). [id:: sase_blog__footnote-omnigent] ^footnote-omnigent`
- `- [ ] #task Link audit across intro + footnotes. [id:: sase_blog__footnote-links]
   ^footnote-links`
- `- [ ] #task Refresh commit/line/user counts in definition paragraph.
   [id:: sase_blog__refresh-counts] ^refresh-counts`

On `sase_blog`, the spike (Wave 2, depends on Wave 1 at most loosely — file now):

- `- [?] #task SPIKE (time-boxed): thesis sentence + mini-outline + task chain for
   each of §1.1–1.7; promote/link Requirements bullets; output is tasks, not prose.
   [id:: sase_blog__section-spike] [dependsOn:: sase_blog__footnote-links]
   ^section-spike` — 🧱 **BLOCKS:** `v1-draft` (via the chains it produces).

On `sase_blog`, assembly placeholder (Wave 4, file now, stays blocked):

- `- [?] #task Voice/humor pass: slop definition, quotes, emoji, closer.
   [id:: sase_blog__voice-pass] [dependsOn:: sase_blog__v1-draft] ^voice-pass`
- `- [?] #task Media pass: 3 AI diagrams, TUI screenshots, alternations figure.
   [id:: sase_blog__media-pass] [dependsOn:: sase_blog__v1-draft] ^media-pass`

Also: confirm-and-close the intro's finished-dependency checkboxes
(`ref-solving-code-review-at-anthropic`, `ref-redesigning-source-control` are read;
only `ref-structured-agentic-software-engineering` is still open) so
`write-introduction` reflects reality.

## 6. Why this beats the alternatives

- **Vs. "one task per section now":** seven "write §1.x" tasks are each as daunting
  as the blank draft — the blockage survives. The spike converts vague sections into
  mechanical outline→draft chains with thesis sentences, so each task starts mid-hill.
- **Vs. "a big planning project":** the canceled zettel-per-section project already
  proved heavyweight structure wrong for a single post. One time-boxed spike with
  named exit criteria can't metastasize.
- **Vs. "research more first":** the vault shows reading is ahead of writing (two of
  three intro-blocking refs finished, annotations intro-ready). The constraint is
  task size, not missing input — hence quick wins first, reading only as spike-sourced
  `#ref` tasks.

**Bottom line:** file 4 footnote tasks + 1 spike + 2 assembly placeholders now (7
tasks, all small except the deliberately-boxed spike); let the spike — and only the
spike — generate the seven per-section chains; keep everything inside the existing
`sase_blog` → `v1-draft` → `sase_pre_blog` → release critical path.
