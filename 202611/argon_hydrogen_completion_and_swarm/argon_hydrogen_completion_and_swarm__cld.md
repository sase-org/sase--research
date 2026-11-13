# Supporting Gemini 4 Argon and Hydrogen in SASE (researcher `cld`)

_Research date: 2026-11-13, one day after Google shipped Gemini 4 Hydrogen._

## Summary

- **Argon is already in the catalog.** Commit `4d8940d4b7` (2026-10-14) added
  `gemini-4-argon-{high,medium,low}` to the `agy` catalog. Its "needs Google AI Ultra"
  advisory is now out of date: Antigravity opened Argon to paid Google AI Pro.
- **Hydrogen is not in the catalog.** It shipped on 2026-11-12. This account's `agy`
  already serves `gemini-4-hydrogen-{high,xhigh,medium,low}`, and I confirmed live runs
  with both `gemini-4-hydrogen-xhigh` and the bare `gemini-4-hydrogen`.
- **Nearly every completion surface reads one file,
  `src/sase/llm_provider/models.yml`.** These all pick up a catalog edit with no further
  code: ACE `%model` completion, macro `model`-argument completion, the model picker,
  the Rust macro LSP (and so editors), validity checks, short-alias resolution, usage
  probes, and the generated docs tables. One hand-kept list also needs editing: the
  `short_model_name` keyword list in the agent list. Shell `--model` completion lists no
  concrete models for any provider, so that is a separate gap.
- **`#research_swarm` lives in the `sase-research-artifacts` plugin, not in sase.** It
  uses `agy/gemini-3.8-flash-high` in two places: the `gemini_model` input default, and
  a member of the plugin's `@image` alias pool.
- **There is a live break next to this work.** The `agy` tier defaults
  (`gemini-3.7-flash-high` / `-low`) are now Enterprise-only, and `agy` rejects them on
  this (paid Pro) account: `model gemini-3.7-flash-high is not recognized`. Any launch
  that resolves the bare `agy` tier fails today.

**Recommendation (details at the end):**

1. Make one manifest-driven sase commit. It adds four Hydrogen slugs right after Argon,
   corrects the Argon advisory, moves the `agy` tiers to Gemini 3.8 Flash (open to all
   plans), adds `hydrogen` to `short_model_name`, and regenerates the docs.
2. Make one plugin commit that sets `gemini_model` (and the `@image` agy member) to
   `agy/gemini-4-hydrogen-xhigh`.
3. Defer to follow-up beads: `agy --effort` support, the Orchestrator, Carbon, a wider
   catalog refresh, and concrete models in shell completion.

---

## 1. What Google shipped

| Fact | Gemini 4 Hydrogen | Gemini 4 Argon | Gemini 4 Carbon | Gemini 3.8 Flash |
| --- | --- | --- | --- | --- |
| Released | 2026-11-12 | 2026-10-13 | (earlier) | — |
| Positioning | "Daily driver" for everyday coding and agentic work; Google says it **replaces 3.8 Flash** and drops the Flash name | Efficient frontier model: deep, long-horizon reasoning with fewer tokens than Carbon | Strongest reasoning model | Previous-generation Flash, still "Stable", no shutdown date |
| Gemini API ID | `gemini-4-hydrogen` | `gemini-4-argon` | `gemini-4-carbon` | `gemini-3.8-flash` |
| Thinking levels | low / medium / **high (default)** / **xhigh (new)** | low / medium / high | low / medium / high | low / medium / high |
| `agy` CLI slugs (this account) | `gemini-4-hydrogen-{high,xhigh,medium,low}` | `gemini-4-argon-{medium,high,low}` | not visible (Ultra-only) | `gemini-3.8-flash-{high,medium,low}` |
| Antigravity plans | Docs table: all plans. Launch blog and press: paid Pro and Ultra. **The sources conflict.** | Pro (paid, or eligible trial) ✝, Ultra, Enterprise; not Free/Plus | Ultra and Enterprise | All plans |
| Price (per M tokens, in/out) | $1.50 / $7.50 | $2 / $10 intro until Nov 30, then $4 / $20 | — | — |
| Context | 1M in, up to 1M out | 1M | 1M | — |
| AA Intelligence Index | 41 (medium), **51 (high)**, **54 (xhigh)** | 50 | 59 | — |
| Terminal-Bench 4.1 | 57% | — | — | 18.2% |

