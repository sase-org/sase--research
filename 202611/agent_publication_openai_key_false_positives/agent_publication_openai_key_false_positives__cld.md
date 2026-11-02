# Agent Publication Errors: A False-Positive Secret Hit That Retries Forever and Starves bob-cli's Queue

_Researcher: cld · 2026-11-02 · Input: `~/.sase/axe/error_digests/digest_20261102_125554.txt`_

## TL;DR

- **What the digest shows.** All 71 errors in the digest come from one place: the
  `publication/agent_publication` chop for one project, **`gh_bobs-org__bob-cli`**. Every
  pass (about every 45 s) ends with `errors=1` because four outbox requests are
  "withheld by publication protection". This has been going on since
  **2026-11-01 18:51 EST**, with about 1,515 digest entries so far.
- **What triggered it.** The research agent **`research.5n.mus`** (Muse model, swarm
  `research.5n`, launched 2026-11-01 18:38) registered its report as
  `blocked-task-why-visual__mus-cf5c493312ed.md`. That artifact path is written into the
  run's `agent_meta.json`. The Rust secret scanner's `openai-key` rule,
  `sk-[A-Za-z0-9_-]{20,}`, has no word boundary, so it matches the substring
  `sk-why-visual__mus-cf5c493312ed` inside "ta**sk-**why…". The run was blocked as if it
  contained an OpenAI key. Its swarm siblings used `blocked_task_…` (underscores) and
  were not flagged. Two later bob-cli agents (`bob-cli-fs.8.1.3`, `bob-cli-fx.2`) hit the
  same false positive through `scripts/test-task-status-cycler-…` in their prompts.
- **Why it never goes away.** Commit `c687d8b6eb` (10-27) settles withheld requests with
  `increment_attempts=False` and no quarantine threshold. A blocked digest can never
  become clean, because the content is immutable and the regex is deterministic. So the
  request is retried and reported as an error on every pass, forever.
- **Why it matters beyond noise.** In `publication_job._drain_project` (`4356cffaa1`,
  10-30), an error in the *hinted* batch breaks out of the loop. It also skips the
  fallback "drain everything ready" loop. The stuck request's hint claim is preserved,
  so it re-hints itself on every pass. **Ten healthy bob-cli publication requests that
  have no hint (linked-scope planner prompt archives) have never been attempted** since
  they were queued; the oldest is 6.5 h old. 66 hint-claim files have also piled up.
- **Root cause in one line.** A word-boundary-less credential regex, applied to
  agent-publication text, produces deterministic false positives on the word "task-".
  The publisher treats a deterministic block as a retryable, never-quarantined error,
  and that error then short-circuits the project's fallback drain loop.

---

## 1. What the digest actually contains

`digest_20261102_125554.txt` covers 12:01:08 → 12:55:42 EST on 2026-11-02 and contains
71 errors. All of them are `Routine: publication / Job: agent_publication` with exit
code 0 but `check_error`:

```
[agent_publication] gh_bobs-org__bob-cli: run withheld by publication protection;
  prompt archive withheld by publication protection;
  prompt archive withheld by publication protection;
  prompt archive withheld by publication protection
agent_publication: projects=4 hood_drained=0 link_drained=0 ... active_remaining=13|14|15 ... errors=1
```

- 68 of the 71 have exactly that message: one "run withheld" plus three "prompt archive
  withheld".
- 3 of the 71 (12:20–12:21) add a second error class:
  `could not restore deferred prompt archive for bbugyi200.athena.bob-cli-fs.2.1.land@{fdc34de9bf82,07e115192e51}: prompt archive is unresolved and a missing local source does not prove there was no prompt obligation`.
  This class is secondary; see §6.

Across all digests, the "withheld" errors first appear at **2026-11-01 18:51:56**
(`digest_20261101_195153.txt`) and are present in every digest after that. They grow
from one clause to two (from 08:47 on 11-02) and then to four (from 11:08):

