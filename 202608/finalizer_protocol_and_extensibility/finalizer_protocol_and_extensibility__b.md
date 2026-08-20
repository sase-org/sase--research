---
create_time: 2026-08-20
updated_time: 2026-08-20
status: final
tags:
  - finalizers
  - commit-workflows
  - plugins
  - feature-flags
  - xprompts
  - skills
---

# Generalized SASE Finalizers: `/sase_final`, `%final`, and Host-Executed Stitches

**Research question.** SASE's commit finalizer is a hard-coded part of the system.
What is the right way to generalize it so users can define their own finalizers
through plugins and configuration, override the selection per agent with a `%final`
directive (defaulting to commit), and have agents declare per-repo stitch intent —
including an explicit refusal reason when they will not commit a dirty repo — through
a new `/sase_final` skill and `sase final` command, without breaking merge-conflict
handling?

**Scope.** Verified against SASE `b6864fdb6` (2026-08-20). Prior research at
[`research:202607/pluggable_finalizers_final_directive/pluggable_finalizers_final_directive.md`](../../202607/pluggable_finalizers_final_directive/pluggable_finalizers_final_directive.md)
was re-read in full and treated as a hypothesis, not as ground truth. No runtime
behavior was changed by this note.

---

## Bottom line

Build a **keyed `finalizers:` config registry** whose one core default is `commit`,
expose it to agents as **`/sase_final` + `sase final`**, and put the user-visible
contract behind a **beta feature flag that defaults off**.

The agent does not create commits at the end of a turn. It **declares intent**: for
every repo whose working tree this run actually dirtied, either a stitch spec
(message, excludes, method) or a non-empty refusal reason. The host **validates that
document, then executes** `sase stitch create` itself. Merge conflicts are not
resolved by the host. A `CONFLICT` (exit 2) leaves the existing
`commit_state.json` checkpoint and starts a follow-up turn whose only job is the
already-documented resolve-then-`--resume` flow.

`%final:commit` is the implicit default when the directive is omitted. Explicit
`%final` values are **ordered operations on that default selection**, not a
replacement list: `%final:lint` adds lint without dropping commit. `%final:!commit`
and `%final:none` are how you turn commit enforcement off for one launch.

A missing `/sase_final` on a **completing** turn whose trigger is unsatisfied forces
exactly one follow-up turn; a second miss fails the run. Intentional handoffs
(`/sase_plan`, `/sase_monitor`, `/sase_pipe`, `/sase_questions`) never reach the
finalizer because they `SIGTERM` the runner inside `provider.invoke()`, and that
exemption must stay mechanical — not a honor-system footnote in the skill.

The July 2026 design is still the right *shape* (config map, plugin opt-in, chop-like
script contract, `%final` as selection). Three of its premises are now false, and
the new agent-facing contract (`/sase_final`, per-repo JSON, refusals, feature flag)
is the part it never specified. Do not wait for the `sase-be` "vars-driven commit
finalizer" epic: that plan is gone from the tree and `commit --vars` never landed.
Do not store intent in `sase var`.

---

## 1. What the July 2026 research got right, and what is now wrong

The July report
([`pluggable_finalizers_final_directive.md`](../../202607/pluggable_finalizers_final_directive/pluggable_finalizers_final_directive.md),
verified then at `84d47aa78`) recommended:

> Make `finalizers:` a keyed config map whose entries are *host-evaluated trigger →
> bounded prompt passes that ask the agent to record sase variables → a script that
> performs the deterministic effect → re-evaluate*. Make `%final` a
> selection-and-bounded-override directive over that registry, never a definition
> site. Plugin-contributed finalizers are opt-in. Sequence after `sase-be`.

That contract — trigger, bounded re-prompt, deterministic script, re-evaluate —
is still the right engine. Several supporting claims are not.

| July claim | Status at `b6864fdb6` |
| --- | --- |
| `run_commit_finalizer` is one hard-coded function called from `_invoke.py` after a successful `provider.invoke()` | **Still true.** Call site is `_invoke.py` immediately after `provider.invoke(...)`. Config is still `commit.finalizer.{enabled,max_passes}` plus `SASE_DISABLE_COMMIT_STOP_HOOK`. `_KNOWN_DIRECTIVES` still has no `final`; `%f` is still free. |
| Finalization is a *turn* hook used as if it were an *agent* hook | **Still true**, and more so: mentors, CRS, fix hooks, workflow prompt steps, and ACE workflow handlers still share `invoke_agent`. |
| Config `finalizers:` must be a **map**, not a list, because the `user` layer replaces lists | **Still true.** `src/sase/config/layers.py` is unchanged in this respect. This single fact should still decide the config shape. |
| Reuse axe-chop script discovery, `--context`, result SDK, and the Rust `axe_chop` decision engine | **Still the right reuse.** `sase.chops.sdk` and `sase-core`'s `axe_chop::{decision,validation}` remain the template. |
| Plugin entries must be opt-in or `pip install` activates credentialed post-run code | **Still true**, and stronger: entry-point groups now also include `sase_artifact_refs`, `sase_file_hooks`, and `sase_task_types`. A new `sase_finalizers` group is still unnecessary for v1. |
| Sequence after `sase-be` ("Vars-driven commit finalization with exclusion-based staging") | **Stale.** There is no `plans:202607/commit_vars_finalizer.md`, no `sase commit --vars`, and no `commit_*` reserved output variables. The script stage was never extracted. Generalizing now *is* inventing that stage, not renaming it. |
| Agents record intent as `sase var` values; the script consumes them | **Superseded.** `sase var` is a cross-agent handoff channel: values appear in ACE and the Telegram completion message, each variable is capped at 65,536 encoded JSON bytes, and `_completion_output_variables` already special-cases `STOP`. Commit messages and refusal prose do not belong there. |
| Feature flags are not part of the design | **Stale.** SASE now has a typed flag registry (`src/sase/feature_flags/`). The commit finalizer already has one flag, `commit_finalizer_shared_clone_exempt` (sunset, default on). User-reaching dual paths now have a mandatory flag-bead lifecycle. |
| The agent still performs the side effect (`/sase_git_commit`) during a follow-up prompt | **Still the production path**, and it is the thing this feature has to replace carefully. Sixteen dedicated test modules under `tests/llm_provider/test_commit_finalizer_*.py` pin it. |

