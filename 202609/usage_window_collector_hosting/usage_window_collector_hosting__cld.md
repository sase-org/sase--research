# Usage-Window Collection as a Service Proc — Research and Recommendation (cld)

**Question.** Should the usage-window collector move from periodic durable procs to a
service proc? Doing so should also allow more frequent refreshes, avoid overwhelming
providers, and handle each provider's failures gracefully. This report critiques that
plan, adjusts the requirements where I think that is justified, and ends with a
recommended solution.

**Short answer.** Yes, move it to a service proc. The migration alone does not deliver
two of the three goals, though:

- **Faster refresh:** a uniformly faster timer is the wrong lever. Claude's usage
  endpoint is known to throttle at 30–60 s polling, and our staleness math is tied to the
  cadence.
- **Robustness:** most of the gaps are in the probe and policy layer. They exist no
  matter which process runs the loop.

I recommend a builtin `usage` daemon that owns the per-provider schedule, with these
properties:

- It wakes on explicit requests (the `u` key), so the `u` press reaches the daemon
  instead of spawning a proc.
- Faster refresh is adaptive: "hot" providers only, with a polling floor declared by
  each provider, and passive data first for Claude.
- It adds a real rate-limit error class that honors `Retry-After` and puts a floor under
  retries.
- The policy lives in `sase_core`.
- Today's proc path stays only as a fallback for when the daemon is not running.

---

## 1. What exists today (verified in code and on athena)

### 1.1 Terminology

Today's usage refreshes are **not** "background commands". In the glossary, that phrase
means a oneshot service proc. Each refresh is instead an ordinary **durable Proc**,
created through `submit_proc_request`:

- argv `python -m sase.llm_provider.usage.refresh_runner`, label `usage-refresh`
- operation `usage.refresh`, origin `axe`, `ace`, `cli` or `limit_event`
- concurrency keys `usage-refresh:<provider>`
- see `src/sase/llm_provider/usage/refresh.py:378`

These procs have no `service` block, so `is_service_row`
(`src/sase/ace/tui/_proc_observer_models.py:112`) does not match them. They show in the
Procs tab and count toward the proc gear. The target of this migration is a
**daemon-mode service proc**, which the sase service (the service host) owns.

### 1.2 Four things submit refreshes

| Trigger | Where | Explicit? |
|---|---|---|
| Scheduler job `usage_refresh` on the 5-minute `checks` routine | `default_config.yml:1240`, `scripts/sase_chop_usage_refresh.py` | no (due-only) |
| TUI fallback loop, every `max(refresh_seconds, 60)` s while the TUI is open, regardless of host state | `ace/tui/actions/_usage_refresh_fallback.py` | no |
| `u` on the Refresh panel, `u` in the Models-panel usage modal, `sase usage refresh` | `ace/tui/actions/refresh_panel.py:149`, `modals/models_panel_usage_modal.py:167`, `main/usage_handler.py:107` | yes |
| A usage-limit disable (an agent hit a quota) | `llm_provider/usage_limit_disable.py:165` → `refresh.py:253` | **yes** |

### 1.3 How a refresh works

1. **Admission** (Rust, `sase_core::provider_usage::{refresh,store}`), per provider:
   - Decides whether the provider is due: `fresh`, `cadence`, `reset_passed`,
     `marked_due`, `backoff` or `retry_after`.
   - Takes a single-flight lease with a 75 s TTL. Later callers join the in-flight
     operation instead of starting a second probe.
2. **Launch:** a durable proc runs the admitted batch
   (`usage/refresh_runner.py`):
   - at most 3 probes at once (`refresh.py:35`)
   - 20 s per provider, 45 s per batch
3. **Probe:** each probe runs in an isolated worker, `python -m
   sase.llm_provider.usage.worker`, with a filtered environment. That worker spawns the
   **vendor CLI**; no collector makes HTTP calls itself.
   - **claude:** up to 5 Node process starts per probe: `--version`, `-p --help`,
     `auth status --help`, `auth status --json`, then `claude -p … /usage`.
   - **codex:** `codex app-server` JSON-RPC `account/rateLimits/read`.
   - **muse:** `muse serve` plus an echo turn that deliberately mints credentials.
   - **agy:** `agy -p /usage`.
   - **grok:** ACP `_x.ai/billing`.
4. **Storage** (Rust store):
   - An `error` observation keeps the last-known-good windows; only `ok`, `not_applicable`,
     `unauthenticated` and `unsupported` change them.
   - Failures back off exponentially from the cadence: `cadence × 2^(n-1)`, capped at
     30 min (`refresh.rs:146`).
   - Explicit refreshes have a **5 s** cooldown (`refresh.rs:17`).
5. **Passive data:** Claude agent streams emit `rate_limit_event`s, recorded for free as
   `stream_event` observations (`usage/claude.py:259`). They are `partial`, so they
   **never** count as a full observation and never delay a probe.

