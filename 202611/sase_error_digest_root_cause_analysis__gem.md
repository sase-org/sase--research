# SASE Error Notification Storm Root Cause Analysis

**Author:** Researcher `gem` (Independent Investigation)  
**Date:** November 8, 2026  
**Target Digest:** `~/.sase/axe/error_digests/digest_20261108_064118.txt` on `athena`  
**Related Digest Artifacts:** `digest_20261107_233611.txt` through `digest_20261108_064118.txt`  

---

## 1. Executive Summary

Bryan reported experiencing recurring error notifications in SASE, specifically pointing to `~/.sase/axe/error_digests/digest_20261108_064118.txt` on `athena` as an example. 

An independent investigation across the SASE codebase, AXE scheduler logs, git repositories, and host state reveals that:

1. **The Primary Incident (100% of errors in `digest_20261108_064118.txt`):**  
   Every single one of the 100 errors in `digest_20261108_064118.txt` (and the recurring hourly "100 error(s) in the last hour" notification flood since midnight on Nov 8) is caused by the scheduler job `agent_publication` failing to clone a non-existent GitHub repository: `git@github.com:sase-org/sase-spotify--agents.git`.

2. **The Mechanism:**  
   - On **Saturday, Nov 7 at 11:32 EST**, the project `sase-spotify` was configured with `is_sase_managed: true` in `sase/sase.yml` and enabled in SASE on `athena`.
   - In SASE, any managed project automatically infers standard sidecar companion repositories, including the `agents` sidecar (`sase-spotify--agents`), with remote `git@github.com:sase-org/sase-spotify--agents.git`.
   - However, `sase repo init` was never run to create this repository on GitHub.
   - At **23:34:43 EST on Nov 7**, an automated documentation chop (`bbugyi200.athena.chop.refresh_docs.sase-spotify.2_471527.1`) created commit `37c9ca8293714019cf92afcfe9746b09765bbe8b` in `sase-spotify_10`. A second chop created commit `ae2c3c31041d08df8f86f2883fba4f5cdee9cc33` at **02:34:26 EST on Nov 8**.
   - These commits automatically enqueued 2 publication requests into the project's agent publication outbox (`gh_sase-org__sase-spotify`).
   - AXE's `publication` routine runs `agent_publication` periodically (~every minute). Because 2 active requests exist, `agent_publication` attempts to drain them by cloning the target sidecar repository.
   - Because `sase-org/sase-spotify--agents` does not exist on GitHub, git exits with code `128` (`Repository not found`).
   - This failure prevents outbox draining, leaving both requests queued (`active_remaining=2`). Because the failure happens during `ensure_agents_clone` before individual items are processed, retry count counters are not incremented and items are never quarantined. The job fails repeatedly on every tick (~60–100 times per hour), triggering hourly digest notifications capped at 100 errors.

3. **Secondary Cascading Failures:**  
   - In `digest_20261108_055917.txt`, error #8 is `housekeeping` / `artifact_run_prune` with `protection_unavailable`. SASE's ACE-run retention system requires `beads` and `plans` sidecars for every enabled project. Because `sase-spotify` is missing both `sase-spotify--beads` and `sase-spotify--plans` on disk, `artifact_run_prune` halts to avoid pruning protected runs.
   - Other peripheral errors in earlier digests on Nov 7 include `artifact_link_backfill` timing out after 300s (due to large stream processing in `bob-cli`), and a single transient lock wait in `gate_turn_reclaim`.

4. **Recommended Solution:**  
   Run `sase repo init` in the `sase-spotify` primary checkout (`~/projects/github/sase-org/sase-spotify/`) on `athena` to create and connect the remote sidecars (`agents`, `beads`, `plans`). Once `sase-spotify--agents` exists, `agent_publication` will immediately drain the 2 pending requests, and both `agent_publication` and `artifact_run_prune` will return to healthy 0-error status.

---

## 2. Notification & Digest Evidence

### 2.1 The Notification Flood on `athena`
Checking the notification inbox via `sase notify list -j -l 50 --sender axe` on `athena` reveals an aggressive hourly flood of error notifications:

| Timestamp (EST) | Notification ID | Notes | Attached Digest File |
| :--- | :--- | :--- | :--- |
| 2026-11-08 06:41:18 | `(digest generation)` | — | `digest_20261108_064118.txt` |
| 2026-11-08 05:59:17 | `2a432070-5ad2-42d5-be26-4380cbf43450` | `35 error(s) in the last hour` | `digest_20261108_055917.txt` |
| 2026-11-08 05:49:23 | `f546a464-781a-400a-8993-c5c05fb0452d` | `100 error(s) in the last hour` | `digest_20261108_054923.txt` |
| 2026-11-08 04:47:37 | `9aa61189-7981-4b61-8142-2e91ee5b72ec` | `100 error(s) in the last hour` | `digest_20261108_044737.txt` |
| 2026-11-08 03:45:46 | `2161b45f-b76f-408d-83c5-6f4b763f3303` | `100 error(s) in the last hour` | `digest_20261108_034546.txt` |
| 2026-11-08 02:43:58 | `86255eaf-6954-469c-8c5d-8c74b7c6aad9` | `100 error(s) in the last hour` | `digest_20261108_024358.txt` |
| 2026-11-08 01:42:03 | `16426a28-c0ab-4814-bacd-42f324ce803a` | `100 error(s) in the last hour` | `digest_20261108_014203.txt` |
| 2026-11-08 00:38:03 | `6aa3eab9-f0a5-4d86-baea-9027a73814f0` | `100 error(s) in the last hour` | `digest_20261108_003803.txt` |
| 2026-11-07 23:36:11 | `63830776-e14b-4a32-8ff8-776c822b778e` | `2 error(s) in the last hour` | `digest_20261107_233611.txt` |

Prior to `2026-11-07 23:36:11`, error notifications were infrequent (e.g. 1 error in an hour for routine maintenance). Starting at 23:36:11 on Nov 7, the system saturated the 100-error limit on every digest cycle.

### 2.2 Inspection of `digest_20261108_064118.txt`
All 100 error sections in `digest_20261108_064118.txt` share identical parameters:
- **Routine:** `publication`
- **Job:** `agent_publication`
- **Error summary:** `agent_publication: projects=8 hood_drained=... active_remaining=2 ... errors=1`
- **Subprocess Output:**
  ```text
  [agent_publication] gh_sase-org__sase-spotify: could not clone configured agents sidecar: Cloning into '/home/bryan/.sase/projects/gh_sase-org__sase-spotify/repos/.sase-agents-clone-XXXX/checkout'...
  ERROR: Repository not found.
  fatal: Could not read from remote repository.

  Please make sure you have the correct access rights
  and the repository exists.
  agent_publication: projects=8 hood_drained=... active_remaining=2 parked=0 lock_busy=0 deferred_projects=0 errors=1
  Structured job result: check_error ...
  ```

---

## 3. Deep-Dive Root Cause Analysis

### 3.1 Project Origin and Configuration
On Nov 7, 2026, `sase-spotify` was onboarded to SASE:
- **Git commit `763d2a6`:** Sat Nov 7 11:32:53 EST (`chore: mark repository as SASE-managed`).
- **File content of `sase/sase.yml`:**
  ```yaml
  is_sase_managed: true
  ```
- **Project Registration:** Registered under directory key `gh_sase-org__sase-spotify` in `/home/bryan/.sase/projects/gh_sase-org__sase-spotify/gh_sase-org__sase-spotify.sase` with workspace `/home/bryan/projects/github/sase-org/sase-spotify/`.

