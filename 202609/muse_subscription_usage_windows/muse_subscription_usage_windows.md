# Muse Code Subscription Usage Windows in SASE — Consolidated

**Date:** 2026-09-20 · **Lead researcher** (consolidating reports A and B plus independent verification)
**Build under test:** `Muse Code 1.3.0 (1.3.0-R3401.1)`, macOS arm64 · MSP schema v1,
fingerprint `sha256:7469c9e352e67def4a59df7e439984d7194fa351e1c8b7abb34060fd977ced81`
**Repo state:** `sase` @ `307872298`, `sase-core` linked checkout

---

## 1. Bottom line

Do not scrape `https://dev.meta.ai/usage`. Muse ships a first-party, stable-surface, local
MSP method — `usage/read` — that returns exactly the two windows you want, for free.

Both prior reports found that method. They then split on the question that decides the whole
design, **"what makes the host produce a number?"**, and **both got it partly wrong**:

- **A** recommended a cold probe: spawn `muse serve`, handshake, `usage/read`. A never
  verified what populates the host and shipped the gap as an open item.
  **That probe is empty forever** — B refuted it and I reproduced the refutation.
- **B** proved the observation is process-local and turn-gated, and concluded that any probe
  must mint a **real model turn** — ~288 turns/day at the default cadence — and therefore
  recommended deferring collection to a large MSP run-transport rewrite.
  **That cost model is wrong.**

**New finding (mine, reproduced 5/5 on the clean sequence):** the host learns its usage from
the **credential mint**, not from a model frame, and `turn/start` triggers the mint
**regardless of which provider the session selected**. `session/start` accepts a
`providerId`, and `"echo"` is Muse's local echo provider — an echo session is created with
`modelId: null` and emits no `session/tokenUsage`. So:

```
muse serve --no-session-log --disable-shell
  → initialize → initialized
  → session/start {providerId: "echo"}        # modelId: null — no model configured
  → turn/start   {input: [{type:"text",text:"hi"}], reasoningEffort:"none"}
  → usage/changed fires ~2.5 s later          → usage/read returns both windows
```

**2.4–2.9 s after `turn/start`; 2.6–3.5 s total from process spawn; zero model call; zero
tokens; zero budget.** That is a genuinely free, schedulable probe, comfortably inside the
existing 20 s per-provider refresh deadline.

This rescues the simple design. The recommendation (§7) is **B's Phase 1 normalizer plus a
scheduled echo-mint probe** — arriving at roughly A's shape, but only because of a mechanism
neither researcher found. B's Phase 3 MSP run-transport rewrite becomes *optional*, justified
by its own token-accounting payoff rather than by usage windows.

---

## 2. What Muse exposes (agreed by both reports, independently re-verified)

`muse schema generate-json-schema --out DIR` emits the wire contract offline from the binary.
`usage/read` (request) and `usage/changed` (notification) are on the **non-experimental**
surface, are not in `capabilities.grantable`, and need no capability negotiation.

```
usage/read  → UsageReadResult = {usage?: SubscriptionUsage}
usage/changed → SubscriptionUsage + emittedAtMs
```

Verified payload (mine, 2026-09-20T16:20:55Z):

```json
{"window": {"usedPercent": 0, "windowDurationMins": 300, "resetsAtMs": 1789935797000},
 "weekly": {"usedPercent": 0, "resetsAtMs": 1789948800000},
 "tier": "27681631238169137",
 "observedAtMs": 1789921255705}
```

Contract details that matter downstream:

- `usage/read` is documented as answering *"without a model call"*; measured at **~1 ms**.
- `SubscriptionUsage.required = [observedAtMs, tier, weekly, window]` — **when `usage` is
  present, both windows are always present**. There is no partial payload to model.
- `usedPercent` is *"an integer ≥ 0, verbatim from the provider — over-quota values above
  100 are valid"*. Do not clamp.
- `windowDurationMins` is required on `window` (observed `300` — literally the 5-hour block)
  and **deliberately absent on `weekly`**: *"same semantics … without a duration"*.
- `UsageReadResult` omits `usage` — *"omitted, never null, when the host has observed
  nothing … truthful absence, no 'nothing observed' error"*.
