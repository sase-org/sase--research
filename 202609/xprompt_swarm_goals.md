# How xprompt swarms get their goals

_Research · 2026-09-27 · project: sase · status: **designed, not built**_

> **Bottom line.** A swarm gets **one** goal, not one per agent. The host binds every
> member of the clan to a single shared **draft** goal at launch. The **first member to
> run `sase goal name`** writes its title and outcome, and every later member gets
> `already named` back. The `#research_swarm` researchers don't get goals of their own.
> They are **contributors** to the swarm's goal: each writes its `__<short>.md` report and
> finishes with `keep_open`. The **lead** (`.final`) is the only member that can claim
> the goal, and it claims with the consolidated report as evidence. You get **one**
> "ready to verify" signal instead of 3–5 `done` pings.

---

## 1. Where this stands

| Item | State |
| --- | --- |
| Design | [`sase_goals_design`](sase_goals_design/sase_goals_design.md) (lead synthesis of 5 reports, 2026-09-27) |
| Delivery plan | [`sase_goals_epic_roadmap`](sase_goals_epic_roadmap/sase_goals_epic_roadmap.md): six epics, **G1 → G6** |
| Code | None yet. `git grep` finds no `goal_id`, `%goal`, or `goal_binding` in `src/` |
| Beads / plans | No Goals epic and no plan so far. The roadmap says to write only the G1 plan first |
| Swarm goals land in | **G4**, "Every agent has a goal". Its phase 2 is `launch-drafts: … clan-shared drafts` |

## 2. The mechanism: the host binds, then the first member names

At launch, a pure Rust resolver (`resolve_goal_binding`) goes down a ladder, and the
first rung that matches wins:

```text
explicit %goal ─► session ─► plan ─► ⟪clan⟫ ─► parent ─► bead ─► routine ─► draft
```

A swarm member usually has no explicit goal, session, plan, or parent. It stops at the
**clan** rung: _"every member of a clan launched together shares one goal."_ Because
nothing names that goal yet, it starts as **one machine-local draft** for the whole
clan. Two rules apply to it:

- **Naming is compare-and-swap.** The first `sase goal name <draft> -t … -o …` wins.
  Siblings that call it later get `already named: "<title>"` and exit 0.
- **Adopt comes before naming.** The intake block tells each agent to run
  `sase goal list` first. If an active goal already describes the request (for example,
  a re-run of the same research), the agent runs `sase goal adopt` with a written reason
  instead of naming a new goal.

Nobody hand-writes goals here: agents can create no goal except their own draft. The
origin records the **root prompt digest** (the swarm prompt before segmentation) apart
from each member's unit-prompt digest.

## 3. Walkthrough: `#research_swarm(prompt="…")`

```text
you ─ #research_swarm ─► host: clan research.N  ──►  ONE shared draft  ⌖7k2mq
 │
 ├─ research.N.cdx   intake block → `sase goal name` (wins) → writes __cdx.md → keep_open
 ├─ research.N.cld   intake block → `sase goal name` → "already named" → __cld.md → keep_open
 │                    (grk / mus / gem, if enabled, behave the same way)
 │
 └─ research.N.final  %wait on every researcher → synthesizes <name>.md
                      → CLAIM ─► one GoalVerify gate ─► you: Verify · Reject · Drop
```

| Member | Role (derived by the host) | Goal text it sees | Finalizer decision | Can claim? |
| --- | --- | --- | --- | --- |
| `.cdx`, `.cld`, … | **contributor**, because the lead waits on it | ~80-token intake block (draft) | `keep_open`, e.g. "wrote `__cdx.md`" | no |
| `.final` (lead) | **owner** | the named goal, as a ~40-token `SASE GOAL ⌖… — …` line¹ | **`claim`** | yes, once no contributor is live |

¹ _Inference: the lead spawns after the researchers finish, so its draft should already
be named when it starts._

**What the lead's claim looks like.** It is a _research/document_ claim, so it needs at
least one `research:` or `file:` ref that a contributor produced. It also needs a claim
sentence of at most 280 characters, 1–3 **check it** steps, and any **gaps**. The
strength badge shows `documented`. The researchers' reports can go in as extra evidence.

## 4. So what _is_ a researcher's goal?

The swarm's goal is the researcher's goal. Its own report is **evidence**, not a goal.

| | Example |
| --- | --- |
| **Title** (≤ 60 chars) | `Research: how xprompt swarms get their goals` |
| **Outcome** (one sentence) | "A consolidated report explains how swarm goals are bound, named, and claimed, and gives a recommendation." |
| **Author** | Whichever researcher reached `sase goal name` first, from its own view of the prompt |
| **Closed by** | The lead's claim, then **your** verdict. An agent never closes a goal. |

## 5. When does a swarm actually get a goal?

This is the roadmap's integration-matrix row for a 5-agent research swarm:

| After | Swarm behavior |
| --- | --- |
| G1 ledger · G2 binding | **Unbound.** Binding fails open. Only an explicit `%goal:<id>` binds a swarm this early. |
| G3 claims | No claim yet, because there is no goal to claim |
| **G4 drafts** | **One goal, lead-only claim**. Acceptance test: _"a 5-agent swarm gives 1 goal and 1 claim."_ |
| G5 tab | Contributor pips on the goal card, and numbered jumps to each researcher |
| G6 cutover | Researcher `done` pings go silent. The claim is the **one** signal. |

## 6. Gaps found by checking the design against the actual xprompt

1. **The lead doesn't always claim.** ⚠️ `critique=true` and `image=true` add members
   that `%wait:research.N.final`. Under the host's role rule, _"an agent another pending
   agent waits on is a contributor"_, the **lead becomes a contributor**, and the claim
   goes to whichever of `.critique` or `.image` finishes last. That means an infographic
   agent could make the claim. The design's statement that "the lead claims with report
   refs" is true only with the default flags.
   _Suggestion for G3/G4 planning:_ let a swarm name its claimer, or keep image/fork
   helpers from ever claiming.
2. **Draft titles and names see boilerplate.** Every researcher segment opens with
   "You are researcher cdx in a 2-researcher swarm…". That text becomes both the draft's
   prompt-excerpt title and the context the winning researcher names from. The lead's
   `%clan(research.N, …, summary=[[RESEARCH PROMPT: {{ prompt }}]])` already carries the
   real question.
   _Suggestion:_ build the clan draft's excerpt from the root prompt or the clan summary.
3. **Explicit `%goal` on a swarm before G4 is unverified.** G2 generalizes
   `_tab_inheritance` into shared directive inheritance. Whether a `%goal` on the swarm
   prompt reaches every segment should be one row in G2's frozen launch-path matrix.

---

**Sources:** the design and roadmap reports linked in §1 (read via `sase artifact read`),
`sase xprompt show research_swarm` (plugin `sase_research_artifacts@7be5cae`), and the
glossary entries _Xprompt Swarm_ and _Agent Clan_.
