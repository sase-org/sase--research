# SASE Monitors: Reliable Continuations with Less Replayed Context

Date: 2026-09-10. Consolidation of two independent reports and a third investigation.

**Decision:** keep the existing detached supervisor, but replace recursive transcript
replay with versioned continuation records containing exact parents and local deltas.
Render each monitor result once, select evidence by outcome, and later allow explicitly
authorized verification success to finish through the host without another model turn.
Ship this incrementally; neither a supervisor rewrite nor a new graph database is
necessary.

The dominant opportunity is removing duplicated history. Smaller tails and shorter
skills help, but cannot fix that representation. Provider sessions and caching deserve
experiments after the portable continuation path is correct.

## Evidence and confidence

The inputs were matched by dependency identity and existing suffix, verified against
artifact metadata, and read through their canonical research references:

| Dependency | Preserved report | Immutable snapshot |
| --- | --- | --- |
| `research.1r.cdx` | [Researcher A](monitor_continuation_design__a.md) | `file:explicit:83c801923385dc4d3670d150` |
| `research.1r.cld` | [Researcher B](monitor_continuation_design__b.md) | `file:explicit:1a600c07aa815f3a01ea020b` |

A contributes the strongest architectural analysis, operational workload measurements,
and cache-prefix investigation. B contributes a useful breakdown of duplicated output,
the existing transcript hooks, and an ambitious savings simulation. This investigation
checked their claims against SASE `3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1`
and sase-core `70df1267359f4a5e5edf01c70b1cb99aeb1b9d99`, ran synthetic reproductions,
and consulted current official provider documentation. Both original reports examined
SASE `f5a3f5c99`; the relevant failure mechanism remains in the inspected checkout.
No predecessor chat transcripts were read in this consolidation.

Historical measurements below are attributed to the original researchers, not claimed
as independently recounted telemetry. Their populations differ and must not be added
together.

| Finding | Evidence | Confidence and practical meaning |
| --- | --- | --- |
| History can grow geometrically | A's six-member lane grew from 5,458 to 342,488 transcript bytes; B found sixteen copies of the oldest monitor in one prompt | High: independently reproduced from current code |
| Monitors dominate the sampled saved prompts | B reports approximately 40 MB and 94% of sampled prompt bytes over four days | Directionally persuasive; not 94% of billed tokens or cost |
| Large potential savings | B simulates 40.27 MB → 5.33 MB, approximately 87% smaller | A combined scenario, not an implemented or quality-validated result |
| Verification is a major workload | A reports 376 `just check`/`just check-full` commands among 855 monitors, 44% | Supports a first-party verification result format and profile |
| Tail selection often misses test detail | B found pytest-style failure markers in 34 of 134 failed `just check*` tails | Useful warning, but does not measure diagnostic recall for lint, type, formatting, or infrastructure failures |
| Follow-up intent is substantial | A's 656 successor requests had a median next-action length of 1,494 characters | Some of this is necessary checkpoint information, not removable boilerplate |

B uses 340/40.1 MB in its opening table and 342/40.27 MB later. Treat those as an
approximately 340-run sample rather than a single exact accounting baseline. Its 87%
simulation removes history/evidence and replaces the newest tail with a 1.5 KB digest;
it does not isolate the benefit of the proposed first phase. Bytes divided by four are
rough estimates, particularly for Unicode and code. Saved prompts omit provider-added
instructions, tool definitions, subsequent tool traffic, and cache accounting.

## What actually needs to change

### 1. The main defect is recursive storage plus replay

