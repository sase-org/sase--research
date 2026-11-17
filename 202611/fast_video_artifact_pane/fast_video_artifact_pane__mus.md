# Fast video artifacts in a tmux pane: research (`__mus`)

**Question:** Viewing a video artifact in a separate tmux pane (the `a` keymap on
the Agents tab) is "incredibly slow". What is the best way to make it much faster —
and is that even the right goal?

**Verdict up front:** Yes, fix it, but do not chase "mpv-in-a-terminal plays like a
native player". The terminal kitty-graphics path has a hard physics floor (every
frame is PNG-encoded and base64-pushed through the pty). The right target is
**poster in under ~1s, playback starting in ~2s for a local file**, achieved mostly
with cheap fixes: kill the ~0.7s config reload in the viewer child process, cut
mpv's startup probing, and show an ffmpeg poster frame instantly while mpv spins
up. Details and a phased plan are below.

All timings were measured in this checkout (`.venv` Python) unless marked
"unmeasured". mpv is **not installed** on this host, so mpv-side first-frame
latency is estimated from the command shape and mpv's documented behavior, not
observed — flagged wherever it matters.

## 1. How video-in-a-pane works today

Keypress to first frame is a five-stage serial pipeline. (All paths below are
relative to the sase repo root.)

1. **Pick.** `a` is bound to `open_artifact_files`
   ([bindings.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/bindings.py:252)).
   `action_open_artifact_files`
   ([_panel_artifact_actions.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/actions/agents/_panel_artifact_actions.py:64))
   pushes an `ArtifactFileSelectionModal`; on confirm it calls `_open_artifact_files`
   ([_panel_artifact_open.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/actions/agents/_panel_artifact_open.py:17)).
   Rows without stored bytes (VCS-backed rows) are first materialized on a worker
   thread (`asyncio.to_thread(_materialize_artifact_file_entries ...)`,
   [_panel_artifact_open.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/actions/agents/_panel_artifact_open.py:126)),
   i.e. bytes are fetched/copied out of the VCS object store **before anything
   opens**. For a large video this step alone can dominate everything below.
2. **Split.** Inside tmux, the ACE process runs `tmux split-window -h ... <viewer
   command>` ([_viewer_tmux.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/graphics/_viewer_tmux.py:94)),
   then decorates panes (titles, window options — roughly a half-dozen serial
   `tmux` subprocess round-trips in
   [_viewer_tmux_decoration.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/graphics/_viewer_tmux_decoration.py:86))
   and arms a SIGUSR1 close-notification PID
   ([_panel_artifact_pane.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/actions/agents/_panel_artifact_pane.py:114)).
3. **Boot a fresh interpreter.** The new pane runs
   `sys.executable -m sase.ace.tui.graphics.viewer <paths> [--kind ...]`
   ([_viewer_tmux.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/graphics/_viewer_tmux.py:300)).
   This is a cold Python process on every open: interpreter + viewer imports.
4. **Reload merged config.** The sequence loop lazily resolves
   `load_artifact_video_playback_config()` on the first video artifact
   ([_viewer_loop_sequence.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/graphics/_viewer_loop_sequence.py:134)),
   which calls `sase.config.load_merged_config()` and picks out
   `ace.artifact_file_viewer.video` (`audio`, `loop`, `vo`, `extra_mpv_args`;
   defaults in
   [default_config.yml](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/default_config.yml:556)).
5. **Block on mpv.** `display_video_artifact` prints a Rich header, then runs
   mpv **synchronously** and blocks until it exits
   ([_viewer_loop_media.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/graphics/_viewer_loop_media.py:175)):
   `mpv --no-config --vo=kitty --keep-open=yes [--mute] --vo-kitty-{alt-screen,no-config-clear,left,top,cols,rows} ... -- <path>`
   ([_viewer_loop_media.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/graphics/_viewer_loop_media.py:37)).
   Nothing is painted between "pane appears" and "mpv's first frame" except the
   header. mpv is a hard requirement: without it the viewer returns
   `missing_mpv` (`validate_artifact_file_viewer_dependencies`,
   [_viewer_render.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/ace/tui/graphics/_viewer_render.py:140)).

The direct `sase artifact open <ref>` path for video is different and already
lean: it builds the same mpv command and execs it with no tmux pane and no
viewer wrapper
([open.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_14/src/sase/artifact_cli/open.py:170)).
Keep that path as-is; the problem is specific to the pane path.

