# Diagram proposals: Copying specific parts of agent questions

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/question_copy_items/question_copy_items__final.md
producer: research.6j.image
check: "mmdc 12.0.0 with Puppeteer --no-sandbox and the PDF-mirroring config rendered 2 of 2 Mermaid diagrams"
```

## question-copy-routes

```yaml
anchor: |-
  `y` (outside input mode) always opens the panel
question: |-
  How does y behave before and after the proposal, including while typing?
illustrates: |-
  Outside input mode, y opens the copy panel and yy copies the whole batch, while y remains ordinary typing in an answer or note.
caption: The proposed chooser preserves ordinary typing and the copy-all chord while adding a current-question snippet route; copying never answers.
review: "465.634x735 px, fit 100.0%; question, source-trace, and visual checks passed; two look rounds, two revisions"
```

```mermaid
---
title: "How does y change in the questions gate?"
config:
  layout: dagre
  flowchart:
    rankSpacing: 12
    nodeSpacing: 8
    padding: 8
    wrappingWidth: 160
---
flowchart LR
  subgraph PROPOSAL["Proposed: press y"]
    direction TB
    PQ{{"`**Typing?**`"}}
    PT["`**Type y**<br/>Text input`"]
    PP["`**Copy palette**<br/>Select target`"]
    PA["`**All Q&A**<br/>Whole batch`"]
    PS["`**Copy snippet**<br/>Active question`"]
    PQ -.->|Yes| PT
    PQ -.->|No| PP
    PP -.->|"y again"| PA
    PP -.->|"snippet key"| PS
  end
  subgraph TODAY["Today: press y"]
    direction TB
    TQ{{"`**Typing?**`"}}
    TT["`**Type y**<br/>Text input`"]
    TA["`**All Q&A**<br/>Whole batch`"]
    TQ -->|Yes| TT
    TQ -->|No| TA
  end
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class TQ,PQ decision
  class TT,PT,PP focus
  class TA,PA,PS outcome
  class PQ,PT,PP,PA,PS proposed
  style TODAY fill:none,stroke:#3B78C2
  style PROPOSAL fill:none,stroke:#3B78C2,stroke-dasharray:5 3
```

## strict-input-tolerant-history

```yaml
anchor: |-
  normalizer; tolerant at display so malformed historical metadata never breaks the
question: |-
  How can new copy metadata be strict while historical questions remain usable?
illustrates: |-
  Strict submission validation reports indexed errors before the handoff, while tolerant display keeps historical questions usable and reports unavailable items instead of guessing values.
caption: Reject malformed new metadata before handoff; keep historical questions usable and never copy guessed or truncated values.
review: "512.851x868 px, fit 100.0%; question, source-trace, and visual checks passed; two look rounds, two revisions"
```

```mermaid
---
title: "Proposed: strict submissions, tolerant historical display"
config:
  layout: dagre
  flowchart:
    rankSpacing: 12
    nodeSpacing: 8
    padding: 8
    wrappingWidth: 165
---
flowchart LR
  subgraph OLD["Historical copy metadata"]
    direction TB
    H["`**Tolerant display**<br/>History`"]
    HQ{{"`**Item usable?**`"}}
    SHOW["`**Offer item**<br/>Exact value`"]
    BAD["`**Unavailable**<br/>Question stays`"]
    H -.->|"inspect"| HQ
    HQ -.->|Yes| SHOW
    HQ -.->|No| BAD
  end
  subgraph NEW["New copy metadata"]
    direction TB
    N["`**Core normalizer**<br/>Strict`"]
    NQ{{"`**Metadata valid?**`"}}
    OK["`**Accept entries**<br/>Copy text`"]
    ERR["`**Indexed error**<br/>No handoff`"]
    N -.->|"validate"| NQ
    NQ -.->|Yes| OK
    NQ -.->|No| ERR
  end
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class N,H,ERR,BAD focus
  class NQ,HQ decision
  class OK,SHOW outcome
  class N,H,NQ,HQ,OK,ERR,SHOW,BAD proposed
  style NEW fill:none,stroke:#3B78C2,stroke-dasharray:5 3
  style OLD fill:none,stroke:#3B78C2,stroke-dasharray:5 3
```
