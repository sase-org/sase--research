# Muse Code Usage Windows for SASE — Research (A)

Date: 2026-09-20 · Researcher A · muse 1.3.0 · sase workspace `sase_11`

Question: how should SASE add support for Muse Code's two subscription
capacity windows — the 5-hour window and the rolling 1-week window currently
visible only at `https://dev.meta.ai/usage` (login-walled) — alongside the
existing Claude / Codex / Grok subscription-usage support?

## Recommendation

Add a Muse collector to the existing subscription-usage subsystem that speaks
the Muse MSP host protocol over stdio — `muse serve` → `initialize` →
`usage/read` — exactly the way the Codex collector speaks `codex app-server`
and the Grok collector speaks `grok agent stdio`. No web scraping, no direct
Meta account-API calls, no credential handling, no model call. Map the two
returned blocks onto SASE's standard window observations
(`used_percent` + `resets_at`), add the two pluggy hooks to the Muse provider,
and let the existing refresh proc, `sase usage` CLI, Models panel, and header
pill pick Muse up with no display-side changes.

Concretely, the implementation is five small pieces mirroring the Grok
collector (`src/sase/llm_provider/usage/grok.py`, ~380 lines) and the Codex
collector (`src/sase/llm_provider/usage/codex_collector.py`):

1. **New `src/sase/llm_provider/usage/muse.py`** — `collect_muse_usage()`
   reusing the existing bounded `JsonLineSession` transport
   (`src/sase/llm_provider/usage/transport.py`): spawn
   `muse serve --no-session-log --disable-shell`, send `initialize` with a
   `sase`-identified `clientInfo`, send `usage/read`, parse the
   `SubscriptionUsage` payload. Set `MUSE_NO_AUTO_UPDATE=1` on the child env
   (same reason `muse.py` sets it for invokes: the launcher swaps the binary
   hourly) and run it in a temp cwd with the sanitized worker env, exactly as
   the Codex collector does.
2. **Two hooks in `src/sase/llm_provider/muse.py`** (the only provider of the
   four without them): `llm_usage_capabilities` →
   `{"probe": True, "passive_events": False}` and `llm_usage_probe` →
   `collect_muse_usage()`. The refresh proc, `sase usage list/refresh`, and
   doctor surfaces are provider-generic (verified: `usage_handler.py` resolves
   providers through the registry; no per-provider display code), so no
   surface changes are needed. The Muse badge (`♾️`) already exists in
   `src/sase/integrations/provider_badges.py`.
3. **Normalization across the Rust boundary.** Snapshot type, store,
   staleness, merge-by-window, and validation are core backend logic, so the
   window mapping belongs in `sase-core` next to `provider_usage.rs` (as
   `provider_usage_normalize_grok_billing` was added for Grok), with the probe
   itself staying in Python. Field mapping is fixed by the schema (below):
   `window.usedPercent` → 5-hour-class window, `weekly.usedPercent` →
   weekly window, `*Ms` stamps ÷ 1000 → `resets_at`, `tier` → plan label,
   `observedAtMs` → observation age ("as of", never live). Keep percents
   uncapped (schema says values above 100 are valid — same "do not cap"
   rule the September consolidation adopted) and reject only
   negative/non-finite values.
4. **Absent-means-absent.** `usage/read` returns `{}` (no `usage` member) when
   the host has observed nothing — verified live twice (see §2). The
   collector must degrade that to a neutral non-ok status (pending-style, not
   `error`-alarm and never a synthesized 0%), the same discipline the Claude
   probe follows on parse failure.
5. **Version floor + drift handling.** Gate on `muse >= 1.3.0` (the verified
   version; `serverInfo.version` reports it on `initialize`) and map
   JSON-RPC `-32601` on `usage/read` to `unsupported_cli_version`, mirroring
   the Grok collector's missing-extension handling. The method is on the
   **stable** surface (also present with `--experimental`, but no opt-in is
   needed), and the schema fingerprint
   (`sha256:7469c9e…fc81`, schema version 1) is reported on every
   `initialize` result if a stricter assertion is ever wanted.

