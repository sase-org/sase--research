# MacBook as thin TUI driver over remote machines: research and recommendation

Researcher: mus. Independent report for the 5-researcher swarm (same brief as
`__cdx` / `__cld` / `__grk` / `__gem`). Sources are the working tree only:
`docs/remote_dispatch.md`, `sase/memory/dispatch.md`, the `src/sase/dispatch/`
and `src/sase/ace/tui/` implementations, `src/sase/macro/_directive_*`,
and `src/sase/default_config.yml`. No peer report was consulted.

## TL;DR

The plan is sound in direction and should be approved with amendments. SASE
already has the hard half of this feature: a credentialed tailnet + gateway +
federation-worker architecture, a `%dispatch:<alias>` launch path with a TUI
picker, unified local+remote Agents rows, and journaled remote stop / retry /
fork / attention / bounded-content reads. What is missing is not a new
transport but **parity, pacing, and honesty**: a named parity matrix instead of
"every operation", a manual per-machine sync key (yes, add it), a `%d` alias
done carefully, and sync defaults that keep a weak Mac idle instead of polling
a fleet.

Recommended solution: keep the Mac as a thin controller; do **not** chase
literal 1:1 parity for operations that are meaningless remotely (tmux attach,
local patch jump, local revive/revert); bind the four currently-unbound remote
actions plus one new per-machine sync action; make fleet refresh cache-first
with explicit network escalation; and fix the two UX traps that will otherwise
sink the feature (source-portability preflight friction and outcome-unknown
launches).

## 1. What exists today (the foundation is real)

### 1.1 Transport and trust

- Target runs `sase_gateway` on loopback (`127.0.0.1:7629`), exposed only via
  private Tailscale Serve HTTPS. Tailnet membership is not authorization:
  enrollment consumes a single-use, short-TTL bootstrap bundle
  (`sase machine bootstrap --json`, `umask 077`, delete after use), and steady
  state uses a credential in protected controller state
  (`docs/remote_dispatch.md`, enrollment section).
- Controller commands are deliberately split: `machine list` never touches the
  network; `discover` / `status` do bounded explicit work; `init` / `add` /
  `repair` share one activation path with authenticated-hello verification.
  Repair rotates quarantined/mismatched enrollments; rename/remove are
  viewer-local (`docs/remote_dispatch.md` command table).
- Operational footgun worth preserving in any UI copy: after upgrading `sase`
  on a supervised target, restart the gateway process, or status lies (old
  binary keeps serving). Version-skew reporting already distinguishes
  `sase-gateway unknown`, `fleet contract unknown`, and capability-vs-fleet
  schema versions.

### 1.2 Launch path

- Exactly one `%dispatch:<alias>` (or `%dispatch(alias)`) per prompt;
  `%dispatch:local` reserved; omit for local. V1 forbids combining with
  `%wait`, `%queue`, `%clan`, and `%hold` cannot combine with `%dispatch`.
  Only the dispatch selector is stripped on the controller; everything else
  runs on the target (`sase/memory/dispatch.md`, `src/sase/macro/_directive_scan.py`).
- `%tab:<name>` travels with the prompt and lineage stamps it into
  agent-initiated launches. `%tab` + `%dispatch` runs a **no-network**
  preflight against the cached fleet-contract version: older than v7 refuses
  with an upgrade hint, unknown warns and proceeds.
- Source portability is the strictest gate: without payload evidence (Patch
  reference or explicit revision) the controller demands a clean checkout,
  current branch with upstream, and published `HEAD`. Local-only payloads
  (inputs, launch units, attachments, files, images) are rejected before
  submission. Requests are durable and idempotent; acceptance-uncertain
  responses are retried under the same key, never a new one.
- TUI launch UX already exists: `gD` (NORMAL) / `Ctrl+G D` (INSERT) opens the
  Launch Target picker over `local` + enrolled aliases with local eligibility
  labels (quarantined visible but disabled, no network probe). A
  Target/Source context line appears once a remote is selected.
  Submission validates source proof off the event loop, shows a provisional
  `QUEUED` row, then `STARTING` on settled accept or outcome-unknown `WAITING`
  with a **check dispatch launch outcome** palette command.