| Digest window (EST)   | Entries | Message shape                                   |
| --------------------- | ------- | ----------------------------------------------- |
| 11-01 18:51 → 19:51   | 83      | `run withheld`                                  |
| 11-01 19:51 → 11-02 08:47 | ~90–98/h | `run withheld`                              |
| 11-02 ~08:47 → 11:07  | ~77–80/h | `run withheld; prompt archive withheld`        |
| 11-02 11:08 → now     | ~61–71/h | `run withheld; prompt archive withheld ×3`     |

No digest before 11-01 19:51 contains "withheld". All 576 digest files were checked.

## 2. The four stuck requests

From `~/.sase/projects/gh_bobs-org__bob-cli/agents-publication-outbox.json`, there are
301 items: 14 active, 283 quarantined, and 4 terminal. Four of the active items carry a
withheld error. All four have `attempts=0` and have `updated_at` refreshed on every pass:

| Outbox request (global agent)            | Created (EST)   | Scope    | `last_error`                                      | Blocked file (ledger)                                      |
| ---------------------------------------- | --------------- | -------- | ------------------------------------------------- | ---------------------------------------------------------- |
| `bbugyi200.athena.research.5n.mus`       | 11-01 18:45:20  | linked   | run withheld by publication protection            | `agents/bbugyi200.athena.research.5n.mus/meta.json` line 1 |
| `bbugyi200.athena.bob-cli-fs.8.1.3`      | 11-02 08:47:14  | linked   | prompt archive withheld by publication protection | `prompts/202611/bob-cli-fs.8.1.3.md` line 11               |
| `bbugyi200.athena.bob-cli-fx.2` @876ae7  | 11-02 11:07:47  | revision | prompt archive withheld by publication protection | `prompts/202611/bob-cli-fx.2.md` line 141                  |
| `bbugyi200.athena.bob-cli-fx.2` @1115a1  | 11-02 11:08:02  | linked   | prompt archive withheld by publication protection | (same prompt archive)                                      |

The private protection ledger is
`~/.sase/projects/gh_bobs-org__bob-cli/agents-publication-protection.json`. It records
every one of these as `status=blocked, reason=scanner_hit`, with evidence
`{"kind":"credential_pattern","rule_id":"openai-key","rules_version":1}`.

## 3. Trigger: a false-positive `openai-key` hit on the word "task-"

### 3.1 The rule

In the linked `sase-core` repo, `crates/sase_core/src/note_attachment/scanner.rs:176-179`:

```rust
fn openai_re() -> &'static Regex {
    RE.get_or_init(|| Regex::new(r"sk-[A-Za-z0-9_-]{20,}").unwrap())
}
```

There is no `\b` before `sk-`. Any hyphenated identifier containing `task-` followed by
20 or more `[A-Za-z0-9_-]` characters therefore matches. The rule was added on
2026-09-30 in sase-core `7806f587` ("core attachment audience policy and scanner",
agent `sase-1d5.1`), originally for note attachments. On 2026-10-26 it was reused for
agents-sidecar publication protection by sase-core `416db289` and sase `f4591e9106`
(agent `sase-1oh.5.1.1`, codex/gpt-6-luna). Agent-publication text started being
scanned with it from that point.

### 3.2 What research.5n.mus actually wrote

`research.5n.mus` is run dir
`~/.sase/projects/gh_bobs-org__bob-cli/artifacts/ace-run/202611/01/20261101183900`. Its
`agent_meta.json` line 369 contains its registered report artifact:

```
…/artifacts/agents/gh_bobs-org__bob-cli/20261101183900/blocked-task-why-visual__mus-cf5c493312ed.md
                                                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                   regex match: "sk-why-visual__mus-cf5c493312ed"
```

The published `meta.json` is compact JSON, which is why the ledger reports `line 1`.
The same swarm's other researchers did not trip the rule because of how they named
their files:

| Agent              | Report artifact stem                     | Matches? |
| ------------------ | ---------------------------------------- | -------- |
| research.5n.cdx    | `blocked_task_visual_grammar__cdx`       | no (`sk_`) |
| research.5n.cld    | `blocked_reason_checkboxes__cld`         | no       |
| research.5n.grk    | `blocked_reason_checkbox_glyphs__grk`    | no       |
| **research.5n.mus**| **`blocked-task-why-visual__mus`**       | **yes**  |
| research.5n.gem    | `blocked_task_visual_distinctions__gem`  | no (`sk_`) |

### 3.3 The other two are the same false positive

- `bob-cli-fs.8.1.3--2` `raw_prompt.md:11`:
  `node --test scripts/test-task-status-cycler-relation-successors…`
- `bob-cli-fx.2--2` `raw_prompt.md:141`:
  `modified: scripts/test-task-status-cycler-pomodoro-completion…`

### 3.4 Every bob-cli hit is a false positive

I counted every `sk-[A-Za-z0-9_-]{20,}` match across bob-cli's `raw_prompt.md`,
`submitted_prompt.md`, `live_reply.md` and `agent_meta.json` files. **All 1,054 matches
are preceded by `ta`**, i.e. they are `task-…` substrings: `test-task-status…` (915),
`prompt-task-wikilink…` (73), `create-task-dependency…`, `sase-task-bead…`, and so on.
bob-cli is a task manager, so it hits this rule constantly. All 40 records in bob-cli's
protection ledger are `openai-key` hits, dating back to 10-26. Most of them blocked
child runs (`--mon`, `--code`, `--N`) silently, without raising an error (see §4.3). The
tailnet project has 1 `openai-key` record. The sase project has 3
`high-entropy-assignment` records, which I did not investigate.

## 4. Why a single false positive becomes a permanent error and a stall

### 4.1 Withheld requests are never charged, so they never quarantine

`src/sase/agents_sync/_commit_publication_transaction_steps.py:270-285`
(`acknowledge_completed`):

```python
withheld_error = settlement_error_for_withheld_request(...)
if withheld_error is not None:
    hooks.update_publications(..., error=withheld_error,
                              increment_attempts=False, quarantine_threshold=None)
    gate_errors.append(withheld_error)
    continue
```

Prompt-archive blocks get the same treatment through
`should_charge_prompt_protection_failure()` (`prompt_archive/protection.py:602-605`),
which returns `False` for `PROMPT_PROTECTION_BLOCKED`.

`git blame` traces this to **`c687d8b6eb` (2026-10-27 07:07)**, "fix(agents-sync): park
withheld publications without charging quarantine". It was written by agent
**`sase-1oh.5.1.land--3--code`** (grok/grok-4.6) under the plan
`202610/agents_publication_withheld_gaps_closeout.md`. The commit title says "park", but
nothing parks the request. It stays active, it is re-selected on every pass, its error
is re-appended to `gate_errors`, and it surfaces as the project error. Nothing
distinguishes "blocked: the identical bytes will never pass" from "unverified: may pass
later". The ledger already records this, with `publication_content_retry_allowed()`
keeping an exact blocked digest out of retry paths, but the outbox settlement does not
use that signal.

### 4.2 Item errors become the drain's error, and the hinted loop then skips the fallback loop

`_commit_publication_drain.py` (end of `drain_agent_publications`) folds item errors
into the outcome: `error="; ".join(result.item_errors)`. Then
`src/sase/agents_sync/publication_job.py::_drain_project`, all from **`4356cffaa1`
(2026-10-30 00:26)**, "feat(agents-sync): add background publication job", agent
**`sase-1pt.6`** (codex/gpt-6-luna), does the following:

1. Claims the project's doorbell hints and builds `hinted_keys`.
2. **Hinted loop.** It drains the hinted keys. `if outcome.error …: result.error = …;
   result.preserve_hints = True; break` (lines 264-269).
3. **Fallback loop.** `if not result.lock_busy and result.error is None:` drains
   everything ready (line 279). **This step is skipped whenever step 2 errored.**
4. `if not result.preserve_hints: finish_hint_claim(claim)` (line 402). The claim is
   *never* finished while the stuck request remains, so the `research.5n.mus` hint from
   18:45 is re-claimed on every pass.

