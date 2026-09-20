# Muse Code Usage Windows in SASE — Researcher B

**Date:** 2026-09-20
**Researcher:** B (independent; peer researcher A is investigating the same request separately)
**Muse build under test:** `Muse Code 1.3.0 (1.3.0-R3401.1)`, macOS arm64
**Repo state:** `sase` @ `e99bd48ac`, `sase-core` @ `39602c950`

---

## 1. TL;DR

**You do not need to scrape `https://dev.meta.ai/usage`.** Muse Code ships a first-party,
stable-surface, local API that returns exactly the two windows you want:

```
muse serve  →  MSP v1 over stdio  →  usage/read
→ {"usage": {"window":  {"usedPercent": 0, "windowDurationMins": 300, "resetsAtMs": ...},
             "weekly":  {"usedPercent": 0, "resetsAtMs": ...},
             "tier": "<opaque id>", "observedAtMs": ...}}
```

`windowDurationMins: 300` is literally the 5-hour window; `weekly` is the rolling weekly
block. I verified this live against the installed binary (§2.3).

**But there is one hard constraint that dominates the whole design:** the Muse host only
knows its usage after *it* has made a real provider request, and that knowledge is
**process-local**. A freshly spawned `muse serve` returns `{}` — truthful absence — and
stays empty forever unless that same process runs a turn. I proved this three ways (§2.4).

So the question is not "how do we read Muse usage" (that part is easy and already
designed for by SASE's `llm_usage_probe` hook). The question is **"where do we get a Muse
host that has already paid for a turn?"** — and the only free answer is *the Muse agent
runs SASE already performs*.

**Recommendation (detail in §7):** land the domain mapping + Rust normalizer now, expose
usage through the existing store/indicator/`sase usage` surfaces, and feed it from a
**passive MSP observer attached to SASE's own Muse runs** rather than from a scheduled
out-of-band probe. Ship it in three phases so that Phase 1 is useful on its own. Do **not**
declare `{"probe": True}` on `MuseProvider` in Phase 1 — that one line silently enrolls
Muse in the 300-second background refresh loop and would mint a real model turn every five
minutes to measure the budget it is spending (§5.1).

---

## 2. What Muse Code actually exposes

### 2.1 The transport: MSP over `muse serve`

`muse serve` "serves an MSP session host over stdio" — newline-delimited JSON-RPC 2.0.
This is structurally identical to how SASE already probes Grok (`grok ... agent stdio`
speaking ACP, driven by `JsonLineSession` in `src/sase/llm_provider/usage/transport.py`).

The handshake has a trap worth writing down, because I hit it:

1. → `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"sase","version":"..."}}}`
   - `clientInfo.name` must match `^[a-z0-9_]+$`. `clientInfo` is required; `capabilities` is optional.
2. ← `InitializeResult` (`serverInfo`, `schema.version`, `schema.fingerprint`, `museHome`,
   `grantedCapabilities`, `experimentalApi`, `userAgent`, `sessionDurability`)
3. → `{"jsonrpc":"2.0","method":"initialized"}` — **a notification, no id, no params.**

**Skipping step 3 makes every subsequent call fail** with
`-32600 / {"kind":"notInitialized"}` even though `initialize` itself succeeded. I lost a
cycle to exactly this. Any SASE collector must send `initialized` before `usage/read`.

Measured handshake cost: **~0.39 s** wall clock to `InitializeResult`; `usage/read` itself
answered in **~1 ms**. `usage/read` makes no model call.

### 2.2 The contract is on the *stable* surface

`muse schema generate-json-schema --out DIR` emits `manifest.json` + `msp.schema.json`
offline from the binary. The manifest for this build:

```json
{"experimental": false,
 "fingerprint": "sha256:7469c9e352e67def4a59df7e439984d7194fa351e1c8b7abb34060fd977ced81",
 "schemaVersion": 1}
```

`usage/read` and `usage/changed` appear in that **non-experimental** bundle. They are not
behind `ClientCapabilities.experimentalApi`, and they are not in `capabilities.grantable`
(the only grantables are `userShell`, `sessionMcp`, `sessionListStream`) — so no capability
negotiation is required to call `usage/read`.

Two relevant surfaces:

| Surface | Kind | Payload |
|---|---|---|
| `usage/read` | request | `UsageReadResult` = `{usage?: SubscriptionUsage}` |
| `usage/changed` | notification | `SubscriptionUsage` + `emittedAtMs` |

Schema docs (verbatim highlights):

- `SubscriptionUsageWindow` — *"The current usage window (the provider's 5-hour-class
  block): verbatim provider percentages with the reset stamp normalized to epoch
  milliseconds (ADR 32563 D2)."* Members: `usedPercent` (*"an integer ≥ 0, verbatim from
  the provider — over-quota values above 100 are valid"*), `windowDurationMins` (*"> 0"*),
  `resetsAtMs`.
