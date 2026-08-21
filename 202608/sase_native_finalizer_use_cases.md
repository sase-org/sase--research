---
create_time: 2026-08-21
updated_time: 2026-08-21
status: research
---

# Completion Contracts, Not Stop Hooks: SASE-Native Uses for Generalized Finalizers

**Research question:** Now that SASE finalizers are host-owned, configurable, and
selectable, what *new* uses are uniquely valuable — uses that go beyond “run a
local check and then commit”?

**Scope:** Primary SASE at `f425005a0f95b1ced138ae5018ed8a60e99e2c6d` on 2026-08-21.
Closed epic `sase-rn` (host-owned pluggable finalizer protocol) and in-progress epic
`sase-rr` (make that protocol unconditional). Plans
`plan:202608/pluggable_finalizers.md` and
`plan:202608/retire_pluggable_finalizers.md`. Prior research
`research:202608/finalizer_protocol_and_extensibility/finalizer_protocol_and_extensibility.md`
and the same-day companion
`research:202608/generalized_finalizer_use_cases.md`. Adjacent SASE surfaces: xprompts
and role tags, file hooks, gates, monitors, `sase var`, beads, artifacts, and the
`just check` / scoped-test lane. External analogs: Claude Code Stop hooks and GitHub
required checks.

This report is complementary, not a restatement. The companion catalog already covers
CI-shaped gates (adaptive verification, policy, SBOM, preview deploy). The cut here is
**SASE-native completion contracts**: promoting prompt-only law into host enforcement,
binding those contracts to roles and xprompts, and reconciling beads, artifacts, vars,
flags, and Patches while the host still owns the workspace.

## Bottom line

Treat a finalizer as a **named, host-verified condition that must hold before a normal
SASE turn may honestly be called complete.** Configuration owns executable policy.
`%final` only selects among configured instances. The agent supplies typed intent only
where judgment is unavoidable. The host executes, independently verifies, and records
evidence.

The highest-leverage move is not inventing new kinds of CI. It is **taking obligations
that SASE already writes into prompts, skills, and xprompts and making the
machine-checkable ones fail closed.** Today `just check`, land-epic closeout,
`/sase_repo` and `/sase_memory_read` ceremony, research-document shape, swarm handoff
keys, and “do not mention the workspace path in a plan” are all social contracts. The
new protocol is the first place those contracts can become real.

Do that by **role**, not by a global default. A universal `just check` would punish
research, chat, plan, and question turns. The commit instance is already a good
default because it is *triggered* by attributable dirt. New instances should either
share that trigger discipline or be selected by the xprompt that already knows the
turn’s job (`#commit`, `#pr`, `#bd/work_phase_bead`, `#bd/land_epic`, `#research`,
`#coder`).

Start this week with `builtin@command` plus xprompt-injected `%final`. Save
declaration-heavy providers until `sase-rr` finishes the non-commit payload bridge
(see “Current seams” below). Keep file hooks, gates, monitors, notifications, and CI
in their own jobs.

## How to think about the new substrate

`sase-rn` replaced a hard-coded `run_commit_finalizer()` call with a sealed plan,
turn-bound declaration, isolated providers, ordered execution, and a bounded
fixed-point controller. `sase-rr` is making that path unconditional. Five properties
matter for product thinking:

| Property | What it buys |
| --- | --- |
| Trusted instance registry | Policy, argv, timeouts, retries, credentials, and required instances live in config. Prompt text cannot smuggle an executor. |
| `%final` as ordered selection | A launch can add, remove, or replace configured instances. Omitting `%final` keeps `defaults` (bundled: `commit`). `required` cannot be opted out. |
| Turn-bound atomic declaration | When a selected instance needs model input, `/sase_final` submits one nonce- and digest-bound envelope. Intent is not proof. |
| Isolated `describe` / `validate` / `execute` / `verify` | Plugins report evidence; the host owns completion, ordering, retries, and failure. |
| Durable artifacts | `finalizer_plan.json`, `final_context.json`, `final_submission.json`, per-attempt output, and `finalizer_result.json` make the contract inspectable. |

