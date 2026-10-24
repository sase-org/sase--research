# TUI GC attribution on Athena and Apollo — 23 October 2026

Status updated 24 October 2026, after the r5 capture: **four-hour measurement
complete on both hosts; representative busy-hour evidence still missing**. Phase
`sase-1nf.13` remains open. Neither `sase-1f3` nor the parent epic is closed.
`gc_soak=no` leaves the 24-hour soak to `gc-fix`.

R5 preserves one uninterrupted census-enabled instance per host beyond four hours
after warmup. Athena fails idle-GC latency, GC share, hitch share, late-hitch, RSS
growth and swap targets even in this quiet workload. Apollo meets those numeric
limits in its observed quiet workload, but cannot establish busy-hour acceptance.
Only one actual j/k action on Athena and none on Apollo occur inside the selected
four-hour windows. The remaining prerequisite is representative interaction, not
another four-hour timeout or another TUI restart.

The evidence supports reducing Agent graph replacement and rendering churn before
changing collector thresholds. Both produce objects that survive reference-count
release until cyclic collection. Large archive/event/completion populations also
increase the live heap traversed by collections. These are ranked investigation
priorities with measured allocation mechanisms, not measured shares of live allocation
traffic. Swap contributes to some severe pauses, but does not explain the numerous
multi-second pauses with zero major faults.

## R5: verified four-hour capture

The user confirmed a stable window around 22:10 UTC on 23 October. The monitor ran
22:22:53–02:17:19 UTC and exited 0 after retaining enough samples from before its
launch to complete both windows. Its 3h54m runtime is not the measurement duration.
The raw archive was published and audited before analysis as
`file:explicit:0a6685051ab0553815b6d538`. It includes earlier segments for provenance;
the r5 results below use only the named instances. Its embedded analysis predates
this verification. The corrected analyzer, independent assertion script, results,
coverage record, live perf-path probe and retained CLI outputs are in
`file:explicit:48ab8282349c800464ca383e`.

| Host / instance | Python | Post-warmup heartbeat endpoints, UTC | Actual span | Census rows |
| --- | --- | --- | ---: | ---: |
| Athena `6666b3ec` | 3.14.7 | Oct 23 22:14:50.621027–Oct 24 02:15:42.929670 | 14,452.309 s | 22 |
| Apollo `ec51eded` | 3.12.3 | Oct 23 22:14:25.246047–Oct 24 02:14:30.828560 | 14,405.583 s | 15 |

Both have 49 heartbeats and 48 paired intervals, no missing interval, one boot,
one witnessed TUI and source `2d1e7fd48646c6240f99ba6ac44f5c6e0f75f3c0` throughout.
Each has 124 process/flag witnesses from 21:56 to 02:17 UTC, with
`SASE_TUI_GC_CENSUS=1` and `SASE_TUI_PERF=1`, stable PID/start ticks, and no malformed
captured rows. Their startups were 21:54:35.150700 and 21:54:10.946364 UTC; all
endpoints are beyond each instance's own 20-minute warmup. Maximum adjacent
heartbeat discrepancy against `window_s` is 0.155 seconds on Athena and 0.00077
seconds on Apollo, under the two-second guard. Setup gaps between probes did not
remove heartbeat intervals from the retained files.

The measured Python GC/graph/fleet/link/event/completion sources match the earlier
producer experiment source `92d27136`; the reviewed intervening Python differences
are custom-gate UI work and a new stranded-work facade. Native dependency/pin changes
mean this is still not proof of identical loaded Rust binaries or a controlled
Python-version comparison. No completed producer experiment was repeated for r5.

