# SASE Monitor Continuations: Eliminating Exponential Context Growth

**Researcher:** A  
**Date:** 2026-09-10  
**Scope:** SASE monitor architecture, continuation correctness, token efficiency, operator ergonomics, and a recommended implementation strategy

## Executive summary

The largest monitor-token problem is not the 200-line output tail. It is the way a monitor follow-up resumes its agent family.

Today a successful monitor follow-up is composed as a new prompt beginning with `#fork:<family>`. Resolving that reference enumerates the family's earlier agents and monitor shells. Each prior agent transcript can already contain an expanded copy of its own earlier conversation. The new family fork embeds those transcripts again, and the resulting prompt is then saved inside the next transcript as `Previous Conversation`. Repeating this cycle produces recursive duplication.

This is observable in real SASE history. One five-continuation lane grew through 5,458, 16,097, 40,549, 84,565, 170,830, and 342,488 bytes. Its fifth continuation contained sixteen `Previous Conversation` regions and sixteen `New Query` headings. The fourth and fifth rendered prompts shared only 897 leading characters—0.27% of the later prompt—so the representation also defeats prefix caching. A prior production incident generated a 1,913,445-character follow-up and was rejected against a 1,048,576-character provider limit.[^1]

The best solution is a staged **Continuation Capsule** redesign:

1. Represent continuation history as an immutable, deduplicated DAG of exact parent node IDs. Persist only each agent's new query/response delta, never a newly expanded copy of all ancestors.
2. Render a stable, append-only provider prefix from that DAG. Old content must remain byte-for-byte stable as new nodes are appended.
3. Record a monitor as a typed `MonitorResult` event and inject it exactly once, together with a compact next-action/branch policy. Raw logs remain durable and on demand.
4. Make `auto` output outcome-aware: no raw tail on ordinary success; a small failure-focused excerpt on failure or timeout; command-authored structured summaries when available.
5. Allow explicit outcome branches so verification success can finalize without another expensive model call, while failure can launch a capable diagnostic agent.
6. Only after the representation is stable, exploit provider prompt caching and compaction. Native provider threads are an optimization, not SASE's source of truth.

This attacks the dominant exponential term, restores caching, reduces routine log tokens, and makes monitor continuations auditable and portable without discarding the mature monitor supervisor.

## Research method and limitations

I independently examined:

- the current monitor, shell-follow-up, chat-storage, and family-fork implementations at SASE commit `f5a3f5c99ec7c55a44ff0517c7eea820f0b46c3c`;
- the Rust core's present family-resolution and bounded-text primitives;
- all 855 locally recorded monitor records available on 2026-09-10;
- selected historical continuation families, using SASE's chat interfaces rather than reading another researcher's output;
- two audited earlier implementation plans covering monitor hardening and a concrete oversized-fork incident;
- current official OpenAI, Anthropic, and GitHub Actions documentation.

Local corpus measurements describe one installation and its workload, not the universal distribution of SASE usage. Character-to-token conversions use SASE's rough four-characters-per-token estimate; actual tokenization varies by model and content. Failure outcomes in the monitor corpus often mean a test command correctly found a defect, not that the monitor infrastructure malfunctioned.

## What a monitor does today

A monitor is already built on a sound high-level lifecycle: it starts a durable proc-shell member in the current agent family, supervises a background process, records its output and terminal state, settles the starter, and optionally launches a new single-turn agent. Earlier hardening work added bounded streaming capture, byte-safe chunking, process-exit handling independent of pipe EOF, timeout and kill escalation, PID/boot identity, claim barriers, settlement, reconciliation, idle timeout, and follow-up workspace recovery.[^2]

The current implementation has several token-oriented safeguards:

- in-memory output retention is capped at 2 MiB, split between the head and tail;
- the output embedded in a follow-up is separately capped at 12,000 Unicode characters;
- `--next-output` can select `tail`, `file`, or `none`;
- command output is fenced and explicitly labeled untrusted;
- a monitor can select a different follow-up model.

