# Unifying agent instruction files behind a single SASE.md spec with dynamic per-workspace rendering

Researcher: mus. Date: 2026-10-05. Swarm suffix: `__mus`.

Request: migrate all existing agent instruction files to a single `SASE.md`
that defines a spec for the agent instruction file, rendered dynamically into
the appropriate file in ephemeral workspaces before launching sase agents.
Motivations named in the request: (1) fix provider file-discovery bugs
documented in the `agent_instructions_budgeted_router` research (Grok reads
both `AGENTS.md` and `CLAUDE.md`; Codex does not read `~/AGENTS.md` at all);
(2) allow parts of the instruction file to render only for certain agents,
possibly via a new `%tag` directive; (3) surface any missed high-value
use cases. Deliverable: critique, adjustments, recommended solution.

## 1. Current state (verified in this checkout)

- The five root provider files are **byte-identical copies**, not symlinks or
  shims. Verified with `md5sum`: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
  `OPENCODE.md`, `QWEN.md` all hash to `93d8ec8d…`.
- They are **generated, not authored**. The AMD pipeline in `src/sase/amd/`
  renders `sase/memory/*.md` sources through
  `src/sase/amd/templates/AGENTS.template.md`
  (`{{ title }} / {{ core_sections }} / {{ reference_entries }} /
  {{ web_sections }}`); an `AGENTS.minimal.template.md` variant also exists.
- The reason for copies is stated in code. `src/sase/amd/constants.py`:
  each provider file is "a byte-for-byte copy of the root's `AGENTS.md`
  (some providers do not read `AGENTS.md` directly, and some do not support
  `@`-import composition)". Legacy one-line `@AGENTS.md` shims are only
  recognized for migration (`provider_shim_plan` in `src/sase/amd/_shared.py`).
- Home-layer files exist separately: `home/AGENTS.md.tmpl` plus provider
  templates, tracked as a distinct scope in
  `src/sase/memory/history/scopes.py` (project scope vs. home scope).
- Prior budgeted-router research in this repo (October 2026, reused here as
  prior work, not peer material) measured the rendered file at 283 lines /
  ~4.3k tokens, identified the decisions roster (~90 lines) as the dominant
  cost, documented the Grok double-load, and recommended a budgeted-router
  architecture with a CI size ratchet. That work is directly composable with
  this proposal: the renderer proposed here is where its budget would live.

## 2. The provider file-discovery bugs (what SASE.md must actually fix)

The request cites two real bugs. They have different shapes and want
different fixes; a single-source file fixes neither by itself.

1. **Grok double-load (reads both `AGENTS.md` and `CLAUDE.md`).**
   When both files exist with identical content, every Grok turn pays twice
   and, worse, sees duplicated (possibly contradictory-after-edit)
   instructions. Single-sourcing content does not fix this: as long as the
   renderer emits both files into the workspace, Grok still loads both.
   The fix is in **what gets emitted per provider**, not in where content is
   authored: for a Grok-driven workspace, emit exactly one file Grok reads
   (or emit provider files whose contents are disjoint — shared contract in
   one, Grok-only notes in the other — never duplicates). This is the
   strongest argument for *lease-time* rendering (Section 4): only at
   workspace setup is the provider known.
2. **Codex home gap (does not read `~/AGENTS.md`).**
   `src/sase/llm_provider/codex.py` works around this with a shadow
   `CODEX_HOME` (`_create_shadow_codex_home`, `_link_home_agents_fallback`,
   `AGENTS.override.md` handling). The failure mode is under-provisioning:
   a Codex agent silently misses home-layer policy. The fix is to **fold the
   home layer into the project file at render time for Codex workspaces**
   (or set the equivalent env/dir the harness already manages) — again a
   render-time decision keyed on provider, not a source-file reorganization.

Related unverified surface: whether Gemini/Antigravity (`agy` reads
`GEMINI.md` per the constants comment) also double-loads. The renderer
design should record each provider's load set in one table and be tested
against it, rather than hard-coding two fixes.

## 3. Critique of the plan

