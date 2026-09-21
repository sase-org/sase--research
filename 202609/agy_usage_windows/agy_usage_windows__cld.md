# Gemini / Antigravity (`agy`) Usage Windows in SASE — Collection and Header Indicator

**Researcher:** cld · **Date:** 2026-09-21
**Build under test:** Antigravity CLI `agy 1.2.7` (Linux x86-64, consumer OAuth login, SSH session)
**Repo state:** `sase` @ `87c604833`, `sase-core` linked checkout @ `b5cea78`

---

## 1. Bottom line

Antigravity already exposes its usage windows through a supported CLI command. There is no
need to scrape anything, reverse-engineer an RPC, or spend a model turn.

```
agy -p "/usage" --output-format json
```

Since `agy 1.1.11`, print mode answers `/usage`, `/quota`, and `/credits` itself. Per the
changelog, it does so *"without starting an agent turn, spending quota, or leaving a
conversation behind"*. It returns a structured payload with **two model groups × two
windows**: Gemini models (weekly + 5-hour) and "Claude and GPT models" (weekly + 5-hour).
Each window carries a float `remaining_fraction` and an RFC 3339 `reset_time`. I verified
the following on this host, several times:

- `num_turns: 0`, `conversation_id: ""`, and all token counters at 0.
- Exit code 0 with an empty stderr.
- 2.4–4.0 s of wall clock, well inside the 20 s per-provider refresh deadline.
- It works under the refresh worker's filtered, secret-free environment.

So the collector is small. Most of the design work is in three places:

1. **Where the Gemini weekly window lands in the header.** With honest model-family
   applicability and today's shipped indicator defaults, **the header shows nothing for
   agy**. I verified this by running a real payload through the real sase-core store,
   projection, and TUI renderer (§7). Two shortcuts both fail. Tagging every bucket
   `account` makes the *Claude/GPT* weekly window the header anchor. A config pin renders
   as `family:gemini 96% 6d1h`. The clean fix is one `agy` arm in sase-core's weekly-anchor
   rule, which renders `🪐 96% 6d1h`, matching every other provider.
2. **Two operational hazards the probe must guard against** (§4):
   - An `agy` older than 1.1.11 would treat `"/usage"` as a **real prompt** and spend quota.
   - A logged-out `agy` starts an **interactive OAuth flow and waits 60 s**.
3. **A likely omitted-zero trap.** The vendor struct tag is `remaining_fraction,omitempty`.
   An exhausted bucket may therefore arrive *without* the field, which is the same class of
   bug Grok already hit (`db535fabd`).

**Recommendation (§8):**

- **sase-core:** add a `normalize_agy_usage` normalizer plus the anchor arm.
- **sase:** add a ~250-line `collect_agy_usage` probe with a version floor, early auth-prompt
  abort, and hygiene flags, and wire `AgyProvider.llm_usage_capabilities` /
  `llm_usage_probe`.
- **Also:** a docs update and one optional presentation polish.

No feature flag is needed. The per-provider on/off switch
`llm_provider.usage_metrics.providers.agy.enabled` already exists generically.

---

## 2. What SASE has today

The subscription-usage pipeline is fully provider-generic. Only the collector and the vendor
normalizer are per-provider. I checked each of these in the working tree:

| Layer | Where | agy status |
|---|---|---|
| Capability + probe hooks | `llm_provider/_hookspec.py:210-229` (`llm_usage_capabilities`, `llm_usage_probe`) | **not implemented** by `AgyProvider` |
| Collectors | `usage/claude.py`, `usage/codex_collector.py`, `usage/grok.py`, `usage/muse.py` | none for agy |
| Vendor normalizers (Rust) | `sase-core/.../provider_usage/{grok,muse}.rs` | none for agy |
| Eligibility | `usage/refresh.py:280-308`: `probe is True` + CLI ready + alias-referenced or explicit enable | agy **is** alias-referenced: the shipped `@xsmall` pool contains `agy/gemini-3.8-flash-high` (`model_alias_defaults.yml:14`), so declaring `probe: True` auto-enrolls it |
| Isolated worker | `usage/probe.py`: filtered env (allowlist + `KEY/TOKEN/SECRET/PASSWORD/CREDENTIAL/AUTH` deny markers), managed temp cwd, killable | generic |
| Store / refresh / backoff | sase-core `store.rs`, `refresh.rs` (30 min backoff cap; only `ok`/`not_applicable`/`unsupported` reset backoff) | generic |
| Header indicator | `ace/tui/widgets/provider_usage_indicator.py` → core `project_usage_indicator` | generic; agy badge `🪐` already exists (`integrations/provider_badges.py:16`) |
| Limit-event refresh | `usage_limit_disable.py:171` → `trigger_usage_refresh_after_limit_event` | generic; agy's usage-limit patterns already exist (`agy.py:411-429`) |
| Disable expiry from windows | `usage_limit_window_reset.py`: `provider_usage_summarize_for_model(windows, model_id)` | generic, and **applicability-sensitive** (§6.2) |

