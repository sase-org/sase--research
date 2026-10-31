# Agent publication "did not materialize during commit drain": root cause and fix

_Researcher: cld · 2026-10-31 · Scope: the recurring `agent_publication` axe error
notifications (example: `~/.sase/axe/error_digests/digest_20261031_100432.txt`)._

## TL;DR

- **What's failing:** Every time an agent **approves a plan**, SASE archives the planner
  prompt and queues an agents-sidecar publication request. That request is keyed to the
  primary checkout's **current `HEAD`**
  (`src/sase/axe/run_agent_exec_plan_accept_sdd.py:33-55`). The request is
  revision-scoped, because `fulfillment_scope_for_commit_cwd()` returns `revision` for
  the primary checkout (`src/sase/agents_sync/prompt_archive/publish.py:158`).
- **Why it can never succeed:** The Rust completion rule only accepts a revision-scoped
  request if the requested SHA is one of the agent's own published run commits
  (`sase-core: crates/sase_core/src/agent_publication_recovery/complete.rs:48-86`). A
  planner's pre-plan `HEAD` is almost always someone else's commit. Epic planners and
  land agents that only touch sidecars never make a primary commit at all. So the request
  can never be fulfilled. The background publisher retries it 3 times, raising one error
  notification per attempt, then quarantines it.
- **Size of the problem:** 8 of 8 planner approvals since the background publisher went
  live (6 in `sase`, 2 in `bob-cli`) produced exactly this failure. All of today's
  `agent_publication` notifications come from it. The data is **not** lost: the sidecar
  page and the prompt archive were both published. The notification is a false alarm
  from a request whose completion rule is wrong.
- **Why it started on Oct 30:** The bug has been latent since early October, when the
  page+SHA completion gate was added in sase-core (`3d406d4c`, 2026-10-03). It became
  visible on 2026-10-30 when `4356cffaa1 feat(agents-sync): add background publication
  job` started draining the outbox every ~15 s from axe. Each failed attempt now becomes
  `errors=1` → `check_error` → an entry in the digest.
- **Recommended fix:** Give planner prompt-archive requests **page-only (`linked`)
  fulfillment** instead of revision fulfillment. This is a small, Python-only change in
  two files plus tests. I checked it against the installed Rust binding: all six stuck
  `sase` rows flip from `fulfilled=False` to `fulfilled=True` under `linked` scope.
  Follow-ups (optional, ranked below):
  - give the scope a properly named `prompt` value in sase-core;
  - fix the dead `terminal_reason` retirement path, which multiplies notifications;
  - fix a cosmetic footer-parsing warning that clutters every digest.

---

## 1. What the notifications actually say

Digest `digest_20261031_100432.txt` contains one error:

```
Routine: publication   Job: agent_publication
Error:   agent_publication: projects=4 hood_drained=0 link_drained=2 ... errors=1
  dropping projected edge with invalid ref: rule=stitch-bead ref='bead:[sase-1g4.2.1.5]'
  [agent_publication] gh_sase-org__sase: published agent page for
      'bbugyi200.athena.sase-1pj.6' did not materialize during commit drain
```

Two different lines are mixed together here:

| Line                                                     | Is it the error?                                           | Section |
| -------------------------------------------------------- | ---------------------------------------------------------- | ------- |
| `published agent page for '…' did not materialize …`     | **Yes.** This is the `errors=1`.                           | §2–§5   |
| `dropping projected edge with invalid ref … bead:[…]`    | No. It's a WARNING log line captured from stderr.          | §6.1    |

### Frequency and onset (from `~/.sase/axe/error_digests/`)

- The first `did not materialize` digest entry was on **2026-10-30 13:04**
  (`bob-cli-eg.land`).
- Since then, every `agent_publication` error in the Oct 31 digests (01:00, 06:19,
  07:59, 08:59, 09:04, 10:04) has been this class. The affected agents are:
  - `sase-1q5.land`, `sase-1q2.land`, `sase-1q4.land`
  - `sase-1pj.7`, `sase-1pj.6`
  - earlier: `sase-1pj.5.1.land`, `bob-cli-eg.land`, `bob-cli-er.land`
- **Each agent appears exactly 3 times.** The quarantine threshold is 3 attempts, and
  every attempt is reported as its own job error.
