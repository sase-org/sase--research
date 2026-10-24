# Publication Recovery Acceptance

2026-10-22

This report closes the acceptance evidence for the publication-blocker recovery work under sase-1nf.10.1.9.1. Statuses distinguish observed proof from checks that remain missing.

## Five acceptance checks

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | A named formerly failing stopped request publishes within 120 seconds. | **MISSING** | The bounded canaries did not publish a named stopped request for the selected classes. The canary budget is spent; no bulk drain or retry-all was run. The canary summary records active rows remaining and the unresolved blockers. |
| 2 | Remote manifests and referenced files agree. | **PASS for Apollo bob-cli replay** | At fetched remote revision 650c73595a6b452aa168f567538f120d8cd4d319, validation found 3 manifests, 804 snapshots, 23 target runs, and no diagnostics. The requested replay paths and content hashes matched, including the two unique runs, chat additions, terminal state and prompt-step updates, three archive objects, and byte-identical monitor chats. 6,426 upstream-only paths remained present. |
| 3 | Repeat recovery is a no-op. | **PASS** | The production helper’s second apply returned already_complete with ahead=0 and behind=0; it published nothing new. The focused real-Git recovery fixtures also pass. |
| 4 | An interrupted real-Git publication resumes without content loss. | **PASS** | test_interrupted_apply_resumes_and_second_apply_is_already_complete passed. The production replay completed from a durable verified backup, and the fetched bob-cli tree retained all 6,426 upstream-only paths. |
| 5 | A newly completed agent publishes automatically after installation. | **PARTIAL — revision field missing** | Agent bbugyi200.athena.sase-1nf.10.1.9.1.6.3--1 (source run run-c64afb11da57b0e9200ab328ab0281ab) completed at 2026-10-22 11:13:41.596 UTC, after both hosts were verified at SASE ba7ab4e96bce13fdf71b9e429bffe92a8cf39205 and core 1503d604844a32a8a93e944addabb0887f8d9bc4. The automatic publication drain recorded at 11:20:20 UTC had no alarm; its inventory, hood publication, manifest verification, push, and cleanup stages were 25.1525 s, 6.9195 s, 0.0436 s, 2.0636 s, and 1.457 s. Fetched agents-sidecar revision 9413fd2ea8d028493cf23243dee97653ca2d22bc contains the run README, prompt, chat, and session page. The acknowledged request no longer exposes its request-bound primary_revision field, so that exact part of the correlation is missing and is not claimed as passed. |

## Revisions, recovery backup, and measurements

The install-replay evidence records both hosts loading the SASE and core revisions above. The workspace core binding matches the pinned revision 1503d604844a32a8a93e944addabb0887f8d9bc4; the acceptance fixtures rebuilt against the linked core and passed.

Apollo’s durable replay backup is:

    /home/bryan/.sase/recovery-backups/bob-cli-replay-sase-1nf.10.1.9.1.6.3

SHA-256 checksums recorded after verification:

- checksums.json: fe2f9f258f67aa91f71cc8cdff4f71dff71b92bd0b45197d8114cba89ddab11b
- unpublished.bundle: 7eb37f053a781026785cfcd8cc23860e13747dc7892cb2c1d1bde6fc578a263c

The report-only stage was verified before apply. The helper applied with the same expected HEAD and backup, then its second apply was a no-op. At the fetched bob-cli revision, the validated remote tree included the unique runs bbugyi200.apollo.bob-cli-7c.2--2 and bbugyi200.apollo.bob-cli-7c.2--mon-0; the remote-proof artifact records the full path/content/hash comparison.

Scoped/full inventory comparison:

| Measurement | Result |
|---|---:|
| Full baseline, 2026-10-20 | 209.84 s; 9,903 Git calls |
| Targeted research profile, 2026-10-21 | 129.956 s |
| Landing-audit cProfile | about 268.5 s; inventory in production drain rows was 106–148 s |
| Post-fix one-hood profile | inventory 23.19 s; planning 7.16 s; 25 Git calls; 0 digest mismatches |
| Post-fix two-hood profile | inventory 22.64 s; planning 5.93 s; 26 Git calls; 0 digest mismatches |

The production drain row also logged an unrelated cleanup error for the page of bbugyi200.athena.sase-1nf.10.1.9.1.6.2; it did not alarm and does not change the publication evidence above.

## Remaining backlog and bounded follow-up

Lock-free snapshots refreshed at 2026-10-22 11:59:42–43 UTC:

| Host / project | Requests | Active | Quarantined | Retired | Stalled |
|---|---:|---:|---:|---:|---:|
| Athena / sase | 3,403 | 4 | 3,397 | 2 | 3 |
| Apollo / bob-cli | 434 | 46 | 388 | 0 | 8 |
| Apollo / sase | 398 | 2 | 112 | 284 | 0 |

These counts do not authorize a bulk drain. The bounded commands for sase-1nf.11 are:

Athena, project sase:

    sase agent sync --project sase --retry-quarantined --retry-limit 25 --retry-error-class timeout --json