As with Muse, the only genuinely new code is a collector and a normalizer. Everything
downstream picks agy up automatically: `sase usage list -p agy`, the Models panel's Providers
· Usage view, doctor, capacity hints, the header, and limit-triggered refresh.

---

## 3. What Antigravity exposes

### 3.1 The `/usage` slash command in print mode

Relevant `agy changelog` entries on this build:

| Version | Entry (abridged) |
|---|---|
| 1.0.8 | *Redesigned the "Models & Quota" page … disabled quota buckets display a dimmed "Disabled" status*; *Added display of quota usage … in the status line* |
| **1.1.11** | ***Added non-interactive answers for the read-only slash commands in print mode, so `-p "/usage"`, `/quota`, `/credits`, `/model`, `/effort` and `/skills` emit one tab-separated record per line — or a structured payload under `--output-format json` and `stream-json` — without starting an agent turn, spending quota, or leaving a conversation behind.*** |
| 1.1.12 | *Fixed the status line reporting model quota that was always one fetch out of date* |
| 1.2.7 | *Improved the `/usage` panel by removing the duplicate remaining-quota percentage line* |

`/quota` is an alias: it returned `command.name: "usage"` with the identical payload.

Verified payload, abridged. The `description` strings are trimmed:

```json
{"conversation_id": "", "status": "SUCCESS", "num_turns": 0, "duration_seconds": 0,
 "usage": {"input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0,
           "cache_read_tokens": 0, "total_tokens": 0},
 "response": "Gemini Models\tWeekly Limit Remaining\t96%\t2026-09-27T20:14:34Z\n…",
 "command": {"name": "usage", "data": {
   "description": "Within each group, models share a weekly limit and a 5-hour limit. …",
   "groups": [
     {"name": "Gemini Models",
      "description": "Models within this group: Gemini Flash, Gemini Pro",
      "buckets": [
        {"id": "gemini-weekly", "name": "Weekly Limit Remaining", "window": "weekly",
         "remaining_fraction": 0.9612414240837097, "reset_time": "2026-09-27T20:14:34Z"},
        {"id": "gemini-5h", "name": "Five Hour Limit Remaining", "window": "5h",
         "remaining_fraction": 0.8664969801902771, "reset_time": "2026-09-21T23:31:12Z"}]},
     {"name": "Claude and GPT models",
      "description": "Models within this group: Claude Opus, Claude Sonnet, GPT-OSS",
      "buckets": [
        {"id": "3p-weekly", "name": "Weekly Limit Remaining", "window": "weekly",
         "remaining_fraction": 1, "reset_time": "2026-09-28T18:40:15Z"},
        {"id": "3p-5h", "name": "Five Hour Limit Remaining", "window": "5h",
         "remaining_fraction": 1, "reset_time": "2026-09-21T23:40:15Z"}]}]}}}
```

The vendor's own framing, from `command.data.description`: *"Within each group, models share
a weekly limit and a 5-hour limit. Quota is consumed proportionally to the cost of the
tokens. … The 5-hour limit smooths out aggregate demand to fairly distribute global capacity
across all users, while your weekly limit is tied directly to your individual tier."* This
matches the Usage Window glossary definition exactly: independent, overlapping, model-subset
windows whose percentages must never be combined.

`--output-format stream-json` emits `{"event":"command_result",…}` followed by
`{"event":"result",…}` with the same data. Plain `-p "/usage"` emits only the TSV rows. Use
`json`: it is one object and parses trivially.

### 3.2 What `agy` does underneath

The probe's own `--log-file` shows the sequence:

1. Silent auth from the stored credential.
2. `POST https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist`, then
   `…:fetchAvailableModels`.
3. `quota_manager doRefreshQuota(force=true)`.
4. `Print mode: running slash command /usage`, backed by
   `…/v1internal:retrieveUserQuotaSummary`.

