# Speeding Up Tmux Video Artifact Viewing in SASE

- **Date:** 2026-11-17
- **Author:** Researcher `gem`
- **Target Surface:** `a` keymap (`open_artifact_files`) on the SASE TUI Agents tab and the shared terminal artifact viewer (`src/sase/ace/tui/graphics/`)

---

## Executive Summary

Viewing video artifacts in a separate `tmux` pane is slow because the current design hits **both** a **~1.2-second launch tax** on every pane open and a **~100–275+ MB/s pixel-streaming bottleneck** inside `mpv --vo=kitty`.

Inspection of `mpv`'s `vo_kitty.c` driver and measurements on real SASE `2560x1548` H.264 screencasts show why: `mpv --vo=kitty` converts every frame to **uncompressed raw RGB24** (`f=24`, zero `o=z` compression), renders the **entire pane pixel canvas** (because SASE omits `--vo-kitty-width`/`height` and `vo_kitty.c` never emits Kitty `c=/r=` upscale cells), omits `--profile=sw-fast` and `--vo-kitty-use-shm=yes`, omits `--vo-kitty-auto-multiplexer-passthrough=yes`, and pushes thousands of `\ePtmux;...\e\\` chunks per frame through `tmux`'s single-threaded server loop and SSH. On a `1280x774 @ 30 fps` stream of a `644 KB` (7.5s) `.mp4`, raw RGB24 base64 output is **`891.65 MB` (`118.89 MB/s`)** — a **1,384× bandwidth inflation** over the source H.264 stream (`0.086 MB/s`). Meanwhile, `mpv` is not even installed on hosts like `apollo`, and `t=s` shared memory cannot work over SSH anyway because remote `mpv` and client-side Kitty do not share `/dev/shm`.

**Critique & Adjusted Direction:** Trying to make 30 fps full-screen pixel streaming fast through a `tmux` pane over SSH fights the physics of terminals, multiplexers, and video codecs. Even aggressive in-terminal optimizations cannot match sending a `0.09–0.20 MB/s` compressed `.mp4` directly to a GPU-accelerated client player. Rather than treating "stream full-motion video inside a tmux pane" as an immutable requirement, SASE should separate **quick in-pane visual inspection** from **full-motion Retina playback**:

1. **Phase 1 (Immediate, ~1.2 s saved + local fix):** Remove cold config re-loading (`~825–896 ms`), eager `markdown_pdf` import (`~274 ms`), `clear` subprocess overhead, and UI-blocking synchronous tmux calls (`~89 ms`), while fixing `mpv` flags (`--profile=sw-fast`, passthrough, and local-only `--vo-kitty-use-shm=yes`).
2. **Phase 2 (Recommended Architecture):** Make the tmux artifact pane land instantly (`<0.5 s`) on a **Frame-0 + Keyframe Storyboard & Interactive Scrubber** (`~90 KB` via `kitten icat`, zero continuous PTY load), add an **on-demand compressed Kitty streamer** (`ffmpeg` + dirty-rect `zlib` `o=z` + single reused `i=` ID + `c=/r=` GPU placement, measured at **`0.73–1.88 MB/s`** — **~63–162× less traffic** than `mpv --vo=kitty` — with local SHM fast path), and provide a **one-key `o` native client handoff** that opens the compressed `.mp4` directly on the user's display host.

---

## 1. Current Architecture Trace (`a` on Agents Tab)

When the user presses `a` on the Agents tab, the flow crosses seven modules:

1. **Keymap & Modal (`src/sase/ace/tui/bindings.py:252`, `src/sase/ace/tui/actions/agents/_panel_artifact_actions.py`):**
   `action_open_artifact_files()` toggles/closes an existing tracked viewer pane if open, or pushes `ArtifactFileSelectionModal`.
2. **Optional VCS Materialization (`src/sase/ace/tui/actions/agents/_panel_artifact_open.py`):**
   If any selected artifact is byte-free (`path is None`), `_materialize_and_open_artifact_files()` extracts bytes into `~/.sase/artifacts/vcs-cache/` off-thread. Byte-backed rows skip directly to `_open_artifact_files()`.
