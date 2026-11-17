# Fast Video Artifact Previews in the tmux Artifact Pane

- **Researcher:** cld (Claude Opus 5.5), one of a 5-researcher swarm
- **Date:** 2026-11-17
- **Question:** Video artifacts opened in the tmux artifact pane (Agents tab, `a` keymap, then pick a
  video) are "incredibly slow". How should SASE make this much faster? Is the current approach
  sound, and what should replace it?

---

## TL;DR

1. **The current path is broken, not just slow.** The viewer runs `mpv --vo=kitty` inside a tmux
   pane. On athena (Debian 13, **mpv 0.40.0**, **tmux 3.5a**), mpv sends kitty graphics as raw APC
   escape sequences with no tmux passthrough wrapping. tmux 3.5a treats every APC string as a
   *pane-title change*. **No video pixels ever reach kitty.** Instead, each 4 KB chunk of video
   becomes a pane title. SASE's artifact-pane decoration shows `#{pane_title}` in the pane border,
   so tmux also redraws the border for every chunk. Measured on athena: a 6 s clip took **47 s**
   to "play", the border showed base64 garbage, and **0 bytes** of kitty image data reached the
   client. That 8× crawl is the slowness the user sees.
2. **Even fully fixed, mpv's kitty output cannot be fast in this setup.** `vo_kitty` sends every
   displayed frame as **uncompressed base64 RGB**: 5.2 MB per frame at a half-screen Retina pane,
   about **130 MB/s (≈1 Gbps)** at 25 fps. Measured:
   - tmux DCS passthrough tops out near **50 MB/s on localhost**, about 9.6 fps at that frame size.
   - A 100 Mbps link gives **2.4 fps**, so a 6 s clip takes 32 s.
   - A 25 Mbps link gives **0.6 fps**, so a 6 s clip takes over 120 s.

   mpv's passthrough mode (≥ 0.41, off by default) also positions frames with an absolute cursor
   move sent to the *outer* terminal. In a split pane, the picture would land over the wrong pane.
   mpv has no Unicode-placeholder support. Tuning mpv flags is therefore a dead end.
3. **Recommended fix: stream the video into kitty's own animation engine.** A small Python encoder
   in the viewer subprocess works like this:
   - ffmpeg decodes frames at a chosen size and fps (default 10).
   - Each frame is diffed against the previous one. Only the changed rectangle is sent, as a
     zlib-compressed `a=f` animation frame.
   - Display goes through a Unicode-placeholder virtual placement, the same mechanism
     `kitten icat` already uses for images in tmux.
   - kitty plays the frames locally in "loading" mode (`s=2`) while the rest upload.
   - Pause, seek, frame-step and replay are tiny `a=a` control commands. Once uploaded, the clip
     loops with **zero further traffic**.

   My prototype, measured through an isolated tmux:
   - **first frame on the wire in ~0.3 s**;
   - **12–21 MB for a whole 22 s 1080p demo** at 1488 px / 10 fps, versus about 2.8 GB for mpv;
   - average bandwidth of about 5–8 Mbps;
   - the encoder runs about 3× faster than real time in pure Python.
4. **Ship a hotfix first.** In tmux, stop launching `vo_kitty` today. Show a poster frame plus
   metadata through the existing `kitten icat` image path (about 0.5 s). Then build the streaming
   player. Keep mpv as an opt-in backend for local, non-tmux viewing, where it really is good
   (shared memory, audio).

---

## 1. How video viewing works today

The pipeline, as of `master` at `ea7916d7a7`:

1. The Agents tab `a` action ends in
   `src/sase/ace/tui/actions/agents/_panel_artifact_open.py`. Inside tmux it calls
   `view_registered_artifact_file(s)_in_tmux_pane()`.
2. `src/sase/ace/tui/graphics/_viewer_tmux.py` runs
   `tmux split-window -h -P -F '#{pane_id}' python -m sase.ace.tui.graphics.viewer --kind … <path>`.
   The TUI then decorates the pane via `_viewer_tmux_decoration.py`, which sets
   `pane-border-status top` and a `pane-border-format` that renders `#{pane_title}`.
3. Inside the pane, `run_artifact_sequence_loop()` (`_viewer_loop_sequence.py`) picks the video
   mode. `display_video_artifact()` (`_viewer_loop_media.py`) prints the gold header, then runs
   this command and blocks until mpv exits:

   ```
   mpv --no-config --vo=kitty --keep-open=yes \
       --vo-kitty-alt-screen=no --vo-kitty-config-clear=no \
       --vo-kitty-left=<left> --vo-kitty-top=<top> --vo-kitty-cols=<cols> --vo-kitty-rows=<rows> \
       [--mute=yes] [--loop-file=inf] <extra_mpv_args> -- <path>
   ```

