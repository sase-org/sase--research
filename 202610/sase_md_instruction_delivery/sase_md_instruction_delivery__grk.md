# Launch-Time Instruction Projection, Not a Root `SASE.md`

> **Research query:** Migrate every existing agent instruction file to a single
> `SASE.md` spec, then construct the provider-appropriate instruction file
> dynamically in ephemeral workspaces before launch. The change should fix the
> load-surface bugs in
> `202610/agent_instructions_budgeted_router/agent_instructions_budgeted_router.md`
> (Grok double-loads `AGENTS.md` and `CLAUDE.md`; Codex does not see
> `~/AGENTS.md`), unlock audience-specific rendering (a `%tag` directive was
> the first instinct), surface missed high-value uses, critique the plan, and
> end with a recommended solution.

Independent report (`__grk`) · 2026-10-05 · sase workspace `sase_14`.

## Bottom line

**Build a launch-time instruction projector in the provider adapters. Keep
`AGENTS.md` as the committed, portable compiled document. Do not introduce a
root `SASE.md`, and do not add a `%tag` directive.**

The idea behind the request is right: SASE already clones a tree into an
ephemeral workspace, already knows the provider at spawn, and already has a
compiler (`sase memory init`) whose output is then copied five ways. The last
mile — *which files this provider will actually concatenate* — is currently
accidental. Making that last mile explicit fixes the Grok and Codex bugs and
unlocks audience-specific content.

The proposed vehicle is the wrong one.

- A new root `SASE.md` collides with the core note `sase/memory/sase.md`, is
  invisible to every vendor CLI, and duplicates a compiler SASE already has
  (memory notes + Jinja templates + `sase memory init`).
- `AGENTS.md` is the cross-tool standard (Agentic AI Foundation). Claude Code
  2.1.277+, Codex, OpenCode, Qwen Code, Antigravity, and Grok all read it.
  Dropping it for a SASE-private name makes unmanaged `sase tmux-agent`
  sessions, GitHub Copilot, Cursor, and a bare clone worse.
- `%tag` / `%t` was retired in favor of `%tribe`. Launch context already
  carries provider, model, agent id, clan, tribe, bead, and macro kind. A new
  free-form tag axis would become soup.
- Writing different bytes over tracked `AGENTS.md` / `CLAUDE.md` in a
  workspace dirties git. The finalizer will try to commit them. Grok also
  concatenates every matching filename it can see, including tracked shims
  that `.gitignore` cannot hide.

The cited bugs are **load-surface** bugs. The budgeted-router work is a
**renderer** bug. Audience-specific sections are a **facet** feature. One new
markdown file does not solve all three, and coupling them will delay the cheap
fixes.

## Scope and inputs

- Prior research:
  `202610/agent_instructions_budgeted_router/agent_instructions_budgeted_router.md`
  (lead consolidation, 2026-10-02). I treated that file as shared input and
  did not read this swarm's peer reports.
- In-tree: `src/sase/amd/`, `src/sase/llm_provider/{claude,codex,grok,muse}.py`,
  `docs/{agent_providers,memory,init,configuration}.md`,
  `sase/memory/glossary/agent-instruction-file.md`,
  `sase/memory/decisions/{adapters-normalize-harnesses,webs-render-in-their-own-section}.md`,
  live `AGENTS.md` / shims / home files.
- Vendor discovery, checked 2026-10-05: xAI Grok Build project rules, Anthropic
  Claude Code memory docs (incl. AGENTS.md fallback since 2.1.277), OpenAI
  Codex `AGENTS.md` guide, OpenCode instructions, Qwen Code memory docs,
  Antigravity rules docs.

## What exists today

### Authoring and compile

Memory notes under `sase/memory/` are the source of truth. `sase memory init`
inlines `type: core`, lists `type: reference` triggers, and renders each
memory web into `## Memory Webs`. Jinja templates
(`AGENTS.template.md`, `memory-sase.template.md`) supply structure. The
compiler writes one root `AGENTS.md`, then copies it byte-for-byte to
`CLAUDE.md`, `GEMINI.md`, `QWEN.md`, and `OPENCODE.md` in the same directory
(`PROVIDER_SHIM_FILES` in `src/sase/amd/constants.py`). Nested `AGENTS.md`
files (`tools/`, `src/sase/ace/`, `demos/tapes/`) get the same copy treatment.

