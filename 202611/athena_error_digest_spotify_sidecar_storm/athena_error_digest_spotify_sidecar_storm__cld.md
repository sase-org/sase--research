# Why athena is flooding you with `agent_publication` errors (and what else is in the digests)

_Research report · 2026-11-08 · machine: athena · source:
`~/.sase/axe/error_digests/digest_20261108_064118.txt` · code checked at sase `master`
`35e4d88efc` (the same commit athena's editable install runs)._

## TL;DR

- **All 100 entries in the example digest are one error.** Every ~17 seconds, the
  `publication/agent_publication` job tries to `git clone`
  `git@github.com:sase-org/sase-spotify--agents.git` and GitHub answers
  `ERROR: Repository not found`. **That repository has never been created.**
  (`gh api repos/sase-org/sase-spotify--agents` → 404.)
- **Root cause: the `sase-spotify` project was only half set up.** On Nov 7 an agent
  (epic `sase-1rs`, phase `sase-1rs.1`) created it through a gated
  `sase project create --setup`. That runs the `create_remote`, `checkout`, `identity`,
  and `manage` steps. The sidecar-creating step, `sase init -p gh_sase-org__sase-spotify`,
  needs a terminal. It was left as a "PROPOSED FOLLOW-UP" for you
  (`sase-1rs.1` note #3) and has not been run yet. So sase-spotify has no agents, beads,
  plans, or attachments sidecar repos.
- **Three code behaviors turn that gap into an endless error loop:**
  1. sase **makes up** the agents sidecar's remote URL from the naming convention
     (`<owner>/<project>--agents`) even when the repo doesn't exist. Because of that, the
     publisher's own "agents sidecar has not been created → skip" branch can never run.
  2. The `refresh_docs[sase-spotify]` chop keeps launching agents that commit. The
     first commit (23:34:43 on Nov 7) queued a publication request; a second one came at
     02:34.
  3. The publisher classes a failed clone as a *repository-scope* failure. These are
     never charged against the queued rows (`attempts` stays 0), never quarantined, and
     **never backed off**. The `publication` routine runs every 15 s, so it retries
     forever and logs a `check_error` each time (~210 per hour, about 1,500 so far).
- **The same half-setup also causes your other recurring error.** The hourly
  `housekeeping/artifact_run_prune` job fails with `protection_unavailable` because
  `sase-spotify:beads` and `sase-spotify:plans` don't exist. It refuses to purge, so
  **~1.26 GB** of prunable run directories have been held back since Nov 7. Most of
  these errors never reached a digest: the digest keeps only the last 100 errors, and the
  `agent_publication` flood pushed them out.
- **Fix now (you, in a terminal on athena, ~5 min):** make the accidentally-public
  `sase-org/sase-spotify--sdd` private, then run `sase init -p gh_sase-org__sase-spotify`
  and accept the agents-sidecar prompt. I ran the read-only check (`-c -j`). It shows init
  will create the agents, plans, and beads sidecars **as private**. Within about 15 s the
  publisher should clone the new repo and publish the 2 queued rows, and both errors
  should stop.
- **Fix in code (so the next new project doesn't do this):** treat "remote repo not
  found" as a persistent, backed-off "not created" state rather than a per-tick error.
  Don't count projects with no agents target as errors. Flag projects whose init is
  still pending. Make the digest group repeated errors with counts. Details are in §6.

---

## 1. What the digest shows

| Field | Value |
| --- | --- |
| Entries | 100 / 100. Every one is `Routine: publication`, `Job: agent_publication` |
| Window | 06:08:52 → 06:40:59 EST (32 min; about one entry every 19 s) |
| Distinct failures | 1: `gh_sase-org__sase-spotify: could not clone configured agents sidecar … ERROR: Repository not found.` |
| Exit code | 0. The job finishes, but `errors=1` makes its structured result `check_error` |
| Summary drift | `active_remaining` is 2 (sometimes 3). `hood_drained`/`link_drained` are occasionally >0 for *other* projects, so the publisher works fine for everything else |

The digest is one of a series. Every hourly digest from **00:38 through 06:41** contains
exactly 100 entries (130,491 bytes each), all this same error:

| Digest | `agent_publication` entries | Other entries |
| --- | --- | --- |
| 2026-11-07 23:36 | 2 (first occurrences: 23:35:49, 23:36:05) | — |
| 2026-11-08 00:38, 01:42, 02:43, 03:45, 04:47, 05:49 | 100 each (capped) | **0**. The flood pushed them out |
| 2026-11-08 05:59 (short 10-min window) | 34 | 1 × `artifact_run_prune` |
| 2026-11-08 06:41 (your example) | 100 (capped) | 0 |

**The real volume is about twice what the digests show.** athena's git-operation log
(`~/.sase/logs/tui_git_ops.jsonl*`) has **1,508** failed `agents_sync.clone` attempts for
`sase-spotify--agents` between Nov 7 18:20 and Nov 8 06:48. Each full hour since
midnight has 203–215 of them, against the 100 the digest keeps.

## 2. Root cause, step by step

### 2.1 sase-spotify was created without its sidecars

From the onboarding journal
(`~/.sase/project_onboarding/journals/sase-org-sase-spotify-f569eb64b274.json`) and
bead `sase-1rs.1`:

- **16:32 UTC (11:32 EST), Nov 7:** `mode: create`, `setup_required: true`. Executed
  steps: `create_remote`, `checkout`, `identity`, `manage`. The journal status is
  `complete`.
- The **TTY-only init step never ran.** `sase-1rs.1` note #1: "The TTY-only init step is
  a handoff that apply never runs under `--json`; it only returns next_argv
  `sase init -p gh_sase-org__sase-spotify`." Note #3 leaves it to you: "PROPOSED
  FOLLOW-UP: Bryan runs `sase init -p sase-spotify` in a terminal."
- `sase-1rs.1` note #2 recorded the result: the agents sidecar is "only an
  auto-injected declaration … `sase-org/sase-spotify--agents` does not resolve". The same
  is true for `--attachments`, `--attachments-private`, and `--beads`.
- The acceptance phase `sase-1rs.11` noted at 17:36 EST that `+spotify` is "blocked
  until Bryan runs `sase init -p sase-spotify` in a terminal". Note #12 re-checked it at
  06:04 EST today: "`sase-org/sase-spotify--agents` still does not exist".

On GitHub today, only the primary repo and the legacy SDD repo exist:

| Repo | Exists | Visibility |
| --- | --- | --- |
| `sase-org/sase-spotify` | yes (created 16:32Z) | private |
| `sase-org/sase-spotify--sdd` | yes (created 22:32Z by a lazy `sase repo open`) | **public** ⚠ |
| `sase-org/sase-spotify--agents` | **no (404)** | — |
| `sase-org/sase-spotify--beads`, `--plans` | **no (404)** | — |

sase-spotify is the **only** one of athena's 8 enabled projects in this state. The other
7 (actstat, body, job, love, tailnet, bob-cli, sase) all have agents, beads, and plans
sidecars, both locally and on GitHub. body and love were onboarded the same morning.
Their `--agents` repos appeared 7–16 minutes after onboarding, which fits someone running
`sase init` in a terminal right afterwards.

### 2.2 sase reports a remote URL for a repo that doesn't exist

`sase repo list -p gh_sase-org__sase-spotify --json` on athena reports:

```text
agents  sidecar  exists=False  source="auto-injected sidecar"
        remote_url=git@github.com:sase-org/sase-spotify--agents.git
sase-spotify--beads  sidecar  exists=False  remote_url=None
sase-spotify--plans  sidecar  exists=False  remote_url=None
```

The URL comes from `inject_default_linked_repos`
(`src/sase/_linked_repo_config_defaults.py:92`). For any `is_sase_managed: true` project,
it adds the hidden `agents` / `attachments` / `attachments-private` rows. It fills in
`SIDECAR_REMOTE_URL_KEY: hidden_identity.remote_url`, which is derived from the naming
convention without checking that the repo exists. (The auto-injected beads/plans rows
use `SIDECAR_REMOTE_URL_KEY: None`.)

That makes the guard in `src/sase/agents_sync/targets.py` unreachable for managed
projects:

```python
if not agents.remote_url:
    outcomes[project_key] = SyncOutcome(..., skip_reason="agents sidecar has not been created")
```

So `resolve_sync_targets` returns sase-spotify as a fully usable publication target,
with a `remote_url` that returns 404.

### 2.3 What filled the queue

`~/.sase/projects/gh_sase-org__sase-spotify/agents-publication-outbox.json` has 2 active
rows, both `attempts: 0`, `last_error: null`, `quarantined: false`:

| Row | Agent | Commit | Enqueued |
| --- | --- | --- | --- |
| 1 | `chop.refresh_docs.sase-spotify.2_471527.1` | `37c9ca8` "docs: complete command and configuration references" (23:34:43) | 23:34:46 EST |
| 2 | `chop.refresh_docs.sase-spotify.2_471527.2` | `ae2c3c3` "docs: correct and clarify command and configuration references" (02:34:26) | 02:34:28 EST |

The `refresh_docs` routine schedules `refresh_docs[sase-spotify]` the same way it does
for every enabled project. Its agents commit and queue publication requests whether or
not the project has an agents sidecar to publish into. The first `agent_publication`
error came **63 seconds after row 1 was queued** (23:35:49). `active_remaining` went from
1 to 2 when row 2 arrived at 02:34. Both match the digest timeline exactly.

(Before 23:34 the same clone already failed silently, once every ~76 min, five times
from 18:20 to 23:26. I couldn't identify which periodic caller made those attempts. They
never produced `check_error`s. The flood started only once there was queued work.)

### 2.4 Why it retries every 15 s with no backoff

1. The `publication` lumberjack runs `agent_publication` every **15 s**
   (`~/.sase/axe/lumberjacks/publication/status.json`: `interval: 15`; `cycles_run: 23,
   errors_encountered: 23` since its 06:41 restart).
2. `drain_agent_publications` (`src/sase/agents_sync/_commit_publication_drain.py:152`)
   calls `ensure_agents_clone`. That runs
   `git clone … sase-spotify--agents.git` in a temp dir under `repos/` and returns
   `could not clone configured agents sidecar: …`.
3. `_record_failure(..., scope=REPOSITORY_FAILURE_SCOPE, stage="ensure_clone")` passes
   the failure to `decide_publication_failure_accounting`. Repository-scope failures are
   **not charged** to rows, so `attempts` stays 0 and nothing reaches the quarantine
   threshold. That makes sense for a brief network problem. A repo that will never exist
   is never ruled out.
4. `publication_job._drain_project` marks the project `repository_error`. Because the
   rows are still "publishable", it rings the project doorbell (`_safe_ring`), and the
   next 15 s tick retries.
5. `sase_chop_agent_publication.py` sets `result.status = "check_error"` whenever
   `tick.errors` is non-zero. axe records each one in `recent_errors.json`, and the
   hourly `error_digest` job writes the digest and the notification.

Nothing in this path remembers that the last N clones failed identically. Nothing turns
"repository not found" into a durable "not created" state. And nothing asks a human to
run the one command that fixes it.

## 3. Your other recurring error has the same root cause

`housekeeping/artifact_run_prune` has failed every hour since Nov 7 (latest run
`20261108T064117`):

```text
artifact_run_prune protection source unavailable: sase-spotify:beads
artifact_run_prune protection source unavailable: sase-spotify:plans
artifact_run_prune: candidates=24307 selected=2634 … bytes=1258243043 … unavailable=2 … reason=protection_unavailable
```

Artifact-run retention needs every enabled project's beads and plans sidecars as
protection sources, and it refuses to purge while any is unavailable (see
`docs/contribute/sdd-storage.md`). For most new projects, the `sidecar_auto_sync`
backstop connects existing sidecars within minutes. For example, apollo showed the same
error for `love:beads`/`love:plans` on Nov 7 until they were connected. sase-spotify's
beads/plans repos **don't exist**, so the backstop can never connect them. It also has
only a legacy single-repo `--sdd` store, while every other project uses split
`--beads`/`--plans`/`--research` sidecars.

Timeline of the unavailable sources in athena's digests:

- Nov 7 07:42: `body:beads`, `body:plans`. Fixed when body was initialized.
- Nov 7 12:03 → 18:24: `sase-spotify:beads`, `sase-spotify:plans` every hour.
- Nov 8 00:38 → 05:49: **missing from the digests.** The 100-entry ring buffer was full
  of `agent_publication` entries.
- Nov 8 05:59, 06:41: still failing (visible in the short 05:59 digest and the run log).

Cost: 2,634 run directories (**~1.26 GB**) selected for pruning have stayed on disk
since Nov 7.

## 4. The rest of what's been in your digests (Nov 4–8)

| Job | When | Cause | Status |
| --- | --- | --- | --- |
| `agent_publication`: sase-spotify clone 404 | Nov 7 23:35 → now; ~1,500 events | §2 | **ongoing** |
| `artifact_run_prune`: `protection_unavailable` | hourly since Nov 7 12:03 | §3 (same root cause) | **ongoing** |
| `artifact_link_backfill`: `timed out after 300s` | Nov 4 → Nov 7 12:03 | per-row re-parse of the release-evidence file (see prior research `202611/artifact_link_backfill_timeouts.md`) | **resolved** by `5692321a2e` (Nov 7 11:12). The last 6 runs all report `ok` |
| `agent_publication`: bob-cli `agent-hood publication did not complete within 120s` | Nov 7 11:40, once | one slow drain | transient |
| `gate_turn_reclaim`: `timed out waiting 5s for lock on …/.gate_followup.lock; held by pid …` | Nov 5 08:56, Nov 7 18:24 | another process briefly held a gate follow-up lock | transient. Retried on the next cycle |
| `sidecar_auto_sync` / `artifact_run_prune` / `stale_running_cleanup` timeouts | Nov 6 14:24, once each | `Could not resolve hostname ssh.github.com` (a short DNS outage on athena) | transient |

apollo does not have sase-spotify and is not affected by §2. Its last digest (Nov 7
16:40) was the transient `love:beads/plans` case described above.

## 5. Adjacent finding: a privacy problem you should fix in the same sitting

`sase-org/sase-spotify--sdd` is **public**, but `sase-org/sase-spotify` is **private**.
`sase-1rs.11` note #7 already traced this. At 22:32Z, an agent's `sase repo open
sase-spotify` lazily created the SDD store through the provider's
`materialize_sdd_store` hook. That path never calls `apply_primary_visibility_policy`;
only `main/repo_init_handler.py` does. The note reports the repo contains only skeleton
commits (READMEs, a PNG, an empty `beads/config.json`), so nothing sensitive has leaked
yet. But it breaks the epic's premise that a private primary gets private sidecars. A
bead search for this found no tracking bead; it exists only as that note's PROPOSED
FOLLOW-UP.

## 6. Recommended solution

### 6.1 Clear the errors now (human-only; needs a TTY on athena)

```bash
# 1. Privacy: close the accidental public SDD repo first.
gh repo edit sase-org/sase-spotify--sdd --visibility private --accept-visibility-change-consequences

# 2. Finish the project setup that onboarding left pending.
sase init -p gh_sase-org__sase-spotify     # answer "yes" to the agents-sidecar prompt

# 3. Verify.
gh repo view sase-org/sase-spotify--agents --json visibility   # expect PRIVATE
sase repo list -p gh_sase-org__sase-spotify                    # agents/beads/plans cloned
```

Why this works: I ran `sase init -p gh_sase-org__sase-spotify -c -j` (read-only) on
athena. Its `repo` planner (16 actions, `requires_tty: true`) would:

- "declare the managed plans, beads, research, and agents sidecars (private:
  sase-org/sase-spotify is private)";
- "create or connect the provider agents sidecar repository with private visibility at
  the machine-level hidden path";
- create or connect the plans and beads sidecars.

After init:

- `ensure_agents_clone` succeeds on the next 15 s tick and the 2 queued rows publish.
  They were never charged, so they are still eligible. `errors` drops to 0.
- The next hourly `artifact_run_prune` has its beads/plans protection sources and
  reclaims the ~1.26 GB.
- Afterwards, check that the legacy `--sdd` store was replaced by the split sidecars. If
  `--sdd` is no longer referenced, retire it. It holds only the two skeleton commits.

**Don't fix this by disabling the agents sidecar for sase-spotify**
(`repos.sidecar.builtin.agents.disabled: true` / `default_linked_repos: false`) without
the code change F2 below. With no agents target, `publication_job.py:160-164` runs
`summary.errors += 1` for that project **on every tick**, whether or not it has queued
work. That is the same 15-second flood with a different message
(`no usable agents publication target`). No test covers that branch.

### 6.2 Prevent it next time (code changes, in priority order)

**F1 — Turn "remote repo doesn't exist" into a persistent, backed-off state instead of a
per-tick error.** (`agents_sync/_git_sync_ops_git.py`, `_commit_publication_drain.py`,
`publication_job.py`)

- When `ensure_agents_clone` fails with a definitive not-found, save a per-project
  `agents_remote_missing` marker with a timestamp. "Definitive" means `Repository not
  found`, or better, the provider's existing preflight returning `not_found` (the
  preflight `sase repo init` already uses).
- While the marker exists, skip the project's drains and re-probe on exponential backoff
  (e.g., 1 min → 1 h cap). Probe immediately when `sase init`/`sase repo init` finishes
  for that project (ring its doorbell).
- Report it **once**: a single notification plus a `sase doctor` WARN naming the fix
  (`sase init -p <key>`), not one `check_error` per tick. Leave queued rows uncharged as
  they are today, so they publish once the repo exists.
- More generally, any repository-scope failure that repeats with the same normalized text
  should back off rather than retry at the full 15 s rate.

**F2 — Count only real errors in `run_publication_job`.** A project whose
`resolve_sync_targets` outcome is a `skip_reason` (disabled, not created) should show in
the heartbeat as `target_unavailable`, not add to `summary.errors`. Only `outcome.error`
should count. Without this, F1's natural implementation (returning a skip) just moves
the flood.

**F3 — Make the inventory say whether a hidden sidecar actually exists.** Today
`inject_default_linked_repos` always fills the agents `remote_url` from the naming
convention, so `targets.py`'s "agents sidecar has not been created" skip never fires.
Add a `provisioned` flag (or a separate `declared_remote_url`), set by `sase repo init` /
the store record. Then consumers like the publisher can skip honestly. Don't just set
the URL to `None`. Other readers need the declared URL, e.g. sase-spotify's privacy
guard (`privacy.py _check_remote`), which deliberately treats a 404 as
`unknown_transcripts` and fails closed.

**F4 — Don't let a project with pending init quietly run scheduled agents.**
`sase project create --setup` marks onboarding `complete` and the project launchable
while `setup_required` init is still pending. The `refresh_docs` routine immediately
starts committing agents there. Options, cheapest first:

- surface "init pending" persistently (TUI badge, `sase doctor`, one notification with
  the exact `sase init -p` command);
- don't schedule per-project chops (`refresh_docs[...]`) until init has recorded
  sidecars;
- have the create gate's follow-up open the init handoff in a terminal.

**F5 — Make the error digest group repeats.** `recent_errors.json` keeps only the last
100 errors (`axe/_state_scheduler.py:178-190`), and the notification says "100 error(s)
in the last hour" no matter how many there really were. One noisy job therefore (a) hid
every other job's errors for six hours, including the `artifact_run_prune` failure, and
(b) under-reported its own count by ~2×. Group by `(job, normalized error)` with
count/first/last, and keep at least one sample per distinct signature.

**F6 — Apply the private-visibility clamp everywhere sidecars get created** (§5). Call
`apply_primary_visibility_policy`, or pass the visibility through the provider options,
in the lazy `materialize_sdd_store` path, not only in `repo_init_handler`. Add a
regression test for `sase repo open` on a private project.

### 6.3 Follow-up tracking

My bead searches turned up nothing that tracks F1–F5. F6 exists only as a PROPOSED
FOLLOW-UP note on `sase-1rs.11`. I did not file beads, because four other researchers
are investigating the same question; the lead can file deduplicated beads from the
synthesis. Suggested sizes: F1 medium, F2 small, F3 small–medium, F4 medium, F5 small,
F6 small.

## Appendix: evidence commands (athena unless noted)

```bash
grep -E '^  Job:' ~/.sase/axe/error_digests/digest_20261108_064118.txt | sort | uniq -c
gh api repos/sase-org/sase-spotify--agents                         # 404 (from apollo)
sase repo list -p gh_sase-org__sase-spotify --json                 # auto-injected remote_url
cat ~/.sase/projects/gh_sase-org__sase-spotify/agents-publication-outbox.json
cat ~/.sase/axe/lumberjacks/publication/status.json                # interval: 15
grep -h sase-spotify--agents ~/.sase/logs/tui_git_ops.jsonl*       # 1,508 failed clones
cat ~/.sase/project_onboarding/journals/sase-org-sase-spotify-f569eb64b274.json
sase init -p gh_sase-org__sase-spotify -c -j                       # read-only init plan
tail ~/.sase/axe/lumberjacks/housekeeping/chops/artifact_run_prune/runs/*.log
sase bead read sase-1rs.1 -r ...; sase bead read sase-1rs.11 -r ...
```
