# Agent publication errors — source and cause (`__mus` report)

Researcher: mus (independent report; peer swarm reports not consulted).
Input: `~/.sase/axe/error_digests/digest_20261102_125554.txt` (71 errors).
Question: where did these errors come from (e.g. what SASE agent introduced them)
and what is causing them?

## What the digest contains

- All 71 entries are identical in shape: `Routine: publication`,
  `Job: agent_publication`, `Exit Code: 0`, structured result `check_error` with
  `agent_publication: projects=4 ... active_remaining=13/14/15 ... errors=1`.
- Every entry names the same project: `gh_bobs-org__bob-cli` (bob-cli).
- Every entry carries `run withheld by publication protection`. 68 of 71 also carry
  `prompt archive withheld by publication protection` three times. 3 entries
  (12:20:02–12:21:27) additionally carry deferred-restore failures for
  `bbugyi200.athena.bob-cli-fs.2.1.land@fdc34de9bf82` and `@07e115192e51`
  (`prompt archive is unresolved and a missing local source does not prove
  there was no prompt obligation`).
- `active_remaining` sits at 13–15: the drain is not making progress and the
  backlog is parked, not draining.

## Cause (mechanism)

Per-tick `agent_publication` runs `run_publication_job`
(`src/sase/agents_sync/publication_job.py`). For bob-cli the drain hits a
withheld run, the settlement error text becomes the project-pass error, and:

- `_ProjectPass.error` set → `summary.errors += 1`
  (`src/sase/agents_sync/publication_job.py`, `_drain_project` / `_run_publication_job`);
- the chop (`src/sase/scripts/sase_chop_agent_publication.py`) maps any
  `tick.errors` to `status = "check_error"` while the process still exits 0;
- axe records one digest entry per tick (roughly every ~45 s), so one stuck
  project produces dozens of near-identical entries.

Withholding itself is by design. A `meta.json` hit is a *structural*-kind block,
so the whole run is withheld (`HoodWithheldError` in
`src/sase/agents_sync/_publication_snapshot_hood.py`; gating in
`src/sase/agents_sync/_publication_snapshot_gating.py`). Withheld prompt-archive
files are parked via `src/sase/agents_sync/prompt_archive/protection.py`
(`PROMPT_PROTECTION_BLOCKED`). The errors=1 is therefore the job correctly
reporting "one project could not drain", not a crash.

## What introduced the offending content

The durable protection ledger
(`~/.sase/projects/gh_bobs-org__bob-cli/agents-publication-protection.json`,
40 records, all `credential_pattern` / `openai-key` scanner hits) shows the
trigger record:

- `2026-11-01T18:49:40-05:00` — `blocked`,
  `agents/bbugyi200.athena.research.5n.mus/meta.json`, line 1,
  `affected_requests: ["run-3b02694d6c5c25650ef1b8b1aeaf87df"]`.

That is ~2 minutes before the first digest error (`2026-11-01T18:51:56`,
`active_remaining=1`). The agent is:

- `bbugyi200.athena.research.5n.mus` — the mus researcher of the prior
  5-researcher swarm `research.5n` (clan generation `20261101183856`, i.e.
  launched ~18:38:56 Nov 1), running `muse-spark-1.3-contributor` via the muse
  provider (per its `meta.json` metadata).
- Its sidecar sync (`801f02528`, `chore(agents): sync from bbugyi200.athena`,
  18:44:40) is the only sidecar commit touching that agent's directory, landing
  ~5 minutes before the block.
- Its run is **still `active`** (`finished_at: null` in its `state.json`), and
  its outbox item is nonterminal with
  `last_error: "run withheld by publication protection"`. This one stuck active
  run is what makes every subsequent tick report `errors=1`.

The scanner rule is `openai-key` = `sk-[A-Za-z0-9_-]{20,}`
(`crates/sase_core/src/note_attachment/scanner.rs:176-178` in the linked
`sase-core` checkout). Two verified limits on precision:

- The scanner deliberately stores no matched values (asserted in
  `agent_publication_protection.rs` tests), so the exact offending substring is
  unrecoverable from the ledger.
- I reconstructed the V2 metadata payload for that agent from its committed
  `meta.json` using the repo's own serialization: it is byte-identical to the
  file on disk (sha256 `0d0c945e…fb1240`, ≠ ledger `a1386f82…106b4`) and
  contains **no** `sk-` match. The offending bytes were therefore transient
  working-tree/lane state at 18:49:40 that was never committed — consistent
  with the agent being mid-run.

