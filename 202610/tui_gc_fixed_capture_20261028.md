# Fixed-code TUI capture: early failure on both hosts, 28 October 2026

The fixed code is live, both requested instrumentation flags are enabled, and
the available telemetry already fails performance targets on Athena and Apollo.
This is **FAIL with incomplete acceptance evidence**, not successful four-hour
verification or a completed 24-hour soak. Even independently validated contiguous
fragments fail GC share, idle-GC latency, and loop-hitch share on both hosts.

At gate `question/6faea19e-df8a-410d-a167-94ebfc7c5a5f`, answered at
2026-10-28T22:16:09Z, the user confirmed both hosts ready and asked:
“Try to get this epic closed without any more waiting.” This assessment therefore
uses already available evidence and schedules no additional capture wait or human
gate. That request is not recorded as a waiver of the acceptance thresholds or as
proof of missing duration/workload. Phase `sase-1nf.14.1.7` and its ancestors remain
unclosed: the original measurement contract is not complete. The proposed follow-up
notes preserve the concrete failures for the epic's land agent.

## Evidence and reproduction

- Raw evidence and reproduction bundle: `file:explicit:8ce7eae6df0b33fe4d6aae99`.
- Governing design: `plan:202610/measured_tui_gc_fixes.md`, fixed-capture and
  fixed-soak sections.
- Complete unchanged R5 baseline:
  `research:202610/tui_gc_measurement_20261023.md`. Its original raw and corrected
  analysis refs remain `file:explicit:0a6685051ab0553815b6d538` and
  `file:explicit:48ab8282349c800464ca383e`. An audited copy of the complete baseline
  is retained in the new bundle; no old observations are pooled with this run.

The bundle retains active and rotated startup/stall/perf logs, process witnesses,
host context, the collector, frozen reporter sources, command argv and exit codes,
text/JSON acceptance output, an independent assertion script and its output, and
SHA-256 hashes. The six executions recorded in `commands.json` exited **1**, as expected
for failed or incomplete acceptance. `verify.py` independently reproduces GC/hitch sums, sorted
idle and navigation quantiles, full-GC counts, and provenance checks. No live TUI
input was injected and neither process was restarted or altered.

To reproduce after extracting the bundle, run `python3 verify.py` inside its
directory. Each host's `commands.json` records the exact original CLI invocation.
Use the bundled `reporter/tui_freeze_report` and adjust input paths to the extracted
host directory. `acceptance.json`/`.txt` cover the full available post-warmup
envelope; `contiguous_fragment.json` is a separate shorter cross-check, not a
replacement for four-hour acceptance. The reporter source at workspace revision
`d1a576ab4e` is byte-equivalent to these four files at the live source revision.

## Preflight and provenance

| Witness | Athena | Apollo |
| --- | --- | --- |
| App instance | `8b65de59` | `7e973b00` |
| Startup, UTC | 20:45:20.175219 | 20:45:21.698951 |
| PID / `/proc` start ticks | 4045198 / 114069905 | 1562336 / 166947655 |
| Boot ID | `2e013859-5e29-418c-bf6d-035a5eeff435` | `1e87418e-2b01-47ab-ad0d-eb23a80d5f96` |
| Process/flag witness, UTC | 22:23:42.729343 | 22:23:43.719244 |
| Python | 3.14.7 | 3.12.3 |
| Startup agent rows / index rows | 42 / 544 | 17 / 197 |
| Startup load1 / CPUs | 22.54 / 64 | 7.16 / 16 |
| Later load1, approximately 22:29 UTC | 119.29 | 9.27 |

Both startup and current-instance perf rows identify source
`196690f6cb4f3ddc89f0cfa18817688fd2675fed`. Git ancestry checks establish that it
contains quiet-policy `353d833bf0`, render fix `0d11a115db`, and the previously
verified fixed source `d12d712e792a3b496015a72e0a4ecb1ed838245f`. Both process
environments have `SASE_TUI_PERF=1` and `SASE_TUI_GC_CENSUS=1`, with no startup,
stall, or perf path overrides. Paths are `~/.sase/logs/tui_startup.jsonl`,
`~/.sase/logs/tui_stalls.jsonl[.1]`, and `~/.sase/perf/tui_jk.jsonl[.1]`.

The executable environments report SASE 0.18.1, sase-core-rs 0.43.0, Textual 8.2.8,
and Rich 15.0.0. The live source's core CI pin is
`65546fd244ec43ee023369fdafb5b5edb6197061`; this is source provenance, **not an
independent identification of the native binary already loaded by either TUI**.
No causal comparison is made between Python versions. Host load, roster sizes,
workload, runtime, and memory pressure differ. Apollo has no configured swap.