Monitor follow-up composition selects the family as its fork target. Family rendering
loads each earlier member's transcript. Agent finalization and monitor handoff save
`state.current_prompt`, which already contains the expanded history. The next family
render therefore imports embedded ancestors again. The family renderer already shares
a visited set, but that cannot remove ancestry baked into text. See the inspected
[follow-up composer](https://github.com/sase-org/sase/blob/3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1/src/sase/monitor/followup_prompt.py),
[family renderer](https://github.com/sase-org/sase/blob/3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1/src/sase/history/chat_fork/family.py),
and [monitor handoff writer](https://github.com/sase-org/sase/blob/3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1/src/sase/axe/run_agent_exec_monitor.py).

For local delta `d_n` and recursively stored transcript `T_n`, the problematic shape
is `T_n ≈ d_n + sum(T_i for i < n)`. Even tiny deltas become expensive.

A synthetic family using the actual `build_fork_injected_history` and
`load_chat_for_resume` functions produced:

| Generation | Prompt characters | Copies of original question |
| --- | ---: | ---: |
| 0 | 11 | 1 |
| 1 | 1,542 | 1 |
| 2 | 3,304 | 2 |
| 3 | 6,828 | 4 |
| 4 | 13,876 | 8 |
| 5 | 27,972 | 16 |

Each turn added only `Question-i` and `Reply-i`, with temporary synthetic member
metadata. Absolute sizes include temporary-path headers; the doubling and repeated
question counts establish the mechanism independently of production transcript data.

### 2. The smaller proposed fix needs a stronger contract

B correctly notices the unused `previous_history=` serialization hook. A's description
of that hook is too broad: the current agent paths embed history in `prompt=` rather
than passing it separately. Moving it into the separate section can help, but is not
sufficient for reliable replay.

The current loader ordinarily parses `Prompt`/`Response` pairs. It consults the separate
previous-conversation region only in specific unresolved-reference fallbacks. A synthetic
file containing an ancestor constraint in `Previous Conversation`, followed by a new
prompt and reply without a fork directive, replayed only the new pair. Simply splitting
storage can therefore silently lose ancestors in direct forks and partial histories.
See [chat_resume.py](https://github.com/sase-org/sase/blob/3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1/src/sase/history/chat_resume.py).

Capture parent identities and the local prompt at expansion time; do not recover them
later by splitting arbitrary Markdown at `New Query`. Users and logs can contain those
headings. Existing transcripts also need an explicit, tested compatibility reader.

B's visited-set change likewise needs care: the current
[`test_multi_parent_expansion_preserves_shared_ancestry_per_parent`](https://github.com/sase-org/sase/blob/3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1/tests/history/test_chat_resume_refs.py)
intentionally repeats shared ancestry for each parent. Deduplicating that representation
is a behavior change requiring branch attribution, not merely fixing an accidentally
copied set. Ordinary monitor families can adopt unique-node replay first.

### 3. Output policy is currently applied too late

`--next-output none` suppresses the new prompt's tail, but the family source builder
independently reads the monitor log, and the proc renderer includes it. `file` has the
same limitation. This confirms B's observation: policy must govern the whole rendered
continuation, including family members and direct monitor references. The newest
result also appears both in history and in the follow-up body. See
[_fork_proc_sources.py](https://github.com/sase-org/sase/blob/3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1/src/sase/scripts/_fork_proc_sources.py)
and [chat_fork/proc.py](https://github.com/sase-org/sase/blob/3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1/src/sase/history/chat_fork/proc.py).

There is a second gap: raw output is not preserved indefinitely. The in-memory capture
keeps 2 MiB of head/tail; the durable log defaults to 2 MiB per segment and retains one
rotated segment. `--all-lines` returns retained output across those segments. It cannot
recover discarded bytes. Neither report's promise of fully recoverable evidence is
safe without a retention change. See
[monitor/logs.py](https://github.com/sase-org/sase/blob/3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1/src/sase/monitor/logs.py)
and [logs/_bounded.py](https://github.com/sase-org/sase/blob/3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1/src/sase/logs/_bounded.py).

### 4. Preserve the handoff's knowledge before shortening it

The monitor handoff writer creates a synthetic assistant response from the command,
reason, monitor identity, and next action. This is not a complete account of the
starter's analysis or tool results. Long `--next` text can be the only portable record
of discoveries and unfinished decisions.

Therefore add a compact, explicit checkpoint before teaching agents to shorten
handoffs. Host-collected facts can include changed paths, worktree identity, artifact
reads, and completed checks. The agent supplies unresolved intent and conclusions that
cannot be derived from filesystem state. Store the next action once and reference it
from handoff views. Do not impose a tiny universal character limit.

## Recommended design

### A portable continuation record on the existing artifact substrate

Adopt A's exact-parent/delta model with B's incremental delivery strategy. Reuse existing
artifact identities, family parent timestamps, and shell metadata. Add a small versioned
record; a graph is the relationship between records, not a requirement for another
database or workflow service.

Illustrative schema, not a new CLI contract:

```json
{
  "version": 1,
  "id": "immutable-run-or-result-id",
  "parents": ["exact-predecessor-id"],
  "kind": "agent_delta|monitor_result|checkpoint",
  "content_ref": "durable-reference",
  "continuation_intent_ref": "durable-reference",
  "workspace_snapshot_ref": "durable-reference"
}
```

Agent deltas contain the local query and response/checkpoint, excluding injected
ancestry. A monitor result is frozen at terminal settlement; mutable progress and
later delivery attempts remain separate operational state. Freeze the exact predecessor
at launch and its terminal content when it settles. A family name remains a navigation
alias, not a mutable parent edge.

Use Rust for schema validation, ancestry traversal, identity-based deduplication,
evidence selection, outcome policies, and budget decisions. Python handles filesystem
and process effects, provider invocation, and presentation through thin bindings. The
current Rust core supplies family-resolution and bounded-text primitives, but no general
continuation replay model was found. See
[agent_family.rs](https://github.com/sase-org/sase-core/blob/70df1267359f4a5e5edf01c70b1cb99aeb1b9d99/crates/sase_core/src/agent_family.rs)
and [text_tail.rs](https://github.com/sase-org/sase-core/blob/70df1267359f4a5e5edf01c70b1cb99aeb1b9d99/crates/sase_core/src/text_tail.rs).

For new serial histories, emit each reachable delta once in stable order. At merges,
preserve explicit branch attribution and the already-rendered primary lineage, appending
unseen nodes from additional parents. A fresh global topological sort can reorder old
content when another branch becomes reachable; deterministic sorting alone does not
guarantee a stable prefix. Avoid changing headings such as `Member i of N` inside the
replayed prefix.

New canonical storage must contain deltas, not a full inherited snapshot in another
field. A separately identified prompt archive can support debugging, but must never be
fed back into ancestry expansion. Legacy artifacts stay immutable. Normalize only
recognized structures with recoverable provenance; label uncertain legacy content and
apply the budget rather than guessing. Deduplicate by event identity, not text equality:
two distinct runs producing the same output are still distinct observations.

### One monitor result, with three evidence layers

Separate host-observed facts from command-authored claims:

| Layer | Contents | Default use |
| --- | --- | --- |
| Execution facts | Outcome, exit code, elapsed time, timeout kind, command, workspace identity, result ID | Always included |
| Diagnostic summary | Failed stage, bounded diagnostics, counts, producer/version, retained ranges | Outcome-selected; command content remains untrusted |
| Evidence | Logs, structured test/lint reports, original checkpoint and source artifacts | Retrieved when needed |

The supervisor owns outcome and exit status. A result file must not be able to claim
success, select a model, or authorize finalization. Validate field sizes and paths,
preserve disabled/fenced rendering, and distinguish execution failure from malformed
summary data.

Add `auto` to the existing output policy instead of immediately replacing the whole
option family with `--next-digest`. Retain explicit `tail`, `file`, and `none` controls.
Apply the policy in one shared place for every history and successor projection.

| Outcome | Suggested `auto` evidence |
| --- | --- |
| Completed | Exit and timing facts, concise result summary and references; no raw log by default |
| Failed | Failed-stage diagnostics and a small fallback excerpt when needed |
| Timeout | Timeout kind, last observed progress, relevant diagnostics and bounded tail |
| Stopped/lost | Reason and recovery evidence; preserve today's no-successor default |

Older monitor results retain compact facts and references rather than repeated raw
excerpts. Do not collapse human gate decisions as though they were expendable logs:
the selected branch and reviewer's instructions must remain available as decisions.

Prefer structured results from first-party producers. `tools/run_silent` already knows
the stage name and exit status before deleting its temporary capture. Extend that path
to preserve a stage-result record and diagnostic artifact; use native test/lint reports
where available. Lightweight text extractors are a useful fallback, not a universal
truth source. The [current wrapper](https://github.com/sase-org/sase/blob/3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1/tools/run_silent)
and [verification recipes](https://github.com/sase-org/sase/blob/3260f6a42b5f6ae22a5cab4473aacd7c6e2ebac1/Justfile)
also show why diagnostics must identify the failed stage, rather than assume every
nonzero check result contains a pytest summary.

Capture structured diagnostic evidence before log rotation can discard it. For raw
logs, choose an explicit quota and retention policy, optionally using compressed
artifact chunks. Record completeness, dropped-byte counts, and retained ranges; describe
retrieval as retained output when completeness is false. Preserve referenced failure
artifacts through the continuation's useful lifetime. Full-output retention is an
optional resource policy, not an implicit promise of `--all-lines`.

Provide bounded diagnostic, tail, and range retrieval. This limits the tool traffic
that could otherwise erase the savings from shorter initial prompts. Digest quality
should be evaluated separately for tests, type errors, lint, process failures, and
timeouts. Neither 100% diagnostic recall nor an 85% reduction is established today.

### Outcome branches and fewer model wake-ups

Keep `--next` as the shared continuation default. Add explicit per-outcome actions and
model selection through a coherent policy/profile rather than a large set of required
flags. Success does not imply that reasoning is unnecessary: a successful benchmark or
research command may produce the task's most important new information.

For a verification profile, allow:

- Success: invoke an already-prepared host completion action.
- Failure: launch an inherited capable model to diagnose and repair.
- Timeout: launch the designated recovery action with timeout evidence.
- Stopped/lost: preserve cancellation semantics and expose recovery explicitly.

The no-model success path is valuable but needs more than an `action: finalize` string.
Today's monitor handoff is exempt from normal final declaration. The host must receive
a prepared, conditional completion intent before handoff, including required repository
decisions and user-facing result text. At completion it validates the tested worktree
fingerprint and all finalizer obligations against current state. If the monitored
command changed tracked files, the workspace changed, declarations became stale, or a
required decision is absent, route to review/recovery. Never interpret exit zero as
permission to commit or publish arbitrary current state.

Use a durable delivery identity, such as `(monitor_id, terminal_result_id, branch)`,
so reconciliation or a supervisor restart cannot launch duplicate successors or apply
completion twice. Persist terminal evidence and the pending action before dispatch,
then record acknowledgment. Preserve existing claim transfer and launch barriers; do
not release a workspace before its continuation or host finalizer has taken ownership.

For waits, reduce *wake-up count* as well as prompt size. Prefer one supervised command
that waits until the external job reaches a terminal condition, with bounded backoff,
over repeated `sleep → agent checks status → sleep` cycles. This fits the current
single-turn model. Add named wait adapters only where recurring workloads justify them.

### Budgets before launch; acceleration after correctness

Preflight the fully expanded SASE prompt and reserve space for provider instructions,
tools, output, and reasoning. Enforce both transport-size and context limits. For CLI
providers whose complete request is hidden, use a conservative reserve and record the
uncertainty; a SASE-only character estimate is not a hard guarantee about total tokens.

First remove duplicate nodes and suppress old diagnostic excerpts. Then retain the
active objective, constraints, unresolved decisions, latest result, and recent deltas.
Compact older material into a checkpoint only when necessary. Store source references
and omissions; if essential context cannot fit, record an actionable nonlaunchable
reason instead of silently clipping instructions. Checkpointing should not require an
extra LLM call after every monitor.

Delta normalization gives linear growth per request, but replaying every unique turn
across a long chain still gives quadratic aggregate input. Budgeted checkpoints and
avoiding unnecessary successor turns address that remaining term.

Provider reuse is an optimization, not the durable source of truth:

| Mechanism | Verified conclusion |
| --- | --- |
| Codex session continuation | `codex exec resume <SESSION_ID>` is supported. SASE currently invokes fresh `exec` and contains a stale comment denying persistence. [Official documentation](https://learn.chatgpt.com/docs/non-interactive-mode#resume-a-non-interactive-session) |
| Claude session continuation | `--resume` with `--fork-session` creates a separate session from prior state. SASE currently creates a fresh UUID. [Official documentation](https://code.claude.com/docs/en/cli-reference) |
| OpenAI conversation IDs | Earlier input in a `previous_response_id` chain is still billed; smaller transport is not free history. [Official documentation](https://developers.openai.com/api/docs/guides/conversation-state) |
| Prompt caching | Requires matching rendered prefixes and eligible cache boundaries. Appending to one giant user message may lose reuse of an earlier endpoint; message structure matters. [Official documentation](https://developers.openai.com/api/docs/guides/prompt-caching) |

Session reuse may preserve useful tool results, but also carries more historical tokens
and stale workspace context. Test recovery after the starter is deliberately terminated,
session flush/persistence, same-provider model changes, unavailable sessions, and
workspace relocation. Always retain a portable fallback; never select a session with
`--last` in concurrent SASE workspaces.

Do not assume CLI adapters expose every API caching control. OpenAI currently documents
model-specific breakpoints and TTL behavior, including a 30-minute minimum TTL for
GPT-5.6 and later. Cache strategy must be measured through the actual provider path,
including cache-write charges. A stable SASE prefix is necessary, not sufficient.
[OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)

Anthropic documents a default five-minute TTL and a more expensive one-hour option;
the lifetime begins at the request's start, not after generation. A's median monitor
duration of 302 seconds therefore understates the total gap between cache use and
successor invocation. Select TTLs from actual usage and expected reuse, rather than
always paying for the longest duration.
[Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

## Implementation order and decision gates

| Stage | Deliverable | Evidence needed to proceed |
| --- | --- | --- |
| 1. Baseline and containment | Measure rendered components; add preflight budgeting; reproduce nesting and split-only ancestry loss | Reproducible fixtures, visible oversize behavior, no silent constraint loss |
| 2. Correct continuation storage | Versioned delta/parent records in Rust and bindings; serial monitor integration; legacy reader; compact handoff checkpoint | Each source once; direct forks preserve ancestors; immutable parent selection; old artifacts still readable |
| 3. Useful result delivery | One typed result, end-to-end output policy, first-party verification summaries, retention metadata and bounded retrieval | `none` produces no raw log anywhere; failure evidence remains actionable across failure classes |
| 4. Outcome policies | Branch-specific actions/models; prepared host finalization on eligible success; durable dispatch identity | Restart/reconciliation and changed-tree tests; no duplicate action or premature claim release |
| 5. Further efficiency | Thresholded compaction, concise skill/profile interface, provider-session/cache experiments | Lower total task cost and latency without worse completion or recovery quality |

Keep the existing supervisor's timeout, process-group termination, startup acknowledgment,
claim transfer, stopped/lost behavior, and workspace-degradation tests passing throughout.
The first rollout can target serial monitor continuations while explicitly preserving
legacy multi-parent fork semantics. Extend deduplicated graph rendering to other shell
types after attribution and compatibility are covered; it need not block the monitor fix.

Compatibility changes and unfinished exposed behavior must follow SASE's feature-flag
rules; permanent evidence and profile choices belong in ordinary configuration. CLI
work needs complete help, short aliases for public long options, optional controls,
and synchronized defaults. Shorten the generated monitor skill from its source template,
fix the canonical example to use the documented command form after `--`, preview the
render, and deploy only from a landed source revision. These are implementation
requirements, not changes performed by this research.

Measure each intervention separately: normalization, evidence projection, structured
diagnostics, branching, compaction, and provider reuse. Capture actual uncached input,
cache writes/reads, output and reasoning usage where available, plus log retrievals,
follow-up count, elapsed time, and task completion. Report results by outcome, chain
depth, provider, command type, and cold/warm cache. The success metric is cost per
correctly completed task, not the smallest first prompt.

Acceptance should include:

- A 100-turn synthetic chain grows with unique content; exact IDs appear once.
- Direct, family, multi-parent, missing-parent, failed-starter, and legacy nested
  histories preserve constraints and branch identity without invented ancestry.
- Adding an ordinary serial continuation preserves prior canonical blocks; checkpoint
  creation or deliberate projection changes are visible cache-boundary resets.
- The newest monitor result appears once; no historical path bypasses output policy.
- Structured diagnostics survive raw-log rotation, and incomplete evidence is labeled.
- Adversarial headings, fences, directives, Unicode, and malformed result files cannot
  alter routing or execution facts.
- All terminal outcomes, starter termination, workspace recovery, stale finalization
  intents, and crash-after-dispatch cases have defined recovery behavior.
- A representative shadow-render and task evaluation shows savings without increasing
  missed failures, unnecessary reruns, or unresolved finalizer obligations.

## Recommended solution

Implement **a small, portable continuation contract with exact parents, delta-only
storage, and one outcome-aware monitor result** on SASE's existing artifact and shell
infrastructure. Put shared semantics in Rust and keep the hardened process supervisor.

Deliver normalization and ancestry correctness first, followed by structured verification
evidence and retention guarantees. Then add explicit outcome branches, with a host-owned
no-model success path only when completion was prepared and the verified worktree still
matches. Shorten handoffs after checkpoints preserve their knowledge, and evaluate
provider sessions and caching against that corrected baseline.

This takes A's durable architectural direction while retaining B's practical incremental
approach. It removes the demonstrated geometric cost, improves the evidence delivered
to the successor, and creates a path to eliminating model turns whose remaining work
is deterministic. The reported 87% reduction is a promising experiment target, not a
savings promise or a reason to skip correctness evaluation.