| Metric | Target | Athena | Apollo |
| --- | --- | ---: | ---: |
| Sorted idle full-collection p95 | ≤0.500 s | **2.761 s**, n=120 | 0.184 s, n=83 |
| Idle p95 excluding census collectors | Diagnostic | **2.953 s**, n=102 | 0.185 s, n=68 |
| GC / paired-interval wall time | <3% | **5.709%**, 825.017 s | 0.664%, 95.688 s |
| Loop hitches / paired-interval wall time | <0.5% | **3.583%**, 517.787 s | 0%, 0 s |
| Automatic/backstop gen-2 within 2 s of input, including census | Zero | 0 observed | 0 observed |
| Late recoveries outside idle or census | Zero | **5** | 0 observed |
| RSS first → last | <0.5 GB growth over 4 h | 3,413,446,656 → 4,107,915,264 B; **+694,468,608 B** | 968,261,632 → 1,146,871,808 B; +178,610,176 B |
| Maximum VmSwap at heartbeats / process probes | About zero | **620,150,784 / 621,490,176 B** | 0 / 0 B |
| Agents j/k latency | p95 <16 ms | One sample, 10.24 ms; **insufficient** | No samples; **unknown** |
| Other tabs / prompt-active comparison | Per-tab latency / state comparison | Unmeasured | Unmeasured |

Full-collection emitted/heartbeat counts agree exactly: 151/151 Athena and 120/120
Apollo, with no suppressed pause rows. Athena has another 5.255 seconds of explicitly
suppressed hitch time, reported separately. The RSS target is decimal GB in
`sase-1f3`; the frozen CLI labels its threshold GiB. Athena misses either interpretation.
Apollo has no configured swap, so its zero VmSwap is not evidence of equivalent memory
pressure. Sampled RSS ranges are 2.178–4.714 GB on Athena and 0.930–1.288 GB on Apollo;
endpoint growth alone does not describe every peak or prove a leak.

### Workload and correction of the earlier j/k classification

`tui_jk.jsonl` is shared by ordinary next/previous navigation, leader commands,
panel switches and prompt actions. The previous analyzer treated every row as j/k.
The corrected analyzer restricts j/k to `next`/`prev` (or artifact-pane-prefixed
equivalents) and reports the other actions separately. The r4 numbers later in this
report are corrected too: Athena's earlier 618.43 ms / n=69 was an all-action p95;
actual Agents j/k is 215.26 ms / n=52. The miss remains, with a different magnitude.

Inside r5's Athena window, four `,j` actions occur at 22:35:18–22:35:53 UTC, with
paint latencies 478–1,390 ms; one `prev` occurs at 22:36:49 UTC, taking 10.24 ms.
Those five samples are not five j/k samples. The one navigation observation cannot
establish a p95 distribution. The most active hour is 22:14:50–23:15:05 UTC: one
j/k, five instrumented actions, five sampled recent-input instants, GC 7.762%,
hitches 4.520%, and ordinary idle-GC p95 3.089 seconds. The remaining three hourly
slices have zero instrumented keys. Even including warmup, this instance has only
13 perf samples, four of which are `next`/`prev`.

Apollo has no perf rows since this instance started, including warmup. Its file
remained 8,288 bytes throughout the 124 probes. The analyzer's nominal busiest hour,
00:04:27–01:04:29 UTC, contains zero instrumented keys and only one sampled
recent-input instant. Calling it a busy hour would misrepresent the evidence.

Both live processes still have both flags; neither overrides `SASE_TUI_PERF_PATH`
or `SASE_HOME`. The collector reads the active and rotated perf files, the retained
rows have no parse errors, and Athena's five new rows appear in the expected file.
There is no observed capture-path failure explaining the gap. Perf logging can
discard an overlapping in-flight sample, so counts are completed measured actions,
not a census of every physical keystroke. This limitation does not establish the
missing workload. Prompt state/duration telemetry remains unavailable.

### Census and paging during r5

The first/last retained post-warmup census populations are 328,356/76,933 garbage
and 1,540,052/2,460,281 survivors on Athena; 20,661/22,795 garbage and
106,579/191,902 survivors on Apollo. These are snapshots, not allocation rates.
Athena's last garbage leaders remain lists (32,823), dictionaries (20,887),
FIFOCaches (10,640), Segments (7,588), Agents (1,656) and Strips (1,520).
Apollo's include Segments (11,354), lists (4,811), FIFOCaches (4,578),
Strips (654) and Agents (198). Both show the seven-cache-per-Strip signature.

