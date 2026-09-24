# Architectural Readiness and Landing Criteria for `sase tool` Epics E3 and E4

**Author:** Researcher `gem` (independent swarm investigation)  
**Date:** 2026-09-24  
**Workspace:** `sase_41` (host `apollo`, master `b85538009`, core pin `6d0d0e6d5c0e`)  
**Context:** Readiness evaluation of Epics E3 (*Failure triage: NEW vs KNOWN vs FLAKY*) and E4 (*Verification receipts and staged reuse*) following the near-completion of Epic E2 (`sase-17p`).  
**Primary Reference:** `research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`

---

## 1. Executive Summary

This investigation evaluates whether Epics **E3** and **E4** as described in the `sase tool` epic roadmap (`sase_tool_epic_roadmap.md`) remain correct and appropriate given that **E2** (`sase-17p: durable ToolRun hand-off and lifecycle control`) is now in its final phase (`sase-17p.6`).

### Direct Answers to Key Questions

1. **Are E3 and E4 still correct and appropriate?**  
   **Yes, unequivocally.** Both epics target the most severe source of measured developer and agent waste in the SASE ecosystem today. Real data queried from the active host store (`~/.sase/tools/runs.sqlite`, 638 recorded runs) shows:
   - **490 out of 556 `check` runs failed (88.1% failure rate)**.
   - **Over 71% of all stage failures occurred in cheap lint/formatting stages** (`lint (symvision)` alone failed 239 times; `lint (mypy)` failed 78 times; `lint (ruff)` failed 41 times) before heavy scoped tests completed.
   - Master remains known-red (`sase-j0` budget check failures), forcing every agent running `check-full` to parse massive failure outputs and hand-author median 1,778-character baseline-difference essays to continuation agents.
   - In SASE's multi-agent model, phase workers run `check` to verify a phase, and land agents re-run `check` on the *exact same tree*, duplicating 3.5–5 minutes of expensive execution per landed change. E4 eliminates this second run completely.

2. **Should we make any changes to the epics?**  
   **Yes. Several important boundary adjustments and architectural refinements are required** to incorporate work that landed in **E1.5** (`sase-16h: guarded recipes & monitor wrapping`) and **E2** (`sase-17p: durable handoff & settlement`):
   - **E3 must consume E2's `terminal_cause`:** Failure signature extraction must distinguish deterministic verification failures from infrastructure/lifecycle aborts (`timeout`, `stopped`, `lost`, `crashed`). A timeout or SIGKILL is not a "NEW" test failure.
   - **Pluggable vs Built-in Diagnostic Extractors:** E3 should provide built-in extractors for the standard toolchain (pytest, ruff, mypy, keep-sorted, symvision) and fall back gracefully to normalized exit diagnostics for arbitrary stages.
   - **Signature Stability:** Failure signatures must strip ephemeral workspace paths (`sase_<N>`), ephemeral worker IDs, and shifting line numbers (using test node IDs and rule codes) to achieve true cross-workspace aggregation.
   - **`rerun RUN` ownership:** The roadmap mentioned `rerun` across both E3 and E4. **`sase tool rerun RUN` must be owned exclusively by E3** as an attempt-chain retry mechanism, while **E4 owns the `-R/--force` bypass flag** for cached receipts.
   - **E4 deterministic failure refusal safety:** E4's "unchanged-since-failure refusal" must refuse *only* when the prior failure was deterministic (`terminal_cause: exited` with exit code > 0), never when the prior run was lost, timed out, or interrupted.
   - **Host-Owned Landing Gate Compliance (Decision 7):** E4 receipts must satisfy the host-owned landing validator via a dedicated non-interactive query command (`sase tool receipt <tool>`). Agents must never bypass verification by fabricating receipt assertions.

