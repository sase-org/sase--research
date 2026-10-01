# Integrating Jev (TypeSafe's decision model) into sase: research, critique, recommendation

_Researcher: cld · 2026-10-01 · Scope: what Jev is, where (if anywhere) it fits in sase,
how to integrate it, and whether to integrate it at all._

## TL;DR

- **Jev is not an LLM provider.** It is a two-week-old, waitlisted, proprietary
  classifier API from TypeSafe AI. It takes text state plus typed questions. Each answer
  is a pick from a list you supply, a score on a 2–10 level rubric, or a yes/no
  probability. Every answer carries a probability, and Jev never generates text. It
  cannot run as a `sase_llm` provider, because sase's provider contract assumes a CLI
  harness that runs a full agent turn and submits a `/sase_final` declaration.
- **Jev's headline advantages are speed (~70–500 ms) and price ($0.042/M input
  tokens). Neither matters for most sase decisions.** Outside agent tool calls, sase
  makes tens to low hundreds of judgment-shaped decisions a day. At that volume a
  small-LLM baseline already costs pennies. The one high-volume stream (~8,100 agent
  tool calls a day) is where Jev is weakest: it is vulnerable to prompt injection, it
  would send every tool call to a third party, and sase has no provider-neutral
  pre-tool hook.
- **sase's own decision records argue against putting Jev in any decision path:**
  - `decisions:triage-annotates-does-not-change-exit-codes`: KNOWN needs an
    independent witness, and a model guess is not one.
  - `decisions:corpus-before-mechanism`: no machinery before the corpus that needs it.
  - `decisions:host-owned-completion`: judgment is supplied, never trusted as proof.
  - `decisions:rust-core-required`: core policy is deterministic Rust.
  - The `forbidden` auto-policies on launch, sudo and task-triage gates.
- **The best real opportunity is one human bottleneck: the task-triage queue.**
  - 189 task-triage gates are still pending. All 189 are still-current gates for distinct
    beads; 177 of them are sase beads.
  - 313 sase task beads are `ready`, with a median age of 9 days.
  - 672 closed task beads already carry a resolution: 389 `done`, 235 `canceled`,
    45 `superseded`. That is a ready-made labeled corpus for testing Jev offline before
    anything is built.
- **Recommendation:** do not integrate Jev into sase core now.
  1. Run a cheap, pre-registered, out-of-tree **shadow evaluation** on the closed-bead
     corpus. It costs under $0.10 of Jev tokens.
  2. Only if Jev clearly beats a small-LLM baseline after calibration, ship an
     **out-of-tree `sase-jev` plugin**. It would run one advisory routine that scores and
     annotates the triage queue and never decides anything.
  3. Promote this to a vendor-neutral `sase decide` primitive only when a second consumer
     with its own corpus appears. Jev would then be one backend, with the policy in the
     Rust core.

---

## 1. What Jev actually is

### 1.1 Facts (cross-checked across sources)

