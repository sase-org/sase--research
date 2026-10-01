# SASE vs. OpenAI's "Harness Engineering": A Critique and Improvement Plan

**Researcher:** cld (swarm `research.33`) · **Date:** 2026-10-01 · **Subject repo:** `sase`
at `ebf070e16a` (master)

**Source critiqued against:** OpenAI, _"Harness engineering: leveraging Codex in an
agent-first world"_ (<https://openai.com/index/harness-engineering/>). openai.com returned
HTTP 403 to direct fetches, so I read the full text through a reader proxy
(`r.jina.ai`). Everything below about the article is paraphrased, with only short quotes.

---

## 1. Bottom Line

SASE is a mature harness, and in several respects it is more rigorous than the one the
article describes:

- decision records with a claim, a rationale, a cost and a reopen condition;
- host-owned completion;
- ToolRun triage verdicts and receipts;
- generated, drift-checked instruction files for five providers;
- audited memory reads;
- a deterministic fake provider for testing the harness itself.

Per human, it also runs at a much higher volume than the OpenAI team:

| | OpenAI team | SASE |
|---|---|---|
| Size | ~1M lines of code | ~1.22M lines of `src/` Python + ~1.38M lines of tests |
| Output | ~1,500 merged PRs over 5 months | 15,493 commits since 2026-02-14 (1,897 in the last 30 days) |
| People | 3 to 7 engineers | one human |
| Agent share | not stated | 618 of the last 632 commits carry a `SASE_AGENT=` trailer |

SASE is weakest at the loops the article treats as essential once throughput outgrows
human attention:

1. **No agent-to-agent review loop is wired into landing.** Commits rebase and push
   straight to master: 0 merge commits in 30 days and no PRs. Mentors exist but are
   not configured for this repo, and they don't block anything.
2. **Several important invariants are instructions, not checks:**
   - the Rust-core boundary;
   - "run `just check` before finishing" — the ordinary completion path records an
     `unverified` mark but doesn't refuse;
   - layering inside the 517k-line `ace` package.
3. **The file-size invariant sits outside the agent's loop.** About **18% of all
   commits in the last 30 days (341/1,897)** are `toobig` file-split agents cleaning
   up files that other agents made too large.
4. **Application legibility stops at the TUI's pixels.** Nothing supports booting this
   workspace's code against an isolated, throwaway state root. Telemetry and traces go
   to shared, machine-global paths.
5. **The knowledge system is well built but not gardened end to end.** Docs get a
   recurring refresh agent; memory notes, nested `AGENTS.md` files and machine-local
   routine config do not. The always-loaded map is about 2.8× the article's ~100-line
   target.

The article's core claim is that when an agent fails, the engineer should ask what
capability is missing and how to make it "legible and enforceable." SASE already
follows that rule; `guarded-recipes` is a textbook example. The highest-leverage work
is to apply it consistently to the four gaps above.

---

## 2. The Standard: What the Article Actually Prescribes

I reduced the article to twelve testable standards (H1–H12):

| # | Standard (paraphrased) |
|---|---|
| H1 | **Humans steer, agents execute.** Human time and attention is the only scarce resource; every human touchpoint should be at a high layer (intent, acceptance criteria, judgment). |
| H2 | **Failure means a missing capability.** When an agent struggles, add the missing tool, guardrail or doc to the repo, and make it enforceable rather than just written down. |
| H3 | **A map, not a manual.** A short (~100-line) `AGENTS.md` works as a table of contents into a structured `docs/` system of record, so context is disclosed progressively. |
| H4 | **The repo is the system of record.** Anything the agent cannot reach in context does not exist. Plans (with progress and decision logs), design docs with verification status, an architecture map, quality grades and a tech-debt record are all versioned and co-located. |
| H5 | **Knowledge is mechanically verified.** Linters and CI check freshness, cross-links and structure, and a recurring "doc-gardening" agent opens fix-ups. |
| H6 | **Enforce invariants, not implementations.** Use rigid layering with checked dependency directions, custom lints and structural tests, and a small set of "taste invariants" (structured logging, naming, file size). Lint messages carry remediation instructions for the agent. |
| H7 | **The app is legible to the agent.** It can boot one instance per worktree, drive the UI (screenshots, DOM snapshots), and query an ephemeral per-worktree observability stack, so performance and behaviour targets become checkable. |
| H8 | **Agents review agents.** Self-review plus additional agent reviewers, iterated until they are satisfied. Human review is optional. |
| H9 | **Throughput changes merge philosophy.** Few blocking gates and short-lived changes; flakes get re-runs, not indefinite blocks. "Corrections are cheap, and waiting is expensive." |
| H10 | **End-to-end autonomy.** Reproduce a bug, record evidence, fix it, validate by driving the app, record evidence again, handle feedback and build failures, escalate only for judgment, merge. |
| H11 | **Entropy needs garbage collection.** "Golden principles" are encoded in the repo; recurring background agents scan for deviations, update quality grades, and open small refactors that can be auto-merged. |
| H12 | **Favour legible dependencies.** Prefer "boring," composable tech, and reimplement opaque upstream behaviour in-repo when that is cheaper to reason about. |

