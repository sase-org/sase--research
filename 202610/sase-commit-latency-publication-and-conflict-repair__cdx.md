# Why SASE commit stages take minutes—and sometimes hours

Independent research by cdx, 2026-10-29. Source checkout: sase `dd59c28f44c7e5fc83cc75188ca58b710d4f32f7`.

The suspicion is supported by production timing records. In the retained sample, a finalizer phase usually took about **three minutes** even without conflict repair. The ordinary delay is predominantly **synchronous publication after the repository commit has already succeeded**. The extreme tail is a different problem: **merge/rebase conflicts launch another model turn inside finalization**, sometimes lasting hours.

The strongest initial intervention is to remove auxiliary publication from the commit's synchronous completion path, while durably preserving all inputs and retry obligations. Treat conflict repair separately; accelerating Git itself or removing formatting would miss most of the measured delay.

## Scope, evidence, and method

I independently examined the local SASE implementation and historical runtime telemetry. I did not read this swarm's other reports, transcripts, summaries, or findings. The measurement corpus excludes October 29 run directories entirely, including the current swarm.

Sources:

- **E1: finalizer telemetry.** Under `/home/bryan/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202610/{22..28}/<run>/`: `finalizers/progress.jsonl`, `finalizers/commit/*.outcome.json`, `*.steps.jsonl`, stitch stdout/stderr, and `commit_hooks/*.json`.
- **E2: publication telemetry.** `/home/bryan/.sase/logs/agent_publication_drains.jsonl` and its retained `.1` rotation, filtered to project `gh_sase-org__sase` and timestamps from 2026-10-22 00:00 UTC through, but excluding, 2026-10-29 00:00 UTC.
- **E3: source.** The revision above, plus the locally opened sase-github checkout at `e4f8bf47c8b0e89b3b46b35369e3574fcf97d0ed`. GitHub's plugin inherits ordinary commit dispatch from SASE's GitCommon implementation; the important behavior is in SASE itself.

The main corpus contains 313 progress journals, including skipped phases. There are **242 completed phase intervals across 241 run directories**, 247 stitch subprocess outcome records, and 15 completed model-turn outcome records. One run has two phase intervals. I measured each phase by pairing `phase_started` and `phase_finished`, not by total agent runtime. I classified a phase as attempting repair when its own interval contained a `model_turn` start event; this includes failed repairs that never produced a completed outcome.

Subprocess duration comes from the outcome's `duration_seconds`. Step duration pairs the same step's `start` with its terminal `ok/fail/warn`. Percentiles use nearest rank; medians use the ordinary midpoint calculation. Different rows have different denominators and some intervals nest: their totals must not be added together.

This is an observational sample of retained telemetry, not an exhaustive census or a controlled benchmark. Historical runs used evolving installed versions. Directory dates select runs, not strict phase-start dates. Wall-clock journal timestamps can theoretically jump; the subprocess clock provides a separate duration source. All sums below are accumulated run-time, not elapsed time on the host: agents run concurrently.

## How long is it?

| Measured interval | Count | Median | p95 | Maximum |
| --- | ---: | ---: | ---: | ---: |
| All completed finalizer phases | 242 | 188.8 s | 1,918.0 s | 15,328.5 s |
| Phases without a model-repair start | 225 | 180.4 s | 361.1 s | 566.5 s |
| Phases with a model-repair start | 17 | 3,625.0 s | 15,328.5 s | 15,328.5 s |
| Stitch subprocesses, all outcomes | 247 | 157.8 s | 279.5 s | 497.1 s |
| Successful `create_commit` provider steps | 229 | 2.11 s | 3.64 s | — |
| Publication steps | 230 | 147.6 s | 251.4 s | 491.6 s |
| `just fix` commit hooks | 151 | 15.3 s | 24.4 s | 39.3 s |
| `sase_git_fix` commit hooks | 95 | 0.04 s | 0.07 s | 3.92 s |
| Completed conflict-repair model turns | 15 | 3,395.8 s | 15,088.4 s | 15,088.4 s |

