# How Coding Agents Use Documentation: Paper Summary and Lessons for SASE

> **Research query:** Summarize the points made by
> [arXiv:2608.20195](https://arxiv.org/abs/2608.20195). What can sase learn from this
> paper? Keep the report concise and easy to understand.

_Written 2026-10-16._

## Bottom line

- **The paper:** Gao and Chen observed real coding-agent sessions to see which
  documentation agents actually use. Their answer is mostly not the classic kind. Agents
  mainly read and write **agent-facing files**: instruction files (`AGENTS.md`,
  `CLAUDE.md`, skills) and their own working notes (plans and logs). Reading docs is
  rarely followed by testing, agents almost never follow links, and doc edits trail code
  edits.
- **For SASE:** the paper largely supports bets SASE has already made: memory-built
  instructions, audited memory reads, artifacts for plans, and host-owned verification.
  It points to four concrete improvements:
  1. Make pages self-contained, and keep them that way while the docs split epic
     (`sase-1le.20`) breaks up large pages.
  2. Put the fix in the error message itself.
  3. Check for missing doc updates at the end of the turn.
  4. Run the same measurement on SASE's own transcripts, which are richer than the
     paper's.

## The paper in brief

**Citation:** Zhijun Gao and Jing Chen (Peking University), _"From Agent Behaviour to
Agent-Friendly Documentation: An Empirical Study of How Coding Agents Discover, Read, and
Write Technical Documentation"_, arXiv:2608.20195v1, 20 Aug 2026. Categories: cs.SE,
cs.AI, cs.HC.

**Question:** Advice on "agent-friendly docs" (clear headings, runnable examples,
`llms.txt`) "rests on intuition about how agents _ought_ to behave rather than
observation of how they do." The authors measure the behavior instead.

**Data:** The authors use two datasets and never pool them:

- **Process data:** 557 sampled agent transcripts from SWE-chat, containing 94,813 tool
  events and 3,033 documentation events. Claude Code makes up 84% of the full corpus.
  The authors oversampled the other agents (OpenCode, Codex, Gemini CLI, and Cursor), so
  the sample is 68% Claude Code.
- **Artifact data:** 33,097 agent-authored pull requests from AIDev, across 2,807
  repositories with more than 100 stars.

Documentation events were classified by file path. A language model labelled the
ambiguous paths, and no human checked those labels. The authors report clustered
bootstrap intervals and stage-adjusted regressions.

## What it found

| # | Finding | Key numbers |
|---|---|---|
| 1 | **Most documentation agents touch is agent-facing.** Agent instruction files and agents' own working notes dominate. Classic docs are a small slice. | Instruction files 35.4%; working notes (plans, `thoughts/`, verification logs) 25.1%; README, architecture, API reference, and troubleshooting together ~11%. Instruction files get ~27× the interactions of API references. |
| 2 | **Reading docs leads to more reading, reasoning, and doc writing, not straight to code.** | After a doc read: another doc read 27%, reasoning 25%, doc edit 11%, **code edit 0.2%** (3 of 1,328). The link to later code edits is "unresolved". |
| 3 | **Docs are not used to verify work.** | Agents were never seen checking a doc against reality ("Verify": 0 events). In the three events after reading docs, agents were *less* likely to run tests (adjusted OR 0.39) or builds (0.25). |
| 4 | **Agents read docs on their own initiative, rarely because something broke.** | 70% self-initiated, 20% user-instructed, 7.5% failure-driven. Only 5.4% of failure-recovery episodes started by reading docs. |
| 5 | **Agents never followed cross-references.** | The authors coded Follow-reference, Compare, and Verify behaviors and observed zero of each. |
| 6 | **Agents write almost as much as they read, and docs trail code.** | 58% of sessions with doc activity both read and wrote docs. 41.5% of agent PRs change docs. When code and docs change in separate commits, code comes first 82.5% of the time. `AGENTS.md` is the most-changed doc file (692 PRs). |

The authors replace the textbook linear journey (discover, read, apply, validate,
update) with a **two-lobed cycle**. One lobe is a recurring _consultation_ loop: orient,
find, read, interpret. The other is a _production_ lobe in which agents write docs. Both
lobes are only loosely coupled to code changes. They suggest, but do not test, that
agents write notes as **external working memory** because context windows are bounded.
They also suggest agents skip doc-based validation because **tests are a cheaper
oracle**.

**Recommendations the authors stand behind:**

- Make instruction files correct and clear first.
- Make documents self-contained and locally retrievable.
- Treat agent-written notes as something that needs maintenance.

**Ideas they explicitly do not support:** that "actionable" or "verifiable" docs help,
that docs are the main failure-recovery resource, or any ranking of recovery strategies.
They offer executable docs only as a hypothesis.

### How much to trust it

- **Observational only.** It shows correlations, not causes.
- **Dominated by one agent.** Claude Code makes up 84% of the corpus and 68% of the
  sample, so the results may say more about one agent's habits than about agents in
  general.
- **Unvalidated labels.** No human checked the model-assigned labels, and no
  inter-rater agreement was measured.
- **Only repo-local files.** Docstrings, websites, and context preloaded at session start
  are invisible unless an agent reads them again. The absolute rates are therefore lower
  bounds.
- **Hidden shell reads.** Reads routed through shell commands are hard to see, so some
  agents may be undercounted.
- **Small samples on recovery.** The doc-first recovery result rests on only 11
  episodes.

## What SASE can learn

Each lesson below is ranked by value. It pairs a paper finding with SASE's current
state and a suggested action.

1. **Instruction files are the documentation that matters. Keep them correct above
   everything else.** _(Findings 1 and 6.)_
   - **SASE today:** SASE is well positioned. `AGENTS.md` and provider shims are
     rendered from `sase/memory/` and checked by a CI parity test, and agents must use
     `/sase_memory_write` before editing memory. In other repos agents edit `AGENTS.md`
     freely; the paper counts 692 PRs doing so. SASE's audited reads show the same
     skew the paper found. Of 2,111 recorded memory reads, rule notes lead:
     `lint_and_test.md` has 668 reads, `sase_beads.md` 316, and `sase_artifacts.md` 232.
   - **Action:** Treat drift in core memory and in the "Read before X" trigger lines as
     the most serious kind of documentation bug. One example is the `macros.md` drift
     found in the
     [docs-as-memory report](docs_backed_memory_and_agent_maintained_docs/docs_backed_memory_and_agent_maintained_docs.md).

2. **Agents don't follow links, so deliver content, not pointers.** _(Finding 5.)_
   - **SASE today:** The glossary read already does this: one command prints a term
     plus every term its definition depends on. `![[target]]` transclusion also exists.
   - **Action:** When a note depends on another note, transclude the dependency or have
     the read command print it, instead of writing "see X". Apply this to the docs
     split epic (`sase-1le.20`). Splitting large docs pages into many small pages adds
     hops, and the paper suggests agents will not take them. Each new page must stand
     on its own for the task it covers.

3. **Reading docs does not make agents verify, so keep verification mechanical.**
   _(Finding 3.)_
   - **SASE today:** This supports the decisions SASE has already made. Completion is
     host-owned, guarded recipes run under `sase tool run`, and receipts serve as proof.
     A prose rule like "you MUST run `just check`" is exactly the kind of instruction
     the paper suggests agents skip.
   - **Action:** Wherever a memory rule can become a check or a generated block, convert
     it. This matches the "generate the registries" recommendation in the docs-as-memory
     report and the paper's executable-docs hypothesis.

4. **Agents rarely open docs after a failure, so put the fix in the error.**
   _(Finding 4.)_
   - **SASE today:** Some commands already do this. Running `sase bead show` as an agent
     fails with the exact `sase bead read … -r '<why>'` command to run instead.
   - **Action:** Make this a convention for every agent-facing refusal and error:
     state the fix, and name the memory selector to read. This is a design inference
     rather than a result proven by the paper, which does not rank recovery strategies.

5. **Agent working notes are a real document type, so manage their lifecycle.**
   _(Finding 1.)_
   - **SASE today:** SASE is ahead of the field here. Plans, research reports, and
     artifacts have labels, retention, and `sase plan search`.
   - **Action:** Give notes a visible status, such as active, implemented, or
     superseded, so a stale plan is never mistaken for current truth. Keep them out of
     the paths agents read to get oriented.

6. **Docs trail code, so check doc updates at the end of the turn.** _(Finding 6.)_
   - **SASE today:** Agents already co-edit docs. The docs-as-memory report found docs
     edits in 36% of recent `src/` commits.
   - **Action:** Run the check where agents actually write docs, at finalize or lint
     time. For example, flag code changes covered by a docs page's proposed `covers:`
     metadata when that page was not updated. Start-of-turn reminders would not help.

7. **Measure SASE's own agents, because SASE has the data the paper lacked.**
   _(Limitations.)_
   - **SASE today:** SASE has an audited `sase memory log` (2,111 reads across 126
     paths and 900 agents) and multi-provider transcripts through `sase chat`. These
     cover Claude, Codex, and Gemini, so they are less dominated by one agent than the
     paper's data. The paper's blind spot, reads hidden inside shell commands, also
     affects SASE. The docs-as-memory report found 38% of recent Codex sessions reading
     docs pages through the shell with no audit trail.
   - **Action:** Reproduce a lightweight version of the study:
     - Classify file reads, including paths inside `cat` and `sed` commands, as
       instruction, memory, docs, or working note.
     - Measure whether reads are followed by verification.
     - Compare providers.

     This would replace intuition about SASE's own documentation with evidence, in the
     same spirit as the `corpus-before-mechanism` decision.

## Suggested next steps

1. Add a "self-contained page" acceptance criterion to the remaining `sase-1le.20.1`
   docs-split phases.
2. Adopt the convention that every agent-facing error names its fix, and audit current
   refusals against it.
3. File a task to prototype the transcript measurement in step 7, using `sase chat` and
   `sase memory log`.

## Sources

- Gao, Z. and Chen, J. (2026). _From Agent Behaviour to Agent-Friendly Documentation._
  arXiv:2608.20195v1. <https://arxiv.org/abs/2608.20195> (abstract and full HTML text
  read; the figure was not inspected).
- SASE evidence: `sase memory log` (read 2026-10-16), bead `sase-1le.20`, and the
  2026-10 reports
  [docs-as-memory](docs_backed_memory_and_agent_maintained_docs/docs_backed_memory_and_agent_maintained_docs.md)
  and
  [instruction bundles vs. readable AGENTS.md](instruction_bundles_vs_readable_agents_md/instruction_bundles_vs_readable_agents_md.md).
