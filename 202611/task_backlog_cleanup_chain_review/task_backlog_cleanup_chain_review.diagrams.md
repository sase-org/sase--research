# Diagram proposals: The Five-Epic Task-Backlog Cleanup Chain

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/task_backlog_cleanup_chain_review/task_backlog_cleanup_chain_review__final.md
producer: research.30.image
check: "mmdc 12.0.0 with Puppeteer --no-sandbox and the PDF-mirroring config rendered 1 of 1 Mermaid diagrams"
```

## host-specific-deferral

```yaml
anchor: |-
  Landers for epics 1–3 deferred it because it passed on athena.
question: |-
  How did a known Apollo failure wait until epic 5 for a fix?
illustrates: |-
  Landers for epics 1–3 deferred the known Apollo prompt-render failure because it passed on athena, until epic 4 reproduced it on Apollo and epic 5 shipped the fix.
caption: "Passing on athena delayed a known Apollo failure across three landings; epic 4 reproduced it, and epic 5 shipped the fix."
review: "531.5×531 px, fit 100.0%; question, source trace, labels, arrowheads, and visual checks passed; 1 revision after the initial title clipped"
```

```mermaid
---
title: "Why was Apollo deferred?"
accTitle: "Host-specific evidence deferred across three cleanup landings"
accDescr: "The epic 1 plan records a known Apollo failure. Landers for epics 1 through 3 defer it because it passes on athena. Epic 4 reproduces it on Apollo; the hosts return ties in opposite order. Epic 5 ships the fix."
config:
  sequence:
    diagramMarginX: 8
    diagramMarginY: 8
    actorMargin: 24
    width: 120
    height: 42
    boxMargin: 6
    noteMargin: 8
    messageMargin: 25
    mirrorActors: false
---
sequenceDiagram
  autonumber
  participant L as Landers<br/>(review agents)
  participant A as athena
  participant P as apollo
  Note over L,P: Epic 1 plan: re-check<br/>the known Apollo failure
  loop Landings 1–3
    L->>A: Check prompt rendering
    A-->>L: Passes
    Note over L,A: Cluster deferred
  end
  L->>P: Landing 4: reproduce
  P-->>L: Failure reproduced
  Note over A,P: Tied files appear<br/>in opposite orders
  Note over L,P: Epic 5 ships the fix
```
