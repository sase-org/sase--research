# Fast prompt project cycling and activation: independent cdx investigation

Researcher: **cdx**. Date: **2026-10-02**. Scope: the prompt input's `Ctrl+N` / `Ctrl+P` workspace MRU cycling and the application `Space` binding that opens it. This report was researched independently; no other swarm report, peer transcript, or peer findings were consulted. No application source was changed.

## Finding

**Make both keymaps consume a prebuilt, immutable launch-history snapshot, and remove synchronous watcher reconfiguration from prompt catalog getters.** These are two separate, demonstrated sources of delay. A cache for the MRU loader alone will materially improve ordinary cycling and activation, but it will leave a first-visit-to-project stall in highlighting.

The strongest evidence is a live watchdog incident: `Ctrl+P` reached disk and Git process creation through MRU validation during an approximately **8.51-second recovered stall**. A separate incident caught `Ctrl+P` rebuilding a filesystem watcher while editing/highlighting the prefix. Controlled measurements then showed that replacing only the MRU loader with a preloaded list reduced an isolated mounted widget's synchronous handler median from **27.70 ms to 2.41 ms**.

The observed delay comes from work executed after dispatch, rather than an inherently slow keybinding mechanism. These measurements do not establish that every occasional delay has the same cause.

## Evidence and scope of confidence

Source checkout: sase `45f165b6d52dddd812e249fe929c80a20520da4d`. Linked checkouts opened through `sase repo open`: sase-core `926edfb8baa1d8e3ba4242156961905595d0faf9`, sase-github `f5fbcc4ffc807d12126f387a4938a8402e6358af`. Benchmarks used the workspace Python **3.14.7**, Textual **8.0.1**, and installed `sase-core-rs` **0.36.1**; the interpreter reported the GIL enabled. Installed extension version and linked source revision are separate evidence and must not be treated as the same build.

I read the project's audited `tui.md`, `tui_perf.md`, and `sase_artifacts.md` guidance. Relevant established constraints are: no disk/subprocess work in key or render paths, no slow awaited body on Textual's serial message pump, worker-built snapshots, coalesced refreshes, and immediate UI updates with secondary work deferred.

### Direct live evidence

I independently read the tail of `~/.sase/logs/tui_stalls.jsonl`, rather than driving or restarting the user's TUI. The examined tail contained 540 records initially. Matching records belonged to PID **872820**, which identified itself as sase **0.17.1**. Times below are America/New_York.

| Time on 2026-10-02 | Observation | Attribution |
| --- | --- | --- |
| 12:37:48.614602 | `tui_hitch`, observed 1.590 s; recovered at 12:37:49.789850 with duration 2.766 s | The main-thread stack explicitly contains `_on_key -> _handle_vcs_mru_cycle_key("ctrl+p") -> _replace_via_keyboard -> _build_highlight_map -> get_warm_prompt_catalog_assist_entries_exact -> _ensure_prompt_catalog_project -> _restart_prompt_source_watcher -> prompt_source_watch_paths -> _memory_source_dirs -> known_project_namespaces -> get_known_project_workspaces -> is_dir`. |
| 12:38:05–06 | Loop and pump hitch/stall records observed about 5.509–5.512 s | All relevant stacks enter the same `Ctrl+P` handler and launchable MRU loader. Samples caught provider metadata file reading, ProjectSpec path existence checks, repeated Rust-backed project enumeration, and `subprocess.run` / `_fork_exec` in GitHub provider detection. |
| 12:38:08 | Matching recovery rows | Loop duration 8.509 s; pump duration 8.513 s. These are multiple observations of one incident, not four independent freezes. |

The first hitch's `last_action` field says `space`, but its actual executing stack says `Ctrl+P`. I attribute it from the stack; it is **not direct proof of a Space-handler freeze**. Likewise, watchdog duration measures absence of progress across an interval, not exclusive CPU time for a single stack frame. These records establish that both offending paths were on the main thread during real stalls; they do not isolate hardware scheduling, paging, or filesystem delays from the application work.

### Controlled component measurements

All real MRU loads in the experiments passed `prune=False`, so the investigation did not rewrite the user's MRU. Profiles ran separately from the unprofiled timing samples. Sample sizes are small; the warm measurements show mechanisms and improvement opportunity, not a production latency distribution.