- Oct 30 also had other `agent_publication` failures. These were transient and have not
  recurred today:
  - `agent-hood publication did not complete within 120s`
  - `[Errno None] … agents-publication-scans/bytes-…`
  - deferred-prompt-archive failures while the new job drained the old backlog

## 2. Anatomy of a failing request

These are the raw rows from `~/.sase/projects/gh_sase-org__sase/agents-publication-outbox.json`
(trimmed):

```json
{"global_agent": "bbugyi200.athena.sase-1pj.6", "local_hood": "sase-1pj",
 "primary_revision": "2763a6bc58cd…", "scope": "revision", "run_id": null,
 "attempts": 3, "quarantined": true, "terminal": false,
 "last_error": "published agent page for 'bbugyi200.athena.sase-1pj.6' did not materialize during commit drain"}
{"global_agent": "bbugyi200.athena.sase-1pj.7", "primary_revision": "2763a6bc58cd…", "scope": "revision", "run_id": null, ...}
```

Two things stand out:

1. **Two different agents request the same revision.**
2. **`run_id` is `null`.** Rows from the commit workflow always carry
   `SASE_AGENT_TIMESTAMP` (`src/sase/workflows/commit/workflow.py:286`). That points to a
   different enqueue path.

### The requested revisions belong to *other* agents

| Failing request             | Requested SHA  | Who actually committed it (`SASE_AGENT=` trailer) | Failing agent's own `commits.json` in sidecar |
| --------------------------- | -------------- | ------------------------------------------------- | --------------------------------------------- |
| `sase-1pj.6`                | `2763a6bc58`   | `sase-1pj.5.1.land`                               | `[]`                                          |
| `sase-1pj.7`                | `2763a6bc58`   | `sase-1pj.5.1.land`                               | `[]`                                          |
| `sase-1q4.land`             | `4a4b6fede8`   | `sase-1q4.8`                                      | `[]`                                          |
| `sase-1q2.land`             | `eec20f6ad5`   | `sase-1q2.6`                                      | `[]`                                          |
| `sase-1q5.land`             | `cb230adb5e`   | `sase-1q4.3`                                      | `[]`                                          |
| `sase-1pj.5.1.land`         | `c9a65d1a58`   | `sase-1pj.5.1.4`                                  | `[2763a6bc58]` (its *own* later commit)       |

In every case, the sidecar page (`agents/<global>/README.md` and
`sessions/<global>.md`) **exists**. The only thing missing is the association with a SHA
the agent never authored.

### Every row was created at the moment of plan approval

Each row's `created_at` timestamp is within ~1–2 s of two other events: that agent's
`plan_path.json` write, and a `chore(agents): archive prompt for <agent>--plan` commit in
the agents sidecar.

| Agent               | Outbox row created | `plan_path.json` written | Sidecar "archive prompt for …--plan" commit | `plan_action` |
| ------------------- | ------------------ | ------------------------ | ------------------------------------------- | ------------- |
| `sase-1q5.land`     | 10-31 00:45:15     | 00:45:13                 | 00:45:17                                    | `tale`        |
| `sase-1q2.land`     | 10-31 05:23:19     | 05:23:18                 | 05:23:21                                    | `epic`        |
| `sase-1q4.land`     | 10-31 07:39:14     | 07:39:13                 | 07:39:17                                    | `tale`        |
| `sase-1pj.7`        | 10-31 08:52:36     | 08:52:35                 | 08:52:40                                    | `epic`        |
| `sase-1pj.6`        | 10-31 08:56:16     | 08:56:15                 | 08:56:19                                    | `epic`        |
| `bob-cli-eg.land`   | 10-30 12:52:52     | 12:52:51                 | 12:52:54                                    | `tale`        |
| `bob-cli-er.land`   | 10-30 20:29:06     | 20:29:05                 | 20:29:08                                    | `tale`        |
| `sase-1pj.5.1.land` | 10-30 15:00:17     | (other artifacts dir)    | 15:00:20                                    | —             |

**Coverage check:** Since 2026-10-30 09:00, the `sase` agents sidecar has exactly
**6** "archive prompt for …--plan" commits and `bob-cli` has exactly **2**. That gives
8/8 planner approvals → 8/8 failing rows. The failure is deterministic, not intermittent.

