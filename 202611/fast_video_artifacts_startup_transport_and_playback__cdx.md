# Faster video artifacts: startup, terminal transport, and playback

Researcher: **cdx** · 2026-11-17 · Independent research for swarm 54

## Finding

Improving this experience is worthwhile, but “make the tmux video viewer faster” combines three different problems: time until the first frame, sustained playback, and responsiveness of controls. Fix and measure them separately.

There is a concrete startup opportunity in SASE: every newly launched viewer reloads the complete merged configuration before playing a video. In local measurements, that first configuration load took **620–688 ms**, compared with **1–2 ms** for a second call in the same process. Separately, the Kitty output path sends decoded RGB pixels through the terminal. That is a poor transport for full-resolution video across SSH, even when the source video is small.

My recommendation is to retain a fast, explicitly budgeted terminal preview, remove unnecessary viewer startup work, and offer playback on the user's computer for full-quality viewing. Do not start by writing another video decoder, pre-extracting every frame, or building a new streaming service.

## Scope and evidence

I inspected SASE at `ea7916d7a7084abc0d1fe2ffe9a5f8f729295f18`, the linked Rust core at `d20108657804cfc257342b0bfb4617ea8bc61a0f`, and the configured chezmoi repository at `1242f0765b3a046f18b4f176d25a63ac8be46a25`. Upstream mpv was inspected locally at `f92afa75cdb06e077a9ecd9a9ec2eb36b16327c2`, including release tags `v0.41.0` and `v0.42.0`. External repositories were opened through `sase repo open`.

I did not inspect another researcher’s report, chat, or findings. No application code or user configuration was changed.

**Limits:** this agent environment has tmux 3.4, FFmpeg 6.1.1, and `kitten`, but no `mpv` executable on PATH. It reports `TERM=tmux-256color` and a forwarded X display. Those facts describe this process, not necessarily the session where the user experiences the problem. I could measure viewer startup components and inspect implementation, but could not measure end-to-end video playback, network throughput, visible frame rate, or input latency. The transport explanation is strongly supported by source; it is not a measured diagnosis of the user's particular clip.

## What actually runs today

The relevant path is:

1. The Agents `a` action collects files and opens the selection modal.
2. Selection calls `_open_artifact_files()`. VCS-only artifacts are materialized off-thread first; files already on disk skip that step.
3. The tmux path runs `tmux split-window -h`, starting a new Python interpreter with `-m sase.ace.tui.graphics.viewer`.
4. The viewer resolves its terminal area and video settings, clears the pane, and launches mpv.
5. The viewer waits for mpv to exit, then resumes its own navigation prompt.