Other points that matter for SASE:

- **Orchestrator.** This is a new Antigravity model-picker option that pairs a planner
  (Carbon or Argon) with Hydrogen as the executor. Its configuration is fixed, so it
  takes no effort level. On this account it appears in `agy models` as
  `gemini-pro-orchestrator-g1-pro` ("Orchestrator (Argon)"). Google's docs only show it
  by display name (`--model "Orchestrator (Argon)"`).
- **Removals.** The Antigravity models page says Claude Sonnet 4.6, Claude Opus 4.6, and
  GPT-OSS-120b "will be removed on November 18, 2026." Gemini 3.7 Flash, 3.6 Flash, and
  3.1 Pro are now listed as **Enterprise-only**. Gemini 3.5 Flash is no longer listed.
- **Research fitness.** Google cites Hydrogen at #5 on Agent Arena for "deep research,
  data analysis, and broad codebase navigation", and tied for #1 on Vals Legal Research
  Bench. For research swarms it is clearly stronger than 3.8 Flash, the model it
  replaces.

## 2. Live probe of this machine's `agy` (v1.5.8)

`agy models` on this account, which looks like paid Google AI Pro (Argon is visible,
Carbon is not):

```text
gemini-4-argon-medium / -high / -low
gemini-4-hydrogen-high / -xhigh / -medium / -low
gemini-pro-orchestrator-g1-pro     Orchestrator (Argon)
gemini-3.8-flash-high / -medium / -low
claude-opus-5-5-{low,medium,high}, claude-sonnet-5-5-{low,medium,high}
gpt-oss-120b-medium
```

Each probe was a one-line "reply OK" prompt with `--output-format json`:

| Invocation | Result |
| --- | --- |
| `--model gemini-3.7-flash-high` (**current sase `large` tier**) | **ERROR** `model gemini-3.7-flash-high is not recognized as a known model…` |
| `--model gemini-4-hydrogen-xhigh` | SUCCESS (1.3 s) |
| `--model gemini-4-hydrogen` (no suffix) | SUCCESS; the base slug is an alias that resolves to the default level |
| `--model gemini-4-hydrogen --effort xhigh` | SUCCESS; the log shows `model alias "gemini-4-hydrogen" resolved to "gemini-4-hydrogen-xhigh"` |
| `--model gemini-4-argon --effort xhigh` | ERROR `gemini-4-argon has no "xhigh" effort (available: low, medium, high)` |
| `--model gemini-4-argon-high --effort low` | ERROR `--model gemini-4-argon-high conflicts with --effort=low` |

What this shows:

1. Hydrogen's slugs follow the same `<model>-<level>` pattern as Argon and Flash, so the
   existing "effort lives in the slug" approach still works.
2. `agy` now has a real `--effort` flag (`low|medium|high|xhigh|max`) that works with a
   bare base slug. SASE's `AgyProvider.invocation_option_args` still says "Antigravity
   exposes no reasoning-effort mechanism today" (`supported={}`), which is no longer
   true. Changing that is optional; see D4.
3. The `agy` tier defaults are broken today on non-Enterprise accounts. SASE's own test
   `test_agy_tier_mapping_never_routes_to_an_advisory_model` says "Agy tiers must work
   for every account", and that invariant is now violated in reality even though the
   test still passes.

## 3. How sase is wired today

### 3.1 The catalog is the single source of truth

`src/sase/llm_provider/models.yml` is, in its own words, "the single edit point for
routine built-in model maintenance." `model_manifest.py` validates it, and
`AgyProvider` answers four hooks straight from it: `llm_known_model_names`,
`llm_model_short_aliases`, `llm_model_advisories`, and `llm_resolve_model_name`. The
manifest also requires every tier default and advisory key to name a catalogued model.

