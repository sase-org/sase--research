# Diagram proposals: Agent hijack dependability: consolidated findings and recommendation

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/agent_hijack_dependability/agent_hijack_dependability__final.md
producer: research.4u.image
check: "mmdc 12.0.0 with Puppeteer --no-sandbox and the PDF-mirroring config rendered 1 of 1 Mermaid diagrams"
```

## claim-latch

```yaml
anchor: |-
  the first transition that observes it applies it exactly once via a ledger
question: |-
  How does a proposed claim latch prevent a successor from launching?
illustrates: |-
  A latched workspace claim transfers to nobody, and the first transition that observes it applies the hijack exactly once via a ledger CAS.
caption: "Provided every handoff uses claim transfer, a latched claim blocks successor launch and applies takeover once through the ledger."
review: "486.734x868 px, fit 100.0%; question, source trace, labels, arrowheads and visual checks passed; 1 revision across 2 look rounds; batch and negative parse checks passed"
```

```mermaid
---
title: "Proposed: how does a latch block successor launch?"
accTitle: "Proposed claim latch at a handoff boundary"
accDescr: "At a claim transition, a latch prevents claim transfer. The first observing transition applies hijack once through a ledger compare-and-swap, retaining the workspace. This depends on all handoffs using claim operations."
config:
  flowchart:
    rankSpacing: 12
    nodeSpacing: 16
    wrappingWidth: 260
---
flowchart TD
  TRANSITION["`**Claim transition**<br/>Under claim lock`"]
  LATCH{{"`**Hijack latch present?**`"}}
  TRANSITION -.->|"inspect claim"| LATCH
  NORMAL["`**Normal handoff**<br/>Claim can transfer`"]
  BLOCK["`**Withhold claim**<br/>Launch no successor`"]
  APPLY["`**First observer applies once**<br/>Ledger compare-and-swap`"]
  HELD["`**Held workspace**<br/>Hijack custody`"]
  LATCH -.->|"No latch"| NORMAL
  LATCH -.->|"Latch present"| BLOCK
  BLOCK -.->|"apply exactly once"| APPLY
  APPLY -.->|"stop, then hold"| HELD
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class TRANSITION,NORMAL,APPLY focus
  class LATCH decision
  class BLOCK,HELD outcome
  class TRANSITION,NORMAL,APPLY,LATCH,BLOCK,HELD proposed
```