4. Config lives in `ace.artifact_file_viewer.video` (`audio`, `loop`, `vo`, `extra_mpv_args`) in
   `src/sase/default_config.yml`. The viewer subprocess re-loads the merged config itself.

The original design (`sdd/tales/202607/video_artifact_preview.md`, commit `64bbbcaf67`) assumed
"mpv speaks the kitty protocol itself, so video mode does not need the kitten binary". It listed
"mpv kitty-vo under tmux passthrough is the main unknown" as the top risk, and made "verify in a
real tmux pane first" step 1. That risk is exactly what went wrong.

### The environment that matters

| Piece | Version / fact | Source |
| --- | --- | --- |
| Where the TUI runs | athena (Debian 13 trixie), inside tmux, reached from the Mac over SSH | chezmoi README / `ssh_clip_doctor` |
| tmux | 3.5a on athena; 3.4 on apollo and the Mac | `tmux -V` |
| tmux config | `allow-passthrough all` | `home/dot_config/tmux/tmux.conf:54` |
| mpv | **0.40.0** on athena (`/usr/bin/mpv`); not installed on apollo or the Mac | `mpv --version` |
| Terminal | kitty **0.47.0** on the Mac; kitten 0.41.1 on athena | `kitty --version` |
| Typical video artifacts | screen recordings (2560×1548 @ 30 fps, ~7 s, ~0.6 MB) and TUI demos (1920×1080 @ 25 fps, 20–30 s, 0.6–2.5 MB) | `ffprobe` on `~/.sase/artifacts` and `demos/out` |

---

## 2. What is actually slow (measured)

### Method

I wrote a small pty harness. It runs a command inside a fresh pseudo-terminal with a realistic
geometry: 95×55 cells at 1520×1870 px, about a half-screen kitty pane on a Retina Mac. It drains
the output, optionally throttled to emulate an SSH link, and counts:

- bytes;
- kitty APC starts (`ESC _G`);
- frame starts;
- wall time.

For tmux runs, the harness *is* the tmux client's terminal. That means it sees exactly what tmux
would send to kitty over SSH. All tmux runs used an isolated server (`tmux -L <probe>`) with
`allow-passthrough all`. Where noted, they also reproduced SASE's border decoration
(`pane-border-status top`, `pane-border-format "#{pane_title}"`).

- **Hosts:** mpv runs were on athena; GIF and streaming-prototype runs were on apollo.
- **Test clip:** `sase_ace_prompt_history_stash.mp4` (1920×1080, 25 fps, 21.8 s, 891 KB) unless
  stated otherwise.
- **Cleanup:** temporary files and the probe tmux servers were removed afterwards.

### Finding 1: inside tmux, today's command shows nothing and drags tmux down

mpv 0.40's `vo_kitty` writes `ESC _G a=T,f=24,…;<base64> ESC \` with no `ESC Ptmux;` wrapper. The
`--vo-kitty-auto-multiplexer-passthrough` option only appeared in **mpv 0.41.0 (2025-12-21)**, and
it defaults to off. SASE never passes it.

In tmux 3.5a, `input.c:input_exit_apc()` calls `screen_set_title()` on *every* APC string. It then
fires `pane-title-changed`, `server_redraw_window_borders()` and `server_status_window()`. Two
further details:

- This APC path does **not** check `allow-set-title`; only the OSC 0/2 path does. So tmux options
  cannot defend against it.
- APC strings over 1 MB are discarded (`INPUT_BUF_LIMIT`), but mpv's 4 KB chunks are well under
  that.

| Run (athena, 6 s of the demo, harness reads as fast as possible) | Wall time | Kitty APC bytes at the terminal | Pane title afterwards |
| --- | --- | --- | --- |
| mpv in tmux **with SASE's border decoration** | **47.3 s** (≈8× slower than real time) | **0** | `Gm=0;EBIWEBEWEBIWDxEW…` (base64) |
| mpv in tmux, no border or status line | 7.2 s | **0** | — |

So the "incredibly slow" experience comes from three things together:

1. mpv has no tmux passthrough.
2. tmux treats APC as a title.
3. SASE puts the title in the border, so every 4 KB of video costs a border redraw sent over SSH.

The picture itself never arrives in either case.

### Finding 2: even with passthrough, mpv's kitty output is the wrong protocol for remote tmux

