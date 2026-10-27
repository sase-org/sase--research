# Finalizer Conflict-Repair Model Escalation: Should a Stitch/Commit Merge Conflict Escalate to `@xlarge`?

Researcher: mus · Swarm `research.2k` · 2026-10-27

## TL;DR

Escalating the conflict-repair turn to a bigger model is directionally sound but
**escalating to the `@xlarge` alias specifically is the wrong implementation**.
`@xlarge` names a *launch-time, cross-provider ordered fallback*
(`claude/opus@xhigh || codex/gpt-6.1-sol@xhigh || grok/grok-4.7@xhigh`), while the
conflict-repair turn runs *inside* the finalizer with an already-bound provider
object. You cannot "switch to `@xlarge`" there without re-resolving a new provider
mid-finalizer — new auth, new subprocess, rebound instruction delivery, and
provider-specific capability checks — which is a large, risky change for a turn that
fires rarely and already has a one-shot budget. The better implementation is
**same-provider effort/model step-up for the single repair turn**: keep the agent's
provider, invoke the repair at that provider's strongest model and `xhigh` effort,
and only if the provider supports it. My recommended solution is a small config knob
(`commit_finalizer.conflict_repair_boost`, default on, effort-only) plus measuring
repair outcomes before considering any cross-provider escalation.

## 1. What the proposal actually touches

### 1.1 The conflict path today

When the built-in `commit` finalizer dispatches an accepted commit decision, each
repository goes through `sase stitch create` via a host-side subprocess
(`dispatch_commit_decisions` in `src/sase/finalizers/commit_dispatch.py`). If the
checkout is left in an in-progress rebase/merge state — the remote moved under the
agent, or a previous operation left a paused operation behind — the stitch exits with
`EXIT_CODE_CONFLICT` (`src/sase/workflows/commit/workflow_types.py`, value 2), and
`src/sase/workflows/commit/workflow.py` prints "hit a merge conflict … run
`sase stitch create --resume`".

The finalizer then calls `resolve_commit_conflict`
(`src/sase/finalizers/commit_repair_conflict.py`), which:

1. Runs **one extra LLM turn**, `run_conflict_repair_turn`, with a long,
   verification-heavy prompt (resolve unmerged files, run the repo's gates,
   `stitch create --resume`, re-verify, report).
2. Re-runs the resume in the same stitch and checks commit markers.
3. On a **second** conflict raises `second_unresolved_conflict` — the budget is
   one-shot per repository per run (`_conflict_repair_spent` guard).
4. Conflicts hit during the *continuation* (remaining repos after a repair) fail
   closed with `repair_handoff_continuation_bound` — **no repair turn at all**.

So "a merge conflict that requires another agent turn" is precisely the
`purpose="conflict_repair"` invocation inside `run_conflict_repair_turn`. It is
already bounded: at most one repair turn per repo, zero in continuation.

### 1.2 What model the repair turn uses today

`run_finalizers` receives the agent's already-bound `provider` object plus
`model_tier` (`"large"`/`"small"`), `model_override`, and `options`
(`src/sase/finalizers/controller_run.py`, `src/sase/llm_provider/_invoke.py`).
Every finalizer follow-up turn — declaration recovery *and* conflict repair —
reuses them verbatim (`invoke_with_instructions(..., model_tier=model_tier,
model_override=model_override, options=options)`). **The repair turn runs at
whatever model/effort the original agent ran at.** An agent launched at `@small`
or `@medium` therefore repairs conflicts with a small/medium model at non-`xhigh`
effort.

### 1.3 What `@xlarge` actually is

From `src/sase/llm_provider/models.yml`:

```yaml
xlarge:
  target: "claude/opus@xhigh || codex/gpt-6.1-sol@xhigh || grok/grok-4.7@xhigh"
```

Three facts matter:

- It is a **launch alias resolved once** in `resolve_launch_selection`
  (`src/sase/llm_provider/_invoke.py`) into a concrete
  provider/model/effort triple. `model_override` downstream is a *model name for
  the already-chosen provider*, not an alias.
- The `||` is an **ordered fallback across providers** (per the
  `size-alias-effort-ladder` decision record), and every alias is required to span
  more than one provider. The finalizer holds one provider object; alias fallback
  semantics do not exist there.
