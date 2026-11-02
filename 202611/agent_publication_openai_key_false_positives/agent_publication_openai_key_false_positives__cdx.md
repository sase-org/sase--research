# Agent publication failures on 2026-11-02: filename false positives, persistent retries, and missing coder prompts

Independent investigation by researcher **cdx**. No reports, chats, or findings from the other `research.5p` researchers were consulted. The unrelated prior agent `research.5n.mus` was inspected only because its publication request is one of the failing requests.

**The dominant errors are false secret detections amplified by publication scheduling.** The Rust OpenAI-key regex matches the letters `sk-` inside ordinary filenames beginning with `task-`. Three agents produced harmless filenames that triggered four persistent publication requests. Publication protection then remembers those content hashes as permanently blocked, leaves the requests active without charging attempts, and reports them as errors on every background pass. A separate pair of requests from `bob-cli-fs.2.1.land` lacks the raw-prompt file that the archive reader requires; those exhausted their retry allowance and were quarantined.

The strongest code-origin attribution is **`sase-1d5.1`**, which introduced the scanner regex in `sase-core` on September 30. The current error flood is an interaction with later work: **`sase-1oh.5.1.1` / `.2` / `.3`** added protection and connected it to publication, **`sase-1oh.5.1.land--3--code`** kept withheld requests active without charging quarantine attempts, and **`sase-1pt.6`** added the recurring publisher and its error reporting. The affected Bob agents supplied ordinary content; they did not introduce the scanner defect.

**Scope and evidence**

The supplied digest was read in full by parsing all its blocks. The investigation also used the live Bob publication outbox and protection ledger, local run metadata and prompt files, selected historical chats through `sase chat show`, source and Git history in the authorized SASE and `sase-core` checkouts, and a read-only reproduction through the installed Rust binding. No production source, outbox, protection ledger, or publication state was changed. The temporary reproduction files were removed.

Source baselines examined:

- SASE: `84e22d98be6b6ab289730573cb2525b11b7d7ea0`.
- `sase-core`: `89a5bd8b810ab20fee5c223bb4b1e40cb2c3ab68`.
- Digest: `/home/bryan/.sase/axe/error_digests/digest_20261102_125554.txt`, SHA-256 `927b549242650db7aadf916cd5d145833092bdae1565b7c20f73840d1ceda75b`.
- Live state was inspected around 13:02–13:06 EST on November 2. It is a later observation, not an immutable snapshot of every state during the digest window.

The digest covers **12:01:08.726352–12:55:42.743296 EST** and contains **71** entries. Every entry is for routine `publication`, job `agent_publication`, and project key `gh_bobs-org__bob-cli`. All subprocess exit codes are **0**, but the structured job outcome is **`check_error`**. This is not contradictory: the wrapper explicitly sets the structured status when the publisher reports errors.

| Digest evidence | Count / meaning |
|---|---|
| One `run withheld by publication protection`, followed by three `prompt archive withheld by publication protection` messages | Present in all 71 entries |
| Only those four messages | 68 entries |
| Those four plus two deferred-prompt failures for `bob-cli-fs.2.1.land` | 3 entries: numbers 24–26 |
| `errors=1` | One project-level error result, not one affected request |
| `lock_busy=0`, `deferred_projects=0` | Neither lock contention nor the job work-budget limit explains this digest |
| Median interval between error timestamps | 44.426 seconds; observed range 41.342–87.321 seconds |

There are successful drains in some entries, so the digest does not establish a total publisher outage. Likewise, `active_remaining=13`–`15` is the overall active-request count, not a count of proven scanner failures.

**The four persistent requests and their actual content**

At the live-state observation, the Bob outbox had 301 rows: 283 quarantined, 4 retired, and 14 active. Only four active rows had the protection errors below; the remaining active rows had no recorded error at that observation. The old quarantined backlog is broader than this digest and was not exhaustively diagnosed.

| Request agent | Revision | Error | Created, EST | Attempts / disposition |
|---|---|---|---|---|
| `research.5n.mus` | `c8a52365e525befb5a1f6a41b2840b9ff46471e4` | Run withheld | Nov 1, 18:45:20 | 0, active |
| `bob-cli-fs.8.1.3` | `f4550e297077687c27c441ce8bafed878df3e921` | Prompt archive withheld | Nov 2, 08:47:14 | 0, active |
| `bob-cli-fx.2` | `876ae775e2681ad981383278b6fd5b61ab704fe6` | Prompt archive withheld | Nov 2, 11:07:47 | 0, active |
| `bob-cli-fx.2` | `1115a14d1e1ff5a286bc963adeadcf6b86b667e2` | Prompt archive withheld | Nov 2, 11:08:02 | 0, active |

