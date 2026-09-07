# Subscription Usage Headroom For Claude / Codex / Grok — Consolidated

Consolidates `provider_subscription_usage__a.md` (design-focused, schema-only probes)
and `provider_subscription_usage__b.md` (empirical, every path verified live on athena),
plus the lead researcher's own verification pass. Research dates: 2026-09-07, against
live logged-in installs `claude 2.1.263`, `codex-cli 0.153.4`, `grok 1.0.13`.

## Answer up front

Ask each provider's own CLI, never the vendor's web endpoints. All three CLIs SASE
already shells out to will report their own subscription quota over a local,
non-inference, zero-cost interface, using their own auth — SASE never touches a
credential:

| Provider | Acquisition (all verified live) | Latency | Notes |
|---|---|---|---|
| claude | **Probe:** `claude -p --output-format json "/usage"` (cost $0, 0 turns) · **plus** passive `rate_limit_event` capture from the stream-json SASE already parses | ~1.7 s | probe returns prose (small regex parser); event returns structured JSON |
| codex | `codex app-server` JSON-RPC → `account/rateLimits/read` | ~1.0 s | structured, multi-bucket, typed |
| grok | `grok agent stdio` ACP → `_x.ai/billing` (note the `_` wire prefix) | ~0.4 s | structured; weekly shared pool |

Normalize onto **named windows of `used_percent` (0–100) plus `resets_at`** — the only
unit all three vendors agree on (none publishes tokens or dollars to subscribers).
Store snapshots in the Rust core next to `provider_disable.rs`, refresh from a durable
proc (~5 min cadence plus opportunistic triggers), read in the TUI only through a
lock-free peek, and put per-provider probes behind a new pluggy hook so a fourth
provider is a plugin change with zero core edits. **v1 is display-only** — no automatic
routing/disable decisions from these numbers.

## Where the two reports disagreed, and what the tiebreak found

**1. Claude acquisition (the substantive conflict).** Report A recommended feeding
Claude usage passively from `RateLimitEvent`s in the stream SASE already parses; report
B rejected stream harvesting ("zero rate-limit fields; verified") and recommended the
`/usage` CLI probe. Both were partly right: B's verification used the `--output-format
json` *result envelope*, which indeed carries no rate-limit fields — but the lead
researcher verified that in `-p --output-format stream-json` mode (exactly how SASE
invokes Claude, `claude.py:325`), a real API turn emits:

```json
{"type":"rate_limit_event","rate_limit_info":{
  "status":"allowed","rateLimitType":"five_hour","resetsAt":1788820200,
  "overageStatus":"rejected","overageDisabledReason":"out_of_credits","isUsingOverage":false,
  "unifiedWindows":{"five_hour":{"utilization":0.1,"resetsAt":1788820200},
                    "seven_day":{"utilization":0.25,"resetsAt":1789257600}}}}
