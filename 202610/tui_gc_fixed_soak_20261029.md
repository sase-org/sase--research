# Fixed-code TUI 24-hour soak: interrupted same-instance interval, 29 October 2026

The soak wait ran to its deadline. The **same capture instances did not**. Athena
`8b65de59` and Apollo `7e973b00` stopped emitting telemetry at 23:09 UTC on 28
October, about eight minutes after the soak retainer started, when both hosts
minted new `app_instance_id` values on the **same PIDs** (`--restart-service`
in-process restart) at a **different source revision**. Later successor instances
are interruption evidence only. They are not pooled with this measurement.

This is **FAIL with incomplete 24-hour coverage**, not a completed soak. Contiguous
post-interrupt fragments still fail idle full-GC p95, GC share, and loop-hitch
share on both hosts. Athena also fails sampled VmSwap and late-hitch attribution.
A new complete interval needs user-confirmed preflight of fresh instances; this
report does not start one.

## Evidence and reproduction

- Raw soak bundle: `file:explicit:524eeed80cfe9f15a74f0182`. It contains
  instance-filtered unique logs, reporter sources, argv, text/JSON acceptance
  output, exit codes, soak-start witnesses, `wait-state.json`, `checkpoint.yaml`,
  `soak_wait.py`, and SHA-256 hashes.
- Prior same-instance capture, already FAIL/INCOMPLETE:
  `research:202610/tui_gc_fixed_capture_20261028.md` /
  `file:explicit:8ce7eae6df0b33fe4d6aae99`.
- Unchanged r5 baseline: `research:202610/tui_gc_measurement_20261023.md`.
- Governing design: `plan:202610/measured_tui_gc_fixes.md`, phase `fixed-soak`.
- Monitor wait `zfxaj9fatwzd` finished 2026-10-29T21:20:10Z, exit 0, after the
  2026-10-29T21:20:00Z deadline.

Retained live files mixed many later instances because the follower kept
appending host JSONL after the capture IDs ended, and rotation ingest duplicated
Apollo capture rows 2× (1298 wanted lines, 649 unique). Acceptance uses
**deduplicated, instance-filtered** rows merged with the earlier capture bundle
so the first post-warmup heartbeats are present. `--instance` selects only
`8b65de59` / `7e973b00`. Census collector time is reported separately and is not
subtracted from headline GC or hitch shares.

Every `tools/tui_freeze_report --acceptance` invocation in `commands.json` exited
**1**.

## Identity, interruption, and what was not pooled

Soak-start witnesses at 23:00–23:01 UTC still matched the capture processes:

| Witness | Athena | Apollo |
| --- | --- | --- |
| App instance | `8b65de59` | `7e973b00` |
| PID / start ticks | 4045198 / 114069905 | 1562336 / 166947655 |
| Boot ID | `2e013859-5e29-418c-bf6d-035a5eeff435` | `1e87418e-2b01-47ab-ad0d-eb23a80d5f96` |
| Startup, UTC | 2026-10-28T20:45:20.175219 | 2026-10-28T20:45:21.698951 |
| Warmup end, UTC | 21:05:20.175219 | 21:05:21.698951 |
| Flags | `SASE_TUI_PERF=1` `SASE_TUI_GC_CENSUS=1` | same |
| Source | `196690f6cb4f3ddc89f0cfa18817688fd2675fed` | same |
| Python | 3.14.7 | 3.12.3 |
| Command | `python -m sase tui --restart-service` | same |

Last capture-instance stall rows are 23:09:43.165999Z (Athena) and
23:09:35.795525Z (Apollo). Last heartbeats are 23:06:05.814902Z and
23:06:00.142745Z. Successor startups on the **same PIDs**:

| Host | New instance | Startup, UTC | Source revision |
| --- | --- | --- | --- |
| Athena | `cda56790` | 23:10:11.076913 | `c33e97574633a027ab3cc9323cbfa8f9d9b78b73` |
| Apollo | `472e4af8` | 23:10:40.962532 | `c33e97574633a027ab3cc9323cbfa8f9d9b78b73` |

Those successors, and every later ID on the same PIDs through 17:44/17:47 UTC on
29 October, are a different measurement. `soak_wait.py` treated the capture as
alive until `/proc/<pid>` vanished (Athena 17:48:32Z, Apollo 19:32:05Z) because
it matched PID, start ticks, boot ID, and flags, **not** `app_instance_id`. The
plan's rule is that every restart is a new instance even when exec reuses the
PID.

