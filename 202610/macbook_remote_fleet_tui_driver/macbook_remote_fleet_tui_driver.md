# Making the MacBook the Main SASE TUI: Remote-Agent Parity (Consolidated)

> **Research query:** How should SASE's remote machine support be finished so that a
> low-powered MacBook can be the main driver of the SASE TUI — launching remote agents
> with a manually specified `%dispatch` directive (plus a new `%d` shorthand), reliably
> performing every Agents-tab operation on remote agents, and syncing and displaying all
> remote agent data, even if slowly or only through a manual per-machine sync keymap? Is
> this a good idea, would a different approach be better, and what requirement
> adjustments and recommended solution are justified?

![Infographic "SASE from a lightweight Mac": start today with SSH/mosh + tmux from the MacBook into athena, build a native Mac viewer next, the verified findings, the four proposed mechanisms (read, write, terminal, parity), how to keep the Mac light, the recommended sequence, and when to switch to native](macbook_remote_fleet_tui_driver_infographic.png)

## Bottom line

- **The goal is right, but "finish the implementation" understates the work.** Running
  agents on athena/apollo while you drive from the Mac fits SASE's design, and all five
  reports agree.
  - Remote **list/render** parity shipped (`sase-133`). Remote **operation and data**
    parity did not.
  - A remote row today is a summary of about 25 fields. It has no prompt, transcript,
    runner output, tool calls, error text, or file paths.
  - Only stop, retry, and attention answering really work on remote rows.
