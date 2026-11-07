# Diagram proposals: Spotify for SASE agents

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/spotify_library_access_for_agents/spotify_library_access_for_agents__final.md
producer: research.3k.image
check: "mmdc 12.0.0 with the PDF-mirroring config rendered 2 of 2 Mermaid diagrams; pinned npx CLI with Puppeteer --no-sandbox"
```

## credential-isolation

```yaml
anchor: |-
  isolate a hostile agent running as Bryan's OS user, which can read the token
question: |-
  Why can a same-user agent bypass gates, and what would hard enforcement require?
illustrates: |-
  The proposed personal tool does not isolate a hostile agent running as Bryan’s OS user; a hard approval requirement would need a separate token holder behind an authenticated approval channel.
caption: In the proposed tool, same-user agents can bypass gates; hard enforcement would require a separate token holder behind authenticated approval.
review: 825.328x673 px, fit 79.1%; reader-question, source-trace and visual checks passed; 1 revision; access arrows, conditional paths dashed
```

```mermaid
---
title: "When do gates need credential isolation?"
config:
  flowchart:
    rankSpacing: 22
    nodeSpacing: 18
    wrappingWidth: 170
---
flowchart TB
  subgraph SAME["Personal tool: same OS user"]
    direction TB
    A["`**Agent**<br/>Runs as Bryan`"]
    T["`**Token store**<br/>Shared credentials`"]
    S["`**Spotify API**<br/>Direct writes possible`"]
    A -->|can read| T
    A -->|can call directly| S
  end
  subgraph ISOLATED["Conditional: separate token holder"]
    direction TB
    B["`**Agent**<br/>Requests changes`"]
    G["`**Approval channel**<br/>Authenticated`"]
    H["`**Token holder**<br/>Separate user or service`"]
    P["`**Spotify API**<br/>Holder makes calls`"]
    B -.->|requests through| G
    G -.->|authorizes| H
    H -.->|calls| P
  end
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class A,B focus
  class T,S risk
  class G,H,P outcome
  class B,G,H,P proposed
  style SAME fill:none,stroke:#C0392B
  style ISOLATED fill:none,stroke:#2E7D4F,stroke-dasharray:5 3
```

## playlist-read-consistency

```yaml
anchor: |-
  Content reads compare the playlist snapshot before and after pagination.
question: |-
  How does a content read avoid mixing playlist versions?
illustrates: |-
  Content reads compare the playlist snapshot before and after pagination, retry a bounded number of times, then return changed_during_read rather than mix versions.
caption: The proposed read protocol checks snapshots around pagination and retries only within a bound; continued changes return changed_during_read.
review: 474.730x786 px, fit 100.0%; reader-question, source-trace and visual checks passed; 1 revision; arrows show proposed control flow
```

```mermaid
---
title: "How would reads avoid mixing playlist versions?"
config:
  flowchart:
    rankSpacing: 16
    nodeSpacing: 18
    wrappingWidth: 175
---
flowchart TD
  READ["`**Read playlist pages**<br/>Snapshot before and after`"]
  SAME{{"`**Snapshots match?**`"}}
  OK["`**Consistent result**<br/>Preserve item order`"]
  RETRY{{"`**Retries remain?**`"}}
  FAIL["`**Changed during read**<br/>Return a typed error`"]
  READ -.->|compare snapshots| SAME
  SAME -.->|Yes| OK
  SAME -.->|No| RETRY
  RETRY -.->|Yes: retry| READ
  RETRY -.->|No: stop| FAIL
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class READ,FAIL focus
  class SAME,RETRY decision
  class OK outcome
  class READ,SAME,RETRY,OK,FAIL proposed
```