Athena's last survivors include 810,729 lists, 585,913 dictionaries, 245,385 paths,
114,860 FIFOCaches, 76,424 DirEntryInfo objects, 45,344 ToolCallEntry objects,
37,755 ArtifactFiles, 29,760 BeadNotes, 22,314 MemoryReadEvents, 20,487
ArtifactReadEvents and 16,405 Strips. The tool-call and bead-model populations are
additional ownership-audit candidates, without measured per-refresh allocation or
proof of leakage. The completed graph/render/event/completion experiments below
remain mechanism evidence; they do not allocate a percentage of live heap to callers.
Apollo's smaller final heap has 57,412 lists, 36,266 FIFOCaches and 5,174 Strips.
Frozen objects remain outside the survivor census: endpoint frozen counts are
603,298/599,749 on Athena and 539,375/535,832 on Apollo.

The 22/15 census spans total 105.108/6.563 seconds. Emitted collectors overlap
70.338/3.966 seconds, leaving noncollector upper bounds 34.770/2.597 seconds.
Maximum individual census cost is 7.699/0.566 seconds. These spans must not be
added to GC totals, and their entire duration is not removable instrumentation cost.

Athena's heartbeat swap begins at 122,843,136 B, reaches 620,150,784 B at
00:05:14 UTC and ends at 325,165,056 B. The two-minute process probes find a slightly
higher peak, 621,490,176 B at 00:01:56 UTC. Hourly heartbeat maxima are
156,401,664, 620,150,784, 388,968,448 and 331,034,624 B; the history is preserved
in `verified-r5.json`. Apollo's heartbeat and probe swap samples remain zero.

Athena has 102 ordinary full collections with zero process major faults
(p95 2.747 seconds, maximum 3.344 seconds), and 14 with positive faults
(maximum 3.134 seconds). The 3.344-second idle collection at 22:26:16 UTC has
zero faults; the 3.134-second collection at 00:01:02 UTC has 1,477 faults.
All 90 ordinary Apollo full collections are fault-free (maximum 0.211 seconds).
This again supports substantial pauses independent of recorded faults. Major faults
and swap occupancy cannot identify the number of seconds spent swapping in.

Five Athena late recoveries have neither idle-trigger overlap nor census overlap:

| UTC recovery | Duration | GC overlap | Trigger / generation |
| --- | ---: | ---: | --- |
| Oct 23 23:31:54 | 2.645 s | 1.960 s | automatic + RSS backstop; 0/1/2 |
| Oct 24 00:00:18 | 2.694 s | 0.253 s | automatic; 0/1 |
| Oct 24 00:07:33 | 4.255 s | 0.629 s | automatic; 0/1 |
| Oct 24 02:00:58 | 2.338 s | 1.767 s | automatic + RSS backstop; 0/2 |
| Oct 24 02:12:20 | 2.324 s | 1.224 s | automatic + RSS backstop; 0/1/2 |

Another 29 have mixed idle/automatic overlap and are not automatically exempt.
Some recovered stacks show graph projection or notification roster work; others show
the selector after recovery. They do not attribute all pause time to those frames.

### Frozen CLI results and limits

`retained_host_acceptance.txt` was produced by executing the frozen CLI on each
host with the full retained stall/startup input supplied in memory; Apollo remained
read-only. Athena exits 1; Apollo exits 0. Apollo's overall PASS does not establish
busy-hour or j/k acceptance. The wrapper supplies no perf input, so the CLI's
"no SASE_TUI_PERF log" message is not evidence that the live flag was absent.

The known unsorted percentile bug prints Athena idle p95 1.739 seconds instead of
2.761 seconds. Including the first heartbeat's preceding-interval totals also makes
its CLI GC/hitch shares 5.93%/3.68%, versus corrected 5.709%/3.583%. Apollo's
microsecond-rounded ISO upper bound excludes the final raw-float heartbeat: the
CLI retains 48, ending at 02:09:30 UTC, despite printing a requested four-hour
envelope. Its displayed RSS growth is consequently 252.7 MiB rather than the
endpoint-correct 170.3 MiB. The independent verifier reproduces this boundary issue;
the 49 original samples and all 48 interval totals govern the results above.