The closest industry analog is a Claude Code **Stop hook**: a check that can refuse to
let the turn end. The important differences are that SASE’s check is selected from
trusted configuration rather than arbitrary session scripts, that agent input is a
typed declaration rather than another free-form prompt, that execution is isolated and
bounded, and that success is a host-verified fixed point rather than “the hook exited
zero.” GitHub required checks remain the authoritative *merge* gate; SASE finalizers
are the earlier *agent-completion* gate, with workspace, baseline, and artifact
context GitHub does not have.

Live effective policy in this workspace is still the bundled default: one selected
instance, `commit` / `builtin@commit`. Everything below is unused capacity.

## Current seams that change which ideas are ready

These constraints are load-bearing. Several otherwise attractive uses are “later”
because of them, not because they are bad ideas.

1. **Normal-success only.** Finalizers run after a successful provider return. Intentional
   `/sase_plan`, `/sase_monitor`, `/sase_pipe`, and `/sase_questions` handoffs terminate
   the runner first. A provider crash never reaches the controller. A finalizer cannot
   be the sole owner of cleanup, lease release, or “always run.”
2. **`builtin@command` is the ready path.** Trusted argv, `cwd: primary`, configurable
   timeout, `submission: none`, zero-exit as success. Ideal for `just check`,
   formatters, scanners, `sase bead epic-symbols`, and any deterministic local check.
   It cannot take a typed agent payload in version 1.
3. **External providers are richer but currently fail closed, and the payload bridge is
   incomplete.** At this revision,
   `src/sase/finalizers/declaration.py` `_validate_provider_payloads()` validates only
   `builtin@commit`, and `src/sase/finalizers/executor.py` `_provider_request()` passes
   config and selection but not the accepted payload or host obligations. External
   instances still publish `submission_required: true`. This is already recorded on
   `sase-rr`; do not file it again. Until that epic lands, do not design products that
   need the model to submit a non-commit schema.
4. **Plugin workers have a host-fixed 30-second operation cap**
   (`PROVIDER_OPERATION_TIMEOUT_SECONDS`). `builtin@command` timeouts are trusted and
   configurable (`just check` needs minutes, not seconds). Long work belongs on a
   monitor or CI, not an external provider subprocess.
5. **Atomic declaration is not atomic effects.** A later instance can fail after an
   earlier one committed or mutated an external system. Side-effecting providers must
   be idempotent, keyed by run/tree identity, independently verifiable, and ordered
   with irreversible work last.
6. **Non-commit instances currently run once per controller pass; commit can be
   reactivated by later dirt.** Mutators before checks before commit. Do not assume
   `%final:foo` inserts `foo` before an already-selected `commit` unless `after:` says
   so.

## Adjacent mechanisms: do not steal their jobs

A completion contract is the wrong tool for most “something should happen around an
agent” ideas. Use the existing surface that already owns that job.

| Need | Use this | Not a finalizer because |
| --- | --- | --- |
| Per-file post-commit publication (research Highlights PDFs, index updates) | `file_hooks` | Non-gating, per-file, after the stitch exists. `research-highlights` is the example. |
| User must choose before a dangerous command | `sase gate` | Completion should not block on a human unless the *definition of done* is that choice. Even then, file the gate from a provider only after local checks and preferably after commit proof. |
| Work that outlives the turn | `sase monitor` | `just check-full`, deploys, flake hunts. The agent must hand off; the monitor follow-up is the next contract. |
| Observation without blocking success | notifications / telemetry | Slack/Telegram “the agent finished,” metrics, traces. |
| Small cross-agent facts | `sase var` | Wrong store for completion intent (not turn-bound, wrong schema, not coverage-checked). Excellent as *evidence a finalizer verifies*. |
| Open-ended judgment | another agent, mentor xprompt, or `/review` | Do not put an LLM in the completion-critical path. |
| Authoritative merge/release proof | CI, protected branches, signed provenance | Workspace-local evidence is traceability, not SLSA. |
| Guaranteed teardown | leases, TTLs, runner `finally` | The current seam is skipped on failure and handoff. |

**Litmus test.** A use is a strong finalizer when most of these are true:

- The condition must hold before a normal run may be called complete.
- It needs the *final* workspace, baseline delta, agent artifacts, or commit proof.
- A deterministic host or provider can verify the postcondition.
- Execution is bounded and retry-safe, or a timeout can fail with evidence.
- Trusted configuration grants any command, credential, or external authority.
- Order relative to other completion conditions matters.

It is a weak finalizer when it is merely informative, unbounded, must run after
crashes, or exists only to ask another model for a general opinion.

## Idea 1 — Promote prompt-only law into host contracts

SASE already has a large informal definition of done. Agents.md, generated skills, and
xprompts tell the model to `just check`, to open other repos through `/sase_repo`, to
read long-term memory through `sase memory read`, to keep workspace paths out of plan
files, to record `PROPOSED FOLLOW-UP:` instead of creating beads from a phase worker,
and to close land-epic work only after `sase bead epic-symbols` is clean.

Those rules fail open. The model can forget, skip, or hallucinate compliance. The new
protocol is the first place the *checkable* subset can fail closed, with evidence.

### 1.1 Verification that already has a command

`just check` is the obvious first instance. The test-suite research
(`research:202608/test_suite_verification_architecture/test_suite_verification_architecture.md`)
already concluded that **diff-scoped selection is the default agent check** and that
the full suite is an integration/CI lane. Promoting `just check` (which is lint plus
`just test-scoped`) to a finalizer does three things prompt text cannot:

- It runs on the *final* tree, after the last edit, not on a mid-turn snapshot the
  agent pinky-swears was green.
- It records argv, exit, duration, and logs under `finalizers/<instance>/`.
- It can sit *before* `commit` via `after:`, so a red check never becomes a stitch.

`just check-full` remains a monitor. Visual PNG snapshots remain `just test-visual` as
an opt-in profile. `just install` can be the first command in a small wrapper if the
workspace venv may be stale; it should not be a separate always-on instance.

The design mistake would be making `just check` a *global* default. Research, planning,
and chat turns that never touch the primary tree should not pay for a scoped pytest
closure. Two safe shapes:

- **Xprompt-selected:** `#commit`, `#pr`, `#coder`, `#bd/work_phase_bead`, and
  `#bd/land_epic` inject `%final:check` (see Idea 2).
- **Dirt-triggered wrapper:** a trusted command that exits 0 immediately when the
  primary baseline delta is empty, and otherwise runs `just check`. That wrapper is
  safe enough to put in `defaults` beside `commit`.

A first config that does not need a plugin:

```yaml
finalizers:
  defaults: [commit]
  required: []
  instances:
    check:
      use: builtin@command
      after: []
      max_attempts: 1
      config:
        command: [just, check]
        cwd: primary
        timeout: 20m
        submission: none
    commit:
      use: builtin@commit
      after: [check]
      max_attempts: 2
      refusal: fail
```

Launches that should verify then add `%final:check`. Until a dirt-triggered wrapper
exists, do not put `check` in `defaults`.

### 1.2 Ceremony that already has an audit log

Several SASE rules are already observable in durable logs. A `builtin@command` (or a
later small plugin) can verify them against the *current run* rather than trusting
prose:

| Prompt-only rule | Host fact a finalizer can check |
| --- | --- |
| Read other repos only through `/sase_repo` | `sase repo log` for this agent/workspace vs. paths actually read |
| Read canonical memory only through `sase memory read` | memory-read audit events vs. direct reads of `sase/memory/*.md` |
| Do not mention the ephemeral workspace directory in a plan | grep of newly dirtied `plans` sidecar files for `sase_<N>` path shapes |
| Generated skill sources are not hand-edited in chezmoi | dirt in managed `SKILL.md` destinations vs. `src/sase/xprompts/skills/` |
| Feature-flag edits follow `sase flag new` | `tools/check_feature_flags` already exists; run it when the flag registry or bead changed |
| Conventional commit subject | already enforced inside `sase stitch create` |

These are high-uniqueness, low-drama uses. They encode *SASE’s own operating system*,
not generic software engineering. A single `sase-hygiene` command that inspects the
run’s artifacts directory, repo-open log, and baseline delta would be more valuable
than a third-party secret scanner for this project.

### 1.3 Land-epic and phase-worker closeout

