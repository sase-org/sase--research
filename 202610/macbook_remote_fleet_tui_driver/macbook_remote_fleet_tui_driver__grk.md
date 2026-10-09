# MacBook as SASE TUI driver: finishing remote-machine support

**Researcher:** grk (independent swarm report)
**Date:** 2026-10-09
**Question:** How should a low-resource MacBook become the main driver of sase's TUI for agents that actually run on remote machines (Apollo and similar), given explicit `%dispatch`, full Agents-tab operations, and a willingness to accept slow or manual data sync?

## Verdict

The product idea is sound: keep the Mac as a thin control plane (viewer + launcher + attention answering) and keep heavy agent work on owner machines. The implementation framing is not. "Finish remote support so every local Agents-tab operation and all remote agent data work on the Mac" is a new fleet-contract plus TUI epic, not remaining glue on V1.

V1 already lists remote rows, groups them, launches with `%dispatch:<alias>` plus a Launch Target picker, and journals owner-side stop / retry / fork plus bounded content and remote attention. What is missing is (1) a Mac-safe pull model so the TUI stops network-stamping every enrolled host on tab switch, apply, and `r`, and (2) a capability-gated expansion of owner-side verbs and on-demand content into the same decks local rows already use.

Do this as a pull-based viewer, not a replica. Add `%d` as a launch-prompt alias of `%dispatch`. Add a per-selected-machine network-sync keymap. Treat "all data displayed" as on-demand fetch of every advertised content handle, with History pagination for older catalog rows. Reject literal local-op mirroring, remote tmux/editor, workflow-step catalog rows, and always-on cross-host polling.

**Do not put the Mac on the current Agents fleet-refresh path until `sase-1j1.6` (gated Apollo gateway restart and measured verification) is closed.** Athena's TUI polling is the client that melted Apollo's gateway on 2026-10-09 (`research:202610/apollo_high_cpu_gateway_snapshot_stampede.md`). A MacBook sitting on Agents with the same `cache_only=False` catalog fan-out would recreate that stampede on owner gateways and would also spend the Mac's CPU, RSS, and tailnet budget doing it.

## What already exists

Fleet contract schema **v7**, protocol **v3**. Mutations are a closed set: `lifecycle.stop`, `lifecycle.retry`, `lifecycle.fork` (`crates/sase_core/src/fleet_mutation.rs`). Content kinds: Transcript, Output, Diff, Log, Artifact, Question (`crates/sase_core/src/fleet_contract/content.rs`). Default content window 64 KiB, hard cap 256 KiB (`FLEET_READ_DEFAULT_CONTENT_BYTES` / `FLEET_READ_MAX_CONTENT_BYTES`). Federation worker on-disk cache: 256 entries / 4 MiB, with per-host in-flight caps and `HOST_READ_BACKOFF` 5s–120s already landed in `sase-1j1.3` (`crates/sase_gateway/src/federation_worker/mod.rs`).

Controller launch is explicit:

- `%dispatch:<alias>` or `%dispatch(alias)` in a normal prompt (`docs/remote_dispatch.md`, `sase/memory/dispatch.md`).
- `%dispatch:local` is reserved; omit the directive for a local launch.
- TUI Launch Target picker: `gD` (NORMAL) / `Ctrl+G D` (INSERT) (`docs/ace.md`).
- V1 refuses combining `%dispatch` with `%wait`, `%queue`, `%clan`, or `%hold` (`src/sase/macro/_directive_scan.py`).
- Source preflight requires published HEAD unless the payload carries a Patch/revision.
- There is **no `%d` alias** in `_DIRECTIVE_ALIASES` today (`src/sase/macro/_directive_types.py`). `scan_dispatch_directive` also early-outs when the prompt does not contain the literal substring `%dispatch`, so a naive alias table edit would still miss `%d:apollo`.

Agents-tab V1 surface (`docs/ace.md` §Machines, `docs/remote_dispatch.md`):

