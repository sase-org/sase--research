---
title: Better research from `#research_swarm` by using SASE as the research OS
status: draft
tags:
  - research-swarm
  - xprompt
  - sase-primitives
  - multi-agent
create_time: 2026-10-01
updated_time: 2026-10-01
---

# Better research from `#research_swarm` by using SASE as the research OS

**Question.** How should `#research_swarm` produce better research, and how can this
xprompt swarm take better advantage of features SASE already has? New SASE features
only if they are truly justified.

**Answer.** The swarm's *control plane* is already strong: independent per-provider
researchers, a file-as-contract handoff through `wait.artifacts`, a clan/tribe, weighted
queue admission, and an optional linker that is a publication barrier. Research *quality*
is lost in the *payload*: every researcher gets the same prompt, chooses its own
filename, writes free-form prose with no schema, and never publishes a structured
findings index. The lead then spends a large fraction of its prompt being a file clerk.
Almost every high-leverage fix is an xprompt change that uses primitives SASE already
ships (`#research(report_target=…)`, `sase var`, `sase plan search --kind research`,
`sase artifact link`, declared frontmatter). One core feature is justified:
**partial-success `%wait`**, because a single failed researcher currently parks the
lead forever.

## Bottom line

Ship these in order:

1. **Shared directory + shared report contract.** Pass a swarm `name` (default
   `research-{@1}`) into `#research(report_target=…)` so every draft lands in
   `<YYYYMM>/<name>/<name>__<suffix>.md` on the first write. Put the sidecar README's
   "question, evidence, alternatives, recommendation" rule, plus `status`/`tags`
   frontmatter, into `#research` itself.
2. **A research method, not a write path.** Tell every researcher to search the
   existing corpus first, prefer audited artifact and repo reads, and emit a claims
   table. Publish a small findings JSON with `sase var set` so the lead can compare
   before opening the traces.
3. **Complementary angles before anyone writes.** Static per-suffix briefs now; an
   optional planner that writes briefs into `sase var` later. Identical prompts are
   the main reason five expensive models rediscover the same files.
4. **Lead as claim-selector and adjudicator**, with file moves deleted once (1) lands.
   Encode the disagreement table and primary-source check that the best leads already
   improvise.
5. **One new SASE feature: `%wait` that can release on failure.** Everything else
   recommended below is prompt or plugin work.

Do not rebuild live debate, do not resurrect critique as an unread sidecar, and do not
invent a swarm-specific goal protocol. Goals already have a design (one clan goal, lead
claims); agents today may only `sase goal list` / `show`, so wire that design when G4
lands.

## Claims

| Claim | Confidence | Evidence |
| --- | --- | --- |
| Independent same-prompt fan-out plus a synthesizing lead is the right *shape* for SASE | high | Swarm source; SASE single-turn / host-carried-info invariants; collaboration research 2026-09 |
| Quality is limited by identical briefs and uncomparable drafts, more than by missing agents | high | Live 2026-10 stem split (four different root filenames for one question); `#research` is write-only; README contract is not in the xprompt |
| STORM-style perspectives *before* writing will raise coverage more than adding a sixth model | medium-high | Shao et al. 2024; this swarm's own overlapping source hunt |
| Lead should select claims and union coverage, not blend prose | medium-high | Maryanskyy 2026; "Beyond Consensus" 2026 on trace-level synthesis; Self-MoA on quality vs diversity |
| `sase var` + `wait.artifacts` already give the lead an index plus traces | high | `docs/xprompt.md` template context; `/sase_var` skill |
| Critique-as-sidecar failed and should not return in that form | high | Linker research: two `__critique.md` files, excluded from Highlights, unused by `rs`/`rsa` |
| One failed researcher parking the lead is a real reliability hole | high | `docs/xprompt.md`: named waits release only on `completed` |
| Agents cannot name or claim goals today | high | `sase goal -h`: human-only `new/edit/drop`; agents get `list`/`show` |
| Declared research frontmatter is unused | high | 82 of 91 canonical 2026-09 reports have no `status:` field |