---

## 3. Scorecard

Grades: **A** = meets or exceeds the article · **B** = mostly there, with clear gaps ·
**C** = partial or instruction-only · **D** = largely absent.

| # | Standard | Grade | One-line verdict |
|---|---|---|---|
| H1 | Humans steer | **B+** | Approval sits at the plan and launch layer, not per commit. Human-attention cost is not measured. |
| H2 | Failure → capability | **A** | The decisions web records this reflex explicitly; `guarded-recipes` is the model case. |
| H3 | Map, not manual | **B** | The map is generated and drift-checked, with progressive disclosure. It is 283 lines, and about half is rosters. |
| H4 | Repo as system of record | **B−** | Excellent decision records. Plans and beads live in sidecars, harness routines live in machine-local config, and there are no quality grades. |
| H5 | Knowledge verified and gardened | **C+** | Generated-file drift and plan links are checked. Docs get a refresh agent; memory, nested `AGENTS.md` files and prose↔code truth do not. |
| H6 | Enforce invariants | **B−** | Many bespoke checkers and AST tests. No checked layering model; the most important boundary is prose; the size gate is out of loop. |
| H7 | App legibility | **B−** | Strong TUI capture and driving. No per-workspace isolated instance and no per-workspace observability. |
| H8 | Agent-to-agent review | **D** | Mentors aren't configured or wired to landing, and there is no self-review step. |
| H9 | Merge philosophy | **A−** | Aligned and more rigorous: two-speed CI and triage verdicts. Verification on landing is still advisory. |
| H10 | End-to-end autonomy | **B** | Epics run unattended through waves to a land agent, and gates provide escalation. There is no evidence capture and no review loop. |
| H11 | Garbage collection | **B−** | `toobig_split` and `refresh_docs` are real GC. No golden-principles list, no quality grades, and GC config is off-repo. |
| H12 | Legible dependencies | **B** | Rust core is pinned and auto-cloned, but split across repos. Boring Python/Textual stack; symvision is published upstream. |

---

## 4. Where SASE Already Meets or Beats the Article

Each of these goes beyond what the article describes, so keep them.

1. **Decision records as compressed, falsifiable architecture.**
   - The `decisions` web has 24 records, each with **Claim / Why / Cost / Reopens
     when**.
   - Records are immutable once accepted; supersession is marked with a back-link,
     never edited in place.
   - This covers the article's "core beliefs" and "design docs with verification
     status," and more. Two examples:
     - `corpus-before-mechanism` records three retrieval systems that were built and
       then deleted (2026-04 to 2026-07).
     - `ci-two-speed-split` lists eight rejected CI alternatives.
   - That is exactly the agent-legible "why" the article says normally lives in Slack.