## Available coverage and target matrix

The observed post-warmup endpoints are:

| Host | UTC endpoints | Span | Paired intervals | Coverage defect |
| --- | --- | ---: | ---: | --- |
| Athena | 21:05:36.129133–22:20:56.979604 | 4,520.850 s | 15 | One 304.094 s interval exceeds the reporter's 302 s limit |
| Apollo | 21:05:36.706177–22:20:52.896231 | 4,516.190 s | 15 | One 302.768 s interval exceeds the reporter's 302 s limit |

All endpoints are after the respective startup plus 20 minutes. Each envelope has
16 heartbeat endpoints. Neither is four hours, and the current reporter rejects
each as contiguous coverage. The interval flags are retained unchanged; this
assessment does not relax the guard or treat an elapsed envelope as accepted
coverage. These intervals have `window_s` 303.696331 s and 302.705728 s, within
0.397442 s and 0.062046 s of wall deltas. Their rejection is specifically the
302-second absolute cap; a later review should distinguish scheduler delay from
lost accounting without weakening coverage evidence. The raw per-interval `window_s` comparisons are in
`independent-verification.json` for later diagnosis.

| Target | R5 Athena | Fixed Athena | R5 Apollo | Fixed Apollo |
| --- | --- | --- | --- | --- |
| Gap-free four-hour span | 14,452.309 s | **INCOMPLETE**, 4,520.850 s with flagged interval | 14,405.583 s | **INCOMPLETE**, 4,516.190 s with flagged interval |
| Idle full-GC p95 ≤0.5 s | 2.761 s, n=120 | **FAIL**, 3.908496 s, n=52 | 0.184 s, n=83 | **FAIL**, 1.016013 s, n=62 |
| Total GC <3% | 5.709% | **FAIL**, 11.2549% / 508.819 s | 0.664% | **FAIL**, 4.2410% / 191.530 s |
| Loop hitches <0.5% | 3.583% | **FAIL**, 14.2473% / 644.098 s | 0% | **FAIL**, 0.7183% / 32.441 s |
| Automatic/backstop full GC within 2 s of input | 0 observed | 0 of 8 eligible; **INCOMPLETE** coverage | 0 observed | 0 of 8 eligible; **INCOMPLETE** coverage |
| Late hitch exception | 5 outside idle/census; additional mixed episodes | **FAIL**, 3 violations and 34 unknown; 0 exempt | 0 observed | 0 observed; **INCOMPLETE** coverage |
| RSS growth <500,000,000 B over four hours | +694,468,608 B | **INCOMPLETE**, no four-hour span | +178,610,176 B | **INCOMPLETE**, no four-hour span |
| Sampled VmSwap zero | Maximum heartbeat 620,150,784 B | **FAIL**, maximum/final 4,567,040 B | 0 B | 0 B observed; **INCOMPLETE** coverage |
| Representative Agents j/k, p95 <16 ms | n=1, insufficient | **INCOMPLETE**, n=31, observed p95 838.889 ms | n=0 | **INCOMPLETE**, n=9, observed p95 210.243 ms |
| Other normally used tabs | Unmeasured | **INCOMPLETE**, none measured or declared | Unmeasured | **INCOMPLETE**, none measured or declared |
| Prompt-active/idle comparison | Unmeasured | Attributed state evidence present, detailed below | Unmeasured | **INCOMPLETE**, no post-warmup text-entry activity |
| Same-instance 24-hour soak | Not established | **INCOMPLETE** | Not established | **INCOMPLETE** |

The R5 figures describe a mostly quiet four-hour workload; the new figures describe
about 75 minutes with different activity and host pressure. Numeric changes are not
a controlled before/after estimate of any individual fix's effect. Athena's R5
process probes reached 621,490,176 B swap, slightly above its heartbeat maximum.

Current full-generation emitted/heartbeat counts agree **60/60** on Athena and
**70/70** on Apollo, with no suppressed full-generation pause rows. The first
heartbeat's preceding-interval counters are excluded. Athena additionally reports
21 suppressed hitch episodes / 58.646 s; those are retained separately, not silently
discarded or added again to the reporter's headline. Apollo reports none.