| Measured component | Samples | Median | Maximum |
| --- | ---: | ---: | ---: |
| Warm `load_launchable_vcs_xprompt_mru_pairs(prune=False)`, 7 returned entries | 12 | 18.09 ms | 21.28 ms |
| Mounted prompt widget's direct `_handle_vcs_mru_cycle_key("ctrl+p")`, real read-only loader | 12 | 27.70 ms | 35.60 ms |
| Same direct handler, loader replaced with preloaded entries | 12 | 2.41 ms | 2.85 ms |
| Space action up to the mount call, real read-only pair loader | 12 | 21.05 ms | 25.56 ms |
| Same Space component, preloaded pair loader | 12 | 0.0095 ms | 0.0325 ms |
| `prompt_source_watch_paths`, 8 contexts including the default, returning 12 paths | 8 | 14.07 ms | 22.58 ms |

The mounted widget experiment used a minimal `App`, `PromptInputBar`, a warm project-tag catalog, and a short prompt. It called the handler directly and drained queued UI work with `pilot.pause()` **outside** the timing interval. It did not model ACE's full app-owned catalog/watcher getter behavior, auto-refresh load, terminal transport, or complete key-to-paint latency. The preloaded-list substitution is an experiment, not an implemented cache with invalidation.

The Space experiment used the real `EntryCustomMixin.action_start_agent_from_patch` and replaced `_show_prompt_input_bar_for_home` with a capture method. It measures the work **before mounting**, not the complete time to a focused editable bar. It supports a shared MRU fix; it cannot prove that mount/focus is already fast enough.

A warm loader profile recorded **9 calls to `list_project_records`, 298 Python project-record conversions, 107 Python `stat` calls, and 6 `subprocess.run` calls** for one seven-entry load. Rust-internal filesystem calls are not included in the Python stat count. The profile took about 27 ms versus the unprofiled 18 ms median. Provider detection accounted for roughly 10 ms cumulative; repeated project inventory calls about 13 ms cumulative. These totals overlap in the call tree and should not be added.

One fresh-process profiled loader took **7.88 s**, dominated by first imports (about 7.49 s cumulative, including hundreds of module reads). This is a cold-process warning, **not an estimate of Space activation in an already-running ACE process**, where many modules have already been imported. First-use imports should nevertheless be kept out of key handlers when practicable.

## What the two keymaps currently do

### Ctrl+N / Ctrl+P

`_prompt_text_area_key_handling.py:447–463` routes these keys through keyword-argument completion first, then `_handle_vcs_mru_cycle_key`. An already-open completion menu has its own earlier routing. Preserve those precedence rules.

`_vcs_mru_cycling.py:385` then:

1. Calls `load_launchable_vcs_xprompt_mru()` synchronously.
2. Computes an edit from current text, cursor, ring index, and the memory-only project-tag catalog.
3. Applies a localized keyboard replacement, moves the cursor, clears completion/hint state, and refreshes completion context.

The ring contains the MRU entries plus one no-prefix stop. `Ctrl+P` moves toward older entries; `Ctrl+N` moves toward newer entries. Project entries can render as `+name`; Patch references remain explicit workspace refs. Prompt cycling changes the submitted text. It does not itself promote every visited project in the global MRU. Keep that distinction, since promoting each keypress would reorder the ring and trigger unrelated refreshes.

The text-edit helper is already localized. There is no evidence justifying wholesale replacement of the TextArea or keymap dispatch.

### Space

`bindings.py:213` and `default_config.yml:893` bind `space` to `start_agent_from_patch`. Despite that legacy-looking action name, `_entry_custom.py:60` repeats the most recently launched VCS prefix, or opens an empty home prompt if there is none.

Before mounting anything, `_resolve_vcs_xprompt_mru_head` calls the same pair loader and derives prefill text, display name, and canonical history grouping. `_show_prompt_input_bar_for_home` then removes an existing bar, creates prompt context, constructs a new `PromptInputBar`, and mounts it. The bar focuses its active TextArea during `on_mount`.

Many mount-time catalogs already load via thread workers or app-owned background caches. Removing completion, prediction, or syntax features indiscriminately is therefore a poor first response. Trace their scheduling and application costs separately if latency remains.

## Why the common loader is too expensive for a keypress

