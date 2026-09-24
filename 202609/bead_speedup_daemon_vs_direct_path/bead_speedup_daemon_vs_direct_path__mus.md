# Bead daemon service proc: is it worth it, and what should it be?

**Researcher:** mus · 2026-09-24 · swarm 3-researcher set (independent report)
**Question:** should we build an optional daemon service proc to make bead
reads (and ideally writes) much faster, and if so how?
**Short answer:** the idea is directionally sound but oversized as stated.
Do not start with a read/write daemon. Kill the ~2 s Python import tax and
extend the existing Rust bead-CLI fast path first (days, helps every
invocation, no lifecycle cost), then — only if that is insufficient — add an
*optional, transparent, read-cache-first* daemon over a Unix-domain socket
with automatic fallback to the direct path. Treat a serializing write path as
a separate, later, explicitly-gated phase.

---

## 1. What I actually measured (this workspace, today)

All timings are wall-clock on this machine, warm caches unless noted.
Absolute numbers will vary; the *ratios* are the finding.

| Command | Time | Notes |
|---|---|---|
| `sase bead list --status open` | ~2.6–2.9 s (4 runs) | slow path, renders ~29 lines |
| `sase bead show <id>` | ~2.6 s | slow path |
| `sase bead stats` | ~0.86 s | much faster than list/show |
| `sase bead <verb> --help` | ~0.3 s | argparse short-circuits heavy imports |
| `.venv/bin/python -c "import sase.bead.cli_query"` | ~1.6 s cumulative / ~2.1–2.3 s wall | import fan-out (below) |
| `from sase.main.entry import main` | ~0.02 s | entry itself is cheap; cost is downstream |

`python -X importtime` on `sase.bead.cli_query` shows the read path dragging
in the presentation stack: `sase.pager` (~1.0 s cumulative), `sase.pager.app /
document / screen`, ACE TUI widgets (`ace.tui.widgets.prompt_panel` ~0.6 s),
`xprompt` properties/models. The tail of the import tree:

- `sase.bead.cli_show_batch` → `sase.pager.*` → ACE TUI → `xprompt.*`

Store shape (this checkout): `sase/repos/beads/issues.jsonl` is ~16.7 MB /
~5,968 lines; the beads sidecar totals ~282 MB mostly in `pages/`.

**Reading:** of the ~2.7 s `list`, on the order of 2 s is interpreter +
import fan-out, not store I/O. The Rust read itself is fast (cf. `stats` at
0.86 s end-to-end including startup). So a daemon that keeps a warm process
can at best remove the ~2 s startup/import portion of reads — real, but it is
a *constant* saving, independent of store size, and obtainable without a
daemon too (see §4).

**Writing:** I did not mutate the real store to time writes, by design. Code
inspection (§2) says write latency is dominated by things a warm process does
*not* remove: git commit/sync/push, publication waits (30 s mutation /
120 s launch budgets), lock acquisition and contention retry, sidecar
convergence hints. A daemon helps writes only secondarily (lock serialization,
amortized imports); the long tail stays.

## 2. How the current paths actually work

### 2.1 Reads: two paths, and the fast one deliberately skips list/show

- `src/sase/main/entry.py` tries `try_handle_bead_fast_path(sys.argv[2:])`
  before argparse. `src/sase/main/bead_fast_path.py::execute_bead_cli`
  resolves a `_FastPathContext` (target routing, read/write dirs, sandbox
  guard) and calls the Rust binding `bead_cli_execute`. On `handled=False` or
  missing binding it returns `None` and Python takes over.
- Explicitly *excluded* from the fast path today: `list`, `read`, `show`
  (always slow), `close`, `create`, `epic-symbols`, `task-type`, `update` with
  Python note surface, `@<path>` expansions, full-format `search`
  (`bead_fast_path.py` lines ~30–55). That exclusion list is precisely the
  verbs users feel as "slow beads".
- Slow reads go `cli_common.get_read_view / get_project` → `BeadProject`
  (`src/sase/bead/project.py`, `_project_queries.py`) → `sase.core`
  `bead_read_facade` (Rust) → Python render through `cli_query_render`,
  `cli_show_batch`, `pager`. Every slow read pays the import fan-out in §1
  plus store location/routing (`store_locator.py`, `operation_context.py`,
  `cli_location.py`, cross-project snapshots).

### 2.2 Writes: the expensive parts are correctness, not imports

A CLI mutation carries a *completion contract*: it must not print success
unless the mutation reached the canonical remote (`bead_fast_path.py`
`published` gating, `mutation_commit.py`, `_sync_publication.py`). The write
path includes:

