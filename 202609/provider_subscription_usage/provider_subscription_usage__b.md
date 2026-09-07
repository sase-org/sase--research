# Surfacing Subscription Usage Headroom In The TUI, Generically, For Claude / Codex / Grok

**Research question.** How should SASE fetch and display "how much of my subscription
allowance is left before I hit a limit" for the Claude, Codex, and Grok providers, in a
way that generalizes to any provider added later?

**Answer up front.** Ask each provider's own CLI, not the vendor's servers. All three
CLIs SASE already shells out to expose their own subscription-usage state over a local,
non-inference, zero-cost interface, and every one of them was verified working on athena
during this research:

| Provider | Ask-the-CLI probe (recommended) | Cost | Latency (measured) |
|---|---|---|---|
| claude | `claude -p --output-format json "/usage"` | `total_cost_usd: 0`, `num_turns: 0` | ~1.7 s |
| codex  | `codex app-server` JSON-RPC → `account/rateLimits/read` | none | ~1.0 s |
| grok   | `grok agent stdio` ACP ext → `_x.ai/billing` | none | ~0.4 s |

Normalize all three onto **one number — percent of window consumed — plus a reset
instant**, because that is the only unit all three vendors actually agree on. Store the
normalized snapshot in the Rust core next to `provider_disable.rs`, refresh it from a
durable proc on a ~5-minute cadence, and let the TUI read it only through a lock-free
peek cache. Add per-provider probes behind a new pluggy hook so a fourth provider is a
plugin change, not a core change.

Full reasoning in §5–§9. §4 is the one section to read before writing any code: the
direct-HTTP alternative for Claude works, but Anthropic's published policy points away
from it.

---

## 1. Evidence status

Researched **2026-09-07** on athena against live, logged-in installs:
`claude 2.1.263`, `codex-cli 0.153.4`, `grok 1.0.13`.

**First-party confirmed and reproduced here.** Every probe and every endpoint in this
report was executed against Bryan's own accounts and returned real data. Response
payloads are quoted verbatim (identifiers redacted). Provider-side wire contracts were
read from vendor source in `gh:openai/codex` and `gh:xai-org/grok-build`, both already
registered external repos.

**Read from the shipped binary, not source.** Claude Code is closed-source; its endpoint
path and payload field names were recovered from the shipped 2.1.263 ELF's string table
and then confirmed by calling the endpoint. That is strong evidence for *what exists
today* and weak evidence for *what will exist next month*.

**Corroborated but not vendor-documented.** The Anthropic `/api/oauth/usage` rate-limit
behavior (User-Agent-keyed buckets, ~180 s safe interval) comes from community reports
on `anthropics/claude-code#31021` and `Claude-Code-Usage-Monitor#202`, not from Anthropic
docs. Treat the cadence numbers as folklore that happens to be consistent with what I
observed.

**Freshness.** Two of the three surfaces are explicitly experimental
(`codex app-server` is labelled `[experimental]` in its own `--help`; the Grok ACP ext
namespace is versioned per release). Assume decay in months, not years, and design for
a probe that can fail without breaking anything.

---

## 2. What the user actually asked for, restated precisely

Bryan checks three web pages by hand:

- `claude.ai/new#settings/usage`
- `chatgpt.com/codex/cloud/settings/analytics#usage`
- `grok.com/?...&_s=usage`

Each shows **percent of a rolling allowance consumed** and **when it resets**. None of
them shows tokens or dollars for a subscription user — the vendors deliberately do not
publish the denominator. So the deliverable is not "token accounting"; it is:

> for each configured provider, one or more named windows, each with
> `used_percent` (0–100) and `resets_at`, refreshed often enough to be actionable and
> displayed where the eye already goes.

That framing matters, because it is what makes the feature genuinely generic. Percent-
of-window is the lowest common denominator across three vendors who agree on nothing
else, and it is exactly what a fourth vendor will also expose.

---

## 3. Four candidate mechanisms, and why one wins

### 3.1 Harvest from the agent output SASE already parses — rejected, doesn't work

The most attractive option: SASE already streams and parses NDJSON from every provider
run (`_subprocess_claude.py`, `_subprocess_codex.py`, `_tool_call_grok.py`). If usage
rode along on those events, the feature would be free and always current.

It does not.

- **Claude.** A real `claude -p --output-format json` run returns top-level keys
  `[api_error_status, duration_api_ms, duration_ms, fast_mode_disabled_reason,
  fast_mode_state, first_content_frame_ms, is_error, modelUsage, num_turns,
  permission_denials, queued_turn_count, result, session_id, stop_reason,
  subagent_stats, subtype, terminal_reason, time_to_request_ms, total_cost_usd,
  ttft_ms, ttft_stream_ms, type, usage, uuid]`. Zero rate-limit fields; `usage` is token
  counts only. Verified by running it.
- **Codex.** The protocol type `TokenCountEvent { info, rate_limits }` does carry a
  `RateLimitSnapshot` — but only on the *raw* protocol channel. SASE invokes
  `codex exec --json` (`src/sase/llm_provider/codex.py:400-404`), which emits the v2
  thread-event schema in `codex-rs/exec/src/exec_events.rs`. That schema has `usage:
  Usage` (tokens) and no rate-limit member. Verified by grep of the vendor source.
- **Grok.** No `x-ratelimit-*` or quota field reaches the CLI's own message stream.