## What a good research-agent swarm is

A research swarm is not "more models on the same prompt." It is a small scientific
team with a host that carries information between single-turn workers. The properties
that actually raise quality:

**Diversity of method, with independence of conclusion.** Model diversity is a weak
proxy. Complementary *angles* (code, corpus, literature, primitives, failure modes)
produce traces the synthesizer can assemble. Independence until synthesis prevents
premature consensus; SASE already enforces this well. Ferreira et al. 2026 find that
multi-agent debate's gains often collapse to ensemble sampling once budget is matched.
Keep independence. Spend the diversity budget on *what each agent is asked to do*.

**An outline or perspective set before anyone writes.** STORM (Shao et al., NAACL 2024)
improved organization (+25%) and coverage (+10%) over outline-driven RAG by discovering
perspectives and asking questions *in the pre-writing stage*. `#research_swarm` jumps
straight to writing. The lead cannot impose an outline after the fact without throwing
away work or rewriting it.

**Comparable traces, then a synthesizer that reads them.** "Beyond Consensus"
(2026) shows an aggregator that reads full reasoning traces recovers correct
intermediate steps that voting discards. Maryanskyy (2026) shows naive blending of
whole answers can lose to a single model, while *selection* of the best artifacts
wins. For open-ended research the right aggregator is mixed: **select the strongest
claim on each disputed point, union the unique coverage, and adjudicate disagreements
against primary sources.** The best SASE leads already do this (the 2026-09 linker
report is the existence proof). The xprompt does not require it.

**A file-as-contract, host-carried handoff.** SASE agents are single-turn.
Collaboration research (2026-09-22) measured that launch-time `%wait` / `#fork` / clan
is how SASE agents actually collaborate, and recommended against live peer messaging.
`#research_swarm` already follows that: researchers are forbidden to read peers;
the lead consumes `wait.artifacts`. Keep that. Enrich the *payload* of the contract.

**Mechanical work belongs to the host.** Naming a directory, moving files, registering
snapshots, and linking drafts are deterministic. Every token the lead spends on them is
a token it does not spend on adjudication.

**Publication is a separate job from research.** The linker (opt-in, implied by
`image=true`) is a publication barrier: the Highlights hook fires once, on ADD, so the
canonical `<name>.md` must appear after the infographic exists. That design is sound.
Research quality is decided *before* the linker runs.

**One outcome record.** A swarm is one question. Five `done` pings are noise. The
goals design (one clan draft, researchers `keep_open`, lead claims) is the right
product shape once agents are allowed to name and claim.

## How the swarm works today

Source of truth: plugin `sase-research-artifacts`
`src/sase_research_artifacts/xprompts/research_swarm.md`, expanded as `#research_swarm`.
Eight authored segments; `%if(should_run=…)` plus `provider_enabled("hard")` drop
disabled providers.

| Segment | Role | Handoff |
| --- | --- | --- |
| `<clan>.cdx/.cld/.grk/.mus/.gem` | Independent researchers, default cdx+cld | `#research(suffix=…)` writes a month-root file and `sase artifact create`s it |
| `<clan>.final` | Lead: read drafts, do more research, merge, optionally move files | Writes `<name>.md` or `<name>__final.md` |
| `<clan>.image` | Opt-in; `#fork`s the lead, then `#research/image` | PNG beside the lead report |
| `<clan>.linker` | Opt-in editor (always on with image) | Publishes hook-eligible `<name>.md` |

Already-good SASE use:

- `%clan` + `tribe=research` and the plugin's tribe config (icon `∴`, color, description).
- `{@1}` keyed hood so overlapping launches cannot steal names.
- `%q(1.5x, w=0.25)` so a handful of quarter-weight members fit in the machine budget.
- `wait.artifacts` (raw-protected so it renders at the *lead's* runtime) as the
  discovery channel; transcripts are out of band on purpose.
- `#research(suffix=)` as the producer contract the lead matches by `wait_name` +
  `__<suffix>.md`, never by list order.
- Provider gating that still allows a solo lead if every researcher flag is off.
- Linker as editor: inventory, URL policy, no new claims. Image implies linker so the
  PDF can embed the PNG.

The independence paragraph is correct for SASE. The problem is everything *around* it.

## Where quality is lost

### Identical briefs, divergent files

Every researcher receives the same user question plus a long independence preamble that
names every peer agent. Diversity is supposed to come from the provider. In practice
the first hour of every swarm is five agents opening the same plugin files.

This dispatch is the measurement. Four researchers writing on the same question at the
2026-10 month root chose four stems (filenames only; contents unread):

- `research_swarm_architecture_and_quality__cdx.md`
- `improving_research_swarm_xprompt__grk.md`
- `research_swarm_improvement_ideas__mus.md`
- `improving_research_swarm_architecture__gem.md`

`#research` tells each agent to pick a descriptive stem and, on collision, pick another.
Independence plus collision-avoidance *guarantees* split stems. The lead is then
required to identify reports via `wait.artifacts` and move them into `<name>/`. The
sidecar README already describes the in-directory layout as the intended end state;
researchers still write to the month root because the swarm never passes
`report_target`.

Corpus: 221 researcher drafts already live inside topic directories (after a lead
moved them) and 15 still sit at a month-root. The move works when the lead succeeds.
It is wasted lead context, and it leaves a mess when the lead has not run yet.

`#research` already accepts `report_target`. The swarm just does not use it.

### `#research` is a write path

The body of `#research` is: pick a path, do not overwrite, run `sase artifact create`.
The sidecar README says research should record the question, evidence, alternatives,
and a recommendation. `#research/more` points at that README. `#research` and
`#research_swarm` do not.

Consequences:

- No required claims table, confidence, or source grade.
- No instruction to run `sase plan search --kind research` (this command found the
  linker report, the swarm-goals note, and the collaboration strategy report in one
  call).
- No instruction to set the frontmatter the *plugin itself* declares
  (`status`, `tags`, `create_time`, `updated_time`). Of 91 canonical 2026-09
  `<topic>/<topic>.md` reports, 82 have no `status:` field. The Artifacts pane's
  status facet and `group_by: status` are empty.
- No `sase var set` of a findings index, so the lead's only structured input is a list
  of paths.

### The lead prompt is a file-clerk spec with research in the margins

The lead is told to (1) identify exactly one report per suffix, (2) research gaps, (3)
pick a stem, create a directory, *move* every draft, (4) write the merge. Step 3 is
pure mechanics and dominates the template. The research instruction is one sentence:
prioritize gaps, weak evidence, and disagreements. There is no requirement to:

- build a disagreement table;
- re-check disputed claims against primary sources;
- select the strongest claim rather than blend;
- add `sase artifact link add <consolidated> derives-from <draft>`;
- keep researcher `status: draft` and set the consolidated `status: final`.

The 2026-09 linker synthesis shows what a lead *can* do when it treats disagreements
as things to rule on. That behavior is tribal knowledge. Put it in the xprompt.

### Critique was the wrong shape of adversary

The linker research records why critique was deleted: two `__critique.md` files in the
whole corpus, excluded from Highlights, and unused by the user's `rs`/`rsa` snippets.
An adversary that writes a file nobody reads cannot improve research. An adversary that
runs *before the lead* and whose registered findings the lead must answer can.

### One failure parks the join

Named `%wait` unblocks only on `done.json` outcome `"completed"`. Failed, killed, or
crashed researchers leave the lead parked with a red `wait_checks` notification. For a
five-researcher swarm this is a single-provider outage becoming a total loss of
synthesis. Image-failure parking of the linker was accepted as a publication invariant
(a PDF without the image is the thing `image=true` exists to prevent). Researcher
failure is different: four good reports and one crash should still synthesize, with
the missing suffix reported.

### Goals and beads are designed, not connected

`xprompt_swarm_goals.md` (2026-09-27) designed one shared clan draft, researcher
`keep_open`, lead `claim`. As of 2026-10-01, `sase goal` still refuses `new` / `edit` /
`drop` inside agent runs. Researchers cannot name the draft. Do not paper over this in
the xprompt. When G4 lands, apply that design, and keep `.image` / `.linker` from
becoming the claimer (the same note already flags that anyone waited-on is a
contributor, so a waiter after `.final` steals the claim).

## SASE features the swarm already uses well

Use these as the floor, not the ceiling.

| Feature | How the swarm uses it |
| --- | --- |
| Xprompt swarm `---` fan-out | Eight segments, one library definition |
| `%if(should_run=)` + `provider_enabled("hard")` | Drop disabled providers at launch |
| `%clan` / `{@1}` / tribe `research` | One hood, TUI grouping, no name theft |
| `%q(1.5x, w=0.25)` | Concurrent quarter-weight members |
| `wait.artifacts` | Lead and linker discover files without transcripts |
| `sase artifact create` | Durable snapshot the waiter can name |
| `#fork` | Image agent inherits the lead's report context |
| File-hook producer filter | Artifact copies never fire Highlights; only the committed canonical file does |
| Model aliases / `researchers` bucket | `@image` fallback chain, `@xlarge` lead/linker |

## SASE features sitting unused

These are the highest-leverage "take better advantage" items. None needs a new
subsystem.

**`#research`'s `report_target`.** Already implemented. The swarm should pass
`<name>/<name>__<suffix>.md` so the first write is the final relative path. `{@1}` is
stable per invocation, so a default `name=research-{@1}` needs no extra planner.

**`sase var`.** Built for exactly this: small JSON handoff values, available to waiters
as `{{ agents["research.{@1}.cdx"].findings }}`. The skill even uses a research-shaped
selector as its example (`sase var get 'research.*.report["summary"]'`). Caps (8 KiB
strings, 64 KiB JSON, depth 8) are plenty for a claims list and fatal if someone tries
to stuff a report body in — which is the right pressure. Reports stay artifacts;
vars are the index.

**`sase plan search --kind research`.** The research README already documents it.
Zero researcher prompts mention it. It is the cheapest prior-art gate in the system.

**`sase artifact read` / `sase artifact link`.** The lead is told to read via artifact
refs (good). Nobody is told to write `derives-from` from the consolidated report to
each draft, or `related` to prior corpus hits. The link registry already has those
relations; the 2026-09 swarm-goals note itself carries a `derives-from` edge. Make
that the lead's last mechanical step.

**Declared frontmatter (`status`, `tags`).** The ref provider's pane groups by
`status` and facets on `tags`. Researchers should write `status: draft`; the lead
`status: final` (or `review` if linker will publish). Tags such as `research-swarm`,
the topic slug, and `literature` / `codebase` make the pane useful.

**Local xprompts / Jinja macros.** Swarm frontmatter currently has no `xprompts:`
helpers. The independence preamble is copy-pasted five times. A `_researcher` local
helper (or a Jinja macro above the first `---`, which already works because the body
is rendered then split) is how a shared method and schema stay in one place.

**`sase var` + `%wait` on a planner.** A nine-line planner segment that only
decomposes the question and `sase var set`s per-suffix briefs would give researchers
adaptive angles with no new SASE feature. Costs one serial agent. Static briefs are
the zero-latency version.

**`%hold`.** An expensive five-model swarm can hold other queued work for its TTL so
it actually gets the 1.5× budget it authors. Optional, user-facing.

**Output specs.** Structured `output:` is a workflow-step feature. Markdown swarms
cannot validate the model response against a schema without becoming a YAML workflow.
`sase var` is the markdown-swarm equivalent. Converting `#research_swarm` to a YAML
workflow just to get `output:` is not justified.

**Goals.** List/show only, for agents. Cite `@goal` when G4 exists. Do not have
researchers call human-only verbs.

## New SASE features: only one is justified now

### Build: partial-success waits

Contract today (`docs/xprompt.md`): a named wait releases only on `"completed"`. That
is the correct default for "code then review" and for "image then linker." It is the
wrong default for "N independent proposers then a synthesizer."

A keyword on `%wait` such as `on=completed|failed|any` (name bikesheddable) would let
the lead start when every researcher has *settled*, and the lead prompt already knows
how to stop if a suffix is missing from `wait.artifacts`. Failed researchers simply
would not appear in that list.

This helps every independent-fan-out swarm, not only research. It is a small, closed
change to wait semantics with a fail-closed default (`completed`), so existing
prompts stay byte-identical.

Do not invent "wait until this artifact label exists" as a separate feature. Agent
completion plus `wait.artifacts` plus the lead's "exactly one per suffix or stop"
rule already covers the missing-registration case, once the lead is allowed to run.

### Do not build

- **Live peer debate / agent messaging.** Contradicts single-turn agents, was tried
  and removed in March 2026, and the 2026-09 collaboration report's usage corpus
  showed native `SendMessage` used once. Independence is a feature here.
- **A swarm-specific goal store.** The ledger and G4 clan-shared drafts are the
  product. Duplicate it in the xprompt and you will fight the host.
- **Host-owned file-moving in core.** `report_target` already puts bytes in the right
  place. A Python workflow step would also work and is heavier.
- **Hook on MODIFY, or firing Highlights for drafts.** The linker research ruled
  these out; ADD-once is what makes the publication barrier work.
- **Always-on linker as a quality strategy.** It improves reading, not findings.
  Flip the default after drafts carry a schema, if rollout diffs stay faithful.
- **Converting the swarm to a YAML workflow** for its own sake. Markdown fan-out plus
  `sase var` plus `wait.artifacts` is the SASE-native shape.

## Ranked improvements to consider

Rank is expected research-quality gain per unit of complexity. Effort is plugin
xprompt unless marked **core**.

### 1. Shared output path and shared report contract (do this first)

Add an optional `name: word` input, defaulting to `research-{@1}` (the keyed marker is
already unique per launch). Change every researcher call to:

```text
#research(suffix=<short>, report_target={{ name }}/{{ name }}__<short>.md)
```

Extend `#research` so that when `report_target` is set, the agent writes exactly that
file under the month dir (it already does) *and* fills:

- YAML frontmatter: `title`, `status: draft`, `tags`, timestamps;
- a one-paragraph question restatement;
- evidence with citations (artifact refs, repo paths, URLs);
- alternatives considered;
- a recommendation or ranked list, as the question requires;
- a claims table (claim / confidence / evidence).

On collision, fail visibly (already the `report_target` rule). Delete the lead's move
step. The lead picks a prettier stem only if the user omitted `name` and wants to
rename at the end; even that can wait.

This removes the live four-stem split, matches the README layout on the first write,
and makes drafts comparable.

### 2. Put a research method in `#research`

`#research` is invoked by the swarm *and* by solo runs. Method belongs there.

Minimum method block:

1. `sase plan search --kind research "<topic>"` and `sase artifact read` any hit that
   is actually used.
2. Open foreign repos with `/sase_repo`; read sidecar artifacts with
   `sase artifact read`.
3. Prefer primary sources (code, docs, measured corpus) over other agents' prose.
4. Grade evidence: measured, code-verified, documented-design, speculation.
5. `sase var set findings --json --value-file …` with
   `{summary, claims[], sources[], open_questions[], suffix}`.

`#research/prompt` already asks for prior art, alternatives, and a recommendation.
Fold that shape into `#research` so the swarm inherits it without a second wrapper.

### 3. Complementary angles, statically at first

Give each suffix a standing brief, still on the same user question:

| Suffix | Standing brief |
| --- | --- |
| `cdx` | Implementation and tests: the plugin, host wait/swarm code, what the tests lock |
| `cld` | Prior SASE research corpus and design notes, via `sase plan search` / artifact read |
| `grk` | SASE primitives the swarm underuses, and whether a core feature is truly required |
| `mus` | Failure modes, cost, and "what I would skip" |
| `gem` | Publication path: hook, linker, Highlights, pane, frontmatter |

Independence stays. Overlap shrinks. For this very question, that mapping is the
natural partition of the work.

A later optional `planner=true` segment can wait-free-run first, `sase var set` per-suffix
briefs from the actual question, and have researchers `%wait` on it. STORM's result is
the reason to keep this on the list. Static briefs get 80% of the value with no extra
latency.

An `angles` text input mapped by order is a middle path if you want user control
without a planner agent.

### 4. Rewrite the lead as an adjudicator

Once files already sit in `<name>/`:

1. Render a findings table from `{{ agents[…].findings }}` (index).
2. `sase artifact read` each draft (traces).
3. Own research only on gaps, weak evidence, and disagreements.
4. Emit a **disagreement table** with a ruling and the primary source that decided it.
5. Select claims; union unique coverage; cut duplicated tours of the same file.
6. Write `<name>.md` or `<name>__final.md` with `status: final`.
7. `sase artifact link add` `derives-from` each draft that was used, and `related` for
   prior corpus the lead actually read.
8. Register if the linker will run.

Keep "the lead does its own research." The linker report's value was exactly the lead
catching researcher errors against code. Do not reduce the lead to a summarizer.

### 5. `sase var` findings as a first-class handoff

Make step 5 of `#research` mandatory for swarm suffixes. Document the schema in
`docs/xprompts.md`. The lead template prints the table above the path list. If a
researcher forgets to set vars, the lead still has `wait.artifacts` and the file;
vars are an acceleration, not a new contract that can strand the join.

### 6. Partial-success `%wait` (core)

See above. Default remains completed-only. The lead segment opts in. The image→linker
edge keeps completed-only.

### 7. Goals, when G4 ships

Apply `xprompt_swarm_goals.md` as written: one clan goal, researchers `keep_open`,
lead claims with the consolidated `research:` ref. Fix the documented hole so
`.image` / `.linker` cannot claim. Until then, do nothing in the xprompt that calls
human-only goal verbs.

### 8. Frontmatter and pane hygiene

Trivial once `#research` requires it. Unlocks the Research pane's status grouping and
tag facets that the plugin already declared. Researchers: `draft`. Lead: `final`.
Linker leaves status alone unless it is publishing.

### 9. Adversary that feeds the lead (optional, later)

If critique returns, it is a segment that `%wait`s on researchers, writes
`__crit.md` *or* a `sase var` objections list, and that the **lead** waits on. The
lead's prompt requires a "objections addressed" section. The file stays hook-ineligible
(`__*` glob). The user-readable report is still the lead's (or linker's) `<name>.md`.
Default off, like `muse`.