`#bd/land_epic` is a multi-step definition of done written as prompt prose: review
every child note, integrate later commits, route `PROPOSED FOLLOW-UP:` through
`/sase_new_task`, run `sase bead epic-symbols`, close the epic, run `just symvision`,
set the plan file to `status: done`. Phase workers are forbidden from creating beads
and must append `PROPOSED FOLLOW-UP:` notes instead.

A land-epic finalizer cannot *perform* the judgment in steps 1–2. It can require
evidence that the mechanical tail happened:

- `sase bead epic-symbols <id>` is empty, or the Justfile lines were re-keyed.
- The plan file frontmatter is `status: done` after a successful close (the existing
  commit finalizer already auto-commits a narrow wip→done frontmatter change; a
  land-specific instance can refuse success if the plan is still `wip` while the
  epic is `closed`).
- Every `PROPOSED FOLLOW-UP:` on child beads has a recorded outcome in the land
  close note (string presence check; later, a typed declaration).

Phase workers can have the inverse contract: fail if the run created a new task bead.
That is a real, currently social, invariant.

## Idea 2 — Bind completion profiles to xprompts and roles

`%final` is launch-scoped. Xprompts already classify launches by job. That is the
missing product seam.

Trusted xprompt bodies (project, user, and package — the same layers that already
inject commit instructions) should be allowed to contribute default selector
operations, applied *before* the user’s `%final`. Prompt text remains selection-only;
the xprompt is itself trusted configuration. Combined with
`research:202608/xprompt_role_binding/xprompt_role_binding.md`, a future `#tag/land_epic`
could resolve both the prompt *and* the completion profile.

A concrete portfolio for this project:

| Launch shape | Suggested `%final` effect | Why |
| --- | --- | --- |
| Bare chat / questions / plan / monitor handoff | bundled `commit` only (handoffs skip the controller anyway) | Do not tax thinking turns. |
| `#commit` / `#propose` / `#pr` / `#coder` | add `check` before `commit` | Code-changing rollover already knows a stitch is the point. |
| `#bd/work_phase_bead` | add `check`, then `commit`; optional `phase-hygiene` | Implementation under an epic. |
| `#bd/land_epic` | add `check`, `epic-symbols`, `commit` | Closeout is mechanical enough to verify. |
| `#research` / `#research/more` / `#research_swarm` | `%final:none,research-doc,commit` | Do not run `just check` on the primary sase tree; do require a well-formed research artifact and then commit the research sidecar. |
| `#mentor` / review | `%final:none` or `review-packet` only | Reviewers should not commit unless asked; they *should* produce a structured findings artifact. |
| Release / soak agents | `%final:none,check-full-via-monitor-is-wrong,compat,commit` | Named heavy profiles, never defaults. |

This is the highest-leverage *product* change relative to the companion catalog.
Without it, Bryan has to remember `%final:check` on every implementation launch, which
is the same class of failure as “remember to run `just check`.”

Implementation note: xprompt-injected `%final` must compose left-to-right with the
user’s selectors and still reject unknown instances at launch. A user
`%final:!check` should still win unless `check` is `required`.

## Idea 3 — Use the declaration channel as a work-product schema

Once `sase-rr` delivers provider-side `validate` against the accepted payload, the
declaration envelope becomes something SASE has never had: **a typed, coverage-checked
end-of-turn document that is not a commit message.**

`sase var` is the wrong store for this (the protocol research already rejected it).
The declaration is turn-bound, digest-bound, and must cover every selected instance
that asked for input. That makes it a good place to require *accountability claims*
the host then checks against facts.

High-value payloads, none of which grant the model executable authority:

### 3.1 Delivery / review packet

```json
{
  "change_kind": "user_reaching",
  "user_visible": true,
  "tests_run": ["just check"],
  "feature_flag": "none | key",
  "migration": false,
  "rollback": "revert the stitch",
  "docs": true,
  "known_limitations": [],
  "artifact_refs": ["file:explicit:..."]
}
```

The provider compares claims to the baseline delta, flag registry, test evidence, and
produced artifacts, then writes a durable review packet or fills an already-authorized
PR body. The companion report ranked this highly; it remains the best use of *custom
payloads*. It is ranked slightly lower here only because it is blocked on the payload
bridge, while Ideas 1–2 are not.