- `SubscriptionUsageWeekly` — *"The rolling weekly block: same semantics as
  `SubscriptionUsageWindow` **without a duration**."* Members: `usedPercent`, `resetsAtMs`.
- `SubscriptionUsage` — adds `tier` (*"The provider's subscription tier id, verbatim"*) and
  `observedAtMs` (*"When the host RECEIVED this observation (frame arrival or mint
  request-send)"*). Explicitly: *"The numbers are point-in-time … so a client renders
  'as of', never implies live data."*
- `UsageReadResult` — *"`{usage?}` — omitted, never `null`, when the host has observed
  nothing (ADR 32563 D2: truthful absence, no 'nothing observed' error)."*
- `usage/changed` — *"The host's last-observed subscription usage DATA changed (window,
  weekly, or tier — **not a stamp-only refresh**) … the absent-to-present first observation
  emits (ADR 32563 D3)."*

That last clause matters for a passive design: `usage/changed` is **edge-triggered on value
change**, so you cannot use it as a heartbeat, but you are guaranteed the first observation.

### 2.3 Verified live payload

After driving a real turn through `muse serve` (§2.4), `usage/read` returned:

```json
{"usage": {"window":  {"usedPercent": 0, "windowDurationMins": 300, "resetsAtMs": 1789935797000},
           "weekly":  {"usedPercent": 0, "resetsAtMs": 1789948800000},
           "tier": "27681631238169137",
           "observedAtMs": 1789918758634}}
```

and the matching notification arrived ~94 ms later:

```json
{"jsonrpc":"2.0","method":"usage/changed",
 "params":{...same payload...},"emittedAtMs":1789918758728}
```

Decoded:

| Field | Value | UTC | Note |
|---|---|---|---|
| `observedAtMs` | 1789918758634 | 2026-09-20T15:39:18Z | host arrival stamp |
| `window.resetsAtMs` | 1789935797000 | 2026-09-20T20:23:17Z | **+4.73 h** — inside a 300-min window |
| `weekly.resetsAtMs` | 1789948800000 | 2026-09-21T00:00:00Z | **+8.34 h**, and exactly UTC-midnight aligned (`% 86400 == 0`) |

Two observations worth carrying into the design:

1. `windowDurationMins: 300` is reported **exactly** — SASE can set `duration_seconds =
   18000.0` with no inference. The weekly block reports **no** duration at all, by design.
2. The weekly reset landed on an exact UTC-midnight boundary. One sample is not proof of a
   rule, but it is a strong hint that the weekly window is **day-aligned**, not a rolling
   `now + 7d`. Do not derive `duration_seconds` for weekly from the reset stamp (§6.3).

### 2.4 The binding constraint: process-local, turn-gated

This is the finding that decides the architecture. Three experiments:

| # | Experiment | `usage/read` result |
|---|---|---|
| 1 | `muse serve` → `initialize` → `initialized` → `usage/read` | `{}` |
| 2 | `muse serve` → handshake → `model/list` (succeeded, returned the catalog) → `usage/read` **polled 6× over 11 s** | `{}` every time, **0** `usage/changed` |
| 3 | `muse serve` → handshake → `session/start` → `usage/read` → `turn/start`(real Meta turn) → wait `turn/completed` → `usage/read` | `{}` **before**, **populated after**; exactly **1** `usage/changed` |

