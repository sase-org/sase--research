# Diagram proposals: Why sase-core CI keeps going red, and the hook that would actually stop it

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202610/sase_core_ci_red_recurrence_and_landing_gate/sase_core_ci_red_recurrence_and_landing_gate__final.md
producer: research.5g.image
check: "mmdc 12.0.0 with the PDF-mirroring config rendered 1 of 1 Mermaid diagrams"
```

## landing-gate-decision

```yaml
anchor: |-
  In sase-core's `sase/sase.yml`, set `commit_hooks.before` to a script. A sketch:
question: |-
  How does the proposed landing gate decide to allow or refuse a commit?
illustrates: |-
  The proposed landing gate accepts a covering pass receipt or runs the cheapest
  checks followed by the full check, refusing failed landings while preserving
  work for repair.
caption: "The proposed gate accepts matching pass receipts within two hours; otherwise checks must pass, and failures preserve work for repair."
review: "535.891×940 px, fit 95.0%; question and visual checks passed; 0 revisions; converging paths are alternatives"
```

```mermaid
---
title: "Proposed landing gate: receipt or fresh checks?"
accTitle: "The proposed sase-core gate's decision paths"
accDescr: "After formatting, a valid exact-tree, same-machine, two-hour pass receipt permits the commit. Otherwise cheap checks precede the full check. Any failure preserves work for repair. Dashed paths are proposed alternatives, not simultaneous requirements."
config:
  flowchart:
    rankSpacing: 22
    nodeSpacing: 24
    wrappingWidth: 220
---
flowchart TD
  FORMAT["`**Format**<br/>Run just fmt`"]
  RECEIPT{{"`**Valid pass receipt?**`"}}
  FAST["`**Cheap checks**<br/>Formatting and feature consistency`"]
  FULL["`**Full sase-core check**<br/>Run sase tool run check`"]
  ALLOW["`**Allow commit**`"]
  REPAIR["`**Refuse landing**<br/>Preserve work; hand to repair`"]
  FORMAT -.->|"format succeeds"| RECEIPT
  FORMAT -.->|"fails"| REPAIR
  RECEIPT -.->|"Yes: same tree,<br/>machine, within 2h"| ALLOW
  RECEIPT -.->|"No"| FAST
  FAST -.->|"Pass"| FULL
  FAST -.->|"Fail"| REPAIR
  FULL -.->|"Pass"| ALLOW
  FULL -.->|"Fail"| REPAIR
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  classDef proposed stroke-dasharray:5 3
  class FORMAT,RECEIPT,FAST,FULL decision
  class ALLOW outcome
  class REPAIR risk
  class FORMAT,RECEIPT,FAST,FULL,ALLOW,REPAIR proposed
```