Later contributors (Nov 2) kept the project stuck and added the prompt-archive
messages: `bob-cli-fs.8.1.1`/`8.1.2` (07:36), `bob-cli-ft.3.1.2` monitors
(08:37), `bob-cli-fs.8.1.3` (08:48, incl. `prompts/202611/bob-cli-fs.8.1.3.md`),
`bob-cli-fx.2` (11:08, incl. `prompts/202611/bob-cli-fx.2.md`), and
`bob-cli-fx.land--code` (11:51) — all `openai-key` blocks. Prompt-archive
withholds first appear in digest `085818` (Nov 2 07:58); Nov 1 digests show
only `run withheld`. Their current on-disk files are likewise clean, so the
same transient-content note applies.

## Ruled out: Nov-1-evening code changes

Commits in the onset window (`9066546`, `82cf08` — `toobig-92/93`
publication-state-repair refactors; `a7920799` staged-handoff reclaim) touch
only `_publication_state_repair_observation*`, staged-handoff, and monitor
files — not gating, scanning, or ledger code. Protection itself dates to Oct
26–27 (`sase-1oh.5.1.1`, codex; `sase-1oh.5.1.3`, grok) with a scan-reuse perf
change Oct 31 (`sase-1qh.3`, codex). Same-rule blocks back to Oct 26
(`bob-cli-an.*`) never produced perpetual errors because those runs
completed/parked. The trigger here is content (an `sk-`-like string in an
active run's bytes), not a code regression.

## Separate pre-existing backlog (not this incident)

220 of 301 bob-cli outbox items carry the chronic
`could not restore deferred prompt archive … prompt archive is unresolved`
error (old agents such as `12s`, `bob-cli-aj.*`). That backlog predates this
incident and is a different failure mode from the protection withholds.

## Timeline of events

| Time (EST) | Event |
|---|---|
| Oct 26–27 | Publication protection lands (`sase-1oh.5.1.1`, `sase-1oh.5.1.3`); `openai-key` blocks seen since Oct 26 without perpetual errors |
| Oct 31 13:15 | Scan-reuse perf change (`sase-1qh.3`) |
| Nov 1 15:54 | Last clean state (digest `163736`: only an unrelated housekeeping timeout) |
| Nov 1 18:38:56 | `research.5n` swarm generation launches (incl. mus researcher, muse-spark) |
| Nov 1 18:44:40 | Sidecar sync `801f02528` publishes the mus agent's files |
| Nov 1 18:49:40 | Ledger: `research.5n.mus/meta.json` BLOCKED (`openai-key`, line 1) |
| Nov 1 18:51:56 | First `agent_publication` error (`active_remaining=1`, run withheld only) |
| Nov 1 19:59 | `3e6c19ee` bounds drain cleanup (after onset; no gating change) |
| Nov 2 07:36–11:51 | Follow-on blocks (`fs.8.1.x`, `ft.3.1.2`, `fx.2`, `fx.land--code`); prompt-archive withholds begin (digest `085818`) |
| Nov 2 12:01–12:55 | Target digest: 71 entries, `active_remaining` 13–15, 3 transient deferred-restore failures at 12:20 |
| Nov 2 13:02 (now) | `research.5n.mus` still `active`; outbox item still `run withheld by publication protection`; latest ticks unchanged |

## Root cause diagnosis (summary)

The errors are the publication job faithfully reporting a stuck project, once
per tick. The project is stuck because the **still-active** agent
`bbugyi200.athena.research.5n.mus` (prior `research.5n` swarm's muse
researcher, `muse-spark-1.3-contributor`) had bytes matching the `openai-key`
credential pattern (`sk-…`) in its scanned `meta.json` payload at 18:49:40 on
Nov 1; as a structural-kind block this withholds the whole run, and because
the run never finished, every drain tick since 18:51:56 reports `errors=1`
→ `check_error` → one digest entry. Nov-2 agents added further `openai-key`
blocks (run + prompt-archive kinds), widening the symptom to the triple
`prompt archive withheld` lines and growing `active_remaining` to 13–15. No
code change in the onset window touched the gating/scanning path; the
protection behavior predates the incident (Oct 26–27) and previously fired
without perpetual errors. Remediation belongs on the content side (finish or
dismiss the stuck `research.5n.mus` run so its bytes leave the active set;
clear/replace the `sk-`-like strings) and optionally on the reporting side
(decide whether a steady-state protection withhold should stay `check_error`
every tick or be downgraded once parked), plus the separate chronic
deferred-prompt-archive backlog (220 items) which is out of scope here.
