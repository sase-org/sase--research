# Why the 2026-11-08 axe digest is full of agent_publication errors

_Research report · 2026-11-08 · source: `~/.sase/axe/error_digests/digest_20261108_064118.txt` on athena_
_Swarm researcher mus · independent findings_

## TL;DR

All 100 errors in the example digest share **one root cause**: the background
`publication / agent_publication` job tries to clone the **agents sidecar** for the
`sase-spotify` project (`gh_sase-org__sase-spotify`) on every pass, and the clone
always fails with `ERROR: Repository not found`. The configured remote —
`git@github.com:sase-org/sase-spotify--agents.git`, derived from the primary
`sase-org/sase-spotify` by the standard `<slug>--agents` convention — **does not
exist on GitHub**. Only `sase-spotify` (private) and `sase-spotify--sdd` (public)
exist; `--agents`, `--beads`, and `--plans` all return "Could not resolve to a
Repository". The job reports `errors=1` with exit code 0 roughly every 17 seconds,
so the same failure fills every digest. The 2 queued `sase-spotify` outbox rows
never drain.

**Recommended fix:** on athena, create the missing sidecar repository (human step),
e.g. `sase init repo -p sase-spotify` / `sase repo init`, confirming the
interactive provider-repo creation prompt for `sase-org/sase-spotify--agents`
(public, the hidden-sidecar default). Re-run publication and confirm the 2 outbox
rows drain. Until then, silence the spam with `sase project disable sase-spotify`
or by parking its outbox rows. Neighboring digests show three correlated but
distinct secondary issues (prune `protection_unavailable`, one `gate_turn_reclaim`
lock timeout, recurring `artifact_link_backfill` 300 s SIGKILLs) — see §5.

## 1. What the digest contains

Counts taken directly from the file on athena:

| Fact | Value |
| --- | --- |
| Total entries | 100 |
| Routine | 100 × `publication` |
| Job | 100 × `agent_publication` |
| Projects scanned per pass | 8 |
| Failing project (every entry) | `gh_sase-org__sase-spotify` |
| Subprocess signature (every entry) | `could not clone configured agents sidecar` + `Cloning into '.../.sase-agents-clone-<rand>/checkout'...` |
| Git stderr (every entry) | `ERROR: Repository not found.` + `fatal: Could not read from remote repository.` |
| Occurrences of `Repository not found` | 100 |
| Occurrences of `sase-spotify` | 100 |
| Time span | 2026-11-08 06:08:52 → 06:40:59 EST (~17 s cadence) |
| Job exit code | 0 in all 100 entries (`check_error` structured result, `errors=1`) |

The 100 subprocess lines differ only in the random temp-dir suffix
(`.sase-agents-clone-<8 chars>`); the error text is otherwise byte-identical.
There is exactly one root cause in this file — not several.

A neighboring digest from the same morning (`digest_20261108_055917.txt`, 35
errors) is the same failure in 34 of 35 entries, plus 1
`housekeeping / artifact_run_prune` `protection_unavailable` entry naming
`sase-spotify:beads` and `sase-spotify:plans` as unavailable. The night before
(`digest_20261107_233611.txt`, 2 errors) is 2/2 the same spotify clone failure.

## 2. How the failing remote URL is derived

The clone helper is `ensure_agents_clone` in
`src/sase/agents_sync/_git_sync_ops_git.py:19`, which runs:

```text
git clone --origin origin <remote_url> <temp>/.sase-agents-clone-<rand>/checkout
```

and on nonzero exit returns `could not clone configured agents sidecar: <stderr>`.
The `remote_url` comes from `ProjectTarget.remote_url`, resolved in
`src/sase/agents_sync/targets.py` from the repo inventory's hidden `agents`
sidecar row. That row is auto-injected for managed projects in
`src/sase/_linked_repo_config_defaults.py:150-197`, with identity from
`resolve_sidecar_repo_identity` (`src/sase/_linked_repo_identity.py:34`):

- role `agents` + primary `sase-org/sase-spotify` → derived repo
  `sase-org/sase-spotify--agents` (`_derived_sidecar_repo`: `<slug>--<role>`);
- remote `canonical_ssh_remote("github.com", "sase-org/sase-spotify--agents")`
  = `git@github.com:sase-org/sase-spotify--agents.git`;
- the SDD store record on athena
  (`/home/bryan/projects/github/sase-org/sase-spotify/.sase/sdd-store.json`)
  only knows `sase-org/sase-spotify--sdd`, so there is no stored override.

So the job clones a repo name the convention predicts, but nobody ever created.

## 3. The repo does not exist (verified)

From athena, 2026-11-08:

```text
gh repo view sase-org/sase-spotify --json name,visibility
→ PRIVATE sase-org/sase-spotify

gh repo view sase-org/sase-spotify--agents
→ GraphQL: Could not resolve to a Repository with the name
  'sase-org/sase-spotify--agents'.

gh repo list sase-org (filtered to spotify)
→ sase-spotify PRIVATE, sase-spotify--sdd PUBLIC — no --agents, --beads, --plans
```