### 10. DRY the researcher body

Jinja macro or local `_researcher(short, model, brief)` helper. Required before the
standing briefs in (3) or the method in (2) become unmaintainable. No user-visible
behavior change.

### 11. Publication and cost polish

- Leave `linker` default `false` until (1)–(4) land; then consider default-on for
  reports you actually read.
- If `gemini=true` is used as a *researcher*, the default `agy/gemini-3.8-flash-high`
  is a cost choice. A stronger slug is justified for synthesis-grade research; keep
  flash for the image alias fallback.
- Keep `muse` default off (warn advisory).
- Keep researcher models at `@xhigh` / equivalent. Self-MoA (Li et al.) is the warning
  against mixing in weaker proposers just for vendor diversity.
- Refresh the plugin CHANGELOG (still describes 0.2.0, August 2026; the swarm has
  since grown linker, image, wait.artifacts, queue weights, provider gating).

### 12. `%hold` on big swarms (optional)

Document a snippet `%hold(pending, future)` or a `hold=true` input for five-model
runs so they are not interleaved with unrelated high-weight work. Purely operational.

## Worked example: this dispatch, under the proposed swarm

User: `#research_swarm(name=research_swarm_quality, grok=true, muse=true, gemini=true): …`

- All five drafts appear under `202610/research_swarm_quality/` with the suffixes the
  lead already understands. No stem negotiation.