### 1.4 Live measurements (athena, 2026-09-23)

- The proc store currently holds **80 `usage-refresh` proc rows** from the last 6.6 h.
  That is about 12 per hour, or about 290 Procs rows a day, all visible in the Procs tab.
  72 came from the scheduler and 8 from the TUI fallback, which sometimes wins the
  admission race.
- Scheduler batches start a median **308 s** apart: the 5-minute interval plus about 8 s
  of tick drift.
- A batch takes 4.0–17.3 s, with a median of 6.2 s.
- All five providers (agy, claude, codex, grok, muse) currently report `ok`.
- The `claude` usage record is at `account_generation` 333; every other provider is at 1.
  Each generation bump clears that provider's windows and backoff schedule. I did not
  trace the cause (see §9).

### 1.5 Service-host facts that constrain the design

These come from `src/sase/service/*` and prior research in
`sase_services_post_landing_hardening`.

- **Supervision:**
  - The host reconciles every 1 s; SIGUSR1 triggers an immediate reconcile.
  - Only `daemon` mode can be configured.
  - Restart policy is `always`, `on-failure` or `never`. Crash backoff starts at 1 s,
    doubles to a 60 s cap, and never gives up.
- **Builtin names:** these are reserved in Rust (`scheduler`, `gateway`). A new builtin
  needs:
  - the reserved list and schema enum updated;
  - an argv mapping in `service/host_support.py:35`;
  - the sase-core pin moved.
- **No way to poke a daemon:** the host does not forward signals to its procs.
- **Per-proc status contract:** a daemon may write `$SASE_SERVICE_PROC_STATUS`
  (`{"state","summary","updated_at"}`, `host_support.py:63-69`). The Services tab shows it
  under REPORTED. **Nothing writes it yet.**
- **Stale code after an update:** the CLI `sase update` restarts only `scheduler`
  (`main/update_restart.py:50`), while the TUI's update path restarts the whole host. A
  new daemon would therefore keep running old code after a CLI update.
- **The TUI auto-starts the host** unless run with `sase ace -x/--no-service`. The
  scheduler itself runs *under* the host. **So whenever the `usage_refresh` scheduler
  job runs, a host is up that could run a daemon instead.** A daemon makes that job
  fully redundant.

---

## 2. Critique of the plan

### What I agree with

1. **Ownership, not periodicity, is the real distinction.** The Procs tab should hold
   work whose lifecycle a user cares about: monitors, `!` commands, gate executions,
   agent procs. Usage collection is machine-level housekeeping with no user-meaningful
   lifecycle, the same kind of thing as the scheduler or gateway, so the service host is
   its natural owner. About 290 rows a day of `usage-refresh` noise in the Procs tab (and
   in the proc gear) is a real annoyance, and nothing about them is actionable.
2. **A long-lived process makes faster, cheaper refresh possible,** in ways a
   proc-per-batch cannot:
   - Independent timers per provider, instead of one batch where the slowest provider
     sets the pace and 45 s is shared.
   - Wake-on-request with about 1 s latency, instead of Python start-up plus supervisor
     start-up per `u` press.
   - Cached CLI capability checks. Claude's `--version` and `--help` probes are 3 of its
     5 Node spawns per probe.
   - A single stable Services-tab row with a status summary. That makes the collector the
     first producer of the unused `status.json` contract.
3. **It removes duplicate schedulers.** Today the scheduler job and the TUI fallback loop
   race each other, and only the Rust leases keep them from double-probing.

### Where I disagree, or would go further

1. **"User-triggered refreshes stay procs" (implied) — no.** When the daemon is healthy,
   the `u` key should send a request to the daemon, not spawn a proc. Two execution paths
   (daemon for periodic work, procs for `u`) means two sets of bugs, two in-flight
   indicators, and a user-triggered path that can bypass the daemon's provider
   protections. Keep the proc path only as the fallback for when no daemon is running.