At report time the original PIDs are gone. Newer TUIs are running (Athena PID
3224594 instance `245957d9`; Apollo PID 3105496) on later revisions. They are
out of scope.

## Requested 24-hour envelope versus observed coverage

Requested post-warmup windows are 21:05:20.175219Z→21:05:20.175219Z+24h (Athena)
and 21:05:21.698951Z→+24h (Apollo). Observed heartbeat coverage:

| Host | Observed UTC endpoints | Span | Heartbeat endpoints | Valid / paired intervals | Coverage defects |
| --- | --- | ---: | ---: | ---: | --- |
| Athena | 21:05:36.129133–23:06:05.814902 | 7,229.686 s | 25 | 22 / 24 | 304.094 s and 302.193 s intervals exceed the 302 s cap; instance ends ~22 h before the request |
| Apollo | 21:05:36.706177–23:06:00.142745 | 7,223.437 s | 25 | 23 / 24 | one 302.768 s interval; instance ends ~22 h before the request |

Neither is four hours, and neither is 24 hours. Full-generation pause rows agree
with paired heartbeat generation-2 counts in the reporter: **100/100** Athena,
**107/107** Apollo. Athena reports 31 suppressed hitch episodes / 85.738 s;
those stay separate from the hitch headline. Census spans inside the envelopes:
Athena n=11, 81.448 s, max 9.972 s; Apollo n=12, 26.809 s, max 3.398 s.

## Target matrix (requested 24 h, original instances only)

Acceptance percentages below are the reporter's paired-interval shares, not
diagnostic shares of the empty 86,400 s request.

| Target | R5 Athena | Capture Athena | Soak Athena | R5 Apollo | Capture Apollo | Soak Apollo |
| --- | --- | --- | --- | --- | --- | --- |
| Gap-free 24 h / four-hour span | 14,452.309 s | INCOMPLETE, 4,520.850 s | **INCOMPLETE**, 7,229.686 s, not contiguous | 14,405.583 s | INCOMPLETE, 4,516.190 s | **INCOMPLETE**, 7,223.437 s, not contiguous |
| Idle full-GC p95 ≤0.5 s | 2.761 s | FAIL, 3.908 s | **FAIL**, 4.476 s, n=87 idle full pauses | 0.184 s | FAIL, 1.016 s | **FAIL**, 1.051 s, n=95 |
| Total GC <3% | 5.709% | FAIL, 11.255% | **FAIL**, 12.597% / 910.753 s | 0.664% | FAIL, 4.241% | **FAIL**, 4.276% / 308.859 s |
| Loop hitches <0.5% | 3.583% | FAIL, 14.247% | **FAIL**, 15.287% / 1,105.219 s | 0% | FAIL, 0.718% | **FAIL**, 0.711% / 51.365 s |
| Near-input automatic/backstop/RSS-backstop full GC | 0 | INCOMPLETE coverage | **INCOMPLETE** coverage; 0 of 13 eligible in counts | 0 | INCOMPLETE | **INCOMPLETE**; 0 of 12 eligible |
| Late hitch exception | FAIL | FAIL, 3 violations / 34 unknown | **FAIL**, 6 violations / 51 unknown / 0 exempt | 0 | INCOMPLETE | **INCOMPLETE**, 2 unknown / 0 violations |
| RSS growth <500,000,000 B over 4 h | +694,468,608 B | INCOMPLETE | **INCOMPLETE**; endpoints 13,796,249,600 → 8,781,848,576 B, peak 16,120,754,176 B; no four-hour span and no final four hours | +178,610,176 B | INCOMPLETE | **INCOMPLETE**; 3,568,902,144 → 1,308,618,752 B, peak 5,058,142,208 B |
| VmSwap zero | FAIL, max 620,150,784 B | FAIL, max 4,567,040 B | **FAIL**, max 631,345,152 B at 22:46:01Z, last 512,479,232 B | 0 B | 0 B, INCOMPLETE coverage | **INCOMPLETE** trajectory (all observed samples 0 B; coverage incomplete) |
| Representative Agents j/k p95 <16 ms | n=1 | INCOMPLETE, n=31, p95 838.889 ms | **INCOMPLETE** busy hour (contiguous coverage required); envelope agents/jk n=42 p50 183.269 / p95 792.183 / max 1,337.490 ms | n=0 | INCOMPLETE, n=9, p95 210.243 ms | **INCOMPLETE**; envelope n=12 p50 58.445 / p95 401.884 / max 522.352 ms |
| Other usual tabs | Unmeasured | INCOMPLETE, none | **INCOMPLETE**, none measured; only `agents` appears | Unmeasured | INCOMPLETE | **INCOMPLETE** |
| Prompt-active vs idle | Unmeasured | Attributed | **PASS**, active 1,112.761 s / idle 5,955.324 s / modal 161.601 s / unknown 0; text-entry 77.110 s | Unmeasured | INCOMPLETE, no text entry | **INCOMPLETE**, active 0 / idle 7,222.470 s / modal 0.967 s / text-entry 0 |
| Same-instance 24-hour soak | Not established | INCOMPLETE | **INCOMPLETE**, interrupted | Not established | INCOMPLETE | **INCOMPLETE**, interrupted |

