---
narration: 1
title: Shrinking Agent Instructions to 100 Lines
source: research:202610/agent_instructions_budgeted_router/agent_instructions_budgeted_router.md
source_blob: d8885867dc4666cab9b97fea33ceea1a7e6163b3
date: 2026-10-02
kind: research
edition: full
producer: agent
target_minutes: 15
cover: agent_instructions_budgeted_router_infographic.png
---

## The question

How should this project shrink its agent instruction files to at most 100 lines? SASE already discloses detail through memory files. The report asks if the shrink is a good idea, what should change in the requirements, and what to build.

The scope is the generated root AGENTS.md in the sase repo. Four provider copies are byte-identical with it. Those are the Claude file, the Gemini file, the Qwen file, and the OpenCode file.

The lead consolidated five independent reports on October 2, 2026, and then checked the claims. The reports are cdx, cld, grk, mus, and gem.

## The short answer

Yes, do it. Treat the shrink as an architecture rule, not as a cleanup. All six analyses agree.

The file is 283 lines and about 4,300 tokens. It holds roughly eight hard rules and ten useful read triggers, plus about 150 lines of catalogs most turns never use. Getting to 85 to 93 lines, about 1,200 to 1,400 tokens, removes no rule and no trigger. cld reached 93 lines and about 1,205 tokens with the project's own formatter.

The trim matters less than a stop on regrowth. A hand trim reached 227 lines on August 29, 2026. The file was 283 lines again by September 28, 2026. Since February it has gone from 105 lines, to 361, to 227, to 283. Without an always-on budget check, a trim lasts a few weeks.

The bloat is in the generator, not in the notes. Three defaults produce it. Always-inlined web rosters are 51% of the file. The shared template renders 76 lines. Reference descriptions run long. Fix those three. Do not move rules into new places.

Change five requirements. Budget lines and tokens together: at most 100 lines at the 88-column width, and at most 1,600 tokens. Aim for about 85 to 90 lines. Enforce a ratchet in the memory-init check. Call the file a router, not an encyclopedia. Judge success by behavior, not by a line count.

The build is Python only. Add two roster densities, names and none. Leave superseded strands out of always-loaded rosters. Set decisions to none. Set glossary and task types to names. Shorten the shared template. Make every trigger one line. Report cost per section. Record a decision that partly supersedes the older webs rule. Do not add a retrieval mechanism.

## What loads today

All five root files are byte-identical. Each is 283 lines and 17,285 bytes, and about 4,316 tokens. That figure is the characters-divided-by-4 heuristic. It is not a tokenizer count.

Decisions dominate. The descriptor plus a 24-row list is 90 lines and about 1,572 tokens, 36% of the tokens. Next by tokens is the reference index, at 33 lines and about 517 tokens. The repos block is 34 lines and about 477 tokens. The 66-term glossary is 27 lines and about 477 tokens. Heading slices put Core at 103 lines, Reference at 33, and Webs at 145.

Regrowth tells the same story. From the August 29, 2026 trim to today, Core went from 99 lines to 103. Reference went from 76 to 33. Webs went from 56 to 145. Decisions alone went from 4 lines to 90. Halving the reference index did not stick. The roster ate those savings, plus 56 more lines. A roster that grows with its corpus does not belong in the always-loaded file.

Inline is the cheap switch, and it is not the whole fix. For 24 decisions, list is 79 lines and about 1,425 tokens. Inline is 26 lines and about 542 tokens. That one frontmatter line saves 53 lines. Inline still grows with the corpus, and it still prints superseded tombstones. Two of the 24 rows are fully superseded. Glossary, 66 terms, drops from 66 lines and about 651 tokens to 18 lines and about 364. Task types, 5 of them, drop from 8 lines and about 118 tokens to 1 line and about 15.

## What else agents load

The file is not the unit of cost. Claude also loads a home ancestor file of 74 lines and about 967 tokens. Roughly 45 of those lines repeat the shared contract. The real Claude load is about 357 lines and about 5,300 tokens. Codex never sees that home file. It reads only from the git root to the working directory.

Grok loads AGENTS.md and the Claude file both. That double load is documented. A Gemini or Antigravity double load is not documented, and it was not verified. Measure it before acting on it.

Adapters already inject the single-turn rule. Claude appends it. Codex puts it in developer instructions. Muse puts it in a prompt prefix. The final-declaration paragraph partly repeats it. A custom template cannot drop required sections. The minimal template keeps only the title and the core, drops the triggers, and so is the wrong tool.

