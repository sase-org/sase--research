# Making `#research_swarm` produce better research (`mus`)

Research question: how can the `#research_swarm` xprompt swarm produce better
research — both by applying what is known about building good research-agent
swarms, and by taking better advantage of existing sase features (recommending
new sase features only where truly justified)? Ends with a ranked list of
improvements to consider.

Method: I inspected the installed swarm definition (`sase xprompt show
research_swarm`, all 8 segments), the `#research` / `#research/more` /
`#research/image` leaves it composes, the `#fork` and `sase var` skills it
could compose, the `%wait` failure semantics in `docs/xprompt.md`
(~lines 2514–2527), the research sidecar README conventions, and my own prior
unrelated research on the swarm's `linker` agent (202609). I did not consult
any peer report from this swarm.

## How the swarm works today (load-bearing facts)

- Five optional per-provider researchers (`cdx`, `cld`, `grk`, `mus`, `gem`;
  only codex+claude default on) each get an identical brief: a strong
  independence firewall paragraph plus `{{ prompt }} #research(suffix=<short>)`.
  Each writes `<stem>__<suffix>.md` and registers it via `sase artifact
  create`.
- The lead (`research.<N>.final`) `%wait`s on every researcher, reads each
  report through `sase artifact read`, does its own gap-focused research,
  moves drafts into `<month>/<name>/`, writes the consolidated report, and
  registers it.
- Optional `image` and `linker` agents finish the pipeline (infographic,
  publishable `<name>.md` with validated links).
- Queue budget (`runners`, default `1.5x`), priority, and `wait` passthrough
  are already parameterized on every segment.

## Strengths to preserve

These already match research-swarm best practice; do not regress them:

1. **Blind independence.** The firewall paragraph (no peer reports, no peer
   transcripts, shared sources allowed) is exactly the blind-review pattern
   that keeps multi-agent swarms from collapsing into correlated
   groupthink. Keep it verbatim.
2. **Lead does its own research.** The lead is instructed to prioritize gaps,
   weak evidence, and disagreements — the generator-critic pattern, not a
   summarizer. This is the highest-leverage segment; protect it.
3. **Fail-closed lead input matching.** Matching researcher reports by
   `wait_name` plus canonical `__<suffix>.md` label, never by list order, and
   stopping on missing/ambiguous input, is correct provenance discipline.
4. **Audited reads, durable snapshots.** `sase artifact read` for context and
   `sase artifact create` registration give the pipeline lineage the TUI,
   search, and Highlights PDF all consume. Every new segment should follow
   the same convention.

## Gaps and ideas

### 1. Zero role diversity: five identical briefs

Every researcher receives the same prompt and the same `#research` leaf, so
the swarm's only source of diversity is provider-model variance. The
literature on parallel research agents is consistent: independent agents with
identical instructions produce correlated coverage and correlated blind
spots; deliberately differentiated angles (adversarial/skeptic, prior-art
surveyor, practitioner/methodologist, cost-and-risk assessor) produce the
disagreement that makes the lead's synthesis valuable. Today's swarm pays
for N researchers and often gets N versions of the same report.

Fix options, cheapest first: (a) an optional `angles=` text input appended
per-researcher ("extra angle for your report only"); (b) 2–3 built-in angle
variants assigned round-robin when more than that many researchers run;
(c) distinct search-strategy hints per provider. (a) is nearly free and
composable with everything below.

### 2. No shared output contract, so the lead merges free-form prose

Researchers are told to "write this research" with no required sections, no
citation convention, and no confidence language. The lead must therefore
merge N unpredictably structured reports, and the linker later validates
links the researchers were never told to emit as checkable URLs. A shared
contract would make synthesis mechanical where it should be mechanical, so
the lead spends effort on judgment, not archaeology.

Concretely, require four short sections in every researcher report: Bottom
line; Ranked findings (each with evidence links as full URLs); Confidence
and open questions (what was *not* verified); Method and sources consulted.
Full URLs are load-bearing: the linker already `curl`s them, and bare
"per the docs" citations are unverifiable. Put the contract in `#research`
itself or a shared preamble segment so `#research/more` follow-ups inherit
it.

### 3. One failed researcher parks the lead forever

Per `docs/xprompt.md`, failed runs never satisfy `%wait`: "the dependent
agent stays parked until a later successful run of the same dependency name
appears," with a `wait_checks` notification. So a single researcher death
(flaky provider, rate limit, bad launch) blocks consolidation of all the
healthy reports, and the lead prompt's only instruction is "stop and report
the missing input instead of guessing" — fail-closed with no recovery path.