- **Two features that look shipped are broken in production.** I verified both:
  - Remote `F` (fork) [**launches a local agent**](#fork-detail). On a weak Mac that is
    the worst failure possible.
  - The remote content viewer [**can never open anything**](#content-viewer-detail).
    Even if it could, the owner refuses to serve the transcript and the runner output.

  Three of the five reports (grk, mus, gem) describe both features as working. Only cld
  found the fork bug. No bead tracks either one.
- **Start today with SSH/mosh + tmux into athena's TUI.**
  - It gives full parity with no new code and costs the Mac almost nothing.
  - It structurally cannot launch agents on the Mac.
  - Keep it permanently as the escape hatch.
- **Then build the native Mac viewer from four generic mechanisms, not operation by
  operation:**
  1. an owner [**manifest plus a bounded on-demand
     mirror**](#reads-through-a-manifest-and-on-demand-mirror) for reads;
  2. one allow-listed [**operation
     route**](#writes-forwarded-through-the-existing-durable-operations) that forwards
     the TUI's *existing* durable operations for writes;
  3. an [**SSH handoff**](#terminal-work-through-ssh-handoff-and-open-on-owner) for
     terminal work;
  4. a CI-enforced [**parity ledger**](#parity-ledger-and-tests).

  Wiring parity one operation at a time has not converged after two epics. With ~60
  operations, it won't.
- **Sync should be [cache-first](#sync-policies-and-keys), with a scoped manual key
  (`,s`).**
  - Keep the 60 s attention poll on unless you choose strict-manual mode.
  - Today, fleet refresh is [triggered by *local* roster
    applies](#refresh-coupling-detail) and always fans out a network catalog to every
    host.
  - On athena that was the client keeping apollo's gateway melted this morning. On an
    idle Mac the same coupling leaves remote rows ~5 minutes stale.
- **Add `%d`, but it is not the real safety net.** On a weak machine the costly mistake
  is *forgetting* `%d`. Add a [viewer role](#dispatch-shorthand-and-the-mac-viewer-role)
  whose local launches require confirmation.

## Verified state of remote support

Verified state: report claims vs. the code.

### What already exists

Every report agrees on this foundation, and I re-confirmed the parts that matter.

**Trust and transport:**
- One-use bootstrap enrollment, scoped controller credentials, pinned installation
  identity, quarantine and repair, and version-skew reporting.
- Gateways listen on loopback behind tailnet-only Tailscale Serve. athena's gateway is up
  on `127.0.0.1:7629` and served at `https://athena.tail297af1.ts.net`.
- athena's enrollment of apollo already records an SSH target (`ssh=apollo`).

**Federation worker** (Rust, local to the controller):
- Unix-socket IPC with 1 MiB frames.
- Per-host back-off from 5 s to 120 s and per-host in-flight caps.
- A disk cache of 256 entries / 4 MiB.

**Fleet contract v7** (gateway protocol v3):
- Read routes: hello, summary, catalog (with a History scope), batch, detail, ranged
  content, and attention.
- Write routes: launch and a closed mutation set — `lifecycle.stop`, `lifecycle.retry`,
  `lifecycle.fork`.
- Mutations are journaled. A lost response is recovered with the same operation key
  inside an acceptance window of at least 30 s.

**TUI:**
- One Agents list with machine chips, machine tabs, group-by-machine, `machine:` queries,
  and a Machines admin pane.
- Remote rows nest into owner-reported sessions and clans.
- The Launch Target picker is `gD` (NORMAL) / `Ctrl+G D` (INSERT).
- Pending remote questions and gates reconcile into the durable notification inbox and
  are answered on the owner.

**Served window and other limits:**
- Each owner serves every live row plus terminal rows up to 7 days old, capped at the
  newest 200.
- Workflow-step rows are not served.
- A remote sudo flow with an SSH handoff already exists.

The key architectural fact: **a remote row is a viewer projection, not a local agent with
its paths filled in.** Remote rows get a synthetic project file, so `get_artifacts_dir()`
returns `None`. Every reader that goes through the artifact directory therefore comes back
empty. All reports agree this separation is correct. The gaps come from TUI code that
still assumes local paths.

### Confirmed defects and gaps

| # | Finding | Reported by | My verification |
|---|---|---|---|
| 1 | **Remote fork launches a local agent** | cld (grk, mus, gem said fork works) | **Confirmed.** [See below](#fork-detail). Untracked. |
| 2 | **Remote content viewer cannot open production rows** | cdx, cld | **Confirmed.** [See below](#content-viewer-detail). |
| 3 | **Owner refuses to serve the transcript and runner output** | cld | **Confirmed.** [See below](#transcript-and-output-detail). |
| 4 | **Dismissing or saving remote rows does not stick** | cld | **Confirmed.** `filter_explicitly_removed` is applied only to `local_base` (`_fleet_projection.py:406-412`). Remote rows return on the next fleet apply. |
| 5 | **Plan approvals from a viewer are blind** | cld | **Confirmed.** The attention wire has a `preview` handle, but the builder always sets `preview: None` (`fleet_attention.rs:463`). |
| 6 | **Launch source evidence is validated, then dropped** | cld | **Confirmed.** [See below](#launch-source-detail). |
| 7 | **16 KiB request body vs 64 KiB prompt cap** | cld | **Confirmed.** `FLEET_REQUEST_BODY_LIMIT_BYTES = 16 * 1024` (`routes/state.rs:45`) vs `MAX_LAUNCH_PROMPT_BYTES = 64 * 1024`. Long `%d` prompts and fork instructions will get a 413 error. |
| 8 | **Fleet refresh is triggered by local applies and always hits the network** | cld, grk (disagreed on cadence; both right) | **Confirmed.** [See below](#refresh-coupling-detail). |
| 9 | **Worker fsyncs its whole cache after every successful host read** | cld | **Confirmed.** `remote_hosts.rs:603-613` calls `cache.persist()`, which rewrites the file and calls `sync_all()` under the cache lock. That is several 4 MB fsynced writes per refresh on a laptop SSD. |
| 10 | **No push path** | cld | **Partly confirmed.** The federation worker never subscribes to `/events`. Everything is polling. |
| 11 | **Leader keys bypass remote gating** | cld | **Confirmed** for `,r` (revert) and `,x` (kill-and-edit). Both call handlers directly (`_leader_mode.py`). |
| 12 | **`%d` needs more than an alias-table edit** | all; cdx, cld, grk, and gem caught the fast path | **Confirmed.** [See below](#dispatch-alias-detail). |
| 13 | **No viewer role exists** | cld | **Confirmed.** A `max_running_agents` value below 1 silently falls back to 10 (`_settings_runner.py`). |
| 14 | **Open reliability beads** | cld, grk | **Confirmed.** [See below](#bead-status-detail). |

#### Fork detail

Finding #1 (fork):
- `action_fork_agent` opens a `Fork on <alias>` prompt bar and records
  `_pending_remote_fork_identity` (`_fork_actions.py:119-122`).
- The intercept in `_submit_launch_proc` fires only when
  `display_name.startswith("Fork on ")` (`_launch_procs.py:82`).
- Every caller passes `launch …` or `check launch …` instead
  (`_launch_submission.py:331`, `_launch_bulk.py:190`, `_fleet_dispatch_launches.py:89`).
- So the fork instruction runs as a new local agent, and the pending identity is never
  cleared.
- The only test stops once the prompt bar opens (`test_remote_lifecycle_actions.py:153`).

#### Content viewer detail

Finding #2 (content viewer):
- `_remote_content.py:55-67` looks for `handles` / `content_handles` in `fleet_content`.
- But `fleet_content` is filled from the summary's `ContentMetadataWire`. That struct has
  only `handle_count`, `kinds`, and lengths, and uses `deny_unknown_fields`.
- Real handles exist only in the `/detail` response, and **no Python code calls
  `FederationFacade.detail()`**.
- The tests pass because they inject `{"handles": [...]}` by hand.
- cdx adds three more problems:
  - content reads are not routed to the owning host (the code takes `hosts[0]`);
  - an empty read at end-of-file is cached, so a growing file never shows new output;
  - each chunk is decoded separately, so a UTF-8 character split across chunks breaks.

#### Transcript and output detail

Finding #3 (transcript and output):
- The gateway's `canonical_content_path` keeps a path only if it resolves inside the
  record's artifact directory.
- I checked a 2026-10-09 athena `done.json`:
  - `response_path` is `"~/.sase/chats/202610/…"`. The `~` is literal, so the path is
    treated as relative and fails.
  - `output_path` is `"/home/bryan/.sase/workflows/…"`, which is outside the artifact
    root.
- Only `commit_diffs/*.diff` survives.

#### Launch source detail

Finding #6 (launch source):
- `FleetLaunchProjectContextWire` carries `revision`, `patch_ref`, and `provider_ref`.
- But the launch handler forwards only prompt, name, model, provider, runtime, and project
  (`fleet_handlers.rs:384-402`).
- Meanwhile the controller demands a clean, pushed checkout and derives `project_id` from
  the TUI's `Path.cwd()` (`launch_preview.py:275-320`).

#### Refresh coupling detail

Finding #8 (refresh coupling):
- Every local roster apply schedules a fleet refresh (`_loading_apply.py`).
- The catalog, followed-batch, and attention calls use `cache_only=False`. Only the
  summary uses `cache_only=True`.
- Each refresh builds a new `FederationFacade` and supervisor.
- Today's `d7c4958551` (sase-1j1.5) added coalescing and stopped respawning on timeout.
  It changed none of the above.
- Why both reports are right: on athena, which has many local agents, the result is about
  one refresh every 7 s. The apollo stampede report confirms athena's TUI was the client
  keeping apollo's gateway melted. On a Mac with no local agents, the same logic falls
  back to the ~300 s sanity pass.

#### Dispatch alias detail

Finding #12 (`%d`):
- `_DIRECTIVE_ALIASES` has no `d`.
- The Rust `metadata.rs` entry for `dispatch` has `alias: None`.
- `scan_dispatch_directive` returns early unless the literal `%dispatch` appears.
- Patch queries already use `%d` for `status:DRAFT` (grk). That is a different widget,
  but it should be documented.

#### Bead status detail

Finding #14 (beads):
- `sase-1j1.6` (gated apollo gateway restart) is IN_PROGRESS.
- `sase-zz`, `-1av`, `-1aw`, `-1b3`, `-1b4`, `-11v`, and `-1ge` are all READY (open).

### Unverified measurements and estimates

I did not re-measure these, and they are not load-bearing for the recommendation:
- cld's sizes: ~336 KB per 100-row host page against the 1 MiB IPC frame cap, and ~30 KB
  of small metadata per agent. I did see 38 files in one of today's artifact
  directories.
- cld's count of ~60 Agents-tab operations, of which about 10 work remotely.

## Critique: is this a good idea?

### What is right

- **The split is right.** Execution belongs where the CPU, RAM, and repos are, and the
  human sits at the laptop. Pull-based federation tolerates a Mac that is often asleep
  with the lid closed. The tailnet note confirms the Mac is offline unless it is powered
  on with the lid open.
- **The hard trust and identity work is done.** That includes enrollment, scoped
  credentials, journaled same-key mutations, version-skew reporting, machine tabs, and
  the attention inbox (see [what already exists](#what-already-exists)).
- **The parity work pays off twice.** athena already views apollo with exactly these
  gaps, and the mobile and Telegram surfaces share the same gateway.
- **Explicit `%dispatch` matches the plan.** The unified-agents plan's "explicit
  consequences" principle calls for it, and auto-placement was deferred for good reason.

### What is wrong or risky

1. **Per-operation parity does not converge** (cld).
   - Each remote operation so far needed a wire field, a route, a bridge operation, a TUI
     branch, fixtures, and a live acceptance pass.
   - List parity alone took an epic plus repeated audits, and hand-built fixtures still
     hid production gaps.
   - The [fork and content bugs](#confirmed-defects-and-gaps) show that the
     half-finished state is *worse* than either extreme: features look supported and
     quietly do the wrong thing.
2. **Literal "every operation" includes things that are local by nature.** Opening tmux in
   the agent's workspace and persistently editing a transcript need a terminal on the
   owner, not an API.
3. **An eager full mirror contradicts the low-resource goal.** What you need is that any
   data is *reachable*, not that all of it is copied.
4. **The native Mac viewer is worth less than it looks** (my addition).
   - athena is both the main owner and the SSH host. So "works when athena is down" only
     buys apollo's agents (apollo is the DigitalOcean rendezvous box) plus cached
     browsing.
   - The real native benefits are:
     - Mac clipboard, images, and notifications;
     - lower keystroke latency;
     - offline browsing;
     - one process seeing every owner without a hub.
   - These are real, but they are quality-of-life wins, not capabilities you lack today.
5. **The Mac's heaviest SASE component is probably the TUI itself, not sync.**
   - It runs constant timers, and file watchers fall back to polling because macOS has no
     inotify.
   - Without `-x` and a disabled scheduler, it starts the service host and its routines.
   - Your shared chezmoi config would also start routines such as telegram on the Mac.
   - None of this has been measured on the Mac (cld; gem's numbers are unsupported).
6. **`%d` does not prevent the expensive mistake.** The mistake is forgetting it, which
   starts a heavy local agent.
7. **A second polling controller before `sase-1j1.6` closes is an outage risk** (grk).
   The Mac's idle cadence is lower than athena's. But `r`, tab switches, and any local
   activity still trigger network catalogs to every host.
8. **"Reliably" depends on bugs that are already filed.** For example, a remote stop
   rejected for a missing capability is journaled as uncertain and never settles
   (`sase-zz`). The attention inventory reads only page 1 (`sase-1av`). A stale snapshot
   reports `ok` after a network failure (`sase-1aw`).

### What I would do differently

- Do not start by "finishing" the native viewer. Drive from the Mac over SSH/tmux today.
- Spend the first native work on **correctness of what already exists**. It benefits
  athena-views-apollo immediately.
- Then build the four generic mechanisms behind a parity ledger, and let the measured Mac
  footprint decide how far to take native (see the [recommended
  solution](#recommended-solution)).

## Requirement adjustments

Each adjustment to your requirements is called out explicitly here.

| # | Your requirement | Adjusted to | Why |
|---|---|---|---|
| 1 | **EVERY** Agents-tab operation works on remote agents | Every Agents-tab action (keymap, leader, copy-mode, palette, Enter) **declares a tested remote disposition**, enforced by a ledger test. The dispositions are: `REMOTE_OP`, `MIRROR_READ`, `VIEWER_LOCAL`, `SSH_HANDOFF`, or `N/A(reason)`. An "open on owner" key is the universal fallback. | Achievable and testable, and stays true as features land. Re-implementing terminal-centric operations natively buys nothing over a handoff. |
| 2 | **ALL** remote data synced and displayed | Everything the local TUI shows is **reachable on demand** through a bounded, evictable cache. A resumable "download everything for this machine" exists for offline use. Missing bytes are shown as missing, never as an empty deck. | Same visible result at a fraction of the disk, network, and owner load. |
| 3 | Sync may be slow or exclusively manual | **Cache-first by default, plus scoped manual sync (`,s`), plus a ≤60 s attention poll on by default.** Strict manual is opt-in and shows "attention discovery is manual". | A missed question or plan gate blocks an agent. Attention data is small. |
| 4 | Type `%dispatch`/`%d` by hand | Keep that, and **add a viewer role with local-launch confirmation**. Retry, fork, and kill-edit inherit the row's owner, as the plan already requires. | The dangerous mistake is the forgotten `%d`. |
| 5 | (implicit) Remote mutations behave like local ones | **The owner applies the mutations; the viewer keeps view state.** Owner-side: dismiss, save-group, rename, tribe, tab, wait/queue, revert. Viewer-side: marks, folds, deck layout, and unread, keyed by installation + logical key + revision. **This reopens** the unified plan's "dismissal remains a viewer operation"; the never-a-stop rule stays. | You will run two TUIs (Mac native and athena over SSH). They must agree on what is dismissed. |
| 6 | (implicit) tmux and workspace operations | **SSH handoff** using the machine `ssh-target`. **This reopens** the plan's "do not promise remote tmux/editor access". | Required by #1. The infrastructure already exists for remote sudo. |
| 7 | (implicit) Approve plans remotely | **The plan body must be readable before approval.** | Today `preview` is always `None`. |
| 8 | (implicit) Launch parity | Lift the 16 KiB body limit for launch and mutations. Image and attachment upload come later. | Long prompts and fork instructions fail today. |
| 9 | (implicit) Launch from the Mac | Viewer launches use **source resolved on the owner**, and the owner honors an explicit `revision`/`patch_ref`. | The current check demands clean, pushed Mac clones, then drops the evidence. |
| 10 | (implicit) `W`, clans, waits | **Same-owner** `%w`/`%q`/`%c` combined with `%d` is in scope. Cross-owner is deferred. | Needed for `W` and clan parity without a cross-host scheduler. |
| 11 | — | **Out of scope:** remote parity for the Patches/Artifacts/Beads/Services tabs, a gateway on the Mac, and auto-placement. | Keeps the effort bounded. Jumps into those tabs get `N/A` or `SSH_HANDOFF`. |
| 12 | — | **Release gate** for "the Mac is the main driver": ledger green, measured Mac footprint acceptable, and `sase-1j1.6` closed. | Prevents adding a second polling controller on an unhealthy owner. |

## Recommended solution

1. **Today:**
   - Drive SASE from the Mac with SSH/mosh + tmux into athena's TUI. You get full
     operation and data parity, near-zero Mac load, and no chance of accidental local
     agents.
   - Finish `sase-1j1.6`.
   - Measure a native `sase tui -x` on the Mac before committing to heavy native work.
2. **Fix what exists first ([P1](#phased-roadmap)).** These bugs make remote support
   look finished while it quietly does the wrong thing:
   - fork launches locally;
   - the content viewer is dead and the owner refuses chat/output;
   - remote dismissal doesn't stick;
   - leader keys bypass gating;
   - refresh is tied to local applies, the worker fsyncs on every read, and the body
     limit is 16 KiB;
   - the open fleet beads.
3. **Make the Mac an explicit viewer ([P2](#phased-roadmap)):**
   - `%d` as an alias of `%dispatch`, implemented in the Rust contract, the Python table,
     and the scan fast path;
   - a viewer role with scheduler off and local launches requiring confirmation;
   - source resolved on the owner;
   - cache-first sync policies with the attention poll kept on;
   - `,s` to sync the selected machine, `,S` to download everything for it, and `r` that
     is scoped to the machine on remote rows.
4. **Build native parity from four generic mechanisms, not per operation:**
   - an owner manifest plus a bounded, evictable **mirror**, so existing readers work on
     remote rows;
   - one allow-listed **`/operation` route** that forwards the TUI's existing durable
     operations;
   - **SSH handoff** plus "open on owner" for terminal work, shipped early as the
     universal fallback;
   - a CI-enforced **parity ledger** behind a single availability gate.
5. **Switch your daily driver from SSH to the native Mac TUI only when:**
   - the ledger is green;
   - the Mac's measured footprint is acceptable;
   - owner gateways stay healthy with the Mac polling.

This keeps the Mac light and makes every byte of remote data reachable when you look at
it. It turns "every operation" from an aspiration into a tested invariant, and every phase
also improves athena's view of apollo.

### Design principle

**Principle: the owner executes, the viewer mirrors, the terminal hands off.**
- The Mac never re-implements owner behavior.
- It caches owner data for reading and forwards the *existing* durable operations for
  writing.
- It opens a terminal on the owner for anything interactive.
- One ledger keeps "every operation" true.

```text
Mac (viewer role)                                          Owner (athena / apollo)
─────────────────                                          ───────────────────────
Textual TUI ── availability gate + disposition ledger
   │
   ├─ reads ──► FleetMirror (namespaced, evictable)   ◄─── /artifacts/manifest + /content (ranged, sha256)
   │                ▲                                       (artifact dir + allow-listed chat/output roots)
   │                └── federation worker (one supervisor, scoped per-host reads, debounced cache)
   │
   ├─ writes ─► `sase machine op <alias> <kind>` (journaled durable proc, same-key recovery)
   │                └──► POST /operation {kind ∈ closed enum} ──► owner runs the SAME durable op
   │                                                             (persist-cleanup, persist-directive,
   │                                                              revert preview/execute, notify.*, …)
   └─ terminal ► ssh -t <ssh-target> -- tmux … / sase tui --select <agent>
```

### Reads through a manifest and on-demand mirror

Read side: manifest plus on-demand mirror.

**sase-core (fleet contract v8):**
- Add a manifest route keyed by logical key and row revision. It lists every resource
  with:
  - a stable identity and a virtual path;
  - kind and MIME type;
  - byte length and sha256;
  - a growth flag and an access state.
- The manifest covers the artifact directory **plus allow-listed external roots**:
  - `chat/` for the transcript, expanding the literal `~`;
  - `output/` for the workflow log;
  - plan files.
- Do **not** weaken the artifact-root check to allow arbitrary paths.
- Emit the already-declared `Artifact` content kind.
- Fill the attention `preview` for plan gates.
- Serve History-scope rows without rebuilding History on every request.

**Python viewer:**
- **Mirror location:** `~/.sase/fleet/mirror/<installation>/<project>/<logical-key>/…`.
  - This is outside `~/.sase/projects`, so the local artifact index never sees it.
  - Files are 0600 and written atomically.
  - A per-agent `manifest.json` makes re-sync incremental.
  - A byte cap applies (e.g. 512 MB) with LRU eviction.
  - A purge command clears it.
- **Row builder:** point a remote row's artifact directory at its mirror. Route owner
  paths (`response_path`, `output_path`, `diff_path`, plan paths) through one
  `resolve_agent_path` mapper. Existing readers then work unchanged: decks, `V`, `D`,
  `e` (read-only), `a`, images, and the copy keys.
- **Fetch tiers:**
  - **Tier A** — small metadata, roughly 30 KB per agent: fetched with a debounce when a
    remote row is selected.
  - **Tier B** — transcript, tool calls, diffs, output, images: fetched when the deck
    that needs them opens. Live files are tailed only while visible.
  - **Tier C** — `,S`: a resumable proc that downloads everything retained for a
    machine, including History pages.
- **Content correctness (from cdx):**
  - Route each read to its owner, never to `hosts[0]`.
  - Never cache an empty read at end-of-file as a permanent chunk.
  - Decode UTF-8 incrementally across chunks.
  - Validate digest, owner, and offset on every chunk.
  - Show each pane's state: partial, cached, stale, or missing.
- **Write a decision record:** "Remote artifacts are a viewer cache, never local state."
  - This deliberately meets the reopen clause of `decisions:agents-sync-publish-only`
    ("sync agent state *into* local disk … a new design exercise").
  - Rules: no registry rows, no index entries, no import journals; evictable at any time;
    keyed by owner identity.

**Rejected alternatives:**
- rsync, SSHFS, or mounting `~/.sase` (cdx, cld, gem, grk). These bypass fleet
  credentials and audit, put network I/O on the TUI event loop, and blur which machine
  owns a process.
- Reviving the old agents-sync import leg. It was explicitly deleted.

### Writes forwarded through the existing durable operations

Write side: forward the durable operations the TUI already has.

**The seam already exists.** The TUI funnels agent mutations through
`_submit_durable_proc`, with producer sites registered in
`_proc_producer_sites_actions.py`. I confirmed these sites:
- `agent.cleanup`, `agent.directive`;
- `agent.revert.preview`, `agent.revert.execute`, `agent.revert.bulk_preview`;
- `notify.state`, `notify.gate`, `notify.plan_gate`, `notify.question`;
- `monitor.stop`, `proc.kill`, `tool.stop`.

**sase-core:**
- Add `POST /api/fleet/v1/operation` under a new `fleet.operation` scope.
- `kind` is a **closed** enum: cleanup/dismiss/save, directive (wait/queue/tribe/tab),
  rename, revert preview/execute, notify state, monitor stop, proc kill, tool stop.
- Each kind has its own payload schema and requires a per-row capability. The owner
  computes capabilities from its own state, for example dismissible only when terminal.
- The owner:
  - journals the operation with same-key recovery, like `/mutate`;
  - resolves the logical key to its local records;
  - runs the same CLI through a bridge inside `spawn_blocking`, so it does not repeat
    `sase-11v`.
- **Never** forward generic `sase …` command lines.

**Rigor requirements (cdx):**
- Revert uses an owner-generated preview token that is re-validated at execute time.
  Report results per repository; there is no promise of atomic rollback.
- Session/clan expansion is snapshotted, so new members cannot silently join a
  destructive cleanup.
- Mixed local/remote bulk actions are split per owner, with per-target receipts. A
  partial success stays visible. A retry targets only the unresolved original keys.

**Python:**
- One dispatcher in the durable adapter. Remote targets submit
  `sase machine op <alias> <kind>` as a journaled durable proc, mirroring
  `sase machine agent`.
- The kind registry, wire format, and capability rules live in Rust, per
  `rust-core-required`. Bump `sase-core-revision.txt` for any new binding.

**Composite operations become compositions:**
- Fix fork with an explicit launch-context flag instead of a display-name prefix.
- `R` gets the same edit-before-relaunch bar as local, pre-filled from the mirrored raw
  prompt. cdx notes local `R` is an edit workflow; remote `R` submits immediately.
- `,x` (kill and edit) = remote stop, then a prompt bar pre-filled from the mirror with
  `%d:<alias>`. The new launch is held until the stop settles.
- `W` → `%d:<alias> %w:<name>`.
- `,<space>` → `%d:<alias> +<project>`.
- `,X` ("kill and edit the last local launch") is `N/A` by definition.

### Terminal work through SSH handoff and open on owner

Terminal side: SSH handoff and "open on owner".

- **`t` / `T` on a remote row:** the owner resolves the exact workspace through a typed
  resolver. The Mac then opens `ssh -t <ssh-target> -- tmux new-session -A …` with safe
  argv handling. Never rebuild the path from `workspace_num` on the Mac.
- **"Open on owner":** runs `ssh -t <target> -- sase tui -t agents --select <agent>`.
  - It needs a small new `--select` deep-link flag; today `sase tui` has only
    `-t/--tab`.
  - From the day it ships, **every** operation is reachable on every remote row, before
    its native disposition lands.
- **Interactive sudo:** reuse the existing remote sudo flow for privileged gates.
- **Persistent edits:** editing an owner file such as a transcript is an SSH-editor
  operation. Opening the mirrored copy in `$EDITOR` is read-only viewing.

### Dispatch shorthand and the Mac viewer role

**`%d`:** change all of these together.
- The Rust directive metadata (alias `d`), its editor/LSP examples, and the matrix test.
- The Python alias table.
- The `scan_dispatch_directive` fast path and stripping.
- `set_dispatch_directive`.
- `docs/macros.md` and `docs/remote_dispatch.md`.
- The `dispatch.md` / `macros.md` memory notes, via `/sase_memory_write`.
- The sase-nvim syntax, if it lists aliases.

The picker and stored prompts keep emitting the canonical `%dispatch:<alias>`.

Required tests:
- `%d:` and `%d(…)` both work, and bare `%d` errors.
- Fenced and disabled regions are respected.
- `%d:local` stays reserved.
- Duplicate short and full forms are rejected.
- The combination bans still fire.
- **`%d:athena` can never launch locally.** An alias-table-only change would make exactly
  that mistake.

**Viewer role** (`machine.role: viewer` in the Mac's `sase_<machine>.yml` overlay):
- The scheduler service proc is disabled.
- TUI auto-start of the service host is skipped (today's `-x`).
- `dispatch.local_launch: allow | confirm | deny`, defaulting to `confirm`.
- An optional, visible `dispatch.default_target`, off by default.
- Owner-resolved launch source.

### Sync policies and keys

**Fleet refresh policies** (`dispatch.fleet.sync_policy`). Every call site must honor the
policy: startup, tab switch, apply, notification poll, and post-action refresh. A timer
setting alone is not enough.

| Policy | Startup / tab switch / local apply | Selected owner | Attention | Content |
|---|---|---|---|---|
| `strict_manual` | cache only | `,s` only | manual; banner says so | on open |
| `lightweight` (**viewer default**) | cache only | summary-first conditional fetch every 60–120 s while Agents is visible; skip the catalog if `catalog_snapshot_id` / `count_revision` are unchanged | network ≤60 s, follows `next_cursor` (`sase-1av`) | Tier A on select, Tier B on open |
| `live` | as `lightweight` | faster refresh for the watched owner only | ≤60 s | tail the visible deck |

**Keys** (update `default_config.yml`, the keymap registry, palette applicability, the
help modal, and the footer together):
- `,s` — **sync selected machine.**
  - Target: the selected remote row's owner, else the active machine tab, else a picker.
  - Never infer the target from a named tab that spans owners.
  - Pin the installation ID at submit time.
  - Runs a scoped `catalog_hosts`, followed rows, attention, and Tier A for visible rows,
    for that host only.
  - Leaves other hosts' caches untouched.
  - Reports what was refreshed and what is still lazy.
- `,S` — **download everything for the machine** (Tier C, resumable, with progress).
- `r` — on a remote row, the same as `,s`; otherwise a local refresh plus a fleet cache
  apply.
- A palette-only "Sync all machines" command, with a confirmation.
- Machines admin `S` — the same as `,s` for the highlighted machine.
- Show `cached Ns ago` on the machine chip and header.

**Worker and gateway hygiene:**
- Keep one long-lived federation supervisor.
- Debounce cache persistence to at most one fsync per 30 s, or use per-entry files.
- Don't cache pages with unique continuation cursors.
- Send per-host catalog frames to stay under the 1 MiB IPC cap.
- After a mutation, refresh only the affected host.
- When a refresh is dropped because the selection moved, schedule a rerun.
- Later: owners publish `/events` invalidations for every agent state change, the worker
  subscribes, and polling becomes the fallback.

### Parity ledger and tests

- **One availability gate** for every entry point: keymaps, leader keys, copy-mode keys,
  the palette, and Enter. This closes the leader/copy bypass.
- **A `REMOTE_DISPOSITIONS` table** covering every Agents-tab action, plus a test that
  **fails when an action has no disposition.** New features then cannot silently fall
  through to local logic.
- **Use a realistic owner fixture, never hand-built handles or capabilities.** The fork
  and content bugs both hid behind hand-built ones.
  - Capture a representative dataset: active, waiting, failed, completed, and dismissed
    agents; a multi-turn session; a monitor; a gate; a named proc; workflow steps; LLM
    calls; ToolRuns; finalizers; a plan; files and commits.
  - Run every test through the **real submit path**.
- **High-value scenarios** (cdx):
  - Two owners with identical agent names and workspace numbers; nothing may route to the
    wrong owner.
  - An agent replaced between selection and stop must not have its successor stopped.
  - Effect executed but response dropped: a same-key retry produces exactly one effect.
  - EOF poll, then append; a UTF-8 character split across chunks; truncation; resume.
  - `,s` on athena while apollo is offline must make no request to apollo and keep its
    cached rows.
  - History beyond 7 days / 200 rows.
  - Mixed bulk cleanup with one owner failing.
- **Resource tests:**
  - Strict-manual idle makes **zero** automatic fleet network calls, verified from the
    worker operation log.
  - Lightweight idle makes at most one summary call per interval per owner, plus the
    attention poll.
- **Live acceptance from the Mac:** extend the `sase-133` rendered-row oracle to the decks,
  so a remote row and the owner's own row render the same after a Tier A/B sync.

### Phased roadmap

| Phase | Content | Size | Notes |
|---|---|---|---|
| **P0 — now, no code** | SSH or mosh + tmux into athena's `sase tui`. Finish `sase-1j1.6`. Enroll athena (and apollo) on the Mac with the SSH target set. **Measure `sase tui -x` on the Mac** with only remote rows: CPU, RSS, idle wakeups, j/k latency. | — | Full parity today. The measurement decides how lean the native viewer must be, or whether to stop at SSH. |
| **P1 — make existing features correct** | Fork intercept. Content: detail hydration, owner routing, EOF caching, UTF-8 decoding, every handle. Sticky dismissal. Enter on a gate row. Leader/copy gating. Optimistic-status override bugs. 16 KiB limit. Worker hygiene. Decouple refresh from local apply. Close `sase-zz`, `-1av`, `-1aw`, `-1b3`, `-1b4`, `-11v`. | M | Pure reliability. Benefits athena viewing apollo immediately. |
| **P2 — Mac ergonomics and pacing** | `%d`. Viewer role and local-launch guard. Owner-resolved source; the owner honors `revision`. Sync policies. `,s` / `,S` / `r` / Machines `S`. Freshness age display. | S–M | Makes the Mac a viable place to launch from. |
| **P3 — read mirror** | v8 manifest, external roots, the `Artifact` kind, plan preview, History paging. Python mirror, path mapper, tiers, LRU, purge. | L | Unlocks every read-side action and blind-free plan approval. Needed before edit-bar retry and kill-and-edit. |
| **P4 — write forwarding** | `/operation` route and its kinds. Owner bridge. Python dispatcher. Move dismiss, save, wait, tribe, tab, rename, revert, monitor/proc/tool stops onto it. Compose `R`-edit, `,x`, `W`, `,<space>`. Same-owner `%w`/`%q`/`%c`. | L | The bulk of write parity, with no new route per operation. |
| **P5 — terminal handoff** | `t`/`T` over SSH; "open on owner" plus `sase tui --select`. | S–M | **Can ship right after P1.** It is the universal fallback, so pull it forward. |
| **P6 — ledger and acceptance** | Disposition table and test; single availability gate; realistic fixtures; live Mac acceptance. | S–M | **Start alongside P1**, so each later phase turns ledger rows green. |
| **Later** | Push invalidations through `/events`; owner-side ToolRun datasets; attachment and image upload for `%d`; cross-owner waits. | M | Push gives freshness at near-zero idle cost. |

**Decision records to write** (with `/sase_memory_write`, when the epic is planned):
1. Remote artifacts are a viewer cache, never local state.
2. Remote mutations forward the TUI's durable operation kinds through one allow-listed
   fleet route. No new route per operation and no generic remote shell.
3. Every Agents-tab action declares a remote disposition, enforced in CI.
4. Viewer machines resolve launch source on the owner, and the owner honors explicit
   revisions.
5. A superseding note for two unified-plan items:
   - owner-side dismissal of terminal rows (the never-a-stop rule is unchanged);
   - SSH handoff for tmux and editor.

### Definition of done

Definition of done for "the Mac is my main driver":
- Every Agents-tab action has a non-TODO disposition with a green test, through the real
  submit path.
- After a Tier A/B sync, a remote row and the owner's own row render the same.
- Every `REMOTE_OP` settles with a receipt and is visible in the owner's TUI.
- `%d:<alias>` never launches locally. Unconfirmed local launches are blocked on the
  viewer.
- An idle Mac viewer makes no more fleet calls than its policy allows, and the worker
  writes at most one fsync per 30 s.
- Owner gateways stay in the `sase-1j1.6` healthy band with the Mac as an active client.

## Risks and open questions

- **Owner load from mirrors.** Range reads must share the gateway's bounded semaphore and
  never trigger snapshot rebuilds. History-only rows need a path that does not rebuild
  History per request.
- **Contract skew across three machines.** v8 must be read-compatible in both directions.
  Upgrade controllers first, or the whole fleet in lockstep. After upgrading `sase` on an
  owner, restart its gateway, or status will be wrong (mus).
- **Privacy.** Transcripts and prompts land on a laptop. Use 0600 files, an optional
  `max_age`, and a purge command.
- **Stale authority.** Cached `RUNNING` does not prove the process is live.
  - Every mutation is re-validated on the owner, using the exact instance and revision.
  - A precondition failure triggers a one-host refresh and a retry with the **same**
    operation key.
  - There is no offline action queue that executes later without fresh intent; the plan
    already forbids it.
- **Multi-controller drift.** View state (marks, folds, unread) is per viewer. Document
  the rule: owner state is truth, controller state is view.
- **Hostname caveat** (cld). Under zsh `$HOSTNAME` is unset, so the federation socket path
  falls back to `sase-host`. That is harmless unless some process exports `HOSTNAME`.
- **Stop-at-SSH is a legitimate outcome.** If [P0](#phased-roadmap) shows a heavy Mac
  TUI, and you find you don't miss Mac clipboard, images, or offline browsing, do P1 for
  athena's benefit and stop there.

## How the reports were reconciled

### Where the reports disagreed and how I resolved it

| Question | Positions | Resolution |
|---|---|---|
| **Role of SSH/tmux into the owner's TUI** | cdx: bridge and parity reference. cld: daily driver now. gem: best choice for one machine. grk: break-glass only. mus: rejected. | **Adopt it now as the daily driver and keep it as the permanent fallback.** It also makes `%d` unnecessary for athena-local work, because nothing runs on the Mac. Build the native viewer in stages, after measuring the Mac footprint. |
| **Read side** | cld: mirror the artifact files. cdx: owner manifest plus a byte cache. grk, gem, mus: wire each handle into its deck. | **Combine cdx and cld.** The owner generates a manifest. The viewer materializes it into a namespaced, evictable mirror, so existing file-based readers work unchanged. Per-handle deck wiring (grk/gem) is just per-operation parity again. |
| **Write side** | cld: one allow-listed route over the existing durable operations. cdx: shared Rust action contract. grk: new typed mutations only if missed. mus: keep V1 exclusions. | **cld's seam with cdx's rigor.** Use a closed Rust enum, a per-kind payload schema, owner-computed capabilities, preview tokens, and per-owner receipts. See [the write side](#writes-forwarded-through-the-existing-durable-operations). |
| **Dismissal** | grk: viewer-only. cld: owner operation. cdx: owner archive plus optional viewer hide. | **Owner-side dismissal of terminal rows**, because you will also use athena's TUI over SSH and the two views must agree. Keep a sticky viewer-only "hide" for when the owner is offline. Dismissal must never become a stop. |
| **tmux / editor** | grk: keep disabled. cdx, cld, gem, mus: SSH handoff. | **SSH handoff** using the existing machine `ssh-target`. This reopens the unified-plan deferral explicitly. |
| **Default sync behavior** | gem: `sync_mode: manual` that skips non-forced refreshes. Others: cache-first plus scoped manual sync plus attention poll. | **Cache-first, with three named policies** ([sync policies](#sync-policies-and-keys)). The attention poll stays on by default. |
| **Sync key** | `,s` (cdx), `,Y` (cld), `gs` (grk, gem), `S` (mus) | **`,s`** for "sync selected machine" and **`,S`** for "download everything for this machine". Both are free in the default leader map. `gD` is a prompt-bar key, so `gs` would add a new `g` prefix to the Agents list. Check user overrides before shipping. |
| **What `r` does** | grk: cache-only fleet. cld: forced network. | **On a remote row, `r` syncs that row's machine (same as `,s`).** Otherwise `r` refreshes local agents and applies the fleet cache. A network sync of *all* hosts is palette-only, behind a confirmation. |
| **Default launch target** | gem: default target. cld: viewer role with confirmation and an optional default. Plan: new prompts default to local. | **Viewer role with `local_launch: confirm`; no default target out of the box.** An optional `default_target` must always be visible in the prompt bar. |
| **Source preflight** | cld: drop it. mus: keep it but surface it. grk, gem: silent. | The owner ignores the evidence ([#6](#launch-source-detail)), so the check gives **false assurance plus real friction**. Fix the contract: the owner honors `revision`/`patch_ref`, and viewer-role launches default to source resolved on the owner. Stop deriving the project from the TUI's cwd. |
| **`%wait` / `%queue` / `%clan` with `%dispatch`** | grk, mus: keep the bans. cdx: allow same-owner later. | **Allow same-owner combinations in a later phase.** `W` ("new prompt waiting on this agent") and clan parity need them. Cross-owner combinations stay deferred. |

### Errors in individual reports

- **grk, mus, gem:** say remote fork works. It does not ([#1](#fork-detail)).
- **gem:**
  - "Remote revive rewinds the workspace" is wrong. `agents_revive` is an
    **Artifacts-tab** action that revives dismissed agents, not an Agents-tab rewind.
  - The resource figures (~20 MB / ~200 MB RAM) and the "1–2 developer weeks" estimate
    have no evidence behind them. The verified gap inventory makes the estimate
    implausible.
  - "If nothing is selected, sync all machines" reintroduces the all-host fan-out.
- **mus:**
  - The four `unbound` remote action IDs are compatibility aliases. The shared keys
    `x`/`R`/`F`/`e`/`A` already reroute on remote rows, as the `default_config.yml`
    comment says. So "the remote verbs have no keys" is overstated.
  - mus rejected SSH/tmux because it "sacrifices the unified multi-host list" and "dies
    with the connection". Both reasons are wrong: athena's TUI already shows apollo's
    rows, and tmux survives disconnects.
- **grk:** treats the unified-agents plan as having ruled out owner-side dismissal and
  remote tmux. It didn't, quite:
  - The plan's actual hard rule on dismissal is that it can "never become a remote
    **stop**". Its sentence "remains a viewer operation" describes the V1 scope.
  - "Do not promise remote tmux/editor access" was a V1 deferral, not a permanent
    decision. Your new requirement is exactly the input that should reopen both.
    [Requirement adjustments](#requirement-adjustments) calls this out.

## Inputs and scope

_Lead-researcher consolidation · 2026-10-09_

**Inputs:**
- Five independent reports: `__cdx`, `__cld`, `__grk`, `__mus`, `__gem`.
- My own verification against:
  - `sase` at `9fd8a081f4` and `sase-core` at `6df3bed3`;
  - live athena state;
  - current bead status;
  - the bound plan `plan:202609/unified_agents_across_machines.md`.

**Scope:** every load-bearing claim in this report was re-checked in code. Where a
finding rests only on one report, that report is named.

## Sources

**Reports** (all in this directory):
- `__cdx`: architecture, action contract, content-cache correctness, and the test matrix.
- `__cld`: verified defects, the durable-operation seam, mirror design, and the Mac host
  footprint.
- `__grk`: the stampede risk, the binding plan constraints, and the attention/history
  pagination issues.
- `__mus`: the parity matrix, source-preflight UX, and outcome-unknown launches.
- `__gem`: the SSH-first framing and deck gating. Its numbers are unsupported, and its
  revive claim is incorrect.

**Code verified (`sase`):**
- Agents actions and launch flow:
  - `src/sase/ace/tui/actions/agents/_fork_actions.py`
  - `src/sase/ace/tui/actions/agent_workflow/_launch_procs.py`
  - `src/sase/ace/tui/actions/agent_workflow/_launch_submission.py`
  - `src/sase/ace/tui/actions/agents/_remote_content.py`
  - `src/sase/ace/tui/actions/agents/_fleet_refresh.py`
  - `src/sase/ace/tui/actions/agents/_loading_apply.py`
  - `src/sase/ace/tui/actions/agents/_fleet_projection.py`
  - `src/sase/ace/tui/actions/agent_workflow/_leader_mode.py`
  - `src/sase/ace/tui/_app_action_availability_agents.py`
  - `src/sase/ace/tui/_proc_producer_sites_actions.py`
  - `src/sase/ace/tui/widgets/decks/availability.py`
- Directives and dispatch:
  - `src/sase/macro/_directive_types.py`
  - `src/sase/macro/_directive_scan.py`
  - `src/sase/dispatch/launch_preview.py`
  - `src/sase/dispatch/ssh_target.py`
  - `src/sase/dispatch/federation/_facade.py`
- Config: `src/sase/config/_settings_runner.py`, `src/sase/default_config.yml`
- Tests and docs: `tests/ace/tui/test_remote_lifecycle_actions.py`,
  `docs/query_language.md`
- Recent commit: `d7c4958551`

**Code verified (`sase-core`):**
- `crates/sase_gateway/src/fleet_reads/content.rs`
- `crates/sase_gateway/src/routes/fleet_handlers.rs`
- `crates/sase_gateway/src/routes/state.rs`
- `crates/sase_gateway/src/federation_worker/imp/remote_hosts.rs`
- `crates/sase_gateway/src/federation_worker/imp/cache.rs`
- `crates/sase_core/src/fleet_contract/content.rs`
- `crates/sase_core/src/fleet_contract/launch.rs`
- `crates/sase_core/src/fleet_contract/error.rs`
- `crates/sase_core/src/fleet_attention.rs`
- `crates/sase_core/src/editor/directive/metadata.rs`

**Live state:**
- A 2026-10-09 athena `done.json` and its artifact directory.
- `sase machine list` (apollo, `ssh=apollo`).
- `tailscale serve status` (athena's gateway, tailnet only).

**Beads:** `sase-1j1.6` (IN_PROGRESS); `sase-zz`, `sase-1av`, `sase-1aw`, `sase-1b3`,
`sase-1b4`, `sase-11v`, `sase-1ge` (READY); `sase-133` and `sase-xe` (CLOSED).

**Plans, research, and memory:**
- `plan:202609/unified_agents_across_machines.md` (unified-actions section and deferrals)
- `research:202610/apollo_high_cpu_gateway_snapshot_stampede.md`
- Memory: `dispatch.md`, `tailnet.md`, `decisions:agents-sync-publish-only`
