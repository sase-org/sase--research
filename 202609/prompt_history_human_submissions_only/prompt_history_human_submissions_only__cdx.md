# Prompt history should record human intent, not orchestration fan-out

**Researcher:** cdx  
**Date:** 2026-09-30

## Executive summary

The proposed direction is good, but I would define it more broadly than “exclude
xprompt-swarm and routine prompts”:

> Prompt history is a replay surface for prompts submitted by a user. It records the
> user-submitted root prompt once (subject to the existing short-prompt and literal
> multi-prompt rules), while machine-generated descendants never enter the store.

The code already has almost all of the provenance needed to enforce this. Prompt rows
and launch paths now carry `origin="typed"` or `origin="generated"`, and an invocation
from inside a SASE agent is forcibly classified as generated. The problem is that the
marker currently changes only prediction behavior; both origins are still written to
the same history and displayed together.

The screenshot's exact failure mode is generated bead-work fan-out. The 01:58 cluster
contains one nine-segment generated bundle plus its nine separately recorded segments,
all marked `generated`. The central history mutation records both a multi-prompt bundle
and every sufficiently long segment, turning one internal orchestration event into ten
visible history rows.

I recommend making `generated` a centralized no-op at both history mutation entry
points, before placeholder learning or failed-launch stashing occurs. Preserve and test
the original typed `#research_swarm` invocation at the user boundary; do not introduce
swarm- or routine-specific prompt-text heuristics. Hide and optionally prune existing
explicitly generated rows, but retain legacy rows whose origin is unknown rather than
guessing destructively.

## Evidence

### What the live history contains

I inspected the current September shard read-only. It contains:

| Origin | Rows |
| --- | ---: |
| `generated` | 79 |
| `typed` | 15 |
| legacy / unset | 3,687 |

The newest 100 rows—the set competing for the screenshot's initial history page—are 79
generated, 15 typed, and 6 legacy. In other words, explicit machine output occupies 79%
of the most useful recency window.

At timestamp `260930_015851`, corresponding to the 01:58 rows in the screenshot, all
ten rows are generated:

- one combined prompt with nine `---`-separated segments;
- nine single-segment rows derived from that combined prompt.

Across all 79 explicit generated rows, there are ten multi-prompt bundles containing 55
segments, 55 corresponding single-segment rows, and only 14 other singleton generated
rows. Thus 65 of 79 rows are explained by just ten generated multi-prompt launches.
The repeated `#bd/work_phase_bead` and `#bd/land_epic` markers in the generated corpus
agree with the screenshot preview.

These counts describe the current local shard, not a synthetic fixture. I did not
inspect any other swarm researcher's report.

### The write path causing the amplification

`src/sase/agent/launch_cwd_bead_work.py:172` explicitly writes the normalized bead-work
bundle with `origin=effective_origin`. Bead work calls this adapter with
`origin="generated"` from `src/sase/bead/cli_work_launch.py`.

`src/sase/history/prompt_store_mutations.py:36-86` then:

1. records prompt placeholders;
2. accepts the generated prompt as recordable;
3. creates a mutation for the whole text;
4. creates another mutation for every long-enough multi-prompt segment.

This is intentional for user-authored literal multi-prompts, as documented in
`docs/xprompt.md:3608-3610`, but it is pathological for generated work bundles.

The same mutation function is reached by ordinary single-agent launches and other
fan-out paths. `origin` is persisted and merged, but it is not an eligibility gate.
The recent origin feature was added so the Rust prediction corpus could reject
machine-generated rows, not so prompt history itself could reject them.

### Xprompt-swarm roots are already distinguishable from their children

The generic launcher captures `submitted_query` before swarm expansion
(`src/sase/agent/launch_cwd_agents.py:103-120`). If expansion yields multiple agents,
the fan-out branch writes that original submitted query, not the rendered child prompts
(`src/sase/agent/launch_cwd_fanout.py:86-92`). Therefore a typed
`#research_swarm(...)` invocation can remain in history without storing each expanded
member prompt.

Swarm membership is propagated separately through `template_group`,
`swarm_xprompts`, and `SASE_LAUNCH_SWARM_XPROMPTS`. That metadata is useful for agent
identity and artifacts, but it is unnecessary for the history decision. The root's
`typed` provenance and the descendants' generated provenance are the cleaner boundary.

### Routine and other generated launches already declare provenance

Routine/job launch paths build `SASE_JOB_*` / legacy `SASE_CHOP_*` environment and call
the launcher with `origin="generated"`. Bead work, plan approval, LaunchApproval,
restarts, and admission dispatch do the same. In addition,
`_effective_prompt_origin()` upgrades `typed` to `generated` whenever `SASE_AGENT` is
present. These are strong signals because they describe how a launch was initiated,
not what its text happens to look like.

There is already a routine-specific exception for failed prompts in
`launch_cwd_agents.py:69-79`: failures with chop/job launch environment are not written.
Successful routine launches, however, still take the normal write path. This asymmetry
is another indication that eligibility belongs in the central mutation policy.

