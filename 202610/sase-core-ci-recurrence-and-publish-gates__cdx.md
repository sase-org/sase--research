# Why sase-core CI keeps failing, and where to prevent recurrence

Independent research by **cdx**, 2026-10-29. No other report or researcher findings from this swarm were consulted.

**Recommendation:** repair the remaining cache-consistency failure, preserve the SQLite deadline fix already landed, and enforce verification at the **final candidate before push / merge**. Use the existing full workspace check for local feedback and required Linux/macOS CI checks to protect `master`. A Git `post-commit` hook is unsuitable as the enforcement point.

## Evidence and scope

I inspected the latest **100 `CI` workflow runs triggered by pushes to `master`**, from **2026-10-12 19:38:00 UTC through 2026-10-29 02:35:46 UTC**. At collection, **68 succeeded and 32 failed**. These are workflow-run counts, not job counts or unique regressions. Release-PR runs were excluded from that denominator, since counting them alongside master pushes would count many of the same failures twice.

For all 32 failed runs, I read job status, failed steps, and failed-job logs. I also inspected the local repository and relevant historical diffs at:

- `sase-core`: `cd62c83df285e70a43fb5fa215a5a95367c8c32d`.
- `sase`: `e59d4255aef192fd4931f03fc2cd1443503c68a1`, for commit/finalizer behavior.
- `sase-github`: `e4f8bf47c8b0e89b3b46b35369e3574fcf97d0ed`, which inherits the common Git commit implementation.

GitHub's connector supplied job metadata and logs. Read-only `gh` queries supplied repository-wide run enumeration, attempt metadata, and branch protection state. Repositories were opened through `sase repo open`; their source/history was read locally. No builds, test reruns, hooks, repository settings, or application code were changed.

The counts use the latest outcome for each run. One successful run in the sample, `39146142422`, had reached attempt 2; all remaining sampled runs were attempt 1. Thus 32% is a **latest-outcome failure rate**, not a first-attempt failure rate. The sample is recent history, not the repository's lifetime rate.

