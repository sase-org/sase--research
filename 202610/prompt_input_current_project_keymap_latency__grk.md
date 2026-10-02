# Prompt-input keymap latency: `<ctrl+n/p>` current-project cycle and `<space>` activation

_Independent research into why two prompt-input keymaps feel slow, and how to make both
hit the TUI keystroke budget. Measurements taken 2026-10-02 against this host's live
`~/.sase` (37 project dirs, 7 VCS xprompt MRU entries, 31 enabled records, 3
launchable)._

## Bottom line

Both keymaps are slow for the same reason: every press synchronously rebuilds the
launchable VCS xprompt MRU on the UI thread, and `<space>` then throws the prompt
widget away and mounts a new one.

`load_launchable_vcs_xprompt_mru()` is a keystroke-path function that:

1. lists every project record once per known MRU project (N+1),
2. re-derives launchability that Rust already stored on `ProjectRecordWire.launchable`,
3. re-detects provider via plugin hooks, which for GitHub runs
   `git config --get remote.origin.url` in a subprocess,
4. defaults to prune-on-load, so a keypress can also rewrite
   `~/.sase/vcs_xprompt_mru.json`.

Measured here:

| Path | Cold (fresh process) | Warm (repeat in-process) |
| --- | ---: | ---: |
| `load_launchable_vcs_xprompt_mru_pairs()` | **446 ms** | **20–26 ms** |
| JSON `_load` alone | — | 0.05 ms |
| `PromptTextArea(..., language="markdown")` construct | — | 4.4–6.1 ms |
| `PromptInputBar` construct | — | 0.13–1.0 ms |

The TUI budget in `tui_perf.md` is **p95 < 16 ms** for j/k key-to-paint. A warm cycle
already misses that budget on data fetch alone. A cold `<space>` pays the 446 ms load
plus first-mount of a markdown `PromptTextArea` with ~29 mixins.

The current-project *display* chip already does the right thing: peek `mtime` on the
tick, resolve on a worker. Completions already do the right thing: `prune=False`,
mtime-keyed catalog cache, `run_worker(..., thread=True)` warmup. The two keymaps did
not get those patterns.

**Recommended solution:** one in-process launchable-MRU snapshot, keyed by
`(mru mtime_ns, size, projects snapshot token)`, built from a single
`list_project_records` pass using `record.launchable` and `record.vcs_kind`. Keystroke
handlers read that snapshot only. `<ctrl+n/p>` keeps a ring on the widget and does
index math plus a short text replace. `<space>` reuses a keep-alive `PromptInputBar`
(hidden pre-mount or in-place reset) instead of unmount+mount. Prune and git detection
move to idle/background. Target: p95 key-to-paint **< 16 ms** for both maps.

---

## 1. What the two keymaps actually do

### 1.1 "Current project stack" is the VCS xprompt MRU

Glossary `current-project`: the current project is derived, not stored. It is the first
entry in `~/.sase/vcs_xprompt_mru.json` that maps to an enabled project (a Patch entry
yields its owning project). `sase project set-current` and a successful launch write
the same store.

That file is also the **cycle ring** for the prompt. It is not a separate "stack"
widget. Traversing "the current project stack" in the prompt input is cycling this MRU.

This host's live MRU (7 entries, most-recent first):

```
#gh:gh_bobs-org__bob-cli
#gh:gh_sase-org__sase
#gh:sase_fix_just_linters_14
#gh:gh_bbugyi200__actstat
#gh:sase_fq_8_1_scratch_probe_1
#gh:bbugyi200/actstat
#gh:sase-org/sase
```

Only three records are `launchable` (`bob-cli`, `sase`, `actstat`). The other four are
Patch-shaped or owner/repo refs. The cycle ring includes those as long as pruning
cannot prove they are gone.

### 1.2 `<ctrl+n/p>` — cycle the ring inside the already-open prompt

Default bindings live on `PromptTextArea`, not the app keymap:

```447:461:src/sase/ace/tui/widgets/_prompt_text_area_key_handling.py
        if event.key == "ctrl+n":
            event.stop()
            event.prevent_default()
            if self._try_xprompt_arg_name_completion_cycle():
                return
            self._handle_vcs_mru_cycle_key("ctrl+n")
            return

        if event.key == "ctrl+p":
            event.stop()
            event.prevent_default()
            if self._try_xprompt_arg_name_completion_cycle(last=True):
                return
            self._handle_vcs_mru_cycle_key("ctrl+p")
            return
```