No `streamGenerateContent` call appears in the log. The binary also serves the same data
locally as `exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary` on the
running agy's random-port language server. Both are private surfaces; see §5.

### 3.3 Window semantics I observed

- **Started windows have anchored, stable resets.** Across 11 samples over ~13 minutes,
  `gemini-weekly` always reported `2026-09-27T20:14:34Z` and `gemini-5h` always reported
  `2026-09-21T23:31:12Z`. The 5-hour block therefore started at 18:31:12Z, which is when
  another Gemini-backed agy session on this host began. That is anchored to first use, not
  an epoch grid and not "5 h after the latest request". Because the vendor also names the
  window, `period_start = resets_at − duration` is exact.
- **Unstarted windows report a rolling reset.** The `3p-*` buckets sat at
  `remaining_fraction: 1`. Their `reset_time` was always *request time + window*
  (`18:31:59Z`, `18:32:02Z`, `18:32:11Z`, … for weekly; `+5h` for 5-hour). A window nobody
  has touched says "if you start now it resets at X".
- **Readings are live but not strictly monotonic.** Gemini readings fell while another agy
  agent was using Gemini on the same account: weekly 0.9856 → 0.9573, 5-hour 0.9829 → 0.8631.
  But three back-to-back probes returned 0.9573/0.8631 and then 0.9612/0.8665 twice. The
  second pair was the exact value from a capture ~4 minutes earlier, so reads can come from a
  lagging backend cache. Treat each probe as a snapshot, and never derive burn rates from
  consecutive deltas.
- **`/credits`** returns `{"remaining_credits": 0, "upgrade_uri": "…/g1-upgrade"}`. This is a
  pay-as-you-go "AI Credits" balance, not a window. It is out of scope, but it could become a
  Models-panel line later.

### 3.4 Likely omitted-zero field

The `agy` binary carries the Go struct tag `RemainingFraction … json:"remaining_fraction,omitempty"`,
and `reset_time` is also `omitempty`. If the field is a plain `float64`, Go drops `0.0`: an
**exhausted bucket would arrive without `remaining_fraction`**. I could not trigger that
shape, because nothing here is exhausted, and I could not tell from strings whether the field
is a pointer. The normalizer must therefore not treat a missing fraction as malformed without
checking further. The same payload's `response` TSV row, `…\t0%\t…` versus `…\tDisabled…`,
disambiguates "exhausted" from the 1.0.8 "Disabled bucket" state (§8, Phase 1).

---

## 4. Hazards found, and what the probe must do about each