`vo_kitty` (mpv source, `video/out/vo_kitty.c`) sends each frame as `f=24` raw RGB, base64-encoded,
in 4 KB chunks. It never uses kitty's zlib option (`o=z`), PNG, or delta frames. Only shared memory
(`--vo-kitty-use-shm`) avoids the copy, and that "only works on the local machine and not via
e.g. SSH" (mpv manual).

In mpv 0.40, the frame's pixel size comes from the **pane's** pixel size. `--vo-kitty-cols/rows`
only affect cursor math, so SASE's bounding flags do not shrink frames. A 1080p video in the probe
pane became 1520×855 px, which is **5,209,877 bytes per frame on the wire**.

| Run (athena, mpv 0.40, outside tmux, 6 s of the demo) | Wall | Frames shown | Effective fps | Wire MB |
| --- | --- | --- | --- | --- |
| Reader unlimited (local pty) | 6.4 s | 150 | 23.3 | 781 (121 MB/s) |
| Reader capped at 12.5 MB/s (≈100 Mbps) | **31.7 s** | 76 | **2.4** | 396 |
| Reader capped at 3.1 MB/s (≈25 Mbps) | **>120 s** (timed out) | 72 | **0.6** | 375 |

Throttling stretches wall time instead of just dropping frames. mpv 0.40 writes synchronously, so
a slow terminal stalls mpv. The status line and keypresses (`q`, `space`) queue behind megabytes of
pixels.

**tmux ceiling.** Synthetic frames in the same wire format (1520×855, DCS-wrapped like mpv ≥ 0.41)
went through tmux 3.5a on localhost at **50 MB/s, i.e. 9.6 fps**. Without tmux, the same frames
ran at 133 MB/s. tmux also marks passthrough output `TTY_NOBLOCK` (`tty_cmd_rawstring`), so it never
discards it under backpressure. A video therefore queues unbounded data in front of every other
pane's redraws, including the SASE TUI pane.

**Placement bug.** In mpv ≥ 0.41, the passthrough path also wraps the frame-positioning
`ESC[row;colf` in passthrough (`append_asprintf_passthrough(p, cmd, TERM_ESC_GOTO_YX, …)`). The
cursor move then goes to kitty directly, in **window** coordinates rather than pane coordinates.
In a right-hand split pane, the video would be drawn over the left pane, and tmux would not know
the image exists, so it would not clear or move it. `kitten icat` avoids this by forcing
**Unicode placeholders** under tmux (`kittens/icat/main.go`: passthrough implies
`use_unicode_placeholder = true`). mpv has no equivalent.

**Conclusion:** upgrading mpv or adding flags (`--vo-kitty-auto-multiplexer-passthrough`, smaller
`--vo-kitty-width/height`, `--vf=fps=8`) cannot make this fast over SSH. Each still sends full
uncompressed frames at playback rate and still places them wrongly in a split pane.

### Finding 3: smaller fixed costs

| Step | Measured cost |
| --- | --- |
| `import sase.ace.tui.graphics.viewer` (cold subprocess) | 0.27–0.33 s (apollo). Mostly the `sase.ace` package `__init__` pulling in patch, config and rich |
| `load_artifact_video_playback_config()` (full merged-config load in the subprocess) | 0.25 s |
| mpv start to first frame (outside tmux) | ~0.3 s |
| `ffprobe` metadata | 0.10 s |
| `ffmpeg` poster PNG at 1488 px | 0.45–0.5 s |

These are worth trimming: pass the already-resolved video config from the TUI via argv/env, and
lazy-import. But they are under a second in total and are not the "incredibly slow" problem.

---

## 3. Critique of the plan and the requirement

**Is fast in-pane video a good idea?** Yes. Agents run on athena; the user sits at a Mac over SSH.
The terminal connection is the only zero-setup channel from the artifact to the user's eyes. In
that setting, an in-pane preview is more robust than any "open a native player" path, which would
need a reverse channel to the Mac, the Mac being awake, file transfer and focus stealing. Images
already work this way, and video should too.

**But "make it faster" is the wrong framing.** The current path cannot be tuned into shape, for
two reasons:

- Under tmux with the installed mpv, it is **functionally broken**: no picture, title spam.
- Even fixed, it is **architecturally mismatched**: raw frames per displayed frame over a remote
  link, absolute placement in a split pane.

This is a redesign of the video backend, not a performance pass. The original plan's key
assumption ("mpv speaks the kitty protocol, so no kitten needed") skipped over exactly what
`kitten icat` handles for images: tmux passthrough, Unicode placeholders, compression and
animation.

**Other process lessons:**