The `bob-cli-fx.2` rows originate from commits in the primary and linked plugin repositories. They are two publication obligations for the same agent/prompt, not two independently discovered secrets.

The ledger identifies all relevant hits as `credential_pattern`, rule `openai-key`, scanner rules version 1. The entire Bob ledger contained 40 blocked records, all with that rule; I did not inspect all 40 source texts and do not claim all 40 are false positives.

The relevant harmless filenames are shown as concatenated components below. This preserves exact evidence without making the report itself contain the long false-positive token. Concatenate the components without spaces or punctuation between them.

| Affected source | Exact filename components | Why it matched |
|---|---|---|
| `research.5n.mus` metadata, `output_variables.artifacts[0].path` | `blocked-task-` + `why-visual__mus-cf5c493312ed.md` | The scanner begins at the `sk-` inside `task-`, then consumes the long artifact-name suffix |
| `bob-cli-fs.8.1.3--2`, raw prompt line 11 | `scripts/test-task-` + `status-cycler-relation-successors.cjs`; also `scripts/test-task-` + `status-cycler-successor-wiring.cjs` | Ordinary test filenames copied into a monitor follow-up command |
| `bob-cli-fx.2--2`, raw prompt line 141 | `scripts/test-task-` + `status-cycler-pomodoro-completion.cjs` | An ordinary filename in a Git status listing carried into the continuation prompt |

The first blocked metadata record was created November 1 at **18:49:40.477360 EST**, destination `agents/bbugyi200.athena.research.5n.mus/meta.json`, content SHA-256 `a1386f82a8a4a169bd9955e1778b6374720f4f754620e39b6104676883d106b4`.

The `bob-cli-fs.8.1.3` canonical prompt record was created November 2 at **08:48:05.943177 EST**, destination `prompts/202611/bob-cli-fs.8.1.3.md`, content SHA-256 `984b9b110016bd1297333df05dad607ecf9c2ef5e81ee53a262ff0f8a5c8944f`.

The `bob-cli-fx.2` prompt record was created at **11:08:36.082614 EST**, destination `prompts/202611/bob-cli-fx.2.md`, content SHA-256 `fc514435287107d97b3540389a945b9be08fa55dd0e7d16744b2497dfe41f101`. Its local prompt and published-candidate prompt digest agree. The second revision is blocked by the same candidate identity even though the ledger's first affected-request entry names the primary revision.

**Scanner defect and verification**

In `sase-core`, `crates/sase_core/src/note_attachment/scanner.rs:176–179` defines:

```rust
Regex::new(r"sk-[A-Za-z0-9_-]{20,}")
```

There is no start-of-token or left-boundary requirement. Hyphens and underscores are allowed throughout the suffix. Consequently a sufficiently long English filename containing `task-` is accepted as an OpenAI key candidate. The rule reports a confirmed credential-pattern hit despite having found a substring of an ordinary word.