There is no `GROK.md`. Grok reads `AGENTS.md` natively.

This workspace, measured 2026-10-05:

| File | Lines | md5 |
| --- | ---: | --- |
| `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `QWEN.md` / `OPENCODE.md` | 285 | identical `93d8ec8d…` |
| `tools/AGENTS.md` | 81 | path-scoped |
| `src/sase/ace/AGENTS.md` | 48 | path-scoped |
| `~/AGENTS.md` and the four home shims | 74 | present |

Home has no `~/.codex/AGENTS.md` and no `~/.grok/` project-rules file besides
`README.md`. Codex's shadow-home fallback is therefore the only path that can
expose `~/AGENTS.md` to Codex. Grok has no equivalent.

The glossary still states the invariant this proposal would break: *sase
supports one agent instruction file per supported agent CLI and ensures that
all agent instruction files in the same directory contain the same contents.*

### Launch

Workspaces are numbered clones under
`~/.local/state/sase/workspaces/.../sase_<N>`. That path is inside `$HOME`.
Instruction files ride along with the clone. Adapters then inject a short
single-turn contract (`--append-system-prompt` for Claude, `developer_instructions`
for Codex, prompt prefix for Muse). `capture_instruction_snapshot` inventories
root files plus the first readable home file; it does not record what the
provider actually loaded, and it skips nested files.

Generated skills already do per-provider Jinja (`{{ provider_name }}` in
`src/sase/macros/skills/`, rendered by `sase skill init`). That is deploy-time
into distinct destinations. Instruction files cannot use the same trick:
several providers read overlapping filenames from the same directory.

## Provider load-surface matrix

This is the fact that decides the architecture. Each CLI concatenates a
different set of paths. Byte-identical shims are a workaround for that, and
they are also how the workarounds fight each other.

| Provider | Project files | Walk | Home / global | Double-load if SASE shims exist | Home `~/AGENTS.md` today |
| --- | --- | --- | --- | --- | --- |
| **Claude Code** | `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`. `AGENTS.md` only when **no** CLAUDE-family file exists on the ancestor chain (default `claude-md-or-agents-md`, since 2.1.277). | Cwd **up** toward `/` (past git root). Nested files load on Read. | `~/.claude/CLAUDE.md` plus any `~/CLAUDE.md` on the ancestor walk. `claudeMdExcludes` can suppress paths. | Project `CLAUDE.md` wins; project `AGENTS.md` is ignored. Home `~/CLAUDE.md` still concatenates. | Loaded, because the workspace lives under `$HOME`. |
| **Grok Build** | Every match of `AGENTS.md` / `Agents.md` / `AGENT.md` / `CLAUDE.md` / `Claude.md` / `CLAUDE.local.md`, plus `.grok/rules/*.md`. `[compat.claude] agents = false` does **not** stop `CLAUDE.md`. | Repo root **down** to cwd. Gitignored files skipped; **tracked** files cannot be gitignored. | `~/.grok/` (and `$GROK_HOME`), **not** `~/AGENTS.md`. | **Yes: project `AGENTS.md` + project `CLAUDE.md`.** Documented in `docs/agent_providers.md`. | **Not loaded.** |
| **Codex** | At most one file per directory: `AGENTS.override.md`, then `AGENTS.md`, then `project_doc_fallback_filenames`. Default cap **32 KiB** (`project_doc_max_bytes`). | Git root **down** to cwd. Stops at git root. | `$CODEX_HOME/AGENTS.override.md` or `AGENTS.md`. SASE shadow home links `~/AGENTS.md` only when the real Codex home has neither file. | No (ignores `CLAUDE.md`). | Only via the shadow-home fallback. A native `~/.codex/AGENTS.md` suppresses it. Ancestor walk never sees `~/AGENTS.md`. |
| **OpenCode** | Prefers `AGENTS.md`; falls back to `CLAUDE.md` if no `AGENTS.md` exists on the walk. | Up from cwd; also a global file. | `~/.config/opencode/AGENTS.md`, then `~/.claude/CLAUDE.md`. | Usually no: `AGENTS.md` wins and `CLAUDE.md` is skipped. | Depends on whether OpenCode treats `$HOME/AGENTS.md` as an ancestor file (workspace is under `$HOME`). |
| **Antigravity (`agy`)** | `AGENTS.md` **and** `GEMINI.md` (and `.agents/rules/*.md`). | Directory of the file being read, up to workspace root. | `~/.gemini/AGENTS.md` / `GEMINI.md`. | **Yes if both shims exist** — same shape as Grok. SASE docs have not verified this; vendor docs say both names load. | Via `~/.gemini/`, not `~/AGENTS.md`. |
| **Qwen Code** | `QWEN.md` **and** `AGENTS.md` by default (v0.13.0+). | Hierarchical, Gemini-CLI heritage. | `~/.qwen/QWEN.md`. | **Likely yes** for identical `QWEN.md` + `AGENTS.md`. | Via `~/.qwen/`, not `~/AGENTS.md`. |
| **Muse** | Not documented in SASE. Launch uses `--prompt-file` and `--no-foreign-personal-context`. | Unknown. | Unknown. | Unverified. Measure with the CLI before projecting. | Unverified. |

### The Claude-home trap (why shims cannot simply be deleted)

Claude's AGENTS.md fallback is: *if any CLAUDE-family file exists on the
ancestor chain, ignore `AGENTS.md`.* SASE workspaces sit at
`/home/<user>/.local/state/sase/workspaces/...`. `~/CLAUDE.md` is on that
chain. Deleting the project `CLAUDE.md` would make a Claude SASE agent load
**home instructions only** and miss the 285-line project file.

That is why `sase memory init` writes a full project `CLAUDE.md` rather than a
one-line `@AGENTS.md` shim, and why "just stop generating `CLAUDE.md`" is not
a Grok fix. The projector has to hide `CLAUDE.md` from Grok **and** keep a
real `CLAUDE.md` for Claude, while still loading home content for providers
that never walk to `~/`.

Grok `--rules` and Codex `$CODEX_HOME/AGENTS.md` are the injection hooks that
already exist for the providers that need them.

## Critique of the plan

### Is a single source plus launch-time materialization a good idea?

Yes, as a **projection layer**. SASE already knows the provider at spawn,
already snapshots instruction bytes, and already normalizes harnesses in
adapters (`decisions:adapters-normalize-harnesses`). Extending that decision
from "single-turn contract" to "instruction load-surface" is the coherent
move.

### Is replacing every instruction file with a root `SASE.md` a good idea?

No.

1. **The source of truth is already `sase/memory/`, not `AGENTS.md`.**
   `AGENTS.md` is compiled output. Migrating *outputs* into a new markdown
   spec adds a third authoring surface (notes, templates, `SASE.md`) and
   invites agents to edit a file no vendor CLI loads.
2. **`SASE.md` is a bad name.** `sase/memory/sase.md` is the always-inlined
   core contract. A root `SASE.md` will be grepped, opened, and mistaken for
   that note. It will also be mistaken for an instruction file by future CLI
   discovery (Grok already scans several aliases; a `SASE.md` matcher is a
   matter of time).
3. **Launch-time writes over tracked files dirty the workspace.** Five
   identical shims are tracked. Overwriting them with a faceted render shows
   up in `git status`. `/sase_final` will offer them as a commit. Grok cannot
   be told to skip a tracked `CLAUDE.md` with `.gitignore`. Any projector that
   mutates tracked paths needs skip-worktree, a restore-on-exit dance, or
   (better) **untracking the shims and gitignoring them**, then reconciling
   the workspace on every launch because workspaces are reused.
4. **Unmanaged CLIs still need a portable file.** `sase tmux-agent` launches
   a raw vendor CLI in the same tree. GitHub Copilot, Cursor, and a clone
   without SASE read `AGENTS.md`. A spec that only materializes inside SASE
   workspaces leaves those sessions under-instructed unless `AGENTS.md`
   remains committed and complete.
5. **The budgeted-router bugs are mostly not a file-format problem.** Grok
   double-load is "two filenames, same bytes." Codex-home is "wrong global
   path." Both are solvable with a projector and the existing compiler. The
   285-line encyclopedia is a renderer/roster problem already specified in
   the 2026-10-02 report. Folding that epic into a `SASE.md` migration delays
   the cheaper win.
6. **A markdown DSL for conditionals will leak.** Claude strips HTML comments
   *except inside code fences*. Directives left in a file the CLI loads
   either cost tokens or, if a provider does not strip them, get treated as
   instructions. Conditionals belong in the compiler/projector, off the load
   path.
7. **`@import` shims were already tried and abandoned** (April–June 2026;
   `PROVIDER_SHIM_CONTENT = "@AGENTS.md\n"` remains only for migration).
   Codex does not expand them. Claude ancestor imports have a documented
   subdirectory expansion bug. Full copies exist for that reason. A `SASE.md`
   that the CLI does not read is fine; a `SASE.md` that some CLIs start
   reading later is another double-load.

### Would I take a different approach?

Yes: **two existing layers plus one new last mile.**

```
memory notes + Jinja templates
        │  sase memory init   (compile, budget, review)
        ▼
committed AGENTS.md          (portable default; humans; unmanaged CLIs)
        │  launch projector   (provider adapter + launch context)
        ▼
exactly the files / flags / shadow-home entries this CLI will load once
        │
        ▼
instruction_snapshot records the effective load, not just the inventory
```

Audience-specific body text is a later, optional input to the same projector
(see [Facets](#how-to-identify-agents-facets-not-tag)). It does not require a
new root file.

## How to identify agents: facets, not `%tag`

`%tag` / `%g` / `sase agent tag` were removed; the replacement is `%tribe` /
`%id(..., tribe=)` / `#tribe:`. Reusing the old name is a migration trap for
every prompt, completion table, and error path that still mentions it.

The interesting audiences are almost all **already in launch context**:

| Facet | Source | Example |
| --- | --- | --- |
| `provider` | resolved adapter | `claude`, `grok`, `codex`, `agy`, `qwen`, `opencode`, `muse` |
| `model` / `alias` | `%model` | `grok-4.6`, `@coder` |
| `kind` | macro / alias / bead | `research`, `coder`, `review`, `plan` |
| `id` | `%id` | `grk`, `research.3n.grk` |
| `clan` | `%clan` | `research.3n` |
| `tribe` | `%id(tribe=)` | `@review` |
| `bead` | `%id(bead=)` / assignment | `sase-xx` |
| `scope` | compiler | `home`, `project`, `nested:tools` |

**Closed vocabulary, matched at projection time.** Author it as frontmatter on
a memory note or as Jinja in an existing template:

```yaml
# sase/memory/research_isolation.md
---
type: core
when:
  kind: [research]
---
Do not open peer swarm reports matching `__cdx.md`, `__cld.md`, …
```

```jinja
{# memory-sase.template.md #}
{% if launch.provider == "grok" %}
Grok loads AGENTS.md only; do not look for GROK.md.
{% endif %}
```

Rules for the matcher:

- Unknown `when:` keys fail `sase memory init --check` (no silent no-ops).
- Default is "all audiences." Facets are additive includes, with an explicit
  `except:` if we ever need excludes.
- `kind` is inferred: `#research` / `#research_swarm` → `research`;
  `%model:@*_coder` → `coder`; plan/questions handoff → `plan`. Users who
  want an extra label use **tribe**, which already exists.
- Provider is the adapter name, not the short code (`grok` not `grk`), so a
  rename of display codes cannot retarget instructions.

A prompt directive whose only job is to change the instruction file creates a
circular UX: the file is generated from the same prompt that the file is
supposed to govern. Facets derived from selectors the user already wrote
(`%model`, `%clan`, `#research_swarm`) avoid that.

## High-value use cases the request missed

The request named two: Grok double-load, Codex missing home, plus
audience-specific sections. These are additional, and several are larger.

1. **Claude-home suppression of project `AGENTS.md`.** Workspaces under
   `$HOME` plus `~/CLAUDE.md` mean Claude never takes the AGENTS.md fallback.
   The projector must write a project `CLAUDE.md` for Claude even after shims
   leave git.
2. **Home-content union.** Claude sees `~/CLAUDE.md` by ancestor walk. Codex
   sees home only via `$CODEX_HOME`. Grok sees home only via `~/.grok/`.
   Qwen via `~/.qwen/`. Antigravity via `~/.gemini/`. A projector that
   *merges* home+project into the file the CLI will load, then excludes the
   native home path (`claudeMdExcludes`, skip linking a second Codex global,
   no extra Grok home file), gives every provider the same union. Today Grok
   SASE agents get **zero** home memory.
3. **Antigravity and Qwen double-load.** Same shape as Grok, currently
   unverified in SASE. `GEMINI.md` + `AGENTS.md` and `QWEN.md` + `AGENTS.md`
   are identical in this repo. Measure with `agy` / `qwen` inspect-or-memory
   commands, then hide the extra name.
4. **Codex 32 KiB cap.** Combined home (74 lines) + project (285) + nested
   along cwd is still under 32 KiB today, and will not stay that way if the
   router is not ratcheted. The projector should fail loud when the Codex
   projection exceeds `project_doc_max_bytes`, rather than silently truncating.
5. **Workspace reuse.** A gitignored `CLAUDE.md` left by a previous Claude
   claim on `sase_14` would still be concatenated by a later Grok claim.
   Projection is a **reconcile** step: create the files this provider needs,
   remove the ones it must not see.
6. **Nested path-scoped files.** `tools/AGENTS.md` and `src/sase/ace/AGENTS.md`
   load for Codex/Grok only along the cwd path (so not at repo-root launch)
   and for Claude on Read. A projector can either leave them (current
   semantics) or flatten a pointer into the root file for root-cwd agents.
   The budgeted-router follow-up to replace duplicated Symvision text with a
   `symvision.md` trigger lives here.
7. **Single-turn contract currently duplicated.** Adapters inject it; the
   compiled `sase.md` section also states it. The projector can drop the
   prose for providers whose adapter already injects it (budgeted-router
   adjustment G) without a new file format.
8. **Launch-context interpolation.** Agent id, workspace number, bead id,
   clan isolation rules ("do not read `__cdx.md`") can be substituted at
   spawn. Putting those in a committed file is impossible; putting them in
   the projector is free.
9. **Unmanaged vs SASE-launched.** Committed `AGENTS.md` stays the portable
   default. Only SASE spawns get faceted extras and hidden shims.
10. **Effective-load snapshot.** Today's `instruction_snapshot` is an
    inventory of files on disk. After projection it should record
    `provider`, `files_presented`, `files_hidden`, `injected_via`
    (flag / shadow-home / file), hashes, and line/token counts against the
    budget. `sase doctor` can then print "Grok will load 1 file, ~N tokens"
    instead of listing five identical shims.
11. **Per-provider token budget.** Claude cares about adherence past ~200
    lines; Codex hard-caps at 32 KiB; Grok has no cap and will happily eat
    both shims. One global `memory.instructions_budget` is necessary; the
    projector reports the *effective* total per provider.
12. **Skill-description sibling budget.** Out of scope, but the same
    projector/doctor table should eventually include skill preamble tokens
    (~1k today, ~20k harness floor). Called out as a follow-up in the
    budgeted-router report; still true.
13. **`grok inspect` / Claude `/memory` / Codex debug as oracles.** The
    projector's tests should assert against what the CLI reports, not against
    which files SASE wrote. That is how the Grok double-load was documented;
    it is also how we will know Antigravity and Qwen.

## Requirement adjustments

Flagged changes to the original request.

> **A. Name.** Do not call the spec `SASE.md`. Keep committed `AGENTS.md` as
> the portable compiled document. If an on-disk IR is ever needed, put it
> under `sase/` with a name no CLI auto-loads (for example
> `sase/instruction_projection.json`). Prefer no extra file: the compiler
> output plus launch context is enough.

> **B. Split the problems.** Ship load-surface projection first (Grok, Codex
> home, Claude-home trap, likely Antigravity/Qwen). Ship the budgeted router
> as the already-specified renderer epic. Ship faceted content last, against
> a closed facet vocabulary. Do not gate the first two on a new markdown
> spec.

> **C. Identification.** No `%tag` directive. Match `when:` / Jinja against
> `{provider, kind, clan, tribe, alias}` derived from the launch that is
> already parsed. Reuse tribe for user-authored labels.

> **D. Git hygiene.** Never overwrite tracked instruction files with a
> different projection. Untrack provider shims, gitignore them, and
> reconcile untracked shims on each launch. Root `AGENTS.md` stays tracked
> and is the default projection (identical bytes ⇒ clean tree for providers
> that only read `AGENTS.md`).

> **E. Home union is in scope for the projector.** "Codex doesn't read
> `~/AGENTS.md`" is the Codex-shaped instance of a general bug: Grok and
> Antigravity also miss `~/AGENTS.md`. The projector injects home content
> through each CLI's actual global slot.

> **F. Effective load is the object under budget.** `sase memory init --check`
> continues to budget the committed `AGENTS.md` (the portable default).
> Launch-time doctor/snapshot reports the provider-effective total, including
> home and hidden shims. A Grok launch that still presents `CLAUDE.md` fails
> that check.

> **G. Unmanaged CLIs keep working.** `sase tmux-agent` and a git clone
> without SASE still see a complete committed `AGENTS.md`. Faceted extras are
> SASE-spawn-only.

> **H. Measure before hiding Antigravity/Qwen/Muse files.** Grok's double-load
> is documented. The others are vendor-documented and should be confirmed
> with the installed CLI before the projector hides names.

> **I. Glossary and shim invariant.** Updating
> `glossary:agent-instruction-file` is part of the work: "same contents in
> every filename" becomes "one compiled document, projected onto the
> filenames this provider will load exactly once."

## Options considered

| Option | Verdict | Why |
| --- | --- | --- |
| Launch-time projector in provider adapters; committed `AGENTS.md` stays | **Adopt** | Fixes load-surface bugs, fits `adapters-normalize-harnesses`, keeps portability. |
| Untrack + gitignore provider shims; reconcile per launch | **Adopt** | Only way to hide `CLAUDE.md` from Grok without skip-worktree fragility. Claude still gets a gitignored `CLAUDE.md` because of the home-trap. |
| Closed facet vocabulary (`when:` / Jinja) for audience-specific body | **Adopt, later** | Unlocks research-vs-coder content using data we already have. |
| Shadow `GROK_HOME` analogous to Codex shadow home, for global rules | **Adopt as a Grok home slot** | Grok never reads `~/AGENTS.md`; `~/.grok/` is the real global. |
| `claudeMdExcludes` for `~/CLAUDE.md` after merging home into the project file | **Optional, later** | Removes the duplicated `sase.md` contract Claude currently pays twice (~45 of 74 home lines). Keep home readable until the union is proven. |
| Root `SASE.md` as the human-edited spec | **Reject** | Name collision, not a vendor filename, duplicates the memory compiler. |
| New `%tag` directive | **Reject** | Retired name; unstructured; launch context already identifies audiences. |
| `@AGENTS.md` one-line shims | **Reject** | Already abandoned; Codex does not expand; Claude ancestor-import bugs. |
| Overwrite tracked files in the workspace, restore on exit | **Reject** | Racey, visible to `git status` mid-turn, fights the finalizer. |
| Inject *all* instructions via CLI flags and leave the tree empty | **Reject as the only path** | Unmanaged CLIs and nested path-scoped files still need files. Use flags for *extras* (single-turn, faceted addenda, Grok `--rules`). |
| Move contract text exclusively into skills | **Reject** | Skills under-trigger (Vercel: 56% never invoked); hard rules must stay always-loaded. |
| Put the projector in `sase-core` | **Reject for v1** | Same reason as the budgeted-router report: `src/sase/amd` and the adapters have no `sase_core_rs` call sites. Revisit if another frontend needs the same projection. |

## Recommended solution

**Phase 1 — Instruction projector (load-surface only).**

New module, e.g. `src/sase/amd/project.py`, called from each adapter just
before spawn, with a `LaunchInstructionContext` (`provider`, `workspace`,
`home_doc`, `project_docs`, `kind`, …).

Per provider, v1 policy:

| Provider | Present | Hide | Inject |
| --- | --- | --- | --- |
| Claude | gitignored project `CLAUDE.md` = compiled project doc (home trap) | nothing required; project `AGENTS.md` is ignored once `CLAUDE.md` exists | existing `--append-system-prompt` |
| Grok | tracked `AGENTS.md` only | delete/ignore leftover `CLAUDE.md` / `GEMINI.md` / `QWEN.md` / `OPENCODE.md` in the workspace | home doc via `--rules` or a disposable `$GROK_HOME` rules file |
| Codex | tracked `AGENTS.md` | leftover shims irrelevant | always write compiled home doc to shadow `$CODEX_HOME/AGENTS.md` (today's fallback, made mandatory for SASE launches so a native `~/.codex/AGENTS.md` cannot silently drop home SASE memory — merge or prefix, don't replace a user's native file without a knob) |
| OpenCode | `AGENTS.md` | leftover `CLAUDE.md` optional | global file only if we need home union |
| Antigravity | `AGENTS.md` | `GEMINI.md` once measured | `~/.gemini/` only if we need home union |
| Qwen | `AGENTS.md` | `QWEN.md` once measured | `~/.qwen/` analog |
| Muse | measure first | — | existing prompt-file prefix |

Reconcile is mandatory on workspace reuse. Tests spy on `grok inspect` /
Claude `/memory` fixtures, not only on which paths were written.

Extend `instruction_snapshot` with `presented` / `hidden` / `injected`
hashes. `sase doctor -C llm.instructions` prints the effective load.

Stop generating committed shims in `sase memory init` once the projector
lands; keep a one-release migration that deletes tracked shims. Nested
directory shims follow the same rule.

**Phase 2 — Budgeted router (already specified).**

Do the 2026-10-02 renderer work against committed `AGENTS.md`: roster
densities, short `memory-sase.template.md`, one-line triggers, ratchet in
`sase memory init --check`. Independent of the projector. Do not wait for
facets.

**Phase 3 — Faceted body text.**

Add optional `when:` on flat notes and Jinja `launch.*` in the existing
templates. Default is all audiences. `sase memory init` can still render the
**unfaceted** portable `AGENTS.md` (every `when:` included, or only
`when`-less notes — pick one and document it; I recommend portable
`AGENTS.md` includes only unfaceted content, and faceted notes render only at
launch). That keeps unmanaged CLIs on the shared contract and gives research
swarms their isolation paragraph without paying it on every coder turn.

Hard rules listed in the budgeted-router report stay unfaceted.

**Phase 4 — Optional IR.**

Only if facet authoring in scattered notes becomes painful. A structured file
under `sase/`, generated, never vendor-loaded. Still not named `SASE.md`.

### What success looks like

- A Grok SASE spawn loads one copy of the project router plus home content,
  confirmed by `grok inspect`.
- A Codex SASE spawn loads project `AGENTS.md` and the SASE home doc via
  `$CODEX_HOME`, even when `~/.codex/AGENTS.md` exists (merged, not dropped).
- A Claude SASE spawn still sees project instructions despite `~/CLAUDE.md`.
- `git status` in the workspace is clean of instruction-file noise.
- `sase tmux-agent` in the same repo still has a complete `AGENTS.md`.
- Faceted notes can target `kind: research` without a new directive.

### What would change my mind

- If Claude dropped ancestor-walk past git root, project `CLAUDE.md` might
  become unnecessary and AGENTS.md-only would suffice for Claude SASE
  agents. Measure on each Claude upgrade.
- If Grok shipped a working `compat.claude.agents = false` or a
  `--no-claude-md` flag, hiding `CLAUDE.md` on disk would be unnecessary for
  Grok. As of the current SASE docs, the compat flag does not do this.
- If a future CLI auto-loads `SASE.md`, that name becomes even worse.

## Appendix: current compiler vs proposed projector

```
TODAY
  notes ──► sase memory init ──► AGENTS.md ──► copy to 4 shims ──► git
                                                    │
                                                    ▼
                                              clone to workspace
                                                    │
                                                    ▼
                                         CLI concatenates whatever
                                         filenames it likes
                                         (Grok: both; Codex: no home;
                                          Claude: home+project CLAUDE.md)

PROPOSED
  notes ──► sase memory init ──► AGENTS.md (committed, budgeted)
                                    │
                     launch context ┤
                                    ▼
                         projector (adapter)
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              files on disk   shadow home      CLI flags
              (reconciled)    (Codex/Grok)     (--rules, …)
                    │               │               │
                    └───────────────┴───────────────┘
                                    ▼
                         one effective load
                         recorded in snapshot
```