- `cdx` reads plugin tests and host wait code. `cld` reads the linker and
  collaboration reports. `grk` audits unused primitives. `mus` lists skip items.
  `gem` traces the hook. The lead's disagreement table is short because the traces
  overlap less.
- Each draft has `status: draft` and a findings var. The lead's first screen is a
  five-row claims index.
- One crashed provider still yields a consolidated report, with that suffix listed
  as missing, *if* (6) has landed; today it yields a parked lead.

## Open questions

- Exact `%wait` keyword spelling (`on=`, `allow_failed=`, `require=settled`) — a
  core design choice, not an xprompt one.
- Whether `name` should be required (better layout, worse one-shot UX) or defaulted
  from `{@1}` (ugly directory names, zero user friction). Default-from-`{@1}` plus
  optional pretty `name=` is the better product.
- Whether static briefs should follow the suffix even when the user turns providers
  off (a solo `gem` researcher would then run the publication brief). A planner
  avoids that; static briefs should fall back to "full question, no specialty" when
  fewer than three researchers run.

## Sources

**SASE, first-party (read as code or audited artifacts):**

- `sase-research-artifacts` xprompts: `research_swarm.md`, `research.md`,
  `research_more.md`, `research_prompt.md`, `research_image.md`
- Plugin docs: `docs/xprompts.md`, `docs/architecture.md`, `docs/configuration.md`,
  `src/sase_research_artifacts/provider.py`, `src/sase_research_artifacts/default_config.yml`