| Property                | Value                                                                                                                                                                                                                                                                                                                                                                                                             | Confidence                                                                         |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Vendor                  | TypeSafe AI (San Francisco, founded 2024). Founders: Diogo Almeida (ex-OpenAI, RLHF/InstructGPT), Erik Gafni, Sasha Sheng. $40M seed led by DCVC.                                                                                                                                                                                                                                                                 | High (Wikipedia, multiple outlets)                                                 |
| Release                 | 2026-09-15, **limited, waitlisted early access**, proprietary. No paper, no published architecture, no SLA.                                                                                                                                                                                                                                                                                                      | High                                                                               |
| Endpoint                | `POST https://api.typesafe.ai/v1/systemone`, fields `model`, `state`, `questions`                                                                                                                                                                                                                                                                                                                                 | High                                                                               |
| Primitives              | **choice**: up to 255 options; returns the selection, the probability of each option, and a confidence derived from how those probabilities are spread. **score**: 2–10 ordered levels; returns a probability-weighted score. **noul**: yes/no; returns P(yes) and no confidence field.                                                                                                                         | High (docs, several independent tutorials agree)                                   |
| Model IDs               | `jev-1.13.0`. Aliases `jev-latest` and `jev-preview` currently resolve to it. Vendors and testers all say to pin the version, because thresholds drift when the alias moves.                                                                                                                                                                                                                                     | High (docs.typesafe.ai/models)                                                     |
| Limits                  | 64k tokens per request in total; 32k for state plus the longest single question. Text only. English first; other languages "not equally well".                                                                                                                                                                                                                                                                  | High                                                                               |
| Rate limits             | The docs say 100K tok/s and 40 req/s and that limits "can change without notice". Another source reports 250K tok/s and 1,200 req/min.                                                                                                                                                                                                                                                                           | Medium: sources disagree and limits are dynamic                                    |
| Price                   | $0.042 per million input tokens; output is free                                                                                                                                                                                                                                                                                                                                                                 | High                                                                               |
| Latency                 | 70–500 ms per request, as reported by the vendor                                                                                                                                                                                                                                                                                                                                                                | Vendor claim                                                                       |
| Data handling           | Jev is not trained on customer data. Zero data retention is available **only to enterprise customers**. Standard accounts are kept "as long as reasonably necessary". Served from one region.                                                                                                                                                                                                                  | High (docs and secondary sources)                                                  |
| SDKs                    | `typesafe-sdk` (Python; `TypeSafeClient` and `AsyncTypeSafeClient`), plus JS/TS. Pydantic AI has a `TypeSafeModel` that escalates to an LLM whenever an answer needs a `str`.                                                                                                                                                                                                                                   | High                                                                               |
| Errors                  | 401, 422 (validation, names the field), 429, 529 (overloaded: retry with backoff)                                                                                                                                                                                                                                                                                                                               | Medium (one source)                                                                |
| Training                | "Reinforcement Learning for Calibrated Decisions" (RLCD), on synthetic data. Unpublished.                                                                                                                                                                                                                                                                                                                        | Vendor claim                                                                       |

The vendor positions Jev as a "System One" model: fast, intuitive judgment that ordinary
code branches on. That frame matters for sase. **sase agents are System Two.** The only
sensible role for Jev is a fast filter **in front of** or **beside** expensive agent
turns, never a replacement for them.

### 1.2 What the independent evidence says (more important than the marketing)

1. **The vendor's own benchmark shows parity with a mid-tier LLM, not superiority.** On
   TypeSafe's four-workflow benchmark, Jev scored 67.8% accuracy. GPT-5.6 Terra scored
   67.9%, and Claude Opus 5 scored 73.1%. Jev wins on cost ($0.0004 vs $0.03 vs $0.18 per
   case) and latency (0.4 s vs 10 s vs 38 s). It does not win on accuracy.
2. **Asking one broad question does badly; splitting it into narrow questions does
   well.** In an independent phishing study (beri.net), one question
   ("is this phishing?") scored **62.6%**, against Claude Haiku 4.5's 81.3%. Five narrow
   yes/no signals, combined with **logistic-regression weights fitted on 1,000 labeled
   examples**, reached 95.0%, against Haiku's 93.2% (not statistically significant). A
   fine-tuned Qwen3-4B trained on the same labels reached 97.4%. The lesson: Jev's useful
   output is a set of cheap features that **you** must weight, and you calibrate those
   weights with **your own** labeled data.
3. **"Calibrated" needs an asterisk:**
   - The same study measured an expected calibration error (ECE) of 0.107 on synthetic
     tickets, 4.4× the noise floor.
   - Its errors run in opposite directions by type: yes/no answers are underconfident,
     while choice and score answers are overconfident.
   - On unknowable questions it was 44.7% accurate while reporting an average
     probability of 0.74.
   - Choice "confidence" comes from the shape of the probability distribution; it is not
     a separate calibrated signal.
   - You cannot carry a yes/no threshold over to a choice question.
4. **Known failure modes (vendor and testers agree):**
   - counting and arithmetic;
   - relative dates;
   - double negatives and indirection;
   - sensitivity to how options are worded;
   - a choice question must always pick something, so add an explicit `none_of_these`
     option;
   - the question key is never sent to the model, so all meaning must be in
     `instructions` and `criteria`.
   - **Adversarial content in the state shifts answers.** TypeSafe says it "expects to
     improve" on this.
