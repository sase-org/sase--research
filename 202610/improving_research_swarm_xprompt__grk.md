---
create_time: 2026-10-01
updated_time: 2026-10-01
status: draft
tags:
  [
    research_swarm,
    xprompts,
    multi-agent,
    sase-research-artifacts,
    mixture-of-agents,
    wait-artifacts,
  ]
---

# Improving `#research_swarm`: better research, better use of SASE

**Question.** How should `#research_swarm` produce better research, and how can
this xprompt take better advantage of features SASE already has? Which new SASE
features are actually justified?

**Researcher.** grk (`research.36.grk`). Independent report. I did not read peer
reports from this swarm.

**How I recovered the question.** This researcher's rendered prompt did **not**
contain the user's research question. `raw_xprompt.md` ends with
`: #research(suffix=grk)`. I recovered the question from
`SASE_MULTI_AGENT_PROMPT_FILE`
(`~/.sase/multi_prompts/202610/gh_sase_org__sase-multiprompt-261001_120547.md`).
That is itself finding #1.

## Bottom line

Keep the topology: **independent heterogeneous proposers, then a strong
selector-synthesizer, then an optional publisher.** That is already the right
multi-agent research shape. Do not add unguided debate rounds, and do not
replace independence with a default decompose-and-assign coordinator.

The cheapest, highest-leverage work is prompt and parser work, not new agents
and not new SASE subsystems:

1. **Fix the `)::\\n` prompt-binding bug** so researchers actually receive the
   question. Fail closed if `prompt` is empty.
2. **Give researchers a report rubric** (question, evidence, alternatives,
   recommendation, confidence, gaps) and tell them to search prior research.
3. **Teach the lead to select, not average.** Literature says synthesis-blending
   destroys the value of a diverse team; a disagreement table plus evidence
   weighting is the whole point of running five models.
4. **Use `sase var`, artifact links, `report_target`, and `%proc`** for
   structured handoff, related-work links, and mechanical file moves. Those
   features exist today and the swarm ignores them.

Add agents only as **opt-in** extras: coverage/angle mode, critique-after-publish,
one gap-fill pass. The one new SASE primitive that is justified is
**success-only wait** (so a failed image agent does not park the linker).
Goals wiring waits on G4.

## What the swarm is today

`#research_swarm` lives in the `sase-research-artifacts` plugin
(`src/sase_research_artifacts/xprompts/research_swarm.md`), not in sase core.
It is a markdown xprompt swarm: top-level `---` fans out one agent per
segment.

| Role | Default | Job |
| --- | --- | --- |
| `.cdx` / `.cld` | on | Independent researchers, `#research(suffix=…)` |
| `.grk` / `.mus` / `.gem` | off | Same job, other providers |
| `.final` | always | Wait on researchers, read `wait.artifacts`, do more research, consolidate |
| `.image` | off | `#fork` the lead, draw `<name>_infographic.png` |
| `.linker` | off (implied by `image`) | Publish hook-eligible `<name>.md` with checked links and embedded image |

The deluxe user snippet `rsa` turns on grok, muse, gemini, and image. This run
was that deluxe shape: five researchers, lead, image, linker.

The architecture is **Mixture-of-Agents with isolated proposers**:

```text
user question
    ├─ cdx, cld, grk, mus, gem   (parallel, no peer reads)
    └─ final waits on all → optional image ∥ linker
```

Independence is explicit and correct. Handoff from researcher to lead is
`sase artifact create` plus runtime `wait.artifacts`, not chat transcripts.
Queueing is `%q(1.5x, w=0.25)` on every member. The clan is
`research.{@1}` with `tribe=research`. Provider hard-disables drop a
researcher even when its boolean is true.

That is a serious, well-evolved swarm. Most of what is wrong is in the
**researcher prompt**, the **lead's aggregation rule**, and **one parser
hole that dropped this run's question**.

## Finding 1 — this run's researchers did not receive the question

### Observation

Launch source (`SASE_MULTI_AGENT_PROMPT_FILE`):