- The plan's own step 1 ("verify `mpv --vo=kitty` renders inside a tmux pane in kitty") either
  didn't happen or was done in a different setup. A cheap **automated pty-plus-tmux probe** would
  have caught this regression class: assert that the client receives kitty APC and that the pane
  title never changes. Section 5 proposes adding one.
- The docs (`docs/reference/agent-attachments.md#video-preview`) currently promise behavior that
  doesn't happen under tmux.

### Requirement adjustments I recommend (explicitly changed)

| # | Adjustment | Why |
| --- | --- | --- |
| R1 | **Reframe "play the video" as "silent animated preview at legible resolution".** Target 8–12 fps; prioritize resolution and text legibility over frame rate. | Artifacts are almost all screen recordings and TUI demos. Legibility matters, 25–30 fps does not. Audio is already muted by default. |
| R2 | **Add explicit latency and bandwidth targets.** First frame < 1 s after the pane opens, over SSH. Real-time playback of a typical 1080p demo on a ≥ 10 Mbps link. Once uploaded, replay and loop cost zero network. | Makes "fast" testable. The prototype meets all three. |
| R3 | **Add a "no collateral damage" requirement.** The preview must never change pane titles, must pace its output, and must not make the SASE TUI pane or other panes laggy. | tmux never discards passthrough data, so an unpaced uploader harms the whole session. |
| R4 | **SASE owns playback keys; mpv is out of the default path.** Same keys as today where possible (`space`, arrows, `r`, `n`/`p`, `z`, `<tab>`, `q`), plus frame-step. **`m` (mute) goes away** in the default backend. | kitty plays the frames, so the SASE viewer loop must interpret the keys. |
| R5 | **kitty is the supported terminal for animated preview** (Unicode placeholders need ≥ 0.28; tested target 0.47). Other terminals get poster plus metadata (and a storyboard later). | This is already de facto true for images, which use `kitten icat`. |
| R6 | **Keep mpv as an opt-in backend** for non-tmux, local, full-fidelity or audio use, with `--vo-kitty-use-shm=yes` when local. | mpv is excellent locally. It just isn't the right default for a remote tmux pane. |
| R7 | (Optional) **A full-fidelity escape hatch:** `o` runs a user-configured external open command, for example a script that copies to the Mac and runs `open`. | Audio and high-fps needs are rare but real. Keep that complexity in user config, not core. |

The backend choice (`kitty` | `mpv` | `poster`) should be an ordinary **config field**, not a SASE
feature flag. Users choose it permanently, per `sase_flags.md`.

---

## 4. Options considered

All numbers are for the 21.8 s 1920×1080 demo unless noted. "Wire" means bytes the terminal must
receive through tmux and SSH.

| Option | Wire bytes (whole clip) | Time to first picture | Sustained need | Verdict |
| --- | --- | --- | --- | --- |
| **A. Today:** mpv 0.40 `vo_kitty` in tmux | 0 image bytes (title spam instead) | never | — | Broken. Hotfix now. |
| **B. mpv ≥ 0.41 with passthrough** | ≈2.8 GB (545 frames × 5.2 MB) | ~0.3 s | ≈130 MB/s; localhost tmux tops out near 9.6 fps; 2.4 fps @ 100 Mbps; 0.6 fps @ 25 Mbps | Reject: bandwidth, wrong placement, and mpv 0.41 isn't in Debian 13. |
| **C. mpv with smaller `--vo-kitty-width/height` and `--vf=fps=8`** | ≈ 8 fps × 2.1 MB at 960×540 ≈ 17 MB/s | ~0.3 s | still >100 Mbps; picture also *physically* small (no `c=/r=` scaling in `vo_kitty`) | Reject. |
| **D. ffmpeg → GIF (cached) → `kitten icat`** | 12–14 MB (icat zlib-RGB sub-rectangle frames) | transcode 3.3–7.4 s, then icat 2.2–3.4 s before its first byte | one-shot upload, then local looping | Viable and simplest (~50 LOC). But a 5–10 s cold start, 256-color palette, no pause/seek unless SASE drives `a=a` with `--image-id`. Fallback option only. |
| **E. Streamed kitty animation (recommended), 1488 px, 10 fps, 5-bit colour** | **21 MB** | **~0.3 s** | ≈1 MB/s average (≈8 Mbps) during the first pass, then 0 | **Recommend.** |
| E′. Same, 4-bit colour | **12.4 MB** | ~0.3 s | ≈0.6 MB/s | Lower-bandwidth profile. |
| E″. Same, 960 px, 8 fps, 5-bit; kitty upscales into the placement | ≈6.7 MB (4.9 MB payload) | ~0.3 s | ≈0.3 MB/s | Slow-link profile; encoder ~8× real time. |
| **F. Cell graphics** (`--vo=tct`, chafa) | ~4.5 MB/s | fast | tmux-native | Reject as default: TUI text in recordings becomes unreadable. Possible non-kitty fallback. |
| **G. Native player on the client** (copy MP4 to the Mac, `open`/IINA) | 0.89 MB (the MP4 itself) | network round-trip plus app launch | — | Best fidelity, but needs a reverse channel, the Mac awake, and focus stealing. Keep as the R7 escape hatch. |
| **H. Poster frame plus metadata only** | ~1–2 MB PNG via icat | ~0.5 s | — | **Phase-0 hotfix** and non-kitty fallback. |

