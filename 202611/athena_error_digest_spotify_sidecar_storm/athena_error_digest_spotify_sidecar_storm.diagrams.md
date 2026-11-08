# Diagram proposals: Athena error digests: a half-onboarded `sase-spotify` project in a retry loop with no backoff

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/athena_error_digest_spotify_sidecar_storm/athena_error_digest_spotify_sidecar_storm__final.md
producer: research.3n.image
check: "mmdc 12.0.0 with Puppeteer --no-sandbox and the PDF-mirroring config rendered 1 of 1 Mermaid diagrams"
```

## connected-without-protection

```yaml
anchor: |-
  So **"connected" and "has every required capability" are different states.**
question: |-
  Why can sidecar sync report OK while artifact cleanup refuses to delete?
illustrates: |-
  The legacy `--sdd` store is connected for sidecar sync but lacks the `beads` and `plans` roles required for retention protection.
caption: "The legacy store passes sync's connection check but lacks retention's required protection roles, so an OK sync result does not make pruning safe."
review: "714.455x751 px, fit 91.4%; named-question, source-trace, labels, arrowheads and visual checks passed; 1 revision"
```

```mermaid
---
title: "Why can sync be OK while pruning refuses?"
accTitle: "Connection does not prove protection coverage"
accDescr: "The same legacy combined store passes sidecar sync's connection check but fails retention's required beads and plans role check. Sync skips auto-connect and reports OK with two missing roles; pruning refuses without protection."
config:
  flowchart:
    rankSpacing: 18
    nodeSpacing: 24
    wrappingWidth: 220
---
flowchart TB
  LEGACY["`**Legacy --sdd**<br/>Combined store record`"]
  subgraph SYNC["Sidecar sync: connection check"]
    CONNECTED{{"`**Store connected?**`"}}
    SKIP["`**Auto-connect skipped**<br/>Already connected`"]
    OK["`**Observed sync result**<br/>OK with missing=2`"]
    CONNECTED -->|"Yes: separate_repo record"| SKIP
    SKIP -->|"observed heartbeat"| OK
  end
  subgraph RETENTION["Artifact retention: protection check"]
    ROLES{{"`**Beads and plans present?**`"}}
    REFUSE["`**Prune refuses**<br/>Protection unavailable`"]
    ROLES -->|"No: --sdd matches neither role"| REFUSE
  end
  LEGACY -->|"connection interpretation"| SYNC
  LEGACY -->|"protection interpretation"| RETENTION
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef decision fill:#FFF7E6,stroke:#C77C02,stroke-width:1.5px,color:#4A3000
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  class LEGACY,SKIP,OK focus
  class CONNECTED,ROLES decision
  class REFUSE risk
  style SYNC fill:none,stroke:#3B78C2
  style RETENTION fill:none,stroke:#C0392B
```
