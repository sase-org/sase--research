# Agent instruction files at <=100 lines: research and recommendation

Researcher: mus. Date: 2026-10-02. Scope: the SASE project's own agent
instruction files (`AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `OPENCODE.md` /
`QWEN.md`) and the `sase/memory/` progressive-disclosure system behind them.

## 1. Current state (measured, not estimated)

- `AGENTS.md` is **283 lines, 17,285 bytes, ~4.3k tokens** (chars/4). The other
  four provider files are byte-identical copies (regular files, not symlinks).
- All five are **generated** by the AMD pipeline in `src/sase/amd/` (templates in
  `src/sase/amd/templates/`: `AGENTS.template.md` plus an existing
  `AGENTS.minimal.template.md`). Edits go to `sase/memory/*.md` sources, not to
  the rendered files.
- Section line budget of the current 283 lines (via `awk` section ranges):
  - Section 1 (Core, inlined): **~104 lines**.
  - Section 2 (Reference index): **~34 lines**.
  - Section 3 (Memory webs): **~145 lines**.
- What is actually inlined as core is only three notes: `sase.md` (the
  dominant one: memory-system explainer + workspace-dirs + repos policy +
  final declaration), `gotchas.md` (~6 lines), and
  `rust_core_backend_boundary.md` (~16 lines). Correction to a plausible
  misreading of the request: `xprompts.md` (166 lines) is already
  `type: reference`, **not** inlined.
- The single biggest line blocks in the rendered file are:
  1. Decisions roster: **24 decision summaries, ~90 lines** (section 3.1).
  2. Repos/cross-repo-read policy (`sase.md` section 1.1.3): **~33 lines**.
  3. Glossary term enumeration (section 3.2): **~18 lines**.
  4. Memory-system explainer + reference/web intros: **~25 lines** of mechanism
     description repeated in slightly different words in sections 1, 2, 3.
- The disclosure mechanism itself works: `sase memory read <selector> -r
  "<reason>"` resolves flat notes, bare webs, and `web:keyword` strands, strips
  frontmatter, and appends **one auditable log row per read** (there are
  dedicated tests: `test_memory_read_log.py`, `test_memory_read_report.py`).
  Reference corpus behind the index is large (`lint_and_test.md` 160 lines,
  `sase_beads.md` 150, `xprompts.md` 166, `sase_artifacts.md` 108,
  `symvision.md` 107) — which is fine, because it is pay-per-read.
- No test currently enforces any size limit on the rendered file (searched
  `src/sase/amd/*.py` and `tests/test_amd*`: only structural parsing, no line
  or token assertions).

## 2. Critique of the plan ("get to <=100 lines")

**It is a good idea, but the requirement as stated optimizes a proxy.**
Lines are a proxy for per-turn token cost and for agent attention. The real
cost is ~4.3k tokens paid on every agent turn in every workspace, plus the
attention cost of a 283-line wall that agents learn to skim. Cutting to ~100
lines (~1.5k tokens) saves roughly 2.5–3k tokens per turn — real money at
swarm scale, and likely better compliance through brevity.

Three caveats that should reshape the requirement:

1. **AGENTS.md is probably not the dominant per-turn cost.** The live system
   prompt of a working agent (provider harness text, skill catalogs, tool
   schemas, injected reminders) can dwarf 4.3k tokens — in this very session
   the standing instructions and skill catalog are several times the size of
   `AGENTS.md`. Recommendation: before committing to 100, measure one real
   agent turn's full context and confirm the rendered file is worth
   optimizing versus, say, skill-catalog verbosity. If it is under ~15% of
   the turn, a 100-line target is aesthetic, not economic.
2. **Progressive disclosure fails closed on the read path, not the write
   path.** Every line demoted from core to reference becomes a line the agent
   must choose to fetch. The `MUST read X before doing Y` pattern only works
   if (a) the trigger condition is recognizable at decision time, and (b)
   compliance is measured. SASE already has the audit log for (b) — use it:
   sample reads-per-domain-task before and after the cut. If `lint_and_test`
   reads drop, the cut hurt more than it saved.
3. **100 is arbitrary; a token budget with a compliance SLO is better.**
   Lines invite gaming (long lines, dense tables). Specify instead:
   rendered core file <= ~1,600 tokens AND reference-read compliance on
   sampled tasks stays at or above baseline. Keep 100 lines as the
   easy-to-check CI proxy for the token budget, not as the goal itself.

A further adjustment: **do not count generated rosters against the budget the
same way as prose.** The decisions roster and glossary term list are indexes,
not reading material. The right move for an index is compression plus a query
command, not necessarily deletion (deleting the only browsable list of 24
decisions makes the web undiscoverable — bare-web reads print *every*
strand, i.e. the most expensive possible fetch).

## 3. Where the ~183 lines can actually go

Ranked by savings-to-risk ratio:

1. **Decisions roster (~90 lines -> ~8).** Highest savings, lowest risk *if*
   replaced with a real index, not a dead pointer. Replace the 24 inline
   summaries with a count, one example invocation, and a roster-listing read
   mode (e.g. a `sase memory read decisions` list view that prints titles
   only — cheaper than the current always-inline roster and cheaper than a
   bare-web full print). Risk: agents lose ambient awareness that a decision
   exists for their situation. Mitigation: keep 3–5 highest-hit decision
   one-liners inline (single-turn agents, host-owned completion, guarded
   recipes, rust-core-required, check-full-is-explicit) and index the rest.
2. **Repos/cross-repo policy (~33 lines -> reference note).** This is
   repo-topology policy needed only when touching non-checkout repos — a
   textbook reference candidate. Keep a 2-line core pointer ("cross-repo
   reads go through `/sase_repo` + audited `sase artifact read`; details in
   reference"). Saves ~30 lines at the cost of one extra fetch on a
   minority of turns.
3. **Glossary enumeration (~18 lines -> ~3).** Replace the 60-term inline
   list with a count, the lookup syntax, and one worked example. Nobody
   browses 60 alphabetized terms; lookup is strictly better.
4. **Deduplicate the mechanism explainer (~25 lines -> ~10).** Core,
   reference, and web intros each re-explain "read on demand with skill X."
   One shared 10-line "how to disclose" block at the top covers all three;
   sections then carry entries only.
5. **Task-types section (~15 lines -> ~8).** Compress five one-paragraph
   entries to a table; keep inline (it routes follow-up filing, a frequent
   action).
6. **Keep verbatim:** the final-declaration block (~8 lines, load-bearing
   every turn), the `/sase_memory_write` guard (~2 lines), gotchas,
   rust-boundary pointer (compress to ~6 lines + reference overflow if it
   grows).

Sketch budget: header + disclosure-howto 14, final declaration 8, workspace
dirs 6, gotchas 6, rust boundary 6, cross-repo pointer 2, reference table 14,
decisions (5 kept + index) 14, glossary pointer 3, task types 8, section
headings ~6 = **~87 lines**. Feasible with margin — but only via items 1–3;
prose trimming alone cannot reach 100.

## 4. Recommended solution

1. **Restate the requirement** as: rendered `AGENTS.md` <= 100 lines AND <=
   ~1,600 tokens, with reference-read compliance (from the existing memory
   audit log) at or above pre-cut baseline on sampled tasks. Lines are the CI
   gate; tokens and compliance are the actual acceptance criteria.
2. **Implement the cut in AMD** (`src/sase/amd/`), not by hand-editing
   rendered files: (a) new roster-index render mode for webs (top-N inline +
   count + list-view read support in `sase memory read`); (b) demote the
   cross-repo policy section of `sase.md` to a reference note; (c) collapse
   glossary roster to `roster: count` style; (d) single shared disclosure
   preamble in the template. Note `AGENTS.minimal.template.md` already
   exists — evaluate whether it (or its successor) becomes the default
   template rather than building a second pipeline.
3. **Add the missing CI gate**: a test asserting rendered line count (and a
   rough token estimate) over the default template, so the file cannot creep
   back to 283 one well-meant paragraph at a time. There is currently no
   such test; without it this project will regress within months.
4. **Measure before/after**: full-turn context share of the rendered file,
   plus per-domain reference-read rates from the audit log for two weeks
   post-cut. Roll back any single demotion whose read rate collapses.
5. **Do not touch** the reference-note bodies in this effort — they are
   already pay-per-read and therefore already at the efficient frontier.
   The waste is entirely in the always-loaded index surface.

Bottom line: yes, do it, but frame it as a token/compliance budget executed
through the AMD generator with an index-query upgrade and a CI size gate —
not as a hand-trimming of prose to hit an arbitrary line number.
