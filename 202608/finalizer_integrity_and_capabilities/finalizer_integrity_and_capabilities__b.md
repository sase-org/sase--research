---
create_time: 2026-08-21
updated_time: 2026-08-21
status: research
---

# Finalizer Bugs and Capability Upgrades

**Research question:** After the pluggable-finalizer protocol landed (`sase-rn`) and
the beta/legacy path was retired (`sase-rr`), what remaining bugs still exist in the
shipped implementation, and which upgrades would make host-owned finalizers actually
powerful rather than merely pluggable?

**Snapshot:** 2026-08-21. Primary HEAD `28009002d` (*fix(finalizers): prove live e2e
acceptance and validate external payloads*). Closed epic `bead:sase-rn`. In-progress
epic `bead:sase-rr` with all four phases closed and the land agent still assigned.
Flag bead `bead:sase-ro` is still open. This report audits the current Python
controller, declaration channel, executor, CLI, generated skill, docs, tests, and the
shared Rust wire in `sase-core`, then re-checks the earlier
`research:202608/finalizer_protocol_and_extensibility/finalizer_protocol_and_extensibility.md`
and `research:202608/finalizer_completion_contracts/finalizer_completion_contracts.md`
against that tree.

**Method:** source audit of `src/sase/finalizers/`, invocation seam, skill template,
config/schema, `docs/`, and the dedicated test corpus; live `sase final list` /
`doctor` / `context -f json` in this turn; bead and plan reads. No production config
was changed.

## Executive conclusion

The protocol is real and the beta split is gone. A normally completing SASE turn now
always resolves a sealed plan, injects `/sase_final`, and runs a bounded host
controller. Built-in `commit` is the only bundled instance, and that path is the
mature one: dirty-repo obligations, Conventional Commit / refuse coverage, sequential
`sase stitch create`, protected baselines, conflict repair, later-dirt reactivation,
and durable artifacts.

What is **not** yet powerful is everything around `commit`. External providers and
`builtin@command` exist, but several host contracts that the protocol and Rust wire
already named are still hardcoded or ignored in Python. The result is a completion
system that can run a trusted argv and can call a plugin subprocess, yet cannot
honestly express “this plugin needs no model input,” “this check should re-run after a
mutator,” “this request is for the sealed plan of *this* run,” or “here is the JSON
schema the agent must fill.”

The highest-leverage work is therefore not a new hook system. It is:

1. **close the remaining host/plugin contract bugs** so a third-party provider can
   actually consume a declaration; then
2. **ship a small portfolio of trusted instances** bound to roles/xprompts, starting
   with `builtin@command` checks, rather than leaving the registry at `commit` alone.

Until (1) lands, installing a plugin and selecting it is a foot-gun: every external
instance currently forces a required empty declaration, plugin workers are told the
config *defaults* rather than the sealed selection, and `max_attempts` is ignored.

## What landed, and what earlier research got wrong

`sase-rn` delivered the four-part protocol (plan, declaration, isolated execute,
independent verify). `sase-rr` made that path unconditional: `FeatureFlag.pluggable_finalizers`
is gone, `run_commit_finalizer()` is gone, and new runs write generic artifacts
(`finalizer_plan.json`, `final_context.json`, `final_submission.json`,
`finalizer_result.json`). Live e2e in `tests/test_finalizers_live_e2e.py` covers clean
completion, dirty commit, `%final:none`, command + fixture plugin, refusal, stale
recovery, later-dirt commit reactivation, first-repo conflict resume, and handoff skip.

Two findings from this morning’s companion research are **already fixed** at this
revision and should not be re-filed:

| Earlier finding | Current status |
| --- | --- |
| Non-commit payloads accepted without provider `validate` | Fixed. `validate_provider_payloads()` now calls `validate_external_declaration_payload()` for every non-command, non-commit instance (`src/sase/finalizers/declaration.py`). |
| `_provider_request()` omitted payload and host obligations | Fixed. The request now loads accepted payloads from `final_submission.json` and obligations from `final_context.json` (`src/sase/finalizers/executor.py`). Covered by `test_external_provider_request_includes_accepted_payload_and_obligations`. |
| Fakey retry e2e missing `SASE_AGENT_NAME` | Fixed in `sase-rr.4`. `tests/fakey/test_retry_pipeline_e2e.py` now pops and asserts the `finalizers` agent-meta block rather than failing context. |

The payload bridge is therefore present. It is not yet *used* as a product: the
generated skill still only documents commit/refuse, and context still emits `{}` for
every external payload.

## How the current seam actually behaves

Before the model turn, `invoke_agent()` always calls
`resolve_and_persist_finalizer_plan()`. If a plan object and artifacts directory exist,
it writes `agent_meta.finalizers` and appends the `/sase_final` instruction. That
happens even for `%final:none` (empty selection) and even for clean commit-only turns.

After a successful provider return, `run_finalizers()`:

- no-ops when there is no artifacts dir, no `SASE_AGENT_TIMESTAMP`, or a pending
  plan/monitor/pipe/question handoff;
- publishes context, recovers a missing/stale declaration at most once, then executes
  selected instances in sealed order;
- reactivates `builtin@commit` when later dirt appears;
- records every other instance in `ran_non_commit` and never re-runs it;
- fails the whole run on the first non-success instance status, including `skipped`.

`sase final list` / `show` / `doctor` inspect **merged configuration defaults**, not
the current turn’s sealed plan. `sase final context` / `submit` are the turn-bound
channel. Live context for this research turn, before any research-sidecar write, was
commit-only with `submission_required: false` and an empty `manifest_template.payloads`
list.

Bundled config is still only:

```yaml
finalizers:
  defaults: [commit]
  required: []
  instances:
    commit:
      use: builtin@commit
      after: []
      max_attempts: 2
      refusal: fail
```

No shipped xprompt currently injects `%final`. Role-bound selection is possible today
as a configuration-plus-xprompt change, but nothing in the tree does it.

## Confirmed bugs

Each item below was verified in the current tree. Severity is about user-visible
correctness or a protocol lie, not about missing features.

### 1. Plugin requests lie about selection and run identity

`run_finalizers()` constructs `FinalizerExecutionContext` with only `artifacts_dir`
and `plan_digest`. `run_id` and `agent_id` stay `None`. `_provider_request()` then
sends:

```python
"run_id": context.run_id,      # always None from the controller
"agent_id": context.agent_id,  # always None from the controller
"selected": [
    item.instance_id
    for item in config.instances.values()
    if item.instance_id in config.defaults
],
```

`selected` is the configured **defaults**, not the sealed plan. A launch of
`%final:none %final:audit` still tells the plugin that `commit` is selected.
`%final:lint` does not list `lint` unless `lint` is also a default. Plugins that key
idempotency on run/agent identity, or that condition work on the real selection, get
the wrong document.

The turn-bound context JSON *does* have the real `run_id` / `agent_id` /
`plan_digest`. The worker request does not. That is a host bug, not a plugin-author
mistake.

### 2. `describe` cannot influence context, and every plugin forces a declaration

The shared Rust wire already has `FinalizerProviderCapabilityWire::{Validate, Execute,
Verify, RequiresSubmission, MutatesRepository}` plus `submission_schema_digest`.
Python never uses those types. `collect_finalizer_providers()` hardcodes string
capabilities (`describe/validate/execute/verify` for plugins) that are not the Rust
enum.

Context construction then ignores describe entirely:

```python
# every non-commit, non-command entry
requirements.append(
    FinalizerPayloadRequirementWire(
        instance_id=entry.instance_id,
        trigger="provider_requested",
        submission_required=True,
        ...
    )
)
```

`execute_plugin_finalizer()` calls `describe` only later, as the first of four
execute-time operations. By then the agent has already been told to submit. The
manifest template for those instances is `{}`. There is no payload schema, no way for
a plugin to opt out of submission, and no way for a check-only plugin to avoid a
recovery turn if the agent omits `/sase_final`.

