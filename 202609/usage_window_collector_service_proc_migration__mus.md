# Usage-window collector: background proc → service proc migration — research (mus)

Researcher: mus · 2026-09-23 · independent swarm report (no peer reports consulted).

Question: should the usage-window collector — currently a periodically submitted
background proc (plus a manual `u` "usage" trigger on the Refresh panel) — migrate to
a service proc, refreshing more frequently, without overwhelming providers and with
graceful per-provider error handling?

Bottom line up front: **do not migrate to a daemon service proc.** The current
architecture (scheduler-owned periodic trigger + short-lived, coalesced,
durable background proc per batch) is already the right shape, is already supervised
by the service host transitively, and already contains the provider-safety and
error-isolation machinery the request asks for. A daemon would buy nothing, cost an
always-on process, duplicate supervision the scheduler already provides, and weaken
the batch durability/coalescing semantics. The two legitimate concerns underneath the
proposal — (a) users being disturbed by visible system procs, (b) refreshing more
often — are both solvable without a migration. Details and a concrete recommendation
in §7.

## 1. How collection works today

Three triggers, one shared submission path, one execution vehicle:

- **Periodic (primary):** the `usage_refresh` job in the `checks` routine
  (`src/sase/default_config.yml:1179-1241`, `interval: 300`), implemented by
  `src/sase/scripts/sase_chop_usage_refresh.py`, calls
  `request_due_usage_refresh(origin="axe")`. The checks routine runs inside the
  scheduler, which itself **is** a service proc (`builtin: scheduler`,
  `src/sase/default_config.yml:119-124`, spawned as `sase scheduler run` by the
  service host in `src/sase/service/host_support.py`). So periodic collection is
  already supervised by the service host transitively: host → scheduler (service
  proc, `restart: on-failure`) → routine (restarts crashed routines) → job every
  300 s.
- **TUI fallback:** while ACE is open, `UsageRefreshFallbackMixin` submits the same
  coalesced refresh on the configured cadence (floored at 60 s) off the UI thread
  (`src/sase/ace/tui/actions/_usage_refresh_fallback.py:33-51`), covering machines
  where AXE is absent.
- **Manual:** Refresh-panel `u` ("usage", footer `r tab · f history · u usage · a all`,
  `src/sase/ace/tui/modals/refresh_panel_modal.py:29,115-116`) submits
  `explicit=True, origin="ace"` on a worker thread
  (`src/sase/ace/tui/actions/refresh_panel.py:149-172`); `sase usage refresh` does
  the same with `origin="cli"` (`src/sase/main/usage_handler.py:105-110`); a
  usage-limit disable event does a best-effort due-mark + explicit submit
  (`refresh.py:253-277`).

All three converge on `submit_usage_refresh` (`src/sase/llm_provider/usage/refresh.py:110-227`),
which per provider checks skip reasons, evaluates due-ness, and **admits, joins, or
defers**: concurrent triggers for the same provider coalesce onto one in-flight run
(`RESERVED`/`JOINED`/`DEFERRED`, store-owned in the Rust core via
`src/sase/llm_provider/usage/store.py`). Only newly reserved providers are submitted,
as **one** background proc per batch (`_submit_started_proc`, `refresh.py:378-423`:
`ProcSubmitRequest`, `label="usage-refresh"`, `timeout = batch + 15 s`,
per-provider `concurrency_keys`). The runner
(`src/sase/llm_provider/usage/refresh_runner.py:60-133`) fans out with at most
`MAX_CONCURRENT_USAGE_PROBES = 3` threads, a 20 s per-provider deadline, a 45 s batch
deadline, and a 75 s lease TTL (`refresh.py:33-40`).

Reads never block on collection: the TUI renders from the store through a lock-free
peek (the design consolidated in prior research,
`sase/repos/research/202609/provider_subscription_usage/provider_subscription_usage.md`).

## 2. Critique of the proposal's premises