| # | Hazard (verified unless marked) | Consequence if ignored | Mitigation |
|---|---|---|---|
| H1 | **agy < 1.1.11 has no non-interactive `/usage`.** It would send the literal prompt `/usage` to the model *(inferred from the changelog; not reproducible here)*. | A real agentic model turn every 5 min: spends quota and creates conversations, which is the Muse report's disaster case. | Version floor: `agy --version` (0.11 s, prints `1.2.7`). Below `1.1.11` → `unsupported`/`unsupported_cli_version`, never spawn `/usage`. Post-hoc envelope guard in core: `num_turns != 0`, non-empty `conversation_id`, or `command.name != "usage"` → `vendor_drift`. Belt and braces: `--mode plan --sandbox --print-timeout 15s` bound any accidental turn. I verified `/usage` still answers with those flags. |
| H2 | **Logged-out print mode launches interactive OAuth.** With an empty `HOME` it printed `Authentication required. Please visit the URL to log in: https://accounts.google.com/o/oauth2/auth?…` to stderr, then `Waiting for authentication (timeout 60s)...`. Killed, it wrote `{"status":"ERROR","error":"authentication failed or timed out",…}` to stdout. | Each tick holds one of the 3 probe slots for the whole 20 s deadline and is recorded as `timeout` rather than logged-out. On a desktop, the flow *might* open a browser every backoff period *(unverified here, because athena is headless over SSH)*. | Read stderr incrementally and kill the child on the `Authentication required` marker (it appears as soon as silent auth fails, ~0.2 s after startup in the log). Report `unauthenticated`/`logged_out`. Also map the stdout ERROR envelope's `authentication` wording to the same result. Existing core backoff then spaces retries up to 30 min. **Verify the macOS behaviour before shipping default-on there.** |
| H3 | **Self-update.** The binary contains `Spawned background update process with PID` and a 15-minute `last_check` fast path. It also contains `AGY_CLI_DISABLE_AUTO_UPDATE` next to `Auto-update disabled via environment variable %s`. | The probe becomes the thing that triggers binary swaps under running agents. | Set `AGY_CLI_DISABLE_AUTO_UPDATE=1` in the probe env, as Muse does with `MUSE_NO_AUTO_UPDATE` and Grok with `--no-auto-update`. *Caveat:* in my runs the 15-minute fast path fired first, so I could not observe the variable take effect. Treat it as present-but-unverified, and consider setting it for `AgyProvider.invoke` too (`sase agent-cli` already owns updates). |
| H4 | **Log spam.** Without flags, every run writes `~/.gemini/antigravity-cli/log/cli-<ts>.log` (~17 KB). | ~288 extra log files per day. | `--log-file <probe temp dir>/agy.log`. Verified: the log goes there and the `cli.log` symlink is untouched. |
| H5 | **Filtered worker env.** The worker drops `SSH_*`, `DBUS_SESSION_BUS_ADDRESS`, `DISPLAY`, and every `*KEY*`/`*TOKEN*` var. | agy picks the keyring or file token store by "SSH session detected". | Verified under the exact `worker_environ()` output: the keyring unlock failed, agy logged `falling back to file`, authenticated, and returned `SUCCESS` in 2.79 s. On a Linux desktop, the keyring attempt could conceivably pop an unlock prompt *(unverified)*. |
| H6 | **API-key-only users.** `GEMINI_API_KEY`/`GOOGLE_API_KEY` are stripped by the worker's deny markers. | Such a user looks "logged out" to the probe (H2 path). | Acceptable, since `/usage` is a subscription concept. Optionally let the parent skip eligibility, or report `api_mode`, when a key is set and no OAuth token exists. What `/usage` itself returns in API-key mode is unverified. |
| H7 | **State side effects.** | — | Verified benign: no conversation, `cache/projects.json` untouched, only `cache/onboarding.json` and the summary DB were touched. The probe ran concurrently with a live agy agent session on the same account every time, with no failures on the probe side. Run it from the probe's managed temp cwd, not a repo. |

---

## 5. Collection approaches considered

| Approach | Cost / latency | Stability | Secrets in SASE? | Verdict |
|---|---|---|---|---|
| **A. `agy -p "/usage" --output-format json`** (recommended) | 0 tokens, 2.4–4.0 s | First-party CLI surface, changelog-documented since 1.1.11 | No; agy uses its own stored credential | ✓ |
| B. Direct `POST …/v1internal:retrieveUserQuotaSummary` | ~1 s, 0 tokens | **Private** internal API (`daily-` host, `v1internal`); also needs `loadCodeAssist` project resolution | **Yes**: SASE would read agy's OAuth token from keyring or file and refresh it with agy's embedded client. This contradicts `UsageProbeContext.auth_context`'s no-secrets rule and the worker's deny list. | ✗ |
| C. Local language server `RetrieveUserQuotaSummary` RPC | ms | Private; random port and CSRF token scraped from a *running* agy process | No | ✗ Only exists while agy runs; very fragile |
| D. Passive: parse agy run output | 0 | — | No | ✗ as a collector. agy's JSON `usage` object is tokens only, with no quota. Limit prose (`Resets in 4h14m50s`) is already consumed by usage-limit detection. |
| E. Gemini CLI (`gemini` 0.35.0 is installed) | — | — | — | ✗ SASE has no Gemini CLI provider (`docs/agent_providers.md:254`: agy replaced it), and its Code Assist quota is not the Antigravity subscription pool SASE agents draw on. |
| F. Text `-p "/usage"` (TSV) | same as A | same | No | Fallback only: integer percents. Kept *inside* A's parse for the omitted-zero case (§3.4). |

A cheap optional enhancement to A: have `AgyProvider.invoke` mark the agy refresh due when a
run finishes, via the existing `_mark_usage_refresh_due` machinery. That gives post-run
freshness without faster cadence. It is not needed for v1.

---

## 6. Mapping onto the SASE observation

### 6.1 Window fields (one bucket → one window)

