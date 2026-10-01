# SASE Against OpenAI's "Harness Engineering": Consolidated Critique

**Date:** 2026-10-01 · **Subject:** `sase` at `ebf070e16a` (master) · **Inputs:** five
independent reports (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`), plus the lead's own
re-read of the article and independent verification against the repo, the machine-local
ToolRun ledger, AXE routine config, and git history.

**Source critiqued against:** Ryan Lopopolo, OpenAI, _"Harness engineering: leveraging
Codex in an agent-first world"_ (February 2026),
<https://openai.com/index/harness-engineering/>. openai.com refuses direct fetches, so
the full text was read through a reader proxy. Article claims below are paraphrased, with
only short quotes.

---

## 1. Bottom Line

SASE is a serious, mature harness. On the **control plane around agents** it is ahead of
the team in the article:

- numbered, claimed workspace clones;
- durable state outside the chat;
- mechanical continuation through monitors, gates, and sessions;
- host-owned completion;
- ToolRun evidence with triage verdicts and receipts;
- audited progressive disclosure through `sase memory read`;
- immutable decision records;
- adapters that normalize several provider CLIs.

The article's real thesis is not "run more agents." It is that **every agent failure
should become a capability that is legible and enforceable**, so each run makes the next
one cheaper. SASE is weakest exactly where that loop should close. All five researchers
found pieces of this. The lead's verification adds one finding that none of them
reported, and it changes the ranking of the gaps:

1. **The landing path has no review and no gate, so no one owns a red master.**
   - All 1,897 commits from the last 30 days were pushed straight to master. There were
     0 merge commits, and the only PRs are automated core-pin bumps.
   - No mentor profiles are configured anywhere, and mentors only run on Patches anyway.
   - The ordinary `/sase_final` path records `unverified` as nonblocking provenance.
   - The ToolRun ledger shows what follows from that. Over the last 7 days on athena,
     `check` ran **1,084 times and passed 31 times**: 31 of 860 settled runs, or 3.6%.
   - Over 1,000 failure signatures have **no owner**. **123 of them were hit by 10 or
     more different agents**. Some stayed on master for 1–4 days.
   - `ci_watch` notifies the human. Its own description says it never launches repair
     agents.

   The article's "corrections are cheap, waiting is expensive" assumes that someone
   actually makes the correction. In SASE, triage makes it cheap for each agent to
   *ignore* an inherited failure, which is correct by design, but nothing makes anyone
   *fix* it.
2. **Several invariants are enforced after the fact or only in prose.**
   - `toobig` is kept out of `just check`. As a result, **341 of 1,897 commits (18%)**
     are later file-split agents.
   - Python has no layering model, and `docs/development.md` admits a large import
     cycle.
   - The Rust-core boundary is enforced only by instructions.
3. **The inner feedback loop is trustworthy but not fast.**
   - Scoped test selection is excellent: 99.2% mean recall.
   - But `check` has a p90 of 27 minutes, and the scoped test stage has a p90 of 40
     minutes.
   - 185 inline runs were killed at the provider ceiling, and the week burned 52.5 hours
     of wasted ToolRun time.
4. **Agents can't easily observe their own change running.**
   - `sase screenshot` relaunches whatever `sase` is on PATH. That is the primary
     checkout's editable install, not the agent's workspace.
   - It also runs against the real `~/.sase` state.
   - Managed projects have no app-boot or observability contract at all.
5. **The knowledge system is the right mechanism with the wrong payload.**
   - The always-loaded map is 283 lines, about 4.3k tokens. 57% of that is rosters.
   - About 1k tokens of duplicated home-level instructions come on top.
   - Docs total 54.9k lines with no agent-facing map.
   - Gardening covers docs only, and it runs from machine-local config.

The fixes follow SASE's own precedent. The `guarded-recipes` decision already did this
once: instruction-led compliance plateaued near 90%, so the rule was promoted into a
guard whose refusal prints the remedy. That move should be repeated wherever an
instruction, a machine-local routine, or a later cleanup agent stands in for an in-loop
check.

---

## 2. The Standard

Merged from the five reports and checked against the article text:

| # | Standard (paraphrased) |
|---|---|
| H1 | **Humans steer, agents execute.** Human time and attention is the only scarce resource. Humans work at the layer of intent, acceptance criteria and judgment. |
| H2 | **Failure means a missing capability.** Ask "what capability is missing, and how do we make it both legible and enforceable?" If documentation falls short, "promote the rule into code." |
| H3 | **A map, not a manual.** A roughly 100-line `AGENTS.md` serves as a table of contents into a structured `docs/` system of record, so context is disclosed progressively. |
| H4 | **The repo is the system of record.** What the agent can't access in context doesn't exist. Plans have progress and decision logs, and the repo holds design docs with verification status, an architecture map, a quality document grading each domain and layer, and a tech-debt record. |
| H5 | **Knowledge is verified mechanically.** Linters and CI check freshness, cross-links and structure, and a recurring doc-gardening agent opens fix-ups. |
| H6 | **Enforce invariants, not implementations.** Each domain has fixed layers (Types → Config → Repo → Service → Runtime → UI) with checked dependency directions, and cross-cutting concerns enter through Providers. Taste invariants cover structured logging, naming, file size and parsing at the boundary. Lint errors carry remediation text. |
| H7 | **The app is legible to the agent.** It boots per worktree, the agent drives the UI over CDP (DOM, screenshots, video), and a per-worktree ephemeral stack exposes logs, metrics and traces (LogQL/PromQL), so SLO-style prompts become checkable. |
| H8 | **Agents review agents.** Self-review plus extra agent reviewers, iterated "until all agent reviewers are satisfied." Human review is optional. |
| H9 | **Throughput changes the merge philosophy.** Few blocking gates, short-lived PRs, and flakes handled with follow-up runs. "Corrections are cheap, and waiting is expensive." The article says this "would be irresponsible in a low-throughput environment." |
| H10 | **End-to-end autonomy.** Reproduce, record video, fix, validate by driving the app, record again, open a PR, handle feedback, fix the build, escalate only for judgment, merge. |
| H11 | **Entropy needs garbage collection.** Golden principles live in the repo. Recurring agents scan for deviations, update quality grades, and open small refactors that can be automerged. |
| H12 | **Favor legible dependencies.** Prefer "boring," composable tech, and reimplement opaque upstream helpers in-repo when that is cheaper to reason about. |

**Context the reports agree on:**

- The article is one team's experience report on a greenfield product: about 1M lines,
  about 1,500 PRs over five months, 3 to 7 engineers, roughly 3.5 PRs per engineer per
  day, and single runs lasting 6+ hours.
- It says its autonomy results "should not be assumed to generalize."
- Two things should **not** be copied literally:
  - the "0 lines of manually-written code" constraint;
  - minimal gating without the cheap-correction machinery that makes it safe.
- The `__gem` report's "horse tack" metaphor and its "two levers: context and tools"
  framing do not appear in the article. Neither is used as a standard here.

For scale:

| | OpenAI team | SASE |
|---|---|---|
| Size | ~1M lines of code | 1.22M lines in `src/` (5,403 files) + 1.38M lines of tests |
| Output | ~1,500 PRs over 5 months | 15,493 commits since 2026-02-14; 1,897 in the last 30 days |
| People | 3 to 7 engineers | one human |
| Agent share | 100% by construction | 1,826 of the last 1,897 commits (96%) carry a `SASE_AGENT=` trailer |

SASE commits are smaller than OpenAI PRs, so these numbers are only indicative. The
order of magnitude still matters: a single human cannot review this volume, so the
article's agent-review and garbage-collection loops matter **more** for SASE than they
did for OpenAI.

---

## 3. Consolidated Scorecard

Grades: **A** meets or beats the article · **B** mostly there · **C** partial or
instruction-only · **D** largely absent. "Spread" shows where the researchers disagreed;
§7 records how each disagreement was resolved.

| # | Standard | Grade | Verdict | Spread |
|---|---|---|---|---|
| — | Isolated per-change environments | **A** | Numbered clones, atomic claims, alternates, rescue, per-launch tmp and Cargo targets. More productized than "boot per worktree." | Unanimous |
| H1 | Humans steer | **B** | Approval sits at the plan, launch and gate layer, not per commit. But red-master repair is routed to the human through notifications, and attention is never measured. | B+ to "strong" |
| H2 | Failure → capability | **B** | The reflex exists and is recorded (`guarded-recipes`). The default response to a struggle is still a bead or note, and inherited failures go unowned. | A to Partial |
| H3 | Map, not manual | **B−** | The mechanism is excellent: generated, drift-checked, audited reads. The payload is about 2.8× the target, and `docs/` has no map. | B to Behind |
| H4 | Repo as system of record | **B−** | Excellent decision records. Plans and beads live in sidecars, load-bearing routines live in machine-local config, and there are no quality grades or debt registry. | B− to strong |
| H5 | Knowledge verified and gardened | **C+** | Generated-file drift is checked, and a docs gardener runs (machine-local). Memory, nested `AGENTS.md` files and prose↔code truth are not gardened. | C+ to Partial |
| H6 | Enforce invariants | **C+** | Many bespoke checkers. The size gate is out of loop, there is no layering model, there is a known import cycle, the core boundary is prose, and F401/F821 are ignored. | Behind to "strong" |
| H7 | App legibility | **C+** | TUI capture tooling is strong. But it captures the wrong code for the agent's change, state is shared, perf floors run only in CI, and managed projects get nothing. | Gap to B+ |
| H8 | Agent-to-agent review | **D** | Nothing reviews the actual landing path: no mentor profiles, and mentors only run on Patches. | D to B− |
| H9 | Merge philosophy | **C+** | The design is aligned and rigorous: two-speed CI, triage that preserves exit codes. In operation, the gate is red about 96% of the time and corrections aren't cheap because nobody owns them. | "Conservative" to A− |
| H10 | End-to-end autonomy | **B−** | Epics run overnight through waves to a land agent. There is no repro or evidence capture, no review loop, and no build-failure remediation. | B to Partial |
| H11 | Garbage collection | **C+** | `toobig_split` and `refresh_docs` are real GC, but narrow and off-repo. There are no golden principles, no grades, and no pattern scans. | B− to gap |
| H12 | Legible dependencies | **B** | Boring Python/Textual stack, pinned Rust core. The cross-repo split costs legibility. | B to neutral |
| — | Feedback-loop trust and speed | **B−** | Trust is excellent: measured selection recall, triage, receipts. Speed is poor: p90 27 min, 185 ceiling kills a week. | "Strong" (cdx) |

---

## 4. Where SASE Already Meets or Beats the Article (Keep These)

1. **Decision records as falsifiable, compressed architecture.**
   - The `decisions` web has 24 immutable records, each with Claim / Why / Cost /
     Reopens when.
   - Supersession is marked with back-links instead of edits.
   - This goes past the article's "core beliefs" and design docs with verification
     status. It is the agent-legible "why" the article says otherwise lives in Slack.
2. **Generated, drift-checked instruction files.**
   - `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `QWEN.md` and `OPENCODE.md` are
     byte-identical renders of `sase/memory/`.
   - `sase validate` runs `init memory --check`, `init skills --check` and plan-link
     validation in both `just check` and CI.
   - The map cannot be hand-edited out of sync.
3. **Progressive disclosure with an audit trail.**
   - Reference notes and web strands are read on demand.
   - Every `sase memory read` records a reason.
   - `sase memory list` reports per-file token cost.
   - OpenAI has no data on which knowledge agents actually use. SASE does.
4. **Rules promoted into code once instructions plateau.**
   - `tools/require_tool_run` came from measuring roughly 90% instruction-led compliance.
   - Its refusal prints both the wrapped form and the bypass form.
   - This is H2 done with measurement first.
5. **Flake and failure handling that preserves signal.**
   - Triage labels failures NEW, KNOWN, FLAKY or UNKNOWN. KNOWN needs an independent
     witness, and triage never changes an exit code.
   - UNKNOWN is currently only about 4% of check failure groups, well under the
     decision's 40% reopen threshold.
   - Classification works. The gap (§5.1) is what happens *after* classification.
6. **A harness that measures itself.**
   - `fakey` is a deterministic fake provider with `@flaky`, `@crash`, `@hang` and
     `@capacity` scenarios.
   - `selection-backtest` and `selection-health` measure the scoped test lane. Depth-3
     closure recall is 99.2% mean and 100% at p10 over 63 replayed commits.
   - `sase tool stats` reports waste, repeats and duration-forecast calibration.
   - The article describes no equivalent instrumentation of the harness itself.
7. **Mechanical continuation.**
   - Under single-turn agents, monitors, gates and session members turn "six hours while
     humans sleep" into a chain of turns that survives crashes, releases runner slots
     during human waits, and records evidence.
   - It is more reliable than one long chat, though each hop costs context.
8. **Host-owned completion.**
   - Agents declare their work, and the host commits, so provenance and bead footers are
     reliable.
   - The article lets agents merge their own PRs. SASE's split is the better foundation
     for adding autonomy *above* it.

---

## 5. Gaps, in Priority Order

### 5.1 The landing path: no review, no gate, and no owner for a red master (H8, H9, H10)

**Evidence** (lead verification unless noted):

- **Landing.**
  - `vcs_create_commit` commits, rebases with `--autostash` onto `origin/master`, and
    pushes with retries (`src/sase/vcs_provider/plugins/_git_commit_dispatch.py`).
  - The last 30 days had 0 merge commits.
  - Recent GitHub PRs are all automated `chore(core-pin)` bumps.
  - `ci.yml` (the heavy matrix) runs only on PRs and on the 2-hourly `full.yml`
    schedule. Master pushes get the bounded `master-gate.yml`.
- **Review.**
  - There are no `mentor_profiles` in `sase/sase.yml`, the user config, or the machine
    config (`__cld`, re-verified).
  - Mentors only run on Patches in Ready or Mailed status (`docs/mentors.md`), and stitch
    landings are not Patches.
  - In practice, nothing reviews what lands on sase master.
- **Verification at landing.**
  - The ordinary `/sase_final` path records `unverified` as "nonblocking provenance, not
    a refusal" (`docs/monitors.md:371-373`).
  - Prepared completion commits only on a pass, but it is opt-in.
- **What that does to the shared gate.** ToolRun ledger, athena, last 7 days:

  | Metric | Value |
  |---|---|
  | `check` runs | 1,084 (31 OK, 829 FAIL, 222 censored) |
  | Settled pass rate | **3.6%** (31/860) |
  | Days with zero passing `check` runs | 09-27 (0/132), 09-29 (0/126) |
  | Failure signature groups | ≥1,000 (query cap). **0 have an owner.** |
  | Groups hit by ≥10 different agents | **123** |
  | Run-weighted item classes | KNOWN 3,411 · NEW 955 · UNKNOWN 228 · FLAKY 113 |

  Typical examples:

  - a `_lint-flags` failure hit 66 agents over 17.5 hours;
  - a terminology-audit failure hit 55 agents over 22 hours;
  - eight symvision findings hit 44 agents over 32 hours;
  - `test_kind_coverage` stayed KNOWN-red for 36 agents over 105 hours.
- **Detection without repair.** The machine-local `ci_watch` routine "never creates
  gates, launch requests, repair agents, or Axe proposals." It only notifies the human.

**Critique.**

- Two reports partly mischaracterize this gap.
  - `__gem` says the problem is that a human must review every Patch. On SASE's own repo
    it is the opposite: nothing reviews anything.
  - `__gem` also calls the merge philosophy "conservative." At landing, SASE is *more
    permissive* than OpenAI. OpenAI has few blocking gates **plus** an agent review loop.
    SASE has neither, and pays its ceremony earlier, in the declaration.
- The article's minimal-gate stance works because correction is cheap and fast: the
  agent fleet fixes what breaks.
- SASE built the classification half of that (triage, KNOWN witnesses) but not the
  correction half. The result is a tragedy of the commons:
  - dozens of agents each pay triage, scrolling and re-run cost on the same inherited
    failure;
  - nobody is assigned to remove it;
  - the gate's exit code stops carrying information for anyone.
- `__cld` predicted this from the `guarded-recipes` plateau ("if ~90% verify, ~60
  commits a week land unchecked"). The ledger confirms the downstream effect.

**What good looks like in SASE's terms.** Keep single-turn agents, host-owned completion,
and triage that never changes exit codes. Add a mechanical owner:

- when a failure signature is hit by N agents, or stays red for more than T hours,
  launch one bounded repair agent, or file an owned `ci` bead;
- refuse landings that add NEW or UNKNOWN failures;
- run a bounded agent review on risky diffs.

### 5.2 Invariants enforced after the fact or only in prose (H6, H11)

**Evidence:**

- **Size.**
  - The `Justfile` deliberately leaves `toobig` (limits 1000/850/700) out of `check` and
    `check-full` because "an agent can rarely act on it (the toobig_split routine owns
    those splits)."
  - The hourly `toobig_split` routine is machine-local.
  - **341 of 1,897 commits in the last 30 days (18%) are toobig split agents.** They
    account for roughly 265k of the 1.22M inserted lines and 233k of the 423k deleted
    lines in that window (approximate `--shortstat` totals).
  - The approach works: the largest `src/` file is 739 lines.
- **Layering.**
  - `src/sase` has 1.22M lines, and `ace` alone has 517k lines across 2,182 files.
  - There is no import-linter, tach, or banned-import config. Ruff selects only E, W, F,
    B, C4, TC004 and UP.
  - Boundaries are about 10 bespoke AST import-scanning tests, each guarding one edge
    (for example `tests/test_agent_monitor_import_boundary.py`).
  - `docs/development.md:82` concedes "a large import cycle in `src/sase`." That cycle is
    why test selection has to be depth-bounded.
  - `docs/architecture.md` has a System Boundary table but no dependency directions.
- **The core boundary** is in always-loaded prose (`rust_core_backend_boundary`). The
  only mechanical check is that bindings exist. Nothing detects Python reimplementing
  core logic.
- **Cheap holes.**
  - Ruff ignores `F401` and `F821` (undefined name) globally.
  - mypy checks only `src`, so 1.38M lines of tests have no undefined-name check short of
    running them.
  - Remediation text in error messages is uneven. `tools/check_test_wait_helpers` and
    the symvision memory give fixes. The pyscripts checker and most flag rules state only
    the violation (`__cld`).

**Critique.**

- The article puts taste invariants in the **authoring** agent's lint loop, with
  remediation text, so the violation never lands.
- SASE lets every agent land oversized files and then spends about one commit in six
  splitting them. Each split costs:
  - a full agent run;
  - a `just check`;
  - a rebase against a fast-moving master;
  - a context-cold agent guessing at module seams the original author already knew.
- "An agent can rarely act on it" is true of a whole-repo gate. It is not true of a
  **diff-aware ratchet** that fails only when *this diff* pushes a file over a limit.
- One-edge-at-a-time AST tests enforce architecture only where it has already broken.
  The article warns that agents copy whatever patterns exist. Without declared layering
  in a 517k-line package, the pattern is whatever the last few hundred agents wrote.

**Resolution.** `__mus` rated invariants and layering "strong" because of the Rust
boundary. That overstates it: the boundary is real, but it is enforced by instruction,
not by checks.

### 5.3 The inner loop is trustworthy but slow (H9, H10)

**Evidence** (ToolRun ledger, last 7 days):

- `check`: p50 3m47s, **p90 27m03s**.
- The scoped test stage: p50 17m04s, **p90 39m46s**. Of its 281 runs, 30 were OK, 144
  failed and 107 were incomplete.
- **185 inline runs were killed at the provider ceiling** (27.7h), and 66 of those were
  re-run within 30 minutes.
- 156 runs were exact repeats (41.3h).
- **52.5 hours** of waste in total.
- The duration forecast backtest misses its own target: 74% of runs land inside p10–p90,
  against ≥80%.
- `lint_and_test.md` already warns that `check` "exceeded 10 minutes in about 19% of
  Muse runs."

**Critique.**

- `__gem` claimed single-turn agents prevent a quick fix-and-retry loop. That's wrong:
  agents iterate freely inside a turn.
- The real friction is that the verification inner loop has a tail longer than provider
  synchronous limits, so agents get killed mid-check, re-run, or hand off to monitors.
- Part of the cause is the master-red problem in §5.1. Part is the import cycle in §5.2,
  which forces bounded but large selections.
- The article's "ensure startup under 800 ms" style of loop needs minutes, not
  tens of minutes.

### 5.4 Agents can't easily observe their own change running (H7, H10)

**Strong:**

- `sase screenshot` takes ordered `-p/-T/-w` scripts and exports SVG to PNG over
  SIGUSR2.
- `--keep` supports iterative driving.
- About 900 tracked pixel-exact PNG goldens with HTML diff reports.
- `AcePage` Pilot `state()` is the closest analogue to a DOM snapshot.
- Repro bundles and perf floors exist.

**Weak** (lead-verified unless noted):

- **Wrong code.**
  - `_build_tui_relaunch_cmd` relaunches `sys.executable -m sase tui`
    (`src/sase/screenshot/local.py`).
  - The `sase` on PATH is a uv tool whose `sase` package is an **editable install of the
    primary checkout**, not the agent's numbered workspace.
  - So a bare `sase screenshot` shows master-ish code rather than the agent's diff,
    unless the agent deliberately uses the workspace venv.
  - The `tui_screenshot` memory warns about this only for `--host` remote captures.
  - `__cld` found this. The lead refined it: it is the primary checkout, not a
    "release."
- **Shared state.** Captures run against the real `~/.sase`, with "real timestamps,
  running procs, and host state." `SASE_HOME` isolation exists, but only per tool
  (pytest workers, smoke harnesses, the demo seeder). Agents have no general recipe.
- **Shared observability.** Telemetry goes to `metrics.sqlite` under the effective SASE
  home, and TUI traces to `~/.sase/perf/`. Parallel workspaces mix their signals, and
  queries are `jq` recipes in a human runbook.
- **Out-of-loop UI signal.** `just check` runs no visual snapshots and no perf floors.
  Those run only in CI or through explicit `fix-tui-screenshots`.
- **No evidence on completion.** `done.json` already supports `image_paths` and
  `video_paths`, but nothing produces before/after media.
- **Managed projects** (`__cdx`, `__grk`):
  - SASE guarantees a code workspace, not a runnable app;
  - there is no contract for booting a stack per workspace, allocating ports, data and
    credentials, waiting for readiness, driving a browser, querying logs, metrics and
    traces, or capturing journeys;
  - for SASE's product claim, this is the biggest strategic gap: other people's web apps
    need exactly the article's CDP and observability investment.

### 5.5 The always-loaded map is the right mechanism with the wrong payload (H3)

**Evidence** (`sase memory list`):

| Item | Size | Share of AGENTS.md |
|---|---|---|
| Generated `AGENTS.md` | 283 lines, 17,285 bytes, ~4,316 tokens | — |
| Decisions roster (24 entries, superseded ones included) | ~1,651 tokens | ~38% |
| Glossary term roster | ~518 tokens | ~12% |
| Task-type catalog | ~310 tokens | ~7% |
| Home `~/CLAUDE.md` (duplicates the SASE Memory, Repositories and Final Declaration sections) | ~966 tokens | — |
| **Total loaded** | **357 lines, ~5.3k tokens** | — |

- The three rosters together are about 57% of `AGENTS.md`.
- `AGENTS.md` points into `docs/` exactly once (`docs/rust_backend.md`).
- `docs/*.md` totals 54,903 lines: `ace.md` 9,159, `configuration.md` 7,545,
  `xprompt.md` 3,796.
- `docs/index.md` is a landing page, not an agent map.

**Corrections to individual reports:**

- `__gem` said `AGENTS.md` is 330 lines and burns "tens of thousands of tokens." It is
  283 lines and about 4.3k tokens.
- The byte-identical provider shims are not a per-turn cost, since each provider reads
  only its own file. The real duplication is the home-level file stacked on the project
  file.
- `__gem` recommended converting core memory to reference memory. That is the wrong
  cut. Core is about 100 lines and carries the safety rules: the repo rule, final
  declaration, and the core boundary. Rosters are the bulk, and they are what should
  move.
- The 7 MUST/IMPORTANT/CRITICAL markers across 283 lines are admirably low-noise
  (`__cld`). Nested hand-written files are not: `src/sase/ace/AGENTS.md` alone has four
  CRITICAL headers.

### 5.6 Knowledge freshness and code GC are narrow and partly off-repo (H4, H5, H11)

**Evidence:**

- **Docs gardening exists and is active.** `refresh_docs` runs every 3 hours once there
  have been 100 commits since the last run. It launches update and then polish agents.
  The last 30 days show "docs: refresh / correct refreshed guides" commits on many days.
  - This corrects `__mus`, who said there is no gardener.
  - It also corrects `__cdx`, who called it "not configured." It is configured, just in
    the machine-local `sase_athena.yml`.
- **Load-bearing harness routines are off-repo.** `toobig_split`, `refresh_docs` and
  `ci_watch` live in the machine-local `~/.config/sase/sase_athena.yml`.
  - `lint_and_test.md` tells agents that `toobig_split` "owns" splits, but no agent in
    the repo can read the rule.
  - This directly conflicts with H4's "anything it can't access in-context doesn't
    exist."
- **Nothing gardens memory or nested `AGENTS.md` files.** Examples:
  - `src/sase/ace/AGENTS.md` sends agents to `home/dot_config/nvim/syntax/saseproject.vim`,
    a chezmoi-repo path that is unreachable without `/sase_repo`;
  - `docs/memory.md:206` documents that a help string "is stale" instead of fixing it.

  Memory edits are human-gated through `memory` beads by design, so automation should
  file beads rather than edit notes.
- **Code GC is file size only.** The hourly `housekeeping` routine is operational
  (temp files, notifications, disk, stale claims). Nothing scans for:
  - duplicated helpers;
  - Python reimplementations of core logic;
  - unvalidated external JSON;
  - obsolete compatibility paths and vocabulary.
- **No quality grades, golden-principles file, or debt registry.** Debt is scattered
  across task beads, flag beads, symvision whitelists and the flake baseline.

### 5.7 Plans are launchable, not living (H4)

**Consensus of `__cld` and `__grk`:**

- Tales and epics are schema-validated, approved through gates, sized, wired to
  dependencies, and launchable. That is stronger *operationally* than a markdown
  ExecPlan.
- But they are frozen at approval. They have no Progress, Surprises, Decision Log or
  Outcomes/Retrospective sections, and learning is scattered across bead notes.

**Critique.**

- Under single-turn agents, every successor turn re-derives context. A living plan is
  the cheapest way to make a chain of turns behave like one long run.
- The epic land agent is also the natural place to record "what capability was missing,"
  which is the article's failure protocol.

### 5.8 SASE measures activity, not leverage (H1)

**What exists.**

- The Admin Center and `sase tool stats` report runs, success, commits, wall time,
  provider usage, waste and pressure.

**What's missing** (`__cdx`, `__cld`, `__grk`):

- gates answered per day and median human response latency;
- human minutes per landed change;
- rework and revert rate (30-day baseline: 436 `fix:` against 832 `feat:` commits, and 5
  reverts);
- red-master hours;
- agent-hours lost to inherited failures;
- recurrence of the same failure signature after a harness fix.

**Why it matters.**

- Without these, nobody can tell whether a new gate, loop or noun pays for itself.
- SASE's own decision records already demand "Reopens when" evidence. These metrics are
  that evidence for the harness itself.

---

## 6. Divergences to Keep

- **Don't adopt "zero manually-written code."** It was an experimental forcing function.
  Humans should keep goals, gates that need judgment, and taste encoding. Measure
  success as human minutes per landed change and repeat-failure rate, not as the share
  of the diff written by agents.
- **Don't abandon single-turn agents.** Make chains cheaper instead: living plans, a
  thinner map, faster checks, and auto-continuation of epic phases. The chain *becomes*
  the six-hour run without turning into an unkillable chat.
- **Don't let agents raw-merge.** Autonomy should mean "the host completes because the
  evidence is sufficient." Prepared completion already sketches this.
- **Keep triage exit-code integrity.** The fix for master-red is ownership and repair,
  not relabeling.
- **Don't read "minimal blocking gates" as "no gates."** The article's safety comes from
  cheap correction plus agent review. Until SASE has both, a narrow landing guard
  (refuse NEW or UNKNOWN only) is the right translation, not the absence of one.

---

## 7. Disagreements Between Reports and How They Were Resolved

| Claim | Source | Verdict | Evidence |
|---|---|---|---|
| `AGENTS.md` is ~330 lines and costs "tens of thousands" of tokens | `__gem` | **Wrong** | 283 lines, ~4.3k tokens; ~5.3k with the home file |
| A human bottleneck on every Patch caps throughput | `__gem` | **Wrong for sase's own repo** | Stitches go direct to master; no mentor profiles exist. The gap is *no* review |
| Single-turn agents prevent quick fix loops | `__gem` | **Wrong** | Agents iterate within a turn. The real friction is `check`'s 27–40 min tail and provider-ceiling kills |
| Receipts make SASE's merge philosophy conservative | `__gem` | **Wrong** | Receipts apply only to the opt-in no-new path; the ordinary path is `unverified`, nonblocking |
| Convert core memory to reference | `__gem` | **Rejected** | Core is ~100 lines of safety rules; rosters are ~57% of the file |
| Invariants and layering are "strong" | `__mus` | **Overstated** | No layering model, known import cycle, prose-only core boundary, size gate out of loop |
| There is no recurring doc-gardening agent | `__mus` | **Wrong** | `refresh_docs` is active (machine-local) |
| `refresh_docs` is not configured | `__cdx` | **Partly right** | Not in the repo's `sase/sase.yml`; configured in machine-local config |
| PR CI is too heavy for throughput | `__cdx` | **Mostly moot** | Feature work never goes through PRs. The heavy matrix runs on a 2-hourly schedule |
| Feedback loops are "fast" | `__cdx` | **Half right** | Trustworthy (99.2% recall) but slow (p90 27 min, 52.5 h weekly waste) |
| `sase screenshot` shows the "installed release" | `__cld` | **Refined** | It shows the primary checkout's editable install, still not the agent's workspace |
| ~38 bespoke AST boundary tests | `__cld` | **Count not reproduced** | About 10 test files scan imports with `ast`; the qualitative point stands |
| Visual snapshots are excluded from `just check` | `__grk` | **Confirmed** | Justfile and `lint_and_test.md` |
| 18% of commits are toobig splits | `__cld` | **Confirmed** | 341/1,897 |

---

## 8. Actionable Takeaways

The takeaways are ordered by leverage. Each one names a first step and a metric that
would show it worked.

### Tier 0: make master green, and keep it green (do first)

1. **Add a red-master andon: give every widely-hit failure an owner.**
   - Extend triage or `ci_watch` so that a failure signature hit by ≥3 distinct agents,
     or red for more than 2 hours, gets exactly one owner:
     - a bounded repair agent (`%auto`, with a capped attempt count), escalating through
       a gate if it fails; or
     - at minimum, an owned `ci` bead linked to the signature and the introducing SHA.
   - Populate the empty OWNER column in `sase tool failures`.
   - This reopens `ci_watch`'s "never launches repair agents" choice deliberately, with
     the ledger numbers in §5.1 as the evidence.
   - **Metrics:**
     - maximum age of a KNOWN signature: under 4h, down from 105h;
     - agents per signature: under 5, down from 66;
     - `check` settled pass rate: above 60%, up from 3.6%.
2. **Guard landing against *new* breakage only (the `guarded-recipes` precedent).**
   - First, report the verified-landing rate: the share of commits whose finalizer saw a
     covering receipt rather than `unverified`.
   - Then make the commit finalizer refuse a landing when the agent's latest covering
     `check` has NEW or UNKNOWN items, unless a declared skip reason is given (for
     example, docs-only).
   - KNOWN and FLAKY items still pass, which keeps the article's low-gate spirit.
   - Together with item 1, this stops the commons from re-reddening.
   - Then replace `lint_and_test.md`'s paragraph listing what is "not explicit
     instruction" for `check-full` with a guard, for example an
     `SASE_CHECK_FULL_AUTHORIZED=<ref>` check.
3. **Put `toobig` back in the loop as a diff-aware ratchet.**
   - Add a `just check` stage that fails only when this diff pushes a file past 850 or
     1,000 lines, or adds a new file over 700.
   - The message should point at the `split_file` seam conventions (facades, no
     `_private` re-exports).
   - Keep `toobig_split` for the legacy backlog.
   - **Metric:** split-agent commits fall from 18% of commits to under 5%.

### Tier 1: close the compounding loops

4. **Add a bounded agent review loop for risky landings.**
   - Check in mentor profiles, or a review finalizer stage, for sase itself. Trigger on
     the exact landing diff for epic phases, diffs over about 200 lines, and
     core-boundary or finalizer paths.
   - Pipe error-severity findings to a fix agent, capped at 2 rounds. Escalate whatever
     is left through a gate.
   - If pre-land latency is unacceptable, run it post-land and file `bug` beads tagged
     with the SHA. That is the article's "corrections are cheap" variant.
   - Allow suggestion-level comments to auto-apply on opt-in profiles (`__grk`).
   - **Metrics:** 7-day rework on the same files, and the revert rate.
5. **Declare the architecture, and check it.**
   - Adopt import-linter or tach, or fold the roughly 10 AST boundary tests into one
     declarative contract file. Start with:
     - the core boundary (Python modules on a list may not reimplement core domains);
     - a layer order inside `ace` (model → state → actions → widgets → app);
     - the `agent`, `monitor` and `finalizers` edges.
   - Generate the dependency section of `docs/architecture.md` from the contract.
   - Every violation names the allowed edge and where the shared helper belongs.
   - Put breaking the `src/sase` import cycle on the scorecard. That makes unbounded test
     selection sound and shrinks the §5.3 tail.
6. **Shorten the inner loop's tail.**
   - Target `check` p90 under 10 minutes and zero ceiling kills.
   - Use what the ledger already shows:
     - route the scoped test lane through a monitor by default when its forecast exceeds
       the provider ceiling;
     - stop exact repeats after a censored run;
     - attack the slowest stages: scoped tests, symvision at p90 2m49s, and feature flags
       at 1m25s.
   - Items 1, 2 and 5 do most of this indirectly.
7. **Shrink the always-loaded map to about 2k tokens, and budget it.**
   - Replace the decisions roster with titles of non-superseded records only, or a
     one-line pointer.
   - Replace the glossary roster with a pointer plus the 10 most-read terms, taken from
     `memory_reads` data.
   - Make the task-type catalog a pointer.
   - Remove the duplicated SASE sections from home-level files, or let `sase memory init`
     own them.
   - Add a 10-line "where to look in `docs/`" block.
   - Add a line and token budget to `init memory --check`, so growth fails the same way
     drift does.

### Tier 2: legibility and system-of-record hygiene

8. **Ship a workspace sandbox for SASE itself.**
   - Add `sase dev up|down`, or `just sandbox`, that:
     - seeds a throwaway `SASE_HOME`/`SASE_TMPDIR`, reusing
       `demos/scripts/seed_sase_ace_demo`;
     - runs **this workspace's** venv;
     - namespaces tmux, telemetry and trace paths per workspace;
     - tears everything down afterwards.
   - Make `sase screenshot` warn or refuse when the code it would relaunch is not the
     calling workspace's.
   - Add a `run` project skill and a `sandbox` catalog tool.
   - For diffs under `src/sase/ace/**`, ask the finalizer for before and after sandboxed
     captures through `done.json.image_paths`.
9. **Move project-scoped harness routines into the repo.**
   - Check the sase-specific parts of `toobig_split`, `refresh_docs` and `ci_watch` into
     `sase/sase.yml` (or `sase/routines.yml`).
   - Leave only capacity knobs in machine config.
   - Agents can then read the rule that "owns" an invariant, and other machines get the
     same GC.
10. **Garden memory and nested `AGENTS.md` mechanically.**
    - Add `sase memory lint` to `sase validate`. It should verify that every backticked
      repo path, `just` recipe, `sase` subcommand or flag, and `[[link]]` in memory notes
      and nested `AGENTS.md` files resolves.
    - Add a weekly `memory_audit` routine that runs the lint plus an LLM truth check and
      files `memory` beads. Edits stay human-gated.
    - The first catches are already known: the `saseproject.vim` path and
      `docs/memory.md:206`.
11. **Make epics living execution plans.**
    - Allow `Progress`, `Surprises`, `Decision Log` and `Outcomes` sections.
    - Phase workers append one line each.
    - The land agent writes the retrospective, including a required "missing capability"
      line: what agents could not see or enforce, and whether a lint, skill or doc was
      added.
12. **Close the cheap lint holes.**
    - Enable `F821` at least for `tests/`, with per-file ignores.
    - Consider `F401` with re-export allowlists.
    - Add remediation text to every report-only checker.
    - Choose one structured-logging convention and lint `print(` outside CLI-output
      modules. Logs only become agent-queryable once they are structured.

### Tier 3: compounding quality, and exporting the harness

13. **Write a ≤30-line golden-principles file with an enforcement column.**
    - Sources: `gotchas`, the `ace/AGENTS.md` CRITICALs, `split_file`, the test-wait
      rule, the core boundary, and parse-at-the-boundary.
    - Each row names its enforcing check, or says UNENFORCED.
    - UNENFORCED rows become the lint backlog. The file can replace scattered core prose.
14. **Generate a per-package quality scorecard (`docs/quality.md`).**
    - Grade each package from signals SASE already collects:
      - size and growth;
      - fix-commit share;
      - failure signatures and their age;
      - flake-baseline entries;
      - test-cost overruns;
      - symvision whitelists;
      - docs-refresh corrections.
    - Point GC routines at the lowest grades instead of only at file size.
15. **Track human attention and harness leverage.** Write a weekly report covering:
    - gates raised and answered, and median latency;
    - approvals per landed commit;
    - red-master hours;
    - agent-hours lost to inherited failures;
    - verified-landing rate;
    - rework and revert rate.

    Treat each new gate, loop or noun as an experiment with a stated target (`__cdx`).
16. **Define an application-harness contract for managed projects.**
    - Add a small manifest such as `sase/harness.yml` with capabilities: `bootstrap`,
      `start`, `ready`, `stop`, `ui`, `logs`, `metrics`, `traces`, `capture`.
    - Namespace ports, data and credentials per workspace, and expose endpoints in launch
      metadata.
    - Bundle a CDP/Playwright skill pack for web projects.
    - This is how SASE *exports* harness engineering instead of only orchestrating CLIs.
17. **Add `sase init harness` for other repos.**
    - It generates a ~100-line `AGENTS.md` map, an `ARCHITECTURE.md` stub, a
      `PLANS.md`/ExecPlan pointer, a `QUALITY_SCORE.md`, and a `just check` hook.
    - `sase memory init` is the insertion point (`__grk`).

### If you do only three things

1. **Items 1 and 2: make master green and keep it green.** Add an owner for every
   widely-hit failure signature, plus a landing guard that refuses only *new* breakage.
   This turns about 50 wasted agent-hours a week and a 3.6% gate pass rate back into a
   signal.
2. **Items 3 and 5: move invariants into the authoring loop.** That means a diff-aware
   size ratchet plus declared, checked layering. This removes roughly one commit in six
   of cleanup churn and stops agents copying drift into a 517k-line package.
3. **Item 4: add a bounded agent review loop on risky landings.** One human cannot
   review 1,900 commits a month. The article's answer is agents reviewing agents, and
   SASE already has the mentor JSON, gates and finalizers to build it.

The cheap wins to do alongside these are item 7 (shrink the map) and item 9 (move
routines on-repo).

---

## 9. Evidence Notes and Caveats

- **ToolRun figures** come from `sase tool stats -t check` and `sase tool failures -t
  check -j` on athena for the 7 days ending 2026-10-01. The ledger is machine-local, so
  apollo runs are excluded.
  - FAIL includes runs whose only failures were inherited KNOWN items, because triage
    never changes exit codes.
  - "Censored" means the run is incomplete.
  - The failure-group query was capped at 1,000 groups.
- **Git figures** come from `git log --since='30 days ago'` at `ebf070e16a`.
  - Toobig commits are those with a `SASE_AGENT=` trailer containing `toobig`.
  - Line churn is an approximate `--shortstat` sum.
  - Commits are not PRs.
- **Memory token counts** come from `sase memory list`, which gives approximate
  per-file tokens.
- **Lead-verified directly:**
  - the ruff and mypy config;
  - the Justfile `check` and `check-full` stages and the toobig comment;
  - CI workflow triggers;
  - the landing rebase/push code;
  - the `unverified` doc text;
  - the absence of mentor profiles in all three config layers;
  - the routine definitions in machine config;
  - the screenshot relaunch path and the PATH install source;
  - the import-cycle note;
  - the nested `AGENTS.md` and `docs/memory.md` drift examples;
  - selection-recall figures;
  - the PR list.
- **Not re-verified:** each decision record's historical claims; individual checker
  messages beyond `__cld`'s examples; whether `__gem`'s "permissive data boundaries"
  claim holds broadly. That claim was left out of the findings for lack of evidence,
  though parse-at-the-boundary stays a recommended golden principle.
- The article is a single-team greenfield report. Its observability stack, CDP wiring
  and six-hour runs describe one repository's investment, not a universal bar.