### 3.2 Sidecar Auto-Injection in SASE
When `is_sase_managed: true` is present, SASE automatically synthesizes sidecar companion repositories.
In `src/sase/_linked_repo_config_defaults.py` (`inject_default_linked_repos`):
```python
    for hidden_role, hidden_description, hidden_visibility in (
        (AGENTS_SIDECAR_ROLE, DEFAULT_AGENTS_DESCRIPTION, "public"),
        (ATTACHMENTS_SIDECAR_ROLE, DEFAULT_ATTACHMENTS_DESCRIPTION, "public"),
        (ATTACHMENTS_PRIVATE_SIDECAR_ROLE, DEFAULT_ATTACHMENTS_PRIVATE_DESCRIPTION, "private"),
    ):
        hidden_identity = resolve_sidecar_repo_identity(
            {"name": hidden_role, DEFAULT_LINKED_REPO_MARKER: True},
            primary_workspace_dir=primary_workspace_dir,
            default_entry=True,
            config=config if config is not None else local_config,
        )
```
In `src/sase/_linked_repo_identity.py`, `_derived_sidecar_repo` generates the slug `{primary.name}--agents`:
- Slug: `sase-spotify--agents`
- Remote URL: `git@github.com:sase-org/sase-spotify--agents.git`
- Machine path: `~/.sase/projects/gh_sase-org__sase-spotify/repos/agents`

Querying GitHub using the GitHub CLI confirms the repository's status:
```bash
$ gh repo view sase-org/sase-spotify--agents
GraphQL: Could not resolve to a Repository with the name 'sase-org/sase-spotify--agents'. (repository)
```
The remote repository **does not exist on GitHub**.

### 3.3 The Trigger: Documentation Stitches and Outbox Enqueueing
At Saturday 23:34:43 EST and Sunday 02:34:26 EST, two automated documentation chops executed in workspace `sase-spotify_10`:
1. `37c9ca8293714019cf92afcfe9746b09765bbe8b`: `docs: complete command and configuration references` (Agent: `bbugyi200.athena.chop.refresh_docs.sase-spotify.2_471527.1`)
2. `ae2c3c31041d08df8f86f2883fba4f5cdee9cc33`: `docs: correct and clarify command and configuration references` (Agent: `bbugyi200.athena.chop.refresh_docs.sase-spotify.2_471527.2`)

When each commit finished, the post-commit workflow step in `src/sase/workflows/commit/workflow_publication.py` enqueued an agent publication entry into SASE's durable outbox.

Inspecting `active_agent_publications("gh_sase-org__sase-spotify")` confirms these two entries:
```python
AgentPublicationOutboxItem(
    project_key='gh_sase-org__sase-spotify',
    local_agent='chop.refresh_docs.sase-spotify.2_471527.1',
    primary_revision='37c9ca8293714019cf92afcfe9746b09765bbe8b',
    artifacts_dir='/home/bryan/.sase/projects/gh_sase-org__sase-spotify/artifacts/ace-run/202611/07/20261107120335',
    attempts=0,
)
AgentPublicationOutboxItem(
    project_key='gh_sase-org__sase-spotify',
    local_agent='chop.refresh_docs.sase-spotify.2_471527.2',
    primary_revision='ae2c3c31041d08df8f86f2883fba4f5cdee9cc33',
    artifacts_dir='/home/bryan/.sase/projects/gh_sase-org__sase-spotify/artifacts/ace-run/202611/07/20261107120457',
    attempts=0,
)
```

### 3.4 The Infinite Loop in `agent_publication`
The execution flow for `agent_publication` is as follows:
1. `src/sase/scripts/sase_chop_agent_publication.py` invokes `run_publication_job()` (`src/sase/agents_sync/publication_job.py`).
2. `_run_publication_job` resolves all enabled projects. It detects 8 enabled projects on `athena`, including `gh_sase-org__sase-spotify`.
3. For `gh_sase-org__sase-spotify`, it checks `active_agent_publications()`, finds 2 active entries, and calls `drain_selected_agent_publications` (`src/sase/agents_sync/_commit_publication_drain.py`).
4. In `drain_agent_publications`:
   ```python
   clone_error = git_sync.ensure_agents_clone(
       target,
       git_runner=git_runner,
       lock_timeout_seconds=timeout,
   )
   if clone_error is not None:
       timer.stage = "ensure_clone"
       timer.outcome = "clone_failed"
       timer.error = clone_error
       timer.failure_scope = REPOSITORY_FAILURE_SCOPE
       return _record_failure(...)
   ```