### 3.2 Research and plan quality

A research finalizer can require:

- a path under the research sidecar for the current month;
- frontmatter `status: research`;
- a ranked-recommendation section (heading match, or a declared `ranking:` list);
- at least one `derives-from` or `related` link to a bead, plan, or prior research
  artifact;
- no `sase_<N>` workspace path in *plan* files (research may cite SHAs).

A plan finalizer can require valid epic frontmatter, phase slugs, and the
no-workspace-path rule. These are SASE-native documents with existing schemas. They
are a better first custom payload than a generic “summary of what I did.”

### 3.3 Swarm and family handoff

Clans and `%wait` already compose agents. What they cannot do is fail the *producer*
for omitting the facts the consumer is about to read. A `handoff` instance can require
declared `sase var` keys (`report_path`, `status`, `bead_id`) and verify they exist,
are well-typed, and point at real artifacts. Combined with `%repeat` / `STOP`, a
producer can be forbidden from succeeding with an empty handoff map.

This is more useful than “notify the next agent.” Notification already happens.
Missing structured output is the actual failure mode.

### 3.4 Feature-flag and user-reaching checklist

AGENTS.md already says user-reaching behavior needs a flag. A provider that sees
TUI, CLI help, default config, or public schema in the diff can require a declaration
of `flag_key`, `kind`, and `why_unflagged` (for truly permanent config). Host facts:
the flag registry, the flag bead, and `tools/check_feature_flags`. This is exactly the
kind of “remember the process” rule that models skip under time pressure.

## Idea 4 — Reconcile SASE objects, not just git trees

Commit already reconciles *repositories*. The rest of SASE’s object model is still
reconciled by prompt.

### 4.1 Beads

After verification and commit proof:

- append a structured bead note with artifact refs, stitch IDs, and what was
  verified;
- refuse land-epic success while descendants are open (the CLI already refuses the
  close; the finalizer can make “I forgot to close” a failed run rather than a
  successful agent that left the epic in progress);
- confirm every `PROPOSED FOLLOW-UP:` was triaged.

Do not let a provider infer authority to close beads from plugin installation. Close
and note commands belong in trusted config, or the agent performs them during the
turn and the finalizer only *verifies*.

### 4.2 Artifacts and links

Automatic captures already snapshot some files at finalization. An explicit
`artifact-publish` instance can require that newly created deliverables are
`sase artifact create`d or VCS-backed locators, and that the run added the links it
declared. Research reports that cite `sase-rn` without a `related` or `derives-from`
edge are a concrete miss; this report’s own links are the intended shape.

### 4.3 Patches, stitches, and PR text

A post-commit instance can require the Patch `DESCRIPTION` / PR body to mention the
bead ID, the user-visible impact from the delivery payload, and the test lane that
ran. Idempotent; verify by reading the Patch record rather than trusting the API
response.

### 4.4 Procs and workspace leftovers

An agent that started a non-monitor proc and left it running has not completed. A
read-only instance can list procs attributed to this agent/family (excluding an
active monitor, which is a handoff) and fail if any remain. This is local, bounded,
and currently unenforced.

## Idea 5 — Human confirmation as a completion condition, narrowly

Gates already pause for a user decision. Most gates should fire *during* the turn
(dangerous command, production change). A few decisions are *definitions of done*:

- explicit user permission to edit `sase/memory/*.md` (instructions say this is
  required; a finalizer can fail if memory files changed and no authorizing gate
  result exists for this run);
- flag removal / `sase flag` closeout;
- publishing a research infographic or other generated media the user asked to
  approve;
- landing a change that disables a required finalizer instance.

Pattern: local checks → commit (or refuse) → gate whose command verifies the already
committed tree and records the decision. Do not block every implementation turn on a
human. Do not use a finalizer to *create* a gate that waits inside the 30-second
plugin cap; create the gate during the turn, or have the provider only *check that a
satisfying gate result already exists*.

## Idea 6 — Hardening and named heavy profiles

These overlap the companion catalog and are included here only with a SASE-specific
spin.

