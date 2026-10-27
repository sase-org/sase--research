# Escalating the commit finalizer's conflict-repair turn to `@xlarge`

_Researcher: cld · 2026-10-27 · Scope: the `builtin@commit` finalizer's one-shot
conflict-repair turn in the `sase` repo, plus 55 days of local run artifacts._

## TL;DR

- **Yes, do it, but as a configurable launch setting rather than a hard-coded
  `@xlarge`.** Add `llm_provider.conflict_repair_model` with a shipped default of
  `"@xlarge"`, modeled on `epic_lander_model` / `big_epic_lander_model`. Resolve it only
  when a conflict actually needs an agent turn, and run the repair turn on that
  provider/model/effort.
- **The one fact that makes this cheap and safe:** the repair turn already starts a
  **fresh provider session**. Every `provider.invoke` mints a new session id, and Claude
  only uses `--resume` for wait-state nudges inside a single invoke. Switching models or
  even providers therefore loses no conversational context, because none is carried
  over today.
- **The evidence supports the direction but does not prove the benefit.** There were
  101 conflict-repair turns between 2026-09-02 and 2026-10-26, and **none ran on an
  opus-class model**. They ran on muse-spark, grok-4.6, gpt-6-luna, gpt-5.5 and sonnet,
  mostly `@medium` epic-phase workers. Loud failures were rare (2 of about 100 attributable
  to the model, and both came from a protocol gap that has since been closed
  structurally). The real case is about **silent merge quality**, plus judgment under
  noisy verification: 59% of repair transcripts had to adjudicate pre-existing or
  unrelated gate failures. Those failure modes are exactly where a stronger model pays
  off, but I could not measure them from the artifacts.
- **Adjustments I recommend (detailed in §5):** make it configurable with an `inherit`
  opt-out. Never re-resolve or downgrade when the turn already ran through `@xlarge`.
  Respect the exec-provider override (`SASE_LLM_EXEC_PROVIDER`) and launch-scoped alias
  overrides. Fail open to the turn's own model when the escalated provider can't be
  resolved or spawned. Re-export the provider sync ceiling for the repair provider.
  Record the repair model per invocation. Pair the change with **giving the repair turn
  context it lacks today**. Scope it to conflict repair only, not declaration recovery.
- **Don't do these:** escalate-on-second-failure, or a classifier that escalates only
  "hard" conflicts. Instead, keep shrinking the conflict set mechanically, for example a
  deterministic `sase-core-revision.txt` pin resolver, so the LLM-repair population stays
  genuinely semantic.

## 1. How conflict repair works today

The relevant chain, all in this repo:

1. The agent's provider turn ends, and `invoke_agent()` calls `run_finalizers(provider=…,
   model_tier=…, model_override=…, options=…)` with **the same provider object and
   model selection the agent turn used** (`src/sase/llm_provider/_invoke.py:441-470`).
2. The commit finalizer dispatches each declared repo through `sase stitch create`.
   During the rebase/sync, git conflicts go through the deterministic resolvers first
   (`_continue_rebase_resolving_semantic_conflicts` →
   `sdd._semantic_conflict_resolver.resolve_semantic_conflicts`, in
   `src/sase/vcs_provider/plugins/_git_commit_dispatch.py:194-223`). Only conflicts those
   can't settle exit with `EXIT_CODE_CONFLICT = 2`
   (`src/sase/workflows/commit/workflow_types.py:21`).
3. `dispatch_commit_decisions` sees exit 2 and calls `resolve_commit_conflict(...)`,
   forwarding the same `provider`, `model_tier`, `model_override` and `options`
   (`src/sase/finalizers/commit_dispatch.py:398-448`). In the bounded post-repair
   continuation (`allow_repair=False`), a conflict fails the run with
   `repair_handoff_continuation_bound` and no agent turn runs.
4. `resolve_commit_conflict` enforces a **one-shot budget per repo per run**: if a
   `conflict_repair_prompt.<repo>.md` artifact already exists, it fails with
   `second_unresolved_conflict`. Otherwise it calls `run_conflict_repair_turn`
   (`src/sase/finalizers/commit_repair_conflict.py:80-245`).
5. `run_conflict_repair_turn` builds a fixed prompt (repo name, checkout path, and
   resolution, verification and scope rules) and, inside `finalizer_owned_turn()`, calls
   `invoke_with_instructions(provider, prompt, purpose="conflict_repair", …,
   model_tier=model_tier, model_override=model_override, options=options)`
   (`commit_repair_conflict.py:461-583`). It never passes `provider_name`, so the
   instruction-bundle label comes from `provider.provider_name()`.
6. The repair agent must resolve, verify, continue the VCS operation, run
   `sase stitch create --resume`, and then submit `/sase_final` for any other dirty repos.
   Turn-ending handoffs (`sase monitor start`, `/sase_handoff`, gates) are **refused**
   inside finalizer-owned turns (`src/sase/finalizers/owned_turn.py`,
   `src/sase/main/monitor/start.py:65-68`, `src/sase/tool/routing.py:276`, since
   `9e5cc41598`, 2026-10-07).

### Key fact: the repair turn is a fresh session

- Claude: `_invoke_loop` starts with `active_session_uuid = None` and passes
  `--session-id <new uuid>`. `--resume` is used only for in-invoke wait-state
  continuations (`src/sase/llm_provider/claude.py:452-578`). A conflict-repair invoke is
  a new conversation.
- Codex: "Codex has no session persistence — reconstruct context"
  (`src/sase/llm_provider/codex.py:362`).
- The other adapters follow the same per-invoke pattern.

So the repair model sees only the repair prompt plus whatever it finds in the checkout.
It does not know the original task, bead or plan. **Changing the model therefore costs
nothing in context continuity**, which removes the strongest usual objection to
switching models mid-run. It also exposes a separate weakness (§4.3): even the original
model arrives at the repair "cold".

### What `@xlarge` resolves to

`src/sase/llm_provider/models.yml:280-282`:

```yaml
xlarge:
  target: "claude/opus@xhigh || codex/gpt-6.1-sol@xhigh || grok/grok-4.7@xhigh"