**Premise 1: "background procs should generally be user-triggered; a periodic process
makes users wonder why a proc is running."** Partly true as a UX observation, false as
an architectural rule. Background procs are the durable execution vehicle for *all*
system work in SASE (scheduler jobs submit them; the proc store, supervisor, timeouts,
and settlement policy exist precisely so system work is bounded and resumable). The
real problem is narrower and confirmed: `usage-refresh` rows carry no service marker
(`_submit_started_proc` sets no `service` block; `ProcSubmitRequest.service` exists at
`src/sase/procs/request.py:56` but is unused here), so unlike service-proc runs —
which the Procs tab hides by default — these rows are visible in `sase proc list` /
the Procs tab while running and linger in history (`history_limit: 100`). A ~45 s row
appearing every 5 minutes is a plausible "why is this running?" Disturbing users is a
*visibility/filtering* issue, not an execution-model issue, and §7 treats it as such.

**Premise 2: "a service proc is more appropriate for periodic work."** Backwards for
this codebase. Config-declared service procs are **daemons**; oneshots are only
transient submissions (`sase service proc run`), never scheduled
(`docs/configuration.md:4059`). A periodic collector as a service proc therefore means
a bespoke long-lived daemon with its own sleep loop — reimplementing, badly, what the
checks routine already provides (fixed interval, per-job timeouts, crash restarts,
single-ownership handover). Only two builtins exist (`scheduler`, `gateway`;
`host_support.py`), so a third builtin is new host surface plus new Rust config
composition plus new restart/backoff tuning, all to supervise ~45 s of work per
5 minutes (~15% duty cycle; worse, an idle process 85% of the time holding no useful
state, since observations live in the store, not in memory).

**Premise 3: "this will allow more frequent refreshes."** Frequency is already a config
knob (`llm_provider.usage_metrics.refresh_seconds`, default 300, floor 60;
`config.py:19-23`), enforced identically on every trigger path. No architecture change
is needed to refresh faster; only a decision about what rate providers tolerate (§4)
and one lease-arithmetic caveat (§6.4).

## 3. What a daemon migration would actually cost

- **New builtin + host surface:** argv resolver (`host_support.py`), config
  composition (Rust-owned `service.procs` merge), enablement/disablement semantics,
  log bounding, status reporting — for a process whose only state is "sleep until
  next tick."
- **Lost batch semantics:** today's one-proc-per-batch gives a durable receipt
  (`UsageRefreshReceipt` with per-provider reserved/joined/deferred/disabled/error),
  a 45 s batch deadline with cleanup margin, per-batch `operation_id`/`proc_id`
  correlation, and automatic release of started leases on submit failure
  (`refresh.py:193-211,426-441`). A daemon must reimplement or abandon each.
- **Lost trigger coalescing:** manual `u`, CLI, limit-event, fallback-loop, and
  scheduler submissions all deduplicate through admission *because* execution is
  on-demand. A daemon doubles the paths (daemon ticks + explicit submissions still
  needed for `u`/CLI/limit-event freshness) and the two must then be deconflicted.
- **Worse failure modes:** a daemon that exits after each batch crash-loops under
  `restart: on-failure` (and its crash-loop `notify` is currently computed but
  unconsumed — prior finding `sase_services_improvements__mus.md` §5); a daemon that
  never exits accumulates in-memory staleness (config, provider registry, plugin
  specs are per-batch inputs today) and needs its own config-reload story.
- **Rust-boundary churn:** admission/due/lease semantics live in sase-core (store is
  a facade; validation calls `provider_usage_project_snapshot`). Per AGENTS.md, any
  semantic change there requires the sase-core change plus the
  `sase-core-revision.txt` pin move — a two-repo change for zero behavioral gain.

## 4. "Don't overwhelm providers" — already guarded, with headroom

Verified probe costs (prior research, live): grok ~0.4 s, codex ~1.0 s, claude ~1.7 s,
agy ~2.4–5 s; all are local, non-inference, zero-model-token interfaces (`$0, 0
turns`), using the user's own CLI auth — SASE never touches credentials (and the
Claude direct-HTTP fallback was deliberately rejected on policy grounds; do not
revisit that as part of this work).

Existing guards, all in the current path:

- ≤3 concurrent probes; 20 s per-provider deadline; 45 s batch deadline; 75 s lease
  TTL so a crashed runner cannot wedge a provider's slot (`refresh.py:33-40`).