### 1.3 Viewer and mutation parity (already shipped)

- Agents tab merges local + remote rows; remote session/clan nodes carry a
  host chip (`apollo`), locals never do; `o` groups **by machine**; query
  spells it `machine:local`. Remote load never joins the `load:` gauge.
- Served window is bounded and symmetric-ish: owner serves 7 days / 200
  completed rows; controller catalog pages at 100 rows × up to 16 pages
  (`_FLEET_CATALOG_PAGE_LIMIT/_MAX_PAGES` in `_fleet_common.py`).
  Workflow-step rows are not served, so remote `×N` can legitimately read
  lower than the owner's. Feed-invalid / stale-cache states are loud (header,
  banner, row marker, detail `Feed error:` line, `last seen … ago`).
- Routed remote mutations today (`_remote_lifecycle.py`, `_remote_content.py`,
  `_remote_attention.py`, `docs/remote_dispatch.md` operations section):
  `x` stop, `R` retry, `F` fork (with `Fork on <alias>` prompt bar), bounded
  content modal (64 KiB default, 256 KiB cap, sha256-validated, cached,
  tail-continuation without refetch), question/gate answer+approve via the
  durable notification inbox (dismissal sticks per revision; outage does not
  dismiss), machine status, launch-outcome checks. All go through journaled
  `sase machine agent stop|retry|fork` / `sase machine attention
  answer|approve` with a ≥30 s settled-receipt window and same-operation-key
  recovery. Fresh agents can be exact-stopped from the owner index before the
  fleet snapshot catches up; remote stop never dismisses the row.
- Fleet refresh (`_fleet_refresh.py`) is already off-thread and careful:
  summary is `cache_only=True`; followed-batch and attention hit the network
  only for followed logical keys; catalog pages over the network with cursor
  continuation; one in-flight refresh with a single coalesced pending rerun;
  generation tokens prevent stale applies; applies defer across
  navigation/hint modes. Attention inventory reconciles independently of the
  visible projection with a 60 s network cadence and cache-only coalescing.

## 2. "Every Agents-tab operation" — the honest parity matrix

The request's strongest sentence ("reliably perform EVERY agent operation …
on remote agents as well") needs to become a matrix, because some local
operations are meaningless or unsafe across the wire. Derived from
`commands/_availability_agents.py` (the authoritative gate) and the
`_REMOTE_AGENT_LOCAL_COMMANDS` blocklist:

| Operation | Local key / command | Remote status today | Recommendation |
| --- | --- | --- | --- |
| Stop (kill) | `x` → `lifecycle.stop` | Shipped, capability-gated | Keep; add bulk/mark scope later |
| Retry | `R` → `lifecycle.retry` | Shipped, capability-gated | Keep; bind dedicated `retry_remote_agent` too |
| Fork | `F` → `lifecycle.fork` | Shipped with prompt bar | Keep |
| View content (chat/output) | palette → content handles | Shipped, bounded modal | Keep; extend to files/diff/artifact (below) |
| Answer / approve (gates, questions) | `A` → attention | Shipped via inbox | Keep; this is the highest-value parity item |
| Check launch outcome | palette, provisional rows | Shipped | Keep; promote visibility (it is the outcome-unknown escape hatch) |
| Launch onto remote | `gD` picker + `%dispatch` | Shipped | Add `%d` alias (see §3) |
| Filter / group by machine / tabs / decks / nav | `f`, `o`, tab strip, decks | Shipped | No work |
| Machine connect / setup | palette, Machines tab `c`/`s`/`r`/`R`/`x`/`Enter`/`f` | Shipped as guidance + bounded hello | Keep guidance-first (do not auto-mutate) |
| Dismiss / mark / save marked / bulk states | marks, cleanup panel | Partially applicable; remote stop does not dismiss | Define explicitly: allow local-only dismissal/marks as view state, never as owner mutation |
| Unread toggle, attempt view, header/jump panels | various | Gated off for remote or context-dependent | Allow where data exists (unread is local view state — safe; attempt view needs served attempts) |
| Copy chat / file path / tool-run id | `copy.agents.*` | Explicitly disabled for remote | Re-enable selectively: chat copy via fetched content chunk; file-path copy only when a portable handle exists; tool-run id when served |
| Tool runs show / stop | `tool_runs.*` | Show needs node runs; stop needs local live run | Make show work off served handles; keep stop local-only (document it) |
| tmux open / tmux mode | `open_tmux` | Disabled for remote (correct) | Keep disabled; offer SSH-handoff target (`-S/--ssh-target`) as the remote equivalent |
| Patch jump, artifact files, metadata, spec edit | `jump_to_agent_patch`, `open_artifact_files`, `view_agent_metadata`, `edit_spec` | Disabled or content-gated | Content-backed detail view is the real project (see §5.3); patch jump needs portable patch refs, not controller paths |
| Rename, tribe edit, add tag (`%wait` dep), revert, kill-and-edit, revive/rewind | `n`, tribe, `W`, revert, `,x`, `w` | Disabled for remote (correct in V1) | Keep V1 exclusions; revive/revert across hosts is a new feature, not parity |
| Follow, attention toasts, focus rows | follow store, inbox | Shipped | Keep; follow keys are the cheapest "track this remote agent" primitive |