### Filtering only the TUI would be incomplete

`PromptHistoryRecord` currently drops `origin` when converting from and back to
`PromptEntry` (`src/sase/history/prompt_catalog.py:24-51,97-109`), and catalog filtering
does not consider it. More importantly, the picker is not the only consumer:

- CLI list/search/replay and statistics read the same shards;
- the legacy prompt word index tokenizes every row without checking origin;
- placeholder seeding reads every shard row without checking origin;
- maintenance and selector code deduplicate the combined corpus.

The Rust next-word corpus does reject `origin="generated"`, and it uses conservative
content heuristics only for old rows with no origin. That protects one feature, not the
store or the other consumers. A TUI-only filter would hide the symptom while retaining
storage growth and completion pollution.

### Generated prompts still have an audit home

Excluding machine prompts from replay history does not erase launch provenance. Every
agent launch writes its launch-boundary prompt to `raw_xprompt.md`, captures xprompt
metadata, and copies revival inputs to a durable per-run archive
(`src/sase/axe/run_agent_runner_setup_prompt.py:41-88` and
`src/sase/core/revival_inputs.py`). Routines also have their own run and launch records.
Canonical prompt publication is a separate agents-sidecar concern. Prompt history does
not need to duplicate those audit stores.

## Critique and requirement adjustments

### 1. Classify by provenance, not by orchestration feature

Special-casing “xprompt swarm” and “routine” would be too narrow. The same unwanted
class includes bead work, approved plan workers, agent-requested launches, restarts,
and future orchestration mechanisms. Conversely, a human can manually type text that
looks exactly like a generated bead or swarm prompt; that submission should remain
replayable.

**Adjustment:** express the rule as “user-submitted roots are recordable; generated
launches are not.” Swarms and routines are examples, not branches in the history code.

### 2. “Typed” means user-submitted, not literally keyboard-entered

Replaying a history row, submitting from mobile, pasting into the TUI, and using
`sase run` are all user intent and should count. An agent invoking `sase run` is not
user intent merely because it crossed the CLI surface. The existing `SASE_AGENT`
override correctly guards this distinction.

**Adjustment:** document `typed` as “user-submitted/replayable” or eventually rename
the semantic to `user`. Do not infer human intent solely from the executable or UI
surface.

### 3. Keep the current literal multi-prompt rule for now

A strict one-row-per-human-submit invariant conflicts with today's documented behavior:
for a literal `---` prompt authored by the user, history stores the combined text and
each human-authored segment so segments can be replayed independently. Removing that
feature is a separate UX decision and is not necessary to solve the observed flood.

**Adjustment:** retain bundle-plus-segment recording only for eligible user-submitted
literal multi-prompts. A short xprompt swarm invocation remains just the invocation;
rendered template segments are generated and remain absent. If history is still noisy
after this change, reconsider the literal-segment feature separately rather than
coupling it to this fix.

### 4. Do not destructively guess about legacy rows

Most September rows predate the new origin field. Rust contains a conservative
generated-text heuristic for prediction, but using prompt content to delete durable
history risks false positives. A human may have typed or edited any of those strings.

**Adjustment:** automatically hide/prune only rows explicitly marked `generated`.
Keep `origin=None` visible. An optional, preview-first inferred cleanup could be offered
later, but should not be part of the migration.

### 5. Failed machine launches should not enter Stash either

`record_failed_launch_prompt()` currently writes history, learns placeholders, and
stashes the text. Those actions make sense for a failed user submission; they do not
make sense for a failed routine or generated descendant. Generated failure recovery
belongs to its request bundle, routine log, bead render source, or agent artifact.

**Adjustment:** the generated no-op must happen before placeholder recording and stash
recovery, not merely before the JSON mutation.

## Options considered

### A. Filter generated rows only in the prompt-history modal

This is a small visual fix but leaves generated rows in CLI search, stats, selectors,
manual completion indexes, placeholder seeding, and storage. It also requires origin to
be threaded through the catalog model. I do not recommend it as the primary solution.

### B. Add `record_history=False` to swarm and routine launch calls

This would address known callers but is a negative boolean that every future fan-out
surface must remember. It also duplicates the meaning of `origin="generated"` and
does not naturally fix failed-launch stashing or placeholder learning. I do not
recommend it.

### C. Stop every generated mutation centrally

This uses the provenance already threaded through all launch paths, fixes successful
and failed launches, and automatically covers new orchestration features. Combined with
root-ingress tests and cleanup of existing explicit generated rows, it satisfies the
product model with the least new machinery. I recommend this option.

### D. Move all history eligibility into Rust immediately