## Earlier evidence and reproducibility

- R4 capture, published and audited before analysis:
  `file:explicit:5c16d510615f85b8ec75fe72`. Contains exact retained JSONL,
  process/flag/boot/clock witnesses, source revisions, transitions, coverage guards,
  producer experiments, and the frozen report CLI. Its embedded `analysis.json`
  predates capture completion; rerun `analyze_capture.py` to obtain final r4 results.
- Original completed producer experiments:
  `file:explicit:d350cd2049aee5ae9163a022`. Use `allocation-*.jsonl`;
  `workspace-venv-allocation-*` are earlier dependency rehearsals.
- Pre-census comparison and baseline checkpoint:
  `file:explicit:1bd8d133f72d4743a06a28c0`.
- Scope and targets: `plan:202610/athena_apollo_audit_fixes.md`,
  `bead:sase-1f3`, `bead:sase-1ez`. The current user instruction limits phase
  closure to `sase-1nf.13`, superseding the plan's instruction to close `sase-1f3`.

The follow-up analysis bundle attached to this phase contains regenerated r4
`analysis.json`, `supplemental.json`, the completion-catalog experiment, retained CLI
outputs from both hosts, the report, and the r5 setup/probe. Artifact refs on this
phase are the durable discovery path.

Capture is read-only: it copies active and rotated startup/stall/j-k logs every two
minutes and records process flags, PID/start ticks, boot identity, wall/monotonic
clock pairs, process RSS/swap/fault counters, and host memory/paging counters. It never
attaches to or changes either live TUI. Exec restarts reuse PIDs; instance IDs, not
PIDs, define windows. Each instance gets its own 20-minute warmup.

The analyzer uses sorted linearly interpolated percentiles. GC and hitch shares use
paired heartbeat endpoints, excluding the first endpoint's counters because they
belong to the preceding interval. RSS coverage uses actual first-to-last samples.
Adjacent heartbeat timestamps must agree with the next heartbeat's `window_s` within
two seconds. Counts are cross-checked against emitted full-collection rows. This is
stricter than interpreting a requested CLI envelope as four hours of evidence.

J/k rows have no instance ID. Attribution uses one witnessed TUI per host, one boot,
nearest wall/monotonic clock pair, and window bounds strictly inside an instance.
Across the full retained r5 metadata, clock-offset spreads are 2.86 microseconds
on Athena and 12.87 microseconds on Apollo.
This supports time attribution, not independent process identity for each key row.
All retained post-warmup j/k samples used below are on the Agents tab; other tabs
remain unmeasured.

The frozen `tools/tui_freeze_report --acceptance` was executed against retained input
on Athena and read-only over SSH on Apollo, with input supplied in memory and no
remote files written. Both r4 selected segments and their hour slices exit 1. The raw
CLI is corroboration only: phase notes 4–5 document its unsorted idle-p95 bug and
missing coverage/late-hitch verdicts. The corrected calculations below take precedence.

## R4 coverage and provenance (historical)

R4 monitored 15:36–21:30 UTC, retaining earlier r2/r3 rows too. It ended at its bounded
deadline with no qualifying four-hour segment. During r4 each host changed instance
four times. Observed transition times (UTC) were Athena 15:58, 16:16, 18:07, 19:42;
Apollo 16:00, 16:16, 18:15, 19:50. These are observation times, not exact launches.

