# Fast Video Artifacts in the tmux Pane: Consolidated Findings and Recommendation

- **Date:** 2026-11-17
- **Question:** Opening a video artifact in a separate tmux pane (Agents tab, `a` keymap,
  pick a video) is "incredibly slow". What is the best way to make it much faster? Is the
  plan sound, and should the requirements change?
- **Inputs:** five independent researcher reports (`__cdx`, `__cld`, `__grk`, `__mus`,
  `__gem`, in this directory) plus lead-researcher verification on apollo. Code facts
  refer to sase `master` at `ea7916d7a7`.

---

## TL;DR

1. **The current path is broken under tmux, not merely slow.** `mpv --vo=kitty` (0.40 on
   athena) emits raw kitty APC escapes with no tmux passthrough wrapping. tmux's parser
   consumes every APC string as a *pane-title change*, so **zero video pixels ever reach
   the terminal**. SASE's own pane decoration renders `#{pane_title}` in the border, so
   every 4 KB chunk of invisible video also forces a border redraw over SSH. Measured
   (cld, athena): a 6 s clip took **47 s** to "play" with nothing displayed. Verified
   independently by the lead on apollo's tmux 3.4: a raw `ESC _G…` APC in an isolated
   tmux server set `pane_title` to the payload. This, plus ~1.2 s of fixed launch
   overhead, is the "incredibly slow" experience.
2. **mpv's kitty output cannot be repaired for a remote tmux pane.** `vo_kitty.c` sends
   every frame as uncompressed base64 RGB24 (no zlib `o=z`, no PNG, no delta frames, no
   `c=/r=` scale-to-cells), ~5 MB per frame at a half-screen Retina pane — ≈130 MB/s at
   25 fps, a **~1,400× inflation** over the source H.264 bytes. tmux passthrough tops out
   near 50 MB/s on localhost (~9.6 fps at that frame size); a 100 Mbps link gives 2.4 fps.
   And in mpv ≥ 0.41's passthrough mode, frame positioning goes to the outer terminal in
   *window* coordinates, so in a split pane the video draws over the wrong pane. Flag
   tuning is a dead end for this topology. mpv also isn't installed on apollo at all
   (`missing_mpv` hard failure today).
3. **Consensus fix, in phases:** (0) hotfix — under tmux, stop launching mpv; show a
   poster/contact sheet plus metadata through the already-working `kitten icat` image
   path, and add a pty+tmux regression probe; (1) remove the ~1–1.2 s launch tax (pass
   resolved config to the child, lazy imports, off-thread tmux decoration);
   (2) make the pane an **inspect-first scrubber** (frame 0 + keyframe storyboard,
   frame-step/jump keys, `z` zoom, `o` native open) with motion on demand;
   (3, gated) a SASE-owned **streaming kitty-animation player** for in-pane motion over
   SSH — two independent prototypes measured it at **~100–230× fewer bytes** than mpv
   with a ~0.3–0.5 s first frame — built only after a cheap rendering spike on the real
   Mac kitty and after the scrubber proves insufficient on its own. Keep mpv as an
   opt-in backend for local, non-tmux, full-fidelity/audio use.

---

## 1. What actually runs today

The pipeline (all five reports agree; paths relative to the sase repo root):

1. Agents-tab `a` → `action_open_artifact_files`
   (`src/sase/ace/tui/actions/agents/_panel_artifact_actions.py`) → selection modal →
   `_open_artifact_files` (`_panel_artifact_open.py`). Byte-free VCS rows are
   materialized off-thread first (unbounded, size-dependent; no progress UI).
2. `view_…_in_tmux_pane` (`src/sase/ace/tui/graphics/_viewer_tmux.py`) runs
   `tmux split-window -h … python -m sase.ace.tui.graphics.viewer`, then decorates the
   pane: ~13 sequential synchronous `tmux` subprocess calls **on Textual's UI thread**
   (`_viewer_tmux_decoration.py`, `_panel_artifact_pane.py`), including
   `pane-border-status top` with a `#{pane_title}` border format.
3. The pane cold-starts a fresh interpreter. `viewer.py` eagerly imports
   `sase.attachments.markdown_pdf` even for a single `.mp4`.
4. The sequence loop calls `load_artifact_video_playback_config()` →
   `load_merged_config()` — a full merged-config reload in the child on every open.