2. **Instruction files are generated and drift-checked.**
   - `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `QWEN.md` and `OPENCODE.md` are byte-identical
     renders of `sase/memory/`.
   - `sase validate` runs `init memory --check`, `init skills --check` and
     `plan links validate`, both in `just check` and in CI.
   - The article only says knowledge is linted. SASE makes the map impossible to
     hand-edit out of sync.
3. **Progressive disclosure with an audit trail.**
   - Reference notes are listed by description only; web strands are read on demand.
   - `sase memory read` logs every read with a reason, and `sase skill log` logs skill
     use.
   - That gives SASE something the article lacks: data on which knowledge agents
     actually consume.
4. **Rules promoted into code once instructions plateau.**
   - `guarded-recipes` records that instruction-led adoption of `sase tool run` stalled
     near 90%.
   - The fix was a dependency-free `sh` guard (`tools/require_tool_run`) whose refusal
     prints the remedy.
   - That is the article's "when documentation falls short, promote the rule into
     code," done with measurement first.
5. **Flake handling that preserves signal.**
   - ToolRun triage labels each failure NEW, KNOWN, FLAKY or UNKNOWN. A KNOWN label
     needs an independent witness, and triage never changes an exit code.
   - `tests/reproducible_flake_baseline.txt` is treated as debt that needs a bead.
   - The article's approach (re-run and move on) is cheaper. SASE's keeps flake debt
     visible without blocking.
6. **A harness that tests itself.**
   - `fakey` is a deterministic fake provider with `@flaky`, `@crash`, `@hang` and
     `@capacity` scenarios that runs through the real registry and retry code.
   - `selection-health` measures whether diff-scoped test selection has ever been
     wrong.
   - `tool-triage-backtest` replays triage over retained logs.
   - The article does not describe instrumenting the harness this way.
7. **Taste invariants with agent-directed remediation.** Examples:
   - `tools/check_test_wait_helpers` says what to use instead and how to annotate an
     exception.
   - `validate_changelog` says to put the text in the commit body.
   - The symvision memory note gives a ranked fix order (delete, then privatize, then
     pragma, then epic whitelist).
   - The `toobig` 1000/850/700 limits clearly work: the largest `src/` file is 739
     lines across 5,403 files.
8. **Low-noise instructions.**
   - The 283-line `AGENTS.md` uses only 7 MUST/IMPORTANT/CRITICAL/NEVER markers.
   - The 2,569 lines of skill sources use 6.
   - That avoids the article's "when everything is important, nothing is" failure in
     the generated surface.

---

## 5. Detailed Critique, Gap by Gap

### 5.1 H8: there is no agent-to-agent review loop on the landing path (biggest gap)

**Article.** A PR goes through self-review, then requested agent reviews locally and in
the cloud. The agent responds and iterates "until all agent reviewers are satisfied."
Humans may review but are not required to.

**SASE today.**

- **Landing:** `vcs_create_commit` commits, runs `git rebase --autostash
  origin/<default>`, and pushes with up to three rebase retries
  (`src/sase/vcs_provider/plugins/_git_commit_dispatch.py`). Master saw 632 commits in
  the last 7 days and no merge commits in the last 30.
- **Mentors** (`docs/mentors.md`) are SASE's review agents, but on this repo they do
  nothing:
  - they run only on Patches in Ready or Mailed status;
  - their comments are applied by a human toggling them in the TUI;
  - nothing blocks on them;
  - there are **no `mentor_profiles`** in `sase/sase.yml` or in the user and machine
    configs;
  - `docs/vcs.md` says GitHub PR URLs get no plugin-supplied mentor profiles.

  In practice, almost nothing that lands on sase master is reviewed by an agent.
- **No self-review step.** Neither the finalizer nor `docs/commit_workflows.md` has
  one. The `review` xprompt exists but is manual.
- **Epics:** the land agent (`bd/land_epic`) does one verification pass, not a loop.

**Why it matters more for SASE than for OpenAI.** With one human, nobody reviews
incoming work by default. Over the last 30 days:

- 436 of 1,897 commits are `fix:` (ratio to `feat:` ≈ 0.52), and 113 of those are
  `fix(ace|tui…)`.
- There were 5 reverts.

That fix ratio alone doesn't prove escaped defects, since many fixes target pre-existing
bugs. But it is the metric a review loop should move, and nobody measures it today.

**What "good" looks like in SASE's own terms.** Agents are single-turn
(`single-turn-agents`), so the "Ralph loop" must be built mechanically, not run inside
one session:

- the finalizer, or a post-land routine, launches a reviewer agent on the exact diff;
- error-severity findings pipe to a fix agent through `/sase_handoff`-style
  continuation;
- iteration is capped at N rounds;
- whatever is still unresolved after the cap escalates through a gate.

### 5.2 H6: SASE has many invariants but no architecture model

**Article.** Each domain has fixed layers with "strictly validated dependency
directions." Cross-cutting concerns enter through one interface. This is "an early
prerequisite" with agents, not a luxury for big teams.

**SASE today.**

- `src/sase/` has **220 entries / 87 subpackages and 1.22M lines**. `ace` alone is
  **517k lines** (42%), followed by `main` (64k), `bead` (51k) and `core` (50k).
- There is **no import-linter, tach or ruff `TID`/`I` banned-import config.** Ruff
  selects only E, W, F, B, C4, TC004 and UP.
- Boundaries exist only as about 38 bespoke AST-scanning tests, each guarding a single
  edge. Examples:
  - `tests/test_agent_monitor_import_boundary.py` ("sase.agent must not import the
    sase.monitor package at module scope");
  - an allowlist for primary-writable store callers;
  - import-cost budgets for the TUI and the chop path.
- **The most important boundary, Rust core vs Python, is enforced only in prose.** It
  is inlined as core memory on every turn (`rust_core_backend_boundary`, 17 lines).
  The only mechanical check is that `require_rust_binding("x")` targets exist. Nothing
  detects Python reimplementing core logic.
- `docs/architecture.md` (286 lines) has a System Boundary table of areas but **no
  dependency directions and no layer model.** `docs/development.md`'s source map lists
  about 33 paths, against 87 subdirectories.

**Critique.** Edge-by-edge AST tests are the right instinct, aimed at symptoms. Each one
is written after a regression, so the architecture is enforced only where it has
already broken. The article warns that agents copy whatever patterns exist. In a
517k-line `ace` package with no declared internal layering, the "pattern that exists"
is whatever the last few hundred agents wrote. A declarative contract file would turn
the scattered tests into one map that is both legible and enforced, and could generate
the dependency section of `architecture.md`.

### 5.3 H6/H11: the size invariant runs outside the loop, so GC becomes churn

**Facts.**

- The `Justfile` comment (lines 726–729) deliberately drops `toobig` from both
  `just check` and `just check-full`, because "an agent can rarely act on it (the
  toobig_split routine owns those splits)."
- `tests/test_justfile_lint.py` pins that choice.
- The `toobig_split` routine lives in machine-local `~/.config/sase/sase_athena.yml`
  and proposes `%auto #split_file:<path>` agents hourly.