v1 is display-only, polled on the existing refresh cadence (per-provider
deadline 20 s; measured round trip is ~0.6 s — §2), with no routing/disable
decisions driven by the numbers. That matches the standing "v1 is
display-only" resolution from the September provider-usage consolidation.

## 1. Current state: Muse is the only provider without a probe

- `src/sase/llm_provider/{claude,codex,grok}.py` each implement
  `llm_usage_probe` (+ `llm_usage_capabilities`); `muse.py` implements
  neither (verified by grep). There is correspondingly no
  `src/sase/llm_provider/usage/muse.py`, while `usage/claude.py`,
  `usage/codex_collector.py`, and `usage/grok.py` exist.
- Muse *token* usage (per-run input/output/cache counts) is already
  recovered from the on-disk session log (`_muse_session_usage.py`). That
  answers "what did a run spend", not "how much allowance remains" — there
  is no allowance denominator anywhere locally, so token logs cannot produce
  quota percentages. They stay as-is; this work adds the allowance side.
- `muse.py` already has a conservative, admittedly unverified
  `llm_default_usage_limit_config` ("usage limit reached", "quota exceeded",
  "insufficient_quota"). Captured real limit wording from Muse should
  tighten those patterns as a follow-up, not block v1.

## 2. The data source: MSP `usage/read` (verified live, no model call)

`muse schema generate-json-schema --out DIR` (offline, exact for the
binary) exposes a stable `usage/read` method plus a `usage/changed` push
notification, with one documented payload shape:

- `SubscriptionUsage`: `{observedAtMs, tier, weekly, window}` — "the one
  usage payload shape", point-in-time with the host's arrival stamp, so
  clients render "as of".
- `SubscriptionUsageWindow` ("the current usage window (the provider's
  5-hour-class block)"): `{resetsAtMs, usedPercent, windowDurationMins}`.
  Percent is an integer ≥ 0, verbatim from the provider — over-quota values
  above 100 are valid.