5. **How the ecosystem uses Jev** (arXiv 2609.30216, 2,170 public repos as of
   2026-09-22):
   - Judging attributes: 77% of repos. Scoring/ranking: 52%. Choosing an action: 31%.
   - Routing & automation repos are 11.5% of projects but drew **41.4% of all stars**.
     Model routing is where the hype concentrates.
   - The agent-relevant patterns are tool-call guardrails (`pi-jev`, `pi-warden`), model
     routers (`jev-router`, Hermes `jev-model-router`), action selection, and context
     compaction decisions.
   - The paper reports **no accuracy data of its own**, and it highlights sensitivity to
     option names.

**Net:** Jev is a real, useful new primitive for **high-volume, bounded, low-stakes**
classification when you have labeled data to calibrate against. It is not a judgment
oracle.

---

## 2. sase as seen by a decision model

### 2.1 Architectural fit: Jev cannot be a `sase_llm` provider

- Providers are pluggy entry points in `pyproject.toml:206-214` (`sase_llm`: agy, claude,
  codex, fakey, grok, muse, opencode, qwen).
- The `LLMProvider.invoke(...) -> InvokeResult(content, usage)` interface
  (`src/sase/llm_provider/base.py`) assumes a text result.
- `docs/llms.md` states the design rule outright: "Providers are thin: they only
  construct CLI commands and run subprocesses."
- Every LLM call goes through `invoke_agent()` (`src/sase/llm_provider/_invoke.py:101`).
  That call resolves a finalizer plan, runs `run_finalizers` (:444-446), and saves chat
  history in `postprocess_success` (:476). Jev cannot produce a declaration, a
  transcript, a commit or a tool call.

Registering Jev as a provider would mean faking all of that. **Rejected.**

### 2.2 sase has no cheap structured-judgment path at all

There is no "small LLM call" in sase today. The closest thing is `get_file_summary()`
(`src/sase/ace/hooks/summarize_utils.py`). It runs the `summarize` xprompt workflow
(`#json:{ summary: line }`) as a full workflow with no `%model`, so it runs at the
default `@large`.

Every other judgment-shaped decision is one of two things:

- made by an agent inside its own turn, as with task-bead deduplication through the
  `/sase_new_task` skill procedure; or
- made by deterministic code: regexes, substring rules, globs, or Rust policy.

This is the most important structural finding. **Jev does not swap in for anything.**
Any integration adds a new capability, a new dependency and a new trust surface.

### 2.3 Measured decision volume (this machine, `apollo`)

| Stream                                | Volume                                                                                                                                                                  | Source                                                                          |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Agent tool calls                      | **~8,100/day**: 56,750 `ToolUse` events in 7 days. Muse 31.9k, Claude 14.4k, Grok 6.3k, Codex 4.2k.                                                                   | `tool_calls.jsonl` under `~/.sase`, files modified since 2026-09-24             |
| Agent runs that made tool calls       | ~97/day (677 in 7 days)                                                                                                                                                 | same                                                                            |
| Task-triage gates                     | 884 gate generations for 282 distinct beads in 30 days. **0 have `response.json`.** 542 were cancelled because the presentation changed, 95 because the bead was no longer ready, 54 because the project was disabled. **189 are still pending** (177 sase, 12 bob-cli). | `~/.sase/interaction_requests/task_triage/`                                     |
| Plan / epic-plan gates                | 142 / 71 in total                                                                                                                                                       | `~/.sase/interaction_requests/`                                                 |
| Question / custom / sudo gates        | 4 / 3 / 4                                                                                                                                                               | same                                                                            |
| ToolRuns                              | 312 in 30 days (~10/day). `check` ran 209 times: 156 FAIL, 52 censored.                                                                                                | `sase tool stats -a -d 30`                                                      |
| Failure-signature groups (30 days)    | 455 groups. By newest class: new 209, known 205, **unknown 16**, flaky 6, unclassified 19. By runs: known 698, new 258, **unknown 45 (~4%)**.                           | `sase tool failures -a -d 30 -j`                                                |
| sase task beads (all time)            | 1,009 total. 672 closed (**389 done / 235 canceled / 45 superseded**), 313 ready (median age 9 days). Task types: untyped 374, bug 206, flake 144, ci 133, feature 60, flag 58, memory 34. | `sase bead list -t task -s all -n 0 -f json`                                    |