Across 284 recent Claude sessions, the first call was measured in full. The minimum was about 25.2 thousand tokens. The 10th percentile was 26.6 thousand. The median was 30.1 thousand. The 90th percentile was 40.3 thousand. The median session made 41 calls.

The fixed floor is about 25 thousand tokens. Instructions are about 5.3 thousand of that floor, roughly 20%. This fix saves about 3 thousand tokens per call, about 12% of the floor, and roughly 120 thousand re-read tokens across a median session. Most of that is cache, so adherence and growth are the stronger case. The other about 20 thousand tokens are a larger budget, and they are out of scope.

## How agents use this content

The log runs from September 1, 2026 to October 2, 2026. It has 1,460 events and about 1,370 run directories. A run counts as research when the agent name starts with research.

The lint and test note wins the traffic comparison. It drew 437 non-research runs and 14 research runs, from a 3-line trigger. The sizes note is the strong child: 220 non-research runs and 9 research runs, at 0 always-loaded cost, because beads is the parent trigger. Beads itself drew 198 non-research runs.

Decisions lose the comparison that matters. They drew 20 non-research runs and 51 research runs, and they cost 90 lines. Glossary is the contrast that earns its keep: 58 non-research runs and 56 research runs, at 27 lines. Task types drew 10 non-research runs, at 23 lines, but the filing rule inside them is a hard rule.

grk reported 727 glossary hits and 214 decision hits. Those count strands, not runs. Per run, decisions were opened by about 20 non-research runs in a month, about 1.5% of runs. cld's 109 glossary agents and 69 decision agents are the right counts.

Short triggers stay. A roster that spends 36% of the file to move 1.5% of runs does not. The explicit full check and guarded recipes are already in the lint and test note, which 437 runs read. The task runner also enforces guarded recipes. Adapters inject the single-turn rule. Host-owned completion lives in the final skill. Keep glossary names, and drop the alias parentheticals. Keep the new-task rule.

## External evidence

Anthropic, verified, says to stay under 200 lines per Claude file, because length hurts adherence. Imports still load at launch. A companion essay says minimal does not mean shortest. cdx, cld, and grk cite that essay.

OpenAI's February 2026 harness note replaced one big agents file with roughly 100 lines that serve as a map, plus lint. That is already the SASE design. cld cites it from a mirror.

Gloaguen and colleagues, verified, found no general gain in success, and over 20% added inference cost. Instructions are followed. Repository overviews are not helpful.

Khatri, in July 2026, is new and verified. Across 288 runs, an on-demand wiki did not measurably beat always-on context. The bound is at most 10 to 15 percentage points. Failures were skill, not missing facts.

A June 2026 probe study is also new and verified. A file of at most 3,000 characters beat a static knowledge base, at 33.0% resolved versus 28.3%.

Vercel, in January 2026, verified the strongest point for pointers. A passive index of 8 kilobytes scored 100%. Skills scored at most 79%, and in 56% of cases the skill was never invoked.

Adherence falls as the instruction count grows. Omissions dominate, and there is a primacy bias. Context files grow by small additions. The median Claude file is about 485 words. This one is about 2,450 words.

100 lines is a practitioner convention, not a measured optimum. The benchmarks score task correctness. Most of this file is a workflow contract an agent cannot infer from code. Keep that contract and the pointers. Move the catalogs to on-demand reads.

## Critique of the plan

A cap of 100 lines is a good idea. Adherence comes first. Roughly eight rules compete with 90 lines of decision summaries and a 66-term glossary. The file already has 5 must markers, 2 important markers, and 3 not or never markers. If many lines are emphasized, none of them stands out.

Accretion is next. Each new note is a local choice with a global cost. A budget makes that cost visible. Cost is real, at about 20% of the per-call floor, and secondary, because those tokens are mostly cached.

The stated plan is weak in four ways. A line cap is gameable. From April to June 2026 the file was 8 to 46 lines only by importing notes or using dynamic memory, which was later removed. Providers do not load the same set, so the file is the wrong object. A cleanup without a ratchet will not last. And over-pruning is the danger that matters. If the trigger is gone, the note is gone. A rule needed before the action cannot hide behind a read.

Do not add a memory kind, a retrieval engine, imports, or a move into skills. Retrieval was built and removed three times. Make the renderer emit a router. Make the budget a ratchet with a cost per section. Record that policy as a decision.