```text
#gh:gh_sase-org__sase
#research_swarm(gemini=true,grok=true,muse=true,image=true,image_model=gpt-6-astra)::
Can you do some research with the goal of helping me come up with ideas to improve the
`#research_swarm` xprompt swarm? …
```

What `research.36.grk` actually received (`raw_xprompt.md` and the main
workflow prompt):

```text
You are researcher grk in a 5-researcher swarm.
…independence boilerplate…
: #research(suffix=grk)
```

`{{ prompt }}` rendered as a lone colon. The question is absent. I only
found it because I looked at the multi-prompt file and the env var that
points at it. A researcher that followed the prompt as written would have
written a report about "write a markdown file under 202610/".

`xprompts.json` for this run records the swarm with `"positional": []` and
`"named": {}` on the child unit (named flags still took effect, because
grok/muse/gemini ran). The `#research` expansion then filled the rest of
the user prompt with write/register instructions.

### Cause

Both shorthand binders require a **space** after `::`:

- `_consume_trailing_shorthand_text` (`src/sase/xprompt/processor.py`):
  `after.startswith(":: ")` or `": "`. `::\n` matches neither and returns
  `[]`.
- `_preprocess_paren_shorthand` (`src/sase/xprompt/_parsing_shorthand.py`):
  `after_paren.startswith(":: ")`. `)::\n` is a no-op.

I reproduced this in the workspace venv:

| Source | Bound payload |
| --- | --- |
| `#research_swarm(args)::\nCan you do some research…` | **unbound** (source unchanged) |
| `#research_swarm(args):: Can you do some research…` | bound |
| `#research_swarm(args):: \nCan you do some research…` | bound (space before newline) |

ACE's `#name::` line shorthand invites pressing Enter immediately after
`::`. Docs show `#template(style=formal):: Please review…` with a space.
The parser and the PIW disagree at the newline. Tests cover
`#name(args):: text` on one line
(`tests/test_xprompt_processor_shorthand.py`) and
`#!research_swarm: some topic` (`tests/test_xprompt_loading.py`). They do
not cover `)::` at end of line.

This is not a hypothetical. It happened on this swarm.

### Fix

This is a **sase parser bug**, not a plugin-only change.

- Treat `::` followed by space, newline, or EOF as double-colon shorthand
  in both `_consume_trailing_shorthand_text` and
  `_preprocess_paren_shorthand`.
- Add a regression test whose source is exactly the `rsa`-style launch:
  `#research_swarm(gemini=true,grok=true)::\n<multiline question>`.
- In the swarm xprompt, **refuse to launch researchers when `prompt` is
  empty**. Render a hard error segment, or pass `should_run=false` for
  every researcher and have the lead report the empty question. Silent
  empty `{{ prompt }}` is unacceptable for a required input.

Until the parser is fixed, the `rsa` chezmoi snippet should put a space
after `::` (`:: $1` already does when `$1` is same-line; ACE newline
launches do not).

## What a good research swarm is

Recent multi-agent results converge on a few design rules. They map cleanly
onto this xprompt.

### Isolated generation, then aggregation

