# Diagram proposals: Footprint: a usage census for finding what sase should delete

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202610/footprint_feature_usage_tracking/footprint_feature_usage_tracking__final.md
producer: research.2p.image
check: "mmdc 12.0.0 with Puppeteer --no-sandbox and the PDF-mirroring config rendered 1 of 1 Mermaid diagrams"
```

## export-privacy-boundary

```yaml
anchor: |-
  The local ledger is detailed: daily, exact counts, and your own
question: |-
  What must happen before local usage data can leave in a future upload?
illustrates: |-
  The Rust-owned export projection coarsens the local ledger, keeps reviews and private detail local, and sends only previewed bytes from data collected after consent.
caption: The proposed export narrows local detail, previews exact bytes, and permits upload only with sharing enabled and data collected after consent.
review: "702.164x917 px, fit 93.0%; question and visual checks passed; 1 revision; batch 1 of 1; broken-input rejection passed"
```

```mermaid
---
title: "Proposed: what can leave in a usage upload?"
accTitle: "Footprint local-to-upload privacy boundary"
accDescr: "A local daily ledger retains review decisions and other local-only detail. Rust projects counts into a coarse weekly pack, previewed byte for byte. Upload is optional and allowed only while sharing is enabled and for data collected after consent."
config:
  flowchart:
    rankSpacing: 10
    nodeSpacing: 14
    wrappingWidth: 260
---
flowchart TB
  subgraph LOCAL["On your machine — proposed"]
    LEDGER["`**Daily ledger**<br/>Exact counts; own names`"]
    PRIVATE["`**Stays local**<br/>Reviews, options, config`"]
    PACK["`**Rust export**<br/>Weekly buckets; approved IDs`"]
    PREVIEW["`**Preview**<br/>Exact outgoing bytes`"]
    ELIGIBLE{{"`**Share on; post-consent data?**`"}}
    LEDGER -.->|"retain detail"| PRIVATE
    LEDGER -.->|"coarsen; no stable ID"| PACK
    PACK -.->|"inspect"| PREVIEW
    PREVIEW -.->|"check upload eligibility"| ELIGIBLE
  end
  ELIGIBLE -.->|"No"| STOP
  STOP["`**No upload**<br/>History stays private`"]
  SERVER["`**Future server**<br/>Receives previewed bytes`"]
  ELIGIBLE -.->|"Yes: optional upload"| SERVER
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef muted fill:#F3F4F6,stroke:#6B7280,stroke-width:1.5px,color:#1F2937
  classDef proposed stroke-dasharray:5 3
  class LEDGER,PACK,PREVIEW,SERVER focus
  class PRIVATE,STOP muted
  class ELIGIBLE decision
  class SERVER proposed
  style LOCAL fill:none,stroke:#3B78C2
```