## 3. The code path

1. **Plan approval.** `run_agent_exec_plan_accept.py:349` →
   `publish_planner_prompt_archive()`
   (`src/sase/axe/run_agent_exec_plan_accept_sdd.py:20-58`):

   ```python
   revision_result = run_git(Path(ctx.workspace_dir), ["rev-parse", "HEAD"], ...)
   primary_revision = revision_result.stdout.strip()
   outcome = publish_prompt_archive(agent_name, primary_revision,
                                    commit_cwd=ctx.workspace_dir, ...)
   ```

   `HEAD` here is just "whatever the workspace was checked out at when the plan was
   approved". In an epic, that is usually the previous phase's or a sibling's landing
   commit.

2. **Enqueue.** `_publish_prompt_archive()`
   (`src/sase/agents_sync/prompt_archive/publish.py:149-163`) enqueues an
   `AgentPublicationOutboxItem`:
   - `scope=fulfillment_scope_for_commit_cwd(commit_cwd)`. The workspace is the primary
     checkout, so this is **`revision`** (`_commit_publication_queue.py:211-219`).
   - `run_id=_publication_run_id(cites_event_run_id)`, which is `None`.

   The inline step then archives the prompt and pushes it successfully, which produces
   the sidecar commit above. It never acknowledges the outbox row; that is left to the
   drain.

3. **Drain (background `agent_publication` job, every ~15 s).**
   `prepare_publications()` publishes the hood (OK). Then `acknowledge_completed()`
   (`_commit_publication_transaction_steps.py:226-353`) runs these checks:
   - withheld check: OK
   - deferred prompt-archive gate: OK (the archive is already present)
   - `publication_request_fulfilled()` →
     `decide_publication_request_completion` (Rust): **not fulfilled**, with reason
     *"required page exists without the requested primary revision"*.

4. **Accounting.** `update_publications(..., increment_attempts=True,
   quarantine_threshold=3, terminal_reason=error)` (lines 310-323). The job reports
   `errors=1`, which becomes `check_error` and lands in the digest. This repeats on the
   next ticks until `attempts == 3`, when the row is quarantined.

### The Rust rule (sase-core `complete.rs`)

```rust
if !page_exists { return not_fulfilled("required publication page is absent") }
if is_linked_scope(&request.request.scope) { return fulfilled("required page exists for a linked-scope request") }
if revision_associated(kind, …, &primary_revision, &request.runs, &request.containers) { fulfilled } else {
    not_fulfilled("required page exists without the requested primary revision")
}
```

`revision_associated` requires `primary_revision` to be in the commit SHAs of the
agent's own runs, or in the commits of its session container and members. Here is how
that plays out for each kind of planner:

| Planner kind                                         | Can its pre-plan `HEAD` ever be associated?                              |
| ---------------------------------------------------- | ------------------------------------------------------------------------ |
| `epic` planners (phase agents like `sase-1pj.6`)     | **Never.** They never make a primary commit; their child beads do.       |
| `tale` planners                                      | **Never.** The coder's commit is a *new* SHA that descends from the planner's `HEAD`. |
| Land agents with only sidecar commits                | **Never.** `sase-1q4.land` made 11 beads/plans commits and 0 primary commits. |

The revision gate is the right rule for **commit** publication rows. It is the wrong
rule for **planner prompt-archive** rows, which have no commit obligation. Their real
obligation is "the session page exists and the prompt archive exists", and the drain
already checks the prompt-archive half separately.

### Empirical confirmation (read-only)

I ran `_publication_request_completion()` through the installed sase (with its Rust
binding) on the six stuck `sase` rows, once as stored and once with `scope="linked"`:

```
sase-1pj.5.1.land  revision-> fulfilled=False (required page exists without the requested primary revision; kind=session) | linked-> fulfilled=True
sase-1q5.land      revision-> fulfilled=False (...)                                                                  | linked-> fulfilled=True
sase-1q2.land      revision-> fulfilled=False (...)                                                                  | linked-> fulfilled=True
sase-1q4.land      revision-> fulfilled=False (...)                                                                  | linked-> fulfilled=True
sase-1pj.7         revision-> fulfilled=False (...)                                                                  | linked-> fulfilled=True
sase-1pj.6         revision-> fulfilled=False (...)                                                                  | linked-> fulfilled=True
```