### 3.2 Inventory of model completion and display surfaces

| # | Surface | Source of data | Hydrogen change needed |
| --- | --- | --- | --- |
| 1 | ACE prompt `%model:` / `%m:` inline completion (`directive_completion.py`, `model_explicit_completion.py`) | `build_model_completion_catalog()` → provider metadata → `models.yml` | **None** (automatic) |
| 2 | Macro `model`-typed argument completion, e.g. `#research_swarm(gemini_model=…)` (`_file_completion_base_inventories.py`, `macro_arg_model`) | Same catalog | **None** |
| 3 | ACE model picker and Launch Control models panel (`model_picker_rows.build_model_rows`, short-alias jump hints) | Registry metadata | **None** in code. **Tests and snapshots may move** (see Risks) |
| 4 | Rust macro LSP, and through it editors such as sase-nvim (`integrations/macro_lsp.py` → `model_completion_catalog_payload()`) | Same catalog, snapshotted at LSP launch | **None**. Editors pick it up when the LSP restarts. I could not open sase-nvim locally (no primary checkout), but it consumes this LSP payload. |
| 5 | Model validity snapshot for the Rust classifier (`model_validity.py` → `sase_core::model_validity`) | `model_to_provider_map()` | **None**. A `provider/model` value such as `agy/gemini-4-hydrogen-xhigh` is accepted even without a catalog entry; a **bare** `gemini-4-hydrogen-xhigh` resolves only once catalogued. |
| 6 | Short-alias resolution (`%m:hydrogen4x`) and the usage-indicator labels | `model_short_alias_map()` | Add `short_aliases` entries |
| 7 | Advisory markers in completion and the picker, plus the doctor advisory check | `llm_model_advisories` | Update the Argon entry (§D2) |
| 8 | Agy usage probe `model_ids` and window applicability (`usage/agy.py`; Rust `provider_usage/agy.rs` keys on the `gemini-` prefix) | Known names | **None**. `gemini-4-hydrogen-*` falls in the `gemini` family. |
| 9 | Generated docs: `docs/reference/providers/models.md` (known models, short aliases) and the `agy.md` tier table | `just fix` regenerates them | Regenerate, then edit the `agy.md` "Model Mapping" prose by hand |
| 10 | Agent-list compact model label `short_model_name()` (`ace/tui/widgets/_agent_list_helpers.py:10`) | **Hand-kept keyword tuple** (`"argon"` added in the Argon commit) | **Add `"hydrogen"`**. Without it, Hydrogen rows show `gemini`. |
| 11 | Shell completion for `--model` (`completion/candidates/catalog_build.py:182`) | **Hard-coded** to the five size aliases only | Lists no concrete model for any provider. Out of scope; see D7. |
| 12 | sase-core (Rust) | No model catalog; Python passes model IDs in | **None** |

Surfaces 1–9 and 12 are data-driven, so adding Hydrogen to the catalog is mostly a YAML
edit plus tests. That matches how the Argon commit was built: 16 files, of which only 2
were non-test source files outside the YAML.

### 3.3 Where `#research_swarm` gets its Gemini model

`sase macro show research_swarm` shows the definition lives in the
**`sase-research-artifacts`** plugin:
`src/sase_research_artifacts/xprompts/research_swarm.md`. The Gemini model appears in
two places:

- The input `gemini_model` (line ~71) defaults to `"agy/gemini-3.8-flash-high"`. Its
  description says effort is chosen through the slug (`-high`/`-medium`/`-low`). Line
  158 maps it to the `gem` researcher, which runs only when `gemini=true` and `agy` is
  not hard-disabled.
- The plugin's `default_config.yml` `@image` alias pool is
  `codex/gpt-6.1-sol@xhigh | grok/grok-4.6@xhigh | agy/gemini-3.8-flash-high`. That pool
  drives the swarm's `<clan>.image` agent.

