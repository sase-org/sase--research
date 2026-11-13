# Argon + Hydrogen model support in SASE — research report (`mus`)

## Bottom line

Argon is already done. `gemini-4-argon-{high,medium,low}` shipped in commit
`4d8940d4b7` ("feat(llm): catalog Gemini 4 Argon on Antigravity", 2026-10-14),
and that commit is the exact template for Hydrogen. A live `agy models` run on
this machine (2026-11-13) shows the Hydrogen slugs SASE must add:

- `gemini-4-hydrogen-high`
- `gemini-4-hydrogen-xhigh` (note: Argon has no `xhigh` variant)
- `gemini-4-hydrogen-medium`
- `gemini-4-hydrogen-low`

**Recommended solution:** mirror the Argon commit one-to-one — (1) add the four
Hydrogen slugs plus short aliases plus an Ultra-gating `info` advisory to the
`agy` section of `src/sase/llm_provider/models.yml`, keeping tier defaults on
Gemini Flash and keeping shipped size aliases Hydrogen-free; (2) add
`"hydrogen"` to the `short_model_name` keyword list in
`src/sase/ace/tui/widgets/_agent_list_helpers.py`; (3) run `just fix` to
regenerate the model tables in `docs/reference/providers/models.md`
(`tools/render_model_docs` owns the `known-models` / `model-short-aliases`
blocks) and hand-extend the Argon prose paragraph in
`docs/reference/providers/agy.md`; (4) change the `gemini_model` default in the
`#research_swarm` xprompt (lives in the `sase-research-artifacts` sidecar, not
this repo) from `agy/gemini-3.8-flash-high` to `agy/gemini-4-hydrogen-high`;
(5) update the pinned catalog expectations in tests; (6) verify with
`just check`. Details and rationale for each step are below.

## Status of the two asks

### Argon: nothing to do

`src/sase/llm_provider/models.yml` already catalogues
`gemini-4-argon-high/medium/low` with `argon4h/m/l` short aliases and an `info`
"needs Google AI Ultra" advisory on each slug, and the advisory hook is wired
in `src/sase/llm_provider/agy.py` (`llm_model_advisories` reads the manifest,
so any new advisory entered in YAML flows to every surface with no Python
change). Docs tables already list Argon. "All model completion surfaces"
already include Argon wherever they derive from the registry (see inventory).
The only remaining Argon-shaped work is Hydrogen.

### Hydrogen: new, four slugs confirmed live

Output of `agy models` on this host, just now (19 lines total, header + 18
models, quoted verbatim):

```text
Fetching available models...
gemini-4-argon-medium	Gemini 4 Argon (Medium)
gemini-4-argon-high	Gemini 4 Argon (High)
gemini-4-argon-low	Gemini 4 Argon (Low)
gemini-4-hydrogen-high	Gemini 4 Hydrogen (High)
gemini-4-hydrogen-xhigh	Gemini 4 Hydrogen (XHigh)
gemini-4-hydrogen-medium	Gemini 4 Hydrogen (Medium)
gemini-4-hydrogen-low	Gemini 4 Hydrogen (Low)
gemini-pro-orchestrator-g1-pro	Orchestrator (Argon)
gemini-3.8-flash-high	Gemini 3.8 Flash (High)
gemini-3.8-flash-medium	Gemini 3.8 Flash (Medium)
gemini-3.8-flash-low	Gemini 3.8 Flash (Low)
claude-opus-5-5-low	Claude Opus 5.5 (Low)
claude-opus-5-5-medium	Claude Opus 5.5 (Medium)
claude-opus-5-5-high	Claude Opus 5.5 (High)
claude-sonnet-5-5-low	Claude Sonnet 5.5 (Low)
claude-sonnet-5-5-medium	Claude Sonnet 5.5 (Medium)
claude-sonnet-5-5-high	Claude Sonnet 5.5 (High)
gpt-oss-120b-medium	GPT-OSS 120B (Medium)
```

Three consequences:

1. The Hydrogen family is `gemini-4-hydrogen-{high,xhigh,medium,low}`. The
   `xhigh` slug is new versus Argon — it is also the first `agy` slug that
   reaches the `xhigh` effort rung, which matters for the swarm-default choice
   below.
2. `gemini-pro-orchestrator-g1-pro` ("Orchestrator (Argon)") is an
   orchestrator-internal model. Do not catalogue it: it is not a user-facing
   chat/completion model and the manifest comment says to keep exact stable
   user slugs.
3. Catalog drift exists but is out of scope: the CLI no longer lists
   `gemini-3.7/3.6/3.5-flash`, `gemini-3.1-pro`, `claude-sonnet-4-6`, or
   `claude-opus-4-6-thinking` (all still in `models.yml`), and it does list
   `claude-opus/sonnet-5-5-*` (not in `models.yml`). Per-account listings vary,
   so I verified only the Hydrogen/Argon facts and recommend filing the drift
   as a separate follow-up, not folding it into this change.