- One Agents list; remote rows carry a host-alias chip and `fleet_origin_alias`.
- Machine tabs `⌂ <local>` / `⌨ <alias>` when `ace.agent_tabs.machine_tabs` is `auto` (default) or `on`.
- Group-by-machine, `machine:<alias>` query, Machines admin (`#` then `3`).
- Remote `x` / `R` / `F` remap to owner-side stop / retry / fork when the row advertises the capability.
- Bounded content opens a **modal** from the first advertised handle (`src/sase/ace/tui/actions/agents/_remote_content.py`).
- Pending questions/gates go through the durable notification inbox (`sase machine attention`).
- Catalog window matches the local recent-completion policy: seven days, at most 200 completed rows. Workflow step rows are not served, so a remote session's `×N` can be lower than the owner's.
- Remote load is excluded from the controller `load:` gauge.

Closed work that is easy to over-read:

- `sase-133` / `sase-133.5` closed **list/render/screenshot** parity from real owner state, not operation parity.
- `sase-xe.16.11.7` closed the unified Agents experience (one list, attention, launch picker, Machines pane). Follow-up still open: attention inventory first page only (`limit=100`, never follows `next_cursor`).
- Unified-agents plan (`plan:202609/unified_agents_across_machines.md`) already bound: one list; attention independent of filters; explicit target machine; terminal dismissal is viewer-only; `%dispatch:<alias>` portable spelling; defer Watch, `%dispatch:auto`, cross-machine queue, auto placement, always-on delivery while ACE is closed. "Do not promise remote tmux/editor access or cross-host continuation." Mac live-acceptance is best-effort and does not block.

## Operation gap matrix

Local Agents-tab verbs today, versus a remote row (`fleet_origin_alias` set). Source of truth: `_LOCAL_AGENT_ROW_ACTIONS` and remaps in `src/sase/ace/tui/_app_action_availability_agents.py`, `_REMOTE_AGENT_LOCAL_COMMANDS` in `src/sase/ace/tui/commands/_availability_agents.py`, footer bindings in `src/sase/ace/tui/widgets/_keybinding_bindings_agents.py`.

| Local verb | Remote today | Honest next step |
| --- | --- | --- |
| Launch (`gD` + prompt) | Works with explicit `%dispatch` | Add `%d` alias; keep picker |
| Stop `x` | Owner-side `lifecycle.stop` when advertised | Keep; never map local dismiss onto this |
| Retry `R` | Owner-side `lifecycle.retry` | Keep |
| Fork `F` | Owner-side `lifecycle.fork` with prompt bar | Keep |
| Answer question / approve gate `Enter` | Inbox + `sase machine attention` | Keep; fix attention pagination (`next_cursor`) |
| Open content | Modal, **first handle only** | Deck-native open of **every** handle, ranged |
| Check launch outcome | Palette-only, unbound | Bind or keep in palette |
| Connect / hello selected machine | Palette + Machines `s` | Keep bounded |
| Rename | Disabled | New fleet op `identity.rename` if/when needed |
| Tribe `N` | Disabled | New fleet op; tribe is owner presentation |
| `%tab` move | `%tab` travels on launch; later moves skipped for remotes | New fleet op or relaunch-with-tab |
| Unread toggle | Disabled | Local viewer annotation is enough |
| Attempt history | Disabled | Needs owner attempt records in catalog/detail |
| Jump to Patch | Disabled | Needs portable Patch ref on the row |
| Agent metadata / prompts | Disabled | New content kinds or detail fields |
| Open artifact files | Disabled | On-demand Artifact handle, not a tree replica |
| tmux attach / tmux mode | Disabled **and should stay disabled** | SSH to the owner if needed |
| Tool Runs deck | Remote rows have no Runs | New fleet content/summary; SQLite stays on owner |
| Wait / queue / clan / hold on launch | Parser rejects with `%dispatch` | Leave V1 ban; later epic |
| Dismiss / cleanup panel | Local only; remote stop does not dismiss | Keep viewer-only dismissal |
| Workflow step children | Not in catalog | Leave out of V1 catalog; History later if needed |
| Copy chat / file path / tool-run id | Disabled | Copy from fetched content, not local paths |