5. `display_video_artifact` (`_viewer_loop_media.py`) runs `subprocess.run(["clear"])`,
   prints a header, and blocks on:

   ```text
   mpv --no-config --vo=kitty --keep-open=yes
       --vo-kitty-alt-screen=no --vo-kitty-config-clear=no
       --vo-kitty-left=… --vo-kitty-top=… --vo-kitty-cols=… --vo-kitty-rows=…
       --mute=yes -- <path>
   ```

   Config: `ace.artifact_file_viewer.video` (`audio: false`, `loop: false`,
   `vo: kitty`, `extra_mpv_args: []`). `--no-config` means none of mpv's documented
   kitty-VO performance flags are active. Without mpv the viewer hard-fails with
   `missing_mpv` (`_viewer_render.py:154`).

Notes that bound the solution space:

- Video **bypasses** the PDF/image page renderer — there is no PNG preprocessing stage
  to optimize (cdx).
- The in-TUI file panel renders videos as a `▶ video … use the view key to play` text
  placeholder (`widgets/file_panel/_display.py`), so the tmux pane is the **only** way
  to see any frame — which is why its failure is the whole product failure (grk).
- The direct `sase artifact open` CLI path is already lean (no pane, no wrapper); leave
  it alone (mus).
- The original design tale (plans sidecar, `202607/video_artifact_preview.md`) assumed
  "mpv speaks the kitty protocol itself" and listed "mpv kitty-vo under tmux passthrough
  is the main unknown" as its top risk, with "verify in a real tmux pane first" as step
  1. That verification evidently did not happen in the real topology (cld).

### Environment that matters

| Piece | Fact | Confidence |
| --- | --- | --- |
| TUI home | athena (or apollo) inside tmux, reached from a Mac over Tailscale SSH | High (chezmoi, SSH env) |
| mpv | **0.40.0 on athena; not installed on apollo or the Mac** | Verified (cld on athena; lead on apollo) |
| tmux | 3.5a on athena, 3.4 on apollo/Mac; `allow-passthrough all` configured | Verified |
| Terminal | kitty 0.47.0 on the Mac; `kitten` present on apollo/athena | Verified (cld); apollo verified by lead |
| ffmpeg/ffprobe | Installed on apollo (6.1.1) and athena | Verified |
| Typical artifacts | Screen recordings (2560×1548@30, ~7 s) and TUI demos (1920×1080@25, 20–30 s), 0.6–5.8 MB H.264 | High (ffprobe over real artifacts; cld, gem) |

---

## 2. Root causes (measured, strongest-evidence versions)

### 2.1 Under tmux, nothing renders and the session drags — CONFIRMED twice

mpv 0.40 writes `ESC _G a=T,f=24,…;<base64> ESC \` with no `ESC Ptmux;` wrapper
(`--vo-kitty-auto-multiplexer-passthrough` only exists from 0.41, default off, and SASE
never passes it). tmux's `input_exit_apc()` calls `screen_set_title()` on **every** APC
string — this path does not even check `allow-set-title` — then fires title-changed
hooks and border/status redraws (tmux `input.c`, cld).

- cld, athena (tmux 3.5a, pty harness as the tmux client): 6 s of a demo clip took
  **47.3 s** with SASE's border decoration, **7.2 s** without it; **0 kitty APC bytes**
  reached the client in both cases; the pane title ended as base64 garbage.
- Lead verification, apollo (tmux 3.4, isolated `tmux -L` server):
  `printf '\033_Ga=T,f=24,s=1,v=1;QUJDREVG\033\\'` left
  `pane_title=[Ga=T,f=24,s=1,v=1;QUJDREVG]`. Same mechanism, both tmux versions.

One researcher (gem) described tmux as "dropping" unwrapped APC; the title-change
mechanism is the correct one, and it is worse than dropping because SASE's
`#{pane_title}` border format turns each chunk into a redraw.

So today's experience on athena is: ~1.2 s of launch tax, then a pane that shows only
the header while mpv pumps megabytes of invisible escapes through tmux at ~8× real time,
degrading every other pane. On apollo it is a `missing_mpv` error. Both are broken.

### 2.2 Even "fixed", mpv's kitty VO is the wrong transport for remote tmux