The result is a self-sustaining head-of-line block:

- Every pass hint-drains `research.5n.mus` (plus `fs.8.1.3` and `fx.2`×2), errors,
  breaks, and never reaches the fallback loop.
- Requests that arrive **with** a new hint (normal `sase stitch create` commits, via
  `workflow_publication.py:426-436`) still get through, because they ride in the hinted
  batch. That is why some passes show `hood_drained=1`.
- Requests that arrive **without** a hint are never selected. Planner prompt-archive
  publications from `axe/run_agent_exec_plan_accept_sdd.py`, which go through
  `prompt_archive/publish.py` with `PUBLICATION_SCOPE_LINKED` and never call
  `append_publication_hint`, rely entirely on the fallback loop.

### 4.3 Why it started at 18:51 on 11-01 and not on 10-26

Scanner blocks have existed since 10-26, but `settlement_error_for_withheld_request()`
returns an error only when the **requested** global agent itself, or its whole hood, is
withheld. Before 11-01, every blocked bob-cli run was a child member (`--mon`, `--code`,
`--3`, …) of a request for a different global agent. Those runs were silently omitted
from the snapshot and the request still acknowledged. The background job only exists
since 10-30. `research.5n.mus` is the first case since then where a **root, requested
run** was blocked. Its request was created at 18:45:20, `done.json` was written at
18:45:27, the ledger block was recorded at 18:49:40, and the first digest error
appeared at 18:51:56.

### 4.4 Evidence the starvation is real

- **Drain telemetry** (`~/.sase/logs/agent_publication_drains.jsonl{,.1}`, 1,007 bob-cli
  records from 11-02 01:30 onward). Every record carries a withheld error.
  `active_requests` per batch is only ever 1–7, never the 13–15 active items. The latest
  record has `active_requests=4` and `distinct_hoods=3`, with stages
  `hood_publish:research` 6.8 s and `inventory_build` 5.4 s over 509 runs scanned.
- **Ten active requests have never been touched.** Each has `attempts=0`, an empty
  `last_error`, and `updated_at == created_at`:
  `bob-cli-fs.2` (06:30), `bob-cli-fs.8` (07:08), `bob-cli-ft.3` (07:34),
  `bob-cli-fs.2.1.land`@cb729a (09:10), `bob-cli-fs.8.1.land` (09:22),
  `bob-cli-ft.3.1.land` (10:38), `bob-cli-fs.2.1.land`@cba88d (11:04),
  `bob-cli-fw.land` (11:21), `bob-cli-fx.land` (11:24), `bob-cli-fs.4` (12:28).
  None of their `(global_agent, revision)` keys appear in any hint file. For example,
  the hint for revision `0095426daa` names `bob-cli-fs.1`, while the outbox row names
  `bob-cli-fs.2`.
- **Hint claims pile up.** `~/.sase/projects/gh_bobs-org__bob-cli/agent_publication/`
  holds **66 `hints.claimed.*.jsonl` files**, the oldest being `research.5n.mus` from
  11-01 18:45. Every pass re-reads all of them and re-runs the artifact-link drain for
  their agents. The heartbeat reports
  `last_outcome: "hood_error; 36 artifact-link rows retained for backfill"` and
  `oldest_active_age_seconds ≈ 65,977` (about 18.3 h).

## 5. Who introduced what (attribution)

