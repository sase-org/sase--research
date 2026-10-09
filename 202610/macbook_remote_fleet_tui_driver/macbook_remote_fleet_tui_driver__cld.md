# Making the MacBook the Main SASE TUI: Finishing Remote-Machine Agents-Tab Parity

_Researcher: cld · 2026-10-09 · Scope: `sase` (Python TUI/CLI) and the linked `sase-core`
(Rust gateway, federation worker, fleet contract v7)_

## TL;DR

- **Your plan is sound but needs restructuring.** A low-resource Mac acting as a
  thin controller over agents that run on athena/apollo fits SASE's architecture.
  About two-thirds of the plumbing already exists and is proven between athena and
  apollo: enrollment, gateway, federation worker, fleet rows, machine tabs, journaled
  stop/retry/fork, and the remote attention inbox.
- **What's missing is not a few features.** Remote parity has been pursued one
  operation and one wire field at a time, and that approach does not converge. The
  Agents tab exposes ~60 distinct operations. Today about 10 work on remote rows. About
  18 are silently disabled, and about 20 fall through to local-only code that gives
  wrong or misleading results. One of those is a real bug: remote **fork launches a
  local agent**.
- **Remote rows carry roughly 25 fields.** A local row is built from ~40 files in the
  agent's artifact directory plus the chat transcript and runner log. The built-in remote
  "content" viewer cannot open anything in production.
- **Recommended direction: "the owner executes, the viewer mirrors, the terminal hands
  off."** Replace per-operation parity with four generic mechanisms:
  1. **Read side:** an on-demand, bounded, evictable **artifact mirror**. The Mac fetches
     a remote agent's files into a namespaced viewer cache, so every existing
     file-based reader (decks, pager, `V`, `D`, `e`, copy keys) works unchanged.
  2. **Write side:** one allow-listed **fleet "operation" route** that forwards the
     *same durable operations* the TUI already submits locally (`sase agent
     persist-cleanup`, `persist-directive`, `revert`, `sase gate answer`, …) to the
     owning machine.
  3. **Terminal side:** **SSH handoff** for the inherently terminal operations (tmux,
     workspace shell), plus a universal **"open on owner"** escape hatch. This makes
     *every* operation reachable from day one.
  4. **Governance:** a **parity ledger test**. It forces every Agents-tab action to
     declare its remote disposition, so "every operation" stays true as new features
     land.
- **Do this right now, with zero code:** SSH (or mosh) + tmux into **athena's** TUI from
  the Mac. That gives you 100% operation parity today, at the lowest possible Mac
  resource cost. It also keeps working as the fallback while the native viewer matures.