- **341 of the 1,897 commits (18%) in the last 30 days carry a `toobig` agent trailer.**

**Critique.**

- **It works:** no `src/` file is over 739 lines.
- **But it is the costly version of the article's pattern.** The article puts taste
  invariants into the authoring agent's lint loop, with remediation text, so the
  violation never lands. SASE lets every agent land oversized files and then spends
  about one commit in six splitting them.
- **Each split costs more than it looks:**
  - a full agent run;
  - a full `just check`;
  - a rebase against a moving master;
  - a context-cold agent guessing the module seams the original author knew.
- **The stated reason can be fixed.** "An agent can rarely act on it" is true of a
  whole-repo gate, not of a **diff-aware ratchet**: fail only if *this diff* pushes a
  file over 850 or 1,000, or creates a new file over 700. The authoring agent, which
  knows the seams, can act on that cheaply.

### 5.4 H1/H9/H10: verification at landing is still an instruction

**Facts.**

- `lint_and_test.md` instructs agents to run `just check` after changing files. But
  the ordinary `/sase_final` path records an `unverified` mark as "nonblocking
  provenance, not a refusal" (`docs/monitors.md` ~370).
- Prepared completion (`sase final prepare` plus a verify monitor) commits only on
  pass, but it is opt-in.
- CI runs after the push (`master-gate.yml`, `on: push`), with the heavy lane every 2h.

**Critique.**

- The minimal-gates stance is consistent with the article and is well argued in
  `ci-two-speed-split` and `check-full-is-explicit`. This is a strength.
- But SASE's own `guarded-recipes` decision found that instruction-led compliance
  plateaus around 90%. Nothing reports what fraction of landed commits carry a
  covering `check` receipt.
- If it is around 90%, roughly 60 commits a week land without even the scoped check,
  and CI detects their breakage after the fact. Each one then becomes a red master that
  other agents' triage must label KNOWN.