### The existing repair tool doesn't cover this

`sase agent sync --repair-revisions -p sase` (report-only, no writes) classifies the
rows as follows:

- `sase-1pj.5.1.land@c9a65d1a588a`: **repaired → `2763a6bc58cd`** ("requested revision
  is an ancestor of recorded run commit").
- The other five: **`unresolved, kept as is (no recorded run commits for this agent)`**.

The stale-revision classifier (`sase-core: agent_publication_recovery/stale.rs:30-89`)
can only rekey a row to a later commit by the same agent. Epic planners and
sidecar-only land agents have no such commit, so the repair tool cannot be the fix.

## 4. Why it showed up now

| Date       | Change                                                                                                                                                         | Effect                                                                                                                                       |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-08-01 | `61075153cb feat(sdd): cross-link plans and archived prompts`: planner prompt archives published with `HEAD`                                                    | Planner rows exist                                                                                                                           |
| 2026-10-03 | sase-core `3d406d4c … page+SHA completion`                                                                                                                      | Revision rows need SHA association. **Planner rows can no longer complete (latent bug).**                                                    |
| 2026-10-24 | `02cd3b39b6` + sase-core `e80f08da`: linked-scope rows fulfill on page existence                                                                               | Fixed this for *linked-repo commits* only; planner rows from the primary checkout are still `revision`                                       |
| 2026-10-30 | `66b15496f9 preserve deferred prompt archive context`                                                                                                           | Planner rows now pass the prompt gate. Before this they failed earlier with "could not restore deferred prompt archive" (124 `sase` + 212 `bob-cli` old quarantined rows of that class) |
| 2026-10-30 | `4356cffaa1 add background publication job` (+ `6d615680b8`)                                                                                                   | The outbox is drained from axe every ~15 s, and **each failed attempt becomes an error notification**                                        |

Older quarantined rows show the same signature before notifications existed, for
example:

- `sase-1oh.land--1--plan@c687d8b6eb` (10-27)
- `sase-1p1.6` (10-27)
- `bob-cli-dd.land--3--plan` (10-27)
- `bob-cli-an.6.6.6.5.6.5.5.land` (10-25)

They failed silently in inline or `sase agent sync` drains.

## 5. Fix options considered

| #   | Option                                                                                                                                       | Verdict                                                                                                                                                                                                                                                                                                      |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A   | **Planner prompt-archive rows enqueue with `linked` (page-only) scope.** `HEAD` stays as the outbox key/anchor.                               | **Recommended.** Python-only, about 10 lines plus tests. Uses the completion rule that already exists. The prompt-archive gate in `acknowledge_completed` still checks the part that matters. Verified to fulfill every stuck row.                                                                              |
| B   | Add a dedicated `prompt` scope in sase-core (completion = page exists; stale classifier = unchanged), wire it through the Python constants and outbox validation | Better long-term naming: "linked" describes linked-repo commits, not planner archives. It crosses the Rust boundary (wire + binding + `sase-core-revision.txt` pin) and touches outbox validation (`_PUBLICATION_SCOPES`). Do it as a follow-up, or instead of A if you want the semantics to be self-describing from day one. |
| C   | Rekey planner rows to the coder's later commit (`--repair-revisions`)                                                                          | Doesn't work for epic planners or sidecar-only land agents (no own commit). It is also racy for tale sessions (the coder may not have committed yet).                                                                                                                                                         |
| D   | Stop enqueueing an outbox row for planner archives                                                                                          | Loses the durable retry vehicle for a prompt archive whose inline publish fails (lock busy, push rejected).                                                                                                                                                                                                  |
| E   | Relax the Rust rule: accept revision rows whose run has zero commits                                                                         | Unsafe. It would silently acknowledge real commit rows whose commit hasn't reached the hood snapshot, which is exactly what the gate exists to catch.                                                                                                                                                        |
| F   | Downgrade the "did not materialize" class to a warning, or notify only at quarantine                                                         | Treats the symptom and would also hide genuine commit-publication losses. It's still worth doing as a *noise* improvement (§6.2), but not as the fix.                                                                                                                                                        |

## 6. Secondary findings in the same digests

### 6.1 `dropping projected edge with invalid ref: rule=stitch-bead ref='bead:[sase-1g4.2.1.5]'` (cosmetic)

- **Source:** `src/sase/artifact_links/projection/_entry.py:51-66` logs a WARNING when a
  projected edge has an invalid ref. The stitch-bead rule walks primary-repo commit
  trailers.
- **Trigger:** Two historical commits have a malformed footer: a bracketed bead ID with
  no `[n]: url` link definition.
  - `sase 8c8c47f720` (2026-10-05): `SASE_BEAD=[sase-1g4.2.1.5]`
  - `bob-cli cc9bd5f5` (2026-10-07): `SASE_BEAD=[bob-cli-5k.3]`

  The footer parser returns the brackets literally, so `bead:[…]` fails ref validation.
- **Impact:** The edge is correctly dropped, but the warning is re-emitted on every full
  projection walk. It shows up in the `agent_publication` and `artifact_link_backfill`
  digests and makes them harder to read.
- **Fix:** Either have the commit-footer parser (Rust, `commit_footer_facade`) treat an
  unresolved `[id]` shortcut reference as the bare `id`, or log it once at DEBUG.
  Low priority.

### 6.2 Each deterministic failure notifies 3×, because the `terminal_reason` retirement path is dead

- **Intended behavior:** `update_agent_publications`
  (`publication_outbox_operations.py:212-279`) is meant to **retire** a request on its
  second identical `terminal_reason` failure ("an indexing race still receives one retry
  before becoming terminal").
- **What actually happens:** `prepare_publications` resets `error=None` on every
  prepared row right after hood publication (`_commit_publication_transaction_steps.py:175-181`).
  So when `acknowledge_completed` charges the failure, the stored `last_error` is always
  `None`. The `item.last_error == terminal_reason` check can never match.
- **Evidence:** Rows end `quarantined=true, terminal=false` after 3 identical errors.
- **Fix:** Compare against the error recorded *before* the prepare reset, for example by
  carrying the prior `last_error` through, or by not clearing it until acknowledgement.
  This cuts deterministic failures to 2 notifications and lands them in the
  `--drop-retired` bucket.
- **Separate improvement:** Have the publisher raise one notification per row state
  transition (to quarantined or retired) rather than per attempt.

### 6.3 Large inert quarantine backlog

| Outbox                                                   | Rows  | Quarantined or retired    |
| -------------------------------------------------------- | ----- | ------------------------- |
| `~/.sase/projects/gh_sase-org__sase/agents-publication-outbox.json` | ~3,550 | All except a handful of in-flight rows (6 active at 10:30); 3.0 MB file |
| `bob-cli` outbox                                         | 278    | All                                                       |

The main error classes in the `sase` backlog are historical:

- 120 s hood-publication timeouts: ~2,900
- "agents sync lock is busy": ~440
- deferred-prompt-archive gate failures: ~124
- "did not materialize": 35

These rows are not retried automatically, so they don't cause today's notifications.
They do bloat `sase agent sync --check` output, and every outbox mutation rewrites the
3 MB JSON under lock.

The report-only `--repair-revisions` pass classifies the `sase` backlog as **993
repairable, 1,938 unresolved, 616 unchanged, 1 linked**. **Do not** run
`--retry-quarantined` across the whole backlog: it would re-attempt thousands of rows
and produce a burst of notifications. Treat cleanup as a separate, deliberate step
(see §7, step 4).

## 7. Recommended solution

**Ship Option A now, then two small hygiene fixes. Do Option B later if you want the
scope name to be self-describing.**

### Step 1: Make planner prompt-archive requests page-scoped (the fix)

In `src/sase/agents_sync/prompt_archive/publish.py`:

1. Add a keyword-only `fulfillment_scope: str | None = None` parameter to
   `publish_prompt_archive` and `_publish_prompt_archive`.
2. Use it when enqueueing:

```python
scope=fulfillment_scope or fulfillment_scope_for_commit_cwd(commit_cwd),
```

In `src/sase/axe/run_agent_exec_plan_accept_sdd.py::publish_planner_prompt_archive`,
pass the scope explicitly:

```python
from sase.agents_sync.publication_outbox import PUBLICATION_SCOPE_LINKED

outcome = publish_prompt_archive(
    agent_name,
    primary_revision,           # anchor/key only: the planner does not own this commit
    ...,
    # A planner's obligation is its session page plus its prompt archive.
    # The prompt-archive gate in acknowledge_completed() enforces the latter.
    # The pre-plan HEAD is usually a sibling's commit and is never one of this
    # agent's run commits, so revision fulfillment can never succeed.
    fulfillment_scope=PUBLICATION_SCOPE_LINKED,
)
```

Leave the commit-workflow call site (`workflow_publication.py:206`) on revision scope.
That caller publishes the committing agent's own post-commit SHA, and the revision gate
is correct there.

**Tests to add:**

- `publish_planner_prompt_archive` enqueues `scope == "linked"`, while the commit-path
  prompt archive still enqueues `revision`.
- A drain of a planner row is acknowledged when the session page and the prompt archive
  exist and the hood has **no** run commits. This is the epic-planner case.
- A tale-planner row is acknowledged even after the coder later commits a descendant SHA.

Then run `just check` per the repo's lint/test conventions.

**Rollout:** The axe publisher runs the globally installed sase, so the fix only takes
effect after a release and reinstall. Global install is human-only.

### Step 2: Fix the dead `terminal_reason` path (§6.2)

Small Python change in `_commit_publication_transaction_steps.py` and
`publication_outbox_operations.py`, so deterministic failures retire after 2 attempts
instead of quarantining after 3. Optionally, change the publication job to notify on
state transitions rather than on every attempt. This isn't needed once Step 1 lands,
but it caps the blast radius of the next deterministic failure class.

### Step 3 (optional, cosmetic): Footer-parser bracket handling (§6.1)

Treat `SASE_BEAD=[id]` with no link definition as `id`, in the Rust footer parser. This
removes the `dropping projected edge … bead:[…]` noise from every digest.

### Step 4 (optional, deliberate cleanup): Existing quarantined rows

The 8 recent planner rows, and the older planner rows like them, are quarantined and
**inert**. They won't notify again. If you want them gone:

- **Once Step 1 is installed:** a one-off script (or a new `--repair-revisions` action)
  can rescope quarantined `revision` rows to `linked` and clear their quarantine. It
  should only touch rows whose agent has no own primary commits **and** whose session
  page and prompt archive exist in the sidecar. Those rows will then be acknowledged on
  the next tick.
- **For the 993 rekeyable historical rows** that `--repair-revisions` reports: review
  the report before `--apply`, and do it per project in a quiet window.

### Step 5 (later, optional): Option B

Introduce an explicit `prompt` publication scope in sase-core: completion = page exists;
stale classifier = unchanged. Mirror it in the Python constants and outbox validation,
bump the outbox schema, and move planner rows from `linked` to `prompt`. Per the Rust
core boundary rule, this also needs the `sase-core-revision.txt` pin bump.

### Expected outcome

After Step 1 is installed, plan approvals stop producing `agent_publication` errors. The
publisher acknowledges each planner row on its first drain, because the session page and
the prompt archive are both already present. The digests go back to showing only real
publication failures.

---

## Appendix: commands and evidence used

All of these are read-only.

```bash
# Digest history
grep -h "did not materialize" ~/.sase/axe/error_digests/digest_2026103*.txt | sort | uniq -c

# Live outbox state and quarantine diagnostics
sase agent sync --check --json
python3 -I <script> ~/.sase/projects/gh_sase-org__sase/agents-publication-outbox.json

# Sidecar truth: pages, commits.json, and prompt archives
#   repo: ~/.sase/projects/gh_sase-org__sase/repos/agents
cat agents/bbugyi200.athena.sase-1pj.6/commits.json   # {"commits":[]}
git log --since='2026-10-30 09:00' --grep='archive prompt for'

# Who authored the requested SHAs
git show -s --format=%B 2763a6bc58 4a4b6fede8 eec20f6ad5 cb230adb5e c9a65d1a58

# Stale-revision classification (report only)
sase agent sync --repair-revisions -p sase --json

# Completion decision under both scopes, via the installed sase + Rust binding
~/.local/share/uv/tools/sase/bin/python -I simulate.py
```
