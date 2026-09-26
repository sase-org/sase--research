---
create_time: 2026-09-26
updated_time: 2026-09-26
status: research
---

# Robust file-hook matching for artifact files: env-var-via-`#research` proposal, critique, and recommendation

**Research question:** make it easier to set file hooks for artifact files with a more
robust and reliable approach to matching artifact files. The proposed mechanism: have the
`#research` xprompt set an environment variable by default, plus a new input argument to
opt out of setting it, with the opt-out threaded through every pre-lead researcher
segment of the `#research_swarm` swarm.

**Bottom line up front:** do not implement the proposal as stated. An LLM-exported
environment variable is the wrong layer for this signal: it is advisory prompt text, not
an enforced mechanism, and it cannot survive to the moment matching actually happens.
Keep the current path/agent-name matcher, add a command-level draft guard as the cheap
robust backstop, and if a matcher change is later justified, add a server-side filter
dimension (file content or control-plane agent identity) — never a self-asserted env
var. Details and a staged plan are at the end.

## 1. How file-hook matching works today (primary sources)

All claims below were verified against the sase checkout at
`/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21` and the
`sase-research-artifacts` linked checkout opened via `sase repo open`.

### 1.1 The matcher

`src/sase/config/file_hooks.py` defines the full filter model. One hook carries
`FileHookFilters` with seven optional dimensions: `projects`, `sidecars`,
`path_globs`, `agent_name_globs`, `ops`, `causes`, `producers`. `hook_matches_event`
ANDs every configured dimension; an omitted dimension matches everything. Two
semantics matter for this proposal:

- `causes`: `event.cause != "user"` requires the cause to be explicitly listed in
  `filters.causes`. `"user"` is the default cause and always passes the cause check.
- `agent_name_globs`: an unattributed event (agent name `None`) is matched as the
  empty string, so it clears a negative-only list but never a list containing a
  positive pattern. In other words, negative-only agent globs fail open on missing
  attribution.

Glob matching uses `wcmatch` with `DOTGLOB | GLOBSTAR | NEGATE | NEGATEALL`, so
`!`-prefixed entries are exclusions.

### 1.2 The research-highlights hook spec

`src/sase_research_artifacts/provider.py` in the
`sase-research-artifacts` plugin defines `RESEARCH_HIGHLIGHTS_HOOK_SPEC` with:

- `sidecars: ["research"]`, `producers: ["commit", "sdd", "finalizer"]`,
  `ops: ["ADD"]`, `timeout: "120s"`.
- `path_globs` excluding month-root drafts (`!20*/*__*.md`), moved drafts
  (`!20*/*/*__*.md`), and infographic/media companions.
- `agent_name_globs` excluding `!research.*.<suffix>` for all five swarm
  researcher suffixes (`cdx`, `cld`, `grk`, `mus`, `gem`), generated from the
  single `_SWARM_RESEARCHER_SUFFIXES` tuple — one source of truth inside that
  file, which is good.

The module docstring is explicit that the ref-provider inventory and the hook
spec intentionally diverge: the `research` ref provider keeps `__<suffix>`
drafts citable via `@research:...`, while the hook excludes them from PDF
generation. The current design is therefore already defense-in-depth: path
shape **and** agent name must both agree a file is a consolidated report
before a Highlights PDF is rendered.

### 1.3 Where matching actually runs (the lifecycle point)

This is the decisive fact for the proposal. Matching does not run when the
researcher agent writes the file. It runs in producers, detached from the
researcher's process:

- `src/sase/artifact_cli/create.py`: `sase artifact create` captures the source
  event pre-copy and dispatches post-copy with `producer="artifact"` and
  hardcoded `cause="user"`. Note the research-highlights hook does **not** list
  the `artifact` producer, so `#research`'s registration step itself never
  triggers Highlights — the hook fires on a later commit/sync/finalizer pass.
- `src/sase/workflows/commit/workflow.py` (`_run_file_hooks`) and
  `src/sase/sdd/_commit_store.py` (`_emit_sdd_file_hooks`): commit-time
  producers with `producer="commit"` / `"sdd"`, `cause="user"` by default.
- `src/sase/file_hooks/producer.py` (`reconcile_commit_file_hooks`):
  `producer="finalizer"`.
- `src/sase/file_hooks/runner.py` executes the hook command detached with
  `env=os.environ.copy()` — the hook *command* sees the environment, but the
  *matcher* (`dispatch.py: _batch_payload` → `match_events`) only consults the
  seven filter dimensions. No producer reads an arbitrary env var into the
  event.

Attribution at match time comes from `resolve_local_agent_name()`
(`SASE_AGENT_NAME` / `agent_meta.json`) and `classify_repository()`. So by the
time a research report is matched, the acting process is typically the lead
agent (which moved the drafts into `<name>/`), an auto-sync, or a human — not
the researcher that wrote the draft. Any signal stored only in the
researcher's process environment is long gone.

### 1.4 What xprompts can and cannot do with environment

