# Root Cause Analysis and Prevention Plan: Master Branch CI Failures

**Author:** Researcher `gem` (Independent Swarm Investigation)  
**Date:** October 1, 2026  
**Target Repository:** `sase-org/sase`  
**Current HEAD Inspected:** `781063e38e9ea44ffeb0416ae8fb675762c32135`  
**Initial CI Failure Commit:** `5cb968c8cb3057469dd6239172f36953265b7dcd` (September 18, 2026)

---

## 1. Executive Summary

Since **September 18, 2026** (over 1,100 commits ago), the `master` branch of `sase` has been continuously failing in GitHub Actions CI under the `Master Gate` workflow. The last green run on `master` was run `#35299164480` at commit `f90c6b549f6e`. Every single subsequent push has triggered a failing `Master Gate` execution.

On the current tip of `master` (`781063e38e`), the failure is multi-faceted:
1. **The Lint Job (`just lint`)** fails during `_lint-symvision` due to three unused public symbols (`HandoffSubmitResult`, `StarterResolution`, `owner_ref`).
2. **The Test Suite (`just test`)** fails across 7 of the 8 deterministic shards with a mix of:
   - Module import collection crashes (`ImportError` in `test_agent_header_panel.py` cascading into `test_contract_manifest.py`).
   - Stale schema and documentation assertion drift.
   - Out-of-sync test mock signatures after adding new CLI/launcher parameters (`history_text`).
   - Event schema payload additions (`blob_oid`, `included_blob_oids`).
   - Missing CLI completion metadata for newly added subcommands (`memory history --at`).
   - Standard library behavior discrepancies across Python versions (Python 3.12 in CI vs Python 3.14 in local development).

The critical question is **why this was allowed to persist for over 1,100 commits without halting the development pipeline**. Our investigation reveals that this is not merely a collection of isolated test bugs, but the consequence of a **structural decoupling between autonomous agent landing gates and GitHub Actions CI**.

---

## 2. Root Cause Analysis: Why Master Is Failing in CI

The failure state is governed by two layers: the **systemic / architectural breakdown** that allowed broken commits to land on `master`, and the **concrete code defects** currently active on HEAD.

### 2.1 The Systemic Breakdown: How Red Commits Kept Landing

```
+-------------------------------------------------------------------------+
| Local Autonomous Agent Turn                                             |
|                                                                         |
| 1. Runs `just check` (runs only `test-scoped`, NOT full suite)          |
| 2. Known issues annotated via Triage -> verdict: `no_new_failures`      |
| 3. Tool receipt policy in `sase.yml` accepts `[pass, no_new_failures]`  |
| 4. Agent declares completion -> Host finalizer commits to local master  |
| 5. Host finalizer executes `git push origin master`                     |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
| GitHub Remote (`origin/master`)                                         |
|                                                                         |
| - Branch protection on `master`: NONE (HTTP 404: Branch not protected)  |
| - Direct `git push` succeeds unconditionally                            |
+------------------------------------+------------------------------------+
                                     | triggers on push
                                     v
+-------------------------------------------------------------------------+
| GitHub Actions: `Master Gate` Workflow                                  |
|                                                                         |
| 1. Runs `just lint` (bare shell execution -> exit code 1 fails)         |
| 2. Runs `just test` (exhaustive 8-shard fast suite, NOT scoped)         |
| 3. Runs on Python 3.12 (local dev runs Python 3.14 -> argparse skew)    |
| 4. NO triage receipt tolerance -> Workflow FAILS                        |
+-------------------------------------------------------------------------+
```

Our investigation identified four distinct architectural gaps:

#### Gap 1: Scoped Local Verification vs Exhaustive CI Suite
In SASE, agents verify changes locally using `just check` (or `sase tool run just check`). By design (Decision 5: *Check-Full Is Explicit-Only* and Decision 24: *Verification Is Two-Speed*), `just check` executes `just test-scoped`, which selects only tests directly affected by the modified files.
However, `.github/workflows/master-gate.yml` executes `just test`, running the entire non-visual test suite across 8 deterministic shards. When an agent modifies a shared component, unselected downstream tests across other shards break without the agent ever running them.