This is the single largest blocker to “powerful” external finalizers. It is also why
selecting a plugin today makes every completing turn declaration-required, even when
the payload is empty.

### 3. Plugin `max_attempts` is ignored; `skipped` fails the run

`builtin@command` honors `instance.max_attempts`. `execute_plugin_finalizer()` does
not: it runs `describe → validate → execute → verify` once and returns. Config,
schema, CLI `show`, and the Rust policy wire all advertise `max_attempts` (Rust even
rejects values outside 1–16). For plugins that field is dead.

Separately, execute may return `skipped` (`_EXECUTE_STATUSES` includes it), but the
controller treats any status other than `success` as a run failure. A provider that
correctly reports “not triggered” therefore fails completion. Combined with bug 2,
plugins cannot even say they did not need to run.

### 4. Non-commit instances never re-run

`_pending_instance_ids()` reactivates commit when `submission_required` or
`trigger == dirty_repository` is still true after a later mutator. Every other
instance is gated on `instance_id not in ran_non_commit`. A `just check` instance
that runs *before* a formatter, or an audit instance that should see post-commit
evidence, will not run again. Later-dirt reactivation of commit is tested; later-dirt
reactivation of a check is not implemented.

This matches the earlier research’s “non-commit runs once” limitation, and it is
still true after `sase-rr`.

### 5. User-facing docs still describe the deleted controller

`docs/commit_workflows.md` still says that remaining dirty work starts “bounded
follow-up passes” that list dirty files and tell the agent to use `/sase_git_commit`
or `/sase_hg_commit`. That is the old commit-finalizer recovery prompt, not
`/sase_final`. Merge-conflict repair still uses the stitch resume skill; ordinary
dirty completion does not.

`docs/llms.md` and `docs/configuration.md` still cite
`src/sase/llm_provider/commit_finalizer.py`, which `sase-rr.2` deleted. Historical
`commit_finalizer_*` readers remain on purpose; these source citations do not.

Long-term memory `sase/memory/xprompts.md` still has no `%final` row. The generated
xprompt docs in `docs/xprompt.md` do. That memory note is stale relative to the
shipped directive.

### 6. Agent-facing contract gaps in `/sase_final` and pretty context

The skill documents only commit/refuse payloads and tells the agent to use `repo_id`
values “from the context.” Context obligations are keyed as `obligation_id`; the
manifest template is what actually contains `repo_id`. The values match, but the
field names do not. Pretty `sase final context` omits `manifest_template` entirely, so
an agent that forgets `-f json` cannot see the envelope it is supposed to submit.

End-of-turn instructions are appended whenever a plan object exists, including
`%final:none`. Enforcement is demand-driven (no recovery if nothing requires
submission), but the model still spends a tool call on `sase final context` for
launches that selected nothing.

### 7. `sase final list` “selected” is not this turn

`handle_final_list` resolves the default plan with empty selectors. During a
`%final:none` or `%final:lint` turn, `sase final list` still reports the configured
defaults as selected. Operators and agents who inspect `list` instead of `context`
get the wrong picture. The column name is `selected`; the data is `defaults`.

### 8. Schema and Rust policy disagree on `max_attempts`

Rust `validate_finalizer_instance_spec` requires `max_attempts` in 1..=16.
`sase.schema.json` only has `minimum: 1`. A config of `max_attempts: 20` is
schema-valid and fails at plan resolution.

`builtin@command` timeouts have no upper bound (`24h` is accepted). Plugin operations
are the opposite: a host-fixed 30.0s cap with no instance config. A `just check`
command instance can be given 20 minutes; an equivalent plugin cannot.

### 9. Test holes that hide the bugs above

There are no xfails in the dedicated finalizer suites. The dangerous gaps are
unasserted behavior, not known red tests:

- `%final:!commit` is parsed but never resolved in a plan test (Rust implements
  `Remove`).
