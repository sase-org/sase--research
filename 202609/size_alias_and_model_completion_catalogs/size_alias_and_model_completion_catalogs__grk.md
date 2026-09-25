# Size-alias pools and model-completion catalogs: one edit, two surfaces

**Researcher:** `research.c.grk` (independent swarm report)
**Date:** 2026-09-25
**Question:** How should maintainers update shipped `@xsmall`…`@xlarge` pool defaults *and* the models offered by `%model` completion (ACE prompt input and external editors via LSP) by touching as few files as is actually desirable?

## Recommendation (up front)

Do it. The pain is real, the direction is right, and most of the architecture already exists. Do **not** merge the two catalogs into one file, and do **not** treat the TUI prompt widget and the LSP as two update surfaces.

Ship **two bundled YAML sources** plus generation and invariant tests:

| Source | Owns | Already exists? |
| --- | --- | --- |
| `src/sase/llm_provider/model_alias_defaults.yml` | Shipped `@xsmall`…`@xlarge` targets, descriptions, pool/fallback grammar | Yes. Runtime loads it; `just fmt-docs` already rewrites the table in `docs/llms.md`. |
| `src/sase/llm_provider/bundled_model_catalog.yml` (new) | Per-provider known model ids, short aliases, large/small tier defaults, optional lineage/predecessor, optional advisories | No. Today this lives as Python literals in each provider module, then is copied into docs tables and tests. |

Keep the public plugin hooks (`llm_known_model_names`, `llm_model_short_aliases`, `llm_model_advisories`, `llm_resolve_model_name`). Bundled providers become thin readers of the YAML. Third-party plugins keep implementing the hooks in code.

After this, a maintainer's typical edit is:

- **Add a completable model:** edit `bundled_model_catalog.yml`, run `just fmt-docs`.
- **Retune a size pool using models that already exist:** edit `model_alias_defaults.yml`, run `just fmt-docs`.
- **Add a model and put it in a pool:** edit both YAML files, run `just fmt-docs`.

CI must refuse a docs/test drift, and must refuse an alias-pool member whose model id is missing from that provider's known-model list. Those two gates are what make "few files" true in practice. Without them, the YAML becomes a third copy.

---

## Critique of the plan

The plan as stated — "update both of these by updating as few files as possible/desirable" — is a good idea. Recent model bumps are 9–28-file commits whose decisions fit in two data files. The rest is transcription.

It is a *better* idea once the two surfaces are named correctly.

**Size-alias pools and completion models are two product decisions.** Putting `grok-4.8` on the `%model` menu is "this id is a real Grok model SASE should resolve and complete." Putting it in `@large` is "this id should win a share of large launches, at this effort, in this selector grammar." Those change on different days, for different reasons, and they have different invariants (effort-ladder descent and multi-provider membership vs. unique ids, short-alias uniqueness, and picker visibility). One file that holds both will make the cheap change (add to the menu) look like a routing change in review, and will tempt someone to retune `@medium` while adding a preview slug.

**The TUI prompt widget and the LSP are already one catalog.** ACE prompt completion calls `sase.xprompt.model_completion.build_model_completion_catalog()`. `sase lsp` materializes the same payload to `model_catalog.json` (`src/sase/integrations/xprompt_lsp.py`). The Rust xprompt LSP (`sase-core` crate `sase_xprompt_lsp`) re-reads that JSON on every `%model` / `=` / `==` request and does not ship its own model list. The Launch Control model picker is a sibling consumer of the same registry metadata. Unifying TUI and LSP catalogs is already done; spending design budget there is solving last year's problem.

**"As few files as possible" is the wrong optimum if it means one file.** The desirable number is **one source of truth per concern**, plus generated artifacts that CI refreshes or rejects. Two YAML files, a docs renderer, and invariant tests beat a single mega-catalog that also tries to own invoke flags, usage collectors, and blog examples.

**The alias half of the plan is already landed.** Changelog `f55ce07` ("drive shipped model alias defaults from one YAML file") plus `tools/render_model_alias_docs` already make YAML the shipped-default edit point. The remaining pain on that half is *fan-out around the YAML*: tests that re-pin the current slugs, prose that restates the current pools, `default_config.yml` comments that copy real targets "as examples," and an effort-ladder predecessor map hardcoded in a test. Fixing that fan-out is higher leverage than inventing a second alias format.

I would take this approach rather than a grand unified catalog, a live CLI scrape (`agy models`, etc.), or generating every mention of a model id in the tree.

---

## Requirement adjustments

These are deliberate changes to the request. Each one is required for the recommendation to stay small.