| Observation field | Value |
|---|---|
| `key` | bucket `id` verbatim: `gemini-weekly`, `gemini-5h`, `3p-weekly`, `3p-5h`. These are vendor machine ids, so users can write `indicator.providers.agy.windows.gemini-5h` and unknown enterprise buckets pass through without a mapping table. |
| `label` | `"Antigravity <group name> <weekly\|5-hour>"`, e.g. `Antigravity Gemini Models weekly` |
| `used_percent` | `(1 − remaining_fraction) × 100`, clamped to [0, 100] (the vendor fraction is bounded) |
| `resets_at` | `reset_time` (RFC 3339 → epoch seconds) |
| `duration_seconds` | `window` token: `weekly` → 604800, `5h` → 18000; parse other `<N>h`/`<N>d` tokens; else `None`. Unlike Muse, the vendor *names* the window, so this is not fabrication. |
| `period_start` | `resets_at − duration_seconds` when both are known |
| `applicability` | see §6.2 |
| `observed_at` | probe clock (the payload has no observation stamp) |
| `vendor_state` | `allowed`. Let percentages drive attention; the vendor reports no allow/reject status. |

Envelope: `outcome: ok`, `completeness: complete`, `account_mode: "subscription"`,
`plan: None`. The payload carries no tier. The startup banner shows one, but do not persist
account-scoped strings.

**Unstarted windows** (§3.3): pass the vendor's rolling reset through unchanged. It is
truthful ("full allowance, resets 7 d after first use"). The store tolerates a moving future
`resets_at`, since `reset_passed` never fires. And these windows are hidden by default policy
because they sit at 100%. Dropping the reset would render `?` countdowns in the Models panel
for a perfectly known state.

### 6.2 Applicability: `model_family`, not `account`

Each group is a model subset, so the honest wire value is:

```json
{"kind": "model_family", "family": "gemini", "model_ids": ["gemini-3.8-flash-high", …]}
{"kind": "model_family", "family": "3p",     "model_ids": ["claude-sonnet-4-6", "claude-opus-4-6-thinking", "gpt-oss-120b-medium"]}
```

Partition by bucket-id prefix (`gemini-*` / `3p-*`). Pass `model_ids` in from
`AgyProvider.llm_known_model_names()` and filter by the `gemini-` prefix in core. An unknown
prefix becomes `{"kind": "unknown", "vendor_label": <group name>, "vendor_id": <bucket id>}`.

This matters beyond display. `usage_window_applies` (core `mod.rs:523-553`) does exact
`model_ids` matching, and the model-picker hints (`hints.py`), alias hints, and
`usage_window_expires_at` disable expiry (`usage_limit_window_reset.py`) all consume it. With
honest scoping, an exhausted Gemini weekly window correctly constrains
`agy/gemini-3.8-flash-high` and correctly does **not** constrain
`agy/claude-opus-4-6-thinking`. `account` would apply Gemini exhaustion to Claude-via-agy
and vice versa.

The known cost: a Gemini model added to agy before SASE's catalog learns it matches
`does_not_apply`. The agy catalog is already maintained against `agy models`
(`agy.py:280`), so this is a catalog-bump chore, not a design flaw. Prefix matching in core
would remove it, but it would change the applicability wire, which is not worth it for v1.

No provider emits `model_family` today. agy would be the first real user, and the renderers
already handle it (`_usage_indicator_format.py:149`, `presentation.py:547`).

---

## 7. The header: measured, not guessed

I fed the captured payload through the **real** stack in a temp `sase_home`:
`provider_usage_prepare_account_context` → `provider_usage_record_observation` →
`provider_usage_load` → `provider_usage_project_indicator` → `usage_indicator_groups` →
`build_usage_indicator_segment`. Live values: Gemini weekly 96%, Gemini 5h 87%, 3p 100%/100%.

| Scenario | Rendered header segment |
|---|---|
| A. `model_family`, shipped indicator defaults | `''`, **nothing**. Neither weekly window is "weekly all-model", so both fall to `default: below_remaining_percent 20`. |
| B. A with Gemini 5h at 12% and 3p weekly at 15% | `🪐 family:3p 15% 6d23h · 5h/family:gemini 12% 4h50m` (no Gemini weekly) |
| C. A plus config pin `providers.agy.windows.gemini-weekly: always` | `🪐 family:gemini 96% 6d1h`: works, but carries a label no other provider's primary window has |
| D. C with Gemini 5h at 12% | `🪐 5h/family:gemini 12% 4h50m · family:gemini 96% 6d1h`: the anchor is not first |
| E. `account` applicability on every bucket (rejected) | `🪐 100% 6d23h · wk/all 96% 6d1h`: **the Claude/GPT weekly becomes the anchor**, because anchor choice is by min window key and `3p-weekly` < `gemini-weekly` |