For the 2560×1548 @ 30 fps screen recording (7.5 s), option E at 1488 px / 10 fps / 5-bit sent
**35.5 MB**, about 4.7 MB/s during the first pass. This is the noisy worst case: a real desktop
capture with lots of motion. On links slower than about 40 Mbps, kitty's loading mode briefly
"buffers" during the first pass. That is the reason for adaptive pacing in Phase 2 (drop to 960 px
or 4-bit colour automatically). For the same clip, mpv would need about 1.26 GB
(225 frames × 5.6 MB; computed, not measured).

---

## 5. Recommended solution

### 5.1 Architecture

```
viewer subprocess (tmux pane)                                   kitty (on the Mac)
-----------------------------                                   -------------------
ffprobe (0.1 s) ─► choose frame size/fps from budget
ffmpeg -vf fps=F,scale=W:H -f rawvideo rgb24 ─► frame N
   │
   ├─ quantize (bytes.translate, 5-bit default)
   ├─ diff vs frame N-1 → dirty bounding box (row memcmp + binary search)
   ├─ zlib(level 1–6) → base64 → ≤128 KB chunks → DCS-wrap if $TMUX
   │
   ├─ frame 1:  a=T,U=1 (virtual placement, c=cols,r=rows)  ─────────► image id I, root frame
   │            + print U+10EEEE placeholder grid in image area        (tmux sees plain text)
   │            + a=a,s=2 (run in *loading* mode)                    ─► starts playing at once
   ├─ frame k:  a=f,x,y,s,v,c=k-1,z=gap  (continuation chunks         ─► appended; kitty waits
   │            repeat a=f,q=2)                                          at the end for more
   ├─ end:      a=a,s=3 (loop) or s=1 (stop at end)                    ─► local looping, 0 bytes
   │
key loop (main thread)  ── space/←/→/,/./r ─► a=a,s=1|3, c=<frame>  ─► pause/seek/step, tiny
footer (text, ~4 Hz): ▶ 00:07.3 / 00:21.8 ━━━━━━╸──── buffered 64% · 10 fps · 1488×838
```

Why this design fits:

- **Bytes scale with what changes, not with pixels × fps.** TUI demos change a few rows per frame.
- **Display size is decoupled from transmit size.** A virtual placement's image "will be fit to
  the specified rectangle, its aspect ratio preserved" (kitty graphics-protocol docs). Frame pixel
  size becomes a *bandwidth* knob. `z` (zoom) is nearly free: re-emit a larger placeholder grid,
  and optionally re-stream at higher resolution in the background.
- **Terminal-driven animation is what kitty recommends for networks.** The docs say:
  "client driven animations can be sub-optimal … especially over the network". `s=2` is
  explicitly the "wait for the arrival of more frames" mode, which gives progressive playback for
  free.
- **tmux only ever sees ordinary text** (the placeholder cells) plus passthrough. Placement,
  scrolling, zoom and pane moves behave like images do today.
- **It stays on the right side of the core-backend boundary.** This is terminal presentation for
  the TUI viewer subprocess. A web frontend would just use `<video>`. It belongs in this repo's
  Python, not `sase-core`, and nothing new touches the Textual event loop.

### 5.2 Wire-format rules (gotchas found during research)

1. **Continuation chunks must repeat `a=f,q=2`, not only `m=`.** kitty before 0.49.0 had a bug:
   chunked `a=f` frames whose continuation chunks carry only `m` *replace the root frame*. It was
   fixed in 0.49.0 (changelog "Fix chunked transmission of animation frame data (a=f)…"). The
   user's Mac runs **0.47.0**. `kitten icat` already repeats `a` and `q` on every chunk
   (`tools/tui/graphics/command.go`), so copy that. *My prototype used `m`-only continuations, so
   its wire format must change before use on the Mac.*