`ctrl+p` walks toward older entries; `ctrl+n` toward newer. The ring has one extra
slot that clears the leading `+<project>` tag / `#workflow:ref`. Replacements prefer
the `+sase` tag form when the project-tag catalog is warm.

The handler then **reloads the launchable MRU on every keypress**:

```385:423:src/sase/ace/tui/widgets/_vcs_mru_cycling.py
    def _handle_vcs_mru_cycle_key(self, key: VcsMruCycleKey) -> bool:
        ...
        from sase.history.vcs_xprompt_mru import load_launchable_vcs_xprompt_mru
        from sase.project_tags import peek_project_tag_catalog

        edit = _cycle_vcs_mru_text(
            text=self.text,
            cursor_offset=self._absolute_offset(self.cursor_location),
            mru=load_launchable_vcs_xprompt_mru(),
            current_index=self._vcs_mru_index,
            key=key,
            catalog=peek_project_tag_catalog(),
        )
        ...
        self._replace_via_keyboard(edit.replacement, start, end)
        self._vcs_mru_index = edit.mru_index
        ...
        self._refresh_xprompt_arg_hint_from_cursor()
        self._on_prompt_completion_context_changed()
```

`load_launchable_vcs_xprompt_mru()` defaults to `prune=True`. Completions already pass
`prune=False` (`src/sase/xprompt/vcs_project_completion.py`); the keymap does not.

After the text replace, the handler always refreshes xprompt arg hints and fires
`_on_prompt_completion_context_changed()`, which schedules Jinja diagnostics on
Textual's serial pump (`set_timer`, 90 ms debounce).

### 1.3 `<space>` — activate the prompt by remounting it

App default keymap (`src/sase/default_config.yml`):

```yaml
start_agent_from_patch: "space"
```

The action is disabled while a prompt bar is already focused, so `<space>` is the
*open* gesture, not an in-prompt character:

```318:329:src/sase/ace/tui/_app_action_availability.py
    # ``start_agent_from_patch`` replays the last launched VCS xprompt by
    # remounting the prompt bar, which tears down whatever the user is
    # currently typing ...
    if action == "start_agent_from_patch" and (
        bool(getattr(app, "_screen_stack", ())) and app._prompt_input_active()
    ):
        return False
```

The action resolves the MRU head, then always unmounts and mounts a new bar:

```14:81:src/sase/ace/tui/actions/agent_workflow/_entry_custom.py
def _resolve_vcs_xprompt_mru_head() -> tuple[str, str, str] | None:
    ...
    pairs = load_launchable_vcs_xprompt_mru_pairs()  # prune=True
    ...

def action_start_agent_from_patch(self) -> None:
    ...
    resolved = _resolve_vcs_xprompt_mru_head()
    ...
    self._show_prompt_input_bar_for_home(
        initial_text=initial_text,
        display_name=display_name,
        history_sort_key=history_sort_key,
    )
```

```440:474:src/sase/ace/tui/actions/agent_workflow/_prompt_bar_mount.py
        # Remove any existing prompt bar before mounting a new one.
        self._unmount_prompt_bar()
        self._setup_home_prompt_context(...)
        bar = PromptInputBar(initial_value=initial_text, id="prompt-input-bar")
        self.mount(bar)
```

Unmount is synchronous because Textual's `remove()` is async and a follow-up
`mount(id="prompt-input-bar")` would raise `DuplicateIds`:

```253:259:src/sase/ace/tui/actions/agent_workflow/_prompt_bar_mount.py
        # Synchronously detach from parent's node list so the ID is freed
        # immediately. Without this, bar.remove() only schedules async
        # removal and a subsequent mount() would hit DuplicateIds.
        parent = bar._parent
        if parent is not None:
            parent._nodes._remove(bar)
        bar.remove()
```

That comment is the constraint that makes "just remount, it is simpler" expensive.
Every `<space>` pays widget destruction, markdown `PromptTextArea` construction,
compose, mount, focus, catalog warmup, and a cancelled-history save on the outgoing
bar.

---

## 2. The shared hot path: `load_launchable_vcs_xprompt_mru_pairs`

