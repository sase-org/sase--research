# Diagram proposals: Claude Design alongside `#research_swarm` for SASE UX

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202610/claude_design_alongside_research_swarms/claude_design_alongside_research_swarms__final.md
producer: research.5a.image
check: "mmdc 12.0.0 with the PDF-mirroring config rendered 2 of 2 Mermaid diagrams"
```

## mockup-proof

```yaml
anchor: |-
  panel at 120×40, and compare it with a `sase screenshot` PNG.
question: |-
  What does a successful redraw establish, and what still needs real Textual proof?
illustrates: |-
  A Claude Design TUI artboard specifies intent, while a Textual prototype plus sase screenshot and the goldens still proves that the design can be built.
caption: A faithful canvas redraw establishes visual intent; a real Textual prototype, screenshots, and goldens still have to prove buildability.
review: "519.875x916 px, fit 97.5%; question, source trace, labels, arrows, and visual checks passed; 1 revision, 2 visual reviews"
```

```mermaid
---
title: "What does a faithful terminal mockup prove?"
config:
  flowchart:
    rankSpacing: 12
    nodeSpacing: 12
    wrappingWidth: 260
---
flowchart TD
  REDRAW["`**Design redraw**<br/>Existing screen, 120×40`"]
  MATCH{{"`**Matches the real terminal?**`"}}
  UNREADY["`**System unfinished**<br/>Not ready to trust`"]
  INTENT["`**Intent only**<br/>Hierarchy, grouping, density`"]
  REAL["`**Textual prototype**<br/>Real terminal implementation`"]
  PROOF["`**Buildability evidence**<br/>Confirmed in real renders`"]
  REDRAW -->|Compare with sase screenshot| MATCH
  MATCH -->|No| UNREADY
  MATCH -->|Yes| INTENT
  INTENT -->|Still requires| REAL
  REAL -->|Check screenshots + goldens| PROOF
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  class REDRAW,INTENT,REAL focus
  class MATCH,UNREADY decision
  class PROOF outcome
```

## human-design-handoff

```yaml
anchor: |-
  design brief. You resolve the brief in a canvas session, and a follow-up agent picks
question: |-
  How can a human canvas session fit between SASE turns without an agent waiting?
illustrates: |-
  A swarm or agent ends its turn with a design brief, a human resolves it in a canvas session, and a follow-up agent picks up the exports from the research directory.
caption: SASE turns end before human canvas work; saved exports and a decision log carry the result into a follow-up turn.
review: "692.5x586 px, fit 94.3%; question, source trace, labels, arrows, and visual checks passed; 1 revision, 2 visual reviews"
```

```mermaid
---
title: "How does Design fit between SASE turns?"
config:
  sequence:
    actorMargin: 20
    width: 110
    height: 45
    messageMargin: 25
    noteMargin: 10
---
sequenceDiagram
  autonumber
  participant FIRST as First SASE<br/>agent turn
  participant HUMAN as Human<br/>canvas session
  participant REPO as Research<br/>repository
  participant NEXT as Follow-up<br/>agent turn
  FIRST->>HUMAN: Design brief
  Note over FIRST: Turn ends
  HUMAN->>HUMAN: Resolve the brief
  HUMAN->>REPO: Export artboards
  HUMAN->>REPO: Commit<br/>decision log
  NEXT->>REPO: Pick up exports<br/>(any provider)
```