At collection, GitHub reported `master.protected = false`, no repository rulesets, and master at the inspected core SHA. See the [branch metadata endpoint](https://api.github.com/repos/sase-org/sase-core/branches/master) and [rulesets endpoint](https://api.github.com/repos/sase-org/sase-core/rulesets); these are live state, while the values above are this report's observation.

## What actually failed

| Failure class | Distinct failed master runs containing it | What the logs showed | Local hook's likely coverage |
| --- | ---: | --- | --- |
| SQLite WAL setup deadline | 10 | macOS elapsed time exceeded the timeout test's 425 ms bound | A Linux pass alone is insufficient |
| Cache-consistency / freshness verification | 6 | Linux `concurrent_readers_see_consistent_snapshots` ended with “cache is stale: the next read rebuilds” | Intermittent detection; needs diagnosis and a deterministic regression |
| Stale plan wire fixture | 6 | Both platforms disagreed over newly added `proposed_with: null` | Full workspace tests should detect it |
| Clippy lint | 3 | Both platforms rejected constant-size `chunks_exact(3)` | Matching-toolchain Clippy should detect it |
| macOS FFI compilation | 2 | `mode_t` type mismatch, then invalid `u16` variadic argument | Native macOS compilation required |
| macOS filename fixture | 2 | Writing a non-UTF-8 filename failed with EILSEQ | Native macOS testing required |
| Invalid GitHub Action reference | 3 | Could not resolve `astral-sh/setup-uv@v10` during job setup | Workflow-specific validation can detect the bad reference policy |
| Overbroad secret-redaction assertion | 1 | Asserted the entire serialized record did not contain `abc` | Intermittent; repair the test's sentinel/assertion |

Counts sum to **33 signatures across 32 runs** because run `40684718736` had both the macOS WAL failure and Linux cache failure.

By failed step, **24 runs failed tests, 5 failed Clippy/compilation, and 3 failed job setup**. None of these 32 failed in formatting, feature-unification checking, wheel smoke, or the release helper test body. That does not prove those gates can never fail; it identifies the observed problem rather than assuming it is mainly formatting.

### The most recent streak is mostly two persistent failures

The WAL test, `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget`, failed in **ten consecutive master push runs** beginning at `3f8baa7984`. Observed durations ranged from approximately **746 ms to 1.226 s**, against a **250 ms budget plus 175 ms scheduling allowance**. Other tests and Ubuntu's equivalent job generally passed. Representative [first run](https://github.com/sase-org/sase-core/actions/runs/40588317685/job/122485612357) and [last run before the fix](https://github.com/sase-org/sase-core/actions/runs/40794754688/job/123188389545).

This has an important implementation explanation. SQLite's built-in busy timeout accounts for accumulated sleeping; it is not a strict elapsed-time deadline across all operations. The old code combined SQLite busy timeouts with an outer elapsed-time budget. Commit [`0fd85e4a`](https://github.com/sase-org/sase-core/commit/0fd85e4ab6e61ab0aec9be6b85cdb0026e71816c) changes the connection to use a custom busy handler with one absolute `Instant` deadline and adds a deterministic scheduler-oversleep test. This is a substantive correction, not merely a looser assertion. [SQLite busy-timeout contract](https://www.sqlite.org/c3ref/busy_timeout.html), [busy-handler contract](https://www.sqlite.org/c3ref/busy_handler.html).

**That fix is already in the inspected master.** The three subsequent master CI runs have passing macOS jobs. Two still conclude red because of the independent Linux cache failure. Three successes are encouraging evidence, not a long-term reliability guarantee; the integration test still has a wall-clock bound.

The cache test appears in six sampled failures, including the newest [run `40807288117`](https://github.com/sase-org/sase-core/actions/runs/40807288117/job/123229151224). Its actual failure is the final `assert!(verify.compared)` at line 934, **after** its snapshot-membership and parity assertions. This distinction matters: these logs do not show that the test observed incorrect issue contents; they show that the cache verifier declined to compare because its freshness probe was stale.

The source's `probe_with` can report stale when the token changes, the manifest is missing, or stored stream signatures fail to match. That narrows the investigation but does not identify which branch occurred. Add diagnostic capture for those conditions and a controlled concurrency schedule before deciding whether the defect is cache publication, invalidation, test setup, or an overly strong verification expectation. A stale cache can be a legitimate fallback state, but recurring unexpected staleness after the test's parity reads warrants investigation. Do not simply remove the assertion.

This signature was already present on October 13, before the October 26 change that consolidated integration tests into one binary. Consolidation may change scheduling and exposure, but it cannot be the original cause. It also recurs after October 18's freshness-stamp CAS fixes. Sources: [current test](https://github.com/sase-org/sase-core/blob/cd62c83df285e70a43fb5fa215a5a95367c8c32d/crates/sase_core/tests/integration/bead_read_model_parity.rs#L868), [verifier and freshness probe](https://github.com/sase-org/sase-core/blob/cd62c83df285e70a43fb5fa215a5a95367c8c32d/crates/sase_core/src/bead/read_model/store.rs#L470), [October 13 failure](https://github.com/sase-org/sase-core/actions/runs/38439181389/job/115440988219).

**Classification caution:** I did not rerun an unchanged SHA to demonstrate fail-then-pass behavior. The cache signature is intermittent across the sampled history and plausibly concurrency-dependent; this report does not certify it as a harmless flake.

### Some failures are exactly what a local full gate should catch

The plan parity fixture remained red for six successive pushes on October 17. The implementation emitted `proposed_with: null`; the expected JSON omitted it. Commit [`da22713e`](https://github.com/sase-org/sase-core/commit/da22713e71a91545c0e48eb2e16797c7165d115b) added the missing expectation and the next master run passed. Both Linux and macOS caught the discrepancy. Representative [failure](https://github.com/sase-org/sase-core/actions/runs/38997640825/job/117293590620).

Three later pushes failed the same Clippy diagnostic in `project_stats/snapshot/attributes.rs`: constant-size `chunks_exact(3)`. Since Clippy runs with `-D warnings`, that is a failing gate even if ordinary compilation succeeds. Representative [failure](https://github.com/sase-org/sase-core/actions/runs/39037820472/job/117411101419).

These are strong candidates for prevention by an enforced full local check **on the tree actually published**. The CI logs do not establish that individual agents skipped checks: a narrower check, an older toolchain, a check before the last edit, or a subsequent rebase could all explain a local/CI mismatch. I did not inspect agent transcripts or historical local tool receipts, so attribution to any one of those causes would be speculation.

### A Linux hook cannot prove macOS compatibility

Two successive compilation failures came from Unix FFI differences in mobile pairing: first `mkdirat`/`fchmod` parameter types, then passing a `u16` mode to variadic `openat` without C's required integer promotion. These were compile errors surfaced during the macOS Clippy step, not style warnings. [Type-mismatch job](https://github.com/sase-org/sase-core/actions/runs/39052497949/job/117453740961), [variadic-argument job](https://github.com/sase-org/sase-core/actions/runs/39071468633/job/117509805463).

The non-UTF-8 filename test similarly assumed that bytes representable in Git trees could be created on the host filesystem. macOS rejected the write with “Illegal byte sequence.” Commit [`80dc704a`](https://github.com/sase-org/sase-core/commit/80dc704a4f2e1f640f7caa9e578957669c31367d) changed the fixture to stage the raw filename directly in Git's index. The preserved contract is committed-tree behavior, without requiring the filesystem to accept the filename. [Failure](https://github.com/sase-org/sase-core/actions/runs/39128445283/job/117678435605).

Retain native macOS coverage. Cross-compilation can catch some type differences, but cannot establish filesystem or scheduling behavior.

### Workflow mistakes and infrastructure are different problems

Three October 19 runs failed before helper tests started because `astral-sh/setup-uv@v10` could not be resolved. The current workflow uses `v10.3.0`, and `.github/scripts/test_workflow_action_pins.py` now checks for exact setup-uv release tags or full commit SHAs. That validation is already included in the local `script-test` gate. It checks the reference's shape/policy, not whether every syntactically valid tag exists. [Failed setup](https://github.com/sase-org/sase-core/actions/runs/39272030360/job/118126542197), [current regression check](https://github.com/sase-org/sase-core/blob/cd62c83df285e70a43fb5fa215a5a95367c8c32d/.github/scripts/test_workflow_action_pins.py).

The old redaction test searched all serialized JSON for the short string `abc`, which can occur in unrelated identifiers or digests. October 18's [`0834d844`](https://github.com/sase-org/sase-core/commit/0834d8446a6baf62ef76208e134bc220a7f4a07e) replaces it with a distinctive sentinel. The failure alone does not demonstrate a real secret leak. [Failure](https://github.com/sase-org/sase-core/actions/runs/38997344710/job/117292684695).

There is also genuine runner starvation, outside the 32 failures above. Release-plz run [`40346929251`](https://github.com/sase-org/sase-core/actions/runs/40346929251) attempt 1 had a cancelled macOS wheel job with `runner_id: 0`, no runner name, and no steps. The existing retry workflow handles only this narrow infrastructure-only case and caps retries. Keep that separation; a test failure is not evidence of runner starvation.

Release failures can also be downstream symptoms: [Release-plz run `40706057331`](https://github.com/sase-org/sase-core/actions/runs/40706057331/job/122878938806) failed its merge step with `CORE_CUT_RED`, pointing to a red macOS CI job on the release PR. Counting that as another independent code defect would exaggerate the number of underlying problems.

## Existing defenses, and their limits

The repo already has a useful canonical gate:

```text
sase tool run check
  -> just check
  -> scripts/check.sh all
  -> fmt-check + features + clippy + workspace tests + release-script tests
```

`scripts/check.sh` also resolves Python >=3.12 for PyO3, sets the libpython search path, and runs Rust tests without ambient Git identity/config or `SASE_*` overrides. These address real historical gaps documented in `AGENTS.md`. A selected-crate test or `just fast` is an iteration tool, not the whole gate. Sources: [instructions](https://github.com/sase-org/sase-core/blob/cd62c83df285e70a43fb5fa215a5a95367c8c32d/AGENTS.md), [check script](https://github.com/sase-org/sase-core/blob/cd62c83df285e70a43fb5fa215a5a95367c8c32d/scripts/check.sh), [CI workflow](https://github.com/sase-org/sase-core/blob/cd62c83df285e70a43fb5fa215a5a95367c8c32d/.github/workflows/ci.yml).

However:

1. **Local checking does not cover the whole CI environment.** The local all-gate does not build/install the manylinux wheel, run twine, resolve GitHub Actions, or run a second operating system.
2. **The toolchain is not numerically pinned.** `rust-toolchain.toml` says `channel = "stable"`, despite the workflow step's “Read pinned toolchain” name. The inspected host and newest CI log both report Rust 1.99.1, so I did not observe a present mismatch. A moving channel still allows future Clippy drift. An explicit Rust version and deliberate updates would make local/CI equivalence easier to establish. [Rustup toolchain files and precedence](https://rust-lang.github.io/rustup/overrides.html).
3. **Instruction-based verification is not mandatory publication evidence.** Ordinary SASE final submission can record verification provenance as `unverified`. Core's named check currently declares `stages: none`; prepared completion expects `stages: run_silent`. Therefore it would be inaccurate to claim that a ready-made mandatory, stage-backed full-check completion gate already protects every core commit. [Core tool definition](https://github.com/sase-org/sase-core/blob/cd62c83df285e70a43fb5fa215a5a95367c8c32d/sase/sase.yml), [ordinary declaration provenance](https://github.com/sase-org/sase/blob/e59d4255aef192fd4931f03fc2cd1443503c68a1/src/sase/finalizers/declaration.py#L124), [prepared stage resolution](https://github.com/sase-org/sase/blob/e59d4255aef192fd4931f03fc2cd1443503c68a1/src/sase/finalizers/_prepare_completion.py#L322).
4. **Master accepts changes before CI establishes safety.** GitHub reported it unprotected. One persistent defect then makes unrelated subsequent commits and release PR updates red.

These are coverage and enforcement gaps; installing another formatter would not address most observed failures. I did not audit every machine's merged hook configuration, so this is not a claim that no developer has a local hook.

## Which hook would help?

Git's `post-commit` runs after commit creation and cannot veto it. `pre-commit` can reject a commit; `pre-push` can reject a push and receives the proposed ref updates. Local hooks require installation/configuration and remain a client-side control. [Git hook semantics](https://git-scm.com/docs/githooks).

SASE has its own configurable `commit_hooks.before` and `commit_hooks.after`, but their ordering creates a further distinction:

- The **before hook** runs before VCS dispatch. The Git provider then stages, commits, amends bead changes, fetches/rebases onto the remote default branch, and pushes. A successful before-hook check can therefore cover a different tree from the published one.
- The **after hook** runs after dispatch; the code explicitly warns that the commit may already be pushed. It is suitable for follow-up reporting, not prevention.
- The Git push retry loop rebases and retries after any push failure. A failing pre-push verification hook could therefore cause repeated expensive checks, or another rebase, unless failure handling distinguishes verification rejection from a remote-update race.

Sources: [before-hook ordering](https://github.com/sase-org/sase/blob/e59d4255aef192fd4931f03fc2cd1443503c68a1/src/sase/workflows/commit/workflow.py#L250), [after-hook warning](https://github.com/sase-org/sase/blob/e59d4255aef192fd4931f03fc2cd1443503c68a1/src/sase/workflows/commit/workflow.py#L517), [commit and push implementation](https://github.com/sase-org/sase/blob/e59d4255aef192fd4931f03fc2cd1443503c68a1/src/sase/vcs_provider/plugins/_git_commit_dispatch.py#L464), [retry loop](https://github.com/sase-org/sase/blob/e59d4255aef192fd4931f03fc2cd1443503c68a1/src/sase/vcs_provider/plugins/_git_commit_dispatch.py#L297).

A short pre-commit formatting check can improve feedback. The useful enforcement location is **after final content changes/rebase, immediately before publication**. A host-owned gate belongs there; a thin Git pre-push hook can cover manual pushes using the same validation entry point.

Implementation requirements for that proposal:

- Validate the actual candidate commit/ref, not whatever happens to be checked out. For a first implementation, reject an unsupported non-HEAD candidate or dirty checkout explicitly rather than silently testing the wrong files.
- Run the canonical full workspace gate, preserving its Python setup and hermetic test environment. Do not replace it with a changed-crate guess.
- After another rebase or content mutation, verification is stale and must run against the new candidate.
- A failed verification leaves a durable, unpushed commit and clear diagnostics; it must not be misclassified as a network/non-fast-forward failure.
- Install any hook through managed workspace setup for all ephemeral core clones. A hook in one `.git/hooks` directory does not establish coverage elsewhere. Avoid a global all-repository Cargo hook.
- Integrate with SASE's recorded tool execution and existing timeout/recovery machinery. Do not start untracked background checks from a post-commit shell.
- Initially rerun when needed; do not introduce cross-tree test-result reuse. If verification evidence is later used, it must bind the repository, final tree, command, configuration, and toolchain, with explicit invalidation. Existing receipts are not blanket permission to skip execution.

These are proposed requirements, not implemented or verified functionality.

## Failure ledger

The following ledger makes the 32-run count auditable. “Cache” denotes the final cache-verification failure, “WAL” the macOS deadline test, and “fixture” the plan-wire parity mismatch.

| UTC date | CI run | Commit | Failure signature |
| --- | --- | --- | --- |
| 2026-10-29 | [40807288117](https://github.com/sase-org/sase-core/actions/runs/40807288117) | `cd62c83df2` | Cache |
| 2026-10-29 | [40797498289](https://github.com/sase-org/sase-core/actions/runs/40797498289) | `0fd85e4ab6` | Cache |
| 2026-10-29 | [40794754688](https://github.com/sase-org/sase-core/actions/runs/40794754688) | `df14e8f438` | WAL |
| 2026-10-28 | [40726794062](https://github.com/sase-org/sase-core/actions/runs/40726794062) | `ed8328f91e` | WAL |
| 2026-10-28 | [40701185834](https://github.com/sase-org/sase-core/actions/runs/40701185834) | `65546fd244` | WAL |
| 2026-10-28 | [40684718736](https://github.com/sase-org/sase-core/actions/runs/40684718736) | `49870f00ec` | WAL + Cache |
| 2026-10-28 | [40663209632](https://github.com/sase-org/sase-core/actions/runs/40663209632) | `00fe29d543` | WAL |
| 2026-10-28 | [40649399409](https://github.com/sase-org/sase-core/actions/runs/40649399409) | `f4bf6074cc` | WAL |
| 2026-10-28 | [40633962628](https://github.com/sase-org/sase-core/actions/runs/40633962628) | `31deb0d2ff` | WAL |
| 2026-10-28 | [40620928157](https://github.com/sase-org/sase-core/actions/runs/40620928157) | `6613c9bb91` | WAL |
| 2026-10-28 | [40611440803](https://github.com/sase-org/sase-core/actions/runs/40611440803) | `83b010ddbe` | WAL |
| 2026-10-27 | [40588317685](https://github.com/sase-org/sase-core/actions/runs/40588317685) | `3f8baa7984` | WAL |
| 2026-10-27 | [40434321453](https://github.com/sase-org/sase-core/actions/runs/40434321453) | `f1ea08fbde` | Cache |
| 2026-10-27 | [40424599394](https://github.com/sase-org/sase-core/actions/runs/40424599394) | `03dce1f20b` | Cache |
| 2026-10-19 | [39289328389](https://github.com/sase-org/sase-core/actions/runs/39289328389) | `f0f2275f9d` | Action reference |
| 2026-10-19 | [39276644215](https://github.com/sase-org/sase-core/actions/runs/39276644215) | `a908ceb30c` | Action reference |
| 2026-10-19 | [39272030360](https://github.com/sase-org/sase-core/actions/runs/39272030360) | `9876b3ae55` | Action reference |
| 2026-10-18 | [39128445283](https://github.com/sase-org/sase-core/actions/runs/39128445283) | `99b10bd062` | macOS filename |
| 2026-10-18 | [39089582114](https://github.com/sase-org/sase-core/actions/runs/39089582114) | `72bf920375` | macOS filename |
| 2026-10-17 | [39071468633](https://github.com/sase-org/sase-core/actions/runs/39071468633) | `dd56b94a8a` | macOS FFI |
| 2026-10-17 | [39052497949](https://github.com/sase-org/sase-core/actions/runs/39052497949) | `916d5e3a64` | macOS FFI |
| 2026-10-17 | [39047734666](https://github.com/sase-org/sase-core/actions/runs/39047734666) | `3b3b740124` | Clippy |
| 2026-10-17 | [39047107362](https://github.com/sase-org/sase-core/actions/runs/39047107362) | `bbef21d021` | Clippy |
| 2026-10-17 | [39037820472](https://github.com/sase-org/sase-core/actions/runs/39037820472) | `733256ede9` | Clippy |
| 2026-10-17 | [39019404346](https://github.com/sase-org/sase-core/actions/runs/39019404346) | `7dc6f6ce25` | Plan fixture |
| 2026-10-17 | [39013647585](https://github.com/sase-org/sase-core/actions/runs/39013647585) | `8df5efda95` | Plan fixture |
| 2026-10-17 | [39006975016](https://github.com/sase-org/sase-core/actions/runs/39006975016) | `be2bfbee12` | Plan fixture |
| 2026-10-17 | [39001186192](https://github.com/sase-org/sase-core/actions/runs/39001186192) | `855ed4c378` | Plan fixture |
| 2026-10-17 | [38999201302](https://github.com/sase-org/sase-core/actions/runs/38999201302) | `b0cd62b931` | Plan fixture |
| 2026-10-17 | [38997640825](https://github.com/sase-org/sase-core/actions/runs/38997640825) | `305b7b808a` | Plan fixture |
| 2026-10-17 | [38997344710](https://github.com/sase-org/sase-core/actions/runs/38997344710) | `ac370734cb` | Redaction assertion |
| 2026-10-13 | [38439181389](https://github.com/sase-org/sase-core/actions/runs/38439181389) | `d30e1337a8` | Cache |

## Recommended solution

**Adopt a layered publication gate, with repair of the recurring failures first.**

1. **Stabilize the signal.** Keep `0fd85e4a`'s SQLite wall-clock deadline fix and observe its macOS results. Give the remaining cache signature a focused investigation with freshness diagnostics and deterministic concurrency tests. Preserve content/parity assertions; avoid blanket retries, ignores, or arbitrary timeout inflation. Keep the already-landed fixture, redaction, platform, and action-pin fixes.
2. **Enforce the existing local gate on the final publish candidate.** Add a repo-specific host-owned verification step after rebase and before push, plus a thin pre-push adapter for manual use. Use `sase tool run check` in agent workflows. Make failure leave work durable and unpushed, and prevent the push retry loop from treating verification rejection as remote contention. Pin the Rust version deliberately.
3. **Protect master with the existing cross-platform CI jobs.** Route core changes through a host-managed candidate branch/PR and require the Linux Rust checks, macOS Rust checks, release-script tests, and wheel smoke to pass before updating master. Require the candidate to be current with master, and avoid routine bypasses for the agents/release automation whose changes need checking. GitHub supports required checks and up-to-date-branch enforcement; configuring that requires adapting the current direct-push workflow, not merely toggling protection while leaving the publisher unchanged. [GitHub protected-branch behavior](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
4. **Track signatures and prevention outcomes.** Record first failing SHA, affected OS, exact failed test/step, fix SHA, and subsequent unchanged-SHA pass/fail evidence. Measure repeated failures per signature, local-gate escapes, and time from first red to repair. Keep runner-starvation retries separate.

Validate the rollout with deliberate bad candidates: a stale wire fixture, a Clippy violation, a missing/invalid action reference, a macOS-only compile error, and a candidate changed by rebase after a passing local check. Verify that local failures stop publication, macOS-only failures cannot advance master, and failed checks leave recoverable commits. Exercise those checks in both a primary core workspace and a linked core workspace.

The measured history supports this priority: **most recent failures are repeated test/platform problems, while several older failures are deterministic omissions a full local gate could catch.** Repair those defects, make the final candidate's verification mandatory, and use native CI as the cross-platform authority before master advances. A post-commit hook alone would move detection around without closing the main gaps.