- There is a related smell. `lint_and_test.md` spends a paragraph listing what
  is *not* explicit instruction to run `check-full`: landing an epic, "being careful,"
  a sibling agent's example, and so on. When a memory note has to argue against
  rationalizations, the rule wants to be a guard. The pattern is already proven in
  `tools/require_tool_run`.

### 5.5 H7: TUI legibility is strong, runtime legibility is weak

**Strong.**

- `sase screenshot` takes an ordered `-p/-T/-w` input script and turns a SIGUSR2 SVG
  export into a PNG.
- `sase tui --tmux` prints its targets for external driving.
- `AcePage` exposes Pilot plus `state()`, the closest analogue to a DOM snapshot.
- 868 pixel-exact PNG goldens with HTML diff reports.
- Repro bundles with `sase repro replay --assert-stable`.
- Perf baselines and floors under `tests/perf/baselines/`.

**Weak, compared with "bootable per worktree" plus an "ephemeral observability stack":**

- **No blessed isolated instance:**
  - `sase` on PATH is the uv-tool release (`#!/home/bryan/.local/share/uv/tools/sase/bin/python`).
  - `sase screenshot` relaunches via `sys.executable -m sase tui`
    (`src/sase/screenshot/local.py:216`), so a bare `sase screenshot` shows the
    **installed release, not the agent's change**.
  - It also runs against the user's real `~/.sase` state. The memory note says live
    captures "include real timestamps, running procs, and host state."
  - `SASE_HOME` isolation exists, but each use is local to one tool: pytest workers,
    the ToolRun smoke harness, `demos/scripts/seed_sase_ace_demo`. Agents have no
    general recipe.
- **No `run` recipe or project skill.** The tool catalog has only `check`,
  `check-full`, `install`, `test` and `test-visual`.
- **Shared observability:**
  - telemetry lives in a machine-global `~/.sase/telemetry/metrics.sqlite`, with no
    project attribution;
  - traces default to `~/.sase/perf/tui_trace.jsonl`;
  - parallel workspaces mix their signals;
  - the query interface is `jq` recipes in a 1,200-line runbook.
- **Perf floors are out of loop.** They run only in CI `perf-floors`, not in the
  agent's `just check`. A prompt like "keep j/k highlight p95 < 16 ms" is not
  something an agent can check locally in one command.
- **No agent-captured evidence.** No before/after media is produced as part of
  completion, though `done.json` already supports `image_paths` and `video_paths`.

### 5.6 H3/H4/H5: the knowledge system is well built but drifting at the edges

**The map is too big.** `AGENTS.md` is 283 lines (17 KB):

| Part | Lines | Contents |
|---|---|---|
| Core | ~103 | always-loaded content |
| Reference index | ~33 | one-line "read when…" entries |
| Web rosters | ~145 | decisions roster ~90, glossary ~27, task types ~22 |

- The decisions roster still lists superseded records (`two-speed-verification`,
  `v1-import-retired`, with "superseded by" tags). That is the article's "graveyard
  of stale rules," paid for on every turn.
- In this session, the home-level `/home/bryan/CLAUDE.md` (74 lines) repeated the
  generated "SASE Memory," "Repositories" and "SASE Final Declaration" sections. Each
  turn loaded those sections twice.

**Docs are a manual, not a map.**

- `docs/` holds 54.9k lines across its Markdown pages. `ace.md` alone is 9,159 lines
  and `configuration.md` 7,545.
- `docs/index.md` is a marketing landing page. There is no agent-facing docs index
  that says "for X, read section Y."

**Off-repo harness state.** Load-bearing harness behaviour lives in machine-local
`~/.config/sase/sase_athena.yml`, not in `sase/sase.yml`:

- `toobig_split`, which owns the size invariant;
- `refresh_docs`, the doc gardener;
- `ci_watch`, which gates releases.

An agent in the sase repo cannot see, version or reason about those routines. The
`lint_and_test` note says the routine "owns" splits, but there is no in-repo
definition to read. This conflicts directly with "anything it can't access in-context
effectively doesn't exist."

**Sidecar plans.**