Sources: [Agents selection](https://github.com/sase-org/sase/blob/ea7916d7a7084abc0d1fe2ffe9a5f8f729295f18/src/sase/ace/tui/actions/agents/_panel_artifact_actions.py), [opening and materialization](https://github.com/sase-org/sase/blob/ea7916d7a7084abc0d1fe2ffe9a5f8f729295f18/src/sase/ace/tui/actions/agents/_panel_artifact_open.py), [tmux launch](https://github.com/sase-org/sase/blob/ea7916d7a7084abc0d1fe2ffe9a5f8f729295f18/src/sase/ace/tui/graphics/_viewer_tmux.py), and [viewer loop](https://github.com/sase-org/sase/blob/ea7916d7a7084abc0d1fe2ffe9a5f8f729295f18/src/sase/ace/tui/graphics/_viewer_loop_sequence.py).

The default command is effectively:

```text
mpv --no-config --vo=kitty --keep-open=yes
    --vo-kitty-alt-screen=no --vo-kitty-config-clear=no
    --vo-kitty-left=… --vo-kitty-top=…
    --vo-kitty-cols=… --vo-kitty-rows=…
    --mute=yes -- /absolute/artifact/path.mp4
```

The current configuration has `audio: false`, `loop: false`, `vo: kitty`, and an empty `extra_mpv_args` list. Loading the merged settings in this environment returned those values too. The command does not set a pixel limit, frame-rate budget, software-scaling profile, shared-memory transfer, or multiplexer passthrough. `--no-config` also means a user's normal mpv configuration will not supply missing optimizations. Sources: [command and configuration loader](https://github.com/sase-org/sase/blob/ea7916d7a7084abc0d1fe2ffe9a5f8f729295f18/src/sase/ace/tui/graphics/_viewer_loop_media.py) and [bundled configuration](https://github.com/sase-org/sase/blob/ea7916d7a7084abc0d1fe2ffe9a5f8f729295f18/src/sase/default_config.yml).

Two distinctions matter:

- **There is no video-to-PNG preprocessing stage here.** Video bypasses the PDF/image page renderer. Optimizing PDF conversion or its page cache will not fix this path. [Rendering dispatch](https://github.com/sase-org/sase/blob/ea7916d7a7084abc0d1fe2ffe9a5f8f729295f18/src/sase/ace/tui/graphics/_viewer_render.py).
- **mpv waiting in the viewer process is not itself a Textual event-loop freeze.** That subprocess owns playback and terminal input. However, launching and decorating the tmux pane still involve synchronous subprocess calls from the TUI action path, and terminal traffic can affect the shared display independently of Python's event loop. Move launch work off the UI pump while retaining main-thread signal handling and UI updates. [Pane tracking](https://github.com/sase-org/sase/blob/ea7916d7a7084abc0d1fe2ffe9a5f8f729295f18/src/sase/ace/tui/actions/agents/_panel_artifact_pane.py).

## Measurements: an avoidable startup cost

I used the installed SASE Python interpreter with `PYTHONPATH` pointing at this checkout's `src`, captured subprocess output, and ran three fresh processes per case. These are small diagnostic samples on a shared server with warm filesystem caches, not a production latency distribution.

| Operation | Three observed times | Median |
|---|---|---:|
| Empty Python process | 30.2, 23.5, 20.9 ms | 23.5 ms |
| Viewer module `--help` | 641.6, 336.8, 310.3 ms | 336.8 ms |
| Import viewer helpers and load video configuration, whole process | 1559.9, 1224.9, 1084.3 ms | 1224.9 ms |
| Read-only `tmux display-message` | 6.6, 6.2, 6.1 ms | 6.2 ms |

A subsequent isolated measurement timed configuration loading after imports:

| Configuration call | Run 1 | Run 2 | Run 3 |
|---|---:|---:|---:|
| First call in fresh process | 688.0 ms | 671.3 ms | 620.3 ms |
| Second call in same process | 1.8 ms | 1.3 ms | 1.3 ms |

A separate cProfile run took about 0.98 s in the loader, with substantial cumulative time under local configuration snapshot/trust evaluation, project identity, configuration merging, imports, and synchronization. Cumulative times overlap and must not be added. The existing merged-config cache is process-local, so a new viewer cannot reuse the TUI's already populated cache. [Config loader and cache path](https://github.com/sase-org/sase/blob/ea7916d7a7084abc0d1fe2ffe9a5f8f729295f18/src/sase/config/_sources.py).

**Implication:** pass the viewer a narrow snapshot of the already-resolved playback settings. Preserve normal trust evaluation in the parent; do not bypass it or read untrusted project YAML directly. The standalone viewer can retain its existing load path. Refresh the snapshot when the effective configuration changes, rather than introducing a permanent second configuration cache.

Also consider a lighter viewer entry point if import profiling justifies it: the graphics package eagerly imports image/rendering helpers even for a video. The `--help` measurement is only a bootstrap proxy; it includes argparse and process exit and is not time to first frame. The tmux measurement is likewise a read-only RPC baseline, not a split-window benchmark. These results do **not** establish that pane creation is the main delay.

## Why playback can remain slow after startup is fixed

### Pixel transport dominates surprisingly early

In the inspected mpv implementation, the Kitty driver scales into an RGB24 frame, copies it, base64-encodes it, and emits terminal graphics chunks. Its direct transport does not send H.264/HEVC/VP9 packets or exploit temporal video compression. Shared memory is a separate path. [mpv Kitty driver](https://github.com/mpv-player/mpv/blob/f92afa75cdb06e077a9ecd9a9ec2eb36b16327c2/video/out/vo_kitty.c).

For direct transport, the approximate encoded payload rate is:

```text
RGB bytes × base64 overhead × frames/second
= width × height × 3 × 4/3 × fps
≈ width × height × 4 × fps
```

| Output canvas and frame rate | Base64 payload, MB/s | Equivalent Mbit/s |
|---|---:|---:|
| 1920×1080 at 30 fps | 248.8 | 1990.7 |
| 1280×720 at 30 fps | 110.6 | 884.7 |
| 960×540 at 24 fps | 49.8 | 398.1 |
| 640×360 at 15 fps | 13.8 | 110.6 |
| 480×270 at 12 fps | 6.2 | 49.8 |

These are calculated terminal payloads, not observed wire traffic. They omit escape framing and transport overhead; SSH compression, if enabled, may reduce actual network bytes. Terminal parsing, copying, rendering, and contention remain additional costs. A nominal 100 Mbit/s link cannot carry the 640×360/15 fps case uncompressed, even before overhead.

The Kitty protocol documentation independently explains the remote-client requirement to transfer pixel data in base64 chunks. Its shared-memory alternative requires access to the same memory namespace; a remote server cannot use its shared memory to feed the laptop's terminal. [Kitty transport specification](https://sw.kovidgoyal.net/kitty/graphics-protocol/#transferring-pixel-data).

### Cell layout is not a pixel budget

SASE supplies rows and columns, but the mpv driver's `get_win_size()` handles cell dimensions and pixel dimensions separately. In v0.42.0 it allocates and transmits the output canvas using pixel width and height. Changing rows/columns does not itself impose a proportional reduction in those pixels.

Consequently, “we already fit the pane” is not proof of bounded traffic. Nor is `--vf=scale=640:-2` alone: the output driver can scale the small input back to its larger canvas. Set an explicit output pixel budget and verify the resulting dimensions. A small canvas may display physically smaller in the pane, especially on a high-DPI screen; do not promise full-pane display without separately validating placement and scaling behavior. This detail is visible in the driver source linked above.

### Faster upstream code helps, but cannot remove the transport cost

The inspected repository tags date mpv v0.42.0 to 2026-11-03. It includes the October terminal writer/swapchain and resize work. Those changes serialize output and move writes to a bounded writer thread; v0.41.0 predates that implementation. Benchmark the user's installed version against a supported recent build before inventing a substitute. This is a comparison recommendation, not a request to reinstall anything globally. [Terminal swapchain implementation](https://github.com/mpv-player/mpv/blob/v0.42.0/video/out/terminal_swapchain.c).

## Alternatives and tradeoffs

| Approach | What it improves | Main cost or limitation | Assessment |
|---|---|---|---|
| Pass resolved settings; reduce import work | Startup on every open | Must retain configuration scope and trust semantics | First implementation |
| Tune mpv scaling, pixel canvas, and frame rate | CPU and terminal payload | Preview loses detail or smoothness | Best short-term in-pane improvement |
| Kitty shared memory | Local pixel transfer | Only works when player and terminal share accessible memory | Useful verified local optimization |
| Persistent viewer/mpv with IPC | Repeated launches and navigation | Lifecycle, cancellation, resize, input ownership; same pixel traffic | Add only if launch/reopen measurements justify it |
| Download compressed original and open locally | Playback quality and terminal load | Initial copy and local opener integration | Simplest full-quality remote path |
| Raw-byte HTTP media endpoint and local player/browser | Progressive playback and seeking | Authentication, range serving, client handoff, codec compatibility | Good later extension, not prerequisite |
| Posters/contact sheets | Almost immediate inspection | Cannot replace motion, timing, audio, or seeking | Complement or fallback |
| Pre-extract every frame / encode GIF | Little architectural benefit | Startup work, storage, quality loss; terminal still transports images | Reject as the main fix |
| Switch to sixel or ANSI/character rendering | Some compatibility cases | No automatic video compression benefit; image fidelity changes | Explicit fallback, not default performance strategy |
| Custom terminal video engine or WebRTC stack | Potential specialized optimizations | Large maintenance/operational scope | Unjustified for this request |

## Adjustments to the requirements

These are proposed changes, not assumptions that the user already requested them:

1. **Define three acceptance criteria:** first useful visual, sustained playback at intended duration, and input response. “Fast” should not mean a smooth clip that takes seconds to appear, or an instant frame followed by slow-motion playback.
2. **Distinguish Preview from Original playback.** Permit a bounded-resolution/frame-rate preview in the existing pane, but label it clearly. Text-heavy screencasts need a full-detail route; silent quality reduction is an unacceptable sole solution.
3. **Allow an explicit client-side Original action.** Retain the current `a` selection workflow and terminal preview. Let full-quality playback use a local native window or browser when the terminal is remote. Avoid automatically opening an unexpected desktop window.
4. **No mandatory preprocessing before the first useful visual.** Generate a poster or proxy lazily only when measured demand warrants it. Keep the original intact; cache derivatives by immutable artifact identity/content plus transform settings.
5. **Make audio semantics explicit.** Today's `audio: false` produces muted playback, which can still initialize/decode audio and can be unmuted inside mpv. Switching to `--audio=no` saves that work but changes behavior: audio is disabled, not merely muted. Adopt that only for a clearly defined silent preview, with Original playback retaining audio.
6. **Support the actual topology.** Local, SSH, and nested tmux/SSH are separate test cases. An inherited `SSH_CONNECTION`, `DISPLAY`, or `TERM` is not sufficient evidence that shared-memory access or a client-local opener will work.

## Concrete implementation scope

### Startup and responsiveness

Pass a validated playback-settings snapshot from the parent into the child viewer. Use the existing resolved configuration and argument quoting conventions. Keep the standalone fallback. Avoid starting another persistent daemon merely to retain four settings.

Perform the pane-launch subprocess and decoration queries outside Textual's serial pump, with bounded subprocess timeouts, coalescing of repeated opens, and a visible opening state. Keep signal installation and UI mutation on the main thread. Do not move `_with_artifact_file_viewer_notify_pid()` wholesale into a worker: it currently installs a signal handler and temporarily mutates process environment. Pass launch context explicitly so concurrent opens cannot race over that environment variable.

Record timestamps around selection, materialization, split completion, child startup, configuration readiness, mpv spawn, and playback readiness. A player event such as `playback-restart` is a useful approximation for readiness, not proof that pixels have reached the user's screen.

### Terminal preview

Prototype using the existing `extra_mpv_args` before adding a broad configuration surface. A starting experiment is:

```yaml
ace:
  artifact_file_viewer:
    video:
      vo: kitty
      audio: false
      extra_mpv_args:
        - --profile=sw-fast
        - --audio=no
        - --vo-kitty-width=640
        - --vo-kitty-height=360
        - --vf=lavfi=[fps=15]
```

**This is an experiment, not a tested production preset.** Check option support, aspect ratio, high-DPI readability, and framing on the target mpv/terminal version. The YAML is additive to the existing SASE-generated command. The pixel budget reduces the transmitted canvas; the FPS filter reduces frame submissions while retaining normal elapsed playback time. It may duplicate frames for lower-FPS sources, so production code should cap rather than blindly raise a source's frame rate. Local `ffmpeg -h filter=fps` confirmed the available constant-FPS filter; mpv documents its libavfilter bridge in [its filter reference](https://github.com/mpv-player/mpv/blob/f92afa75cdb06e077a9ecd9a9ec2eb36b16327c2/DOCS/man/vf.rst).

`sw-fast` selects cheaper software conversion/scaling; it does not solve network saturation. The built-in profile is defined in [mpv's profile source](https://github.com/mpv-player/mpv/blob/f92afa75cdb06e077a9ecd9a9ec2eb36b16327c2/etc/builtin.conf). Keep diagnostics available rather than hiding every error with `--really-quiet`. Do not use `--untimed`, change playback speed, or assume `--framedrop=vo` is new optimization: normal VO frame dropping is already the upstream default.

Separately test `--vo-kitty-auto-multiplexer-passthrough=yes` on supporting mpv builds. It first appears in the inspected v0.41.0 release lineage. The chezmoi tmux configuration already sets `allow-passthrough all`; SASE's command does not enable mpv's corresponding option. This is a compatibility/placement check, not a bandwidth optimization. Nested tmux needs its own validation.

For a genuinely local terminal, test `--vo-kitty-use-shm=yes`; keep direct transfer as fallback. Prefer a bounded capability probe to guessing locality from environment variables. Both settings and their limits are described in the [official mpv manual](https://mpv.io/manual/stable/#video-output-drivers).

If 640×360/15 fps cannot remain timely, trying 480×270/12 fps is a useful diagnostic, but do not continue reducing quality until a screencast is unreadable. That is the point to use Original playback on the client.

### Full-quality playback on the client

For an initial implementation, use a compressed-file download to a client cache and a local native opener. The cache can key off artifact identity/content digest, download atomically, and reuse the bytes for repeated plays. Large files need progress and cancellation. Whole-file transfer delays initial playback, so it is appropriate for short artifacts, not a universal solution.

Kitty already offers remote-file download/open behavior. It provides a useful manual prototype before building integration, but ordinary nested SSH has documented host-discovery limitations. Do not infer that a hyperlink to an arbitrary remote path will always open the correct machine's file. [Kitty remote files](https://sw.kovidgoyal.net/kitty/kittens/remote_file/).

A server-side `xdg-open` or `mpv --vo=gpu` is not automatically client playback. A forwarded X display also does not establish that compressed media is decoded locally. Explicitly distinguish the machine holding the artifact from the machine displaying it.

If large clips and seeking make full downloads inadequate, extend existing Rust gateway infrastructure with an authenticated raw-byte media route. Reuse artifact resolution/identity, bound access to the requested artifact, and support byte ranges, correct content type/length, cancellation, and stable content identity. Avoid a general directory server. A browser cannot use the current fleet content API directly as its video source: that route is a POST returning bounded base64 ranges in JSON, despite the wire type having `supports_range`. HTTP media range responses are a distinct interface. [Existing gateway content contract](https://github.com/sase-org/sase-core/blob/d20108657804cfc257342b0bfb4617ea8bc61a0f/crates/sase_gateway/src/contract.rs), [gateway routes](https://github.com/sase-org/sase-core/blob/d20108657804cfc257342b0bfb4617ea8bc61a0f/crates/sase_gateway/src/routes/router.rs), and [HTTP range semantics](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Range_requests).

Native mpv offers wider format tolerance than assuming every artifact can play in an HTML video element. A browser route should detect unsupported formats and offer a native download/open fallback; add transcoding only when needed. Keep authorization compatible with how the chosen client sends requests—an HTML video URL cannot simply inherit arbitrary application bearer headers.

Shared artifact resolution, cache/derivative policy, authorization, and transport contracts belong in `sase_core`, with HTTP delivery in `sase_gateway`. Python can own tmux layout, viewer subprocess glue, and Textual state. Any newly consumed Rust binding requires advancing SASE's `sase-core-revision.txt` after the core change.

## How to validate the choice

Use at least one text-heavy screencast, one motion-heavy clip, and one larger/high-resolution artifact. Include cold viewer processes, repeated opens, stored and VCS-materialized artifacts, direct local terminal, SSH plus tmux, and the user's nested layout if applicable. Record actual mpv, terminal, and tmux versions and both pane cell and pixel dimensions.

Run a small comparison:

1. Existing SASE command.
2. Same command with a settings snapshot and leaner bootstrap.
3. `sw-fast` alone, then explicit pixel/FPS budgets.
4. Verified-local shared memory where applicable.
5. Original compressed file played on the client.

Measure selection-to-first-visual, player-spawn-to-first-visual, seek/pause/quit response, effective displayed frame rate, elapsed media time versus wall time, CPU, and transport volume. Do not use output redirected to `/dev/null` as evidence of terminal performance. A decode-only benchmark is useful specifically to isolate decoding from presentation.

Suggested **initial targets to validate**, not achieved results: first useful visual within 500 ms for an already-local cached artifact; input response within 100 ms; a declared 12–15 fps preview that tracks real elapsed time without growing backlog; and no material regression in other TUI interactions. Also test ending playback, repeated `q`, replay, resizing, zoom, pane close, and return to the Agents pane. With `--keep-open=yes`, EOF keeps mpv alive and SASE's own navigation prompt does not resume until mpv exits; communicate or simplify that ownership instead of treating it as unexplained slowness.

Tests should cover settings propagation and invalidation, command construction, capability fallback, cancellation/cleanup, and the absence of blocking work on the UI pump. Add byte-range/authorization and VCS identity tests only if implementing the media route. Update default configuration and help when introducing user-facing controls. Real terminal playback measurements remain necessary; mocked subprocess tests cannot validate this improvement.

## Recommended solution

**Ship the startup fix and a bounded mpv terminal preview first, while preserving an explicit Original playback path on the user's computer.** Reuse the parent's trusted settings, move pane launch work off the UI pump, measure first-frame readiness, and test `sw-fast` with genuine output-pixel and frame-rate limits. Use shared memory only when local access is verified.

For SSH viewing where full fidelity matters or the preview still misses its latency target, transfer the compressed original and decode on the client. Start with a cached download/native opener; add a raw-byte range endpoint to the existing Rust gateway only when file size and seeking justify it. This addresses the actual transport limit without committing SASE to maintaining another media engine or streaming platform.