| Layer | Commit | Date (local) | SASE agent / model | Contribution to this incident |
| ----- | ------ | ------------ | ------------------ | ----------------------------- |
| Scanner rule | sase-core `7806f587` | 09-30 08:51 | `sase-1d5.1` | Adds `openai-key` = `sk-[A-Za-z0-9_-]{20,}` with no word boundary (note attachments). **Latent false positive.** |
| Protection wiring | sase-core `416db289`, sase `f4591e9106` | 10-26 17:06–17:10 | `sase-1oh.5.1.1` (codex/gpt-6-luna) | Reuses the attachment scanner (rules v1) for agents-sidecar publication. **Exposes the false positive to every chat, prompt and meta file.** |
| Prompt-archive withholding | `0f76e05de4` | 10-27 00:54 | `sase-1oh.5.1.3` (grok/grok-4.6) | Withholds blocked prompt archives (the source of the "prompt archive withheld" clauses). |
| No-charge retry | **`c687d8b6eb`** | 10-27 07:07 | **`sase-1oh.5.1.land--3--code`** (grok/grok-4.6) | Withheld requests settle with `increment_attempts=False, quarantine_threshold=None`. **A blocked request can never leave the active queue.** |
| Background job | **`4356cffaa1`** | 10-30 00:26 | **`sase-1pt.6`** (codex/gpt-6-luna) | Hinted-loop error → `break`, skip the fallback loop, preserve hints. **Turns one stuck request into project-wide starvation plus a per-pass digest error.** |
| Background enqueue | `e69360f49d` | 10-30 02:15 | `sase-1pt.7` (codex/gpt-6-luna) | Commit path enqueues and hints instead of draining synchronously; extends the fallback loop. |
| Trigger content | (run, not a commit) | 11-01 18:38–18:45 | **`research.5n.mus`** (Muse) | Names its report `blocked-task-why-visual__mus`, which the scanner flags. **First root-run block after the job existed.** |
| Same trigger, later | (runs) | 11-02 08:42, 11:02 | `bob-cli-fs.8.1.3--2`, `bob-cli-fx.2--2` | Prompts contain `scripts/test-task-status-cycler-…`. |