The TUI already encodes the right split: remote rows are **viewer-only**. Mutations go to the owning host with a scoped operation key and an acceptance window (≥30s). A lost response is recovered with the **same** key. Terminal dismissal on the viewer must never become a remote stop (`docs/remote_dispatch.md`, unified-agents plan).

Literal "every local operation" therefore includes tmux attach, local artifact-directory browse, local ToolRun SQLite, local unread files, and local dismiss. Those are host-local by construction. Mirroring them would either ship owner filesystem/process handles over the fleet API (the contract explicitly forbids paths, PIDs, and secrets on content handles) or replicate owner state onto the Mac (the resource budget the user is trying to protect).

## Sync and resource model

### What the TUI does today

`_run_agents_fleet_refresh` (`src/sase/ace/tui/actions/agents/_fleet_refresh.py`):

- `summary` is `cache_only=True`.
- `followed_batch` and `attention` are `cache_only=False` whenever there are followed keys.
- `catalog` / `catalog_hosts` are **always** `cache_only=False`, page size 100, up to 16 pages (`_FLEET_CATALOG_PAGE_LIMIT` / `_FLEET_CATALOG_MAX_PAGES`).

That refresh is scheduled from:

- Agents tab switch (`src/sase/ace/tui/_app_watchers.py`)
- roster apply (`_loading_apply.py`)
- manual `r` (`refresh_panel.py` uses `force=True`)
- remote mutation / attention settlement (`force=True`)

`force` only cancels in-flight TUI tasks and starts another full network catalog. It does not mean "this host only" and it does not stay on the federation cache.

Default auto-refresh interval is 10s (`docs/ace.md`). Idle ticks already prefer cache for the **attention inventory** path (`_auto_refresh_surfaces.py`); the Agents catalog path does not.

### Why this is the wrong default for a MacBook controller

Measured on 2026-10-09 (`research:202610/apollo_high_cpu_gateway_snapshot_stampede.md`): Athena's TUI plus `sase_federation_worker` hit Apollo through Tailscale Serve on every Agents refresh, about every 7s, up to ~18 calls per refresh (summary, optional followed_batch/attention, catalog, up to 15 extra catalog pages), each preceded by worker `health` + `replace_config`. Combined with a 4s uncancellable gateway snapshot timeout, that produced:

- 6–11 of 16 cores in `sase_gateway` alone
- ~500 threads, ~1000 SQLite fds, 8–12 GB RSS
- two `sase.service` OOM kills
- load average peaking ~563

`sase-1j1` phases 1–5 closed the gateway single-flight, WAL bounds, worker host-state + backoff, telemetry, and client stop-amplify. **Phase `.6` (gated Apollo restart and measured verification) is still in progress**, created the same day as this report. Client hardening is real (`HOST_READ_BACKOFF_BASE` 5s, max 120s, per-host in-flight 4). It is not a license to add a second controller that network-catalogs every host on every `r` and tab switch.

A low-resource Mac as the *main* TUI makes this worse in two directions at once:

1. **Owner gateways** see another polling client. The stampede was bistable: one slow build plus constant polling never recovered, including after reboot with a clean WAL.
2. **The Mac** pays federation-worker CPU, JSON parse, catalog merge, and TUI rebuild on a machine the user already does not want running many agents. Historical ACE idle RSS of 2.3–2.5 GB (`sase-v3`, closed/canceled but still the right order of magnitude) leaves little headroom for a 4 MiB federation cache plus materialized remote decks if those decks eagerly hydrate.

tui_perf.md is binding here: never block the event loop; cache then refresh; idle ticks revalidate rather than recompute; activity gates defer non-urgent work. A Mac-as-driver design that network-fetches all hosts on apply violates those rules even if the gateway is healthy.

### What "all data" can mean without a replica