The July report also did not specify: an agent-facing skill, a `sase final` command that
persists JSON, per-repo stitch specs, required refusal reasons, the interaction with
`CommitWorkflow`'s exit-2 checkpoint, or a feature flag. Those are the load-bearing
new requirements.

---

## 2. Current commit finalizer, verified

### 2.1 Placement — keep this seam

`run_commit_finalizer` (`src/sase/llm_provider/commit_finalizer.py`) runs in the
process that owns the invocation, after a successful provider turn and before
success postprocessing, `done.json`, workspace-claim release, and the completion
notification. Provider-native stop hooks are not involved. That is why Claude,
Codex, Antigravity, Qwen, OpenCode, Muse, and Grok share one policy. Any
generalization must keep this call site as the driver; do not move enforcement into
a runtime hook.

Provider failure never reaches it: the `except` branches in `_invoke.py` re-raise
without finalization. `events: [success]` is still the only honest lifecycle event
at this seam.

### 2.2 What it actually does today

On a SASE agent session (`SASE_AGENT_TIMESTAMP` set, config enabled, env kill-switch
unset):

1. Auto-commit leftover bead-store state in a separate/sidecar SDD clone, then
   **verify that commit published**. An unpublished bead commit fails the run
   (`reason: bead_state_unpublished`) rather than reporting `finalized`.
2. Collect dirty state for the main workspace, opened linked repos, opened external
   repos, and SDD sidecars (`commit_finalizer_state.py`). Pre-existing dirt captured
   at runner start (`commit_finalizer_baseline.json`) is excluded so this agent is
   not blamed for another run's in-flight edit. Family-attach continuations
   **inherit** the parent's baseline, so leftover work stays this lane's job.
3. Best-effort auto-commit of two machine-managed diffs: SDD plan `status: wip` →
   `done`, and proven Q&A-only agents-sidecar prompt edits.
4. If anything enforced is still dirty, re-invoke the same provider up to
   `commit.finalizer.max_passes` (default 2) with a follow-up that lists dirty paths
   and tells the agent to use `/sase_git_commit` / `/sase_hg_commit`.
5. After each pass, the **discarded-work guard** fails the run if a repo went clean
   without an attributable `SASE_AGENT=` commit (or a run-owned ledger entry). Shared
   clones have a slightly looser classifier behind
   `commit_finalizer_shared_clone_exempt`.
6. Still dirty after max passes → `CommitFinalizerError`, run recorded failed.

The agent is the one that shells out to `sase stitch create`. The host only nags and
re-checks. That is why merge conflicts are currently "free": they happen *while the
model is still in a turn*, and the skill's "On Merge Conflict" section can run
`sase_git_commit --resume` against `SASE_ARTIFACTS_DIR/commit_state.json`.

### 2.3 Conflict handling that must not regress

This is no longer the 2026-04 gap documented in
[`research:202604/commit_conflict_resume.md`](../../202604/commit_conflict_resume.md).
`CommitWorkflow` now distinguishes `OK` / `FAILED` / `CONFLICT` (exit 0/1/2),
checkpoints before VCS dispatch, auto-resolves bead-store and benign upstream
movement, and leaves a paused rebase plus `commit_state.json` for real conflicts.
The `/sase_git_commit` skill documents the recovery:

1. `git diff --name-only --diff-filter=U`
2. resolve markers, `git add`, `git -c core.editor=true rebase --continue`
3. `sase_git_commit --resume` — **do not** re-run the original create

The 2026-07 tale `plans:202607/sase_commit_first_try_reliability.md` is **done**:
mechanical bead races are supposed to succeed on the first `sase stitch create`,
the `-M` message file is preserved on failure, and `--resume` is reachable. A
generalized finalizer that throws those invariants away — for example by running
`git commit` from a script, or by treating exit 2 as a hard fail with no follow-up
— reopens the most expensive agent failure mode SASE has.

