# Diagram proposals: Agent publication errors, Nov 1–2: a `task-` false positive the publisher retries forever

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/agent_publication_openai_key_false_positives/agent_publication_openai_key_false_positives__final.md
producer: research.5p.image
check: "mmdc 12.0.0 with the PDF-mirroring config rendered 2 of 2 Mermaid diagrams; batch passed; invalid-input check exited nonzero"
```

## ledger-revalidation

```yaml
anchor: |-
  A fixed rule alone will not
question: |-
  Why must recovery change both the scanner and the stored block?
illustrates: |-
  A fixed rule alone cannot free the four rows because their exact digests are stored as blocked, while the proposed reviewed revalidation path supersedes false-positive records with provenance.
caption: A rule correction leaves stored blocks intact; proposed audited revalidation supersedes confirmed false positives with provenance.
review: "687.219x601 px, fit 95.0%; question, source, and visual checks passed; 1 visual revision; second look passed"
```

```mermaid
---
title: "Why does a scanner fix leave old blocks in place?"
config:
  flowchart:
    rankSpacing: 18
    nodeSpacing: 18
    wrappingWidth: 220
---
flowchart TD
  subgraph AUTO["Rule fix alone: existing cache behavior"]
    direction TB
    FIXA["`**Corrected rule (proposed)**<br/>Content bytes unchanged`"]
    SAVED["`**Stored blocked digest**<br/>Rules bump does not invalidate`"]
    SKIP["`**No rescan**<br/>Identical bytes stay blocked`"]
    FIXA -->|"automatic lookup"| SAVED
    SAVED -->|"reuses disposition"| SKIP
  end
  subgraph AUDIT["Rule fix plus audit: proposed recovery"]
    direction TB
    FIXB["`**Corrected rule (proposed)**<br/>Content bytes unchanged`"]
    CHECK["`**Explicit revalidation**<br/>Use corrected rules`"]
    REPLACE["`**Supersede false-positive record**<br/>Keep provenance`"]
    FIXB -.->|"proposed: reviewed revalidation"| CHECK
    CHECK -.->|"proposed: confirmed false positive"| REPLACE
  end
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class FIXA,FIXB focus
  class SAVED,SKIP risk
  class CHECK,REPLACE outcome
  class FIXA,FIXB,CHECK,REPLACE proposed
  style AUTO fill:none,stroke:#C0392B
  style AUDIT fill:none,stroke:#2E7D4F,stroke-dasharray:5 3
```

## publication-routing

```yaml
anchor: |-
  New commits still get through: their requests arrive with a hint
question: |-
  Why do new commits publish while planner sessions stay queued?
illustrates: |-
  The hinted batch can publish new commits and report blocked-key errors in the same pass, while unhinted planner agent and session publication waits for the skipped fallback.
caption: New commits can publish despite batch errors; unhinted planner agent/session data waits, although its prompt Markdown is already published.
review: "755.297x814 px, fit 86.4%; question, source, and visual checks passed; 0 visual revisions; both conditions jointly explain the planner wait"
```

```mermaid
---
title: "Why can commits publish while planners wait?"
config:
  flowchart:
    rankSpacing: 18
    nodeSpacing: 18
    wrappingWidth: 220
---
flowchart TD
  COMMIT["`**New commit request**<br/>Arrives with a hint`"]
  PLAN["`**Planner request**<br/>Arrives without a hint`"]
  BATCH["`**Hinted batch**<br/>Includes new commit requests`"]
  PUBLISH["`**New commits can publish**<br/>Occasional successful drains`"]
  ERROR["`**Stuck keys error**<br/>Fallback loop skipped`"]
  WAIT["`**Planner publication waits**<br/>Agent and session data`"]
  COMMIT -->|"routes to"| BATCH
  BATCH -->|"can drain new commits"| PUBLISH
  BATCH -->|"also encounters blocked keys"| ERROR
  PLAN -->|"depends on fallback drain"| WAIT
  ERROR -->|"prevents fallback progress"| WAIT
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  class COMMIT,PLAN,BATCH focus
  class PUBLISH outcome
  class ERROR,WAIT risk
```