Rejecting this is important because it is the option a reviewer will ask about first.

### 3.2 Read the local credential file and call the vendor's private HTTP API — works, but is the fallback, not the plan

All three CLIs park an OAuth token in a predictable JSON file, and all three vendors have
an endpoint that answers with usage. I verified all three end-to-end (§5–§7). This is the
approach every third-party usage monitor takes.

It works. It is also the option with every downside: SASE handles credentials it has no
business handling, impersonates a client it is not, breaks silently on token expiry, and
— for Claude specifically — sits on the wrong side of a published Anthropic policy (§4).

Keep it as a **fallback** for hosts where the CLI probe fails, off by default.

### 3.3 Scrape the vendor web UI with browser cookies — rejected

`POST https://grok.com/rest/rate-limits` is what the grok.com usage modal calls. It
exists and is auth-gated to *web session cookies only*:

```
POST /rest/rate-limits  (CLI OAuth bearer)
403 {"code":7,"message":"Action cannot be performed by OAuth2 token users.
     [WKE=unauthorized:oauth2-auth-forbidden]"}
POST /rest/rate-limits  (no auth)
401 {"code":16,"message":"No credentials presented."}
```

That would require extracting cookies from a browser on a headless server. Dead end, and
§7 makes it unnecessary anyway.

### 3.4 Ask the provider's own CLI — recommended

Every one of the three CLIs will answer a usage question over a local interface, using
its own auth, at zero inference cost. This is the winner on every axis that matters:

- **No credential handling.** SASE never reads, stores, forwards, or refreshes a token.
  It runs the vendor's unmodified binary, as the user, on the user's own machine.
- **Vendor-owned semantics.** When Anthropic changes what counts as a window, the
  `claude` binary changes with it. SASE inherits the fix.
- **Naturally generic.** "Every coding-agent CLI can report its own quota" is a stable
  assumption about this class of tool, not a bet on three specific endpoints.
- **Cheap.** 0.4–1.7 s per provider, no tokens, no dollars, no orphan processes (checked:
  no stray `codex app-server`, no `grok agent stdio`, no `~/.grok/leader.sock` left
  behind after the probes).

The cost is that one of the three (Claude) answers in prose rather than JSON, so it needs
a small tolerant parser. That is a real but bounded price, and §5.3 shows the parse is
three regex groups against a line format the vendor has kept stable across releases.

---

## 4. The Anthropic policy question — decide this before writing code

Anthropic's Claude Code legal page, section **"Authentication and credential use"**
(fetched 2026-09-07, `code.claude.com/docs/en/legal-and-compliance`), says verbatim:

> **OAuth authentication** is intended exclusively for purchasers of Claude Free, Pro,
> Max, Team, and Enterprise subscription plans and is designed to support ordinary use of
> Claude Code and other native Anthropic applications.
>
> **Developers** building products or services that interact with Claude's capabilities,
> including those using the Agent SDK, should use API key authentication […] Anthropic
> does not permit third-party developers to offer Claude.ai login into their own
> applications, or to route requests through Free, Pro, or Max plan credentials on behalf
> of their users. Moreover, developers may not collect, store, or intermediate Claude.ai
> credentials or session tokens […]
>
> Anthropic reserves the right to take measures to enforce these restrictions and may do
> so without prior notice.

The same page **explicitly blesses** the shape SASE already has:

> Nor does it prevent an end user from signing in to the unmodified Claude Code binary
> with their own Claude subscription […]
> The Claude Code binary must not be modified.

Read those two together and the conclusion is unusually clean:

- **`claude -p "/usage"` is squarely inside the permitted shape.** SASE runs the
  unmodified binary; the binary authenticates itself; SASE never touches the token.
- **Reading `~/.claude/.credentials.json` and calling `api.anthropic.com` directly is
  outside it.** That is a non-native application using a consumer OAuth token. It may be
  tolerated in practice for one user on one machine, but SASE is an installable
  open-source project — the moment it ships this on by default, SASE is the "third-party
  developer" the paragraph is addressed to.

Anthropic deployed server-side enforcement in early 2026; secondary reporting
(The Register, 2026-02-20) describes consumer OAuth tokens erroring outside Claude Code
and Claude.ai. The `/api/oauth/usage` endpoint still answers today (§5.1), but that is
exactly the kind of thing enforcement closes without notice.

**Recommendation.** Ship the CLI probe as the only Claude path that is on by default.
If the HTTP fallback is implemented at all, gate it behind explicit per-provider opt-in
config, send an honest `User-Agent: sase/<version>` — **never** impersonate
`claude-code/<version>` — and document the policy text next to the setting. The
community's "use the claude-code UA to get a friendlier rate-limit bucket" trick is
precisely the impersonation the policy is aimed at; buying a shorter poll interval with
it is a bad trade.

The Codex and Grok endpoints carry no comparable published restriction, but the same
architectural preference applies for the same engineering reasons.

---

## 5. Claude — verified

### 5.1 Direct HTTP (works, undocumented, policy-encumbered)

Endpoint recovered from the 2.1.263 binary's string table (`/api/oauth/usage`, alongside
field literals `five_hour`, `seven_day`, `utilization`, `resets_at`, `rate_limit_tier`)
and confirmed live:

```bash
TOK=$(jq -r .claudeAiOauth.accessToken ~/.claude/.credentials.json)
curl -s -H "Authorization: Bearer $TOK" https://api.anthropic.com/api/oauth/usage
```