#### Gap 2: Triage Receipts (`no_new_failures`) vs Zero-Tolerance Bare CI
Under `sase/sase.yml`, the `check` tool specifies:
```yaml
receipt:
  accept: [pass, no_new_failures]
  ttl: 2h
```
When an existing failure (such as an unused symbol in `symvision`) is classified as `KNOWN`, `sase tool run` issues a verdict of `no_new_failures`. Host completion finalizers treat this receipt as sufficient proof to permit landing the commit.
However, in GitHub Actions, `master-gate.yml` runs raw `just lint` and `just test` directly. GitHub Actions does not evaluate SASE triage receipts or forgive "known" failures. A non-zero exit code immediately marks the job as failed.

#### Gap 3: Complete Absence of Branch Protection on `master`
Querying the GitHub API:
```bash
gh api repos/:owner/:repo/branches/master/protection
# Output: {"message": "Branch not protected", "status": "404"}
```
There is no branch protection rule, status check requirement, or merge queue configured on `master`. When host finalizers execute `git push origin master`, GitHub accepts the push immediately regardless of the CI status of prior commits or the pending CI result of the current commit.

#### Gap 4: Python Runtime Skew (Python 3.12 vs 3.14)
- **Local Environment:** The developer and agent environments run Python **3.14.7** (installed by `uv` satisfying `requires-python = ">=3.12"`).
- **CI Environment:** `.github/workflows/master-gate.yml` explicitly specifies:
  ```yaml
  with:
    python-version: '3.12'
  ```
Python 3.14 introduced changes to standard library `argparse` formatting for options with choices (omitting duplicate metavars on short flags). Code and tests authored or updated locally under Python 3.14 pass locally but fail deterministically on Python 3.12 in CI.

---

### 2.2 Concrete Catalog of Failures on HEAD (`781063e38e`)

Below is the exhaustive audit of every failing component on HEAD:

| Job / Shard | Failing Test / Target | Root Cause | Introducing Commit / Context |
| :--- | :--- | :--- | :--- |
| **Lint** | `_lint-symvision` | Unused public symbols: `HandoffSubmitResult` (`src/sase/tool/handoff_launch.py`), `StarterResolution` (`src/sase/tool/starter.py`), and `owner_ref` (`src/sase/tool/owner.py`). | Allowed into master via `no_new_failures` triage in commit `7d2c8e0caab8` and `7884ffe854e5`. |
| **Test (Shard 2)** | `tests/ace/tui/widgets/test_agent_header_panel.py` | `ImportError: cannot import name 'test_hint_document_forces_expansion' from 'tests.ace.tui.widgets.test_agent_header_panel_basic'`. | Commit `c6b802a647` replaced the test in the implementation module with `test_hint_document_leaves_header_collapsed` but forgot to update the re-export facade. |
| **Test (Shard 4)** | `tests/test_contract_manifest.py::test_contract_manifest_matches_marker_selection` | Fails with exit code 2 during `pytest -m contract --collect-only` because Shard 2's `ImportError` breaks global test collection. | Cascading error from `test_agent_header_panel.py`. |
| **Test (Shard 3)** | `tests/test_config_schema_repositories.py::test_config_schema_documents_intrinsic_agents_sidecar_contract` | `AssertionError: assert '~/.sase/projects/<project_key>/repos/agents' in ...`. | Commit `e300173faf` updated the schema description to `~/.sase/projects/<project_key>/repos/<role>` but left the test assertion expecting the hardcoded `agents` path. |
| **Test (Shard 7)** | `tests/main/test_memory_log.py::test_memory_log_json_id_outputs_raw_event` | `AssertionError: {'blob_oid': None, 'included_blob_oids': []}` extra keys in json output. | Commit `297faf1d38` added git blob tracking fields to memory read events without updating the strict dictionary assertion in this test. |
| **Test (Shard 7)** | `tests/main/test_parser_command_help.py::test_memory_help_marks_primary_command_and_init_alias` | `AssertionError: assert '{agent-docs,init,list,log,read,show,web}' in ...`. | Subcommand `history` was added to `sase memory` in `sase-1dr.5`/`.6`, changing the synopsis to `{agent-docs,history,init,list,log,read,show,web}`. |
| **Test (Shard 7)** | `tests/test_agent_artifact_directory_operation_audit.py::test_artifact_directory_operation_sites_are_reviewed` | `AssertionError: Extra items in left set: 'src/sase/bead/attachments/lifecycle.py:quarantine_local_object'`. | New helper `quarantine_local_object` was added to attachments lifecycle without registering it in `_REVIEWED_DIR_OPERATION_CONTEXTS`. |
| **Test (Shard 6)** | `tests/completion/test_kind_coverage.py::test_every_value_slot_is_kinded_choiced_or_hinted` | `AssertionError: uncaptioned completion value slots: memory/history:at`. | The `--at` argument on `sase memory history` was added without defining a completion `ValueKind` or value hint in `kinds.py`. |
| **Test (Shard 5)** | `tests/test_partial_launch_cleanup.py::test_launch_query_rolls_back_partial_multi_prompt_launch` | `TypeError: fail_launch() got an unexpected keyword argument 'history_text'`. | `launch_agents_from_cwd` had `history_text` added to its signature, but the mock in this test did not accept `**kwargs`. |
| **Test (Shard 5)** | `tests/test_axe_run_agent_runner_started_at.py::TestRunStartedAtRecording::test_home_mode_running_marker_cleanup_updates_artifact_index` | `AssertionError: assert 4 == 3`. | Marker update count increased from 3 to 4 during setup due to additional launch metadata tracking. |
| **Test (Shard 8)** | `tests/test_force_reuse_launch_seam_rejection.py` (2 tests) | `AssertionError: Expected launch_agents_from_cwd(..., origin='typed') Actual: (..., origin='typed', history_text=None)`. | Same root cause: signature change in `launch_agents_from_cwd` broke exact mock matching. |
| **Test (Shard 8)** | `tests/test_bead/test_show_images.py::test_parser_help_covers_images_and_open` | `AssertionError: assert '-i, --images' in ...`. | Python 3.12 renders `-i {choices}, --images {choices}` whereas Python 3.14 renders `-i, --images {choices}`. |