- External payload *rejection* is implemented in the fixture plugin and never driven;
  unit tests mock `validate_external_declaration_payload`.
- `test_plugin_timeout_and_malformed_output_fail_closed` only asserts timeout.
- `worker_entry.py` has no direct tests; live e2e is not a full `CommitWorkflow`
  stitch.
- CLI `list`/`show`/`doctor` rendering and non-zero doctor exit are untested.
- Plugin `max_attempts`, `skipped` status, and “selected means sealed plan” are
  untested — which is why bugs 1–3 survived `sase-rr.4`.

## What is already strong

Do not “improve” these; they are the reason the protocol is worth extending.

- Host-owned selection: prompt text cannot supply argv, cwd, env, or credentials.
  Plugin config layers cannot activate instances.
- Built-in commit: opaque `repo-*` obligation IDs, sequential stitches, protected
  pre-run dirt, tree/SHA evidence, refusal-fail, conflict checkpoint, one
  declaration-recovery turn distinct from one conflict-repair turn.
- `builtin@command`: argv-only, no shell, sanitized env, configurable timeout, no
  model payload.
- Bounded controller: 8 cycles, no-progress fingerprint, fail-closed.
- Durable artifacts and metrics with bounded labels.
- CLI conventions: bare `sase final` defaults to `list`; `-f/--format`; positional
  submit path.

## How to make finalizers powerful

The companion reports already argued for host-owned **completion contracts** rather
than stop hooks. That direction is still right. The implementation gap is that the
host does not yet ask providers the questions the wire prepared: do you need a
payload, what is its schema, do you mutate, should you run again?

### Near-term: finish the provider contract, then ship three instances

**A. Context-time `describe`.** When publishing `final_context.json`, run `describe`
for each selected external instance (and read declared capabilities / schema
digests). Use the result to set `submission_required`, populate
`manifest_template.payloads` from the advertised JSON schema, and record
`MutatesRepository` so the controller knows what can reactivate later work. Do not
wait until execute.

**B. Truthful worker requests.** Pass the sealed plan’s selected instance IDs, the
context `run_id` / `agent_id` / `turn_nonce` / `context_digest`, accepted payload, and
host obligations. Honor `max_attempts`. Map execute `skipped` to “not pending,” not
to run failure.

**C. Triggers for non-commit instances.** Replace `ran_non_commit` with the same
trigger vocabulary commit already uses: `always`, `dirty_repository`,
`provider_requested`, plus an explicit `once`. A check that should see the tree after
a formatter belongs *after* that formatter and should re-run if the formatter created
new dirt.

**D. Shipped instances, selected by role.** The protocol without a portfolio is an
SDK. Configure, in trusted project/user config, a small set that xprompts can select
today with `%final` (no new directive required):

| Instance | Provider | Suggested selection | Job |
| --- | --- | --- | --- |
| `commit` | `builtin@commit` | default | Attributable dirty repos |
| `check` | `builtin@command` → `just check` | `#commit` / `#pr` / coder / epic work | Fast local verification before commit |
| `research-doc` | `builtin@command` or a narrow plugin | `#research*` | Month path, required sections, ranked recommendations |
| `sase-hygiene` | command wrapping existing audits | advisory, then required on land | `sase repo` / memory-read / generated-skill provenance |

Bind them by injecting `%final` from the xprompt that already knows the job, applying
role defaults *before* user `%final` so `%final:!check` still wins unless `required`.
Do **not** default `just check` globally; research and review turns would pay for it.

`builtin@command` is enough for `check` *today*, because it needs no payload. Do not
block that instance on the plugin-contract bugs.

### After the contract is truthful

These stay ranked below the contract fix because they need typed declarations or
cross-repo host context:

- **Delivery / review manifest.** Agent declares user-visible impact, tests, flag,
  migration, rollback, docs, limitations, artifact refs. Provider validates claims
  against the diff and writes a durable packet. This is the strongest use of the
  atomic declaration channel once templates are schema-driven.