- Every member runs at **`xhigh` effort on each provider's flagship model** — the
  most expensive, slowest, most rate-limit-exposed configuration SASE ships.

## 2. Critique of the plan as stated

### 2.1 "Always escalate to `@xlarge`" conflates two different escalation axes

There are two independent upgrades available to the repair turn: a **bigger model**
and **more reasoning effort**. The evidence in this repo says effort is the
load-bearing one. The `size-alias-effort-ladder` decision record's whole thesis is
that "a size alias should buy capability through the *model*, not by starving a
good model of reasoning budget" — and its corollary cuts the other way too: a
capable model starved of budget underperforms. The repair prompt is long,
procedural, and verification-heavy (run gates, check markers, resume, re-verify);
that shape benefits strongly from `xhigh` effort on the *same* model, which costs
far less than switching to opus-class models and needs no provider swap.

### 2.2 Cross-provider escalation inside the finalizer is architecturally hostile

"Escalate to `@xlarge`" literally means: abandon the bound provider, resolve
`claude/opus@xhigh`, fall back to codex then grok on failure, construct a new
provider object mid-`run_finalizers`, rebind instruction delivery
(`SASE_INSTRUCTIONS_FILE`, v2 manifests, `agent_meta.json` provenance), and route
usage/cost attribution to a different provider. Consequences:

- **Auth/latency**: a fresh provider launch (CLI subprocess, login/session checks)
  inside a turn that is already past the agent's main latency budget.
- **Fallback lies**: if `claude` is down and the alias would have fallen back to
  codex at launch, the in-finalizer re-resolution must duplicate that fallback
  logic or silently downgrade the guarantee the alias name promises.
- **Capability skew**: providers differ in VCS tooling behavior (sync ceilings,
  conflict-state detection, `resolve_model_name` tiers). The repair prompt assumes
  the executing provider's VCS surface; swapping providers swaps those behaviors
  under a prompt written for the original one.
- **Decision-record friction**: `single-turn-agents`, `host-owned-completion`,
  and the one-shot repair budget all push toward *bounded, same-context*
  recovery. A provider swap is the opposite of bounded.

### 2.3 "Always" ignores frequency, cost, and the actual failure mode

- **Frequency**: conflicts require a concurrent writer to the same repos (or a
  leftover paused operation) between baseline and stitch. This is rare relative to
  total finalizer runs, but "always escalate" pays the maximum price (flagship
  model × `xhigh` × slowest provider path) on exactly the runs that are already
  slow and failure-adjacent. Rare × expensive is tolerable; the problem is the
  failure mode below.
- **Failure mode**: most repair failures are not "model too weak". The code paths
  that end a repair are: second conflict (genuinely hard merge — bigger model
  plausibly helps), `stale_conflict_checkpoint`, `stitch_timeout`/output caps,
  verification-gate failures, and missing declarations. Timeouts, caps, and
  missing gates do not improve with a bigger model; some get *worse* (slower time
  to first token under load, longer outputs hitting caps).
- **Blast radius of `@xhigh` everywhere**: the effort ladder couples rungs across
  aliases; hardcoding `xhigh` flagship usage into the finalizer adds unmeasured
  load to the exact providers/tiers most likely to be rate-limited when many
  agents repair at once (e.g., after a master push moves many checkouts).

### 2.4 The proposal under-specifies scope

"Requires another agent turn" covers two different turns with different stakes:
`conflict_repair` (has the full paused-operation context and a resume path) and
`declaration_recovery` (missing/stale declaration — a planning failure, not a
merge-semantics problem). Escalating declaration recovery to `@xlarge` buys
nothing: re-emitting a declaration is not a reasoning-hard task. The requirement
should name `conflict_repair` only.

## 3. Adjustments to the requirements (proposed)

1. **Scope to `conflict_repair`, not "any turn after a conflict".** Declaration
   recovery and continuation-bound failures stay on the agent's own model.