From mpv source (`video/out/vo_kitty.c`) and measurements (cld, gem, cdx — independent
and consistent):

- **Uncompressed RGB24 + base64**, 4 KB chunks. No `o=z` zlib, no PNG, no delta frames.
  Payload ≈ `width × height × 4 × fps` bytes/s: ~5.2 MB/frame at a 1520×855 pane,
  **121–133 MB/s** measured locally at full rate; gem measured **891 MB** for one 7.5 s
  clip (vs 0.64 MB of source H.264 — ~1,384× inflation).
- **The frame size is the pane's pixel size.** `--vo-kitty-cols/rows` only affect cursor
  math; SASE's existing flags do not shrink frames. Capping `--vo-kitty-width/height`
  shrinks the *displayed* picture instead, because `vo_kitty` never emits `c=/r=`
  scale-to-cells placement (all three reports agree; contradicts "we already fit the
  pane" intuitions).
- **tmux ceiling:** synthetic frames in mpv's wire format passed through tmux at
  ~50 MB/s on localhost (9.6 fps at that frame size) vs 133 MB/s without tmux. tmux
  marks passthrough output `TTY_NOBLOCK` and never discards it, so a video queues
  unbounded data ahead of every pane's redraws, including the SASE TUI itself (cld).
- **Throttled links stall rather than drop:** 2.4 fps at ~100 Mbps (6 s clip → 32 s),
  0.6 fps at ~25 Mbps (→ >120 s). mpv 0.40 writes synchronously; keypresses queue
  behind megabytes of pixels (cld, measured).
- **Placement bug in the "fixed" path:** mpv ≥ 0.41 passthrough wraps its absolute
  `ESC[row;colf` cursor move, which the outer terminal interprets in **window**
  coordinates. In a right-hand split, frames would draw over the left pane, and tmux
  would not know the image exists. `kitten icat` avoids this by forcing Unicode
  placeholders under tmux; mpv has no equivalent (cld, from source).
- **Shared memory (`--vo-kitty-use-shm=yes`) is local-only** by design; a remote host's
  `/dev/shm` cannot feed the Mac's kitty (mpv manual; all reports).

**Resolution of a researcher disagreement:** grk and mus proposed shipping an mpv "flag
pack" (`--profile=sw-fast`, pixel caps, `fps` filter, passthrough flag) as Phase 0. cld
and gem showed that under tmux this still sends full uncompressed frames (≥15–34 MB/s
even at 960px/15fps), places them in the wrong pane on ≥ 0.41, and athena's 0.40 doesn't
support the passthrough flag at all. The consolidated position: **mpv flags are worth
keeping only for the non-tmux and local cases** (`sw-fast`, shm, audio); they are not a
fix for the tmux pane, and the tmux hotfix is to stop launching mpv there entirely.

### 2.3 A ~1–1.2 s fixed launch tax on every open (all five reports)

| Cost | Measured range (varies by host/venv) | Source |
| --- | ---: | --- |
| Fresh-process merged-config reload in the viewer child | **0.25–0.90 s** (apollo .venv 0.64–0.68 s; uv-tools 0.82–0.90 s; second call in-process ~1 ms, but the child is always fresh) | cdx, mus, gem, cld |
| Cold viewer import (eager `markdown_pdf` etc.) | **0.27–0.66 s** | grk, mus, gem, cld |
| ~13 synchronous `tmux` subprocess calls on the UI thread | ~89 ms (UI stall, violates tui_perf rule 1) | gem |
| `subprocess.run(["clear"])` | ~10–25 ms | gem |
| VCS materialization for byte-free rows | unbounded, before the pane opens, no progress UI | mus |

This tax is real, removable, and paid by every artifact kind — but it is **not** the
"incredibly slow" headline; the transport failure is.

---

## 3. Critique: is the plan a good idea?

**Keeping the tmux pane: yes.** The pane is the right container — the TUI stays up,
`l` focuses, `a` toggles, `n`/`p` sequences work, nothing steals focus, and over SSH the
terminal is the only zero-setup channel from artifact to eyes. Images already work this
way. Abandoning it for "open a native player" as the *default* would strand the remote
topology this TUI actually lives in.

**"Make the current playback faster": no — wrong framing.** The current path cannot be
tuned into shape: it is functionally broken under tmux today, and architecturally
mismatched (raw pixels per displayed frame over a network, absolute placement in a
split pane) even when "fixed". This is a **redesign of the video backend**, not a
performance pass.

**Also wrong as a goal: native-player smoothness in the pane.** The artifacts are
screencasts and TUI demos. The user's real questions are "what did the agent produce?"
and "what happens around 0:22?" — a poster, a storyboard, and frame scrubbing answer
those faster than linear playback, at native sharpness, with ~100 KB of traffic. Motion
is a second step, not the landing state (grk, gem; file managers — ranger, lf, yazi —
independently converged on still-first preview for exactly this reason).

**Process lesson:** the design tale's own top risk ("mpv kitty-vo under tmux
passthrough") and its step 1 ("verify in a real tmux pane first") predicted this
failure. A cheap automated pty+tmux probe (assert the client receives kitty APC; assert
`#{pane_title}` never changes) would have caught it and should ship with the hotfix.
The docs (`docs/reference/agent-attachments.md#video-preview`) currently promise
behavior that does not happen under tmux.

### Requirement adjustments (explicitly called out)

| # | Adjustment | Why |
| --- | --- | --- |
| R1 | **Reframe "play the video" as "inspect first, motion on demand".** Default landing: poster + keyframe storyboard + metadata; `space`/`p` starts motion; target 8–12 fps for motion, prioritizing text legibility over frame rate. | Artifacts are screencasts/demos; legibility and time-to-answer beat fps. |
| R2 | **Set SLOs, not "much faster":** first useful pixel < 0.5–1 s after the pane opens (SSH included); motion start < 2.5 s; input response < 100 ms; replay/loop after first pass costs ~zero network. | Makes "fast" testable. Prototypes meet these. |
| R3 | **"No collateral damage" requirement:** the viewer must never change pane titles, must pace output (tmux never drops passthrough), and must not lag the SASE TUI or other panes. | Today's path degrades the whole session; unpaced uploads would too. |
| R4 | **mpv becomes optional; ffmpeg (+ kitten) becomes the video-inspect dependency.** `missing_mpv` becomes a degraded-mode banner, not a dead end. Doctor rows updated. | mpv is absent on real hosts (apollo, the Mac); ffmpeg is present everywhere this runs. |
| R5 | **kitty is the supported terminal for animated/graphic preview; others get poster + metadata.** | Already de facto true for images via `kitten icat`. |
| R6 | **Keep mpv as an opt-in backend** for local, non-tmux, full-fidelity or audio use, with `--profile=sw-fast` and `--vo-kitty-use-shm=yes` when genuinely local (capability probe, not env-var guessing). | mpv is excellent there; it's only wrong as the remote-tmux default. |
| R7 | **Add a one-key native client handoff (`o`)** — local display: `xdg-open`/`open`/`mpv --vo=gpu`; remote: user-configured command (copy-back or reuse an already-present client file). Never auto-open a desktop window. | Full-fidelity/audio needs are rare but real; keep the complexity in config, not core. Screencast clips recorded on the Mac may already exist client-side (zero transfer). |
| R8 | **Backend choice (`kitty`/`mpv`/`poster`) is an ordinary config field, not a SASE feature flag.** Extend existing `ace.artifact_file_viewer.video` keys; don't rename (tests/docs pin them). | Users choose permanently; per `sase_flags` policy this is configuration. |
| R9 | **This stays in the Python TUI** (`src/sase/ace/tui/graphics/`). Terminal presentation fails the rust-core litmus; a web frontend would use `<video>`. Only if a Python per-frame diff loop proves too slow does the tight loop move to `sase_core`. | Boundary rule; avoid premature Rust/wire work. |
| R10 | **Per-stage timing telemetry** (select → materialize → split → child-ready → first visual → motion-start) behind debug logging. VCS materialization gets a progress indication. | The next complaint should be diagnosable, not vibes-based. Distinguishes local-file pain from VCS-row pain. |
| R11 | **Make audio semantics explicit.** Today's `--mute=yes` still initializes audio; `--audio=no` disables it. Use the latter only for the declared silent preview; Original/native playback keeps audio. | Behavior change must be deliberate (cdx). |

---

## 4. Options, merged verdicts

Numbers are for a 21.8 s 1920×1080 TUI demo unless noted; "wire" = bytes through
tmux/SSH to the terminal.

| Option | First visual | Wire (whole clip) | Verdict |
| --- | --- | --- | --- |
| **A. Today** (mpv 0.40 `vo_kitty` in tmux) | never | 0 image bytes; title spam instead | Broken. Hotfix now. |
| **B. mpv ≥ 0.41 + passthrough + flags** | ~0.3 s | ~2.8 GB; ≥15–34 MB/s even capped | Reject for tmux: bandwidth, wrong-pane placement, not in Debian 13. Keep the flags for non-tmux/local mpv use. |
| **C. Poster + metadata via `kitten icat`** | **~0.5 s** | ~0.1–2 MB | **Phase-0 hotfix** and universal fallback. |
| **D. Keyframe storyboard + frame scrubber** (ffmpeg stills + icat) | **~0.35 s** | ~90 KB sheet; 100–350 KB per scrubbed frame | **Default landing (Phase 2).** Native 2560×1548 sharpness on zoom; answers most inspection questions with zero sustained load. |
| **E. Streamed kitty animation** (ffmpeg → dirty-rect → zlib `a=f` frames → Unicode-placeholder placement, `s=2` loading mode, SASE-owned keys, paced writes) | ~0.3–0.6 s | **12–21 MB** (cld, 1488 px/10 fps); **0.73–1.88 MB/s** (gem, 960 px/12 fps); then ~0 for replay/loop | **In-pane motion over SSH (Phase 3, gated).** Two independent prototypes, consistent numbers, ~100–230× less than mpv. Real wire-format gotchas (below). |
| **F. ffmpeg → GIF/WebP → `kitten icat`** | 4–14 s cold start | 10–15 MB burst | Reject: startup wait, 256-color banding, no controls, kitty RAM blowup (~633 MB for 28 s). |
| **G. Cell graphics** (`--vo=tct`, sixel, chafa) | fast | moderate | Reject as default: recorded TUI text becomes unreadable. Possible non-kitty fallback only. |
| **H. Native client handoff** (`o`) | app launch + transfer | ~the MP4 itself (0.6–5.8 MB), or 0 if already client-side | **Escape hatch (R7).** Best fidelity/audio; needs reachability; never the only path. |
| **I. Persistent viewer pane / mpv IPC** | — | — | Defer. Only if repeated-open telemetry justifies it after Phases 0–2. |
| **J. Gateway HTTP byte-range media route** (browser/native player streams from the Rust gateway) | — | compressed stream | Later extension only, if large clips + seeking demand it. Note: the existing fleet content API is POST + base64 JSON and is **not** usable as a `<video>` source; a range route would be new `sase_gateway` work (cdx). |
| K. Custom decoder / WebRTC / network streamer service | — | — | Reject: unjustified scope. |

**Resolution of the central divergence (build the streamer or not):** grk rejected
"custom ffmpeg|icat loop" and cdx warned against building a media engine — but both were
arguing against *worse* designs (PNG-per-frame piping; a new decoder/service). The
cld/gem design is neither: ffmpeg decodes; SASE only encodes kitty animation-protocol
frames (~400–600 lines incl. controls/pacing/tests), the clip plays client-side in
kitty, and replay is free. Two independent prototypes measured it. The consolidated
position: it is the **only** way to get real motion in a remote tmux pane, it is
feasible, and it should be built **after** the inspect-first UX ships and a one-hour
rendering spike passes on the real Mac kitty — because the scrubber may absorb most of
the demand for in-pane motion, and the streamer is the one piece with meaningful
maintenance weight.

---

## 5. Recommended solution (phased)

### Phase 0 — hotfix (ship first, ~hours)

In `display_video_artifact()`: when `$TMUX` is set, **do not launch mpv**. Instead
render a poster frame (`ffmpeg -ss … -frames:v 1`, ~0.2–0.5 s) through the existing
`kitten icat` image path (which already handles tmux passthrough and placeholders
correctly), print `ffprobe` metadata (duration, resolution, fps, size), and a footer
hint. This alone removes the 47 s crawl, the base64 pane titles, the border-redraw
storm, and the session-wide lag — and it works on hosts without mpv.

Ship the **regression probe** in the same change: an opt-in integration test that runs
the viewer's video mode in an isolated `tmux -L` server inside a pty and asserts
(a) kitty APC reaches the client within 1 s, (b) `#{pane_title}` is unchanged,
(c) total wire bytes stay under budget. This is the test the original plan called for
and never got.

Update `docs/reference/agent-attachments.md#video-preview` to match reality (read
`docs_writing.md` first).

### Phase 1 — remove the launch tax (benefits every artifact kind)

1. Pass the already-resolved video playback settings (and client-topology hints) from
   the TUI parent to the viewer child via env/argv (`split-window -e` or one JSON env
   var). Keep `load_merged_config()` as the standalone fallback. Preserve trust
   semantics — snapshot the parent's resolved config; don't bypass trust evaluation or
   read project YAML directly. Saves ~0.6–0.9 s per open.
2. Lazy-import `markdown_pdf` (and other non-video helpers) in the viewer; consider a
   slim entry point for single-video opens. Saves ~0.3–0.4 s.
3. Replace `subprocess.run(["clear"])` with an ANSI write; move the ~13 pane-decoration
   `tmux` calls off the Textual UI thread with bounded timeouts and a visible opening
   state. Keep signal installation and UI mutation on the main thread; do **not** move
   `_with_artifact_file_viewer_notify_pid()` wholesale into a worker (it installs a
   signal handler and mutates process env — pass launch context explicitly instead).
4. Add the R10 telemetry spans, and a progress indication for VCS materialization.

### Phase 2 — inspect-first pane (the product change)

For `mode == "video"`: show frame 0 immediately, then a cached timestamped keyframe
contact sheet (~90 KB JPEG, 0.9–2 s to generate, cached by content digest + area under
the viewer cache dir). Keys: `h`/`l` (or `←`/`→`) frame-step, `0`–`9` jump to deciles,
`z` zoom (full-sharpness single frames), `space`/`p` play, `o` native open, plus today's
`n`/`p`/`<tab>`/`q`. mpv becomes the motion backend only where it works: local,
non-tmux (or verified-local tmux via capability probe) with `--profile=sw-fast` and
`--vo-kitty-use-shm=yes`. Doctor: ffmpeg/ffprobe required for video inspect; mpv
optional for motion/native playback.

Optional rider: reuse the image cell-preview path to show a lazy, mtime-keyed poster in
the in-TUI file panel so `a` is no longer the only way to see a frame (grk's Phase-2
"poster in the TUI"; debounce so highlight movement never waits on ffmpeg).

### Phase 3 — streamed kitty-animation motion (gated go/no-go)

**Gate 1 (spike, ~1 h):** on the Mac's kitty 0.47 over SSH to athena, verify that
`s=2` loading-mode animation renders through a Unicode-placeholder virtual placement
under tmux. Both features are documented and `kitten icat` combines them for GIFs, but
neither prototype rendered on a real display.

**Gate 2 (demand):** live with Phase 2 for a while. Build the streamer when in-pane
motion is actually missed (TUI-demo timing review is the expected driver).

Design (cld's architecture, cross-checked by gem's measurements): ffmpeg decodes at a
budgeted size/fps (default ~1488 px/10 fps; 960 px/8 fps slow-link profile) → per-frame
dirty-rectangle diff → zlib → base64 → ≤128 KB chunks → DCS-wrapped `a=f` animation
frames onto one reused image ID, played by kitty in loading mode; SASE owns the keys
(pause/seek/step/replay map to tiny `a=a` control commands; replay and loop cost zero
network after the first pass).

Wire-format rules that are easy to get wrong (found during prototyping):

- Continuation chunks must repeat `a=f,q=2`, not only `m=` — kitty < 0.49 otherwise
  *replaces the root frame*; the Mac runs 0.47. (Both prototypes used `m`-only
  continuations and must change.)
- 64–128 KB chunks; stay under tmux's 1 MB `INPUT_BUF_LIMIT` (larger is silently
  discarded). `q=2` everywhere (responses can't return through tmux).
- Placeholder image IDs need non-zero high/middle bytes (copy kitten's
  rejection-sampling rule and diacritic table).
- **Pace output:** never run more than ~2–3 s ahead of the playhead; write from a
  dedicated thread; keep control commands at the head of the queue (tmux never drops
  passthrough bytes — R3).
- Budget kitty frame memory (~400 MB default; kitty caps at 5×320 MB and ENOSPCs):
  lower fps, then resolution; past the floor, preview the first N seconds and say so.
- Delete images on exit/`n`/`p` (`a=d`) from the existing signal cleanup path.

Measured expectations: first frame ~0.3–0.6 s; 12–21 MB for a 22 s 1080p demo
(vs ~2.8 GB via mpv); noisy 2560×1548 desktop capture ~35 MB (the worst case that
motivates the adaptive step-down to 960 px/4-bit). Pure-Python encoding ran ~3× real
time; move the diff loop to `sase_core` only if profiling demands it (R9).

### Explicit non-goals

No new decoder or network streaming service; no record-time thumbnail pipeline coupling
agents to TUI needs; no sixel/tct default; no X11 forwarding as the implementation; no
changes to `sase artifact open`; no persistent-pane/mpv-IPC work before telemetry
justifies it; no `sase-core`/gateway work unless Phase 3 profiling (diff loop) or a
future range-streaming need (option J) forces it.

### Validation

Fixture set: one text-heavy screencast, one motion-heavy clip, one large/high-res
artifact; cold and repeated opens; stored and VCS-materialized rows; local terminal,
SSH+tmux, and the real Mac→athena hop. Measure selection→first-visual,
motion-start→first-frame, key response, effective fps vs wall time, wire bytes, and
other-pane responsiveness during playback. Acceptance per the R2 SLOs; unit tests for
command construction, backend dispatch (including the tmux guard), snapshot
propagation/invalidation, wire-format goldens (Phase 3), and the pty+tmux probe.

---

## 6. Where the researcher reports disagreed, and how it resolved

| Disagreement | Resolution |
| --- | --- |
| Slow vs broken | **Broken under tmux** (cld measured athena 3.5a; lead reproduced the APC→title mechanism on apollo 3.4). cdx/grk/mus analyzed a path that cannot currently draw at all in tmux; their transport math still holds and bounds the "fixed" case. |
| tmux "drops" unwrapped APC (gem) | It doesn't drop it; it consumes it as a pane title and redraws — worse, given SASE's `#{pane_title}` border. |
| Ship an mpv flag pack as Phase 0 (grk, mus) | Rejected for tmux (still uncompressed, wrong-pane placement on ≥ 0.41, athena's 0.40 lacks the flag). Retained for the local/non-tmux mpv backend. |
| Config-reload cost: 0.25 s (cld) vs 0.62–0.90 s (cdx/mus/gem) | Host/venv variance; all agree it is fresh-process, cacheable-in-parent work worth ~0.6–0.9 s on the affected hosts. |
| Build a custom streamer (cld, gem) vs don't (grk, cdx, mus) | The "don't" cases argued against different, worse designs. Adopted as **Phase 3, gated** on a real-kitty rendering spike and demonstrated demand after the inspect-first UX ships. |
| Pane-first (cld) vs handoff-friendly (cdx, gem) | Both: the pane remains the default (robust over SSH, no reverse channel); native handoff is a one-key configured escape hatch, never automatic. |

## 7. Provenance

- `__cld` — the broken-path discovery and measurements (athena), tmux/mpv/kitty source
  analysis, streamer prototype + wire-format gotchas, phased plan skeleton, probe test.
- `__gem` — launch-tax breakdown (incl. UI-thread tmux calls), bandwidth-inflation
  benchmarks on real screencasts, dirty-rect zlib prototype, storyboard/scrubber design,
  client-handoff detail.
- `__grk` — inspect-vs-play reframing, file-manager precedent, in-TUI placeholder
  finding, keep-the-pane contract, still-extract timings, "no feature flag" call.
- `__mus` — stage-by-stage pipeline trace, VCS-materialization and telemetry
  requirements, mpv-optional stance, `sase artifact open` non-goal.
- `__cdx` — three-way acceptance criteria, trust-preserving config snapshot, audio
  semantics, capability-probe-not-env-guessing, gateway range-route analysis and its
  POST/base64 caveat, validation protocol.
- Lead — independent apollo verification of the APC→title mechanism, code-claim
  verification at `ea7916d7a7`, design-tale location correction (plans sidecar), and
  this consolidation.