```67:128:src/sase/history/vcs_xprompt_mru.py
def load_launchable_vcs_xprompt_mru_pairs(..., *, prune: bool = True):
    entries = _load_vcs_xprompt_mru()
    resolvable_refs = None if projects_dir is not None else _resolvable_vcs_ref_index()
    ...
    filtered = [
        entry
        for entry in entries
        if not _is_default_vcs_xprompt_prefix(entry)
        and not _is_stale_known_project_prefix(entry, projects_dir, alias_map=alias_map)
        and not _vcs_prefix_ref_is_gone(entry, resolvable_refs)
        and not _vcs_prefix_provider_mismatched(entry, resolvable_refs)
    ]
    if prune and filtered != entries:
        _save_vcs_xprompt_mru(filtered)
    return _dedupe_mru_pairs(filtered, projects_dir)
```

The file even documents this as a per-keystroke path ("so the per-keystroke
`<ctrl+p>` path never re-reads project records per entry") — and then each
predicate re-reads them anyway.

### 2.1 What each predicate costs

**JSON load** is not the problem. `_load_vcs_xprompt_mru()` was **0.047 ms**.

**`_resolvable_vcs_ref_index`** builds known workspaces, the cached Patch index, and
the alias map. First call in a process that had already imported the module: **316 ms**.
Later calls drop, but cProfile still shows ~5 ms per load from Patch enumeration and
alias-map `list_project_records`.

**`_is_stale_known_project_prefix`** extracts the project, then calls
`is_launchable_project()`. That helper lists **all** project records *every call*, then
re-checks the spec:

```64:89:src/sase/ace/tui/modals/project_discovery.py
def is_launchable_project(project_name, projects_dir=None, include_states=("enabled",)):
    records = list_project_records(...)
    canonical_name = resolve_project_alias_ref(...)
    for record in records:
        ...
        return _is_launchable_project_file(Path(record.project_file))
```

```92:105:src/sase/ace/tui/modals/project_discovery.py
def _is_launchable_project_file(project_file: Path) -> bool:
    workspace_dir = parse_workspace_dir(str(project_file))
    ...
    detect_workflow_type(str(project_file))  # plugin hook
    return True
```

It never reads `record.launchable`.

**`_vcs_prefix_provider_mismatched`** calls `detect_workflow_type()` again for each
known-project prefix.

**`detect_workflow_type`** is a pluggy first-result hook. The GitHub plugin's
implementation runs a subprocess on the UI thread:

```62:91:sase-github/src/sase_github/workspace_plugin.py
    def ws_detect_workflow_type(self, project_file: str) -> str | None:
        ...
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            check=False,
        )
```

That is a direct violation of `tui_perf.md` rule 11: *keystroke paths must never spawn
subprocesses*. A git credential helper that prompts would freeze the TUI.

### 2.2 cProfile of the warm path (this host, 8 repeats)

`load_launchable_vcs_xprompt_mru_pairs(prune=True)` × 8 = **206 ms** total
(~**26 ms/call**), 144k Python function calls.

Dominant cumulative time:

| Site | Calls | Cum |
| --- | ---: | ---: |
| `_is_stale_known_project_prefix` | 56 | 121 ms |
| `is_launchable_project` | 24 | 114 ms |
| `list_project_records` | 72 | 97 ms |
| GitHub `ws_detect_workflow_type` → `subprocess.run` | 48 | 85 ms |
| `_vcs_prefix_provider_mismatched` | 56 | 45 ms |
| `_resolvable_vcs_ref_index` | 8 | 40 ms |

Per keypress that is **6 `git config` subprocesses** and **9 `list_project_records`**
walks of 37 projects. `prune=True` vs `prune=False` was the same ~20 ms once caches
exist; the disk write is not the hot path.

Isolated pieces (same process, already warm):

| Call | Time |
| --- | ---: |
| `_load_vcs_xprompt_mru` | 0.05 ms |
| `_resolvable_vcs_ref_index` (first in this process) | 316 ms |
| stale-check all 7 entries | 75 ms |
| mismatch-check all 7 entries | 8.5 ms |
| `is_launchable_project("sase")` | 3.9 ms |
| `detect_workflow_type` per launchable spec | 1.7–2.7 ms |

Fresh process (import + first load): **import 33 ms + first load 446 ms**. Second load
in that process: **22 ms**. The "sometimes slow" report for `<space>` is this cold/warm
cliff, not a race.

### 2.3 The data is already on the record

Rust `build_project_record` (`sase-core/crates/sase_core/src/project_spec.rs`) already
computes both fields **without git**:

- `launchable` = is a real project AND enabled AND `WORKSPACE_DIR` exists.
- `vcs_kind` = `"gh"` from a `gh_<owner>__<repo>` directory key, or `"git"` when the
  spec carries `BARE_REPO_DIR`.

Python already surfaces them:

```100:106:src/sase/core/project_lifecycle_wire.py
    launchable: bool
    ...
    vcs_kind: str | None = None
```

`list_project_records` of all 37 dirs was **4.4 ms** for a full snapshot. One snapshot
plus a dict lookup is enough to judge every MRU prefix. The keymap currently spends
20–446 ms re-deriving a 4 ms answer, and spends most of that in git.

Semantic caveat: Rust `launchable` does not require a loaded workspace plugin.
`_is_launchable_project_file` does (`detect_workflow_type` raises if no plugin claims
the spec). For a *keystroke* filter, `record.launchable` plus `record.vcs_kind` is the
correct offline approximation. Plugin-missing / provider-mismatch pruning belongs on
the background refresh, the same way completions already treat an unclaimed
`workflow_type is None` as "not a completion row" without blocking typing.

---

## 3. Why `<space>` is also slow, and why it feels intermittent

`<space>` does the same MRU load (446 ms cold / 20–26 ms warm), then remounts.

`PromptTextArea` is a markdown tree-sitter `TextArea` plus ~29 mixins
(`prompt_text_area.py`: next-word, vim keys, Jinja diagnostics, yank/search/todo
highlight, artifact-ref, xprompt syntax, completions, snippets, VCS cycling, …).
Construct of that widget: **6.1 ms** first, **4.4 ms** after. `PromptInputBar`
construct is cheap (**0.97 → 0.13 ms**) because the expensive child is built in
`compose`.

`on_mount` then:

- focuses and places the cursor,
- schedules an xprompt stale check,
- fires **seven catalog warmers** (those correctly use `run_worker(..., thread=True)`),
- calls `_on_prompt_completion_context_changed()`, which schedules Jinja inspect on
  the pump via `set_timer`.

So even after the data path is fast, `<space>` still:

1. saves cancelled history for the outgoing bar (when one exists),
2. synchronously detaches the old DOM node,
3. constructs a markdown highlighter,
4. composes and mounts,
5. queues pump work that can hitch the first keystrokes in the new bar.

A previous in-process Textual `run_test` of this same bar (earlier in this
investigation) printed **first mount 307 ms, second mount 22 ms** before the test
harness crashed on an unrelated stale `sase_core_rs` binding. Treat those mount
numbers as directional, not as a checked-in bench: they match the construct+compose
shape and the cold/warm split. This turn did not re-run a full app mount.

"Sometimes slow" for `<space>` is therefore:

- first press after TUI start, or after the process dropped import caches → ~0.5 s of
  MRU work plus first-mount,
- later presses → ~20–26 ms MRU + ~20 ms remount, still over the 16 ms budget,
- plus a 90 ms-debounced Jinja inspect on the pump after focus.

---

## 4. Patterns that already exist and should be reused

The codebase already solved this class of bug three times. The keymaps should copy
those shapes, not invent a fourth.

### 4.1 Current-project chip: peek vs resolve

`src/sase/current_project.py` and `launch_context_source.py`:

- Tick is peek-only: `os.stat` of the MRU file `(mtime_ns, size)` plus a time-gated
  config token, floored at 0.5 s.
- Resolve (`resolve_current_project`) runs on `run_worker(..., thread=True)`.
- The source widget is `display: none`, mounted once. Views paint from its state.

`<ctrl+n/p>` needs the *list*, not just the head, but the freshness protocol is the
same: peek on the key, serve the last good snapshot, refresh off-thread if the token
moved.

### 4.2 Completions: prune=False + mtime cache + worker warmup

`src/sase/xprompt/vcs_project_completion.py` keeps `_ENTRIES_CACHE` keyed by spec
signature + MRU signature. `on_mount` warms it with
`_warm_vcs_project_completion_catalog()` → `run_worker(_warm_vcs_completion_catalogs,
thread=True)`. That worker already calls `load_launchable_vcs_xprompt_mru_pairs(prune=False)`.

The cycle keymap can share that warmup. It should not build a second cache with a
different key.

### 4.3 Pump-free timers

`tui_perf.md` rule 2: Textual serially awaits `set_timer` / `call_later` /
`call_after_refresh`. `asyncio.to_thread` inside those callbacks still blocks the
pump. Slow bodies go through `spawn_pump_free_task()`. Jinja diagnostics currently
use `set_timer` then `_inspect_with_engine_scope` on the pump
(`_jinja_diagnostics.py`). A cycle or a remount that immediately fires that path
adds a hitch ~90 ms later, which the user attributes to the keymap.

### 4.4 Host-pressure history

`docs/perf_runbook.md` records bead `sase-zn` as an investigation of **prompt-input
lag** on a long-lived TUI. Phase 1 was host relief (tmpfs, RSS). Later phases did not
instrument these two keymaps. `SASE_TUI_PERF=1` still only records j/k
(`~/.sase/perf/tui_jk.jsonl`). These two maps are unmeasured in production, which is
why they stayed slow after the Agents-tab work.

---

## 5. Alternatives considered

| Option | What it does | Verdict |
| --- | --- | --- |
| **A. `prune=False` on the keymap only** | Matches completions; skips a JSON write | Necessary, not sufficient. Warm path stays ~20 ms. |
| **B. Memoize `is_launchable_project`** | Cuts N+1 `list_project_records` | Still runs `git config` per known project. |
| **C. `run_worker` per `<ctrl+n/p>`** | Moves load off the UI thread | First key still waits; applying the result from a worker still hits the pump; held keys queue workers. tui_perf: do not spawn per-keystroke workers for a 16 ms budget. |
| **D. `asyncio.to_thread` in the key handler, then mutate** | Classic Textual footgun | Rule 1+2: the await is on the pump; UI mutation after await is stale. |
| **E. Snapshot the ring once at TUI start** | Fast forever | Stale after `sase project set-current`, a launch, or another TUI. Peek-token invalidation is required. |
| **F. Keep remounting, just cache the MRU** | Fixes the 446 ms cliff | `<space>` still pays markdown construct + mount + Jinja. Warm remount is still ≥16 ms. |
| **G. Drop markdown highlighting on the prompt** | Cheaper construct | A few milliseconds. Not the 20–446 ms. Do not take this as the fix. |
| **H. Rebind `<space>` away from prompt open** | Avoids the gesture | Does not fix `<ctrl+n/p>`. The open path stays slow for whatever key replaces it. |
| **I. Call `resolve_ref` to validate the ring** | "Correctness" | Bare-git `resolve_ref` *creates* projects. The existing comments in `_vcs_prefix_ref_is_gone` exist specifically to forbid this on `<ctrl+p>`. |
| **J. Shared snapshot + widget ring + keep-alive bar** | See §6 | **Recommended.** |

---

## 6. Recommended solution

Three layers. Ship them as one change if possible; if they must split, the snapshot
is the first PR because both keymaps share it.

### Layer 1 — One launchable-MRU snapshot (shared)

Add a process-local cache next to the existing VCS completion cache, or extend that
cache so cycle, `<space>` prefill, and `+` completion share one object.

**Key:** `(mru_path.stat().st_mtime_ns, mru_path.stat().st_size, projects_snapshot_token)`.
The projects token can be the same spec-mtime signature completions already use, or
the lifecycle wire's existing change token if one is handy. Peek with `os.stat` only
(copy `peek_current_project_change_token`).

**Build (off the keystroke path):**

1. `_load_vcs_xprompt_mru()` (JSON, ~0.05 ms).
2. `list_project_records(..., include_home=True)` **once** (~4 ms).
3. Build `key → record` and alias maps from that list.
4. For each MRU entry:
   - drop the implicit `#git:home` default,
   - if it names a known project: keep iff `record.launchable` and
     `record.vcs_kind` matches the tag's workflow (or `vcs_kind` is unknown — keep,
     do not git-probe),
   - if it names a Patch: keep iff the Patch name is in the cached Patch index
     (already used by `_vcs_prefix_ref_is_gone`),
   - never call `detect_workflow_type`, `is_launchable_project`, or `resolve_ref`.