And critically, experiment 1 was run *minutes after* a separate `muse exec` process had
completed a real turn on the same machine and account — and still returned `{}`. There is
**no cross-process cache**. The observation lives in the host process's memory only.

Corroborating negatives:

- **`muse exec --json` carries no usage.** A real minimal turn produced 30 stream records
  across 16 distinct `payload_type`s (`run.terminal.completed`, `run.model.configured`,
  `task.lifecycle.*`, …). Grepping for `usedPercent|used_percent|subscription|resetsAt`
  → **0 hits**. So SASE's *current* Muse transport cannot see usage at all.
- **The durable session log carries no usage either.** I enumerated every `payload_type` /
  event `kind` across 5 local `session.jsonl` files (peer researcher's session deliberately
  excluded) — 60+ distinct kinds including `model_completed`, `goal_usage_attribution`,
  `resource_usage_sampled` — and **0** subscription-usage records. So the trick
  `_muse_session_usage.py` uses for *token* counts (glob the session log after the run) has
  no equivalent for *subscription* usage.
- `muse exec --help` exposes no flag that would emit it.

**Consequence:** any SASE design must answer "who paid for the turn?" The only three
answers are: (a) SASE's own Muse agent runs, (b) a probe that mints its own turn, or
(c) an out-of-band HTTP call to Meta (§3).

### 2.5 Auth and account context

`~/.config/muse/auth.json` (mode `0600`) records, without the secret itself:

```
mechanism = oauth · storage = keychain · obtained_via = device_code
api_base_url = https://api.meta.ai/v1
user_full_name, user_email
```

The credential lives in the macOS Keychain; `~/.local/bin/muse` is a bash launcher
(`muse-code/launcher-2`) that hourly self-updates the real 289 MB `muse-bin-<version>`
binary from `lookaside.facebook.com`. SASE already sets `MUSE_NO_AUTO_UPDATE` for runs —
a usage probe must set it too, or a probe could trigger a binary swap.

Binary strings show a "mint" flow (`TBH_MINT_BASE_URL`, `"mint returned an empty api key"`)
and subscription plumbing (`subscription_stamp_missing_tier_name: active stamp folded
without a display name`, gates `subscription_launch` / `subscription_upsell` in
`~/.local/share/muse/feature-config/`). This is consistent with the schema's
*"frame arrival or mint request-send"* wording: usage is learned when the CLI exchanges
its OAuth token for a Model API key **and/or** when response frames come back. Experiment
2 shows the mint is lazy — it does not happen at `model/list`.

---

## 3. Why not scrape `https://dev.meta.ai/usage`

You use that page today, so it's worth stating explicitly why it should **not** be the
implementation:

- It would need a live Meta web session cookie, which is a different credential from the
  device-code OAuth token Muse stores in the Keychain. SASE has no supported way to get it,
  and `UsageProbeContext.auth_context` is documented as *"must not carry secrets, account
  ids, emails, tokens, or filesystem credential paths."*
- The probe worker environment in `probe.py` deliberately strips any env var whose name
  contains `KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH`. Threading a web cookie into it
  would mean punching a hole in that allowlist.
- It is an undocumented, unversioned HTML/JSON surface with no stability contract — versus
  `usage/read`, which ships a **content-hashed stable-surface fingerprint**
  (`schema.fingerprint`) the client can compare against and which SASE's existing
  `vendor_drift` reason code was built for.
- It duplicates data that is already available locally, first-party, and free.

The same argument rules out calling `api.meta.ai/v1` directly with a minted key: it's an
internal contract, SASE would have to re-implement the mint, and the local API already
normalizes reset stamps to epoch ms for you.

**Use `usage/read`.** The web page and the MSP method are the same numbers.

