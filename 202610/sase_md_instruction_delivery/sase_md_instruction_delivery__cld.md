# One Spec, Delivered Per Invocation: Evaluating a `SASE.md` Source for Agent Instructions

> **Research query:** Migrate all existing agent instruction files to a single `SASE.md`
> that defines a spec for the agent instruction file, used to construct the right
> instruction file dynamically in ephemeral workspaces before SASE launches agents
> there. Motivations: fix the provider-loading bugs from the
> `agent_instructions_budgeted_router` research (Grok reads both `AGENTS.md` and
> `CLAUDE.md`; Codex never reads `~/AGENTS.md`), and render some parts only for some
> agents (perhaps via a new `%tag` directive). Find missed use cases, critique the plan,
> adjust the requirements where justified, and recommend a solution.

_Researcher: cld · 2026-10-05 · sase checkout `8c8c47f720` · provider CLIs installed on
athena: Claude Code 2.1.289, codex-cli 0.160.0, grok 1.0.46, agy 1.2.17, Muse 1.4.2,
qwen 0.25.0, opencode 1.18.34._

## Bottom line

- **Yes, build this. It is the right architecture, and it is more urgent than the query
  assumes.** Today's bugs come from one source: SASE writes static files and then lets
  each provider CLI decide what to read. Provider discovery rules differ, and they change
  without notice. I measured what each provider actually loaded in recent runs
  ([table](#what-each-provider-actually-loads-today)):
  - **Grok has loaded no instruction file at all since about 2026-09-10.** It used to
    load both files. 568 of 568 Grok sessions in SASE workspaces since 2026-09-11
    recorded `agents_md_files: []`; before that, 421 of 429 loaded both `CLAUDE.md` and
    `AGENTS.md`. Grok runs are 13% of all runs. The share of non-research Grok runs that
    submitted a final declaration fell from 60% to 26% over the same window, while
    Claude and Codex each moved 6 points or less. That drop is a correlation, not proof
    of cause.
  - **Codex does read `~/AGENTS.md` when SASE launches it.** The shadow-`CODEX_HOME`
    bridge (`codex.py:207-221`, commit `db5df9ee50`, 2026-05-31) supplies it. Rollouts
    from 2026-10-02 show the home file followed by `--- project-doc ---`. So that part
    of the premise is outdated, as is the prior report's claim that "Codex never sees the
    home file."
  - **The real bug is the reverse: Claude and Codex both load the shared SASE contract
    twice.** 10 of the 12 paragraphs in the home file appear word for word in the
    project file: 42 lines, about 790 tokens, on every call. The two copies also give
    different "linked repositories" lists. Claude and Codex together are 56% of runs.
  - **Muse loads the project file once but never sees the home layer.** That means no
    tailnet, Obsidian, or chezmoi knowledge. Muse is 29% of runs.
  - **The docs show dead and doubled copies.** OpenCode never reads `OPENCODE.md`. Qwen
    reads both `QWEN.md` and `AGENTS.md`.
- **[Four changes](#requirement-adjustments) to the plan as stated:**
  1. **Deliver the instructions; don't write them into the workspace.** Each provider
     adapter should inject one per-invocation render through an explicit channel:
     Claude `--append-system-prompt-file`, Grok `--rules`, the Codex shadow-home
     `AGENTS.md`, or a prompt prefix. Writing files into ephemeral workspaces breaks in
     [seven ways](#why-not-write-the-file-into-the-workspace). One of them alone is
     fatal: Grok skips gitignored instruction files and currently skips untrusted
     workspaces entirely.
  2. **`SASE.md` should be the composition spec, not the content store.** It holds the
     layout and conditions. Memory notes stay the content and gain a `when:` frontmatter
     key. A single monolithic file would undo the core/reference/web architecture and
     its audited reads.
  3. **Don't add `%tag` first.** Almost every real conditional section can be keyed on
     launch facts SASE already knows: provider, session role, phase worker, tribe,
     macros used, commit method, VCS, host, and mode. `%tag` already existed once (it
     became groups, then tribes), and legacy `tag` metadata is still read as a tribe
     today. Free-form labels, if ever needed, should be **macro-declared `traits`**.
     That follows the project's own
     [`corpus-before-mechanism`](#audience-targeting-is-tag-the-right-primitive) rule.
  4. **Make "exactly once, on every provider" a tested invariant.** Run a conformance
     check against provider transcripts in `sase doctor` and CI. The Grok regression
     went unnoticed for about four weeks; a check like this would have caught it on day
     one.
- **[Missed use cases](#high-value-use-cases-you-may-have-missed)**, highest value
  first:
  - Fold the four hand-written, provider-specific single-turn directives (now hidden in
    adapter Python) into the reviewable spec.
  - Give lean renders to monitor and gate turns, which are 12.5% of runs.
  - Make accurate per-invocation provenance replace today's `instruction_snapshot`,
    which records files the provider may never have read.
  - Use rules that depend on role and commit method, such as the phase-worker bead rule.
  - Add home layers that depend on the host, retiring the chezmoi hostname-template
    hack.
  - Let plugins contribute their own sections.
  - In foreign repos, deliver the SASE contract without touching upstream files.
  - Run A/B tests of instruction variants, measured with the existing audit logs.
- **[Recommendation](#recommended-solution):**
  - **Phase 0** (now, small): a Grok `--rules` stopgap, drop the dead and doubling
    copies, and add the conformance check.
  - **Phase 1:** a per-invocation **instruction bundle** renderer plus adapter delivery,
    behind a flag for each provider.
  - **Phase 2:** stop committing generated instruction files; turn nested files into
    path-scoped notes; make the home layer a layer.
  - **Phase 3:** `when:` audiences with per-audience budget checks.
  - **Phase 4:** `traits` only once a real section needs one.

## Scope and method

- **Code read:**
  - the instruction generator (`src/sase/amd/`, `src/sase/main/init_memory/`);
  - every provider adapter (`src/sase/llm_provider/`);
  - the runner and workspace lifecycle (`src/sase/axe/`);
  - the finalizer dirty-state logic;
  - the directive parser (`src/sase/macro/_directive_*.py`).
- **Ground truth on what the model actually saw** came from each provider's own session
  record:
  - Codex rollouts (`~/.codex/sessions/`);
  - Grok `prompt_context.json` (`agents_md_files`, 1,051 sessions);
  - Muse `session.jsonl`;
  - for Claude, the instruction blocks injected into this very session (both
    `/home/bryan/CLAUDE.md` and the workspace `CLAUDE.md` are present).
- **Usage and behavior** came from SASE's own records:
  - `agent_meta.json` for 7,007 sase-project runs over 30 days;
  - finalizer artifacts for the declaration rates;
  - git history.
- **Provider documentation** was checked against official docs (URLs inline) and against
  `--help` from the installed CLIs. Claims I could not verify are labeled as such.
- **Prior work:** `research:202610/agent_instructions_budgeted_router/agent_instructions_budgeted_router.md`
  (read via `sase artifact read`). This report builds on its "budgeted router"
  conclusions and does not repeat them.

## What exists today

### The pipeline

`sase memory init` renders one root `AGENTS.md` from `src/sase/amd/templates/AGENTS.template.md`:

- title;
- core notes, including the generated `sase/memory/sase.md` contract from
  `memory-sase.template.md`;
- reference triggers;
- the web section.

It then writes `CLAUDE.md`, `GEMINI.md`, `QWEN.md`, and `OPENCODE.md` as **byte-identical
copies** (`PROVIDER_SHIM_FILES`, `src/sase/amd/constants.py:13`).

It runs a second time for the home root (`~/` via chezmoi). Per-machine H1 titles are
handled there by generating `AGENTS.md.tmpl` with a `{{ if eq .chezmoi.hostname … }}`
switch (`_chezmoi_template.py`).

The three nested `AGENTS.md` files (`tools/`, `src/sase/ace/`, `demos/tapes/`) are
written by hand, and each one also gets four copies.

| Fact | Value |
| --- | --- |
| Tracked instruction files in `sase` | **20** (5 names × 4 directories) |
| Commits touching root `AGENTS.md` | 261 all-time; **111 in the last 60 days** (of 3,931) |
| `chore: run sase init memory` commits, 60 days | 26 |
| Per-provider content variation | **None.** Only the H1 switches by host (chezmoi). |
| Provider-specific instruction text that exists anyway | **4 hand-maintained single-turn directives in adapter code** (`claude.py:50`, `codex.py:57`, `agy.py:71`, `_muse_directive.py`), invisible to memory review |
| Drift check | `sase memory init --check` via `just validate`. CI runs `sase init memory --no-commit` in the checkout *before* `just validate` (`ci.yml:55-58`), which probably regenerates the files and masks drift. **Unverified**: I did not run CI. |

### What each provider actually loads today

These are SASE-launched runs in the `sase` project. Run share is from 7,007 runs in the
last 30 days.

| Provider | Share | Home layer | Project file | Nested files | Evidence |
| --- | ---: | --- | --- | --- | --- |
| Codex | 31% | ✅ via SASE's shadow-home symlink | ✅ | ❌ (cwd is the repo root; Codex reads only root→cwd) | Rollout `2026-10-02T15-40`: `# AGENTS.md instructions for …` → `# athena - Bryan Bugyi's Home Server` → `--- project-doc ---` |
| Muse | 29% | ❌ | ✅ once | unknown | 8 of 8 sessions on 2026-10-05: project H1 ×1, home ×0 |
| Claude | 25% | ✅ `~/CLAUDE.md` as an ancestor | ✅ | ✅ lazy | Both files appear in this session's injected context |
| Grok | 13% | ❌ | **❌ since about 2026-09-10** (before that, ×2: `CLAUDE.md` + `AGENTS.md`) | ❌ | `prompt_context.json` `agents_md_files`: 421/429 had 2 files through 09-10; 568/568 had 0 from 09-11 to 10-05 |
| agy | 0.9% | ❌ | docs: `AGENTS.md` and/or `GEMINI.md` | lazy | Not verified; [Antigravity rules](https://antigravity.google/docs/rules) |
| OpenCode | ~0 | ❌ | `AGENTS.md` only; **`OPENCODE.md` is never read** | — | [opencode.ai/docs/rules](https://opencode.ai/docs/rules) |
| Qwen | 0 runs | ❌ | **`QWEN.md` and `AGENTS.md` both** (×2) | — | [Qwen memory docs](https://qwenlm.github.io/qwen-code-docs/en/users/features/memory/) |

**Grok detail.** `grok inspect` in a workspace prints `Project trusted: no` and
`Project Instructions (0)`. `~/.grok/trusted_folders.toml` lists only the primary
checkout. Sessions outside workspaces kept loading two files until 2026-09-13.

My best explanation is a Grok-side trust gate shipped around 09-10. xAI's docs don't
document one ([project rules](https://docs.x.ai/build/features/project-rules)), so the
cause is **unconfirmed**. The effect is certain. Note also that Grok's documented rules
say "Files ignored by `.gitignore` are skipped".

**Behavioral signal.** For completed non-research runs with finalizers (monitor and gate
turns excluded, last 60 days, split at 2026-09-11), the share that submitted a final
declaration was:

| Provider | Before | After |
| --- | --- | --- |
| Grok | 60% (62/104) | **26% (43/163)** |
| Claude | 55% | 49% |
| Codex | 64% | 58% |

Grok's use of `sase final context` barely moved (62% → 56%). One reading: skill
descriptions still lead Grok to `/sase_final`, but without the contract it more often
fails to submit. This is a correlation; model updates in the same window could
contribute.

**Home and project duplication.** The home file is 74 lines and about 965 tokens. 10 of
its 12 body paragraphs (42 lines, about 793 tokens) appear verbatim in the project file:
the memory explainer, the cross-repo rule, the artifact rule, and the final declaration.

Under "Configured linked and sidecar repositories associated with this project", Claude
and Codex agents are told the linked repo is `chezmoi` in one block and six `sase-*`
repos in the other.

### Provider facts that constrain the design

All verified in official docs except where marked.

- **Claude Code** ([memory](https://code.claude.com/docs/en/memory), [settings](https://code.claude.com/docs/en/settings-reference), [CLI](https://code.claude.com/docs/en/cli-reference)):
  - Loads `CLAUDE.md` from cwd **and every ancestor**, and lazily loads nested files.
  - Delivers that content "as a user message after the system prompt".
  - **Reads `AGENTS.md` natively since v2.1.277**, but in the default mode only if no
    `CLAUDE.md` exists in cwd *or any ancestor*. `~/CLAUDE.md` is an ancestor of every
    workspace, so it disables this on athena.
  - `claudeMdExcludes` (absolute paths or globs) is valid in a `--settings` JSON.
  - `--append-system-prompt-file` exists and can combine with `--append-system-prompt`.
- **Codex** ([AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)):
  - Reads a global `$CODEX_HOME/AGENTS.override.md` or `AGENTS.md`, then the files from
    the project root down to cwd.
  - Nothing above the git root and nothing below cwd.
  - `project_doc_max_bytes` defaults to **32 KiB**; content past the limit is silently
    truncated. Today's home plus project total is about 21 KiB.
- **Grok** ([project rules](https://docs.x.ai/build/features/project-rules), [settings](https://docs.x.ai/build/settings/reference)):
  - Reads `AGENTS.md`, `CLAUDE.md`, and related names in each directory, with no size
    cap, and skips gitignored files.
  - `--rules <TEXT>` appends to the system prompt.
  - `GROK_CLAUDE_AGENTS_ENABLED=0` stops it scanning `CLAUDE.md`.
- **Antigravity:**
  - Reads `AGENTS.md` or `GEMINI.md` per directory.
  - Limits: 24,000 bytes per file, 20k-token aggregate.
  - No documented system-prompt flag.
- **AGENTS.md standard** ([agents.md](https://agents.md/)): has **no** mechanism for
  conditional or agent-specific sections. SASE would be designing this itself.

## Critique of the plan

### What the plan gets right

1. **It finds the right faulty layer.** The content (memory notes) is healthy. What
   breaks is the *projection*: static copies that each provider CLI interprets
   differently. A single source rendered at launch is the only structure that removes
   the home/project duplication for every provider at once. A static home file cannot
   know whether a project file will also load.
2. **Audience targeting is real demand, and it already exists in hiding.** SASE already
   ships agent-specific instructions:
   - four provider-specific directives in adapter code;
   - per-provider Jinja in skills (`sase_questions.md`:
     `{% if provider_native_ask_tool == … %}`);
   - prose exceptions in the shared file, e.g. "Unless your prompt explicitly forbids
     creating beads (epic phase workers, for example…)".

   Those are conditional sections written as prose. Making them explicit makes them
   reviewable and lets them be budgeted.
3. **It fits decided architecture.** `decisions:adapters-normalize-harnesses` says each
   adapter makes its CLI conform to SASE's contract and that the host never models a
   harness's private semantics. Instruction delivery is exactly such a harness
   difference. The prior router report deferred "move contract text into
   adapter-injected system prompts" because that text would be "invisible to memory
   review". A spec rendered from memory and delivered by adapters removes that
   objection.

### Where I would change it

#### Why not write the file into the workspace

The query says to construct the file "dynamically in ephemeral workspaces". The code
and the provider docs show seven problems with that:

1. **The files are tracked, so per-launch writes become commits.** The finalizer
   baseline is captured at bootstrap (`run_agent_runner_bootstrap.py:326`), before
   workspace prep. Staging is `git add -A`. A rewritten `AGENTS.md` would show up as
   `changed_since_run_start`, and the default is to commit it. They would have to be
   untracked first.
2. **Once untracked and gitignored, Grok skips them** (documented). Grok also currently
   skips untrusted workspaces entirely (observed).
3. **Ignored files survive workspace reuse.** Prep stashes only non-ignored files
   (`git stash push --include-untracked`). A launch path that forgets to regenerate
   leaves the previous agent's instructions in place. Finalizer follow-up turns
   (`declaration_recovery.py:83`, `commit_repair_conflict.py:409`) call
   `provider.invoke` directly.
4. **Ancestor files still load.** Claude still reads `~/CLAUDE.md` above every workspace,
   so the duplication survives unless the home file is handled anyway.
5. **Timing is fragile.** For `#gh` launches, the `sase_github` `prepare` step stashes
   non-ignored files after the runner's own prep. The only safe write point is
   `_invoke.py:405-436`, the last code before `provider.invoke`.
6. **The agent can edit its own instructions,** and so can a malicious upstream repo in
   foreign-repo work. A host-side render delivered over a system-prompt channel is
   tamper-proof and takes precedence over repo-supplied text.
7. **The execution provider is only final at invoke time.** Routing and fallback
   (`A || B`) can change it (`execution_provider_label != requested_provider_label`,
   `_invoke.py:416`). A workspace file written "before launch" can target the wrong
   provider.

Every provider has an explicit channel, and five of seven have a first-class one
([delivery table](#delivery-per-provider)). Writing files remains a reasonable
*fallback* channel for a future provider that has nothing else.

#### "A single `SASE.md` file"

If `SASE.md` holds the instruction *text*, it becomes the 283-line encyclopedia the
router research just argued against, in a new place. It would also bypass what works
today:

- per-note `type: core|reference`;
- audited `sase memory read`, which drove 437 runs per month to `lint_and_test.md`;
- web strands;
- `[[links]]`;
- `/sase_memory_write` routing.

The useful single file is the **composition spec**: layout, layer order, budgets, and
conditions. It replaces `AGENTS.template.md`, `memory-sase.template.md`, and the
`memory.agents_template` config. The content stays in notes. Most projects would never
need a `SASE.md` at all, because the packaged default spec covers them.

The name also collides with `sase/memory/sase.md`, the generated contract note. That
note should be retired: its text moves into the packaged base spec, which is SASE-owned
and versioned with `sase`, not with each project.

#### "Migrate all existing agent instruction files"

There are more instruction sources than the root file. A complete migration covers:

| Source | Today | Migrates to |
| --- | --- | --- |
| Root `AGENTS.md` and 4 copies | generated, committed | per-invocation bundle (project layer) |
| `~/AGENTS.md` and 4 copies, plus chezmoi `.tmpl` | generated, committed to chezmoi | home layer, conditional on host |
| `tools/`, `src/sase/ace/`, `demos/tapes/` `AGENTS.md` (+12 copies) | hand-written | path-scoped reference notes (`paths: [tools/**]`) shown as one-line triggers. Today only Claude ever sees them (Codex, Grok, and Muse run at the repo root). `tools/AGENTS.md` also duplicates `symvision.md`. |
| 4 single-turn directives in adapter code | Python string constants | package-layer sections with `when: {provider: …}`; facts like `{{ provider.sync_ceiling }}` are filled in from adapter data |
| Rollover-macro "no direct commit" text | injected by `#commit`/`#pr`/`#propose` bodies | sections conditional on `commit_method` (optional, later) |

#### What's missing from the plan

- **Verification.** The Grok regression shows that provider discovery changes silently.
  Without a conformance check, the new design will drift the same way.
- **Humans and external tools.** `docs/agent_providers.md` keeps `CLAUDE.md` precisely
  so "any human running `claude` in the same tree" still works. `sase-org/sase` is a
  **public** repo. Both need an explicit answer
  ([below](#humans-home-files-and-the-public-repo)).
- **Rendering per invocation, not per launch,** for the provider-fallback reason above.

## Requirement adjustments

_Each of these changes the requirements as stated._

> **A. Deliver, don't write.** SASE runs get instructions **only** through the adapter's
> explicit channel. Natively discovered files carry no SASE-owned content in SASE runs.
> Repo-owned files, such as an upstream `AGENTS.md` in a foreign repo, still load
> natively and are not duplicated.

> **B. `SASE.md` is a composition spec.** It is optional, layered over a packaged
> default, and contains layout plus conditions. Memory notes remain the content and gain
> `when:`. `sase/memory/sase.md` is retired into the packaged base.

> **C. Render per provider invocation,** at the `_invoke.py` hook. That includes
> finalizer follow-up turns and fallback re-invocations.

> **D. Audiences come from launch facts first.** No `%tag` in v1. Free-form labels are
> deferred until a section needs one. When they arrive they are macro-declared
> **traits**, with a `%trait` directive only as an escape hatch. Never reuse the word
> "tag".

> **E. Exactly-once delivery is an enforced invariant.** A conformance check reads each
> provider's own transcript and asserts that the bundle hash appears exactly once and no
> SASE-owned file loaded natively. It runs in `sase doctor` and in a scheduled smoke
> job. This is the deliverable, the way the budget ratchet was in the router research.

> **F. Budgets apply per audience.** The router research's ≤100-line / ≤1,600-token
> ratchet applies to each rendered audience in a matrix, not to one file.

> **G. Keep a human projection.** `sase instructions sync` writes *gitignored* local files
> for interactive sessions, using `mode: interactive`. The public repo may keep a tiny
> committed stub. Nothing generated is committed.

> **H. Fix Grok now,** independently of the redesign (Phase 0).

## Design

### Layers

The bundle is composed in a fixed order and deduplicated by section id. A rule stated in
the package layer is never repeated by a later layer, which removes the home/project
duplication by construction.

| # | Layer | Source | Owner |
| ---: | --- | --- | --- |
| 1 | **Package** | the runtime contract: final declaration, `/sase_repo`, memory routing, single-turn rules per provider | `sase` (versioned) |
| 2 | **Plugins** | hook-contributed sections, e.g. `sase-github` VCS rules when `vcs: github`, research-artifact rules for research agents | plugin |
| 3 | **Home** | home memory (tailnet, Obsidian, chezmoi), with sections conditional on `host`; spec at `~/.config/sase/SASE.md` | user (chezmoi) |
| 4 | **Project** | project memory notes, plus an optional project `SASE.md` layout | project repo |
| 5 | **Launch** | optional live facts (bead and epic context, selected finalizers), placed last for cache friendliness | runtime |
| — | **Repo-owned** | an upstream `AGENTS.md` or `CLAUDE.md` in foreign repos | upstream; loaded natively, never copied |

### The spec format

`SASE.md` is Markdown plus Jinja, because Jinja is already the engine: `mdtemplates.py`
uses `StrictUndefined`, and skills already render per provider. Template inheritance
gives project overrides that don't go stale when the package template changes. That
staleness is the main weakness of today's custom `memory.agents_template`.

```jinja
{# SASE.md — optional; omit it and the packaged default is used #}
{% extends "sase:base.md" %}

{% block title %}# {{ project.title }}{% endblock %}

{% block project %}
{{ memory.core() }}              {# type: core notes whose `when:` matches #}
{{ memory.reference() }}         {# one-line triggers whose `when:` matches #}
{{ memory.webs(decisions="names" if audience(tribe="research") else "none") }}
{% endblock %}
```

The packaged base owns the contract and the provider-specific text that lives in adapter
code today:

```jinja
{% block contract %}
## SASE Runtime Contract
- End every turn with `/sase_final`; hand long commands to `/sase_monitor`.
{% if audience(provider="codex") %}
- `exec_command` returns after `yield_time_ms` while the command keeps running; …
{% endif %}
{% if audience(phase_worker=true) %}
- Do not create beads; record `PROPOSED FOLLOW-UP:` notes on your phase bead.
{% endif %}
{% endblock %}
```

Memory notes opt in with frontmatter, evaluated by the **same** evaluator:

```yaml
---
type: reference
description: Read before changing the SASE TUI…
when:
  role: [root, code, plan]      # OR within a key
  not: { tribe: [research] }    # AND across keys; `not` negates
---
```

**Why `audience(...)` and not raw Jinja comparisons?**

- `audience()` validates every key *and value* against a closed schema. A typo like
  `provider="codx"` fails `sase instructions check`; a raw comparison would silently be
  false.
- Frontmatter `when:` and the template share one evaluator.
- The checker can **enumerate the audience matrix** (every combination of referenced
  fact values) to render and budget each variant.

A reference note whose `when:` does not match only loses its *trigger line*. The note
stays readable through `sase memory read` for any agent.

### Launch facts (closed schema)

| Fact | Source today | Example values |
| --- | --- | --- |
| `mode` | new | `sase` (launched), `interactive` (local human projection), `external` (committed stub) |
| `provider` | `execution_provider_label` (`_invoke.py`) | `claude`, `codex`, `grok`, `muse`, `agy`, plugin providers |
| `model`, `size`, `effort` | model alias resolution / invocation options | `opus`, `large`, `high` |
| `role` | `agent_session_role` | `root`, `plan`, `code`, `epic`, `commit`, `monitor`, `gate` |
| `phase_worker` | `phase_bead_id` present | `true` |
| `tribe`, `clan` | `agent_meta` | `research`, `chop` |
| `macros` | `macros.json` names and `MacroTag` tags | `research_swarm`, `pr` |
| `commit_method` | `SASE_COMMIT_METHOD` | `pr`, `commit`, `propose` |
| `vcs`, `project`, `home_mode` | `RunnerRunState` | `github`, `sase` |
| `host` | hostname, or the `%dispatch` target | `athena`, `apollo`, `mac` |
| `flags` | SASE feature flags | for staged rollouts and A/B tests |
| `traits` | *deferred*; macro frontmatter | `read_only` |

### Audience targeting: is `%tag` the right primitive?

| Option | Verdict | Reasoning |
| --- | --- | --- |
| **Launch facts** (table above) | **Adopt (v1)** | No new syntax. Every concrete conditional I found keys on a fact SASE already has: provider (directives), role (monitor/gate leanness), phase worker (beads rule), tribe (decisions density), commit method (rollover text), host (home layer). Facts don't drift, because nobody has to remember to apply them. |
| **Macro-declared `traits:`** in macro frontmatter | **Adopt later**, when a section needs a fact that isn't derivable | The macro is what knows an agent's job. `#research_swarm` can declare `traits: [research]`, and every member inherits it with no per-prompt typing. "trait" is unused anywhere in `src/` and `docs/`. |
| `%trait:x` directive | Escape hatch only, after traits exist | A prompt-level override is useful for experiments. It needs both parsers (Python `_KNOWN_DIRECTIVES` and Rust `DIRECTIVES` / `typed_units.rs`), plus LSP completion and docs. |
| **`%tag:x` (the query's idea)** | **Reject the name** | `%tag` shipped on 2026-04-25, became `%group` on 05-10, and was replaced by tribes on 07-17. Legacy `tag` metadata is **still read as a tribe** (`core/agent_tribe.py:258,306`), so a new `tag` field would collide with that compat path. "Tag" already means macro tags, project tags (`+proj`), proc tags, notification tags, and prompt tags. Hand-typed labels also drift. |
| Reuse tribe (`%id(tribe=…)`) | Reject as the mechanism; keep it as one fact | A tribe is single-valued and controls presentation (TUI panels, `ace.tribes` styling). Tying instructions to it would couple display to behavior. |

This follows `decisions:corpus-before-mechanism`: ship the label mechanism only once a
real section needs it.

### Delivery per provider

| Provider | Explicit channel | Native SASE files to suppress in SASE runs | Notes |
| --- | --- | --- | --- |
| Claude | `--append-system-prompt-file <bundle>` (the adapter already passes `--append-system-prompt`) | `~/CLAUDE.md`, via `--settings '{"claudeMdExcludes":["/home/bryan/CLAUDE.md"]}'` | The system prompt survives compaction, which native `CLAUDE.md` handling re-reads from disk. **Verify** whether Task subagents inherit it. |
| Codex | write the bundle as `AGENTS.md` in the **existing** per-run shadow `CODEX_HOME`, replacing the `~/AGENTS.md` symlink; fall back to `developer_instructions` when the shadow home is disabled | none once project files are untracked | Merges natively with a foreign repo's own `AGENTS.md`. Mind the 32 KiB cap. |
| Grok | `--rules <bundle text>` | `GROK_CLAUDE_AGENTS_ENABLED=0` | Unaffected by trust and gitignore. |
| Muse | prompt prefix (the existing `wrap_muse_prompt` path) | — | Check whether Muse has a rules flag. Keep the prefix out of the user-visible prompt history. |
| agy | prompt prefix (the existing `_wrap_agy_print_prompt`) | — | 120 KiB argv cap. |
| Qwen | `--append-system-prompt` | — | |
| OpenCode | `instructions:` in a generated config, or a prompt prefix | — | |
| plugin providers | new hook `llm_instruction_delivery(bundle) -> DeliveryPlan`; default is prompt prefix | — | |

Every invocation also writes `$SASE_ARTIFACTS_DIR/instructions.md` and
`instructions.json`. The JSON holds the facts, section ids, budget, and hash. It also
exports `SASE_INSTRUCTIONS_FILE` so an agent can re-read its own instructions. The
instruction hash goes into `agent_meta.json`.

That replaces `capture_instruction_snapshot` (`launch_evidence.py:166`). The snapshot
records whatever files are on disk, not what the provider read: it would claim Grok saw
`AGENTS.md`, and it stops after the first home file.

### Humans, home files, and the public repo

- **Interactive sessions.** `sase instructions sync` (today's `sase memory init`)
  renders `mode: interactive` into **gitignored** `AGENTS.md` and `CLAUDE.md` in the
  primary checkout and the home directory. It never writes into ephemeral workspaces.
  SASE runs exclude these: Claude through `claudeMdExcludes`, and Codex no longer
  bridges.
- **Public repo.** Today's file tells a non-SASE tool to "use your `/sase_final` skill",
  which is wrong outside SASE. The options:
  - commit nothing; or
  - commit a **tiny, hand-written `AGENTS.md` stub** of about 10 lines ("instructions
    are generated by SASE from `SASE.md`; key commands: `just check` …"). Its native
    double-load in SASE runs is negligible.

  Don't commit a full `mode: external` projection. Avoiding a double load would require
  per-provider suppression of `AGENTS.md`, and Codex and Grok cannot reliably do that.

### Rust / Python boundary

- **Launch-fact schema and `when:` evaluator → `sase-core`.** They are a cross-frontend
  contract. The LSP should validate and complete `when:` keys in memory frontmatter and
  `SASE.md`. A TUI or web "preview the instructions agent X will get" must match the
  launch path. This passes the litmus test in `rust_core_backend_boundary`.
- **Markdown composition stays in Python for v1.** The memory renderer is there today.
  Move it to Rust only if a second frontend needs full previews. The prior report
  concluded "Python-only" for budget rendering; the difference here is that audiences
  are a contract, not just a generator detail.

## High-value use cases you may have missed

In priority order:

1. **Exactly-once, uniform delivery for every provider.** This includes giving Muse and
   Grok the home layer (tailnet and Obsidian runbooks reach only 56% of runs today), and
   removing the Claude/Codex duplication of about 790 tokens per call.
2. **One reviewable source for *everything* SASE tells a model.** The four adapter
   directives, the instruction files, and the rollover-macro rule text are written
   separately today and drift separately.
3. **Lean renders by role.** Monitor (640) and gate (239) turns were **12.5% of runs** in
   30 days. Each loads the full catalog of reference triggers and webs that a mechanical
   follow-up turn rarely needs. Phase workers get the bead rule as a rule, not as an
   "unless" clause.
4. **Research vs. code audiences.** In the router report's month of audit data, the
   small population of research runs opened decision records 51 times, against 20 for
   all non-research runs combined, and research runs don't need lint triggers. That settles the
   router report's decisions-roster debate per audience instead of for everyone.
5. **Accurate provenance.** Answer "what exactly did this agent see?" with a hash and a
   stored render. That supports debugging misbehavior, replays, and the TUI memory
   versions view.
6. **Host-aware home layer.** Retire the chezmoi `AGENTS.md.tmpl` hostname switch, and
   render correctly for `%dispatch` to apollo or mac. The target machine renders with
   its own host facts.
7. **Plugin-contributed sections.** `sase-github`, `sase-telegram`, and
   `sase-research-artifacts` can ship the instructions for their own features, shown
   only when active. Today the host repo's memory describes them by hand.
8. **Foreign and OSS repos.** Deliver the SASE contract without modifying or committing
   upstream files. Through the system-prompt channel it also outranks repo-supplied text,
   which gives some resistance to prompt injection.
9. **Measured instruction experiments.** Flag-gated variants (`when: {flags: …}`)
   measured with `memory_reads.jsonl` and finalizer compliance. That is the
   "success is behavioral" loop the router report asked for.
10. **Size-aware budgets.** A leaner render for `@xsmall` and `@small` agents.
11. **No more regeneration churn.** About 1.9 commits per day touch `AGENTS.md`. With
    per-launch rendering, a memory edit takes effect at the next launch, and the CI
    drift-masking issue disappears.

## Options considered

| Option | Verdict | Why |
| --- | --- | --- |
| Per-invocation bundle + adapter delivery + `SASE.md` composition spec | **Adopt** | Fixes every observed loading bug structurally, enables audiences, and follows `adapters-normalize-harnesses`. |
| Query as literally stated: write files into each workspace | Adopt only as a fallback channel | [Seven problems](#why-not-write-the-file-into-the-workspace); fatal for Grok. |
| Status quo plus targeted shim fixes (drop copies for some providers) | Do Phase 0 only | Can't fix the home/project duplication (a static home file can't know about the project file) or enable audiences. Claude can't drop `CLAUDE.md` because `~/CLAUDE.md` blocks its native `AGENTS.md` mode. |
| Monolithic `SASE.md` holding all instruction text | Reject | Undoes core/reference/webs, audited reads, and per-note ownership, and brings the 283-line encyclopedia back. |
| Provider-native conditionals (`.claude/rules` `paths:`, Codex overrides, Antigravity triggers) | Reject as primary | Not uniform; no audience concept beyond paths. |
| `%tag` free-form directive | Reject the name and defer the mechanism | See [the audience options table](#audience-targeting-is-tag-the-right-primitive). |
| Commit a full `external` projection | Reject | Needs `AGENTS.md` suppression that Codex and Grok can't reliably do. Use a tiny stub instead. |
| Move all of it to Rust now | Defer | The schema and evaluator go to Rust; composition follows only on demand. |

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Render failure leaves an agent with no instructions | Fall back to the last-known-good bundle for that project and audience, with a loud notification. Fail closed only if none exists. |
| Channel semantics differ (system prompt vs. user message, compaction, subagents) | Conformance check, plus before/after trigger-health and `/sase_final`-compliance metrics from the audit logs; roll back per provider via flag. |
| Double load during migration | Turn on explicit delivery **per provider**, in the same release that removes or suppresses that provider's native SASE file. |
| Audience sprawl makes behavior hard to predict | Closed facts only; `sase instructions render --as <agent>` and `--matrix`; per-audience budgets; a preview in the TUI agent panel. |
| Provider CLI updates change flags or discovery | The conformance check runs in `sase doctor` and on a schedule. This is exactly what would have caught Grok. |
| Version skew on `%dispatch` machines | Bundle schema version in `instructions.json`; dispatch refuses mismatched majors. |
| Prompt-cache churn from per-audience variation | Low. Sessions are short-lived and the system prompt already varies with cwd. Live facts go last. |

## Recommended solution

**Build instruction bundles.** A bundle is one per-invocation render, composed from
layered memory by an optional `SASE.md` spec, targeted by closed launch facts, delivered
exactly once by each provider adapter through an explicit channel, recorded as
provenance, and checked by a conformance test.

### Phase 0: stopgaps (days, independent)

1. **Grok:**
   - Pass the current rendered `AGENTS.md` content through `--rules`.
   - Set `GROK_CLAUDE_AGENTS_ENABLED=0` so a trust fix can't bring back the triple load.
   - File a bug bead for the zero-load, including the measurements above.
2. **Stop generating the copies nobody needs:**
   - Stop generating `OPENCODE.md`; OpenCode never reads it.
   - Stop generating `QWEN.md`; Qwen also reads `AGENTS.md`, so the copy doubles.
   - Verify Antigravity's precedence before dropping `GEMINI.md`.
   - Keep `CLAUDE.md` for now. `~/CLAUDE.md` blocks Claude's native `AGENTS.md` mode.
3. **Conformance check, first version.** Add `sase doctor instructions`, which parses
   the latest session of each provider:
   - Codex rollout headers;
   - Grok `agents_md_files`;
   - Muse and Claude transcripts.

   It reports the copies of project and home content each provider received.

### Phase 1: bundle renderer + delivery (one epic, flag per provider)

1. **Renderer.** Package base spec, then plugin hook, then home layer, then project
   layer. Dedupe by section id. Retire `sase/memory/sase.md` into the package base.
2. **Provider hook.** Add a delivery hook for each provider
   ([table](#delivery-per-provider)), invoked at `_invoke.py` and from both finalizer
   follow-up paths.
3. **Adapter directives.** Fold the four adapter directives into package sections that
   use `when: {provider: …}`.
4. **Provenance.** Write `instructions.md` and `instructions.json` to the artifacts dir
   and the hash to `agent_meta`. Replace `capture_instruction_snapshot`.
5. **Conformance assertion.** Upgrade the conformance check to assert exactly one bundle
   hash per invocation.

### Phase 2: stop committing generated files

1. Untrack and gitignore the 20 generated instruction files. Optionally add the tiny
   public `AGENTS.md` stub.
2. Turn the nested `AGENTS.md` files into path-scoped reference notes with one-line
   triggers. Merge `tools/AGENTS.md`'s Symvision text into `symvision.md`.
3. Change `sase memory init` into `sase instructions sync`, which writes the gitignored
   human projections. Drop the chezmoi `.tmpl` hostname switch in favor of `host` facts.
4. Update the following, each through `/sase_memory_write`:
   - `docs/agent_providers.md`, which still says "Instruction double-load";
   - the glossary's **Agent Instruction File** term, which is stale ("run automatically
     as a sase post-commit hook");
   - `docs/init.md`.

### Phase 3: audiences

1. Put the launch-fact schema and `when:` evaluator in `sase-core`, with LSP validation.
   The `audience()` Jinja function calls the evaluator.
2. Add `sase instructions check --matrix`: render every reachable audience and enforce
   the router report's ratchet per audience.
3. Use the first conditionals with measured value:
   - lean monitor and gate renders;
   - the phase-worker bead rule;
   - decisions density for research vs. code;
   - commit-method rules.

### Phase 4: traits, only on demand

Add macro frontmatter `traits:` once a real section needs a label that no fact provides.
Add a `%trait` escape hatch after that. Never `%tag`.

### Governance

Write a decision record, roughly "Instructions Are Rendered Per Invocation And Delivered
By Adapters". It extends `adapters-normalize-harnesses` and records:

- invariants A, C, and E;
- the facts-first audience rule (D);
- the reopen conditions:
  - a provider loses every explicit channel; or
  - the conformance check can't observe a provider's actual context.

### What would change my mind

- **Explicit delivery measurably lowers compliance.** If trigger reads or `/sase_final`
  compliance drop for a provider after the switch, and reverting that provider's flag
  restores them, then that provider's channel is weaker than native loading. Fall back
  to native-file delivery for that provider alone.
- **Grok's zero-load is a SASE-side bug,** fixable by passing trust or cwd correctly.
  The redesign is still right, but Phase 0 becomes a one-line fix.
- **Real outside contributors appear on `sase-org/sase`.** Then the committed `external`
  projection becomes worth its suppression complexity.