| Host / instance | Revision | Post-warmup RSS endpoints, UTC | Span | Coverage issue |
| --- | --- | --- | ---: | --- |
| Athena `4b163b84` | `35e593bc` | 16:36:40–18:01:55 | 85.25 min | Too short; no heartbeat gaps |
| Apollo `2f68ee2a` | `35e593bc` | 16:35:29–18:10:34 | 95.08 min | Too short; no heartbeat gaps |
| Athena `50f150ff` | `bdec291c` | 18:26:25–19:36:38 | 70.21 min | Too short; one interval discrepancy >2 s |
| Apollo `3f11ca83` | `bdec291c` | 18:34:16–19:44:18 | 70.02 min | Too short; no heartbeat gaps |
| Athena `f6719135` | `bdec291c` | 20:01:18–21:26:37 | 85.32 min | Too short; no heartbeat gaps |
| Apollo `208693b9` | `bdec291c` | 20:09:31–21:29:37 | 80.09 min | Too short; no heartbeat gaps |

Earlier retained segments are shorter still. None may be pooled across restarts to
claim four hours. The Athena `50f150ff` discrepancy is about 2.3 seconds, not proof
that an entire five-minute heartbeat disappeared; it nonetheless fails the capture's
strict continuity guard and is not used for the primary comparison.

The historical r4 comparison below uses the same `35e593bcc01553b14b4b5109cbc7992162c1caa6`
revision on both hosts. The measured Python GC, graph, fleet, links and completion
sources match the experiment workspace `92d271364cb5`. The intervening changes
include launch/monitor work and a Rust CI pin change from `1503d604` to `246e2874`.
Later `bdec291c77b0de1aab4c00abecef7430761db736` also changes custom-gate sizing and
the declared Rust package dependency from 0.42.0 to 0.42.2. This is not proof of
identical loaded native binaries; no comparison here isolates a native-version effect.

A read-only probe at 21:56 UTC found another restart on both hosts: Athena
`6666b3ec` launched 21:54:35 UTC; Apollo `ec51eded` launched 21:54:10 UTC, both
source `2d1e7fd48646c6240f99ba6ac44f5c6e0f75f3c0` with both flags preserved.
Their warmup ends about 22:14 UTC. These instances are measured separately in the
r5 section above; they are never pooled with the r4 tables.

## Historical before/after and r4 acceptance targets

The original `sase-1ez` baseline recorded 10.7–12.9% frozen time (12.31% reproduced),
25.5% all-GC time, 16.7% gen-2 time, gen-2 p50 2.16 seconds, and RSS rising from
1.48 to 4.66 GB plus 1.46 GB swap in 50 minutes. The current shares are lower than
that old workload, but these are unmatched observations with census overhead; they
are not a causal before/after speedup estimate.

For the `35e593bc` segments above:

| Metric | Target | Athena, Python 3.14.7 | Apollo, Python 3.12.3 |
| --- | --- | ---: | ---: |
| Sorted idle full-collection p95 | ≤0.500 s | **3.536 s**, n=45 | **0.578 s**, n=28 |
| Idle p95 excluding census collectors | Diagnostic separation | **3.558 s**, n=41 | **0.581 s**, n=22 |
| All GC / wall time | <3% | **8.131%** | 0.802% in observed workload |
| Loop hitches / wall time | <0.5% | **4.302%** | 0% in observed workload |
| Automatic/backstop gen-2 starting within 2 s of input | Zero | 0 observed, including census | 0 observed, including census |
| Late recoveries outside idle or census | Zero | **3**; target missed | 0 observed |
| RSS endpoint change | <0.5 GB over 4 h | +153,378,816 B / 85 min: **insufficient duration** | −272,084,992 B / 95 min: **insufficient duration** |
| Maximum sampled VmSwap | About zero | **1,725,120,512 B** | 0 B |
| Agents j/k p95 | <16 ms | **215.26 ms**, n=52 | **281.84 ms**, n=12 |
| Other tabs' j/k p95 | <16 ms per tab | Unknown | Unknown |

Full-collection emitted/heartbeat counts match 55/55 on Athena and 39/39 on Apollo;
no suppressed pause rows were reported. These are measured misses on the available
segments, not full-contract acceptance. In particular, a negative short-window RSS
delta cannot pass the four-hour requirement.

Pre-census matching-source four-hour windows on 21 October had sorted idle p95
1.823/0.687 seconds, GC share about 1.31/1.13%, and sampled swap zero on Athena/Apollo.
Their source was `54779b62`, their workload mostly idle, and they lacked census and
attributable j/k. Their CLI percentages were not fully endpoint-aligned. They supply
historical context; the census-enabled four-hour requirement is now met by r5.