---

## 4. What SASE already has (almost all of it)

The good news: this feature is mostly *mapping*, not *building*. The subscription-capacity
subsystem is already provider-agnostic and already models exactly this concept.

**Domain (glossary `usage-window`, read this turn):** *"a provider-reported capacity
allowance over a time interval … independently identified and measured, with a reset time
when the provider reports one … Usage windows can overlap, and their percentages are
independent: do not add, average, or otherwise merge them. A window's duration is the size
of the interval; time remaining to reset is a separate clock-derived value."* Muse's two
windows fit this without stretching it.

**Rust core** — `sase-core/crates/sase_core/src/provider_usage/`:
- `mod.rs` — `ProviderUsageObservationWire`, `UsageWindowObservationWire`,
  `UsageApplicabilityWire`, `validate_usage_observation`, `remaining_percent`,
  `exceeded_by_percent`, `format_remaining_text`.
- `grok.rs` — `normalize_grok_billing`, the precedent for a per-vendor normalizer. Its
  header states the division of labour outright: *"Probe transport stays in Python. This
  module owns percentage, period, completeness, and plan-label decisions."*
- `indicator.rs`, `store.rs`, `refresh.rs`, `compatibility.rs` — display policy, the
  machine-local cache, and refresh scheduling/backoff.

**Python** — `src/sase/llm_provider/usage/`:
- `probe.py` — isolated worker execution, deadline/output bounds, env scrubbing,
  `record_passive_usage_observation()` for `source: "stream_event"`.
- `transport.py` — `JsonLineSession`, deadline-bounded newline-JSON RPC. **This is exactly
  the MSP transport**; Grok's ACP probe already uses it unchanged.
- `_strategy.py` — ordered fallback chains + `classify_probe_failure()`, which already maps
  JSON-RPC `-32600/-32601/-32602` to `vendor_drift`. All three are real MSP error codes.
- `grok.py` / `claude.py` / `codex_collector.py` — the three existing collectors.

**Hooks** (`_hookspec.py`): `llm_usage_capabilities() -> {"probe": bool, "passive_events":
bool}` and `llm_usage_probe(context)`. `MuseProvider` implements **neither** today.

**Config** (`default_config.yml` `llm_provider.usage_metrics`): `enabled`,
`refresh_seconds: 300` (min 60), `warn_percent: 75`, `critical_percent: 90`,
`indicator.{enabled,default,weekly_all,providers.<name>.windows.<key>}`,
`providers.<name>.enabled`. Plus a `usage_refresh` durable job
(`sase_job_usage_refresh`, line ~1212).

Net: **the only genuinely new code is a Muse collector + a Muse normalizer.** Everything
downstream — store, freshness, backoff, indicator policy, `sase usage list`, the TUI header
indicator — already works generically.

---

## 5. Mapping Muse → the SASE observation

Proposed normalization, one `SubscriptionUsage` → one observation with two windows:

| SASE window field | 5-hour window | Weekly window |
|---|---|---|
| `key` | `"session"` | `"weekly"` |
| `label` | `"Muse 5-hour session"` | `"Muse weekly all models"` |
| `used_percent` | `window.usedPercent` (float-widened) | `weekly.usedPercent` |
| `resets_at` | `window.resetsAtMs / 1000.0` | `weekly.resetsAtMs / 1000.0` |
| `duration_seconds` | `window.windowDurationMins * 60.0` → `18000.0` | **`None`** (vendor reports none) |
| `period_start` | `resets_at - duration_seconds` *(derivable, exact)* | `None` |
| `applicability` | `{"kind": "account"}` | `{"kind": "account"}` |
| `observed_at` | `observedAtMs / 1000.0` | same |
| `source` | `"probe"` or `"stream_event"` | same |
| `vendor_state` | `"allowed"` (see §6.5) | same |

Envelope: `outcome: "ok"`, `completeness: "complete"`, `account_mode: "subscription"`,
`plan: None` (see §6.1), `authoritative_empty: false`.