2. **Chunk size:** use about 64–128 KB, as kitten does, to cut per-chunk DCS overhead. Stay well
   under tmux's 1 MB DCS limit (`INPUT_BUF_LIMIT`); anything above it is silently discarded.
3. **tmux wrapping:** wrap as `ESC Ptmux; <payload with every ESC doubled> ESC \`. Ensure
   passthrough is enabled for the pane (`tmux set -p allow-passthrough on`), as
   `tui.TmuxAllowPassthrough()` does in kitten. The user's global `all` already covers this.
4. **Image IDs for placeholders** must have non-zero high and middle bytes, so the ID is encoded in
   a 24-bit foreground colour plus a third diacritic. Copy kitten's rejection-sampling rule
   (`kittens/icat/transmit.go`). Print the placeholder grid with the 297-entry
   `rowcolumn-diacritics` table.
5. **Use `q=2` everywhere.** Responses can't come back through tmux and would corrupt the pane's
   input.
6. **Clean up on exit and on `n`/`p`:** send `a=d,d=I,i=<id>` (best effort, including from the
   existing SIGHUP/SIGTERM cleanup handler) so frames don't sit in kitty's memory. Keep the image
   alive for `r` replay within the same viewer session.
7. **Budget kitty memory.** kitty stores decoded frame rectangles. The prototype's 22 s clip at
   1488 px held 240–300 MB uncompressed; at 960 px it was 84 MB. kitty's frame cache is capped at
   5 × 320 MB (`kitty/graphics.c`) and returns `ENOSPC` past that. Default budget: about 400 MB.
   Lower fps, then resolution, for long clips. Past the floor, preview the first N seconds and say
   so in the footer.
8. **Pace output.** Never run more than about 2–3 s of video ahead of the playhead, and keep
   control commands (`a=a`) at the head of the write queue. tmux never drops passthrough bytes,
   so an unpaced upload makes every pane laggy (R3). Write from a writer thread, so the key loop
   never blocks on a full pty.

### 5.3 Player UX

The player keeps the existing artifact-viewer shell: header, footer, `n`/`p`/`z`/`<tab>`/`q`, and
multi-artifact sequences. Changes:

- **Starts instantly:** the first frame appears about 0.3–0.6 s after the subprocess starts, then
  plays while it buffers. The footer shows a timeline and `buffered NN%`.
- **Keys (SASE-owned):**
  - `space`: pause or resume (`s=1` / `s=2|3`);
  - `←`/`→` (and `h`/`l`): seek ∓/± 5 s (`c=<frame>`, clamped to buffered frames);
  - `,`/`.`: frame step while paused;
  - `0`–`9`: jump to 0–90 %;
  - `r`: replay from frame 1 (no re-upload);
  - `o`: optional external open (R7).
- **Position tracking** is open-loop: SASE's own clock, start time plus frame gaps, re-anchored on
  every pause and seek with an explicit `c=`. That is accurate enough for a progress bar.
- **End of clip:** stop on the last frame by default, or loop when `loop: true`.

### 5.4 Configuration (update `default_config.yml` and `sase.schema.json`)

Keep the existing flat keys so current user configs keep working, and add:

```yaml
ace:
  artifact_file_viewer:
    video:
      backend: kitty        # kitty (streamed animation) | mpv | poster
      fps: 10               # preview frame rate (kitty backend)
      max_width_px: 1600    # transmit-size cap; kitty scales into the pane
      color_bits: 5         # 8 = lossless RGB; 4–5 suppress codec noise, shrink bytes 2–3.5×
      frame_budget_mb: 400  # uncompressed frames held in kitty; lowers fps/size for long clips
      loop: false
      audio: false          # mpv backend only
      vo: "kitty"           # mpv backend only
      extra_mpv_args: []    # mpv backend only
```

Also:

- `validate_artifact_file_viewer_dependencies("video")` should require `ffmpeg`/`ffprobe` for
  `kitty`/`poster` and `mpv` only for `mpv`.
- Update `doctor`'s optional-tools rows to match.
- Update the docs: `docs/reference/agent-attachments.md#video-preview` and
  `docs/reference/config/ace-behavior.md`. Read `docs_writing.md` first.

### 5.5 Phasing

**Phase 0: hotfix (≈1–2 h, ship first).** In `display_video_artifact()`, when `$TMUX` is set and
the backend is still mpv `vo_kitty`, do not launch mpv. Instead:

- render a poster frame (`ffmpeg -ss 0 -frames:v 1 -vf scale=…`, ~0.5 s);
- show it through the existing `kitten icat` image path, which already handles tmux correctly;
- print `ffprobe` metadata (duration, resolution, fps, size);
- add a footer hint.

This alone removes the 8× crawl, the base64 pane titles and the tmux load. Add the regression probe
below in the same change.

**Phase 1: streaming kitty player.** Add a new module, for example
`src/sase/ace/tui/graphics/_viewer_video_kitty.py` (encoder, placeholder grid, writer thread,
control commands), plus a player loop in `_viewer_loop_media.py`. Dispatch on `backend`. The
prototype core (diff, chunk, wrap) is about 150 lines; with placeholders, controls, pacing,
budget and cleanup, expect about 400–600 lines plus tests.

**Phase 2: polish.**

- Adaptive pacing: measure blocking-write throughput in the first second and step down fps,
  colour bits, then size, when the first pass falls behind real time.
- `s` storyboard view: an ffmpeg `tile` contact sheet through the image path, useful for long
  recordings.
- The `o` external-open hook.
- Fallback chain: kitty → poster for non-kitty terminals, plus kitty's `e=` feature query
  (kitty ≥ 0.50) when *not* in tmux.
- Viewer startup trims: pass the resolved config via env, and import the viewer without pulling in
  the `sase.ace` package `__init__`. Saves about 0.4 s per open.

### 5.6 Tests

- **Unit tests** (fake stdout, no real ffmpeg or terminal):
  - golden wire-format tests: first-chunk keys, continuation chunks carry `a=f,q=2,m=`, ESC
    doubling, chunk size ≤ 128 KB;
  - property test that composing each dirty rectangle onto the previous frame reproduces the
    current frame;
  - budget → fps/size selection;
  - pause/seek position math;
  - placeholder-grid encoding (ID in foreground colour, diacritics);
  - backend dispatch, including the Phase-0 tmux guard.
- **Integration probe** (slow, opt-in marker). Turn the research harness into a test: run the
  viewer's video mode in an isolated `tmux -L` server inside a pty with pixel geometry, then
  assert that:
  - the client receives kitty APC within 1 s;
  - `#{pane_title}` is unchanged at the end;
  - total wire bytes for a fixture clip stay under budget.

  This would have caught today's failure.
- **Manual acceptance** in real kitty 0.47 on the Mac over SSH to athena:
  - the demo and the screen recording play smoothly;
  - pause, seek and step work;
  - `z` zoom works;
  - the TUI pane stays responsive during the first pass;
  - after `q`, kitty memory is released.

### 5.7 Risks and open questions

- **Rendering not verified on a real kitty.** I measured wire bytes and timings, not pixels. I had
  no display access, and the prototype used absolute cursor placement rather than placeholders.
  Before committing, spend about an hour checking on the Mac (kitty 0.47) that `s=2` loading-mode
  animation renders through a Unicode-placeholder virtual placement under tmux. Both features are
  documented and `kitten icat` combines them for GIFs, but run it anyway.
- **Kitty memory on long clips:** mitigated by `frame_budget_mb`, the 960 px profile, and deleting
  images on exit.
- **Noisy content** (camera video, busy desktops) compresses worse, as the 35 MB screen recording
  shows. Colour quantization and adaptive stepping cover this. GIF-style palettization via ffmpeg
  is a further option if needed.
- **CPU:** pure Python ran at about 3× real time at 1488 px on apollo (16-core Xeon 8168); athena is
  faster. If it ever matters, use NumPy or ffmpeg-side denoising (`hqdn3d`) before reaching for
  Rust.
- **Nested tmux** (local tmux → SSH → remote tmux) would need double wrapping. This is the same
  limitation `kitten icat` images have today; out of scope.

---

## 6. Recommendation

1. **Ship Phase 0 now.** In tmux, replace the mpv `vo_kitty` launch with poster plus metadata
   through the existing `kitten icat` path, and add the pty-plus-tmux regression probe. Today's
   path renders nothing under tmux and degrades the whole session. Removing it is a pure win.
2. **Build Phase 1: a SASE-owned streaming kitty-animation player.** ffmpeg decodes, then dirty
   rectangles, then zlib, then `a=f` frames go to a Unicode-placeholder virtual placement, with
   `s=2` loading-mode playback, SASE-owned keys and paced writes. Make it the default
   `backend: kitty`. Measured through tmux, it starts in about 0.3 s and moves **≈130–230× fewer
   bytes** than mpv `vo_kitty` (12–21 MB versus about 2.8 GB for a 22 s 1080p demo). It replays
   for free and places correctly in split panes.