2. **"Refresh more frequently" — not uniformly, and not for Claude.** There are three
   reasons:
   - **Claude's usage endpoint punishes fast polling.** Public reports show
     `/api/oauth/usage` returning sticky 429s to tools polling every 30–60 s, for more
     than 30 minutes. `Retry-After` is `0` or missing
     ([#30930](https://github.com/anthropics/claude-code/issues/30930),
     [#31637](https://github.com/anthropics/claude-code/issues/31637),
     [#31021](https://github.com/anthropics/claude-code/issues/31021)). An expired token
     can also return 429 with a large `Retry-After`
     ([TokenTracker #608](https://github.com/xiufengsun/TokenTracker/issues/608)).
     - Our Claude probe runs `claude -p /usage`, which presumably uses the same endpoint.
       Today's 5-minute cadence works (claude is `ok`), but 60 s would be asking for
       trouble.
     - Meanwhile, Claude already gives us free, live windows through `rate_limit_event`
       whenever an agent is running. That is exactly when the numbers move.
   - **Staleness is tied to the cadence.** Freshness is fresh at ≤2× cadence, stale at
     ≤4×, and "unknown" beyond that (`sase_core/src/provider_usage/mod.rs:501`). Lowering
     the global `refresh_seconds` to 60 would mark a Claude window "unknown" after 4
     minutes, blanking the header whenever Claude is probed more slowly. Probe cadence
     and display freshness must be decoupled.
   - **Most windows barely move while idle.** Weekly windows change slowly, and 5-hour
     windows only move while you are using the provider. Speed only pays off for a
     provider that is currently busy.
3. **The move does not by itself deliver "graceful, robust, reliable".** Most of the
   gaps are in the probe and policy layer (§5), and they affect any host process:
   - There is no rate-limit error class, and `Retry-After` is never passed through even
     though Rust accepts it.
   - Explicit refreshes have a 5 s cooldown, and usage-limit events are *explicit*, so
     they bypass backoff at exactly the moment a provider is throttling.
   - There is a process-kill gap that can orphan vendor CLIs.
   - When a batch runs out of time, the runner can overwrite a real result with a
     `deadline_exceeded` error.
   - A Muse mint timeout blanks the Muse windows.
4. **Stale code after an upgrade is a new failure mode.** A long-lived collector that
   imports probe code survives a CLI `sase update` today (§1.5). It must either be
   restarted by the update or exit on its own when the code changes.
5. **The scheduling policy belongs in `sase_core`.** Due, backoff, cooldown, floors,
   jitter and budgets are shared backend policy used by the CLI, TUI, daemon and fallback
   alike. By the project's Rust-boundary rule they belong in `sase_core`, with the Python
   daemon as thin glue. The due/backoff policy already lives there
   (`provider_usage/refresh.rs`).

### Is it worth it?

- **If the only goal were a quieter Procs tab,** one day of work would do: tag
  `usage-refresh` rows as housekeeping and hide them.
- **For all three goals,** the daemon is justified. That is faster refresh with provider
  protection, robustness, and a clean `u` path. It is a medium-sized epic across
  `sase-core` and `sase`, and it costs about 45 MB RSS for one more resident Python
  process (an idle routine on athena uses about 47 MB).

---

## 3. Adjusted requirements (my changes, called out)

| # | Original requirement | Adjusted requirement | Why |
|---|---|---|---|
| R1 | Run the collector as a service proc | **A builtin `usage` daemon service proc owns scheduling for every provider.** The scheduler's `usage_refresh` job is deleted. | The scheduler only runs under the same host, so the job is redundant. One owner instead of three. |
| R2 | `u` triggers a refresh (today: a proc) | **`u`, the Models-panel `u`, `sase usage refresh -b` and limit events send a *request* to the daemon** through the Rust store, which wakes it within about 1 s. Only when the daemon is unhealthy do they fall back to today's durable-proc path. | One code path and one set of protections. No proc rows in the normal case. |
| R3 | Refresh more frequently | **Adaptive cadence:** idle providers stay at `refresh_seconds` (300 s). A provider that is hot (recent agent launch on it, a window at warn level or above, or a window reset just passed) moves to `active_refresh_seconds` (new, default 120 s). **Every provider also has a plugin-declared floor, and Claude's floor is 300 s**, with live Claude numbers coming from passive `rate_limit_event`s. | Refreshes where the numbers move, and respects the known Claude throttling. |
| R4 | Don't overwhelm providers | **Guardrails enforced in Rust, not by convention:** per-provider floors; single-flight leases (existing); a global concurrency of 2 with staggered starts; ±10% jitter; a persisted per-provider hourly probe budget; an explicit cooldown of **60 s** instead of 5 s; limit events **mark due** instead of forcing an explicit probe. | Speeding up must not create new ways to hammer a provider. The explicit path is today's weakest point. |
| R5 | Handle per-provider errors gracefully | **Error classes with distinct retry policies:** transient, rate-limited, auth, unsupported/parked, vendor drift (§5). Add a `rate_limited` reason code. Pass `Retry-After` through, clamped, treating 0 or missing as unknown. Keep last-known-good windows and show their age (existing). Surface collector health in the Services tab and in `sase usage list -v`. | A throttled or logged-out provider should look different from a flaky one, and should never be retried every cadence. |
| R6 | *(new)* | **Decouple display freshness from probe cadence.** Freshness is measured against `max(refresh_seconds, provider floor)`, never against the faster hot cadence. | Otherwise faster polling blanks the header as "unknown". |
| R7 | *(new)* | **Handle upgrades:** the daemon exits with a restart code when its code fingerprint changes, and the CLI's update restart covers it. | Otherwise it keeps running old probe code after a CLI update. |
| R8 | *(new)* | **Degrade safely when there is no daemon.** With `-x/--no-service`, a host that is down, `enabled: false`, or a crash loop, the TUI fallback loop and `u` keep working through today's proc path. They switch on a daemon-health check instead of running unconditionally. | The host is not guaranteed to be running. |

---

## 4. Approaches compared

| Option | Summary | Verdict |
|---|---|---|
| **A. Hide the rows** | Keep everything; mark `usage-refresh` procs as housekeeping so the Procs tab and gear skip them. | A quick win for noise only. It does nothing for cadence, robustness or `u` latency. Worth doing only if the daemon slips. |
| **B. Faster scheduler routine** | A dedicated `usage` routine at 60 s. | **Reject.** It creates more proc churn: every tick spawns a job process, and every due batch spawns a proc. Routines cannot be woken, so `u` still spawns procs. The batch coupling stays. |
| **C. Daemon service proc owning the schedule** *(recommended)* | A builtin `usage` daemon plans per-provider due times through Rust, runs probes in isolated workers, and wakes on store-backed requests. The proc path stays as fallback. | **Recommend.** It meets all the goals and reuses existing leases, backoff, store and worker isolation. |
| **D. C plus long-lived vendor connections** | Keep `codex app-server` or `muse serve` open and consume push notifications (`account/rateLimits/updated`, `usage/changed`). | **Defer.** Codex's push fires during turns, and SASE's agents run through `codex exec`, not the daemon's connection. It holds vendor processes and auth state open. Third-party integrations also report quirks in that notification, such as `primary`/`secondary: null` snapshots once a bucket is exhausted. Revisit after C. |
| **E. Direct HTTP to vendor usage APIs** | Read the CLIs' tokens and call the endpoints directly. | **Reject**, as the original design did: credential handling, token expiry, and for Claude a policy problem. The 429 evidence also applies directly. |
| **F. Run the loop inside the service host** | No new process. | **Reject.** The host must stay a thin supervisor. A probe bug or a lock hang must never stall supervision of the other procs. |

---

## 5. Provider protection and per-provider error handling

### 5.1 Error classes and retry policy (proposed; policy in `sase_core/provider_usage/refresh.rs`)

| Class | Outcomes / reason codes | Retry policy | What the user sees |
|---|---|---|---|
| **Success** | `ok`; also `not_applicable` (API mode) | Next due at the provider's cadence (hot or idle) ± jitter | Windows plus their age |
| **Transient** | `timeout`, `deadline_exceeded`, `probe_failed`, `parse_error`, `malformed_payload` | `max(cadence, floor) × 2^(n-1)` with full jitter, capped at 30 min (today's curve, plus jitter and the floor) | Last-known-good windows, aging; a health note after 3 failures |
| **Rate-limited** *(new)* | new `rate_limited`: 429, "rate limit", "too many requests" or similar in CLI output or JSON-RPC errors | `Retry-After` when > 0, clamped to [15 min, 6 h]. If 0 or missing: a 15 min floor that doubles to a 2 h cap. **An explicit request does not bypass this** (Rust already honors `retry_after_until` for explicit requests). | "claude: rate-limited · retry ~14:05" |
| **Auth** | `unauthenticated`/`logged_out`; also 429 streaks that persist through a full cycle (the expired-token pattern) | No automatic retry until the account context changes or 60 min pass. An explicit request is allowed after the 60 s cooldown. | "claude: logged out — run `claude auth login`" |
| **Parked** | `unsupported`, `not_installed`, `unsupported_cli_version` | No retry until the CLI binary's (path, mtime, size) changes; checked at most hourly | Provider omitted, or "unsupported CLI vX" |
| **Vendor drift** | `vendor_drift` | Parked 1 h, plus a diagnostic log line and an attention notice once per episode | "codex: CLI response changed" |

Required plumbing:

- Record the reason code with each attempt. Today `record_provider_usage_refresh_attempt`
  gets only the outcome, so Rust cannot choose the backoff class.
- Pass `retry_after_seconds` through. Rust already accepts it; `_finish_job` never sets
  it (`refresh_runner.py:190`).

Each collector needs a small classifier:

- **claude:** match 429/rate-limit wording in the `/usage` output and on stderr.
- **codex:** JSON-RPC error messages and codes.
- **agy:** today a rate limit shows up as `parse_error` because stdout is not JSON; check
  stderr first.
- **grok and muse:** match error substrings.

Make `not_installed` consistent: muse, agy and grok report it as outcome `error`, while
claude and codex report `unsupported`.

### 5.2 Guardrails against overwhelming providers

1. **Per-provider floor, declared by the plugin.**
   - Extend `llm_usage_capabilities()` with `min_probe_interval_seconds`. Today
     `_registry_metadata._usage_capabilities` keeps only booleans
     (`_registry_metadata.py:112`), so it must be widened.
   - Suggested floors: claude 300, muse 180 (each probe mints credentials), agy 120,
     grok 120, codex 60. These are judgment calls; tune them against real 429 data.
2. **Single-flight per provider:** the existing Rust lease stays, so CLI, fallback and
   daemon can never probe the same provider at once.
3. **Global concurrency and staggering:** the daemon runs at most 2 probes at a time,
   and starts are ≥2 s apart. That lowers CPU spikes from Node start-ups and avoids a
   thundering herd after a daemon restart.
4. **Jitter:** ±10% on every next-due time, plus full jitter on backoff. This avoids
   synchronizing with other machines (athena, apollo and mac each run their own host and
   may share accounts) and with vendor-side windows.
5. **Persisted hourly budget:** a per-provider token bucket in the Rust store, for
   example 12 probes/h for claude and 30/h for the others. It is a hard ceiling that
   survives daemon restarts and crash loops, and it caps the damage from a policy bug.
6. **Explicit cooldown 5 s → 60 s.** Pressing `u` repeatedly should not probe Claude every
   6 seconds. When a provider is in cooldown, the `u` toast says "claude refreshed 40 s
   ago" instead of probing.
7. **Limit events mark the provider due instead of probing explicitly.** When many agents
   hit a limit together, the result should be one coalesced, backoff-respecting refresh.
   Today it is a series of explicit probes during the throttle.
8. **Passive-first for Claude.** A `stream_event` observation that covers the provider's
   known window keys counts as "fresh enough" to stretch Claude's probe interval to the
   idle cadence while hot. The probe then mainly catches usage from outside SASE (for
   example claude.ai).
9. **Restarts are safe:** due-ness comes from persisted schedule state, so a restarted or
   crash-looping daemon only probes providers that are actually due.

### 5.3 Robustness bugs to fix regardless of host (all verified in code)

1. **Orphaned vendor CLIs** (`usage/transport.py:274`).
   - **Problem:** `_terminate_process_tree` SIGKILLs only while the worker is still
     alive. If the worker dies on SIGTERM, a grandchild that ignores SIGTERM is never
     killed.
   - **Fix:** snapshot the descendants and process groups before sending SIGTERM, and
     SIGKILL whatever is left of that snapshot unconditionally.
   - **Why it matters here:** faster cadence means orphans pile up faster.
2. **A batch deadline double-records results** (`refresh_runner.py:86-132`).
   - **Problem:** leaving the `ThreadPoolExecutor` block waits for running probes, which
     record their real observation. Afterwards the runner records a newer
     `deadline_exceeded` error for the same jobs and counts a second failure. That can
     turn a success into backoff.
   - **Fix:** skip futures that have already finished, or record the timeout only for
     futures that truly never finished. This still matters for the fallback path.
3. **A probe can run twice** (`usage/probe.py:117`). A `TypeError` raised *inside* a
   collector reruns the whole probe as `method(context)`. For Muse that is a second
   credential mint. **Fix:** inspect the signature once instead of catching `TypeError`.
4. **A Muse mint timeout blanks its windows** (`usage/muse.py:198`). If the mint budget
   runs out, the probe returns an authoritative empty observation. **Fix:** return
   `error/timeout`, which keeps the last-known-good windows.
5. **The Codex session closes on a best-effort failure** (reported by the collector
   survey; `transport.py:108` closes on any transport error). A failed best-effort
   `account/read` closes the session, so the following `account/rateLimits/read` fails
   as `probe_failed`.
6. **The worker env allowlist drops variables** (`usage/probe.py:37-61`):
   `CLAUDE_CONFIG_DIR`, proxy variables and `NODE_EXTRA_CA_CERTS` are dropped. The probe
   can therefore read a different Claude account than the one agents use, or fail behind
   a proxy.

---

## 6. Recommended design in detail

### 6.1 Process model and configuration

```yaml
# default_config.yml
service:
  procs:
    usage:
      builtin: usage              # new reserved builtin → argv: sase usage run
      description: "Subscription usage-window collector."
      restart: always             # it exits on code change to get restarted (R7)

llm_provider:
  usage_metrics:
    enabled: true                 # master switch (unchanged); daemon idles when false
    refresh_seconds: 300          # idle cadence AND display-freshness reference (R6)
    active_refresh_seconds: 120   # NEW: cadence while a provider is hot (clamped to floor)
    ...
```

- **Use `builtin:`, not `command:`.**
  - A builtin launcher uses the host's own interpreter (`_sase_command()`), so it avoids
    PATH skew between the host and the user's shell.
  - It reserves the name, and it matches `scheduler` ↔ `sase scheduler run`.
  - The reserved-name change lands in the same `sase-core` change as the policy work, so
    it adds no extra pin bump.
- **New CLI subcommand `sase usage run`** (sorted into `list`, `refresh`, `run`, per the
  CLI rules). It runs the daemon in the foreground and is mostly internal, like
  `sase scheduler run`.
- **Machine opt-out** uses the existing overlay (`service.procs.usage.enabled: false`).
  Per-provider opt-out uses the existing `usage_metrics.providers.<name>: false`.
- **No feature flag.** `enabled:` on the service proc and `usage_metrics.enabled` are
  permanent config choices. An implementing epic may use a short-lived `beta` flag as
  scaffolding while phases land, per the flag rules.

### 6.2 Daemon loop (thin Python; policy in Rust)

```text
startup: record code fingerprint; write status "starting"
loop (wake at the earliest next_at, a request, or the 30 s heartbeat; poll the store's mtime every 1 s):
  settings = usage_metrics settings (config-token cached)
  if not settings.enabled: status "disabled"; sleep until config changes; continue
  providers = eligible_usage_providers()           # cached for 60 s and by config token
  plan = rust.provider_usage_refresh_plan(now, providers(+floor, +hot), cadences)
         -> per provider {due, reason, next_at}      # floors/jitter/budget/backoff inside
  for p in plan.due (most overdue first), ≤2 in flight, starts ≥2 s apart:
      admit(p, explicit = p.reason == "requested")  # existing lease; joins/defers
      run_usage_probe(isolate=True, capability_hint=cache[p])  # existing worker
      record_observation(obs); record_attempt(outcome, reason_code, retry_after)
  write $SASE_SERVICE_PROC_STATUS {state, summary, updated_at}
  if code fingerprint changed: exit 75             # host restarts with new code
```

- **Probes still run in isolated worker subprocesses.** Only scheduling moves into the
  long-lived process. A hung or crashing probe can never wedge the daemon.
- **Capability cache:**
  - The daemon keeps each CLI's version and help-probe results, keyed by (resolved path,
    mtime, size), and passes them to the worker as a hint.
  - That cuts Claude from 5 Node spawns per probe to 2, and agy and grok from 2 to 1.
  - This is the main reason "more frequent" gets *cheaper* rather than costlier.
- **The loop defends itself:**
  - Each iteration runs in a try/except.
  - If the store is unreadable, it reports status `degraded` and backs off (5 s → 60 s).
  - After K consecutive loop failures it exits non-zero, so the host restarts it in a
    fresh process with its existing crash-loop notification.
- **Status summary**, about 200 characters. Example:
  `claude ok 2m · codex ok 40s · agy ok 3m · grok backoff→12m · muse rate-limited→14:05`.
  - This is the first producer of the per-proc `status.json` contract.
  - It fits the watchdog idea (`watchdog_seconds`) from the prior services research.
- **Logging:** one structured line per attempt (provider, outcome, reason, duration,
  next_at) into the host-managed, size-bounded `output.log`.

### 6.3 Waking the daemon and explicit requests

Add a Rust store operation, `provider_usage_request_refresh(provider, origin, now)`:

- It records `requested_at` in the provider's schedule.
- It returns a per-provider receipt: `requested`, `cooldown(next_at)`,
  `rate_limited(next_at)`, `disabled` or `parked`.
- The plan treats `requested` as explicit: it bypasses freshness and ordinary backoff, but
  not the cooldown, `retry_after` or the hourly budget.

The daemon notices a request by polling the usage state file's mtime every 1 s (one
`stat`). That needs **no new IPC**: no signal-forwarding, PID-ownership or socket work,
and a request survives a daemon restart. SIGUSR1 to the daemon's PID can be added later
if 1 s ever feels slow.

The in-flight indicator comes from the store (requested and reserved state) instead of
proc projections. The Models-panel usage modal (`_usage_refresh_scope`,
`models_panel_usage_modal.py:57,269,315`) and the Refresh-panel toast read that.

### 6.4 Callers after the migration

| Caller | Daemon healthy | Daemon unhealthy |
|---|---|---|
| Refresh-panel `u`, Models-panel `u` | `request_refresh` + toast from the receipt ("Refreshing usage: codex, grok · claude refreshed 40 s ago") | Today's `submit_usage_refresh(explicit=True)` durable proc (user-caused, so visible) |
| `sase usage refresh` (waits by default) | Request, then poll the store until each requested provider's `last_attempt_at ≥ requested_at` (45 s cap) | Today's proc plus `_wait_for_operation_ids` (`usage_handler.py:122`) |
| `sase usage refresh -b` | Request only; print the receipt | Today's proc |
| Usage-limit disable | `mark_due("limit_event")`, never explicit | Same mark; the fallback loop picks it up |
| TUI fallback loop | **Idle** (checks health every 60 s) | Today's due-only submit. Optionally tag those rows as housekeeping so they stay hidden. |
| Scheduler job `usage_refresh` | **Deleted** | n/a (it only ever ran under the host) |

"Healthy" means the service status snapshot shows proc `usage` running **and** its
reported `updated_at` is under 90 s old (three heartbeats). The TUI already reads the
status snapshot (`service/control.py:318`), so this costs nothing extra.

### 6.5 Knowing which providers are hot, cheaply

There is no need to scan agents. At launch, the provider launch path writes a
best-effort hint, `mark_provider_usage_hot(provider, until=now+15 min)`, into the Rust
store. That is one small locked write, next to the existing Claude
`auth status --json` context step. A provider also counts as hot when any window is at
warn level or above, when a window reset has just passed, or for 30 min after a limit
event.

### 6.6 Upgrades and multiple machines

- **Upgrades:** the daemon compares its code fingerprint (`sase_core_rs` version,
  installed dist version, and the git SHA for editable installs) every 60 s and exits 75
  on a change. The CLI update restart should also restart the host (or at least
  `usage`), matching the TUI and the prior research's §3.8 fix.
- **Multiple machines:** each machine's daemon polls the accounts that machine is logged
  into. If athena, apollo and mac share a Claude account, the account sees three times
  the probe load. The floors and jitter keep that safe at the defaults. Document the
  per-machine opt-out (`usage_metrics.providers.claude: false` in a machine overlay) and
  leave cross-machine federation of usage state for later.

---

## 7. Where the code changes go (Rust-boundary rule)

| `sase-core` (`sase_core::provider_usage`) | `sase` (Python) |
|---|---|
| `refresh_plan` API (per-provider due/next_at with floors, hot cadence, jitter, budget) | The `usage` daemon loop, `sase usage run`, the status writer, the fingerprint check |
| Backoff classes chosen by reason code; `rate_limited` reason; `Retry-After` clamping | Rate-limit classifiers in each collector; plumbing `retry_after`/reason into attempts |
| `request_refresh` store operation and receipts; explicit cooldown 60 s; hot hints | TUI and CLI routing (§6.4), the health check, in-flight state from the store |
| Freshness measured against `max(refresh_seconds, floor)` | `llm_usage_capabilities()` floors and widened metadata normalization |
| Reserved builtin name `usage` and the schema enum | Default config entry, delete the scheduler job, host argv mapping, update-restart coverage |
| Pure-policy unit tests (table-driven: hot/idle, 429 with 0/absent/huge Retry-After, budget exhaustion, jitter bounds) | Daemon tests with a fake clock and probe runner; TUI and CLI tests for both health states; the transport kill-gap test |

Moving the `sase-core-revision.txt` pin is required, because the new bindings are called
from sase.

---

## 8. Phasing

1. **Harden probes and policy.** Valuable even if the daemon never ships.
   - Everything in §5.3.
   - The `rate_limited` class, `Retry-After` and reason-code plumbing.
   - Explicit cooldown of 60 s; limit events mark due instead of probing explicitly.
   - Jitter on the existing loops.
   - Mostly Rust plus collector classifiers; one pin bump.
2. **Rust planning surface.**
   - `refresh_plan`, `request_refresh`, hot hints, floors, the hourly budget.
   - Decouple freshness from cadence.
   - Reserve the `usage` builtin name.
3. **The daemon and the cutover.**
   - `sase usage run`, the `usage` builtin entry, the status writer, the stale-code exit.
   - TUI and CLI routing with the health-gated fallback; delete the `usage_refresh` job.
   - Models-panel in-flight state from the store; update-restart coverage.
4. **Make faster refresh cheaper.**
   - Capability cache handed to workers; hot launch hints.
   - Claude passive-first deferral; `active_refresh_seconds` on by default.
   - Measure a week of attempt logs (429 counts, durations) before lowering any floor.

Phases 1–2 are independent of the host question. If the daemon is deprioritized, ship
them and the housekeeping tag from Option A.

---

## 9. Risks and open questions

- **Memory:** about 45 MB RSS for a new resident process. Keep imports lazy; the daemon
  needs only config, the Rust binding and the probe runner.
- **A wedged daemon** would silently freeze usage data. Mitigations:
  - the heartbeat-gated fallback (the TUI resumes submitting procs within about 90 s);
  - status-age display (existing);
  - later, the host-side `watchdog_seconds` from the prior services research.
- **Claude throttling in practice:** there is no telemetry today, because 429s are
  hidden inside `probe_failed` and `parse_error`. Phase 1's classification gives the
  first real data. Tune the Claude floor from that data, not from third-party anecdotes.
- **Account-generation churn:** Claude's usage record is at `account_generation` 333
  while the others are at 1. Every bump clears windows *and the backoff schedule*, which
  would quietly defeat rate-limit protection. The cause is not traced; investigate it
  before relying on persisted backoff.
- **Token-refresh races:** every probe except grok can make the vendor CLI refresh or
  mint tokens while agents are running (inferred from how the CLIs work). Probing more
  often makes such a race more likely. That is one more reason to be hot-only and
  passive-first rather than faster everywhere.

---

## 10. Recommended solution

Adopt **Option C**: a builtin **`usage` daemon service proc** that owns
subscription-usage scheduling for every provider. The scheduling *policy* lives in
`sase_core`; the daemon is a thin Python loop.

1. **Ownership.** Add `service.procs.usage` (`builtin: usage`, `restart: always`), run as
   `sase usage run`. Delete the scheduler's `usage_refresh` job. The TUI fallback loop
   and today's durable-proc path remain **only** as a health-gated fallback (daemon
   heartbeat older than 90 s, `-x`, or disabled).
2. **User requests reach the daemon.** Refresh-panel `u`, Models-panel `u`,
   `sase usage refresh` and limit events write a store-backed request. The daemon picks
   it up within about 1 s through an mtime poll. Receipts explain cooldown, rate-limit
   and disabled states. There are no proc rows in the normal case.
3. **Faster, but adaptive.** Idle stays at 300 s. Hot providers (recent launch, a window
   at warn level or above, a reset just passed, a recent limit event) run at 120 s.
   Plugin-declared floors apply, with **Claude at 300 s and passive-first**. Display
   freshness is measured against the idle cadence, so faster polling never blanks the
   header.
4. **Provider protection in Rust:** floors, single-flight leases, 2 concurrent probes
   with staggered starts, ±10% jitter, a persisted hourly budget, a 60 s explicit
   cooldown, and limit events that mark due.
5. **Per-provider error classes:** transient, rate-limited (new `rate_limited` reason,
   clamped `Retry-After`, 15 min → 2 h floor), auth, parked and drift. Each has its own
   retry policy. Last-known-good windows are kept and their age shown. Collector health
   appears in the Services-tab status summary and in `sase usage list -v`.
6. **Reliability of the daemon itself:** every probe in an isolated worker; a per-iteration
   try/except with a bounded failure count; a stale-code exit (75) plus update-restart
   coverage; `status.json` heartbeats.
7. **Fix the verified bugs first** (§5.3): the kill-gap orphans, the runner's double
   recording, the `TypeError` rerun, the Muse blanking, the Codex session close, and the
   worker env allowlist. Also investigate Claude's account-generation churn.
8. **Ship in four phases** (§8). Phases 1–2 pay off even if the daemon is delayed. Base
   any further cadence reduction on a week of classified attempt logs.

---

## Sources

**Code (this workspace and the linked `sase-core`):**

- `src/sase/llm_provider/usage/{refresh,refresh_runner,probe,transport,worker,config,muse,claude,types}.py`
- `src/sase/scripts/sase_chop_usage_refresh.py`
- `src/sase/ace/tui/actions/{refresh_panel,_usage_refresh_fallback}.py`
- `src/sase/ace/tui/modals/models_panel_usage_modal.py`
- `src/sase/main/{usage_handler,update_restart}.py`
- `src/sase/service/host_support.py`
- `src/sase/ace/tui/_proc_observer_models.py`
- `src/sase/llm_provider/_registry_metadata.py`
- `src/sase/default_config.yml`
- `sase-core/crates/sase_core/src/provider_usage/{refresh,store,mod}.rs`

**Live state on athena:** `~/.sase/procs/procs.jsonl`, `~/.sase/llm_provider_usage.json`,
and `ps` RSS of the host, scheduler and routines.

**Prior research** (read through `sase artifact read`):

- `research:202609/provider_subscription_usage/provider_subscription_usage.md`
- `research:202609/subscription_capacity_experience/subscription_capacity_experience.md`
- `research:202609/service_host_and_services_tab/service_host_and_services_tab.md`
- `research:202609/sase_services_post_landing_hardening/sase_services_post_landing_hardening.md`

**External:**

- [anthropics/claude-code #30930 — /api/oauth/usage persistent 429 (retry-after: 0)](https://github.com/anthropics/claude-code/issues/30930)
- [anthropics/claude-code #31637 — usage endpoint aggressively rate limits](https://github.com/anthropics/claude-code/issues/31637)
- [anthropics/claude-code #31021 — OAuth usage API persistent 429](https://github.com/anthropics/claude-code/issues/31021)
- [xiufengsun/TokenTracker #608 — expired token returns 429 with long Retry-After](https://github.com/xiufengsun/TokenTracker/issues/608)
- [itismyfield/AgentDesk PR #5727 — backoff for Claude usage polling after 429](https://github.com/itismyfield/AgentDesk/pull/5727)
- [jortega0033/agentdock #116 — Codex account/rateLimits/updated notification handling](https://github.com/jortega0033/agentdock/issues/116)