3. **How should E3 and E4 be sequenced?**  
   The roadmap suggested running `{E3, E4, E5}` in parallel. **This research strongly advises against uncoordinated parallel implementation of E3 and E4.**  
   Both E3 and E4 require modifications to the shared Rust core (`sase-core::tool_run` wire schema, SQLite tables, and PyO3 bindings). Running them concurrently risks core pin ratcheting collisions (identical to the issue documented in `sase-17p` Note #1).  
   **Recommended Sequencing:**  
   $$\mathbf{E2 \rightarrow E3 \rightarrow E4 \rightarrow E5 \rightarrow E6 \rightarrow E7 \rightarrow E8}$$  
   - **E3 runs first:** It is diagnostic/read-only with respect to execution semantics, provides immediate relief for the 88% failure rate and red master, and enriches the failure metadata consumed by E4's unchanged-since-failure refusal.  
   - **E4 runs second:** It alters execution dispatch (short-circuiting runs on receipt match, running cheap stages first, refusing unchanged failures), building upon the stable diagnostic baseline established by E3.

---

## 2. Empirical Verification on Live Environment (Apollo)

An audit of the live state on host `apollo` as of 2026-09-24 reveals the exact operational substrate:

### 2.1 ToolRun Store Corpus (`~/.sase/tools/runs.sqlite`)
A query into the live SQLite ledger across 638 recorded runs demonstrates why E3 and E4 are critical:

```text
Total Tool Runs Recorded: 638
State Breakdown:
  - failed:    490 (76.8%)
  - succeeded: 110 (17.2%)
  - lost:       24  (3.8%)
  - signaled:   14  (2.2%)

Tool Distribution:
  - check:      556 runs (490 failed, 66 succeeded)
  - test:        23 runs
  - check-full:   1 run
  - install:      1 run
  - ad-hoc (--): 57 runs
```

### 2.2 Stage Failure Breakdown
Stage timing and exit code telemetry captured in `stages` shows where execution actually fails:

```text
Top Failed Stages Across All Runs:
  1. lint (symvision):        239 failures
  2. test (scoped):           129 failures
  3. lint (mypy):              78 failures
  4. lint (ruff):              41 failures
  5. stage one (smoke):        38 failures
  6. fmt (python):             19 failures
  7. lint (pyscripts):         17 failures
  8. lint (feature flags):     14 failures
  9. fmt (markdown):            6 failures
 10. lint (toobig):             4 failures
```

**Key Takeaway:** Over 71% of stage failures are in lint and formatting stages that take 0.2s to 45s. Today, unless the agent manually runs sub-recipes, a full `check` or handed-off monitor runs all preceding stages or queues behind heavier work before failing. E4's cheap-stages-first directly eliminates the long tail of heavy test dispatch for lint failures, while E3 immediately surfaces the exact lint failure signature.

### 2.3 Red-Master Baseline (`sase-j0`)
The master branch remains red on exhaustive verification due to test-suite budget constraints (`sase-j0`, +38 corroborations). Currently, any agent running `check-full` or encountering shared test failures must parse thousands of lines of output to confirm that the failure is not new.

---

## 3. Deep Dive: Epic E3 — Failure Triage (NEW vs KNOWN vs FLAKY)

### 3.1 Motivation and Core Value
Today, when `sase tool run check` fails, the output is raw stdout/stderr logs. In an agent workflow:
1. The agent's context window is flooded with tracebacks containing ephemeral workspace paths (`/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_41/...`).
2. Providers truncate output (Claude at ~30k chars), frequently cutting off the critical error header or summary.
3. The agent must spend cognitive effort and LLM tokens discerning whether a failure was caused by its own edit or is pre-existing on `master`.
4. When handing off to a monitor or follow-up agent, the agent hand-writes extensive prose (median 1,778 characters) explaining pre-existing failures.

E3 converts failure diagnosing from an ad-hoc, error-prone manual chore into a deterministic, machine-classified ledger feature.

### 3.2 Architectural Adjustments for E3

#### Adjustment 1: Infrastructure vs Verification Separation via E2's `terminal_cause`
In E2 (`sase-17p`), the `ToolRun` schema introduced `terminal_cause` (`exited`, `timeout`, `stopped`, `lost`, `crashed`).  
E3 must inspect `terminal_cause`:
- If `terminal_cause != exited`: The failure is an **Infrastructure/Harness Abort**. Do not attempt to parse pytest or linter output. Report `CAUSE: timeout` (or `stopped`, `lost`) and skip signature classification.
- If `terminal_cause == exited` and `exit_code != 0`: Proceed with stage diagnostic extraction and failure classification.

#### Adjustment 2: Normalized Signature Invariants
Signatures must be hashable, canonical strings invariant across ephemeral workspaces and minor line shifts:
- **Test Failures:** `test:<relpath>::<test_function>#<exception_class>`. Line numbers inside test bodies change as code is edited; pytest node IDs do not.
  *Example:* `test:tests/tool/test_handoff.py::test_wait_timeout#TimeoutError`
- **Linter / Static Analysis Failures:** `lint:<linter_name>:<relpath>:<rule_or_code>[:<symbol>]`.
  *Example:* `lint:symvision:src/sase/tool/executor.py:private_import:_raw_proc_spawn`
- **Compiler / Syntax Failures:** `build:<tool>:<relpath>:<error_code>`.
- **Generic / Unrecognized Failures:** `stage:<stage_description>#exit_<exit_code>`.

All file paths in signatures must be normalized relative to the repository root. Any path containing `sase_\d+/` or absolute checkout prefixes must be stripped before hashing.

#### Adjustment 3: Three-Tier Classification Engine
Given an extracted signature $S$ from run $R$ on commit $C$ with merge-base $M$:
1. **KNOWN:**
   - $S$ was observed on a run where `git_head == M` or `git_head == origin/master`.
   - OR $S$ is explicitly mapped to an active task bead (e.g. `sase-j0`).
2. **FLAKY:**
   - $S$ matches an entry in `tests/.test_selection/` flake history, or was observed alternating pass/fail on the same commit SHA within the past 14 days.
3. **NEW:**
   - $S$ is neither KNOWN nor FLAKY. $S$ was introduced by the workspace's local changes.

#### Adjustment 4: Structured Continuation Payloads
E3 updates `src/sase/monitor/followup_prompt.py` and `followup_continuation.py` (the `sase-zl` adoption leg). When a monitor wrapping a ToolRun completes with failure:
- The continuation prompt automatically embeds a structured triage summary:
  ```markdown
  ### Tool Run Failure Triage (Run adeb77a5f189)
  - **NEW Failures (1):**
    - `lint:symvision:src/sase/tool/executor.py:private_import`
      *Message:* Private import of `_raw_proc_spawn` from `sase.proc`
  - **KNOWN Failures (2) [Ignorable]:**
    - `test:tests/perf/test_budget.py::test_full_suite#BudgetExceeded` (Bead: `sase-j0`)
  ```
- The hand-written `--next` essay is replaced entirely by machine-classified facts.

#### Adjustment 5: Ownership of `sase tool rerun RUN`
`sase tool rerun RUN` belongs in E3:
- Re-executes the exact tool invocation of `RUN` as a new attempt or linked child run (`parent_run_id = RUN`).
- Ignores cached receipts (always executes).
- Evaluates whether the failure signatures from attempt 1 disappeared in attempt 2 (verifying fix or flakiness).

### 3.3 Proposed E3 Phase Plan (~6 phases)

1. **`core-signatures` (Size: medium):** Add `ToolFailureSignatureWire`, `ToolRunFailureSummaryWire`, and `failures` storage tables to `sase-core`. Implement canonical signature hashing, workspace path normalization, and PyO3 bindings. Ratchet core pin.
2. **`extractors` (Size: medium):** Implement Python diagnostic extractors for `pytest` (node IDs, exception classes), `ruff`, `mypy`, `symvision`, and generic exit codes. Connect to `events.jsonl` stage failure events.
3. **`classifier` (Size: medium):** Build the three-tier classification engine: compare signatures against merge-base runs in `runs.sqlite`, active task beads in the bead store, and flake data.
4. **`cli-failures` (Size: medium):** Implement `sase tool failures [TOOL]` (grouped signatures, affected agents, counts, first-seen timestamps) and `sase tool rerun RUN` (attempt-chain execution). Add suggested task bead output (`/sase_new_task` guidance for recurring unmapped signatures).
5. **`continuation-integration` (Size: medium):** Wire structured failure triage into `src/sase/tool/render.py` (compact agent footer) and `src/sase/monitor/followup_prompt.py` (deleting hand-written `--next` prose).
6. **`acceptance-and-flags` (Size: medium):** Prove end-to-end classification against a test fixture containing 1 NEW failure, 1 KNOWN (`sase-j0`) failure, 1 FLAKY failure, and 1 INFRA failure. Update memory and docs. Remove `tool_failure_triage` beta flag.

---

## 4. Deep Dive: Epic E4 — Verification Receipts and Staged Reuse

### 4.1 Motivation and Core Value
In SASE, heavy verification is run repeatedly on identical or near-identical trees:
1. **Phase Worker $\rightarrow$ Land Agent Duplication:** A phase worker runs `sase tool run check` (3.5–5 minutes) and passes. It declares completion. The land agent checks out the patch and runs `sase tool run check` again on the exact same tree. This is 100% pure waste.
2. **`just install` Waste:** Measured at 74.5 hours across 1,798 invocations on apollo. Re-running `install` when `uv.lock` and `pyproject.toml` have not changed is unnecessary.
3. **Repeated Runs After Non-Code Edits:** Agents editing markdown notes or plans trigger `check` or `test`, paying minutes of pytest execution when covered python code did not change.
4. **Lint Failures Late in Execution:** When cheap lint stages are mixed into a monolithic verification command, agents wait for heavy environment setup or earlier stages before failing on a syntax or formatting error.

### 4.2 Architectural Adjustments for E4

#### Adjustment 1: Dual Receipt Scopes (`tree` vs `workspace`)
Receipt validity must respect environment boundaries:
- **`scope: tree` (Shareable machine-wide across workspaces):**
  *Applicable Tools:* `check`, `check-full`, `test`.
  *Key Inputs:* Git tree hash (`head_tree`), dirty diff hash, declared input file hashes (`inputs:` from `sase.yml`), toolchain probes (`python`, `just`, `sase-core-rs`), and allow-listed environment variables.
  *Semantics:* If Workspace 41 runs `check` on tree $T$ and mints a `tree` receipt, Workspace 42 on the same host can reuse that receipt if its tree and toolchain are identical.
- **`scope: workspace` (Workspace-local only):**
  *Applicable Tools:* `install`.
  *Key Inputs:* Lockfile hash (`uv.lock`), `pyproject.toml`, workspace `.venv` python interpreter identity.
  *Semantics:* A receipt for `install` in Workspace 41 cannot be reused by Workspace 42 because their virtual environments are physically distinct.

#### Adjustment 2: Passes Only; Deterministic Failure Refusal
- **Passes Mint Receipts:** Only runs settling with `state: succeeded` (exit code 0) mint reusable receipts. A receipt has a configurable TTL (e.g. 12 hours for `check`, 7 days for `install`).
- **Failures Never Become Receipts:** A failure is never reused to simulate a failure.
- **Unchanged-Since-Failure Refusal:** If an agent invokes `sase tool run TOOL` on a tree whose fingerprint matches a prior run that failed with `terminal_cause: exited`:
  - Execution is **refused**:  
    `Error: Refusing to run 'check': fingerprint matches run <run-id> which failed with exit code 1 (3m ago). Nothing has changed. Use -R/--force to run anyway.`
  - **Critical Safety Guard:** Refusal applies *only* if the prior failure was clean and deterministic (`terminal_cause: exited`). If the prior run was `lost`, `timeout`, `crashed`, or `stopped`, refusal MUST NOT trigger.

#### Adjustment 3: Host-Owned Completion Landing Gate Compliance (Decision 7)
In accordance with SASE Decision 7 (*Completion Is Host-Owned*):
- Agents do not create commits or bypass landing checks on their own recognizance.
- When an agent finishes, the host-owned landing harness executes.
- E4 provides `sase tool receipt <tool>`:
  - Exits 0 if and only if a valid, non-expired cryptographic pass receipt exists in `runs.sqlite` for the current tree and toolchain.
  - The lander runs `sase tool receipt check`. If it exits 0, the lander accepts verification and skips re-execution. If it exits 1, the lander runs `sase tool run check` for real.

#### Adjustment 4: Cheap-Stages-First Protocol
In `sase/sase.yml`:
```yaml
tools:
  check:
    argv: [just, check]
    stages: run_silent
    cheap_stages: [lint, fmt]
    receipt:
      scope: tree
      ttl: 12h
      inputs: [Justfile, pyproject.toml, uv.lock, sase-core-revision.txt]
```
When `sase tool run check` is called (whether foreground or with `-H` durable handoff):
1. **Pre-flight Inline Stage:** Run `cheap_stages` (`lint`, `fmt`) *inline* in the foreground before allocating capacity or detaching to a background monitor/proc.
2. If any cheap stage fails: Terminate immediately. Output the failure. No background proc is spawned; no queue capacity is reserved.
3. If cheap stages pass: Mint per-stage pass receipts, then proceed to the remaining heavy stages (`test (scoped)`).

### 4.3 Proposed E4 Phase Plan (~7 phases)

1. **`core-receipts` (Size: medium):** Add `ToolReceiptWire` and `receipts` table in `sase-core` (`runs.sqlite`). Implement receipt minting, TTL validation, scope matching (`tree` vs `workspace`), and PyO3 query bindings. Ratchet core pin.
2. **`receipt-mint-and-query` (Size: medium):** Integrate receipt minting on successful ToolRun completion. Implement `sase tool receipt TOOL` (silent exit code with `--json` metadata) for scripts and landing gates.
3. **`run-reuse-and-force` (Size: medium):** Teach `sase tool run` to check receipts before dispatch. On valid receipt hit, return immediately citing receipt ID and minting run. Add `-R / --force` to bypass receipts.
4. **`unchanged-failure-refusal` (Size: medium):** Implement deterministic unchanged-since-failure refusal with explicit reference to previous failed run ID and `-R` override instructions. Enforce safety exemption for infra aborts.
5. **`cheap-stages-inline` (Size: medium):** Implement the pre-flight cheap stages executor. Run declared `cheap_stages` inline before handoff or heavy reservation; mint stage receipts.
6. **`host-completion-and-install` (Size: medium):** Configure `install` tool with workspace-scoped receipts (skipping `just install` on unchanged lockfiles). Integrate `sase tool receipt` into host-completion landing gates.
7. **`acceptance-and-flags` (Size: medium):** Run false-reuse safety matrix (touching inputs, mutating files, invalidating toolchain, TTL expiration). Verify hours avoided metric. Remove `tool_receipts` beta flag.

---

## 5. Interaction, Ordering, and Risk Analysis

### 5.1 Serial vs Parallel Execution (Why E3 Must Precede E4)
The original roadmap suggested developing E3, E4, and E5 in parallel. We must reconsider this in light of multi-agent development patterns:

| Dimension | Parallel Development (E3 || E4) | Serial Development (E2 $\rightarrow$ E3 $\rightarrow$ E4) |
| :--- | :--- | :--- |
| **`sase-core` Pin Management** | **High Risk:** Both epics alter `crates/sase_core/src/tool_run/` (signatures in E3, receipts in E4). Concurrent branch PRs will collide on `sase-core-revision.txt` floor ratchets. | **Clean:** E3 lands and ratchets the core pin; E4 builds cleanly on top of E3's core floor. |
| **Execution Risk** | High: E4 changes execution semantics (skips, short-circuits) simultaneously while E3 changes failure reporting. | Low: E3 is read-only/diagnostic. Once diagnostics are proven, E4 adds reuse controls. |
| **Feature Synergy** | Low: E4's unchanged-since-failure refusal would only be able to say "failed with code 1". | High: E4's refusal can cite E3's failure signatures: *"Refusing run: matches run 1a2b which failed with NEW signature `lint:symvision`"*. |

**Recommendation:** Execute **E3 first**, then **E4**.

### 5.2 Relationship to In-Flight and Open Beads

- **`sase-17p` (E2):** In phase 6 (closing). E3 and E4 cleanly build on top of E2's durable handoff (`-H`), lifecycle facade (`stop`, `wait`, `show -F`), and `terminal_cause`.
- **`sase-16h` (E1.5):** Landed. E1.5's `tools/require_tool_run` guard ensures *all* agent verification runs go through `sase tool run`, guaranteeing 100% receipt and failure triage coverage.
- **`sase-124` (TUI freshness):** In progress. Does not conflict with E3 or E4 because TUI surfaces are deferred to E5.
- **`sase-j0` (Red master budget failures):** Active. Serves as a perfect live test fixture for E3's `KNOWN` classification.

---

## 6. Crystal-Clear Landing Criteria

To ensure agents implementing and landing E3 and E4 have unambiguous targets, the landing criteria are defined as objective, black-box verifiable contracts.

### 6.1 Landing Criteria for Epic E3 (Failure Triage)

An agent landing E3 must verify all of the following on a clean checkout without model-specific mocks:

1. **Deterministic Signature Extraction:**
   - Run a test command containing a deliberate test failure (`pytest` assertion error) and a deliberate lint failure (`ruff` or `symvision` error).
   - Verify that `sase tool show <run-id> --json` contains a non-empty `failures` array with normalized signature IDs.
   - Verify that signature strings contain **no workspace-specific directory names** (e.g. `sase_41` does not appear anywhere in the signature).
   - Verify that moving the file to another workspace or editing unrelated lines preserves the signature identity.

2. **Accurate Three-Tier Classification:**
   - **KNOWN:** On a branch with no changes relative to `master`, run `sase tool run check-full`. Verify that `sase-j0` budget failures are classified as `KNOWN` and attributed to bead `sase-j0`.
   - **NEW:** Introduce a new syntax error or assertion failure in a test. Run `sase tool run check`. Verify that the failure is explicitly labeled `NEW` in both CLI output and JSON.
   - **INFRA:** Trigger a timeout or send `SIGKILL` to a running tool. Verify that `terminal_cause` reflects the abort and that the run is classified as `INFRA_FAILURE`, not `NEW` test failure.

3. **CLI Commands:**
   - `sase tool failures`: Prints a formatted table of active failure signatures across recent host runs, showing signature, classification (NEW/KNOWN/FLAKY), affected runs, and first-seen timestamp.
   - `sase tool rerun <run-id>`: Re-runs the exact argv of `<run-id>` as a linked attempt (`attempt: 2`), ignoring cached receipts.

4. **Structured Continuation Delivery:**
   - Start a monitor on a failing command. Verify that the rendered prompt in `followup_prompt.py` contains the structured triage markdown block and does NOT require the starter agent to supply manual `--next` prose.

5. **Code Hygiene & Flags:**
   - Feature flag `tool_failure_triage` is registered as a beta flag at start and **completely removed** before epic landing.
   - Core pin in `sase-core-revision.txt` is updated to a published commit containing the new Rust contracts.
   - `just check` passes with zero warnings.

---

### 6.2 Landing Criteria for Epic E4 (Verification Receipts and Staged Reuse)

An agent landing E4 must verify all of the following on a clean checkout:

1. **Receipt Minting and Retrieval:**
   - Run `sase tool run check` on a passing tree. Verify that a receipt is created in `runs.sqlite` with `scope: tree`, matching `fingerprint_digest`.
   - Run `sase tool receipt check`. Verify that it exits with code 0 and prints the valid receipt metadata.

2. **Instant Pass Reuse:**
   - Immediately run `sase tool run check` a second time on the unchanged tree.
   - Verify that execution completes in **under 1.0 second**.
   - Verify that stdout prints: `Reusing pass receipt <receipt-id> from run <run-id>. Exit 0.`
   - Verify that no child subprocess was spawned.

3. **Receipt Invalidation & Force Flag:**
   - Touch a source file tracked by git (`touch src/sase/main.py`). Run `sase tool run check`. Verify that a fresh run executes for real (cache miss).
   - On an unchanged tree with an existing receipt, run `sase tool run check -R` (or `--force`). Verify that fresh execution is forced and a new receipt is minted.

4. **Deterministic Unchanged-Since-Failure Refusal:**
   - Cause a deterministic failure (e.g. invalid syntax in a python file). Run `sase tool run check` (fails with exit code 1).
   - Without touching any files, run `sase tool run check` again.
   - Verify that execution is refused with exit code 2 and a message explaining: `Nothing has changed since run <run-id> failed. Use -R to force.`
   - Run `sase tool run check -R`. Verify that execution proceeds.

5. **Cheap-Stages-First Inline Execution:**
   - Introduce a lint error in a file (`ruff` violation) while having a heavy test suite configured.
   - Run `sase tool run -H check`.
   - Verify that the cheap lint stage executes inline in the foreground and fails within ~15 seconds.
   - Verify that no background monitor or durable proc was handed off.

6. **Host Landing Gate Integration:**
   - In a mock lander script or `host_completion.py`, invoke `sase tool receipt check`. Verify that it programmatically verifies the receipt without executing the underlying tool.

7. **Code Hygiene & Flags:**
   - Feature flag `tool_receipts` is registered as a beta flag at start and **completely removed** before epic landing.
   - Core pin in `sase-core-revision.txt` is updated to a published commit containing the new Rust contracts.
   - `just check` passes with zero warnings.

---

## 7. Recommended Next Moves for Bryan

1. **Authorize E3 (`Failure Triage`) as the immediate successor to E2:**  
   Once `sase-17p.6` lands and its beta flag is removed, write the E3 epic plan (`tool_e3_failure_triage.md`) using `/sase_plan`.
2. **Assign E3 to a dedicated land/phase agent team:**  
   Execute E3's 6 phases serially. E3 requires no changes to execution semantics, carries low regression risk, and immediately solves the developer-facing confusion of the 88% failure rate and red master.
3. **Queue E4 (`Verification Receipts`) directly after E3:**  
   With E3's diagnostic structures in place, E4's receipt and refusal contracts will build seamlessly on top of a rock-solid diagnostic foundation.