Those are useful defenses, but they bound only one component of the prompt. The current default remains `tail` with 200 lines. More importantly, the follow-up's routing prefix selects the durable family when a family name is available. Family rendering then loads every prior agent transcript and formats every monitor/proc member. The follow-up body independently repeats the newest monitor's command, outcome, timings, reason, output pointer, and—by default—its tail. Thus the latest monitor evidence can appear twice: once as a family member and once in the new monitor-finished prompt.[^3]

### The storage/rendering loop

The problematic sequence is:

```text
agent A transcript (delta A)
        │
        ▼
monitor M1 terminal event
        │  #fork:<family> expands A + M1
        ▼
agent B transcript stores [expanded A + M1] + delta B
        │
        ▼
monitor M2 terminal event
        │  #fork:<family> expands A + M1 + all of B + M2
        ▼
agent C transcript stores the expanded result again
```

The transcript serializer has an explicit `previous_history` field and writes its complete text into a `Previous Conversation` section before the new prompt and response. Family rendering subsequently loads the complete serialized transcript for every agent member.[^3]

If `d_i` is member `i`'s unique conversational delta and `T_i` is its stored transcript, the current family pattern approaches:

```text
T_n ≈ d_n + Σ T_i for all earlier family agents
```

When every `T_i` already contains earlier `T_j`, aggregate stored and rendered history grows exponentially in continuation depth. Bounding monitor output does not change that recurrence.

## Empirical findings

### Monitor workload

The local corpus contains 855 monitor records across 543 family lanes. Of these, 656 (76.7%) requested a successor agent and 199 were fire-and-forget. There were 142 lanes with more than one monitor; the busiest contained ten.

| Measure | Observation |
| --- | ---: |
| Total monitors | 855 |
| Monitors with a next action | 656 |
| Stored output mode `tail` / `file` / `none` | 807 / 34 / 14 |
| Stored tail length of 200 lines | 807 |
| Follow-ups launched normally | 616 |
| Follow-ups launched degraded | 10 |
| Follow-ups not launchable | 6 |
| Legacy/unrecorded follow-up outcome | 24 |
| Explicit follow-up model | 52 of 656 (7.9%) |
| Next-action length, median / mean / p90 / p99 | 1,494 / 1,757 / 3,268 / 6,913 chars |
| Next actions over 2,000 / 4,000 / 8,000 chars | 213 / 41 / 4 |
| Elapsed duration, median / p90 / p99 | 302 s / 1,980 s / 5,586 s |

The most common commands were `just check-full` (242) and `just check` (134), together accounting for 44.0% of all records. That matters because verification has a particularly asymmetric continuation policy: success often requires only finalization or a concise notification, whereas failure may require a capable diagnostic agent.

The stored states were 495 failed, 313 completed, 35 timed out, nine stopped, two lost, and one still running. Again, a `failed` command is normally useful monitor output, not a supervisor defect. Among records with a next action, 130 completed successfully while 515 failed or timed out. A single unconditional successor/model policy therefore handles materially different branches.

The initiating agents also use `--next` as a manual checkpoint. Mean next-action length rose from 1,655 characters in August to 2,282 characters in September, about 38%. Long handoffs may be rational compensation for unreliable or bloated inherited context, but they add another repeated token source.[^4]

### Direct evidence of recursive duplication

For one ordinary lane, persisted transcript sizes progressed as follows:

| Agent member | Transcript bytes | Approximate multiplier vs previous |
| --- | ---: | ---: |
| `016--0` | 5,458 | — |
| `016--1` | 16,097 | 2.95× |
| `016--2` | 40,549 | 2.52× |
| `016--3` | 84,565 | 2.09× |
| `016--4` | 170,830 | 2.02× |
| `016--5` | 342,488 | 2.00× |

The final member contained sixteen copies each of the `Previous Conversation` and `New Query` headings. Its rendered prompt was 335,286 characters (roughly 83,800 tokens), up from 163,370 characters in the preceding member. Only 897 characters at the start were identical between those two prompts.