Why this happens: in core `indicator.rs`, `is_weekly_all_window = is_all_model_scope &&
is_weekly_window`. `is_all_model_scope` is true only for `account` or Claude's product scope.
The anchor (the unlabeled first window) and the `weekly_all: always` policy both key off that
flag. Muse needed a similar provider arm (`is_weekly_window`, `provider == "muse"`).

**Recommended:** add one narrowly scoped arm so `agy`'s `gemini-weekly` (with `model_family`
`gemini`) counts as the provider's weekly anchor. Put it in `is_weekly_all_window` only, not
`is_all_model_scope`, so `classify_scope` stays honestly `model_family` in tooltips and the
Models panel. I emulated that arm by setting `weekly_all` on the projected entry and
rendering:

| State | Recommended arm | + optional bare-family compact names |
|---|---|---|
| live | `🪐 96% 6d1h` (13 cells) | `🪐 96% 6d1h` |
| Gemini 5h at 12% | `🪐 96% 6d1h · 5h/family:gemini 12% 4h50m` (42) | `🪐 96% 6d1h · 5h/gemini 12% 4h50m` (35) |
| + 3p weekly at 15% | `… · family:3p 15% 6d23h · 5h/family:gemini …` (64) | `🪐 96% 6d1h · 3p 15% 6d23h · 5h/gemini 12% 4h50m` (50) |
| Gemini exhausted | `🪐 0% 6d1h · 5h/family:gemini 0% 4h50m` (40) | `🪐 0% 6d1h · 5h/gemini 0% 4h50m` (33) |

The optional polish drops the `family:` prefix in the **compact** header name only
(`_usage_indicator_format._scope_suffix`). Full specifiers in tooltips and `sase usage list`
keep `family:gemini`. No other provider emits `model_family`, so nothing else changes.

**Behaviour to accept consciously:** the header renders provider groups in **provider-name
order**, a deliberate recent decision (`961a8cea2`, `docs/ace.md`). `agy` sorts first. Against
this machine's real store (read-only load):

| Budget | Today | With agy |
|---|---|---|
| unbounded | `🎭 73% 5d5h  🤖 ! 0% 2d22h  🛰️ 0% 3d18h  🦋 77% 6d5h` (54) | `🪐 96% 6d1h  🎭 73% 5d5h  🤖 ! 0% 2d22h  🛰️ 0% 3d18h  🦋 77% 6d5h` (67) |
| 60 cells | all four fit | Muse overflows to `+1` |
| 40 cells | `🎭 … 🤖 …  +2` | `🪐 …  🎭 …  +3`: Codex drops out |

agy also becomes the provider a click on the cluster opens ("first displayed provider"). If
that is unwanted, the smallest stable alternative is ordering groups by
`llm_autodetect_priority` (claude 0, codex 10, …, agy 30). That is a separate presentation
decision; I would ship v1 with name order and revisit only if it annoys you.

The 5-hour Gemini window stays on the generic default (shown below 20% remaining). That is
consistent with Claude's `session` window, and the vendor itself frames 5 h as a
global-capacity smoother that can block you before the weekly does. The `3p-*` windows use the
same default. If you never route agy to Claude/GPT, they sit at 100% and never appear.

---

## 8. Recommended solution

### Phase 1 — `sase-core`: normalizer and anchor arm

1. `crates/sase_core/src/provider_usage/agy.rs` with
   `ProviderUsageNormalizeAgyUsageRequestWire { schema_version, payload, model_ids,
   provider, context_id, account_generation, request_started_at, now }` and
   `normalize_agy_usage`, modelled on `muse.rs`. `payload` is the whole `--output-format
   json` result object. The normalizer owns all vendor decisions:
   - **Envelope.** `status != "SUCCESS"`:
     - `error` mentioning authentication → `unauthenticated`/`logged_out`.
     - Otherwise → `error`/`probe_failed` with a bounded diagnostic.

     `num_turns != 0`, non-empty `conversation_id`, or `command.name != "usage"` →
     `error`/`vendor_drift` (`agy_usage_not_a_command_answer`). This is the post-hoc half of
     H1.
   - **Buckets → windows** per §6.1/§6.2. Parse `reset_time` with `chrono`, as `grok.rs`
     already does.
   - **Omitted fraction** (§3.4). Look up the bucket's TSV row in `response` by
     `(group.name, bucket.name)`: `0%` → exhausted (`used_percent: 100`); a non-percent
     status such as `Disabled` → omit the window and add a diagnostic. If neither form is
     found → `malformed_payload`, `completeness: partial`.
   - An empty `groups` array → truthful authoritative-empty, never `0%`.