The discarded-work guard is part of the same story. Manual conflict resolution can
rewrite the commit body and drop `SASE_AGENT=`. Resume restamps that footer before
`vcs_finalize_commit` so an unattributed `HEAD` is not classified as a discard.
Host-executed stitches must go through `sase stitch create` / `--resume`, not a
private git wrapper, or this guard starts failing clean work.

### 2.4 Early termination is already mechanical

`/sase_plan` (`sase plan propose`), `/sase_monitor` (`sase monitor start`),
`/sase_pipe`, and `/sase_questions` send `SIGTERM` to the runner process group.
`provider.invoke()` does not return, so `run_commit_finalizer` never starts. The
runner then rewrites the SIGTERM-induced failure as a completed handoff
(`normalize_handoff_interruption_state` in `run_agent_helpers_handoff.py`).

The follow-up member (monitor `--next`, pipe successor, plan coder) is a new
completing turn in the same workspace. Baseline inheritance makes leftover dirty
files *that* turn's job. The exemption the user asked for already exists if we
keep finalization after `invoke()` returns. Do not add an honor-system "you may
skip `/sase_final`" path that a completing agent can claim.

---

## 3. The new requirements, analyzed

### 3.1 `/sase_final` as the agent-facing contract

Asking the model to "use `/sase_git_commit`" from a *follow-up* prompt is how SASE
gets commits today, and
[`research:202607/scalable_skill_disclosure`](../../202607/scalable_skill_disclosure/scalable_skill_disclosure.md)
measured that skill at roughly **44% of skill traffic** — almost all of it
machinery-invoked by the finalizer, not by the original turn.

`/sase_final` inverts that. The original turn is told: before you stop talking,
declare what should happen to every dirty repo. The host then either:

- executes the declaration (happy path: **zero extra LLM turns**), or
- re-prompts once because the declaration is missing, incomplete, or a stitch hit
  `CONFLICT` / `FAILED`.

That is a latency and token win on the common path, and it is the only way a
*plugin* finalizer can require structured input without teaching every agent a new
ad-hoc skill.

**Do not put the commit-message taxonomy, per-repo `cd` recipe, or JSON schema in
the skill body.** Skill descriptions are Level-1 context for every runtime
([same disclosure research](../../202607/scalable_skill_disclosure/scalable_skill_disclosure.md)).
`/sase_final` should be short: run `sase final status`, do what it prints, treat
handoff skills as the only exemption. `sase final status` is the evolving contract
— it can list dirty repos, coverage holes, the selected finalizers, and a copy-paste
example for each missing repo.

Generate `/sase_final` for **every** runtime. `/sase_hg_commit` is the cautionary
counterexample: it is Gemini-only, and the uniform-runtimes rule exists so that
does not happen again. Keep `/sase_git_commit` for (a) the user explicitly asking
to commit mid-flight and (b) the `--resume` path, which the flag-off branch still
needs.

### 3.2 `sase final` persists JSON; it is not `sase var`

`sase var` is the wrong store:

- Completion notifications and ACE surface the snapshot. Commit messages and
  refusal reasons would leak into Telegram.
- Caps (256 keys, 8 KiB per string leaf, 64 KiB encoded per variable) are the
  wrong shape for a multi-repo stitch document.
- There is no schema, no coverage check against dirty state, and no per-finalizer
  namespacing beyond a naming convention.

Persist a **per-finalizer intent document** under the run's artifacts directory,
for example `$SASE_ARTIFACTS_DIR/finalizers/<name>.json`. `sase final` is the only
writer the commit finalizer trusts. A hand-authored file in the workspace is not
enough: the CLI can copy message bytes, stamp `written_at`, and record the dirty
fingerprint at put-time so a later host pass can detect "the agent kept editing
after declaring."

CLI shape, following `cli_rules.md` (bare group delegates to `list`; required
values are positionals; every public long option has a short alias). `final` does
not collide with any top-level subcommand in `src/sase/main/parser.py`.

```
sase final                         # notice + list (operator)
sase final list                    # registry: name, layer, enabled, default, trigger
sase final show <name>             # resolved spec
sase final doctor                  # cycles, unresolvable scripts, prefix collisions
sase final status                  # this run: dirty repos vs coverage (agent)
sase final commit <repo> -M <file> # merge a stitch spec into the commit document
sase final refuse <repo> -r <text> # merge a refusal
sase final put <name> <file>       # generic JSON for any finalizer (stdin as -)
sase final get <name>              # dump the document
sase final resume                  # thin wrapper over `sase stitch create --resume`
```

`commit` / `refuse` / `status` / `resume` are the agent-facing commit-finalizer
helpers. `put` is the plugin escape hatch. `list` / `show` / `doctor` are operator
tools and can land later than the agent-facing subset.

Repo identity in the document must use the same names `collect_dirty_state`
already emits (`main`, the linked-repo display name, the external open-ref, the
SDD sidecar role). Paths are recorded for the host but are not what the agent
types: agents already get those names in today's dirty-details block.

Illustrative commit-finalizer document:

```json
{
  "schema_version": 1,
  "finalizer": "commit",
  "written_at": "2026-08-20T18:01:00Z",
  "dirty_fingerprint": "<host-computed>",
  "repos": {
    "main": {
      "action": "stitch",
      "kind": "main",
      "message": "feat(finalizers): persist per-repo stitch intent\n\n...",
      "exclude": ["scratch/notes.md"],
      "method": null,
      "do_not_close_bead": false
    },
    "sase-core": {
      "action": "refuse",
      "kind": "sibling",
      "reason": "Opened to read the axe_chop decision engine; no intentional edits."
    }
  }
}
```

`sase final commit` copies the `-M` file into `message` at put time so execution
does not depend on a working-tree file that `.sase/` might recycle. It also runs
the existing conventional-commit subject gate (`commit.message`) immediately, so
the agent can rewrite the message *in the original turn* instead of discovering
the rejection after the host tries to commit.

### 3.3 Refusal is diagnostic, not permission

The user asked for a refusal reason so the finalizer failure is *informative*.
That is the right v1 policy:

- Every currently-enforced dirty repo must appear in the document with either
  `action: stitch` or `action: refuse`.
- Missing repo → incomplete document → one follow-up turn, then fail
  (`reason: intent_incomplete`, listing the holes).
- `refuse` with a non-empty reason → the commit finalizer **still fails**, but
  `commit_finalizer_result.json` (and the user-visible error) carry
  `reason: refused` plus the agent's prose. That is the insight that is missing
  today, when a dirty tree after two passes is just `dirty_after_max_passes`.
- Empty reason → invalid document, same as missing.
- Pre-existing baseline dirt is already excluded; agents must not be asked to
  refuse it.

Do not accept leftover dirty work in v1 just because a reason string exists.
Agents would learn to refuse the primary repo. If a later policy wants allowed
codes (`user_instruction`, `secrets`, `unrelated_generated`), that is a config
field on `finalizers.commit`, not a silent default.

### 3.4 `%final`, and what "default `%final:commit`" should mean

Two interpretations:

| Model | `%final:lint` means | Accidental commit disable? |
| --- | --- | --- |
| **Replacement** (literal reading of "if not used, default to `%final:commit`") | run only lint | **Yes** — the most expensive footgun in the system |
| **Additive over defaults** (July, and this report) | run commit *and* lint | No; drop commit with `%final:!commit` or `%final:none` |

Recommend **additive**. The implicit default *is* `%final:commit` in the only
sense that matters: when the directive is absent, the enabled core defaults
run, and `commit` is the only core default. An explicit `%final:commit` is a
no-op on a stock config. `%final:none` suppresses current *and future* core
defaults for that launch, which is the per-launch analogue of
`finalizers.enable_defaults: false`.

Directive mechanics, still valid from July and re-verified:

- Add `"final"` to `_KNOWN_DIRECTIVES` and `_MULTI_VALUE_DIRECTIVES`.
- Alias `"f": "final"` (`_DIRECTIVE_ALIASES`; `%n`/`%t` remain deprecated).
- Colon grammar already accepts `!`, `-`, `/`, `,`. Use `!name` for removal;
  hyphenated finalizer names would make `%final:-license-audit` ambiguous.
- Closed kwarg allowlist: `enabled`, `max_passes`, `on_failure`, `timeout`.
  Never `script`, `command`, `env`, `prompt`. `%clan(..., summary_script=...)`
  already accepts an executable from prompt text, but that script is decorative
  and fail-soft; a finalizer script is credentialed and completion-blocking.
- Persist the resolved selection in `agent_meta.json` via `build_agent_meta`,
  not the environment (nested launches, `scrub_agent_identity_env`).
- Unknown names, unknown removals, cycles, and a `depends_on` that was
  explicitly removed fail at **launch**, before any provider call.
- Mentors, CRS, fix hooks, and workflow steps carry no prompt directives, so
  they get config defaults only. That is probably correct; an
  `on_failure: fail` plugin finalizer enabled globally would start failing
  mentor turns, which is why plugin entries are opt-in.

`%final` vs workflow `finally: true` steps (`docs/workflow_spec.md`) is a naming
collision in prose only. Keep `%final`. Call the workflow feature "`finally`
steps" in docs. Decide before the directive ships; renaming later needs a
`_DEPRECATED_DIRECTIVE_MESSAGES` entry.

### 3.5 Plugins and configuration

Keep July's dual-seam, zero-new-entry-point design:

1. **Declare** in a `sase_config` `default_config.yml` `finalizers:` map (the
   same layer `sase-github` / `sase-telegram` / `sase-nvim` already use).
2. **Implement** as a console script, resolved like a chop
   (`discover_chop_script`).

The registry loader forces `enabled: false` for any finalizer whose originating
`ConfigLayer.name` is `plugin:*`, regardless of the plugin's YAML, until the
`user` / `overlay:*` / `local` layer re-enables it or `%final:<name>` selects it.
Installing a plugin must not activate post-completion code with the agent's
credentials. That is the `notification_gates` `neutral_only` precedent, and it is
the one genuinely new safety rule this feature needs.

A `sase_finalizers` resource group remains a documented v2 hatch if plugin
authors need to ship definition *bundles* with relative prompt assets. The config
map stays the selection surface either way. Relative `prompt:` paths inside a
plugin layer have no filesystem anchor after merge (`layers.py` stores plugin
layers with `path=None`); prefer `prompt_xprompt:` and keep prose in the existing
xprompt system.