```

Structured, both major windows in one event (`utilization` is a 0–1 fraction), plus
overage state. Caveats confirmed: it fires only when rate-limit info changes during a
real turn (a zero-cost `/usage` run emits none), and it omits the model-scoped weekly
window that `/usage` shows. **Resolution: do both.** The `/usage` probe is the
on-demand/bootstrap source (all three windows, plan discriminator); passive
`rate_limit_event` capture in `_subprocess_claude.py` is a free freshness supplement
that updates the cache on every agent run — on a host running agents constantly, the
displayed number stays current between probe ticks at zero cost.

**2. Direct-HTTP fallbacks.** A said never; B said opt-in, off by default. Resolution:
**do not ship them in v1.** All three CLI probes are verified working, so the fallback
buys little, and the Claude one is policy-encumbered (below). Revisit only if a CLI
probe path breaks (`allow_direct_http` config stays reserved for that day).

**3. Refresh model.** A pulled on modal-open/manual-refresh only; B ran a 5-minute
durable proc. Resolution: **B's proc**, which is what makes a top-bar pill honest,
carrying A's cache semantics (coalesced refreshes, stale labeling, reset-crossing
expiry, per-provider failure independence).

**4. UI surface.** A confined v1 to the Provider Routing modal; B added a top-bar pill,
Models-panel section, CLI, and doctor line. Resolution: **B's surfaces**, folding A's
detail-area guidance (all windows, reset countdown, observation age, precise
unavailable reason) into the Models-panel section.

**5. Canonical measure.** A stored `used_fraction` (0–1); B stored `used_percent`
(0–100). Resolution: **`used_percent`** — it is the native unit of Claude `/usage`
prose, Codex `usedPercent`, and Grok `creditUsagePercent` (only the Claude event needs
×100). Keep exactly one stored measure (compute "remaining" at render), do **not** cap
at 100 (Claude spend can exceed it; renderer caps the bar, label says "exceeded"), and
reject only negative/non-finite values.

## Per-provider detail

### Claude

- **Probe:** `claude -p --output-format json "/usage"`. Verified twice independently:
  `total_cost_usd: 0`, `num_turns: 0`, ~1.7 s; handled locally by the binary, never
  reaches the sampling path. The `result` prose contains one line per window:
  `Current session: 10% used · resets Sep 7, 6:30pm (America/New_York)` — session,
  week (all models), and week (model-scoped). Parser is one regex
  (`^Current (?P<label>[^:]+): (?P<pct>\d+)% used · resets (?P<reset>.+)$`); the reset
  time appears both with and without minutes (`6:30pm` and `8pm` — both observed), and
  the zone name resolves with `zoneinfo`. The first line ("You are currently using your
  subscription…") is the subscription-vs-API discriminator → `status: not_applicable`
  for API-key installs. **Parse failure degrades to `status: error`, never raises and
  never synthesizes 0%.**
- **Event:** recognize `type: "rate_limit_event"` in `_subprocess_claude.py` and write
  `unifiedWindows` (+ overage/status fields) through the shared observation path. Merge
  by window key; an event about one window must not erase another's last observation.
  Preserve the explicit `allowed` / `allowed_warning` / `rejected` status rather than
  deriving state from percent thresholds.
- **Policy (decide-before-coding, from B, quoted from
  code.claude.com/docs/en/legal-and-compliance):** OAuth credentials are for the
  unmodified Claude Code binary; third parties "may not collect, store, or intermediate
  Claude.ai credentials or session tokens", while running the unmodified binary under
  the user's own login is explicitly blessed. The CLI probe and stream capture are
  squarely inside the permitted shape; reading `~/.claude/.credentials.json` and
  calling the undocumented `/api/oauth/usage` endpoint directly makes an installable
  open-source SASE exactly the "third-party developer" the policy addresses (and
  Anthropic began server-side enforcement in early 2026). B verified the endpoint works
  today; that is not a reason to ship it.
- Dead ends (verified by B): statusline JSON (has `rate_limits` on 2.1.251+, but the
  statusline is not invoked in `-p` mode); `--bare` (blocks OAuth); no `claude usage`
  subcommand.

### Codex

`codex app-server` (JSON-RPC over stdio; `initialize` → `initialized` →
`account/rateLimits/read`, ~1.0 s, no orphan process). Verified live response carries
`rateLimitsByLimitId` — one entry per bucket, each with `limitName`, `planType`, and
`primary`/`secondary` windows of `{usedPercent, windowDurationMins, resetsAt}` — plus
`rateLimitReachedType`, `credits`, and `rateLimitResetCredits` (Bryan's account holds 3
free "full reset" credits; worth showing beside a nearly-exhausted bar later).

- Parse `rateLimitsByLimitId` when present, fall back to legacy `rateLimits`. Treat
  buckets as an unordered collection keyed by the server's `limitId`; do not hard-code
  "primary = 5h, secondary = weekly".
- Pass `{"excludeResetCreditDetails": true}` on background polls (the vendor doc
  comment says that is its purpose). Do **not** set `supportsLunaReserve` — the type
  comment restricts it to clients that can apply Reserve, and setting it records
  experiment exposure.
- `~/.codex/auth.json` `auth_mode` (`"chatgpt"` vs API key) is the
  subscription-vs-API discriminator → `not_applicable` for API-key auth.
- Caveat: `codex app-server` is labelled `[experimental]` in its own `--help`. There is
  an `account/rateLimits/updated` push notification if a long-lived connection ever
  becomes worthwhile; not for v1. SASE's normal `codex exec --json` channel
  (`codex.py:400`) carries no rate-limit data (v2 thread-event schema — verified in
  vendor source), so a Codex passive feed is not available today.

### Grok

ACP extension over `grok agent stdio`: after `initialize`, call **`_x.ai/billing`**
(the un-prefixed `x.ai/billing` returns -32601; ext methods take a `_` wire prefix).
Verified live, ~0.4 s, no leader socket left behind:

```json
{"config":{"creditUsagePercent":49.0,
  "currentPeriod":{"type":"USAGE_PERIOD_TYPE_WEEKLY",
    "start":"2026-09-04T13:19:34Z","end":"2026-09-11T13:19:34Z"}, …}}