The same default string also appears in the plugin's `README.md`,
`docs/configuration.md`, `docs/macros.md`, `tests/test_default_config.py`, and
`tests/test_macro_loading.py`. Its `CHANGELOG.md` is managed by release-please and must
not be edited.

The user's global config (chezmoi `home/dot_config/sase/sase.yml`) has an `rsa` snippet,
`#research_swarm(…gemini=true…)`. It does not override `gemini_model`, so the plugin
default is the only value to change.

## 4. Design decisions

### D1. Catalog entries, order, and short aliases

- **Add** `gemini-4-hydrogen-xhigh`, `gemini-4-hydrogen-high`, `gemini-4-hydrogen-medium`,
  and `gemini-4-hydrogen-low` **after the Argon block** and before 3.8 Flash.
  - This follows the CLI's family order (Argon, then Hydrogen, then Flash).
  - Within the family, list levels highest-first, matching the existing Argon and Flash
    blocks. The CLI lists the default level first (high, xhigh, …), but the manifest has
    never copied that within a family.
  - Keeping Argon first leaves `tests/test_model_picker_jump.py` (expects
    `gemini-4-argon-high` and `-medium` right after `__default__`) and the models-panel
    PNG test (waits for `gemini-4-argon-high`) pinned to the same first row.
- **Short aliases** follow the `<family><gen><level-initial>` pattern (`argon4h`,
  `flash38h`), using `x` for xhigh: `hydrogen4x`, `hydrogen4h`, `hydrogen4m`,
  `hydrogen4l`.
- **Argon needs no new entries.** Its three slugs still match `agy models`. "Supporting
  Argon" here means fixing its advisory and display, not cataloguing it again.
- I rejected cataloguing the base slug `gemini-4-hydrogen` (no suffix). It works in
  `agy`, but its level depends on the CLI default. Effort should stay explicit in the
  slug until D4 is done.

### D2. Advisories

- **Argon:** the current label "needs Google AI Ultra" is wrong. Rewrite it as `info` /
  "needs Google AI Pro or Ultra". Detail: Antigravity serves Argon on paid Google AI Pro
  (or eligible-device trials), Google AI Ultra, and Gemini Enterprise, not on Free or AI
  Plus, and `agy` exits with an error when the account cannot use it. Rename and update
  `test_agy_flags_argon_as_ultra_gated` in `tests/llm_provider/test_model_advisories.py`
  to match.
- **Hydrogen:** I recommend **no advisory for now**. Antigravity's own models table
  lists it for every plan, while the launch blog and press say "paid Pro and Ultra." An
  advisory that turns out wrong is lasting noise in every completion row. A missing one
  costs at most a clear `agy` error that lists the available models. Revisit once a Free
  account's `agy models` output settles the question.

### D3. Tier defaults (the live break)

`large: gemini-3.7-flash-high` and `small: gemini-3.7-flash-low` no longer work for
Free, Plus, Pro, or Ultra accounts. Options:

| Option | Pros | Cons |
| --- | --- | --- |
| **A. 3.8 Flash high/low** | Open to every plan per Google's table, so the "tiers work for every account" invariant holds again. No advisory question. Same family as today. | Google now calls it previous-generation; Hydrogen is much better (Terminal-Bench 57% vs 18%). |
| B. Hydrogen high/low | Google's new everyday model, 2.5× faster than 3.8 Flash and far stronger | Free-plan availability in Antigravity is disputed; promoting it could recreate today's break for Free users |
| C. Leave as-is | No churn | Bare `agy` launches stay broken |

**Recommend A in this change**, and file a follow-up to move to B once Free-plan access is
confirmed. This is a scope addition beyond what was asked. I recommend it because it
edits the same YAML block, the new docs paragraph has to describe the tiers anyway, and
it repairs a failure that exists today. It moves these tests:
`tests/llm_provider/test_agy_provider_core.py` (lines 51–53, 119, 155, 261) and
`tests/test_agy_integration_polish.py` (`_AGY_LARGE` / `_AGY_SMALL`, plus
`flash37h`/`flash37l` → `flash38h`/`flash38l`). `tests/doctor/test_checks_providers_default.py`
uses a self-contained fixture payload and can stay.