`finalizers:` is a **map**. A YAML list would let one user `sase.yml` entry
silently delete the builtin commit finalizer and every plugin contribution,
because the `user` layer's `list_strategy` is `replace`.

### 3.6 Feature flag

This is user-reaching behavior that is not ready to be unconditional, and it
duplicates the current finalizer until it soaks. That is exactly what
[`research:202608/feature_flag_field_guide`](../feature_flag_field_guide/feature_flag_field_guide.md)
says a flag is for: a scheduled deletion with a switch attached. It is **not** a
permanent "which finalizer runs" setting — that is `finalizers.commit.enabled`
and `%final`.

Create with `sase flag new`, not by hand:

- **Key:** `pluggable_finalizers`
- **Kind:** `beta` (default **off**)
- **When enabled:** the invoke-layer driver runs the registry; completing turns
  with an unsatisfied trigger require a `/sase_final` document; the commit
  entry host-executes stitches from that document; `%final` is honored.
- **When disabled:** today's `run_commit_finalizer` + follow-up
  `/sase_git_commit` path is unchanged. `/sase_final` may exist as a generated
  skill (chezmoi is global) but launch prompts must not mention it, and
  `sase final commit` must error with "flag off".
- **Remove when:** the enabled path has both-states tests, the commit finalizer
  is an ordinary registry entry with no special-case driver, conflict-resume
  e2e is green, and a soak period has produced no production incidents that
  the disabled path would have avoided.

Do not reuse `commit.finalizer.enabled` as the flag. That key is a permanent
kill switch for commit enforcement and must survive flag removal. Do not reuse
`commit_finalizer_shared_clone_exempt`; that is a sunset classifier inside the
discarded-work guard.

The Off branch has to stay explicit enough that a later worker can delete it in
the same change that closes the flag bead. Route on `current_flags().enabled(
FeatureFlag.pluggable_finalizers)` at the `_invoke.py` seam, not at every helper.

Internal registry extraction that is *not* user-visible can land without the
flag. The flag covers the agent-visible contract (skill, host execute, `%final`,
plugin opt-in).

---

## 4. Merge conflicts: the part to get right

Host-executed stitches are the design's load-bearing change. They are also the
way to break the current conflict workflow.

### 4.1 What must stay true

- Mechanical bead-store conflicts and benign upstream movement are handled
  **inside** `sase stitch create` with no agent. The host script must call that
  command, not `git commit`.
- A real semantic conflict is `RunResult.CONFLICT` / exit 2, a paused rebase,
  and `commit_state.json`. The agent, not the host, resolves markers.
- After resolution, **`--resume`** replays push, Patch, STITCHES, provenance
  restamp, and after-hooks. Re-running create is how you get a second commit on
  top of a paused rebase.
- The discarded-work guard must still see an attributable `SASE_AGENT=` commit
  (resume restamps the footer for this reason).
- Multi-repo intent is sequential. If repo A conflicts, do not start repo B's
  stitch until A is resumed. One checkpoint file exists today; do not invent a
  second until a test proves you need it.

### 4.2 Recommended conflict state machine

```
original turn
    agent: /sase_final → sase final commit|refuse …   (declaration only)
    invoke() returns
host
    auto-commits (beads, SDD closeout, prompt Q&A)     (unchanged safety nets)
    collect_dirty_state
    if clean and no unpublished bead commit: done
    if dirty and no/incomplete document:
        follow-up pass 1 ("run /sase_final; status printed below")
        if still missing: fail
    for each stitch spec, in document order:
        sase stitch create -M <copied message> -x …   (cwd = repo.path)
        OK      → next repo
        FAILED  → follow-up with the command's stderr; agent may rewrite
                  the spec via sase final commit and the host retries
        CONFLICT → stop the repo loop
                   follow-up with the existing On Merge Conflict recipe
                   plus "then: sase final resume"
                   on resume OK, continue the remaining specs
    re-collect dirty state
    refusals still dirty → fail with reason: refused
    leftover dirty with no refusal → fail with reason: intent_incomplete
    discarded-work guard runs around every host stitch and every follow-up
```

`sase final resume` is a one-line wrapper around `sase stitch create --resume`
so the completing agent has one skill (`/sase_final`) for declaration *and*
conflict finish. `/sase_git_commit --resume` can stay as a synonym while the
flag is on; the flag-off branch still needs it.

### 4.3 Follow-up budget

Today `max_passes: 2` is "two LLM follow-ups after the original turn." Keep that
as a **single shared budget** covering missing intent, rejected messages, hook
failures, *and* conflict resolution. The user's "force one turn, then fail" is
the missing-skill case; a conflict on pass 1 still deserves pass 2 for
`--resume`. Do not give skill-enforcement and conflict-recovery separate
counters in v1 — two knobs will drift. If soak shows conflicts starving the
skill-enforcement budget, add `conflict_passes` later.

Handoff SIGTERM never consumes this budget because the finalizer never starts.

### 4.4 Stale intent