- `assert_bead_store_write_sandboxed` guard, read-only-store refusal
  (checkout-local `.sase/sdd-store.json` discoveries are read-only),
- Rust mutation lock (`lock_timeout` → safe verbatim retry only, via
  `_store_contention.py`; any other failure must propagate untouched),
- `bead_store_write_lock` / SDD `store_git_write_lock`, `git_sync`,
  `push_bead_work_launch` (sync + push, 30 s mutation wait budget),
  background refresh scheduling (`schedule_bead_refresh`,
  `_maybe_schedule_bead_refresh`, TTL-gated),
- ownership routing: user primary vs. machine writable sidecars/leases
  (`background_store.py`, `operation_context.py`) plus sidecar convergence
  hints. Automated writers must *not* resolve the canonical locator.

A daemon writer would have to re-host every one of these semantics to stay
correct. Missing any (idempotency, lock ordering, publication gating,
read-only refusal, sandbox guard, audit sync logs) turns "faster writes" into
"wrong writes".

### 2.3 Service procs: what a daemon would plug into

- `sase service` manages a per-machine foreground host supervising direct
  children (`subprocess.Popen`) with restart policy, exit settlement, bounded
  logs (`src/sase/service/host*.py`, `restart.py`, `status.py`). Live here:
  `gateway`, `scheduler`, `telegram_receiver`.
- Proc identity/config is Rust-composed (`service.procs` layers,
  `src/sase/service/config.py`; `ServiceProcConfig` has `mode`, `restart`,
  `stop_signal/timeout`, `log_max_bytes`, `after`, `launcher` of kind
  `command` or `builtin`, `cwd`, `env`). A bead daemon would be one more
  `command` launcher (e.g. `sase bead-daemon serve`) or a new builtin.
- There is **no existing IPC story** for procs: no socket/HTTP/gRPC/FIFO
  convention in `bead/` or `service/` (verified by search). The daemon needs a
  transport designed from scratch: framing, versioning, auth, lifecycle.
- Precedent that constrains the design: native service lifecycle is
  *disabled under pytest* (exit 125, `platform_models.py`); guarded recipes
  refuse raw agent runs; the Rust core is required (shared behavior lives in
  `sase-core`, no Python fallback — project memory `rust-core-required`).
  A Python daemon that reimplements store semantics violates that boundary;
  it must be a thin transport over the Rust facades, or the daemon logic
  itself must move into `sase-core` with Python only spawning it.

### 2.4 Already in flight (do not duplicate)

- The bead list shows an open task `sase-x3`: "Rust bead store multi-get:
  statuses-for-ids binding to replace the list_issues full hydration in
  `bead_statuses_for_project`". That is exactly the non-daemon read fix
  family (§4). Coordinate, don't compete.
- `bead_refresh_mode` (`background`/`blocking`/`off`) plus TTL-gated
  background integration already exists to keep read freshness costs off the
  critical path. A daemon cache must compose with these markers, not bypass
  them.

## 3. Critique of the plan as stated

**"Optional daemon makes reads much faster."** Partly true. It removes the
~2 s warm-up per invocation. But (a) most of that is removable without any
daemon (§4), (b) the saving is constant while store-driven costs (16 MB
JSONL today, growing; `pages/` at 282 MB) grow underneath it, and (c) a
cache daemon buys staleness risk on every read: git integration, background
refresh, machine-writer sidecars, and direct-CLI writers all mutate state
behind its back. The invalidation story (mtime/generation markers?
event-stream tailing? `integration_marker_generation`?) is the whole project;
the socket is the easy part.

**"Ideally writing too (though harder)."** Correct that it is harder —
understated how much harder. Writes are a distributed-commit problem (local
mutation + git commit + push + publication + convergence hints) with
per-project ownership routing and sandbox/read-only guards. A daemon writer
is a single-writer serialization point: good for lock contention, but it
becomes a single point of failure, a crash-recovery problem (was the mutation
applied before the crash? — needs idempotency tokens, never blind retry), an
ordering problem across projects/workspaces, and an audit problem (whose
claim? which agent? sync-log attribution). "Faster writes" mostly won't
materialize for the long tail (push/network), while correctness risk goes up
across the board.