---

## 3. How to Fix This (Immediate Remediation)

To restore `master` to a passing state, the following concrete fixes must be applied in a single coordinated patch:

### 1. Fix Symvision Unused Symbols (`just lint`)
- In `src/sase/tool/handoff_launch.py`: Make `HandoffSubmitResult` private (`_HandoffSubmitResult`) or remove from `__all__` if internal.
- In `src/sase/tool/starter.py`: Make `StarterResolution` private (`_StarterResolution`) and update references within the module.
- In `src/sase/tool/owner.py`: Remove unused public `owner_ref` export (the private `_owner_ref` is already used internally).

### 2. Fix Import Error in Test Facade (`test (2)` and `test (4)`)
- In `tests/ace/tui/widgets/test_agent_header_panel.py`: Replace `test_hint_document_forces_expansion` with `test_hint_document_leaves_header_collapsed` in the import list and `__all__`.

### 3. Fix Sidecar Config Schema Assertion (`test (3)`)
- In `tests/test_config_schema_repositories.py`: Update `test_config_schema_documents_intrinsic_agents_sidecar_contract` to check for `~/.sase/projects/<project_key>/repos/<role>` (or verify `~/.sase/projects/<project_key>/repos/` prefix).

### 4. Fix Memory Log JSON Assertion (`test (7)`)
- In `tests/main/test_memory_log.py`: In `test_memory_log_json_id_outputs_raw_event`, add `"blob_oid": None` and `"included_blob_oids": []` to the expected dictionary.

### 5. Fix Memory CLI Help Synopsis (`test (7)`)
- In `tests/main/test_parser_command_help.py`: In `test_memory_help_marks_primary_command_and_init_alias`, update the expected subcommand synopsis string to include `history`:
  `"{agent-docs,history,init,list,log,read,show,web}"`.

### 6. Fix Artifact Directory Operation Audit (`test (7)`)
- In `tests/test_agent_artifact_directory_operation_audit.py`: Add `"src/sase/bead/attachments/lifecycle.py:quarantine_local_object"` to `_REVIEWED_DIR_OPERATION_CONTEXTS`.

