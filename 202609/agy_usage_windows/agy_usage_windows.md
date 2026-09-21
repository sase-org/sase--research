# Gemini / Antigravity (`agy`) Usage Windows — Collection and Top-Right Header Indicator

**Consolidated report** · lead researcher · 2026-09-21
**Inputs:** [`agy_usage_windows__cld.md`](agy_usage_windows__cld.md) (cld) and
[`agy_usage_windows__gem.md`](agy_usage_windows__gem.md) (gem), plus the lead's own
verification.
**State under test:** `agy 1.2.7` on athena (headless, SSH), `sase` @ `87c604833`,
`sase-core` linked checkout @ `006dd16`.

---

## 1. Bottom line

The collection problem is solved at the vendor side. `agy 1.1.11+` answers
`agy -p "/usage" --output-format json` in print mode without starting a model turn. It
returns two model groups × two windows: Gemini weekly, Gemini 5-hour, Claude/GPT
weekly, and Claude/GPT 5-hour. Each window has a float `remaining_fraction` and an
RFC 3339 `reset_time`. Both researchers verified this, and so did I. Everything
downstream of a collector (store, refresh scheduler, header, Models panel, `sase usage`,
limit-triggered refresh) is already provider-generic, and the `🪐` badge and agy
palette already exist.

The real decisions are:

1. **How to scope the windows.** The two reports disagree here, and it is the main
   finding of this synthesis. gem's scheme tags Gemini buckets `account`. It gives a
   clean header with no core change, but it applies Gemini exhaustion to
   Claude-via-agy models. cld's scheme uses honest `model_family` scoping. It is
   correct everywhere, but the header shows **nothing** until sase-core learns that
   agy's Gemini weekly window is the provider's headline window. I reproduced both
   through the real core and renderer (§4).
2. **Where the normalizer lives.** gem recommends a Python normalizer now and Rust later.
   cld recommends Rust from the start. The Rust-core decision and the Grok/Muse
   precedent settle this in favour of Rust (§5).
3. **Probe hardening.** Only cld's report covers this. Old `agy` builds would send
   `/usage` as a real prompt. Logged-out `agy` blocks on an interactive OAuth prompt.
   Exhausted buckets may omit `remaining_fraction`. I confirmed that `--print-timeout`
   does *not* bound the OAuth wait (§3).

**Recommendation (§6):**

- **sase-core:** add a normalizer (`agy.rs`), `model_family` applicability, and one
  narrowly scoped `agy` arm in the weekly-anchor rule.
- **sase:** add a ~250-line hardened collector wired into `AgyProvider`, and drop the
  `family:` prefix in compact header names.
- The header then reads `🪐 96% 6d1h`, and `🪐 96% 6d1h · 5h/gemini 12% 4h50m` under
  pressure.
- No feature flag. Budget roughly 700–900 lines across both repos, modelled on the Muse
  change.

---

## 2. What both reports agree on (and I re-verified)

| Fact | Evidence |
|---|---|
| `/usage` in print mode spends nothing | My run: `status: SUCCESS`, `num_turns: 0`, `conversation_id: ""`, `total_tokens: 0`, exit 0, empty stderr. The `--log-file` output shows `doRefreshQuota` → `retrieveUserQuotaSummary` and **no** `streamGenerateContent`. |
| Latency fits the 20 s per-provider deadline | cld 2.4–4.0 s; gem ~3.4 s; my run 4.98 s with the hardening flags. `USAGE_REFRESH_PROVIDER_DEADLINE_SECONDS = 20.0`, at most 3 concurrent probes. |
| Payload shape | `command.data.groups[].buckets[]` with `id` (`gemini-weekly`, `gemini-5h`, `3p-weekly`, `3p-5h`), `window` (`weekly`/`5h`), `remaining_fraction`, and `reset_time`. `/quota` is an alias. |
| Direct REST (`v1internal:retrieveUserQuotaSummary`) and the local language-server RPC are not viable | Both are private surfaces. REST would require SASE to hold agy's OAuth token, which breaks the probe's no-secrets rule; gem also got `403 UNSUPPORTED_CLIENT`. The RPC exists only while an agy process is running. |
| Downstream is generic | The hooks `llm_usage_capabilities`/`llm_usage_probe` exist (`_hookspec.py`), and `AgyProvider` does not implement them. Eligibility (`refresh.py:280`) auto-enrolls agy once `probe: True` is declared, because `agy/gemini-3.8-flash-high` is in the shipped `@xsmall` pool (`model_alias_defaults.yml:14`). `SASE_AGY_PATH` already satisfies `_provider_cli_ready`. |
| Cadence cost | `DEFAULT_USAGE_CADENCE_SECONDS = 300` gives ≈288 probes/day, each ~3–5 s of wall clock with zero model tokens. |