If the agent calls `/sase_final` and then keeps editing, the put-time dirty
fingerprint will not match the post-`invoke` fingerprint. Treat that as
incomplete, not as "close enough," and follow up. The skill must say: **last
action of a completing turn**, after every file write.

If the agent committed mid-flight with `/sase_git_commit` (user-requested or
`-B`), those repos are clean before the finalizer and do not need a spec.
Coverage is against *remaining* enforced dirt, not against the whole run.

### 4.5 What not to do

- Do not have the host `git add` / `git rebase --continue`. Agents already do
  that well; the host's job after a conflict is to refuse `--resume` while
  markers remain (today's `CommitWorkflow.resume` already does).
- Do not auto-resolve non-bead conflicts. Preferring "ours" or "theirs" from a
  script is how you ship conflict markers.
- Do not skip the discarded-work guard on the host-execute path. A script that
  `git reset --hard` to look clean is exactly the failure that guard exists for.
- Do not run remaining stitches while a rebase is paused.

---

## 5. Alternatives considered

### A. Host-execute after the turn (recommended)

Agent declares; host runs `sase stitch create`; conflicts bounce into a
follow-up.

- **Pros:** Happy path costs zero extra LLM turns. Plugin finalizers get the
  same "declare, then the host acts" shape (create beads, publish artifacts,
  etc.). Intent is schema-checked. Coverage and refusals are enforceable.
  Conflicts reuse the checkpoint that already exists.
- **Cons:** Dual path until the flag comes off. Conventional-commit and hook
  failures are discovered after `invoke()` unless put-time validation catches
  them (subject gate can; `just fix` cannot). One new CLI group and one new
  skill.

### B. Agent still executes `/sase_git_commit`; `/sase_final` is only a coverage affidavit

Closest to today. The finalizer nags until dirty is gone *and* a document
accounts for every repo.

- **Pros:** Conflict handling does not move. Smaller change.
- **Cons:** Still burns a follow-up turn on every dirty run. The "finalizer
  acts" requirement is not met. Plugin finalizers have no execution engine —
  they would each invent their own. Refusals are just comments on a path that
  still fails after `/sase_git_commit` was not run.

### C. `sase final commit` both records *and* runs `sase stitch create` immediately

Declaration and effect happen while the model is still in the original turn.

- **Pros:** Conflicts and hook failures are live. Put-time and execute-time are
  the same moment, so stale-intent vanishes.
- **Cons:** Agents can (and will) call it mid-turn, then keep editing. The
  host still needs a post-`invoke` coverage check, so you pay for both models.
  Plugin authors copy the "do the effect inside the CLI" pattern, which is
  harder to sandbox than a chop-style script. The July "script performs the
  effect" isolation is lost.

### D. July's `sase var` intent + wait for `sase-be`

- **Reject.** The epic is gone. Vars leak. The user asked for a `sase final`
  JSON document.

### E. Replacement `%final` (explicit list, implicit `%final:commit`)

- **Reject as the default semantics.** `%final:lint` would disable commit
  enforcement. Offer exact selection as `%final:none %final:lint`.

### F. New `sase_finalizers` plugin resource group as the definition site

- **Defer.** Config-only is one surface, already merged, already diagnosed.
  Revisit if plugin authors need bundled prompt assets that cannot be
  xprompts.

---

## 6. Recommended solution

**A keyed `finalizers:` registry, an agent-facing `/sase_final` + `sase final`
intent document, host-executed `sase stitch create` for the builtin `commit`
entry, additive `%final` over an implicit commit default, plugin opt-in, and a
beta flag that keeps today's path until the new one has soaked.**

### 6.1 Engine

The July three-part contract, with the middle step renamed:

```
trigger (host, cheap) → intent pass (LLM, /sase_final) → script (host) → re-evaluate
```

Either half of prompt/script may be omitted. `commit` uses both. A pure script
finalizer (no prompt) is a post-run chop. A pure prompt finalizer is today's nag
loop.

`scope: turn` (default, today's timing) vs `scope: agent` (once in
`finalize_loop`, later). v1 only ships `turn`. Name the field anyway so the
ambiguity in §2.1 does not leak into plugin authors' configs.

Trigger providers, closed set, chop-style extension later:

| Provider | Fires when |
| --- | --- |
| `repo_dirty` | Enforced dirty state remains (commit's trigger; reuse `collect_dirty_state`) |
| `intent_missing` | Selected finalizer has no valid document for this turn |
| `intent_stale` | Document fingerprint ≠ current dirty fingerprint |
| `vars_absent` | Reserved keys missing (plugin "you must set a summary" case) |
| `always` | Every completing turn |
| `checkpoint_pending` | `commit_state.json` exists (conflict follow-up) |

`intent_missing` / `intent_stale` / `checkpoint_pending` are how the user's
"force a new turn if they skip `/sase_final`" rule is implemented without
forcing a turn on a *clean* research agent that forgot the skill. Tell agents
to always call it; only *force* a follow-up when a trigger is unsatisfied.
Clean + missing document is a recorded skip, not a failure.

### 6.2 Builtin `commit` entry

```yaml
finalizers:
  enable_defaults: true
  commit:
    description: |-
      Require every agent change to be committed before completion

      Detects uncommitted work in the primary workspace and every opened
      linked, external, and SDD sidecar repository. Asks the agent to
      declare a stitch or a refusal per repo via /sase_final, then
      executes those stitches with sase stitch create.
    enabled: true
    default: true          # only the bundled core layer may set this
    scope: turn
    trigger: {provider: repo_dirty}
    prompt_xprompt: _finalizer_commit
    script: sase_final_commit
    max_passes: 2
    on_failure: fail
    vars_prefix: commit    # unused by the JSON document; reserved so plugins
                           # cannot squat the name
```

Deprecate `commit.finalizer.{enabled,max_passes}` onto these fields with the
existing `_collect_deprecated_keys` machinery. Keep
`SASE_DISABLE_COMMIT_STOP_HOOK` disabling **only** `commit`; add
`SASE_DISABLE_FINALIZERS` as the master kill.

Safety nets that are not the agent's job stay in the host script, *before*
coverage is checked: bead-store auto-commit + publication verification, SDD
`status: done` closeout, agents-sidecar Q&A auto-commit, discarded-work guard,
pre-existing baseline exclusion. Expressing `commit` as an ordinary registry
entry does **not** mean those special cases move into the LLM prompt. They are
script behavior. The July "zero special cases in the *driver*" test is the
right test; zero special cases in the *commit script* would throw away a year
of incident response.

### 6.3 Agent contract (flag on)

Launch prompt injection, not AGENTS.md (AGENTS.md cannot branch on a beta
flag, and chezmoi skills are global):

> Before ending a completing turn, invoke `/sase_final`. Exempt: this turn
> is handing off through `/sase_plan`, `/sase_monitor`, `/sase_pipe`, or
> `/sase_questions` (those commands kill the process; do not also declare).

The skill:

1. `sase skill use sase_final`
2. `sase final status`
3. For each hole: `sase final commit <repo> -M .sase/commit_message.md`
   and/or `sase final refuse <repo> -r "..."` 
4. If status reports a paused conflict: resolve, then `sase final resume`
5. Do this last, after every file write

Coverage is computed from `collect_dirty_state` after auto-commits. Linked and
external repos the agent never dirtied (or only opened) do not appear. A repo
it dirtied and will not stitch **must** carry a refusal reason.

### 6.4 `%final`

| Form | Meaning |
| --- | --- |
| *(omitted)* | enabled core defaults (`commit`) |
| `%final:commit` | explicit same-as-default |
| `%final:lint` | add `lint` |
| `%final:!commit` | remove commit for this launch |
| `%final:none` | clear defaults, including future ones |
| `%final:none %final:lint` | exact selection |
| `%final(commit, max_passes=3)` | bounded override |
| `%f` | alias |

Selectors are left-to-right operations on the config-derived selection.

### 6.5 Plugin opt-in and CLI

As §3.5. Wire `sase final doctor` into `sase doctor`. Agent-facing subcommands
must refuse to write intent when `pluggable_finalizers` is off, with a message
that names the flag.

### 6.6 Artifacts

- `$SASE_ARTIFACTS_DIR/finalizers/<name>.json` — intent
- `$SASE_ARTIFACTS_DIR/finalizer_result.json` — aggregate
- Keep writing `commit_finalizer_result.json` as a compatibility alias
  (`axe/runner_reporting.py` reads the literal name)
- `finalizer_<name>_pass_<N>_{prompt,response}.md` generalizing
  `commit_finalizer_prompt_artifacts.py`
- Record variable *names* and refusal *reasons* in the result; do not copy
  full commit-message bodies into user-visible notifications

---

## 7. Phasing

| Phase | What | User-visible? | Flag |
| --- | --- | --- | --- |
| 0 | `sase flag new pluggable_finalizers` (beta, off) plus both-states test skeleton | no | created |
| 1 | Intent document + agent-facing `sase final {status,commit,refuse,put,get,resume}` + schema + put-time subject gate. Commands error when the flag is off. | only if flag on | on |
| 2 | Host script `sase_final_commit` executes the document through `sase stitch create`; conflict → follow-up + `sase final resume`; discarded-work guard and publication checks preserved. `_invoke.py` routes on the flag: off = today's function, on = new driver with one `commit` entry. `/sase_final` skill + launch-prompt injection when on. | yes, gated | on |
| 3 | `finalizers:` keyed config, schema, `FinalizerSpec`, deprecate `commit.finalizer.*`. Prove `commit` is an ordinary registry entry from the *driver's* point of view. | no additional | on |
| 4 | `%final` parsing, `agent_meta.json`, TUI completion, launch-time validation | yes, gated | on |
| 5 | Plugin opt-in enforcement, `sase final {list,show,doctor}`, chop-like script SDK, `inhibit_if`. Rust decision engine when a second frontend needs "would this fire?" | yes, gated | on |
| 6 | Soak, then FlagTriage **Remove**: delete the Off branch, make the On branch unconditional, close the flag bead. Permanent knobs remain `finalizers.commit.enabled` and `%final`. | commit path changes for everyone | removed |

Phase 2 is the whole product bet. If host-executed stitches plus `--resume`
cannot preserve the discarded-work guard, bead publication check, and conflict
recipe, stop and keep alternative B rather than generalizing a broken commit
entry.

Tests to pin beyond the happy path: flag off ≡ current 16-module suite; flag
on + clean tree + skipped skill does not follow up; flag on + dirty + skipped
skill follows up once then fails; incomplete coverage vs refusal-fail;
put-time subject rejection; stale fingerprint after extra edits; sequential
multi-repo with a conflict in the first repo not dispatching the second;
`--resume` restamp vs discarded-work guard; SIGTERM handoff does not fail the
run for missing intent; family-attach baseline inheritance; plugin layer
`enabled: true` stays off; `%final:lint` does not drop commit; `%final:none`
does; `script`/`env`/`prompt` kwargs rejected; `user` list-shaped `finalizers`
is a schema error, not a silent wipe.

---

## 8. Risks

- **Dual-path cost.** The Off branch is the entire current finalizer. That is
  acceptable only because the flag bead *forces a deletion date*. Do not let
  this become a permanent config.
- **Skill compliance.** Agents skip "do this at the end" instructions; that is
  why the follow-up exists. If soak shows even the follow-up being ignored,
  lower `max_passes` messaging, not the coverage rule.
- **`just fix` / after-hook failures** cannot be validated at put time. They
  remain a follow-up. That is already today's world.
- **Non-agent `invoke_agent` callers** inherit config-default finalizers.
  Plugin `on_failure: fail` entries that a user enabled globally will fail
  mentor turns. Opt-in plus docs.
- **In-repo `sase/sase.yml`** can define a finalizer in a malicious PR — the
  same exposure `file_hooks` and chops already have. Document it.
- **Latency.** N finalizers × `max_passes` on *every* turn is the failure
  mode of `scope: turn`. Triggers stay host-evaluated and cheap; share one
  `collect_dirty_state` per turn; consider a global cap in phase 5.
- **Rust boundary.** Trigger evaluation and the decision record belong in
  `sase-core` once ACE or `sase final list` must agree with the runner on
  "would this fire?" Phase 5, not phase 1. Follow how `axe_chop` actually
  evolved.
- **`/sase_git_commit` remaining in the catalog.** Mid-flight commits and the
  flag-off branch need it. After flag removal it can shrink to "user asked"
  plus `--resume` synonym; do not delete it in the same change as the flag.

---

## 9. Sources

**Prior SASE research (read, not trusted as current truth)**

- [`research:202607/pluggable_finalizers_final_directive`](../../202607/pluggable_finalizers_final_directive/pluggable_finalizers_final_directive.md)
  — registry, `%final`, plugin opt-in, chop reuse. Premises about `sase-be`
  and `sase var` are stale.
- [`research:202604/commit_conflict_resume`](../../202604/commit_conflict_resume.md)
  — the gap that `CommitWorkflow` checkpoint/`--resume` closed.
- [`research:202607/scalable_skill_disclosure`](../../202607/scalable_skill_disclosure/scalable_skill_disclosure.md)
  — `/sase_git_commit` as machinery-invoked, 44% of skill traffic; keep
  `/sase_final` Level-1-small.
- [`research:202608/feature_flag_field_guide`](../feature_flag_field_guide/feature_flag_field_guide.md)
  and [`feature_flag_architecture`](../feature_flag_architecture.md) — beta
  flag, not a permanent setting.
- [`research:202608/xprompt_role_binding`](../xprompt_role_binding/xprompt_role_binding.md)
  — `%final` is a directive, not a tag; do not wait on tag-resolution work.
- [`research:202606/sibling_repos_open_tracking_feasibility_consolidated`](../../202606/sibling_repos_open_tracking_feasibility_consolidated.md)
  — finalizer target discovery from opened workspaces; already largely landed
  in `commit_finalizer_state.py`.

**Current code (anchors at `b6864fdb6`)**

- `src/sase/llm_provider/_invoke.py` — sole `run_commit_finalizer` call
- `src/sase/llm_provider/commit_finalizer.py` and `commit_finalizer_{config,state,prompting,baseline,git_progress,types}.py`
- `src/sase/xprompts/skills/sase_git_commit.md` — create + `--resume` contract
- `src/sase/xprompt/_directive_types.py` — `_KNOWN_DIRECTIVES`, aliases
- `src/sase/feature_flags/registry.py` — existing flags, including
  `commit_finalizer_shared_clone_exempt`
- `src/sase/plugins/inventory.py` — entry-point groups
- `src/sase/chops/sdk.py` — script `--context` / result template
- `src/sase/axe/run_agent_helpers_handoff.py` — SIGTERM handoff rewrite
- `docs/commit_workflows.md` — workflow stages, exit codes, discarded-work guard
- `src/sase/default_config.yml` — `commit.finalizer.{enabled,max_passes}`
- `plans:202607/sase_commit_first_try_reliability.md` — done; first-try stitch
  create is the host script's prerequisite

**Deliberately not used as a dependency**

- `sase-be` / `plans:202607/commit_vars_finalizer.md` — not in the tree
- `sase var` as the intent store — wrong channel
