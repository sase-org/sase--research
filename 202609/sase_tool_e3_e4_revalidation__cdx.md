# Revalidating `sase tool` E3 and E4 after E2

**Research date:** 2026-09-24  
**Scope:** Independent review of E3 (failure triage) and E4 (receipts and staged reuse) in the [`sase tool` epic roadmap](sase_tool_epic_roadmap/sase_tool_epic_roadmap.md), using the landed E1/E1.5 implementation, the nearly complete E2 implementation, the current `sase`/`sase-core` code, and the live ToolRun corpus.

## Executive conclusion

Both epics are still appropriate, but neither should be implemented exactly as the original roadmap describes.

1. **Land E3 first, as “failure facts and honest triage.”** Its primary result should be durable, versioned failure facts and defensible classifications. It must admit `UNKNOWN`; it must not turn incomplete baseline evidence into a confident `NEW` or `KNOWN` label.
2. **Then land a narrower E4, as “verification receipts and exact whole-tool reuse.”** The first release should reuse only complete, successful, non-mutating, whole-tool verification results under an exact applicability key. It should not yet reuse individual stages, change E2 handoff timing, or make `just install` a no-op.
3. **Do not run the E3 and E4 implementations concurrently on the same hot paths.** Both require changes to the Rust wire/store contract, ToolRun settlement, catalog expansion, CLI parsing, and completion tests. E4 should consume the stable stage identity and failure semantics established by E3.

This is a sequencing correction to the roadmap, not a rejection of its direction:

```text
E2 durable handoff
       |
       v
E3 durable failure facts + classification + immutable reruns
       |
       v
E4 whole-tool verification receipts + exact reuse
       |
       v
successor epic: stage DAG/reuse, inline preflight, install postconditions
```

## Why the roadmap needs updating

The original roadmap was written before the actual E1, E1.5, and E2 contracts settled. Several premises have since changed.

### The substrate is real and heavily used

E1 (`sase-135`) and E1.5 (`sase-16h`) are closed. They delivered the ToolRun catalog/store, stage events, fingerprints, adoption reporting, guarded recipes, monitor wrapping, and wrapper-fidelity enforcement. E2 (`sase-17p`) has landed phases 1–5 and is completing acceptance/flag removal around reserve → bind → adopt → acknowledge handoff.

A snapshot of the live ledger on 2026-09-24 contained:

| Measure | Observed |
|---|---:|
| ToolRuns | 638 |
| Agent-attributed runs | 621 |
| Failed | 490 |
| Lost | 24 |
| Signaled | 14 |
| Succeeded | 110 |
| Failed wall time | 55.9 h |
| Successful wall time | 6.6 h |
| Named `check` runs | 556 |
| Runs with a complete clean-tree failure fingerprint | 21 |
| Runs with an attempt number greater than 1 | 0 |

The top recorded failing stages were Symvision (239 stage failures), mypy (78), scoped tests (56), ruff (41), Python formatting (19), pyscripts (17), and feature-flag validation (14). The immediate operational pain is therefore failure interpretation and recovery, not lack of cached successes.

The roadmap's claim that E3 is an adoption vehicle for “built-but-unused” monitor machinery is now stale. Adoption is already enforced by E1.5, and E2 owns durable monitor handoff. E3 should justify itself through better failure facts and decisions.

### Current stage data is execution-local, not reusable identity

The current ToolRun stage record contains a randomly generated `stage_id`, description, timing, exit status, output byte offsets, completeness, and bounded diagnostics. It does **not** contain:

- a stable catalog stage key;
- a normalized failure identity or normalizer version;
- reference/baseline classification evidence;
- a retry-chain link; or
- declared stage inputs and outputs.

The random ID is correct for addressing one execution, but it cannot identify “the same stage” across runs. E3 needs an optional stable `stage_key` before either cross-run classification or future stage reuse can be sound.

### The current fingerprints are necessary but not sufficient for E4

The catalog declares only four file inputs for `check`, `check-full`, and `install`: `Justfile`, `pyproject.toml`, `uv.lock`, and `sase-core-revision.txt`. `check` additionally records two environment values and a short toolchain list. In reality, verification also consults state such as the feature-flag bead store, selection/coverage baselines, installed plugin/runtime state, and executable/tool versions.

