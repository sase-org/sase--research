# Publish the agent snapshot before the code commit

Independent research by **cdx**, 2026-11-04. No other member of this research swarm's report, transcript, summary, or findings was consulted.

**Recommendation.** Adopt the ordering requirement, but implement a forward change rather than broadly reverting publication work. A code commit that advertises an agent page should require verified publication of that page first. Keep background processing for later enrichment, backlinks, indexes, and recovery. The existing `inline` setting does **not** enforce this requirement: it publishes after the code commit and permits deferred publication.

A useful, enforceable guarantee is: **SASE never creates a linked code commit until the exact agent snapshot it references has been published and verified.** That guarantee requires refusing the commit when verification is unavailable. No implementation can additionally guarantee that GitHub, every reader's network, and repository permissions will remain available forever. Those are different promises.

**What I inspected.** This report is based on SASE source and history at `d563b9da4d39339ee5662046254a58ad4e355468`, its pinned Rust core at `55532e2d878dfc5415bdd695a1978cc5c5fb5a3c`, the linked GitHub plugin at `e4f8bf47c8b0e89b3b46b35369e3574fcf97d0ed`, selected existing tests, official Git/GitHub documentation, and retained Apollo publication timing logs. Repository access used `sase repo open`. I did not run mutating publication/recovery commands, change configuration, revert code, or inspect peer research. This is source analysis and observational research, not an implemented or experimentally verified replacement.

**The current ordering is weaker than the desired contract.** The normal Git workflow does this:

```text
construct agent footer URL from local configuration
  → save commit checkpoint
  → create code commit, possibly amend/rebase it, push it
  → record result
  → attempt publication inline OR enqueue it for background publication
  → finish host completion
```