- Tales, epics, beads and prompt archives live in sidecar repos reached through
  `sase repo path` or `SASE_SDD_*`. That is legible to SASE agents, but not to a plain
  provider session or an outside reviewer.
- More importantly, **plans have no living progress or decision log.** OpenAI-style
  ExecPlans carry progress, surprises, decision logs and an outcomes retrospective.
  SASE's plan schema is frozen at approval (unknown fields are errors). Progress is
  scattered across bead notes, and nothing writes the retrospective back into the plan
  the next agent will read.

**Gardening covers docs only.**

- The `refresh_docs` job (update, then polish, every 100 commits) is real doc-gardening
  and visibly active: "docs: refresh guides…" and "docs: correct refreshed guides
  against current behavior" commits on 2026-09-21, 22, 23, 26, 27, 28 and 29.
- Nothing equivalent covers:
  - **memory notes.** Edits are human-gated through `memory` beads. Unresolved
    `[[links]]` are only `sase doctor` warnings, and `sase doctor` is not part of
    `sase validate`.
  - **nested hand-written `AGENTS.md` files.**
  - **prose↔code truth claims in general.**
- Concrete examples:
  - `src/sase/ace/AGENTS.md` tells agents to update
    `home/dot_config/nvim/syntax/saseproject.vim`, a chezmoi-repo path that does not
    exist in this checkout and is unreachable without `/sase_repo`. The same file has
    four "CRITICAL" headers.
  - `docs/memory.md:206` documents that a help string "is stale" instead of fixing
    it. The help string at `src/sase/main/parser_memory.py:386-388` is still stale.

**Missing artifacts the article treats as standard:**

- a per-domain **quality grade** document;
- an aggregate **tech-debt registry**. Debt is spread across task beads, flag beads,
  symvision whitelists and the flake baseline, with no single view;
- **freshness or ownership metadata** on docs and memory. No `verified_at`, `owner` or
  `stale_after` fields exist anywhere.

### 5.7 H6: cheap lint holes

- **Ruff:**
  - `F821` (undefined name) and `F401` (unused import) are globally ignored
    (`pyproject.toml:277–283`).
  - mypy covers `src` only, so the **1.38M lines of tests have no undefined-name
    check** short of running them.
  - Since `just check` runs only a diff-scoped test lane, an undefined name in an
    unselected test survives until CI.
- **Checker messages without remediation:**
  - `tools/pyscripts-260801` ("[Rule 1] Unused: …") states only the violation.
  - The patch/stitch terminology audit and most `check_feature_flags` rules do the
    same.
  - The article's rule is that custom lints are written so their errors inject the fix.
- **Logging is not enforced:**
  - 378 `src` files use `logging.getLogger` and 381 contain bare `print(` (many of
    them are legitimate CLI output).
  - Nothing distinguishes the two, and there is no structured-logging convention. That
    matters for H7: logs only become agent-queryable once they are structured.

### 5.8 H12: the cross-repo core is a legibility tax

- The Rust core (`sase-core`) is a separate repo, pinned by `sase-core-revision.txt`
  and auto-cloned into `sase/repos/linked/`.
- `tools/validate_sase_core_rs` alone is 3,452 lines of skew and wire-schema checking.
- `rust-core-required` and the core-boundary memory justify the split well.
- The cost lands squarely on agent legibility:
  - one logical change spans two repos, a pin bump and a binding check;
  - the critical boundary is enforced in prose (see 5.2).
- The article's heuristic of preferring dependencies the agent can fully internalize
  in-repo doesn't require merging the repos. It does argue for making the boundary
  mechanically visible from the sase side.

### 5.9 H1: human attention is spent well but never measured

- Human touchpoints are concentrated at the steering layer, as the article recommends:
  - `PlanApproval` and `EpicApproval`;
  - `LaunchApproval` for agent-spawned agents;
  - `TaskTriage` for task beads after a +1 threshold;
  - questions and gates for judgment calls.
- Landing itself needs no approval.
- Epic waves run unattended: commits arrive at 34–51 per hour-of-day bucket between
  00:00 and 05:00 over the last 30 days.
- But SASE measures plenty about compute and almost nothing about the article's
  "one truly scarce resource." No report gives:
  - gates answered per day or median human response latency;
  - human minutes per landed change;
  - the share of a human's attention spent on approvals versus judgment.