**What this means for economics.** Every stream except tool calls handles at most a few
hundred decisions a day. Take ~2k tokens per decision and 500 decisions a day: that is
about 1M tokens a day, ~$0.04 on Jev or ~$1 on a Haiku-class model. Jev's 40–400×
cost advantage is real but **worthless at this scale**, and its latency advantage only
matters in a hot loop.

The real arguments for Jev in sase are therefore:

- typed outputs that never fail to parse;
- probabilities you can threshold to abstain;
- not tying up a subscription-quota agent turn for a one-bit question.

### 2.4 Inventory of judgment-shaped decision points

"Fit" combines whether the question has a bounded answer space, whether labels exist,
the stakes, and the constraints from sase's decision records.

| #   | Decision point                                                                                                                                                                                                                                          | Mechanism today                                                                                                                                           | Labels to evaluate against?                                                                                                  | Fit                                                                                                                                                                                                                     |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Task-triage queue: launch, close or snooze?** (`bead/task_gate.py`, `scripts/sase_chop_bead_task_triage.py`)                                                                                                                                          | A human answers the gate. Auto-resolution is `forbidden` (`notification_gates/adapters.py`, `task_triage` adapter).                                       | **Yes, 672 resolved beads**                                                                                                  | **Best fit, but advisory only.** Score and annotate the queue so the human sees the most-likely-to-launch beads first and stale ones flagged; never auto-resolve.                                                        |
| 2   | Task-type and size sanity (`bead/cli_crud_create.py`, `bead/work_prompt.py:50`)                                                                                                                                                                         | The filing agent declares both                                                                                                                            | Yes: 635 typed beads, 943 sized                                                                                              | Good **offline** check: does Jev agree with the filing agent? A cheap second opinion; low stakes.                                                                                                                       |
| 3   | Duplicate/superseded detection for new tasks                                                                                                                                                                                                            | The agent searches and reasons inside `/sase_new_task`                                                                                                    | Weak: 45 superseded beads, links not always recorded                                                                         | Jev cannot retrieve. It could only answer a pairwise "is A a duplicate of B" over candidates from search, and the filing agent already does that with better reasoning. Low value.                                   |
| 4   | Agent wait-claim detection (`llm_provider/_wait_signals.py`)                                                                                                                                                                                            | `WAIT_SIGNAL_RE` regex over the last 700 characters of the reply                                                                                          | None collected                                                                                                               | Technically a clean yes/no question, but it would put a network call on every Claude/Muse turn end. Defer until there is evidence the regex misses.                                                                    |
| 5   | Retry-error classification (`axe/run_agent_retry_spawn.py:103` `_classify_error`)                                                                                                                                                                      | Substring rules                                                                                                                                           | None                                                                                                                         | **Reject.** Provider error strings are deterministic text, and a regex is the right tool.                                                                                                                              |
| 6   | ToolRun failure triage (Rust `triage_classify`, `tool/executor_triage.py`)                                                                                                                                                                              | Deterministic, witness-based                                                                                                                              | Yes                                                                                                                          | **Reject** for verdicts: KNOWN *requires an independent witness*. UNKNOWN is about 4% of runs, far below the record's own 40% reopen bar. At most an advisory hint on UNKNOWN items, and the gap is too small to matter. |
| 7   | Gate auto-resolution (`GateAdapter.auto_policy`)                                                                                                                                                                                                        | `approval` / `first` / `forbidden`                                                                                                                        | No                                                                                                                           | **Reject.** Plan approval needs reasoning over a whole plan. Launch, sudo and HITL are `forbidden` for trust reasons a classifier does not change. Question gates are rare (4 in total).                               |
| 8   | Pre-tool-call guardrail (the `pi-warden` pattern)                                                                                                                                                                                                       | None. There is no PreToolUse veto hook (`llm_provider/_tool_call_claude.py` only records). Agents run with permissions skipped in ephemeral workspaces; structural guards are guarded recipes, sudo gates and host-owned completion. | None                                                                                                                         | **Reject for now.** It is the only stream with volume, but see §4.                                                                                                                                                     |
| 9   | Size / model routing for unsized prompts (the `jev-router` pattern)                                                                                                                                                                                     | Curated `@size` aliases (`decisions:size-alias-effort-ladder`) plus explicit `%model`                                                                   | **No outcome corpus**                                                                                                        | Interesting, but you cannot evaluate it without measuring output quality per size. Defer.                                                                                                                              |
| 10  | Monitor follow-up / "should this wake an agent?" (`monitor/outcome_policy.py`, `monitor/followup.py`)                                                                                                                                                   | A deterministic outcome-to-action map. Every terminal monitor launches a follow-up agent.                                                                 | No                                                                                                                           | Plausible later as a System One gate in front of a System Two turn, but follow-ups almost always need the agent anyway. Defer.                                                                                        |
| 11  | Mentor profile routing (`config/mentor.py`, `ace/scheduler/mentor_profile_matching.py`)                                                                                                                                                                 | Globs and regexes over diffs and notes                                                                                                                    | Weak                                                                                                                         | Plausible ("does this diff need mentor X?"). The saving is avoided full mentor turns. Needs a corpus first.                                                                                                           |