## Surface inventory: what "all model completion surfaces" concretely means

`docs/reference/providers/models.md` states the design rule: catalog membership
in `models.yml` *is* picker rows, `%model:provider/model` routing, and
completion. I verified each surface against that claim:

| Surface | Derives from manifest automatically? | Edit needed for Hydrogen? |
| --- | --- | --- |
| `src/sase/llm_provider/models.yml` (`agy` section) | n/a (source of truth) | Yes — add 4 models + aliases + advisories |
| `%model` directive completion (`src/sase/macro/model_completion.py` + `_model_completion_catalog.py`) | Yes, built from `get_llm_metadata_payload()` | No |
| TUI model picker rows | Yes, same registry payload (`tests/test_model_picker_options.py` asserts membership) | No (tests need updating, code does not) |
| TUI model-picker jump order | Yes, manifest order | No code change, but `tests/test_model_picker_jump.py` pins `visible_ids[:3]` for filter `"gemini"` — it will break and must be re-pinned |
| Agent-list short model name (`_agent_list_helpers.py::short_model_name`) | No — hardcoded keyword tuple, extended with `"argon"` by the Argon commit | Yes — add `"hydrogen"` next to `"argon"` |
| `%model` completion detail, resolved model label, `sase doctor -C llm.model_advisory` | Yes, via `model_advisory_map()` / `model_advisory_for()` in `registry.py` | No (new advisories flow through) |
| Shell completion runtime grammar cache (`src/sase/completion/`) | Yes — no hardcoded model ids found anywhere under `src/sase/completion/` | No |
| `sase.schema.json` | Only an example string (`"gemini-3.7-flash-high"`); not a value enumeration | No |
| Generated docs tables (`docs/reference/providers/models.md`, tier table in `docs/reference/providers/agy.md`) | Regenerated by `just fix` (`tools/render_model_docs`) | Run the generator; do not hand-edit tables |
| Hand-written docs prose (Argon paragraph in `agy.md`) | No | Yes — extend to Hydrogen by hand |
| `docs/llms.md` | No — it is now a moved-page shim (generated, "do not edit") | No |
| Tier defaults + shipped size aliases | Manifest data, deliberate policy choice | No change (see policy below) |
| Rust core (`sase-core`) | No hardcoded catalog; `model_validity/classifier.rs` consumes the wire `known_model_aliases` map | No change, no `sase-core-revision.txt` bump (no wire change) |
| `#research_swarm` `gemini_model` default | Lives in sidecar `sase-research-artifacts/.../xprompts/research_swarm.md` | Yes — default swap (separate repo) |

The Argon commit confirms this inventory: it touched `models.yml`, `agy.py`
(advisory hook — already in place, no repeat needed),
`_agent_list_helpers.py`, docs prose + generated tables, and tests. A Hydrogen
change should touch the same set minus `agy.py`.

## Recommended implementation (sase repo)

All paths relative to the sase checkout root.

### 1. `src/sase/llm_provider/models.yml` (`agy` section only)

- Prepend the four Hydrogen slugs to `models:`, mirroring how Argon heads the
  list (picker/completion order follows manifest order, newest first).
  Order within the family: I recommend effort-descending
  `xhigh, high, medium, low`. Rationale: the file's existing convention is
  descending (`high, medium, low`), and the file's own "keep CLI ordering"
  comment is already violated by Argon (CLI prints medium first), so
  descending is the more consistent rule. Either order works mechanically;
  pick one and note it in the commit message.
- Add short aliases. Manifest validation (`model_manifest.py`) requires each
  alias non-empty, each model known, and no duplicate alias *within the
  provider*. Recommended, parallel to `argon4h/m/l`:
  `gemini-4-hydrogen-high → hydrogen4h`,
  `gemini-4-hydrogen-xhigh → hydrogen4x`,
  `gemini-4-hydrogen-medium → hydrogen4m`,
  `gemini-4-hydrogen-low → hydrogen4l`.
  The longer `hydrogen4*` prefix (rather than `hy4*`) keeps the family
  greppable and cannot collide with any existing shorthand (`flash*`,
  `pro*`, `sonnet*`, `opus*`, `gptoss*`, `astra`, `mini`, `fable`, `haiku*`,
  `wonder*`, `spark*`, `qwen*`, `gpt*`). The `xhigh → 4x` mapping follows the
  existing first-letter convention (`4h/4m/4l`).
