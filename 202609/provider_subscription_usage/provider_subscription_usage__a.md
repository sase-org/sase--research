# Generic subscription-usage metrics for SASE

Research date: 2026-09-07

## Executive conclusion

SASE should model subscription usage as a provider-neutral collection of quota windows, but it should not try to acquire every provider's data in the same way. The robust common seam is the normalized observation and cache, not a common HTTP endpoint.

The initial implementation should support two acquisition modes:

1. **Pull probes** through a provider's first-party local process. Codex has a documented `codex app-server` method, and Grok Build has an `x.ai/billing` ACP extension used by its own pager.
2. **Invocation observations** captured from a provider's normal event stream. Claude Code's documented `RateLimitEvent` is the best supported Claude surface today; it should update the shared cache whenever SASE invokes Claude.

Do not scrape the three web settings pages, read browser cookies, or call private web endpoints with copied OAuth tokens. Those approaches duplicate authentication and token refresh, are harder to secure, and will break more readily than the vendors' local clients.

For the first release, show the metrics in ACE's existing Provider Routing modal and keep them **display-only**. A percentage of 100 is not uniformly equivalent to “cannot launch”: providers can have multiple independent buckets, reset credits, overage, or fallback/free-tier behavior. Later, only an explicit provider rejection signal should feed SASE's existing temporary-disable machinery.

## Provider findings

| Provider | Best initial source | Available information | Confidence | Important limitation |
|---|---|---|---|---|
| Codex | `codex app-server` → `account/rateLimits/read` | Multiple named buckets; primary/secondary window percent, duration, reset; plan and reached state; optional credits | High | ChatGPT-backed auth only; API-key-only usage is intentionally out of scope |
| Claude | Existing Claude `stream-json` invocation → documented `RateLimitEvent` | Limit type, utilization fraction, reset, allowed/warning/rejected state, overage state | Medium-high | Observation is event-fed, not an on-demand account query; no value before a qualifying Claude response/event |
| Grok | `grok agent stdio` → ACP extension `_x.ai/billing` (`x.ai/billing` internally) | Included-credit percent, weekly/monthly period and reset, tier; additional billing fields are available but should be ignored initially | Medium-high | First-party and open source, but the custom ACP method is not documented as a stable external compatibility contract |

I also performed schema-only local probes against the installed Codex 0.153.4 and Grok 1.0.13 processes. Both returned authenticated usage data without exposing credentials to SASE code. The probes recorded only field names/types, not account identifiers, percentages, balances, or reset values. Codex returned both `rateLimits` and a two-entry `rateLimitsByLimitId`; Grok returned `creditUsagePercent`, `currentPeriod`, and related optional billing fields.

## Codex