---

## 3. Constraints from sase's own decision records

These are binding architecture. Any Jev integration has to respect them.

- **`decisions:corpus-before-mechanism`: no mechanism before its corpus.** sase built
  speculative recall machinery three times and deleted it three times, at real cleanup
  cost. A general `sase_decision` subsystem built before even one consumer has proven out
  repeats that pattern. The task-bead corpus is what makes a *measured* first step
  possible.
- **`decisions:triage-annotates-does-not-change-exit-codes`: triage annotates; it never
  changes an exit code.** A probabilistic guess is not an independent witness. Jev may
  annotate; it may never mint KNOWN or FLAKY.
- **`decisions:host-owned-completion` and `decisions:receipts-prove-before-they-skip`.**
  Host-owned selection is paired with agent-supplied judgment, and receipts never skip
  verification. A Jev score must never satisfy a finalizer, skip a check, or count as a
  receipt.
- **`decisions:rust-core-required` and the `rust_core_backend_boundary` core note.** If
  a decision *policy* (threshold, abstain rule, the shape of the stored record) ever
  matters to more than one frontend, it belongs in `sase-core`. A network call to a
  vendor is not deterministic core logic, so the **transport** belongs in a Python
  plugin. Keep the two apart from day one.
- **`decisions:hold-pull-fail-open` (fail-open for courtesies, fail-closed for
  correctness).** Jev is an early-access, single-region service whose rate limits change
  without notice, so it may only drive *courtesies*: ordering, hints, annotations. When it
  is down, sase must behave exactly as it does today.
- **The adapters-normalize-harnesses record and four live runtimes.** Any per-tool-call
  integration needs four harness-specific hooks (muse, claude, grok, codex). That
  per-harness cost is exactly what `decisions:adapters-normalize-harnesses` warns
  about.

---

## 4. Integration options, evaluated

### A. Jev as a `sase_llm` provider: **reject**

This is a category error (§2.1). Jev cannot satisfy finalizers, transcripts or tool
calls.

### B. A first-class `sase_decision` entry-point group, `sase decide` CLI and Rust policy: **right eventual shape, premature now**

The shape would be:

- a new pluggy group modeled on `sase_llm`;
- typed request and response records (choice, score, binary; probabilities; model
  version; latency);
- a Rust-owned threshold/abstain policy and decision-record schema;
- a `sase decide` CLI so chops, `%if::` predicates, workflow steps and agents can all
  call it;
- backends: Jev, plus a *small-LLM structured fallback* that does not go through
  `invoke_agent`.

This is the right architecture **if and when** two or more consumers exist with
measured wins. Built today, it would be a mechanism with no corpus: a CLI family,
wire types, a doctor check and docs, all at risk of the same deletion cycle the
corpus-before-mechanism record documents. It is also the most vendor-neutral answer to
the gap Jev exposes (§2.2). Keep it as **step 3**.

### C. Pre-tool-call guardrail: **reject for now**

