# Diagram proposals: Fast Video Artifacts in the tmux Pane: Consolidated Findings and Recommendation

Proposals for the swarm linker, not a report. Each diagram restates only what the source
report says.

```yaml
source: research:202611/fast_video_artifact_pane/fast_video_artifact_pane__final.md
producer: research.54.image
check: "mmdc 12.0.0 with the PDF-mirroring config rendered 2 of 2 Mermaid diagrams; Puppeteer --no-sandbox"
```

## title-redraw

```yaml
anchor: |-
  tmux's `input_exit_apc()` calls `screen_set_title()` on **every** APC
question: |-
  Why does invisible video slow the tmux session?
illustrates: |-
  Unwrapped kitty graphics become pane-title changes that trigger SASE border redraws over SSH, so other panes degrade while no video graphics reach the client.
caption: "Unwrapped kitty graphics become pane titles, so SASE redraws borders while no video reaches the terminal."
review: "630.836×942 px, fit 94.8%; question, source trace, labels, arrows and visual checks passed; 1 revision"
```

```mermaid
---
title: "Why does invisible video slow tmux?"
config:
  flowchart:
    rankSpacing: 12
    nodeSpacing: 12
    wrappingWidth: 260
---
flowchart TD
  MPV["`**mpv 0.40**<br/>Unwrapped graphics escapes`"]
  PARSER["`**tmux parser**<br/>Consumes each graphics escape`"]
  TITLE["`**Pane title**<br/>Replaced with graphics payload`"]
  BLANK["`**Client terminal**<br/>Receives zero graphics escapes`"]
  BORDER["`**SASE border redraws**<br/>Displays the changing pane title`"]
  LAG["`**Session-wide lag**<br/>Other panes degrade too`"]
  MPV -->|sends graphics escapes| PARSER
  PARSER -->|sets title| TITLE
  PARSER -->|consumes instead of forwarding| BLANK
  TITLE -->|triggers redraw for every chunk| BORDER
  BORDER -->|repeated redraws over SSH| LAG
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef risk fill:#FDECEC,stroke:#C0392B,stroke-width:1.5px,color:#5F1414
  class MPV,PARSER focus
  class TITLE,BLANK,BORDER,LAG risk
```

## animation-ownership

```yaml
anchor: |-
  frames onto one reused image ID, played by kitty in loading mode;
question: |-
  What crosses SSH, and why is replay almost free?
illustrates: |-
  The proposed streamer carries frame messages and priority controls through a shared paced writer while kitty plays client-side and replays without new frame uploads.
caption: "Proposed: SASE sends paced frames and priority controls; kitty reuses uploaded frames for replay and looping."
review: "614.07×1138 px, fit 78.5%; question, source trace, labels, arrows and visual checks passed; 2 revisions"
```

```mermaid
---
title: "Proposed: what crosses SSH during animation?"
config:
  flowchart:
    rankSpacing: 12
    nodeSpacing: 12
    wrappingWidth: 260
---
flowchart TD
  subgraph REMOTE["Remote host — proposed viewer"]
    FFMPEG["`**ffmpeg**<br/>Budgeted size and frame rate`"]
    ENCODE["`**SASE frame encoder**<br/>Dirty rectangles, zlib, base64`"]
    KEYS["`**SASE playback keys**<br/>Pause, seek, step, replay`"]
    WRITER["`**Paced writer**<br/>Only 2–3 seconds ahead`"]
    TMUX["`**tmux**<br/>Wrapped animation chunks`"]
    FFMPEG -.->|decoded frames| ENCODE
    ENCODE -.->|frame messages| WRITER
    KEYS -.->|tiny controls, queue priority| WRITER
    WRITER -.->|frames and controls| TMUX
  end
  subgraph CLIENT["Client terminal — proposed playback"]
    direction LR
    KITTY["`**Kitty animation**<br/>Plays while frames arrive`"]
    REPLAY["`**Replay and loop**<br/>Reuse uploaded frames locally`"]
    KITTY -.->|after the first pass| REPLAY
  end
  TMUX -.->|SSH: frames and controls| CLIENT
  classDef focus fill:#E8F1FB,stroke:#3B78C2,stroke-width:1.5px,color:#0F2E52
  classDef outcome fill:#E7F5EC,stroke:#2E7D4F,stroke-width:1.5px,color:#123D24
  classDef proposed stroke-dasharray:5 3
  class FFMPEG,ENCODE,KEYS,WRITER,TMUX focus
  class KITTY,REPLAY outcome
  class FFMPEG,ENCODE,KEYS,WRITER,TMUX,KITTY,REPLAY proposed
  style REMOTE fill:none,stroke:#3B78C2
  style CLIENT fill:none,stroke:#2E7D4F
```