Du et al. 2023/2024 ([arXiv:2305.14325](https://arxiv.org/abs/2305.14325))
showed multi-agent debate can improve factuality. Later work is much more
cautious:

- **Unguided homogeneous debate is expensive groupthink.**
  [arXiv:2605.00914](https://huggingface.co/papers/2605.00914): isolated
  self-correction beat debate; debate used 2.1–3.4× tokens; sycophantic
  conformity reached 85.5% modal adoption.
- **Cognitive-diversity debate is not the driver.**
  [arXiv:2609.35875](https://arxiv.org/abs/2609.35875): debate beats a
  single agent, but at matched budget it ties or loses to self-consistency
  sampling. Almost all of debate's benefit is in the **first exchange**.
- **Self-organizing teams fail to use their expert.**
  [Pappu 2026](https://proceedings.mlr.press/v306/pappu26a.html): LLM teams
  average expert and non-expert views; losses up to 41.1%. Consensus-seeking
  rises with team size.

The swarm's "do not read your peer" rule is the right prior. Keep it.

### The bottleneck is the aggregator, not the roster

Wang et al. 2024 (Mixture-of-Agents, [arXiv:2406.04692](https://arxiv.org/abs/2406.04692))
and Li et al. 2025 (Self-MoA, [arXiv:2502.00674](https://arxiv.org/abs/2502.00674))
disagree on whether mixing models helps. Maryanskyy 2026
([arXiv:2603.20324](https://arxiv.org/html/2603.20324v1)) reconciles them:
**diversity helps only if aggregation is selection, not blending.**

In that experiment, judge-based selection of a diverse team won 0.810
against a single-model baseline. MoA-style synthesis of the **same**
candidates won 0.179 — worse than the baseline on every one of 42 tasks
(ΔWR = +0.631 for selection over synthesis). Majority vote sat at chance
(0.496). Homogeneous Opus×3 with a judge sat at 0.512.

The current lead prompt says "merge the strongest findings … resolve
conflicts, cut duplication." That is closer to selection than to blending,
but it never says:

- do not average disagreements
- do not treat five reports as five equal votes
- keep a disagreement table
- weight by evidence quality, not by how many researchers said it
- a weaker model in the deluxe roster (muse with a `warn` advisory,
  `agy/gemini-3.8-flash-high`) is a source of orthogonal errors, not a
  vote

Without those rules, deluxe `rsa` launches (this one) are at risk of
exactly the synthesis failure mode the literature measured.

### Roles beat sameness when the work can be split

[Theory of Scene (arXiv:2609.32939)](https://arxiv.org/abs/2609.32939):
homogeneous agents without a public role hit a "symmetry trap" — they
collide on work they should split and diverge on work they should share.
A public role plus shared scene is enough to divide labor.

Anthropic's deep-research coordinator skill does this: decompose into
MECE angles, assign one researcher per angle, then a writer who does
**no extra research**. SASE's swarm does the opposite: five copies of
the same prompt, different models, and a lead who **does** extra research.

Both are valid. They optimize different things:

| Mode | What you buy | Cost |
| --- | --- | --- |
| **Ensemble (today's default)** | Independent conclusions from different model families; the lead can select | Five overlapping literature reviews |
| **Coverage (opt-in)** | Broader ground, less duplicate tool work | Weaker cross-check on any one claim |

Default should stay ensemble. Coverage should be an opt-in `mode=`.
Persona-only diversity is a tax ([arXiv:2609.35875](https://arxiv.org/abs/2609.35875));
if coverage mode is added, assign **angles and source classes**, not
personas.

### A research report needs a contract

The research sidecar README already states the contract:

> Research should record the question, evidence, alternatives, and a clear
> recommendation.

The researcher prompt never says this. `#research` only says **where** to
write and how to register. Anthropic's researcher notes template (Takeaway /
Cited Findings / Inferences / Gaps, every claim sourced) is a better
producer contract for a downstream synthesizer.

This commute-audio `__grk.md` from earlier today shows what a good
independent report looks like when the researcher invents a structure:
question, recommended solution first, numbered decisions, prior-art
delta, corpus measurements. That structure is not required, so quality
will keep depending on the model.

## Finding 2 — the researcher prompt is almost entirely independence boilerplate

Each researcher segment is:

1. identity + peer names + "do not read peers" (necessary)
2. `{{ prompt }}` (the actual work)
3. `#research(suffix=…)` (path + `sase artifact create`)

Missing, and cheap to add:

- Restate the research question in a labeled block so it cannot drown in
  boilerplate (and so a parser miss is visible).
- Rubric: question, method, evidence with citations, alternatives,
  recommendation, confidence, open questions.
- Required first moves: open the research sidecar; `sase plan search --kind research`
  (and/or `sase artifact list`) for related prior work; `sase artifact read`
  for anything you actually use; `sase repo open` for code you cite.
- Frontmatter the ref provider already declares: `create_time`,
  `updated_time`, `status`, `tags`.
- `sase var set` a small index of the report (see next section).
- Do not invent a peer's path; do not treat `#research`'s write
  instructions as the topic.

The five researcher bodies are copy-pasted. Independence text has already
had to be updated in five places (see `plans:202609/research_swarm_independence.md`).
A Jinja loop over `researchers` that emits `---` segments would make the
next rubric change a one-edit change. Segment count is not a platform
cap; "up to eight authored segments" in the plugin docs is descriptive.

## Finding 3 — SASE features the swarm leaves on the table

### `sase var` (highest unused leverage)

Documented in `docs/xprompt.md` and the `/sase_var` skill. A waiter
renders `{{ agents["research.36.cdx"].bottom_line }}`. Caps are small on
purpose (8 KiB leaves, 64 KiB JSON): **index the report, do not store
it.**

Have every researcher (and the lead) set:

```bash
sase var set bottom_line --value "…"
sase var set confidence --value medium
sase var set report_label --value "research:202610/…__grk.md"
sase var set open_questions --json --value '["…"]'
sase var set sources --json --value '["research:…","plan:…"]'
```

The lead's prompt can print a comparison table from `agents[…]` **before**
it reads the full markdown. `wait.artifacts` stays the path to the bodies.
Vars are the index. Today the lead's only structured input is a list of
paths.

### Artifact links

`sase artifact link add` already supports `derives-from`, `related`,
`cites`. The lead prompt only says "SASE derives your plan's links from
the artifacts you read this turn," which is about **plan** files, not the
research report.

Bob already has an open task: "Research lead in `#research_swarm` should
be told to link to related research files" (`sase_art_links.md`,
scheduled 2026-10-06). That is a prompt change:

- lead: `derives-from` each researcher `research:` ref
- lead: `related` to prior research it actually used
- researchers: `related` to prior reports they built on

Do not ask agents to hand-edit generated link tables.

### `#research(report_target=…)` and `%proc` — stop making the lead a file mover

Researchers pick independent stems at the month-dir root. The lead then
picks `<name>`, creates `<name>/`, and `mv`s each file, preserving
suffixes. That is mechanical, collision-prone, and burns lead context.
`#research` already accepts `report_target`. `%proc` is a first-class
launch unit (`docs/xprompt.md`).

Write drafts into a clan-scoped directory from the start:

```text
#research(report_target=research.{@1}/__cdx.md)
```

Then either the lead or a `%proc` renames `research.{@1}/` to a
descriptive `<name>/`. The lead's job becomes: read, select, write
`<name>.md` / `<name>__final.md`. The README's
`<YYYYMM>/<topic>/` layout is unchanged; only who does the `mv` changes.

### Shared starting corpus, still independent conclusions

Independence forbids reading **this swarm's** peer reports. It already
allows "shared input material, and unrelated prior research." The swarm
does not **give** that material, so five models each rediscover the
xprompt, the plugin docs, and the same 202609 plans.

Inject a short reading list into every researcher segment:

- the xprompt source (`sase-research-artifacts` via `/sase_repo`)
- `docs/xprompts.md` and `README.md` of that plugin
- `sase plan search --kind research` hits for `research_swarm` / the topic
- the research sidecar README (the rubric)

They still form independent conclusions. This is how you get diversity of
**judgment** without diversity of "did anyone find the file."

### `wait.artifacts` is already the right handoff

Keep it. Do not go back to `wait.chats`. The raw-protected loop on the
lead and linker is the correct pattern. Pair it with `sase var` rather
than replacing it.

### Image should not `#fork` the lead

The image segment is:

```text
%wait:research.{@1}.final … #fork:research.{@1}.final #research/image
```

`#research/image` does not name a file; it relies on the forked
transcript. That is the most expensive context in the swarm, used to
draw a PNG. The linker already finds `__final.md` through
`wait.artifacts`. Image should do the same: wait, read the registered
report, draw. Forking also fights the independence rule (the image agent
inherits the lead's reasoning).

### `#research/more` as an opt-in gap fill

`#research/more` exists and is unused by the swarm. After the lead
writes, an opt-in `more=true` (or a single `%repeat` slot with `STOP`)
can extend `<name>__final.md` on listed gaps. Default off: it adds a
serial agent. Do not hide this inside the lead; a single-turn lead cannot
come back later.

### `sase questions` is the wrong default intake

The deep-research skill asks clarifying questions first. `sase questions`
is a **handoff that kills the turn** and parks the session on a question
gate. If even one researcher asks, that member blocks the lead (`%wait`
releases on completion, and a QUESTION session is not complete). Do not
put `sase questions` in researcher prompts.

If intake is wanted, make it a **single optional intake agent before the
researchers**, with the existing `wait=` input already gating researchers.
That reuses `#research_swarm(wait=intake)`.

### Goals: designed, not built

`research:202609/xprompt_swarm_goals.md` already says the right thing: one
clan draft, researchers `keep_open`, lead claims with the report as
evidence. Gap: if image or linker `%wait`s on the lead, the host's
contributor rule would make the **image agent** the claimer. When G4
lands, name the claimer (lead, or linker if it is the publisher). Do not
build a parallel goal mechanism in the xprompt.

### Beads, memory, mentors

Researchers are not told they may file follow-up task beads through
`/sase_new_task`. Five researchers filing the same discovery would
duplicate; tell **only the lead** to file beads for follow-up
implementation work, after synthesis.

`sase memory read` is unused. For SASE-internal topics (this one), a
one-liner "read glossary:xprompt-swarm and the xprompts.md reference
note" would have saved rediscovery. Keep it as a suggested first move in
the rubric, not a hard-coded list of notes (the topic varies).

Mentors on the lead report are possible and probably not worth a swarm
segment. The linker is already an editorial pass.

### Queue, tribe, provider gating, Highlights hook

These are in good shape. Do not churn them.

- `%q(1.5x, w=0.25)` fits five quarter-weight researchers under a 1.5×
  budget. Give the lead a slightly higher priority when `priority` is
  unset so it starts the moment the last researcher finishes; optional.
- `tribe=research` plus clan summary already carry the question for the
  Agents tab. Prefer that summary over the independence boilerplate when
  goals start taking prompt excerpts.
- Hard-disable gating is correct. Soft-disable still running is correct.
- Highlights hook globs correctly ignore `__*.md` drafts and `__final.md`.
  Do not put `final` in `agent_name_globs` (that vetoes the lead on the
  no-linker path). Already documented in `provider.py`.

## Finding 4 — deluxe roster vs aggregator quality

`rsa` adds muse (`warn`: trains on your data) and gemini flash-high, plus
image/linker. Self-MoA says mixing weaker models **hurts if you blend**.
Maryanskyy's exploratory cell says a weaker model can **help a strong
selector** by adding orthogonal errors, and it lowers cost.

So: keep muse/gemini opt-in. Make the lead a strong selector (finding 3's
aggregation rules). Do not promote muse/gemini into the default pair
until the lead's selection rubric exists. The muse default-off because of
the training advisory is independently correct.

`lead_model` default `@xlarge` is right. The aggregator is the bottleneck;
it should stay a frontier model. `linker_model` `@xlarge` is expensive
for an editor; after the linker prompt has been stable for a while,
consider `@large` for the linker only.

## Finding 5 — image failure parks publication

Documented today: named waits release on completion, so a **failed**
image agent leaves the linker parked, no `<name>.md`, no PDF. Recovery
is rerun the same `research.<N>.image` name or kill the linker.

This is the one new SASE primitive I think is justified:
`%wait(on=success)` / optional waits. Failed producers would release
waiters with empty `wait.artifacts` for that name, and the linker already
has "if the image agent completed without a PNG, publish without it."
Extending that to "if the image agent failed, publish without it" needs
the wait semantics to change. A plugin cannot fake it: `%wait` is host
behavior.

Until then, consider making the linker wait **only on the lead**, and
poll for the PNG with a short `%wait(time=…)` floor plus filesystem
check — worse than success-only wait, but it unblocks publication.

## Finding 6 — critique belongs after publish, default off

`plans:202609/research_swarm_critique.md` is still wip. The linker plan
removed critique to free a segment and because almost no one passed
`critique=true`. Bob still has "Add `crique` agent to `#research_swarm`."

Bring it back as **opt-in, after the linker** (or after the lead when
linker is off):

- fresh context, `%wait` on the published report, no `#fork`
- write `<name>__critique.md` beside the canonical report
- companion, not a rewrite; the Highlights PDF stays the lead/linker
  document
- never the goal claimer

Default off keeps today's fast path byte-identical, which that plan
already required. Nine segments is fine.

## Finding 7 — `#git:home` and other open product gaps

Bob still has, as scheduled work rather than swarm-prompt work:

- Make `#research_swarm` work with `#git:home` (high, 2026-10-04). The
  swarm hard-codes `sase repo path research`. Home/chezmoi has no
  research sidecar.
- Make Grok an optional third member — **already done** (`grok=true`).
  The bob task is stale.
- Lead should link related research — **prompt change, finding 3**.

Do not let the swarm invent a second research root. If `git:home` should
work, the research sidecar role (or a fallback directory) has to exist
for that project; that is configuration, not a new xprompt feature.

## Alternatives I considered and rejected

| Idea | Why not (as default) |
| --- | --- |
| Multi-round debate among researchers | Sycophancy, 2–3× tokens, first exchange captures most benefit; independence is the feature |
| Deep-research-style coordinator that always decomposes | Destroys the heterogeneous-model ensemble this swarm is for; offer as `mode=coverage` |
| Always-on linker | Extra serial `@xlarge` on every `rs` dispatch; keep opt-in / implied-by-image |
| Always-on critique | Same; unused when it existed |
| Lead also draws the infographic | Cannot wait on a child it has not launched; hook fires on first ADD |
| Deterministic linker script | Cannot place semantic cross-links or restructure prose; fine as a later URL/anchor checker `%proc` |
| `sase questions` inside researchers | One question parks that member; lead waits forever |
| New research runtime in sase-core | The plugin + existing directives already compose the pipeline |
| Store report bodies in `sase var` | Explicitly out of spec; vars are small handoff values |

## Ranked improvements

Rank is **leverage / cost for this xprompt**, not a general multi-agent
wishlist. "Do now" items are parser or prompt changes in
`sase-research-artifacts` plus one sase shorthand fix.

### Do now

1. **Fix `)::\\n` / `::\\n` shorthand binding** in sase, and **fail closed
   on empty `prompt`** in the swarm. This run shipped researchers a colon
   instead of a question. Highest severity, already reproduced.
2. **Researcher rubric + labeled restatement of the question** in every
   researcher segment. Match the sidecar README. Require prior-art search
   via `sase plan search --kind research` and `sase artifact read`.
3. **Lead selection protocol:** disagreement table; select the best
   argument; do not average; do not equal-weight muse/flash; keep
   dissent as alternatives; do your own research on gaps (already
   asked, keep it).
4. **`sase var` index** from every researcher (`bottom_line`,
   `confidence`, `report_label`, `open_questions`, `sources`) and a lead
   comparison table from `{{ agents[...] }}`.
5. **Clan-scoped `report_target`** so drafts land in
   `research.{@1}/__<short>.md`. Demote the lead's `mv` to a `%proc` or
   a short rename step.
6. **Artifact links** from the lead (`derives-from` drafts, `related`
   prior research). Closes the existing bob task with a prompt change.

### Do next (still mostly the plugin)

7. **Stop `#fork`ing the lead into image.** Image waits and reads
   `wait.artifacts` like the linker.
8. **Shared reading list** in researcher prompts (plugin docs, this
   xprompt, prior research hits). Independence of **conclusions** stays.
9. **DRY researcher segments** with a Jinja loop over `researchers`.
10. **Opt-in `mode=coverage`:** a cheap planner assigns complementary
    angles; default remains ensemble.
11. **Opt-in critique after publish** (`critique=true`), companion
    `__critique.md`, default off, not the claimer.
12. **Opt-in `#research/more` gap fill** after the lead lists gaps.
    Default off.

### Do when SASE grows the primitive

13. **`%wait(on=success)`** (or optional waits) so a failed image agent
    does not park the linker. Justified host change; document recovery
    until it exists.
14. **Goals G4:** one clan draft; researchers `keep_open`; claimer is
    the lead, or the linker when it publishes; image never claims.
    Follow `research:202609/xprompt_swarm_goals.md`.
15. **`#git:home`:** give that project a research sidecar or an explicit
    fallback root. Do not special-case the xprompt.

### Explicitly do not do

16. **Unguided debate rounds** among researchers.
17. **Make coverage-mode / coordinator decomposition the default.**
18. **Always-on linker or critique.**
19. **A new sase-core research orchestrator.** Compose what exists.
20. **Treat muse/gemini as default equals** before the lead selects
    rather than averages.

## Suggested shape after the "do now" pass

```text
#research_swarm(prompt, grok=?, muse=?, gemini=?, image=?, linker=?,
                mode=ensemble|coverage, critique=?, more=?)

researchers  →  clan dir __<short>.md + sase var index + artifact register
     ↓ wait.artifacts + agents.*
lead         →  select (not blend) + own research + <name>__final.md
                + derives-from links + optional bead follow-ups
     ↓
image?       →  wait.artifacts, no fork, PNG beside the report
linker?      →  <name>.md (hook-eligible), embed PNG if present
critique?    →  <name>__critique.md
more?        →  #research/more on listed gaps
```

Default `rs` (codex+claude+lead) stays three agents and should stay fast.
Deluxe `rsa` stays the quality path, and becomes one once the question
actually reaches the researchers and the lead selects.

## Confidence and gaps

- **High:** prompt-binding bug (reproduced against the parser);
  independence-then-select topology; `sase var` / artifact links /
  `report_target` underuse; image-fork cost; empty researcher rubric.
- **Medium:** how often ACE launches `::` at EOL in the wild (this run
  did; I did not measure historical multi-prompts); whether muse/flash
  currently drag deluxe consolidations (would need a sample of
  `__final.md` vs drafts).
- **Low / not checked:** whether other researchers in *this* swarm also
  missed the question (I did not read their prompts or reports, per
  independence). If they recovered it the same way I did, the bug is
  still real; if they did not, their reports are off-topic and the lead
  will see it.
- **Out of scope:** rewriting the Highlights hook, changing queue math,
  renaming tribes, moving the xprompt back into sase core.

## Sources

### This run (primary evidence)

- `~/.sase/multi_prompts/202610/gh_sase_org__sase-multiprompt-261001_120547.md`
- `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202610/01/20261001120549/raw_xprompt.md`
- `…/submitted_xprompt.md`, `…/workflow-tmp_261001_120750-main_prompt.md`,
  `…/xprompts.json`
- Workspace venv reproduction of `_consume_trailing_shorthand_text` and
  `preprocess_shorthand_syntax`

### Plugin and host (read via `/sase_repo` / workspace)

- `sase-research-artifacts`: `xprompts/research_swarm.md`,
  `research.md`, `research_image.md`, `research_more.md`,
  `docs/xprompts.md`, `docs/architecture.md`, `default_config.yml`,
  `provider.py`, `tests/test_xprompt_loading.py`, `README.md`, `AGENTS.md`
- sase: `docs/xprompt.md` (wait.artifacts, shorthand, `%proc`, `%q`),
  `src/sase/xprompt/processor.py`,
  `src/sase/xprompt/_parsing_shorthand.py`,
  `tests/test_xprompt_processor_shorthand.py`
- Research sidecar `README.md`
- Plans: `202609/research_swarm_critique.md`,
  `202609/research_swarm_independence.md`,
  `202609/research_swarm_linker_agent.md`,
  `202610/research_swarm_gpt61sol.md`
- Prior research: `202609/xprompt_swarm_goals.md`,
  `202609/research_swarm_linker_agent/research_swarm_linker_agent.md`
- Bob: `sase.md` (critique, grok member, git:home),
  `sase_art_links.md` (lead should link related research)
- Skills: `/sase_var`, `/sase_questions`, `/sase_chats`; Anthropic
  `deep-research/SKILL.md` and `references/researcher.md`

### External

- Wang et al., Mixture-of-Agents, [arXiv:2406.04692](https://arxiv.org/abs/2406.04692)
- Li et al., Self-MoA, [arXiv:2502.00674](https://arxiv.org/abs/2502.00674)
- Maryanskyy, Selection bottleneck, [arXiv:2603.20324](https://arxiv.org/html/2603.20324v1)
- Du et al., Multi-agent debate, [arXiv:2305.14325](https://arxiv.org/abs/2305.14325)
- The Cost of Consensus, [arXiv:2605.00914](https://huggingface.co/papers/2605.00914)
- Beyond Symmetric Agents, [arXiv:2609.35875](https://arxiv.org/abs/2609.35875)
- Theory of Scene, [arXiv:2609.32939](https://arxiv.org/abs/2609.32939)
- Pappu, Multi-Agent Teams Hold Experts Back, [ICML 2026](https://proceedings.mlr.press/v306/pappu26a.html)
- Okawa, Biased Consensus in Multi-Agent LLM Debates, [ICML 2026](https://proceedings.mlr.press/v306/okawa26a.html)
- Ganglani, 7 AI Agent Swarm Patterns, [2026](https://www.kunalganglani.com/blog/ai-agent-swarm-coordination-patterns)