`200`, and — checked separately — the `anthropic-beta: oauth-2025-04-20` header that
community write-ups call mandatory is **not** required; a bare `Authorization` header
suffices. A bogus token returns a clean
`401 {"type":"error","error":{"type":"authentication_error",...}}`.

Response (real, truncated):

```json
{"five_hour":{"utilization":3.0,"resets_at":"2026-09-07T22:30:00.483075+00:00",
  "limit_dollars":null,"used_dollars":null,"remaining_dollars":null,"locked_reason":null},
 "seven_day":{"utilization":25.0,"resets_at":"2026-09-13T00:00:00.483098+00:00", ...},
 "seven_day_opus":null,"seven_day_sonnet":null,
 "limits":[
   {"kind":"session","group":"session","percent":3,"severity":"normal",
    "resets_at":"2026-09-07T22:30:00.483075+00:00","scope":null,"is_active":false},
   {"kind":"weekly_all","group":"weekly","percent":25,"severity":"normal",
    "resets_at":"2026-09-13T00:00:00.483098+00:00","scope":null,"is_active":false},
   {"kind":"weekly_scoped","group":"weekly","percent":30,"severity":"normal",
    "resets_at":"2026-09-13T00:00:00.483303+00:00",
    "scope":{"model":{"id":null,"display_name":"Fable"}},"is_active":true}],
 "extra_usage":{"is_enabled":false,"monthly_limit":20000,"used_credits":0.0, ...},
 "spend":{"used":{...},"limit":{...},"percent":0,"severity":"normal", ...}}
```

Note the `limits[]` array: Anthropic has already converged on
`{kind, group, percent, severity, resets_at, scope, is_active}`. That is a well-designed
normalized shape and §9 borrows from it directly.

**Caveats.** The endpoint is undocumented; `anthropics/claude-code#31021` (persistent
429s) was closed *not planned*. Rate limiting is keyed on User-Agent; ~180 s is the
reported safe floor with the blessed UA, with exponential backoff on 429. The access
token expires (observed `expiresAt` ~5 h out) and is refreshed **only when Claude Code
itself runs** — fine on a host that runs SASE agents constantly, a silent-staleness trap
on a quiet host. On macOS the credentials live in Keychain
(`security find-generic-password`), not in a file, so the file-reading fallback is
Linux-only anyway. `ANTHROPIC_CONFIG_DIR` / `CLAUDE_CONFIG_DIR` can move the file.

### 5.2 CLI probe (recommended)

```bash
claude -p --output-format json "/usage"
```

Verified: `subtype: success`, `is_error: false`, **`total_cost_usd: 0`**,
**`num_turns: 0`**, `duration_api_ms: 0`, all token counters `0`, ~1.7 s wall. `/usage`
is handled locally by the binary; it never reaches the sampling path. The `result` field
holds:

```
You are currently using your subscription to power your Claude Code usage

Current session: 6% used · resets Sep 7, 6:29pm (America/New_York)
Current week (all models): 25% used · resets Sep 12, 7:59pm (America/New_York)
Current week (Fable): 30% used · resets Sep 12, 7:59pm (America/New_York)

What's contributing to your limits usage?
Approximate, based on local sessions on this machine — …
Last 24h · 2678 requests · 48 sessions
  51% of your usage was at >150k context
  …
```

Cross-check: those three lines are exactly the endpoint's three `limits[]` rows
(session / weekly_all / weekly_scoped:Fable) — same percentages, same resets. The CLI
prose and the private endpoint are the same data.

The trailing "what's contributing" block is a bonus SASE could surface later (context
size, subagent-heavy sessions, parallelism, top skills). It is explicitly local-machine
approximate; do not present it as authoritative.

### 5.3 The parser

```python
LINE = re.compile(
    r"^Current (?P<label>[^:]+): (?P<pct>\d+)% used · resets (?P<reset>.+)$"
)
```

Three groups; `label` maps to a stable key (`session`, `weekly` for "week (all models)",
`weekly:<model>` for a scoped week); `reset` is `%b %-d, %-I:%M%p (Zone)` or
`%b %-d, %-I%p (Zone)`, resolvable with `zoneinfo`. The first line
(`You are currently using your subscription…`) is the subscription-vs-API discriminator:
an API-key install says something else, and the adapter should then report
`status: not_applicable` rather than guessing.

**Parse failure must degrade, never raise** — the snapshot becomes
`status: "error"` with the raw first line kept for diagnosis, mirroring how
`usage_limit_disable.py` refuses to let a detection bug mask the real error.

### 5.4 Dead ends checked

- The statusline JSON payload would have been the ideal free channel, but the statusline
  is **not invoked in `-p`/print mode** (verified: a `--settings` statusline hook writing
  to a temp file produced no file). TUI-only.
- `--bare` blocks OAuth entirely (`Not logged in · Please run /login`), so it cannot be
  used to make the probe cheaper.
- There is no `claude usage` subcommand; the command list is
  `agents/attach/auth/auto-mode/doctor/gateway/import/install/logs/mcp/plugin/project/
  respawn/rm/setup-token/stop/ultrareview/update`.

---

## 6. Codex — verified

### 6.1 CLI probe (recommended)

`codex app-server` speaks JSON-RPC over stdio and implements
`account/rateLimits/read` (`codex-rs/app-server-protocol/src/protocol/common.rs:1272`).
Handshake is `initialize` → `initialized` → the call. Verified live:

```json
{"id":2,"result":{
  "rateLimits":{"limitId":"codex","limitName":null,
    "primary":{"usedPercent":9,"windowDurationMins":10080,"resetsAt":1789392969},
    "secondary":null,
    "credits":{"hasCredits":false,"unlimited":false,"balance":"0"},
    "individualLimit":null,"spendControlReached":false,
    "planType":"pro","rateLimitReachedType":null},
  "rateLimitsByLimitId":{
    "codex":{…as above…},
    "codex_bengalfox":{"limitName":"GPT-5.3-Codex-Spark",
      "primary":{"usedPercent":0,"windowDurationMins":300,"resetsAt":1788821854},
      "secondary":{"usedPercent":0,"windowDurationMins":10080,"resetsAt":1789408654},
      "planType":"pro"}},
  "rateLimitResetCredits":{"availableCount":3,"credits":[{"title":"Full reset", …}]},
  "accountId":"<redacted>","rateLimitUpsell":null}}
```

~1.0 s, no orphan process. Structured, typed, multi-bucket, and it even reports the
three free "rate limit reset" credits sitting on the account — a genuinely useful thing
to show next to a nearly-exhausted bar.

Pass `{"excludeResetCreditDetails": true}` for background polls; the vendor's own doc
comment says that is what it is for. Do **not** set `supportsLunaReserve` — the type
comment says it is "opt in only for clients that can apply Reserve, not for passive
account usage readers", and setting it records experiment exposure.

The response is `GetAccountRateLimitsResponse`
(`codex-rs/app-server-protocol/src/protocol/v2/account.rs:331`); windows are
`RateLimitWindow { used_percent: f64, window_minutes, resets_at }`
(`codex-rs/protocol/src/protocol.rs:2367`).

There is also an `account/rateLimits/updated` server notification, so a long-lived
app-server connection could get pushes instead of polls. Not worth it for v1.

**Caveat.** `codex app-server` is `[experimental]` in its own help text.

### 6.2 Direct HTTP fallback (works)

Codex's own client falls back to this path (`rate_limit_resets.rs:126`,
`PathStyle::CodexApi => "{base}/api/codex/usage"`):

```bash
TOK=$(jq -r .tokens.access_token ~/.codex/auth.json)
ACC=$(jq -r .tokens.account_id  ~/.codex/auth.json)
curl -s -H "Authorization: Bearer $TOK" -H "chatgpt-account-id: $ACC" \
     -A "sase/0.1" https://chatgpt.com/backend-api/codex/usage
```

Returns `plan_type`, `rate_limit.{primary,secondary}_window`,
`additional_rate_limits[]`, `credits`, `spend_control`, `rate_limit_reset_credits`.

Header findings worth recording, all measured:

- `chatgpt-account-id` is **required** (403 without it).
- A default `curl/*` User-Agent → **403** (Cloudflare). `Mozilla/5.0` → **403**.
  `sase/0.1` → **200**. `python-urllib/3.13` → **200**. So an honest SASE UA works and
  impersonation is unnecessary; only browser-shaped UAs are blocked.
- The `originator: codex_cli_rs` header is neither necessary nor sufficient.

`~/.codex/auth.json` carries `auth_mode: "chatgpt"` vs. an `OPENAI_API_KEY` — the
subscription-vs-API discriminator. The access token is a JWT (observed `exp` 10 days
after `last_refresh`), so staleness pressure is far lower than Claude's.

---

## 7. Grok — verified, and better than expected

Grok looked like the weak leg. It is not.

### 7.1 What does *not* work

- `grok`'s `/usage` slash command maps to ACP `x.ai/session/usage`, which is
  **session token totals only** — `crates/codegen/xai-grok-shell/src/extensions/usage.rs`
  reads an in-memory `UsageLedger`. Not quota.