1. **Treat TUI prompt completion and editor LSP as one consumer.** The requirement is "models the registry publishes as known," which both surfaces already read. Do not add a TUI-specific list or an LSP-specific list.

2. **Keep size-alias defaults and known-model catalogs as sibling files.** Updating "both" should be possible in one change *set*, not one blob. Completing a model and routing it through a size pool stay independent.

3. **Do not rewrite README, blog posts, or pedagogical `%model:` examples from the catalog.** Those are illustrations. Auto-updating them turns every Codex rename into a docs-history rewrite. Point narrative docs at the generated table in `docs/llms.md` when they need current slugs. Keep example snippets on stable names (`opus`, `sonnet`, `haiku`) or obviously-fake ids.

4. **Change `src/sase/default_config.yml` comments so they stop tracking shipped defaults.** The file already says the YAML is the single responsibility for shipped targets, then copies real pool strings as "grammar examples." Those comments churn on every retune (Grok 4.7, GPT-6 Sol, etc.). Replace them with grammar-only examples that cannot be mistaken for defaults.

5. **Do not live-query vendor CLIs to populate completion.** `agy.py` already documents that its list is "exact stable slugs reported by `agy models`." That is an authoring hint, not a runtime source. Completion has to work offline, in tests, and on machines that lack a given CLI. A later `sase doctor` advisory that diffs a present CLI's model list against the bundled catalog is useful; making the menu depend on that CLI is not.

6. **Keep plugin hooks as the extension point.** YAML is for *bundled* providers. A third-party `sase_llm` plugin must still be able to publish known models from Python. The completion catalog is already built from hook metadata (`build_llm_metadata_payload` → `known_model_names`).

7. **Add a docs drift gate.** `just fmt` / `just fix` run `tools/render_model_alias_docs` and rewrite `docs/llms.md`. `just fmt-check` does **not** verify that generated block, and no test reads the `<!-- BEGIN GENERATED: model-alias-defaults -->` region. Today a YAML edit can land with a stale table if someone skips `just fix`. Generation without a check is another copy.