- Per-provider due evaluation + admit/join/defer: concurrent triggers (scheduler tick
  + ACE fallback + user `u` mash) never multiply in-flight work for one provider.
- Eligibility gating: only registered providers with `probe: True`, CLI present, and
  referenced-or-explicitly-enabled are collected (`refresh.py:280-308`); global and
  per-provider `enabled` kill-switches (`config.py:30-47,110-117`).
- Invalid config degrades to defaults, never to aggressive values (`config.py:59-84`).

At 5-minute cadence this is ≈288 probe-batches/day of a few seconds each — negligible
against local CLI interfaces. Dropping to the 60 s floor multiplies that ~5×, still
trivially cheap in wall-clock and tokens; the binding constraint is vendor-side
tolerance for polling account endpoints, for which there is no observed signal of
trouble at either cadence, plus the lease/dedupe layer that turns overshoot into
joins rather than stampedes.

## 5. Per-provider error handling — already graceful, isolated, and typed

- **Isolation:** `run_usage_probe(..., isolate=True)` runs each probe in a killable
  worker subprocess with an absolute `deadline_at`; hangs are killed, not waited out
  (`usage/probe.py:64-84,224-265`, `timeout` → typed reason).
- **Runner-level:** per-future `try/except` maps crashes to `probe_failed`
  observations; pending/in-flight leftovers at the batch deadline become
  `deadline_exceeded`; persistence failures are logged, never fatal
  (`refresh_runner.py:113-133,161-167`).
- **Collector-level outcome taxonomy** (never synthesize 0%, never raise): e.g.
  Claude maps not-installed / API-key-mode (`not_applicable`) / logged-out
  (`unauthenticated`) / timeout / `probe_failed`, with a CLI version preflight
  (`usage/claude.py:65-200,355-394`); agy has a version floor (prevents old builds
  from running `/usage` as a *real agent turn* every tick), stderr-marker early kill
  of the logged-out OAuth hang, `AGY_CLI_DISABLE_AUTO_UPDATE`, and a private
  `--log-file` (`usage/agy.py:28-70,120-260` — the H1/H2/H4/H5 mitigations from
  `agy_usage_windows/agy_usage_windows.md` are implemented); grok/muse use
  deadline-bounded transports with `timeout` reason codes
  (`usage/grok.py`, `usage/muse.py`); passive Claude `rate_limit_event` capture is
  best-effort and exception-proof (`usage/claude.py:328-353`).

Residual gaps worth closing instead of migrating (ranked):

1. **Cross-collector audit of logged-out hangs.** Agy's auth-marker early kill is the
   model; confirm codex/muse/grok collectors fail fast (not full-deadline) when
   logged out.
2. **Omitted-zero handling.** An exhausted bucket may omit its fraction field
   (agy H3); every normalizer must map "field missing + status exhausted" to
   `used_percent: 100`, never to skip/silent-drop.
3. **Passive freshness beyond Claude.** The `rate_limit_event` supplement keeps
   Claude numbers current between ticks at zero cost on agent-heavy hosts; check
   whether codex/grok streams carry equivalent quota events before building
   anything.

## 6. Adjustments to the stated requirements

1. **Drop "migrate to a service proc."** Replace with: keep the scheduler-owned
   trigger + on-demand background-proc execution (which is already transitively
   supervised by the service host via the scheduler service proc).
2. **Reframe the UX goal** from "background procs should be user-triggered" to
   "system refresh work should not disturb users." The fix is visibility, not
   supervision: filter `usage-refresh` rows (by `label`/`origin`) from the Procs tab
   and default `proc list` output, or equivalent. Do **not** fake a `service` marker
   onto these rows to hide them: the kill router and `is_service`/`service_name`
   already disagree on stripped rows (prior findings #1–2 in
   `sase_services_improvements__mus.md`), and borrowing that marker would divert
   `sase proc kill` down the service-stop path. TUI changes require the `tui.md`
   reference read first.
3. **"Refresh more frequently" needs no migration** — it is `refresh_seconds` today.
   Any change below 300 s should be validated against observed probe p99s per
   provider, not assumed.