Net: roughly two-thirds of the tab already routes or degrades correctly. The
remaining third splits into (a) safe view-state items to enable, (b) one real
project (content-backed detail/files/diff), and (c) items to explicitly
declare non-goals. Shipping "EVERY" literally would mean reimplementing tmux
attach and local-filesystem patch semantics over HTTPS — that is where the
plan should bend, not break.

## 3. `%d` shorthand for `%dispatch`

- **Safe to add.** `_DIRECTIVE_ALIASES` currently maps
  `a c e h i m n q r t w` — `d` is unclaimed, and `%dispatch` is in
  `_KNOWN_DIRECTIVES`. No collision in the parser, and directive completion
  (`_directive_completion_candidates.py`) can offer `%d` alongside
  `%dispatch`.
- **Do it as alias, not replacement.** Canonicalize `%d` → `dispatch` exactly
  like `%e` → `effort`: duplicate/conflict validation, prompt cleanup, and
  picker insertion should all emit the canonical `%dispatch:<alias>` form so
  logs, beads, and transcripts stay greppable. Accept `%d:<alias>` and
  `%d(alias)`; reject bare `%d` with the same "requires a configured machine
  alias" error as `%dispatch`.
- **Watch the nearby `g`-prefix collision, not the parser.** Prompt `gd`
  today means edit-definition-under-cursor while `gD` means dispatch picker.
  That is unrelated to `%d` but will confuse the same users; keep `gD` and
  document `%d` next to it in the picker hint and help (`agents_main_sections`).
- Minor: `%dispatch` rejects `+` ("use `%dispatch:<machine>`") and multi-keys;
  carry those errors over verbatim to `%d`.

## 4. Manual per-machine sync keymap: yes, and make it the default posture

The request proposes "slow or even exclusively manual" remote sync plus "a
new keymap that syncs the currently selected remote machine's data … anyway".
I endorse both halves, with one refinement: ship the keymap **and** change the
default auto behavior to cache-first, rather than shipping a manual key on top
of aggressive polling.

- **Why manual-first is right for a weak Mac.** Each network refresh fans out
  to summary + catalog pages + followed-batch + attention through a local
  federation worker subprocess. Nothing in `_fleet_refresh.py` suggests this
  is free: it is paged (100×16), multi-host, and projection work is pushed
  off-thread precisely because it is not cheap. A controller that polls every
  visible host on every tick turns the Mac into a fleet aggregator — the
  opposite of the thin-driver goal. Cache-first + explicit escalation is the
  correct posture, and the codebase already leans that way (summary
  `cache_only=True`, coalesced single rerun, nav-gated deferral).