The agents-sync commits from 11-01 to 11-02 did not touch the code paths above:
`a0b00da79b`, `0547d23ce3`, `9066546900`, `82cf081fc4`, `3e6c19ee37` ("bound
publication drain cleanup under index-lock contention", `sase-1qt.2`) and `84e22d98be`
("require Rust cleanup policy…", `sase-1qt.land`). They addressed other publication
failure modes (cleanup and index-lock contention, repair deadlines) and neither
introduced nor fixed this one. That fits the "we are still dealing with" observation:
the earlier fixes targeted different errors.

## 6. Secondary error: `.land` deferred prompt archives (3 entries in this digest)

`could not restore deferred prompt archive for bob-cli-fs.2.1.land@fdc34de9bf82 / @07e115192e51: prompt archive is unresolved and a missing local source does not prove there was no prompt obligation`

- **Where it comes from.** `prompt_archive/deferred.py::restore_deferred_prompt_archives`
  passes the case to the Rust classifier
  `sase-core …/agent_publication_recovery/complete.rs` (`PROMPT_STATUS_UNAVAILABLE`,
  `blocks_acknowledgment: true`).
- **The pattern.** The outbox item's `artifacts_dir` points at the `*.land--code` member
  run. Those runs have `prompt_origin: generated` and contain `followup_prompt.md` but
  **no `raw_prompt.md`**. In bob-cli for 202611, 5 of 6 `.land--code` runs lack it. So
  `_local_prompt_source_present()` is `False`, the archive is not in the sidecar, and the
  classifier refuses to acknowledge.
- **How it behaves.** Unlike the withheld errors, this one *is* charged. It quarantines
  after 3 attempts in about 3 minutes, which is why it appears in only 3 entries. It has
  recurred today for `fs.2.1.land` (09:28, 12:18), `fx.land` (11:50) and `fw.land`
  (11:53), each time as a revision/linked pair. So far it has quarantined 8 `.land`
  requests today. It is a separate defect (land-workflow members have no
  `raw_prompt.md` for the deferred prompt archive to use), it limits itself, and it is
  not what keeps the digest firing every 45 s. I did not trace when `.land--code` runs
  stopped writing `raw_prompt.md`.

## 7. Impact

- **Noise.** About 1,515 digest entries in about 18 h (80–98 per hour), all
  `errors=1` with exit code 0.
- **Lost publication for blocked runs.** About 30 bob-cli runs' chat, prompt or meta
  files are withheld from the public `sase--agents` sidecar because of false positives,
  plus 2 prompt archives (`bob-cli-fs.8.1.3`, `bob-cli-fx.2`).
- **Starvation.** 10 legitimate bob-cli requests, including planner prompt archives for
  `fs.2`, `fs.8`, `ft.3`, `fs.4` and several `.land` agents, have not published for up
  to 6.5 h. They will not publish while any withheld request remains hinted.
- **Wasted work.** Each pass re-scans about 509 runs (about 20 s of drain time),
  re-claims 66 hint files, and re-drains artifact links for their agents.
- **Other projects** (`sase`, `tailnet`, `actstat`) are idle and healthy. Projects are
  drained independently and the error is per-project.

## 8. Fix directions (not implemented)

1. **sase-core scanner.** Anchor the vendor-prefix rules, for example
   `(?:^|[^A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}`, or require the real OpenAI shapes
   (`sk-proj-…`, `sk-` followed by 48 alphanumeric characters with no hyphenated English
   words). Bump `rules_version` so the ledger can re-evaluate. Add regression fixtures
   for `test-task-status-cycler-…` and `blocked-task-why-visual__mus-<hex>`. Per the
   Rust-core boundary rule this belongs in `sase-core`, with sase's
   `sase-core-revision.txt` pin moved afterwards.
2. **Settlement.** Treat `blocked` (a deterministic, digest-pinned result) differently
   from `unverified`. Either retire or quarantine the request with a clear terminal
   reason, or truly park it: exclude it from selection until the source digest or
   `rules_version` changes. In both cases, do not count a parked request as a job error.
3. **Job loop.** In `publication_job._drain_project`, a hinted-batch *item* error should
   not suppress the fallback loop. Exclude the already-attempted keys and continue.
   Finish or prune claims whose keys are parked or blocked so hint files stop piling up.
4. **Hints.** Have `publish_prompt_archive` (planner and linked path) append a doorbell
   hint like the commit path does, so those requests do not depend on the fallback loop.
5. **Operator relief for the current state.** There is no supported override. The
   doctor check only says "Sanitize blocked source content and publish its changed
   digest". Once (1) lands with a rules bump, the four stuck requests should clear on
   their own. Until then the only remedies are code changes or deliberate hand edits of
   private state (outbox or ledger), which I have not done and do not recommend without
   your approval.
6. **Secondary.** Resolve the `.land--code` prompt source: use `followup_prompt.md`, or
   classify generated-prompt members as having no prompt obligation.

---

## Timeline (all times EST/EDT local; DST ended 11-01 02:00)

| When | Event |
| ---- | ----- |
| 2026-09-30 08:51 | sase-core `7806f587` (`sase-1d5.1`) adds the attachment scanner with `openai-key = sk-[A-Za-z0-9_-]{20,}` (no word boundary). |
| 2026-10-26 17:06–17:10 | `sase-1oh.5.1.1` wires the scanner into agents-sidecar publication protection (sase-core `416db289`, sase `f4591e9106`). |
| 2026-10-26 22:40 | First bob-cli `openai-key` ledger records (`bob-cli-an.6…` children). Silently withheld, no errors. |
| 2026-10-27 00:54 | `0f76e05de4` (`sase-1oh.5.1.3`) withholds blocked prompt-archive text. |
| 2026-10-27 07:07 | **`c687d8b6eb` (`sase-1oh.5.1.land--3--code`)**: withheld requests retry without charge and never quarantine. |
| 2026-10-28 → 11-01 12:42 | More false-positive blocks on bob-cli child runs (`15h--mon`, `er.2--3`, `f5.land--code`, …). Still silent, because none is the requested root agent. |
| 2026-10-30 00:26 | **`4356cffaa1` (`sase-1pt.6`)**: background `agent_publication` job with the hinted-loop break that skips the fallback loop and preserves hints. |
| 2026-10-30 02:15 | `e69360f49d` (`sase-1pt.7`): commits enqueue and hint for the background job. |
| 2026-11-01 13:23 | Unrelated earlier publication errors (f5.land "required page exists without requested primary revision"; an `AgentRunStateDiscoveryWindowRequestWire` import error in sase). |
| 2026-11-01 18:38 | Swarm `research.5n` (8 agents) launched in bob-cli. |
| 2026-11-01 18:45:20–27 | **`research.5n.mus`** finishes; its publication request and doorbell hint are queued. Its report artifact is named `blocked-task-why-visual__mus-cf5c493312ed.md`. |
| 2026-11-01 18:49:40 | Ledger blocks `agents/…research.5n.mus/meta.json` (`openai-key`, line 1). |
| **2026-11-01 18:51:56** | **First digest error**: `gh_bobs-org__bob-cli: run withheld by publication protection`. It repeats about every 45 s from here on. |
| 2026-11-01 19:59 | `3e6c19ee37` (`sase-1qt.2`) fixes a different publication issue (cleanup and index-lock). No effect on this one. |
| 2026-11-02 06:30 | First hint-less linked request (`bob-cli-fs.2`) queued. Never attempted. |
| 2026-11-02 08:47–08:48 | `bob-cli-fs.8.1.3` prompt archive blocked (`test-task-status-cycler…`). The digest message gains a "prompt archive withheld" clause. |
| 2026-11-02 09:28–09:31 | First `.land` "missing local source" pair quarantined (`fs.2.1.land`). |
| 2026-11-02 09:38 | `84e22d98be` (`sase-1qt.land`) lands another publication fix. No effect on this one. |
| 2026-11-02 11:07–11:08 | `bob-cli-fx.2` prompt archive blocked twice (revision and linked rows). The message now has 4 clauses. |
| 2026-11-02 11:50–11:55 | `.land` "missing local source" quarantines for `fx.land` and `fw.land`. |
| 2026-11-02 12:18–12:21 | `.land` "missing local source" for `fs.2.1.land`@fdc34de9/@07e11519. These are the 3 two-class entries in this digest. |
| 2026-11-02 12:55:54 | Digest written: 71 errors, `active_remaining` 13–15, 66 claimed hint files, oldest active about 18 h. |

## Root-cause diagnosis (summary)

1. **Trigger (content).** On 2026-11-01 at 18:45 the research agent
   **`research.5n.mus`** named its report artifact `blocked-task-why-visual__mus-…`. The
   sase-core credential rule `openai-key` (`sk-[A-Za-z0-9_-]{20,}`, with no word
   boundary; added 09-30 by `sase-1d5.1` and applied to agent publication on 10-26 by
   `sase-1oh.5.1.1`) matched the "**sk-**" inside "ta**sk-**…". Its run's `meta.json`
   was blocked as a leaked OpenAI key. Later, `bob-cli-fs.8.1.3` and `bob-cli-fx.2` hit
   the same rule through `scripts/test-task-status-cycler-…` in their prompts. Every one
   of the 1,054 `sk-` matches in bob-cli's artifacts is this false positive.
2. **Persistence (settlement policy).** Commit **`c687d8b6eb`** (agent
   **`sase-1oh.5.1.land--3--code`**, 10-27) settles withheld requests with no attempt
   charge and no quarantine. A deterministic, digest-pinned block is therefore retried
   and reported as an error on every pass, indefinitely.
3. **Escalation (job control flow).** Commit **`4356cffaa1`** (agent **`sase-1pt.6`**,
   10-30) makes any hinted-batch error break out of the project drain, skip the fallback
   "drain all ready" loop, and keep the hint claim. The stuck request therefore re-hints
   itself forever. bob-cli's 10 hint-less linked requests (planner prompt archives and
   `.land` linked rows) have been starved since 06:30, and hint claims have grown to 66
   files.

The digest errors are the visible symptom of (1) combined with (2). The real damage,
starved publications, comes from (3). A separate, self-limiting defect accounts for the
remaining 3 digest entries: `.land--code` member runs have no `raw_prompt.md`, so their
deferred prompt archives are refused and quarantined.
