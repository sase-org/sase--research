# Diagram proposals: Ending gate, plan, and monitor turns through host completion

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202610/staged_handoffs_through_host_completion/staged_handoffs_through_host_completion__final.md
producer: research.5f.image
check: "mmdc 12.0.0 with the PDF-mirroring config rendered 1 of 1 Mermaid diagrams"
```

## monitor-finalization-race

```yaml
anchor: |-
  A monitor spawned at CLI time could run
question: |-
  Why must a monitor start after finalization?
illustrates: |-
  Staging a monitor and spawning it after finalization keeps `just check` from running while the commit finalizer's `just fix` hook rewrites files.
caption: Starting the monitor after finalizers settle prevents its check from racing the commit hook's file rewrites.
review: "562x759.5 px, fit 100%; question and visual checks passed; 1 visual revision in 2 look rounds; 1 syntax repair"
```

```mermaid
---
title: "Why delay monitor startup?"
accTitle: "Rejected early monitor startup and proposed delayed startup"
accDescr: "Starting a monitor at CLI time lets just check read the same files that the host's just fix hook may be rewriting. In the proposal, the agent stages the monitor, the host settles finalizers, then it starts the monitor against the final tree."
config:
  sequence:
    actorMargin: 22
    diagramMarginX: 8
    diagramMarginY: 12
    messageMargin: 25
    noteMargin: 10
    width: 120
    wrap: true
    mirrorActors: false
---
sequenceDiagram
  autonumber
  participant A as Agent CLI
  participant H as Host
  participant M as Monitor
  participant T as Working tree
  Note over A,T: Rejected: spawn at CLI time
  A->>M: Spawn monitor
  par Can overlap
    M->>T: just check reads files
  and Commit finalization
    H->>T: just fix rewrites files
  end
  Note over A,T: Proposed: spawn after finalizers settle
  A-->>H: Stage, then finish via /sase_final
  H-->>T: just fix before commit
  Note over H: Finalizers settle
  H-->>M: Spawn monitor
  M-->>T: just check reads final tree
```