5. Humanize display forms with the snapshot's `display_name` / tag catalog peek.
6. **`prune=False` on this path.** Persist pruning from `record_vcs_xprompt_usage`,
   an idle worker, or the existing catalog warmup — not from a key.

**Warm:** call the builder from `_warm_vcs_completion_catalogs()` so the first
`<space>` after TUI start already has a snapshot. The current-project source's
worker can invalidate/rebuild when its peek token changes.

**API:** `peek_launchable_vcs_xprompt_mru_pairs() -> list[tuple[str, str]]` returns
the last snapshot immediately. `load_launchable_...` stays for CLI / tests / prune
semantics, but TUI key handlers stop calling it.

**Budget for a hit:** well under 1 ms (stat + list copy). **Miss:** serve the stale
snapshot and rebuild on a worker; do not block the key.

### Layer 2 — `<ctrl+n/p>` becomes index math

On the widget (`VcsMruCyclingMixin` / `PromptTextArea`):

1. Keep `_vcs_mru_ring: tuple[str, ...]` and `_vcs_mru_token`.
2. On key: if `peek` token matches and the ring is non-empty, run
   `_cycle_vcs_mru_text` against the stashed ring. That function is already pure.
3. Apply `_replace_via_keyboard` for a short leading-tag replace (this is the
   unavoidable TextArea cost; it is small relative to 20–446 ms).