- **Proposed binding.** Add one `AppKeymaps` field, e.g.
  `sync_remote_machine`, default-bound (suggest `S`: verify against the
  Agents-tab map — `s` there is taken by `change_status` on patches but the
  Agents tab uses `r`/`R` for refresh/retry, so confirm no Agents-tab conflict
  before finalizing; otherwise ship bound to a free key, never `unbound`).
  Simultaneously **bind the four orphaned remote actions** that are
  `unbound` today (`retry_remote_agent`, `view_remote_agent_content`,
  `answer_remote_attention`, `check_dispatch_launch_outcome`) — the plan's
  "every operation" promise fails on its face while the remote verbs have no
  keys. All five belong in `default_config.yml` next to `agents_refresh: "r"`,
  with the existing comment block extended.
- **Proposed semantics for the sync key** (selected row's
  `fleet_origin_alias`; no-op with a warning on local rows):
  1. cache-only summary apply first (instant, keeps list responsive);
  2. targeted `catalog_hosts` + followed-batch + attention for that alias
     only (not all enrolled hosts);
  3. Machines-tab `s`-style bounded hello for that alias piggybacked or on
     demand;
  4. failures render as the existing loud stale/invalid states, never silent.
- **Auto policy.** Default: Agents-tab tick and tab-switch apply cache-only;
  network escalation happens on (i) the new sync key, (ii) row-focus after a
  staleness threshold, (iii) post-mutation refresh (`force=True` already
  exists), and (iv) attention-inventory network poll (keep 60 s, it is
  follow-key-scoped and cheap). Put the cadence behind existing config, not a
  new daemon. Explicitly decide: no background full-fleet poll loop in V1.

## 5. Critique: is this a good idea, and what would I change?

**Yes — with the amendments below, this is the right architecture, not just a
convenience.** The Mac-as-controller / strong-boxes-as-runners split matches
the system's design center (stateless reads through a worker, bounded serves,
journaled idempotent mutations). It also buys real things: battery and RAM
stay flat while remote hosts burn tokens; the TUI stays usable on a plane
with stale caches; one controller sees every host in one list. The alternative
— beefing up the Mac or running everything locally — fights the hardware
instead of routing around it.

That said, five adjustments are load-bearing:

1. **Downgrade "EVERY operation" to a published parity matrix (§2).**
   Promise: launch, list, filter/group, stop, retry, fork, content, attention,
   outcome-check, per-machine sync — all reliable on remote rows. Explicit
   non-goals for V1: tmux attach (use recorded SSH handoff), local patch
   jump, local revive/revert/kill-and-edit, `%wait`/`%queue`/`%clan`/`%hold`
   combos. Each non-goal needs one sentence in the docs and, where applicable,
   a disabled-with-reason palette state (the availability gates already do
   this — keep them).
2. **Treat source-portability preflight as the #1 UX risk, not a footnote.**
   The clean-checkout + published-HEAD + no-local-payloads gate will fire
   constantly from a Mac that mostly edits dotfiles and prompts. Users will
   read it as "remote is broken". Either (a) teach the happy path first —
   picker shows the three preflight conditions before submit, with the exact
   failing condition named; or (b) make Patch-reference / explicit-revision
   evidence one keystroke away from the prompt bar. Do not loosen the check
   silently; its idempotency story depends on it.
3. **Design for outcome-unknown as normal.** Provisional `QUEUED` → `STARTING`
   → `WAITING` + outcome-check is good, but `WAITING` will be the common
   sight on flaky hotel wifi. Keep the provisional row until the authoritative
   fleet row arrives (already the design), and make the outcome-check command
   prominent, not palette-buried.
4. **Mind multi-controller skew.** Follow state, dismissal, marks, and inbox
   ack are controller-local. Two Macs driving one runner will disagree about
   "dismissed" and "read". That is acceptable if stated; it is a bug report
   factory if not. Document: owner state is truth, controller state is view.
5. **Do not auto-heal the network.** The loud stale/invalid rendering is a
   feature. Any "retry in background until fresh" behavior reintroduces the
   resource problem and masks partitions. Manual sync + post-mutation refresh
   + scoped attention polling is enough for V1.

Alternatives considered and rejected: (a) full bidirectional sync / CRDT
fleet state — vastly more machinery for no V1 payoff; the cache + journaled
mutation model already gives the needed guarantees. (b) VNC/SSH-tmux
"drive the strong box's TUI" — trivially full-parity but sacrifices the
unified multi-host list, burns Mac battery on rendering, and dies with the
connection. (c) Running agents on the Mac after all with limits — concedes
the premise; the whole point is the Mac stays thin.