```

- Map `creditUsagePercent` → the single weekly window; `currentPeriod.end` →
  `resets_at`. If only legacy `monthlyLimit`/`used` fields exist, derive percent
  exactly as Grok's own pager does (vendor source: `xai-grok-pager` helpers).
- Ignore `onDemandCap`, `onDemandUsed`, `prepaidBalance`, top-up, history in v1 —
  billing/overage data, explicitly out of scope.
- The pool is **account-wide across all Grok products** (docs.x.ai FAQ; prior research
  `202608/supergrok_subscription_tiers`): the number moves when Bryan uses grok.com
  chat too. Label it as account-wide.
- `not_applicable` is a real state: vendor changelogs hide billing for API-key, free,
  and enterprise auth. The ext namespace is first-party but not a documented stable
  contract — a missing-method response degrades to `unsupported_cli_version`, not a
  traceback. Dead ends (verified): `x.ai/session/usage` is session token totals only;
  `grok.com/rest/rate-limits` rejects CLI OAuth tokens (web cookies only);
  `cli-chat-proxy` `x-ratelimit-*` headers are static advertised caps that never move.

## Architecture

Follows the pattern SASE already uses for the reactive half (epic sase-n4,
usage-limit auto-disable): provider-specific policy in Python pluggy hooks, durable
machine-wide state in the Rust core, display through a lock-free peek.

```
 durable proc (~5 min, parallel probes, per-probe timeout ~10 s)
   claude → /usage probe        codex → app-server        grok → ACP billing
        └──────────────┬──────────────┴─────────────┬──────────┘
                       ▼                            │
      sase_core::provider_usage (Rust, sibling of provider_disable.rs)
      ~/.sase/llm_provider_usage.json — locked atomic write, 0600
                       ▲                            
   record_provider_usage_observation(...)  ← rate_limit_event from
                       │                      _subprocess_claude.py (free)
        ┌──────────────┴───────────────┐
        ▼                              ▼
 peek_provider_usage() (lock-free)   sase usage list / sase doctor
        ▼
 ProviderUsageIndicator pill · Models panel → Providers section
```

**Rust/Python boundary.** The snapshot type, store, staleness rules, merge-by-window
logic, and validation are core backend logic (CLAUDE.md litmus test) →
`../sase-core/crates/sase_core/src/provider_usage.rs`, a near-copy of
`provider_disable.rs` (serde wire structs, fs2-locked atomic write, strict `from_wire`,
schema version, read-repair). Probes stay in Python provider plugins — they are
per-vendor policy, must be shippable by third-party plugins, and keeping them out of
`sase_core` avoids dragging subprocess/network deps into a crate that has none.

**The hook** (in `_hookspec.py`, beside `llm_default_usage_limit_config`, line 172):

```python
@hookspec(firstresult=True)
def llm_usage_probe(self) -> "ProviderUsageProbe | None": ...
    # Absence ⇒ status "unsupported"; implementations never raise —
    # they return a snapshot whose status describes the failure.
```

Usage is dynamic state — call the hook on the plugin instance at refresh time; it must
not enter the registry metadata cache. A separate shared
`record_provider_usage_observation(...)` path serves event-fed updates (Claude today;
any future provider whose stream carries quota).

**Wire contract** (merged from both reports):

```python
ProviderUsageSnapshot:
    version: int                 # strict on read
    provider: str
    fetched_at: float            # epoch seconds
    source: str                  # "probe" | "stream_event"
    status: str                  # "ok" | "not_applicable" | "unauthenticated"
                                 #     | "unsupported" | "error"
    account_mode: str | None     # "subscription" | "api"
    plan: str | None
    detail: str | None           # short diagnostic, never a secret
    windows: list[UsageWindow]   # unordered, keyed