Two other current examples show the cost of resolving a mutable family rather than an exact immutable parent. Expanding `#fork:sase-yz.2` produced 812,394 bytes, while the selected starter transcript alone was 86,142 bytes. Expanding `#fork:sase-z3.3` produced 468,194 bytes versus 237,972 bytes for its exact starter. Exact-parent loading is not sufficient as a final design because the exact transcript can itself contain expanded ancestry, but these ratios show that dynamic family enumeration compounds the problem.[^5]

The failure mode is not theoretical. The audited September fork-context incident recorded a monitor follow-up of 1,913,445 characters, of which 1,889,378 were inherited history. The provider rejected it because it exceeded a 1,048,576-character input limit. That incident fixed family identity classification and added a 12,000-character output-tail bound; it did not promise that arbitrary conversation histories would fit.[^1]

### Why provider caching currently helps little

OpenAI prompt caching works on an exact repeated prefix and recommends placing stable content first while appending variable content later. Cached input can be substantially cheaper and faster, but only the matching prefix qualifies.[^6] Anthropic follows the same basic principle: cache hits use the longest previously cached prefix, with a five-minute default TTL and an optional one-hour TTL at a higher write cost.[^7]

SASE's current renderer changes early text such as `Members shown: x of N`, `Member i of N`, source counts, and surrounding merged-history headers whenever a family grows. It also recursively injects histories that were laid out differently in earlier requests. The measured 0.27% common prefix is therefore the predictable result, not an outlier.

This matters especially for monitors: the median command runs for about 302 seconds, almost exactly Anthropic's default five-minute TTL, while p90 is 33 minutes. Even an otherwise cacheable prefix will often cross the default TTL between starter and successor. A one-hour cache may be worthwhile for predicted long monitors, but only after SASE creates a stable prefix. Paying a higher cache-write cost for a prompt that changes at its beginning would accomplish little.[^7]

## Requirements for a better design

A good replacement should satisfy all of the following:

1. **Linear unique history.** Each user/assistant delta and shell result appears at most once in a rendered continuation.
2. **Immutable ancestry.** A continuation records exact parent node identities at launch. Resolving the same continuation later must not silently acquire newer family members.
3. **Stable prefix.** Adding a node appends content; it does not renumber, rewrite, or rewrap prior content.
4. **Auditable degradation.** If context must be compacted, the successor can see what was summarized or omitted and can retrieve the durable sources.
5. **Provider portability.** SASE history remains usable across OpenAI, Anthropic, local, and future providers.
6. **Outcome-aware evidence.** A routine zero exit does not inject 200 raw lines merely because a failure would have needed diagnostics.
7. **Outcome-aware compute.** Success, failure, timeout, stopped, and lost outcomes may select different actions and models—or no model at all.
8. **Untrusted-output safety.** Logs and command-authored summaries remain data, are bounded, and cannot activate xprompt directives.
9. **Supervisor continuity.** Existing hard-won process, claim, timeout, log, reconciliation, and workspace guarantees remain intact.
10. **Preflight guarantees.** SASE knows the rendered size before launch and never knowingly sends an oversized request.

## Options considered

| Option | Benefit | Why it is insufficient or risky |
| --- | --- | --- |
| Change the default from 200 tail lines to `none` | Small, immediate token reduction | Does not affect recursively duplicated conversation history or long handoffs; may hide the only useful failure clue. |
| Always use `file` and let the successor inspect logs | Avoids eager log tokens | Adds tool latency and still leaves exponential history; agents may read far more than a bounded diagnostic excerpt. |
| Resume only the exact starter transcript | Avoids mutable family enumeration | The starter transcript may already contain all expanded ancestors. It reduces one multiplier but preserves recursive storage. |
| Use provider conversation/session IDs | Reduces transport and client reconstruction | OpenAI's `previous_response_id` still bills earlier input tokens; provider state is not portable or a sufficient durable audit record.[^8] |
| Rely on prompt caching | Can sharply discount stable repeated input | Current prefixes are unstable; caching reduces price/latency, not context-window occupancy or context-quality degradation.[^6][^9] |
| Summarize with an LLM after every monitor | Bounds old context | Adds a model call to every monitor, introduces nondeterministic loss, and can summarize poisoned logs. Useful only as a thresholded compaction layer. |
| Replace supervision with systemd or a workflow engine | Could add generic scheduling features | Does not solve conversation representation and would discard mature SASE-specific settlement, family, claim, and follow-up behavior. |
| DAG-normalized deltas + typed continuation capsules | Eliminates recursive duplication, enables caching, supports bounded evidence and branches | Cross-cuts chat persistence and fork rendering and therefore requires a careful compatibility reader and staged rollout. |