**Why `applicability: {"kind": "account"}` and not `{"kind": "product", "product":
"muse"}`:** I read `indicator.rs`. `is_all_model_scope()` returns `true` unconditionally for
`Account`, but for the `Product` variant it is hard-coded to `provider == "claude" &&
product == "claude"`. A Muse `Product`-scoped window would therefore be silently excluded
from all-model classification. `Account` is also semantically right — Muse reports one
account-wide pair of windows with no per-model split, and `usage_window_applies()` maps
`Account → Applies` for every model. Grok already uses `Account` for the same reason.

**A `usage/read` returning `{}` is not an error.** It is the documented truthful-absence
case and must map to a windowless status observation — I'd use `outcome: "ok"` with
`authoritative_empty: true` if the domain permits it, otherwise `outcome: "not_applicable"`
with a `muse_usage_not_yet_observed` diagnostic. It must **not** be `error`, or the
collector-health counter (`USAGE_COLLECTOR_FAILING_THRESHOLD = 3`) will mark Muse broken
after three cold probes.

### 5.1 The auto-enrollment landmine

`eligible_usage_providers()` in `refresh.py` enrolls any registered, non-hidden provider
where `usage_capabilities.probe is True`, the CLI is ready, and the provider is referenced
by a model alias (or explicitly enabled). It then refreshes on the **global**
`refresh_seconds`, which defaults to **300** and has **no per-provider override** —
`UsageMetricsSettings` carries a single `refresh_seconds` float and a
`providers: Mapping[str, bool]` that is on/off only.

So: adding `return {"probe": True}` to `MuseProvider.llm_usage_capabilities` and writing a
probe that mints a turn would run a real Muse model turn **every 5 minutes, forever** —
~288 turns/day spent purely to measure how many turns you have left. That is the observer
effect at its most literal. This is the single biggest trap in this feature.

---

## 6. Sharp edges

### 6.1 `tier` is an opaque account-scoped number, not a plan name

Observed: `"tier": "27681631238169137"`. That is a 17-digit id, not `"Pro"`. The binary
even carries the diagnostic `subscription_stamp_missing_tier_name: active stamp folded
without a display name`, which implies the display name is a *separate*, sometimes-absent
thing.

Two problems if you naively map `tier → observation.plan`:
1. **Cosmetic:** the TUI would render "Plan 27681631238169137".
2. **Privacy:** it is plausibly an account- or entitlement-scoped identifier, and it would
   be persisted into the machine-local usage store. SASE's own probe-context contract bans
   account ids from `auth_context`; persisting one in `plan` is at minimum inconsistent
   with that posture.

**Recommendation:** leave `plan: None`. If you want tier change detection (useful — it
should bump `account_generation`), hash it into the opaque `auth_context` fingerprint
rather than storing it verbatim.

### 6.2 `usedPercent` is an integer that may exceed 100

The schema says over-quota values above 100 are valid. SASE handles this correctly already:
`validate_used_percent` only rejects non-finite/negative, `remaining_percent_value` is
`max(0, 100 - used)`, and `exceeded_by_percent_value` reports the overage. No core change
needed — but the collector must **not** clamp at 100 on the way in, or you lose the
overage signal.

### 6.3 `weekly_all` display classification needs a decision

`indicator.rs::is_weekly_window()` resolves in this order:
1. If `duration_seconds` matches `WEEK_SECONDS` (604800) → **true**.
2. If `duration_seconds` is `Some` and does *not* match → **false**.
3. Else fall through to a hard-coded allowlist: `claude` with key `weekly`/`weekly:*`, or
   `grok` with key `included_weekly` and `Account` scope.

Muse reports no weekly duration, so step 3 applies and Muse is **not** matched → the
default `indicator.weekly_all: always` policy would not reach it, and the weekly window
would fall back to `indicator.default` (`below_remaining_percent: 20`) — i.e. invisible
until you're 80% through the week. Almost certainly not what you want.