Scope the budget to the root AGENTS.md. The copies inherit it. Nested files and the home file stay separate. Require at most 100 lines at the 88-column width and at most 1,600 tokens, and count imports. Report Claude's home file and Grok's double load, and do not fail on those totals. Aim for about 85 to 90 lines, so the next core note does not force a higher limit. The ratchet starts at today's size, drops as each phase lands, and rises only through a reviewed config change. Every loaded line is a rule a machine does not already enforce, or a trigger. Every reference note keeps a trigger. Superseded rows stay out.

Eight hard rules stay loaded. The final skill is last, and the monitor covers long work. The repo skill comes before any other repo. Sidecar artifacts use the artifact read command. Memory reads and writes keep their routing. Stay in the workspace. Read the lint and test note after tracked edits. Keep the Rust-core litmus test. File discovered work through the new-task skill. A rule a machine already enforces gets one line. Success is trigger health and contract compliance, not the line count alone. Skill descriptions, the Grok double load, and copied Symvision text are separate beads.

## The recommended solution

Make the generated AGENTS.md a budgeted router. The target is about 85 to 93 lines and about 1,200 to 1,400 tokens, under a ceiling of 100 lines and 1,600 tokens. cld's mock keeps every trigger at 93 lines and about 1,205 tokens. Memory edits go through the memory-write skill, with each file named and confirmed. Generated notes change only through their templates.

Phase 0 needs no code. The file goes from about 283 lines to 190. Switch decisions from list to inline, saving 53 lines, and cut that descriptor to two lines. Make each reference description one trigger of 90 characters or less, with the lint and test note as the only must. Shorten the Rust note to about 5 to 7 lines, fold gotchas into one line, and demote neither. Fill the null glossary and task-type descriptions.

Phase 1 is a small Python change and lands at about 85 to 93 lines. Cut the shared template from 76 rendered lines to about 18 to 20, four to six short rules, with linked repos shown as names only. Add names and none. Names drop aliases and summaries. None is a strand count plus a browse command, and fully superseded strands stay out. Set decisions to none, glossary to names, and task types to names, and keep the 2-line new-task rule. Shorten the intros and update their anchor checks in the same change. Do not hide text in comments to pass a check.

Add a max line count and a max token count. The check fails over budget, prints each section's cost, and starts at the measured size. Tests cover clean rosters, omitted superseded strands, complete core and reference sets, identical provider copies, a failing over-budget path, and the home overlay. The shared template also takes the home file from 74 lines to about 35. That is intentional.

Phase 2 records that always-loaded instructions are a budgeted router. It supersedes the older webs decision only on the cost clause. Descriptors still get their own section. Link the busy notes to the decisions for their domains.

The blocks sum to about 85 to 93 lines. The contract takes 18 to 20. Ten triggers take 18 to 22. Glossary names take 13 to 15. Titles take 8 to 10. Rust takes 6 to 7. Task types take 5 to 6. Decisions take 5. The webs intro takes 3. Gotchas take 2 to 3.

cdx and gem wanted no rosters. cld wanted titles only. grk wanted a cap. mus wanted a top-N list. The resolution is per web, and it stays in Python, because this generator has no Rust call site. Revisit only if a screen shows the budget. Block from day one, at the current size. The token ceiling is 1,600. gem said 1,500. cld and mus said 1,600. cdx and grk said 2,000. The ceiling discussion measures cld's mock at 101 lines and about 1,379 tokens. A ceiling of 2,000 would let 100 lines get dense.

gem's 566 lines for Antigravity are unverified. Only Grok's double load is documented. Cache stability is a weak reason to keep the long file. Reject the minimal template, import shims, skills as the main lever, keyword retrieval, and nested files. Shims were tried from April to June 2026. Claude still loads them, and Codex does not expand them. Keep the home file for now. 22 non-research runs read the tailnet note this month, and the template rewrite roughly halves that cost.

Compare the two weeks before with the two weeks after. Lint and test reads must not fall from 437 a month. Glossary lookups should stay around 50 or more. Decision reads, about 20 a month, should not fall, and should rise once the links land. Missing final declarations, and other-repo access outside the repo skill, should hold steady. Spot-check cdx's list: a typo fix, a keymap change, a Rust-owned feature, a linked-repo read, filing a bead, a long-command handoff, and an incomplete turn.

Roll back one line, not the whole file. If decision reads or final-skill compliance drop, restore five or six titles in core, about 6 lines. Those are host-owned completion, the explicit full check, guarded recipes, gates never block, and Rust core required.

Four follow-ups stay separate. Budget skill descriptions, about 1 thousand tokens inside a floor of about 20 thousand. Stop injecting the Claude file into Grok, while still writing that file. Point the tools agents file at Symvision. Verify what Antigravity loads.