- Without that, nobody can tell whether a new gate type, say a review-escalation gate
  from 5.1, saves or spends the scarce resource.

---

## 6. Actionable Takeaways (Prioritized)

Each item names the gap it closes and a first step sized for one agent or a small epic.

### Tier 1: highest leverage, do first

1. **Wire a bounded agent-review loop into landing (H8).**
   - Configure a `mentor_profiles` set (or a dedicated review finalizer stage) for
     sase itself, triggered on the exact landing diff.
   - Start with epic phases and diffs over ~200 lines.
   - Error-severity findings pipe to a fix agent, capped at 2 rounds. Anything still
     unresolved goes to a gate, not to master.
   - If pre-land latency is unacceptable, run it as a post-land routine that files
     `bug` beads tagged with the offending SHA. That is the article's "corrections are
     cheap" variant.
   - Success metric: fix-after-feat rework on the same files within 7 days, and the
     revert rate.
2. **Measure verified-landing rate, then guard it (H9/H10).**
   - Add a report: the share of landed commits whose finalizer saw a covering `check`
     receipt versus `unverified`.
   - If it is under ~95%, apply the `guarded-recipes` precedent: the commit finalizer
     requires a covering receipt or an explicit declared skip reason, for example
     docs-only diffs.
   - Make the same move for `check-full`: refuse it inside agents unless
     `SASE_CHECK_FULL_AUTHORIZED=<bead|prompt ref>` is set. Then delete the
     paragraph-long "this is not explicit instruction" list from `lint_and_test.md`.
3. **Put `toobig` back in the loop as a diff-aware ratchet (H6/H11).**
   - Add a `just check` stage that fails only when this diff grows a file past 850 or
     1,000 lines, or adds a new file over 700.
   - Its message should point at the `split_file` seam conventions, such as facades
     and no `_private` re-exports.
   - Keep `toobig_split` for the legacy backlog.
   - Target: bring `toobig` agent commits from 18% of all commits to under 5%.
4. **Declare the architecture and check it (H6/H4).**
   - Adopt import-linter or tach, or extend the existing AST-boundary helpers into one
     declarative `architecture` contract file.
   - Start with:
     - the Rust-core boundary, for example banning `sase.*` modules from
       reimplementing listed core domains by module allowlist;
     - a layer order inside `ace`, such as model → state → actions → widgets → app;
     - the `agent`/`monitor`/`finalizers` edges that today have one-off tests.
   - Generate the "Dependency rules" section of `docs/architecture.md` from the
     contract so the map can't drift from the check.
   - Every violation message should say which layer may import which, and where the
     shared helper belongs.

### Tier 2: legibility and system-of-record hygiene

5. **Ship a per-workspace sandbox (H7).**
   - Add `just sandbox up|down`, or `sase dev up`, which:
     - seeds a throwaway `SASE_HOME`/`SASE_TMPDIR` world, reusing
       `demos/scripts/seed_sase_ace_demo`;
     - runs **this workspace's** `.venv/bin/sase`;
     - namespaces the tmux session and every telemetry and trace path to the
       workspace;
     - tears everything down afterwards.
   - Make `sase screenshot` refuse, or warn loudly, when the `sase` it relaunches is
     not the workspace's code.
   - Add a `run` project skill and a `sandbox` tool-catalog entry.
6. **Move project-scoped harness config into the repo (H4).**
   - Check the sase-specific parts of `toobig_split`, `refresh_docs` and `ci_watch` into
     `sase/sase.yml` (or `sase/routines.yml`).
   - Leave only machine capacity knobs in `~/.config/sase/sase_athena.yml`.
   - Then apollo and the Mac get the same GC, and agents can read the rule that "owns"
     an invariant.
7. **Shrink the always-loaded map toward ~120 lines (H3).**
   - Drop superseded records from the inlined decisions roster, or inline only titles
     and slugs.
   - Replace the glossary term dump with a one-line pointer plus the 10 most-read
     terms, chosen from `memory_reads.jsonl` data.
   - Remove the duplicated SASE sections from the home-level `CLAUDE.md`, or have
     `sase memory init` own that file too.
   - Add a line and token budget to `init memory --check`, so growth fails the same way
     drift does.
