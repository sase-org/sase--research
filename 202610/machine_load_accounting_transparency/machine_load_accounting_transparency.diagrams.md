# Diagram proposals: Machine load: why athena showed `3/8` with 6 agents running, and how to make it legible

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202610/machine_load_accounting_transparency/machine_load_accounting_transparency__final.md
producer: research.5e.image
check: "mmdc 12.0.0 with the PDF-mirroring config rendered 2 of 2 Mermaid diagrams"
```

## invalid-weight-fault

```yaml
anchor: |-
  a live claim with an invalid weight is skipped from the sum
question: |-
  Why can the gauge show free capacity while admission is blocked?
illustrates: |-
  An invalid live weight emits a diagnostic and blocks admission, but the TUI discards that diagnostic, so the proposed gauge preserves the fault alongside the known subtotal.
caption: "Invalid weights block admission; discarding diagnostics makes the terminal UI show spare capacity, while the proposed gauge preserves the fault."
review: "684.641x766 px, fit 95.3%; question and visual checks passed; every node and edge traced to C4 or F5; 0 revisions"
```

```mermaid
---
title: "Why can free capacity still block launches?"
accTitle: "An invalid weight creates a hidden accounting fault"
accDescr: "The snapshot skips an invalid live weight and emits a diagnostic. Admission blocks launches, but the current TUI drops the diagnostic and presents the subtotal as spare capacity. The proposed gauge preserves the fault and shows the known subtotal."
config:
  flowchart:
    rankSpacing: 22
    nodeSpacing: 14
    wrappingWidth: 180
---
flowchart TD
  INVALID["`**Invalid weight**<br/>Live claim`"]
  SNAP["`**Snapshot**<br/>Subtotal plus diagnostic`"]
  ADMISSION["`**Admission**<br/>Launches blocked`"]
  TUI["`**Current TUI**<br/>Diagnostic discarded`"]
  FREE["`**Gauge in fixture**<br/>0 of 8; 8 free`"]
  FAULT["`**Proposed gauge**<br/>?/8 ! + known subtotal<br/>Admission blocked`"]
  INVALID -->|"skipped from sum;<br/>fault emitted"| SNAP
  SNAP -->|"fault blocks admission"| ADMISSION
  SNAP -->|"diagnostic dropped"| TUI
  TUI -->|"subtotal shown as free"| FREE
  SNAP -.->|"proposed: preserve fault"| FAULT
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class SNAP focus
  class INVALID,ADMISSION,TUI,FREE risk
  class FAULT outcome
  class FAULT proposed
```

## parallel-claim-owners

```yaml
anchor: |-
  cdx built a synthetic case with two parallel branches in one displayed session:
question: |-
  How can lost claim owners merge parallel work?
illustrates: |-
  Dropping runner_claim_owner_key lets the TUI synthesize a shared session for two parallel branches, explaining the synthetic runtime count of 2 versus the TUI count of 1, not the screenshot incident.
caption: "Lost owner keys merge parallel claims in this synthetic example: runtime 2, terminal UI 1; this did not cause the screenshot discrepancy."
review: "491.812x728 px, fit 100.0%; question and visual checks passed; claim membership and totals traced to C3 and the claim rules; 1 revision"
```

```mermaid
---
title: "How can lost owners merge parallel claims?"
accTitle: "Synthetic parallel-branch example: runtime 2, TUI 1"
accDescr: "Two parallel branches have distinct canonical claim owners in the runtime. The TUI drops those owners and groups the branches through a synthesized session, undercounting the synthetic example. This was not the screenshot's cause."
config:
  flowchart:
    rankSpacing: 18
    nodeSpacing: 18
    wrappingWidth: 190
---
flowchart TB
  subgraph RUNTIME["Runtime: total 2 in synthetic case"]
    direction TB
    RA["`**Branch A**<br/>Parallel member`"]
    RB["`**Branch B**<br/>Parallel member`"]
    RCA["`**Claim A**<br/>Distinct owner key`"]
    RCB["`**Claim B**<br/>Distinct owner key`"]
    RA -->|"assigned to"| RCA
    RB -->|"assigned to"| RCB
  end
  subgraph TUI["TUI projection: total 1 in same case"]
    direction TB
    TB["`**Branch B**<br/>Owner key dropped`"]
    TA["`**Branch A**<br/>Owner key dropped`"]
    TC["`**One claim**<br/>Synthesized session`"]
    TB -->|"grouped into"| TC
    TA -->|"grouped into"| TC
  end
  RUNTIME ~~~ TUI
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  class RA,RB,RCA,RCB focus
  class TA,TB,TC risk
  style RUNTIME fill:none,stroke:#3B78C2
  style TUI fill:none,stroke:#C0392B
```
