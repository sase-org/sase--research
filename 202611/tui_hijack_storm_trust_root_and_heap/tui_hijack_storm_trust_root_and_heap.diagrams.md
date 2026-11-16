# Diagram proposals: SASE TUI Slowdown: Three Stacked Causes and a Staged Recovery Plan

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/tui_hijack_storm_trust_root_and_heap/tui_hijack_storm_trust_root_and_heap__final.md
producer: research.62.image
check: "mmdc 12.0.0 with the PDF-mirroring config rendered 3 of 3 Mermaid diagrams"
```

## archive-scan-storm

```yaml
anchor: |-
  Each refresh starts a new scan while old ones still run.
question: |-
  Why do archive scans keep piling up and delay unrelated loads?
illustrates: |-
  The roster-generation cache never converges, so refreshes overlap archive scans and queue other default-executor work.
caption: "Changing roster generations discard slow results; later refreshes keep launching scans, saturating the shared executor and delaying other loads."
review: "679.198x742 px, fit 96.1%; question, source and visual checks passed; 0 revisions"
```

```mermaid
---
title: "Why do refreshes create an archive-scan storm?"
config:
  flowchart:
    rankSpacing: 26
    nodeSpacing: 22
    wrappingWidth: 210
---
flowchart TD
  R["`**Refresh**<br/>Roster generation advances`"]
  S["`**Archive scan**<br/>Uses shared executor`"]
  D["`**Result discarded**<br/>Cache stays cold`"]
  E["`**Executor saturated**<br/>Overlapping scans occupy workers`"]
  L["`**Other loads wait**<br/>Shared work queues`"]
  R -->|"schedules another scan"| S
  S -->|"finishes after generation moves"| D
  D -->|"next refresh schedules again"| S
  S -->|"overlapping scans cause"| E
  E -->|"queues unrelated work"| L
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  class R,S focus
  class D,E,L risk
```

## quadratic-trust-lookup

```yaml
anchor: |-
  defeats `_project_identity`'s fast primary match, so it scans **all** registered
question: |-
  Why does resolving each project's shortcuts multiply configuration work across every project?
illustrates: |-
  The wrong checkout root defeats the fast primary match, making each project trigger merges and git remotes across all registered projects.
caption: "A failed fast identity match turns each project's lookup into a scan of all projects, multiplying startup configuration work."
review: "785.5x743 px, fit 83.1%; question, source and visual checks passed; 1 sizing/source revision"
```

```mermaid
---
title: "Why does startup multiply configuration work?"
---
sequenceDiagram
  autonumber
  participant APP as TUI constructor
  participant PROVIDER as Provider discovery
  participant IDENTITY as Identity lookup
  APP->>PROVIDER: Discover tabs for shortcuts
  loop Each project (10 measured)
    PROVIDER->>IDENTITY: Resolve identity
    Note over IDENTITY: Wrong root:<br/>fast primary match fails
    loop All registered projects
      IDENTITY->>IDENTITY: Merge config<br/>run git remote
    end
    IDENTITY-->>PROVIDER: Return identity
  end
  PROVIDER-->>APP: Return provider records
```

## slim-list-records

```yaml
anchor: |-
  nested `AgentArtifactRecordWire` trees (`_record_from_dict`) for list paint.
question: |-
  How would list records and full detail records differ after the proposed heap change?
illustrates: |-
  Python currently inflates full nested wire trees for list paint; the proposal consumes slim rows and hydrates full records only for the selected identity.
caption: "Proposed slim rows serve the list; only the selected identity gets a full record."
review: "616.266x673 px, fit 100.0%; question, source and visual checks passed; 1 visual revision to place Today before Proposed"
```

```mermaid
---
title: "How would slim list rows avoid full-record inflation?"
config:
  flowchart:
    rankSpacing: 26
    nodeSpacing: 24
    wrappingWidth: 210
---
flowchart TB
  subgraph AFTER["Proposed"]
    direction TB
    C2["`**Core list response**<br/>Slim row records`"]
    W2["`**Python list rows**<br/>Consume slim records`"]
    P2["`**List paint**<br/>Uses slim rows`"]
    H2["`**Full record**<br/>Hydrate selected identity only`"]
    C2 -.->|"Python consumes"| W2
    W2 -.->|"feeds"| P2
    P2 -.->|"selection requests detail"| H2
  end
  subgraph TODAY["Today"]
    direction TB
    C1["`**Core list response**<br/>List projection available`"]
    W1["`**Python list rows**<br/>Full nested wire trees`"]
    P1["`**List paint**<br/>Uses inflated records`"]
    C1 -->|"Python inflates"| W1
    W1 -->|"feeds"| P1
  end
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class C1 focus
  class W1,P1 risk
  class C2,W2,P2,H2 outcome
  class C2,W2,P2,H2 proposed
  style TODAY fill:none,stroke:#3B78C2
  style AFTER fill:none,stroke:#2E7D4F,stroke-dasharray:5 3
```