Additional window semantics, from cld and confirmed in my run:

- **Started windows have anchored, stable resets.** The same `gemini-weekly`/`gemini-5h`
  reset times held across all captures.
- **Unstarted windows report a rolling reset** of request time + window. In my run the
  `3p-*` buckets moved to `…18:58:13Z`.
- **Only started buckets carry a `description` string.** This is new in my run; untouched
  `3p-*` buckets omit it.
- **Readings can lag a backend cache.** Treat each probe as a snapshot, and never derive
  burn rates from consecutive deltas.
- **`remaining_fraction` can arrive as the JSON integer `1`.** The parser must accept
  ints.

---

## 3. Hazards the probe must handle

gem's report does not mention these. Its sample collector would hit H1, H2, and H3.

| # | Hazard | Status | Mitigation |
|---|---|---|---|
| H1 | `agy < 1.1.11` has no non-interactive `/usage` and would run `/usage` as a **real agent turn** every 5 min. | Inferred from the changelog | Gate on `agy --version` (0.1 s; prints bare `1.2.7`). Below the floor, report `unsupported`/`unsupported_cli_version` and never spawn `/usage`. In core, add a post-hoc envelope guard: `num_turns != 0`, a non-empty `conversation_id`, or `command.name != "usage"` → `vendor_drift`. Add `--mode plan --sandbox` as belt-and-braces; `/usage` still answers with them. |
| H2 | Logged-out print mode prints `Authentication required…` to stderr, then `Waiting for authentication (timeout 60s)` and a paste prompt. | **Verified by cld and me.** My run with an empty `HOME` and `--print-timeout 3s` still hung until my outer 20 s kill. Closing stdin does not abort the prompt either. On kill, stdout gets `{"status":"ERROR","error":"authentication failed or timed out",…}`. | Read stderr incrementally and kill the process group on the `Authentication required` marker. Report `unauthenticated`/`logged_out`. Also map the stdout ERROR envelope's "authentication" wording to the same outcome. Without this, every tick holds a probe slot for the full deadline and is misreported as `timeout`. |
| H3 | Omitted zero: the binary's struct tags are `remaining_fraction,omitempty` (proto3 `fixed32` float, non-`oneof` in the relevant message) and `reset_time,omitempty`. An **exhausted** bucket may therefore arrive without the field. | Evidence from the struct tags, which I re-checked with `strings`. Not observed, because nothing here is exhausted. The float32-widened values (e.g. `0.9612414240837097`) fit a proto float source. | Never treat a missing fraction as "skip". Cross-check the same bucket's row in the payload's `response` TSV: `0%` means exhausted (`used_percent: 100`); a non-percent status such as the 1.0.8-era `Disabled` means omit the window with a diagnostic. If neither matches, report `malformed_payload`/`partial`. Grok hit this exact class of bug (`db535fabd`, fixed by moving parsing into core). gem's sample collector `continue`s past a missing fraction, which silently drops the one window that matters most. |
| H4 | Self-update: the binary contains `AGY_CLI_DISABLE_AUTO_UPDATE` and a background updater. | Variable present; its effect was not observable | Set `AGY_CLI_DISABLE_AUTO_UPDATE=1` in the probe env (compare Muse `MUSE_NO_AUTO_UPDATE` and Grok `--no-auto-update`). |
| H5 | Log spam: each run writes `~/.gemini/antigravity-cli/log/cli-<ts>.log` (~18 KB). | Verified | Pass `--log-file <probe temp cwd>/agy-usage.log`. |
| H6 | Filtered worker env: SSH/DBUS/`*TOKEN*`/`*KEY*` variables are stripped. | Verified by cld under exact `worker_environ()` (keyring fails, falls back to file token, SUCCESS). gem verified an `env -i HOME PATH` variant. | Keep the worker's filtered env; don't hand-roll one. API-key-only users look logged out, which is acceptable because `/usage` is a subscription concept. |
| H7 | macOS logged-out behaviour (does it open a browser each backoff?) | **Unverified** (athena is headless) | Check on the Mac before relying on default-on there; the early abort in H2 is likely sufficient. |