### Activity and the busy-hour requirement

After filtering action types, the most navigation-heavy Athena hour in the r4
primary segment is 16:36:40–17:36:49 UTC: 32 actual j/k samples, 40 total instrumented
actions, 41 distinct sampled recent-input instants, 5.953% GC, 3.213% hitches,
ordinary idle p95 2.959 seconds, and Agents j/k p95 149.13 ms. Ten-minute j/k bins are
18, 3, 0, 0, 11, 0. This is an observed active hour with bursts of normal interaction,
not evidence of uniformly sustained load. It is a different instance/revision from
the r5 four-hour measurement and cannot supply a matching busy hour for it.

The same-revision Apollo candidate is 16:35:29–17:35:32 UTC: 12 j/k samples, five
sampled input instants, 1.021% GC, zero hitches, ordinary idle p95 0.586 seconds, and
j/k p95 281.84 ms. Ten-minute j/k bins are 0, 0, 10, 0, 1, 1. Across all retained r4 segments, the largest hour contains only 12 actual j/k
samples; the later count of 14 in the earlier report included other actions. Apollo lacks evidence of a representative busy hour
comparable to Athena. Do not describe a quiet low-GC hour as a successful busy-hour run.

Prompt-active state and duration are absent from these logs. `text_area_changed`
actions demonstrate some editing, but do not identify continuous prompt-active periods.
Input age cannot substitute for that state. A prompt-active versus idle comparison is
therefore unavailable, rather than favorable or unfavorable.

## Garbage, survivors and instrumentation cost

Athena's 17:54:56 UTC census on `4b163b84` finds 669,751 garbage objects and 2,915,138
tracked survivors. Garbage leaders are 194,571 lists, 169,613 Rich Segments,
150,343 dictionaries, 83,092 FIFOCaches, 37,734 Rich Styles, 11,870 Strips, and
9,278 Agents. The cache/Strip ratio is approximately seven; the earlier census in
the producer bundle has an exact seven-to-one ratio.

Survivors include 820,454 dictionaries, 761,684 lists, 264,399 PosixPaths, 256,004
tuples, 127,496 FIFOCaches, 74,629 ArtifactFiles, 63,961 completion metadata objects,
53,345 DirEntryInfo objects, 31,443 document candidates, 26,518 file candidates,
22,296 MemoryReadEvents, 20,295 ArtifactReadEvents, 18,194 Strips, 16,997 BeadTouches,
and 11,663 SkillUseEvents. The completion populations merit explicit inclusion with
archive/event snapshots; they were less prominent in the earlier producer checkpoint.
Counts measure objects, not bytes or leaks. A top-40 histogram is not a complete heap.

Apollo's final corresponding census finds 15,573 garbage and 518,164 tracked
survivors. Garbage includes 7,294 lists, 3,256 Segments, 2,520 FIFOCaches, 366 Agents,
and 360 Strips. Survivors include 115,880 lists, 92,028 FIFOCaches, 40,242 Segments,
22,658 ArtifactFiles, 13,975 BeadTouches and 13,144 Strips. These materially different
populations preclude assigning the host difference solely to Python version.

Across the primary segments, six census spans total 29.449 seconds on Athena and
7.734 seconds on Apollo. Emitted collectors overlap at least 19.528 and 4.940 seconds
of those spans. The remaining 9.921/2.794 seconds bound noncollector census work from
above; unlogged short collections can also be present. The maximum individual Athena
census costs 9.597 seconds. Census duration includes both full collections and type
enumeration. Its cleanup collection is tagged automatic outside the idle trigger.
Do not add census duration to GC totals or interpret the whole span as removable
overhead: the initial idle collection would happen without census too.

`gc.get_objects()` excludes frozen objects. Athena's frozen counts at the primary
segment endpoints are 620,349/561,314; Apollo's are 439,478/436,614. The survivor
histograms are neither whole-process memory nor directly comparable tracked-object
units across Python versions.