Apollo, project bob-cli:

    sase agent sync --project bob-cli --retry-quarantined --retry-limit 25 --retry-error-class rebase_conflict --json

Apollo, project sase:

    sase agent sync --project sase --retry-quarantined --retry-retired --retry-limit 25 --retry-error-class manifest_mismatch --json

Run those only after Apollo write access is restored and active-first healthy selection is confirmed. The canary evidence already records the access failure, the stale-revision dud rows, and the need to retry Apollo’s SASE manifest-mismatch class once writes work.

## Known issues carried forward

These remain open and are not counted as passing acceptance:

- Apollo job and tailnet projects still fail fetch with “Repository not found”.
- Tagged-commit “prompt archive is unresolved” failures remain, including production occurrences in Athena drain rows.

## Evidence index

- Original blocker diagnosis: file:explicit:684de02c487788fab67ad837, file:explicit:b2ebf67eabeaef7b5e0a1265, file:explicit:07eac2cef30caada4c976c16, file:explicit:1e757f4f4eadfca380da107c, file:explicit:f3576bf6104be8530cc534e2.
- Earlier landing canary evidence and queue snapshots: file:explicit:c891f25f8c6e92bc1d7fa099, file:explicit:78bab28f1683b5a88c97264e, file:explicit:696eb3078287cfc1f2969ec5, file:explicit:0e081201ada8de38f248aba6.
- Install and replay evidence from phase sase-1nf.10.1.9.1.6.3: file:explicit:0a2f73e51e5d9337c3710d44, file:explicit:f1176d53bef9cf9cc67f3d1d, file:explicit:6bb0a3bad7880c345c167024, file:explicit:4b8203965ca7b80abdbb6cd4, file:explicit:2b39984b614454d0fad35467, file:explicit:9f2c23a8b3d9bd53371c40ad, file:explicit:f3ae6ce054168755bc7f3a4a, file:explicit:6f0d4aa7c4fb0eb6a8ca3113.
- Bounded canary summary and companion artifacts from phase sase-1nf.10.1.9.1.6.4: file:explicit:4c82a2fd9e41c219eeac5d92.
- Post-fix profile notes: phase sase-1nf.10.1.9.1.6.1 (one-hood and two-hood profile attachments).
- Focused fixture test output: file:explicit:2c04408af2441e0bc4710cae (1,060 passed; 9 replay-recovery cases passed).
- Automatic completion record: agent:bbugyi200.athena.sase-1nf.10.1.9.1.6.3--1; fetched run/page/prompt tree at agents revision 9413fd2ea8d028493cf23243dee97653ca2d22bc.
- Original stale-replay inventory and prior recovery context: file:explicit:05af6c55b55e24008cbd9f2f, file:explicit:24a51cfff990818ebfeee77, file:explicit:9b5d34d8d0a2451778c37f55, file:explicit:dd0fbaede0466d626da83b7f, file:explicit:ad889331c1dd2457a7a16946.

At the time of this 2026-10-22 report, checks 1 and the request-bound revision field
for check 5 were missing. The 2026-10-24 follow-up below updates check 5; check 1
remains missing.

## 2026-10-24 follow-up — installed repair and bounded publication proof

Both hosts now expose `sase agent sync --repair-revisions`. At capture time they ran
SASE `0.18.0+120.gc594443dc` (commit
`c594443dc78c5acde55e25f25c73e573647e5560`) and sase-core-rs
`0.42.4+3.g7ec12d2d7` (commit
`7ec12d2d7ad8e670abe26aa396259a512f330391`). Apollo's GitHub identity check greeted
`bbugyi200`.

### Updated acceptance checks

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | A named formerly failing stopped request publishes within 120 seconds. | **MISSING** | The authorized one-row attempts ran once per host/project, but none completed a named stopped request. Athena/SASE revived a timeout row and then reported that the published page did not materialize. Apollo/bob-cli selected an active `unknown` row and its rebase failed while applying `a090a3a2c`. Apollo/SASE selected an active `other` row, then reported that the page did not materialize; the fetched row's revision did not match. No batch or further retry was run. |
| 2 | Remote manifests and referenced files agree. | **PASS for the earlier Apollo bob-cli replay** | The previously recorded fetched-revision replay validation remains the check-2 evidence; the fresh bounded retry attempts did not add another successful replay. |
| 3 | Repeat recovery is a no-op. | **PASS** | The existing second-apply `already_complete` evidence and focused real-Git fixtures remain valid. |
| 4 | An interrupted real-Git publication resumes without content loss. | **PASS** | The existing real-Git resume fixture and fetched bob-cli replay evidence remain valid. |
| 5 | A newly completed agent publishes automatically after installation. | **PASS — natural completion** | Agent `bbugyi200.athena.13y` completed at `2026-10-24T21:07:34.626Z` with commit `201d1cf4ef3b1e7c7045ae936ae5c89cc8b2266d`. The automatic drain timing row at `21:10:03Z` includes `hood_publish:13y` (3.1897 s). At fetched agents revision `70d09617414bfe14282ff9506ed5debc9ed01171`, its run `run-19c27c1caa8a1818717f9afbdc3a7872`, page, and prompt are present, with no validation diagnostics. The acknowledged row was already absent from the post-drain outbox snapshot. |

