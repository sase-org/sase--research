# Research Report: Top 10 Most Impactful Task Beads for SASE

**Researcher:** `research.3a.gem` (Swarm Member `gem`)  
**Date:** 2026-11-04  
**Project:** `gh_sase-org__sase`  
**Scope:** Exhaustive audit of all active task beads, cross-host running agent/epic conflict analysis on `apollo` and `athena`, and ranked recommendations for immediate work.

---

## 1. Executive Summary

This independent research investigation evaluates the current active task bead backlog for the `sase` project to identify the **10 most impactful task beads** that should be prioritized for immediate work. 

A comprehensive census of the bead store identified **391 active task beads** (`by_status`: 12 `open`, 375 `ready`, 3 `snoozed`, 1 `in_progress`). To ensure recommendations do not collide with in-flight development, live agent and epic states across both local host `apollo` and remote fleet host `athena` were audited. 

The selected 10 beads span critical security remediation, infrastructure resilience during provider outages, widespread agent/developer workflow blockers, silent telemetry degradation for Antigravity (`agy`), test isolation contamination, and architectural enforcement of the Rust backend boundary. Each recommended bead has zero file or subsystem conflicts with ongoing epics on `apollo` or `athena`.

### Top 10 Ranked Task Beads Summary

| Rank | Bead ID | Title | Type | Size | Confirmed +1s | Primary Subsystem |
|:---:|:---:|:---|:---:|:---:|:---:|:---|
| **1** | [`sase-1ot`](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1ot/README.md) | Rotate and purge the 27 historical secret-scanner hits in public `sase--agents` history | Bug | Large | +1 | Security / Public Repository |
| **2** | [`sase-1r7`](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1r7/README.md) | Adopt SSH publickey credential retries in sidecar push, AXE sidecar runner, finalizer pushes, and bead sync | Feature | Large | 0 (New) | Git Infrastructure / Resilience |
| **3** | [`sase-zo`](https://github.com/sase-org/sase--beads/blob/main/pages/sase-zo/README.md) | `sase repo open` rejects configured sidecars when inventory uses the project display name | Bug | Small | +10 | Repo Management / CLI |
| **4** | [`sase-v6`](https://github.com/sase-org/sase--beads/blob/main/pages/sase-v6/README.md) | `rust-lsp-install` copies `sase-xprompt-lsp` from checkout-local target dir and exits 0 after cp/chmod/mv fail | Bug | Small | +5 | Build & Tooling / LSP |
| **5** | [`sase-15o`](https://github.com/sase-org/sase--beads/blob/main/pages/sase-15o/README.md) | `agy` trajectory tool-call extraction and structural no-progress detection are silently off on `agy` 1.2.7 | Bug | Large | +2 | LLM Provider / Antigravity |
| **6** | [`sase-1q3`](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1q3/README.md) | Pytest inherits `SASE_MODEL_OVERRIDE` and fails seven model/provenance assertions | CI | Small | 0 (New) | Test Suite Isolation |
| **7** | [`sase-1r4`](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1r4/README.md) | Signature-skew `TypeErrors` after a live sase update escape update-skew classification and leave staged monitors as zombies | Bug | Large | 0 (New) | Process Supervision / Updates |
| **8** | [`sase-1qv`](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1qv/README.md) | `sase-1pn` landing repairs never landed: slot-refusal policy still lives in Python despite closeout claiming a Rust binding | Bug | Medium | +1 | Core Architecture / Rust Core |
| **9** | [`sase-1i6`](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1i6/README.md) | Federation IPC tests fail because the `AF_UNIX` socket path is too long | CI | Small | 0 (New) | Federation IPC / Test Suite |
| **10** | [`sase-1qu`](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1qu/README.md) | `test_update_shortcut_dispatch_performs_no_disk_or_subprocess_work` fails cold: patches `Path.read_text` before keymap defaults cache is warm | CI | Small | 0 (New) | TUI Keymap / Test Suite |

---

## 2. Host and Active Work Audit (`apollo` and `athena`)

Before filtering task beads, a full audit was performed across active runner slots and agent states on both `apollo` (Bryan's rendezvous server / local machine) and `athena` (remote execution server).

### 2.1 Live Agent Census

#### On Host `apollo` (Local)
* **`gh_sase-org__sase`**:
  * `cd--code` (PID 383242, `RUNNING`): Implementing `@plan:202611/codex_exec_final_answer_integrity.md`. Scoped strictly to Codex execution and final answer declaration integrity.
  * `research.3a.*` (PIDs including `gem`, `cdx`, `cld`, `grk`, `mus`): The 5-researcher research swarm analyzing task beads.
* **`gh_bobs-org__bob-cli`**:
  * `bob-cli-h2.*` and `bob-cli-h0.*`: Clan members working on the `bob-cli` project. Separate repository, zero conflict.

#### On Host `athena` (Remote via Dispatch)
* **`gh_sase-org__sase`**:
  * `18a` (PID 2327694, `RUNNING`): Working on plan `#actstat:sase-core` (activity status in sase-core).
  * `18b` (PID 2451849, `RUNNING`): Diagnostic and fix plan for agent cleanup after kill/dismiss (`~/tmp/screenshots/20261104_151315.png`).
  * `sase-1qz` Clan (`sase-1qz.6.1.2` `RUNNING`, `sase-1qz.land` `WAITING`): Epic: *Agent Hijack: stop a stalled agent, keep its work, recover in one keypress*. Touches `sase agent hijack`, recovery panels, and prompt bar integration.
  * `sase-1r8` Clan (`sase-1r8.4--mon` `INSTALLING`, `sase-1r8.land` `WAITING`): Epic: *Stop agent publication false blocks, parked-row floods, and drain starvation*. Touches `src/sase/agent/publication.py`, `drain.py`, and scanner rules versioning.
  * `sase-1r2` Clan (`sase-1r2.5--mon` `WAITING PYPI`, `sase-1r2.land` `WAITING`): Epic: *Green Full CI on master, a containing published core, and sase v0.19.0 confirmed on PyPI*. In final release / PyPI confirmation stages.
  * `sase-1n6` / `sase-1n6.11` Clan (`sase-1n6.11.4--mon` `WAITING GITHUB`, `sase-1n6.11.land` `WAITING`): Epic: *Exact-candidate release train and steward*. Touches release automation.
* **`gh_bobs-org__bob-cli`**:
  * `185--3`, `bob-cli-h4.*`: Active agents in `bob-cli`. Separate repository.

### 2.2 Conflict Avoidance Validation
Based on this audit, any candidate task beads touching the following areas were strictly screened or scheduled to avoid collision:
1. Agent Hijack logic, `sase agent hijack` commands, and recovery UI (`sase-1qz`).
2. Agent publication scanning, drain loops, and scanner false-positive blocking (`sase-1r8`).
3. Agent dismiss/kill process cleanup (`18b`).
4. Codex execution final answer wrappers (`cd--code`).
5. Core activity status (`18a`).

All 10 recommended task beads are orthogonal to these areas and can be worked immediately without merge or runtime conflicts.

---

## 3. Detailed Ranked List of Recommended Task Beads

---

### Rank 1: `sase-1ot` — Rotate and Purge Historical Secret-Scanner Hits in Public Repo History

* **Bead ID:** `sase-1ot`
* **Type / Size / Status:** `bug` / `large` / `ready`
* **Confirmed +1s:** 1 (corroborated from private audit report `audit-report.md`)
* **Created:** 2026-10-27 by `bbugyi200.athena.sase-1oh.land`
* **Primary Subsystem:** Public Git History / Security

#### Problem Statement & Root Cause
A private audit of the public `sase-org/sase--agents` sidecar repository (at tip `5066d26a`) using core scanner rules v1 discovered **27 secret-scanner hits** across 138,525 tracked files. While new agent publications are protected by pre-push scanning, historical commits in the public GitHub repository still contain exposed credential signatures. The repository owner (Bryan) explicitly approved credential rotation plus a complete git history rewrite via approval gate `custom-57bc7a62`. However, because epic `sase-1oh` closed upon delivering the scanner, no dedicated bead was assigned to execute the remediation.

#### Impact & Justification
Exposing credentials in public GitHub history represents an ongoing, high-severity security risk. Automated scrapers actively scan public GitHub commits for tokens. Even if credentials are restricted or revoked, un-purged history violates repository security integrity and triggers repeated false positives during historical audits. Since owner approval has already been granted, this security task must take highest precedence.

#### Conflict Check
Zero overlap with ongoing epics. Ongoing epic `sase-1r8` is fixing forward publication scanners for new agent rows, but `sase-1ot` is a one-time historical rewrite of the external sidecar `sase-org/sase--agents`.

#### Recommended Solution
1. Coordinate with Bryan to verify rotation/revocation of the 27 credential values identified in private report `audit-report.md` (hash: `53a690592e...`).
2. Clone `sase-org/sase--agents` into an isolated workspace.
3. Use `git-filter-repo` (or BFG Repo-Cleaner) with the exact paths and replacement patterns from `audit-report.md` to strip the exposed strings from all historical commits and tags.
4. Verify using `sase repo open` and core scanner rules v1 that zero scanner hits remain.
5. Coordinate force-push to `sase-org/sase--agents` and notify connected hosts to re-sync their sidecar tracking branches without triggering re-push storms (referencing sibling bead `sase-1or`).

---

### Rank 2: `sase-1r7` — Adopt SSH Publickey Credential Retries in Network Git Call Sites

* **Bead ID:** `sase-1r7`
* **Type / Size / Status:** `feature` / `large` / `ready`
* **Confirmed +1s:** 0 (Freshly filed on 2026-11-04 following active incident)
* **Created:** 2026-11-04 by `bbugyi200.athena.sase-1r5.1.land`
* **Primary Subsystem:** Git Network Infrastructure / `src/sase/git_credential_retry.py`

#### Problem Statement & Root Cause
During GitHub's SSH authentication degradation incident on 2026-11-04, multiple SASE background jobs and agent runs failed catastrophically on transient `Permission denied (publickey)` errors. Epic `sase-1r5.1` introduced a shared `CredentialRetry` policy (`src/sase/git_credential_retry.py`), but scoped it only to call sites that already consulted the sase-core retryability classifier (SDD store clone, SDD network git, operational-lease fetch). Four major network git sites were left unadapted and still abort immediately on the first transient denial:
1. `src/sase/sdd/_sidecar_git.py:push_sidecar` — Runs `run_sdd_git(..., check=True)`, immediately raising `SddMaterializationError`.
2. `src/sase/axe/runner_workspace_sidecar.py` — `default_git_runner` (`_run_sidecar_push`) retries only branch divergence, never authentication blips, breaking AXE background publication.
3. `src/sase/vcs_provider/plugins/_git_commit_dispatch.py` — Finalizer push handlers (`_push_with_retry`, `_push_current_branch_with_rebase_retry`) retry only branch collisions, aborting turn-ending stitch pushes.
4. `src/sase/bead/_sync_worker_run.py` — Retries only push races (`is_retryable_push_race`), causing sync cycle failures.

#### Impact & Justification
Transient network and SSH key validation drops at GitHub or local agent hosts cause stitch landings, background AXE workers, and sidecar materializations to crash. In the case of turn-end finalizer pushes, a transient SSH drop causes host completion to fail, abandoning an agent's verified work.

#### Conflict Check
Epic `sase-1r5.1` has closed. In-flight epics (`sase-1r8`, `sase-1qz`, `sase-1r2`) do not touch these four git call sites. `sase-167` touches deploy-key wording in `_sync_logs.py`/`ssh_agent.py` and is clearly partitioned from the bead sync worker.

#### Recommended Solution
1. In `src/sase/sdd/_sidecar_git.py`, `src/sase/axe/runner_workspace_sidecar.py`, and `src/sase/vcs_provider/plugins/_git_commit_dispatch.py`:
   - Intercept git execution failures and classify them with `classify_failure_retryability`.
   - On `RETRYABILITY_VERDICT_CREDENTIAL_UNCONFIRMED`, instantiate a `CredentialRetry` helper.
   - Use `BACKGROUND_CREDENTIAL_RETRY_BUDGET` for finalizers and AXE background work; ensure no locks or admission permits are held while sleeping.
2. In `src/sase/bead/_sync_worker_run.py`:
   - Incorporate credential retry evaluation alongside `is_retryable_push_race`.
3. Add focused unit tests using SSH shims (patterned after `tests/sdd_store/test_sidecar_clone_retry_credentials.py`) and reset `sase.git_credential_retry._EXHAUSTED_HOSTS` in test teardown.
4. Update budget documentation in `docs/reference/agents/service-host.md`.

---

### Rank 3: `sase-zo` — `sase repo open` Rejects Configured Sidecars Under Project Display Names

* **Bead ID:** `sase-zo`
* **Type / Size / Status:** `bug` / `small` / `ready`
* **Confirmed +1s:** **10 independent +1 confirmations** (highest among all open bugs)
* **Created:** 2026-09-11 by `bbugyi200.athena.research.1u.final`
* **Primary Subsystem:** `src/sase/main/repo_handler_common.py`, `repo_open_external.py`

#### Problem Statement & Root Cause
In `src/sase/main/repo_handler_common.py:match_repo_record`, candidate repository records are filtered by comparing `RepoRecord.project` against `ProjectContext.project_name`. However, project inventory records store `project="sase"` (the human display name) and `project_key="gh_sase-org__sase"` (the canonical project key), while host context operates on the canonical key. Because the filter compares the canonical key against the display name, all configured candidates are erroneously stripped. Running `sase repo open research -r "..."` fails with exit code 2: `Unknown repo`, listing only `gh_sase-org__sase` as valid.

#### Impact & Justification
Core Memory Section 1.1.3 strictly mandates: *"When you need to read or modify files in any repository other than your own workspace checkout, agents MUST use your `/sase_repo` skill first... Do NOT read sidecar artifact files directly"*. Because `sase repo open` fails for `research` and other configured sidecars, agents are either blocked from reading necessary reference materials or tempted to bypass audited access rules. Ten different agent runs have hit and logged this failure.

#### Conflict Check
No active agent or epic is modifying `src/sase/main/repo_handler_common.py` or `repo_open_external.py`.

#### Recommended Solution
1. In `src/sase/main/repo_handler_common.py:match_repo_record`:
   - Normalize project matching to check whether `context.project_key` matches either `record.project_key` or `record.project`, or resolve `record.project` through the display snapshot mapping before comparison.
2. Update `src/sase/main/repo_open_external.py:_unknown_repo_error` with the same normalized comparison.
3. Add regression tests in `tests/main/test_repo_open.py` verifying that `sase repo open research` and `sase repo open sase--research` resolve correctly from a workspace whose project key is `gh_sase-org__sase`.

---

### Rank 4: `sase-v6` — `rust-lsp-install` Silently Fails and Exits 0 on Custom Cargo Target Directories

* **Bead ID:** `sase-v6`
* **Type / Size / Status:** `bug` / `small` / `ready`
* **Confirmed +1s:** **5 independent +1 confirmations**
* **Created:** 2026-08-28 by `bbugyi200.athena.sase-um.land`
* **Primary Subsystem:** Build Infrastructure / `Justfile:998-1022`

#### Problem Statement & Root Cause
The `rust-lsp-install` recipe in `Justfile` builds and installs `sase-xprompt-lsp`. It suffers from two bugs:
1. It hardcodes the source path as `src="{{ sase_core_dir }}/target/release/sase-xprompt-lsp"`. On developer machines and servers where Cargo is configured with a global target directory (such as Bryan's host `~/.cargo/config.toml` configuring `target-dir = "/mnt/poseidon/cargo-target"`), the binary is written to `/mnt/poseidon/cargo-target/release/sase-xprompt-lsp`. Thus `cp` reads a non-existent path.
2. The installation command is structured as a single `@`-prefixed, `;`-separated shell line without `set -e`:
   ```bash
   cp "$src" "$tmp"; chmod +x "$tmp"; mv -f "$tmp" "$dest"; printf "[rust-lsp-install] installed %s\n" "$dest"
   ```
   When `cp`, `chmod`, or `mv` fail, the shell continues to `printf`, which exits 0. `just install` reports complete success despite installing nothing.

#### Impact & Justification
Agents and developers run outdated versions of `sase-xprompt-lsp` indefinitely while believing they are running newly compiled code. This leads to hours wasted debugging LSP syntax highlighting, macro completions (`%dispatch`, `%wait`), and prompts against stale binaries. 5 separate runs have documented version skew (e.g. `sase-xprompt-lsp` reporting 0.32.6 while `sase_core_rs` was 0.32.8).

#### Conflict Check
No in-flight agent is modifying the LSP recipe in `Justfile`.

#### Recommended Solution
1. In `Justfile` (`rust-lsp-install` recipe):
   - Add `set -euo pipefail` at the start of the shell script block.
   - Dynamically discover the actual binary output directory by querying `cargo metadata --format-version 1 --no-deps` or inspecting `CARGO_TARGET_DIR` / `cargo locate-project` rather than hardcoding `target/release`.
   - Validate that `test -f "$dest"` succeeds and that `.venv/bin/sase-xprompt-lsp --version` executes cleanly before printing the installation confirmation.

---

### Rank 5: `sase-15o` — Antigravity (`agy`) Trajectory Extraction and No-Progress Detection Silently Disabled

* **Bead ID:** `sase-15o`
* **Type / Size / Status:** `bug` / `large` / `ready`
* **Confirmed +1s:** **2 independent +1 confirmations**
* **Created:** 2026-09-21 by `bbugyi200.athena.research.23.cld`
* **Primary Subsystem:** LLM Provider / `src/sase/llm_provider/_subprocess_agy.py`

#### Problem Statement & Root Cause
In `src/sase/llm_provider/_subprocess_agy.py`, SASE defines:
```python
_SUPPORTED_AGY_TRAJECTORY_VERSIONS = frozenset({"1.0.10"})
```
The active version of Antigravity CLI in the environment has evolved to `1.2.7+`. Because the version check is an exact set match rather than a compatible range or schema validator, SASE detects a version mismatch, logs a quiet debug notice, and completely disables trajectory tool-call extraction, token accounting, and structural no-progress detection for all `agy` runs.

#### Impact & Justification
Antigravity (`agy`) is one of the primary supported agent runners in SASE. With trajectory extraction disabled:
- SASE cannot detect when an `agy` agent is looping without making progress (costing tokens and runner slots).
- Tool-call histories in SASE's agent tab and chat archive are stripped or empty.
- Usage-window metrics and token quotas cannot be tracked accurately.

#### Conflict Check
No active agents are editing `_subprocess_agy.py`. (`cd--code` is working on Codex execution, not Antigravity).

#### Recommended Solution
1. In `src/sase/llm_provider/_subprocess_agy.py`:
   - Replace the strict single-version frozenset with a semver compatibility validator (e.g. supporting `1.0.10 <= version < 2.0.0` or allowlisting known tested versions including `1.2.7`).
   - Validate trajectory schema keys dynamically: if expected fields (`step_index`, `tool_calls`, `content`) are present in `transcript.jsonl`, extract them regardless of patch-level CLI bumps.
2. Add unit tests in `tests/test_subprocess_agy.py` asserting that version strings `1.2.7`, `1.3.0`, etc. successfully trigger trajectory extraction.

---

### Rank 6: `sase-1q3` — Pytest Inherits `SASE_MODEL_OVERRIDE` and Fails Model/Provenance Assertions

* **Bead ID:** `sase-1q3`
* **Type / Size / Status:** `ci` / `small` / `ready`
* **Confirmed +1s:** 0 (Freshly filed on 2026-10-30)
* **Created:** 2026-10-30 by `bbugyi200.athena.sase-1pj.5.1.land`
* **Primary Subsystem:** Test Harness Isolation / `tests/_conftest_environment.py`

#### Problem Statement & Root Cause
When `SASE_MODEL_OVERRIDE` is present in the ambient environment (common during development or when launched from within an agent session with an override), running pytest produces **7 deterministic failures** across 4 test suites:
- `tests/test_workflow_executor.py::TestShouldHitl`
- `tests/main/test_init_skills_deploy.py`
- `tests/test_bead/test_sync_checkpoint.py`
- `tests/test_commit_workflow_publication_outcomes.py`
The test isolation fixture `tests/_conftest_environment.py::_clear_agent_env_vars` explicitly cleans `SASE_AGENT*` and `SASE_MODEL_ALIAS_OVERRIDES`, but omits `SASE_MODEL_OVERRIDE`. Tests expecting standard fixture models receive the ambient override and fail assertion checks.

#### Impact & Justification
This is an insidious trap for both human developers and autonomous test verification agents. An agent running `just check` in an environment where `SASE_MODEL_OVERRIDE` was exported will see 7 unexplained test failures, falsely believing it broke workflow execution and skills deployment.

#### Conflict Check
Zero conflicts. No active agent touches `_conftest_environment.py`.

#### Recommended Solution
1. In `tests/_conftest_environment.py::_clear_agent_env_vars`:
   - Add `"SASE_MODEL_OVERRIDE"` to the tuple of environment variables cleared before test execution.
2. Ensure explicit per-test `monkeypatch.setenv("SASE_MODEL_OVERRIDE", ...)` remains supported.
3. Add a dedicated test in `tests/test_conftest_isolation.py` ensuring that setting `SASE_MODEL_OVERRIDE` in `os.environ` prior to pytest execution does not bleed into test cases.

---

### Rank 7: `sase-1r4` — Signature-Skew `TypeErrors` Escape Update-Skew Classification and Leave Zombie Monitors

* **Bead ID:** `sase-1r4`
* **Type / Size / Status:** `bug` / `large` / `ready`
* **Confirmed +1s:** 0 (Freshly filed on 2026-11-03)
* **Created:** 2026-11-03 by `bbugyi200.athena.17s`
* **Primary Subsystem:** Process Management / `src/sase/monitor/`

#### Problem Statement & Root Cause
When SASE is updated live on a system while background monitors and agents are active, newly imported modules may have different function signatures than the running host process. When a staged monitor attempts to execute a function whose signature changed, Python raises a `TypeError`. SASE includes an update-skew healer designed to detect skew and trigger recovery. However, the classifier currently only checks for specific `ImportError` and `AttributeError` patterns. It ignores `TypeError` shapes. As a result, the monitor process crashes unhandled, leaving staged monitor tasks as unmonitored "zombies" that never complete or hand off.

#### Impact & Justification
Three background agents died silently on `athena` on 2026-11-03 due to this defect. Zombie monitors hold locks, orphan workspace clones, and fail to report completion to the host, requiring manual human investigation and cleanup.

#### Conflict Check
Distinct from active agent `18b` (which is debugging agent dismiss/kill UI cleanup). Does not overlap with `sase-1qz` or `sase-1r8`.

#### Recommended Solution
1. In the update-skew classifier (`src/sase/monitor/` / `src/sase/update_skew.py`):
   - Broaden the error classifier to inspect `TypeError` tracebacks occurring during post-update execution.
   - Check if the caller frame belongs to a module whose mtime or disk content indicates a live update occurred since process start.
2. If signature skew is detected, route the event to `sase-1jf`'s resume-in-place recovery path rather than allowing the process to terminate as a zombie.
3. Add a test simulating a modified function signature across module reloads to confirm recovery.

---

### Rank 8: `sase-1qv` — Slot-Refusal Policy Still Lives in Python Despite Closeout Claiming Rust Core Binding

* **Bead ID:** `sase-1qv`
* **Type / Size / Status:** `bug` / `medium` / `ready`
* **Confirmed +1s:** 1 (corroborated by `research.30.final`)
* **Created:** 2026-11-02 by `research.30.final`
* **Primary Subsystem:** Core Architectural Boundary / `sase-core`

#### Problem Statement & Root Cause
The closeout of epic `sase-1pn` claimed that runner slot quarantine and admission refusal policies had been migrated to the `sase_core` Rust backend. An architectural audit revealed that this landing repair was never actually integrated into master; the slot-refusal logic continues to reside in Python.

#### Impact & Justification
Core Memory Section 1.3 (*Rust Core Backend Boundary*) and Decision Record 29 (*The Rust Core Is Required*) establish a strict litmus test: core domain and admission behavior must belong in `sase_core` in Rust, callable via `sase_core_rs`. Leaving admission and slot refusal in Python violates the core backend invariant and causes divergences between the CLI, TUI, and external tools.

#### Conflict Check
No active epic is working on slot-refusal policies in `sase-core`. `18a` is working on `#actstat:sase-core` (unrelated activity status module).

#### Recommended Solution
1. Open linked repo `sase-core` via `sase repo open sase-core`.
2. Implement the runner slot-refusal and quarantine admission policy in `crates/sase_core/src/runner/admission.rs`.
3. Expose the Rust functions via PyO3 in `sase_core_rs`.
4. In `src/sase/agent/` in the main repo, replace the Python fallback logic with the `sase_core_rs` binding call.
5. Update `sase-core-revision.txt` to pin the new `sase-core` commit.

---

### Rank 9: `sase-1i6` — Federation IPC Tests Fail Due to `AF_UNIX` Socket Path Length Exceeding 108 Chars

* **Bead ID:** `sase-1i6`
* **Type / Size / Status:** `ci` / `small` / `ready`
* **Confirmed +1s:** 0 (Reproduced on clean master `a10a6c6035`)
* **Created:** 2026-10-08 by `bbugyi200.apollo.sase-1i4.land`
* **Primary Subsystem:** Federation IPC Test Suite / `tests/test_dispatch_federation.py`

#### Problem Statement & Root Cause
In Linux, Unix domain sockets (`AF_UNIX`) have a maximum path length of 108 bytes (`sizeof(sockaddr_un.sun_path)`). In `tests/test_dispatch_federation.py:632`, temporary sockets are created under the pytest `tmp_path`. When SASE runs inside deep workspace paths (e.g. `/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_17/...`), the path length of the socket exceeds 108 bytes. `server.bind()` throws `OSError: AF_UNIX path too long`, the helper thread dies, and the test hangs or fails deterministically on clean master.

#### Impact & Justification
Deterministic CI failure when running tests in standard SASE numbered workspaces (`sase_<N>`). Any developer or agent running federation tests from workspace clones encounters an unavoidable test failure.

#### Conflict Check
Zero conflicts. No active agent touches `test_dispatch_federation.py`.

#### Recommended Solution
1. In `tests/test_dispatch_federation.py`:
   - Change the socket binding fixture to allocate socket files directly in `/tmp` (or via `tempfile.TemporaryDirectory(dir="/tmp")`) using a short randomized name.
   - Ensure proper cleanup in fixture teardown.
2. Verify that `tests/test_dispatch_federation.py::test_ipc_client_decodes_success_and_error_frames` passes cleanly even when executed from a workspace clone with a path > 120 characters.

---

### Rank 10: `sase-1qu` — `test_update_shortcut_dispatch_performs_no_disk_or_subprocess_work` Fails Cold

* **Bead ID:** `sase-1qu`
* **Type / Size / Status:** `ci` / `small` / `ready`
* **Confirmed +1s:** 0 (Verified deterministic on clean master)
* **Created:** 2026-11-02 by `bbugyi200.athena.sase-1qt.land`
* **Primary Subsystem:** TUI Keymap Test Suite / `tests/ace/tui/test_log_panel_keymap.py`

#### Problem Statement & Root Cause
`tests/ace/tui/test_log_panel_keymap.py::test_update_shortcut_dispatch_performs_no_disk_or_subprocess_work` verifies that shortcut dispatch performs no disk or subprocess work by monkeypatching `Path.read_text`, `Path.write_text`, and `subprocess.run`/`Popen`. However, if this test executes in a fresh pytest worker before any other keymap test has run ("cold"), the keymap loader attempts to load default keymap configurations from disk. It encounters the monkeypatch on `Path.read_text` and immediately fails. It only passes if another test in the same process ran first and populated the in-memory cache.

#### Impact & Justification
Order-dependent test failure that breaks pytest-xdist parallel test runs whenever this test is assigned to a fresh worker. This introduces intermittent red CI runs that waste agent turns diagnosing fake keymap regressions.

#### Conflict Check
Zero conflicts. No active agent touches `test_log_panel_keymap.py`.

#### Recommended Solution
1. In `tests/ace/tui/test_log_panel_keymap.py`:
   - Explicitly warm the keymap defaults cache before applying the disk and subprocess monkeypatches:
     ```python
     from sase.ace.tui.keymap import warm_keymap_cache  # or appropriate cache warmer
     warm_keymap_cache()
     ```
2. Verify that running the test alone in a cold pytest process (`pytest -q tests/ace/tui/test_log_panel_keymap.py::test_update_shortcut_dispatch_performs_no_disk_or_subprocess_work`) passes 100% of the time.

---

## 4. Notable Runner-Ups & Honorable Mentions

The following beads were evaluated and are highly recommended as the next tier once the top 10 are underway:

* **`sase-1qm` (Bug, Large)** — *Host completion refuses an unchanged prepared-completion intent with `stale_worktree_fingerprint`*. This is a high-value bug in `sase_core::completion_eval.rs` where a passing check is falsely rejected. It is placed just outside the top 10 because it is complex to reproduce consistently (observed only once under specific cross-repo conditions) compared to the actionable, deterministic fixes above.
* **`sase-1el` (Bug, Large)** — *Bead-assigned phase agents cannot hand off: gate-turn creation fails with `missing_gate_turn_row`*. Blocks epic phase agents from using `/sase_gate` or `/sase_monitor`. Should be prioritized as soon as epic `sase-1qz` (hijack/recovery) settles, ensuring no transaction lock collisions.
* **`sase-172` (CI, Large, +4)** — *`test_load_launchable_prunes_provider_mismatched_prefix` drops genuine bare-git entries*. A deterministic VCS-MRU pruning bug with 4 confirmations.
* **`sase-yn` (CI, Large, +7)** — *`sase-core provider_priority` concurrency test fails with `LockTimeout`*. Affects tests when `TMPDIR` is redirected onto `/home`.
* **Note on `sase-j0` (+38 +1s)** — Marked `in_progress` with 38 +1s (*`just check-full` test cost budgets exceeded*). It is currently under observation while epic `sase-1r2` lands release v0.19.0 and stabilizes Full CI; working on `sase-j0` concurrently with `sase-1r2`'s final landing would create direct conflicts on `test_cost_budgets.json`.

---

## 5. Recommended Execution Roadmap

To maximize developer velocity and minimize test latency, the top 10 beads should be addressed in two focused batches:

### Batch 1: Quick Wins & Test Suite Hygiene (Low Effort, Immediate ROI)
1. **`sase-1q3`** (Small): Scrub `SASE_MODEL_OVERRIDE` in `_clear_agent_env_vars` (stops 7 test failures).
2. **`sase-1qu`** (Small): Warm keymap defaults cache before monkeypatching (fixes cold test failure).
3. **`sase-1i6`** (Small): Move federation IPC socket paths to `/tmp` (fixes AF_UNIX length failure).
4. **`sase-v6`** (Small): Add `set -euo pipefail` and dynamic cargo target discovery to `Justfile`.
5. **`sase-zo`** (Small): Normalize project display name vs canonical key matching in `sase repo open`.

### Batch 2: High-Impact Stability & Security Remediations
6. **`sase-1ot`** (Large): Execute owner-approved history rewrite of `sase--agents` to purge 27 secrets.
7. **`sase-1r7`** (Large): Adopt `CredentialRetry` in sidecar push, AXE runner, finalizers, and bead sync.
8. **`sase-15o`** (Large): Update Antigravity trajectory allowlist and schema validator for `agy` 1.2.7+.
9. **`sase-1r4`** (Large): Classify live-update signature-skew `TypeError`s to eliminate zombie monitors.
10. **`sase-1qv`** (Medium): Port runner slot-refusal policy to `sase-core` in Rust to honor architectural boundaries.
