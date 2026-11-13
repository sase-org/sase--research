# Diagram proposals: Google Argon and Hydrogen support in SASE — consolidated research

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/argon_hydrogen_completion_and_swarm/argon_hydrogen_completion_and_swarm__final.md
producer: research.4k.image
check: "mmdc 12.0.0 with the PDF-mirroring config rendered 1 of 1 Mermaid diagrams; Puppeteer --no-sandbox; broken-chart control exited nonzero"
```

## effort-routing

```yaml
anchor: |-
  SASE's adapter still passes an empty supported-effort map
question: |-
  Why does SASE reject effort that agy supports?
illustrates: |-
  SASE's adapter rejects `@effort` before launch, while slug variants work today and
  upstream `agy` supports base slugs with `--effort`.
caption: "SASE rejects @effort before launch; encode effort in the model slug, even though Antigravity’s CLI accepts --effort directly."
review: "652.953×812 px, fit 100.0% rounded; question, source trace, and visual checks passed; 1 revision across 2 look rounds"
```

```mermaid
---
title: "Why does SASE reject effort that agy supports?"
config:
  flowchart:
    rankSpacing: 24
    nodeSpacing: 18
    wrappingWidth: 260
---
flowchart TB
  subgraph SASE["SASE adapter — current behavior"]
    SLUG["`**Slug effort**<br/>agy/gemini-4-hydrogen-xhigh`"]
    SUFFIX["`**Explicit effort**<br/>agy/gemini-4-hydrogen@xhigh`"]
    REJECT["`**Rejected before launch**<br/>Empty supported-effort map`"]
    SUFFIX -->|"rejects @effort"| REJECT
  end
  subgraph AGY["Antigravity CLI (agy)"]
    DIRECT["`**Direct CLI call**<br/>Base slug + --effort xhigh`"]
    RUN["`**Hydrogen at xhigh**<br/>Either route is supported`"]
    DIRECT -->|"accepts --effort"| RUN
  end
  SLUG -->|"accepts suffixed slug"| RUN
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  class SLUG,SUFFIX,DIRECT focus
  class RUN outcome
  class REJECT risk
  style SASE fill:none,stroke:#3B78C2
  style AGY fill:none,stroke:#2E7D4F
```