### Repair results

Report counts are ordered as unchanged / linked / repaired / unresolved. Every apply
used an exact source-to-dated-backup SHA-256 preflight. Unresolved rows remained
untouched by repair.

| Host / project | Report classification | Apply and audit |
|---|---|---|
| Athena / sase | 101 / 469 / 996 / 1,891 | Apply itself exited 0; audit records 996 repaired, 469 linked, and 6 merged rows. The wrapper later exited 3 because its jq unresolved-row comparison had a syntax error. An independent comparison of the saved before/after snapshots found all 1,891 unresolved `(agent, revision)` rows unchanged. Backup and pre-apply source SHA-256: `334607e207fe4dc8f30f8b4181fa8e55e5c923cb7a1bdc857049433af55c7d39`; post-apply source: `4665188aa37f965837d58839a16b2a5a7d0f5a394ba1c0fa56464660faf72826`. |
| Apollo / bob-cli | 13 / 113 / 56 / 304 in report mode; apply reported 305 unresolved | Apply exited 0; audit records 56 repaired and 113 linked rows. The apply-time classification saw one additional unresolved row. Exact backup/source preflight SHA-256: `19fbe07ad9d1167a5e43752bf493fe3eb62960e97dbf13099be87feabbce8565`; post-apply source: `e46806cb6998ac0f447b50a57cbafc2b7f7517c841be2a1b15ec0d6339fba80a`. |
| Apollo / sase | 19 / 52 / 26 / 319 | Apply exited 0; audit records 26 repaired and 52 linked rows. Exact backup/source preflight SHA-256: `684b2214e41e72ac71ca20c0404d618bc2521d167d29a9bfe09226258e187db7`; post-apply source: `8ab6a4df737b793517156a3ce2f158d1e1643c2691e1e5cf0a5f3ad2a8750df6`. |

The old failed Athena preflight attempts did not apply changes. The later atomic
transaction made the successful apply against its fresh matching backup. All
unresolved report classes were preserved; no unresolved row was forced or dropped.

### Bounded attempts and remaining outbox

| Host / project | UTC attempt and result | Selected row and remote validation |
|---|---|---|
| Athena / sase | `2026-10-24T21:25:21Z`–`21:26:05Z`, exit 1 | Selected `bbugyi200.athena.research.0o.cdx@95827e05e1df` (timeout). It was revived, but the drain reported `published agent page ... did not materialize`; no fetched-sidecar validation file was captured. The selected row returned active with the same request revision; all other snapshot rows were unchanged. |
| Apollo / bob-cli | `2026-10-24T21:40:53Z`–`21:41:00Z`, exit 1 | Selector chose active `bbugyi200.apollo.bob-cli-ac.land@1257c2e8d90c` (`unknown`), not a rebase-conflict row. Rebase failed applying `a090a3a2c`; all 522 outbox rows were unchanged. Fetched revision `a090a3a2c8a78ef2e967237756595324a2e4cf7a` contains that stranded bob-cli commit. Remote validation had no diagnostics, but this selected row had no matching run, revision, or prompt. |
| Apollo / sase | `2026-10-24T21:52:15Z`–`21:52:57Z`, exit 1 | Selector chose active `bbugyi200.apollo.a4@69c625f8d9af` (`other`), not a manifest-mismatch row. It failed because the page did not materialize; the row's attempts changed 2→3 and it was quarantined. Fetched revision `094cfd0b7f679e2a85ab9bfb533c1c93d5917b74` validated without diagnostics, but its run commit did not match the requested revision. The attempt did not push (`push_attempts=0`, `pushed=false`); the stranded `f2d32a476b` commit was not confirmed at the fetched revision. |

Post-attempt outbox snapshots recorded Athena/sase 3,451 rows (1 active, 3,448
quarantined, 2 terminal), Apollo/bob-cli 522 (134 active, 388 quarantined), and
Apollo/sase 416 (132 quarantined, 284 terminal). No retry batch was run. The next
phase's bounded commands, after it confirms safe selection, remain:

Athena, project sase:

    sase agent sync --project sase --retry-quarantined --retry-limit 25 --retry-error-class timeout --json

Apollo, project bob-cli:

    sase agent sync --project bob-cli --retry-quarantined --retry-limit 25 --retry-error-class rebase_conflict --json

Apollo, project sase:

    sase agent sync --project sase --retry-quarantined --retry-retired --retry-limit 25 --retry-error-class manifest_mismatch --json

Check 1 remains missing, so this follow-up does not close the recovery-proof phase.
The active-first selector chose rows outside the requested historical failure classes
on both Apollo projects, and the Athena timeout retry did not materialize its page.