8. **Move the effort-ladder predecessor map out of the test.** `test_shipped_size_aliases_follow_the_effort_ladder` hardcodes `continued_from = {"grok/grok-4.6": "grok/grok-4.7"}`. That is policy (a newer model of the same family continues the previous model's descent instead of restarting at `xhigh`), currently living in a test. Encode lineage next to the catalog (`predecessor` / `supersedes`) so adding Grok 4.8 is data, not a test edit.

9. **Preserve the frozen alias fixture.** `tests/_model_alias_defaults_fixture.py` already exists so most tests do not churn when shipped pools change. Keep it. Tests marked `real_model_alias_defaults` should assert *invariants* (effort ladder, multi-provider membership, alias-member ⊆ known models, Muse contributor still on `@medium` and below) rather than exact slug tuples.

10. **Include large/small tier defaults in the known-model catalog, as a justified extra.** `_TIER_TO_MODEL` in each provider is a third copy that churns on the same commits and feeds the per-provider "Model Mapping" tables in `docs/llms.md`. It is not completion, but it is the same maintainer motion. Putting `tiers.large` / `tiers.small` in the bundled catalog YAML collapses that third copy. Leave invoke-time effort CLI flags (`_EFFORT_CLI_ARGS`) in Python; those are process argv, not catalog data.

11. **Do not confuse this with `sase completion spec` / `just sync-completion-spec`.** That snapshot is the argparse CLI grammar for shell tab-completion. It is unrelated to `%model` values.

---

## Current architecture (what actually has to change today)

### Size-alias pools — already a YAML source, still a copy problem

Shipped defaults live in `src/sase/llm_provider/model_alias_defaults.yml`. `model_alias_policy.py` loads that file through `importlib.resources`, validates selector grammar, and refuses unknown alias names. User config may override only the five builtin names under `llm_provider.model_aliases.builtin`.

```yaml
# src/sase/llm_provider/model_alias_defaults.yml (current)
medium:
  target:
    "claude/sonnet@xhigh | codex/gpt-5.6-terra@xhigh | grok/grok-4.6@high |
    muse/muse-spark-1.3-contributor@xhigh"
```

`tools/render_model_alias_docs` (invoked by `just fmt-docs`) rewrites the generated table in `docs/llms.md`. The renderer deliberately does **not** import `sase.llm_provider` so docs generation stays cheap and plugin-free.

Runtime consumers of the YAML: alias resolution, Launch Control, `%model:@medium` completion rows (the five implicit aliases are injected from `BUILTIN_MODEL_ALIAS_NAMES`, with descriptions/targets from the YAML via `build_alias_views()`).

What still fans out when the YAML changes:

- `tests/llm_provider/test_load_balanced_alias_defaults.py` re-pins every provider's current `(model, effort)` for each size, plus exact `@large` / `@xlarge` member tuples.
- `tests/llm_provider/test_ordered_fallback_aliases.py` and several routing tests pin the same slugs.
- `docs/ace.md`, `docs/agent_providers.md`, `docs/configuration.md`, `docs/getting_started.md`, `docs/llms.md` prose, and `sase/memory/decisions/size-alias-effort-ladder.md` restate current members.
- `src/sase/default_config.yml` comments copy real pool strings.
- The effort-ladder predecessor dict in the test named above.

The test suite already has the right isolation pattern: by default tests freeze aliases to a *different* graph (`tests/_model_alias_defaults_fixture.py`); only tests that opt into `real_model_alias_defaults` see shipped values. The leak is those opted-in tests asserting slugs instead of policy.

### Completion models — one runtime catalog, many Python/docs/test copies

Each bundled provider publishes:

```python
def llm_known_model_names(self) -> list[str]: ...
def llm_model_short_aliases(self) -> dict[str, str]: ...
```

The registry (`_registry_metadata.py`, `_registry_catalog.py`) builds `known_model_names`, `model_to_provider`, and `model_short_aliases`. That payload feeds:

1. **ACE prompt input** — `src/sase/ace/tui/widgets/directive_completion.py` and `_file_completion_workers.py` call `build_model_completion_catalog()`.
2. **External editors** — `prepare_lsp_environment()` writes `model_catalog.json`; Rust `load_model_catalog()` reads it per request.
3. **Launch Control model picker** — `build_model_options()` / `build_model_rows()` from the same registry.
4. **Bare-name routing** — `resolve_model_provider("gpt-6-sol")` uses `model_to_provider`. Provider-qualified `codex/gpt-7-new` can still invoke without being in the known list; it simply will not complete and will not resolve as a bare name.

`docs/llms.md` then **hand-maintains** two tables that duplicate the hooks: "Automatic Provider Resolution" (known names → provider) and "Model Short Aliases." Those tables are not generated. Adding Gemini 3.8 or Grok 4.7 is a docs edit for that reason.

Tests duplicate the lists a third time:

- `tests/llm_provider/test_agy_provider_core.py` keeps `_AGY_MODELS` and the full short-alias dict, asserted equal to the hook.
- `tests/llm_provider/test_grok_provider_core.py` asserts `== ["grok-4.7", "grok-4.6"]`.
- `tests/llm_provider/test_muse_provider_identity.py` does the same with `_MUSE_MODELS`.
- `tests/test_xprompt_model_completion_catalog.py` adds a new test function per model family (`test_model_completion_catalog_includes_grok_47`, `..._agy_gemini_38_flash_variants`, `..._reflects_real_builtin_model_metadata` pinning Astra/Sol/Luna/Terra/Spark).
- `tests/test_model_picker_options.py` asserts a growing set of ids (`opus`, `gpt-6-sol`, `grok-4.7`, `gemini-3.8-flash-high`, …).

Those tests are why "add a model to completion" is never just the provider module.

### Empirical fan-out (recent commits)

| Change | Commit | Files |
| --- | --- | --- |
| Add Grok 4.7 and retune aliases | `1cea18e00f` | 19 |
| Add GPT-6 Sol and make it the Sol default | `682089c845` | 28 |
| Put Grok in `@xlarge` (alias-only) | `e65cc22eeb` | 13 |
| Add Gemini 3.8 Flash and `@xsmall` member | `f546929e46` | 9 |
| Retune cheap aliases onto Luna/Terra | `17084a6e27` | (alias YAML + docs + tests; same pattern) |

The decision in each of those commits is one or two data edits. The file count is copies.

---

## Alternatives considered

### A. One mega-YAML for aliases, known models, tiers, advisories, effort flags

Fewest files. Couples menu membership to routing. Makes plugin providers a special case (they cannot ship the same file). Pulls invoke argv into a data file that the docs renderer would then have to understand. Reject.

### B. Per-provider YAML files (`catalogs/claude.yml`, `catalogs/grok.yml`, …)

Nice blame and review isolation. Worse for "few files": adding Grok 4.8 and putting it in `@large` is still two files, but generating the two `docs/llms.md` tables needs a directory walk, and a new bundled provider is another file before the Python plugin even exists. Acceptable if the team prefers isolation; not the default.

### C. Keep Python literals; only generate docs and stop pinning tests

Highest leverage per hour. "Add a model" becomes: edit `grok.py`, run `just fmt-docs`. The alias YAML is already the other edit point. Docs renderer would have to import provider plugins (today it specifically avoids that) or duplicate a parser. Python lists are fine for programmers and worse for a data-only diff. This is a valid Phase 1 if YAML work slips; it is not the end state, because the renderer isolation and the "data not code" review story both matter.

### D. Live CLI discovery (`agy models`, Codex `/models`, etc.)

Always stale-free, always wrong for SASE. Completion would depend on which CLIs are installed on the machine running the TUI/LSP, tests would need network or fixtures for every vendor, and a CLI rename during a provider upgrade would silently change the menu. Keep shipped catalogs. Optional doctor diff later.

### E. Generate every slug mention in the tree

Over-generation. Blog posts, README one-liners, parser help strings, and xprompt comments should use stable or clearly-illustrative ids. Generating them makes history unreadable and forces screenshot/golden churn for no user-facing gain.

### F. Infer known models from alias-pool membership

A pool is a *subset*. Completion must offer `o3`, `claude-fable-5`, `gpt-6-astra`, and old Gemini flashes that are not in any shipped alias. Alias YAML cannot be the known-model list.

---

## Recommended solution

### Data layout

Keep the existing alias file. Add one sibling catalog:

```yaml
# src/sase/llm_provider/bundled_model_catalog.yml
schema_version: 1
providers:
  grok:
    known_models:
      - id: grok-4.7
        short_alias: null          # optional; omit when none
      - id: grok-4.6
        predecessor: grok-4.7      # effort-ladder continuation
    tiers:
      large: grok-4.7
      small: grok-4.6
  muse:
    known_models:
      - id: muse-spark-1.3
        short_alias: spark13
      - id: muse-spark-1.3-contributor
        short_alias: spark13c
        advisory:
          severity: warn
          label: trains on your data
          detail: "..."
    tiers:
      large: muse-spark-1.3
      small: muse-spark-1.3
```

Exact schema can be bikesheded in implementation; the required fields are `id`, optional `short_alias`, optional `predecessor`, optional `advisory`, and `tiers`. Order of `known_models` is display order (Antigravity already cares about CLI ordering).

A tiny loader (`bundled_model_catalog.py`) caches the parse, validates uniqueness of ids and short aliases, validates that `predecessor` and `tiers` references exist, and exposes:

```python
def bundled_known_model_names(provider: str) -> list[str]: ...
def bundled_short_aliases(provider: str) -> dict[str, str]: ...
def bundled_tier_model(provider: str, tier: ModelTier) -> str: ...
def bundled_advisories(provider: str) -> dict[str, dict[str, str]]: ...
def bundled_predecessor(model_id: str) -> str | None: ...
```

Each bundled provider's hooks become one-liners. Third-party plugins are untouched.

### Generation

Extend `tools/render_model_alias_docs` (or split a `tools/render_model_catalog_docs` that shares YAML reading) so `just fmt-docs` rewrites **three** marked blocks in `docs/llms.md`:

1. Size-alias defaults table (already exists).
2. Automatic provider-resolution table (known names → provider).
3. Short-alias table.

Optionally a fourth family of blocks for per-provider `Model Mapping` tier tables. That is the justified extra from adjustment 10.

The renderer must keep its current property: **no import of provider plugins.** Both YAML files are data; the tool can stay extensionless and cheap.

### Gates (this is the actual "few files" mechanism)

| Gate | Failure mode it kills |
| --- | --- |
| `fmt-docs --check` (wire into `just fmt-check` / `just check`) | YAML changed, generated `docs/llms.md` block not refreshed. |
| Alias-member ⊆ known models, for every `provider/model` in the shipped YAML | Pool retune that names a slug nobody published. Today this is legal at runtime for qualified ids and silently drops the model from completion. |
| Effort-ladder invariant, reading `predecessor` from the catalog | Pool retune that reuses a model at the same rung, or restarts a superseded model at `xhigh`. |
| Multi-provider membership (existing decision `size-alias-effort-ladder`) | Single-vendor pool. |
| Short-alias uniqueness across a provider | Two models claiming `flash38h`. |
| Frozen-fixture shape check (already documented in the fixture) | Alias graph shape change (`target` vs `fallback`) without a fixture update. |

Product-claim tests that should remain, rewritten off slugs:

- `@medium` and below still include the Muse contributor model (training-terms opt-in).
- Only `@xsmall` includes an Antigravity member.
- `@large` round-robins Claude, Codex, and Grok (assert provider prefixes).
- `@xlarge` is ordered fallback (assert mode + provider prefixes).

Presence tests for completion should iterate the bundled catalog: "every known model id appears as a `kind=model` row; every short alias is a match hint; hidden providers stay off the picker." Delete the per-family `test_model_completion_catalog_includes_*` functions that exist only to pin the latest slug.

### Maintainer workflow after landing

```text
# New Grok model, menu only
edit src/sase/llm_provider/bundled_model_catalog.yml
just fmt-docs

# Same model also takes @large at xhigh; previous flagship continues descent
edit src/sase/llm_provider/bundled_model_catalog.yml   # id + predecessor
edit src/sase/llm_provider/model_alias_defaults.yml    # pool members
just fmt-docs
```

If the effort ladder or the ⊆ check fails, the YAML is wrong; there is no third file to hunt.

A new *bundled provider* still needs a Python module (invoke, stream parsing, auth). That is out of scope for this maintenance problem. The catalog YAML only removes the name-list chore from that module.

### Sequencing

**Phase 1 — stop the fan-out, keep Python lists.** Generate the two `docs/llms.md` tables from the existing hooks *or* from a first cut of the YAML. Add the docs drift check. Rewrite `real_model_alias_defaults` tests to invariants. Neutralize `default_config.yml` example comments. Add alias-member ⊆ known-models. This already drops a 19-file Grok bump to "provider module + alias YAML + generated docs."

**Phase 2 — move bundled names into YAML.** Provider hooks become loader calls. Short aliases, tiers, advisories, and predecessor join the catalog. Docs renderer stays plugin-free. Completion tests iterate the loader.

**Phase 3 — optional doctor.** When a CLI is present, warn if `agy models` (etc.) reports ids missing from the bundled catalog. Advisory only.

Phase 1 is enough to make the original request true for aliases and *almost* true for completion. Phase 2 is the recommended end state because it matches the alias YAML pattern the project already chose, and because the docs renderer isolation is a real constraint.

### What not to do in the same change

- Do not regenerate ACE/pager screenshot goldens because a slug in a help string moved; keep those strings on stable names.
- Do not put `_EFFORT_CLI_ARGS`, retry config, or usage-window metadata in the catalog YAML.
- Do not generate `sase/memory/decisions/size-alias-effort-ladder.md` from the YAML. That file is a decision record; update it when the *rule* changes, and let examples in it lag or point at the generated table.
- Do not teach the Rust LSP about YAML. It should keep reading the materialized JSON.

---

## Is this a good idea?

Yes. The project already voted for this design once, for aliases, in `f55ce07` and the `model_alias_defaults.yml` header ("This file is the single edit point"). Completion names were left as Python literals and hand-maintained docs, so every vendor rename reopens the old fan-out. Extending the same YAML-plus-generation pattern to known models, and deleting the slug-pinning tests, is the consistent next step.

The idea is *not* "one file to rule every model string in the repository." It is "two data files for two decisions, generated docs, and tests that check rules instead of today's slugs." That is the desirable minimum.

---

## Sources (inspected, this workspace)

- `src/sase/llm_provider/model_alias_defaults.yml`
- `src/sase/llm_provider/model_alias_policy.py`
- `src/sase/llm_provider/{claude,codex,grok,agy,muse,qwen,opencode,fakey}.py` (known-model hooks, short aliases, `_TIER_TO_MODEL`)
- `src/sase/llm_provider/_hookspec.py`, `_registry_metadata.py`, `_registry_catalog.py`
- `src/sase/xprompt/model_completion.py`, `_model_completion_catalog.py`
- `src/sase/integrations/xprompt_lsp.py` (`_materialize_model_catalog`)
- `src/sase/ace/tui/widgets/directive_completion.py`, `_file_completion_workers.py`
- `src/sase/default_config.yml` (comments that still copy shipped pools)
- `tools/render_model_alias_docs`, `Justfile` (`fmt-docs`, `fmt-check`)
- `docs/llms.md` (generated alias table; hand-maintained known-model and short-alias tables)
- `docs/editor.md` (LSP catalog snapshot semantics)
- `tests/_model_alias_defaults_fixture.py`, `tests/llm_provider/test_load_balanced_alias_defaults.py`
- `tests/test_xprompt_model_completion_catalog.py`, `tests/test_model_picker_options.py`
- `tests/llm_provider/test_agy_provider_core.py`, `test_grok_provider_core.py`
- `sase/memory/decisions/size-alias-effort-ladder.md` (via `sase memory read`)
- Linked `sase-core` crate `sase_xprompt_lsp` `catalogs.rs` (`load_model_catalog` reads JSON, no hardcoded ids)
- Git history: `1cea18e00f`, `682089c845`, `e65cc22eeb`, `f546929e46`
