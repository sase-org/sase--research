# Deferred memory-web rosters: stop inlining the decisions roster into every agent bundle

Research report by `mus` (5-researcher swarm, suffix `__mus`). Independent conclusions;
no peer report was consulted.

**Verdict:** the proposal is sound and worth building, with adjustments. The decisions
roster costs ~2,100 tokens (~38%) of every sase-agent instruction bundle while only
planners need it for discovery. The right fix is a generic per-web opt-out —
`roster: deferred` — plus one new audited roster command, no Rust changes, and a new
decision record (the project's own immutability rule requires one). Details and the
recommended rollout are below.

## 1. What I verified about the current system

### 1.1 The roster really is inlined into every bundle, and it dominates the budget

Measured in the sase checkout (`sase instructions render -s`):

| Section | Bytes | Tokens (est) | Share of bundle |
|---|---|---|---|
| Whole bundle | 22,166 | 5,549 | 100% |
| `proj.web.decisions` | 8,408 | 2,102 | ~38% |
| `proj.web.glossary` | 2,172 | 542 | ~10% |
| `proj.web.task_types` | 1,155 | 289 | ~5% |

The committed [AGENTS.md](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/AGENTS.md)
(20,854 bytes) carries the same roster: its Memory Webs section is 175 lines, of which
the Decisions subsection (`### 3.1 Decisions`) is 118 lines for 31 strands. The
descriptor file [sase/memory/decisions.md](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/sase/memory/decisions.md)
is 137 lines / ~2,161 tokens per [sase/memory/README.md](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/sase/memory/README.md).
So removing the decisions roster from the always-loaded bundle saves roughly
**2,000 tokens per agent turn** — the single largest cheap win available in the bundle
(the doctor check
[src/sase/doctor/checks_instructions_bundle_size.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/doctor/checks_instructions_bundle_size.py)
already names "memory web rosters" as the thing to shrink when a bundle nears its cap).

### 1.2 How the roster gets into the bundle (pipeline)

- Web model and roster styles live in
  [src/sase/memory/web/models.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/memory/web/models.py)
  (`WebRosterStyle = "inline" | "list"`) and
  [src/sase/memory/web/frontmatter.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/memory/web/frontmatter.py)
  (`_VALID_ROSTERS`, error `"roster must be inline or list"`).
- Roster rendering is
  [src/sase/memory/web/roster.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/memory/web/roster.py)
  (`render_strand_roster`, `render_web_body_with_roster`). `roster: list` webs render
  the numbered title/slug/summary list; `roster: inline` (glossary) renders the
  semicolon-separated keyword line.
- A subtle point the proposal should get right: `strip_managed_roster_markers` strips
  only the `<!-- sase:strands -->` marker *lines*, not the roster content. In
  [src/sase/main/init_memory/root_planning.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/main/init_memory/root_planning.py)
  (`memory_web_root_plan`), the on-disk descriptor (`note_overlay`) keeps the full
  managed roster, and the `web_note_bodies` used for `AGENTS.md`/bundle rendering keep
  the roster text with markers removed. There is no "roster already stripped" shortcut
  to exploit — deferral is genuinely new behavior.
- Bundle assembly consumes the same units:
  [src/sase/amd/memory_units.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/amd/memory_units.py)
  (`collect_memory_root_units`, `render_memory_root_units`) and
  [src/sase/instructions/sections_units.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/instructions/sections_units.py)
  (`web_section`, `web_section_id`). The compiler
  ([src/sase/instructions/compile.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/instructions/compile.py))
  additionally registers every `roster: list` web as a `CompactableWeb` for the
  compaction ladder
  ([src/sase/instructions/compaction.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/instructions/compaction.py)).
- The closed compaction-step vocabulary
  (`INSTRUCTION_MANIFEST_COMPACTION_STEPS = ("superseded_summaries", "list_rosters")`)
  in
  [src/sase/core/instruction_manifest.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/core/instruction_manifest.py)
  mirrors the Rust core, which owns validation. Per the `rust-core-required` decision,
  any new compaction step or manifest kind is a cross-repo change needing a
  `sase-core-revision.txt` pin move. **The recommended design avoids this entirely.**

### 1.3 The suspected gap is real: no roster-only audited read exists

- `sase memory show decisions` dumps **all 31 strand bodies (1,197 lines)** unaudited.
  `sase memory read decisions -r ...` (bare web selector) likewise resolves to every
  strand — far too expensive for roster discovery, and it is exactly what a planner
  should *not* have to do.
- `sase memory web show decisions` prints an unaudited rich table (`table`/`names`/
  `json`) — good for humans, wrong shape for agents (not the AGENTS.md roster prose),
  and unaudited by design (`show` "is for humans and tooling").
- The audit schema already generalizes to webs:
  [src/sase/memory/_read_log_models.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/memory/_read_log_models.py)
  (`MemoryReadEvent.kind: "note" | "web" | "strand"`, `selectors`,
  `resolved_targets`, `included_targets`, schema version 3). A roster read fits this
  schema with no migration (see §4.2).
- TUI: the Memory panel already renders per-web cards with `Roster`, `Links`, `Size`,
  and `Last audited read` rows
  ([src/sase/ace/tui/modals/memory_panel_web_rendering.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/ace/tui/modals/memory_panel_web_rendering.py),
  summaries from
  [src/sase/ace/tui/memory_panel_catalog.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/ace/tui/memory_panel_catalog.py).
  No per-agent memory-read surface exists in the decks, so the Memory panel web card
  is unambiguously the "appropriate place".
- The shared skills
  [src/sase/macros/skills/sase_plan.md](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/macros/skills/sase_plan.md)
  and
  [src/sase/macros/skills/sase_memory_read.md](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/macros/skills/sase_memory_read.md)
  confirm the constraint: `sase_plan` skill step 1 already mandates one memory read
  (`sase_sizes.md`), and neither skill may be edited per-project. The trigger
  instruction therefore has to live in project-owned memory — i.e. the decisions
  descriptor body itself, which stays inlined. That is the elegant core of the
  proposal: **replace the 8 KB roster with a ~3-line conditional instruction in the
  one place every agent still loads.**

## 2. Critique: is this a good idea?

**Yes — with five adjustments (marked [ADJUSTMENT] in §4).** Strengths first:

1. **The savings are real and permanent.** ~2,000 tokens/turn across every agent in
   two projects, independent of provider caps or compaction luck. Today's compaction
   ladder only trims rosters when a bundle is already oversize; the common case pays
   full price forever.
2. **Generic, not bespoke.** A per-web `roster:` mode fixes the class (glossary and
   `task_types` keep working unchanged; any future heavy web can opt in). No
   decisions-specific code paths, honoring the "no custom support" constraint.
3. **It respects the hardest constraint.** Not touching the shared `/sase_plan` skill
   and instead putting the conditional in project memory is the only viable trigger,
   and it degrades gracefully: an agent that ignores it is no worse off than an agent
   that ignores any reference-memory MUST today.
4. **Auditability is preserved by construction** if the roster command requires `-r`
   and logs (unlike `web show`, which is correctly unaudited human tooling).

Risks and honest costs:

1. **Planners are not the only agents who need decisions; some decisions are
   safety-relevant for everyone.** `host-owned-completion`, `gates-never-block`, and
   `guarded-recipes` constrain *implementer* behavior today by ambient exposure. After
   deferral, a non-planning agent never sees them unless the plan inlines them. The
   proposal as written underestimates this: plans must start carrying the decisions
   they rely on (the plan skill already embeds reviewer choices, so citing decision
   slugs is a small extension of an existing habit, but it is a new obligation that
   needs stating explicitly — [ADJUSTMENT 1]).
2. **Compliance is social, not enforced.** "MUST read the roster" has exactly the
   force of every other memory MUST. Mitigation is cheap: the descriptor line should
   be short, imperative, and copy-pasteable, and `sase memory init --check` / CI
   should validate the new frontmatter value so a typo fails loudly rather than
   silently rendering nothing.
3. **Discovery degrades for quick non-plan work.** An agent doing a small task that
   *should* respect a decision (e.g. creating a gate) loses serendipitous discovery.
   Acceptable — small tasks already routinely skip reference memory — but the rollout
   should say so openly and keep strand-level `sase memory read decisions:<keyword>`
   working unchanged (it does; strands are untouched).
4. **Two-project + generated-web surface.** bob-cli needs the identical descriptor
   change via its own checkout, and the mechanism must not break the generated
   `task_types` web (`roster: list`, built by `build_generated_task_types_web`) or
   `roster: inline` webs. All three modes must keep passing through validation,
   rendering, and the compaction ladder's `CompactableWeb` filter (deferred webs
   simply stop registering — strictly fewer bytes, no ladder change needed).
5. **The project's own rules demand a decision record.** Per the decisions
   descriptor's immutability rule, changing `memory-webs` /
   `webs-render-in-their-own-section` behavior requires writing a *new* decision
   strand and marking the old ones `superseded-in-part` — not editing them. The plan
   should include this instead of discovering it mid-implementation ([ADJUSTMENT 4]).

## 3. Alternatives considered

| Approach | Verdict |
|---|---|
| Convert decisions to a reference note (one-line description + on-demand read) | Rejected. Loses the web's keyword/alias/prefix resolution, per-strand audit, summaries, and validation; strictly worse discoverability than a deferred roster. |
| New compaction-ladder step that drops list rosters | Rejected as the primary fix. Only helps oversize bundles (the common case still pays), and a new ladder step touches the Rust-owned closed vocabulary (`INSTRUCTION_MANIFEST_COMPACTION_STEPS`) plus the `sase-core-revision.txt` pin — the heaviest change for the least reliable saving. |
| Purpose-scoped bundles (planners get roster, others don't) | Rejected. The host binds `purpose` today (`ordinary`, `declaration_recovery`, `conflict_repair`), but "is planning" is not a fact; adding it is a manifest/Rust change with delivery-matrix fallout. Overkill by an order of magnitude. |
| Editorial trimming of summaries | Complementary hygiene, not a solution. 31 summaries × ~100 chars saves hundreds of tokens once and regrows; do it opportunistically, don't depend on it. |
| Status quo (rely on compaction) | Rejected. Pays ~2,100 tokens/turn in the common case forever; the doctor check already flags rosters as the pressure point. |

## 4. Adjustments to the requirements

1. **[ADJUSTMENT 1] State the plan-citation obligation.** The deferred-roster
   instruction in the descriptor must tell planners to (a) read the roster, (b) read
   the strands they rely on, and (c) **cite the applied decision slugs in the plan
   file** so implementers inherit the constraints without ambient exposure. Without
   (c), `host-owned-completion`-class constraints go dark for coders.
2. **[ADJUSTMENT 2] Prefer `roster: deferred` as the mode name, and keep the managed
   roster region on disk.** Alternatives (`off`, `manual`, `on-demand`) either read as
   "deleted" or overpromise. `deferred` says exactly what happens: rendering is
   deferred to an explicit command. `sase memory init` must keep syncing the managed
   `<!-- sase:strands -->` region in the descriptor file — it becomes the source of
   truth the roster command renders from (via the existing `render_strand_roster`, so
   output is byte-identical to today's AGENTS.md roster).
3. **[ADJUSTMENT 3] Make the roster command audited-only with a required reason.**
   Recommended shape: `sase memory web roster <web> -r "<why>"`. No `show`
   equivalent (preserves the read/show audit split the `sase_memory_read` skill
   teaches). Audit encoding that avoids a schema bump: `kind="web"`,
   `canonical_path` = the descriptor path (e.g. `sase/memory/decisions.md`),
   `selectors=("decisions",)`, `included_targets=()` (no strand bodies included),
   `byte_count` = roster bytes. A full-web read has non-empty `included_targets`, so
   the two stay distinguishable in `sase memory log --json`, and the Memory panel
   web card's existing `Last audited read` row lights up with no TUI data-model
   change. Optional TUI polish: render a `ROSTER` badge / "roster read" line on the
   web card when the latest matching event has empty `included_targets`.
4. **[ADJUSTMENT 4] Author a new decision strand; mark old ones superseded-in-part.**
   E.g. `deferred-rosters`: claim (heavy webs defer roster rendering to an audited
   command), rejected alternatives (reference-note conversion, ladder step,
   purpose-scoped bundles), cost (planner pays one extra read; non-planners lose
   ambient discovery), reopen condition. Mark `memory-webs` and
   `webs-render-in-their-own-section` superseded-in-part with `[[...]]` back-links,
   in both sase and bob-cli.
5. **[ADJUSTMENT 5] Explicitly rule out Rust/manifest changes.** No new compaction
   step, no new manifest section kind, no new `MemoryReadKind` value (schema stays v3).
   Deferred webs drop out of `CompactableWeb`; everything else in compile/compaction
   is untouched. Frontmatter validation (`_VALID_ROSTERS` + the
   `validate_memory_webs` summary-required rule, which should be waived or kept?
   — keep requiring summaries: the roster command still renders them) stays
   Python-side. Flag as an implementation-time check that no Rust parser duplicates
   the `roster:` vocabulary.

## 5. Recommended solution

**Per-web deferred roster rendering ("beautiful" = one knob, one command, zero
special cases):**

1. **Frontmatter:** allow `roster: deferred` next to `inline`/`list`
   ([frontmatter.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/memory/web/frontmatter.py)).
   Semantics: descriptor body + managed roster region still sync to disk unchanged;
   `AGENTS.md` / bundle rendering emits the descriptor body with the roster region
   replaced by a fixed 2–3-line instruction naming the web and the exact command,
   e.g.: *"The `decisions` roster is deferred to save context. Any agent writing a
   SASE plan MUST run `sase memory web roster decisions -r \"<why>\"` and read the
   strands it relies on, citing applied decisions in the plan."* Reuse
   `roster_label` in that line so it reads naturally for any web.
2. **Command:** `sase memory web roster <web> -r <reason>` (with `-f`,
   `PATTERN`-filter parity borrowed from `web show`). Output = today's
   `render_strand_roster` markdown for that web, so it "looks like the roster
   currently in AGENTS.md" by construction, not by imitation. Audited per §4.3.
3. **TUI:** no data-model change. Confirm the web card shows the roster read under
   `Last audited read`; add the small `ROSTER` affordance (§4.3) as the visible
   "display it in the TUI" deliverable, plus `sase memory log` already covering
   inspection.
4. **Content (both repos):** set `roster: deferred` on `sase` and `bob-cli`
   `decisions.md`; keep the descriptor prose, add the plan-citation sentence; add
   the `deferred-rosters` decision strand and supersede-in-part markings (§4.4).
   Open bob-cli strictly through `/sase_repo` (external repo) — never web-fetch its
   files.
5. **Regeneration & docs:** run `sase memory init` in both projects (refreshes
   `AGENTS.md` + `CLAUDE.md` copies + provider shims; `init --check` CI must go
   green), update
   [docs/reference/agents/memory-initialization.md](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/docs/reference/agents/memory-initialization.md)
   (it documents the inline-roster behavior verbatim today) and the
   [design-decisions glossary entry](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/docs/reference/design-decisions.md),
   and extend the web frontmatter docs with the third mode.
6. **Tests:** frontmatter validation (accept/reject `deferred`), roster-command
   output byte-equality with the previously inlined roster, audit-log shape
   (`included_targets=()`), bundle shrinkage (~8 KB off `proj.web.decisions`,
   replaced by the instruction stub), init round-trip (disk roster region intact,
   `init --check` clean), and TUI card rendering for a roster event.

**Expected outcome:** every agent's bundle shrinks by ~8 KB / ~2,000 tokens; only
planning turns pay the roster read (plus cited strands); reads stay fully audited
and visible in the Memory panel; no shared skill, Rust core, or manifest change.

## 6. Open questions for the lead

1. Should any strands be *pinned* always-inline (e.g. `host-owned-completion`,
   `gates-never-block`) via an optional frontmatter list, or is plan-citation (§4.1)
   sufficient? I recommend shipping without pinning, adding it only if implementers
   demonstrably miss safety-critical decisions.
2. Should `sase memory web show` (unaudited table) gain a warning when pointed at a
   deferred web, nudging toward the audited roster command? Cheap, prevents the
   audit bypass from becoming the habitual path.
3. bob-cli sequencing: land the mechanism in sase first with sase's own decisions
   deferred, then apply the one-line frontmatter change to bob-cli — or both
   atomically? I recommend mechanism-first, content-second.