The user is willing to wait, and even to sync manually. That instinct is the architecture, not a fallback.

Three layers, all pull:

1. **Catalog / roster.** Bounded recent window (7d / 200 completed) is the Agents list. Older rows belong to a History scope with cursor pagination, fetched when the user asks (existing `action_refresh_agents_full_history` is the local analogue). Workflow steps stay out of the catalog unless a later contract version advertises them as first-class rows.
2. **Handles.** Every content handle on the selected row is listed in the existing decks (chat/output/diff/log/artifact/question). Bytes arrive on open, with range and growth already in the contract (`supports_range`, `supports_growth`). Default 64 KiB window, 256 KiB cap: raise the cap later if transcripts need it; do not prefetch every handle for every row.
3. **Mutations and attention.** Stop/retry/fork/answer are RPCs with receipts. They already force a fleet refresh after settle; that refresh should be **the selected host only**.

The federation cache (256 entries / 4 MiB) is a freshness buffer, not a replica of owner `~/.sase`. Copying remote artifact trees, workspaces, or ToolRun SQLite onto the Mac would fight the low-resource constraint and the "machine link writes stay off the primary" decision (`decisions:machine-link-writes-off-primary`).

## Critique of the proposed plan

### What is right

- Mac as the daily driver of sase's TUI, with almost no local agents, is the correct split for a weak laptop plus a strong owner (Apollo).
- Explicit `%dispatch` (with a `%d` shorthand) matches the unified-agents commitment to an explicit target machine. Auto-placement and `%dispatch:auto` were deferred for good reasons (wrong-host launches are expensive to undo).
- Slow or manual sync is the only model that keeps both the Mac and the owner gateways alive. The proposed per-selected-machine sync keymap is **necessary**, not optional.
- Requiring every *user-facing agent operation that is already a fleet verb* to work from the Mac is the right product bar for stop, retry, fork, launch, answer, and read.

### What is wrong or too large

- **"Finish the implementation"** understates the gap. List parity landed. Operation parity is a contract expansion: new advertised capabilities, TUI remaps, receipts, and tests in sase-core *and* sase.
- **"Every local Agents-tab operation"** is not a coherent remote requirement. tmux, local files, local ToolRuns, local dismiss, and local unread are host-local. Shipping them over fleet either leaks owner internals or clones owner state.
- **"All of that data is able to be synced and displayed"** if read as a full replica will blow the Mac's RSS and the 4 MiB federation cache. Read as "every advertised handle can be opened, and history can be paged" it is achievable.
- **Leaving current auto-refresh in place** while making the Mac the main TUI recreates the Athena→Apollo stampede, now with the laptop as a second client. `sase-1j1.5` reduced amplification; it did not make all-host `cache_only=False` catalog on every apply cheap.
- **Running a gateway on the Mac** is unnecessary for this use case. The Mac is a federation *client* (`sase_federation_worker` + enrolled hosts). Owner machines run `sase_gateway` behind Tailscale Serve (not Funnel).

### Binding constraints this plan must not re-litigate

From `plan:202609/unified_agents_across_machines.md` and `sase/memory/dispatch.md`:

- One Agents list; machines are origin/filter, not a second product.
- Terminal dismissal is viewer-only.
- Mutations are owner-side with advertised capabilities.
- No remote tmux/editor, no cross-host continuation, no always-on delivery while ACE is closed.
- Shared backend lives in `sase-core` (`decisions:rust-core-required`). New fleet ops, content kinds, and catalog scopes are core wire, then thin Python/TUI adapters.

## Requirement adjustments

Call-outs. These change the user's wording; the underlying goal (Mac drives the TUI, remotes do the work, nothing important is invisible) stays.