### D4. Effort: slug variants vs. `agy --effort`

`agy` 1.5.8 now resolves `--model <base> --effort <level>` and rejects conflicting or
unsupported combinations (see the probe table). SASE could therefore accept
`agy/gemini-4-hydrogen@xhigh` and map it to `--model gemini-4-hydrogen --effort xhigh`.

- **Pros:**
  - The swarm defaults would line up (`@xhigh` everywhere).
  - The ACE effort picker would mean something for `agy`.
  - The `size-alias-effort-ladder` decision's special case ("Antigravity … carries no
    `@effort` suffix") could go away.
- **Cons:**
  - Supported levels differ per model (Hydrogen has xhigh, Argon and Flash do not, the
    Orchestrator has none). `effort_cli_args` takes one per-provider map, so this needs
    a per-model support map.
  - Suffixed slugs and an effort conflict, so the catalog would need base slugs.
  - It needs a minimum-`agy`-version gate.
  - It means writing a new decision record that partly supersedes
    `size-alias-effort-ladder`.

**Defer to a separate feature bead.** Hydrogen works with the existing slug-variant
model, so the request does not depend on this.

### D5. Which Hydrogen variant for `#research_swarm`

Every other swarm researcher defaults to its provider's top rung (`@xhigh`). For
Hydrogen, xhigh scores 54 vs 51 for high on the AA index. Artificial Analysis puts the
cost per task at about $3.16 vs $1.87 (for `agy` this means plan quota, not dollars).
Swarms run rarely and depth is the point, so **use `agy/gemini-4-hydrogen-xhigh`**. Use
the same value for the `@image` pool's agy member, which keeps the plugin's
"every member at top effort" pattern and removes the last Gemini 3.8 Flash reference in
the swarm.

Changing the `@image` member is a judgment call. The user asked about "the current
Gemini model that we use for that macro swarm", and `agy/gemini-3.8-flash-high` is that
model in both places. If you want to limit the change to the researcher, leave
`@image` alone.

The plugin needs **no `sase` floor bump**. The Rust classifier accepts any `agy/<rest>`
value, and `agy` itself validates the slug at launch. The plugin change can therefore
land before or after the sase catalog change; landing sase first just gives nicer picker
labels sooner.

### D6. Orchestrator and Carbon

- **Orchestrator (Argon), `gemini-pro-orchestrator-g1-pro`:** defer. The slug is opaque
  and undocumented (Google's docs use the display name, which has spaces and
  parentheses that the `%model` completion catalog's inline-value regex
  `^[A-Za-z0-9_\-=./@]+$` in `macro/_model_completion_catalog.py` rejects).
  It takes no effort. Its planner/executor hand-offs inside one `agy --print` turn have
  not been tested against SASE's no-progress guard. Also, `short_model_name` would label
  it `pro` today, because the `"pro"` keyword matches before anything else.
- **Carbon:** not requested, Ultra-only, and its CLI slugs cannot be confirmed from this
  Pro account. The agy changelog implies `gemini-4-carbon-{low,medium,high}`. File a
  follow-up to catalog it with the old "needs Google AI Ultra" advisory text, which fits
  Carbon exactly.

### D7. Shell completion

`sase … --model <TAB>` completes only `xsmall…xlarge`, for every provider. Adding
concrete models there means teaching `model_candidates()` to read `models.yml` (cheap,
no plugin load) and deciding between `provider/model` and bare forms. That is a general
feature, not a Hydrogen change, so it belongs in a feature bead. If "all model
completion surfaces" is meant literally, this is the one surface the catalog edit will
not reach.

### D8. Shipped size aliases

Leave them unchanged. `@xsmall` keeps `agy/gemini-3.8-flash-high`, which is still open
to every plan. Moving Hydrogen into the ladder is a separate policy call under
`decisions:size-alias-effort-ladder`. A first appearance at xhigh would make Hydrogen
far too heavy for `@xsmall`, and a higher alias needs its own rung analysis.