```

`@xlarge` is an **ordered fallback**, not a pool. In practice "escalate to `@xlarge`"
means *Claude Opus at `xhigh`, unless routing marks Claude unavailable, then
gpt-6.1-sol, then grok-4.7*. Ordered-fallback resolution consults the provider routing
context (disables and availability) via `resolve_launch_selection` →
`resolve_model_provider_with_cursor` (`src/sase/llm_provider/launch_selection.py:264-370`,
`load_balancing.py:467-530`). It consumes no round-robin cursor, so resolving it in the
finalizer has no side effects on pool fairness.

## 2. Evidence from 55 days of conflict-repair turns

Method: I scanned `~/.sase/projects/*/artifacts/ace-run/**/finalizers/commit/
conflict_repair_prompt.*.md` and joined each hit with the run's `agent_meta.json`,
`finalizer_result.json`, the repair operation record, and the stitch stdout/stderr.
Window: **2026-09-02 → 2026-10-26**. The scripts were throwaway, read-only, and run
outside the repo.

### 2.1 Frequency and base rate

| Measure | Value |
| --- | --- |
| Conflict-repair turns | **101** (57 `sase`, 44 `bob-cli`) |
| Runs with a commit-finalizer dir, Sep–Oct, all projects | 1,976 |
| Repair rate per commit-finalizer run | **~5.1%** |
| Repairs per day | **~1.8** |
| Files per conflict (after semantic resolvers) | median 1, max 6; 67% single-file |

### 2.2 Which models did the repairs (the turn's own model)

| Provider / model / effort | Repairs |
| --- | --- |
| muse / muse-spark-1.3-contributor / xhigh | 38 |
| grok / grok-4.6 / high | 14 |
| codex / gpt-5.5 / xhigh | 12 |
| codex / gpt-6-luna / xhigh | 10 |
| muse-spark@high, grok-4.6@xhigh, claude/sonnet@xhigh | 6 each |
| everything else (gpt-6-astra, gpt-6-luna@high, gemini-flash, …) | 9 |
| **claude/opus (any effort), or any `@large`/`@xlarge` alias** | **0** |

By alias: 62 `@medium`, 7 `@small`, 30 explicit or no alias, 2 custom.

Conflict rate per (alias, model), from the 1,976-run base:

| Alias, model | Runs | Repairs | Rate |
| --- | --- | --- | --- |
| `@medium`, gpt-5.5 | 35 | 8 | 22.9% |
| `@medium`, sonnet | 39 | 6 | 15.4% |
| `@medium`, grok-4.6 | 118 | 13 | 11.0% |
| `@medium`, muse-spark | 320 | 27 | 8.4% |
| `@xlarge`, opus | 235 | 0 | 0.0% |
| (none), opus | 113 | 0 | 0.0% |

**Don't read the 0% as "opus avoids conflicts".** That's a workload confound: 346 of 362
opus runs committed **only to sidecar repos** (plans and research write new files), while
534 of 579 `@medium` runs committed to the main repo, mostly as parallel epic-phase
workers touching shared files. **We have no local evidence about opus's
conflict-repair quality.** The proposal would be its first exposure.

### 2.3 Outcomes and failure taxonomy

| Outcome | Count | Model-attributable? |
| --- | --- | --- |
| Success (`conflict_repair=success`), including 4 `revision_pin_skipped`, 1 `memory_change_uncovered`, 1 `stitch_failed`-after-commit, 1 `stitch_timeout_after_commit` | 91 | — |
| `controller_exception`: provider exit 143 (killed) | 3 | No (infra / timeouts) |
| `controller_exception`: provider exit 1 / CalledProcessError | 2 | No |
| `controller_exception`: workspace dir vanished mid-repair | 1 | No |
| `controller_exception`: `AttributeError` in host code | 1 | No (bug) |
| `second_unresolved_conflict` (gpt-6-luna@xhigh, 2026-10-04, both `bob-cli`) | 2 | **Yes**, but structural |
| No result yet (run from 2026-10-26) | 1 | — |

Both model-attributable failures had the same shape. The repair agent **handed its
verification gate (`just all`) to SASE Monitor** mid-repair, which ended the turn with
the rebase still paused. The host resumed and got exit 2 again. Three days later
(`9e5cc41598`) turn-ending handoffs became mechanically refused in finalizer-owned
turns. Since then, every loud failure has been infrastructure.

### 2.4 What conflicts reach the LLM

- Kind mix (98 runs with a file list): pure code 20, prose 16, test code 9, data/config 7,
  and mixed or other for the rest.
- Most frequent files: `Justfile` (10), `README.md` (9), **`sase-core-revision.txt`
  (9)**, `package.json` (6), plugin `manifest.json` (3), then a long tail of `.rs` and
  `.py` sources and docs.
- Pin-file conflicts are routed to LLM repair **by design**: "A concurrent pin change on
  origin during the primary sync uses the existing conflict-repair flow"
  (`docs/contribute/commit-workflow-orchestrator.md:714-716`).

### 2.5 What repair turns spend their time on

- Duration of the repair model turn (operation records): **median ~11 min, p90 ~58 min**,
  with a multi-hour tail. Most of that is running the target repo's gate.
- 68 of 87 transcripts with a response mention running a gate (`just check`, `just all`,
  cargo or pytest, `sase tool run`).
- **51 of 87 (59%) had to adjudicate pre-existing or unrelated failures** ("also fails on
  onto …", "pre-existing", "unrelated"). Bead notes show the same pattern repeatedly
  (`sase-1nf.10.1`, `sase-1le.20.1`, `sase-1ko`, `sase-11u`, `sase-13s`, `sase-13q`,
  `sase-13n`, `sase-10g`).
- 50 of 87 mention duplicates, mostly the model checking for the
  both-sides-added-an-entry hazard the prompt warns about.

## 3. Is this a good idea?

### 3.1 Arguments for

1. **The asymmetric payoff is real.** A repair turn decides what lands on `master`. A
   loud failure strands the run, which is recoverable. A **silent** bad merge (a dropped
   hunk, a duplicated enum entry, the wrong side of a pin, a "pre-existing failure" that
   was actually ours) lands, is pushed, and is attributed to an agent that never saw it.
   That's the worst place in the system to economize.
2. **The population is pre-filtered toward hard cases.** Deterministic resolvers run
   first, so what reaches the LLM is by construction what mechanical rules couldn't
   settle.
3. **The repair turn is context-free (§1),** so the agent has to reconstruct intent from
   git alone. That's a reasoning-heavy task, and today it's handled almost entirely by
   `@medium`-class models.
4. **The verification judgment is subtle.** In 59% of repairs the agent had to decide
   whether a red gate was its own problem, without being able to hand off to a monitor.
   That's a judgment call where stronger models help and weaker ones either over-block or
   wave through real regressions.
5. **The cost is bounded by frequency.** About 1.8 repairs per day is about 5% of
   commit-finalizer runs, and only the repair segment of each run gets escalated. It
   adds roughly 28% to the current count of Claude-opus sessions (101 repairs vs 362 opus
   runs over the same window). That's noticeable for Claude usage windows, but `@xlarge`
   falls back to codex/grok when Claude is unavailable.
6. **It follows the existing philosophy.** `decisions:size-alias-effort-ladder` says
   capability is bought through the model. `big_epic_lander_model: "@xlarge"` already
   encodes "use the biggest model where integration risk concentrates", and conflict
   repair is the per-commit version of that same integration risk.

### 3.2 Arguments against, and caveats

1. **Unproven benefit.** Loud failures attributable to the model were 2 of about 100,
   and their cause is now closed structurally. Escalation will **not** reduce the
   remaining loud failures (exit-143 kills, vanished workspace, host bugs). It might
   increase exit-143 timeouts if opus@xhigh turns run longer, though gate time dominates
   anyway. Silent quality is the target, and it currently has **no metric**. Without
   instrumentation (§5, R5) you won't be able to tell whether this helped.
2. **"Always" can be a downgrade or a gratuitous switch.**
   - If the turn already ran through `@xlarge`, re-resolving might pick a different
     fallback member than the turn used.
   - If the turn ran `opus@max`, a literal `@xlarge` drops it to `xhigh`.
   - If the user forced an execution provider (`SASE_LLM_EXEC_PROVIDER`, as tests do with
     `fakey`, or for provider testing), escalation would silently bypass that.
3. **Provider-switch plumbing is not free.** The finalizer currently reuses the turn's
   provider *object*. A different provider needs its own `get_provider()`, the
   `SASE_PROVIDER_SYNC_CEILING_SECONDS` / soft-ceiling env re-exported for **its** ceiling
   (`_invoke.py:66-84`, `382-404`), a usage hot hint, and an explicit `provider_name` for
   the instruction-bundle label. A remote `%dispatch` machine may not have the Claude CLI
   installed or authenticated.
4. **Attribution gets muddied.** `usage.json` is a single per-run blob with no model
   attribution (`_subprocess_artifacts.py:58-66`), and the agent row, `agent_meta.model`
   and commit metadata all name the turn's model. Opus tokens would be billed or
   displayed under (say) muse-spark unless the repair invocation records its own
   selection.
5. **It treats a symptom of two other problems:**
   - Repair turns are blind to intent (§4.3).
   - Some conflict classes should never reach a model. 9 of 98 were
     `sase-core-revision.txt` pin bumps, and the host knows the sibling's pushed SHA, so
     picking the descendant revision is mechanical.

   Escalation without these fixes spends `opus@xhigh` on work that is either
   under-informed or trivial.

### 3.3 Verdict

Good idea, with the adjustments below. The fresh-session finding removes the main
technical risk. The frequency data bounds the cost. And landing merged code on `master`
is the one place where a weak model's mistakes are silent. But ship it as a
**configurable launch setting with an observable selection**, so you can later answer
"did it help?" and turn it off temporarily when Claude quota is tight.

## 4. Approaches considered

### 4.1 Where the policy lives

| Option | Pros | Cons | Verdict |
| --- | --- | --- | --- |
| **A. Hard-code `"@xlarge"`** in `run_conflict_repair_turn` | ~20 lines | No opt-out; invisible in Launch settings; no temporary override; a magic string in finalizer code | Reject |
| **B. New launch model field `llm_provider.conflict_repair_model`** (default `"@xlarge"`) | Mirrors `epic_lander_model` / `big_epic_lander_model`. Gets `LaunchModelSettingSnapshot`, expression validation with shipped-default fallback (`_launch_model_field_value`), Models-panel rows (`ace/tui/modals/models_panel_rows.py:106-124`), and `setting:<field>` temporary overrides for free. Users can set `@large`, `@xlarge@max`, or a pinned model | Touches several files; empty string is treated as invalid and falls back to the shipped default (`model_launch_settings.py:410-434`), so opt-out needs an explicit sentinel | **Recommend** |
| C. Per-instance finalizer config (`builtin@commit` config) | Recorded in the finalizer plan digest | Model routing would then live in two config trees; builtin finalizer config is deliberately constrained | Reject |

**Rust boundary.** The choice between epic-land fields is Rust-owned
(`select_epic_land_model` via `src/sase/core/model_route_facade.py`). Should this choice
be Rust-owned too? I'd keep it in **Python, next to the commit finalizer**, which is
itself Python and runner-only. No TUI, web or editor surface has to reproduce the
repair-time decision; they only display the setting, and that comes from the shared
snapshot machinery. If you later want the policy unit-testable from `sase-core`, or
reused by other finalizer-owned turns, move the pure function
`select_conflict_repair_model(turn_selection, configured_expr) -> {model, source}`
into `sase_core` alongside `select_epic_land_model`. That move requires bumping the
`sase-core-revision.txt` pin.

### 4.2 When to escalate

| Option | Verdict | Why |
| --- | --- | --- |
| **Always, on the first (only) repair turn** | **Recommend** | Silent errors are the target, and they're only prevented on the first attempt. |
| Escalate only on a second attempt (same model first) | Reject | The one-shot budget exists for good reasons (a paused rebase, a partially staged tree). Loud first-attempt failures are rare and mostly infra, and a bad-but-clean first resolution lands with nothing to escalate from. |
| Escalate only "hard" conflicts (classify by file type or size) | Reject for now | Adds a heuristic that misjudges in both directions. 67% of conflicts are single-file, but single-file `.rs`/`.py` conflicts are exactly the semantic ones. Shrink the easy set with deterministic resolvers instead. |
| Escalate only when the turn's model is below some size | Fold into "never downgrade" | Cross-provider capability ordering isn't defined in the codebase. The only safe comparison is "same alias" or "same model, compare effort rung". |

### 4.3 The complementary fix: give the repair turn context

Today's prompt (`commit_repair_conflict.py:474-528`) carries the repo name and path but
not:

- the **conflicted files and incoming upstream commits** that `_format_rebase_conflict`
  already computes and prints to the stitch's stderr (`_git_commit_dispatch.py:231-247`),
  which is available as `stitch.stderr` at the `resolve_commit_conflict` call site;
- the **declared commit message** for this repo (the intent of "our" side);
- a pointer to the **original task**: the run's `raw_prompt.md`, the bead id, or the
  agent's final response.

`declaration_recovery` already does exactly this with `build_recovery_evidence(...)`
(`src/sase/finalizers/declaration_recovery.py:71-79`). Conflict repair is the one
finalizer-owned turn that runs blind. The prompt also says "every repository *you*
changed this turn", which reads oddly when a different model runs the repair. That
wording should become "the original agent turn". This fix is cheap, helps every model,
and pairs naturally with escalation: the strongest model with the most context is the
right combination for the riskiest commit step.

## 5. Adjusted requirements

The user's requirement is: *"always escalate to `@xlarge` when the stitch/commit
finalizer hits a merge conflict that requires another agent turn."* My adjustments, each
**clearly a change from that requirement**:

- **R1. Configurable, default `@xlarge`** *(adjustment: "always" becomes "by default")*.
  Add `llm_provider.conflict_repair_model: "@xlarge"` as a fourth `LaunchModelField`.
  Accept any `%model` grammar (`@large`, `@xlarge@max`, `claude/opus@max`). Add an
  explicit opt-out sentinel `inherit` meaning "use the turn's own selection". An empty
  string can't be the opt-out, because the existing field loader treats empty as invalid
  and falls back to the shipped default.
- **R2. Never gratuitously re-resolve or downgrade** *(adjustment)*.
  - If the turn's alias trail (`agent_meta.model_alias_trail`) already contains the
    target alias, reuse the turn's exact provider/model/effort.
  - If the resolved escalation target has the same provider and model as the turn, keep
    the **higher** of the two effort rungs.
  - Don't attempt any other cross-model "stronger than" comparisons.
- **R3. Respect routing overrides** *(clarification)*.
  - If `SASE_LLM_EXEC_PROVIDER` is set, inherit the turn's selection. That keeps test
    harnesses on `fakey` and honors deliberate provider pinning.
  - Resolve the target with the launch-scoped alias overrides
    (`active_launch_alias_overrides()`), so a launch that redefines `@xlarge` gets its
    own definition.
  - Resolve through `resolve_launch_selection(..., consume=True,
    routing_context=capture_provider_routing_context())`, so provider disables and usage
    routing apply.
- **R4. Fail open before spawn, never after** *(adjustment)*. If resolving the target,
  or `get_provider()` for it, raises (unknown provider, CLI not installed on a dispatch
  host), log a warning diagnostic and run the repair on the turn's own selection. Once
  the escalated provider has started, its failure is the repair's failure. Don't retry
  on another model, because the checkout may be partially staged.
- **R5. Make the selection observable per invocation** *(new requirement)*.
  - Record the provider, model, effort and `source` (`configured` / `shipped` /
    `inherit` / `same_alias` / `exec_override` / `fallback_after_error`) in the
    conflict-repair operation record, as a finalizer evidence item (e.g.
    `kind="conflict_repair_model"`), and in `agent_meta.json`.
  - Make sure the repair invocation's usage can be attributed to its own model, not the
    turn's.
  - This is what lets you answer "did escalation help?" later.
- **R6. Provider-correct invocation environment** *(new requirement)*. Around the repair
  invoke, export the **repair** provider's sync and soft ceilings, then restore the
  turn's values. Emit the usage hot hint for the repair provider. Pass `provider_name=`
  to `invoke_with_instructions` so the instruction bundle and manifest carry the right
  label.
- **R7. Scope: conflict repair only** *(clarification)*. Declaration-recovery turns stay
  on the turn's model for now. They're a protocol-compliance repair, not an integration
  decision. Revisit only if their failure data warrants it.
- **R8. Give the repair turn context** *(new, complementary)*: conflicted files and
  incoming commits from `stitch.stderr`, the declared commit message, and a pointer to
  the original prompt and response artifacts (§4.3).
- **R9. Shrink the LLM-repair set mechanically** *(follow-up, not a blocker)*: start with
  a deterministic resolver for `sase-core-revision.txt` pin conflicts (choose the
  descendant revision, which the host can check).

## 6. Recommended solution

### 6.1 Code shape

1. **Config surface** (`src/sase/llm_provider/model_launch_settings.py`,
   `src/sase/default_config.yml`):
   - Add `CONFLICT_REPAIR_MODEL_FIELD = "conflict_repair_model"`, default `"@xlarge"`,
     plus a `setting:conflict_repair_model` override key and
     `get_conflict_repair_model()`.
   - Document it in `default_config.yml` next to `big_epic_lander_model`, per the
     "Default Keymap Config" gotcha.
   - Add a Models-panel row (`ace/tui/modals/models_panel_rows.py:106-124`) and the
     `config.py` re-export, as the epic fields have.
2. **Selection** (new `src/sase/finalizers/commit_repair_model.py`):

   ```python
   @dataclass(frozen=True)
   class RepairInvocation:
       provider: Any
       provider_name: str | None
       model_override: str | None
       options: LLMInvocationOptions | None
       source: str  # configured|shipped|inherit|same_alias|exec_override|fallback_after_error

   def resolve_conflict_repair_invocation(*, turn_provider, turn_model_override,
                                          turn_options, model_tier, artifacts_dir) -> RepairInvocation:
       # 1. SASE_LLM_EXEC_PROVIDER set            -> inherit (source=exec_override)
       # 2. expr = conflict_repair_model setting; expr == "inherit" -> inherit
       # 3. target alias in agent_meta.model_alias_trail -> inherit (source=same_alias)
       # 4. sel = resolve_launch_selection(PromptDirectives(model=expr),
       #          active_launch_alias_overrides(), model_tier=model_tier, consume=True,
       #          routing_context=capture_provider_routing_context())
       # 5. same provider+model as turn -> keep the higher effort rung
       # 6. provider = get_provider(sel.provider)   # any exception -> inherit
       #                                            # (source=fallback_after_error)
   ```

3. **Invocation** (`commit_repair_conflict.py`):
   - In `run_conflict_repair_turn`, call the resolver before writing the prompt artifact.
   - Wrap the invoke in a small context manager that sets and restores
     `SASE_PROVIDER_SYNC_CEILING_SECONDS*` for the repair provider and emits the usage
     hot hint.
   - Pass `provider_name=` through `invoke_with_instructions`.
   - Add the selection to the operation record and the evidence list.
   - The `_invoke.py` helpers `_provider_sync_ceiling_seconds` and
     `_mark_usage_hot_for_launch` are private. Lift them into a small shared module
     rather than importing underscored names across packages, which Symvision would
     flag.
4. **Prompt context (R8):**
   - Thread `stitch.stderr` (already in scope at `commit_dispatch.py:433`) and the
     declared message into `resolve_commit_conflict` → `run_conflict_repair_turn`.
   - Append a bounded "Conflict context" section: conflicted files, incoming commits, the
     declared message, and the artifact paths of the original prompt and response.
   - Reword "you changed this turn" to "the original agent turn changed".
5. **Tests** (with the `fakey` provider):
   - The escalated selection reaches `invoke`.
   - The exec override keeps `fakey`.
   - An `@xlarge` turn isn't re-resolved and no cursor is consumed.
   - `inherit` is honored.
   - A `get_provider` failure falls back and records `fallback_after_error`.
   - Ceiling env vars are restored after the invoke.
   - The evidence item is present.
6. **Docs.** Update the conflict-repair section of
   `docs/contribute/commit-workflow-orchestrator.md` and the configuration reference for
   the new field. Read `sase memory read docs_writing` first.

### 6.2 Rollout and success criteria

- Ship with the default `@xlarge`. Watch the `conflict_repair_model` evidence and repair
  outcomes for about 4 weeks (about 50 repairs at the current rate).
- Track:
  - loud failure rate (expected unchanged; infra-dominated);
  - repair duration (expect gate-dominated, so roughly flat);
  - Claude usage-window pressure (+~1.8 opus sessions per day);
  - a **silent-quality proxy**: follow-up commits or beads within 7 days that touch the
    same conflicted files with "fix", "restore", "dedupe" or "revert" in the subject.
- **Reopen condition:** the silent-quality proxy doesn't improve and Claude quota
  pressure becomes material. Then set `conflict_repair_model` to `@large`, or temporarily
  to `inherit` via the `setting:` override.
- Optional: capture the decision as a new `decisions:` record ("Conflict repair escalates
  to `@xlarge`") through `/sase_memory_write`, since it sets a cross-cutting model-routing
  precedent for finalizer-owned turns.

### 6.3 One-paragraph recommendation

Implement escalation as a new `llm_provider.conflict_repair_model` launch setting
(default `"@xlarge"`, opt-out `inherit`). Resolve it lazily when a conflict needs an agent
turn, through the normal launch-selection machinery, so alias overrides and provider
availability apply. Skip it when the turn already ran `@xlarge` or an exec-provider
override is active. Fail open to the turn's own model only before the repair provider
starts. Run the repair with that provider's ceilings and instruction label, and record
the chosen model as finalizer evidence so the change can be evaluated. Land the
repair-prompt context enrichment in the same change, and follow up with a deterministic
pin-file resolver. Escalation buys judgment, context buys information, and mechanical
resolvers keep both focused on the conflicts that actually need them.

## Appendix: data notes and limitations

- Artifact retention: the earliest repair found is 2026-09-02. Older runs may have been
  pruned or may predate the feature.
- My categorization of agent kind (phase/land/other) uses name shape and is approximate.
  The opus-vs-medium repo split uses `commit_results.json` entry names: the main repo
  records an empty name, sidecars record theirs.
- I couldn't measure silent merge correctness from artifacts. The "pre-existing failure"
  and "duplicate" percentages are keyword matches over repair responses, not graded
  judgments.
- I quote no per-token prices. Cost reasoning here is relative (frequency × segment
  share), not dollar-denominated.