All figures in this table derive from E1. There were 240 successful phase intervals and two failed intervals. Thirty-seven phases exceeded five minutes; fourteen exceeded thirty minutes, and **all fourteen included a repair start**.

Seventeen repair-bearing phases are 7.0% of intervals but account for **65.7% of aggregate phase elapsed time**. Thus both impressions can be true: ordinary commits routinely take minutes, and a few extraordinary commits dominate the total time spent finalizing.

The 247 subprocess records cover 151 primary-repository attempts, 49 research, 27 sase-core, 14 plans, and six other/resume attempts. Eighteen subprocesses returned nonzero: seventeen conflict exits and one other failure. Counting a phase is not equivalent to counting a Git commit or an entire agent session.

## The normal delay: publication is on the critical path

The actual flow is approximately:

1. Validate the declaration, inspect/reconcile repositories, and order commit obligations.
2. Run a repository's before hook.
3. Stage and create its Git commit, synchronize with origin, and push.
4. Run after-commit bookkeeping and publication.
5. Reinspect state and continue with any remaining repository obligations.

The measured `create_commit` provider step includes its normal synchronization and push work. It is not just the local `git commit` syscall. Git dispatch creates the commit and calls its fetch/rebase/push machinery; the workflow emits a successful `push` marker after dispatch. The two markers therefore should not be counted as independent timed work. See [Git commit dispatch](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/vcs_provider/plugins/_git_commit_dispatch.py#L181) and [workflow dispatch](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/workflows/commit/workflow.py#L355).

In 230 attempts with both an outcome and a publication span, publication consumed **34,154.2 of 38,267.9 subprocess seconds: 89.25%**. The median duration remaining after subtracting publication from each matched subprocess was **20.5 seconds**, p95 **35.8 seconds**. This is an attribution calculation, not a measured performance improvement from an implemented change.

Two concrete E1 examples make the attribution particularly clear:

| Run / repository | Whole stitch | Before hook | Commit dispatch | Publication |
| --- | ---: | ---: | ---: | ---: |
| `20261028181311` / research | 459.03 s | 0.073 s | 2.05 s | 453.25 s |
| `20261028200509` / sase-core | 497.12 s | 0.049 s | 1.87 s | 491.55 s |

For these records, use the respective run's `finalizers/commit/attempt-1.research.*` and `attempt-1.sase-core.*` files. Nearly all their elapsed time occurs after the repository commit dispatch.

The publication wrapper performs multiple serial operations: bead-page publication, canonical prompt archival, plan-header refresh, agent-hood publication, and artifact-link outbox draining. A hood groups agents sharing the first dotted-name prefix, so names such as `research.5f.cdx` belong to the broad `research` hood. This is larger than one research swarm or one agent session.

Crucially, `publish_committed_agent_hood()` **enqueues a durable request and immediately drains publication before returning**. The current implementation already has deferred-publication semantics, but still pays the synchronous attempt cost on the successful commit path. Prompt archival separately acquires the agents lock and performs its own publication work before the hood drain. [Publication wrapper](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/workflows/commit/workflow_publication.py#L100), [enqueue plus synchronous drain](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/agents_sync/_commit_publication_queue.py#L42), [prompt-archive path](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/agents_sync/prompt_archive/publish.py#L155).

### What the inner drain timings establish

The independently filtered E2 window contains 246 publication-drain records: 152 `published`, 73 `no_requests`, 17 `lock_busy`, and four `timeout` outcomes. These labels are coarse: some records also carry item errors, and `no_requests` does not necessarily imply no work was performed. The controller uses that outcome when zero requests were drained; some such records have substantial inventory and preparation timings.

| Inner drain measurement | Count | Median | p95 |
| --- | ---: | ---: | ---: |
| Agents-lock wait | 246 | ~0 s | 10.0 s |
| Inventory build | 229 | 27.7 s | 35.8 s |
| Preparation, including nested hood rendering | 229 | 11.2 s | 22.7 s |
| Pull/rebase | 229 | 0.58 s | 0.69 s |
| Push | 212 | 1.78 s | 2.93 s |
| Research-hood rendering | 47 | 11.7 s | 51.7 s |

Preparation includes the per-hood spans: adding them together would double-count work. Inventory contained a median 37.5 hydrated runs and p95 1,179; the largest record contained 1,397. In one slow research-related drain, the recorded inventory carried approximately 13.1 MB of chat bytes plus 2.5 MB of prompt bytes. These are telemetry counters, not report or transcript contents I consulted.

Requested-hood filtering **already exists**, introduced in commit `1f107c4a89` on October 20. Recommending that same optimization as new work would be misleading. Its limitation is that a large hood can still encompass much history, while historical-association and indexed-record discovery precede parts of the filtering. Narrower incremental processing would be a further change. [Inventory implementation](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/agents_sync/inventory.py#L83), [transaction timing boundaries](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/agents_sync/_commit_publication_transaction_engine.py#L47).

There is also an important measurement gap. I matched 228 outer publication spans to drain records using the stitch process PID embedded in hook filenames and the drain's timestamp falling inside that publication span. For each match I summed only non-nested drain stage timings plus its agents-lock wait, then subtracted that from the outer publication duration:

- Median outer publication: **146.3 seconds**.
- Median measured inner drain subtotal: **45.8 seconds**.
- Median per-attempt residual: **101.2 seconds**, p95 **200.5 seconds**.

These medians are computed independently and are not expected to add exactly. The residual includes other wrapper operations, target/clone setup, untimed bookkeeping, and gaps around the measured drain. **The evidence does not identify which of those consumes the residual.** Prompt archival and link/provenance operations are concrete code paths to instrument, not proven individual culprits.

Consequently, optimizing hood rendering alone is unlikely to remove the entire common delay. Equally, the measured lock waits do not support blaming minutes of ordinary latency primarily on that particular lock. Other locks outside the inner timer remain unmeasured.

### Repeated unsuccessful publication adds cost without immediate benefit

Across the 247 stitch stdout records:

- 229 mention quarantined publication requests.
- 192 contain `artifact-link legacy index writes are fenced; use link events`.
- 91 mention an unresolved prompt archive.
- 19 report that a published agent page did not materialize.
- Six report the 120-second publication timeout.

These categories overlap. They describe warning occurrences, not distinct root causes or all failures in the system.

The two slow examples above reported approximately 3,493 and 3,499 quarantined requests, respectively, while their repository commits still completed. This is evidence that publication health is degraded; it is **not** evidence that every commit renders all 3,500 requests. The drain selects active requests with a batch cap of 25, and the observed active-request median was two.

The fenced-write diagnostic comes from an explicit guard on obsolete artifact-link index mutation. Retrying that same path cannot by itself make the prohibited write valid. The prompt-archive path can call referenced-by write-back, and the commit workflow reports its failure as deferred publication. Diagnose and migrate that caller to the supported event path before reactivating failed work indiscriminately. [Referenced-by drain](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/agents_sync/referenced_by_publication.py#L24), [legacy-write guard](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/sdd/_artifact_link_store_sidecar.py#L35).

## The extreme delay: another development turn inside “commit”

Fifteen completed conflict-repair operations had a median duration of **56.6 minutes**. The longest recorded repair alone took **15,088.4 seconds**, approximately **4 hours 11 minutes**. Its encompassing finalizer phase took 4 hours 15 minutes.

Examples from E1:

| Run | Finalizer phase | Recorded repair | Initial conflict evidence |
| --- | ---: | ---: | --- |
| `20261027152410` | 15,328.5 s | 15,088.4 s | Justfile, core pin, generated footprint catalog, docs, CLI implementation |
| `20261027152407` | 8,424.2 s | 8,164.8 s | Primary-repository rebase conflict |
| `20261026181515` | 7,055.2 s | 7,011.5 s | Primary-repository rebase conflict |
| `20261024111030`, first phase | 6,481.4 s, failed | No completed repair outcome | `sase-core-revision.txt` |

The last case illustrates why counting only completed model outcomes undercounts repair: its journal records repair starting, then roughly 6,341 seconds later the phase fails with `controller_exception`. A later phase in the same run succeeds. I do not assume all of that intervening time was model computation; it can include tools and checks.

Seven of the seventeen initial conflict stdout records identify **only `sase-core-revision.txt`** on the conflicted-files line. Other cases include semantic source conflicts and shared generated files. This makes pin conflict handling a concrete target for further investigation, but does not justify selecting one hash arbitrarily.

The host's repair prompt requires resolving semantic conflicts, checking the integrated content, running applicable repository verification, resuming the paused stitch, and submitting a fresh final declaration. That is a substantial development/verification turn. “Single repair turn” bounds the number of turns, not elapsed wall time. The source calls the provider directly under `finalizer_owned_turn()`; the 1,800-second stitch subprocess timeout does not wrap that provider invocation. [Repair prompt and invocation](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/finalizers/commit_repair_conflict.py#L447), [stitch timeout application](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/finalizers/commit_repair_stitch.py#L475).

I have not apportioned those repair intervals among model reasoning, test execution, package setup, or tool admission. Doing so requires a separate tool-level timing join. Their location inside finalization is established; a claim that a particular model or test suite causes most of the hours is not.

Multi-repository finalization further compounds the problem. Dispatch is sequential, including each repository's publication before proceeding. In the longest example, sase-core was committed and published before main encountered its rebase conflict. That increases completion time and may enlarge the window in which another agent changes the primary branch. The latter is a plausible mechanism, not a measured causal effect.

## Instrumentation can make the stage look more mysterious than it is

A concrete journal defect complicates analysis: the ordinary dispatch path calls the stitch runner first and then calls `record_stitch_artifacts()`. That recorder emits `op_started` while writing completed artifacts. Therefore the journal's start/finish timestamps can be only milliseconds apart even when the recorded subprocess duration was minutes.

For `20261024111030`'s first sase-core stitch, the recorded duration is **111.506 seconds**, while its journal `op_started` and `op_finished` differ by only **0.025 seconds**. This report uses the outcome duration, not that misleading event gap. [Dispatch ordering](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/finalizers/commit_dispatch.py#L365), [recorder implementation](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/finalizers/commit_repair_stitch.py#L128).

The 120-second publication budget is also narrower than “the whole commit must finish within two minutes.” Its alarm wraps the locked hood drain, after target resolution, clone setup, and lock acquisition. It excludes earlier prompt publication and later wrapper work. That explains why an outer publication step can legitimately exceed 120 seconds without contradicting the configured inner bound. Five E2 records recorded an alarm, but only four ended with outcome `timeout`; alarm and final outcome must be retained separately. [Bounded drain](https://github.com/sase-org/sase/blob/dd59c28f44c7e5fc83cc75188ca58b710d4f32f7/src/sase/agents_sync/_commit_publication_drain.py#L112).

## Reproducing and extending the analysis

The following read-only fragment reproduces the principal phase distribution without searching reports or opening agent transcripts. It deliberately fixes the historical date directories, so it does not enter the current swarm's runs.

```python
from pathlib import Path
import json
import math
import statistics

root = Path(
    "/home/bryan/.sase/projects/gh_sase-org__sase/"
    "artifacts/ace-run/202610"
)
phases = []
for day in range(22, 29):
    for path in (root / f"{day:02}").glob("*/finalizers/progress.jsonl"):
        current = None
        for line in path.read_text().splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event") == "phase_started":
                current = {"start": event["t"], "repair": False}
            elif current is not None:
                if (
                    event.get("event") == "op_started"
                    and event.get("kind") == "model_turn"
                ):
                    current["repair"] = True
                elif event.get("event") == "phase_finished":
                    phases.append({
                        **current,
                        "seconds": event["t"] - current["start"],
                        "run": path.parts[-3],
                        "status": event.get("status"),
                    })
                    current = None

for label, selected in (
    ("all", phases),
    ("without_repair", [p for p in phases if not p["repair"]]),
    ("with_repair", [p for p in phases if p["repair"]]),
):
    values = sorted(p["seconds"] for p in selected)
    print(label, {
        "n": len(values),
        "median": statistics.median(values),
        "p95": values[math.ceil(0.95 * len(values)) - 1],
        "max": max(values),
    })
```

For step attribution, pair same-name start/terminal events in `*.steps.jsonl`, then join the file stem to `*.outcome.json`. For the publication residual, derive stitch PID from the matching hook metadata filename, join drain rows by that PID and publication time interval, and exclude colon-named nested hood/prompt stages from the summed inner-stage subtotal. Exclude ambiguous joins. This produced 228 matches here.

Retain future evidence beyond the publication logger's one-megabyte rotation, and include run, repository, attempt, operation, parent span, monotonic duration, queue age, and terminal reason. Explicit start spans should surround declaration work, reconciliation, actual stitch execution, every publication-wrapper substep, and repair tools/checks. The current counters are enough to locate the major problem but not enough to explain the approximately 101-second residual.

## Recommended solution

**Make repository finalization finish after the required commits/pushes, postcondition checks, and a durable publication handoff; let a host-owned worker complete auxiliary publication.** Prioritize this over Git tuning or weakening verification.

Implement it with these boundaries:

1. **Preserve durability before returning.** Capture immutable prompt/artifact inputs, exact repository/revision identities, publication obligations, and applicable link eligibility before releasing the workspace. An outbox row pointing at files that will disappear is insufficient: unresolved source obligations already appear in the observed failures. Queue-persistence failure must remain a completion error.

2. **Defer the whole auxiliary publication wrapper, not just the hood drain.** Account for prompt archival, bead/plan projections, referenced-by work, hood rendering, and artifact-link updates. Reuse existing queues where their guarantees suffice. A supervised host worker must own retry and process lifetime; a subprocess launched by the terminating provider cannot supply that guarantee. Preserve revision-specific records when coalescing repeated rendering work.

3. **Measure correctness and freshness separately from commit success.** Display “committed; publication pending” with queue age and retry/failure details. Acknowledge requests only after the required published content is verified. Test termination immediately after enqueue, worker restart, duplicate delivery, push rejection, missing sources, unavailable remotes, and interrupted rendering. Confirm eventual publication and no lost obligations.

4. **Fix the persistent publication failures and reduce repeated work.** Route fenced legacy write-back through supported link events; recover unresolved obligations deliberately. Keep bounded batches and serialized sidecar mutation. Incrementally hydrate/render changed publication units and cache stable associations with explicit invalidation. Requested-hood scoping is already present; the remaining large-hood cost needs finer granularity. Do not blindly retry thousands of quarantined rows on every commit.

5. **Address conflict repair as a separate recovery workflow.** Show its elapsed time and current check distinctly from committing. Give recovery a persisted checkpoint and explicit execution/time budget; budget exhaustion should yield a visible recoverable state, never false success. Investigate deterministic resolution for core-pin/generated-file conflicts using ancestry and compatibility checks, then validate the integrated result. Retain semantic model repair and required checks for conflicts that cannot be proved mechanical.

6. **Verify the benefit against this baseline.** First move operation-start events before execution and time the publication residual. Compare at least 100 subsequent ordinary attempts, stratified by repository count and repair, using commit latency, publication queue age, drain throughput, failures, and eventual completion. A useful initial target is p95 under 60 seconds for a single ordinary repository commit under comparable conditions, plus an explicit publication-freshness target. That is a proposed target, not a demonstrated result; the measured 20.5-second median non-publication remainder makes it plausible.

This separates two evidenced costs: routine minutes spent publishing auxiliary state, and exceptional hours spent repairing integration. It preserves host-owned commits and verification while making both the speed and the meaning of “finished” easier to trust.