- `SubscriptionUsageWeekly` ("the rolling weekly block, same semantics …
  without a duration"): `{resetsAtMs, usedPercent}`.
- `UsageReadResult`: `{usage?}` — **omitted, never null, when the host has
  observed nothing** ("truthful absence").

Live probes against the installed `muse 1.3.0` (throwaway scripts under
`/tmp`, kept out of the repo for re-running):

- `initialize` (`clientInfo: {name, version}`) → `initialized` →
  `usage/read` returns `{"id":2,"result":{}}` — truthful absence on a fresh
  host, twice reproduced. The method costs no model call (its description:
  "Reads the host's last-observed subscription usage window … without a
  model call").
- Full round trip (process spawn + handshake + read): **0.6 s wall**,
  comparable to Grok's ~0.4 s and well inside the 20 s per-provider refresh
  deadline (`USAGE_REFRESH_PROVIDER_DEADLINE_SECONDS`).
- Method is on the stable surface; the `--experimental` export carries it
  too, so no experimental opt-in is required. `initialize` also reports
  `serverInfo.version: 1.3.0` and the schema fingerprint for gating.

What populates the host's observation is the one point not yet directly
observed (see §5, item 1 for the experiment and the decision tree — the
collector design is correct under either outcome).

## 3. Dead ends checked (so implementation doesn't retry them)

- **No `muse usage` subcommand.** `muse --help` lists
  resume/exec/config/export/trace/skills/plugins/sandbox/schema/serve/… —
  no usage/account/billing command. (Claude has no `usage` subcommand
  either; it uses a `/usage` prompt probe. Muse offers no equivalent prompt
  probe — `exec --json` carries no quota data.)
- **`muse exec` session logs carry no quota.** The 2026-09-20 session logs
  were searched for `usedPercent`, `resetsAtMs`, `observedAtMs`,
  `windowDurationMins`, `subscription_usage`: the only matches are echoes
  of this investigation's own tool output inside `output` /
  `tool_result_batch_committed` records. Genuine quota events
  (`usage/changed`, observation records) do not appear. The one
  quota-adjacent event name, `resource_usage_sampled`, is OS-level RSS/CPU
  telemetry, not subscription capacity. So there is **no passive
  stream-event feed** for Muse comparable to Claude's `rate_limit_event` —
  `passive_events: False`, like Grok and Codex.
- **Scraping `dev.meta.ai/usage`.** The page is login-walled (fetching it
  unauthenticated redirects to an SSO confirm screen). Scraping would need
  browser-session credentials handled by SASE, break on markup changes, and
  violate the consolidation's "ask each provider's own CLI, never the
  vendor's web endpoints" principle. Rejected.
- **Direct Meta account API with the CLI's OAuth token.** Third-party
  projects report quota living behind Meta account endpoints, but reaching
  them from SASE means reading tokens out of `~/.config/muse/auth.json`
  (mode 0600, user credentials) and intermediating them — exactly the
  credential-handling shape the September consolidation rejected for
  Claude's `/api/oauth/usage` fallback on policy grounds. The `serve` +
  `usage/read` path uses the user's own login through the unmodified Muse
  binary and never touches a secret (`auth.json` inspected keys-only:
  `schema_version` + `providers.meta.{mechanism, storage, obtained_via,
  api_base_url, user_full_name, user_email}` — the probe needs none of
  them). Rejected for v1; same rationale as the Claude direct-HTTP
  rejection.
- **Estimating quota from token logs.** Rejected (§1): percentages need the
  provider's allowance denominator, which only `usage/read` (or the
  login-walled web page) has.
- **Long-lived `serve` + `usage/changed` push.** The notification exists
  (`usage/changed` carries the full `SubscriptionUsage` shape whenever the
  DATA changes), mirroring Codex's `account/rateLimits/updated` push. The
  consolidation deferred Codex's push the same way: not for v1 while polling
  works. A persistent host would also contradict the one-shot collector
  pattern (`JsonLineSession` spawns, reads, closes, kills — no orphan
  processes, a property explicitly verified for the Codex and Grok
  collectors). Deferred, not rejected.

## 4. How the pieces fit the existing architecture

| Concern | Existing pattern | Muse instantiation |
|---|---|---|
| Transport | `usage/transport.py::JsonLineSession` (bounded lines, correlated ids, killable child) | Same; `argv = (muse, "serve", "--no-session-log", "--disable-shell")`. `--no-session-log` matters on a 5-minute poll: without it every poll would mint durable session state. |
| Handshake | Codex: `initialize`→`initialized`→read; Grok: `initialize`→ext call | MSP: `initialize` (with `clientInfo.name: sase`-family) → `initialized` → `usage/read` with `{}` params. Unknown-method `-32601` → `unsupported_cli_version`. |
| Auth discrimination | Claude: API-mode text → `not_applicable`; Codex: `auth_mode`; Grok: payload evidence | `tier` is verbatim from the provider and doubles as the plan discriminator; `muse exec --api-key-stdin` (API mode) behavior is untested — implementation should confirm what `usage/read` returns there and map it to `not_applicable`/`api_mode` rather than guessing. Logged-out behavior is likewise untested; map transport/auth errors to the existing `unauthenticated`/`logged_out` outcomes at implementation time. |
| Observation build | Grok: Rust `provider_usage_normalize_*` binding; Claude: Python window builders + `validate_observation` | Either a new `provider_usage_normalize_muse_usage` binding in `sase-core` (preferred — snapshot/merge/staleness/validation are core per the Rust-boundary rule) or Python construction through `validate_observation`. Window identities (suggested): 5-hour-class → stable key for the `window` block with `windowDurationMins` recorded (do not hard-code 300 — record what the provider reports, the same "don't hard-code primary = 5h" lesson as Codex); weekly → stable key for the `weekly` block. |
| Refresh | Durable proc, ~5 min, per-provider 20 s deadline, per-provider failure independence | Muse joins the same proc via its capability hook; expected 0.6 s cost per tick. First tick on a machine where the host never observed usage yields the neutral absent-status (§2), not zeros. |
| Display | `peek.py` projection → header pill, Models panel, `sase usage list`, doctor line; per-provider badge from `provider_badges.py` | No changes: Muse badge `♾️` already registered; all surfaces iterate the snapshot generically. Verify at implementation that a two-window Muse entry renders (5h + weekly) and that attention-ordering treats it like the other providers. |

## 5. Open items for implementation time (not research blockers)

1. **When does the host's first observation land?** During this research
   a 60-second idle-host listener was launched (`initialize` →
   `initialized`, then collect every frame watching for `usage/changed`;
   re-run: `python3 /tmp/muse_usage_listen_a.py`) to test whether a fresh
   `serve` host self-populates usage without any session or turn. It was
   still running when this report was written, so the outcome is recorded
   here as a decision tree rather than a result:
   - *If an idle host emits `usage/changed`* (or a re-`usage/read` shows a
     `usage` member): the probe is self-sufficient from tick one — ship as
     designed.
   - *If it stays silent:* the follow-up is whether `session/start`
     (memory-only with `--no-session-log`, no turn) or only a real model
     turn triggers the first fetch. Either way the collector's
     absent-status (§2, item 4 of the recommendation) covers the gap, so
     this does not block v1 — it only determines how quickly the first
     tick after install shows numbers.
   Under no circumstance should absence be rendered as 0%.
2. **API-key and logged-out behavior** of `usage/read` (see §4).
3. **`tier` value vocabulary** (what strings Meta sends; map to plan labels,
   keep verbatim on unknown).
4. **Real limit wording** from Muse to tighten
   `llm_default_usage_limit_config` (currently explicitly unverified).
5. **Render check** of the two-window Muse entry at 60/80/140 columns in
   both themes, per the header-design research's validation protocol.

## 6. Bottom line

The September consolidation's rule — ask each provider's own CLI over a
local, non-inference, zero-cost interface using its own auth — already
describes the Muse answer; Muse just happens to expose it as a documented
MSP method rather than a prompt probe or an extension call. `muse serve` +
`usage/read` returns both requested windows (5-hour-class `window` with
`windowDurationMins`, rolling `weekly`), integer percents, millisecond
reset stamps, a tier string, and an arrival stamp, for ~0.6 s and zero
tokens. Implement the Muse collector as a fourth instance of the proven
Codex/Grok pattern, keep v1 display-only on the existing refresh/display
plumbing, and treat unobserved-usage as absence at every layer.

### Provenance (independent verification this turn)

- `muse schema` stable + experimental exports read locally; `usage/read`,
  `usage/changed`, `SubscriptionUsage`, `SubscriptionUsageWindow`,
  `SubscriptionUsageWeekly`, `UsageReadResult` shapes quoted from the
  installed binary's own schema (Muse 1.3.0, fingerprint above).
- Live `serve` handshake + `usage/read` → `{}` (empty = unobserved), twice;
  timed at 0.6 s wall. Scripts kept at `/tmp/muse_usage_probe.py` and
  `/tmp/muse_usage_listen_a.py` for re-running (outside the repo
  deliberately).
- `muse --help` / `muse exec --help` show no usage subcommand; session-log
  survey over 2026-09-20 logs shows no genuine quota records;
  `resource_usage_sampled` confirmed as OS telemetry by reading the record.
- SASE-side claims checked against the working tree: hook absence in
  `muse.py`, collector presence for the other three providers,
  provider-generic `usage_handler.py` / peek / badges (`♾️`), 20 s
  per-provider deadline.
- External corroboration only: third-party projects agree the subscription
  is a 5-hour + 7-day pair also shown in the CLI's `/usage`-equivalent and
  the web page; one older source claiming "no endpoint, only stream events"
  predates the stable `usage/read` method verified above and is superseded
  by direct evidence. `dev.meta.ai/usage` confirmed login-walled by fetch.
- Prior SASE research reused through `sase artifact read` (audited):
  `research:202609/usage_window_header_design/usage_window_header_design.md`
  and `research:202609/provider_subscription_usage/provider_subscription_usage.md`.
  No peer report from this swarm was located, opened, or consulted.