## 2. Where the time actually goes (measured)

| Stage | Cost (this checkout) | Notes |
|---|---|---|
| Viewer `--help` (interpreter + argparse, proxy for cold boot) | **0.29s** | `.venv` Python; full viewer import 0.33s. Paid on every open. |
| `import sase.config` | 0.13s | Subset of the above. |
| `load_merged_config()`, first call in a fresh process | **0.64–0.68s** | Timed in-process twice; second call 1ms (cached) — but the viewer pane is always a fresh process, so it always pays full price. Also prints a stale-`sase_core_rs`-wheel warning to stderr on this checkout. |
| `tmux split-window` + decoration round-trips | unmeasured, est. 0.05–0.2s | ~6 serial `tmux` spawns; small but on the critical path. |
| ffmpeg poster extract (720p test file, `-ss 0.5 -frames:v 1`) | **0.32s** | Includes ffmpeg startup. `ffprobe` duration/size: **0.11s**. |
| mpv startup + first kitty frame | **unmeasured (mpv absent here)** | Expected dominant term: demuxer probe, stream selection, audio-device init (even muted), kitty-vo init, first PNG encode. |
| VCS materialization of byte-free rows | unmeasured, unbounded | `git show`-scale copy before the pane even opens; linear in file size. |

Takeaway: roughly **1 second of fixed, removable overhead** (cold interpreter +
config reload) sits in front of mpv, and the pane shows nothing useful while mpv
starts. The "incredibly slow" feel is likeliest the sum of: materialization for
remote/VCS rows + ~1s fixed overhead + mpv vo=kitty first-frame latency (PNG
encode per frame, base64 through tmux passthrough) + full-res decode of large
agent recordings.

## 3. Critique: is "make the tmux pane faster" the right goal?

**Yes, with a scope correction.** Fast triage of agent-produced screen recordings
is a legitimate loop — the Agents tab is where you already are, and on a remote
host (or inside tmux over SSH) there is no local-window player to hand off to,
which is exactly why the in-terminal mpv path exists. Abandoning it would
strand remote users.

But three adjustments to the goal are warranted:

1. **Do not promise native-player smoothness.** `vo=kitty` will never do
   high-framerate full-HD through a pty; its niche is "watchable evidence
   preview", and the docs already position it that way
   ([agent-attachments.md](https://github.com/sase-org/sase/blob/main/docs/reference/agent-attachments.md#video-preview)).
   Judge success by *time-to-first-meaningful-pixels*, not fps.
2. **Do not start by replacing the player.** mpv with `--no-config` and pinned
   geometry is the right engine (documented, configurable via
   `ace.artifact_file_viewer.video`, tested in
   `tests/ace/tui/artifact_file_viewer/test_sequence_loop.py`). The fixed
   overhead around it is cheaper to remove and benefits every artifact kind.
3. **Treat "no mpv" as a supported state, not an error.** mpv is missing on at
   least one real dev host (this one). A poster-frame mode that works with only
   ffmpeg + kitten (both present) turns a hard `missing_mpv` failure into a
   useful degraded preview and incidentally fixes first-paint latency.

What I would **not** do: build a second player (ffplay needs X and is already
installed here but useless over SSH; `vo=tct`/chafa block output is a
downgrade for real footage); pre-generate thumbnails at record time (couples
the agent runner to TUI needs); or stream over the network (no such transport
exists in this path — files are local by the time the viewer runs).

## 4. Options considered

- **A. Kill the fixed overhead (cheap, invisible).** Pass the four video fields
  from the already-running ACE process to the viewer child via environment
  (child keeps `load_merged_config()` only as fallback), and/or make the child
  import lazily. Removes ~0.7s on every open. No UX change, tiny blast radius.
- **B. Poster-first preview (best perceived-latency win).** On pane open,
  extract one frame with ffmpeg (~0.3s, ffmpeg/ffprobe already on PATH) and
  paint it with the existing `kitten icat` path plus duration/resolution from
  ffprobe (~0.1s); then start mpv (same keypresses) or on explicit play key.
  Works even when mpv is absent. This is the only option that helps the worst
  case (huge file, slow decode) because *something* is visible in <0.5s.
- **C. Trim mpv's own startup (cheap, evaluate each flag).** Candidates:
  `--aid=no --ao=null` (skip audio-device probing; audio is muted by default
  anyway), `--hwdec=auto-safe`, `--demuxer-readahead-secs` tuning, and
  `--vo=kitty` only when the terminal actually speaks kitty graphics (fall back
  to the configured `vo`, e.g. `tct`, otherwise). Each needs a before/after
  first-frame measurement with mpv present — do not ship on theory.
- **D. Reuse one persistent viewer pane (medium).** `split-window` + fresh
  interpreter + reflow on every open becomes "open once, retarget on `a`".
  Saves ~0.4s plus layout churn, and removes the pane open/close tracking
  complexity (`_track_artifact_file_tmux_pane`). Costs real state management
  (stale pane, crashed viewer, focus protocol) — do this only if A–C still
  feel slow.
- **E. Native playback when possible (small, additive).** If a local display
  exists (`$DISPLAY`/`WAYLAND_DISPLAY`, not SSH-forwarded tmux), prefer
  `mpv --vo=gpu` (real hw decode) or even the existing `xdg-open` route used
  for PDFs. Auto-detect with config override; remote tmux keeps vo=kitty.
- **F. Pre-warm on selection (small).** When the artifact modal highlights a
  video row, resolve config + extract the poster in the background so `Enter`
  opens onto a warm cache. Nice-to-have; overlaps with B's cache.

## 5. Requirements adjustments (called out explicitly)

1. **Set an SLO, not "much faster":** poster ≤1s, mpv first frame ≤2.5s for a
   local ≤1080p file. Without this, "fast enough" is untestable.
2. **Make mpv optional:** poster + metadata view must work with ffmpeg/kitten
   only; `missing_mpv` becomes a warning banner, not a dead end. (Justified:
   mpv is absent on real hosts; ffmpeg is already effectively required.)
3. **Add per-stage timing telemetry** (split → interpreter-ready → config →
   poster → mpv-first-frame, debug log) so the next complaint is diagnosable
   instead of vibes-based. Cheap `time.perf_counter` spans.
4. **Keep the tested contracts stable:** `artifact_video_player_command`'s
   argument shape and the `ace.artifact_file_viewer.video` config keys are
   pinned by tests and docs — extend (new flags/keys), don't rename.
5. **Materialization needs a progress story:** for VCS-backed rows, show that
   bytes are being fetched (size + spinner) rather than a hung modal; consider
   extracting the poster *during* materialization since the bytes are in hand.

## 6. Recommended solution

**Phase 1 (small, do first): A + B + telemetry.**

1. ACE passes `SASE_ARTIFACT_VIDEO_{AUDIO,LOOP,VO,EXTRA_ARGS}` (or one JSON
   env var) into `split-window -e`; the viewer child uses it and keeps
   `load_merged_config()` as fallback. Deletes ~0.7s.
2. Viewer paints an ffmpeg poster via the existing `kitten_icat_command`
   path immediately, with ffprobe duration/resolution in the header, then
   execs mpv over it (same UX, one step). Poster path doubles as the
   no-mpv degraded mode (REQ-2).
3. Add the timing spans (REQ-3) and evaluate the mpv flag candidates in C
   with real first-frame numbers before shipping any.

**Phase 2 (only if Phase 1 misses the SLO): D**, persistent viewer pane;
**E** can ride along any time as an additive auto-detect.

**Explicit non-goals:** no new player engine, no record-time thumbnail
pipeline, no network streaming, no changes to `sase artifact open` (already
lean).

## 7. Gaps and how to close them

- mpv first-frame latency with `vo=kitty` was not measurable here (no mpv on
  this host). Close with: `time mpv --no-config --vo=kitty <720p clip>` on
  apollo, then A/B each candidate flag from option C.
- Whether the reporter's pain is local files or VCS-materialized rows changes
  the priority of REQ-5 vs Phase 1. The telemetry in Phase 1 answers this
  permanently.
- Kitty-graphics passthrough (`allow-passthrough`) and terminal frame-rate
  caps were not audited; if first frame is fast but playback stutters, that —
  plus decode resolution caps (`--video-scale`/`--vf=scale`) — is the next
  place to look.

*Methods: cold-boot, config-load, and ffmpeg/ffprobe timings measured
directly in this checkout (see §2); pipeline structure read from the sources
cited in §1; mpv-side claims marked unmeasured. No peer-report material was
consulted.*