5. `ensure_agents_clone` (`src/sase/agents_sync/_git_sync_ops_git.py`) sees that `~/.sase/projects/gh_sase-org__sase-spotify/repos/agents/.git` does not exist and attempts:
   ```bash
   git clone --origin origin git@github.com:sase-org/sase-spotify--agents.git <temp_checkout>
   ```
6. GitHub denies the clone because the repository does not exist (`ERROR: Repository not found`).
7. `ensure_agents_clone` returns `"could not clone configured agents sidecar: ..."`.
8. Because the failure is at the repository level (`REPOSITORY_FAILURE_SCOPE`), the drain terminates immediately.
9. **Critical Loop Mechanism:** Because execution failed before iterating over outbox items, `item.attempts` is never incremented. Outbox items only enter quarantine or park status after repeated failed item attempts. As a result, the items remain permanently active (`active_remaining=2`), causing AXE to retry on every tick indefinitely.

---

## 4. Analysis of Secondary & Historical Errors

### 4.1 `artifact_run_prune: protection_unavailable` (Nov 8, 05:59:17)
In `digest_20261108_055917.txt`, error #8 occurred in `housekeeping / artifact_run_prune`:
```text
artifact_run_prune protection source unavailable: sase-spotify:beads
artifact_run_prune protection source unavailable: sase-spotify:plans
reason=protection_unavailable
```
**Root Cause:**
In `src/sase/core/agent_artifact_run_protection.py`, `_REQUIRED_SIDECAR_ROLES = ("beads", "plans")`. Before purging expired ACE-run directories, SASE scans the beads and plans sidecars of all enabled projects to ensure that run directories referenced by open beads or active plans are protected.
Because `sase-spotify` has not been initialized with `sase repo init`, `sase-spotify--beads` and `sase-spotify--plans` do not exist. SASE fails closed to prevent data loss and aborts the prune pass with `protection_unavailable`.

### 4.2 `artifact_link_backfill: timed out after 300s` (Nov 7, 07:47 & 12:03)
In `digest_20261107_084222.txt` and `digest_20261107_120333.txt`:
```text
[artifact_link_backfill] gh_bobs-org__bob-cli: touch index re-reduced 740 stream(s)
[artifact_link_backfill] gh_bobs-org__bob-cli: done in 184.86s
[artifact_link_backfill] gh_sase-org__sase: starting ...
Job timed out after 300s (SIGKILL, exit code -9)
```
**Root Cause:**
`artifact_link_backfill` iterates sequentially through all enabled projects. When `gh_bobs-org__bob-cli` required re-reducing 740 streams (taking 184.86s), only ~115s remained for subsequent projects. Processing `gh_sase-org__sase` exceeded the remaining window and was terminated by the 300s job timeout.

### 4.3 `gate_turn_reclaim: reclaim_errors` (Nov 7, 17:27)
In `digest_20261107_182402.txt`:
```text
gate turn reclaim failed: sase-1rs.11--gate: GateError: timed out waiting 5s for lock on .../.gate_followup.lock; held by pid 2356907
```
**Root Cause:**
A transient lock contention. PID 2356907 was actively holding `.gate_followup.lock` to complete an accepted gate turn when the reclamation pass ran, exceeding the 5s acquisition timeout. This was resolved on the next cycle once the gate process exited.

---

## 5. Verification: What `sase repo init --check` Reports

Running `sase repo init --check` in `/home/bryan/projects/github/sase-org/sase-spotify/` on `athena` directly validates our findings:

```text
SASE initialization check

Needs attention:
  run  init repo  create or connect configured sidecar repositories, refresh sidecar guide files, declare the plans, beads, research, and agents sidecars and update repository ignore rules
       ~ update  sase/sase.yml                                                                            +20                    declare the managed plans, beads, research, and agents sidecars (private: sase-org/sase-spotify is private)
       + create  sase/repos/plans                                                                         –                      create or connect the provider plans sidecar repository
       + create  sase/repos/beads                                                                         –                      create or connect the provider beads sidecar repository
       + create  ~/.sase/projects/gh_sase-org__sase-spotify/repos/agents                                  –                      create or connect the provider agents sidecar repository with private visibility at the machine-level hidden path
       + create  .gitignore                                                                               +1                     ignore host-scoped linked repository clones
```