8. **Garden memory and nested `AGENTS.md` mechanically (H5).**
   - Add `sase memory lint` to `sase validate`. It should verify that every
     backticked repo path, `just` recipe, `sase` subcommand and flag, and `[[link]]` in
     memory notes and nested `AGENTS.md` files exists, and fail on unresolved links.
   - Add a weekly `memory_audit` routine modelled on `refresh_docs`. It runs that lint
     plus an LLM truth check and files `memory` beads, since edits stay human-gated by
     design.
   - First catches: the `saseproject.vim` path, and the stale help string documented
     in `docs/memory.md:206`.
9. **Make epics living execution plans (H4).**
   - Allow `## Progress`, `## Surprises`, `## Decision Log` and `## Outcomes`
     sections in epic files.
   - Have phase workers append one line each.
   - Have the land agent write the retrospective and roll up `PROPOSED FOLLOW-UP`
     notes.
   - Then the next planner reads what happened, not just what was intended.

### Tier 3: compounding quality

10. **Generate a quality scorecard per package (H4/H11).**
    - Add `sase quality report`, which writes `docs/quality.md`.
    - Grade each top-level `src/sase/*` package from signals SASE already collects:
      - size and growth;
      - share of fix commits;
      - flake-baseline entries;
      - test-cost budget overruns;
      - symvision whitelists;
      - docs-refresh corrections;
      - coverage contexts.
    - Point the GC routines at the lowest grades instead of only at file size.
11. **Write a short "golden principles" file with an enforcement column (H11).**
    - Collect the recurring taste rules into one ≤30-line list, each naming its
      enforcing check or saying "UNENFORCED." Sources:
      - `gotchas`;
      - the four CRITICALs in `src/sase/ace/AGENTS.md`;
      - `split_file.md`;
      - the test-wait rule;
      - the core boundary.
    - The UNENFORCED rows become the lint backlog, and the file can be core memory in
      place of scattered prose.
12. **Close the cheap lint holes (H6).**
    - Enable `F821` at least for `tests/`, with per-file ignores where dynamic names
      are intentional.
    - Consider `F401` with re-export allowlists.
    - Add remediation text to every report-only checker (`pyscripts`,
      terminology audit, flag rules).
    - Pick one logging convention and lint `print(` outside CLI-output modules.
13. **Make agent evidence part of completion for UI changes (H10).**
    - When a diff touches `src/sase/ace/**`, ask the finalizer for before and after
      sandboxed `sase screenshot` captures (item 5), attached through
      `done.json.image_paths`.
    - Optionally record a short VHS tape for interaction bugs.
14. **Track human attention as a first-class metric (H1).**
    - Write a weekly report covering:
      - gates raised and answered;
      - median response latency;
      - approvals per landed commit;
      - unattended-hours share;
      - the item 2 verified-landing rate;
      - the item 1 rework rate.
    - Use it to decide whether each new gate or loop pays for itself, the way the
      decision records already require "Reopens when" evidence.

---

## 7. Closing Note

The article ends by saying the discipline now lives in the scaffolding rather than the
code. SASE has clearly taken that to heart.

What remains is to close the loop between the scaffolding and the code at the points
where today a human-written instruction, a machine-local config or a later cleanup
agent stands in for an in-loop check:

- review;
- verification at landing;
- file size;
- layering;
- runtime legibility;
- memory freshness.

SASE has already made this move once, with `tools/require_tool_run`. Its own decision
records say to repeat it whenever an instruction plateaus.

### Evidence Notes and Caveats

- Repo metrics come from `git ls-files`/`git log` at `ebf070e16a` on 2026-10-01.
  "Commits" are not PRs; SASE commits are typically smaller than an OpenAI PR, so
  throughput comparisons are indicative only.
- The `toobig` share counts `SASE_AGENT=` trailers containing `toobig` (341) against
  all commits (1,897) in `git log --since='30 days ago'`.
- Survey subagents gathered part of the evidence. I spot-checked the load-bearing
  claims directly:
  - the ruff config;
  - the `Justfile` check recipes;
  - the commit statistics;
  - the routine definitions;
  - the absence of mentor config;
  - the screenshot relaunch path.
- I did not verify the decision records' historical claims beyond reading them.