It has the only meaningful volume, about 8.1k calls a day. On Jev that would be ~$1/day
at ~3k tokens per call, against ~$24/day on Haiku, so Jev's economics really do show up
here. It is still the wrong first move:

1. **It would be a security control that adversarial input defeats.** Text inside the
   state shifts answers, and tool inputs and outputs routinely carry untrusted content
   (web pages, issue bodies, emails). An injectable guard gives false assurance, and
   guardrails themselves become denial-of-service targets (arXiv 2606.14517).
2. **Data egress.** Every Bash command, file excerpt and diff, including Bob-vault
   content and anything a `/sase_gmail` read surfaces, would go to a two-week-old vendor.
   Standard accounts have no fixed retention period.
3. **Four harness implementations** and a new 70–500 ms of latency on every tool call.
   At 8.1k calls a day that adds roughly 0.2–1.1 agent-hours of wall time per day.
4. **sase already has structural guards** that do not depend on judgment: ephemeral
   workspaces, guarded recipes, sudo gates, and agents never committing or pushing.

Revisit only as a shadow-mode logger in one harness, after a real incident shows a
structural guard gap.

### D. Out-of-tree plugin that scores the task-triage queue (advisory): **recommended pilot (after the eval)**

- **Delivery.** A separate `sase-jev` repo, like `sase-telegram`, which ships job and
  chop scripts rather than core entry points. Axe already discovers `sase_chop_*` and
  `sase_job_*` scripts on PATH or in the venv (`axe/chop_script_runner.py`), so this needs
  **zero sase core changes** and uninstalling is a full rollback.
- **What it does.** On a schedule, it builds a state from each `ready` bead: title,
  description, type, size, `plus_one_count`, age, and recently touched paths. It asks
  narrow questions, for example:
  - noul "is the problem described still plausibly present?";
  - noul "is this a duplicate of an epic currently in progress?" (with candidates
    supplied);
  - score "user-visible impact";
  - choice "launch / close / snooze / none_of_these".
- **Where results go.** It records the answers, with the pinned model ID, an input hash
  and the probabilities, as advisory annotations, for example a bead note or a sidecar
  record.
- **How results are used.** The weighting that turns features into a ranking is fitted
  offline (logistic regression), following the beri.net lesson. The queue is presented
  in score order.
- **Hard rules:**
  - it never resolves a gate (the `task_triage` auto-policy stays `forbidden`);
  - it never closes or snoozes a bead;
  - it fails open;
  - it pins `jev-1.13.0`;
  - it re-runs the calibration set before any model bump.

### E. `%if::` predicates that call Jev: **allowed as personal experimentation; nothing to build**

`%if::` code-form predicates (behind the `typed_launch_units` beta flag) run a
supervised script that inherits the environment (`agent/launch_condition_runtime.py`
copies `os.environ` at line 182). Exit 0 means eligible and exit 1 means skipped. A user
could already gate a launch on a Jev noul with a 10-line script. This is a good
place for ad-hoc "should this routine wake an agent?" experiments, and it needs no code.

### F. Replace regex classifiers (wait claims, retry errors) or add a gate `model` auto-policy: **reject or defer**

These would add network nondeterminism to deterministic hot paths, or put a classifier
in charge of decisions sase deliberately reserves for humans.

---

## 5. Critique: is integrating Jev a good idea?

**Mostly no, as currently framed. A narrow "yes" for one advisory, evaluated use.**

1. **The value proposition does not match the workload.** Jev is built for thousands of
   decisions a second. sase's judgments are few, high-stakes and reasoning-heavy. The
   decisions that matter most are plan approval, launch approval, task value and failure
   ownership. They need multi-step reasoning, rationale and audit trails, which Jev
   explicitly does not provide ("useless for open-ended generation"; it gives no
   rationales).
2. **"Calibrated" is the real draw, and it is conditional.** Probabilities you can
   threshold to abstain fit sase's fail-open, abstain-when-unsure culture well. But
   independent testing says you need per-question calibration on labeled data, and that
   one-shot questions underperform Haiku. So Jev only pays off where sase *has labels*.
   Today that is mainly the closed task beads.
