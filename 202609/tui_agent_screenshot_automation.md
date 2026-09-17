# Agent-Driven Screenshots of a Real `sase tui` Instance

**Date:** 2026-09-17
**Author:** sase agent (research), for Bryan Bugyi
**Goal:** Decide the best way to let sase agents spin up a real `sase tui` instance on
the local machine — and ideally on any tailnet machine — emulate user actions
(keypresses), and produce a PNG screenshot that looks like what the user would see,
so agents can verify the visual impact of their changes.

---

## 1. Problem Statement and Requirements

An agent working on the TUI today can run the visual snapshot suite, but has no
one-command way to answer "what does *my* change actually look like in a real, running
`sase tui`?" The requested capability:

1. Spin up a **real instance** of the TUI via the actual `sase tui` command (not only an
   in-process test harness).
2. **Emulate user actions** — keypresses at minimum.
3. **Capture a PNG** of the resulting screen.
4. The PNG should look **identical to what the user would see** on their machine.
5. Stretch goal: do all of the above on **any tailnet machine** (`athena`, `apollo`,
   `mac` — Tailscale SSH, chezmoi-managed `~/.ssh/tailnet.conf` aliases; `mac` is
   best-effort/often offline).

A useful precision on requirement 4, because it drives the whole design: a terminal UI
has no single canonical pixel rendering. What the user "sees" is the character grid +
colors + attributes that Textual draws, rasterized by *their* terminal emulator with
*their* font. Three fidelity tiers exist:

- **Tier 1 — grid fidelity:** identical characters, colors, layout, theme. This is what
  matters for "did my change break/improve the UI".
- **Tier 2 — canonical pixel fidelity:** deterministic pixels from a project-blessed
  renderer and font (what sase's visual snapshot suite already defines: resvg +
  bundled Fira Code).
- **Tier 3 — literal pixel fidelity:** the exact pixels of Bryan's terminal emulator and
  font config. Only achievable by screenshotting that actual emulator.

Tier 1+2 are achievable deterministically and are almost certainly what agents need.
Tier 3 is achievable only with heavyweight machinery (Section 4.5) and buys nothing for
"see the impact of my change".

## 2. What Already Exists (this changes the problem a lot)

The sase repo already contains ~80% of the machinery. Any solution should compose
these pieces rather than introduce a parallel stack.

### 2.1 `sase tui --tmux` — real-instance launching for agents (exists today)