- `usage/changed` is **edge-triggered on value change**, not a heartbeat, but *"the
  absent-to-present first observation emits"* — which is what makes it usable as the probe's
  completion signal.
- `observedAtMs` is *"when the host RECEIVED this observation (**frame arrival or mint
  request-send**)"*. That parenthetical is the documented hook the echo-mint probe rides on.

**Handshake trap (B's find, worth keeping):** `initialize` must be followed by the
`initialized` **notification** (no id, no params) or every later call fails `-32600
{"kind":"notInitialized"}`. `clientInfo` is required and `clientInfo.name` must match
`^[a-z0-9_]+$` (`"sase"` works). Handshake measured at 0.29–0.39 s.

`initialize` returns `serverInfo.version`, `museHome`, `grantedCapabilities`,
`experimentalApi`, `sessionDurability`, and `schema.{version,fingerprint}` — but **no auth
state**, so the collector cannot distinguish logged-out from unobserved at handshake time.

---

## 3. The turn-gating constraint (B correct, A wrong) — reproduced

A cold host is empty and stays empty. My run, on a machine that had already completed several
real Muse turns on this account today:

| Step | `usage/read` |
|---|---|
| cold, immediately after handshake | `{}` |
| after `model/list` (succeeded) | `{}` |
| after `session/list` (succeeded) | `{}` |
| after `session/start` with the **default `meta`** provider, no turn | `{}` |
| after 20 s idle | `{}`, **0** `usage/changed` |

So both of A's structural assumptions fail: there is **no cross-process cache** (other
processes' turns do not help), and an idle host does **not** self-populate. A's decision tree
("if an idle host emits `usage/changed` … ship as designed") resolves to its unfavourable
branch. A's cold-probe collector would return a neutral absent status on every tick, forever —
a feature that looks healthy and shows nothing.

Also confirmed from both reports, so implementation does not retry them: there is no `muse
usage` subcommand; `muse exec --json` stream records carry no subscription usage; and the
durable `session.jsonl` log carries none either (B enumerated 60+ record kinds across 5 local
sessions — `resource_usage_sampled` is OS-level RSS/CPU telemetry, not capacity). The
session-log trick `_muse_session_usage.py` uses for *token* counts has no subscription
equivalent.

---

## 4. The mint is the trigger, and the mint is free (new)

`session/start` takes an optional `providerId`. Selecting `"echo"` — Muse's documented
startup provider mode (`--provider <MODE>  Startup provider: echo or meta`) — yields a
session with `providerId: "echo"`, `modelId: null`. Sending `turn/start` into that session
still causes the host to mint, and the mint response carries the subscription stamp.

| Trial | Sequence | Result |
|---|---|---|
| 1 | handshake → echo session → turn | populated |
| 2 | handshake → echo session → turn | populated, **2.07 s** after `turn/start` |
| 3 | handshake → echo session → **failed `view/subscribe` (-32601)** → turn | **empty after 12 s** |
| 4–6 | handshake → echo session → turn (×3, fresh host each) | populated in **2.88 / 2.85 / 2.43 s** |

Every trial running the minimal sequence populated (5/5). Trial 3 is the one non-reproduction
and it interleaved an unknown-method error before `turn/start` without checking the turn ack,
so it is most likely a failed turn rather than a suppressed mint — but it is reported here
rather than dropped, and it argues for keeping the probe sequence minimal and never issuing
speculative methods on the probe connection.

Evidence the echo turn is genuinely free: the session has **no model** (`modelId: null`);
**zero `session/tokenUsage`** notifications were emitted for it; the echo provider answers
locally by construction; and the schema legitimises the mint (an auth exchange) as an
independent source of the observation.

**Residual risk, stated plainly:** "an echo turn mints" is *observed* behaviour, not a
documented contract. If a future Muse defers the mint until provider dispatch, the probe
degrades to `{}` → absent status. That is a **safe failure** — absence, never a wrong number —
but it must be handled as absence and never as `0%` (§5) and never as `error` (§6.2).
The probe must also **assert** the started session reports `providerId == "echo"` and
`modelId == null` **before** sending `turn/start`, and abort otherwise. Without that guard, a
future Muse that ignores or rejects `providerId: "echo"` would silently spend a real turn
every 5 minutes — exactly B's disaster scenario, arrived at by accident.

### Why not the alternatives

| Approach | Marginal cost | Verdict |
|---|---|---|
| **Echo-mint probe** (recommended) | **zero**, ~2.7 s | ✓ |
| Cold `usage/read`, no turn (A's plan) | zero | ✗ empty forever (§3) |
| Probe that mints a **real** turn (B's option A) | 1 model turn/tick, ~288/day | ✗ self-defeating, and unnecessary |
| Scrape `dev.meta.ai/usage` | HTTP | ✗ see below |
| Direct `api.meta.ai/v1` with a minted key | HTTP | ✗ re-implements the mint; internal contract |
| Passive `usage/changed` on SASE's own Muse runs | zero | ✓ correct but large; now optional (§7 Phase 3) |

**On scraping the web page** — the argument both reports make, with B's sharper points: it
needs a live Meta **web session cookie**, a different credential from the device-code OAuth
token Muse keeps in the macOS Keychain; SASE's `UsageProbeContext.auth_context` is documented
as *"must not carry secrets, account ids, emails, tokens, or filesystem credential paths"*;
and `probe.py` deliberately strips any env var matching `KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH`
from the worker, so threading a cookie through would mean punching a hole in that allowlist.
It is also an unversioned HTML surface, versus a content-hashed schema fingerprint. The page
and `usage/read` are the same numbers; read them locally.

---

## 5. Reset semantics (new — settles B's open question #1)

Both windows report **anchored, stable** reset stamps, not rolling `now + duration`. B sampled
at 15:39Z; I sampled at 16:20Z and 16:21Z; **all samples carry identical stamps**:

| | value | UTC | notes |
|---|---|---|---|
| `window.resetsAtMs` | 1789935797000 | 2026-09-20T20:23:17Z | identical across samples 42 min apart |
| derived window start | — | 2026-09-20T15:23:17Z | `reset − 300 min`, exact |
| `weekly.resetsAtMs` | 1789948800000 | 2026-09-21T00:00:00Z | identical across samples |

- `window.resetsAtMs % 18000s = 15797` → the 5-hour block is **anchored to first use**, not to
  an epoch-aligned grid. Because the vendor reports the duration, `period_start = resets_at −
  duration_seconds` is **exact** and safe to derive.
- `weekly.resetsAtMs % 86400s = 0` (exact UTC midnight) but `% 604800s = 345600` (not a 7-day
  epoch grid), and it sat only **7.65 h** away. Two independent samples with the identical
  stamp rule out a rolling `now + 7d`.

**Therefore: never set `duration_seconds = 604800` on the weekly window.** B's §6.3 caution is
correct and now has a second confirming sample. The vendor omits the weekly duration on
purpose; fabricating it would write a wrong number into the store and, per §6.1 below, would
also be the wrong way to get it displayed.

---

## 6. Mapping onto SASE (claims re-verified in the working tree)

One `SubscriptionUsage` → one observation with two windows:

| SASE field | 5-hour window | Weekly window |
|---|---|---|
| `key` | `"session"` | `"weekly"` |
| `label` | `"Muse 5-hour session"` | `"Muse weekly all models"` |
| `used_percent` | `window.usedPercent` | `weekly.usedPercent` |
| `resets_at` | `window.resetsAtMs / 1000.0` | `weekly.resetsAtMs / 1000.0` |
| `duration_seconds` | `windowDurationMins * 60.0` → `18000.0` | **`None`** (§5) |
| `period_start` | `resets_at − duration_seconds` (exact, §5) | `None` |
| `applicability` | `{"kind": "account"}` | `{"kind": "account"}` |
| `observed_at` | `observedAtMs / 1000.0` | same |
| `source` | `"probe"` | same |
| `vendor_state` | `"allowed"` | same |

Envelope: `outcome: "ok"`, `completeness: "complete"`, `account_mode: "subscription"`,
`plan: None` (§6.3), `authoritative_empty: false`.

### 6.1 Use `Account` applicability — and Muse needs a `is_weekly_window` arm

Verified in `sase-core/crates/sase_core/src/provider_usage/indicator.rs`:

- `is_all_model_scope()` (line 844) returns `true` unconditionally for
  `UsageApplicabilityWire::Account`; the `Product` arm is hard-coded to `provider == "claude"
  && product == "claude" && model_ids.is_empty() && key in {session, weekly}`. A Muse
  `Product`-scoped window would be **silently excluded** from all-model classification.
  `Account` is also semantically right: Muse reports one account-wide pair with no per-model
  split. Grok already uses `Account`.
- `is_weekly_window()` (line 811) resolves duration first — `Some(≈604800)` → true,
  `Some(other)` → false — and otherwise falls through to an allowlist: `claude` with key
  `weekly`/`weekly:*` **and** Claude product scope, or `grok` with key `included_weekly` and
  `Account`. Muse reports **no** weekly duration, so the fallthrough applies and Muse is not
  matched.

Consequence, confirmed against `src/sase/default_config.yml:1534-1544`
(`indicator.weekly_all: always`, `indicator.default.below_remaining_percent: 20`): the Muse
weekly window would **miss the `weekly_all: always` policy** and fall back to the default —
invisible until you are already 80 % through the week. Almost certainly not what you want.

**Fix: add the Muse arm in Rust** (`provider == "muse" && key == "weekly" && matches!(…,
Account)`). It asserts nothing false about duration, and it is squarely core classification
logic per the `rust_core_backend_boundary` core memory. Do **not** take the shortcut of
fabricating `duration_seconds = 604800` (§5).

B also flags, correctly, that `indicator.rs` now carries three `provider == "…"` string
allowlists and that every new provider touches them. Worth a follow-up task; **not** a
prerequisite for this work.

### 6.2 Absence must not become an error

`usage/read → {}` is the documented truthful-absence case. Map it to a windowless
non-error observation (`outcome: "ok"` with `authoritative_empty: true`, else
`not_applicable` with a `muse_usage_not_yet_observed` diagnostic). If it maps to `error`, the
collector-health counter (`USAGE_COLLECTOR_FAILING_THRESHOLD = 3`) marks Muse broken after
three such ticks. Under no circumstance render absence as `0 %` — a point both reports make
and the single most important display rule here.

### 6.3 `tier` is an opaque account id — keep `plan: None`

Observed `"tier": "27681631238169137"`, identical across all my samples: a 17-digit id, not
`"Pro"`. The binary carries the diagnostic `subscription_stamp_missing_tier_name: active stamp
folded without a display name`, implying the display name is a separate, sometimes-absent
thing. Mapping it to `observation.plan` would render "Plan 27681631238169137" **and** persist a
plausibly account-scoped identifier into the machine-local store — inconsistent with SASE's own
`auth_context` no-account-ids posture. Leave `plan: None`; if you want tier-change detection
(it should bump `account_generation`), hash it into the opaque auth fingerprint instead.

### 6.4 Auto-enrollment is real — and now it is what we want

Verified at `src/sase/llm_provider/usage/refresh.py:298`: `eligible_usage_providers()` skips
any provider whose `usage_capabilities.probe is not True`, then requires CLI readiness and
either a model-alias reference or an explicit enable. So `{"probe": True}` **does** enrol Muse
in the background loop at the global cadence — B's landmine is accurately described.

With a free probe that landmine is defused: `{"probe": True, "passive_events": False}` is the
correct declaration, and the 300 s default cadence costs ~2.7 s of wall clock and nothing else.

Also confirmed (`usage/config.py:34,37`): there is a single global `refresh_seconds` and
`providers: Mapping[str, bool]` is on/off only — **no per-provider cadence override**. Not a
blocker now, but if the echo-mint path ever regresses to a paid probe, a
`providers.<name>.refresh_seconds` override becomes a prerequisite, not a nicety.

### 6.5 Probe hygiene

`MUSE_NO_AUTO_UPDATE=1` (the `~/.local/bin/muse` launcher self-updates the real binary hourly
from `lookaside.facebook.com`; `src/sase/llm_provider/muse.py:64,277,476` already sets this for
runs); `--no-session-log` for memory-only sessions (`initialize` confirms `sessionDurability:
"ephemeral"`); `--disable-shell` and the sandbox defaults; scratch cwd and killable child, both
already provided by `probe.py` / `spawn_killable_process`; and the bounded `JsonLineSession`
transport, which is already exactly an MSP client — Grok's ACP probe uses it unchanged.

### 6.6 Drift detection is cheap here

`InitializeResult.schema.fingerprint` is reproducible offline via `muse schema
generate-json-schema` and can be compared **before** parsing — a stronger signal than
`classify_probe_failure()`'s `-32601` sniffing (which already maps `-32600/-32601/-32602` to
`vendor_drift`). Treat a mismatch as a **warning and proceed**: the schema itself says *"A
mismatch is a warning condition, not an error"*, and the launcher's hourly self-update means
the fingerprint will churn across releases. A hard pin would break on every Muse update.

### 6.7 Current SASE state

Verified: `claude.py`, `codex.py`, `grok.py` each implement both usage hooks; `muse.py`
implements **neither** — Muse is the only provider without them. The `♾️` Muse badge already
exists (`src/sase/integrations/provider_badges.py:17`). Everything downstream — store,
staleness, backoff, `sase usage list`, the TUI header indicator, doctor — is provider-generic.
**The only genuinely new code is a Muse collector and a Muse normalizer.**

---

## 7. Recommended solution

### Phase 1 — Rust normalizer + weekly classification (`sase-core`)

Add `crates/sase_core/src/provider_usage/muse.rs` with
`normalize_muse_subscription_usage(request)`, modelled on `grok.rs::normalize_grok_billing`
(same request-wire shape, `schema_version` check, `validate_usage_observation`). Ms→s
conversion, `windowDurationMins * 60`, `period_start` derivation, the absent-`usage` case, and
plan-label policy live **here**, not in Python — the Grok normalizer's own header claims
*"percentage, period, completeness, and plan-label decisions"* for core, and the
`rust_core_backend_boundary` core memory is unambiguous. Export from `mod.rs`, bind in
`sase_core_py`. Extend `is_weekly_window()` with the Muse arm (§6.1). Fixtures: the real
payload in §2, `usedPercent > 100`, and absent-`usage`.

### Phase 2 — Free scheduled echo-mint probe (Python)

Add `src/sase/llm_provider/usage/muse.py` with `collect_muse_usage(context)` driving
`muse serve --no-session-log --disable-shell` over the existing `JsonLineSession`:

1. `initialize` (`clientInfo.name: "sase"`) → **`initialized` notification** → optional
   fingerprint warning check.
2. `session/start` with `commandId` (**UUIDv7 — the server rejects UUIDv4**),
   `workspaceRoot` = scratch cwd, `providerId: "echo"`.
3. **Guard:** assert the returned session reports `providerId == "echo"` and `modelId == null`.
   Abort to a `vendor_drift` status otherwise — never send a turn into a model-backed session.
4. `turn/start` with `reasoningEffort: "none"` and a single minimal text part.
5. Await `usage/changed` (fires ~2.5 s) with a `usage/read` poll fallback and a deadline well
   inside `USAGE_REFRESH_PROVIDER_DEADLINE_SECONDS` (20 s); kill the child.
6. Wrap in `_strategy.ProbeStrategy` so `-32601`/`-32602` classify as `vendor_drift`, and map
   `{}` to the absent status of §6.2 rather than an error.

Declare `MuseProvider.llm_usage_capabilities() → {"probe": True, "passive_events": False}` and
let the existing refresh proc, `sase usage list/refresh`, header pill, Models panel, and doctor
pick Muse up with no display-side changes. Document the probe's mechanism and its zero cost in
`docs/configuration.md` in the same change. Per `sase_flags.md`, the user-facing on/off is a
**config field** (`llm_provider.usage_metrics.providers.muse`), already generic — **not** a
feature flag; a `beta` flag is only warranted if this lands as a multi-phase epic whose Phase 1
would expose a half-finished surface.

**After Phase 2 the feature is done**: both windows visible, on cadence, at no budget cost.

### Phase 3 — Optional: passive collection via an MSP run transport

Move `MuseProvider.invoke` from `muse exec --json` to `muse serve` + MSP and record
`usage/changed` through `record_passive_usage_observation()` (`source: "stream_event"`). With
the free probe in hand this is **no longer needed for usage windows** — judge it on its own
merits, which are real: MSP's `session/tokenUsage` gives server-derived, counted-once token
counts and would retire `_muse_session_usage.py`'s session-log glob (a documented filesystem
race and double-counting hazard), and `session/contextUsage` adds context pressure SASE has no
Muse equivalent for. It is an **epic**, not a task: MSP is a full session host (approvals,
view subscription/paging, turn lifecycle) and its `approval/request` flow must be reconciled
with SASE's `--disable-sandbox` posture and `muse.py::_safety_args`.

### Sequencing

**Do Phase 1 + Phase 2.** They are small, they deliver exactly what you asked for, and none of
the domain, store, or display work is thrown away if Phase 3 ever happens.

---

## 8. Confidence and open items

**Verified on this machine, this build:** the MSP handshake including the `initialized`
requirement and the UUIDv7 `commandId` requirement; `usage/read`/`usage/changed` on the
non-experimental surface with a matching fingerprint; the exact payload shape and required
members; cold/`model/list`/`session/list`/`session/start(meta)`/idle all returning `{}` with no
`usage/changed`; the echo-mint path populating in 2.4–2.9 s across 5/5 clean trials; echo
sessions having `modelId: null` and emitting no `session/tokenUsage`; anchored reset stamps
identical across samples 42 min apart; `eligible_usage_providers`'s `probe is True` gate; the
single global `refresh_seconds` and boolean-only per-provider map; both `indicator.rs`
allowlists; Muse being the only provider without usage hooks; the `♾️` badge.

**Open:**

1. **Echo-mint durability.** Undocumented incidental behaviour (§4). Mitigated by the
   `providerId`/`modelId` guard and by absence-not-error handling. Worth a comment in the
   collector naming the assumption so a future Muse bump is diagnosable.
2. **Logged-out and API-key behaviour.** `initialize` carries no auth state, so logged-out
   almost certainly presents as a failed mint → permanent `{}`. Not verifiable without logging
   out (destructive). Map transport/auth errors to the existing `unauthenticated`/`logged_out`
   / `api_mode` outcomes at implementation time rather than guessing now.
3. **Weekly window duration.** Two samples agree on a UTC-midnight-aligned stamp (§5) but do
   not establish the interval. Sample `weekly.resetsAtMs` across several days before anyone
   considers hard-coding a duration; the §6.1 allowlist arm makes that unnecessary.
4. **`usedPercent` granularity.** Integer-valued, observed at 0 throughout. Whether it moves in
   coarse steps is unknown and affects how useful a 300 s cadence really is — but the cadence
   is free, so this is a curiosity, not a risk.
5. **Real limit wording.** `muse.py::llm_default_usage_limit_config` carries admittedly
   unverified patterns (`"usage limit reached"`, `"quota exceeded"`, `"insufficient_quota"`).
   Tighten from captured Muse limit output as a follow-up; not a blocker.
6. **Render check.** Validate a two-window Muse entry at 60/80/140 columns in both themes, and
   confirm attention-ordering treats it like the other providers.

**Research cost:** one real Meta turn (a ~4-token prompt, spent before the echo path was found)
plus six free echo turns. Reported `usedPercent` was 0 for both windows throughout, so no
increment was observable.

---

## 9. Provenance

- Reports A (`muse_subscription_usage_windows__a.md`) and B
  (`muse_subscription_usage_windows__b.md`) read through `sase artifact read`.
- Independent verification this turn: `muse schema generate-json-schema` (fingerprint matched
  both reports); six live `muse serve` sessions covering cold reads, non-turn methods, idle
  watch, `session/start(meta)` without a turn, and the echo-mint sequence; timestamp decoding
  cross-checked against B's recorded sample.
- SASE-side claims checked in the working tree (`refresh.py`, `usage/config.py`,
  `default_config.yml`, `muse.py`, `provider_badges.py`) and in the `sase-core` linked checkout
  opened via `/sase_repo` (`provider_usage/indicator.rs`, `provider_usage/grok.rs`).
- Glossary term `usage-window` read via `/sase_memory_read`; its rule that overlapping windows
  are independent and must never be merged or averaged is what makes the two Muse blocks two
  windows on one observation rather than one blended number.