2. `indicator.rs`: the `agy` / `gemini-weekly` / `model_family gemini` arm in
   `is_weekly_all_window`, with a comment naming why. The previous synthesis already flagged
   the growing `provider == "…"` allowlists as a follow-up smell. A declarative
   "headline window" hint on the observation wire would retire them all, but it is a schema
   change and not a prerequisite.
3. Export from `mod.rs`, bind `provider_usage_normalize_agy_usage` in `sase_core_py`, and add
   fixtures:
   - the verified payload above
   - both omitted-zero variants
   - a disabled bucket
   - the logged-out ERROR envelope (captured, §4 H2)
   - a turn-ran drift envelope
   - an unknown group
   - an unstarted rolling-reset bucket

   Cut a `sase-core-rs` release.

### Phase 2 — `sase`: collector and wiring

1. `src/sase/llm_provider/usage/agy.py` → `collect_agy_usage(context, executable)`:
   - `agy --version` gate: ≥ 1.1.11, else `unsupported_cli_version` (H1). Parse loosely: the
     output is a bare `1.2.7`.
   - Spawn:

     ```
     agy -p /usage --output-format json --mode plan --sandbox --print-timeout 15s \
         --log-file <cwd>/agy-usage.log
     ```

     - stdin `DEVNULL`
     - cwd = the probe's managed temp dir
     - env = inherited worker env plus `AGY_CLI_DISABLE_AUTO_UPDATE=1`
     - killable child with the existing deadline margins (`_subprocess_deadline` pattern
       from `muse.py`)
   - Stream stderr and kill on `Authentication required` → `unauthenticated`/`logged_out`
     (H2).
   - `json.loads(stdout)` → core binding with `model_ids` from the provider catalog.
   - `FileNotFoundError` → `not_installed`; deadline → `timeout`; bad JSON → `parse_error`.

   `JsonLineSession` is not needed. This is one request and one response. A plain
   `Popen` with a stderr reader thread is simpler than bending the JSON-lines transport.
2. `AgyProvider`: `llm_usage_capabilities → {"probe": True, "passive_events": False}` and
   `llm_usage_probe` delegating to the collector with `SASE_AGY_PATH` resolution
   (`_agy_bin()`). Bump the `sase-core-rs` floor and `sase-core-revision.txt`.
3. Config/docs:
   - `default_config.yml`: a commented `agy` indicator example (pin or hide `gemini-5h` /
     `3p-*`).
   - `docs/agent_providers.md` Antigravity section: a "Subscription usage" subsection
     stating *zero tokens, ~3 s per refresh, version floor 1.1.11*.
   - `docs/llms.md` and `docs/configuration.md`: add agy to the collector lists.
4. Tests: a scripted fake-`agy` fixture (like `tests/.../usage_probe/muse_msp_cli.py`) that
   covers:
   - success
   - old version (asserting `/usage` is never spawned)
   - an auth prompt (asserting an early kill, well under the deadline)
   - a timeout
   - a malformed payload
   - omitted-zero
   - a turn-ran envelope

   Plus an indicator projection test asserting the header anchor.
5. **Optional polish:** the bare-family compact name (§7), with a visual snapshot at 60/80/140
   columns.

**No feature flag.** Per `sase_flags.md`, the user-facing choice is a permanent config field,
and it already exists generically (`llm_provider.usage_metrics.providers.agy.enabled`). If
this is split into an epic, Phase 1 (core) exposes nothing to users by itself, so it still
needs no `beta` scaffolding.

### Size and cost

The Muse change is the closest analogue: ~1,040 lines including a 400-line collector and
400 lines of tests. The agy collector is simpler (no session protocol and no echo-mint trick),
so expect roughly **700–900 lines across both repos**, most of them fixtures and tests. At the
default cadence, the runtime cost is ~288 probes/day × ~3 s of wall clock and five small
Google API calls each. That is the same calls every interactive `agy` launch makes, with
**zero model tokens**.

---

## 9. Confidence and open items

**Verified on this host:**
- `/usage` and `/quota` payload shape, `num_turns: 0`, empty `conversation_id`, zero tokens,
  empty stderr, exit 0.