`sase repo init` is explicitly waiting to create:
1. The remote GitHub sidecar repositories (`sase-spotify--plans`, `sase-spotify--beads`, `sase-spotify--agents`).
2. The local machine-level hidden clone path at `~/.sase/projects/gh_sase-org__sase-spotify/repos/agents`.
3. The configuration updates in `sase/sase.yml`.

---

## 6. Recommended Solution & Action Plan

To completely stop the error notifications and restore normal operation across all SASE routines, follow this procedure on `athena`:

### Step 1: Initialize `sase-spotify` Sidecars
Change into the primary checkout of `sase-spotify` on `athena`:
```bash
cd /home/bryan/projects/github/sase-org/sase-spotify
sase repo init
```
This interactive command will:
- Prompt for confirmation to create the missing GitHub repositories under `@sase-org` (`sase-spotify--plans`, `sase-spotify--beads`, and private `sase-spotify--agents`).
- Initialize local checkouts and clone `sase-spotify--agents` to `~/.sase/projects/gh_sase-org__sase-spotify/repos/agents`.
- Update `sase/sase.yml` with explicit sidecar declarations and commit them.

*(Note: If you do not want `sase-spotify` to have sidecars or be SASE-managed, alternative steps are provided in Section 6.2).*

### Step 2: Verify Publication Drain
Once the `sase-spotify--agents` repository exists, trigger a manual run of the `agent_publication` chop:
```bash
sase chop run publication:agent_publication
```
**Expected outcome:**
- `agent_publication` clones `sase-spotify--agents` successfully into `~/.sase/projects/gh_sase-org__sase-spotify/repos/agents`.
- The 2 queued commits (`37c9ca829371` and `ae2c3c31041d`) are drained and published.
- The summary will show `active_remaining=0` and `errors=0`.

### Step 3: Verify Pruning Retention
Trigger a manual run of `artifact_run_prune`:
```bash
sase chop run housekeeping:artifact_run_prune
```
**Expected outcome:**
- `sase-spotify:beads` and `sase-spotify:plans` are now connected and discoverable.
- Pruning preview finishes with 0 unavailable sources and exit status `0`.

---

### 6.2 Alternative Option: If `sase-spotify` Should NOT Have Sidecars
If `sase-spotify` was meant to be a standalone repository without companion sidecars:

1. **Disable sidecar injection in `sase/sase.yml`:**
   In `/home/bryan/projects/github/sase-org/sase-spotify/sase/sase.yml`, change:
   ```yaml
   is_sase_managed: false
   ```
   Or explicitly disable default linked repos:
   ```yaml
   is_sase_managed: true
   repos:
     default_linked_repos: false
   ```

2. **Purge the 2 Orphaned Publication Requests:**
   Because the outbox will still have the 2 queued entries, drain or clear them so AXE does not continue attempting publication:
   Using python in the SASE environment on `athena`:
   ```bash
   /home/bryan/.local/share/uv/tools/sase/bin/python -c '
   from sase.core.agent_publication_recovery import list_agent_publications, acknowledge_agent_publications
   items = list_agent_publications("gh_sase-org__sase-spotify")
   acknowledge_agent_publications([it.logical_key for it in items])
   print("Cleared", len(items), "outbox items")
   '
   ```
   Or disable the project temporarily:
   ```bash
   sase project disable sase-spotify
   ```

---

## 7. Conclusion

The recurring error storm on `athena` (manifesting in `digest_20261108_064118.txt` and consecutive hourly notifications of 100 errors) is neither a transient network flake nor a defect in the publication engine. It is a deterministic failure caused by marking `sase-spotify` as SASE-managed without running `sase repo init` to provision the expected sidecar repositories on GitHub. Once `sase-spotify` is initialized (or its managed sidecars are explicitly opted out), the error storm will cease entirely.