Current Athena RSS goes from 13,796,249,600 to 5,494,075,392 B, with sampled range
5,354,917,888–15,527,321,600 B. Apollo goes from 3,568,902,144 to 5,058,142,208 B,
range 1,491,382,272–5,058,142,208 B. These short-window endpoints do not substitute
for four-hour RSS growth, and neither establishes a leak by itself. Full RSS/swap
trajectories are retained in the JSON reports.

### Failures independently present without the coverage gaps

To separate known failures from the reporter's coverage rejection, the same
unchanged reporter was run on contiguous fragments bounded by actual heartbeats.
No restarts or hosts were combined and no values were subtracted.

| Contiguous fragment | Athena | Apollo |
| --- | ---: | ---: |
| UTC bounds | 21:25:44.139213–22:20:56.979604 | 21:05:36.706177–22:10:49.603220 |
| Observed duration | 3,312.840 s | 3,912.897 s |
| Idle full-GC p95 | **3.929704 s**, n=34 | **0.907595 s**, n=53 |
| GC share | **11.7889%** | **4.0104%** |
| Loop hitch share | **14.7488%** | **0.6271%** |
| Full-GC rows / heartbeat count | 40 / 40 | 60 / 60 |
| Near-input full collections | 0, fragment PASS | 0, fragment PASS |
| Maximum VmSwap | **4,567,040 B** | 0 B |

These shorter fragments corroborate current performance failures. They are not
four-hour acceptance runs, and their local PASS values cannot complete the epic.

## Interaction and instrumentation limits

Only observed Agents navigation was selected; Agents was not inferred to be the
user's only usual tab. The user supplied no representative workload description or
additional tab list. The best candidate hours retained in the CLI invocations are
Athena 21:15:36.129133–22:15:36.129133 UTC and Apollo
21:05:36.706177–22:05:36.706177 UTC. They contain respectively 30 and 8 measured
next/prev actions across three ten-minute bins. Both miss the required 100 actions
across four bins, independently of the contiguous-coverage rejection. No candidate
is asserted to represent normal busy use.

Across the full selected envelopes Athena has 45 attributed instrumented actions:
31 j/k, 3 leader, 5 panel, 6 prompt. Apollo has 16: 9 j/k, 6 leader, 1 panel.
The cumulative dropped-sample witnesses are 2 and 1. Legacy rows and other
instances remain excluded. Navigation p50/p95/max is 159.455/838.889/1,337.490 ms
on Athena and 63.530/210.243/303.319 ms on Apollo. Those sparse distributions
demonstrate slow observations, not a representative p95 acceptance verdict.

Athena's activity sequence reconstructs 1,057.016 s prompt-active, 3,303.795 s idle,
160.039 s modal-open including 77.110 s modal text entry, 48 transitions, and zero
unknown duration. Its fully prompt-active heartbeat bucket contains one interval
/ 301.344 s, with GC 12.935 s and loop hitches 2.216 s. Fully idle buckets contain
five intervals / 1,505.835 s, GC 151.630 s and loop hitches 218.191 s. Eight mixed
intervals remain unassigned; one invalid interval is excluded from the comparison.
Emitted pause/episode observations overlap these counters and must not be added.

Apollo reconstructs 4,515.224 s idle, 0.967 s non-text modal activity, four
transitions, and zero prompt-active or modal-text-entry duration in this envelope.
Its 13 fully idle valid intervals contain GC 156.921 s and hitches 24.539 s; one
mixed interval is unassigned and one invalid interval excluded. The user's preflight
confirmation is preserved, but this instance's measured window cannot establish the
missing active/idle comparison.

Six Athena and seven Apollo census spans inside the envelopes total 40.357 s and
14.982 s; maxima are 9.586 s and 3.140 s. Census spans overlap collections. No
census duration was subtracted from headline metrics, nor added to GC time. This
bundle does not claim a census-free measurement. Census samples still show Agent,
Strip/FIFOCache, and archive/event populations, supporting further ownership and
update-cadence investigation without proving the responsible allocation shares.

## Disposition

Fixed-code preflight is established. Successful acceptance and completed duration
coverage are not. Waiting alone cannot resolve the currently observed slow pauses
and swap failure, and sparse navigation cannot be promoted to a busy workload.
The measured result is published now under the user's no-further-wait preference.

No source changes, installs, TUI restarts, new monitor, new question gate, or new
task beads were performed. `sase bead epic-symbols sase-1nf.14.1.7` reports no
leftovers. Failure proposals on the assigned phase identify the exact source and
evidence for the land agent. The four-hour, per-tab/workload, Apollo text-entry,
and same-instance 24-hour obligations remain unresolved; neither this phase nor
the epic is represented as completed or fixed.
