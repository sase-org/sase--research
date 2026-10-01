# SASE vs. OpenAI's "Harness Engineering" — a critique

Researcher: mus (`__mus`) — independent swarm report; no peer reports consulted.
Date: 2026-10-01. Source: Ryan Lopopolo, "Harness engineering: leveraging Codex
in an agent-first world" (OpenAI, 2026-02-11),
<https://openai.com/index/harness-engineering/>.
Subject: SASE (Structured Agentic Software Engineering), this repo
(`AGENTS.md`, `Justfile`, `docs/`, `sase/memory/`, `src/sase/`,
`sase-core-revision.txt`).

Method: full read of the source article; repo inspection via directory listings,
`AGENTS.md` header, `Justfile` `check`/`check-full` recipes, `sase/memory/`
catalog, and targeted greps. I did not run the test suite and did not read
every memory strand — claims drawn from listings rather than deep reads are
marked below.

Context caveat: the article reports one team's greenfield experiment (empty repo
→ ~1M lines, ~1,500 PRs, 3→7 engineers, 0 manually-written lines, ~10x
speedup). SASE is a different animal: a brownfield orchestrator/harness that
drives many providers, many repos, and human operators — not a product built
under a no-hand-code constraint. Some standards transfer directly; some need
translation. I note where the article's advice should not be copied literally.

## 1. What the article actually claims

Distilled to testable theses:

1. **Humans steer, agents execute.** The scarce resource is human time/attention;
   engineer work moves to systems, scaffolding, leverage.
2. **Depth-first enabling.** When the agent fails, never "try harder" — ask what
   capability is missing and make it legible *and enforceable*.
3. **Application legibility.** Per-worktree bootable app, agent-drivable UI
   (CDP/DOM/screenshots), ephemeral per-task observability (LogQL/PromQL).
   Single runs work 6+ hours.
4. **Map, not manual.** One big `AGENTS.md` fails (crowds out context,
   non-guidance, rots, unverifiable). Keep ~100-line TOC; knowledge lives in a
   structured `docs/` system of record; progressive disclosure; mechanical
   enforcement (linters, doc-gardening agents).
5. **Agent legibility is the goal.** In-context or it doesn't exist. Prefer
   boring, composable deps; reimplement small opaque helpers in-repo.
6. **Invariants, not micromanagement.** Rigid layering + dependency-direction
   rules enforced by custom linters whose error messages inject remediation;
   freedom inside boundaries; centralize boundaries, allow local autonomy.
7. **Throughput changes merging.** Minimal blocking gates, short-lived PRs,
   flakes fixed by follow-up rather than blocking.
8. **Agent-generated means everything**: code, tests, CI, tools, docs, eval
   harnesses, review comments, dashboards.
9. **End-to-end autonomy loop.** One prompt → validate, repro, video, fix,
   re-validate, PR, feedback, merge; escalate only on judgment calls.
10. **Entropy/GC.** Agents replicate uneven patterns; Friday-cleanup doesn't
    scale. Golden principles + recurring background cleanup PRs, mostly
    automergeable; pay tech debt continuously.
11. **Discipline moves to scaffolding.** The article is explicit that
    long-horizon coherence is still unproven.

## 2. Scorecard: SASE against each thesis

Ratings: strong (meets/exceeds) · partial · gap.

| # | Thesis | SASE verdict | Evidence |
|---|--------|--------------|----------|
| 1 | Attention is scarce | **strong** | Whole architecture optimizes operator attention: TUI, monitors, notification gates, triage-that-annotates, host-owned completion |
| 2 | Depth-first enabling | **strong** | `gotchas.md`, memory-write skill gating, task beads for discovered follow-ups, adapter/normalize-harness decision |
| 4a | Progressive disclosure | **strong (design), gap (entry point)** | `sase/memory/` core/reference/webs split is exactly the article's model — but `AGENTS.md` is 283 lines (~3x the article's ~100-line budget) and inlines the full catalog |
| 4b | System of record + plans as artifacts | **strong** | `docs/` (51 files), beads as exec-plans analogue, `validate-committed-plans` in `just check` |
| 4c | Mechanical enforcement + gardening | **strong on lint, gap on gardening** | `just check`: ruff, mypy, symvision, flags, terminology, keep-sorted, changelog; no recurring doc-gardening agent or quality-grade doc found |
| 6 | Invariants + layering | **strong** | Rust core boundary (`rust_core_backend_boundary`, `sase-core-revision.txt` pin, `probe_core_floor`), symvision, boundary litmus test |
| 7 | Merge philosophy / two-speed gates | **strong** | `check-full-is-explicit`, two-speed CI, `just check` vs `just check-full`, flake baselines, triage-never-changes-exit-codes |
| 8 | Everything agent-generated incl. evals | **partial** | Generated skills from templates, demo tapes, test-cost budgets; no named agent-quality eval harness found |
| 3 | App legibility (boot/drive/observe) | **gap** | Visual-test/screenshot infra + workspace providers exist for humans; no agent-callable drive-the-TUI loop, no agent query surface over logs/metrics |
| 9 | End-to-end autonomy loop | **partial (by design)** | Monitors + follow-ups + host completion approximate it; single-turn-agents decision deliberately differs from 6-hour runs — same effect, different architecture |
| 10 | Entropy GC | **gap** | No golden-principles doc or recurring cleanup tasks found |
| 5 | Boring deps, reimplement small | **neutral** | Pinned renderer stack for PNG determinism is in the spirit; dependency-legibility audit never done explicitly |