gem's sample code also calls `proc.communicate(timeout=…)` but catches `TimeoutError`.
`subprocess.TimeoutExpired` is not a subclass of `TimeoutError` (checked), so a timeout
would be misfiled as `probe_failed`, and the child would not be killed. Use Muse's
`_subprocess_deadline` pattern with an explicit kill of the process group.

---

## 4. The key disagreement: applicability, and what the header shows

In sase-core, `is_weekly_all_window = is_all_model_scope && is_weekly_window`.
`is_all_model_scope` is true only for `account` or Claude's product scope. That flag
decides two things: the `weekly_all: always` policy, and which window becomes the
unlabeled anchor. The anchor is the min window key among `weekly_all` entries
(`_ordered_provider_entries`), and core sorts `weekly_all` entries first.

I fed a live-shaped observation through the real
`record_provider_usage_observation → load_provider_usage → provider_usage_project_indicator
→ usage_indicator_groups → build_usage_indicator_segment` stack in a temp `SASE_HOME`. I
also asked `provider_usage_summarize_for_model(windows, "claude-opus-4-6-thinking")`, the
query behind model-picker hints, alias hints, and the usage-limit disable-expiry
fallback:

| Scheme | Live (96% / 87%) | Gemini 5h at 12% | Gemini exhausted | `agy/claude-opus-4-6-thinking` when Gemini is exhausted |
|---|---|---|---|---|
| **gem:** Gemini buckets `account`, 3p buckets `models` | `🪐 96% 6d1h` | `🪐 96% 6d1h · 5h 12% 4h50m` | `🪐 0% 6d1h · 5h 0% 4h50m` | **100% used, limited by `gemini-5h`/`gemini-weekly`: wrong** |
| All buckets `account` | `🪐 100% 6d23h · wk/all 96% 6d1h` (the **3p** weekly becomes the anchor, since `3p-weekly` < `gemini-weekly`) | … | … | wrong, as above |
| **cld:** `model_family`, no core change | `''`: **nothing** | `🪐 5h/family:gemini 12% 4h50m` | `🪐 5h/family:gemini 0% 4h50m · family:gemini 0% 6d1h` | correct: limited only by `3p-*`, 0% used |
| **cld + core anchor arm** (emulated: pin + `weekly_all` on `gemini-weekly`) | `🪐 96% 6d1h` | `🪐 96% 6d1h · 5h/family:gemini 12% 4h50m` | `🪐 0% 6d1h · 5h/family:gemini 0% 4h50m` | correct |
| cld + arm + compact-name polish (cld's measurement) | `🪐 96% 6d1h` | `🪐 96% 6d1h · 5h/gemini 12% 4h50m` | `🪐 0% 6d1h · 5h/gemini 0% 4h50m` | correct |

**Resolution:** gem is right that its scheme renders well with no core change, which
cld's report did not test. But `account` is a false statement about the vendor's own
model (*"Within each group, models share a weekly limit and a 5-hour limit"*) and about
the Usage Window glossary definition (windows scoped to a model subset). It leaks into
behaviour, not just labels:

- **Model-picker and alias hints** would show `agy/claude-opus-4-6-thinking` and
  `agy/gpt-oss-120b-medium` as exhausted whenever Gemini is.
- **`usage_window_expires_at`** would size a Claude-via-agy disable from a Gemini reset.
  This is only a fallback: `usage_limit_config.py:273-298` first honours the reset hint
  parsed from the error text, and agy's limit errors usually carry `Resets in …`. gem's
  "exact millisecond backoff" benefit is therefore overstated for either scheme.

The honest scheme plus a small core rule costs ~5 lines of Rust. Muse needed the same
kind of arm (`3cae8ef` touched `indicator.rs` by +5). That is the right trade.

The arm's shape: add it in `is_weekly_all_window` only, not in `is_all_model_scope`,
matching `provider == "agy"`, `key == "gemini-weekly"`, and `model_family` `gemini`, with
a comment. `classify_scope` then stays honestly `model_family` in tooltips and the
Models panel.

**Header ordering, to accept consciously.** Groups render in provider-name order
(`961a8cea2`), so `agy` sorts first. It also becomes the provider a click on the cluster
opens. At narrow budgets it pushes one more provider into `+N` overflow; cld measured
Codex dropping out at 40 cells. Ship with name order; revisit (e.g. order by
`llm_autodetect_priority`) only if it annoys you.

The Gemini 5-hour and the `3p-*` windows stay on the generic default: shown below 20%
remaining. That matches Claude's `session` window and the vendor's framing of 5 h as a
global-demand smoother. If you never route agy to Claude/GPT, the `3p-*` windows sit at
100% and stay hidden.

---

## 5. Where the normalizer lives

The options:

- **Python normalizer plus core validation.** This follows the Codex/Claude pattern;
  gem's Option 2 and Stage 1 of its hybrid.
- **Rust normalizer.** This follows the Grok/Muse pattern.

Choose Rust, and skip the staged hybrid:

- The project rules say shared backend behaviour belongs in `sase-core`
  (`rust_core_backend_boundary`, decision `rust-core-required`). A vendor-payload
  normalizer whose output drives CLI, TUI, hints, and backoff meets that litmus test.
- The precedent trend points the same way. Codex (`codex_collector.py`) and Claude
  (`_claude_support_windows.py`) are the older Python-normalizing collectors. Grok was
  *moved* to core after its omitted-zero bug (`db535fabd`, "collect Grok omitted-zero
  billing through core"). Muse went core-first.
- The "wheel friction" gem cites is one ordinary release cycle. Muse shipped as
  `sase-core` `3cae8ef` (+835 lines) and `sase` `608640272` (+1,041 lines, bumping
  `sase-core-rs` and `sase-core-revision.txt`), both on 2026-09-20. A staged hybrid would
  write the normalizer twice, and the Python version would carry exactly the
  omitted-zero trap (H3) that core was chosen to own.

The collector (subprocess, version gate, stderr watch) stays in Python, like `muse.py`
and `grok.py`. It is process I/O glue, not domain logic.

---

## 6. Recommended solution

### Phase 1 — `sase-core`

1. **`crates/sase_core/src/provider_usage/agy.rs`**, modelled on `muse.rs`, with
   `normalize_agy_usage(request)`.
   - The request carries `schema_version`, the whole `--output-format json` `payload`,
     `model_ids`, `provider`, `context_id`, `account_generation`, `request_started_at`,
     and `now`.
   - **Envelope handling:**
     - `status != "SUCCESS"`: an authentication error becomes `unauthenticated`/
       `logged_out`; anything else becomes `error`/`probe_failed` with a bounded
       diagnostic.
     - The turn-ran guard (H1) → `vendor_drift`.
   - **Buckets → windows:**
     - `key` = the bucket `id` verbatim, so users can configure
       `indicator.providers.agy.windows.gemini-5h`.
     - `used_percent = clamp((1 − remaining_fraction) × 100)`.
     - `resets_at` = the parsed `reset_time` (use `chrono`, as `grok.rs` does).
     - `duration_seconds` comes from the `window` token (`weekly` → 604800, `5h` → 18000,
       generic `<N>h|<N>d`, else `None`).
     - `period_start = resets_at − duration`.
     - `vendor_state: allowed`.
     - Pass unstarted rolling resets through unchanged.
   - **Applicability:**
     - `model_family` `gemini` for `gemini-*` buckets, with `model_ids` filtered from the
       passed catalog by the `gemini-` prefix.
     - `model_family` `3p` for `3p-*`, with the remaining catalog ids.
     - Anything else → `unknown` with the vendor label and id. Enterprise and business
       accounts likely use different group names, so they must degrade to `unknown`
       rather than fail.
   - **Omitted fraction:** use the TSV cross-check (H3).
   - **Empty `groups`:** return an authoritative empty result, never `0%`.
   - **Envelope fields:** `account_mode: subscription`, `plan: None`. Do not persist the
     tier string from the banner.
2. **`indicator.rs`:** add the `agy`/`gemini-weekly`/`model_family gemini` arm in
   `is_weekly_all_window` (§4).
3. **Wiring:** export from `mod.rs`, bind `provider_usage_normalize_agy_usage` in
   `sase_core_py`, add a round-trip binding test, and cut a `sase-core-rs` release.
4. **Fixtures:**
   - the verified payload
   - both omitted-zero variants, plus a `Disabled` row
   - the logged-out ERROR envelope
   - a turn-ran envelope
   - an unknown group
   - an unstarted bucket
   - an integer `1` fraction
   - a projection test asserting `🪐`-anchor selection

### Phase 2 — `sase`

1. **`src/sase/llm_provider/usage/agy.py`: `collect_agy_usage(context, executable=None)`**
   - Resolve the binary via `_agy_bin()`/`SASE_AGY_PATH`.
   - Run the `agy --version` floor check at `1.1.11`.
   - Spawn this in its own process group, from the probe's managed temp cwd, with stdin
     `DEVNULL`:

     ```
     agy -p /usage --output-format json --mode plan --sandbox --print-timeout 15s \
         --log-file <cwd>/agy-usage.log
     ```

   - Use the inherited worker env plus `AGY_CLI_DISABLE_AUTO_UPDATE=1`, and keep Muse's
     deadline margins.
   - Run a stderr reader thread that kills on `Authentication required`.
   - `json.loads(stdout)` → the core binding with `model_ids` taken from
     `AgyProvider.llm_known_model_names()`.
   - Map failures: `FileNotFoundError` → `not_installed`, deadline → `timeout`, bad JSON
     → `parse_error`.
   - A plain `Popen` is simpler than `JsonLineSession`, because this is one request and
     one response.
2. **`AgyProvider`:** add `llm_usage_capabilities → {"probe": True, "passive_events":
   False}` and an `llm_usage_probe` that delegates lazily to the collector. Bump the
   `sase-core-rs` floor and `sase-core-revision.txt`.
3. **Compact-name polish** (`_usage_indicator_format._scope_suffix`, compact form only):
   render `model_family` as the bare family (`5h/gemini`, `3p`). Keep `family:gemini` in
   tooltips and `sase usage list`. agy is the first and only `model_family` emitter, so
   nothing else changes. I recommend including this in v1 rather than leaving it
   optional: it saves 7 cells per badge in a budget-constrained header. Add a visual
   snapshot at 60/80/140 columns. Read `sase/memory/tui.md` before touching this.
4. **Docs/config:**
   - `docs/agent_providers.md` Antigravity section: "Subscription usage: zero tokens,
     ~3–5 s per refresh, requires agy ≥ 1.1.11".
   - Add agy to the collector lists in `docs/llms.md` and `docs/configuration.md`.
   - Add a commented `agy` indicator example to `default_config.yml` (pin `gemini-5h`,
     hide `3p-*`).
5. **Tests:** a scripted fake-`agy` fixture (like `tests/.../usage_probe/muse_msp_cli.py`)
   covering:
   - success
   - an old version (assert `/usage` is never spawned)
   - an auth prompt (assert the kill happens well under the deadline, and the result is
     `logged_out`)
   - a timeout
   - malformed JSON
   - omitted-zero
   - a turn-ran envelope

**No feature flag.** The user-facing switch is the existing permanent config
`llm_provider.usage_metrics.providers.agy.enabled`. Phase 1 exposes nothing by itself.
Both reports agree.

**Optional later:**

- Mark agy's refresh due when an `AgyProvider.invoke` run finishes, via
  `_mark_usage_refresh_due`, for post-run freshness.
- Surface `/credits` (a pay-as-you-go balance, not a window) as a Models-panel line.
- Replace the growing `provider == "…"` anchor allowlist (claude, grok, muse, now agy)
  with a declarative "headline window" hint on the observation wire. That is a schema
  change and should not block this work.

**Size:** Muse, the closest analogue, was ~1,880 lines across both repos. agy has no
session protocol, so expect **~700–900 lines**, mostly fixtures and tests.

---

## 7. Open items and residual risk

1. **The omitted-zero shape is unobserved.** The TSV cross-check covers both
   possibilities. Capture a real exhausted payload when one occurs and add it as a
   fixture.
2. **macOS logged-out behaviour** (H7). Verify before relying on it on the Mac.
3. **Whether `AGY_CLI_DISABLE_AUTO_UPDATE` takes effect** before the updater's
   15-minute fast path. It is harmless to set either way.
4. **Enterprise, API-key, and ADC accounts' `/usage` output** is untested. Unknown groups
   degrade to `unknown` applicability.
5. **Catalog lag.** A new Gemini model that agy ships before SASE's catalog knows it will
   match `does_not_apply`. This is a catalog-bump chore; prefix matching in core would
   remove it, but it would change the applicability wire.

## 8. Side findings (out of scope)

- `_SUPPORTED_AGY_TRAJECTORY_VERSIONS = {"1.0.10"}` (`_subprocess_agy.py:24`), and
  `SASE_AGY_TOOL_TRAJECTORY_VERSION_ALLOWLIST` is unset. On the installed `1.2.7`,
  trajectory tool-call extraction and structural no-progress detection are therefore
  silently off. cld found this; I confirmed it.
- `agy 1.2.7` supports `--output-format json|stream-json` and `--effort`, but the
  `agy.py` docstring and `invocation_option_args` still say neither exists. cld found
  this.

## 9. Provenance

- **Researcher reports:** read via `sase artifact read`:
  - cld (`file:explicit:cc7f8ddb81337502af00a116`)
  - gem (`file:explicit:e6049a9af814d97937701bf5`)
- **Lead verification commands (athena, 2026-09-21 ~18:58Z):**
  - `agy --version`, `agy --help`, `strings` over the binary for struct tags
  - one `agy -p /usage --output-format json --mode plan --sandbox --print-timeout 15s
    --log-file …` run (zero tokens)
  - one logged-out run: `env -i HOME=<empty>`, `--print-timeout 3s`, outer `timeout 20`
- **Simulation:** `/tmp/agy_lead_sim/sim.py`, run against the real core bindings and the
  TUI renderer in a temp `SASE_HOME`; the real store was untouched.
- **Code read:**
  - `sase`: `usage/{refresh,_facade,types,transport,muse,grok,codex_collector,_claude_support_windows}.py`,
    `usage_limit_window_reset.py`, `usage_limit_config.py`,
    `ace/tui/widgets/{_provider_usage_indicator,_usage_indicator_format}.py`,
    `llm_provider/{agy,_subprocess_agy}.py`, `model_alias_defaults.yml`
  - `sase-core` (opened via `sase repo open`): `provider_usage/{indicator,mod}.rs`, and
    the commit history of `muse.rs`/`grok.rs`
- **Memory:** `glossary:usage-window`.
