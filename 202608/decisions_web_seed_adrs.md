---
create_time: 2026-08-24
updated_time: 2026-08-24
status: research
tags: [adr, decisions, memory, architecture, governance, agent-context]
---

# Which Architectural Decision Records SASE Should Write First

**Research question:** `glossary_to_memory_webs.md` §3.8 concludes that the `decisions`
web "must ship with roughly ten *real* ADRs written from actual history." Which
decisions are those, in what order, and what makes one worth a record in this project
rather than in a general-purpose engineering repo?

**Scope:** Architecture research only; no behavior changed and no ADR written. Measured
at `sase@4041c17e4` on 2026-08-24, with the linked `sase-core` checkout at
`835d6c3`, the `research` sidecar at its opened checkout, and the live flag, project,
and repo inventories from the CLI.

**Companion:** `202608/glossary_to_memory_webs/glossary_to_memory_webs.md` — the design
this report seeds. Its §3.4 (no closure in v1), §3.7 (slug is identity), §4.2 (strand
frontmatter), and §4.4 (validation) constrain the record format proposed in §6 below.

---

## Bottom line

Write the seed set from the decisions agents are **currently getting wrong**, not from
the decisions that were hardest to make. Those are different sets, and the difference is
the whole recommendation.

SASE has 307 distinct research topics across 411 markdown reports in the research
sidecar. It has 13,217 commits, 208 of them marked breaking. It has 17 memory notes
carrying rules. What it does not have anywhere is a record of **why** any of it is that
way, addressable by name. Research reports capture the deliberation but are addressed by
topic and date, not by decision; memory notes capture the rule but deliberately omit the
rationale to stay inside a 2,273-word core budget; commit messages capture the change but
are unreachable to an agent that does not already know which commit to read.

The top five, ahead of the full ranking in §7:

1. **Agents are single-turn; continuation is mechanical.** The most frequently violated
   decision in the system, and it is recorded only as an instruction ("use
   `/sase_monitor` instead"), never as a decision with a reason.
2. **The Rust core is required, and there is no Python fallback.** Cross-repo, 213,719
   Rust LOC, and the corollary that makes it work — strict loading, no env-var backend
   switch — is written in a module docstring rather than anywhere an agent will look.
3. **Verification is two-speed because host capacity, not test speed, is the
   constraint.** The rule is in core memory; the capacity argument that makes the rule
   correct is in a research report, so agents escalate to `check-full` on instinct.
4. **No retrieval mechanism ships before its corpus.** Three memory features were built
   and then deleted — dynamic memory after seven weeks, episodes after three, keyword
   metadata later still. This is the negative ADR the memory-webs work is itself
   relying on.
5. **SASE invents domain nouns instead of reusing industry terms.** Thirty-plus renames,
   including one where a consolidated research report recommended `rivet` and the project
   shipped `Patch` anyway. The glossary lists the words; nothing explains the policy.

Two structural findings worth stating separately:

- **The `decisions` web's real job is rationale, not history.** A record whose body could
  be replaced by its title earns nothing. Every candidate below is ranked by how much
  the *reasoning* costs to reconstruct, not by how important the decision was.
- **Three of the ten strongest candidates are decisions the project reversed.** Reversal
  records are the highest-value ADRs SASE can write, because a reversed decision leaves
  no artifact in the tree at all — only in commit archaeology no agent will perform.

---

## 1. What earns an ADR in this project

### 1.1 The reader is an agent on a fresh context window

Nygard's original proposal assumes a human successor reading a decision log to understand
inherited code. SASE's successor is an agent that will never read the log unprovoked; it
reads what core memory names and what an audited read returns. That inverts two of the
usual ADR selection rules.

It makes **recurrence** dominate importance. A decision an agent bumps into weekly beats a
larger decision it bumps into once a year, because the ADR is only paid for when it is
read. It also makes **invisibility** dominate significance: a decision legible from the
code needs no record, because the agent is already reading the code. The best ADR here
describes something an agent *cannot* infer from the tree — a rejected alternative, a
constraint from another repo, a cost measured once and never re-measured.

### 1.2 Five selection tests

A candidate earns a record if it passes at least three:

| Test | Question |
| --- | --- |
| **Recurrence** | Will an agent hit this in the next 90 days of ordinary work? |
| **Reversal cost** | If someone violates it, is the damage expensive or merely untidy? |
| **Invisibility** | Is the reasoning absent from the tree — a rejection, a measurement, a cross-repo constraint? |
| **Contested** | Was there a credible alternative, or a prior position that was overturned? |
| **Settled** | Is this actually decided, so the record is a record and not a proposal? |

The **Settled** test is the one that disqualifies most exciting candidates. An ADR for a
decision still being made is a design doc wearing an ADR's clothes, and it corrupts the
web: readers stop trusting that a strand in `decisions` describes what is true.

### 1.3 What the existing surfaces already cover, and what they miss

| Surface | Carries | Missing |
| --- | --- | --- |
| Core memory (17 notes, 2,273 words core) | The rule, imperatively | Rationale, alternatives, cost — deliberately, for budget |
| Research sidecar (307 topics) | Deliberation, evidence, recommendation | Whether it was adopted; addressable only by topic+month |
| Commit log (13,217 commits, 208 breaking) | The change and its blast radius | Unreachable without knowing the commit |
| `docs/architecture.md` (191 lines) | The current shape | Zero counterfactuals; describes what is, never what was rejected |

The gap is exactly ADR-shaped: **adopted rationale, addressed by name.** That is a
stronger justification for the `decisions` web than the Zettelkasten framing in the
companion report, and it should lead the web note's own description.

### 1.4 A measured warning about research-report-shaped ADRs

75 of the 307 research topics are consolidated multi-agent reports, several of them
30–40KB. If ADRs are written by summarizing those, the web will inherit their length and
nobody — human or agent — will read a strand. The glossary's own definition budget is
instructive: min 9 / median 50.5 / max 118 words per term. An ADR needs more than a
glossary term but far less than a research report. **Target 250–450 words**, with the
research report cited rather than restated. Enforce it socially at first; if strands
drift past ~600 words, the web has become a documentation directory.

---

## 2. The decision surface, measured

| Measure | Value |
| --- | --- |
| `sase` commits (2026-02-14 → 2026-08-24) | 13,217 |
| Breaking-change commits (`type!:`) | 208 |
| Python source | 829,509 LOC across 3,759 modules |
| Tests | 929,888 LOC across 3,418 test files |
| `sase-core` (4 crates, since 2026-04-28) | 213,719 Rust LOC across 859 commits |
| Research topics / markdown reports | 307 / 411 (75 consolidated, 104 swarm drafts) |
| Memory notes | 17 (8 core, 9 reference) |
| Runtime dependencies | 13, including a hard `sase-core-rs>=0.31.0,<0.32.0` |
| Enabled projects | 3 (`sase`, `bob-cli`, `actstat`) |
| Open feature flags | 3, aged 85–88 days |
| Largest Python module / cap | 698 lines / 700 (`toobig src 1000 850 700`) |

Two of these numbers are themselves decisions worth recording. The 700-line cap is not an
accident of style — it is a machine-enforced constraint whose largest module sits two
lines under it across 3,759 files, which only happens when a gate is doing the work. And
13 runtime dependencies for an 830KLOC application is a deliberate posture, visible in the
Prometheus removal (2026-07-17) and the "remove bundled monitoring stack" commit that
followed it.

---

## 3. Tier 1 — the seed set

Ten records, ranked. Each entry gives the decision, the tests it passes, what the record
prevents, and the primary evidence a writer should cite.

### 3.1 Agents are single-turn; continuation is mechanical

**Decision.** A SASE agent runs for exactly one provider turn. Work that outlives the turn
is continued by a mechanism that terminates the runner and starts a successor — `sase
monitor`, `/sase_pipe`, `/sase_plan`, `/sase_questions` — never by the agent waiting,
sleeping, or scheduling its own wake-up.

**Tests.** Recurrence ✓ · Reversal cost ✓ · Invisibility ✓ · Contested ✓ · Settled ✓

**Why first.** This is the decision the runtime environment fights hardest. Every hosted
agent runtime ships background-execution and scheduling primitives, and every one of them
silently no-ops here. The `/sase_monitor` skill already says so twice, and
`docs/monitors.md:9` states the model in one line — but both state it as a *rule*, and a
rule without a reason is the first thing an agent rationalizes away when its native tool
"would obviously work."
The record must carry the mechanism: the runner captures the turn and exits, so there is
no process left to resume into.

**Prevents.** Burned turns waiting on nothing; handoffs that lose their prompt; agents
scheduling wake-ups that never fire.

**Cite.** `docs/monitors.md:9` · `src/sase/xprompts/skills/sase_monitor.md:6,24` ·
`202608/monitor_command_substrate/` · `feat(cli)!: make run detached-only` (`b20637f4f`,
2026-07-02) and its reversal `feat(cli)!: retire detached proc mode` (`ac5d95810`,
2026-08-15), which together show the model being tested and settled.

### 3.2 The Rust core is required and has no Python fallback

**Decision.** Shared deterministic backend behavior lives in `../sase-core`, is consumed
through the `sase_core_rs` PyO3 wheel, and is a **hard** runtime dependency: no
`SASE_CORE_BACKEND` switch, no dispatcher, no dual-run parity mode, no Python
implementation of a ported operation.

**Tests.** Recurrence ✓ · Reversal cost ✓ · Invisibility ✓ · Contested ✓ · Settled ✓

**Why second.** `rust_core_backend_boundary.md` is 110 words of core memory and states the
litmus test well, but it cannot afford the two things an agent needs when it hesitates:
*why* the fallback was removed, and what "shared backend behavior" cost when it was
duplicated. Both were decided once, in April, and are now recoverable only from a research
report and a module docstring. The no-fallback corollary is load-bearing — it is what
turns a "prefer Rust" preference into a boundary — and it currently lives in the docstring
of `src/sase/core/rust.py`, which no agent reads before deciding where to put code.

**Prevents.** Reimplementing core logic in Python "just for now"; adding a Python fallback
during a wheel-version skew; splitting a behavior across both repos.

**Cite.** `src/sase/core/rust.py` module docstring (strict loader contract) ·
`202604/rust_backend_migration.md` (the 2026-04-29 update recording the dispatcher
removal) · `pyproject.toml:46` · `docs/rust_backend.md` ·
`202608/core_dependency_window_ratchet/` for the version-window consequence.

### 3.3 Verification is two-speed because host capacity is the constraint

**Decision.** `just check` runs whole-repo lint gates plus a diff-scoped test lane
selected from a static import-graph closure; `just check-full` — every gate plus the full
suite — is reserved for landing, broadening changes, and CI, and is run through a monitor
rather than inline.

**Tests.** Recurrence ✓ · Reversal cost ✓ · Invisibility ✓ · Contested ✓ · Settled ✓

**Why third.** `build_and_run.md` already carries the policy in unusual detail, so the
marginal value is not the rule — it is the measurement that makes the rule non-negotiable.
The measured finding is counter-intuitive enough that agents override it: the suite is not
slow because tests are slow. Roughly 200–400 full-suite runs per day are admitted against
a host supplying about 46,000 worker-minutes per day at about 61 worker-minutes per run,
so the suite consumes a quarter to a half of the machine's entire gated capacity
continuously. Every downstream symptom — 45-minute gate waits, contention flakes — follows
from that one number. An agent that "just runs the full suite to be safe" is not being
careful; it is taking capacity from every sibling workspace.

**Prevents.** Reflexive `check-full`; treating scoped selection as a shortcut rather than
a heuristic backstopped by CI; re-deriving the capacity argument every quarter.

**Cite.** `202608/test_suite_verification_architecture/` (bottom line and the capacity
arithmetic) · `202605/just_check_speed_research.md` · `Justfile:614,635` ·
`tools/select_tests`, `tools/selection_health`.

### 3.4 No retrieval mechanism ships before its corpus

**Decision.** SASE does not build memory retrieval, linking, or recall machinery ahead of
a corpus that demonstrably needs it. Mechanism follows corpus; the corpus is the evidence
that the mechanism is the right shape.

**Tests.** Recurrence ~ · Reversal cost ✓✓ · Invisibility ✓✓ · Contested ✓ · Settled ✓

**Why fourth, and why it is the most valuable negative record.** This decision was learned
three times at real cost, and every artifact of the learning has been deleted:

| Feature | Built | Removed | Removal commit |
| --- | --- | --- | --- |
| Dynamic memory (keyword-triggered recall) | 2026-04-12 | 2026-05-31 | `e8c2f14bb` |
| Memory episodes (94 touching commits) | 2026-05-23 | 2026-06-15 | `37973b8b3` |
| Memory note `keywords:` metadata | — | 2026-07-13 | `21e1640ee` |

The episodes removal alone deleted a CLI command family, a package, a wire/facade layer,
an ACE modal with its keybinding and TCSS block, a doctor check, a console script, a docs
page, and its tests — three weeks after the first episode commit landed, with cleanup
commits trailing until 2026-08-08. Nothing in the current tree records that it happened.
Meanwhile `202608/directed_zettelkasten_first_post/` reached the same conclusion
independently from a different direction — *"the methodology is the
failure mode it treats"* — and `glossary_to_memory_webs.md` §3.4 and §1.4(i) are both
explicitly resting on this lesson to justify shipping `decisions` with no closure engine.
The lesson is currently doing load-bearing work while existing nowhere addressable.

**Prevents.** The fourth attempt. Concretely: it is the argument that keeps the
`decisions` web from acquiring a link model in v1, and it is the specific reason
`21e1640ee`'s removal of `keywords:` must not be quietly undone by strand-level
addressing aliases (see `glossary_to_memory_webs.md` §4.2).

**Cite.** The three removal commits above ·
`202605/sase_episodes_events_decision_consolidated.md` ·
`202604/dynamic_memory_critique.md` · `202608/directed_zettelkasten_first_post/`.

### 3.5 SASE invents domain nouns instead of reusing industry terms

**Decision.** Load-bearing concepts get purpose-built SASE nouns — `bead`, `stitch`,
`patch`, `proc`, `chop`, `node`, `tribe`, `clan`, `hood`, `xprompt`, `tale`, `lumberjack`
— rather than borrowed industry terms, and renames are executed as hard cutovers with a
terminology lint rather than deprecation aliases.

**Tests.** Recurrence ✓✓ · Reversal cost ~ · Invisibility ✓ · Contested ✓✓ · Settled ✓

**Why fifth.** This is the first thing every agent and every new reader encounters, and it
is the single largest source of "is this the same thing as X?" confusion. The glossary
holds 34 terms but by construction holds no policy: it says what a Stitch is, never why
SASE has a word for it. The policy is genuinely contested and the record can prove it —
`202608/naming_the_change_unit/` is a consolidated three-way report that recommended
**`rivet`**, and the project shipped **`Patch`** (`b5786b57f`, 2026-08-11). An ADR that
records a recommendation *not* taken, with the reason, is worth more than five that record
agreement. The record should also state the rename mechanics, because they are unusual:
`_lint-patch-stitch-terminology` is a standing gate, and the commit log shows ~30
terminology cutovers (`task`→`proc`, `lane`→`node`, `group`→`tribe`, `companion`→`sidecar`,
`vcs`→`stitch`, `ChangeSpec`→`Patch`) executed without compatibility aliases.

**Prevents.** Re-litigating names; introducing an industry-term synonym alongside a SASE
noun; adding deprecation aliases during the next rename.

**Cite.** `202608/naming_the_change_unit/` · `202607/sawi_rename_decision/` ·
`202607/xprompt_plang_rename_consolidated.md` ·
`202606/coral_subcommand_naming_consolidated.md` ·
`202606/sase_rename_research_consolidated.md` ·
`Justfile:_lint-patch-stitch-terminology` · `docs/change_spec.md`.

### 3.6 Bead state is an append-only event log; JSONL is a projection

**Decision.** The canonical, git-portable bead state is append-only per-stream event logs
under `events/`; `issues.jsonl` is a generated compatibility projection and `beads.db` a
local cache. Writes append events first, then regenerate. Agents never hand-edit any of
the three.

**Tests.** Recurrence ✓ · Reversal cost ✓✓ · Invisibility ✓ · Contested ✓ · Settled ✓

**Why sixth.** The motivating problem is invisible from the tree and impossible to infer:
a single mutable JSONL file shared across ~30 numbered workspaces and three machines
produces constant merge conflicts, which is what `202605/bead_jsonl_merge_conflicts.md`
and `202605/greenfield_bead_storage_architecture.md` were written to solve. The chosen
design also carries non-obvious semantics an agent can violate by "fixing" data directly:
dependency removals sort after same-timestamp adds; duplicate closes are retained but
ignored so `closed_at` cannot move; reads prefer the manifest and fall back to legacy
JSONL only when no event store exists. `sase_beads.md` states the never-hand-edit rule;
the record supplies the reason that makes it obviously correct.

**Prevents.** Editing `issues.jsonl` to repair state; resolving a bead-store merge conflict
by hand; assuming `beads.db` is authoritative.

**Cite.** `docs/beads.md` §"Event Log + Compatibility Projections" ·
`202605/greenfield_bead_storage_architecture.md` · `202605/bead_jsonl_merge_conflicts.md`.

### 3.7 Memory is flat, tiered, and file-backed

**Decision.** Agent-facing memory is flat markdown notes at one level under
`sase/memory/`, split into always-loaded core (Tier 1) and read-on-demand reference
(Tier 2), rendered into `AGENTS.md` and per-provider shims by a generator, and reached
through audited reads rather than free filesystem access.

**Tests.** Recurrence ✓ · Reversal cost ✓ · Invisibility ✓ · Contested ✓✓ · Settled ✓

**Why seventh.** Flatness is enforced, not incidental — `_is_flat_note_path(parts)` is
literally `len(parts) == 1`, and six AMD path regexes hard-code a flat filename with a
character class that excludes `/`. That constraint is the single largest determinant of
the memory-webs design (its §4.1 drops the `webs/` segment specifically because of it),
and it is currently discoverable only by reading six regexes. The tier split is equally
contested: the glossary note alone has moved between tiers four times, which is the
strongest evidence that the split is real and that per-collection tiering was the missing
knob. Write this before the web migration, so the web ADR has something to supersede.

**Prevents.** Proposing nested memory paths; moving a note between tiers without a reason;
re-deriving why generated shims must accept old anchors.

**Cite.** `src/sase/memory/read_log.py:158,161` · `src/sase/amd/_agents_doc.py:13-33` ·
`feat(memory)!: remove legacy memory layout support` (`257d9e654`, 2026-06-17) ·
`202604/short_term_vs_long_term_memory.md` · `202605/sase_amd_command_research.md` ·
`202606/amd_memory_init_consolidated.md`.

### 3.8 Completion is a host-owned finalizer declaration, not an agent's word

**Decision.** A turn completes when the host's selected finalizers are satisfied. The
agent submits one atomic, turn-bound declaration; bounded providers execute and verify
postconditions independently; refusal requires a reason and normally fails the run.
Prompt text can never supply an executor, environment, or repository path, and installing
a plugin never activates a finalizer.

**Tests.** Recurrence ✓ · Reversal cost ✓ · Invisibility ~ · Contested ✓✓ · Settled ✓

**Why eighth.** Three consolidated research reports in a single month
(`finalizer_protocol_and_extensibility`, `finalizer_completion_contracts`,
`finalizer_integrity_and_capabilities`), two epics (`sase-rn`, `sase-rr`), and a breaking
cutover (`2f9c4ae29`, 2026-08-21) that made pluggable finalizers the only completion path.
The design's defining property is a rejection: finalizers are deliberately *not* generic
stop hooks, and the trust boundary — host-owned selection, agent-supplied judgment only —
is the whole point. That rejection is exactly the kind of thing a future proposal will
re-propose. The mechanical exemptions (`/sase_plan`, `/sase_monitor`, `/sase_pipe`,
`/sase_questions` terminate the runner before the success path) belong in the record too,
because they look arbitrary without it.

**Prevents.** Reintroducing prompt-supplied finalizer configuration; adding a generic stop
hook; treating an intent to resume later as an exemption.

**Cite.** `202608/finalizer_protocol_and_extensibility/` ·
`202608/finalizer_completion_contracts/` · `202608/finalizer_integrity_and_capabilities/`
· `202607/pluggable_finalizers_final_directive.md` · `2f9c4ae29` ·
`src/sase/finalizers/` (33 modules).

### 3.9 Agents work in ephemeral numbered workspace clones

**Decision.** Each agent runs in a numbered full clone of the project's primary repo
(`sase_1`…`sase_30`) with its own virtualenv, claimed atomically from a registry
immediately before spawn. Workspaces are not repos, are not stable across runs, and must
never be named in a durable artifact.

**Tests.** Recurrence ✓✓ · Reversal cost ✓ · Invisibility ~ · Contested ✓ · Settled ✓

**Why ninth.** Ranked below its recurrence because core memory already carries the
operative consequences — `sase.md` forbids naming a workspace in a plan, and
`build_and_run.md` requires `just install` before anything else in a cold workspace.
What core memory cannot afford is the *why* — per-workspace venvs are what make parallel
agents isolated, and lazy materialization of linked repos and sidecars into a workspace is
what keeps 30 clones affordable. Without that, the rules read as arbitrary ceremony and
get skipped by the agent in a hurry.

**Prevents.** Running commands against a sibling workspace's venv; hard-coding a workspace
path in a plan or bead; cloning a linked repo by hand instead of through `sase repo open`.

**Cite.** `docs/workspace.md` (project / repo / workspace distinction) ·
`202605/workspace_directory_layout_research.md` · `src/sase/workspace_provider/lease.py` ·
`feat(workspaces)!: scope linked repos to host workspaces` (`a26272942`) ·
`feat!: make linked repository materialization opt-in` (`c13664dc6`).

### 3.10 Durable non-code state lives in sidecar repos, cloned lazily and by consent

**Decision.** Plans, research, beads, and agent-hood snapshots live in separate sidecar
repositories rather than in the primary repo. They are cloned on demand, carry their own
visibility settings, and publishing one is an explicit consent action; every cross-repo
read goes through `sase repo open` and is recorded in an audit trail.

**Tests.** Recurrence ✓✓ · Reversal cost ✓ · Invisibility ✓ · Contested ✓ · Settled ✓

**Why tenth.** The recurrence is very high — `/sase_repo` is mandatory for every
non-workspace read, including web-transport reads of a repo's files — but the *rule* is
already stated forcefully in core memory, so the record's job is narrower: why the split
exists at all (a primary repo that would otherwise carry ~161MB of research PNGs, per the
sdist exclusion note in `pyproject.toml`), and why publication is consent-gated (agent-hood
snapshots publish prompts and family relationships to anyone who can read the remote).
That privacy argument is genuinely non-obvious and is currently in one docs page.

**Prevents.** Committing plans or research into the primary repo; web-fetching another
repo's files; creating an `agents` sidecar remote without setting visibility first.

**Cite.** `docs/agents_sidecar.md` §"Privacy and configuration" ·
`split_plans_research_companion_layout_consolidated/` (repo root) ·
`202607/shared_sdd_clone_consolidated.md` · `202606/sibling_repos_removal_consolidated.md`
· `pyproject.toml` sdist `only-include` comment · `feat(sdd)!: rename companion
repositories to sidecars` (`3cf8ea2bf`).

---

## 4. Tier 2 — the second wave

Real ADRs, all of which pass the tests, held back only because the seed set has to prove
the web is worth having before the web earns more of the budget.

**11. Provider boundaries are pluggy entry points, and runtimes are uniform.** Four entry
point groups (`sase_llm`, `sase_vcs`, `sase_workspace`, `sase_artifact_refs`), mostly
`firstresult=True`; `use:` fields require a plugin prefix (`54da09ba5`). The uniformity
corollary — no runtime-specific branching, all runtimes have hooks, skills, and the same
commit workflow — is already a `gotchas.md` rule and is violated by well-meaning
special-casing. Cite `docs/plugins.md`, `202602/pluggy_repo_separation.md`,
`202602/sase_plugin_specifics.md`.

**12. Structure is machine-enforced: 700-line modules and symbol-visibility linting.**
`toobig src 1000 850 700` plus symvision unused-symbol and private-misuse gates, on an
agent-authored codebase of 3,759 modules whose largest file is 698 lines. This is a
construction-technique decision in Nygard's sense and is the reason "split X into focused
modules" appears throughout the log. The record should say what it buys — bounded context
per read, cheap review, mechanical enforcement instead of taste. Cite `Justfile:339`,
`sase/memory/symvision.md`, `202607/scalable_skill_disclosure.md` for the same principle
applied to prompts.

**13. Feature flags gate not-yet-ready behavior only, and every flag files its removal
bead.** Two kinds (`beta` default off, `sunset` default on), creation only through `sase
flag new`, removal tracked as a typed task bead. The record should carry the boundary that
`feature_flags.md` states but does not justify — a permanent user choice is a config field,
not a flag — and should be honest that enforcement is imperfect: all three live flags are
85–88 days old. Cite `202608/feature_flag_architecture.md`,
`202608/feature_flag_lifecycle_governance/`, `202608/open_feature_flag_closeout/`,
`98b27e849`.

**14. Cut over state; never break an already-emitted document.** Two halves of one policy
that look contradictory until stated together. State and identity migrate hard — three
migration facades were reverted in a single day (`f2cd75bc5`, `850cb910e`, `e433d3885`,
2026-08-03) — because a small, fully-owned deployment does not need them. Generated
documents are the exception: `parse_amd_agents_document` reads shims emitted by older
versions, so parsers must **add, never replace** accepted forms. Cite those three reverts,
`glossary_to_memory_webs.md` §5, `src/sase/amd/_agents_doc.py`.

**15. Human-in-the-loop is one typed gate substrate, not per-surface prompts.** Durable
interaction requests under `~/.sase/interaction_requests/<kind>/<id>/` carry the reviewed
content, option-query branches, validation schemas, and hash-verified commands; the
notification row is a projection; ACE, mobile, Telegram, and CLI resolve the same bundle;
unanswerable gates fail closed at creation (`ff0b765a4`), and free-text smuggling was
deliberately removed (`27d04a679`). Cite `docs/notifications.md`,
`202607/unified_notification_gates_consolidated.md`, `202608/gate_input_collection/`.

**16. Artifact identity is `<kind>:<argument>` behind a provider registry.** A closed
six-relation link registry, a versioned wire schema (bumped to 5 in `cb453a529`), and
plugin-supplied kinds. Worth recording now rather than later because the memory-web
address `<web>:<keyword>` was chosen to be artifact-compatible — that compatibility is a
decision with a cost, and it should be legible before someone "simplifies" either grammar.
Cite `sase/memory/sase_artifacts.md`, `202608/ref_provider_contract/`,
`202608/artifact_link_graph/`, `f53e43ab1`.

---

## 5. Tier 3 — not yet, and why

- **The memory-webs decision itself.** It will eventually be the most-cited strand in the
  web, and it is tempting to write it first. Do not: as of this report it is a research
  recommendation, not a decision. Write it when phase 2 lands, and have it record what
  §3.7's ADR superseded.
- **Telemetry is local-only; no bundled monitoring stack.** Prometheus ingestion was
  replaced by a local store and the bundled stack removed (`7ccc4688c`, `55df5a75b`,
  2026-07-17). Genuinely settled and cleanly reasoned, but low recurrence — an agent
  almost never faces this choice.
- **Model aliases are keyed by size, not role.** Roles were replaced by size launch
  settings (`2fcca46eb`, 2026-08-15) after load-balanced pools (`5a23c297f`) and several
  earlier reshuffles. The rate of change here is still high enough that a record would
  need revision within a quarter; wait for it to hold still.
- **The agent taxonomy: family, clan, tribe, hood, node.** Five terms, all in the glossary,
  all still moving (the most recent commit in the log promotes a chop member to clan
  declarer at dispatch time). The glossary covers the *what*; an ADR on the *why* should
  wait until the shape stops changing.

---

## 6. Record format that fits the web design

Constraints inherited from `glossary_to_memory_webs.md`:

- **Slug is identity, keyword is display (§3.7).** Numbering therefore freezes at creation,
  which is correct for ADRs and matches Nygard. Filename `0007-rust-core-boundary.md`,
  `keyword: Rust Core Boundary`. A useful free consequence: `normalize_glossary_reference`
  resolves a unique normalized prefix, so `sase memory read decisions:0007` works without
  building anything.
- **Lifecycle fields go in an opaque `metadata:` mapping (§4.2).** `status`,
  `decided_on`, `supersedes`, `epic`, `commits` — generic memory code must not interpret
  them, so the ADR's own vocabulary stays out of the memory schema.
- **No closure in v1 (§3.4).** ADR titles do not occur inside each other's prose, so
  mention-closure would fire on nothing. Supersession is prose until the corpus is large
  enough to justify adopting the existing `supersedes` / `superseded-by` artifact
  relations. Three of the ten seed records will already want a supersession link; write
  them as prose and treat that as the v2 trigger.
- **The web note renders as `reference`, and only its own body inlines (§3.6).** Ten ADR
  bodies at 250–450 words would be 2,500–4,500 words — more than the entire 2,273-word core
  budget. The roster belongs in Tier 2.
- **Status vocabulary.** Keep it to four: `accepted`, `superseded`, `reversed`,
  `amended`. `reversed` is not standard ADR vocabulary and should be added deliberately,
  because §3.4's record and the vocabulary record both need it and "superseded" understates
  what happened.

Two writing rules worth fixing before the first strand:

1. **Lead with the rejected alternative.** In this corpus the alternative is almost always
   the interesting part, and it is the part no reader can reconstruct.
2. **Cite, never restate, the research report.** The research sidecar is the evidence
   layer; the ADR is the conclusion layer. A strand that restates a consolidated report
   will be stale within a month and long from birth.

---

## 7. Ranked recommendation

| # | Decision record | Status | Passes | Est. words |
| --- | --- | --- | --- | --- |
| 1 | Agents are single-turn; continuation is mechanical | accepted | 5/5 | 400 |
| 2 | The Rust core is required and has no Python fallback | accepted | 5/5 | 450 |
| 3 | Verification is two-speed because host capacity is the constraint | accepted | 5/5 | 400 |
| 4 | No retrieval mechanism ships before its corpus | accepted | 4/5 | 450 |
| 5 | SASE invents domain nouns instead of reusing industry terms | accepted | 4/5 | 400 |
| 6 | Bead state is an append-only event log; JSONL is a projection | accepted | 5/5 | 350 |
| 7 | Memory is flat, tiered, and file-backed | accepted | 5/5 | 400 |
| 8 | Completion is a host-owned finalizer declaration | accepted | 4/5 | 400 |
| 9 | Agents work in ephemeral numbered workspace clones | accepted | 4/5 | 300 |
| 10 | Durable non-code state lives in consent-gated sidecar repos | accepted | 5/5 | 350 |
| 11 | Provider boundaries are pluggy entry points; runtimes are uniform | accepted | 4/5 | 300 |
| 12 | Structure is machine-enforced: 700-line modules, symbol linting | accepted | 4/5 | 300 |
| 13 | Feature flags gate not-yet-ready behavior; each files a removal bead | accepted | 4/5 | 300 |
| 14 | Cut over state; never break an already-emitted document | accepted | 4/5 | 350 |
| 15 | Human-in-the-loop is one typed gate substrate | accepted | 4/5 | 350 |
| 16 | Artifact identity is `<kind>:<argument>` behind a provider registry | accepted | 4/5 | 300 |

**Cut line after #10.** That is ~3,900 words of strand bodies — a real corpus, written
from history that already exists, and the smallest set that makes the web worth keeping.
Records 11–16 are the second wave; write them when the first ten have been *read* by an
agent that would otherwise have gotten something wrong. The Tier 3 items in §5 stay
unwritten until they are settled.

**If you only write three,** write 1, 2, and 4. Number 1 is violated most often, number 2
is the most expensive to violate, and number 4 is the only one whose subject matter has
already been deleted from the tree three times.

---

## 8. What was checked

Measured at `sase@4041c17e4` on 2026-08-24: commit counts and the 208 breaking-change set
via `git log`; `src/` and `tests/` LOC and module counts; `Justfile:286-341,614-660`
(`_lint-toobig`, `_lint-symvision`, `_lint-patch-stitch-terminology`, `check`,
`check-full`); `pyproject.toml:10,41,46,155-200` (Python floor, `pluggy`, the
`sase-core-rs` window, four entry-point groups, sdist `only-include`);
`src/sase/core/rust.py` strict-loader docstring; `src/sase/finalizers/` (33 modules);
`src/sase/memory/read_log.py`; `docs/architecture.md`, `docs/beads.md`, `docs/monitors.md`,
`docs/notifications.md`, `docs/workspace.md`, `docs/agents_sidecar.md`,
`docs/change_spec.md`; `src/sase/xprompts/skills/sase_monitor.md`. Live CLI state:
`sase repo list`, `sase project list` (3 enabled), `sase flag list` (3 open, 85–88 days).
Linked `sase-core` at `835d6c3` via `sase repo open`: 4 crates, 213,719 Rust LOC, 859
commits since 2026-04-28. Research sidecar via `sase repo open`: 307 distinct topics, 411
markdown files, 75 consolidated, 104 swarm drafts.

Removal and rename commits verified individually: `e8c2f14bb`, `37973b8b3`, `21e1640ee`,
`257d9e654`, `f2cd75bc5`, `850cb910e`, `e433d3885`, `b5786b57f`, `2f9c4ae29`, `ac5d95810`,
`b20637f4f`.

Not verified, out of scope: whether any Tier 2 candidate has an in-flight epic that would
change its conclusion before it is written; whether `bob-cli` or `actstat` would want
project-scoped `decisions` webs of their own; the exact strand-count threshold at which
prose supersession becomes painful enough to adopt `supersedes` relations.

## 9. Sources

Repository evidence as enumerated in §8. Research sidecar reports cited inline, principally
`202608/glossary_to_memory_webs/`, `202608/test_suite_verification_architecture/`,
`202608/naming_the_change_unit/`, `202608/finalizer_*`,
`202608/directed_zettelkasten_first_post/`,
`202608/feature_flag_*`, `202608/core_dependency_window_ratchet/`,
`202608/monitor_command_substrate/`,
`split_plans_research_companion_layout_consolidated/`,
`202606/amd_memory_init_consolidated.md`, `202605/greenfield_bead_storage_architecture.md`,
`202605/bead_jsonl_merge_conflicts.md`, `202605/workspace_directory_layout_research.md`,
`202605/sase_episodes_events_decision_consolidated.md`, `202604/rust_backend_migration.md`,
`202604/short_term_vs_long_term_memory.md`, `202602/pluggy_repo_separation.md`.

External:

- Michael Nygard, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
  — one decision per small file, sequential immutable IDs, superseded records retained.
- AWS Prescriptive Guidance, [Architectural decision record process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
  — overview/detail split, lifecycle states, immutability and supersession.
- Anthropic, [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  — progressive disclosure and just-in-time retrieval, the model the roster/strand
  split follows.