`git blame` assigns that exact regex to commit [`7806f587b0971816fe2623db835dde4582925063`](https://github.com/sase-org/sase-core/commit/7806f587b0971816fe2623db835dde4582925063), whose `SASE_AGENT` trailer names `bbugyi200.athena.sase-1d5.1`. That is direct attribution to the introducing implementation, rather than an inference from the last file edit.

I invoked the installed `attachment_scan_file` Rust binding on temporary files containing only the filenames above, with an empty environment map to exclude environment-secret matching:

| Input | Installed binding result |
|---|---|
| `ordinary task text` | `clean`, rules version 1 |
| Research artifact basename above | `hit`, `credential_pattern`, `openai-key`, line 1 |
| Relation-successor test path above | Same hit |
| Pomodoro-completion test path above | Same hit |

This directly reproduces the false positives without real credentials or a live publication attempt. The first attempt to run the reproduction with the generic shell Python failed because it could not import `sase.core`; rerunning through the installed SASE Python succeeded. No source tests were modified or broad test suite run for this research-only task.

**Why the failures persist and generate so many notifications**

The failure chain spans the scanner, ledger, outbox, and scheduler:

1. Publication uses the attachment scanner through `src/sase/agents_sync/_publication_protection_scan.py:286–317`. Both rendered run text/metadata and canonical prompt text are checked.
2. A scanner hit becomes a durable `blocked` record identified by repository, destination, and content digest.
3. `prompt_archive/protection.py:433–466` returns the prior block before rescanning identical content. The Rust `publication_protection_retry_allowed` function refuses exact blocked identities, and `publication_protection_resolve_verified_clean` deliberately retains blocked records. Rule-version history is recorded, but it is not an automatic invalidation mechanism.
4. `_commit_publication_transaction_steps.py:270–303` records withheld errors with `increment_attempts=False` and no quarantine threshold. The requests remain active. Existing tests explicitly assert this state and the presence of a withheld item error.
5. `_commit_publication_drain.py:273–291` joins those item errors into `CommitPublicationOutcome.error`.
6. `publication_job.py` selects active rows once their completion marker exists or the ten-minute grace period expires. It has no protection-aware readiness check. An error preserves the hint; ready active work also rings the project doorbell again.
7. `sase_chop_agent_publication.py:11–38` logs the diagnostics and sets `check_error` whenever the per-tick error count is nonzero. The configured publication interval is 15 seconds, with filesystem doorbells and a five-minute fallback. Job work plus the interval is consistent with the roughly 44-second spacing in the digest.

The October 27 change titled “park withheld publications without charging quarantine” therefore parks them only in the sense of preserving them without attempt charges. It does **not** make them dormant to the later scheduler. The October 30 publisher repeatedly reselects them and converts the expected protection refusal into another error result.

A scanner-only fix will **not necessarily clear these existing rows**: the old exact-digest blocks are sticky. Recovery needs an explicit, audited way to revalidate false-positive records under the corrected rule and supersede their old classification. Blindly retrying quarantined rows, dropping retired rows, or reinstalling the same code does not address these four active blocks.

**The separate missing-prompt failures**

Digest entries 24–26 add these two failures for `bob-cli-fs.2.1.land`:

- Primary revision `fdc34de9bf82600e187ef8f6ebb66473fc4d2bbf`, created in the outbox at **12:18:19.802192 EST**.
- Plans-repository revision `07e115192e515d4e1d6db2ab384869ca0ce89030`, created at **12:18:46.536045 EST**.

Both point at run directory:

`/home/bryan/.sase/projects/gh_bobs-org__bob-cli/artifacts/ace-run/202611/02/20261102110455`

The directory exists and contains `followup_prompt.md`, 155 bytes, carrying the approved-plan implementation request. It contains **neither** `raw_prompt.md` nor `raw_xprompt.md`; `submitted_prompt.md` and `prompt_archive_inputs.json` are absent too. Metadata identifies this as `bob-cli-fs.2.1.land--code`, with parent timestamp `20261102104839` and source plan agent `bob-cli-fs.2.1.land--plan`.

The parent directory does contain a 272-byte raw prompt and a planner archive-input record. Thus this is not evidence that no prompt ever existed. The writer and reader disagree about which durable prompt representation the coder turn supplies:

- `axe/run_agent_exec_plan_artifacts.py:34–50` stores the successor prompt as `followup_prompt.md`.
- `agents_sync/prompt_archive/deferred.py:73–85` chooses the explicit request artifact directory first, then requires `resolve_raw_prompt_path` before attempting restoration.
- `legacy_xprompt_names.py:123–127` resolves only the canonical raw filename and its legacy counterpart. It does not consider the follow-up file or the parent's planner inputs.
- The Rust classifier in `agent_publication_recovery/complete.rs:89–140` refuses acknowledgment when restoration did not occur, no canonical archive was recognized, and the snapshot does not positively establish that no prompt is required.

The error text is therefore an intentional completeness guard exposing a prompt-persistence/resolution gap. It is not another scanner hit. The observed absence plus this code path establishes why restoration cannot start from the selected directory. I did not reconstruct every historical snapshot or prove which original change first made coder directories lack raw prompts; attribution of that older omission to one agent would exceed the evidence. The follow-up writer is long-standing, so blaming its most recent caller edit would be misleading.

The two requests reached **three attempts** and were quarantined at **12:21:17.923723** and **12:21:17.933919 EST**. The corresponding digest error timestamps are **12:20:02.291677**, **12:20:45.230005**, and **12:21:27.357019**. Their disappearance from later entries means retries stopped; it does not mean the archives were repaired. The outbox also retains earlier quarantined requests from the same session, but those are outside the supplied digest's two new failures.

The primary commit's own trailer confirms `SASE_AGENT=bbugyi200.athena.bob-cli-fs.2.1.land` and `SASE_MODEL=codex/gpt-6-luna`. Its title is “fix(task-complete): finish relation successor core.” This identifies the affected commit producer, not the author of the publication bug. The run's `done.json` retains some parent/provider metadata, while `agent_meta.json`, the chat header, and commit trailer identify the coder execution; I used those more specific records for attribution.

**Code-origin attribution and what the previous fixes did**

| Change | Agent in commit metadata | Relevance |
|---|---|---|
| `sase-core` `7806f587b097` | `sase-1d5.1` | Introduced the unbounded OpenAI-key regex; direct root defect |
| `sase-core` `f9aa563c1` and SASE `1a69c8947d` | `sase-1nf.10.1.1` and `sase-1nf.10.1.3` | Added/connected failure accounting and the conservative prompt-completeness gate; explains the missing-prompt error text and retry charging |
| SASE `f4591e9106` | `sase-1oh.5.1.1` | Added protection state and the scanner adapter |
| SASE `67edb9677d` | `sase-1oh.5.1.2` | Applied protection to transcript/run publication |
| SASE `0f76e05de4` | `sase-1oh.5.1.3` | Applied protection to prompt archives and avoided attempt charges for protection refusals |
| SASE `c687d8b6eb` | `sase-1oh.5.1.land--3--code` | Explicitly retained withheld run requests at zero attempts and returned their item errors |
| SASE `66b15496f9` | `sase-1pt.5` | Preserved deferred archive context and preferred the request's artifact directory; did not add follow-up-prompt resolution |
| SASE `4356cffaa1` | `sase-1pt.6` | Added recurring publication job and `check_error` reporting |
| SASE `e69360f49d` | `sase-1pt.7` | Shifted commit publication onto the background queue |
| SASE `6d615680b8` | `sase-1pt.9.1` | “Stop stale publication retries” addressed retained link hints and Referenced By processing; its diff does not fix withheld publication readiness or the regex |

This sequence explains why prior publication fixes can be real improvements while these errors remain. Preserving protected content, avoiding quarantine charges, and enabling background publication were individually reasonable behaviors; their combined state contract lacks a distinct non-runnable protection-blocked state.

**Repair implications, without applying changes**

A complete correction should cover three boundaries:

- Correct the core scanner's token boundaries and credential-shape policy. Add regression cases using the benign filename components above and positive credential-shaped controls. A left-boundary check addresses this demonstrated substring bug; it should not be treated as a complete secret-detector design by itself.
- Separate protected, unverified, runnable, and failed publication states. Confirmed unchanged blocks should remain visible without being continuously scheduled or generating identical error digests. A changed digest or reviewed rule revalidation should make work eligible again. Add an integration test from scanner result through outbox selection and structured job status; the existing drain tests enforce no-charge behavior but do not demonstrate a quiet scheduler.
- Persist or resolve the exact coder prompt through a common durable contract. Test accepted-plan coder turns, parent/session identity, and multiple repository commits. For the two affected rows, recover the precise coder prompt from recorded follow-up evidence, verify its archive and provenance, and only then release the selected quarantined requests. Do not substitute an arbitrary parent prompt merely because it is available.

A corrected scanner also needs a reviewed migration/revalidation path for existing false-positive ledger records. The current “resolve verified clean” API intentionally preserves confirmed blocks, so neither a rules-version bump nor an ordinary retry alone guarantees recovery. The 40 historical blocked records and the 283 quarantined requests warrant separate classification; clearing them wholesale would discard useful evidence and mix different failures.

**Evidence locations for follow-up**

The local state paths are `~/.sase/projects/gh_bobs-org__bob-cli/agents-publication-outbox.json` and `agents-publication-protection.json`. These were inspected read-only. The run directories used for the persistent requests are `artifacts/ace-run/202611/01/20261101183900`, `artifacts/ace-run/202611/02/20261102084201`, and `artifacts/ace-run/202611/02/20261102110218`, under that project directory. Relevant evidence is in `agent_meta.json`, `raw_prompt.md`, and `done.json`; no peer research report was opened.

Selected completed transcripts were accessed with `sase chat show --agent … -f raw`:

| Agent selector | Saved transcript beneath `~/.sase/chats/202611/` |
|---|---|
| `research.5n.mus` | `gh_bobs_org__bob_cli-ace_run-research_5n_mus-261101_183900.md` |
| `bob-cli-fs.8.1.3--2` | `gh_bobs_org__bob_cli-ace_run-bob_cli_fs_8_1_3__2-261102_084201.md` |
| `bob-cli-fx.2--2` | `gh_bobs_org__bob_cli-ace_run-bob_cli_fx_2__2-261102_110218.md` |
| `bob-cli-fs.2.1.land` | `gh_bobs_org__bob_cli-ace_run-bob_cli_fs_2_1_land__code-261102_104839.md` |

The last filename uses the parent timestamp even though the outbox selects coder run directory `20261102110455`; that distinction matters when investigating the missing prompt. Commit attribution above comes from repository history and `SASE_AGENT` trailers, not from a researcher's claim about who wrote a change.

**Timeline of events**

Times are America/New_York, with explicit UTC offsets because daylight saving time ended between the October and November events. Commit times below use Git committer time; enqueue and detection times use their durable state fields.

| Time | Event |
|---|---|
| Sep 30, 08:51:54 −04:00 | `sase-1d5.1` introduces the attachment scanner and the `openai-key` regex in core commit `7806f587b097`. |
| Oct 20, 17:20:54 / 19:44:10 −04:00 | `sase-1nf.10.1.1` and `.3` establish core failure accounting and the Python drain's prompt-completeness checks. Missing prompt evidence is no longer success. |
| Oct 26, 17:10:06 −04:00 | `sase-1oh.5.1.1` adds durable publication protection state in `f4591e9106`. |
| Oct 26, 20:17:10 −04:00 | `sase-1oh.5.1.2` connects protection to transcript/run publication in `67edb9677d`. |
| Oct 27, 00:54:32 −04:00 | `sase-1oh.5.1.3` connects protection to prompt archives in `0f76e05de4`. |
| Oct 27, 07:33:19 −04:00 | `sase-1oh.5.1.land--3--code` keeps withheld requests active without attempt charges in `c687d8b6eb`. |
| Oct 30, 00:24:35 −04:00 | `sase-1pt.5` preserves request-specific deferred prompt context in `66b15496f9`. |
| Oct 30, 01:19:13 / 02:15:51 −04:00 | `sase-1pt.6` adds the background publisher; `sase-1pt.7` changes commits to enqueue publication. |
| Oct 30, 06:13:01 −04:00 | `sase-1pt.9.1` fixes a different stale-retry path involving links; protected hood requests remain eligible. |
| Nov 1, 18:45:20 −05:00 | The unrelated `research.5n.mus` report commit creates its publication request. |
| Nov 1, 18:49:40 −05:00 | Its artifact basename inside metadata trips `openai-key`; the run is durably blocked. |
| Nov 2, 08:47:14 / 08:48:05 −05:00 | `bob-cli-fs.8.1.3` enqueues; its test-command filename trips prompt protection. |
| Nov 2, 11:07:47–11:08:36 −05:00 | Two `bob-cli-fx.2` revisions enqueue; a Git status test filename trips the same scanner rule. |
| Nov 2, 12:01:08 −05:00 | First supplied digest entry already shows the four persistent protection diagnostics. This is the digest boundary, not their original onset. |
| Nov 2, 12:17:57 −05:00 | `bob-cli-fs.2.1.land--code` lands primary revision `fdc34de9bf82`. |
| Nov 2, 12:18:19 / 12:18:46 −05:00 | Primary and plans publication rows enqueue using coder directory `20261102110455`, which has a follow-up prompt but no raw prompt. |
| Nov 2, 12:20:02 / 12:20:45 / 12:21:27 −05:00 | Three digest entries add the two unresolved-archive errors. |
| Nov 2, 12:21:17 −05:00 | Both missing-prompt rows reach attempt 3 and become quarantined during the last of those job runs. |
| Nov 2, 12:55:42 −05:00 | Last supplied digest entry still reports the four active protection refusals. |
| Nov 2, about 13:02–13:06 −05:00 | Independent inspection confirms zero attempts on the four persistent rows and reproduces the filename false positives in the installed Rust scanner. |

**Root-cause diagnosis**

The dominant incident is a **confirmed scanner false positive**: an unbounded OpenAI-key regex introduced by `sase-1d5.1` mistakes `sk-` inside long `task-` filenames for credentials. Publication protection correctly follows its input verdict but permanently records the mistaken classification. The no-charge retry policy and background publisher then leave these requests continuously runnable and emit repeated project-level errors. The visible flood is therefore both a classification defect and a publication-state/scheduling defect.

The short-lived additional errors are a **separate prompt-persistence contract mismatch** affecting `bob-cli-fs.2.1.land`: the coder has a recorded follow-up prompt, but its selected directory lacks either raw-prompt filename accepted by deferred archiving. The guard refuses to acknowledge an unproven archive obligation and quarantines the rows after three attempts. Their silence after 12:21 reflects quarantine, not recovery. Fixing only the regex, only the logging, or only the missing-prompt rows will leave part of this incident unresolved.