The order is explicit in `workflow.py`, `_workflow_tracking.py`, and the shared Git dispatch implementation. The GitHub plugin inherits the ordinary commit implementation from `GitCommon`. Both ordinary code commits and pull-request creation need the new boundary. A check after provider dispatch is too late: a remote reader can already see the commit. [Workflow source](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/src/sase/workflows/commit/workflow.py#L270), [tracking source](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/src/sase/workflows/commit/_workflow_tracking.py#L215), [Git dispatch](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/src/sase/vcs_provider/plugins/_git_commit_dispatch.py#L537).

`resolve_agent_commit_tag` deliberately resolves links locally. It establishes the sidecar's hosted repository, branch, and agent/session path; it does not establish that the destination page exists remotely. Current footers generally link `blob/main/...`, not an immutable sidecar revision. Session footers identify the session page without a turn anchor. Thus even an existing session page does not prove that the newly committing turn is represented. [Link construction](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/src/sase/agents_sync/links.py), [publication documentation](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/docs/contribute/agents-sidecar-sync.md).

The background default was introduced by [`e69360f49d`, October 30](https://github.com/sase-org/sase/commit/e69360f49d60b2657f7c509fec937d2b10866a09), following the background publisher job. It selects enqueue-only behavior when background mode is configured, AXE is running, and the publisher heartbeat is at most 15 minutes old. That is a scheduling/liveness hint, not evidence that this particular page was published. The job normally waits for `done.json`, or a ten-minute request age, before publishing a new run. A five-minute backstop covers missed wakeups. These policies intentionally allow a gap between code publication and page publication. [Mode and enqueue implementation](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/src/sase/workflows/commit/workflow_publication.py#L318), [publisher readiness](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/src/sase/agents_sync/publication_job.py#L452), [documented scheduler behavior](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/docs/reference/agents/hood-sync.md#L341).

Inline mode still runs after the primary commit. If a publication request is durable but remains queued, `workflow_publication.py` warns and continues; an inability to durably queue can fail the workflow, but the code commit already exists. I also inspected the parent of the October 30 change: post-commit publication with deferred-error handling already existed there. The existing acceptance test named `test_tagged_commit_publishes_and_pushes_every_sidecar_before_returning` checks publication before the publication helper returns. It does not test publication before the primary commit or push. [Inline failure behavior](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/src/sase/workflows/commit/workflow_publication.py#L200), [acceptance test](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/tests/test_commit_publication_inline.py#L314).

**There is operational evidence of a separate persistent failure.** I aggregated the existing `~/.sase/logs/agent_publication_drains.jsonl` and its `.1` rotation without reading agent transcripts or publication payloads. The first observation contained 1,089 rows from approximately **08:02:07 to 17:02:09 UTC on November 4**. Of these, **361 were for SASE, all failed at `pull_rebase`**. Inspecting the error strings for those same SASE rows gave:

| SASE drain failure | Recorded attempts |
| --- | ---: |
| Could not replay sidecar commit `7b4d2fef9c` | 330 |
| SSH `Permission denied (publickey)` | 30 |
| Pull attempted while not on a branch | 1 |
| Total | 361 |

SASE's median lock wait rounded to 0.000 seconds, nearest-rank p95 to 0.001 seconds, and maximum was 0.238 seconds. Every sampled SASE drain selected 25 active requests. This is repeated retry evidence, not 361 distinct broken pages or proof of the total queue size. The stored generic error class called these pull failures `rebase_conflict`, including SSH refusals; the table above uses the actual error strings instead.

The retained sample contains no successful SASE drain from which to estimate healthy publication latency. Log rotation also prevents a controlled before/after comparison with the async rollout. The running host's installed version was not independently matched to the checkout. Nevertheless, the observed repeated replay failure is concrete: changing scheduling mode cannot make that sidecar commit rebase cleanly, and credentials need their own diagnosis. The existing documentation already describes backup-first stale-replay recovery that preserves owner content and regenerates derived browsing pages. Its applicability must be checked against the current HEAD and current state; an old SHA in this report is not authorization to reset anything. [Recovery procedure](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/docs/contribute/agents-sidecar-sync.md#stale-replay-recovery).

This evidence supports two distinct conclusions: async-after-commit violates the desired ordering **by design**; the observed publication errors also include failures that a synchronous path would inherit. It does not establish that the async change caused every publication defect.

**What “100% certainty” can mean.** Distinguish these conditions:

| Condition | What it establishes |
| --- | --- |
| A durable outbox entry exists | Work is owed and can be retried. |
| A valid page exists in the local sidecar checkout | Local materialization succeeded. |
| The remote Git repository contains the exact page and required payload at a retained revision | Publication to the Git authority succeeded. |
| The intended reader can fetch the exact hosted URL now | That serving path is working for that reader at that observation. |
| Every reader can always fetch it in the future | Not an achievable unconditional distributed-system guarantee. |

The current acknowledgment logic is stronger than merely recording an enqueue: the transaction pushes before acknowledging, or follows its already-current path, and checks the required page plus revision association. However, the page observations are local filesystem checks; they are not HTTP readiness checks. A strict replacement should bind its proof to the exact remote revision and payload, and treat failures to establish remote state as unknown, not success. [Transaction engine](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/src/sase/agents_sync/_commit_publication_transaction_engine.py#L153), [page observations](https://github.com/sase-org/sase/blob/d563b9da4d39339ee5662046254a58ad4e355468/src/sase/agents_sync/publication_completion.py#L125).

An outbox is useful for eventual work, but it cannot make a consumer observe a page before the producer commits if publication is explicitly scheduled afterward. Also, SASE's code-commit-plus-later-outbox-write is not a single atomic database transaction; checkpoints provide recovery around that gap. The transactional-outbox pattern's atomic local write and idempotent relay concepts are useful here, but its eventual delivery property should not be confused with the requested ordering. [Original pattern description](https://microservices.io/patterns/data/transactional-outbox.html).

A single Git push can atomically update multiple refs when the server supports `--atomic`. It cannot atomically publish two independent repositories. Fortunately, this task does not require all-or-nothing publication across both repositories: publishing an agent snapshot and then failing to create its code commit leaves an unused snapshot, which is compatible with the requested one-way dependency. [Git push documentation](https://git-scm.com/docs/git-push).

**The recommended design separates a useful snapshot from later history.** Introduce a host-enforced precommit publication operation with a stable operation/run identity, independent of the future code SHA:

1. Freeze the agent content needed for this commit: identity, current turn, prompt, available response/chat, and the required referenced payload. Run the existing publication protection checks. Mark host finalization as pending where appropriate. A precreated empty page, or an old session page with no current-turn content, is insufficient.
2. Prepare and publish that exact snapshot to the agents repository. Prefer one bounded transaction for its prompt archive and agent page. Verify that the intended remote contains the snapshot and required objects at a specific sidecar SHA. Keep that revision reachable under a retention policy.
3. Persist a host-authored **publication proof record** identifying the project, remote repository, agent/session and current run, page path, sidecar SHA, snapshot digest, and publication contract version. It must prove this operation's snapshot, not merely that some publication once succeeded. This is a proposed new proof type, not SASE's existing ToolRun verification receipt.
4. Construct the commit's linked agent tag from that proof. Only then let the VCS provider create the code commit and push it. Queue later code-SHA backlinks, terminal status, finalizer logs, and broader derived views separately.

For the strongest historical reference, link the code commit to `blob/<verified-sidecar-SHA>/<page-path>`. GitHub documents these as links to a specific immutable file version. The snapshot can also offer a link to the live session page for later updates. Retention, access control, and repository existence remain operational prerequisites. [GitHub permalink documentation](https://docs.github.com/en/repositories/working-with-files/using-files/getting-permanent-links-to-files).

If “live” specifically means the GitHub HTML page, add a bounded readiness probe of that exact permalink before authorizing the code commit, using the intended access level. For public provenance, an authenticated writer's success does not establish anonymous access. Check identity/content and avoid treating a login redirect's HTTP 200 as the agent page. This narrows serving-path uncertainty at publication time; it cannot promise all future requests succeed. These URLs are GitHub repository file views, so waiting for a GitHub Pages deployment would target the wrong subsystem.

The safety argument is short: the only transition that creates a linked code commit requires a matching verified publication proof; unknown or failed publication has no transition to commit creation. Crashes before proof leave work pending. Crashes after publication but before commit leave an unused snapshot. A retry re-observes remote state and resumes idempotently. None of those paths needs to produce a code commit pointing to an unpublished snapshot. This is conditional on enforcing the boundary on every relevant SASE commit path and retaining the referenced publication; arbitrary manual commits outside SASE are outside that guarantee.

**Simply moving today's publication call earlier will not work.** Primary-scope outbox rows are keyed by the created code SHA, and the Rust completion policy requires that SHA in the published run/session's commit association. October 24's [`02cd3b39b6`](https://github.com/sase-org/sase/commit/02cd3b39b64358f37b2fa097f0ebfa1db2960e53) corrected rows that mistakenly used the pre-dispatch HEAD. Do not reintroduce that bug by substituting the old HEAD for a future commit. The new precommit operation needs its own identity and fulfillment predicate; preserve the existing post-commit revision-association obligation for subsequent enrichment. Linked-repository publication currently has a weaker page-only scope, which must not be mistaken for proof of fresh current-turn content. [Rust fulfillment policy](https://github.com/sase-org/sase-core/blob/55532e2d878dfc5415bdd695a1978cc5c5fb5a3c/crates/sase_core/src/agent_publication_recovery/complete.rs).

Likewise, a precommit barrier cannot wait for a `done.json` that the host writes only after commit finalization. Capture the provider's finished output before host completion, publish a truthful pending-finalization snapshot, and update the terminal state afterward. A fully final page including successful commit/push results cannot truthfully precede those events. Precomputing a Git hash is not a general escape: amendments, rebase retries, signatures, and message changes can change it; mutually embedding the final code and sidecar hashes also creates a circular dependency.

The publication predicate, proof schema, and transition rules belong in `sase-core`, with bindings and the SASE revision pin updated together. Python should orchestrate Git/network I/O and call that policy. The host finalizer and VCS provider paths need enforcement, including resume, PR creation, linked/sidecar repositories, and any automatic commit path that emits a linked `SASE_AGENT` footer. Agent-side instructions alone cannot enforce the invariant. Publication's own infrastructure commits must not recursively require the snapshot they are publishing; keep their existing infrastructure attribution separate or use a previously proven target.

**There are meaningful speedups that preserve the barrier.** Their sizes need measurement after the persistent replay failure is repaired.

| Change | Why it can save time without weakening ordering |
| --- | --- |
| Publish required content early and overlap preparation with independent verification | The commit waits only for the unfinished tail, then checks the exact frozen snapshot. Rebuild or revalidate if relevant inputs change. |
| Publish prompt archive and required agent content in one transaction | Inline currently has separate prompt and hood pull/commit/push paths; the queued transaction already prepares deferred prompts alongside hood data. Consolidation can remove duplicate network trips. |
| Limit the critical path to this commit's required snapshot | Current drains can select up to 25 requests and publish whole hoods. Unrelated backlog and sibling content should not determine whether this commit's own page is ready. |
| Reuse an already published immutable snapshot when its exact identity and bytes match | Avoid repeating render/scan/upload work. A heartbeat, old session page, or local file alone is not adequate evidence. Remote/retention assumptions still apply. |
| Keep a warm, serialized publisher per sidecar; use bounded batching for simultaneous callers | Amortize startup and Git work while each caller waits for its own proof. A background worker is compatible with synchronous dependency enforcement. Bound batching delay. |
| Move optional shared indexes, reverse links, and post-commit metadata off the critical path | A direct immutable page link need not wait for every project-wide navigation view. Include every asset needed to read that snapshot in the required set. |

As a latency model, if required publication takes `P`, can start `A` time before code creation is otherwise ready, and creating/pushing code takes `C`, the added publication wait can approach `max(0, P - A)` rather than all of `P`. This is an explanatory model, not a measured prediction. There is no finite completion-time guarantee when the publication service is unavailable; strict safety means waiting or failing without making the linked commit.

Existing performance work should be preserved. The October 21 change [`54779b62f5`](https://github.com/sase-org/sase/commit/54779b62f57805fbec295240f4de7201c87a4376) reports reducing a quadratic inventory operation from 8,689 registry rebuilds to one, inventory time from 106–148 seconds to about 23 seconds, and total time to about 30 seconds. Those are the commit author's historical measurements, not measurements reproduced here. Targeted inventory and payload generation also landed before the background default. This history demonstrates that algorithmic improvements can reduce real work instead of only moving the wait elsewhere.

The repeated replay failures suggest another avenue: shared derived Markdown should be regenerated from authoritative owner content on a fresh remote base, rather than repeatedly replaying a stale derived-page commit. Existing recovery already distinguishes these categories. Automating that safely would require preserving unique owner snapshots and append-only objects and refusing genuine conflicting authoritative edits; blindly dropping the failed commit would be unsafe. A local publisher lock cannot eliminate writes from another machine.

**Choose the contract explicitly.**

| Option | Meets publication before code commit creation? | Assessment |
| --- | --- | --- |
| Existing background default | No | Fast return, but missing pages are an allowed state. |
| Existing `mode: inline`, or reverting only the enqueue change | No | Shortens the normal missing-page window; still post-commit and best-effort. |
| Strict precommit snapshot publication, then background enrichment | Yes, under the stated storage/retention assumptions | Recommended balance of trustworthy provenance and limited critical-path work. |
| Create code locally, publish a commit-associated snapshot, then push code | No for local readers; can satisfy publication before remote exposure | Reasonable if the user explicitly relaxes “before the actual commit” to “before push.” Requires splitting today's combined dispatch and handling rebases. |
| Keep an unlinked global agent ID when publication is unavailable | Avoids advertising a broken hyperlink, but does not supply a published page | Possible explicit offline policy, not a silent fallback for strict mode. |

I would not broadly revert the publication subsystem: that would risk losing recovery, protection, diagnostics, and performance fixes, while retaining the original ordering flaw. A temporary switch to `inline` can be a deliberate mitigation after diagnosing the current sidecar state, but it should be described honestly as best-effort post-commit publication. With the sampled SASE repository failure unresolved, it could add repeated foreground waits while still returning with a queued page.

Keep existing outboxes and checkpoints during a forward migration. Outstanding primary-SHA requests still represent real publication obligations. A new precommit proof must not acknowledge them merely because a page exists, and legacy resume must not create a duplicate code commit that was already made under the old contract. Old commits with missing pages need publication repair, not history rewriting to pretend the pages preceded them.

**Evidence required before calling a replacement complete.** Test the boundary itself, rather than only checking pages after the helper returns:

- At the instant the primary provider would invoke `git commit`, independently read the sidecar remote and verify the exact linked snapshot, current run, and required objects. At primary push, repeat the externally visible ordering assertion.
- Inject lock, credential, timeout, validation, push, and HTTP-readiness failures. Verify that no new linked primary commit is created; the pending operation remains resumable.
- Simulate accepted sidecar push with lost acknowledgment, and crashes between every publication/proof/commit step. Retrying must neither duplicate a code commit nor treat an unverified publication as successful.
- Cover an old session page missing the current turn, solo-to-session identity changes, multiple repository commits, PR creation, resume, and a primary rebase after snapshot publication.
- Exercise two-machine sidecar contention, lost worker wakeups, stale proof records, changed snapshot bytes, withheld content, and publication success followed by primary commit failure. Required content that cannot be safely published must block strict mode or follow an explicitly chosen redaction policy.

Measure healthy and failed operations separately: time until the page is verified, time until the code commit is created, time until primary push, and time until host completion. Preserve per-stage timings and report p50/p95 with sample sizes, payload sizes, queue depth, and failure classes. The current retained failure-only SASE sample cannot justify a performance target.

The decision I recommend is therefore concrete: **make publication a prerequisite for the linked commit, preserve asynchronous enrichment, and repair the persistent sidecar failure independently.** That gives the ordering guarantee the user wants without treating all asynchronous work as the problem, or promising an impossible guarantee of permanent Internet availability.