Security notes (no change to the trust model, just do not regress it):
bootstrap secrets never in argv/logs/beads; `machine show` stays redacted;
Funnel stays forbidden; quarantine stays visible-but-disabled; same-key
recovery discipline (never resubmit under a new key when uncertain) must
extend to any new bulk remote action.

## 6. Recommended solution (phased)

- **Phase 0 — aliases and keys (small, unblocks everything).**
  `%d` alias with canonicalization + completion + help text; bind
  `sync_remote_machine` + the four unbound remote actions in
  `default_config.yml`; add the picker hint line. Tests: parser alias matrix,
  keymap-metadata coverage (the catalog self-check fails loudly on drift —
  keep it green), picker insertion emits canonical form.
- **Phase 1 — read parity and pacing (the core ask).**
  Per-machine sync action per §4; Agents tick cache-first; stale/invalid
  rendering unchanged; `by machine` grouping + `machine:<alias>` filters
  verified against multi-host fixtures; catalog pagination exercised to the
  16-page ceiling in tests. Success metric: idle Mac shows zero network
  fleet I/O between explicit syncs (verify by worker-op log, not by vibes).
- **Phase 2 — safe write parity.** Enable local-view-state ops on remote rows
  (marks, dismissal-as-view, unread, save-marked, copy-reference); keep
  owner-mutations capability-gated. Decide bulk semantics: per-alias grouping
  with per-host receipts, same-key recovery per host.
- **Phase 3 — content-backed detail.** Extend the bounded content client
  (handles, digest, 64/256 KiB bounds, tail continuation) to files/diff/
  artifact metadata so `edit_spec`-as-view, metadata, and artifact-files
  work off served handles; patch-jump only via portable refs. This is the
  only phase with real protocol surface; keep it behind capability
  advertisement exactly like lifecycle/attention today.
- **Phase 4 — auto-sync policy and docs.** Document the no-background-poll
  default, the attention 60 s cadence, multi-controller view-vs-truth rule,
  upgrade-restart discipline, and the parity matrix with non-goals. Add a
  `doctor -D -C dispatch` + `machine status` preflight checklist to the
  runbook section for Mac drivers.

## 7. Verification sketch for the implementing plan

- Parser: `%d:alias` / `%d(alias)` accepted, bare `%d` errors, combos with
  `%wait`/`%queue`/`%clan`/`%hold` rejected, picker round-trips canonical.
- Fleet: multi-host fixture with one invalid + one stale host renders loud
  states; `×N` mismatch documented by fixture (workflow steps unserved);
  provisional launch rows resolve to authoritative rows by logical locator.
- Mutations: stop/retry/fork/attention against a fake gateway assert
  journaled keys, ≥30 s window behavior, and same-key retry on dropped
  response; quarantined alias refuses with the viewer-local message.
- Resources: cold-start and tab-switch fleet refresh with N enrolled hosts
  asserts cache-only by default and per-alias network only on the sync key;
  worker subprocess idle-shutdown covered.
- Config: `just check` (per repo memory, the agent verification recipe) plus
  the keymap-metadata drift check; no `check-full` unless CI needs repair.

## 8. Requirement adjustments log (explicit)

1. "Manually specify `%dispatch`" → also accept `%d`; picker still inserts
   canonical `%dispatch:<alias>`. Justification: §3, zero parser risk.
2. "EVERY agent operation" → parity matrix with named V1 non-goals (§2, §5.1).
   Justification: literal parity demands reimplementing local-only semantics
   (tmux, local paths, revive) over HTTPS.
3. "Slow or manual sync" → manual per-machine sync key shipped **and**
   auto-refresh made cache-first (§4). Justification: a manual key on top of
   polling leaves the resource problem unsolved.
4. Unbound remote actions → bound by default (§4). Justification: unbound
   verbs cannot satisfy a reliability promise.
5. Added: preflight-visibility and outcome-unknown prominence as acceptance
   criteria (§5.2–5.3). Justification: these are the two states Mac drivers
   will live in; burying them fails the feature regardless of transport.