**Required security/policy instance.** Secret scan, forbidden binaries, protected
paths, dependency/license allowlists, “schema change requires a migration.” Make it
`required` in repositories where `%final:none` would be unsafe. Prefer local
deterministic tools; do not brick completion on a transient SaaS scanner.

**Deterministic normalization.** Formatters and generated-file refresh *before*
`check` and `commit`, exploiting the fixed-point controller. Idempotent only.
Projects that do not trust the generator should check cleanliness rather than
mutate.

**Cross-repo contracts.** SASE routinely spans primary, `sase-core`, plugins, and
sidecars. A provider should consume the host’s opaque repository inventory rather
than rediscovering paths. Check core binding floors, generated-skill source vs.
canonical branch, CLI completion snapshots, and protocol wire versions.

**Named `%final` profiles** for visual snapshots, TUI perf budgets, API
compatibility, and migration reversibility. Too expensive for every turn; perfect as
configured instances the land agent or a release launch selects.

**Release evidence.** SBOM, tool versions, plan/context digests, artifact hashes.
Workspace-local; do not overclaim SLSA. Keep cryptographic attestation in a trusted
build.

**Preview deploy and cleanup.** Useful later. Today: 30-second plugin cap, no
always/failure lifecycle, handoffs skip the seam. Prefer monitors, CI, and TTL
reapers.

## What to configure this week vs. after `sase-rr`

**This week, with `builtin@command` only:**

1. Add a `check` instance wrapping `just check` at a 15–20 minute timeout. Do not
   default it globally. Inject `%final:check` from `#commit`, `#pr`, `#coder`, and
   the bead work/land xprompts.
2. Add an `epic-symbols` instance for land launches: `sase bead epic-symbols` (or
   `just symvision` after close — order this carefully; close is still an agent
   action, the finalizer verifies).
3. Add a `research-doc` instance that is a small trusted script: the research
   sidecar has a new markdown file for the current month, it contains a ranked
   list heading, and it does not dirty the primary tree unexpectedly.
4. Leave `commit` as the bundled default. Set `required: [commit]` only in projects
   where `%final:none` would be a footgun.
5. Run `sase final doctor` after every config change. Keep plugin layers inert.

**After the payload bridge and unconditional protocol:**

6. A `delivery` provider with a real schema, host-side comparison to the diff, and
   a review packet artifact.
7. A `handoff` provider that validates `sase var` snapshots for named swarm roles.
8. A `hygiene` provider that checks repo-open and memory-read audits for the run.
9. Optional `required: [policy]` with a local scanner.
10. Consider xprompt-default `%final` as a small follow-up epic so profiles are not
    tribal knowledge.

**Do not schedule yet:** preview deploys, cryptographic provenance as a default,
cleanup-as-sole-mechanism, LLM-as-finalizer, Telegram/notification finalizers, or
anything that needs to run after a crash.

## Anti-catalog

These look like finalizers and should not be.

- **“Ask another model if the work looks done.”** Claude’s prompt-based Stop hooks
  do this. It is unbounded, gameable, and expensive. SASE already has mentor
  agents and recovery turns for missing declarations. Keep judgment in agents;
  keep completion in deterministic verifiers.
- **“Always format / always generate / always deploy.”** Silent mutation of
  semantics, network-dependent generation, and partial external effects. Format
  only where the tool is trusted; generate in a profile; deploy in CI or a
  monitor.
- **“Notify me when the agent finishes.”** Already the completion-notification
  path. A failing notifier should not fail the agent.
- **“Clean up the preview environment / kill the cloud lease.”** Wrong seam.
- **“Run `just check-full` before every success.”** The scoped-lane research
  exists specifically so this does not happen. Use `/sase_monitor`.
- **“The plugin will mark itself skipped.”** The host owns skip/success. A
  provider that wants to no-op should exit success with evidence that the trigger
  was false, or not be selected.

## Ranked recommended use cases

Ranked by **value × SASE-uniqueness × feasibility now**, with safety as a veto.
Items the companion catalog already ranked are kept only when this cut changes
their priority.