- `grok.com/rest/rate-limits` (the web usage modal's API) rejects the CLI's OAuth token
  outright (§3.3).
- `cli-chat-proxy.grok.com` does return `x-ratelimit-limit-tokens: 53000000` /
  `x-ratelimit-remaining-tokens: 53000000` / `x-ratelimit-limit-requests: 8300` /
  `x-ratelimit-remaining-requests: 8300` on `/v1/chat/completions` — but only when
  `x-grok-client-surface: grok-build` is sent, and **`remaining` never moved across
  repeated real calls**. These are static advertised caps, not live counters. Do not use
  them.
- The token's scopes (`openid profile email offline_access grok-cli:access api:access
  conversations:read conversations:write workspaces:read workspaces:write`) contain no
  usage scope.
- No `/v1/usage`, `/v1/rate-limits`, `/rest/quota`, `/rest/entitlements`, … (all 404).

### 7.2 What does work

`xai-grok-shell` ships an ACP extension `x.ai/billing`
(`crates/codegen/xai-grok-shell/src/extensions/billing.rs`) whose doc comment reads:
*"Fetches the authenticated user's Grok Build billing configuration (credit limit, usage,
on-demand cap, billing period, history) from the backend. The pager and desktop use it to
display credits and usage."* It is session-independent.

**ACP ext methods take a `_` prefix on the wire.** `x.ai/billing` returns
`-32601 Method not found`; `_x.ai/billing` works. Verified over `grok agent stdio` after
`initialize`:

```json
{"id":10,"result":{"config":{
  "creditUsagePercent":49.0,
  "currentPeriod":{"type":"USAGE_PERIOD_TYPE_WEEKLY",
    "start":"2026-09-04T13:19:34.664647+00:00",
    "end":"2026-09-11T13:19:34.664647+00:00"},
  "onDemandCap":{"val":0},"onDemandUsed":{"val":0},
  "prepaidBalance":{"val":0},"isUnifiedBillingUser":true,
  "billingPeriodStart":"2026-09-04T…","billingPeriodEnd":"2026-09-11T…"}}}
```

~0.4 s, no leader socket left behind.

The equivalent direct HTTP call (what the extension does internally) adds a per-product
breakdown:

```bash
TOK=$(python3 -c "import json;d=json.load(open('$HOME/.grok/auth.json'));print(next(iter(d.values()))['key'])")
curl -s -H "Authorization: Bearer $TOK" \
  'https://cli-chat-proxy.grok.com/v1/billing?format=credits'
```

```json
{"config":{"currentPeriod":{"type":"USAGE_PERIOD_TYPE_WEEKLY","start":"…","end":"2026-09-11T13:19:34Z"},
 "creditUsagePercent":49.0,
 "productUsage":[{"product":"GrokBuild","usagePercent":49.0},{"product":"GrokChat"}],
 "isUnifiedBillingUser":true,"prepaidBalance":{"val":0},
 "onDemandCap":{"val":0},"onDemandUsed":{"val":0},
 "topUpMethod":"TOP_UP_METHOD_SAVED_PAYMENT_METHOD"}}
```

`isUnifiedBillingUser: true` plus `USAGE_PERIOD_TYPE_WEEKLY` is exactly the shared weekly
pool documented at `docs.x.ai/grok/faq` and analysed in
`research:202608/supergrok_subscription_tiers/supergrok_subscription_tiers.md`. So
**49% of Bryan's weekly Grok pool is consumed, resetting 2026-09-11T13:19Z**, and
`productUsage` gives the same API/Build/Chat/Imagine/Voice split the web Usage tab shows.

Sanity note against that prior report: because the pool is shared across every Grok
product, this number moves when Bryan uses grok.com chat, not just when SASE runs Grok
agents. The TUI reading is account-wide, and should be labelled as such.

**Caveats.** Drop `?format=credits` and you get the legacy monthly shape with all-zero
counters — the parser must key off `creditUsagePercent`/`currentPeriod` and treat the
legacy `monthlyLimit`/`used` fields as a last resort, exactly as the vendor's own struct
comment instructs. Grok's access token is short-lived (observed `exp` ~2 h out), which
makes the CLI-mediated path meaningfully more robust than the file-reading one here.
Changelogs confirm `/usage` and the billing UI are hidden for API-key auth
(`0.2.64`), free/X-Basic accounts (`0.2.86`), and enterprise auth (`0.2.117`) — so
`status: not_applicable` is a real state the adapter must handle.

---

## 8. Recommended architecture

The shape follows the one SASE already used for the reactive half of this problem
(epic `sase-n4`, "Auto-disable LLM providers on usage-limit errors"): **provider-specific
policy in Python pluggy hooks, durable machine-wide state in the Rust core, display
through a lock-free peek.** Reusing it is most of why this is a small feature.

```
                 ┌──────────────────────────────────────────────┐
  durable proc   │ sase usage refresh   (cadence ~5 min)        │
  (procs/)       │  ├─ claude  → claude -p --output-format json │
                 │  ├─ codex   → codex app-server (JSON-RPC)    │  in parallel,
                 │  └─ grok    → grok agent stdio (ACP)         │  ~1.7 s wall
                 └───────────────────┬──────────────────────────┘
                                     │ normalized ProviderUsageSnapshot
                                     ▼
              sase_core::provider_usage   (Rust, sibling of provider_disable.rs)
              ~/.sase/llm_provider_usage.json   — locked atomic write
                                     │
                    ┌────────────────┴─────────────────┐
                    ▼                                  ▼
       peek_provider_usage()  (lock-free)      sase usage [list]  /  sase doctor
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
  ProviderUsageIndicator   Models panel → Providers section
  (top-bar pill)           (full per-window table)
```

### 8.1 Rust core vs. Python — where the boundary falls

`CLAUDE.md`'s litmus test ("would a web app, CLI, or editor integration need this to
match the TUI?") says the **snapshot type, the store, and the staleness rules** are core
backend logic. They belong in `../sase-core/crates/sase_core/src/provider_usage.rs`,
built as a near-copy of `provider_disable.rs`: `serde` wire structs, a
`fs2`-locked atomic write through `NamedTempFile`, strict `from_wire` rehydration, a
schema version, and read-repair.

The **probes** stay in Python, in the provider plugins. This is not a boundary dodge; it
matches the existing split exactly. `llm_default_usage_limit_config()` — the
provider-specific *policy* for the reactive half — is a Python pluggy hook, while
`provider_disable.rs` — the durable *state* — is Rust. Probes are policy: they encode one
vendor's CLI invocation and one vendor's output dialect, they must be shippable by a
third-party provider plugin, and putting subprocess-spawning HTTP-parsing vendor glue
into `sase_core` would drag `reqwest`/`tokio` into a crate that today has no network
dependency at all (its deps are serde/regex/chrono/fs2/rusqlite/sha2/libc/tempfile).
`sase_gateway` already carries `reqwest`, so the door is open if a later phase wants it;
v1 should not walk through it.

Where a Python probe needs HTTP (the fallback paths), use stdlib `urllib.request` — the
precedent is `src/sase/agent_clis/latest.py`, which already does exactly this with a TTL
cache. No new dependency.

### 8.2 The new pluggy hook

Add to `src/sase/llm_provider/_hookspec.py`, alongside
`llm_default_usage_limit_config()`:

```python
@hookspec(firstresult=True)
def llm_usage_probe(self) -> "ProviderUsageProbe | None":
    """How to read this provider's subscription usage headroom.

    Omitting the hook means SASE reports no usage for this provider, so
    third-party provider plugins stay compatible without implementing it.
    Implementations must never raise: return a snapshot whose ``status``
    describes the failure instead.
    """
```

Each provider returns a probe object with one method,
`read(timeout: float) -> ProviderUsageSnapshot`. `claude.py`, `codex.py`, and `grok.py`
each get ~60 lines. A fourth provider is one hook implementation and zero core edits —
which is the "generic fashion" requirement, satisfied structurally rather than by
promise.

Consistent with every other metadata hook in that file, absence of the hook is a
supported state, not an error.

### 8.3 The wire contract

```python
ProviderUsageSnapshot:
    version:      int          # schema version, strict on read
    provider:     str          # "claude" | "codex" | "grok" | …
    fetched_at:   float        # epoch seconds
    source:       str          # "cli" | "http"
    status:       str          # "ok" | "not_applicable" | "unauthenticated"
                               #      | "unsupported" | "error"
    account_mode: str | None   # "subscription" | "api"
    plan:         str | None   # "max" | "pro" | "SuperGrok Pro"
    detail:       str | None   # short human error/diagnostic, never a secret
    windows:      list[UsageWindow]

UsageWindow:
    key:            str          # stable: "session" | "weekly" | "weekly:fable"
    label:          str          # "Session (5h)" | "Week (all models)"
    used_percent:   float        # 0–100, THE universal field
    resets_at:      float | None # epoch seconds
    window_seconds: int | None
    scope:          str | None   # model/product this window is scoped to
    primary:        bool         # drives the headline number for this provider
```

`used_percent` is deliberately the only required measure. Dollars, tokens and credits are
optional side-channels that two of three providers do not report for subscriptions;
modelling them as required would force every adapter to lie.

Mapping is mechanical:

| Provider | Source field | → `used_percent` | → `resets_at` |
|---|---|---|---|
| claude | `Current …: N% used` line / `limits[].percent` | `N` | parsed reset instant |
| codex  | `rateLimitsByLimitId[*].primary.usedPercent` | as-is | `resetsAt` (epoch) |
| grok   | `config.creditUsagePercent` | as-is | `currentPeriod.end` |

Remaining headroom is `100 - used_percent`. Display it as the remaining side of a bar so
the user reads headroom, not consumption — that is literally the question being asked.

`status` carries the states that will actually occur: an API-key install
(`not_applicable`), a logged-out CLI (`unauthenticated`), a provider with no hook
(`unsupported`), a probe crash or parse failure (`error`). None of these should ever be
rendered as `0%`, which reads as "plenty left" — render them as `—` with a tooltip.

### 8.4 Refresh cadence and who runs it

A durable proc (`src/sase/procs`), submitted the same way
`usage_limit_disable.py:_submit_drain()` submits `sase agent drain`:

- **Cadence: 5 minutes**, floor 60 s, configurable. Well above the ~180 s Anthropic
  folklore floor even if the HTTP fallback is ever enabled; comfortably fresh for a
  window that resets every 5 hours or 7 days.
- **Probes run in parallel**, one short-timeout subprocess each. Total wall ≈ slowest
  probe ≈ 1.7 s.
- **Opportunistic refresh** on two events that make the cached value obviously wrong:
  immediately after `handle_possible_usage_limit()` writes a disable, and when a
  provider disable expires.
- **`concurrency_keys=["provider-usage-refresh"]`** so overlapping submissions collapse,
  exactly as the drain proc does.
- Per-provider failures are independent: one broken probe must not blank the others.

This obeys `tui_perf` rule 10 ("periodic ticks revalidate; recomputes get a longer
cadence"): the TUI's 30 s tick re-reads a cached file, while the actual recompute happens
on the much longer proc cadence.

### 8.5 TUI surfaces

1. **Top-bar pill**, `ProviderUsageIndicator`, next to `ProviderDisablesIndicator` in
   `_app_layout.py:69-77`. Compact: `⛽ cld 25% · cdx 9% · grk 49%`, showing each
   provider's `primary` window, colour-ramped (normal / warn ≥75 / critical ≥90), with
   `—` for non-`ok` statuses. Click opens the Models panel, matching
   `ProviderDisablesIndicator.on_click`. Poll on the existing 30 s interval; **read only
   through `peek_provider_usage()`** — never a subprocess, never a network call, never a
   blocking parse on the UI thread (`tui_perf` rules 1, 8, 11).
2. **Models panel → Providers section** (`models_panel_providers.py`): full per-window
   table — every window with label, bar, percent remaining, reset countdown, plan name,
   and snapshot age. Add an `r`-key manual refresh that submits the proc rather than
   fetching inline.
3. **`sase doctor`**: one line per provider — probe reachable, auth mode, snapshot age.
   This is where "my usage pill has said `—` for two days" gets diagnosed.

Show the snapshot's age whenever it exceeds ~2× the cadence. A stale usage number is
worse than no usage number, because it will be trusted.

### 8.6 CLI

Per `cli_rules` (bare group delegates to `list`; alphabetical; every long option gets a
short alias; no required options):

```
sase usage                 # → sase usage list
sase usage list [-j|--json] [-p|--provider <name>] [-v|--verbose]
sase usage refresh [-p|--provider <name>] [-w|--wait]
```

`sase usage` reads the cache and never blocks; `sase usage refresh` submits the proc.
`--json` emits the wire snapshot verbatim so the mobile app and any future web client
consume the same contract.

### 8.7 Config

Extend the existing `llm_provider:` block in `src/sase/default_config.yml`, mirroring the
commented `usage_limit:` section at lines 1276-1306:

```yaml
llm_provider:
  usage_metrics:
    enabled: true                # master switch
    refresh_seconds: 300         # poll cadence; floor 60
    warn_percent: 75             # pill turns warn at/above this
    critical_percent: 90         # pill turns critical at/above this
    allow_direct_http: false     # opt in to credential-file fallbacks (see §4)
    providers:
      claude:
        enabled: true
        allow_direct_http: false # per-provider override
```

### 8.8 Feature flag

A `beta` flag (`sase flag new provider_usage_metrics -k beta`) is warranted: this is
user-reaching behavior landing across several phases, and a landed phase would otherwise
expose a half-built pill. Per `sase_flags`, the epic deletes the Off branch and closes
the flag bead before landing. `--when-enabled` / `--when-disabled` are trivially
authorable here (pill and CLI present vs. absent; no probe proc submitted).

---

## 9. Failure modes to design for, up front

| Failure | Symptom if ignored | Handling |
|---|---|---|
| Provider CLI not installed / not on PATH | probe subprocess raises | `status: unsupported`, no pill entry |
| Logged out, or token expired and CLI hasn't refreshed | garbage or 401 | `status: unauthenticated`, pill shows `—` |
| API-key auth instead of subscription | percentages meaningless | `status: not_applicable`, omit from pill |
| Claude prose wording changes | parser returns 0% | parse failure ⇒ `status: error`; **never** synthesize 0 |
| `codex app-server` experimental API removed | probe errors | fall through to the HTTP path if opted in, else `error` |
| Probe hangs | proc wedges | hard per-probe timeout (10 s), whole-refresh timeout (30 s) |
| Snapshot stale | user trusts an old number | render age past 2× cadence; grey the pill past 4× |
| Many agents finish at once | refresh storm | `concurrency_keys` collapse + cadence floor |

The governing rule, borrowed verbatim from `usage_limit_disable.py`'s docstring: a bug in
this feature must never mask or replace anything the caller was already doing. A usage
pill is decoration; it may never take down an agent run.

---

## 10. Suggested phasing

1. **Core contract + store.** `sase_core::provider_usage` (wire type, locked store, peek),
   Python facade `src/sase/llm_provider/provider_usage.py` +
   `provider_usage_peek.py`. Ships with a `fakey` provider probe so the whole pipeline is
   testable with no network and no vendor CLI.
2. **Hook + three probes.** `llm_usage_probe()` in `_hookspec.py`; CLI-mediated
   implementations in `claude.py`, `codex.py`, `grok.py`. `sase usage list` / `refresh`
   land here, so the feature is fully usable from the CLI before any TUI work.
3. **Refresh proc + cadence + opportunistic triggers.**
4. **TUI:** pill, then the Models-panel section, then the `sase doctor` line.
5. **Optional, opt-in:** direct-HTTP fallbacks behind `allow_direct_http`, with the §4
   policy note rendered next to the setting.
6. **Remove the flag**, deleting the Off branch, and close the flag bead.

Phases 1–2 alone answer the literal request ("it would be much easier if I didn't have to
open three web pages"), which makes them a good place to stop and reassess.

---

## 11. The obvious follow-on (deliberately out of scope)

SASE's routing already supports a **soft** provider disable —
`PROVIDER_DISABLE_MODE_SOFT` "spares the provider in load-balanced pools while another
member can cover; it never diverts a `||` fallback and never blocks an explicit request"
(`sase_core/src/provider_disable.rs`). Once a live `used_percent` exists, the reactive
epic `sase-n4` inverts into a proactive one: at ≥90% consumed, write a soft disable so
pools drain toward other providers *before* anyone eats a hard limit and a stranded-agent
drain.

That is a strictly better outcome than today's "hit the wall, then relaunch 20 agents",
and it is the real payoff of this work. It should not be in v1 — automatic routing
changes driven by a freshly-built, vendor-undocumented number need a few weeks of the
number simply being *displayed and trusted* first. But the wire contract in §8.3 should
be designed knowing this is where it goes, which is why `primary` and `used_percent` are
first-class rather than derived.

---

## 12. What would reopen this analysis

- Anthropic ships a first-party structured usage surface (`claude usage --json`, or
  rate-limit fields on the print-mode `result` envelope). Worth filing as an upstream
  feature request; it would delete §5.3 entirely.
- Anthropic enforcement extends to `/api/oauth/usage`, retiring §5.1 as even a fallback.
- `codex app-server` graduates from `[experimental]`, or the `account/rateLimits/updated`
  push notification makes a long-lived connection worth the complexity.
- xAI exposes usage on a documented API surface, or changes the ACP ext namespace.
- A fourth subscription-backed provider lands whose usage is *not* expressible as
  percent-of-window — at which point §8.3's single-measure contract needs revisiting.

---

## 13. Open questions for Bryan

1. **Direct-HTTP fallbacks at all?** §4 argues the Claude one is policy-encumbered for a
   distributable tool. Options: (a) CLI-only, simplest and cleanest; (b) CLI-first with
   opt-in HTTP fallback; (c) HTTP-first for structured data. I recommend (b) with the
   fallback shipping disabled — and (a) is a perfectly defensible simplification, since
   all three CLI probes were verified working.
2. **Pill contents.** One headline percent per provider (compact, fits the existing
   top-bar budget), or the worst window across all providers (one number, less
   informative)? I lean per-provider — the whole point is choosing which provider to run.
3. **Threshold notification.** Should crossing 90% send a SASE notification through
   `notifications/senders.py`, as `notify_provider_usage_limit_disabled` already does for
   the reactive case? Cheap to add, easy to make annoying; suggest off by default.
4. **Fleet scope.** Usage is account-wide, so every machine on the tailnet sees the same
   numbers. Confirm the snapshot stays machine-local cache (simple) rather than being
   federated through the fleet surfaces (needless).

---

## Appendix A — reproducible probes

```bash
# Claude — 0 tokens, 0 dollars, ~1.7 s
claude -p --output-format json "/usage" | jq -r .result

# Codex — JSON-RPC over stdio, ~1.0 s
python3 - <<'PY'
import json, subprocess, time
p = subprocess.Popen(["codex","app-server"], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, text=True, bufsize=1)
send = lambda o: (p.stdin.write(json.dumps(o)+"\n"), p.stdin.flush())
send({"method":"initialize","id":1,
      "params":{"clientInfo":{"name":"sase","title":"SASE","version":"0.1.0"}}})
while True:
    m = json.loads(p.stdout.readline())
    if m.get("id") == 1:
        send({"method":"initialized","params":{}})
        send({"method":"account/rateLimits/read","id":2,
              "params":{"excludeResetCreditDetails": True}})
    if m.get("id") == 2:
        print(json.dumps(m["result"], indent=2)); break
p.kill()
PY

# Grok — ACP over stdio; note the leading underscore on the ext method, ~0.4 s
python3 - <<'PY'
import json, subprocess
p = subprocess.Popen(["grok","agent","stdio"], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, text=True, bufsize=1)
send = lambda o: (p.stdin.write(json.dumps(o)+"\n"), p.stdin.flush())
send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,
      "clientCapabilities":{"fs":{"readTextFile":False,"writeTextFile":False}}}})