1. **Replace "every local Agents-tab operation" with a closed remote verb set.** Launch, stop, retry, fork, answer/approve, open every content handle in decks, check launch outcome, connect/hello, per-machine sync, filter/group/tab. Capability-gated later: rename, tribe, tab-move, wait. Permanently out of V1 remote: tmux, local artifact-tree browse, local ToolRun SQLite, local dismiss-as-stop, workflow-step rows.
2. **Replace "all data synced" with "all advertised data fetchable."** Catalog stays bounded. History is an explicit scope. Content is on-demand, every handle, ranged. No replica of owner `~/.sase`.
3. **Make per-selected-machine network sync a required keymap**, and make ordinary `r` / auto-refresh / tab-switch **cache-only** for fleet. An all-hosts network sync may exist as a rare command-palette action with a confirmation, not as the default of `r`.
4. **Keep `%dispatch` combo bans in V1.** `%wait` / `%queue` / `%clan` / `%hold` on a remote launch is a later epic (cross-machine queue was already deferred).
5. **Do not require the Mac to run agents or a gateway.** `max_running_agents` on the Mac can stay tiny. Enrollment plus `sase_federation_worker` is enough.
6. **Gate Mac-as-driver traffic on `sase-1j1.6`.** Until Apollo's gateway is measured healthy under a single polling client, adding the Mac as the *main* TUI is an outage plan.
7. **Fix remote content to use every handle, not `handles[0]`**, as part of "displayed." Today's modal is a prototype, not parity.
8. **Follow attention `next_cursor`.** Unified-agents follow-up: inventory `limit=100` never paginates. A Mac driver that cannot see page two of remote questions will miss work.
9. **`%d` is launch-prompt only.** Patch query language already uses `%d` for `status:DRAFT` (`docs/query_language.md`). Same letter-reuse pattern as `%m` (model vs. other surfaces) and `%w` (wait). Document the collision; do not invent a different letter.

## Alternatives considered

### A. SSH to Apollo and run sase's TUI there

Works today, zero new fleet work. Gives up the Mac as the daily driver, which is the whole request. Keep as a break-glass path (`sase tui --tmux` on the owner) for tmux attach and local files.

### B. Replicate owner agent state onto the Mac

rsync / sidecar clone of remote agent dirs, then treat rows as local. Full local-op parity "for free." Cost: disk, RSS, conflict with hidden-clone write lanes, stale rows, and a second source of truth. Rejected.

### C. Push / Watch / SSE from every owner into the Mac TUI

Always-on delivery. Unified-agents explicitly deferred this while ACE is closed, and a laptop on battery/Wi‑Fi is the worst push client. Revisit after pull is boring and correct.

### D. Thin pull-based viewer (recommended)

Mac holds enrollment, federation cache, and TUI projection. Owners hold agents, indexes, gateways. Sync is cache-first, per-host, user-triggered for network. Ops are journaled RPCs. Content is handle-lazy into existing decks.

### E. Auto `%dispatch` / placement

User said they are fine specifying `%dispatch` by hand. Keep it that way. Auto-placement was deferred because a wrong-host launch is costly.

## Recommended solution

**Name:** Mac as pull-based fleet control plane.

**Picture:** The MacBook runs sase's TUI, `sase_federation_worker`, and almost no agents. Apollo (and other owners) run agents, `sase_gateway` on loopback, Tailscale Serve, and the artifact index. The Mac never copies owner state; it caches fleet wire and fetches bytes when a row is opened or a host is synced.

### Phase 0 — Do not add a second polling client yet

- Close `sase-1j1.6` with measured Apollo health under Athena (threads, index fds, RSS, WAL, TUI diagnostic rate).
- Confirm `HOST_READ_BACKOFF` and per-host in-flight caps hold under Agents-tab use.

### Phase 1 — Mac-safe refresh (unblocks the laptop)

TUI + thin dispatch adapter (Python) on top of existing worker `cache_only`:

- Default fleet refresh (`tab_switch`, `apply`, idle, ordinary `r`): `cache_only=True` for summary **and** catalog **and** followed_batch/attention.
- New action `sync_selected_machine` (recommend `gs`, next to `gD`; document in `src/sase/default_config.yml` keymap config). Network-refresh **one** host: the selected remote row's alias, else the active machine tab's alias, else a picker. Show stale age on the chip (`stale · cached 5m ago` already exists).
- Palette-only `sync_all_machines` with an explicit confirm. Never the default of `r`.
- After stop/retry/fork/attention/launch settle, network-refresh **that host only**.
- Keep tui_perf: pump-free task, generation token, cache-then-paint, activity gate, no event-loop I/O.
- Footer/header: `cached Ns ago` so slow sync is honest rather than silent.

This phase alone makes the Mac viable as the daily TUI **with current V1 verbs**.

### Phase 2 — `%d` shorthand (small, local to macros)

- `_DIRECTIVE_ALIASES["d"] = "dispatch"`.
- Fix `scan_dispatch_directive`'s `"%dispatch" not in prompt` early-out to also accept `%d:` / `%d(` / `%d ` forms (the alias table is otherwise ignored).
- Launch Target picker can keep inserting the canonical `%dispatch:<alias>` (portable, grep-friendly) or the short form; prefer canonical in generated prompts, accept both in parse.
- Docs: `docs/macros.md`, `docs/remote_dispatch.md`, `sase/memory/dispatch.md`. Mention Patch-query `%d` collision.
- Tests: alias round-trip, combo bans still fire, `%d:local` reserved, fenced/literal zones.

### Phase 3 — Display parity without a replica (sase-core + TUI)

- Open **all** content handles, not `handles[0]`. Map kinds onto existing decks (chat/output/diff/log/artifact/question) instead of a one-shot modal.
- Honor `supports_range` / `supports_growth`; page past 64 KiB up to the 256 KiB cap; show a "truncated, press …" affordance rather than pretending the file ended.
- History scope: continue catalog cursors when the user asks for older than the 7d/200 window (the comment in `_fetch_fleet_catalog` already claims this loop is the path).
- Attention inventory: follow `next_cursor` (existing unified-agents follow-up).
- Tool Runs: a later content/summary kind from the owner; do not open owner SQLite from the Mac.
- Copy actions: copy fetched text / agent id / session id, never a remote filesystem path.

### Phase 4 — Capability-gated extra verbs (only if still missed after daily use)

New fleet mutation kinds in `sase_core::fleet_mutation` (closed enum expansion, schema bump), advertised on the row, remapped in TUI availability:

- `identity.rename`
- `presentation.tribe`
- `presentation.tab` (viewer `%tab` is already presentation-only; an owner tab move is the same idea on the owner)
- maybe `lifecycle.wait` once cross-machine wait is designed

Each is a journaled owner-side op with the same acceptance-window / same-key recovery as stop/retry/fork. No Python-only mutation path.

Leave V1 launch combo bans until a dedicated epic for remote wait/queue/clan.

### Explicit non-goals

- Remote tmux / editor / workspace attach.
- Replicating artifact directories, workspaces, or ToolRun stores onto the Mac.
- `%dispatch:auto`, cross-machine queue, Watch/push while ACE is closed.
- Workflow-step rows in the remote catalog.
- Mac-side `sase_gateway`.
- Treating viewer dismiss as `lifecycle.stop`.
- All-host network catalog as the default of `r`.

### Suggested keymap and config

| Action | Suggested binding | Notes |
| --- | --- | --- |
| Launch Target picker | `gD` / `Ctrl+G D` | Already exists |
| Sync selected machine | `gs` | New; network, one host, pump-free |
| Ordinary refresh | `r` | Local Agents + **cache-only** fleet |
| Sync all machines | palette | Confirm; rare |
| `%d` / `%dispatch` | prompt directive | Alias; picker still writes canonical form |

`ace.agent_tabs.machine_tabs: auto` is already the right default for a Mac with enrolled remotes: one `⌨ apollo` tab, local `⌂` tab, `]` / `[` to move. Per-machine sync should prefer the active machine tab's alias when no row is selected.

### Success criteria (Mac daily driver)

A session on the MacBook, Agents tab, Apollo enrolled, almost no local agents:

1. Opening Agents paints from cache in one frame; no tailnet catalog until `gs` or a mutation.
2. `gs` on `⌨ apollo` refreshes only Apollo; other hosts stay cached; chips show age.
3. `%d:apollo` and `gD` both launch; combo bans still hold.
4. On an Apollo row: `x` / `R` / `F` / `Enter` (attention) / deck-open of every handle work; tmux and local-file actions stay unavailable with a one-line reason.
5. Truncated content can be paged; questions beyond the first 100 still appear.
6. Apollo gateway threads, index fds, and RSS stay in the `sase-1j1.6` healthy band while the Mac TUI is the primary client.
7. Mac TUI idle RSS does not grow with Apollo's archive; only with the bounded catalog plus open decks.

### Implementation boundary

- Wire, capabilities, mutations, catalog scopes, content reads: **sase-core** (`sase_gateway`, `sase_federation_worker`, `sase_core::fleet_*`). Bump `sase-core-revision.txt` when sase consumes a new binding.
- TUI availability, keymaps, decks, cache-first refresh: **sase** Python, calling `sase_core_rs` / existing `sase.dispatch` facade.
- No second Python fleet client.

## Risks

- **Stampede regression.** Any path that sets `cache_only=False` for all hosts on a timer will re-melt owners. Treat that as a P0 test: two controllers, one slow host, assert one in-flight build and client backoff.
- **Stale-row mutations.** Cache-first means stop/retry/fork must keep using row revision + exact locator; precondition failures should trigger a one-host refresh and a retry of the **same** operation key.
- **`sase-zz`.** Missing `lifecycle.stop` journaled as `acceptance_uncertain` forever already exists. More Mac-driven mutations will hit this; fix receipts before expanding the verb set.
- **Letter collision.** `%d` in a Patch query vs `%d` in a launch prompt. They live in different input widgets; still document.
- **First-handle modal.** If Phase 3 slips, users will believe remote chat/diff/log "does not exist" because only handle 0 opens.
- **Attention page-1.** Same visibility hole for questions.

## Closing recommendation

Take the MacBook idea. Change the requirement from "full local-op and full-data replica" to "pull-based control plane with owner-side verbs and on-demand handles." Sequence: **gateway verification (`sase-1j1.6`) → cache-first TUI + `gs` per-machine sync → `%d` → every-handle decks + attention/history pagination → extra fleet ops only if daily use still misses them.**

I would not SSH-only, would not rsync owner `~/.sase`, and would not turn `r` into an all-host network catalog. The user's offer to sync slowly and to type `%dispatch` (now `%d`) by hand is the correct control-plane UX for a weak laptop.

## Sources

- `docs/remote_dispatch.md`, `docs/ace.md` (Machines, agent tabs, Launch Target), `docs/macros.md`, `docs/query_language.md`, `docs/perf_runbook.md`
- `sase/memory/dispatch.md`, `sase/memory/tui.md` → `tui_perf.md`
- `src/sase/macro/_directive_types.py`, `_directive_scan.py`
- `src/sase/ace/tui/_app_action_availability_agents.py`, `commands/_availability_agents.py`, `actions/agents/_fleet_refresh.py`, `_remote_content.py`, `_remote_lifecycle.py`, `actions/refresh_panel.py`
- `src/sase/default_config.yml` (`dispatch.federation_worker`, `ace.agent_tabs.machine_tabs`)
- sase-core: `fleet_mutation.rs`, `fleet_contract/content.rs`, `fleet_contract/error.rs`, `crates/sase_gateway/src/federation_worker/mod.rs`
- `research:202610/apollo_high_cpu_gateway_snapshot_stampede.md`
- `plan:202609/unified_agents_across_machines.md`, `plan:202610/apollo_gateway_snapshot_stampede.md`
- Beads: `sase-133`, `sase-133.5`, `sase-xe.16.11.7`, `sase-1j1` (`.6` still in progress), `sase-zz`, `sase-v3`
