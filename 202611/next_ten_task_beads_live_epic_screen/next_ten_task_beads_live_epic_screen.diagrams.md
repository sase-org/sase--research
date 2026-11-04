# Diagram proposals: The ten task beads to work next, screened against live epics on apollo and athena

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/next_ten_task_beads_live_epic_screen/next_ten_task_beads_live_epic_screen__final.md
producer: research.3a.image
check: "mmdc 12.0.0 with the PDF-mirroring config rendered 2 of 2 Mermaid diagrams; Puppeteer --no-sandbox"
```

## reboot-recovery

```yaml
anchor: |-
  Release claims held by dead owners from the previous boot, or
question: |-
  Why can a relaunch fail after reboot, and what would prevent repeat failures?
illustrates: |-
  The proposed boot reconciler releases dead claims and uses a durable marker to relaunch each stranded epic once per boot, avoiding the stale-claim failure seen in the reboot relaunches.
caption: "The proposed reconciler clears dead claims and relaunches each stranded epic once per boot; repeat scheduler starts do nothing."
review: "773.714x668 px, fit 84.4%; question, source, unique-anchor, and visual checks passed; 1 layout revision; 2 look rounds"
```

```mermaid
---
title: "How would reboot recovery avoid stale claims?"
config:
  layout: dagre
  flowchart:
    rankSpacing: 12
    nodeSpacing: 12
    wrappingWidth: 180
---
flowchart LR
  subgraph TODAY["Observed after the reboot"]
    direction TB
    C0["`**Reboot**<br/>Dead processes; no completion`"]
    C1["`**Relaunch attempts**<br/>Dead owners retain claims`"]
    C2["`**7 of 8 blocked**<br/>Already in progress`"]
    C0 -->|Relaunch attempted| C1
    C1 -->|Stale claim blocks| C2
  end
  subgraph PLAN["Proposed reboot reconciler"]
    direction TB
    P0["`**Boot reconciler**<br/>Find stranded epics`"]
    Q{{"`**Relaunched this boot?**`"}}
    RELEASE["`**Release claims**<br/>Dead prior-boot owners`"]
    RUN["`**Relaunch epic**<br/>Record durable boot marker`"]
    SKIP["`**No repeat relaunch**<br/>Second start does nothing`"]
    P0 -.->|Check durable marker| Q
    Q -.->|No| RELEASE
    RELEASE -.->|Claims cleared| RUN
    Q -.->|Yes| SKIP
  end
  TODAY ~~~ PLAN
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class C0,C1,C2 risk
  class Q decision
  class P0,RELEASE,RUN,SKIP outcome
  class P0,Q,RELEASE,RUN,SKIP proposed
  style TODAY fill:none,stroke:#C0392B
  style PLAN fill:none,stroke:#2E7D4F,stroke-dasharray:5 3
```

## editor-recovery

```yaml
anchor: |-
  and then the `finally` blocks unlink the temp file
question: |-
  What happens to changed prompt text when the editor fails?
illustrates: |-
  On a non-zero editor exit, the proposed recovery compares the file with its initial content and stashes changed drafts, preserving the text that current finally cleanup deletes.
caption: "The proposal stashes changed drafts without auto-submitting, retains their temporary files, and deletes only unchanged text after editor failure."
review: "715.201x535 px, fit 91.3%; question, source, unique-anchor, and visual checks passed; 1 layout revision; 2 look rounds"
```

```mermaid
---
title: "Where does a failed editor's draft go?"
config:
  layout: dagre
  flowchart:
    rankSpacing: 12
    nodeSpacing: 12
    wrappingWidth: 180
---
flowchart LR
  subgraph TODAY["Current behavior"]
    direction TB
    C0["`**Editor exits nonzero**`"]
    C1["`**Return None**`"]
    C2["`**Finally deletes file**<br/>Changed draft is lost`"]
    C0 -->|Failure returns| C1
    C1 -->|Cleanup always runs| C2
  end
  subgraph PLAN["Proposed recovery"]
    direction TB
    P0["`**Editor exits nonzero**`"]
    Q{{"`**Text changed?**`"}}
    KEEP["`**Recover changed text**<br/>Stash + toast; keep temp file`"]
    DELETE["`**Delete temp file**<br/>No changed draft`"]
    P0 -.->|Compare with initial content| Q
    Q -.->|Yes| KEEP
    Q -.->|No| DELETE
  end
  TODAY ~~~ PLAN
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class C0,C1,C2 risk
  class Q decision
  class P0,KEEP,DELETE outcome
  class P0,Q,KEEP,DELETE proposed
  style TODAY fill:none,stroke:#C0392B
  style PLAN fill:none,stroke:#2E7D4F,stroke-dasharray:5 3
```