The final option is the only one that removes the dominant term rather than trimming around it.

## Proposed architecture: continuation events, not fabricated chat history

### 1. A durable continuation DAG in the Rust core

Every agent, monitor, proc, and gate becomes an immutable continuation node. A node stores exact parent IDs and only its own new content or a durable reference to it.

```rust
struct ContinuationNodeWire {
    schema_version: u32,
    node_id: String,                 // immutable artifact identity
    kind: ContinuationKind,          // agent | monitor | proc | gate | checkpoint
    parents: Vec<ContinuationEdge>,  // exact node IDs, never a mutable family name
    delta_ref: Option<String>,       // this agent's query/response only
    result_ref: Option<String>,      // typed shell result, if applicable
    created_at: String,
}
```

The shared Rust core should own schema validation, graph traversal, cycle detection, deterministic topological ordering, ancestor deduplication, budget selection, and a wire response describing what was included. This is shared backend behavior: CLI, TUI, editor integrations, and future web clients must agree. The current Rust core already contains deterministic family-resolution wires and Unicode-safe line/character tailing, but no general continuation graph or compaction primitive.[^10]

Python remains responsible for provider adapters, monitor-supervisor integration, and presentation. It should not independently reimplement graph traversal.

A family name remains a useful live navigation label. It must stop being the persisted meaning of a continuation edge. At monitor start, SASE knows the starter artifact timestamp and monitor artifact identity; those exact IDs should be written as edges. A later family member cannot retroactively become an ancestor.

### 2. Delta-only transcript persistence

New agent transcript artifacts should preserve:

- the model-visible new query after control directives are removed but before ancestry is textually inserted;
- the assistant response;
- exact parent node IDs;
- optional provider request/response IDs as hints;
- a separately retained rendered-prompt archive when deep debugging requires it.

They should not save the expanded ancestry inside the ordinary transcript. This converts a continuation chain from recursive snapshots into event sourcing: the graph is the history; each node is a delta.

Old artifacts must stay immutable. The compatibility reader can normalize legacy family histories without rewriting them:

- when every member of a legacy family is available, extract only the outermost prompt/response delta from each member and discard embedded `Previous Conversation` copies during rendering;
- when only an isolated old transcript is resolvable, use its embedded history as a fallback, mark the node `legacy_expanded`, and apply deduplication where provenance is recoverable;
- emit inclusion and omission metadata so operators can diagnose imperfect legacy reconstruction.

This compatibility path should be tested against the known exponential lane and the prior 1.9-million-character artifact.

### 3. Stable append-only rendering

The renderer should output canonical message items in topological order. Once node A has been rendered, adding B or C must append new bytes after A rather than changing A's heading or position.

Avoid prefix text containing total counts, `i of N`, current-family summaries, or timestamps that change on every render. Put changing diagnostics at the end or outside the model input. A small immutable node header can include the node ID and kind, but its bytes must never change.

The renderer should return both messages and diagnostics:

```rust
struct RenderedContinuationWire {
    messages: Vec<ContinuationMessageWire>,
    included_node_ids: Vec<String>,
    omitted_node_ids: Vec<String>,
    estimated_chars: u64,
    estimated_tokens: u64,
    unique_delta_chars: u64,
    duplication_ratio: f64,
    stable_prefix_digest: String,
    needs_compaction: bool,
}
```

The essential invariant is `duplication_ratio ≈ 1.0` for new histories. A diamond-shaped merge should include its shared ancestor once. A 100-node linear chain should grow with the sum of deltas, not with continuation depth squared or exponentially.