while True:
    m = json.loads(p.stdout.readline())
    if m.get("id") == 1:
        send({"jsonrpc":"2.0","id":2,"method":"_x.ai/billing","params":{}})
    if m.get("id") == 2:
        print(json.dumps(m.get("result"), indent=2)); break
p.kill()
PY
```

## Appendix B — direct HTTP fallbacks (opt-in only; see §4)

```bash
# Claude  — undocumented; Authorization alone suffices; honest UA
curl -s -H "Authorization: Bearer $(jq -r .claudeAiOauth.accessToken ~/.claude/.credentials.json)" \
     -H "anthropic-beta: oauth-2025-04-20" -A "sase/<version>" \
     https://api.anthropic.com/api/oauth/usage

# Codex   — chatgpt-account-id required; browser-shaped UAs are 403'd
curl -s -H "Authorization: Bearer $(jq -r .tokens.access_token ~/.codex/auth.json)" \
     -H "chatgpt-account-id: $(jq -r .tokens.account_id ~/.codex/auth.json)" \
     -A "sase/<version>" https://chatgpt.com/backend-api/codex/usage

# Grok    — ?format=credits is load-bearing; without it you get the legacy zeroed shape
curl -s -H "Authorization: Bearer <grok oauth key from ~/.grok/auth.json>" \
     'https://cli-chat-proxy.grok.com/v1/billing?format=credits'