3. **Keep mpv as `backend: mpv`** for local, non-tmux, full-fidelity or audio use. Use
   `--vo-kitty-use-shm=yes` when local.
4. **Adopt requirement changes R1–R7.** In particular: a silent preview at 8–12 fps that stays
   legible, explicit latency and bandwidth targets, and "no collateral damage to the tmux
   session".

---

## Appendix A: Source references

- **SASE**
  - `src/sase/ace/tui/graphics/_viewer_loop_media.py`: `artifact_video_player_command`,
    `display_video_artifact`
  - `_viewer_loop_sequence.py`: video branch
  - `_viewer_tmux.py`: split-window launch
  - `_viewer_tmux_decoration.py`: `pane-border-status top`, `#{pane_title}` border format
  - `src/sase/default_config.yml`: `ace.artifact_file_viewer.video`
- **mpv** (`gh:mpv-player/mpv`)
  - `video/out/vo_kitty.c`: `KITTY_ESC_IMG "…a=T,f=24,…"`, base64 per frame, 4096-byte chunks,
    GOTO wrapped by `append_asprintf_passthrough`
  - options `use-shm` and `auto-multiplexer-passthrough`, the latter added in commit `d9dc84c0fc`
    and first released in v0.41.0 (2025-12-21)
  - athena runs v0.40.0
- **tmux** (`gh:tmux/tmux` at tag `3.5a`)
  - `input.c`: `input_exit_apc` sets the title with no `allow-set-title` check; `INPUT_BUF_LIMIT`
    is 1 MB; `input_dcs_dispatch` handles passthrough
  - `tty.c`: `tty_cmd_rawstring` sets `TTY_NOBLOCK`
  - `options-table.c`: `allow-set-title`
- **kitty** (`gh:kovidgoyal/kitty`)
  - `docs/graphics-protocol.rst`: Unicode placeholders and virtual-placement fit, animation
    control `s=1/2/3`, network caveat for client-driven animation, storage quota
  - `kittens/icat/main.go`: tmux implies passthrough and placeholders
  - `kittens/icat/transmit.go`: frame `a=f`, `compose_onto`, image-ID rule
  - `tools/tui/graphics/command.go`: zlib, 128 KB chunks, `a`/`q` repeated on continuation chunks
  - `kitty/graphics.c`: 320 MB quota, 5× frame-cache cap
  - `docs/changelog.rst`: 0.49.0 fix for chunked `a=f`

## Appendix B: Raw measurements

```
# athena, mpv 0.40.0, pty 95x55 cells / 1520x1870 px, demo clip --length=6
direct-unlimited      wall 6.43s  781.5MB  150 frames  23.3 fps  5,209,877 B/frame
direct @12.5MB/s      wall 31.71s 396.0MB   76 frames   2.4 fps
direct @3.1MB/s       wall 120s (timeout) 375MB 72 frames 0.6 fps
tmux 3.5a + SASE border decoration: wall 47.34s, kitty APC at client = 0, title = base64
tmux 3.5a, no border/status:        wall 7.17s,  kitty APC at client = 0
synthetic 1520x855 frames: direct 133 MB/s (25.6 fps); tmux DCS passthrough 50.2 MB/s (9.6 fps)

# apollo, GIF path (ffmpeg palettegen/paletteuse, 10 fps)
demo 960px  : transcode 3.25s, 0.99 MB gif, icat via tmux 12.1 MB wire, first byte 2.59s
demo 1520px : transcode 7.36s, 2.25 MB gif, icat via tmux 11.9 MB wire, first byte 3.35s
screencast 1520px: transcode 6.18s, 1.88 MB gif, icat via tmux 14.0 MB wire

# apollo, streaming prototype through tmux 3.4 (wire = bytes at client)
demo 1488x838 10fps raw RGB : 44.2 MB wire, first 0.34s, encode 8.3s, 213 frames
demo 1488x838 10fps 5-bit   : 21.2 MB wire, first 0.35s, encode 7.8s, raw rects 296 MB
demo 1488x838 10fps 4-bit   : 12.4 MB wire, first 0.36s, encode 6.7s, raw rects 239 MB
demo 960x540 8fps 5-bit     : 4.9 MB payload (≈6.7 MB wire), encode 2.6s, raw rects 84 MB
screencast 1488x900 10fps 5-bit: 35.5 MB wire, first 0.63s, encode 9.2s, raw rects 247 MB

# fixed costs (apollo)
viewer import 0.27–0.33s; merged config load 0.25s; ffprobe 0.10s; poster PNG 0.45–0.51s
```