- Host: `docs/xprompt.md` (swarm expansion, `wait.artifacts`, `%wait` completion
  rule, template context, `%if`, `%q`); `docs/blog/posts/xprompts-in-depth.md`
- Sidecar README layout contract
- `sase artifact read research:202609/research_swarm_linker_agent/research_swarm_linker_agent.md`
- `sase artifact read research:202609/xprompt_swarm_goals.md`
- `sase artifact read research:202609/multi_agent_collaboration_strategy/multi_agent_collaboration_strategy.md`
- Glossary: Xprompt Swarm, Agent Clan, Artifact, Goal, Sase Monitor
- Live corpus counts in this workspace's research sidecar (2026-09 canonical
  frontmatter; 2026-10 root draft filenames)
- `sase goal -h` (agent-visible verbs as of 2026-10-01)

**External:**

- Shao, Jiang, Kanell, Xu, Khattab, Lam. "Assisting in Writing Wikipedia-like
  Articles From Scratch with Large Language Models" (STORM). NAACL 2024.
  https://aclanthology.org/2024.naacl-long.347/
- Li et al. "Rethinking Mixture-of-Agents: Is Mixing Different Large Language
  Models Beneficial?" (Self-MoA). OpenReview.
  https://openreview.net/forum?id=K6WwK8URlV
- Maryanskyy. "When Agents Disagree: The Selection Bottleneck in Multi-Agent LLM
  Pipelines." arXiv:2603.20324, 2026. https://arxiv.org/html/2603.20324v1
- "Beyond Consensus: Trace-Level Synthesis in Mixture of Agents." arXiv:2605.29116,
  2026. https://arxiv.org/html/2605.29116v1
- Ferreira, Liu, Zheng. "Beyond Symmetric Agents: Cognitive Diversity and
  Multi-Agent Debate in Small Language Models." arXiv:2609.35875, 2026.
  https://arxiv.org/abs/2609.35875
