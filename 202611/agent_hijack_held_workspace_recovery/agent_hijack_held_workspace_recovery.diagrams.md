# Diagram proposals: Agent Hijack: Stop the Turn, Keep the Work

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/agent_hijack_held_workspace_recovery/agent_hijack_held_workspace_recovery__final.md
producer: research.33.image
check: "mmdc 12.0.0 with --no-sandbox and the PDF-mirroring config rendered 1 of 1 Mermaid diagrams; a deliberately broken diagram exited nonzero"
```

## recovery-resolution

```yaml
anchor: |-
  A resolution writes `resolving` plus its action under the
question: |-
  How does recovery prevent duplicate successors after concurrent requests or a crash?
illustrates: |-
  Exactly-once resolution locks the action before effects and reconciles a crash by adopting the reserved successor or returning to held.
caption: The resolution lock rejects concurrent recovery; after a crash, adopt the reserved successor if it exists, otherwise return to held.
review: "607.324x786 px, fit 100.0%; question, labels, arrowheads, source trace, and visual checks passed; 1 revision, 2 visual looks"
```

```mermaid
---
title: "Proposed: how does recovery avoid duplicates?"
accTitle: "Proposed hijack resolution and crash reconciliation"
accDescr: "The resolution lock refuses a second request. After a crash, reconciliation adopts the reserved successor if it exists, or returns the hijack to held."
config:
  flowchart:
    rankSpacing: 12
    nodeSpacing: 24
    wrappingWidth: 210
---
flowchart TD
  BUSY{{"`**Already resolving?**<br/>Check under lock`"}}
  REFUSE["`**Refuse second request**<br/>Already being resolved`"]
  RECORD["`**Record resolving + action**<br/>Under lock, before effects`"]
  EXISTS{{"`**Reserved successor exists?**`"}}
  ADOPT["`**Adopt successor**<br/>Use the reserved run`"]
  HELD["`**Return to held**<br/>Show a toast`"]
  BUSY -.->|Yes| REFUSE
  BUSY -.->|No| RECORD
  RECORD -.->|after a crash: reconcile| EXISTS
  EXISTS -.->|Yes| ADOPT
  EXISTS -.->|No| HELD
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class RECORD focus
  class BUSY,EXISTS decision
  class REFUSE,ADOPT,HELD outcome
  class BUSY,REFUSE,RECORD,EXISTS,ADOPT,HELD proposed
```