- **Adjustments to your requirements are listed in [§6](#6-requirement-adjustments-explicitly-called-out).**
  The main ones:
  - Define "EVERY operation" as "every operation has a declared, tested remote path".
    Some of those paths are SSH handoffs, not native re-implementations.
  - Define "ALL data synced" as "all data reachable on demand through a bounded cache",
    not an eager full copy.
  - Add a per-machine **viewer role** with a default dispatch target and a
    local-launch guard. `%d` alone does not guard against forgetting it.
  - Drop the Mac's clean-and-pushed-checkout launch preflight. The owner ignores that
    evidence anyway.

---

## 1. Method and sources

I read the code and docs directly, and ran four parallel read-only code sweeps. I then
re-verified their highest-impact claims myself:

- **Agents-tab action inventory:** keymaps, palette, leader keys, copy keys, and
  remote gating.
- **Remote data path and local-vs-remote data availability.**
- **The sase-core gateway, federation worker, and fleet contract.**
- **What a Mac running the TUI executes in the background.**

Primary sources:

- **Docs:** `docs/remote_dispatch.md`, plus reference memory `dispatch.md`, `macros.md`
  and `tui.md`.
- **Decision records:** `agents-sync-publish-only`, `rust-core-required`,
  `host-owned-completion` and `corpus-before-mechanism`.
- **Beads:**
  - `sase-xe`, the remote dispatch epic.
  - `sase-133` / `sase-133.5`, Agents-tab parity, including its landing-audit note.
  - `sase-1bc`, machine tabs.
  - `sase-1j1`, the apollo snapshot stampede. It is in progress today. Phase .6, the
    gated apollo gateway restart, is still open.
  - The open fleet defects listed in §3.6.
- **Plan:** `plan:202610/apollo_gateway_snapshot_stampede.md`.
- **Live state on athena:** `sase machine list` (only `apollo` is enrolled),
  `~/.sase/fleet/worker_cache.json` (4.2 MB), and recent `done.json` /
  artifact-directory listings.

Paths below are relative to the `sase` repo unless prefixed `sase-core:`.

---

## 2. Where remote support stands today

### 2.1 Architecture as built

```
Mac/athena TUI (viewer)                          Owner (athena/apollo)
───────────────────────                          ─────────────────────
Agents tab
  └─ _schedule_agents_fleet_refresh  ──IPC──►  sase_federation_worker (local, Rust)
       (actions/agents/_fleet_refresh.py)        · AF_UNIX, 1 MiB frames, idle-exit 300 s
                                                 · per-host back-off 5→120 s
                                                 · disk cache ~/.sase/fleet/worker_cache.json
                                                        │ HTTPS + bearer credential
                                                        ▼ (Tailscale Serve → loopback)
                                                 sase_gateway /api/fleet/v1/*
                                                   hello, summary, catalog, batch, detail,
                                                   content, attention(+inventory,+resolve),
                                                   launch, mutate(stop|retry|fork), events(SSE)
                                                 · FleetReadService snapshot of
                                                   agent_artifact_index.sqlite, reused ≤60 s
                                                 · writes shell out to `sase mobile
                                                   agent-bridge` / `notification-bridge`
TUI actions → `sase machine agent|attention` (journaled durable procs, same-key recovery)
```

**What works well:**

- **Enrollment and trust:** bootstrap bundles, rotation, quarantine, version-skew
  diagnostics.
- **Machine tabs (`⌨ <alias>`) and grouping:** remote rows nest into owner-reported
  sessions and clans. A rendered-row parity oracle backs this (sase-133).
- **Lifecycle operations:** journaled, idempotent remote stop/retry with a 30 s
  acceptance window.
- **Remote attention:** questions and gates are reconciled into the durable
  notification inbox and answered through `RemoteAttentionModal`.
- **Honest feed health:** stale or invalid feeds show loudly in the header, banner,
  rows and detail panel.
- **Gateway hardening:** the snapshot-stampede fixes landed today (single-flight,
  back-off, bounded index work).

### 2.2 Wire facts that shape any design

- **Row shape.** A served row (`sase-core: crates/sase_core/src/fleet_contract/resolution.rs:141-214`)
  carries identity/locators, labels, status/bucket/lifecycle/liveness, model/provider,
  timestamps, clan/tribe/`agent_tab`, queue capacity/weight, owner presentation facts,
  per-row `capabilities.resource`, and **content metadata only** (`handle_count`,
  `kinds`, `total_byte_len`; `fleet_contract/content.rs:47-54`, `deny_unknown_fields`).
  It deliberately carries **no file paths, no full prompt (only a ≤512-byte `intent`),
  no token or cost data, and no error text**.
- **Served window.** The owner serves every live row plus terminal rows that are both
  ≤7 days old and among the newest 200 (`sase-core: crates/sase_core/src/fleet_presentation.rs:25-30`).
  A History scope exists, but the TUI never requests it.
- **Content handles** exist only in `/detail` responses
  (`sase-core: crates/sase_gateway/src/fleet_reads/resolution.rs:219-248`).
  Content kinds are Transcript, Output, Diff, Log and Question. **A path must
  canonicalize under the record's artifact dir**
  (`sase-core: crates/sase_gateway/src/fleet_reads/content.rs:166-188`).
- **Push vs pull.** SSE `/events` exists, but it publishes invalidations **only after a
  fleet launch**, and the federation worker never subscribes. In practice everything is
  polling.

---

## 3. Gap analysis

### 3.1 Operations: what happens when the selected row is remote

Gating works as follows. `check_action` (`src/sase/ace/tui/_app_action_availability_agents.py:177-291`)
re-routes `x`/`R`/`F`/`e`/`A` for remote rows when the row advertises the matching
capability. It returns False for everything in `_LOCAL_AGENT_ROW_ACTIONS` (lines 19-37),
and does so silently. **Leader keys (`,x`, `,r`, `,<space>`) and copy-mode keys (`%p`,
`%@`, …) dispatch straight to handlers and bypass this gate.** I verified this in
`actions/agent_workflow/_leader_mode.py:181-186, 318-329`.

| Class | Count | Examples |
|---|---|---|
| **Routed to the owner** | ~13 (≈10 actually work) | `x` stop (single, bulk, cleanup-panel), `R` retry, `A`/Enter/inbox answer and approve, `r` forced refresh, check provisional launch outcome |
| **Silently disabled** | ~18 | `n` rename, `N` tribe/tab, `U` unread, `V` metadata, `D` attempts, `a` artifacts/images, `t`/`T` tmux, jump to Patch, `W` new prompt waiting on agent, copy chat/file path, tool-run card/stop |
| **Falls through to local logic (wrong or misleading)** | ~20 | see bugs below; also `w` wait edit ("No artifacts directory"), `,r` revert ("No workspace directory"), `,x` kill-and-edit ("No prompt found"), `,<space>` builds a **local** `+project` prompt, `$` link-follow resolves the remote **name** in the **local** link index, `%p`/`%@` copy, every content deck shows empty or "No prompt file found." |
| **Works, viewer-local** | nav, marks, folds, grouping, `%n`/`%s` copy | — |

Confirmed defects:

1. **Remote fork is broken.**
   - `action_fork_agent` opens a "Fork on <alias>" prompt bar and records
     `_pending_remote_fork_identity` (`actions/agents/_fork_actions.py:107-123`).
   - The interception in `_submit_launch_proc` checks
     `display_name.startswith("Fork on ")` (`actions/agent_workflow/_launch_procs.py:81-89`).
   - But every caller passes `display_name=f"launch …"` or `"check launch …"`
     (`_launch_submission.py:330-331`, `_launch_bulk.py:189-190`,
     `_fleet_dispatch_launches.py:88`).
   - So the branch is dead. The user's fork instruction **launches as a new local
     agent**, and the pending identity is never cleared. This has been the case since
     `1a3a12a7ef`.
   - The only test (`tests/ace/tui/test_remote_lifecycle_actions.py:153-159`) asserts
     that the prompt bar opens, and stops there.
2. **Remote content can never open in production.**
   - `_content_handle_for` reads `fleet_content["handles"]`
     (`actions/agents/_remote_content.py:55-67`).
   - Real rows carry `ContentMetadataWire`, which has no handles. No Python code calls
     the federation `detail` op, though `_facade.py:255-266` exposes it.
   - Even with handles, the owner drops the two most valuable files:
     - `done.response_path` is stored as `~/.sase/chats/...` with a **literal `~`**.
     - `output_path` lives under `~/.sase/workflows/`.
     - Both resolve outside the artifact root. I verified this on a 2026-10-09
       `done.json`. Only `commit_diffs/*.diff` would survive.
   - The tests pass because they inject `{"handles": [...]}` by hand.
3. **Dismissing or saving remote rows does not stick.**
   - Cleanup-panel "dismiss done" (`_dismissing.py:106-180`) writes local dismissal
     state for remote rows.
   - `s` "save marked as group" (`_marking.py:101-160`) writes a local saved-group
     archive for them.
   - But `filter_explicitly_removed` applies only to the local base
     (`_fleet_projection.py:406-412`), so the rows come back on the next fleet refresh.
   - There is no remote dismiss operation at all, though rows carry a `dismissable`
     flag.
4. **Enter on a remote pending-gate row** takes the local gate path and reports "no
   longer pending" (`_agent_enter_scopes.py:40-43`). `A` works.
5. **Remote monitors, procs, clans and provisional launch rows cannot be stopped or
   cleared.**
   - The owner grants `lifecycle.stop` only to `AgentTurn` rows
     (`sase-core: …/fleet_reads/resolution.rs:226-232`).
   - Synthesized clan/session containers and provisional rows have no capabilities at
     all.
6. **Optimistic status bugs:**
   - With several remote rows selected, only the last row gets the override.
   - Any completion clears every override, including other machines'
     (`_remote_lifecycle.py:168-197`).

### 3.2 Data: what a local row has that a remote row lacks

Remote rows get a synthetic `project_file="/fleet/<id>/project.yml"`, so
`get_artifacts_dir()` returns `None`. **Every reader that goes through the artifact
directory comes back empty.**

| Data | Local source | Remote today |
|---|---|---|
| Full prompt, live reply, chat transcript | `raw_prompt.md`, `live_reply.md`, `~/.sase/chats/…` | ≤512-byte `intent`; nothing else |
| Tool calls / LLM calls / token usage | `tool_calls.jsonl`, `usage.json` | none |
| Diffs, live workspace diff, files deck | `commit_diffs/`, `diff_path`, workspace | none |
| Runner stdout, error and traceback | `~/.sase/workflows/*.txt`, `done.json` | none; a FAILED remote row shows **no reason** |
| Plan / epic / bead links | `plan_path`, `epic_bead_id`, … | plan action/committed flags only |
| Wait/queue context, attempt history, finalizer status, output variables, PR/bug/stitch | various field files | none, or capacity/weight only |
| Plan body for a remote plan approval | the plan gate bundle | **not shipped**: attention `preview` is always `None` (`sase-core: fleet_attention.rs:463`). You would approve plans blind |

A recent agent artifact dir on athena holds about 45 files. `tool_calls.jsonl` alone is
150 KB and `commit_diff.diff` is 74 KB. Small metadata (`agent_meta.json`, `done.json`,
`raw_prompt.md`, `live_reply.md`, `usage.json`, `workflow_state.json`) totals about
30 KB.

### 3.3 Sync behavior and cost

- **No fleet timer.** Remote rows refresh only after a *local* Agents apply, on
  switching to the Agents tab, on `r`, or after a remote mutation. A local apply is
  spaced at least 5 s apart and gated by stat-only change tokens.
  - On a Mac with **no local agents**, nothing changes locally, so remote rows refresh
    roughly every **300 s** (the sanity pass).
  - Off the Agents tab they never refresh.
  - The low-activity viewer you want is exactly the case that gets the stalest data.
- **Results are discarded if the selection moved** while a network refresh was in
  flight (`_fleet_refresh.py:528-530`), and no rerun is scheduled.
- **Coalescing shares a task set with attention polls.** A refresh requested while an
  attention poll runs is marked pending and never consumed. A forced refresh cancels
  attention announce tasks (`_fleet_refresh.py:86-102`; `_remote_attention.py:149-154`).
- **Per-refresh overhead:**
  - A new `FederationFacade`/`Supervisor` is built on every refresh, so `replace_config`
    is resent each time. The stampede plan called this out as amplification; the Python
    side still does it.
  - Each call also pays a health probe.
  - The catalog's first page bundles **all hosts into one IPC frame**. That is about
    336 KB per 100-row host page, measured from the cache, against a **1 MiB frame
    cap**. Two busy hosts fit; three will not.
- **SSD wear on a laptop.**
  - After *every* successful host read, the worker rewrites the whole 4 MiB cache file
    and fsyncs it under the cache lock (`sase-core: …/federation_worker/imp/remote_hosts.rs:603-613`,
    `imp/cache.rs:118-140`). That is several fsynced 4 MB writes per refresh.
  - Cache keys include unique continuation cursors, so most entries are never hit again.
- **Owner cost.** Each poll can trigger an owner snapshot rebuild: an index revalidate
  with a per-record stat. After sase-1j1 this is bounded, but every additional viewer
  (Mac + athena both polling apollo) adds owner load. Conditional fetches would
  remove most of it, since `/summary` already returns `catalog_snapshot_id` and
  `count_revision`.

### 3.4 Launching from the Mac

- **`%d` is free.** The Python alias table is `src/sase/macro/_directive_types.py:108-120`;
  the authoritative Rust contract has `dispatch` with `alias: None`
  (`sase-core: crates/sase_core/src/editor/directive/metadata.rs:737-749`). The two are
  bound together by a parity test (`tests/test_macro_directive_contract.py`).
- **Required changes for `%d`:**
  - The Rust contract.
  - The Python table.
  - The **narrow `scan_dispatch_directive` fast path**, `if "%dispatch" not in prompt:
    return None` (`_directive_scan.py:94`). It must also strip `%d`; otherwise the target
    receives `%d:…`.
  - `set_dispatch_directive` (it always writes `%dispatch:`).
  - The docs that say "no alias".
- **`%d` collision risk is low:**
  - The directive regex fires after whitespace or `([{"'`, so prose such as
    `printf("%d")` would produce a loud launch error.
  - The same is already true of `%c`, `%e`, `%i` and `%a`, which are also printf
    specifiers.
  - Fenced code and backticked text are safe.
- **Source preflight is pure friction on a viewer.**
  - Without Patch evidence, the controller requires the TUI's cwd to be a clean Git
    checkout with a pushed `HEAD` (`src/sase/dispatch/launch_preview.py:275-320`). It
    derives the project from `Path.cwd()`.
  - But the gateway forwards only `prompt`, `project_id` and model fields to the
    owner's bridge. **`revision`, `patch_ref`, `provider_ref` and `references` are
    validated and then dropped** (`sase-core: …/routes/fleet_handlers.rs:384-402`).
  - The Mac therefore has to maintain clean, pushed clones of every project to produce
    evidence the owner ignores.
- **The fleet HTTP body limit is 16 KiB** (`sase-core: …/routes/state.rs:44`). The
  contract allows 64 KiB prompts (`fleet_contract/error.rs:52`), so long `%d` prompts
  and fork instructions get a 413.
- **Local-only payloads are rejected:** attachments, images, files and collected
  inputs. Pasting a screenshot into a `%d` prompt from the Mac does not work today.
- **No default or sticky target.** A remote machine tab does not change where a launch
  runs; the prompt says "runs on ⌂ local · gD launch on <alias>".

### 3.5 The Mac as a host

- **No viewer or thin-client role exists.** `max_running_agents: 0` is rejected and
  falls back to 10.
- **Without `-x` and a disabled scheduler,** the Mac's TUI starts the service host,
  which starts the scheduler. The scheduler spawns 9 routine subprocesses (hooks 5 s,
  agent_waits 2 s, waits 10 s, sidecar_sync 30 s, usage 60 s, …). Your shared
  `~/.config/sase/sase.yml` also adds a 5 s `telegram` routine, which would
  then run on the Mac too.
- **macOS has no inotify,** so the TUI's artifact watchers fall back to token-gated
  polling.
- **The TUI itself runs constant timers:** 1 s countdown, 10 s auto-refresh, 2 s/5 s
  MRU and source polls, 30 s indicators, a 0.5 s proc observer, and watchdog/GC
  threads. On a viewer-only Mac, **the TUI process itself, not sync, will dominate
  CPU**. That argues for measuring before building (§7.7, P0).
- **Existing knobs:**
  - `sase service proc disable scheduler` (a persistent machine-local override).
  - `sase tui -x`, and `-r`/`-s` refresh intervals.
  - `ace.updates.*`, `llm_provider.usage_metrics.enabled`.
  - Machine overlays (`~/.config/sase/sase_<machine>.yml` with `id.machine_name`).

### 3.6 Reliability debt already filed

These open beads directly undermine "reliably". They should be prerequisites,
not afterthoughts:

| Bead | Defect |
|---|---|
| `sase-1j1.6` | apollo's gateway is still stopped pending the measured restart |
| `sase-zz` | a remote stop rejected for missing `lifecycle.stop` is journaled as `acceptance_uncertain` and never settles |
| `sase-1av` | the attention inventory reads only page 1 per host |
| `sase-1aw` | a stale cached snapshot reports `ok` after a network failure |
| `sase-1b3` | the owner snapshot stays frozen until index gc plus a gateway restart |
| `sase-1b4` | a live row reports FAILED while its `status_bucket` is running |
| `sase-11v` | fleet gate actions block the gateway request for the full gate execution |
| `sase-1ge` | fleet fault scenarios exceed the 16 ms j/k p95 budget |

---

## 4. Critique: is this a good idea?

### What is right about it

- **It matches how you actually use SASE.** Agents run where the CPU, RAM and repos
  are. The human sits at the laptop. Pull-based federation is naturally tolerant of a
  Mac that is often asleep or lid-closed.
- **Most of the hard trust and identity work is done.** That includes enrollment,
  per-scope credentials, journaled idempotent mutations, version skew, machine tabs and
  the attention inbox. Finishing it compounds the investment, because the same gateway
  serves mobile and Telegram.
- **The parity work pays off even without the Mac.** athena already views apollo with
  the same gaps.

### What is risky or wrong

1. **The current trajectory does not converge.**
   - Each remote operation so far has needed:
     - a wire field or capability,
     - a gateway route,
     - a bridge op,
     - a TUI branch,
     - fixtures,
     - and a live acceptance pass.
   - Read-only *rendering* parity alone took an epic, a child epic and repeated audits
     (sase-133, whose landing note found that hand-built fixtures hid production gaps).
   - With ~60 operations, local features landing weekly, and ~40 artifact files per
     agent, "one more field, one more route" leaves remote permanently behind.
   - The fork and content bugs show that the half-finished state is worse than either
     extreme: features *look* supported and quietly do the wrong thing.
2. **"Every operation" cannot be met by re-implementing every operation remotely.** A
   handful are inherently terminal-local, such as opening tmux in the agent's workspace
   or an interactive revert preview. They need a terminal on the owner, not an API.
3. **"All data synced" as an eager mirror conflicts with "low-resource Mac".** Most
   data is never looked at. What matters is that any of it is *reachable*.
4. **The low-resource constraint mostly bites in the TUI process, not in sync.** A
   native Textual TUI on macOS, without inotify, is the Mac's heaviest SASE component.
   Sync design should not be over-optimized while that cost is unmeasured.
5. **`%d` is the wrong safety net.** On a low-resource viewer, the dangerous failure is
   *forgetting* `%d`, which starts a heavy local agent. That needs a default target or a
   guard, not a shorter spelling.

### The alternative I would weigh seriously

**Run the TUI on athena and attach from the Mac (SSH or mosh + tmux).**

- **Advantages:**
  - 100% operation and data parity on athena's agents, today, with zero code.
  - Near-zero Mac resources.
  - athena's TUI already shows apollo's rows, with the same gaps as the native Mac
    viewer would have.
  - Clipboard already works over SSH: `src/sase/core/clipboard.py` pushes through `tmux
    load-buffer -w`, and the TUI has an OSC 52 delivery path.
- **Costs:**
  - Keystroke latency over the tailnet (mosh mitigates it).
  - No Mac-native integrations (images, sound, opening files in Mac apps).
  - A dependency on athena being up.

**Verdict:** adopt it **now** as the daily driver and the guaranteed fallback. Then
build the native Mac viewer with the generic mechanisms below. The native viewer earns
its keep through:
- resilience when athena is down,
- a unified view that doesn't route through athena,
- Mac-native integrations,
- and the reusable owner-operation and mirror infrastructure, which also helps athena
  viewing apollo and mobile.

---

## 5. Options considered

| Option | Read parity | Write parity | Mac cost | Build cost | Converges? | Verdict |
|---|---|---|---|---|---|---|
| **A. Continue per-operation typed parity** (status quo trajectory) | add wire fields per datum | add route/bridge/branch per op | low | very high, unbounded | **No** | Reject as the strategy; keep the existing typed stop/retry/fork |
| **B. SSH/mosh + tmux into the owner's TUI** | 100% | 100% | lowest | ~0 | Yes | **Adopt now** as daily driver and escape hatch |
| **C. Generic mechanisms: artifact mirror + operation forwarding + SSH handoff + parity ledger** | ~100% via existing readers | ~100% via existing durable ops | low (bounded cache, conditional polling) | large but bounded | **Yes** | **Recommended** native path |
| **D. Mount owners' `~/.sase` on the Mac (sshfs/NFS)** | 100% "for free" | none | low CPU, but network I/O on the TUI event loop | low | partial | Reject: macFUSE friction on Apple Silicon, TUI stalls on network I/O (`tui_perf.md` concerns), breaks offline |
| **E. Owner-rendered detail** (`sase agent show` over the gateway) | main panel only; no tools/LLM/diff/files decks | none | low | medium | No | Reject as primary; fine as a fallback for the header |
| **F. Re-import remote agents into local state** (old agents-sync import leg) | 100% | confusing (whose state?) | high | high | — | Reject: explicitly deleted (`decisions:agents-sync-publish-only`) |

---

## 6. Requirement adjustments (explicitly called out)

1. **"EVERY agent operation" means every operation has a declared, tested remote
   disposition.** Not every operation is re-implemented natively. Each action
   (keymap, leader key, copy-mode key, palette command) declares exactly one of:
   - `REMOTE_OP(kind)`: forwarded to the owner.
   - `MIRROR_READ`: served from the mirrored artifacts.
   - `VIEWER_LOCAL`: presentation state such as marks, folds and unread.
   - `SSH_HANDOFF`: runs on the owner in a terminal.
   - `N/A(reason)`: with a visible message. For example, `,X` "kill-and-edit **last
     local** launch" has no remote meaning.

   *Why:* this is achievable, testable, and stays true as features are added. Native
   re-implementation of terminal-centric operations buys nothing over a handoff.
2. **"ALL data synced" means all data *reachable*, behind a bounded cache.**
   - Small metadata is fetched for the *selected* remote row.
   - Heavy files are fetched when a view needs them.
   - A manual keymap bulk-syncs a machine's metadata tier.
   - The cache is an LRU with a byte cap.

   *Why:* the same "everything displayable" outcome at a fraction of the Mac's disk,
   network and owner load.
3. **Add a viewer role for the Mac, with a default dispatch target and a local-launch
   guard.** `%d` is still worth adding. The role should also:
   - disable the scheduler,
   - optionally set `dispatch.default_target: athena`,
   - and confirm or deny local launches.

   *Why:* the costly mistake on a weak machine is the forgotten `%d`. You said manual
   `%d` is fine; I'm recommending the guard anyway because it is cheap and prevents the
   one failure that actually hurts the Mac.
4. **Relax or replace the launch source preflight.** On a viewer launch,
   default to **owner-resolved source**: the owner's project checkout and workspace
   rules, driven by `+project` / `#gh:` refs in the prompt. Alternatively, make the
   owner actually honor `revision`/`patch_ref`.

   *Why:* today the Mac must keep clean, pushed clones of every project to produce
   evidence the gateway drops.
5. **Mutations go to the owner. Viewer-local state is limited to presentation.**
   - Dismiss, save-as-group, tribe, tab, wait, rename and revert are forwarded.
   - Marks, folds, deck layout and (by default) unread stay viewer-local, keyed by the
     remote logical key.

   *Why:* athena's TUI and the Mac's TUI can both be open, and they must agree on what
   is dismissed.
6. **Attention freshness is not "slow sync".** Pending questions and plan/gate
   approvals should keep the ≤60 s inventory poll, or better, independent of how
   lazily agent rows refresh. The **plan body must be readable before approving**,
   which is in scope.
7. **Launch parity includes long prompts and attachments.**
   - Raise the 16 KiB fleet body limit for `/launch` and `/mutate` (fork).
   - Image/attachment `%d` launches can follow later through the gateway's existing
     attachment machinery.
8. **Out of scope for this effort:** remote parity for the Patches, Artifacts, Beads and
   Services tabs. Beads already sync through their sidecar. Agents-tab actions that
   *jump* to those tabs get an `N/A` or `SSH_HANDOFF` disposition.

---

## 7. Recommended solution

### 7.1 Principle

**The owner executes, the viewer mirrors, the terminal hands off.**
- The Mac never re-implements owner behavior.
- It (a) caches the owner's files for reading.
- It (b) forwards the *existing* durable operations for writing.
- It (c) opens a terminal on the owner for anything inherently interactive.

One parity ledger makes "every operation" a CI-enforced property.

### 7.2 Read side: an on-demand artifact mirror

**sase-core (fleet contract v8):**
- Add `POST /api/fleet/v1/artifacts/manifest {logical_key, row_revision, tier}`. It
  returns `[{handle_id, kind, virtual_path, byte_len, sha256, mtime, supports_growth}]`.
  The entries cover:
  - the record's artifact dir,
  - **plus allow-listed external roots mapped to virtual paths:** `chat/<file>` for the
    transcript (expand the literal `~`) and `output/<file>` for the workflow log.
- Emit the already-declared but unused `Artifact` content kind. Reuse `/content` ranged
  reads (64–256 KiB, sha256-verified, tailable for growing files).
- Exclude lock files and enforce per-tier byte caps.
- Fetch the plan body for plan gates through the same mechanism, and populate the
  attention `preview` handle.

**Python viewer:**
- **Mirror location:** `FleetMirror` at
  `~/.sase/fleet/mirror/<installation_id>/<project_id>/<turn_id>/<run_id>/…`. This is
  outside `~/.sase/projects`, so the local artifact index never sees it.
  - Writes are atomic.
  - A per-agent `manifest.json` makes re-sync incremental.
  - An LRU byte cap applies (`dispatch.mirror.max_bytes`, e.g. 512 MB by default).
- **Row builder:** when a remote row has a mirror, set its artifacts dir to the mirror,
  so `get_artifacts_dir()` works. Route owner absolute paths (`response_path`,
  `output_path`, `diff_path`, plan paths) through one mapper, `resolve_agent_path(agent,
  raw)`. All existing readers then light up: main deck prompt/reply, tools and LLM-calls
  decks, files/diff deck, `V`, `D`, `e` (read-only), `a`, images, and the `%p`/`%c`/`%E`
  copy keys.
- **Fetch tiers:**
  - **Tier A** (~30 KB/agent: meta, done, raw prompt, live reply, usage, workflow
    state): debounced fetch on selection of a remote row.
  - **Tier B** (transcript, tool calls, diffs, output, images): fetched when the view
    that needs it opens. Live rows tail growing files only while that view is visible.
  - **Tier C:** the manual "sync machine" key (§7.5) fetches Tier A for every served row
    on that machine and pulls the History catalog page.
- **I/O rules:** all I/O runs off the event loop, under the `tui_perf.md` rules, with a
  visible "syncing ⌨ apollo…" chip.
- **Cost estimate:** a full Tier-C sync of 200 agents is about 6–10 MB once, and
  near-zero afterwards because of sha256 skips.

**Decision record to write.** "Remote agent artifacts are a viewer cache, never local
state." This consciously meets the reopen condition of `agents-sync-publish-only` with a
*new* design, as that record demands:
- no registry rows, no index entries, no import journals;
- evictable at any time;
- keyed by owner identity.

**Rejected alternative:** `rsync` over Tailscale SSH. It is simple and incremental, and
would be a fine prototype spike. But it bypasses the per-scope fleet credentials and
audit, and it needs owner path knowledge on the viewer.

### 7.3 Write side: forward the durable operations the TUI already has

The TUI already funnels agent mutations through `_submit_durable_proc(argv, operation,
request, …)`. These are registered as proc-producer sites in
`src/sase/ace/tui/_proc_producer_sites_actions.py`:
- `agent.cleanup` → `sase agent persist-cleanup` (kill/dismiss/save),
- `agent.directive` → `sase agent persist-directive` (wait/queue/tribe/tab),
- `agent.revert.preview|execute`,
- `notify.state`, `notify.gate`, `notify.plan_gate`,
- `monitor.stop`, `proc.kill`, `tool.stop`.

**That is the seam.**

**sase-core:**
- Add `POST /api/fleet/v1/operation` with a new scope `fleet.operation`. The request is
  `{operation_key, target:{logical_key,row_revision}, kind: FleetOperationKindWire,
  payload}`.
- `kind` is a closed, allow-listed enum: `agent_cleanup`, `agent_directive`,
  `agent_revert_preview`, `agent_revert_execute`, `notify_state`, `monitor_stop`,
  `proc_kill`, `tool_stop`, `agent_rename`, …
- Each kind has a per-kind payload schema and a required per-row capability. The owner
  computes the capabilities from its own state: `agent.dismiss` iff dismissable,
  `agent.directive.wait` iff waiting or queued, and so on.
- The owner:
  - journals the operation (same-key recovery, like `/mutate`),
  - resolves the logical key to its local artifacts dir,
  - rewrites identity fields,
  - and runs the same CLI through a bridge op inside `spawn_blocking`. Current
    `/mutate` and attention handlers block a tokio worker (sase-11v); the new route
    must not.
- **Never** forward generic `sase <tokens>` (`command-line.submit`).

**Python:**
- One dispatcher in the durable adapter: if the target agents are remote, submit `sase
  machine op <alias> <kind> --request-sidecar <file>` as a journaled durable proc,
  mirroring `sase machine agent`. Otherwise run locally.
- Thin per-kind payload adapters stay in Python. The kind registry, wire, and
  capability rules live in Rust, per the Rust-core boundary.

**Composite operations become compositions:**
- `,x` kill-and-edit = remote stop + open a prompt bar pre-filled with the mirrored raw
  prompt and `%d:<alias>`.
- `R` retry gets the same edit-bar experience as local.
- `W` = a prompt bar pre-filled with `%d:<alias> %w:<name>`.
- `,<space>` = `%d:<alias> +<project>`.
- Fix the fork interception: use an explicit launch-context flag, not a display-name
  prefix.

### 7.4 Terminal side: SSH handoff and an "open on owner" escape hatch

- **Reuse the per-machine SSH target** that remote sudo already uses (`sase machine add
  -S`, `sase machine show`).
- **`t` / `T` on a remote row** opens a local tmux window running `ssh -t <target> --
  tmux new-session -A -s <agent> -c <owner_workspace>`. The row needs the owner's
  `workspace_dir` on the wire; that is an owner-local path, used only on the owner.
- **Add an "Open on owner" key** that runs `ssh -t <target> -- sase tui -t agents
  --select <agent>`. This needs a small new `--select` deep-link flag. It is the
  universal fallback: from the day it ships, **every** operation is reachable on every
  remote row, even before its native disposition lands.

### 7.5 Mac viewer profile, `%d`, sync policy and keymaps

- **`%d` alias** for `%dispatch`. Change all of these together:
  - the Rust directive contract, plus its editor/LSP examples and matrix test,
  - the Python alias table,
  - `scan_dispatch_directive`'s fast path and stripping,
  - `set_dispatch_directive`,
  - `docs/macros.md` and the `dispatch.md` / `macros.md` reference notes (through
    `/sase_memory_write`),
  - and the sase-nvim syntax, if it lists aliases (not checked; the repo was not
    opened).
- **Viewer role:** `machine.role: viewer`, in the Mac's `sase_<mac>.yml` overlay. It
  implies:
  - the scheduler service proc is disabled;
  - `dispatch.local_launch: confirm` (allow / confirm / deny);
  - an optional `dispatch.default_target: <alias>`, inserted as `%d:<alias>` when a
    prompt has none;
  - TUI auto-start of the service host is skipped (today's `-x`).
- **Fleet refresh policy:** `dispatch.fleet.refresh_interval_seconds`.
  - The default is 30 s while the Agents tab is visible; 0 means manual only.
  - It runs on its own timer, independent of local applies.
  - Each tick does a summary-first conditional fetch: skip `/catalog` when
    `catalog_snapshot_id` is unchanged.
  - Use per-host catalog frames and keep one long-lived federation supervisor.
- **Manual sync keymaps:**
  - **`,Y`** "sync selected machine": a deep Tier-C mirror plus a forced catalog. It
    sits next to `,y` "full history refresh". Bare `Y` is globally bound to Patch sync.
  - **`S`** in Admin Center → Machines: the same action for the highlighted machine.
  - Add both to `src/sase/default_config.yml` (per the gotchas memory) and to the help
    modal and footer.
- **Worker hygiene:**
  - Debounce or batch cache persistence (for example at most once per 30 s, or
    per-entry files).
  - Stop caching unique continuation-cursor pages.
  - Have `s` (hello) reset back-off.

### 7.6 Keeping "every operation" true: the parity ledger

- Add **one availability gate** used by every entry point: keymaps, leader keys,
  copy-mode keys, palette and Enter. That closes the leader/copy bypass.
- Add a declarative `REMOTE_DISPOSITIONS` table covering every Agents-tab action, plus a
  test that **fails when an action has no disposition**. New features then cannot
  silently reintroduce local-only fall-through.
- Behavior tests per disposition class must use the **realistic owner fixture**, not
  hand-built capabilities or handles. Both the fork bug and the content bug hid behind
  hand-built ones. Tests must also go through the real submit path.
- Run live acceptance from the Mac using the existing remote `sase screenshot` capture
  over SSH.

### 7.7 Phased roadmap

| Phase | Content | Size | Notes |
|---|---|---|---|
| **P0 (now)** | SSH/mosh + tmux into athena's TUI as the daily driver. Finish `sase-1j1.6` (apollo gateway restart). Enroll athena *and* apollo on the Mac. Measure `sase tui -x` CPU/RAM on the Mac with only remote rows | — | Gives full parity immediately. The measurement decides how much the native viewer must slim down |
| **P1: make what exists correct** | Fix fork, Enter-on-gate, leader/copy gating, and the dismiss/save fall-through. Add the dedicated fleet timer. Fix the selection-drop and task-set coalescing bugs. Raise the body limit. Fix worker cache persistence, per-host frames and the persistent supervisor. Close `sase-zz`, `-1av`, `-1aw`, `-1b3`, `-1b4`, `-11v` | M | Pure reliability; required before claiming "reliably" |
| **P2: Mac ergonomics** | `%d`; viewer role; default target and local-launch guard; owner-resolved source; refresh policy; `,Y` and Machines `S` | S–M | Makes the Mac a viable launch point |
| **P3: read mirror** | Core manifest route, `Artifact` kind, external roots, plan preview. Python mirror, path mapper, tiers, LRU | L | Unlocks every read-side action and the plan body; prerequisite for edit-bar retry and kill-and-edit |
| **P4: write forwarding** | Core `/operation` route, kinds and capabilities; owner bridge; Python durable-adapter dispatcher; migrate dismiss/save/wait/tribe/tab/rename/revert/monitor/proc/tool stops; compose `,x`, `W`, `,<space>` | L | The bulk of write parity, with no per-op routes |
| **P5: terminal handoff** | `t`/`T` over SSH; "Open on owner" plus `sase tui --select` | S–M | Can ship any time after P1; it is the universal fallback |
| **P6: ledger and acceptance** | Disposition table and test, single availability gate, realistic-fixture tests, live Mac acceptance | S–M | Start alongside P1 so each later phase turns ledger rows green |
| **Later** | Owner publishes `/events` invalidations on every agent state change; worker subscribes; polling becomes a fallback | M | Push freshness at near-zero idle cost |

**Acceptance criteria for "done":**
- Every Agents-tab action has a non-`TODO` disposition in the ledger, with a green test.
- On the Mac, a remote row and the owner's own row render identically after Tier A/B
  sync. Extend the sase-133 rendered-row oracle to the decks.
- Every `REMOTE_OP` settles with a receipt and is visible on the owner's TUI.
- An idle Mac viewer makes at most two small summary requests per refresh interval.
- The worker cache causes no more than one fsynced write per 30 s.

### 7.8 Decision records to add

1. **Remote artifacts are a viewer cache, never local state.** This reopens
   `agents-sync-publish-only` deliberately, under its own reopen clause.
2. **Remote mutations forward the TUI's durable operation kinds through one allow-listed
   fleet route.** No per-operation routes after `/mutate`; no generic remote shell.
3. **Every Agents-tab action declares a remote disposition.** This is CI-enforced.
4. **Viewer machines resolve launch source on the owner.** The controller-side
   checkout proof is dropped unless the owner honors it.

### 7.9 Risks and open questions

- **Owner load from mirrors.** Range reads are cheap file I/O, but they must share the
  gateway's bounded semaphore and never trigger snapshot rebuilds. `/detail` and
  `/content` currently read from the presentation snapshot. History-only rows need a
  path that does not rebuild History per request.
- **Contract churn across three machines.** v8 must be read-compatible both ways. Per the
  existing doc, upgrade the controllers first, or the fleet in lockstep, and keep
  machine-tab fallbacks.
- **Privacy of mirrored data.** Transcripts and prompts land on the laptop. Use 0600
  files, an optional `dispatch.mirror.max_age`, and a "purge mirror" command.
- **The Mac TUI's own CPU.** If the P0 measurement shows the Textual process is too
  heavy, the right fix is a lighter viewer profile (longer timers, no local-scan work
  when the machine has no local agents), or simply staying on SSH. More sync work will
  not help.
- **The Mac's hostname caveat.** Under zsh `$HOSTNAME` is unset, so the federation
  socket path falls back to `sase-host`. That is harmless unless some process exports
  `HOSTNAME`, in which case two workers would share one cache file.

---

## 8. Recommended solution (summary)

1. **Today:** drive SASE from the Mac by SSH/mosh + tmux into athena's TUI. Finish the
   apollo gateway restart (`sase-1j1.6`) and enroll both athena and apollo on the Mac.
   Measure the native TUI's footprint on the Mac before committing to heavy native work.
2. **Then build the native Mac viewer.** Do not continue per-operation parity. Build
   four generic mechanisms:
   - an **on-demand, bounded artifact mirror**, so every existing reader works on
     remote rows;
   - **forwarding of the TUI's existing durable operations** through one allow-listed
     fleet route;
   - **SSH handoff plus an "open on owner" escape hatch** for terminal operations and
     as the universal fallback;
   - **a CI-enforced parity ledger** behind a single availability gate.
3. **Fix the existing remote defects first:**
   - broken fork, dead content viewer, non-sticky dismiss, Enter-on-gate, leader/copy
     bypass;
   - refresh tied to local activity, selection-drop, coalescing, 4 MiB fsync per read,
     1 MiB frame ceiling, 16 KiB body limit;
   - the open fleet beads.
4. **Make the Mac an explicit viewer:**
   - the `machine.role: viewer` overlay (scheduler off, local-launch confirm, optional
     default target),
   - `%d` as an alias of `%dispatch`,
   - owner-resolved launch source,
   - a summary-first fleet refresh timer,
   - `,Y` and Machines `S` to sync the selected machine on demand.

This keeps the Mac light, makes remote data as complete as local data whenever you look
at it, and turns "every operation" from an aspiration into a tested invariant. It also
improves athena's view of apollo and the mobile gateway along the way.

---

## Appendix A: Evidence index (selected)

- **Fork interception dead branch:** `src/sase/ace/tui/actions/agent_workflow/_launch_procs.py:81-89`
  vs callers `_launch_submission.py:330-331`, `_launch_bulk.py:189-190`,
  `actions/agents/_fleet_dispatch_launches.py:88`. Origin: `1a3a12a7ef`.
- **Content handles expected but never present:** `actions/agents/_remote_content.py:55-67`;
  `sase-core: crates/sase_core/src/fleet_contract/content.rs:47-54`. Capabilities are
  `CapabilitySetWire{resource,host,protocol}` (`content.rs:69-74`), so the TUI's
  `resource` lookup *does* match real rows. The capability side is fine; only content
  is broken.
- **Owner content roots:** `sase-core: crates/sase_gateway/src/fleet_reads/content.rs:97-188`.
  The `done.json` sample has `response_path: '~/.sase/chats/202610/…'` and `output_path:
  '/home/bryan/.sase/workflows/202610/…'`.
- **Launch forwarding drops source evidence:** `sase-core: crates/sase_gateway/src/routes/fleet_handlers.rs:384-402`.
  Controller preflight: `src/sase/dispatch/launch_preview.py:275-320`.
- **Body limit:** `sase-core: crates/sase_gateway/src/routes/state.rs:44`, `router.rs:100`;
  prompt limit `fleet_contract/error.rs:52`.
- **Worker cache persistence:** `sase-core: crates/sase_gateway/src/federation_worker/imp/remote_hosts.rs:603-613`,
  `imp/cache.rs:110-130`.
- **Fleet refresh triggers and selection drop:** `src/sase/ace/tui/actions/agents/_fleet_refresh.py:77-107, 509-545`.
- **Remote rows not filtered by local dismissal:** `src/sase/ace/tui/actions/agents/_fleet_projection.py:395-420`.
- **Leader dispatch without remote gating:** `src/sase/ace/tui/actions/agent_workflow/_leader_mode.py:181-186, 318-329`.
- **Durable operation seam:** `src/sase/ace/tui/_proc_producer_sites_actions.py`;
  `src/sase/ace/tui/actions/agent_durable.py:30-70`.
- **Directive alias table and narrow dispatch scan:** `src/sase/macro/_directive_types.py:27-34, 108-120`;
  `src/sase/macro/_directive_scan.py:87-100`.
- **Leader keys (`,Y` free; `,y` = full history refresh):** `src/sase/default_config.yml:1135-1165`.
  `Y` is globally bound to Patch sync (`src/sase/ace/tui/bindings.py:64`).

## Appendix B: Recommended disposition for each operation group

| Operation group | Keys | Today on remote rows | Disposition |
|---|---|---|---|
| Stop / kill (single, bulk, cleanup) | `x`, `X` | works (stop) | keep typed `/mutate`; add monitor/proc stop through `REMOTE_OP` |
| Retry | `R` | works, but no edit bar | typed retry + mirrored-prompt edit bar |
| Fork / resume | `F` | **broken (launches locally)** | fix interception; typed fork |
| Kill-and-edit | `,x` | "No prompt found" | stop + `%d:<alias>` prompt from mirror |
| Dismiss / save group / revive | `X`→dismiss, `s`, `!R` | local write, row reappears | `REMOTE_OP(agent_cleanup)` |
| Wait/queue, tribe/tab, rename | `w`, `N`, `n` | disabled or misleading | `REMOTE_OP(agent_directive / agent_rename)` |
| New prompt waiting on / in project | `W`, `,<space>` | disabled / local launch | compose `%d:<alias>` prompt |
| Revert | `,r` | "No workspace directory" | `REMOTE_OP(agent_revert_preview/execute)` |
| Answer / approve | `A`, Enter, inbox | works (Enter on gate row broken) | fix Enter; add plan preview through the mirror |
| Prompt, reply, chat, tools, LLM calls, diff, files, metadata, attempts, artifacts, images | decks, `e`, `V`, `D`, `a` | empty or disabled | `MIRROR_READ` |
| Copy prompt / chat path / file path / ref / tool-run id | `%p` `%c` `%E` `%@` `%r` | missing or wrong | `MIRROR_READ`; machine-qualified refs |
| tmux / workspace | `t`, `T` | disabled | `SSH_HANDOFF` |
| Tool-run card / stop | palette | "lives on <machine>" | mirror tool-run store, or `REMOTE_OP(tool_stop)` |
| Unread, mark-all-read, unread jumps | `U`, `,u`, `,j` | disabled / local-only | `VIEWER_LOCAL`, keyed by logical key |
| Link follow | `$` | resolves the local name (wrong) | owner-qualified subject, or `N/A` with message |
| Provisional `%dispatch` row | palette | check works; cannot clear | add "discard provisional row" |
| Prompt-bar completions of remote names | `%w:` etc. | offered as local names | machine-qualify or filter |
| Kill-and-edit last local launch | `,X` | n/a | `N/A` (local-only by definition) |
| Anything not yet native | — | — | "Open on owner" (SSH into the owner's TUI) |