4. **Lease/cadence arithmetic must be kept invariant.** Lease TTL (75 s) exceeds the
   batch deadline (60 s incl. cleanup); the cadence floor (60 s) is *below* the TTL,
   so at the fastest cadence consecutive ticks for a slow provider will join/defer
   rather than run — that is correct backpressure, but it means the *effective*
   minimum per-provider cadence is TTL-bounded. Document it; if a true sub-60 s
   cadence is ever wanted, lower the floor *and* re-derive TTL > batch + cleanup,
   in sase-core, with the pin move.
5. **Keep the Rust boundary.** Due/lease/admission/observation-schema changes belong
   in sase-core with no Python fallback (AGENTS.md §1.3); Python keeps trigger,
   presentation, and collector glue only.

## 7. Recommended solution

**Keep the architecture; tune the knobs; hide the rows; close the ranked gaps.
Do not create a service proc.**

1. **No new service proc, no new builtin, no daemon.** The checks-routine job stays
   the periodic trigger; the ACE fallback loop stays the AXE-absent cover; `u`,
   CLI, and limit-event explicit submits stay as-is. All keep flowing through
   `submit_usage_refresh` admission.
2. **Frequency:** lower `refresh_seconds` in config (toward the 60 s floor) only
   after a short measurement pass of per-provider probe p99 vs. cadence; ship the
   chosen default with the TTL-bounded effective-minimum documented in
   `docs/configuration.md`. No code change required for this step.
3. **Disturbance fix (the actual UX ask):** hide `label == "usage-refresh"` system
   rows from the Procs tab and default listings (origin/label filter, not a service
   marker). Small TUI + CLI-display change; read `tui.md` memory first; add a
   visual/CLI test asserting system rows are hidden while user procs still show.
4. **Robustness follow-ups (in order):** §5 gaps 1–3, each with a collector-level
   regression test using the existing fixtures (`tests/llm_provider/fixtures/`,
   `test_usage_*.py` family: `test_usage_refresh.py`, `test_usage_refresh_runner.py`,
   `test_usage_probe.py`, per-provider `*_usage_probe` tests).
5. **Explicit non-goals:** no direct-HTTP fallbacks (Claude policy), no
   add/average/merge of overlapping windows (percentages are independent per the
   usage-window glossary), no automatic routing/disable decisions from these numbers
   (display-only v1, per consolidated prior research).

Why this beats the alternatives: it preserves supervised-but-cheap execution (host →
scheduler → routine → short batch proc), keeps every existing safety property
(concurrency cap, deadlines, leases, coalescing, kill-switches, typed per-provider
failures) without reimplementation, solves both underlying asks (frequency via an
existing knob, disturbance via filtering), and touches one repo in Python only —
unless gap work reaches store semantics, in which case the sase-core change follows
the standard boundary procedure.

## 8. Verification and provenance

- Method: source review of the shipped tree (`src/sase/llm_provider/usage/`,
  `src/sase/scripts/sase_chop_usage_refresh.py`,
  `src/sase/ace/tui/actions/{refresh_panel,_usage_refresh_fallback}.py`,
  `src/sase/ace/tui/modals/refresh_panel_modal.py`, `src/sase/service/`,
  `src/sase/procs/`, `src/sase/default_config.yml`); glossary strands
  (`usage-window`, `service-proc`, `oneshot`, `proc`, `routine`) via audited
  `sase memory read`; unrelated prior research consulted (base consolidated notes
  only — provider_subscription_usage, agy_usage_windows — no swarm peer reports).
- Not independently re-verified in this pass: live probe latencies/costs (taken from
  the cited prior verifications), and whether `usage-refresh` rows visibly disturb
  Procs-tab users today (inferred from the store/observer filtering rules; worth one
  screenshot/extraction before building the §7.3 filter).
- Test family covering this area for any follow-up change: `tests/llm_provider/test_usage_refresh*.py`,
  `test_usage_probe.py`, `test_usage_eligibility.py`, `test_usage_config.py`,
  `tests/ace/tui/test_refresh_panel_*.py`.