Two fixes:
- **(a) Preferred — extend the Rust allowlist**: add
  `provider == "muse" && key == "weekly" && matches!(applicability, Account)`. Honest: it
  asserts nothing about duration. Costs a `sase-core` change, which you're making anyway
  for the normalizer, and it is squarely core classification logic per the
  `rust_core_backend_boundary` memory.
- **(b) Shortcut — set `duration_seconds = 604800.0`** on the weekly window. Zero Rust
  change. But it *fabricates* a vendor fact the vendor deliberately omits, and my single
  sample (weekly reset at an exact UTC midnight, only 8.3 h out) is more consistent with a
  **day-aligned** weekly boundary than a rolling 7-day one. If the real interval is not
  exactly 604800 s, you've written a wrong number into the store.

I recommend **(a)**.

### 6.4 `is_all_model_scope` / `is_weekly_window` are provider allowlists generally

Worth flagging as a small architectural smell for whoever does this: `indicator.rs` contains
three separate `provider == "claude"` / `provider == "grok"` string comparisons. Every new
provider requires touching them. If you're in there anyway, consider whether classification
should be driven off `applicability` + `duration_seconds` alone, with the allowlist as a
named compatibility shim. That's a refactor, not a prerequisite — don't let it block this.

### 6.5 `vendor_state` has no Muse signal

Claude derives `vendor_state` from rate-limit status fields; Muse's payload has none. Set
`"allowed"` when a reading is present (percentages are self-describing) — or `"unknown"` if
you want to be strict. I'd use `"allowed"`, matching what Claude's *probe* path does, since
an absent rejection signal from a host that just completed a turn is meaningful.

### 6.6 Drift detection is unusually cheap here

`InitializeResult.schema.fingerprint` is a sha256 of the binary's stable-surface bundle, and
`muse schema generate-json-schema` reproduces it offline. A collector can pin a known-good
fingerprint and emit `vendor_drift` on mismatch *before* parsing anything — a stronger
signal than the `-32601`-sniffing `classify_probe_failure()` fallback. Treat a mismatch as a
**warning** and still attempt the read: the schema itself says *"A mismatch is a warning
condition, not an error (SS1.4.1)."*

### 6.7 Probe hygiene

If a probe process is spawned, it must: set `MUSE_NO_AUTO_UPDATE=1` (or the launcher may
swap the binary mid-probe); pass `--no-session-log` (avoids littering
`~/.local/share/muse/sessions/`); run in a scratch cwd (`probe.py` already provides one);
and be killable at the deadline (`spawn_killable_process` already provides that). Note that
`--no-session-log` *disables* `--session-id` and local session messaging — fine for a probe,
fatal for a run transport (§7 Phase 3).

---

## 7. Options considered

| # | Approach | Marginal cost per reading | Freshness | Build cost | Verdict |
|---|---|---|---|---|---|
| A | Scheduled probe that mints its own turn | **1 real model turn** | On cadence | Low | ✗ Self-defeating |
| B | Scrape `dev.meta.ai/usage` | HTTP only | On cadence | Medium | ✗ Unsupported, needs a web cookie (§3) |
| C | Passive observer on SASE's own Muse runs (MSP transport) | **Zero** | Per Muse run | High | ✓ Correct, but big |
| D | Read-only cold probe (`usage/read` with no turn) | Zero | Never populates | Trivial | ✗ Always `{}` (§2.4) |

**A** is the naive reading of "add a probe like Claude's", and it's worth being explicit
about why the analogy fails. Claude's probe (`_claude_support_command.py`) runs
`claude -p --output-format json --safe-mode --no-session-persistence --max-budget-usd 0.01
/usage`, and `has_zero_cost_markers()` then asserts `num_turns == 0 && total_cost_usd == 0`.
Claude's `/usage` is answered **locally, without a model call** — that's why the probe is
free and why a 300 s cadence is fine. Muse has no such local answer and no `--max-budget-usd`
equivalent. At the default cadence, option A would spend ~288 turns/day of the budget it
reports on. Even at 1/hour it burns ~24 turns/day and writes a session log each time.