**The direction is sound; the plan as stated is half of the solution.**
A single human-editable source plus a deterministic renderer is strictly
better than five checked-in copies that drift: it eliminates a whole class
of sync bugs, gives one place to enforce the budgeted-router token/line
ratchet, and is a natural home for conditional rendering. External practice
agrees — the portable pattern is "one canonical source, provider files are
generated compatibility surfaces" (several harness projects converge on
exactly this; one states it as a rule: never make a provider-specific file
the source of truth).

Four adjustments are needed before building:

1. **Name what `SASE.md` is: source, not spec-of-a-spec.** The request calls
   it "a spec for the agent instruction file." That invites a meta-document
   describing a format, with the format implemented elsewhere — two things to
   keep in sync. Better: `SASE.md` (or `SASE.md.tmpl` under AMD conventions)
   **is** the single authored source; the existing AMD renderer plus a small
   conditional-block extension **is** the implementation. One artifact, one
   pipeline.
2. **Decide the two call sites, not one.** "Rendered dynamically in
   ephemeral workspaces" is necessary but not sufficient: external tools,
   humans, and non-sase harnesses read the checked-in root files directly
   and will never invoke the lease-time renderer. So the renderer needs two
   call sites sharing one code path: (a) **commit time** — `sase memory init`
   (re)grixon the checked-in root files (full, provider-maximal content) so
   the repo stays usable without sase; (b) **lease time** — ephemeral
   `sase_<N>` workspace setup renders the provider- and role-minimal file
   for the agent about to launch. Same function, different context flags.
   Rendering must be byte-deterministic given (source hash, context flags).
3. **Do not scope it to "agents" vaguely — scope conditionality to a
   closed axis.** Open-ended per-agent customization recreates the N-files
   problem inside one file. See Section 5 for why `%tag` is the wrong
   mechanism and what to use instead.
4. **Budget it from day one.** Combine with the budgeted-router outcome:
   the renderer enforces `<=100 lines / <=~1,600 tokens` (or whatever the
   adopted ceiling is) per rendered surface, prints per-section cost, and
   fails CI over budget. Conditional blocks make budgets per-surface, which
   is precisely what the router work could not do with one static file.

A further caution: conditional rendering means different agents operate
under different contracts. That is the point, but it makes debugging
("which instructions did this agent see?") harder. Every rendered file must
carry a short provenance header (source commit, context flags, renderer
version), and the existing `sase memory read` audit-log pattern should
extend to "which surface was rendered for this run."

## 4. Missed high-value use cases

Beyond the two cited bugs and conditional sections:

1. **Per-provider load-set correctness as data.** Encode each provider's
   actual load set (which filenames it reads, home vs. project, import
   support) in one tested table; the renderer emits the minimal sufficient
   set. Fixes Grok duplication and the Codex home gap structurally, and
   absorbs future providers without new bugs.
2. **Home-layer folding for remote dispatch.** `%dispatch` sends agents to
   remote machines where `~/AGENTS.md`/chezmoi state may not exist or may
   contain secrets. Lease-time rendering can fold *only the safe subset* of
   the home layer into the workspace file — or explicitly none — per
   dispatch target. A static checked-in file cannot do this.
3. **Token budget per model tier.** Cheap models need the minimal router;
   `xhigh` reasoning agents can afford fuller context. The renderer can take
   an effort/tier flag and select block variants. (Keep to two densities at
   most; more is untestable.)
4. **Role-specific surfaces.** This swarm itself is the example: researchers
   need memory-read routing and final-declaration rules but not the commit,
   bead-filing, or TUI sections that implementing workers need. Roles like
   `investigate` / `implement` / `review` are a better-tested second axis
   than agent identity.
5. **Nested-directory files.** `scopes.py` shows every subdirectory
   `AGENTS.md` plus shims is tracked scope. The single source should define
   how nested files inherit/override (currently implicit), and the renderer
   should produce them too.
6. **Drift detection and migration.** The renderer already plans
   create/overwrite/delete with blockers for custom content
   (`provider_shim_plan`). Reuse that machinery: `sase memory init` reports
   which provider files are stale, custom-diverged, or deletable, instead of
   silently overwriting.
7. **Provenance and debuggability.** Stamp rendered files with source hash +
   flags (Section 3); log the render event where workspace leases are
   recorded so `sase repo log`-style audit covers it.