2. **Escalate effort first, model second, provider never (in v1).** Same provider,
   same model, `xhigh` effort (best-effort: providers that reject explicit effort
   must skip silently per `LLMInvocationOptions` semantics) is the default. A
   same-provider model step-up (provider's large-tier flagship) is opt-in config.
   No cross-provider re-resolution inside `run_finalizers`.
3. **Keep the one-shot budget.** Escalation must not buy extra repair turns: one
   boosted turn per repo, then `second_unresolved_conflict` as today. Otherwise a
   stronger model becomes an excuse to loosen the bound the
   `host-owned-completion` decision depends on.
4. **Make it observable and reversible.** Record the boosted model/effort in the
   conflict-repair operation record and `agent_meta.json` (the recorder already
   exists in `run_conflict_repair_turn`); gate behind
   `commit_finalizer.conflict_repair_boost` (`effort` | `model+effort` | `off`)
   so a rate-limit incident can be mitigated by config, not code revert.
5. **Measure before widening.** The repo already emits `commit_conflict_detected`
   metrics and repair outcome evidence (`conflict_repair: success`). Add repair
   success/failure by (provider, model, effort) and revisit only if same-model
   `xhigh` repair still fails at a meaningful rate.

## 4. Options considered

| Option | Mechanism | Verdict |
|---|---|---|
| A. Literal `@xlarge` switch in finalizer | Re-resolve alias mid-run, swap provider | Reject: architecturally hostile (§2.2), pays most, helps least reliably |
| B. Same model, `xhigh` effort for repair turn | Override `options.reasoning_effort` in `run_conflict_repair_turn` | Recommend as default: smallest diff, matches effort-ladder thesis |
| C. Same provider, flagship model + `xhigh` | `model_override = provider.resolve_model_name("large")` + `xhigh` for the repair call | Recommend as opt-in: helps `@small`/`@medium` agents most; no provider swap |
| D. Retry loop with escalating models | Multiple repair turns, bigger each time | Reject: violates one-shot budget; masks genuinely unresolvable merges |
| E. Human handoff instead of model escalation | Surface conflict to user, skip auto-repair | Reasonable fallback for repeated failures, not a replacement: auto-repair succeeds today for mechanical conflicts |

Why B/C beat A technically: `provider.invoke(prompt, model_tier=...,
model_override=..., options=...)` already threads all three knobs through
`invoke_with_instructions` to the bound provider. B sets `options` effort to
`xhigh` (explicit); C additionally sets `model_override` to the provider's
large-tier model. Both are ~10-line changes confined to
`commit_repair_conflict.py` plus config plumbing. A requires a provider
factory call, alias resolution, fallback handling, and delivery rebinding inside
the host-owned finalizer path — new failure modes in the least-tested,
highest-stakes code.

## 5. Recommended solution

1. Add `commit_finalizer.conflict_repair_boost` config: `effort` (default) |
   `model+effort` | `off`.
2. In `run_conflict_repair_turn`, when boost is enabled, invoke with
   `reasoning_effort=xhigh` (explicit); under `model+effort`, additionally
   resolve the provider's large-tier model for that one call. On provider
   rejection of explicit effort, fail open to the agent's own settings (existing
   `LLMInvocationOptions` contract).
3. Record boosted model/effort in the repair operation record and outcome
   evidence; add repair success/failure broken down by (provider, model, effort).
4. Explicitly do **not**: switch providers, add repair turns, escalate
   declaration recovery, or reference the `@xlarge` alias anywhere in the
   finalizer path (the alias remains a launch-time concept; reusing its name
   would promise fallback semantics the finalizer cannot honor).
5. After data: if `model+effort` repair still fails at a meaningful rate on
   genuine second-conflict cases, *then* consider a bounded cross-provider retry
   as a separate proposal with its own design — not as a silent property of
   "escalate".

## 6. Caveats

- I did not measure actual conflict frequency or repair success rates; the
  "rare" claim is inferred from the mechanism (requires a concurrent writer or
  leftover operation), not from metrics. The recommended instrumentation (§5.3)
  exists precisely to replace this inference.
- Cost comparisons are structural (`xlarge` = flagship × `xhigh`, the most
  expensive combination SASE ships) rather than priced per-token; exact
  cost/latency deltas need provider billing data.
- All code citations are from the current checkout; file paths may drift.