4. If the token moved: keep cycling on the last ring (user must not stall), and
   schedule **one** coalesced worker to rebuild. Last-request-wins, same as
   `_schedule_agents_async_refresh`.
5. Skip `_refresh_xprompt_arg_hint_from_cursor()` unless the new text actually
   contains an xprompt arg trigger. Skip or pump-free the Jinja timer: cycle is a
   leading-tag swap, not a template edit.
6. Keep the existing xprompt-arg-name completion steal of `ctrl+n/p` when that
   context is active — it already returns before MRU load.

Do not spawn a worker per key. Held `<ctrl+n>` would otherwise stampede.

### Layer 3 — `<space>` reuses a keep-alive prompt bar

Remount is the remaining cliff after Layer 1.

Preferred shape, modeled on `LaunchContextSource`:

1. After first paint (startup worker, not first `<space>`), mount a hidden
   `PromptInputBar` (`display: none` or a CSS class that is already used for
   non-rendering keep-alives in `_app_layout.py`). Give it a stable id.
2. `<space>`: resolve the head from the snapshot (~0 ms), `begin_prompt_session`,
   `load_text` / stack reset / `cursor to end`, unhide, focus. No `remove()`, no
   `DuplicateIds`, no markdown re-init.
3. Dismiss / submit: hide and reset in place. Keep today's cancelled-history save
   on *dismiss*, and today's no-save path on *submit*, but both operate on the
   same instance.
