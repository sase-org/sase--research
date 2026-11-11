# Diagram proposals: The next seven task beads: salvage what already landed-in-name, then unstrand the fleet

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/next_seven_task_beads_salvage_and_unstrand/next_seven_task_beads_salvage_and_unstrand__final.md
producer: research.4a.image
check: mmdc 12.0.0 with the PDF-mirroring config rendered 2 of 2 Mermaid diagrams; Puppeteer --no-sandbox
```

## monitor-ownership

```yaml
anchor: |-
  bound ownership using actual delivery/recovery facts, distinguishing a dead abandoned
question: |-
  How should stale monitor ownership be bounded?
illustrates: |-
  The proposed repair bounds monitor ownership using actual delivery/recovery facts, distinguishing a dead abandoned follow-up from a real queued successor, a live monitor, and legitimate settlement grace.
caption: The proposed repair distinguishes abandoned follow-ups from queued successors, live monitors, and settlement grace before classifying bead ownership.
review: 585.539x990 px, fit 90.2%; question, source trace, and visual checks passed; 0 revisions
```

```mermaid
---
title: "How should stale monitor ownership be bounded?"
config:
  flowchart:
    rankSpacing: 20
    nodeSpacing: 18
    wrappingWidth: 220
---
flowchart TD
  subgraph CURRENT["Current classification"]
    DONE["`**Done monitor**<br/>Stale followup_pending flag`"]
    OWN["`**Owned / monitor**<br/>Hidden from recovery indefinitely`"]
    DONE -->|"stale flag implies"| OWN
  end
  subgraph PROPOSAL["Proposed: use delivery and recovery facts"]
    FACTS{{"`**Actual follow-up state?**`"}}
    STRANDED["`**Stranded**<br/>Abandoned follow-up`"]
    KEEP["`**Legitimate ownership**<br/>Protect real recovery work`"]
    FACTS -.->|"dead and abandoned"| STRANDED
    FACTS -.->|"queued successor, live monitor,<br/>or settlement grace (any)"| KEEP
  end
  DONE -.->|"proposed classification"| FACTS
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class DONE,FACTS focus
  class OWN risk
  class STRANDED,KEEP outcome
  class FACTS,STRANDED,KEEP proposed
  style CURRENT fill:none,stroke:#C0392B
  style PROPOSAL fill:none,stroke:#2E7D4F,stroke-dasharray:5 3
```

## continuation-growth

```yaml
anchor: |-
  so every session member re-nests its whole ancestry
question: |-
  How does fork replay block a follow-up?
illustrates: |-
  Capturing the fork-expanded prompt and replaying it as the parent user block re-nests ancestry until an over-cap request fails capture and leaves the next monitor follow-up not-launchable.
caption: Fork replay re-nests ancestry; exceeding the 262,144-byte cap fails capture and leaves the next monitor follow-up not-launchable until manual resume.
review: 800x718 px, fit 81.6%; question, source trace, and visual checks passed; 0 revisions
```

```mermaid
---
title: "How does fork replay block a follow-up?"
config:
  flowchart:
    rankSpacing: 22
    nodeSpacing: 20
    wrappingWidth: 220
---
flowchart TD
  EXPANDED["`**Expanded fork prompt**<br/>Includes the whole ancestry`"]
  CAPTURE["`**authored_local_request**<br/>Captures the expanded prompt`"]
  REPLAY["`**Parent user block**<br/>Replays captured ancestry`"]
  FAILURE["`**Capture fails**<br/>Validator rejects oversized request`"]
  BLOCKED["`**Next monitor follow-up**<br/>Not launchable`"]
  RESUME["`**Manual intervention**<br/>sase monitor resume`"]
  EXPANDED -->|"stored as"| CAPTURE
  CAPTURE -->|"rendered as"| REPLAY
  REPLAY -->|"next member re-nests ancestry"| EXPANDED
  EXPANDED -->|"over 262,144 bytes"| FAILURE
  FAILURE -->|"leaves"| BLOCKED
  BLOCKED -->|"requires"| RESUME
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  class EXPANDED,CAPTURE,REPLAY focus
  class FAILURE,BLOCKED risk
  class RESUME outcome
```