UsageWindow:
    key: str                     # provider-stable id where available (codex limitId),
                                 # else derived ("session", "weekly", "weekly:fable")
    label: str
    used_percent: float          # 0–100+, THE universal field; never capped in store
    resets_at: float | None
    window_seconds: int | None
    scope: str | None            # model/product scope
    state: str                   # "allowed" | "warning" | "rejected" | "unknown"
    primary: bool                # drives the headline number
```

Never persist raw payloads, tokens, emails, or account IDs (hash any stable identity
for cache invalidation on account switch). Future token/cost/billing metrics are
additive typed sections on a later schema version — do not pre-weaken this into
key/value telemetry.

**Cache semantics** (from A): expire a window when its reset passes without a newer
observation — never reinterpret the old percent as the new window's; keep the last good
snapshot on probe failure but label it stale with a diagnostic code; coalesce
concurrent refreshes per provider (`concurrency_keys=["provider-usage-refresh"]` like
the drain proc); one broken probe never blanks the others.

**Refresh cadence:** 5 min default (floor 60 s, configurable), plus opportunistic
refresh when `handle_possible_usage_limit()` writes a disable and when a disable
expires. Total refresh wall time ≈ slowest probe ≈ 1.7 s.

**TUI surfaces** (paths verified: `src/sase/ace/tui/_app_layout.py`,
`src/sase/ace/tui/modals/models_panel_providers.py`):

1. **Top-bar pill** next to `ProviderDisablesIndicator`: each provider's `primary`
   window, e.g. `⛽ cld 25% · cdx 9% · grk 49%`, colour-ramped (warn ≥75, critical
   ≥90), `—` for any non-`ok` status (an error rendered as 0% reads as "plenty left").
   Click opens the Models panel. Reads only through the peek on the existing 30 s tick
   — never a subprocess, network call, or blocking parse on the UI thread (tui_perf
   rules; timer ticks update countdown text only).
2. **Models panel → Providers section:** every window with bar, percent remaining
   (display headroom — that is the question being asked), reset countdown, plan,
   snapshot age, source, and a precise unavailable reason; `r` submits the refresh
   proc rather than fetching inline. First paint is cache-only; re-check selection
   before applying async results.
3. **CLI** (per cli_rules): `sase usage` → `sase usage list [-j] [-p <name>] [-v]`;
   `sase usage refresh [-p <name>] [-w]`. `--json` emits the wire snapshot verbatim.
4. **`sase doctor`:** one line per provider — probe reachable, auth mode, snapshot age.

Show snapshot age whenever it exceeds ~2× cadence; grey the pill past 4×. A stale
number is worse than none, because it will be trusted.

**Config** (extend `llm_provider:` in `default_config.yml`): `usage_metrics.enabled`,
`refresh_seconds`, `warn_percent`, `critical_percent`, per-provider `enabled`.
**Feature flag:** `provider_usage_metrics` (`beta`) — user-reaching behavior landing
across phases; delete the Off branch and close the flag bead before the epic lands.

## Failure modes (design in up front)

| Failure | Handling |
|---|---|
| CLI not installed / hook absent | `unsupported`, no pill entry |
| Logged out / token expired | `unauthenticated`, pill `—` |
| API-key auth | `not_applicable`, omitted from pill |
| Claude prose wording changes | parse failure ⇒ `error`; never synthesize 0% |
| `app-server` experimental API removed / ACP method missing | `unsupported_cli_version` diagnostic, no traceback |
| Probe hangs | hard per-probe timeout (10 s), whole-refresh timeout (30 s) |
| Reset crossed without refresh | window expires; not reinterpreted |
| Account switched | identity-hash mismatch invalidates cache |
| Refresh storm (many agents finish) | concurrency-key collapse + cadence floor |

Governing rule (borrowed from `usage_limit_disable.py`): a usage pill is decoration —
a bug in this feature must never mask an error or take down an agent run.

## Why not the alternatives

- **Web scraping the three settings pages / browser cookies:** requires browser-session
  credentials on a headless server; Grok's web endpoint actively rejects CLI OAuth
  tokens (403 `oauth2-auth-forbidden`). Dead on arrival, and unnecessary.
- **Direct HTTP with tokens read from CLI credential files:** works today (B verified
  all three end-to-end), but SASE would handle credentials it shouldn't, break silently
  on token expiry (Claude's access token lives ~5 h and refreshes only when Claude Code
  runs; Grok's ~2 h; macOS keeps Claude's in Keychain), and for Claude it sits on the
  wrong side of published Anthropic policy. Not in v1; reserve as a documented,
  opt-in, honest-User-Agent (`sase/<version>`, never impersonation) contingency.
- **Harvest-only from existing agent streams:** only Claude emits quota on its stream,
  and only during real turns; Codex's `exec --json` and Grok's stream carry nothing.
  Fine as a supplement, unusable as the sole mechanism.

## Phasing

1. **Core contract + store:** `sase_core::provider_usage` + bindings + Python facade;
   `fakey` provider probe fixture so the pipeline tests with no network or vendor CLI.
2. **Hook + three probes + CLI:** `llm_usage_probe()`; implementations in `claude.py`,
   `codex.py`, `grok.py` (~60 lines each); `sase usage list`/`refresh`. Fully usable
   from the CLI here — a fine checkpoint to reassess.
3. **Claude stream capture:** `rate_limit_event` → observation path.
4. **Refresh proc** + opportunistic triggers.
5. **TUI:** pill → Models-panel section → doctor line.
6. **Flag removal** (delete Off branch, close flag bead).

Tests are fixture-driven, no live provider calls in CI: multi-bucket Codex,
legacy-shape Grok, both Claude reset-time formats, partial/malformed/extra-field
payloads, `not_applicable`/`unauthenticated` discrimination, merge-by-key, reset
expiry, stale fallback, concurrent writers, child-process cleanup, and TUI tests
proving first paint never waits and ticks never probe.

## The deliberate follow-on (out of scope for v1)

`provider_disable.rs` already has a **soft** disable mode (verified: spares a provider
in load-balanced pools without blocking explicit requests). Once `used_percent` is live
and trusted, writing a soft disable at ≥90% inverts the reactive sase-n4 epic into a
proactive one — pools drain before anyone hits the wall. Both reports agree this must
wait until the displayed numbers have earned trust; the contract's `primary` +
`used_percent` + `state` fields are designed for it. Claude's explicit
`rejected`/`allowed_warning` states and Codex's `rateLimitReachedType` are the right
future triggers — never a bare percentage threshold (Grok can continue on credits;
buckets are independent; stale snapshots cross resets).

## What would reopen this

- Anthropic ships structured usage output (`claude usage --json` or rate-limit fields
  on the print-mode envelope) — worth filing upstream; deletes the prose parser.
- `codex app-server` graduates from experimental, or is removed.
- xAI documents a stable usage API or changes the ACP ext namespace.
- A provider lands whose quota is not expressible as percent-of-window.

## Open questions for Bryan

1. **Ship HTTP fallbacks at all?** Recommendation: no — CLI-only v1; revisit if a probe
   path breaks.
2. **Pill contents:** per-provider headline percents (recommended — the point is
   choosing a provider) vs one worst-window number.
3. **Threshold notification** at 90% via `notifications/senders.py`? Cheap, easy to
   make annoying; suggest off by default.
4. **Fleet scope:** usage is account-wide, so every tailnet machine sees the same
   numbers; keep the snapshot machine-local (recommended) rather than federated.

## Sources

- Vendor source via registered external repos: `gh:openai/codex`
  (`app-server-protocol/src/protocol/v2/account.rs`, `protocol/src/protocol.rs`,
  `exec/src/exec_events.rs`, `backend-client/src/client/rate_limit_resets.rs`),
  `gh:xai-org/grok-build` (`xai-grok-shell/src/extensions/billing.rs`, `usage.rs`,
  pager helpers, changelogs).
- Live verification on athena (B's full pass; lead re-verified the Claude `/usage`
  probe and newly verified `rate_limit_event` in `-p` stream-json mode).
- [Claude Code — Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance);
  [Claude Agent SDK Python reference](https://code.claude.com/docs/en/agent-sdk/python);
  [statusline rate-limit data](https://code.claude.com/docs/en/statusline#rate-limit-usage);
  [Codex app-server docs](https://learn.chatgpt.com/docs/app-server);
  [docs.x.ai Grok FAQ](https://docs.x.ai/grok/faq);
  [anthropics/claude-code#31021](https://github.com/anthropics/claude-code/issues/31021);
  [The Register on Anthropic third-party enforcement](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/).
- Prior SASE research:
  `research:202608/supergrok_subscription_tiers/supergrok_subscription_tiers.md`.