4. If a second bar is truly required (feedback mode, approve-prompt, xprompt
   markdown editor remount), keep those as explicit remounts. The default
   `start_agent_from_patch` path is home-mode replay and does not need a new
   widget.

If keep-alive is too entangled with session identity (`begin_prompt_session`
mints a new `session_id` today), the fallback is **in-place reset of the last
bar** when `#prompt-input-bar` already exists but is inactive/hidden, and
keep-alive only for the common "no bar mounted" case.

Jinja diagnostics, catalog warmup, and height updates stay on the existing
workers / pump-free tasks. They must not run inline in the `<space>` handler.

### Measurement (do this in the same PR)

Extend `SASE_TUI_PERF=1` so it records `prompt.space` and `prompt.ctrl_n` /
`prompt.ctrl_p` key-to-paint samples next to j/k (`docs/perf_runbook.md`,
`~/.sase/perf/tui_jk.jsonl` or a sibling file).

Gates:

- warm `<ctrl+n/p>` p95 **< 16 ms**
- warm `<space>` p95 **< 16 ms**
- cold first `<space>` after TUI start **< 50 ms** perceived (snapshot already
  warmed); if warmup has not finished, the bar still opens on a stale-or-empty
  prefill and the worker fills the tag — it does not block open
- stall watchdog: no `tui_hitch` attributed to `load_launchable_vcs_xprompt_mru`
  or `ws_detect_workflow_type` on these keys
- unit tests: cycle and `<space>` prefill never call `subprocess.run` / `git`
  (patch `detect_workflow_type` and assert zero calls on the keymap path)

### What not to do

- Do not wrap the key handler in `to_thread` and then mutate the TextArea.
- Do not call `resolve_ref` to "be sure" the ring is valid.
- Do not keep `git config` on the keystroke path "just for GitHub".
- Do not rebuild `PromptInputBar` on every `<space>` once a keep-alive exists.
- Do not prune-on-keypress; a held `<ctrl+n>` must not rewrite the MRU file.
- Do not skip the peek token and freeze a startup snapshot for the session.

