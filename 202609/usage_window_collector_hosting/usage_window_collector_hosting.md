# Usage-Window Collector: Where It Should Run, and How to Refresh Faster Safely (consolidated)

Lead-researcher consolidation of three independent reports (`__cld`, `__mus`, `__gem`
in this directory), plus new code and live-state verification on athena on 2026-09-23.

**Question.** Should the usage-window collector stop running as periodic background
procs and become a service proc? That move should also allow more frequent refreshes,
avoid overwhelming providers, and handle each provider's failures gracefully.

## Bottom line

1. **Your instinct is right, and the problem is worse than it looks.** The periodic
   `usage-refresh` procs are not just confusing. On athena they make up **76 of the 103
   non-service proc rows (74%)**. They share the 100-row finished-proc history budget
   with your real procs, so they push user history out of the store every few hours. A
   faster cadence on today's path would erase user proc history within about 2 hours.
2. **Change the requirement from "its own service proc" to "owned by the service
   tree".** The scheduler already *is* a builtin service proc. I recommend a dedicated
   scheduler routine, a `usage` lane with a 60 s interval, whose job **runs the probe
   batch itself instead of submitting a proc**.
   - This removes every periodic proc row.
   - It gives the collector Services-tab job nodes, bounded run history, overrun
     metrics and the `r` manual-run key for free.
   - It is already restarted by `sase update`.
   - It needs no new builtin, no IPC and no health-gated fallback machinery.
   - A dedicated `usage` daemon (cld and gem's recommendation) is a sound design, but
     its extra benefits are small for its cost today. §8.4 states when to adopt it.
3. **The host change is not what makes this faster or safer.** The provider-protection
   and error-handling policy does that, and it is host-independent: it lives in
   `sase_core` and in the collectors. All three reports agree this work is needed, and
   it should land first. It includes:
   - adaptive "hot" cadence instead of a globally faster timer;
   - per-provider polling floors, with **Claude at 300 s**, because its usage endpoint
     is known to throttle 30–60 s pollers;
   - a real `rate_limited` error class that honors `Retry-After`;
   - limit events that stop bypassing backoff;
   - several verified probe and runner bugs.
4. **User-triggered refreshes (`u`, `sase usage refresh`) can stay procs.** That is
   consistent with your own rule that user-initiated work may be a visible proc. They
   already pass through the same Rust admission (single-flight leases, cooldown,
   `Retry-After`), so they cannot bypass provider protection.

---

## 1. How it works today (verified)

**Triggers.** All of them converge on `submit_usage_refresh`
(`src/sase/llm_provider/usage/refresh.py`):

| Trigger | Where | Explicit? | Cadence |
|---|---|---|---|
| Scheduler job `usage_refresh` in the `checks` routine | `default_config.yml:1240`, `scripts/sase_chop_usage_refresh.py` | no | the routine interval, **300 s** (`default_config.yml:1186`) |
| TUI fallback loop, which runs **whether or not the host is up** | `ace/tui/actions/_usage_refresh_fallback.py:33` | no | `max(refresh_seconds, 60)` |
| Refresh-panel `u`, Models-panel `u`, `sase usage refresh` | `ace/tui/actions/refresh_panel.py:149`, `main/usage_handler.py:107` | yes | on demand |
| A usage-limit disable (an agent hit its quota) | `refresh.py:253-277` | **yes** (`refresh.py:271`) | on event |

**Pipeline.**

1. **Admission.** Rust (`sase_core::provider_usage`) makes a per-provider due decision:
   `retry_after`, then `cooldown`, then `explicit`, then `backoff`, `marked_due`,
   `reset_passed`, and finally `cadence`. It then takes a single-flight lease with a
   75 s TTL, and concurrent callers **join or defer** instead of double-probing.
2. **Execution.** One durable proc per batch: `label="usage-refresh"`, no `service`
   block (`refresh.py:378-423`).
3. **Runner.** At most 3 concurrent probes, a 20 s deadline per provider and a 45 s
   batch deadline (`refresh.py:33-40`).
4. **Probes.** Each probe runs in an isolated `worker` subprocess, which spawns the
   vendor CLI:
   - claude: `claude -p /usage`, plus up to 4 capability and auth spawns;
   - codex: `app-server` `account/rateLimits/read`;
   - agy: `-p /usage`;
   - grok: ACP `_x.ai/billing`;
   - muse: `serve`, plus an echo turn that mints credentials.
5. **Store.** Errors keep the last-known-good windows. Failures back off as
   `cadence × 2^(n-1)`, capped at 30 min (`sase-core …/provider_usage/refresh.rs:146`).
   The explicit cooldown is **5 s** (`refresh.rs:17`). Claude `rate_limit_event`s from
   agent streams are recorded for free as partial `stream_event` observations.

**Constraints that shape the design (verified in code):**

- **Freshness is tied to the cadence.** A window counts as fresh up to 2× the cadence,
  stale up to 4×, and "unknown" beyond that (`sase-core …/provider_usage/mod.rs:501-514`).
  The cadence floor is 60 s (`mod.rs:69`).
- **Explicit requests bypass backoff but not `Retry-After`** (`refresh.rs:205-240`).
  Nothing ever sets `Retry-After`, though:
  - `refresh_runner._finish_job` never passes `retry_after_seconds`
    (`refresh_runner.py:190`), although the Rust wire accepts it;
  - limit events are explicit, so they skip backoff at exactly the moment a provider
    is throttling.
- **Where service-marked rows show up.** The Procs tab's default query is `-service`
  (`default_config.yml:306`), and the proc gear skips service rows. `sase proc list` has
  no service filter.
  - `sase proc kill` routes only **named daemon** rows to the service-stop path
    (`main/proc_handler.py:311-315`).
- **Proc retention.** `procs.history_limit: 100` bounds the *generic* finished rows
  (`default_config.yml:96`). Named, non-transient service procs get their own 20-row
  bucket per name (`sase-core …/procs/store.rs:34,537-600`). Today's `usage-refresh`
  rows fall into the generic bucket.
- **Config-declared service procs must be daemons.** sase-core rejects `mode: oneshot`
  in `service.procs` (`service/config.rs:1115`). Transient oneshots
  (`{mode: oneshot, source: transient}`) are the store behind the TUI's `!` background
  commands, with `bgcmd-slot:<n>` display slots (`procs/oneshot.py`).
- **Update restarts.** `sase update` restarts only the `scheduler` service proc
  (`main/update_restart.py:42`). Routines restart with it; a new daemon would not.
- **Jobs.** Routines are config-only (`axe.routines.<name>`). Job runs are recorded with
  bounded history under `~/.sase/axe/lumberjacks/<routine>/chops/<job>/`; athena keeps
  about 10 runs. Jobs are visible and manually runnable (`r`) as Services-tab nodes.

**Live state on athena, 2026-09-23 (my checks):**

- **Proc store:** 162 rows in `procs.jsonl`, 76 of them `usage-refresh` (69 from the
  scheduler, 7 from the TUI fallback) across about 6.3 h. That is 74% of the 103
  non-service rows.
- **Batches:** cld measured a median batch of 6.2 s (4.0–17.3 s), starting a median
  308 s apart. All five providers are `ok`.
- **Resident SASE Python processes:** host 59 MB, scheduler 33 MB, and eight routines
  at 35–126 MB each. A new resident process of any kind costs about 35–60 MB.
- **Claude's `account_generation` of 333 is historical, not ongoing churn.** Until
  commit `961a8cea2` (2026-09-13), the passive Claude path used a hashed auth context ID
  while the probe used `default`, so the two kept bumping the generation. Both now use
  `default`, and the current record and schedule are stable at generation 333. This
  retires cld's open risk that generation bumps silently wipe backoff.
  - One oddity: a stale generation-1 `claude` schedule row, last written 2026-09-20. It
    is harmless; see §9.

---

## 2. Critique of the plan

**What is right:**

- **Periodic, machine-level housekeeping does not belong on the Procs surface.** The
  data above shows the harm is concrete (evicted user history, gear noise, about 290
  rows a day), not just aesthetic.
- **Ownership by the service tree is the right model.** The Services tab already exists
  for exactly this kind of work: routines and jobs nested under the scheduler.

**What needs adjusting:**

1. **"Service proc" should mean "service-owned", not "a new daemon".** A dedicated
   daemon is one valid host, but the scheduler service proc already provides
   supervision, crash restarts, run history, timeouts, overrun metrics, a manual-run
   key and update restarts. The collector only has to stop *submitting procs* from its
   job. (§4 compares the options.)
2. **Hosting is not what limits frequency.** The job fires on the `checks` tick (300 s),
   so lowering `refresh_seconds` does nothing when the TUI is closed.
   - This corrects mus's claim that frequency "is just a knob".
   - A faster lane fixes that, but a **uniformly** faster timer is the wrong lever:
     - **Claude's usage endpoint punishes fast polling.** Public reports describe
       `/api/oauth/usage` returning sticky 429s to tools polling every 30–60 s. The
       429s persist for over 30 minutes, with `Retry-After` either `0` or missing
       ([#30930](https://github.com/anthropics/claude-code/issues/30930),
       [#31637](https://github.com/anthropics/claude-code/issues/31637)). Our probe runs
       `claude -p /usage`, which almost certainly uses the same endpoint (inferred).
       Today's 300 s works.
     - **Most windows do not move while idle.** Weekly windows drift slowly, and the
       5-hour windows move only while that provider is in use. Reset countdowns are
       computed locally from `resets_at`.
     - **Faster polling would blank the display.** Lowering the global
       `refresh_seconds` also tightens the freshness math, so a provider probed more
       slowly (Claude at its floor) would show as "unknown".
3. **"Don't overwhelm providers" is about per-provider rate, not concurrency.** The
   3-probe concurrency cap protects local CPU; each probe goes to a different vendor.
   Provider protection comes from single-flight leases (existing), polling floors,
   jitter, honoring `Retry-After`, and not letting explicit or limit-event paths bypass
   backoff (missing today).
4. **"Graceful and robust" is mostly probe and policy work,** and it applies to any
   host (§6 and §7).

---

## 3. Where the reports disagreed, and how I resolved it

| Question | cld | mus | gem | Resolution (evidence) |
|---|---|---|---|---|
| Migrate at all? | Yes, a builtin `usage` daemon | No; keep it, tune the knob, hide the rows | Yes, a `usage_collector` daemon, with a service-marker fix first | **Migrate periodic work into the service tree, as a scheduler routine that runs inline.** Hiding the rows alone leaves the history eviction in place. The daemon is deferred (§4). |
| Can frequency be raised without changes? | No; staleness math and Claude throttling | Yes, `refresh_seconds` | No; adaptive tiers | **No.** The job is tied to the 300 s `checks` tick, and the freshness math and Claude evidence apply as well. |
| Active cadence | 120 s when hot, with per-provider floors (Claude 300 s) | Toward 60 s after measuring | 60 s for all providers when active | **cld.** External 429 evidence rules out 60 s for Claude. Measure before lowering any floor. |
| Add a `service` marker to `usage-refresh` rows? | n/a | No; it would divert `proc kill` to service-stop | Yes, as a named builtin oneshot | **No, but mus's reason is wrong.** Only named *daemon* rows are diverted. The real problem: config rejects oneshot service procs, the transient-oneshot store belongs to `!` commands, and no Services-tab node would show these rows, so they would become invisible. It would be an unsupported proc shape. |
| How `u` reaches the collector | A store-backed request plus an mtime poll | Unchanged | A Unix socket, with an in-TUI thread fallback | **Unchanged (a user-triggered proc).** Admission already enforces every protection. If a daemon ever ships, use cld's store-backed request, never a socket or in-TUI probing. |
| Claude generation 333 | Untraced risk | n/a | n/a | **Resolved:** a historical, fixed context-ID ping-pong (§1). |
| Muse mint timeout blanks its windows | Bug | n/a | n/a | **A documented, accepted trade-off** (`muse.py:198` docstring). Worth revisiting (§7). |
| Anthropic ToS risk from polling | n/a | n/a | Asserted | **Unsupported by the evidence and unnecessary.** The documented risk is throttling. |

---

## 4. Hosting options compared

| Option | Periodic proc rows | User history eviction | New surface | Update restart | `u` path | Verdict |
|---|---|---|---|---|---|---|
| **A. Hide the rows** (label filter) | hidden | **still evicted** | small TUI/CLI filter | n/a | proc | Insufficient |
| **B. Service marker on the rows** (gem, phase 1) | hidden | fixed only if named | an unsupported proc shape; the rows become invisible everywhere | n/a | proc | Reject |
| **C. Dedicated `usage` scheduler routine, job runs inline** *(recommended)* | **gone** | **fixed** | config entry, an inline execution mode, store-based join waiting | **free** (scheduler restart) | proc (user-triggered) | **Recommend** |
| **D. Builtin `usage` daemon** (cld, gem) | gone | fixed | reserved builtin name in Rust and a pin move, argv mapping, `sase usage run`, status writer, stale-code exit, health-gated fallback, request channel | **must be added** | store request, no proc | Defer (§8.4) |
| **E. Loop inside the service host** | gone | fixed | host becomes a worker | n/a | — | Reject: the host must stay a thin supervisor |
| **F. Direct HTTP to vendor usage APIs** | — | — | credential handling | — | — | Reject (prior policy decision; 429 evidence) |

**Why C over D, in short:**

- **Both deliver the three goals.** The policy that makes refreshes faster and safer is
  shared.
- **What D adds is small:**
  - `u` about 1 s faster: it avoids one Python spawn, but a probe spawns ≥2 processes
    anyway.
  - An in-memory capability cache, which C can persist on disk instead.
  - Its own Services-tab node with a `status.json` summary. The job nodes and
    `emit_summary` already provide an equivalent.
  - No job spawn on every tick.
- **What D costs:**
  - a new daemon to keep healthy, with its own failure modes: wedging, stale code after
    a CLI update, crash loops;
  - a second, Python-side scheduler loop;
  - a fallback path gated on daemon health;
  - two-repo builtin plumbing.
- **Memory is a wash.** A dedicated routine and a daemon are each one resident Python
  process of about 35–60 MB.

**C's real costs:**

- One Python job spawn per 60 s tick, most of which find nothing due. That is about
  1,440 spawns a day, modest next to the probes' own spawns.
- The occasional overrun indicator if a batch approaches 60 s. The measured maximum is
  17 s.

---

## 5. Adjusted requirements (my changes, called out)

| # | Original | Adjusted | Why |
|---|---|---|---|
| R1 | Run the collector as a service proc | **Periodic collection is owned by the service tree:** a dedicated `usage` scheduler routine (60 s) whose job runs the admitted batch inline. The job moves out of `checks`. | Removes proc rows and history eviction, reusing the scheduler's supervision, history, metrics and update restarts. |
| R2 | *(implied)* `u` goes through the new service | **User-triggered refreshes stay procs.** `u` and the CLI keep today's explicit path; the toast reports receipt reasons (cooldown, retry-after, backoff) instead of always saying "already running" (`refresh_panel.py:26`). | Your own rule allows user-initiated procs, and Rust admission already enforces every protection. |
| R3 | Refresh more frequently | **Adaptive cadence:** idle stays at `refresh_seconds` (300 s). *Hot* providers use a new `active_refresh_seconds` (default 120 s). Hot means a recent agent launch on that provider, a window at warn level or above, a reset that just passed, or a recent limit event. **Plugin-declared floors** apply, with Claude at 300 s, and Claude takes live numbers from passive `rate_limit_event`s. | Refreshes where the numbers move, and respects the documented Claude throttling. |
| R4 | Don't overwhelm providers | **Per-provider guardrails in Rust:** floors; single-flight leases (existing); ±10% jitter on next-due (machines may share accounts); explicit cooldown **5 s → 60 s**; limit events **mark due** instead of forcing an explicit probe. | Speeding up must not open new ways to hammer a provider. The explicit and limit-event paths are the weakest points today. |
| R5 | Handle per-provider errors gracefully | **Error classes with distinct retry policies** (§6), including a new `rate_limited` reason, `Retry-After` passed through and clamped, last-known-good windows kept with their age shown, and collector health in the job summary and `sase usage list -v`. | A throttled or logged-out provider should look different from a flaky one, and should not be retried every cadence. |
| R6 | *(new)* | **Keep display freshness tied to the idle cadence:** never lower `refresh_seconds` just to probe faster. The hot cadence is a separate knob, and freshness uses `max(refresh_seconds, floor)`. | Otherwise faster polling blanks the header as "unknown". |
| R7 | *(new)* | **The TUI fallback loop only runs when the scheduler is not running** (`-x`, host down, disabled). | Today it races the scheduler unconditionally: 7 of the 76 rows came from it. |
| R8 | *(new)* | **Joins wait on the store, not on proc IDs.** `sase usage refresh` waits for `last_attempt_at ≥ requested` or a lease release when the owning operation is an inline job run. | `_wait_for_operation_ids` currently assumes every operation is a proc (`usage_handler.py:213-234`). |

---

## 6. Provider protection and error policy (host-independent; policy in `sase_core`)

| Class | Reason codes | Retry policy | User sees |
|---|---|---|---|
| Success | `ok`, `not_applicable` | next due at the provider's cadence (hot or idle, never below its floor), ±10% jitter | windows plus their age |
| Transient | `timeout`, `deadline_exceeded`, `probe_failed`, `parse_error`, `malformed_payload` | today's `max(cadence, floor) × 2^(n-1)` capped at 30 min, plus jitter | last-known-good windows, aging; a health note after 3 failures |
| **Rate-limited** *(new)* | `rate_limited` (429, "rate limit" or "too many requests" in CLI output or JSON-RPC errors) | `Retry-After` when > 0, clamped to [15 min, 6 h]; when 0 or missing, a 15 min floor that doubles up to 2 h. Explicit requests already respect `retry_after_until`. | "claude: rate-limited · retry ~14:05" |
| Auth | `unauthenticated` / logged out | today's backoff (30 min cap). Allow an explicit retry after the cooldown. | "run `claude auth login`" |
| Parked | `unsupported`, `not_installed`, `unsupported_cli_version` | no retry until the CLI binary's (path, mtime, size) changes | provider omitted, or "unsupported CLI vX" |
| Vendor drift | `vendor_drift` | parked for 1 h, with one attention notice per episode | "codex: CLI response changed" |

**Required plumbing:**

1. Record the reason code with each attempt. Today Rust sees only the outcome.
2. Pass `retry_after_seconds` through.
3. Give each collector a small 429/rate-limit classifier. agy currently turns a
   non-JSON rate-limit message into `parse_error`, so it must check stderr first.
4. Normalize `not_installed`. muse, agy and grok report it as `error`; claude and codex
   report `unsupported`.

**Deliberately cut from cld's list:**

- **The persisted hourly probe budget** is redundant with floors, leases, backoff and a
  60 s explicit cooldown, which already cap the worst case, and it adds more persisted
  state.
- **Global concurrency 3 → 2** protects CPU, not providers. Keep 3 and add a short
  start stagger if Node start-up spikes matter.

---

## 7. Defects to fix regardless of host

| # | Defect | Status | Fix |
|---|---|---|---|
| 1 | **Runner double-records at the batch deadline.** When no future completes before `work_deadline`, the loop breaks and leaving the `ThreadPoolExecutor` waits for running probes, which record their real observation and attempt. The runner then records a newer `deadline_exceeded` observation plus an error attempt for the same jobs (`refresh_runner.py:60-133`). A success can turn into backoff. | **Verified in code** | Only mark futures that are still not done after shutdown, or cancel and skip the ones that finished. |
| 2 | `Retry-After` is never passed through (`refresh_runner.py:190`) | **Verified** | See §6. |
| 3 | Limit events are explicit (`refresh.py:271`), so they bypass backoff, and the explicit cooldown is 5 s (`refresh.rs:17`) | **Verified** | Limit events: mark due only. Cooldown: 60 s. |
| 4 | **Probe re-run on `TypeError`.** Any `TypeError` raised *inside* a collector re-runs the whole probe as `method(context)` (`probe.py:117`). For Muse that means a second credential mint. | **Verified** | Inspect the signature once instead of catching `TypeError`. |
| 5 | **Process-kill gap.** `_terminate_process_tree` sends SIGKILL only if the root survives the SIGTERM grace period (`transport.py:274-292`). A grandchild that ignores SIGTERM outlives a root that exits. | **Verified by reading** | Snapshot the descendant process groups before SIGTERM, then SIGKILL the snapshot unconditionally. |
| 6 | **Worker env allowlist** drops `CLAUDE_CONFIG_DIR`, `HTTP(S)_PROXY`/`NO_PROXY` and `NODE_EXTRA_CA_CERTS` (`probe.py:37-61`). The probe can read a different Claude account, or fail behind a proxy. | **Verified by reading** | Allowlist them. None match the denied secret markers. |
| 7 | agy and grok `--version` timeouts are a hard 2.0 s (`agy.py:25`, `grok.py:26`), which risks spurious errors under load | Constant verified; gem's "observed on athena" not reproduced (all providers `ok` today) | A capability cache keyed by the binary's (path, mtime, size) removes most version spawns. Raise the timeout to 4 s. |
| 8 | A missed Muse mint returns an authoritative empty observation and blanks the Muse windows (`muse.py:198`) | **A documented trade-off** | Revisit: return `error/timeout` to keep the last-known-good windows. |
| 9 | Codex session closes on a failed best-effort `account/read` (cld; `transport.py:108`) | Not re-verified | Check it, and keep best-effort calls from poisoning the session. |
| 10 | The `u` toast says "already running" for every deferral (`refresh_panel.py:26`) | **Verified** | Render the receipt reason. |

---

## 8. Recommended solution

### 8.1 Phase 1: host-independent hardening (ship first; useful whatever the host)

- **sase-core (`provider_usage`):**
  - reason-aware backoff classes, the `rate_limited` reason and `Retry-After`
    clamping;
  - explicit cooldown of 60 s;
  - per-provider floors and ±10% jitter in the due evaluation;
  - freshness computed against `max(refresh_seconds, floor)`.
- **sase:**
  - fix defects 1–7 and 10;
  - collector rate-limit classifiers;
  - limit events mark due;
  - pass the reason code and `retry_after` into attempts.
- **Floors** come from `llm_usage_capabilities()`, adding `min_probe_interval_seconds`,
  which means widening `_registry_metadata._usage_capabilities`. Starting values:
  claude 300, muse 180, agy 120, grok 120, codex 60–120.
- **Process:** move the `sase-core-revision.txt` pin once, per the Rust-boundary rule.

### 8.2 Phase 2: move periodic collection into the service tree

```yaml
axe:
  routines:
    usage:
      description: |-
        Collect subscription usage windows for eligible providers

        Runs every minute. Rust due evaluation (floors, hot cadence, backoff,
        Retry-After) decides which providers are actually probed, so most ticks
        are no-ops.
      interval: 60
      job_timeout: "90s"
      jobs:
        - name: usage_refresh
          script: sase_job_usage_refresh
```

- **Remove `usage_refresh` from `checks`.**
- **The job runs the batch inline.** It admits due providers, then calls the existing
  batch runner (`_run_admitted_refresh`: isolated workers, deadlines, lease release)
  in-process, and emits a per-provider summary.
  - Example summary: `claude ok · codex ok · grok backoff→12m`.
  - Add an execution mode to `submit_usage_refresh`, such as `execution="inline"`, so
    admission, receipts and lease-release-on-failure stay shared.
- **Joiners wait on the store (R8).** A `u` press that joins an inline-owned provider
  still gets a correct receipt, and the CLI waits on the store instead of a proc.
- **TUI fallback loop:** idle while `is_axe_running()`; otherwise today's due-only proc
  path (R7).
- **`u` and `sase usage refresh`:** unchanged explicit proc path, with receipt-reason
  toasts.
- **Result:** no periodic proc rows, user proc history protected, collector status
  visible and manually runnable on the Services tab, and code refreshed by
  `sase update`.
- **Process:** read the `tui` reference memory before touching TUI code. Update
  `docs/axe.md` and the usage docs in `docs/configuration.md`.

### 8.3 Phase 3: make faster refresh cheap and targeted

- **`active_refresh_seconds`** (default 120 s) for hot providers.
- **Hot hints:** the provider launch path writes a best-effort
  `mark_provider_usage_hot(provider, until=now+15m)` to the Rust store. Warn-level
  windows, just-passed resets and recent limit events also count as hot.
- **Claude passive-first:** a fresh `stream_event` covering Claude's known windows
  stretches its probe interval back to idle.
- **Capability cache:** CLI version and help results, keyed by the binary's (path,
  mtime, size) and handed to workers. That takes Claude from 5 Node spawns per probe to
  2.
- **Measure before tuning:** collect a week of classified attempt logs (429 counts,
  durations) before lowering any floor.

### 8.4 When to promote to a dedicated `usage` daemon instead (reopen conditions)

Adopt cld's daemon design, and not gem's socket or in-TUI variant, if any of these holds:

1. **You want long-lived vendor connections:** `codex app-server`
   `account/rateLimits/updated` pushes, or muse `usage/changed`. A routine job cannot
   hold those.
2. **User-triggered refreshes should also stop producing proc rows.**
3. **The `usage` lane regularly overruns,** or its per-tick spawn cost shows up in
   athena's memory or CPU budget.

The daemon's shape would be:

- builtin `usage`, run as `sase usage run`;
- store-backed `request_refresh` receipts, picked up by a 1 s mtime poll (no new IPC);
- a `$SASE_SERVICE_PROC_STATUS` heartbeat;
- exit 75 when the code fingerprint changes, plus `sase update` restarting the host or
  all builtins;
- the proc path as a health-gated fallback (heartbeat older than 90 s).

Phases 1 and 3 carry over unchanged.

### 8.5 Explicit non-goals

- No direct-HTTP usage calls. That is a prior policy decision, and the 429 evidence
  backs it.
- No adding, averaging or merging of overlapping windows (the usage-window glossary).
- No automatic routing or disable decisions from these numbers in this work.
- No cross-machine federation of usage state. Document the per-machine opt-out
  (`usage_metrics.providers.claude: false` in a machine overlay) for hosts that share an
  account.

---

## 9. Risks and open questions

- **Claude throttling in practice is unmeasured.** 429s are hidden inside `probe_failed`
  and `parse_error` today, so Phase 1's classification produces the first real data.
  Tune the floors from it, not from third-party anecdotes.
- **Routine overrun.** A 60 s lane with a 45 s batch deadline can occasionally overrun.
  The measured maximum is 17 s, and the overrun indicator makes it visible. If it
  becomes chronic, raise the interval or promote to the daemon (§8.4).
- **Token-refresh races.** Every probe except grok can make its vendor CLI refresh or
  mint tokens while agents are running (inferred). Hot-only, passive-first polling keeps
  this exposure well below a globally faster timer.
- **Stale generation-1 `claude` schedule row.** It was last written 2026-09-20, after
  the context-ID fix, while the live record is at generation 333. The writer was not
  traced. It is harmless, but the store should drop schedules for superseded
  generations, and a one-off trace is worth doing.
- **Multi-machine load.** athena, apollo and mac each poll the accounts they are logged
  into. Floors and jitter keep that safe at the defaults.

---

## Sources

**Code:**

- `src/sase/llm_provider/usage/{refresh,refresh_runner,probe,transport,muse,claude,agy,grok}.py`
- `src/sase/scripts/sase_chop_usage_refresh.py`
- `src/sase/ace/tui/actions/{refresh_panel,_usage_refresh_fallback}.py`
- `src/sase/ace/tui/_proc_observer_models.py`, `src/sase/ace/tui/_proc_query.py`
- `src/sase/main/{proc_handler,usage_handler,update_restart}.py`
- `src/sase/procs/{oneshot,service_meta,store}.py`
- `src/sase/default_config.yml`, `docs/axe.md`, `docs/configuration.md`
- linked `sase-core`: `crates/sase_core/src/provider_usage/{refresh,store,mod}.rs`,
  `crates/sase_core/src/procs/store.rs`, `crates/sase_core/src/service/config.rs`

**Live state on athena:** `~/.sase/procs/procs.jsonl`, `~/.sase/llm_provider_usage.json`,
`~/.sase/axe/lumberjacks/checks/chops/usage_refresh/`, and `ps` RSS.

**Git:** `961a8cea2` (Claude passive context-ID fix, 2026-09-13).

**Glossary:** Oneshot Service Proc, Service Proc, Proc, Routine, Sase Service, Usage
Window.

**Constituent reports:** `usage_window_collector_hosting__{cld,mus,gem}.md`.

**External:**

- [anthropics/claude-code #30930](https://github.com/anthropics/claude-code/issues/30930):
  persistent 429 with `retry-after: 0` for 30–60 s pollers.
- [anthropics/claude-code #31637](https://github.com/anthropics/claude-code/issues/31637):
  sticky 429 at 30–60 s polling, lasting 30+ min, with no `Retry-After`.
- Further 429 and back-off reports cited in `__cld`: #31021, TokenTracker #608,
  AgentDesk PR #5727, agentdock #116.