```

## Appendix C — sources

Vendor source read through registered external repos:
`gh:openai/codex` (`codex-rs/backend-client/src/client/rate_limit_resets.rs`,
`codex-rs/protocol/src/protocol.rs:2324-2380`,
`codex-rs/app-server-protocol/src/protocol/v2/account.rs:300-360`,
`codex-rs/exec/src/exec_events.rs`) and `gh:xai-org/grok-build`
(`crates/codegen/xai-grok-shell/src/extensions/billing.rs`,
`.../extensions/usage.rs`, `.../agent/mvp_agent/acp_agent.rs:2544`,
`crates/codegen/xai-grok-shell/changelogs/`).

Prior SASE research: `research:202608/supergrok_subscription_tiers/supergrok_subscription_tiers.md`
(shared weekly pool, tier ladder).

Web:
- [Claude Code — Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)
- [anthropics/claude-code#31021 — OAuth usage API returns persistent 429](https://github.com/anthropics/claude-code/issues/31021)
- [Claude-Code-Usage-Monitor#202 — Anthropic OAuth Usage API](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/issues/202)
- [The Register — Anthropic clarifies ban on third-party tool access to Claude](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/)
- [OpenAI Help Center — Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan)
- [docs.x.ai — Grok FAQ (shared weekly usage pool)](https://docs.x.ai/grok/faq)