The shared-domain principle points toward Rust for reusable policy, but the history
store and its mutation side effects are currently Python-owned. The immediate rule is a
simple provenance gate at that existing storage boundary; adding a Rust round trip for
`origin == generated` would add complexity without improving correctness. The Rust
prediction code should retain its legacy heuristic, but it should not become a deletion
engine. If prompt-history persistence later moves into `sase_core`, move this invariant
with it.

## Implementation blueprint

### 1. Make the mutation boundary authoritative

In both `add_or_update_prompt()` and `record_failed_launch_prompt()`:

1. resolve the effective origin first;
2. if it is `generated`, return immediately;
3. only then record placeholders, apply the word threshold, mutate a shard, or stash a
   failed prompt.

Keep `origin=None` recordable for compatibility, but require every production launch
surface to pass an explicit origin. A generated use of text already present as a typed
row must not bump that row's recency; recency should mean the last human use.

The effective-origin guard should treat routine/job process context as generated too,
not only `SASE_AGENT`. Existing routine launch APIs already pass generated explicitly,
but checking canonical `SASE_JOB_*` (and accepted legacy `SASE_CHOP_*`) context protects
custom routine scripts that call `sase run` directly.

### 2. Preserve exactly one user root before derived dispatch

Audit every user ingress:

- TUI submit;
- ordinary `sase run`;
- prompt replay/edit;
- mobile launch;
- remote dispatch;
- direct typed admission (`%if` / `%proc`).

The ordinary generic launcher already records `submitted_query` before swarm expansion.
However, direct typed admission exits the normal `sase run` path and dispatches child
units with `origin="generated"`. Once generated writes become no-ops, that path must
explicitly record the original user query once. Remote-dispatch early returns deserve
the same audit. This is the main regression risk in an otherwise small change.

Do not record both at ingress and again in the generic launcher unless deduplication and
recency semantics are intentional. Prefer one owner for root recording and test call
counts.

### 3. Preserve origin through catalog models

Add `origin` to `PromptHistoryRecord`, `record_from_entry()`, and `to_entry()`. Even if
new generated writes stop, this is required to safely classify existing rows and avoids
silently discarding provenance during conversions.

User-facing history readers should exclude explicit generated rows by default so the
fix is visible immediately after upgrade. Diagnostic/maintenance code may read the raw
corpus to report and remove them. Word-index and placeholder-seeding consumers should
use the same eligible-entry iterator rather than inventing separate filters.

### 4. Clean up existing explicit generated rows conservatively

Extend existing prompt maintenance with a previewable origin predicate, for example
`sase prompt prune --generated` (following the command's existing dry-run/confirmation
conventions). Report explicit generated counts in `sase prompt doctor` so cleanup is
discoverable.

I prefer an explicit cleanup over silent destructive migration because prompt history
is user data. The current machine would remove 79 rows, including the ten-row cluster in
the screenshot. Keep unset/legacy rows. If an automatic cleanup is chosen instead, it
should be idempotent, lock all shard rewrites, fail closed on a corrupt shard, and make
a recoverable backup.

### 5. Update documentation

`docs/prompt.md` currently says generated prompts are stored and merely excluded from
prediction. Change it to define history as user-submitted intent and point generated
launch auditing to agent artifacts/routine records. Keep the literal multi-prompt
segment rule in `docs/xprompt.md`, explicitly scoped to user-authored prompts.

## Regression tests

At minimum, add tests proving:

1. `add_or_update_prompt(..., origin="generated")` creates no shard, records no
   placeholders, and does not update a prior typed row's `last_used`.
2. `record_failed_launch_prompt(..., origin="generated")` creates neither history nor
   Stash state.
3. `SASE_AGENT` and routine/job context override a claimed typed origin to generated.
4. A typed `#research_swarm(...)` launch records exactly that invocation once and none
   of its rendered member prompts.
5. A generated planned bead-work launch with N segments records zero rows (the current
   behavior is N+1).
6. A typed literal `---` multi-prompt retains the current combined-plus-segments
   behavior.
7. Direct typed admission records its original root exactly once while its dispatched
   units record nothing.
8. Human failed launches remain cancelled and recoverable; generated failures do not.
9. Cleanup removes explicit generated rows across every shard, retains typed and unset
   rows, and preserves an older typed copy when a newer generated duplicate exists in a
   different shard.
10. Catalog conversion preserves origin, and all default user-facing consumers exclude
    explicit generated rows consistently.

## Recommended solution

Adopt a single invariant: **prompt history records user-submitted root prompts; machine
launch prompts never enter it**. Enforce it centrally by returning early for effective
`origin="generated"` in both successful and failed history mutation functions, before
placeholder learning or Stash recovery. Keep the current `submitted_query` behavior so
a human's `#research_swarm` invocation is stored while rendered members are not; make
routine/job context force generated provenance; and patch any bypassing user ingress
(especially direct typed admission and remote dispatch) to record its original root
once. Preserve origin through catalog models, hide explicit generated rows from every
default consumer, and offer a conservative previewable prune for existing explicit
generated rows while leaving legacy unknown rows untouched.