1. **Role-bound `just check` before commit.** Highest immediate value. Use
   `builtin@command` plus xprompt-injected `%final:check` on code-changing
   launches (or a dirt-triggered wrapper if you want it in `defaults`). Do not
   make it global. Keep `just check-full` on a monitor. This converts the most
   frequently skipped prompt-law into a host contract without waiting for
   `sase-rr`’s payload work.
2. **Xprompt / role completion profiles.** The multiplier on every other item.
   `#research` should not verify the primary Python tree; `#bd/land_epic` should
   verify symbols and checks; `#mentor` should not default-commit. Until xprompts
   can contribute selectors, document the `%final` recipes and put them in the
   relevant xprompt bodies as literal directives (those files are already trusted
   config).
3. **Land-epic and phase-worker mechanical closeout.** `epic-symbols` / symvision
   cleanliness, plan `status: done`, no illicit task-bead creation from phase
   workers, `PROPOSED FOLLOW-UP:` presence. Unique to SASE, already specified in
   prompt prose, checkable with existing CLIs.
4. **Run-scoped SASE hygiene audits.** Repo-open log vs. foreign paths read;
   memory-read audit vs. canonical memory files; plan files leaking `sase_<N>`
   paths; generated-skill dirt; feature-flag registry lint when those files
   change. This is the operating system of SASE, currently honor-system.
5. **Research and plan document contracts.** Ranked recommendations, required
   artifact links, month-path placement, plan frontmatter. Directly improves the
   quality of the durable corpus this sidecar exists to hold. Start as a trusted
   script; add a typed payload after the bridge.
6. **Structured delivery / review declaration.** Best use of the declaration
   channel: user-visible impact, tests, flags, migrations, rollback, docs,
   limitations, artifact refs — validated against the diff. Wait for the
   non-commit payload bridge. Do not fake it with `sase var`.
7. **Swarm/family handoff contract.** Require named `sase var` keys and artifact
   refs from producer agents. Fails the producer, not the waiting consumer, which
   is the correct locus.
8. **Required local security and repository-policy gate.** Secrets, protected
   paths, forbidden binaries, “this change class requires a migration.” Make it
   `required` where bypass is unsafe. Keep scanners local and deterministic.
9. **Deterministic format / generated-artifact reconciliation.** Exploits the
   fixed-point controller. Place before `check` and `commit`. Only for idempotent
   tools the project already trusts.
10. **Feature-flag and user-reaching checklist.** When the diff touches TUI, CLI,
    default config, or public schema, require a flag key or an explicit
    “permanent config” reason, checked against the registry. Process law that
    models drop.
11. **Cross-repository contract check.** Core floors, plugin schemas, generated
    clients, completion snapshots, sidecar pointers to committed source. Needs
    host-issued opaque repo inventory in the provider request (part of the same
    bridge/`sase-rr` work).
12. **Post-commit bead / Patch / PR reconciliation.** Structured notes, Patch
    description, PR body, bead close verification. After commit proof; idempotent;
    surface partial completion if the remote side fails.
13. **Named compatibility, visual, and perf profiles.** `%final:visual`,
    `%final:compat`, TUI latency budgets, API checkers. Opt-in for land and
    release launches; never a default.
14. **Human confirmation that a completion-critical permission existed.** Memory
    edits, flag removal, a few publish paths. Verify a gate *result*, do not wait
    inside the worker. Narrow on purpose.
15. **Release evidence bundle.** Useful for release-shaped runs; keep
    cryptographic claims in CI. Not a default.
16. **Preview deploy, crash-safe cleanup, notifier plugins.** Defer until an
    always/failure lifecycle, async job shape, and longer provider budgets exist.
    Use monitors, file hooks, TTLs, and the existing notification path instead.

## Recommendation

Configure three instances on the sase project as soon as `sase-rr` makes pluggable
finalizers the only path (and even now, while the beta is forced on): `check`,
`epic-symbols`, and `research-doc`, all `builtin@command`, with `commit` remaining
the default. Teach the code-changing and land xprompts to select `check`. Teach
research xprompts to select `research-doc` and not `check`. Treat everything that
needs a custom payload as a follow-up behind the protocol gap already owned by
`sase-rr`.

The mental shift that unlocks the rest: **stop asking “what else could run when the
agent stops?” and start asking “which of our prompt-only definitions of done can the
host now prove?”**