Direct checks for `sase-spotify--agents`, `--beads`, and `--plans` all return the
same "Could not resolve" error. The primary's origin is
`git@github.com:sase-org/sase-spotify.git`, so derivation is working as coded —
the target is simply absent (equivalently: renamed, never created, or invisible
to athena's GitHub identity, all of which produce this exact message).

Local project state corroborates a never-completed setup:

- `~/.sase/projects/gh_sase-org__sase-spotify/` has an `agents-publication-outbox.json`
  with **2 active items** (runs `20261107120335`, `20261107120457`, both
  `refresh_docs` scope `revision`, `attempts=0`, never draining);
- `repos/` holds only a stale `.sase-agents-sync-clone.lock` — the sidecar was
  never cloned;
- the primary checkout was created 2026-11-07 17:32 (`Initial commit` +
  `chore: mark repository as SASE-managed`); digest history flips from
  `projects=4` (pre-spotify) to `projects=8` right after, and the spotify clone
  errors start then and never stop.

## 4. Why it spams instead of failing once

- `agent_publication` runs on a tight scheduler loop (~17 s observed here).
- A missing sidecar is a **per-pass, per-project structured error** (`errors=1`,
  exit code 0), not a crash — the scheduler records it, axe batches it into the
  hourly digest, and the next pass retries the identical clone into a fresh temp
  dir. Nothing backsoff or quarantines a clone failure the way the publisher
  parks protection blocks.
- The 2 outbox rows stay `active_remaining=2` (occasionally 1 or 3 as hints
  shift), so every pass has work to attempt and every pass emits the error.
  Occasional `hood_drained=1` / `link_drained=9` lines show the other 7 projects
  still making progress around the failing one.

This also explains the correlated `artifact_run_prune protection_unavailable`
entries in neighboring digests: with no beads/plans/agents clones on the
machine, prune cannot prove protection and refuses to purge
(`purged=0, freed_bytes=0`). Fixing the sidecars clears both.

## 5. What this is not (other errors in nearby digests)

These appear in digests hours apart from the example file and have independent
causes. They are **not** the cause of the 100 errors above:

| Nearby error | Cause | Pointer |
| --- | --- | --- |
| `artifact_run_prune: protection_unavailable` (`sase-spotify:beads/plans`, sidecars not connected) | Same missing-sidecar family as §3; prune fail-closes correctly | This report §4 |
| `gate_turn_reclaim: reclaim_errors` (1 entry 2026-11-07 17:27, 5 s lock timeout held by pid 2356907) | Transient lock contention on one gate followup lock, not a config error | Single-entry transient |
| `artifact_link_backfill: timed out after 300s` (recurring, killed in `gh_sase-org__sase: drain`) | Known O(rows × evidence) per-row evidence reread + single deadline check; already diagnosed | [artifact_link_backfill_timeouts](artifact_link_backfill_timeouts.md) |
| Nov 1–4 `agent_publication` withheld/parked storm on `bob-cli` | `openai-key` scanner false positive on `task-` filenames; different project, different signature (`withheld`, `openai-key`), predates spotify | [agent_publication_errors_still_occurring](agent_publication_errors_still_occurring.md) |

In particular, the Nov 2/Nov 4 scanner bug is **not** present in the example
digest: zero entries mention `withheld`, `openai-key`, or `bob-cli`.

## 6. Recommended solution

**Primary fix (one human step on athena):**

1. `sase init repo -p sase-spotify` (alias `sase repo init`) and accept the
   interactive, default-no prompt to create the missing provider repository
   `sase-org/sase-spotify--agents` (public, per the hidden-sidecar default).
   Repeat for `--beads` / `--plans` if the project needs them — prune already
   lists both as unavailable.
2. Re-run the publication job once and confirm the 2 outbox rows drain and the
   next digest has no `sase-spotify` clone errors.
3. If the sidecar must stay absent (e.g. spotify needs no agent publication),
   do the explicit alternative instead: `sase project disable sase-spotify`,
   or disable just its `agents` sidecar / park the 2 outbox rows, so the
   scheduler stops attempting the clone every 17 s.

Agents must not run the creation themselves: `sase project create … --yes` and
provider-sidecar creation require human confirmation (and `sase gate` for agent
proposals).

**Do not** "fix" this by pointing the sidecar at `--sdd` or another existing
repo: `agents` is a hidden machine-scoped clone with its own format/invariants
(see `repo_inventory.py:317-323`), and repointing would corrupt publication
rather than restore it.

**Separate follow-ups (not this digest):** pursue the backfill index + deadline
fixes in [artifact_link_backfill_timeouts](artifact_link_backfill_timeouts.md);
no action needed for the single reclaim lock timeout unless it recurs.

## Method and confidence

- Read all 100 entries of `digest_20261108_064118.txt` on athena via SSH;
  grepped routine/job/error/subprocess lines and counted `Repository not found`
  (100) and `sase-spotify` (100).
- Cross-checked `digest_20261108_055917.txt` (34/35 same), `digest_20261107_233611.txt`
  (2/2 same), and Nov 1–7 digest signatures to separate the spotify wave from the
  older bob-cli scanner wave and the sase backfill timeouts.
- Traced the clone path in-repo: `_git_sync_ops_git.py:19`,
  `targets.py:85-178`, `_linked_repo_config_defaults.py:150-197`,
  `_linked_repo_identity.py:34-89`, `repo_inventory.py:417-457`.
- Verified on athena: `gh repo view` for `--agents`/`--beads`/`--plans` (all
  unresolvable), `sase-spotify` PRIVATE + `--sdd` PUBLIC, primary origin,
  outbox (2 active rows), and project creation timestamp (Nov 7).
- Confidence: **high** for the single root cause of the 100 example errors
  (uniform signature + confirmed-absent remote). **Medium** that creating the
  `--agents` repo alone fully silences the job — `--beads`/`--plans` absence
  already trips prune, so expect to create those too if publication needs them.