Two honest disagreements with the article, not just gaps:

- **SASE optimizes for human-operator legibility first (TUI, tabs, screenshots),
  the article for agent legibility.** Both are needed in a harness, and SASE is
  right to invest in the operator side — but the imbalance is real: there is
  more machinery for *watching* agents than for agents to *inspect, drive, and
  verify* the system themselves.
- **The article's "minimal blocking gates" must not be read as "thin
  `just check`."** SASE's two-speed answer (fast default `check`, explicit-only
  `check-full`, scheduled exhaustive CI) is the correct translation of that
  thesis to a brownfield harness. Copying minimal-gating literally would drop
  the boundary enforcement that thesis 6 depends on.

## 3. Where SASE already goes beyond the article

- Multi-provider orchestration with host-owned completion and single-turn
  discipline (decisions: `single-turn-agents`, `host-owned-completion`,
  `explicit-handoff-fails-closed`).
- Memory webs with authorship protocol (`memory-links-are-authored`) — a more
  worked-out version of "repo knowledge as system of record" than the article's
  `docs/` sketch.
- Shared-backend-in-Rust with no Python fallback (`rust-core-required`) — a
  harder, more durable form of "enforce invariants."
- Custom static analysis with agent-facing purpose (symvision) plus terminology
  and test-wait linters — the article's "error messages inject remediation"
  idea, already institutionalized (message quality itself unaudited — see T6).

## 4. Actionable takeaways

Ordered by leverage-per-effort as I judge it. T1–T3 are the highest value.

- **T1. Put `AGENTS.md` on a diet; enforce the budget mechanically.** Target the
  article's ~100-line TOC: move the reference-memory catalog and web/strand
  listings out of the always-inlined hot path (they're already
  on-demand-readable; they don't need to be always-present). Add a line-count /
  shape check to `just check` so the entry point can't silently regrow. This is
  the single closest-to-literal finding from the article (SASE at 283 lines is
  living the "1,000-page manual" failure mode it already warns against).
- **T2. Start doc gardening.** A recurring (monitor-scheduled, not Friday)
  task that diffs reference memory + `docs/` against code behavior and opens
  fix-up patches; record freshness/ownership metadata on reference notes. Close
  the loop the article insists on: knowledge base with verification status.
- **T3. Write down golden principles and GC them.** One short opinionated doc
  (shared-utils-over-helpers, validate-at-boundaries, no guessed shapes —
  SASE's equivalents of the article's examples), plus background cleanup tasks
  whose mechanical output can automerge. Pay continuously, not on Fridays.
- **T4. Give agents a legibility loop over the TUI, not just screenshots for
  humans.** The visual-test/screenshot infra is the seed: wrap "boot it, drive
  it, assert on it" as an agent-callable skill with a structured log/query
  surface, so a monitor-driven agent can reproduce → fix → re-validate the way
  the article's CDP/observability loop does. This is the biggest capability gap
  (thesis 3) and squarely thesis-2-shaped: a missing capability, not a harder
  prompt.
- **T5. Add evals for harness changes.** Test-cost budgets and flake baselines
  cover code; nothing named covers *agent-affecting* changes (flags, xprompts,
  memory edits, default config). A small quality-regression harness —
  SASE's `QUALITY_SCORE` analogue — would make taste encodable and catch drift
  the way the article's per-domain grades do.
- **T6. Audit linter messages as agent instructions.** Sample symvision, flags,
  and terminology diagnostics and grade them the way you'd grade a prompt: does
  each failure tell the agent exactly how to fix it? Promote the article's
  throwaway line into a lint on lints.
- **T7. Defend two-speed verification with a metric.** Track `just check`
  wall-time and gate-failure rate; keep the agent default fast by explicit
  policy (already the doctrine — make drift visible). Resist both
  check-bloat and literal minimal-gating.
- **T8. Keep single-turn + mechanical continuation, but name the long-loop
  story.** The article's 6-hour runs are SASE's monitor/follow-up chains. Make
  sure one documented path exists for "agent works a task for hours while the
  human sleeps" and that its observability (claims, delivery, diagnostics under
  `src/sase/monitor/`) is itself agent-legible, not just TUI-legible.

## 5. What would reopen or weaken this critique

- I did not verify: symvision message quality (T6 assumes unaudited), absence
  of gardening/eval-harness code (grep-level absence, could live in the linked
  `sase-core` repo or under other names), or actual `AGENTS.md` token cost in
  provider shims.
- The article is a single-team greenfield report and says its autonomy results
  "should not be assumed to generalize"; SASE's orchestrator context differs
  enough that theses 3 and 9 needed translation, and a second researcher
  working from the `sase-core` side may see boundary enforcement differently.