`#research` (`xprompts/research.md`) and `#research_swarm`
(`xprompts/research_swarm.md`) are Jinja prompt templates with typed `input:`
frontmatter (`path`, `word`, `text`, `bool`, `int`). Prompt directives
(`src/sase/xprompt/_directive_types.py`) are a closed set: `auto, clan,
effort, final, hide, hold, model, id, dispatch, repeat, queue, wait, if,
proc` — there is no `%env` / `%setenv` directive. `environment:` blocks exist
only for workflow definitions (`src/sase/xprompt/workflow_models.py`), not for
prompt xprompts. So "the `#research` xprompt sets an environment variable" can
only mean prompt *prose instructing the LLM* to run something like
`export SASE_...=...` in its shell — advisory text obeyed (or not)
independently by five different provider harnesses (codex, claude, grok, muse,
gemini), with no verification that the export happened, persisted across tool
calls, or was in effect when any matching-relevant command ran.

## 2. Critique of the proposal

### 2.1 Prompt text is not a mechanism

An instruction to export a variable is followed at the LLM's discretion, in a
subshell the launcher does not control, under harnesses that may not propagate
shell exports to subsequent `sase` invocations (several providers execute tool
calls without a persistent shell session). There is no acknowledgement, no
audit, and no retry. A matching signal with a silent failure mode ("agent
forgot to export") is less reliable than the current suffix convention, which
at least leaves durable, inspectable evidence in the filename.

### 2.2 Fatal lifecycle mismatch: process-scoped signal vs. repo-scoped event

Even a perfectly exported variable cannot work, because of §1.3. The events
the hook matches are produced by *later* commits/syncs/finalizers, usually in
*different processes under different identities*. Environment variables do not
cross that boundary. To make the variable matter, every producer capture path
(`file_hooks/artifact.py`, `file_hooks/commit.py`, `_commit_store.py`) would
need new code mapping the variable into the event (e.g. into `cause` or a new
field), plus tests — at which point the env var is just an unreliable transport
for a value that should have been first-class from the start.

### 2.3 Agent-controlled suppression is a trust problem

Hook matching should depend on server-side-observable facts (file paths, commit
cause passed by trusted code, agent identity from the control plane), not on a
value the matched agent asserts about itself. Under the proposal, any agent —
including a compromised, confused, or merely buggy one — can suppress hook
execution by exporting the variable, or trigger spurious runs by unsetting it.
The current filename/agent-name signal has the same self-assertion flavor, but
it is at least durable and auditable after the fact; env vars leave no trace.

### 2.4 Wrong default polarity and real API churn

"Set by default, opt out for pre-lead researchers" inverts the natural shape:
drafts are the exception (a handful of swarm segments), consolidated reports
are the rule (every direct `#research` caller). A default-on behavior changes
every existing direct `#research` invocation, and the opt-out must be threaded
through five researcher segments in `research_swarm.md`'s Jinja
(`#research(suffix=cdx)` → `#research(suffix=cdx, <new_flag>=...)` × 5),
plus the `research.md` frontmatter, plus docs (`docs/xprompts.md`), plus the
plugin's `test_frontmatter.py`-style contract tests. That is a large,
cross-repo surface for a signal that §§2.1–2.3 show cannot do the job.

### 2.5 The problem it solves is smaller than it looks

The current spec already excludes both pre-move (`20*/*__*.md`) and post-move
(`20*/*/*__*.md`) draft shapes plus companions, and all five researcher agent
names. The residual gaps are narrow and should be named explicitly rather than
re-architected around:

1. The stem is agent-chosen (mitigated: no-overwrite creation rule forces a new
   stem on collision; lead normalizes layout afterward).
2. `agent_name_globs` only help when the researcher itself is the committing
   identity; after the lead moves drafts, attribution names the lead — but the
   post-move path glob already covers that case. The two dimensions genuinely
   back each other up.
3. A sixth researcher suffix would need the plugin's tuple updated — a one-line
   change in one file, and swarm segments are generated from the same template
   family. This is maintenance, not fragility.

## 3. Alternatives considered

- **A. Positive-path matching** (match only the consolidated shape instead of
  excluding draft shapes): strictly more robust in theory, but `wcmatch` globs
  cannot express "basename equals parent directory name" (`<name>/<name>.md`),
  so this needs engine support (a new filter predicate). Not worth it alone.
- **B. Trusted `cause` marking**: have trusted code (not the agent) stamp
  research-draft commits with a dedicated cause, mirroring the existing
  `ARTIFACT_LINK_FILE_HOOK_CAUSE = "artifact_links"` precedent in
  `src/sase/sdd/_artifact_link_commit.py`. Clean semantics (`causes` is already
  a filter dimension), but researchers don't commit — the lead/sync does — so
  the stamper would have to infer draft-ness from paths anyway, adding nothing
  over the path globs. Rejected as indirection without gain.
- **C. Content-based filter (frontmatter)**: match on something that travels
  *with the file* across moves, commits, and actors — e.g. a `status: draft`
  vs `status: final` frontmatter convention, enforced by the `#research`
  template. This is the only option that is robust in the same sense the
  request asks for. Costs: a new engine filter dimension that reads file
  content at match time, plus a frontmatter convention change. Note the
  skew found during this research: the ref-provider spec declares
  `status ∈ {draft, review, final, archived}` from frontmatter, yet real
  reports in `202609/` carry `status: research`. Convention and spec must be
  reconciled before content-based matching can build on `status`. Viable as a
  follow-up, not a first step.
- **D. Command-level draft guard** (recommend as the immediate step): make the
  Highlights command itself re-check draft-ness (suffix `__<suffix>.md`,
  companions, `__critique.md`) and exit 0 without rendering. A backstop behind
  the matcher covers every present and future matcher gap; the failure it
  converts (spurious PDF in the reading queue) is the expensive direction,
  while its own failure mode (skipped PDF) is cheap and re-runnable. Small,
  local to the plugin repo, easily tested.
- **E. Structural enforcement in the swarm**: have `#research_swarm` pre-assign
  the draft location (e.g. researchers write straight into `<month>/<clan>/`
  staging, lead renames into place) so path globs match directory structure
  rather than agent obedience to the suffix rule. Shrinks the largest
  agent-obedience surface without any engine change. Compatible with D.
- **F. Launcher-set identity, if env-like signaling is insisted on**: the
  robust version of the proposal's instinct is not an LLM export but a
  control-plane attribute — resolve `agent_name → clan/role` server-side at
  match time (new filter dimension such as `agent_clan`), set by the launcher
  that created the agent, unforgeable by the agent itself. Only worth building
  if D+E prove insufficient.

## 4. Adjustments to the requirements (called out)

1. **Drop the environment variable entirely** — both the default-set and the
   opt-out input argument. It adds cross-repo API surface for a signal that
   cannot reach the matcher (§§2.1–2.2) and that agents could forge (§2.3).
2. **Do not thread any new flag through `#research_swarm`'s researcher
   segments.** No requirement should touch those five segments unless it
   changes what the researchers write, not what their shells export.
3. **Restate the goal as defense-in-depth**: matcher exclusions (keep) +
   command-level guard (add) + optional structural staging (consider) — rather
   than "one robust matcher signal".
4. **Reconcile the `status` frontmatter skew** (spec says
   draft/review/final/archived; practice says `research`) before any
   content-based matching is designed; either is defensible, the
   contradiction is not.

## 5. Recommended solution (staged)

1. **Now, in `sase-research-artifacts` (small, no sase-core change):** add the
   command-level draft guard (alternative D): the research-highlights command
   re-validates each input path against the draft/companion shapes already
   enumerated in `RESEARCH_HIGHLIGHTS_HOOK_SPEC` and no-ops with a logged
   reason. Add unit tests mirroring the spec's glob lists so spec and guard
   cannot drift silently.
2. **Now, documentation:** record the §2.5 residual gaps and the
   `_SWARM_RESEARCHER_SUFFIXES` single-source-of-truth in the plugin's docs so
   the next "is this fragile?" question starts from evidence.
3. **Next, optionally:** structural staging (alternative E) in
   `research_swarm.md`/`research.md` — researchers write into clan staging,
   lead normalizes. Reassess after steps 1–2: if no spurious PDFs occur over a
   few swarm runs, stop here.
4. **Only if spurious or missed hooks persist:** design a server-side filter
   dimension — frontmatter convention first (fixing the `status` skew), or
   launcher-attributed agent clan/role (alternative F). Explicitly do not
   revisit prompt-text-exported environment variables; any proposal in that
   family must explain how the signal crosses the process boundary of §1.3
   and why the agent must be trusted to assert it (§2.3).

## Sources inspected

- `src/sase/config/file_hooks.py` — filter model, `hook_matches_event`,
  `match_events`, provider-`use` resolution.
- `src/sase/file_hooks/{artifact,commit,context,dispatch,producer,runner,models}.py`
  — capture, attribution, batch matching, detached execution
  (`env=os.environ.copy()` reaches the command, not the matcher).
- `src/sase/artifact_cli/create.py` — `producer="artifact"`, `cause="user"`.
- `src/sase/workflows/commit/workflow.py`, `src/sase/sdd/_commit_store.py`,
  `src/sase/sdd/_artifact_link_commit.py` — commit/sdd producers and the
  `artifact_links` cause precedent.
- `src/sase/agent/identity.py` — `SASE_AGENT_NAME` / `agent_meta.json`
  attribution the matcher actually sees.
- `src/sase/xprompt/_directive_types.py`, `workflow_models.py` — no `%env`
  directive; `environment:` is workflow-only.
- `sase-research-artifacts`: `provider.py` (hook spec + intentional
  inventory/hook divergence), `xprompts/research.md`,
  `xprompts/research_swarm.md`, `docs/xprompts.md`, `default_config.yml`.
- Research sidecar `README.md` layout conventions and `202609/` report
  frontmatter (`status: research` vs the spec's enum).