**D** is what "just add `usage/read`" actually gets you, and it's why this research matters:
it looks like it works, it returns HTTP-200-shaped success, and it is empty forever.

**C** is the only design where the reading is free, because SASE is *already* paying for
Muse turns every time it runs a Muse agent. The cost is that it requires moving Muse's run
transport from `muse exec --json` to `muse serve` + MSP — a real rewrite of
`_subprocess_muse.py`, `_tool_call_muse.py`, and `_muse_session_usage.py`, since MSP is a
full session-host protocol (approvals, view subscription/paging, turn lifecycle, user-input
dialogs) rather than a one-shot JSONL stream.

**That rewrite has a second, independent payoff** worth weighing: `_muse_session_usage.py`
currently recovers *token* counts by globbing
`$XDG_DATA_HOME/muse/sessions/*/*/*/<session-id>/session.jsonl` after the process exits,
because *"Muse's `muse exec --json` stdout stream carries no token counts at all."* MSP
gives you `session/tokenUsage` as a first-class notification with server-derived
counted-once `promptTokens`/`totalTokens` and a `cumulative` block — deleting a filesystem
race and a documented double-counting hazard. Plus `session/contextUsage` for context
pressure, which SASE has no Muse equivalent for today.

---

## 8. Recommended solution

**Land it in three phases. Phase 1 and 2 are independently shippable and jointly deliver
the feature; Phase 3 is the optimization that makes it free.**

### Phase 1 — Domain mapping + normalizer (no collection yet)

*In `sase-core` (`crates/sase_core/src/provider_usage/`):*
- Add `muse.rs` with `normalize_muse_subscription_usage(request)`, modelled directly on
  `grok.rs`: takes the decoded `SubscriptionUsage` map + `provider`/`context_id`/
  `account_generation`/`request_started_at`/`now`, emits a validated
  `ProviderUsageObservationWire` with the two windows per §5. Export it from `mod.rs` and
  bind it in `sase_core_py`.
- Ms → s conversion, `windowDurationMins * 60`, and `period_start` derivation live **here**,
  not in Python — this is exactly the "percentage, period, completeness, and plan-label
  decisions" the Grok normalizer's header claims for core.
- Extend `is_weekly_window()` with the Muse arm (§6.3a).
- Handle the empty-`usage` case as a windowless non-error observation (§5).
- Fixtures: the real payload in §2.3, plus `usedPercent > 100`, plus absent-`usage`.

*Rationale:* the `rust_core_backend_boundary` core memory is unambiguous — if a web app or
CLI would need this to match the TUI, it's core backend logic. Normalization is.

### Phase 2 — Explicit, user-invoked probe (opt-in, never scheduled)

- Add `src/sase/llm_provider/usage/muse.py`: `collect_muse_usage(context)` driving
  `muse serve` through the existing `JsonLineSession`, with the full
  `initialize` → `initialized` → `usage/read` handshake (§2.1), fingerprint check as a
  warning (§6.6), probe hygiene per §6.7, and `_strategy.ProbeStrategy` wrapping so
  `-32601`/`-32602` classify as `vendor_drift`.
- `MuseProvider.llm_usage_capabilities()` returns **`{"passive_events": True}`** — note
  **not** `{"probe": True}`. This keeps Muse out of `eligible_usage_providers()` and
  therefore out of the 300 s scheduled loop (§5.1), while still letting the store accept
  observations.
- Wire the collector to the explicit path only: `sase usage refresh -p muse` (or whatever
  the existing explicit-refresh verb is) and the TUI's refresh-panel action. A human asking
  for a reading has consented to the cost; a background loop has not.
- The probe mints one minimal turn (`session/start` → `turn/start` with a 4-token prompt
  → `usage/read`). Document that cost in `docs/configuration.md` in the same change. Use
  `--reasoning-effort none`.