## 5. Risks and gotchas

- **Visual PNG snapshots.** The models-panel and picker snapshots render the agy rows
  near the top. Four new rows after Argon can shift visible content. If the visual lane
  fails, regenerate with `just update-visual-snapshots`, after reading the `tui.md` /
  `tui_screenshot.md` memory.
- **Hard-coded model lists in tests.**
  - `test_agy_provider_core.py` (`_AGY_MODELS`, alias dict)
  - `test_agy_usage_probe.py` (`_GEMINI_IDS`)
  - `test_model_advisories.py` (agy list, `_ARGON_SLUGS`, `_FLASH_SLUGS`)
  - `test_agent_list_helpers.py` (add a Hydrogen case)
- **Bare vs. provider-prefixed values.** Only catalogued slugs resolve without `agy/`.
  Keep the swarm default provider-prefixed (`agy/…`) as it is today.
- **Generated docs drift.** Run `just fix` so `docs/reference/providers/models.md` and
  `agy.md` regenerate. The hand-written Argon paragraph in `agy.md` currently states the
  Ultra-only claim and "tier defaults stay on Gemini Flash", so it needs editing.
- **`agy` version.** The 1.5.8 changelog adds Hydrogen for `GEMINI_API_KEY` and ADC
  logins. For Google-account logins the model list appears to come from the server. If
  a host's `agy models` lacks Hydrogen, the fix is `agy update`.
- **Other stale 3.7-Flash pins.** Outside this change, several pins now fail on
  non-Enterprise accounts:
  - sase's own `sase/macros/reads.md` (`agy/gemini-3.7-flash-high`)
  - doc examples (`docs/reference/macros/directive-syntax.md`, `config/agents*.md`,
    `default_config.yml` and schema comments)
  - the chezmoi snippets `m_agy`, `m_agy_pro`, `m_agy_pro_flash`, `m_swarm`
  - `home/bin/executable_tmux_ai_window`

## 6. Recommended solution

### Commit 1: sase, "catalog Gemini 4 Hydrogen on Antigravity"

1. In `src/sase/llm_provider/models.yml`, under `providers.agy`:
   - Insert `gemini-4-hydrogen-xhigh`, `-high`, `-medium`, and `-low` after the three
     Argon slugs.
   - Add `short_aliases` `hydrogen4x/h/m/l`.
   - Rewrite the three Argon advisories as `info` / "needs Google AI Pro or Ultra", with
     the Pro/Ultra/Enterprise detail.
   - Set `tiers.large: gemini-3.8-flash-high` and `tiers.small: gemini-3.8-flash-low`.
   - Update the header comment, e.g. "Hydrogen and Argon are reachable by name; tiers
     stay on 3.8 Flash because it is the only Gemini family Antigravity serves on every
     plan."
2. In `src/sase/ace/tui/widgets/_agent_list_helpers.py`, add `"hydrogen"` to the
   `short_model_name` keyword tuple, before `"flash"`.
3. Update the tests:
   - Hydrogen slugs and aliases in `test_agy_provider_core.py`, `test_agy_usage_probe.py`,
     and `test_model_advisories.py`.
   - The Argon advisory assertions.
   - The tier assertions in `test_agy_provider_core.py` and
     `test_agy_integration_polish.py`.
   - A new `short_model_name("gemini-4-hydrogen-xhigh") == "hydrogen"` case.
   - Keep `test_agy_tier_mapping_never_routes_to_an_advisory_model` green: 3.8 Flash
     carries no advisory.
4. Run `just fix` to regenerate the provider docs tables, then rewrite the Model Mapping
   paragraph in `docs/reference/providers/agy.md`. It should cover:
   - Argon on Pro, Ultra, and Enterprise.
   - Hydrogen's four slugs, including `-xhigh`.
   - Why the tiers sit on 3.8 Flash.