---

## 7. Suggested implementation order

1. **Snapshot + `peek_launchable_vcs_xprompt_mru_pairs`**, wired into
   `_handle_vcs_mru_cycle_key` and `_resolve_vcs_xprompt_mru_head`, with
   `prune=False` and no `detect_workflow_type`. This alone turns cold 446 ms into
   warm ~1 ms and removes git from the keymap. Tests in
   `tests/test_vcs_xprompt_mru_pruning.py` stay on the explicit `load_*(prune=True)`
   API.
2. **Widget ring stash** so held `<ctrl+n/p>` is index math.
3. **Keep-alive / in-place `<space>`**, plus moving Jinja inspect off the pump.
4. **Perf JSONL + a slow bench** modeled on `tests/ace/tui/bench_tui_jk.py`.

Step 1 is the correctness-preserving win and is safe to land alone. Steps 2–3 are
what make the maps *feel* instant. Step 4 is how we keep them that way.

---

## 8. Files that have to change

| File | Change |
| --- | --- |
| `src/sase/history/vcs_xprompt_mru.py` | Snapshot, peek token, record-based filter, no git on peek |
| `src/sase/ace/tui/widgets/_vcs_mru_cycling.py` | Use peek; stash ring; stop calling `load_launchable_*()` |
| `src/sase/ace/tui/actions/agent_workflow/_entry_custom.py` | Head from peek snapshot |
| `src/sase/ace/tui/actions/agent_workflow/_prompt_bar_mount.py` | Keep-alive or in-place reset for home-mode `<space>` |
| `src/sase/ace/tui/widgets/_file_completion_base.py` | Warm the snapshot in the existing catalog worker |
| `src/sase/ace/tui/widgets/_jinja_diagnostics.py` | `spawn_pump_free_task` instead of pump-side inspect |
| `src/sase/ace/tui/modals/project_discovery.py` | Optional: make `is_launchable_project` use `record.launchable` (helps other callers; not required for the keymap once it stops calling this) |
| `src/sase/xprompt/vcs_project_completion.py` | Share snapshot / signature with the MRU peek |
| `tests/test_vcs_xprompt_mru_pruning.py` and new TUI keymap tests | Prove zero subprocess on cycle/open; pruning still happens off-key |
| `docs/perf_runbook.md` | Document `prompt.space` / `prompt.ctrl_n/p` samples |

No sase-core wire change is required. `launchable` and `vcs_kind` are already on
`ProjectRecordWire`.

---

## 9. Risks and limits

- **Stale ring for one key.** Serving the last snapshot when the token moved means a
  just-disabled project can appear for one `<ctrl+n>` until the worker lands. That is
  the same contract as the current-project chip. Blocking the key to be perfectly
  fresh is how we got 446 ms.
- **Patch entries.** Record-based launchability does not apply to Patch refs. Keep
  the existing offline Patch-name index (`find_all_patches_cached`); do not turn
  those into `is_launchable_project` calls.
- **Hidden bar vs session identity.** `begin_prompt_session` mints a new session.
  Keep-alive must call it on show, and cancelled-history save must still see the
  *previous* session's text on dismiss. This is the fiddly part of Layer 3; Layer 1
  does not depend on it.
- **DuplicateIds.** Any design that mounts a second `#prompt-input-bar` before the
  first is fully detached will crash. Keep-alive avoids a second mount.
- **These numbers are this host, this MRU.** 7 entries / 3 git configs is a small
  ring. A 30-entry MRU of GitHub projects would multiply the current keymap cost
  linearly. The snapshot design is O(records once) instead of O(entries × records ×
  git).

---

## 10. Recommendation

Implement the shared launchable-MRU snapshot (Layer 1) and the widget ring stash
(Layer 2) as the default fix for `<ctrl+n/p>`, and replace `<space>` remount with a
keep-alive / in-place reset (Layer 3). Reuse the peek/worker protocol already proven
by `LaunchContextSource` and VCS completions. Stop calling `detect_workflow_type` and
`is_launchable_project` from any prompt key handler. Measure both maps with
`SASE_TUI_PERF` against a 16 ms p95 budget.

That is the smallest change that makes both operations feel like a keystroke instead
of a catalog rebuild.