- 2.4–4.0 s latency across 7 successful runs.
- `--mode plan --sandbox --print-timeout 15s` compatibility.
- The logged-out stderr prompt, the 60 s wait, and the ERROR envelope.
- `--log-file` redirection.
- Success under the exact `worker_environ()` filter.
- The underlying `retrieveUserQuotaSummary` call chain.
- Anchored resets for started windows and rolling resets for unstarted ones.
- Non-monotonic back-to-back reads.
- The invalid-`--model` idea is **not** a usable guard. It makes `/usage` itself fail too
  (tested).
- Every header rendering in §7 via the real core and renderer.

**Open:**

1. **Omitted-zero shape** (§3.4). This is evidence from struct tags, not an observed payload.
   The TSV cross-check covers both possibilities. Capture a real exhausted bucket when one
   occurs.
2. **macOS behaviour when logged out.** Does print mode open a browser? This decides whether
   an early-abort alone is enough on a desktop, or whether the collector also needs an
   offline auth pre-gate. There isn't one on macOS: the Keychain is not inspectable offline,
   which is why `llm_auth_evidence` declares no credential paths.
3. **`AGY_CLI_DISABLE_AUTO_UPDATE` effect** (H3). It is in the binary, but its ordering
   against the 15-minute fast path was unobservable.
4. **API-key and enterprise/ADC accounts.** Their `/usage` output was not tested. The binary
   carries separate `businessaicode.v1beta/v1main` `QuotaSummaryGroup`/`QuotaSummaryBucket`
   messages, so enterprise group names likely differ. That is why unknown groups must degrade
   to `unknown` applicability rather than fail.
5. **Backend cache lag** (§3.3). It is cosmetic at a 300 s cadence with floored percents, but
   it rules out delta-based burn estimates.

**Side observations (outside this feature):**
- `agy 1.2.7` now has `--output-format json|stream-json` and `--effort low|medium|high`. The
  `agy.py` module docstring and `invocation_option_args` (`supported={}`) still say neither
  exists.
- `_SUPPORTED_AGY_TRAJECTORY_VERSIONS = {"1.0.10"}` (`_subprocess_agy.py:24`) means that on
  the installed 1.2.7, trajectory tool-call extraction and structural no-progress detection
  are silently off. `SASE_AGY_TOOL_TRAJECTORY_VERSION_ALLOWLIST` is not set in this
  environment.

**Research cost:** zero model tokens spent by me. Every probe was a `/usage`, `/quota`,
`/credits`, or `/model` slash-command answer. Two invalid-model runs failed before any model
call.

---

## 10. Provenance

- **Commands** (all on athena, 2026-09-21 ~18:31–18:45Z):
  - `agy --version`, `agy --help`, `agy models`, `agy changelog`
  - `agy -p {/usage,/quota,/credits,/model} --output-format {json,stream-json}` plus plain
    text, with and without `AGY_CLI_DISABLE_AUTO_UPDATE=1`, `--log-file`,
    `--mode plan --sandbox --print-timeout 15s`, an invalid `--model`, `HOME=<empty temp>`,
    and `env -i <worker_environ()>`
  - `strings` over `~/.local/bin/agy` for struct tags, RPC names, and env vars
- **Code read:**
  - `sase`: `llm_provider/agy.py`, `_subprocess_agy.py`, `usage/{types,_strategy,muse,grok,
    config,refresh,probe,hints,_facade}.py`, `usage_limit_window_reset.py`,
    `ace/tui/widgets/{provider_usage_indicator,_provider_usage_indicator,
    _usage_indicator_format}.py`, `default_config.yml`, `model_alias_defaults.yml`
  - `sase-core` (opened via `sase repo open`): `provider_usage/{mod,muse,grok,indicator,
    refresh}.rs`
- **Simulation scripts:** `/tmp/agy_sim/sim.py`, `sim2.py`, `sim3.py` (temp `sase_home`; the
  real store was only *loaded*, never written).
- **Prior research read via `sase artifact read`:**
  - `research:202609/muse_subscription_usage_windows/muse_subscription_usage_windows.md`
    (collector and normalizer precedent, probe hygiene, no-flag reasoning)
  - `research:202609/usage_window_header_design/usage_window_header_design.md` (header
    grammar and budget)
- **Memory read via `sase memory read`:** `sase_flags.md`, `glossary:usage-window`.