Codex has the cleanest integration surface. OpenAI documents `codex app-server` as the interface for deep product integration. It runs a JSONL JSON-RPC protocol over stdio, performs the normal `initialize`/`initialized` handshake, and exposes `account/rateLimits/read` plus `account/rateLimits/updated`. The response supports a backward-compatible single bucket and a multi-bucket map keyed by `limitId`; each window can carry `usedPercent`, `windowDurationMins`, and `resetsAt`. The response can also carry `planType`, `credits`, `rateLimitReachedType`, and earned reset credits. [Codex app-server documentation](https://learn.chatgpt.com/docs/app-server)

The current open-source implementation confirms that app-server owns authentication and fetches the ChatGPT account limits on the caller's behalf. It also preserves the multi-bucket response rather than reducing it to the historical `codex` bucket. [Codex account protocol types](https://github.com/openai/codex/blob/1e66885a16161048215a3782ecdd1739aab0aabf/codex-rs/app-server-protocol/src/protocol/v2/account.rs) and [account request processor](https://github.com/openai/codex/blob/1e66885a16161048215a3782ecdd1739aab0aabf/codex-rs/app-server/src/request_processors/account_processor.rs)

Recommendation:

- Spawn `codex app-server` with pipes, complete its documented handshake, issue `account/rateLimits/read`, and terminate cleanly after the result. If ACE later keeps a process alive while the provider modal is open, consume `account/rateLimits/updated` notifications as well.
- Parse `rateLimitsByLimitId` when present and fall back to `rateLimits`; do not hard-code “primary means 5 hours” or “secondary means weekly.” Preserve the server's bucket ID, label, duration, and reset.
- Treat API-key-only auth as `not_applicable`, not as a probe error. Subscription quota and API organization rate limits are different products.
- Do not call the internal ChatGPT backend URL directly. App-server already owns auth refresh, account selection, headers, and response evolution.

## Claude

Anthropic now documents two useful subscription surfaces:

- Claude Code status-line input includes `rate_limits.five_hour` and `rate_limits.seven_day`, each with `used_percentage` and `resets_at`. It requires Claude Code 2.1.251 or newer and appears only for eligible Claude.ai subscribers after the first API response. The fields can be independently absent. [Claude Code rate-limit status-line data](https://code.claude.com/docs/en/statusline#rate-limit-usage)
- The Claude Agent SDK defines `RateLimitEvent`, emitted when quota status changes. Its `RateLimitInfo` carries `status` (`allowed`, `allowed_warning`, or `rejected`), `rate_limit_type` (`five_hour`, `seven_day`, model-specific weekly limits, or `overage`), `utilization` as a 0–1 fraction, and reset/overage fields. [Claude Agent SDK Python reference](https://code.claude.com/docs/en/agent-sdk/python)

The Agent SDK event is the better SASE integration point. SASE already invokes Claude with `--output-format stream-json`; `src/sase/llm_provider/_subprocess_claude.py` currently handles assistant, error, and result events and can add a rate-limit observation callback without a second login or network request. The status-line shape is useful corroboration and a fallback contract, but SASE should not install or replace a user's status-line command merely to collect metrics.

There is no equally stable, documented, standalone “get my Claude subscription usage now” API. The current Claude client contains private OAuth usage machinery and an experimental SDK control request whose own name warns callers not to rely on it. That is unsuitable as the initial production contract.

Recommendation:

- Extend the existing Claude stream parser to recognize the documented rate-limit event and persist each bucket observation through the generic core store.
- Merge individual event updates by `rate_limit_type`; an event about `seven_day_opus` must not erase the last known `five_hour` bucket.
- Show `waiting for first Claude usage observation` until data arrives. On manual refresh, explain that Claude usage refreshes after a Claude response rather than silently returning zero or scraping private endpoints.
- Require Claude Code 2.1.251+ for this capability and degrade to `unsupported_cli_version` on older clients.
- Preserve the event's explicit `allowed_warning` and `rejected` states. These are more useful than deriving a state from arbitrary percentage thresholds.

Anthropic's error guidance separately distinguishes subscription quota errors from temporary service throttling and API-key 429s, reinforcing that SASE should not conflate all rate-limit-looking events. [Claude Code usage-limit error guidance](https://code.claude.com/docs/en/errors#usage-limits)

## Grok

The user-facing Grok Usage page represents a shared weekly allowance. xAI says paid users receive one pool across Grok products, displayed as percentage used with a reset date/time; extra usage credits can continue service after the included pool is exhausted. [xAI Grok usage and limits FAQ](https://docs.x.ai/grok/faq#usage--limits)

The current official Grok Build source exposes the corresponding data through its local agent protocol:

- `x.ai/billing` authenticates through Grok Build's own auth manager and queries the CLI proxy. Its typed response prefers `creditUsagePercent` and `currentPeriod` (weekly or monthly, with start/end), while retaining legacy monthly-limit fields. [Grok Build billing extension](https://github.com/xai-org/grok-build/blob/72a61251fcffb464bcc687aeb5a998e5a98ec0c9/crates/codegen/xai-grok-shell/src/extensions/billing.rs#L1-L275)
- Grok's own pager maps that response into its credit bar, preferring the new percentage/period fields and falling back to legacy limit/used values. [Grok pager normalization](https://github.com/xai-org/grok-build/blob/72a61251fcffb464bcc687aeb5a998e5a98ec0c9/crates/codegen/xai-grok-pager/src/app/effects/helpers.rs#L1614-L1676)

Recommendation:

- Start `grok agent stdio`, use an ACP client, and send the custom wire method `_x.ai/billing` with empty parameters. Parse the nested `x.ai/billing` result. Let Grok own OAuth loading and refresh.
- Normalize `creditUsagePercent` to the included-allowance quota window and `currentPeriod.end` to its reset. If only legacy `monthlyLimit` and `used` exist, derive the percentage exactly as Grok's pager does.
- Ignore `onDemandCap`, `onDemandUsed`, `prepaidBalance`, auto-top-up, and history in the first release. They are billing/paid-overage data, explicitly deferred by this project request.
- Mark this adapter `compatibility: first_party_unstable` in diagnostics because `x.ai/billing` is a vendor-owned extension used in production but not currently promised as a stable public API. A missing-method response should produce `unsupported_cli_version`, not a traceback.
- Do not scrape `https://grok.com/?_s=usage`; that would require browser-session credentials and bypass the working first-party auth boundary.

## Generic SASE design

### 1. Normalize quota windows, not vendor dashboards

Put the durable domain and cache behavior in `sase-core`, consistent with the project's Rust-core boundary. Keep provider protocol clients in the existing Python provider plugins because discovery and CLI invocation already live there.

A useful version-1 wire shape is:

```text
ProviderUsageSnapshotV1
  version
  provider
  observed_at
  source                 # pull_probe | invocation_event
  source_version         # provider CLI version, optional
  identity_fingerprint   # opaque/hash only, optional
  windows[]

QuotaWindowV1
  limit_id               # provider-stable opaque ID
  label                  # optional display label
  used_fraction          # finite, >= 0; retain >1 for exceeded spend caps
  resets_at              # Unix seconds, optional
  window_seconds         # optional
  scope                   # account | model | overage | unknown
  state                   # allowed | warning | rejected | unknown
```

The read result should wrap the last good snapshot with a separate probe state:

```text
ProviderUsageReadV1
  provider
  status                  # fresh | stale | unsupported | unauthenticated |
                          # not_applicable | unavailable
  snapshot                # optional last good observation
  checked_at
  diagnostic_code         # stable, non-secret; optional
```

Important semantics:

- Store one canonical `used_fraction`; calculate user-facing remaining as `max(0, 1 - used_fraction)`. Never persist both and risk disagreement.
- Do not cap stored usage at 100%. Claude spend limits can exceed 100; the renderer may cap a bar while still showing “exceeded.” Reject only negative, non-finite, or structurally invalid values.
- Treat windows as an unordered collection identified by `limit_id`. Do not bake `primary`, `secondary`, `5h`, or `7d` into the core type.
- Keep future token/cost/billing metrics as additive typed sections on a later envelope version. Do not weaken the initial quota type into arbitrary key/value telemetry in anticipation of future scope.
- Never store raw provider payloads, access/refresh tokens, email addresses, or account IDs. If an adapter has a stable account ID, store only a domain-separated hash so a cache entry can be invalidated after account switching.

### 2. Add a dynamic provider capability, not metadata

`src/sase/llm_provider/_hookspec.py` already gives each registered provider optional metadata hooks, but usage is dynamic and must not enter the registry's metadata cache. Add an optional per-provider operation such as:

```python
llm_probe_subscription_usage() -> Mapping[str, object] | None
```

Call it directly on the selected plugin instance, as the registry already does for provider-owned capabilities. Omission means `unsupported`, preserving third-party provider compatibility. The plugin returns the neutral versioned observation payload; Rust validates, merges, persists, and evaluates freshness. Separately expose a shared `record_provider_usage_observation(...)` path for event-fed providers such as Claude.

This split makes a future provider cheap to add: implement one probe or feed observations from its normal stream, with no TUI or routing changes.

### 3. Use a small, safe shared cache

Add a machine-wide file such as `$SASE_HOME/llm_provider_usage.json`, implemented in Rust with the same bounded-lock and atomic-write discipline as `provider_disable`. Use mode 0600 and retain only normalized values.

- Read cached data immediately.
- Refresh pull-capable providers in the background on modal open and on an explicit refresh action.
- Coalesce concurrent refreshes per provider and use a hard subprocess timeout. Keep the last successful snapshot when a probe fails, but label it stale and retain a stable diagnostic code.
- Expire a bucket when its reset passes unless a newer observation replaces it; never reinterpret the old percent as the new window's percent.
- Invalidate or quarantine cached values on a changed identity fingerprint. When a provider cannot supply identity, use a short maximum age and make the uncertainty visible.

### 4. Put the first UI in Provider Routing

The Provider Routing modal in the Models panel is the natural first surface: users are already deciding which provider to launch, and the code already loads a provider snapshot with a threaded Textual worker (`models_panel_providers.py`).

Suggested rows:

```text
CLAUDE   available   5h 74% left · 7d 38% left
CODEX    available   5h 61% left · weekly 12% left
GROK     available   weekly 47% left
```

Show only the two most constraining windows inline. The selected-provider detail area can show every window, absolute reset time plus countdown, last-observed age, source, and a precise unavailable reason. Whole percentages are adequate; source values do not justify decimal precision in the routing UI.

Follow SASE's TUI performance rules: render cached state synchronously, launch provider probes from a pump-free/background worker, coalesce reloads, and let timer ticks update countdown text only. A timer tick must never launch network requests or subprocesses. Re-read the highlighted provider before applying an asynchronous result so a late response cannot move or repaint the wrong detail selection.

### 5. Keep routing independent in version 1

Do not automatically disable a provider from `remaining == 0` in the first release. Examples of why:

- Grok may continue via prepaid/on-demand credits or a free tier.
- Codex may expose multiple buckets and an explicit `rateLimitReachedType` distinct from percentage.
- Claude provides an authoritative `rejected` state, while `allowed_warning` is deliberately not rejection.
- A stale snapshot can cross a reset without a successful refresh.

A later integration can call the existing provider-disable path only when the provider supplies an explicit hard-rejection signal and an applicable reset. Existing invocation-error detection remains the safety backstop. It should not be replaced by proactive metrics.

## Implementation sequence

1. Add the versioned Rust wire types, validation/merge logic, atomic cache, and Python bindings. Include a fake multi-window provider fixture.
2. Add the optional Python probe hook and a provider-agnostic usage service that combines cached reads, pull refreshes, and event observations.
3. Implement Codex through app-server and Grok through ACP; use strict allow-list parsers and subprocess timeouts.
4. Teach the Claude stream parser to record `RateLimitEvent` updates. Do not alter user Claude settings.
5. Extend the Provider Routing snapshot and renderer, keeping first paint cache-only and refresh work off the event loop.
6. After a release of display-only telemetry, evaluate whether explicit provider rejection states should seed temporary disables.

## Verification and failure cases

Tests should be fixture-driven and perform no live provider calls in normal CI:

- Core round trips, additive unknown fields, finite/range validation, merge-by-limit-ID, passed-reset expiry, stale fallback, identity change, concurrent writers, and partial-corruption repair.
- Provider fixtures for multi-bucket Codex, single/legacy Grok, partial Claude event sequences, missing/null fields, unauthenticated accounts, API-key-not-applicable accounts, method-not-found, timeout, malformed JSON, and extra future fields.
- Subprocess protocol tests with interleaved notifications/stdout noise and guaranteed child cleanup.
- TUI tests proving first paint does not wait, cursor selection survives late results, modal close cancels work, timer ticks do not probe, and stale/error labels are visible.
- A manually enabled, non-CI schema smoke test may query installed provider clients but must redact all values and identifiers, as done for this research.

## Principal risks

1. **Vendor protocol drift.** Mitigate with allow-list parsing, CLI-version diagnostics, fixtures, and `unsupported_cli_version` degradation. Grok is the highest risk because its ACP extension is not a documented public contract.
2. **Misleading freshness.** Always show observation age/status, expire crossed windows, and never turn a failed refresh into zero usage.
3. **Account switching.** Hash stable provider identity where available and avoid long-lived unscoped cache entries.
4. **Credential exposure.** Delegate auth to vendor processes; do not log raw payloads or launch commands containing secrets.
5. **Routing overreach.** Keep metrics informational until explicit rejection/overage semantics are tested per provider.

## Bottom line

Implement a generic, Rust-owned quota-window store with two Python-side ingestion paths: optional first-party probes and observations from normal provider streams. Ship Codex pull, Grok pull, and Claude event capture together in a display-only Provider Routing UI. This delivers useful “how much is left, and when does it reset?” information now, while keeping vendor authentication quirks and future API-token/billing statistics out of the common model.