This normalization removes exponential per-request growth. Without compaction, billed history still grows linearly per request and total spend across a very long sequence is quadratic in the number of turns. That is why normalization is necessary but not the final token optimization.

### 4. A typed MonitorResult event

A monitor completion should enter the graph once as structured evidence:

```json
{
  "schema_version": 1,
  "monitor_id": "...",
  "outcome": "completed|failed|timeout|stopped|lost",
  "exit_code": 0,
  "started_at": "...",
  "finished_at": "...",
  "elapsed_seconds": 301.6,
  "timeout_kind": null,
  "command": "just check-full",
  "cwd": "...",
  "summary": "all required checks passed",
  "diagnostics": [],
  "log_ref": "...",
  "total_bytes": 48123,
  "retained_output_truncated": false,
  "trust": "untrusted_command_result"
}
```

The successor prompt should render this event once. The separate prose table currently created by `compose_followup_prompt` should become a view over the event rather than a second copy of metadata and output already present in the family fork.

The raw log remains the source artifact. The capsule contains a reference, digest, sizes, and a bounded summary/diagnostic projection. This follows a useful precedent from CI systems: GitHub Actions separates raw logs from annotations and a concise step summary so users can understand a result without scanning the full stream.[^11]

### 5. Outcome-aware `auto` evidence

Add `auto` as the default successor-output policy:

- **completed:** include exit/timing metadata and a command-authored summary, but no raw tail by default;
- **failed:** include structured diagnostics plus a fallback tail bounded by both lines and characters (for example, 80 lines and 8 KiB);
- **timeout:** include timeout kind, last-output time, and a smaller tail showing where progress stopped;
- **stopped/lost:** include the termination/reconciliation reason and only the evidence needed to decide recovery;
- **all outcomes:** include a durable log reference and an explicit retrieval command.

Allow the command to write bounded JSON to a path supplied in `SASE_MONITOR_RESULT_PATH`. The schema can carry `summary`, `diagnostics`, `annotations`, and useful output artifact references. First-party adapters can translate `just`, JUnit, and SARIF outputs. Arbitrary commands fall back to exit state plus a bounded tail. Never make regex parsing of free-form logs the primary truth source.

Retain explicit `tail`, `file`, and `none` for unusual workloads. Treat summary strings, diagnostics, file paths, and logs as untrusted content; cap field counts and sizes, validate paths, and keep them in disabled/fenced regions.

### 6. Outcome-specific continuation policy

Replace the single `next_action`/`next_model` pair with declarative branches:

```yaml
on:
  completed:
    action: finalize
  failed:
    action: launch_agent
    model: inherit
    prompt: repair the reported failures, rerun the focused checks, then finish
  timeout:
    action: launch_agent
    model: inherit
    prompt: diagnose the stall from the result and log reference
```

Possible actions should initially be small and explicit: `launch_agent`, `notify`, `finalize`, and `none`. A deterministic `finalize` transition is the high-leverage creative change for verification: a successful read-only `just check` need not awaken a second full-strength model merely to say it passed. Host-owned completion remains responsible for actual finalization; the monitor records the event and requests the host transition rather than creating commits or pretending an agent turn continued.

Branching must be author-controlled. SASE should not silently downgrade a model just because a command exited zero; some successful commands produce new data requiring hard reasoning. A `verify` profile, however, can safely expose concise defaults and let the initiating agent explicitly select them:

```text
sase monitor verify \
  --timeout 90m \
  --on-success finalize \
  --on-failure "repair failures, rerun focused checks, then finish" \
  --failure-model inherit \
  -- just check-full
```

Other profiles such as `wait`, `deploy`, and `benchmark` can choose sensible status labels, timeouts, idle-timeout behavior, evidence policy, and branch options. Profiles should be normal long-lived configuration, not hidden heuristics.

### 7. Budgeted checkpoints and compaction

Once histories are normalized, add a hard context budget with three tiers:

1. system/project instructions, active user objective, safety constraints, unresolved decisions, and the newest shell result;
2. the most recent full deltas that fit;
3. an auditable checkpoint summarizing older nodes, with exact source node IDs and retrieval references.

Compaction should occur only when the preflight renderer predicts a threshold breach, not after every monitor. Prefer a checkpoint authored from trusted conversation state; do not feed raw command output to a summarizer as instructions. Store the checkpoint as another immutable graph node and retain all original nodes.

OpenAI's compaction endpoint can reduce context while carrying forward opaque provider state, and Anthropic offers context editing/compaction facilities. These are valuable adapter-level accelerators, but a provider-specific opaque item cannot be the only durable SASE representation.[^9][^12] SASE should be able to switch providers or reconstruct an audit trail from its graph.

Similarly, OpenAI Conversations or `previous_response_id` can simplify transport, but the documentation explicitly states that earlier input tokens in the chain are still billed. Native threads therefore do not replace context budgeting.[^8]

### 8. Cache-aware provider adapters

After append-only rendering is established:

- record provider-reported cached and uncached input tokens;
- place stable project/system instructions and immutable ancestry before the newest result/action;
- use a prefix digest to detect accidental renderer churn;
- add Anthropic cache breakpoints at stable ancestry boundaries;
- consider the one-hour Anthropic TTL when expected monitor duration exceeds the five-minute default, balancing the higher write cost;
- allow OpenAI automatic prompt caching to reuse the unchanged prefix;
- keep provider response/conversation IDs as disposable acceleration hints attached to graph nodes.

Provider caching can then reduce repeated-input cost substantially. It still does not reduce the model's occupied context or cure context rot, so it comes after graph normalization and before—not instead of—compaction.[^6][^9]

## Token-efficiency opportunities beyond the main fix

### Shrink the initiating skill and CLI ceremony

The generated monitor skill currently occupies roughly 8,000 characters, around 2,000 tokens by the project's estimator, and agents must read it whenever they use the skill. Much of that text describes mandatory flag choreography and edge cases.

A profile-driven CLI can infer project, lane, cwd, common status labels, safe output policy, and routine reason text. Keep the generated skill as a short contract with two or three examples; move deep recovery material to command help and a reference document loaded only on demand. This saves tokens before the monitor even starts and reduces malformed invocations.

### Make next actions deltas, not mini-transcripts

The median next action is already about 1,500 characters, and one third exceed 2,000. Once graph continuity is reliable, guidance should explicitly tell agents not to restate the entire task, earlier decisions, or files changed. The capsule needs only unresolved work, branch-specific intent, and any fact not already represented in the graph.

SASE can show an estimated next-action token count and warn when a handoff repeats recognizable prior text. It should not impose an overly small hard cap: a genuinely complex continuation may need detail.

### Avoid eager log reads after launch

The successor should first reason from `MonitorResult`. Only if the summary/diagnostics are inadequate should it retrieve a bounded range or search the full log. Provide commands for `errors`, `tail`, and byte/line ranges instead of only `--all-lines`. This keeps the default cheap without sacrificing access.

## Implementation sequence

### Phase 0 — instrument and lock in regression fixtures

Add metrics before behavior changes:

- rendered characters and estimated tokens;
- unique-delta characters and duplication ratio;
- number of reachable/included/omitted nodes;
- stable-prefix digest and common-prefix length with the parent request;
- monitor-result characters, raw-log characters, and next-action characters;
- provider cached/uncached input tokens;
- selected outcome branch and model;
- compaction count and retrievals of omitted material.

Preserve the measured `016` lineage and the audited 1.9-million-character incident as sanitized regression fixtures.

### Phase 1 — implement Rust DAG normalization and legacy reading

Add versioned continuation-node and render-request/result wires in `sase-core`; expose them through `sase_core_rs`; integrate them with family scans and artifact identities. Implement chain, branch, merge, missing-node, and cycle behavior. Shadow-render current histories and compare factual coverage without changing launches.

Critical tests:

- every reachable node appears at most once;
- a 100-node chain is proportional to the sum of unique deltas;
- a diamond merge includes the common ancestor once;
- adding a child preserves the exact previously rendered prefix;
- dynamic family growth cannot change a persisted parent set;
- legacy nested histories flatten to one copy of every available member delta;
- invalid/missing legacy provenance degrades visibly rather than silently;
- Unicode and fenced untrusted output preserve current safety properties.

### Phase 2 — persist delta transcripts and MonitorResult capsules

New transcripts write exact parent references and local deltas. The monitor supervisor emits `MonitorResult`; follow-up rendering removes the duplicate prose/tail path. Keep the legacy reader permanently enough to read historical artifacts, but do not write new legacy-expanded transcripts.

Introduce `auto` evidence and the bounded result-file protocol. Exercise completed, failed, timeout, idle-timeout, stopped, lost, truncated-output, workspace-degraded, and no-output cases.

### Phase 3 — branch policies and monitor profiles

Generalize the existing shell follow-up substrate so monitor outcomes select distinct actions and models. Start with explicit user-authored policies. Add `verify` only after deterministic finalization is safely integrated with host-owned completion. Then shorten the generated skill around the profile CLI.

### Phase 4 — hard budgets, checkpoints, and provider acceleration

Reject no request merely after provider failure: preflight every launch, compact before the configured threshold, and surface the budget decision in monitor metadata. Add provider caching, TTL selection, conversation IDs, and native compaction as optional adapters backed by the same portable graph.

## Acceptance criteria

The redesign should not be considered complete merely because prompts are smaller in a unit test. Suggested gates are:

- zero known-oversize successor launches; preflight always compacts or reports a specific nonlaunchable reason;
- duplication ratio at or below 1.05 for newly written linear families;
- rendered size for the six-member `016` fixture close to the sum of its unique deltas, not 335,286 characters;
- exactly one rendered copy of the latest `MonitorResult` and its diagnostic excerpt;
- adding a continuation leaves the old rendered prefix byte-identical;
- routine successful `verify` runs inject no raw output by default;
- failure fallback evidence remains bounded and full logs remain retrievable;
- legacy histories and all monitor terminal states retain factual continuity;
- current process supervision, settlement, workspace-transfer, claim, and recovery tests continue to pass;
- telemetry demonstrates lower p50/p90/p99 successor input and higher cached-input ratios without higher follow-up failure rates.

## Risks and mitigations

**Lossy legacy normalization.** Some old transcripts may not expose enough provenance to recover perfect deltas. Preserve originals, mark fallback content, and prefer visible omission over invented ancestry.

**Compaction omits a critical detail.** Keep immutable source references, always retain the active objective/constraints and recent full deltas, and let agents retrieve omitted nodes. Evaluate checkpoints with factual continuity tests, not only length.

**Structured result spoofing or prompt injection.** Treat the result file exactly like stdout: untrusted, schema-validated, size-capped, path-constrained, and rendered inside disabled/fenced regions.

**Success finalization is too aggressive.** Require an explicit `verify` branch policy. Do not infer that arbitrary exit-zero commands imply task completion.

**Cross-repo implementation complexity.** Put graph semantics and budget decisions in Rust once; keep Python adapters thin. Deliver normalization before profiles or provider-specific optimizations so each phase has an independently measurable benefit.

**Cache economics change.** Instrument actual cached-token usage and retain provider-neutral correctness. TTL and breakpoint strategies are tunable adapters, not foundational storage semantics.

## Recommended solution

Implement a **shared, event-sourced Continuation Capsule system** rather than further tuning the current text-concatenation prompt.

The first deliverable should be Rust-core continuation DAG normalization with exact immutable parent IDs, delta-only agent transcripts, a legacy flattening reader, deterministic append-only rendering, and a hard preflight size report. This directly fixes the observed exponential growth and restores the stable prefixes that provider caching needs.

The second deliverable should convert monitor completion into one typed `MonitorResult` event, make `auto` evidence the default, retain raw logs by reference, and eliminate the duplicate monitor tail/metadata currently supplied by both family history and the follow-up body.