This is the swarm's worst robustness gap. Options: (a) document an explicit
recovery runbook in the lead segment (how to relaunch exactly the missing
`suffix` researcher into the same clan, or when to proceed with N−1 and
record the gap); (b) a `quorum=` input (e.g. "proceed when ≥2 of 3 report,
noting the absence"); (c) a genuine sase feature — wait-on-settled rather
than wait-on-success for named agents. (a) costs nothing and should ship
regardless; (c) is the only item here that justifies new platform work, and
even it could start as (b) implemented in-prompt.

### 4. No time-box: a hung researcher is indistinguishable from a slow one

Related to (3): researchers get no effort guidance ("a complete partial
report beats a perfect missing one"), and the lead cannot tell stall from
depth. Add one sentence to each researcher brief time-boxing the
investigation and directing a graceful partial write-up, plus a hint in the
lead about the `wait_checks`/monitor recovery path. Pure prompt text, zero
platform cost.

### 5. No structured digest for triage and tooling

The lead template renders only `wait.artifacts` markdown entries. If each
researcher also published a small structured digest via `sase var set`
(e.g. `summary`, `top_findings` JSON, `confidence`, `open_questions`,
`report_path`), three things unlock: the lead can render the digests as a
triage scaffold before deep-reading; future tooling can diff digests to
route follow-up (`#research/more`) to the right report; and `sase var list`
gives durable, queryable swarm telemetry without opening files. Small
prompt addition plus a few lines of lead-template Jinja.

### 6. Ambiguity fans out instead of being resolved once

Each researcher independently resolves an ambiguous `prompt`, so divergence
often reflects different guesses about the question rather than different
findings. For high-stakes topics, a 30-second pre-swarm clarification
(`sase questions`) or a one-paragraph shared brief pinned in every segment
would remove the cheapest source of synthesis conflict. Recommend an
optional `brief=` input: when supplied, it is prepended verbatim to every
researcher and the lead.

### 7. Claim-level provenance ends at the lead

Artifact registration tracks *file* provenance well, but inside the
consolidated report there is no record of which claim came from which
researcher (or from the lead's own research). The removed `critique` agent
used to re-verify synthesis fidelity adversarially; without it, a lead that
mismerges two reports is undetectable. The cheap substitute is a forcing
function, not a new agent: require the consolidated report to carry a short
provenance appendix mapping each major claim to its source report(s), and
require disagreements-between-researchers to be surfaced explicitly rather
than smoothed over. Consider restoring a critique-lite check later only if
provenance appendices prove insufficient.

### 8. Drafts land in a shared flat namespace

Researchers write `<month>/*.md` at the month root; the lead later moves
them into `<name>/`. Concurrent swarms in one month share that flat
namespace, and a lead that dies mid-move leaves orphans the hook globs
(`!20*/*__*.md`) hide but nothing reaps. Prefer namespacing drafts by
dispatch from the start (e.g. pass `report_target` with the clan id baked
in, or have `#research` accept a subdirectory), so the move step becomes
optional and orphans are attributable.

### 9. Provider defaults are a diversity decision wearing a cost costume

Only codex+claude default on; grok/muse/gemini default off. Since finding
(1) says model variance is currently the *only* diversity source, every
default-off provider weakens the mechanism the swarm relies on most.
Re-evaluate which defaults maximize finding-independence per dollar (two
different labs beats two runs from one lab), and say so in the input
descriptions so users choose deliberately. The `muse` warn-advisory note in
`muse_model` is a good precedent — extend that candor to the other toggles.

### 10. No quality telemetry, so improvements are untestable

Nobody records which researcher reports the lead actually cited, whether the
linker had to repair claims, or whether readers found the consolidation
useful. Without that loop, every item above is argued on principle. Cheap
telemetry: the provenance appendix (7) plus digest vars (5) already yield
cite-rates per researcher for free; log them (or just make them greppable)
and revisit defaults quarterly. Defer heavier eval (graded synthesis
fidelity, A/B briefs) until the cheap loop shows a question worth answering.

### 11. Preflight the Jinja in CI

The swarm body is intricate conditional Jinja (`provider_enabled`,
per-researcher peer lists, linker layout branches). A broken conditional
silently drops a researcher or misnames a suffix. If not already covered in
the `sase-research-artifacts` repo's tests, add expansion golden tests over
the researcher-toggle × linker × image matrix asserting segment counts,
suffix names, and wait wiring — the same discipline the core repo applies to
swarm expansion (`tests/test_xprompt_swarm_expansion.py`).

## Ranked list of improvements to consider

Ordered by expected research-quality gain per unit of effort; earlier = do
first.

1. **Add a shared researcher output contract** (Bottom line / Ranked
   findings with full-URL evidence / Confidence and open questions / Method
   and sources). Makes synthesis mechanical, feeds the linker's `curl`
   validation, costs only prompt text. (§2)
2. **Give researchers differentiated angles** — at minimum an optional
   `angles=` input, ideally built-in role variants round-robined across
   researchers. The single biggest lever on finding-independence. (§1)
3. **Write the lead's partial-failure runbook**: how to relaunch a missing
   `suffix` researcher into the same clan, and when to proceed with N−1
   plus a recorded gap. Turns the swarm's worst failure mode into a
   recoverable one with no platform work. (§3a)
4. **Time-box the researchers in-prompt** ("a complete partial report beats
   a perfect missing one"). One sentence per segment. (§4)
5. **Require a claim-provenance appendix and explicit disagreement
   surfacing in the consolidated report.** Replaces most of what the
   deleted critique agent provided, with no new agent. (§7)
6. **Publish per-researcher structured digests via `sase var set` and
   render them in the lead template.** Cheap triage scaffold today;
   cite-rate telemetry and targeted `#research/more` routing tomorrow. (§5)
7. **Add an optional shared `brief=` input** prepended to every segment, to
   stop ambiguity from fanning out into false disagreement. (§6)
8. **Namespace drafts by dispatch from the start** so the lead's move step
   is optional and orphans are attributable. (§8)
9. **Re-evaluate default-on providers as a diversity decision**, and
   document the independence-per-dollar tradeoff on each toggle. (§9)
10. **Mine the cheap telemetry** (cite-rates from provenance appendices,
    digest vars) before building heavier eval. (§10)
11. **Add expansion golden tests** over the toggle matrix in the plugin
    repo if missing. Correctness hygiene, not quality gain — hence last.
    (§11)
12. **New sase feature (only if 3 proves insufficient): wait-on-settled
    semantics** for swarm waits, so the lead can consolidate whatever
    resolved instead of parking on the first failure. Justify it with
    incident evidence from the runbook era, not in advance. (§3c)