- Config: this is a permanent user choice, so per the `sase_flags.md` memory it is a
  **config field, not a feature flag** — *"Do not flag anything users are meant to choose
  forever; that is a config field."* Suggest `llm_provider.usage_metrics.providers.muse.
  enabled` (already generic) plus, if scheduling is ever wanted, a **new**
  `providers.<name>.refresh_seconds` override, since the current global `refresh_seconds`
  cannot express "Muse is expensive, poll it rarely."
  - The one case for a `beta` flag is if you run this as a multi-phase epic and Phase 2
    would land a half-finished surface — that's the documented epic-scaffolding exception.

**After Phase 2 the feature works**: `sase usage list -p muse --json` shows both windows,
the TUI header indicator shows them under existing policy, and reset times — the part that
*doesn't* go stale — are exact.

### Phase 3 — Passive collection via MSP run transport (makes it free)

- Move `MuseProvider.invoke` from `muse exec --json` to `muse serve` + MSP, subscribing to
  `usage/changed` and calling `record_passive_usage_observation()` with
  `source: "stream_event"`. Flip capabilities to `{"probe": True, "passive_events": True}`
  once a non-turn-minting probe path exists, or leave probe off entirely — with passive
  collection, every Muse agent run refreshes usage for free and a probe becomes redundant.
- Fold in `session/tokenUsage` to retire the `_muse_session_usage.py` session-log glob, and
  `session/contextUsage` for context pressure.
- This is a substantial piece of work and deserves its own plan. **Size it as an epic, not
  a task.** It is also the phase where MSP's approval flow (`approval/request`,
  `approval/decide`) has to be reconciled with SASE's `--disable-sandbox` posture and the
  `sase stitch create` interaction documented in `muse.py::_safety_args`.

### Sequencing note

If you only want one phase: **do Phase 1 + Phase 2.** They are maybe a few days of work,
they deliver the windows you asked for, and Phase 3 replaces only the *feeding* mechanism —
none of the domain, store, or display work is thrown away.

---

## 9. Confidence and open questions

**High confidence (directly verified on this machine, this build):** the MSP handshake
including the `initialized` requirement; `usage/read` / `usage/changed` existing on the
non-experimental surface; the exact payload shape and a real populated reading; the
process-local, turn-gated nature of the observation; `muse exec --json` and the durable
session log carrying no subscription usage; `model/list` not triggering a mint; the SASE-side
code paths, hooks, config, and the two `indicator.rs` provider allowlists.

**Open / not verified:**

1. **Weekly window duration.** One sample (UTC-midnight aligned, 8.3 h out) is not enough to
   say whether the weekly block is rolling-7-day or calendar-aligned. Resolve by sampling
   `weekly.resetsAtMs` across several days before hard-coding 604800 anywhere. This is the
   main reason I recommend §6.3(a) over (b).
2. **Whether the mint alone suffices.** `observedAtMs` is documented as *"frame arrival **or**
   mint request-send"*, and experiment 2 shows `model/list` doesn't mint. If some cheaper
   MSP operation *does* force a mint, a genuinely free probe becomes possible and Phase 2's
   cost disappears. Worth ~30 minutes of probing other methods (`session/resume`,
   `session/compact`, `skill/list`) before building the turn-minting probe.
3. **`usedPercent` granularity.** Integer-valued and observed at 0. Whether a light user
   ever sees a non-zero value between refreshes, or it jumps in coarse steps, is unknown and
   affects how useful a 5-minute cadence would even be.
4. **`tier` semantics.** Assumed opaque and account-scoped from its shape and the
   `subscription_stamp_missing_tier_name` diagnostic. Not confirmed.
5. **MSP stability posture.** The fingerprint is per-binary and the launcher self-updates
   hourly by default, so `schema.fingerprint` will churn across Muse releases. Pinning it as
   a hard gate would break on every update — hence "warning, then proceed" (§6.6).

**Cost incurred by this research:** two real Muse model turns (one via `muse exec`, one via
`muse serve`), each a ~4-token prompt. Both reported `usedPercent: 0` afterward.