`sase tui -T/--tmux` (`src/sase/main/parser_ace.py:104`, `src/sase/main/ace_tmux.py`)
is a first-class, explicitly agent-targeted feature. It launches the TUI in a new tmux
window named `sase_tmux_<N>` inside a dedicated `sase_ace_agents` session (or the
caller's session when already inside tmux), and prints machine-readable
`sase_tmux_window=` / `sase_tmux_session=` / `sase_tmux_pid=` lines. Its help text
literally says it is for agents that drive the TUI via `tmux send-keys` and observe it
via `tmux capture-pane`. It auto-injects `SASE_TUI_TRACE=1` / `SASE_TUI_PERF=1`.

Gaps relative to this research's goal:

- **No size control.** The detached `sase_ace_agents` session is created without
  `-x`/`-y`, so panes default to 80×24 unless a client attaches or `default-size` is
  set. Screenshots need explicit, reproducible geometry (the visual suite's canonical
  size is 120×40).
- **Observation is text-only.** `tmux capture-pane` yields text (or ANSI with `-e`),
  not a PNG.

### 2.2 In-process driving: `AcePage` + Pilot (exists today)

`src/sase/ace/testing/ace_page.py` is a Playwright-style async harness around
`AceApp.run_test()`: `page.press(...)`, `page.click(selector)`,
`await page.expect_state(...)`, `page.export_svg()` (via Textual's
`app.export_screenshot()`), default size 120×40, fast-startup stubs, settle barriers.
200+ test modules use it. It does **not** run the literal `sase tui` process, but it
runs the real `AceApp` against whatever `$SASE_HOME` state you give it.

### 2.3 A hardened SVG→PNG pipeline (exists today)

`tests/ace/tui/visual/png_diff.py` rasterizes Textual SVG exports with
`resvg_py.svg_to_bytes`, `skip_system_fonts=True`, and only the four fonts bundled in
`tests/ace/tui/visual/fonts/` (Fira Code Regular/Bold, DejaVu Sans, Noto Emoji). A
renderer fingerprint (`renderer_env.json`: textual 8.0.1, rich, resvg-py, pillow, font
SHA256s, platform) gates byte-stable comparison against 674 committed golden PNGs.
Convergence helpers (`wait_for_visual_idle`, cursor-blink disabling, animation pins,
clock pins) make frames deterministic. This is the project's **canonical pixel
definition** of what the TUI looks like — CI already treats it as ground truth.

### 2.4 Live-TUI screenshot capture precedent (exists today)

`sase repro capture` (`src/sase/ace/tui/repro/capture.py:458`) proves the key trick:
**a running production TUI can export its own screenshot** — `_capture_screen` calls
`app.export_screenshot(title=..., simplify=True)` inside the live app and writes
`screen.svg` into the repro bundle. Today it's triggered by an in-app key-binding
action (`ReproActionsMixin.action_capture_agents_repro`,
`src/sase/ace/tui/actions/repro.py`) and is agents-tab-only, but the pattern
generalizes trivially: any trigger (key, signal, control file) can make the live app
dump a pixel-perfect SVG of its current frame using Textual's own renderer — the same
renderer that painted the user's terminal.

### 2.5 VHS demo pipeline (exists today)

`demos/tapes/*.tape` + `just demos` run charmbracelet **VHS** (ttyd + headless Chrome +
ffmpeg): each tape sets `FontFamily "Fira Code"`, 1920×1080, GitHub Dark theme, seeds a
fake workspace (`demos/scripts/seed_sase_ace_demo`), runs the literal
`sase tui --refresh-interval 0 -x` command, drives it with `Type`/`Enter`/`Space` and
`Wait+Screen /regex/` synchronization, and emits GIF+MP4. VHS also supports a
`Screenshot out.png` directive, so the existing pipeline can already produce PNGs of a
real terminal-emulator rendering.

### 2.6 Real-PTY smoke harness (exists today)

`tests/ace/tui/terminal_smoke/` spawns `python -m sase ace ... -x -r 0` under `pexpect`
(120×40) and decodes the ANSI stream with `pyte`. Text-grid assertions only, no
rasterization — but it demonstrates the "real process over a real PTY" leg and the
env needed (`COLUMNS`/`LINES`, `LC_ALL=C.UTF-8`, `TERM`).

### 2.7 Determinism knobs that matter for any solution

- Launch flags: **always `-x` (no axe daemon) and `-r 0` (no auto-refresh)** for
  screenshotting; `-t <tab>` picks the startup tab.
- Env pins used by the visual suite (`tests/ace/tui/visual/conftest.py`):
  `COLORTERM=truecolor`, `TERM=xterm-256color`, unset `FORCE_COLOR`/`NO_COLOR`,
  `TEXTUAL_ANIMATIONS=none`, `TZ=UTC`; clock/version pins for byte-stability.
- Theme is hardcoded (`flexoki`), so dark/light does not vary by environment; per-tribe
  colors/icons and keymaps come from user config (`$SASE_HOME/sase.yml`) — a screenshot
  faithful to "what Bryan sees" must run against his real `$SASE_HOME`, which a real
  `sase tui` process does by default.
- State is `$SASE_HOME`-scoped, not cwd-scoped; the TUI starts fine with empty state
  (onboarding panels) and shows the machine's real agents/patches otherwise — which is
  exactly what "see the impact on this machine" wants.

## 3. The Gap

Composing the inventory: sase can already (a) launch a real TUI for agents in tmux,
(b) drive a TUI with keys both in-process and via tmux, (c) export pixel-perfect SVGs
from a live TUI, and (d) rasterize those SVGs to deterministic PNGs. What is missing is
**one command that chains these legs**, plus:

1. Reproducible pane geometry for the tmux path.
2. A *generic, externally triggerable* screenshot export in the live app (repro capture
   is agents-tab-only and key-bound).
3. The rasterizer living in `src/` (it currently lives under `tests/`, with fonts).
4. A remote (`--host <tailnet-alias>`) story.

## 4. Options Analysis

### Option A — In-process harness only (`AcePage` → SVG → PNG)

Drive `AceApp.run_test()` with Pilot, export SVG, rasterize with the existing pipeline.

- **Pros:** already fully built; fastest (~seconds); deterministic; no tmux/PTY needed;
  size parameterizable; CI-proven.
- **Cons:** does not exercise the literal `sase tui` entry point, real PTY, real
  terminal I/O, or the real startup path (fast-startup stubs skip parts of it); by
  default runs against stubbed state. Fails the "real instance" requirement on its own.
- **Verdict:** keep as the CI/regression lane (it already is), not the answer here.

### Option B1 — Real instance in tmux + `capture-pane -e` ANSI → external rasterizer

`sase tui -T -x -r 0`, drive with `send-keys`, then `tmux capture-pane -e -p` and feed
the ANSI text to an ANSI→PNG renderer (charmbracelet `freeze` supports exactly this,
with configurable font).

- **Pros:** captures what actually crossed the wire — would catch escape-sequence-level
  or terminfo bugs that Textual's own exporter cannot see; `freeze` is a single static
  binary.
- **Cons:** new third-party rendering stack **parallel to** the blessed resvg pipeline,
  so agent screenshots would not be comparable to golden PNGs; tmux truecolor fidelity
  depends on tmux build/config (`terminal-overrides` RGB capability); `capture-pane -e`
  loses some attributes across tmux versions; must install `freeze` on every capture
  machine; fonts differ from the canonical bundle.
- **Verdict:** good diagnostic trick to document, wrong primary pipeline.

### Option B2 — Real instance in tmux + in-app SVG export + existing resvg pipeline ⭐

`sase tui -T -x -r 0` (real process, real `$SASE_HOME`, real PTY), drive with
`tmux send-keys` + regex settle-waits on `capture-pane`, then trigger a **new generic
screenshot export inside the live app** (generalizing `sase repro capture`'s
`_capture_screen`): the app writes `app.export_screenshot()` SVG to a requested path;
the CLI rasterizes it to PNG with the (promoted) resvg+bundled-fonts renderer.

- **Pros:** real `sase tui` instance ✔; keypress emulation ✔; PNG ✔; pixels rendered by
  the *same* renderer/fonts as the golden visual suite, so an agent's ad-hoc screenshot
  is directly comparable to CI snapshots and to the demo aesthetic (demos also use Fira
  Code); no new heavyweight dependencies (resvg_py + Pillow already in the `visual`
  extra; tmux already required by `--tmux`); works headless on a server with no
  display; SVG leg needs nothing beyond Textual, so remote machines don't need the
  rasterizer at all.
- **Cons:** needs three modest code changes (export trigger, geometry control,
  promoting the rasterizer out of `tests/`); Textual's exporter renders the app's
  internal frame — it would not catch a hypothetical bug *between* Textual and the
  terminal (mitigable via the B1 diagnostic path); screenshot font is canonical Fira
  Code, not Bryan's terminal font (Tier 2, not Tier 3 fidelity).
- **Verdict:** **recommended core.** Details in Section 6.

### Option C — VHS tape with `Screenshot`

Extend the existing `demos/` VHS pipeline: generate a tape that launches
`sase tui -x -r 0`, drives keys, and emits `Screenshot out.png` (and optionally
GIF/MP4).

- **Pros:** already installed and proven in this repo; renders through a *real terminal
  emulator* (xterm.js) with configurable font/theme — the closest practical thing to
  Tier 3 "what a user sees", including terminal padding/background; also yields
  animated GIFs, which are excellent evidence for interaction changes.
- **Cons:** heavy runtime (ttyd + headless Chrome + ffmpeg) that would need installing
  on every tailnet capture machine; slow (tens of seconds per run); tape-file
  indirection is clunkier for ad-hoc agent use; nondeterministic at the pixel level
  (browser text rendering), so unsuitable for comparison against goldens; VHS controls
  its own environment, so "this machine's real `$SASE_HOME` state" needs care.
- **Verdict:** keep as the **animation/demo lane** and as an optional `--gif` upgrade
  path; not the primary screenshot mechanism.

### Option D — Xvfb + real GUI terminal emulator + xdotool + scrot

Run Bryan's actual terminal emulator under Xvfb, launch `sase tui` in it, inject keys
with xdotool, screenshot the X display.

- **Pros:** the only true Tier 3 fidelity (exact emulator + font stack).
- **Cons:** heavy, brittle, per-emulator config drift, useless on `mac` (no Xvfb),
  slowest, hardest to make deterministic. The extra fidelity over B2/C changes no
  agent decision.
- **Verdict:** rejected.

### Option E — pexpect + pyte (extend the terminal-smoke harness)

- **Pros:** real process over a real PTY, pure Python.
- **Cons:** pyte reconstructs a text grid, not pixels; would still need a
  grid→SVG/PNG renderer, i.e. reinventing what Textual's exporter already does better.
- **Verdict:** rejected as the capture leg; the smoke harness stays what it is.

### Fidelity summary

| Option | Real `sase tui` proc | Grid fidelity | Pixel story | New deps | Speed |
| --- | --- | --- | --- | --- | --- |
| A (AcePage) | no | exact | canonical (resvg) | none | fastest |
| B1 (tmux+ANSI) | yes | tmux-dependent | freeze's renderer | freeze | fast |
| **B2 (tmux+SVG)** | **yes** | **exact** | **canonical (resvg)** | **none** | **fast** |
| C (VHS) | yes | exact | real emulator (xterm.js) | ttyd+chrome+ffmpeg | slow |
| D (Xvfb) | yes | exact | literal user emulator | X stack | slowest |

## 5. Tailnet (Remote) Design

All three machines share the tailnet `tail297af1.ts.net` with chezmoi-managed SSH
aliases (`athena`, `bryan`; `apollo`, `bryan`; `mac`, `bbugyi` — best-effort). That
makes the remote story a thin transport layer, **provided the capture leg is cheap on
the remote side**:

- **Split capture from rasterization.** The remote leg (spawn tmux TUI, send keys, wait,
  export **SVG**) needs only sase itself plus tmux — no resvg, no fonts, no display.
  The SVG comes back over the SSH pipe (or `scp`), and the *calling* machine rasterizes
  to PNG. This keeps the `visual` extra and font bundle an agent-machine-only concern
  and sidesteps macOS wheel/toolchain questions entirely.
- Invocation shape: `sase tui screenshot --host mac ...` ≈
  `ssh mac -- sase tui screenshot --emit-svg ... > local.svg` + local rasterize. The
  chezmoi `tailnet.conf` aliases mean no host/user/key plumbing in sase.
- The remote screenshot deliberately reflects **that machine's installed sase version
  and `$SASE_HOME` state** — that is the feature (e.g. "what does the fleet tab look
  like on apollo right now"), not a bug. The command should print the remote
  `sase --version` alongside the artifact so agents don't misattribute differences.
- Failure modes to design in: `mac` offline (short `ConnectTimeout`, clear error);
  remote sase too old to know the new subcommand (detect via exit code, report
  "upgrade sase on <host>"); no tmux on remote (already a clean error in
  `ace_tmux.py`).
- Non-goal: pushing an agent's *uncommitted working-tree changes* to another machine to
  screenshot them there. That is a deployment problem (the sase-managed workspace/fleet
  machinery is the right home for it), not a screenshot problem. Local screenshots of
  the agent's dev venv cover the "see my change" case; remote screenshots cover the
  "see deployed reality" case.

## 6. Recommended Solution

**Build `sase tui screenshot` (working name) as a thin composition of existing parts —
Option B2 as the core, with `--host` for the tailnet and VHS retained as the separate
demo/GIF lane.** Concretely:

### 6.1 New in-app generic screenshot export (the only real TUI change)

Generalize `repro/capture.py`'s `_capture_screen` into a global, tab-agnostic export:

- A request/response file protocol on the live app: the app watches (or is signaled to
  check) a request path and writes `app.export_screenshot(simplify=True)` SVG to the
  named output. Two workable triggers, in preference order:
  1. **Signal trigger:** a `SIGUSR2` handler (SIGUSR1 is already taken by the artifact
     pane close-notification in `actions/agents/_panel_artifact_pane.py`) that reads a
     path from `SASE_TUI_SCREENSHOT_DIR` (injected by `--tmux`, like
     `SASE_TUI_TRACE`) and schedules the export on the app thread. The CLI then does
     `kill -USR2 $sase_tmux_pid` and polls for the file. No keymap surface, works even
     when a modal has focus.
  2. **Hidden key-binding action** (`action_export_screenshot`) driven via
     `tmux send-keys`. Simpler, but consumes a key, requires `default_config.yml`
     keymap registration (per the gotchas memory), and can be swallowed by
     text-input focus — the signal path avoids all three problems.
- Export must run on the UI thread after an idle settle (reuse the convergence idea
  from `_ace_png_snapshot_waits.py`: cursor-blink off for the frame, wait for pending
  visual work).

### 6.2 The CLI orchestration (no new deps)

`sase tui screenshot [-o out.png] [--size 120x40] [--press k1 k2 ...]
[--wait-for REGEX] [--settle-ms N] [--svg] [--keep] [--host ALIAS] [-- TUI_ARGS...]`:

1. Launch via the existing `--tmux` machinery with `-x -r 0` defaults appended, after
   **fixing geometry**: create/resize the target window to `--size` (tmux
   `resize-window -x -y`; also set `default-size` on the dedicated session so the
   80×24 detached-session default stops mattering).
2. Drive `--press` keys with `tmux send-keys`; between steps, honor `--wait-for`
   regexes by polling `tmux capture-pane -p` (the VHS `Wait+Screen` idiom, which the
   demo tapes prove is the right synchronization primitive for this app).
3. Trigger the Section 6.1 export; collect the SVG.
4. Rasterize with the **promoted** renderer: move `render_svg_to_png` + the four fonts
   from `tests/ace/tui/visual/` into `src/sase/ace/tui/visual_render.py` (+ package
   data), keep `resvg_py`/`pillow` in the `visual` extra, and have the tests import the
   promoted module so there is exactly one canonical rasterizer. `--svg` skips
   rasterization (and is what `--host` uses on the remote side); a clear error tells
   users to install `.[visual]` when the extra is missing.
5. Default cleanup kills the tmux window (`--keep` preserves it for interactive
   follow-up driving — agents will often screenshot, look, then send more keys).
6. `--host ALIAS`: run steps 1–3 remotely over the tailnet SSH alias with
   `--emit-svg`, stream the SVG back, rasterize locally (Section 5).

### 6.3 Placement and process notes

- Everything here is TUI presentation/automation glue → it belongs in this Python repo,
  not sase-core (per the rust-core boundary rule).
- Adding the subcommand triggers the `cli_rules.md` reference-memory obligation; a
  key-binding variant (if chosen over the signal) triggers the `default_config.yml`
  keymap gotcha; agent-facing docs belong next to the `--tmux` help and in
  `docs/ace.md`.
- Determinism defaults (animations off, `TZ`, truecolor env) should be applied by the
  command itself so agents can't forget them; a `--raw-env` escape hatch preserves
  "exactly what my shell would do".

### 6.4 What this buys, per requirement

| Requirement | How it's met |
| --- | --- |
| Real `sase tui` instance | Existing `--tmux` launcher; real process, PTY, `$SASE_HOME` |
| Emulate user actions | `tmux send-keys` + regex settle-waits (VHS-proven idiom) |
| PNG output | Live-app SVG export → canonical resvg+Fira Code rasterizer |
| "Identical to what the user sees" | Tier 1 exactly; Tier 2 = project-canonical pixels, byte-comparable with the golden suite; Tier 3 available via the VHS lane when literal emulator pixels matter |
| Any tailnet machine | `--host <alias>` over chezmoi SSH aliases; SVG-only remote leg keeps remote deps at "sase + tmux" |

### 6.5 Suggested build order

1. Promote the rasterizer out of `tests/` (pure refactor, visual suite keeps passing).
2. In-app export trigger + `SASE_TUI_SCREENSHOT_DIR` env injection in `--tmux`.
3. `sase tui screenshot` local orchestration (sizing, press/wait, PNG).
4. `--host` remote leg.
5. Optional later: `--gif` that emits a generated VHS tape for animated evidence.

## 7. Risks and Open Questions

- **Textual-exporter blind spot:** B2 renders the app's internal frame; a terminal-layer
  regression (terminfo, tmux passthrough) would not appear. Mitigation: document the
  `tmux capture-pane -e` + `freeze` diagnostic recipe; the terminal-smoke pexpect suite
  already guards the PTY path functionally.
- **Signal availability on macOS:** `SIGUSR2` exists on macOS; fine for `mac`. Windows
  would need the key-binding fallback, but no tailnet machine is Windows.
- **Modal/focus timing:** screenshots taken mid-animation or mid-refresh will be
  nondeterministic; the settle machinery exists but must be wired into the live-app
  export, not just the test harness.
- **tmux geometry semantics** differ slightly across tmux versions
  (`resize-window`/`default-size` need tmux ≥ 2.9); worth a version check with a clear
  error, matching `_require_tmux_binary`'s style.
- **Naming:** `sase tui screenshot` vs a flag on `sase repro`; screenshot-as-subcommand
  reads better for agents and leaves `repro` focused on bug bundles. Final name is an
  implementation-time CLI-rules question.

## 8. Bottom Line

Don't build a new capture stack — chain the four that already exist. The recommended
`sase tui screenshot` command launches a real TUI through the existing agent-facing
`--tmux` machinery, drives it with `tmux send-keys` synchronized by screen-regex waits,
has the live app export its own pixel-perfect SVG (the proven `sase repro capture`
trick, generalized and externally triggerable), and rasterizes with the same
resvg+bundled-font renderer that defines the project's 674 golden PNGs — giving agents
fast, deterministic, canonical screenshots of the real application on any tailnet
machine, with VHS retained as the separate lane for animated demos and
literal-terminal-emulator pixels.