## 5. How to identify agents for conditional rendering (do not use `%tag`)

The request's first instinct — a new `%tag` directive tagging agents, with
sections rendered only for matching tags — should not be adopted. Three
reasons:

- **Wrong layer.** `%`-directives (`%id`, `%model`, `%dispatch`, `%effort`,
  … enumerated in `src/sase/macro/_directive_types.py`) are **run-time
  prompt directives**: they modify one agent launch. Instruction-file
  rendering is **author/lease-time** content selection. Overloading one
  syntax for both confuses authors ("does `%tag` change this run or this
  file?") and couples the renderer to the prompt parser.
- **Identity is the least stable key.** Agent names/ids in sase are
  ephemeral (`research.3n.*` swarm members, numbered workspaces); tags bound
  to them rot within days and cannot be tested in CI. What is stable across
  months: *provider* (`claude`, `codex`, `grok`, `gemini`, `opencode`,
  `qwen`), *surface* (root vs. nested vs. home), *role* (investigate /
  implement / review), and *tier* (cheap vs. xhigh).
- **Combinatorial sprawl.** Free-form tags invite every team to mint its
  own; N tags yield 2^N surfaces, none of them covered by the budget or by
  tests. A closed axis with an allowlist keeps the surface matrix small
  enough to render and assert in CI.

**Recommended mechanism:** fenced conditional blocks in the single source,
keyed on a closed, enumerated context — e.g. markdown with frontmatter-style
attributes per section, or fenced directives such as
`::: only(provider=codex)` / `::: except(provider=grok)` — resolved by the
AMD renderer against an explicit context record
`{provider, surface, role, tier}`. Rules:

- Exactly one axis to start: **`provider`**. Add `role` only after two
  real role surfaces ship behind it; never add free-form keys without a
  decision record.
- Every conditional block must declare its fallback (shown to everyone
  else) or be marked additive-only; no silent disappearance of load-bearing
  rules.
- The set of valid keys is an allowlist in code (`PROVIDER_SHIM_FILES`-style
  constant); unknown keys fail the render loudly.
- `sase memory init` renders and asserts **every** matrix cell (all
  providers × surfaces), so conditional content is tested even though any
  one workspace sees only its slice.

## 6. Recommended solution

1. **Create the single source.** Move authorship to one file (working name
   `SASE.md`, living next to `sase/memory/` or as its index), keeping the
   existing memory-note corpus untouched — notes stay pay-per-read; only the
   always-loaded index surface is unified.
2. **Extend the AMD renderer (Python only, no Rust call site — presentation
   layer).** Add: (a) conditional-block parsing with provider-keyed
   inclusion; (b) the provider load-set table; (c) per-surface budget
   enforcement (lines + tokens, per-section cost report, CI failure over
   budget); (d) provenance header emission.
3. **Two call sites, one code path.** Commit-time full render of checked-in
   root files (keeps external tools working); lease-time minimal render into
   ephemeral `sase_<N>` workspaces keyed on `{provider, surface, role,
   tier}`. Deterministic given inputs.
4. **Fix the two cited bugs in the renderer, not the source.** Grok
   workspaces get a disjoint (never duplicated) file set; Codex workspaces
   get the home layer folded in. Cover both with tests asserting emitted
   file sets per provider.
5. **Phase the rollout.** Phase 0: single source + byte-identical output
   (no behavior change; proves the pipeline). Phase 1: provider load-set
   fixes + budget ratchet. Phase 2: one conditional axis (`provider`), then
   optionally `role`. Each phase ships with the matrix-render CI check.
6. **Explicitly reject:** `%tag` run-time tagging for render selection;
   free-form tag keys; hand-edited provider files (renderer owns them;
   custom content = blocker, reusing `provider_shim_plan` semantics);
   moving reference-note bodies (already pay-per-read and efficient).

Bottom line: yes, do it — as a single authored source plus a deterministic,
tested, budget-enforcing renderer with commit-time and lease-time call
sites, conditioned on a closed provider axis. That fixes the cited
double-load and home-gap bugs structurally (which single-sourcing alone
would not), unlocks role/tier surfaces later without re-architecture, and
composes with the budgeted-router line/token ceiling instead of competing
with it.