R5 remains a quieter four-hour baseline on different instances. Numeric movement
from capture to soak is extra time on the **same** instances, not a new
before/after of the producer fixes.

### Hourly heartbeat summaries (original instances)

Later-endpoint generation-2 and hitch counters only; first heartbeat in the
envelope is excluded from the sums.

| Hour UTC | Athena gen2 n / s / hitch s / RSS range / swap max | Apollo gen2 n / s / hitch s / RSS range / swap max |
| --- | --- | --- |
| 21:00 | 51 / 108.716 / 521.256 / 5.35–15.53 GB / 0 | 51 / 29.956 / 18.911 / 1.49–4.16 GB / 0 |
| 22:00 | 44 / 151.377 / 533.616 / 3.97–14.46 GB / **631,345,152 B** | 53 / 43.608 / 32.454 / 2.15–5.06 GB / 0 |
| 23:00 | 9 / 32.676 / 100.096 / 8.78–16.12 GB / 522,149,888 B | 8 / 6.469 / 0 / 1.31–4.04 GB / 0 |

Athena swap is zero through 22:15, 4.6 MB at 22:20, then climbs to 631 MB at
22:46 and is still 512 MB at the last heartbeat. There is no final four-hour RSS
window: the instance is gone.

### Failures on contiguous fragments (coverage gaps removed)

Athena 21:25:44.139213–22:56:03.292426Z, 5,419.153 s, 18/18 valid intervals,
full-GC rows 71/71:

| Metric | Value |
| --- | ---: |
| Idle full-GC p95 | **4.387 s** |
| GC share | **13.208%** |
| Loop hitch share | **15.678%** |
| VmSwap max | **631,345,152 B** |
| Near-input full GC | 0, **PASS** |
| Agents j/k in selected hour | n=31, p95 838.889 ms, floors unmet |

Apollo 21:05:36.706177–22:10:49.603220Z, 3,912.897 s, 13/13 valid intervals,
full-GC rows 60/60 (same early fragment as the capture report):

| Metric | Value |
| --- | ---: |
| Idle full-GC p95 | **0.908 s** |
| GC share | **4.010%** |
| Loop hitch share | **0.627%** |
| VmSwap | 0 B, fragment **PASS** |
| Late hitches | 0, **PASS** |
| Near-input full GC | 0, **PASS** |
| Agents j/k in selected hour | n=8, floors unmet |

These fragments corroborate the performance misses. They are not four-hour or
24-hour acceptance.

## Workload carried forward

Only the Agents tab has attributed samples on these instances. Additional j/k
after the capture report (Athena 22:44–23:09, Apollo 22:46) stays on Agents.
Candidate hours still top out at 31 Athena / 9 Apollo `next`/`prev` actions
against the 100-action / 4-bin floor. No other usual tab was declared or
measured. Dropped-sample witnesses are 3 (Athena) and 1 (Apollo), cumulative.

Athena's extra selected busy hour 22:09:18–23:09:18Z cannot become valid while
coverage is non-contiguous.

## Disposition

The 24-hour same-instance soak did not complete. The interrupted segment plus
contiguous fragments are a complete honest FAIL/INCOMPLETE matrix for these
instances at source `196690f6cb4f3ddc89f0cfa18817688fd2675fed`. Waiting on the
original PIDs cannot continue: they already restarted onto other revisions.

A replacement 24-hour interval requires user-confirmed preflight of **new**
instances (one TUI per host, `SASE_TUI_PERF=1`, `SASE_TUI_GC_CENSUS=1`, verified
`app_instance_id`, actual Agents j/k and usual tabs) after the in-process
restarts. This report does not splice post-restart telemetry and does not close
parent epic `sase-1nf.14.1`.