3. **Tmux Split & Pane Decoration (`src/sase/ace/tui/graphics/_viewer_tmux.py`, `_viewer_tmux_decoration.py`, `src/sase/ace/tui/actions/agents/_panel_artifact_pane.py`):**
   - `view_artifact_files_in_tmux_pane()` runs `tmux split-window -h -P -F #{pane_id} ...` launching `python -m sase.ace.tui.graphics.viewer`.
   - `_track_artifact_file_tmux_pane()` then executes `decorate_artifact_file_tmux_panes()` plus `_sync_artifact_file_viewer_layout()`: **13 sequential synchronous `subprocess.run(["tmux", ...])` calls** on Textual's UI thread (`4x show-options`, `3x display-message`, `2x select-pane -T`, `4x set-option`).
4. **Viewer Subprocess Loop (`src/sase/ace/tui/graphics/viewer.py`, `_viewer_loop_sequence.py`, `_viewer_loop_media.py`, `_viewer_render.py`):**
   - `run_artifact_sequence_loop()` computes `artifact_image_area()` from cell dimensions (`shutil.get_terminal_size()`), calls `load_artifact_video_playback_config()`, and calls `display_video_artifact()`.
   - `display_video_artifact()` validates `shutil.which("mpv")`, runs `subprocess.run(["clear"])`, prints a Rich header panel, moves the cursor, and executes `artifact_video_player_command()`:

```python
[
    "mpv",
    "--no-config",
    "--vo=kitty",
    "--keep-open=yes",
    "--vo-kitty-alt-screen=no",
    "--vo-kitty-config-clear=no",
    f"--vo-kitty-left={left}",
    f"--vo-kitty-top={top}",
    f"--vo-kitty-cols={columns}",
    f"--vo-kitty-rows={rows}",
    "--mute=yes",  # unless audio=True
    # "--loop-file=inf" if loop=True
    "--",
    str(expanded),
]
```

This exact viewer stack is shared by `Artifacts -> Files` (`src/sase/ace/tui/actions/artifacts_files.py`), `NotificationModal` (`V`, `src/sase/ace/tui/modals/notification_modal_attachments.py`), prompt hints (`_view_files_with_artifact_file_viewer` in `src/sase/ace/tui/actions/hints/_files.py`), and `sase artifact open` (`src/sase/artifact_cli/open.py`).

---

## 2. Root-Cause Performance Diagnosis (Code & Measurements)

### 2.1 Launch & Control-Plane Overhead (~1.2 Seconds Before Playback Begins)

Benchmarking the installed `sase` virtualenv (`/home/bryan/.local/share/uv/tools/sase/bin/python3`) and live `tmux 3.4` session on `apollo` shows substantial startup work before `mpv` even executes:

| Startup Step | Source Location | Measured Cost |
| --- | --- | ---: |
| 13 synchronous `tmux` subprocesses on UI thread | `_panel_artifact_pane.py`, `_viewer_tmux_decoration.py` | **89.1 ms** |
| Cold import of `sase.ace.tui.graphics.viewer` (eagerly imports `sase.attachments.markdown_pdf`) | `src/sase/ace/tui/graphics/viewer.py:13` | **273.7 ms** |
| `load_artifact_video_playback_config()` → `load_merged_config()` (re-parses YAML/plugins/schema inside child pane) | `src/sase/ace/tui/graphics/_viewer_loop_media.py:73-100` | **824.5–895.7 ms** |
| `clear_terminal()` subprocess (`subprocess.run(["clear"])`) | `src/sase/ace/tui/graphics/_viewer_loop_terminal.py:135-138` | ~10–25 ms |
| **Total pre-player tax** | | **~1.20 s** |

Note that running 13 synchronous `subprocess.run` calls on Textual's UI thread also violates `sase/memory/tui_perf.md` Rule 1 ("Never block the event loop... No synchronous... subprocess calls").

### 2.2 Inside `mpv --vo=kitty`: Why Frame Streaming Collapses

Inspecting upstream `mpv` (`sase/repos/external/gh/mpv-player/mpv/video/out/vo_kitty.c`, `terminal_swapchain.c`, `osdep/terminal-unix.c`, `DOCS/man/vo.rst`) exposes six compounding issues:

1. **Zero compression (`f=24` raw RGB24 + base64):**
   `vo_kitty.c:44,51` hardcodes `IMGFMT_RGB24` (`3 bytes/px`) and `KITTY_ESC_IMG = "\033_Ga=T,f=24,s=%d,v=%d,C=1,q=2,m=1;"`. It has **no `o=z` zlib compression** support. Every pixel costs `3 * (4/3) = 4.0` ASCII bytes on stdout.
2. **Unbounded full-canvas emission:**
   SASE passes `--vo-kitty-cols` and `--vo-kitty-rows`, but **never passes `--vo-kitty-width` or `--vo-kitty-height`**. In `vo_kitty.c:143-173`, `get_win_size()` reads `TIOCGWINSZ` pixel dimensions (`terminal_get_size2()`). Following `mpv` commit `ebf3c145f9` (*"draw the video into a frame the size of the canvas"*), `vo_kitty` clears the full `vo->dwidth x vo->dheight` pane buffer (including letterbox bars) and transmits **every pixel of the entire pane canvas on every frame**.
   - On the active Kitty client observed via `tmux list-clients` (`261x79` cells, `11x21 px/cell`, `xterm-kitty kitty(0.47.0)`), a half-screen split pane is ~`130x77` cells (~`1430x1617 px`).
   - One frame at `1430x1617` = `6.94 MB` raw RGB24 = **`9.25 MB` base64** across `~2,258` 4096-byte escape chunks. At 30 fps that is **`~277.5 MB/s` (~2.22 Gbps)** through the PTY!
   - Conversely, when `TIOCGWINSZ` returns `xpixel=0, ypixel=0` (as observed in detached/headless PTYs), `vo_kitty.c` falls back to `320x240` (`~9.2 MB/s` at 30 fps and blurry).
3. **`vo_kitty` cannot decouple transmitted resolution from display size:**
   `KITTY_ESC_IMG` in `vo_kitty.c:51` does not emit Kitty's `c=<cols>,r=<rows>` placement keys. If SASE caps `--vo-kitty-width`/`height` to e.g. `640x388` to save bandwidth, Kitty displays a small `640x388` box rather than GPU-upscaling it to fill the `cols x rows` pane.
4. **Shared memory (`--vo-kitty-use-shm=yes`) is both off and impossible over SSH:**
   `vo_kitty.c` defaults `use_shm` to `false`. Locally on the same machine, `--vo-kitty-use-shm=yes` reduces PTY traffic to ~90 bytes/frame (`t=s`). Over SSH (`SSH_CONNECTION` from MacBook Kitty to `apollo` or `athena` tmux), `/dev/shm` is not shared across machines, so `t=s` cannot work at all (`DOCS/man/vo.rst:431-435`).
5. **Missing `--profile=sw-fast`, FPS cap, image-ID reuse, and frame deduplication:**
   - `mpv`'s own `DOCS/man/vo.rst:404` warns: *"You may need to use `--profile=sw-fast` to get decent performance."* SASE omits it, leaving `libswscale` on higher-cost default scaling for `2560x1548` inputs.
   - Every frame emits `a=T` (transmit+display with `i=0`) instead of updating a single `i=<id>` or emitting `a=f` dirty-rect deltas, churning Kitty's texture cache and sending identical static screencast frames 30 times/second.
