# Diagram proposals: On-demand memory web rosters: consolidated research and recommended design

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/on_demand_web_rosters/on_demand_web_rosters__final.md
producer: research.6e.image
check: mmdc 12.0.0 (--no-sandbox) with the PDF-mirroring config rendered 2 of 2 Mermaid diagrams
```

## selector-routing

```yaml
anchor: |-
  Bare-web guard per §3.5, with `-a/--all-strands` added to `read` and `show`.
question: |-
  Which content does a read return, and when is an accidental full-web dump refused?
illustrates: |-
  The roster selector returns the catalog without strand bodies, while the bare-web guard refuses on-demand full-web reads without --all-strands.
caption: Bare web reads return all strand bodies for either always-loaded webs or an explicit --all-strands request;
  roster selectors return the catalog.
review: 810.448x808 px, fit 80.5%; question, visual and source checks passed; 1 revision
```

```mermaid
---
title: "Proposed: what does a memory read return?"
accTitle: "Proposed memory selector routing and bare-web guard"
accDescr: "Roster selectors return summaries; strand selectors return selected records. A bare web returns all strand bodies only if loading is always or the all-strands flag is present. Otherwise the read is refused before audit or output."
config:
  flowchart:
    rankSpacing: 16
    nodeSpacing: 12
    wrappingWidth: 150
---
flowchart TD
  SELECT{{"`**Selector?**`"}}
  ROSTER["`**Roster only**<br/>Titles and summaries`"]
  STRAND["`**Selected record**<br/>Strand body`"]
  MODE{{"`**On-demand loading?**`"}}
  FLAG{{"`**--all-strands passed?**`"}}
  ALL["`**Full web read**<br/>Every strand body`"]
  REFUSE["`**Refused**<br/>Before audit or output`"]
  SELECT -.->|"roster:web"| ROSTER
  SELECT -.->|"web:keyword"| STRAND
  SELECT -.->|"bare web"| MODE
  MODE -.->|"No: always"| ALL
  MODE -.->|"Yes"| FLAG
  FLAG -.->|"Yes"| ALL
  FLAG -.->|"No"| REFUSE
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  class SELECT,MODE,FLAG decision
  class ROSTER,STRAND,ALL focus
  class REFUSE risk
```

## audit-compatibility

```yaml
anchor: |-
  shrinks the change to pure Python, and the MEMORY lane renders it correctly today.
question: |-
  Why can v1 surface roster reads without upgrading the Rust audit reader?
illustrates: |-
  Schema-v3 web events use the existing MEMORY lane, whereas a new roster kind requires sase-core to land first to avoid silently dropped reads.
caption: Reusing schema v3 avoids the Rust-reader dependency; a new roster kind must wait for a reader upgrade.
review: 748x635 px, fit 87.3%; question, visual and source checks passed; 1 revision
```

```mermaid
---
title: "Why reuse schema v3 for roster reads?"
accTitle: "Proposed v1 compatibility and deferred v2 dependency"
accDescr: "The proposed schema-v3 web event is recognized by the current Rust reader and displayed in the MEMORY lane. A future schema-v4 roster event is silently dropped unless the Rust reader has been upgraded first."
config:
  flowchart:
    rankSpacing: 16
    nodeSpacing: 14
    wrappingWidth: 150
---
flowchart TB
  subgraph V2["Deferred v2"]
    NEW["`**Schema v4**<br/>kind = roster`"]
    UPDATED{{"`**Reader upgraded first?**`"}}
    DROP["`**Silently dropped**<br/>Unknown encoding`"]
    RECOGNIZED["`**New kind accepted**<br/>Requires sase-core update`"]
    NEW -.->|"read event"| UPDATED
    UPDATED -.->|"No"| DROP
    UPDATED -.->|"Yes"| RECOGNIZED
  end
  subgraph V1["Proposed v1"]
    WEB["`**Schema v3**<br/>kind = web`"]
    CURRENT["`**Rust reader**<br/>Existing; accepts encoding`"]
    MEMORY["`**MEMORY lane**<br/>Shows roster:decisions`"]
    WEB -.->|"read event"| CURRENT
    CURRENT -.->|"surfaces in"| MEMORY
  end
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  class WEB,CURRENT,MEMORY,NEW,RECOGNIZED focus
  class UPDATED decision
  class DROP risk
  style V1 fill:none,stroke:#3B78C2
  style V2 fill:none,stroke:#C77C02
```