`install` is more problematic: it mutates the virtual environment and depends on the resolved core wheel or local Rust checkout, Cargo state, required-plugin declarations, and installed state. The current input digest cannot prove that installation is already correct.

The live corpus reinforces the concern. Exact repeated successful full-fingerprint groups were found only among a few ad-hoc runs; no named-tool successful exact-fingerprint repetition was present in this snapshot. That is not proof that reuse lacks value, but it means E4 should first measure eligibility in shadow mode rather than commit to a complex stage cache on assumption.

This matches established build-cache practice. Gradle requires cacheable tasks to declare complete inputs and outputs and warns that missing inputs can produce incorrect hits; it also treats path normalization and relocatability as explicit concerns ([Gradle Build Cache](https://docs.gradle.org/current/userguide/build_cache.html)). Bazel action identity similarly depends on the command, inputs, environment, and outputs, and its default test-result policy does not reuse a prior failure ([Bazel remote caching](https://bazel.build/remote/caching), [Bazel command reference](https://bazel.build/reference/command-line-reference)). Pytest's last-failed cache is useful navigation, but it is not proof that a result remains valid ([pytest cache](https://docs.pytest.org/en/stable/how-to/cache.html)).

## Revised E3: failure facts and honest triage

### Epic objective

After any terminal ToolRun, users and agents can retrieve durable, bounded failure facts, compare them only with eligible reference evidence, rerun a reproducible invocation as a new ToolRun, and receive a structured continuation payload that distinguishes new, known, flaky, infrastructure, control, and indeterminate outcomes without overstating certainty.

### Classification model

Do not overload one `NEW`/`KNOWN` bit with several different questions. Persist two axes:

| Axis | Values | Meaning |
|---|---|---|
| `failure_kind` | `verification`, `infrastructure`, `control`, `unknown` | What class of event ended or failed the run? |
| `disposition` | `new`, `known`, `flaky`, `unknown` | What does eligible comparison evidence establish about a verification failure? |

Infrastructure and control events are never called `NEW`. Examples include a missing executable, monitor loss, an explicit stop, timeout, signal, or handoff/protocol failure. They retain their typed terminal cause and normally have `disposition: unknown`.

For a verification failure:

- **`known`** means the same versioned failure signature appears in an eligible reference run.
- **`new`** means an eligible reference run covered the same subject/stage and proves the signature was absent.
- **`flaky`** means the canonical unchanged-input oracle has both a failure and a pass for the same subject. The existing `tests/reproducible_flake_baseline.txt` and `tools/selection_health --fail-on-new-flake` behavior should remain authoritative; E3 must consume or extend it, not create a competing flake database.
- **`unknown`** means the available data cannot support one of the above statements. This is a successful classification outcome, not an error.

An active CI/flake task, a matching task title, or a human label may be supporting context, but it must not by itself turn a signature into `known`. The ToolRun and canonical flake evidence remain the facts; tasks are workflow suggestions.

### Reference eligibility must be explicit

A comparison is eligible only when all required dimensions match or have an explicit compatibility rule:

- tool definition digest and catalog generation;
- invocation/argument digest;
- stable `stage_key`;
- failure-normalizer name and version;
- complete current and reference fingerprints;
- selected baseline SHA and repository identity;
- tool-specific scope and covered subjects; and
- reference provenance (for example the selected merge base, not merely “some run on master”).

The classifier must also know whether the reference run reached and covered the relevant subject:

- If the reference stopped in an earlier stage, it proves nothing about a later-stage failure.
- For a pytest node, absence is `new` only if the reference executed that node or an authoritative full selection containing it.
- A dirty or incomplete reference is not silently promoted to a clean merge-base baseline.
- If no eligible ToolRun exists for the selected merge base, report `unknown` and explain the missing evidence. Do not substitute a nearby run without saying so.

The selected reference and the reason it was eligible must appear in both human and JSON output.

### Durable failure fact contract

Capture normalized facts during ToolRun settlement, while the stage output and typed terminal cause are still available. `sase tool failures` should query stored facts; it should not need to rescan a log that retention may later trim.

At minimum, each failure fact needs:

- ToolRun ID and execution-local `stage_id`;
- optional stable `stage_key` from the expanded catalog;
- producer/parser name and version;
- normalized signature digest;
- bounded, redacted display summary;
- source byte range or diagnostic provenance when retained;
- failure kind and typed terminal cause;
- classification, selected reference run/SHA, and an ordered list of evidence/rejection reasons; and
- schema/normalizer version.

Normalization must be producer-specific and conservative. It may strip ANSI escapes and recognized workspace/temp prefixes, and may normalize volatile PIDs, timestamps, or line numbers only when a semantic identity remains. It must not collapse different test nodes, symbols, diagnostics, commands, or exit causes. Never store a raw secret-bearing command line merely to improve a signature. Different normalizer versions are incomparable unless an explicit migration/reclassification exists.

### Rerun semantics

`sase tool rerun RUN_ID` should create a **new** ToolRun using the source run's frozen invocation. It must never reopen or append an attempt to a terminal ToolRun, because a ToolRun currently has one owner, log, fingerprint sequence, and terminal settlement.

Store an immutable chain:

- `retry_of_run_id` — immediate predecessor;
- `retry_root_run_id` — first run;
- `retry_ordinal` — monotonic position; and
- whether the new run's input fingerprint exactly matches its predecessor.

Only named, explicitly rerunnable tools should opt in initially. Refuse ad-hoc invocations and mutating tools unless their catalog contract later defines safe replay. No automatic retry belongs in E3. A same-input fail → pass pair may be submitted to the canonical flake evidence path; a changed-input pass is useful recovery history but not flake proof.

### CLI and continuation surface

Recommended public commands:

- `sase tool failures [RUN_ID]` — bounded human view plus versioned JSON, including `unknown` reasons;
- `sase tool rerun RUN_ID` — immutable linked rerun with normal `-H` handoff behavior; and
- existing `sase tool show` — includes stable stage keys, failure summaries, references, and retry links.

E2's continuation payload should be extended additively with failure facts and classification. Suggestions for `ci` or `flake` task creation should be fully formed commands with evidence fields, but E3 must never create tasks automatically. A CI suggestion is appropriate only for a confirmed true verification failure; a flake suggestion requires unchanged-input fail/pass evidence.

### Recommended E3 phases

E3 is now **large**, not medium:

1. **Rust failure/stage/retry contract:** additive wire fields/tables, stable stage key, normalizer versions, retry links, compatibility tests.
2. **Capture at settlement:** producer-specific parsing, bounded/redacted summaries, typed kind, persistence before log retention.
3. **Reference and flake classifier:** merge-base selection, coverage eligibility, canonical flake integration, explicit rejection reasons.
4. **Failure query surface:** `failures`, `show`, versioned JSON, retention behavior.
5. **Immutable rerun chains:** frozen invocation, opt-in/refusal policy, handoff integration, same-input evidence.
6. **Continuation and task suggestions:** structured monitor result, CI/flake command generation, no automatic writes.
7. **Acceptance, docs, and cleanup:** compatibility matrix, fixture repository, core revision pin, beta-flag removal.

If partial exposure needs a flag, use one `tool_failure_triage` flag. Off must preserve the old user-visible surface; on enables the complete structured surface. Remove the flag before the epic lands.

### E3 landing criteria

E3 is landed only when all of the following are demonstrated:

- [ ] Every terminal mode—success, verification failure, infrastructure failure, explicit stop, timeout, signal, lost owner, and handoff/protocol failure—has a stable typed representation.
- [ ] Stable `stage_key` and random execution `stage_id` are both present and have distinct documented meanings.
- [ ] At least the first-party pytest, mypy, ruff/format, Symvision, and generic command-exit producers have versioned normalizers with collision/non-collision fixtures.
- [ ] Failure summaries are bounded and redacted, survive log expiration, and remain traceable to retained evidence.
- [ ] A comparable baseline produces deterministic `new`/`known`; an earlier-stopping, incomplete, mismatched-definition, mismatched-argument, mismatched-normalizer, or uncovered baseline produces `unknown` with the exact reason.
- [ ] `flaky` is emitted only for unchanged-input fail/pass evidence recognized by the canonical flake path.
- [ ] `rerun` creates a new ToolRun, preserves the original, freezes the invocation, links root/predecessor/ordinal, and refuses non-opted-in tools.
- [ ] Same-input and changed-input reruns are visibly different and only the former can support flake evidence.
- [ ] Human output, `--json`, `show`, `failures`, and E2 continuation all agree on facts and IDs.
- [ ] CI/flake task commands are suggestions only and satisfy the canonical task-type evidence requirements.
- [ ] Old schema-1 stores and older optional-field readers still work; new readers handle records without E3 fields.
- [ ] The linked `sase-core` change is published and `sase-core-revision.txt` is pinned past it before Python callers rely on the fields.
- [ ] Acceptance uses a controlled fixture repository and does not depend on current master being green or on a naturally occurring failure.
- [ ] The beta flag is removed and user/agent documentation states the evidence limits of every classification.

## Revised E4: verification receipts and exact whole-tool reuse

### Epic objective

For explicitly opted-in pure verification tools, `sase tool run` may replace execution with a prior successful result only when a complete, unexpired applicability proof matches current state exactly. Every reuse is itself auditable as a new ToolRun, every refusal has an explainable reason, and forcing execution is always available.

### Narrow the first landing

The first E4 should include:

- successful whole-tool receipts;
- exact applicability checks;
- shadow eligibility measurement;
- an audited reused ToolRun record;
- `-R/--force` to force real execution; and
- `sase tool receipt TOOL` to explain the candidate, hit, miss, invalidation, or refusal.

Defer these original-roadmap items:

| Deferred item | Why it should not gate E4 |
|---|---|
| Per-stage receipts/reuse | Stages do not yet declare a dependency DAG, inputs, outputs, or safe replay boundaries. E3's stable key is necessary but not sufficient. |
| “Cheap stages inline before handoff” | It changes E2's explicit `-H` immediate-handoff contract and reintroduces split execution/log ownership. Treat it as later latency work. |
| `just install` no-op | Install is mutating and its current fingerprint omits material inputs and postconditions. Raw `just install` is also an intentional bootstrap path outside guarded-tool enforcement. |
| Failure-result reuse | A failure is navigation/evidence, never a reusable success. A later failure should invalidate an older same-key success. |

### Receipt applicability key

Receipt reuse must be catalog opt-in, never a default inferred from a zero exit code. The key and proof need at least:

- project and repository identity;
- tool definition digest/catalog generation;
- frozen argument digest and semantic scope;
- HEAD, index, tracked-tree, untracked, and dirty-content fingerprints as applicable;
- declared file/input digests;
- declared environment values;
- toolchain/executable identities;
- named external-state probes;
- workspace identity for workspace-scoped/dirty receipts;
- receipt policy version and literal per-tool TTL; and
- source ToolRun ID and successful after-fingerprint.

Before enabling `check`, E4 must audit and fingerprint every material dependency, including feature-flag state, selection/coverage/flake baseline inputs, required/installed plugin state when consulted, and the actual Python/Just/Rust-core identities. A dependency can be declared as a file, environment input, toolchain identity, or named probe, but it cannot remain ambient and invisible.

Recommended initial policy:

- Only `check` is eligible in the first release, after the dependency audit.
- Give it an explicit catalog TTL (a conservative starting candidate is one hour); do not invent a global TTL fallback.
- `check-full`, `install`, ad-hoc commands, and mutating tools remain execution-only until separately justified.
- A clean receipt may be tree-scoped and reusable across workspaces only when every normalized key component matches.
- A dirty receipt is exact-content and workspace-scoped; matching HEAD alone is never enough.

### Minting and invalidation rules

A receipt may be minted only when:

1. the tool explicitly opts in as pure verification;
2. execution ended successfully;
3. before and after fingerprints are complete;
4. the observed inputs did not mutate (`mutated_input = false`);
5. all required probes completed; and
6. the successful **after** state supplies the receipt fingerprint.

Never mint from failure, signal, timeout, stop, lost ownership, incomplete fingerprints, ad-hoc execution, or a run whose inputs changed. Never reuse such outcomes.

A later equivalent-key non-success blocks an older success until a later eligible success is recorded. This prevents an old green result from masking a newly observed failure. Expiry is a miss, not deletion; the source ToolRun remains auditable under ordinary retention.

### Reuse is a new audited ToolRun

An eligible reuse invocation must reserve and settle a new ToolRun without spawning a child process. Record at least:

- `execution_mode: reused`;
- `receipt_id`;
- `reused_from_run_id`;
- the freshly observed applicability key;
- eligibility decision and policy version; and
- zero executed stages plus a clear `REUSED` human result.

Do not edit or “reopen” the source run. Reused runs should not contribute zero-duration samples to E6 timing predictions.

Revalidate repository observations immediately before recording reuse. If state drifts during the check, refuse reuse and execute (or report an explicit unstable-state miss); never silently mint or consume a receipt across drift.

`-R/--force` must mean **force execution**, never “force reuse.” It bypasses an otherwise valid receipt while retaining all normal ToolRun recording. `sase tool receipt TOOL` should state the exact first rejection reason and expose all relevant reasons in JSON.

### Host-completion contract

E4 does not require host completion to trust a historical result blindly. The host can request `sase tool run check`; that invocation may produce a freshly validated reused ToolRun. Completion still evaluates sealed intent plus the current repository observation. Host policy must be able to require `-R` for a real execution, and drift after the reuse decision must cause the ordinary completion observation to reject or rerun.

Acceptance must cover three distinct paths:

1. policy permits an exact reuse and completion accepts the new reused ToolRun;
2. policy forces execution with `-R`; and
3. repository drift makes the receipt inapplicable and completion obtains fresh evidence.

### Recommended E4 phases

1. **Rust receipt/applicability contract:** tables/fields, proof and rejection types, retention, old-store compatibility.
2. **Catalog expansion and shadow mode:** opt-in policy, TTL, external probes, core publish/pin, eligibility metrics with execution always continuing.
3. **Reuse execution path:** atomic-enough revalidation, no child spawn, new audited ToolRun, invalidation ordering.
4. **CLI/explanation surface:** `receipt`, versioned JSON, `-R/--force`, parser/help/completion coverage.
5. **`check` dependency audit and host policy:** close ambient inputs, enable only the proven tool, completion tests.
6. **Acceptance, docs, and cleanup:** concurrency/drift fixtures, retention, flag removal, successor-epic evidence report.

Use one `tool_receipts` beta flag if needed. Off should compute and report shadow eligibility but always execute; on may reuse. Remove it before landing.

### E4 landing criteria

E4 is landed only when all of the following are demonstrated:

- [ ] Receipt reuse is explicit per-tool catalog policy with a literal TTL; tools without it always execute.
- [ ] The applicability key includes definition, arguments, repository state, declared inputs, environment, toolchain, external probes, scope, policy version, and required workspace identity.
- [ ] `check` has a documented dependency audit with no known material ambient input left outside the fingerprint/probe contract.
- [ ] An immediate second eligible `check` spawns no child, prints `REUSED` with receipt/source IDs, and creates a distinct reused ToolRun.
- [ ] Changes to HEAD/tree/index/untracked content, dirty hashes, definition, arguments, environment, toolchain, external probes, workspace scope, policy version, or TTL cause execution with an exact miss reason.
- [ ] Incomplete fingerprints/probes, input mutation, failure, signal, timeout, stop, loss, ad-hoc runs, and opt-out tools never mint or satisfy a receipt.
- [ ] A later same-key non-success invalidates an older success until a later eligible success.
- [ ] `-R/--force` always executes and records a normal ToolRun even when a receipt is valid.
- [ ] Concurrent repository mutation cannot silently produce a hit; it becomes execution or an explicit unstable-state refusal.
- [ ] Clean cross-workspace and dirty workspace-scoped behavior are separately tested.
- [ ] Reused runs are excluded from duration prediction samples and cannot recursively obscure the original executing source.
- [ ] `receipt`, `run`, `show`, `runs`, human output, and versioned JSON agree on source, policy, hit/miss, and rejection facts.
- [ ] Old schema-1 stores/readers and additive optional fields remain compatible; retention never leaves an unexplained dangling receipt reference.
- [ ] Linked-core publication and the local core revision pin land in the required order.
- [ ] Fixture acceptance does not depend on a green master and covers allowed reuse, forced execution, expiry, invalidation, and drift recovery.
- [ ] Raw `just install` behavior is unchanged; install reuse, stage reuse, and inline preflight are documented as out of scope.
- [ ] Shadow-mode measurements are preserved in the epic landing note to justify (or reject) a successor stage-reuse epic.
- [ ] The beta flag is removed and host/agent documentation explains when reuse is permissible.

## Shared architectural constraints

Both epics should preserve the contracts established by E1–E2:

- Shared domain, storage, comparison, and applicability behavior belongs in `sase-core`; Python remains producer/UI glue.
- Keep wire schema 1 compatible through additive optional fields/tables unless evidence forces a coordinated version break.
- Publish the Rust change, then advance `sase-core-revision.txt`, then consume the new binding.
- One ToolRun has one process/log owner and one terminal settlement. Neither epic introduces a second supervisor.
- Handoff remains reserve → bind → adopt → acknowledge, and explicit `-H` remains prompt.
- Human text and JSON are two views of the same stored facts; JSON additions are versioned.
- Acceptance is based on controlled fixtures, not the health of the current development branch.
- Each epic gets at most one temporary beta flag, with a real old branch and mandatory removal before landing.

The CLI additions should also follow existing ordering and alias rules. With the proposed commands, the conceptual `sase tool` order is `failures`, `list`, `receipt`, `rerun`, `run`, `runs`, `show`, `stop`, `wait`; every public long option, including `--force`, needs its short alias and parser/help/completion tests.

## Recommended roadmap replacement text

### E3 — Failure facts, classification, and rerun chains (large)

Persist versioned, bounded failure facts during ToolRun settlement; add stable stage identities; classify verification failures against explicit eligible reference and canonical flake evidence as `new`, `known`, `flaky`, or `unknown`; distinguish infrastructure/control causes; expose `failures` and structured continuation; and rerun frozen named-tool invocations as new, immutable linked ToolRuns. Never infer confidence from an uncovered or incompatible baseline, and never create CI/flake tasks automatically.

**Lands when:** the complete E3 checklist above passes against fixture repositories; all terminal causes and unknown-evidence paths are represented; reruns preserve audit history; old stores remain readable; Rust is published/pinned before use; and the beta flag is removed.

### E4 — Exact whole-tool verification receipts (large)

For explicitly opted-in pure verification tools, mint receipts only from successful, complete, non-mutating executions and reuse them only under an exact, unexpired applicability proof. Record each reuse as a new ToolRun, explain every refusal, allow `-R/--force` execution, and integrate reuse with host completion's fresh repository observation. Start with audited `check`; defer install, individual-stage reuse, and inline preflight.

**Lands when:** the complete E4 checklist above passes; shadow measurements justify enabling `check`; all input/probe drift forces execution; later failures invalidate older successes; reuse is auditable and excluded from timing predictions; old stores remain readable; Rust is published/pinned before use; and the beta flag is removed.

## Final recommendation

Proceed with both epics, but amend the roadmap before planning them. E3 should be the next epic after E2 because the live data shows a large, expensive failure-triage problem and because E3 establishes stable identities E4 will need. E4 should follow with a deliberately small correctness surface: exact whole-tool reuse for audited verification only. Treat stage reuse, install postcondition caching, and pre-handoff inline work as a separately justified successor, informed by E4 shadow data rather than assumed savings.

That sequence preserves the original product direction—durable evidence first, then faster reuse—while aligning the landing criteria with the system that E1, E1.5, and E2 actually built.