3. **Vendor maturity risk is high.**
   - The product is 16 days old, waitlisted and served from one region.
   - Rate limits change without notice, and there is no SLA, paper or published
     architecture.
   - Alias drift silently invalidates thresholds.
   - There is no Jev credential in this environment, so access must be obtained before
     anything can be tested.
   - Anything that depends on Jev must survive it disappearing.
4. **Data governance is not free.** Bead text for public sase work is low-sensitivity.
   Transcripts, tool calls, the Bob vault and Gmail-derived content are not. Without
   enterprise zero data retention, keep Jev to public-repo bead metadata.
5. **Watch the hype signal.** 1,865 repos in the first week, with routing projects
   drawing 41% of the stars, is fashion, not evidence that routing works. sase's own
   routing (size aliases) is deliberately curated and testable. A learned router would
   need an outcome-quality corpus sase does not have.
6. **What Jev usefully exposes is a gap.** sase has no cheap, typed judgment primitive;
   even a one-line file summary runs a `@large` workflow. That gap is real and has
   nothing to do with any vendor. If it is ever filled, fill it vendor-neutrally (option
   B), with Jev as one backend and a small-LLM structured call as the other. Do not make
   Jev the architecture.
7. **Where it could genuinely help:**
   - The human is the bottleneck on the task queue: 189 pending triage gates and 313
     ready beads with a median age of 9 days. Every triage gate in the last 30 days was
     cancelled or is still pending; none was answered through the gate.
   - Cheap, calibrated ordering and staleness hints on that queue are a courtesy that
     fails safe.
   - It can be measured before it ships: done vs canceled is a ready label.

---

## 6. Recommended solution

### Step 0: Prerequisites (≈1 hour, no code)

- Get early access. Store the key as an environment variable only; the Hermes router's
  rule is that keys never go in request bodies or config.
- Decide the data boundary: **only public-repo task-bead metadata**. Exclude bob-cli,
  personal projects, transcripts and tool calls.
- Pin `jev-1.13.0`.

### Step 1: Pre-registered offline shadow evaluation (out of tree; ≈1 day; under $0.10 of Jev tokens)

- **Corpus.** The 672 closed sase task beads, as `sase bead list -t task -s all -n 0 -f
  json`. The label is `done` vs `canceled ∪ superseded`.
- Split 50/50 into a fitting half and a scoring half, stratified by task type and time.
  The labels lean toward `done` (389 of 672), so the 58% majority baseline is the bar to
  beat.
- **Arms:**
  1. majority class;
  2. logistic regression on free features: type, size, `plus_one_count`, age, description
     length;
  3. Jev, one choice question;
  4. Jev, about five narrow questions (noul and score) with fitted logistic weights;
  5. a small-LLM structured baseline using the cheapest `@xsmall` member, with the same
     questions.
- **Secondary checks, same harness:** task-type agreement with the filing agent (635
  typed beads) and size agreement (943 sized).
- **Metrics:** accuracy and AUROC; ECE after per-question calibration; coverage at 0.9
  precision; cost and p50 latency per bead.
- **Pre-registered go criterion.** Arm 4 must beat arms 2 and 5 on AUROC by at least
  0.05, **and** reach at least 30% coverage at 0.9 precision for "will be canceled".
  Otherwise stop: either cheap features already capture the signal, or the LLM baseline
  is as good and needs no new vendor.
- Write it up as a research report. File nothing in sase yet.

### Step 2: If and only if Step 1 passes, an advisory `sase-jev` plugin (≈2–3 days)