5. Verify:
   - `sase tool run check` (not raw `just check`).
   - The visual lane, regenerating snapshots only if the agy rows moved.
   - A live smoke run: `sase run` with `%m:agy/hydrogen4x` and a trivial prompt, plus a
     bare `agy`-tier launch, which should now succeed.

### Commit 2: sase-research-artifacts, "default the gemini researcher to Gemini 4 Hydrogen"

1. In `xprompts/research_swarm.md`, set `gemini_model.default` to
   `"agy/gemini-4-hydrogen-xhigh"`. Update the description to "choose effort through
   the model slug (`-xhigh`/`-high`/`-medium`/`-low`)".
2. In `default_config.yml`, change the `@image` pool's agy member to
   `agy/gemini-4-hydrogen-xhigh` (optional; see D5).
3. Update `README.md`, `docs/configuration.md`, and `docs/macros.md` (three mentions),
   plus `tests/test_default_config.py` and `tests/test_macro_loading.py` (lines ~687,
   806, 1044–1045). Do not touch `CHANGELOG.md`.
4. Verify with `sase tool run check` in the plugin. Then run
   `sase macro explain` or `sase macro show research_swarm` to confirm the default.
   Optionally launch a one-off `#research_swarm(gemini=true, codex=false, claude=false)`
   on a throwaway prompt.

### Follow-up beads (use `/sase_new_task`; do not bundle them)

- **feature:** `agy` reasoning-effort passthrough via `--effort` and base slugs, with a
  per-model level map (D4).
- **feature:** catalog Gemini 4 Carbon (Ultra advisory) and decide on Orchestrator
  (Argon) (D6).
- **bug:** refresh the agy catalog against current `agy models`. Add the Claude 5.5
  slugs. Prune or mark Enterprise-only Gemini 3.7/3.6/3.5 Flash and 3.1 Pro. Drop Claude
  4.6 and GPT-OSS after their 2026-11-18 removal.
- **bug:** move the stale `agy/gemini-3.7-flash-high` pins in `sase/macros/reads.md` and
  in doc examples.
- **feature (optional):** concrete models in shell `--model` completion (D7).
- **user config (chezmoi):** repoint `m_agy*`, `m_swarm`, and `tmux_ai_window` from 3.7
  Flash to `gemini-4-hydrogen-high` or 3.8 Flash.
- **policy (later):** promote Hydrogen to the agy tier defaults, and possibly the size
  ladder, once Free-plan Antigravity access is confirmed.

## Sources

- Antigravity docs, "Choose a model" (plan table, Orchestrator, removal dates):
  <https://antigravity.google/docs/models/>
- Antigravity CLI effort docs: <https://antigravity.google/docs/cli/commands/effort>
- Antigravity blog, "Gemini 4 Hydrogen and Orchestrator now in Google Antigravity":
  <https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity>
- Google blog, "Introducing Gemini 4 Hydrogen":
  <https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/>
- Gemini API models page (model codes, 3.x status): <https://aistudio.google.com/docs/models>
- Google blog, "Gemini 4 Argon":
  <https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-argon/>
- InfoWorld, "Google adds multi-model Orchestrator, Gemini 4 Hydrogen, to Antigravity":
  <https://www.infoworld.com/article/4248403/google-adds-multi-model-orchestrator-gemini-4-hydrogen-to-antigravity.html>
- 9to5Google launch coverage: <https://9to5google.com/2026/11/12/gemini-4-hydrogen-launch/>
- The Decoder, benchmark tables:
  <https://the-decoder.com/googles-gemini-4-hydrogen-outscores-the-bigger-argon-just-four-weeks-after-its-launch/>
- SiliconANGLE, pricing and Argon intro pricing:
  <https://siliconangle.com/2026/11/12/google-releases-gemini-4-hydrogen-a-lower-cost-model-said-to-outscore-argon/>
- Local evidence: `agy models`, `agy changelog`, and the `--model`/`--effort` probes
  (agy 1.5.8, 2026-11-13); sase commit `4d8940d4b7`; `sase macro show research_swarm`.