6. **`tmux` DCS passthrough overhead and missing flag:**
   - SASE omits `--vo-kitty-auto-multiplexer-passthrough=yes` (added in `mpv` commit `d9dc84c0fc` / `v0.41.0`, defaulting to `false`; absent entirely in older builds like Ubuntu 24.04's `0.37.0`). Without passthrough wrapping, `tmux` drops raw `\033_G...` sequences unless wrapped externally.
   - When passthrough *is* active (`allow-passthrough all` in `tmux.conf`), every 4096-byte chunk is wrapped in `\033Ptmux;\033...\033\\` (`vo_kitty.c:57-59,321-332`), forcing `tmux`'s single-threaded event loop to parse and re-frame **~45,000–67,000 DCS blocks per second** before pushing them down the SSH TCP socket. Backpressure fills `tmux` buffers and stalls `mpv`'s `terminal_swapchain` (`terminal_swapchain.c:127-134`), dropping playback to 1–3 fps and delaying `q` exit.

### 2.3 Empirical Benchmarks on Real SASE Screencast Artifacts

Measured directly on `apollo` (16-vCPU Xeon Platinum 8168) using two real `~/tmp/screencasts/*.mp4` clips (`2560x1548`, H.264, `yuv420p`, `30 fps`):

- **Short clip (`20261115_195328.mp4`):** `7.50 s`, `225 frames`, **`644,475 B` (`629 KiB`, `0.086 MB/s`)**
- **Long clip (`20261117_094416.mp4`):** `28.37 s`, `851 frames`, **`5,792,412 B` (`5.52 MiB`, `0.204 MB/s`)**

| Representation / Pipeline | Short Clip (7.5s) Total Payload | Short Rate | Long Clip (28.4s) Total Payload | Long Rate | Startup / Generation Cost |
| --- | ---: | ---: | ---: | ---: | --- |
| **Source H.264 `.mp4`** | **0.64 MB** | **0.086 MB/s** | **5.79 MB** | **0.204 MB/s** | **0 ms** (already on disk) |
| Raw RGB24 base64 (`1280x774 @ 30fps`, `mpv`-like) | 891.65 MB | 118.89 MB/s | ~3,376 MB (est.) | ~118.9 MB/s | `ffmpeg` decode 2.15 s |
| Raw RGB24 base64 (`960x580 @ 15fps`) | 251.67 MB | 33.56 MB/s | 948.8 MB | 33.4 MB/s | `ffmpeg` decode 1.08 s / 3.33 s |
| Full-frame `zlib-1` (`o=z`) base64 (`960x580 @ 15fps`) | 53.80 MB | 7.17 MB/s | 125.6 MB | 4.4 MB/s | +1.56 s (short) / +~5 s (long) CPU |
| Full-frame `zlib-1` (`o=z`) base64 (`640x388 @ 10fps`) | 16.75 MB | 2.23 MB/s | — | — | decode 0.93 s + zlib 0.47 s |
| **Dirty-rect crop `zlib-1` (`thr=8`, `960x580 @ 12fps`)** | **14.09 MB** *(22/90 skipped)* | **1.88 MB/s** | **20.80 MB** *(181/340 skipped)* | **0.73 MB/s** | streaming (frame 1 in **476 ms**, `362 KB` b64) |
| Animated GIF (`960x580 @ 10fps`) → `kitten icat` | **1.59 MiB** *(439 chunks, `a=f`)* | *(one-shot)* | `4.97 MB` GIF *(~10–15 MiB stream est.)* | *(one-shot)* | **3.95 s** short (`2.27s` ffmpeg + `1.68s` icat); `8.01 s` ffmpeg alone on long |
| Animated WebP (`960x580 @ 10fps`, `-q:v 75 -compression_level 0`) | 5.73 MB file | *(one-shot)* | 17.26 MB file | *(one-shot)* | `2.18 s` (short) / `6.44 s` (long) |
| Animated PNG (`960x580 @ 10fps`) | 21.20 MB file | *(one-shot)* | — | — | `8.95 s` (short) |
| **5×2 Contact Sheet JPEG (`384px` tiles, single pass)** | **90.1 KB** | *(static)* | **86.5 KB** | *(static)* | **0.86 s** (short) / **1.94 s** (long) |
| Keyframe-only scan (`-skip_frame nokey`) | — | — | — | — | **0.43 s** across entire 28.4 s clip |

*Key insight from `kitten icat` on `short.gif` (measured via PTY):* `kitten icat` produced **1.59 MiB** total for 75 frames because it uses Kitty animation frames (`a=f`, `o=z`, cropped `x=,y=,s=,v=` sub-rectangles — e.g., a `5x7` pixel cursor blink took 105 bytes) plus Unicode placeholders (`U=1`). However, pre-encoding the GIF took `2.27 s` (short) and `8.01 s` (long), and `kitten icat` pushes **all frames into Kitty's RAM upfront** (`284 frames × 960×580×4 B ≈ 633 MB` for a 28 s clip; a 2-minute clip exceeds 2.6 GB and triggers Kitty graphics cache eviction).

---

## 3. Critique of the Plan & Adjusted Requirements

### Is "View Video Artifacts in a Separate Tmux Pane" a Good Idea?

**As the sole or primary full-motion player, no.** It is a classic abstraction mismatch:

1. **Codec inversion:** Re-inflating a `0.09–0.20 MB/s` H.264 file into `15–277 MB/s` of raw RGB escapes just to push pixels down a terminal PTY is fundamentally wasteful.
2. **Screencast legibility vs. pane geometry:** Real SASE video artifacts are predominantly `2560x1548` UI/code screencasts. Shrinking them into a half-width tmux pane blurs small text; running full-DPI kills transport speed.
3. **Hostile UX for inspection:** Watching a 30-second video linearly without a visual scrubber wastes time when you only need to inspect second `0:22`. Pressing `<tab>` back to SASE while `mpv` continues blasting frames shares the same SSH/tmux pipe with Textual, degrading TUI responsiveness too.
4. **Local/remote asymmetry:** In SASE's multi-host workflow (MacBook Kitty over Tailscale SSH to `apollo`/`athena` `tmux`, plus local sessions), `mpv --vo=kitty --vo-kitty-use-shm=yes` only fixes the local case and completely misses the SSH case.

**However, completely abandoning the tmux artifact pane is also wrong.** Users expect `a` on the Agents tab to stay unified across markdown, PDF, images, text, and video (`n`/`p` navigation, `z` zoom, zero window focus stealing for a 1-second sanity check).

### Explicitly Proposed Requirement Adjustments

| Original / Implicit Requirement | Proposed Adjustment | Justification |
| --- | --- | --- |
| **R1:** Selecting a video in `a` must immediately auto-stream full-motion video in the tmux pane. | **Default the tmux pane to an instant Keyframe Storyboard + Interactive Frame Scrubber; make live motion one keypress (`space`/`p`) or opt-in config (`mode: stream`).** | Cuts time-to-visual from multi-second stalls to `<0.5 s` (`~90 KB` payload), gives at-a-glance inspection of the entire clip, and keeps full `2560x1548` sharpness when zoomed on a single frame. |
| **R2:** `mpv --vo=kitty` is the mandatory backend for terminal video playback (`validate_artifact_file_viewer_dependencies`). | **Replace `mpv` as the mandatory remote backend with `ffmpeg` (+ `kitten`). Keep `mpv` only as a local SHM accelerator (`--vo-kitty-use-shm=yes`) or native GUI opener.** | `mpv` isn't installed on `apollo`, `vo_kitty.c` lacks `o=z` compression and `c=/r=` upscaling, and SSH cannot use SHM. `ffmpeg` is already on `apollo` and required by `svid_fetch`. |
| **R3:** Video viewing must happen strictly inside the tmux pane. | **Add a one-key native client handoff (`o`) that opens the `.mp4` on the user's display machine (local `open`/`xdg-open`/`mpv`, or SSH/Tailscale bridge to client).** | Only client-side hardware decoding gives 2560×1548 Retina 30/60 fps with scrubbing and audio at `0.09–0.20 MB/s` instead of `15–277 MB/s`. |
| **R4:** Viewer subprocess resolves config independently on launch. | **Pass pre-resolved viewer settings and attached-client topology from the TUI parent; lazily import PDF tooling.** | Eliminates ~1.1 s of wasted Python/YAML/plugin startup before anything paints (improves images, PDFs, and Markdown too). |

---

## 4. Candidate Approaches & Tradeoff Matrix

### Option A: Tune `mpv --vo=kitty` (+ Local SHM)
- **How it works:** Detect same-host vs. SSH client; pass `--profile=sw-fast`, `--vo-kitty-auto-multiplexer-passthrough=yes` (when supported), `--vo-kitty-use-shm=yes` (local only), and `--vf=fps=15,scale=960:-2` (remote).
- **Pros:** Tiny code change in `_viewer_loop_media.py`; keeps `mpv` seek/pause/audio keys.
- **Cons:** Over SSH + `tmux`, `vo_kitty.c` still emits uncompressed `f=24` raw RGB24 (`~15–34 MB/s` at `960x580 @ 15fps`) and **cannot** make Kitty upscale a smaller buffer because `KITTY_ESC_IMG` omits `c=/r=` — capping `--vo-kitty-width`/`height` shrinks the displayed video on Retina screens. Also keeps `mpv` dependency (missing on `apollo`).

### Option B: Pre-Transcode MP4 → Animated GIF / WebP → `kitten icat`
- **How it works:** `ffmpeg` converts clip to GIF/WebP, then `kitten icat --place` uploads animation frames (`a=f`/`a=a`).
- **Pros:** Low total bytes on short clips (`1.59 MiB` for 7.5 s GIF); Kitty plays locally with zero ongoing tmux/SSH traffic once uploaded.
- **Cons:** Unacceptable startup wait (`3.95 s` on 7.5 s clip; `~14 s` on 28.4 s clip); Kitty buffers every decoded RGBA frame in RAM (`~633 MB` for 28 s, >2.6 GB for 2 min -> cache eviction); no pause or seek controls; 256-color GIF banding (and WebP was 7× larger). **Not recommended** except possibly for <3 s micro-clips.

### Option C: Custom Streaming Kitty Protocol Renderer (`ffmpeg` → Dirty-Rect/Tile `zlib` `o=z` + `c=/r=` + Fixed `i=`)
- **How it works:** `ffmpeg` decodes and fast-scales (`flags=fast_bilinear`) to a bounded resolution (e.g. `max_width=960`, `12–15 fps`) piped as raw RGB24 to a lightweight streamer (Python or `sase-core` Rust with `flate2`). Each frame diffs against the previous frame with a small H.264 noise deadband (`|Δ| > 8`), skips unchanged frames, crops the dirty bounding box (or sends `a=f,r=1` / `a=T,i=1` updates with `o=z` zlib compression and `c=<cols>,r=<rows>` GPU upscaling), and exposes `space`/`←/→`/`r`/`q` in our loop.
- **Pros:** **~63–162× less bandwidth** than `mpv --vo=kitty` (`0.73–1.88 MB/s` measured vs `118.9 MB/s`), `~0.4–0.5 s` time-to-first-frame, bounded Kitty RAM (1 reused ID), instant `q`/`<tab>` cancellation, no `mpv` required.
- **Cons:** Full-screen scroll/pan sequences still spike to ~`3–7 MB/s` over SSH; requires maintaining custom playback/seek timing logic (and no audio over stdout pipe); `a=f` sub-rect updates require Kitty (while full-frame `a=T,i=1,o=z` works in Ghostty/WezTerm too).

### Option D: Instant Keyframe Storyboard + Interactive Frame Scrubber (`ffmpeg` + `kitten icat`)
- **How it works:** On open, immediately extract & display Frame 0 (`<0.4 s` via `kitten icat`), and generate/cache a `5x2` (or `4x2`) timestamped keyframe contact sheet (`~86–90 KB` JPEG in `0.86–1.94 s`, or faster via `-skip_frame nokey`). Keys `h/l` (`←/→`) and `0-9` scrub single crisp frames (`100–350 KB` each via `kitten icat --place`) in-pane; `z` zooms tmux pane for razor-sharp `2560x1548` inspection.
- **Pros:** Sub-second open, `<100 KB` initial payload, zero continuous tmux/SSH load, text stays crisp when zoomed, full timeline visibility at a glance, trivial to test and cache by file hash/mtime.
- **Cons:** Not live motion by itself (pairs cleanly with Option C and/or Option E).

### Option E: Native Client Player Handoff (Zero Pixel Streaming)
- **How it works:** Open the compressed `.mp4` (`0.09–0.20 MB/s`) directly in a native GPU-accelerated player (`QuickTime` / `IINA` / `mpv` on macOS, `mpv`/`xdg-open` on local Linux):
  - **Local session:** direct `open` / `xdg-open` / `mpv` on the file path.
  - **Remote SSH session (e.g. Mac Kitty -> `apollo`/`athena`):** reuse `~/tmp/screencasts/<basename>` if already present on the SSH client (zero transfer for `macrec` clips!) or transfer/stream the `.mp4` over SSH/Tailscale (e.g., `scp` to client cache or ephemeral HTTP byte-range server over SSH forward) and invoke `ssh ${SASE_CLIENT_PEER:-mac} open ...`.
- **Pros:** **1,384× less bandwidth** than `mpv --vo=kitty`, full `2560x1548` Retina 30/60 fps, hardware H.264 decode, instant seeking, audio support, zero tmux interference.
- **Cons:** Opens a window outside tmux; remote SSH handoff requires client reachability (already solved in Bryan's `chezmoi` setup via `ssh ${CLIP_PEER:-mac}` in `executable_xc`, though headless/non-configured clients need Option D/C fallback).

### Comparison Summary

| Option | Time to 1st Visual | SSH+Tmux Rate (28.4s clip) | Local Rate | UI Text Sharpness | Pause / Seek | Kitty RAM | Complexity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Current (`mpv --vo=kitty`)** | ~1.5 s+ | ~119–277 MB/s (stalls) | ~119–277 MB/s | Native (if unscaled) | mpv keys (laggy) | High churn | Existing |
| **A. Tuned `mpv` (+ local SHM)** | ~0.5 s (after launch fix) | ~15–34 MB/s (still slow) | **~0 MB/s** (`t=s`) | Blurry if downscaled | mpv keys | High churn | Low |
| **B. MP4 → GIF + `kitten icat`** | **~14 s** (4 s on 7.5s) | ~10–15 MiB burst | ~10–15 MiB burst | 256-color dithered | None | **~633 MB+** | Low |
| **C. Custom Kitty `o=z` Streamer** | **~0.4–0.5 s** | **~0.7–1.9 MB/s** | ~0 MB/s (w/ SHM) | Good (up to 960px) | Space, seek, speed | **~2–4 MB (1 ID)** | High |
| **D. Keyframe Storyboard + Scrubber** | **~0.35 s** | **~0.09 MB total** | **~0.09 MB total** | **2560×1548 native** | Frame/decile scrub | **<5 MB** | Medium |
| **E. Native Client Handoff** | **~0.15–0.8 s** | **~0.20 MB/s** (or 0 if cached) | **0 network** | **2560×1548 Retina** | Full native + audio | **0 MB** | Low–Medium |

---

## 5. Recommended Solution

Implement a **two-phase hybrid architecture** that removes the launch bottleneck for all artifacts, makes the tmux pane instant and lag-free by default, preserves in-pane motion when desired, and gives a one-key escape hatch to native hardware-accelerated playback.

### Phase 1: Immediate Wins (Low Risk, Fixes Launch Overhead & Local `mpv`)

1. **Eliminate the ~1.2 s pane launch tax (`src/sase/ace/tui/graphics/` & `_panel_artifact_pane.py`):**
   - Have the TUI pass already-loaded `ArtifactVideoPlaybackConfig` settings (and whether the attached tmux client is local vs. remote SSH) to `sase.ace.tui.graphics.viewer` via CLI flags/env so the viewer child skips `load_merged_config()` (**saves ~825–896 ms**).
   - Lazy-import `sase.attachments.markdown_pdf` inside `render_artifact_file_pages()` instead of at top-level `viewer.py` (**saves ~274 ms** for video/image/text opens).
   - Replace `subprocess.run(["clear"])` with `sys.stdout.write("\x1b[2J\x1b[H")` and consolidate/offload `decorate_artifact_file_tmux_panes()`'s 13 `tmux` subprocesses off the UI thread (**saves ~89 ms** of UI stall).
2. **Fix tmux-client locality detection & `mpv` flags (`_viewer_loop_media.py`):**
   - Detect local vs. remote SSH dynamically via `tmux` client metadata (`SSH_CONNECTION` / client environment in `tmux show-environment`, since TUI process `os.environ` goes stale across `tmux attach`).
   - When `mpv` is used **locally** (same host as Kitty): add `--profile=sw-fast`, `--vo-kitty-use-shm=yes`, and `--vo-kitty-auto-multiplexer-passthrough=yes` (probe `mpv --list-options` / cache once so `mpv <= 0.40` does not error on unknown flag).
   - Over **SSH**: never pass `--vo-kitty-use-shm=yes`.

### Phase 2: Recommended Video Experience (Three-Tier Hybrid)

Make the tmux video pane fast, legible, and self-contained without requiring `mpv` on headless servers:

1. **Tier 1 — Instant Default Landing (`<0.5 s`): Keyframe Storyboard + Interactive Scrubber (Option D)**
   - On selecting a video, immediately extract & display Frame 0 (`kitten icat --place`) followed in-place by a cached `5x2` (or `4x2`) timestamped contact sheet (`ffmpeg -skip_frame nokey` or single-pass `fps=10/<dur>,scale=384:-1,tile=5x2`, ~90 KB JPEG, cached under `~/.cache/sase/video-previews/<sha256>/`).
   - Print video metadata (`duration`, `resolution`, `fps`, `codec`, `size`) and scrubber controls: `h/l` or `←/→` to step frames, `0-9` to jump to `0%–90%`, `z` to zoom for razor-sharp `2560x1548` frame inspection, `p`/`space` to play in-pane, `o` to open natively, `n/p` (when multi-artifact) / `<tab>` / `q` as today.
2. **Tier 2 — On-Demand In-Pane Motion (`space` / `p`, or `ace.artifact_file_viewer.video.mode: "stream"`): Compressed Kitty Streamer (Option C) / Local SHM `mpv`**
   - **If local same-host + `mpv` available:** launch `mpv --vo=kitty --vo-kitty-use-shm=yes --profile=sw-fast ...` (~0 PTY traffic, full FPS).
   - **If remote SSH or `mpv` absent:** stream via `ffmpeg` (`fps=12`, `scale=min(iw,960):-2:flags=fast_bilinear`, `rgb24`) into a dirty-rect + `zlib` (`o=z`) Kitty frame emitter (`c=<cols>,r=<rows>`, single fixed image ID `i=`, `a=f` delta updates when Kitty or `a=T,i=<id>` replacement fallback), skipping unchanged frames (`|Δ| <= 8`). If Python per-frame diffing proves too slow on large panes, move the tight `diff + flate2 + base64` loop into `sase_core` (`sase-core` already provides the Rust binding boundary).
   - Replace `mpv`-only doctor failure in `checks_tools.py` / `_viewer_render.py` so `ffmpeg` satisfies video viewing when `mpv` is absent.
3. **Tier 3 — One-Key Native Retina Playback (`o`, Option E):**
   - **Local display:** invoke platform opener (`open` on macOS, `xdg-open` / `mpv` on Linux).
   - **Remote SSH:** if a configured client peer (e.g., `ace.artifact_file_viewer.video.client_ssh_host` / `CLIP_PEER` pattern) is reachable:
     - First check if `~/tmp/screencasts/<basename>` exists on the client with matching size/digest (zero transfer for `macrec` screencasts), otherwise `scp` to client cache (644 KB–5.8 MB over Tailscale transfers in <1 s) or serve via an ephemeral byte-range HTTP URL over an SSH reverse tunnel, then run `open` / `mpv` natively on the client.

### Summary Recommendation

Do **not** invest in trying to make `mpv --vo=kitty` fast over SSH + `tmux` — its lack of `o=z` compression, lack of `c=/r=` upscaling, full-canvas emission, and absence of SHM over SSH make it structurally unsuited to remote tmux panes. Instead:
- Ship **Phase 1** immediately to eliminate the **~1.2 s** launch overhead across the viewer and unlock `--vo-kitty-use-shm=yes` locally.
- Ship **Phase 2** with **Instant Keyframe Storyboard + Interactive Scrubber** as the default tmux pane view (plus `space` for **dirty-rect `zlib` Kitty streaming** and `o` for **native `.mp4` client handoff**), turning video inspection from a multi-second bandwidth stall into a sub-second, crisp, and genuinely useful TUI workflow.