`history/vcs_xprompt_mru.py` does more than read a small JSON array:

- `_resolvable_vcs_ref_index` builds known workspace and active Patch inventories plus aliases on every load. Patch parsing is cached by file metadata, but discovering/stating files still performs work.
- Each known project entry can invoke `is_launchable_project`. That function enumerates project records, resolves aliases through another enumeration, reads workspace metadata, checks paths, and detects the provider.
- `_vcs_prefix_provider_mismatched` can detect that same provider again.
- `sase-github` provider detection reads ProjectSpec metadata and runs `git config --get remote.origin.url`. This is a local Git query, not evidence of a network request or credential prompt, but process creation and filesystem work still have unbounded latency relative to a frame budget.
- Default `prune=True` can **write** the filtered MRU during an operation presented as navigation or activation. Setting `prune=False` removes that write but leaves the expensive validation.

The loader's comment describes its reference index as “cheap, cached, offline.” Offline and partly cached do not mean memory-only. The measured warm costs and live stacks contradict using this routine as a keystroke accessor.

`list_project_records` in Rust iterates project directories and reads active specs. Its current PyO3 binding in `crates/sase_core_py/src/query/mod.rs:534` already wraps the Rust scan in `allow_threads`. It therefore has the GIL release needed for genuine off-thread scanning; the missing step here is moving the calling work off the UI thread and removing repeated calls. New bindings must preserve that property. PyO3's current documentation calls this operation `detach`. [PyO3 parallelism guide](https://pyo3.rs/main/parallelism).

## The second bottleneck: a warm getter changes filesystem watches

Both `get_prompt_catalog_assist_entries` and `get_warm_prompt_catalog_assist_entries_exact` call `_ensure_prompt_catalog_project`. If that project is newly encountered and the prompt watcher exists, `_ensure_prompt_catalog_project` synchronously calls `_restart_prompt_source_watcher`.

That restart stops the watcher, discovers watch paths, and starts another watcher. `ArtifactWatcher.stop()` can join a thread for **up to one second**; `start()` installs watches and performs path checks. Watch-path discovery repeatedly resolves project namespaces and content-layout roots. A render/highlight getter thereby takes a path that can read disk, re-enumerate projects, and wait on a watcher thread.

Project cycling makes this especially visible: changing to a previously unseen project can trigger this path inside `_replace_via_keyboard` through highlighting, then again through completion-context notifications. Ordinary warm revisits often look fast because the project has already entered the tracked set. This explains an intermittent first-visit penalty without requiring the MRU file itself to be large.

The fix must cover **watch-path discovery, watch installation, and watcher shutdown/join**, not merely relocate the outer restart to another synchronous callback. Reuse or extend the current watcher when possible, and do blocking preparation/installation work in a worker. Pure catalog peek getters should not restart or stop anything.

## Options and decision

| Approach | Expected effect | Main limitation | Decision |
| --- | --- | --- | --- |
| Change the keybinding, tune escape delays, or change completion debounce | Little evidence of benefit for these paths | Leaves the confirmed synchronous work intact | Do not prioritize |
| Cache only raw MRU JSON or switch to `prune=False` | Avoids one read or one write | Revalidates projects/providers and still restarts watchers | Insufficient |
| Await `asyncio.to_thread(loader)` from each key handler | Frees the loop during some work | Adds per-key latency, can serialize the receiving message pump, and makes asynchronous edits/order difficult | Avoid as the final design |
| Prewarm once and never invalidate | Excellent warm latency | Launch history, disabled projects, names, aliases, and Patch state become stale | Insufficient |
| Immediately use an app-owned snapshot; coalesce background refresh; make catalog getters pure and watcher updates asynchronous | Removes both demonstrated paths from interaction | Requires explicit freshness, cold-state, and ordering rules | **Recommended** |
| Keep a hidden reusable prompt widget permanently mounted | Could reduce repeated compose/theme/focus cost | Complicates cancellation, session state, stack/target bindings, and stale workers | Only after measuring residual activation costs |
| Rewrite all prompt editing or deploy a new storage daemon | Unproven additional benefit | Large scope relative to identified causes | No evidence to justify it now |