## Measured producers, ranked for investigation

The offline harness prepares input fixtures and imports before tracing, warms each
operation, disables automatic GC in its own process, and records three trials of
Python traced live/peak bytes plus an isolated DEBUG_SAVEALL type census. It never
changes the live TUIs. Numbers are median decimal bytes per operation. They exclude
native allocations, many input strings, and real refresh frequency; they are not total
allocation traffic, deep object size, RSS, or a measured fraction of live pauses.

| Operation | Fixture | Held B | Peak B | B after dropping result | Objects reclaimed by GC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Build Agent graph with back-references | 100 rows | 825,184 | 825,544 | 824,352 | 2,100 |
| Copy Agent graph with back-references | 100 rows | 801,304 | 836,808 | 800,504 | 2,100 |
| Copy graph without back-references | 100 rows | 801,176 | 836,680 | 10,616 | 0 |
| Copy graph and project clan tree | 100 rows | 927,126 | 950,918 | 847,446 | 2,201 |
| Fleet projection | 100 shell rows | 1,487,913 | 4,922,052 | 43,476 | 0 |
| Reload changed link aggregate | 10,000 links | 4,014,298 | 5,995,758 | 4,014,298, cache-owned | 0 |
| Unchanged link cache hit | 10,000 links | 760 | 1,577 | 760 | 0 |
| Plain Strip construction | 1,000 strips | 1,185,384 | 1,185,384 | 10,072 | 0 |
| Strip full-width divide | 1,000 strips | 1,465,376 | 1,465,616 | 1,456,576 | 18,000 |
| Strip full-width crop_extend | 1,000 strips | 1,417,312 | 1,417,528 | 1,408,512 | 17,000 |
| Memory-read parse/model conversion | 10,000 events | 8,594,486 | 13,321,760 | 120,656 | 0 |
| Skill-use parse/model conversion | 10,000 events | 6,124,618 | 10,851,490 | 6,100 | 0 |
| Artifact-file parse/model conversion | 10,000 files | 4,473,998 | 6,391,057 | 15,480 | 0 |
| Bead-touch parse/model conversion | 10,000 touches | 7,439,953 | 13,881,300 | 19,860 | 0 |
| Completion document candidates | 10,000 rows | 720,312 | 805,432 | 328 | 0 |
| Completion file candidates | 10,000 rows | 720,312 | 805,432 | 328 | 0 |
| Completion catalog metadata/index construction | 10,000 documents + 10,000 files | 3,271,078 | 9,686,478 | 134,648 | 0 |

The completion experiment extends the completed producer work for a population newly
prominent in r4. It calls the real catalog constructor with prebuilt candidate inputs;
these inputs and strings are excluded from its catalog row. All final Athena trials
use Python 3.14.7, Textual 8.2.8 and Rich 15.0.0; the completion run records installed
`sase-core-rs` 0.42.1. It measures only Python allocations around native indexing.
Tracemalloc affects timings, so elapsed values in the JSONL are not live pause estimates.

1. **Agent graph churn and back-references.** The real `copy_agent_graph` retains
   about 800 KB per synthetic 100-row graph until GC, versus immediate release for
   the acyclic control. The cyclic result has 100 Agents, 1,700 lists and 300
   dictionaries; 25-row copies produce 525 cyclic objects. Thousands of live census
   garbage Agents corroborate the candidate. Reduce redundant replacement/copies and
   inspect graph projection cadence while preserving worker ownership and aliases.
   The experiment does not identify which live caller accounts for each graph.
2. **Rendering churn and Strip self-caches.** Full-width `divide` caches a list
   containing `self`; full-width `crop_extend` can cache `self`. All seven FIFOCaches
   remain reachable through the cycle. The same mechanism reproduces on Apollo
   Python 3.12.3 with identical Textual/Rich versions: about 1.44 MB retained for
   divide and 1.39 MB for crop_extend per 1,000 strips. Tracked garbage counts differ
   (13,000/12,000), so do not use their ratio as an interpreter efficiency score.
   Reduce unnecessary renders/rebuilds; the experiment does not prove every live
   Strip cycle came from these exact operations.