- Add one `info` advisory per Hydrogen slug, copying Argon's "needs Google AI
  Ultra" text verbatim unless entitlement is checked first (open question
  below). Advisory gating has a hard consequence: the guard test
  `test_agy_tier_mapping_never_routes_to_an_advisory_model` forbids pointing a
  tier at an advisory-flagged model, so adding the advisory *locks in* the
  "tiers stay on Flash" policy mechanically. That is the desired outcome.

### 2. Keep tier defaults and shipped size aliases unchanged

`tiers: large/small` stay `gemini-3.7-flash-high/low`; no Hydrogen member joins
any alias in `aliases:`. This repeats the Argon rationale verbatim: an
Ultra-gated default would break every non-Ultra account, and
`test_agy_tier_mapping_never_routes_to_an_advisory_model` enforces it. (Side
note: `3.7-flash` no longer appears in this account's `agy models` output, so
tier freshness may deserve its own follow-up; do not change tiers in this
change.)

### 3. `src/sase/ace/tui/widgets/_agent_list_helpers.py`

Add `"hydrogen"` to the `short_model_name` keyword tuple alongside `"argon"`.
Both keywords are substrings of disjoint slug families so relative order
between them is irrelevant; keep them adjacent for readability.

### 4. Docs

- Run `just fix` (`tools/render_model_docs` regenerates `known-models`,
  `model-short-aliases` in `models.md` and the `model-tiers-agy` block in
  `agy.md`). `just check` fails on stale generated content, so this is
  enforced, not optional.
- Hand-edit the Argon prose paragraph in `docs/reference/providers/agy.md`
  ("Gemini 4 Argon is catalogued as …") to cover Hydrogen the same way:
  slugs, slug-chosen effort (including the new `xhigh` variant), same
  entitlement note, same "tiers stay on Flash, no shipped alias routes to it"
  sentence.
- `docs/reference/providers/models.md` advisory section already links the
  agy integration page generically; no structural edit needed beyond the
  regenerated tables, though the parenthetical naming "the informational
  Gemini 4 Argon entitlement advisory" could be widened to "Argon/Hydrogen".

### 5. Tests to update (all pinned expectations, no behavior changes)

- `tests/llm_provider/test_agy_provider_core.py`: `_AGY_MODELS` list + the
  `llm_model_short_aliases()` dict — add the four slugs/aliases in manifest
  order.
- `tests/llm_provider/test_model_advisories.py`: add a `_HYDROGEN_SLUGS`
  tuple next to `_ARGON_SLUGS`; extend the Argon advisory assertions to cover
  it. Note `test_agy_flash_models_carry_no_advisory` stays as-is (Flash still
  unflagged).
- `tests/llm_provider/test_agy_usage_probe.py` and
  `tests/llm_provider/test_agy_usage_indicator_default.py`: extend the pinned
  model lists.
- `tests/test_model_picker_jump.py`: the `"gemini"`-filter `visible_ids[:3]`
  assertion (`__default__, gemini-4-argon-high, gemini-4-argon-medium`) will
  change because Hydrogen heads the manifest — re-pin to whatever manifest
  order dictates.
- `tests/test_model_picker_options.py`: add a Hydrogen membership assertion
  next to the existing `gemini-3.8-flash-high` / `3.7` / `3.6` lines.
- `tests/ace/tui/widgets/test_agent_list_helpers.py` (Argon cases added by the
  Argon commit): add the Hydrogen short-name case.
- Visual snapshot tests referencing Argon
  (`test_ace_png_snapshots_provider_usage_indicator.py`,
  `test_ace_png_snapshots_models_panel_navigation.py`) and the
  `prompt_next_word*` tests touched by the Argon commit: check whether they
  pin the full catalog; update only if they fail, per the "re-run on
  untouched base" rule if anything else is red.
- `tests/test_llm_provider_core.py`,
  `tests/test_load_balanced_alias_defaults.py`: no change expected (Flash
  routing assertions unaffected), but they are the canaries — run them.

### 6. Verify

`just fix` then `just check` (the manifest-policy, generated-content, and
tier-guard checks are all inside `just check`/CI). Per the decisions log,
`just check` is the agent default; `just check-full` runs only on explicit
instruction or to repair a CI failure.

## Recommended implementation (`#research_swarm`, sidecar repo)

The xprompt lives at
`sase-research-artifacts/src/sase_research_artifacts/xprompts/research_swarm.md`
(opened via `sase repo open sase-research-artifacts`). Change exactly one
default:

```yaml
  - name: gemini_model
    type: model
-    default: "agy/gemini-3.8-flash-high"
+    default: "agy/gemini-4-hydrogen-high"
```

Rationale for `-high` rather than `-xhigh`:

- The request is a family swap ("use the new Hydrogen model instead of the
  current Gemini model"), not an effort escalation. `flash-high → hydrogen-high`
  is the minimal parallel change: same relative effort rung, same cost class,
  same no-`@effort`-suffix constraint (agy rejects explicit effort suffixes;
  that documented restriction is unchanged).
- `-xhigh` is a defensible alternative — every other swarm researcher defaults
  to `@xhigh` (`codex/gpt-6.1-sol@xhigh`, `claude/opus@xhigh`,
  `grok/grok-4.6@xhigh`, `muse-...@xhigh`), and Hydrogen is the first agy
  family that can actually meet that rung via slug. But it likely costs more
  per run and exceeds what was asked. If the lead wants effort parity across
  researchers, `-xhigh` is the way; otherwise ship `-high`.
- Do not change `gemini: false` (opt-in default), the `gemini_model` type, or
  the description text — all remain accurate. The `type: model` input
  validates against the registry, so the new default resolves as soon as the
  sase-side catalog lands; note the ordering dependency (sidecar default
  dangles until the sase change ships — or land sase first).

Sidecar tests pinning the old default and needing the same one-line update
(`tests/test_macro_loading.py` lines ~687, ~806, ~1044–1045: default
assertion, `%m:agy/gemini-3.8-flash-high` segment assertions, and the
no-`@effort`-suffix assertion which holds unchanged for Hydrogen).

Two deployment footnotes to verify at implementation time (I could not verify
from this checkout): (a) prior research notes reference a chezmoi copy at
`chezmoi/home/sase/xprompts/research_swarm.md` — the chezmoi linked repo is not
cloned in this workspace, so confirm whether that path is a live second copy
or stale history; (b) the sidecar's `Justfile`/release flow may need a version
bump or wheel-contract refresh (`tests/test_wheel_contract.py`,
`wheel_smoke.py` exist — run the sidecar's own `just check` equivalent).

## Open questions (answer before or during implementation)

1. Is Hydrogen Ultra-gated like Argon? This account's `agy models` lists
   Hydrogen, but this account's entitlement is unknown. Run `agy models` on a
   non-Ultra (Free/Plus/Pro) account: if Hydrogen appears, drop the advisory
   to a plain catalog entry; if not, keep the mirrored info advisory. Default
   if unverifiable: keep the advisory (fail-loud with guidance beats a bare
   `agy` exit error).
2. `-high` vs `-xhigh` swarm default (above). Recommend `-high`; escalate only
   on explicit ask.
3. Hydrogen ordering in `models.yml` (CLI order `high, xhigh, medium, low` vs
   effort-descending `xhigh, high, medium, low`). Recommend descending;
   either is mechanical, but state the choice in the commit message since the
   file comment claims CLI ordering.
4. Confirm no live chezmoi second copy of `research_swarm.md` (above).

## Out of scope (do not fold in)

- Opus/Sonnet 5.5 (`claude-opus/sonnet-5-5-*` served by `agy` but uncatalogued)
  and the stale Flash/Pro/4-6 entries: separate catalog-drift follow-up
  (consider a `bug` task bead).
- `gemini-pro-orchestrator-g1-pro`: exclude deliberately.
- Tier-default freshness (`3.7-flash` absent from this account's listing):
  separate follow-up; changing tiers here would entangle entitlement policy
  with catalog maintenance.
- Renaming the `gemini`/`gemini_model` input names in the swarm (e.g. to
  `hydrogen`): gratuitous churn against docs, tests, and transcripts that say
  "gemini researcher". Keep the names; only the default slug changes.

## Sources and method

- Manifest: `src/sase/llm_provider/models.yml` (agy section, lines ~24–95).
- Manifest loader/validation: `src/sase/llm_provider/model_manifest.py`.
- Provider hooks: `src/sase/llm_provider/agy.py` (`llm_known_model_names`,
  `llm_model_short_aliases`, `llm_model_advisories`, `resolve_model_name`).
- Completion catalog: `src/sase/macro/model_completion.py`,
  `src/sase/macro/_model_completion_catalog.py` (registry-derived; no edit).
- Short display name: `src/sase/ace/tui/widgets/_agent_list_helpers.py`.
- Docs generation: `tools/render_model_docs`, `docs/reference/providers/models.md`,
  `docs/reference/providers/agy.md`.
- Argon template commit: `4d8940d4b7` (full file list via `git show --stat`).
- Swarm xprompt + pinning tests: `sase-research-artifacts` sidecar
  (`xprompts/research_swarm.md` inputs ~71–76, researcher fan-out ~158;
  `tests/test_macro_loading.py` ~654–1114).
- Live oracle: `agy models` on this host, run twice with identical output
  (18 models + header), corroborating the four Hydrogen slugs and the
  orchestrator exclusion. No peer-report material consulted; filenames in the
  research directories were listed only to avoid output collision.
- Not re-verified by execution: test-suite green status (no code changed in
  this turn) and the non-Ultra entitlement question above.