- **Land/phase closeout.** Mechanical checks for epic symbols, descendant
  disposition, “phase workers do not create task beads,” plan `status: done`.
- **Cross-repo compatibility.** Core binding floor, plugin schemas, generated
  clients, sidecar links — using host-issued repo inventory, never plugin path
  discovery.
- **Post-commit reconciliation.** Idempotent bead/Patch/artifact evidence after
  commit proof (`after: [commit]`).
- **cwd policies beyond `primary`.** Linked and sidecar repos as closed host
  policies (`plans`, `research`, `opened:<repo_id>`), still never raw paths from
  prompt text.

### Do not stretch this seam

Keep using monitors for long jobs, gates for human authorization, CI for
authoritative provenance, and runner `finally`/TTLs for crash cleanup. Intentional
handoffs will keep skipping the controller; that is mechanical, not a bug to “fix”
by running finalizers after SIGTERM. A future `failure` / `always` lifecycle is a
separate design.

## Ranked recommended bug fixes / improvements

Ranked by (user-visible correctness × SASE-specific leverage) / (implementation risk).
Items 1–8 are bugs or protocol lies. Items 9–16 are capability upgrades.

| Rank | Kind | Recommendation | Why this rank |
| --- | --- | --- | --- |
| **1** | Bug | Pass sealed-plan `selected`, `run_id`, `agent_id`, and context/plan digests into every worker request. Add a regression that `%final:none %final:audit` does not advertise `commit`. | Every plugin is currently given the wrong identity document. Small, local, unblocks idempotent providers. |
| **2** | Bug | Run `describe` (and honor `RequiresSubmission` / `submission_schema_digest`) at context publish time. Stop hardcoding `submission_required=True` for all external instances. Put the advertised schema into `manifest_template`. | This is the difference between “plugins exist” and “plugins can be optional, typed, or silent.” Highest leverage remaining protocol fix. |
| **3** | Bug | Honor `max_attempts` for plugins. Treat execute `skipped` as not-pending. Align JSON schema `max_attempts` with the Rust 1–16 cap. | Config, CLI, and wire already claim this behavior. Cheap, currently a lie. |
| **4** | Bug | Replace `ran_non_commit` with explicit triggers (`always` / `dirty_repository` / `once` / `provider_requested`) so checks can re-run after a mutator. | Commit already has the reactivation model; checks that run once are unsafe next to formatters and generators. |
| **5** | Bug | Rewrite `docs/commit_workflows.md` recovery prose to `/sase_final` + stitch resume; retarget `docs/llms.md` and `docs/configuration.md` away from deleted `commit_finalizer.py`. | Agents and humans still being taught the old follow-up-pass model will skip the declaration channel. |
| **6** | Bug | Teach `/sase_final` non-commit payloads; use `obligation_id`/`repo_id` consistently; include `manifest_template` in pretty context *or* make the skill refuse pretty output. Skip end-of-turn injection when the sealed plan has zero submission-capable instances. | The skill is the only agent API. Empty `{}` templates plus field-name drift will produce bad submissions the moment a plugin is selected. |
| **7** | Bug | Make `sase final list`/`show` distinguish config default vs *this turn* selected when `SASE_ARTIFACTS_DIR` is set; keep defaults-only behavior outside a turn. | Operators debugging `%final` currently get defaults labeled as selected. |
| **8** | Bug | Drive the fixture plugin’s reject path, `%final:!commit` plan resolution, real `worker_entry` isolation/timeout/malformed JSON, CLI doctor/show handlers, and plugin `max_attempts` through tests. Live e2e should keep hermetic git, but unit tests must not mock away validate. | These holes are how bugs 1–3 shipped through `sase-rr.4`. |
| **9** | Improvement | Ship `check` as `builtin@command` wrapping `just check` (15–20 minute timeout) and select it from code/PR/epic xprompts via `%final:check`, with `after` ordering so it runs before `commit`. Do not make it a global default. | Highest product value that does not wait on plugin-contract work. Role binding is already possible: no xprompt currently emits `%final`. |
| **10** | Improvement | Same pattern for `research-doc` and a narrow `sase-hygiene` command instance (audited repo/memory reads, generated-skill source, no ephemeral workspace paths in plans). Start advisory. | Turns SASE prompt-law into host-verified completion for the two other high-volume jobs besides code. |
| **11** | Improvement | First-class role/xprompt default lists in trusted config (`finalizers.profiles.coder: [check, commit]`) applied before user `%final`, so authors do not have to remember the directive. Keep `%final:!name` and `required` as the escape hatches. | Selection-by-role is the design from the completion-contracts research; xprompt-injected `%final` is a workable v0, config profiles are the durable form. |
| **12** | Improvement | Configurable plugin timeouts and closed cwd policies (`primary`, `plans`, `research`, `opened:<obligation_id>`). Cap command timeouts too. | `just check` cannot live in a plugin at 30s; sidecar-aware checks cannot live in command while cwd is only `primary`. |
| **13** | Improvement | Typed delivery/review-manifest provider once item 2 exists: impact, tests, flags, migration, rollback, docs, limitations, refs — validated against host facts, never treated as proof. | Best use of the declaration channel beyond commit messages. |
| **14** | Improvement | Land/phase mechanical closeout (epic symbols, follow-up disposition, no phase-created task beads, plan `status: done`) as command or plugin instances selected only by land/phase xprompts. | Consequential SASE definitions of done currently enforced by prose. |
| **15** | Improvement | Post-commit bead/Patch/artifact reconciliation (`after: [commit]`) and cross-repo compatibility checks using host-issued inventory. | Valuable, but ordering and idempotency keys depend on truthful run identity (item 1) and mutation flags (item 2). |
| **16** | Later | `failure`/`always` lifecycle, async job/status providers, preview deploy, cryptographic provenance. File as separate designs. | Wrong seam today. Monitors, gates, and CI already exist. |