3. **Archive, event and completion snapshots.** These are large survivor populations.
   Their isolated converters/catalog constructors are acyclic and mostly release on
   ownership release. Audit scope, replacement cadence and redundant ownership;
   the census does not prove unbounded growth. The completion metadata/index build
   adds about 3.27 MB held and 9.69 MB peak for 20,000 prepared candidates, excluding
   native allocations and the input candidates themselves.
4. **Fleet projection.** A real 100-shell-row projection holds 1.49 MB and peaks at
   4.92 MB, but is acyclic alone. This fixture excludes session relationships and
   downstream apply. Existing signature/repaint skipping means every apply must not
   be assumed to rebuild the projection.
5. **Artifact-link snapshots.** A changed 10,000-row aggregate costs about 4 MB held,
   but unchanged reads share the cache. LinkIndex already uses native shared handles
   and lazy bounded chip caching. Proposing another full Python-index migration would
   be based on an obsolete premise; native index memory is not measured here.

## Paging and late hitches

Within Athena `4b163b84`, 35 ordinary full collections have zero process major faults
(p95 3.507 seconds, maximum 3.870 seconds); 12 have positive faults (median
2.674 seconds, maximum 6.615 seconds). The 6.615-second backstop starts
17:22:05.984 UTC with 41,035 major faults while the segment reaches 1.725 GB sampled
swap. Paging plausibly contributes to that episode. The 3.870-second idle pause at
17:53:39.802 has zero faults, as do many others. All 27 ordinary full collections in
the primary Apollo segment have zero major faults, with maximum 0.677 seconds.

Major faults can include file-backed reads; process VmSwap measures occupancy, not
swap-in time. Host paging counters aggregate other processes and two-minute samples
cannot resolve one pause. The data cannot assign a numeric fraction of a pause to
swap-in. It supports correlated paging pressure in one severe episode and substantial
collector/heap costs independent of recorded faults.

Three Athena late recoveries occur outside census and have no idle-trigger overlap:

| UTC recovery | Duration | GC overlap | Triggers / generations |
| --- | ---: | ---: | --- |
| 16:38:24.437 | 2.168 s | 0.629 s | automatic, gen 0/1; sampled stack in Textual rendering |
| 16:56:49.740 | 2.550 s | 1.856 s | automatic + RSS backstop, gen 0/2 |
| 17:25:57.718 | 4.142 s | 3.242 s | automatic, gen 0/1; last-key age 0.525 s |

The other 12 late recoveries have mixed idle/automatic overlap. Overlap alone cannot
prove exclusive idle-collection causation, so they are not silently exempted. The
three clear non-idle cases already establish a miss. Younger-generation collector
cost and rendering work deserve attention alongside full collections. Recovery-time
stacks can show the selector after a stall; they do not locate all time spent during it.

## Remaining acceptance work

The four-hour prerequisite is complete and preserved. Do not discard r5, repeat the
producer experiments, or start another long timeout merely because busy-hour evidence
is absent. First establish whether the user actually used these specific TUIs during
the proposed busy hour. If they did, investigate the missing telemetry before another
capture. If they did not, the next useful capture is a bounded hour of normal active
use on both existing instances, including j/k on the usual tabs, with early checks
that the expected rows are arriving. Keep it separate from the completed four-hour
window. If either instance has since restarted, do not combine it with r5 or silently
relax the same-instance requirement.

Actual target misses are findings for `gc-fix`; they are not a reason to delay closing
a completed measurement phase. Here the representative workload requirement itself
remains unproven, so `sase-1nf.13` stays open. `sase bead epic-symbols sase-1nf.13`
reported no entries during r5 verification. No product source or memory edits and no
new beads were made. Proposed follow-ups are recorded only on the assigned phase.
Only that phase may close after the remaining measurement scope is satisfied;
`sase-1f3` and ancestors stay open, and the 24-hour soak stays with `gc-fix`.