**What the plan omits:** transport choice and auth; protocol versioning and
mixed-version fleets (uv-tool python vs. repo `.venv` vs. release); cache
invalidation and freshness contract (what does "stale" mean in seconds?
who observes it?); multi-writer coexistence (daemon + direct CLI + machine
writers must all keep working — the daemon can never be required); offline
and test behavior (tests block lifecycle; daemon must be absent-but-fine);
observability (`service proc logs/show/status` integration, degradation
telemetry); blast radius (one daemon per machine serving many projects and
checkouts — keying, isolation, per-store locks); and the Rust-boundary
question (where does the daemon's store logic live?).

**Is it a good idea?** As a *read-cache-first, optional, transparent*
performance layer: yes, conditionally — after the cheap wins. As a
*read/write daemon from day one*: no. The write half concentrates all the
risk and little of the latency saving, and it tempts reimplementing core
store semantics in Python against the project's own boundary rule.

## 4. What I would do instead (or first)

In cost order; each step pays off with or without a daemon:

1. **Import diet for the bead slow path (biggest ROI, no daemon).**
   `cli_query`/`cli_show_batch` unconditionally pull `pager` + ACE TUI +
   `xprompt`. Defer those imports to actual pager/render use, split a
   `--plain`/`--json` path that never imports TUI code, and measure with
   `-X importtime` in CI. Target: slow reads from ~2.7 s toward the ~0.9 s
   `stats` band. This helps every agent, every checkout, daemon or not.
2. **Extend the Rust `bead_cli_execute` fast path to the excluded read
   verbs** (`list`, `show`, `read`, full `search`) and the excluded
   presentation-neutral mutations. The scaffolding (context resolution,
   sandbox assert, publication gating, refresh scheduling) already exists;
   each verb is incremental. This is the durable fix for "beads feel slow".
3. **Point-query bindings before daemons.** `sase-x3` (statuses-for-ids
   multi-get) is the pattern: replace full-hydration `list_issues` scans
   with targeted Rust bindings wherever callers need N statuses/details.
   Audit `bead_statuses_for_project`, TUI poll loops, and wait evaluation
   for scan-then-filter shapes.
4. **Then, if reads are still too slow: optional read-cache daemon.**
   Narrow scope (§5, phase 1): warm process, UDS, read-only, generation-aware
   cache, direct-path fallback. Writes stay direct.
5. **Only then: gated single-writer queue** (§5, phase 2), behind the same
   socket, with idempotency tokens and the publication contract intact —
   and only with evidence that lock contention (not push/network) is the
   write bottleneck.

Alternatives considered and rejected: TCP/localhost HTTP server (bigger
attack surface, port conflicts across workspaces, no benefit over UDS for
local clients); SQLite mirror daemon (a second source of truth alongside
JSONL event streams + git — the project already maintains one compat mirror
and rebuilds it lazily; don't add another); file-watch (inotify/FSEvents)
invalidation as the primary mechanism (misses git-integration and cross-clone
updates; generation/mtime polling is dumber and more honest); making the
daemon required (breaks tests, sandboxes, offline checkouts, mixed-version
fleets — non-starter).

## 5. Recommended solution (staged, with requirement adjustments)

### Adjusted requirements (call-outs vs. the original sketch)

- **[ADJUSTED] Optional and transparent, not merely optional.**
  Every `sase bead` invocation must work identically with the daemon
  stopped, crashed, stale, or version-skewed — automatically falling back
  to the direct path with zero flags. The daemon is a cache, never a
  dependency. Clients enforce a short dial/read deadline and fail over.
- **[ADJUSTED] Reads first; writes explicitly out of scope for v1.**
  Ship read acceleration and measure. A write path ships only as a
  separately-gated phase with its own correctness bar (§5 phase 2).
- **[ADJUSTED] Rust owns store semantics.**
  The daemon (Python or otherwise) is transport + cache + supervision only.
  Reads/writes execute through the existing `sase_core_rs` facades
  (`bead_read_facade`, `bead_mutation_facade`, `bead_cli_execute`). No
  Python reimplementation of filtering, ID resolution, locking, or merge
  logic. If daemon-resident logic is needed that other frontends would
  share, it goes in `sase-core` and the `sase-core-revision.txt` pin moves
  accordingly (per project boundary rule).
- **[ADJUSTED] Freshness contract is explicit and observable.**
  Define max-staleness per verb, expose `daemon generation vs. store
  generation` in `service proc show` / a `bead-daemon status`, and log
  fallback counts. A cache whose staleness nobody can see is a bug source.
- **[ADJUSTED] Absent in tests and sandboxes by default.**
  Follow the existing lifecycle-blocked-in-tests precedent: no daemon
  requirement in pytest, guarded recipes, or read-only/sandboxed stores.
  Opt-in only.

### Phase 0 — measure and slim (no daemon; 1–2 days)

- Add a timing harness for `list/show/stats/search` + `-X importtime`
  assertion on `sase.bead.cli_query` (fail on new top-level TUI imports).
- Lazy-load `pager`/TUI/`xprompt` out of the query path; add a
  non-interactive render path for piped/JSON output.
- Success bar: slow reads approach the `stats` band (~1 s) with no behavior
  change. Reassess whether a daemon is still justified; much of the time it
  won't be.

### Phase 1 — optional read-cache daemon (only if Phase 0 insufficient)

- **Supervision:** one `service.procs` entry, `command` launcher
  (`sase bead-daemon serve`), per-machine UDS at a versioned path under the
  service state dir (file-mode 0700 dir / 0600 socket; no TCP).
- **Protocol:** minimal versioned JSON-RPC-ish over UDS: `hello/capabilities`
  (version, project keys, generation), `read` verbs verbatim
  (`list/show/read/search/stats/ready/blocked`), `status` (cache age,
  generation, hit rate), `invalidate`, `shutdown`. Client dial timeout
  ~50 ms, read deadline ~1–2 s, then direct fallback.
- **Cache:** per `beads_dir` read-model keyed on store generation
  (`integration_marker_generation` + `issues.jsonl`/events mtime/size);
  any mismatch → re-read through Rust facade, never serve stale beyond the
  contracted bound. TTL-gated background refresh continues underneath.
- **Routing:** daemon resolves the same `operation_context` routing as the
  CLI (canonical vs. sidecar, read-only refusal) — it must refuse exactly
  what the CLI refuses.
- **Fallback truthfulness:** every response header says `served_by:
  daemon|direct` and `stale_seconds`; slow-path parity tests run both ways.
- Success bar: p50 `list/show` ≤ ~0.3 s daemon-hot with identical output
  bytes vs. direct; daemon-stopped runs bit-identical and ≤ today's times.

### Phase 2 — gated write queue (separate decision, separate bar)

Only if contention/lock-wait evidence (holder-file records, `lock_timeout`
rates) shows the writer lock — not push/network — is the bottleneck:

- Single-writer FIFO per `beads_dir` inside the daemon; idempotency token
  per requested mutation (client-generated); never retry a non-`lock_timeout`
  failure; preserve the publication contract (no success output until
  published) and sync-log attribution.
- Crash protocol: on restart, recover lock state, report unknown-outcome
  tokens as such (client re-reads; never replays blindly).
- Disabled by default wherever the lifecycle is blocked (tests), in
  sandboxes, and for read-only stores; direct writes always remain.
- Success bar: contention errors → ~0 with no increase in unpublished-
  as-success incidents (must stay zero) and no divergence vs. direct writes
  under a mixed daemon+direct workload test.

### What to build first, concretely

Phase 0 items are shovel-ready now (import laziness, fast-path verb
coverage, multi-get bindings). Phase 1 wants a short design note on the UDS
protocol + freshness contract before code. Phase 2 wants contention telemetry
first — without it, it's speculation.

---

## 6. Risks and open questions

- Cache invalidation across git integration and machine-writer sidecar
  convergence is the hardest correctness piece; generation markers are the
  honest signal, mtime alone is not.
- Thundering-herd on daemon restart (every agent reconnects at once) needs
  a staggered reconnect or preserved socket backlog discipline.
- Mixed-version fleets: old CLI vs. new daemon protocol must fail over to
  direct, loudly in logs and silently in UX.
- `pages/` (282 MB here) and generated bead pages: explicitly out of cache
  scope; the daemon caches structured reads, not rendered pages.
- The fundamental question Phase 0 may answer: if slow reads reach ~1 s
  without a daemon, is a supervised cache process worth its lifecycle,
  debugging, and staleness surface? My prior is often no — and that is a
  good outcome: the import diet and fast-path work keep paying forever.

## 7. Bottom line

Build the speed, not the daemon — then daemonize only the remainder. The
measurements say ~70% of read latency is process warm-up, the fast-path
scaffolding already exists but skips exactly the slow verbs, and the write
tail is git/network/locks that a daemon barely shortens while fully
inheriting its correctness burden. Stage it: slim imports → extend Rust fast
path → targeted multi-get bindings → (if needed) optional read-cache daemon
with auto-fallback → (only with contention evidence) gated write queue. That
sequence gets most of the speed with almost none of the risk, and each step
is independently shippable.
