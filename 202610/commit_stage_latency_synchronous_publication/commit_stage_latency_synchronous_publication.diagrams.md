# Diagram proposals: Why SASE agent commit stages take minutes, and sometimes hours

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202610/commit_stage_latency_synchronous_publication/commit_stage_latency_synchronous_publication__final.md
producer: research.5h.image
check: "mmdc 12.0.0 with the PDF-mirroring config rendered 3 of 3 Mermaid diagrams; negative parse test exited nonzero"
```

## publisher-contention

```yaml
anchor: |-
  If the lock is busy, mark
question: |-
  How should a host publisher handle concurrent publication requests?
illustrates: |-
  The proposed host-owned publisher batches publication, marks itself dirty on lock contention without charging an attempt, and acknowledges requests only after verified publication.
caption: "Proposed: either trigger wakes one host publisher; lock contention schedules another pass without quarantine or charging an attempt."
review: "638x851 px, fit 100.0%; question, source trace, labels, arrowheads, crossings and reading-direction checks passed; 0 revisions"
```

```mermaid
---
title: "How should publisher contention be handled?"
accTitle: "Proposed host publisher handles contention without quarantine"
accDescr: "Either shutdown after done.json or a periodic sweep wakes a host-owned publisher. A busy lock marks the publisher dirty for another pass without charging attempts or quarantine. Available lock permits batch publication; requests are acknowledged only after verification."
config:
  flowchart:
    rankSpacing: 20
    nodeSpacing: 22
    wrappingWidth: 230
---
flowchart TD
  subgraph HOST["Proposed: host-owned publisher"]
    RUN["`**Runner shutdown**<br/>After done.json`"]
    SWEEP["`**Periodic sweep**<br/>Backstop wake-up`"]
    LOCK{{"`**Publication lock busy?**`"}}
    DIRTY["`**Mark publisher dirty**<br/>No quarantine or attempt charged`"]
    BATCH["`**Batch publication**<br/>Build inventory, render hood once`"]
    ACK["`**Acknowledge request**<br/>Only after verified publication`"]
    RUN -.->|"either trigger wakes"| LOCK
    SWEEP -.->|"either trigger wakes"| LOCK
    LOCK -.->|"Yes"| DIRTY
    DIRTY -.->|"run another pass"| LOCK
    LOCK -.->|"No"| BATCH
    BATCH -.->|"content verified as published"| ACK
  end
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class RUN,SWEEP,BATCH focus
  class LOCK,DIRTY decision
  class ACK outcome
  class RUN,SWEEP,LOCK,DIRTY,BATCH,ACK proposed
  style HOST fill:none,stroke:#3B78C2,stroke-dasharray:5 3
```

## referenced-by-retry

```yaml
anchor: |-
  The `RuntimeError` escapes `drain_referenced_by_requests` before
question: |-
  Why do failed referenced-by requests never leave the retry loop?
illustrates: |-
  The referenced-by write-back fails after the lock, pull, and snapshot but before the attempt counter updates, so every commit replays requests that never quarantine.
caption: "Fenced link write-back fails before attempt accounting, so active requests repeat the expensive work on every commit and never quarantine."
review: "450.25x870 px, fit 100.0%; question, source trace, labels, arrowheads, crossings and reading-direction checks passed; 0 revisions"
```

```mermaid
---
title: "Why do referenced-by retries never quarantine?"
accTitle: "The fenced write fails before retry accounting"
accDescr: "Every commit replays active requests, taking a sidecar lock, pulling and building a full link snapshot before a legacy-write fence throws RuntimeError. The exception skips attempt accounting; requests remain active and the next commit repeats the work."
config:
  flowchart:
    rankSpacing: 18
    nodeSpacing: 22
    wrappingWidth: 230
---
flowchart TD
  REPLAY["`**Every commit**<br/>Replays active referenced-by requests`"]
  WORK["`**Plans-sidecar work**<br/>Lock, pull, full link snapshot`"]
  FENCE["`**Legacy-write fence**<br/>Raises RuntimeError`"]
  SKIP["`**Attempt update skipped**<br/>Exception escapes the drain`"]
  ACTIVE["`**83 requests stay active**<br/>82 still at zero attempts`"]
  REPLAY -->|"pays for"| WORK
  WORK -->|"only then reaches"| FENCE
  FENCE -->|"fails before accounting"| SKIP
  SKIP -->|"never quarantines"| ACTIVE
  ACTIVE -->|"next commit retries"| REPLAY
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  class REPLAY,WORK focus
  class FENCE,SKIP,ACTIVE risk
```

## swallowed-drain-timeout

```yaml
anchor: |-
  An alarm that lands there becomes a
question: |-
  Why can a drain publish after its 120-second alarm fires?
illustrates: |-
  The scanner can turn PublicationDrainTimedOut into a scan_error for one file, allowing the locked drain to carry on and end published after the alarm.
caption: "The locked drain's alarm can become a per-file scan error; six drains still published. Passes A and C remain outside its scope."
review: "515.508x1092 px, fit 81.8%; question, source trace, labels, arrowheads, crossings and reading-direction checks passed; 0 revisions"
```

```mermaid
---
title: "Why can publication outlive its 120-second alarm?"
accTitle: "Secret-scanner handlers can swallow a publication timeout"
accDescr: "The publication timeout is a TimeoutError and OSError. When a scanner handler catches it, the alarm becomes a scan_error for one file and the drain carries on. Six logged alarms ended published after 174 to 219 seconds, while 25 ended timeout."
config:
  flowchart:
    rankSpacing: 16
    nodeSpacing: 20
    wrappingWidth: 230
---
flowchart TD
  ALARM["`**120-second alarm fires**<br/>Raises PublicationDrainTimedOut`"]
  TYPE["`**TimeoutError subclass**<br/>Also an OSError`"]
  CATCH{{"`**Caught by scanner handler?**`"}}
  ERROR["`**scan_error verdict**<br/>For one file`"]
  CONTINUE["`**Drain carries on**`"]
  PUBLISHED["`**6 drains published**<br/>After 174–219 seconds`"]
  TIMEOUT["`**25 drains ended timeout**`"]
  ALARM -->|"exception type is"| TYPE
  TYPE -->|"Exception or OSError handler"| CATCH
  CATCH -.->|"Yes: alarm swallowed"| ERROR
  ERROR -->|"does not stop drain"| CONTINUE
  CONTINUE -->|"observed outcome"| PUBLISHED
  CATCH -->|"No: timeout propagates"| TIMEOUT
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  classDef muted fill:#F3F4F6,stroke:#6B7280,stroke-width:1.5px,color:#1F2937
  class ALARM,TYPE focus
  class CATCH,ERROR,CONTINUE,PUBLISHED risk
  class TIMEOUT muted
```