The third deliverable should add explicit outcome branches and profiles. In particular, `verify` should be able to finalize deterministically on success and launch an inherited strong model only on failure or timeout. Then shorten the monitor skill and make next actions compact deltas.

Finally, add thresholded auditable checkpoints and provider-specific cache/session/compaction adapters. Do not begin with these optimizations: provider threads still bill history, caching cannot help an unstable prefix, and summarization cannot correct recursive storage.

In short: **keep the hardened supervisor; replace recursive transcript snapshots with a deduplicated continuation graph; represent monitor completion once as structured evidence; and spend model tokens only on the outcomes that need them.**

## Sources

[^1]: SASE audited plan artifact, “Monitor fork context,” September 2026, describing the 1,913,445-character rejected input and the bounded-tail remediation: [sase--plans/202609/monitor_fork_context.md](https://github.com/sase-org/sase--plans/blob/main/202609/monitor_fork_context.md). Accessed 2026-09-10 through `sase artifact read plan:202609/monitor_fork_context.md`.

[^2]: SASE audited plan artifact, “Monitor hardening,” August 2026, covering streaming, process identity, claims, settlement, timeout, reconciliation, and follow-up guarantees: [sase--plans/202608/monitor_hardening.md](https://github.com/sase-org/sase--plans/blob/main/202608/monitor_hardening.md). Accessed 2026-09-10 through `sase artifact read plan:202608/monitor_hardening.md`.

[^3]: Current SASE implementation at commit `f5a3f5c9`: [monitor follow-up composition](https://github.com/sase-org/sase/blob/f5a3f5c99ec7c55a44ff0517c7eea820f0b46c3c/src/sase/monitor/followup_prompt.py), [family fork formatting](https://github.com/sase-org/sase/blob/f5a3f5c99ec7c55a44ff0517c7eea820f0b46c3c/src/sase/history/chat_fork/family.py), [recursive resume loading](https://github.com/sase-org/sase/blob/f5a3f5c99ec7c55a44ff0517c7eea820f0b46c3c/src/sase/history/chat_resume.py), and [chat serialization](https://github.com/sase-org/sase/blob/f5a3f5c99ec7c55a44ff0517c7eea820f0b46c3c/src/sase/history/chat_storage.py). Accessed 2026-09-10.

[^4]: Local SASE monitor corpus, 855 records returned by `sase monitor list --all --format json`, analyzed 2026-09-10. This is a local operational record without a public URL.

[^5]: Local SASE chat corpus inspected through `sase chat list`, `sase chat show`, and `sase xprompt expand` on 2026-09-10. Measurements used unrelated historical lanes and did not consult the peer researcher's report or chat.

[^6]: OpenAI, [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), especially the exact-prefix requirement, stable-prefix guidance, automatic caching, and cached-input economics. Accessed 2026-09-10.

[^7]: Anthropic, [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), especially longest-prefix reuse and five-minute versus one-hour TTL behavior. Accessed 2026-09-10.

[^8]: OpenAI, [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state), especially Conversations, `previous_response_id`, and billing of prior input tokens in a chain. Accessed 2026-09-10.

[^9]: Anthropic, [Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows), especially context accumulation, context rot, and the distinction between prompt caching and occupied context. Accessed 2026-09-10.

[^10]: Current `sase-core` implementation, [Unicode-safe bounded text tail](https://github.com/sase-org/sase-core/blob/main/crates/sase_core/src/text_tail.rs) and [deterministic agent-family parent resolution](https://github.com/sase-org/sase-core/blob/main/crates/sase_core/src/agent_family.rs). Accessed from the linked repository on 2026-09-10.

[^11]: GitHub Docs, [Workflow commands for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands), including annotations and `$GITHUB_STEP_SUMMARY` as structured, concise views beside raw logs. Accessed 2026-09-10.

[^12]: OpenAI, [Compaction](https://developers.openai.com/api/docs/guides/compaction), describing server-side and standalone compaction and the opaque compaction item. Accessed 2026-09-10.