## Suggested sequencing

If only one follow-up epic is approved, its phases should be:

1. **Truthful plugin contract** — items 1–4 and 8 (bugs that make plugins lie).
2. **Agent/docs surface** — items 5–7 (stop teaching the old controller).
3. **Shipped `check` + xprompt `%final`** — item 9, then 10–11 (power users can feel).
4. **Typed declaration providers** — items 12–15, after describe-at-context exists.

Do not wait for `sase-rr` land to *design* this; the phases are already closed and the
remaining work is follow-up. Do wait to close `sase-ro` only on the retirement
criteria already on that bead (unconditional path, no Off branch, generated skill
deployed from the landed tree). The items above are not retirement blockers.

## Sources

- `bead:sase-rn`, `bead:sase-rr` (including `.1`–`.4` notes), `bead:sase-ro`
- `plan:202608/pluggable_finalizers.md`, `plan:202608/retire_pluggable_finalizers.md`
- `research:202608/finalizer_protocol_and_extensibility/finalizer_protocol_and_extensibility.md`
- `research:202608/finalizer_completion_contracts/finalizer_completion_contracts.md`
- Current sources: `src/sase/finalizers/{controller,declaration,executor,providers,cli,plan,config,sdk,worker_entry}.py`, `src/sase/llm_provider/_invoke.py`, `src/sase/xprompts/skills/sase_final.md`, `src/sase/default_config.yml`, `src/sase/config/sase.schema.json`, `docs/{commit_workflows,llms,configuration,xprompt}.md`
- Shared wire: `sase-core` `crates/sase_core/src/finalizer/{wire,selection,mod}.rs`
- Tests: `tests/test_finalizers_{foundation,protocol_harness,extension_runtime,live_e2e,commit_reconciliation}.py`, `tests/test_finalizer_declaration_channel.py`, `tests/fakey/test_retry_pipeline_e2e.py`
- Live CLI: `sase final list`, `sase final doctor`, `sase final context -f json` on this turn (commit selected, not triggered, no obligations before the research write)