### 7. Fix Completion Slot Coverage (`test (6)`)
- In `src/sase/completion/kinds.py`: Add a value hint or kind mapping for `memory/history:at` (e.g. `ValueKind.FILE` or a timestamp/ISO string hint).

### 8. Fix `launch_agents_from_cwd` Mock Signatures (`test (5)` and `test (8)`)
- In `tests/test_partial_launch_cleanup.py`: Update `fail_launch` to accept `**kwargs: object`.
- In `tests/test_force_reuse_launch_seam_rejection.py`: Update `mock_launch.assert_called_once_with(prompt, origin="typed", history_text=None)`.

### 9. Fix Marker Setup Call Count (`test (5)`)
- In `tests/test_axe_run_agent_runner_started_at.py`: Update `assert setup_index_update.call_count == 4`.

### 10. Fix Python 3.12 Argparse Formatting Discrepancy (`test (8)`)
- In `tests/test_bead/test_show_images.py`: In `test_parser_help_covers_images_and_open`, assert `"--images"` and `"-i"` individually rather than the literal substring `"-i, --images"`, ensuring compatibility across Python 3.12 and 3.14.

---

## 4. How to Prevent This in the Future (Systemic Prevention)

Fixing the current 12 breakages will turn master green, but without structural changes, master will inevitably break again within days. We recommend four systemic guardrails:

### Guardrail 1: Establish Protected Branches and Automated Staging Lane
Autonomous agent pushes directly to `master` must be intercepted by a gatekeeper.
- **Option A (GitHub Merge Queue / Protected Branch):** Enable branch protection on `master`. Require the `Master Gate` workflow checks (`lint` and all 8 `test` shards) to pass before commits are integrated. Agents push to feature branches or PRs, and GitHub merges only when green.
- **Option B (Fast Integration Staging Branch):** If autonomous direct-trunk workflow is preserved, have host finalizers push to a `staging` branch. A lightweight Actions workflow tests `staging`, and upon success fast-forwards `master`.

### Guardrail 2: Eliminate the Landing Bypass for Unclean Checks
The contract between SASE triage and commit finalization must be tightened:
- **Decision Rule:** A `no_new_failures` verdict must **not** authorize pushing to `master` unless those failures are hermetically skipped or quarantined. If a failure cannot be resolved, the agent must not land on master.
- When `just lint` fails, it must fail the finalizer before `git push origin master` can ever be executed. A commit should never be pushed to upstream master if `just _lint-symvision` exits with code 1.

### Guardrail 3: Align Local and CI Python Runtime
To eliminate environment skew:
- Check in `.python-version` specifying `3.12` at the root of the repository so `uv` automatically creates local development virtualenvs matching CI.
- Alternatively, upgrade GitHub Actions runners to the version of Python actively used in development, but maintain a single pinned minor version (e.g. Python 3.12 or 3.13) across both `.python-version` and CI matrix definitions.

### Guardrail 4: Pre-Push Sharded Fast-Suite Verification in Finalizers
`just check` is appropriate for rapid inner-loop iteration during an agent's turn. However, before the host finalizer executes `git push origin master`:
- The host finalizer should run a fast pre-push gate (or at least run tests on changed modules and their dependent test suites).
- For significant refactors affecting root components (`sase.main`, `sase.agent.launch`), run `just test` across affected shards prior to pushing.

---

## 5. Recommended Implementation Roadmap

1. **Step 1 (Immediate Repair):** Apply the 10 code and test fixes detailed in Section 3 in a dedicated PR/commit. Verify locally with `just _lint-symvision` and all 8 shards of `just test`.
2. **Step 2 (Runtime Pinning):** Add a root `.python-version` file pinned to `3.12` to guarantee local tests match CI argparse and stdlib semantics.
3. **Step 3 (CI / Finalizer Enforcement):** Update `commit_dispatch` / host completion logic to disallow pushing to remote master if `just _lint-symvision` fails, preventing "KNOWN" triage annotations from masking lint breakages.
4. **Step 4 (Branch Protection):** Configure GitHub branch protection on `master` requiring `Master Gate` status checks to pass.