Textual recommends thread workers for blocking synchronous APIs and requires UI mutations to return to the main thread through `call_from_thread` or messages. Thread cancellation also does not forcibly stop the underlying thread. [Textual worker guide](https://textual.textualize.io/guide/workers/). These constraints favor one coalesced background builder with guarded result publication, rather than one worker per repeated keypress.

Textual's installed `MessagePump.on_callback` awaits `invoke(event.callback)`. Merely scheduling an async loader through `call_later`, a timer, or `call_after_refresh` is not enough to free its serial pump. Use the project's existing `spawn_pump_free_task` plus `asyncio.to_thread`, or an established worker path, without awaiting the slow worker from the key/message callback. [Textual message-pump API](https://textual.textualize.io/api/message_pump/).

## Proposed design details

### One shared launch-history snapshot

Keep canonical MRU identities, their display/prefill spellings, associated project keys, and head-prefill metadata together in an immutable snapshot with a generation and a distinct ready/loading/error status. The application owns snapshot publication and scheduling. Both Space and cycling perform only a memory peek plus an edit/mount operation.

Warm it after first paint, reusing the existing startup catalog pattern. Serve the last completed snapshot during refresh. Keep one builder in flight, with one pending refresh and generation checks; do not start a new scan per key. An initial implementation can call the existing loader with `prune=False` through a worker adapter, preserving its filtering rules. That is a scheduling repair, not another implementation of MRU policy.

A reusable batch resolver that changes normalization, filtering, or persistence belongs in `sase_core`, with a typed wire/binding and the required sase core-revision pin update. Backend/domain policy should not be duplicated inside a TUI cache. Provider plug-in detection can supply metadata/results through a thin adapter; do not hard-code GitHub versus Git behavior in the widget or assume Rust's current `launchable`/`vcs_kind` fields fully replace provider validation.

For later efficiency, enumerate lifecycle records and Patch identities once per refresh and memoize provider detection per project in that batch. The measured duplicate calls are unnecessary even off-thread and consume host capacity. Moving them to a background worker is the responsiveness priority; eliminating them is the next efficiency improvement.

### Freshness, integrity, and ordering

Refresh on local successful launch / set-current changes, external MRU changes, relevant ProjectSpec/alias/name/lifecycle changes, active/archive Patch changes, and provider/config changes. Provider choice here also depends on workspace Git configuration, so ProjectSpec mtime alone does not cover all inputs. Use available change events plus a modest background fallback probe for uncovered or missed changes. Never enumerate projects or stat a large tree from the peek accessor.

Do not require a persistent derived database for this fix. A read-only in-process snapshot with explicit invalidation and worker-side revalidation is enough to test the recommendation.

The selection should follow a canonical identity, not blindly reuse `_vcs_mru_index` against a newly reordered list. Pin one immutable ring during a rapid navigation burst; adopt a newer generation at a safe boundary and rebase the index by canonical identity. Preserve directions, no-prefix stop, aliases, explicit Patch refs, cursor placement, literal/code-zone exclusions, undo behavior, and menu precedence.

Represent a genuinely empty MRU separately from a cold cache. Space should mount and focus immediately using a ready head when available. If cold, it can mount an editable blank bar and start one warm request. Apply delayed prefill only if the same prompt session/pane is still mounted and its text/cursor state has not changed. Never overwrite typing, reopen a cancelled bar, or steal focus when a result arrives.

Cold-cycle intent needs an explicit policy: briefly indicate loading and either retain the user's ordered cycle intent against the forthcoming ring while the pane is untouched, or leave the text unchanged with clear feedback. Startup prewarming should make this rare. Do not let asynchronous results independently replay old edits over new input.

Navigation stays read-only. Avoid pruning from the cache worker because a stale read followed by a write can overwrite a concurrently promoted MRU head. If pruning remains desirable, use an explicit atomic, concurrency-safe maintenance or authoritative write path. Launch must still revalidate the selected target through existing authoritative guards; a stale presentation snapshot must not allocate or resurrect a project.

### Pure getters and background watch maintenance

Split “return existing catalog entries” from “request this project for completion.” A `get_warm...` / highlight accessor should return the exact warm entries or a cold sentinel without expanding watches. Explicit context changes may add a project to an in-memory desired set and schedule one background watch/catalog update.

Compute watch roots off-thread from a captured desired-project set. Avoid synchronous `stop()` / `join()` on the app pump. Prefer extending the existing watcher for new roots where safe; otherwise prepare a replacement off-thread, publish only if its generation remains current, and dispose of obsolete watchers off-thread. Because stop/start and worker callbacks can race, preserve generation ownership and ensure teardown does not deadlock on `call_from_thread` while the UI waits for a join.

Retain polling/revalidation while watch coverage is incomplete or unsupported. After installing coverage, reconcile once to catch changes made during preparation. Rapid project cycling should grow a desired set and coalesce maintenance, rather than repeatedly recreate watchers.

Existing syntax/highlight features can remain. In the snapshot experiment the rest of a short-prompt synchronous cycle already took approximately 2–3 ms. If large prompts remain expensive, then trace repeated highlight rebuilds and full-stack state sync. The profile recorded four highlight rebuilds inside one sampled cycle, so there is a plausible secondary optimization; it is lower priority than the two live-confirmed disk paths.

## Verification that would decide whether the repair is sufficient

Measure handler-entry-to-text mutation, mutation-to-next-refresh, Space-to-focus/first-editable-paint, and worker build duration separately. Existing `SASE_TUI_PERF` / `JKPerfTimer` covers j/k, so enabling it alone does not provide these keymaps' latency. Add narrowly scoped trace spans/counters or equivalent dedicated instrumentation, using buffered/background output so measurement does not introduce disk writes into the handler.

Use warm and cold scenarios, repeated activation/cancellation, first visit to every project, alternating/repeated cycling, a 100-entry MRU, many lifecycle records, archived/deleted Patches, large/multiline prompts, a running refresh, missing inotify, external MRU changes, and normal host load. Include a busy-worker / deliberately delayed provider-and-watch fixture: input should remain responsive while background readiness is delayed.

Deterministic regressions should assert that ready key handlers and warm render getters perform **zero MRU file reads/writes, project enumeration, provider subprocesses, watcher stop/start, or thread joins**. Simulate delayed older results, cancellation/reopen, edits during warmup, and MRU reorder to prove stale results cannot overwrite text or reorder cycle intent. Run existing cycling semantics tests alongside them.

Suggested acceptance targets, to agree during implementation: warm synchronous cycle p95 under **5 ms**, cycling key-to-paint p95 under **16 ms** on a normally loaded host, and warm Space-to-editable-paint p95 under **50 ms**. Cold snapshot construction may take longer, but it must never prevent ordinary typing/cancellation. These are proposed targets, not achieved production results. Record maxima and watchdog incidents in addition to medians.

When testing deployed code, confirm the running TUI restarted onto the repaired imports; editable installation does not update already-imported modules in an old process. If latency still occurs with both disk paths removed, use watchdog stacks to distinguish app-pump backlog, refresh/render work, and host contention before proposing another architectural change.

## Reproduction notes

The following small harness illustrates the mounted-handler comparison. Run from the sase checkout using its virtualenv. It explicitly avoids live MRU pruning and measures only the synchronous component. The research ran 12 samples per mode; the table records the resulting medians/maxima.

```python
import asyncio
import statistics
import time
from unittest.mock import patch
from textual.app import App, ComposeResult
from sase.ace.tui.widgets.prompt_input_bar import PromptInputBar
from sase.ace.tui.widgets.prompt_text_area import PromptTextArea
from sase.history.vcs_xprompt_mru import load_launchable_vcs_xprompt_mru
from sase.project_tags import load_project_tag_catalog

class CycleApp(App):
    ENABLE_COMMAND_PALETTE = False
    def compose(self) -> ComposeResult:
        yield PromptInputBar(initial_value="+sase fix a problem")

async def run():
    cached = load_launchable_vcs_xprompt_mru(prune=False)
    load_project_tag_catalog()
    app = CycleApp()
    async with app.run_test() as pilot:
        text_area = app.query_one(PromptTextArea)
        await pilot.pause()
        modes = (
            ("real", {"side_effect": lambda:
                load_launchable_vcs_xprompt_mru(prune=False)}),
            ("snapshot", {"return_value": cached}),
        )
        for label, kwargs in modes:
            samples = []
            with patch(
                "sase.history.vcs_xprompt_mru.load_launchable_vcs_xprompt_mru",
                **kwargs,
            ):
                for _ in range(12):
                    started = time.perf_counter()
                    text_area._handle_vcs_mru_cycle_key("ctrl+p")
                    samples.append((time.perf_counter() - started) * 1000)
                    await pilot.pause()
            print(label, statistics.median(samples), max(samples))

asyncio.run(run())
```

For the Space component, subclass `EntryCustomMixin`, override `_show_prompt_input_bar_for_home` to capture arguments, and time `action_start_agent_from_patch()` with its `load_launchable_vcs_xprompt_mru_pairs` import patched first to a read-only real loader and then to a previously captured pair list. Do not interpret the result as mount/focus timing.

The watchdog timestamps and path tails above are durable excerpts of the incident evidence. No peer artifact is needed to reproduce the conclusions. CPU/page-cache conditions may differ on another run.

## Source map

All repository paths below were inspected locally. Lines refer to the source revisions identified above.

| Repository / source | Relevant content |
| --- | --- |
| sase: `src/sase/ace/tui/widgets/_prompt_text_area_key_handling.py:447`; `widgets/_vcs_mru_cycling.py:195,251,385` | Key precedence, ring semantics, synchronous loader, localized edits |
| sase: `src/sase/history/vcs_xprompt_mru.py:28,67,263,300,388` | MRU reading/filtering, pruning writes, alias/project/provider validation |
| sase: `src/sase/ace/tui/actions/agent_workflow/_entry_custom.py:14,60`; `_prompt_bar_mount.py:201,343,403` | Space prefill, old-bar cancellation/history safety, context and mounting |
| sase: `src/sase/ace/tui/widgets/_prompt_input_bar_lifecycle.py:75`; `_file_completion_base.py:38` | Focus and existing background warmups |
| sase: `src/sase/ace/tui/actions/_startup_prompt_catalog.py:93,122,373`; `_startup_watchers.py:84,106` | Catalog getter side effects and synchronous watcher restart |
| sase: `src/sase/ace/tui/prompt_catalog.py:141,230`; `util/fs_watcher.py:161,198,219` | Watch root discovery, installation, join, incremental watch support |
| sase: `src/sase/ace/tui/widgets/_xprompt_syntax_highlight.py:102`; `_prompt_input_bar_stack_lifecycle.py:96` | Highlight getter and change-notification fanout |
| sase: `src/sase/ace/tui/modals/project_discovery.py:64,92`; `src/sase/project_aliases.py:233`; `src/sase/ace/patch/cache.py:64` | Repeated lifecycle/alias scans; metadata-based Patch cache |
| sase: `src/sase/project_tags/catalog.py:243,297`; `src/sase/current_project.py:81`; `actions/_startup_loads_tags.py:14` | Existing worker/peek and startup patterns to reuse |
| sase-core: `crates/sase_core/src/project_spec.rs:428,513`; `crates/sase_core_py/src/query/mod.rs:534` | Rust inventory disk access and existing GIL release |
| sase-github: `src/sase_github/workspace_plugin.py:64` | Provider detection and local Git subprocess |
| sase: `tests/ace/tui/widgets/test_prompt_vcs_mru_cycling.py`; `test_vcs_mru_cycling_logic.py` | Semantic tests to preserve; many widget tests replace the loader, explaining why they do not enforce real performance |
| sase: `src/sase/ace/tui/util/pump_tasks.py`; `util/perf.py`; `util/trace.py`; `docs/perf_runbook.md` | Scheduling and measurement mechanisms |

## Recommended solution

Implement **one background-refreshed, immutable launch-history snapshot shared by Space and Ctrl+N/P, together with pure warm prompt-catalog getters and coalesced off-thread watcher maintenance**. Make key handlers immediately use memory and update/focus the prompt; validate authoritative launch state at submission. Keep the current localized edits and key semantics.

Treat the snapshot and watcher repairs as one responsiveness change: the MRU substitution has demonstrated an approximately **11.5× reduction in synchronous cycling cost**, while the live watcher stack proves a second stall survives an MRU-only repair. Batch backend validation through Rust-owned domain APIs as needed, but prioritize removing those calls from interaction before expanding scope to widget reuse, parser rewrites, or a persistent indexing service. Verify first-visit-to-project behavior and actual key-to-paint/focus latency under load before declaring both keymaps fast.