- Ship it as a separate repo exposing one chop script, `sase_chop_jev_task_triage_score`.
  Use stdlib `urllib` (sase's existing HTTP convention) or `typesafe-sdk` pinned.
- Use speculative fan-out: all questions for a bead in one request, so the state is sent
  once.
- Persist a decision record per bead: input hash, model ID, questions version,
  probabilities, fitted score and timestamp.
- Surface the result as an annotation the human sees when the triage gate or bead
  appears. Sort the queue by expected value of attention. Never auto-resolve, close or
  snooze.
- Fail open everywhere. A weekly replay of the held-out set detects drift; a model bump
  requires recalibration.
- **Kill criteria.** After four weeks, measure whether triage latency (gate-to-resolution
  time) or ready-queue age fell, and how often the human acted against a high-confidence
  hint. If the queue does not shrink, uninstall.

### Step 3: Only when a second consumer has its own corpus, generalize vendor-neutrally

Candidates for that second consumer are mentor routing (#11), monitor wake decisions
(#10) and size routing (#9), each once it has labels.

- Add `DecisionRequest` / `DecisionRecord` wire types and threshold/abstain policy to
  `sase-core`.
- Add a `sase_decision` entry-point group with Jev and small-LLM-structured backends.
- Add a `sase decide` CLI. Read `cli_rules.md` first.
- Write a decision record: "Decisions are advisory courtesies; a model probability is
  never a witness, receipt or approval."
- Gate rollout with a feature flag per the `sase_flags.md` rules.

### What not to do (now)

- Do not add Jev as a `sase_llm` provider.
- Do not give any gate kind a `model` auto-policy.
- Do not let Jev mint KNOWN or FLAKY, skip a check, or satisfy a finalizer.
- Do not put Jev on the per-tool-call path, or send transcripts, tool I/O, Bob-vault or
  Gmail content to it.
- Do not build the general decision subsystem before Step 1 has produced a corpus-backed
  win.

### When to reopen this recommendation

- Jev publishes independent calibration results, or ships GA with an SLA and standard
  zero data retention. Then revisit the guardrail and routing options in shadow mode.
- sase grows a decision stream above about 10k/day that is bounded, low-stakes and
  labeled. Then the economics start to matter.
- The Step 1 eval passes on a second corpus. Then build Step 3.

---

## Sources

- Jev overview and facts: [Wikipedia: Jev (AI model)](https://en.wikipedia.org/wiki/Jev_(AI_model)),
  [TypeSafe docs: Models](https://docs.typesafe.ai/models),
  [MarkTechPost release coverage](https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/)
- Mechanics, calibration, limits: [Victor Dibia: How Jev works](https://victordibia.com/explainers/jev/),
  [DataCamp: System One models / Jev](https://www.datacamp.com/blog/system-one-models-jev),
  [Flavio Copes: deep dive into Jev](https://flaviocopes.com/jev/),
  [Abrar Qasim: Jev API gotchas](https://abrarqasim.com/blog/typesafe-ai-jev-api-tutorial-choice-score-noul-and-the-gotchas/)
- Independent evaluation: [beri.net: Jev 62.6% asked once, 95% split five ways](https://www.beri.net/article/typesafe-jev-typed-decision-model-calibration-decomposition-shadow-eval)
- Ecosystem: [arXiv 2609.30216: Jev in the Wild](https://arxiv.org/html/2609.30216v1),
  [MindStudio: Jev use cases tested](https://www.mindstudio.ai/blog/jev-use-cases-automation)
- Integrations and patterns: [Pydantic AI: TypeSafe (Jev)](https://pydantic.dev/docs/ai/models/typesafe/),
  [Hermes Agent: jev-model-router plugin](https://hermes-agent.nousresearch.com/docs/plugins/jev-model-router),
  [MarkTechPost coding guide: speculative fan-out](https://www.marktechpost.com/2026/09/23/a-coding-guide-to-typesafe-ai-jev/),
  [jev-guardrails: LLM-as-judge vs Jev (search summary only)](https://github.com/deepansh-saxena/jev-guardrails),
  [arXiv 2606.14517: DoS attacks on LLM-based agent guardrails](https://arxiv.org/pdf/2606.14517)
- sase internals: `pyproject.toml` (`sase_llm` entry points); `docs/llms.md`;
  `src/sase/llm_provider/{base.py,_invoke.py,_wait_signals.py}`;
  `src/sase/notification_gates/{adapters.py,service.py}`;
  `src/sase/axe/run_agent_retry_spawn.py`; `src/sase/agent/launch_condition_runtime.py`;
  `src/sase/ace/hooks/summarize_utils.py`; `src/sase/monitor/outcome_policy.py`. Decision
  records were read through `sase memory read`. Volume figures come from local
  `~/.sase` state, `sase tool stats`, `sase tool failures` and `sase bead list` on
  2026-10-01.
