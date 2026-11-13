# Google Argon and Hydrogen support in SASE

Independent research by **cdx**, 2026-11-13. No other researcher’s report, findings, or transcript was consulted. This report investigates implementation; it does not change SASE’s code or deploy a new configuration.

The best approach is a focused change across **SASE and the `sase-research-artifacts` plugin**: retain the existing Argon catalog entries, add all four verified Hydrogen variants to the central manifest, repair the shell model-completion exception, and change the swarm’s Gemini researcher default to `agy/gemini-4-hydrogen-high`. Existing prompt and editor completion code already supports these model names.

## 1. Verified model names and current availability

The installed Antigravity CLI reports version **1.5.8**. Its `agy models` command returned the following relevant entries, in this order:

| Exact CLI model ID | CLI display name | SASE catalog at the inspected revision |
| --- | --- | --- |
| `gemini-4-argon-medium` | Gemini 4 Argon (Medium) | Present |
| `gemini-4-argon-high` | Gemini 4 Argon (High) | Present |
| `gemini-4-argon-low` | Gemini 4 Argon (Low) | Present |
| `gemini-4-hydrogen-high` | Gemini 4 Hydrogen (High) | Missing |
| `gemini-4-hydrogen-xhigh` | Gemini 4 Hydrogen (XHigh) | Missing |
| `gemini-4-hydrogen-medium` | Gemini 4 Hydrogen (Medium) | Missing |
| `gemini-4-hydrogen-low` | Gemini 4 Hydrogen (Low) | Missing |

These are observed CLI identifiers, not guessed Gemini API IDs. In SASE, explicit selectors should prefix them with `agy/`. Do not invent a `hydrogen` provider, add an unverified `gemini-4-hydrogen` base ID, or copy these IDs into OpenCode’s catalog without separately verifying that provider’s model naming.

Google announced Hydrogen on November 12, 2026. Its announcement describes high as the default thinking level, alongside low, medium, and xhigh, and positions Hydrogen as the faster model for everyday agentic execution. This supports choosing high for the default research worker, although it does not establish quality on SASE’s actual research workloads. [Google launch announcement](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-Hydrogen/)

**Access guidance has changed during rollout.** Google’s November 12 Antigravity announcement describes Hydrogen rolling out to paid Pro and Ultra. The current model documentation lists Hydrogen on all listed plan tiers, and Argon on eligible Pro, Ultra, and Enterprise plans; the Pro footnote covers paid plans and eligible-device trials. Prefer the current model table, date the evidence, and use `agy models` on the deployment account to check availability. SASE’s existing assertion that Argon excludes all Pro accounts is stale. [Antigravity launch post](https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity), [current model and entitlement documentation](https://antigravity.google/docs/models)

The local model list establishes catalog visibility for this account, not successful inference, latency, or entitlement for every user. No model-generation call was made during this research.

## 2. Current ownership and data flow

Inspected revisions:

- SASE: `9285c4f55eec790693c7bcae9dc88e87a847a21f`.
- `sase-research-artifacts`: `a8b1d74ea0a8e70c53d4c247c25e5ea361775e8a`.
- `sase-core` linked checkout: `1b3aef9464b929dafbce125638367596041ece5b`; SASE’s checked-in core pin is `bab5978195d9a52afa828b18cdba779a1b930ee2`.

### The model manifest is already the principal source of truth

[`src/sase/llm_provider/models.yml`](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/src/sase/llm_provider/models.yml#L1) explicitly declares itself the single edit point for routine built-in model maintenance. It already contains:

- Three Argon model IDs and `argon4h`, `argon4m`, `argon4l` short aliases.
- An informational Ultra-only advisory for each Argon variant, which now needs correction.
- Antigravity tier defaults of `gemini-3.7-flash-high` and `gemini-3.7-flash-low`.
- An independent size-alias pool containing `agy/gemini-3.8-flash-high`.

`model_manifest.py` loads and structurally validates this data. `AgyProvider.llm_known_model_names`, `llm_model_short_aliases`, and `llm_model_advisories` read it. The registry turns those hooks into model/provider mappings and shared metadata. Adding a new Gemini provider or a second hard-coded list in `agy.py` would bypass the design already present. [Manifest loader](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/src/sase/llm_provider/model_manifest.py), [Antigravity hooks](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/src/sase/llm_provider/agy.py#L263)

### Completion surface inventory

| Surface | Current source/behavior | Required work |
| --- | --- | --- |
| ACE model picker, including default/follow-up selection | `modals/model_picker_rows.py` reads registry mappings, short aliases, and advisories | Manifest data; verify all seven IDs under an enabled `agy` provider |
| Prompt `%model:` and `%m:` completion | `macro/model_completion.py` and `_model_completion_catalog.py` build registry-backed entries | Manifest data |
| Provider-scoped prompt completion, e.g. `%m:agy/hydrogen4` | Shared Rust filtering operates on those entries | Manifest short aliases; no model-specific Rust branch |
| Concrete `==model` shortcut | `widgets/model_explicit_completion.py` uses the shared catalog and Rust contract | Manifest data |
| Model-typed macro arguments, including `gemini_model=` | `_file_completion_macro_args.py` delegates to the directive model builder | Manifest data |
| Rust macro LSP/editor completion | Python materializes `model_completion_catalog_payload()` into JSON; Rust reads model entries from that file | Refresh/restart materialization after installation; no new wire schema |
| `=alias` shortcut and alias-only `@…` queries | Intentionally select configured/implicit aliases, not concrete models | Preserve this distinction; new model short aliases are search hints, not automatically executable `@aliases` |
| Shell `--model` completion | `completion/candidates/catalog_build.py:model_candidates()` returns only five size aliases | **Separate adapter change is necessary** |
| Shell `--next-model` on gate creation | `completion/kinds.py` currently lists `next_model` as intentionally non-completable | Classify this selector as `ValueKind.MODEL` if “all surfaces” includes every CLI model selector; recommended |

Relevant source: [shared model catalog](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/src/sase/macro/model_completion.py), [macro argument completion](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/src/sase/ace/tui/widgets/_file_completion_macro_args.py#L79), [model picker](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/src/sase/ace/tui/modals/model_picker_rows.py#L306), [LSP materialization](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/src/sase/integrations/macro_lsp.py#L401), [Rust completion filtering](https://github.com/sase-org/sase-core/blob/1b3aef9464b929dafbce125638367596041ece5b/crates/sase_core/src/model_completion.rs), [shell candidates](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/src/sase/completion/candidates/catalog_build.py#L177), [CLI kind classification](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/src/sase/completion/kinds.py).

### Shell completion is the meaningful implementation exception

A direct check of `SASE_COMPLETION_NO_CACHE=1 sase completion candidates model` returned exactly `xsmall`, `small`, `medium`, `large`, and `xlarge`. The test `tests/completion/test_candidates_providers.py:test_model_candidates_are_the_builtin_size_aliases` explicitly pins this behavior. Thus a manifest-only patch cannot truthfully claim to update every completion surface.

The shell candidate path has an important import restriction: importing `sase.llm_provider` or `sase.macro` pulls in packages forbidden on this fast path. Calling `build_model_completion_catalog()` from `model_candidates()` is therefore not an acceptable quick fix. [Import contract](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/src/sase/completion/candidates/catalog.py#L1)

Recommended small solution: make this adapter project **the packaged manifest’s built-in model strings** into shell candidates while retaining the five existing aliases. Locate the resource through the lightweight `sase` package, e.g. `importlib.resources.files("sase").joinpath("llm_provider", "models.yml")`, rather than importing the `sase.llm_provider` subpackage. Use the existing safe YAML reader. Offer both bare canonical names and provider-qualified selectors so `gemini-4-…` and `agy/gemini-4-…` prefixes work. Preserve short aliases as metadata rather than suggesting them as standalone executable model values.

Keep this a data projection, not a new resolver or duplicate catalog. Reuse the existing candidate filtering/deduplication conventions; verify import discipline in a subprocess. Update `model_source_path()` so manifest changes invalidate the candidate cache, accounting for packaged-resource behavior, and keep the existing bounded TTL as a fallback. This proposal requires implementation tests; it was not implemented here. A richer shell catalog covering user aliases and third-party provider hooks can use a separately materialized metadata snapshot later, but is not necessary to expose these built-in models and should not make completions depend on a running editor.

The generic shell emitters already consume typed candidates. Avoid inserting Google model names separately into Bash, Zsh, Fish, or chezmoi-generated completion scripts. If `next_model` is reclassified, regenerate/install the affected completion specification through the existing mechanism.

## 3. Where `#research_swarm` must change

The authoritative macro belongs to **`sase-research-artifacts`**, not SASE’s bundled macros and not the user’s chezmoi macros:

`src/sase_research_artifacts/xprompts/research_swarm.md`, lines 71–76:

```yaml
- name: gemini_model
  type: model
  default: "agy/gemini-3.8-flash-high"
```

The registered runtime macro reports the same default. The researcher list uses `gemini_model` for the `agy` provider’s existing `gem` member. The `gemini` boolean remains false by default, with provider gating, researcher report suffixes, and lead wait dependencies already derived from the member list. [Macro source](https://github.com/sase-org/sase-research-artifacts/blob/a8b1d74ea0a8e70c53d4c247c25e5ea361775e8a/src/sase_research_artifacts/xprompts/research_swarm.md#L71)

Change that default to:

```yaml
default: "agy/gemini-4-hydrogen-high"
```

Update its description to include the `-xhigh` variant and to say **SASE’s current Antigravity adapter** rejects explicit effort suffixes. Keep the `gemini`/`gemini_model` parameter names, `.gem` researcher identity, `__gem.md` report suffix, opt-in behavior, and explicit model override. Hydrogen remains a Gemini-family model, so renaming the slot would introduce migration work without improving this feature.

Also update:

- Plugin `README.md` around line 167, which spells out the default and effort restriction.
- Plugin `tests/test_macro_loading.py` around lines 687, 806, and 1044, which assert the old default and rendered Gemini directive.
- Preserve the explicit override test around line 945 and tests for provider gating, independent reports, lead waits, and participant counts.

Chezmoi’s `home/dot_config/sase/sase.yml` invokes `#research_swarm` without overriding `gemini_model`; changing the plugin default therefore reaches these invocations. Other chezmoi macros such as `m_agy` and `m_swarm`, and SASE’s separate `reads` macro, reference older Flash models but are not definitions of `#research_swarm`. They should not be swept into this targeted change.

## 4. Effort handling: distinguish the adapter from current upstream capability

Today SASE’s `AgyProvider.invocation_option_args()` passes an empty supported-effort map. Explicit `%effort` or `@effort` therefore fails within SASE before launching `agy`. The invocation path already forwards the chosen model slug verbatim through `--model`. Consequently both `agy/gemini-4-hydrogen-high` and `agy/gemini-4-hydrogen-xhigh` fit the existing contract without new subprocess code. [Current adapter](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/src/sase/llm_provider/agy.py#L419)

However, **upstream now supports `--effort`**: installed `agy --help` lists it, and Google documents per-invocation effort overrides with model-dependent support. Updating SASE to forward it is a separate feature involving policy, conflicting slug/suffix semantics, supported CLI versions, and tests. It is unnecessary to add these models. Avoid preserving the inaccurate statement that modern Antigravity itself has no effort mechanism. [Official CLI effort documentation](https://antigravity.google/docs/cli/commands/effort)

Use **high** for the swarm default because it preserves the previous worker’s selected level and is Google’s advertised Hydrogen default. Expose xhigh as an explicit choice, for example:

```text
#research_swarm(gemini=true, gemini_model=agy/gemini-4-hydrogen-xhigh):: topic
```

This selection is an implementation recommendation, not a measured quality comparison between high and xhigh.

## 5. Concrete change scope

### SASE

1. Add the four Hydrogen IDs to `providers.agy.models` in `src/sase/llm_provider/models.yml`. Respect the observed CLI order within the relevant entries; optionally align the existing Argon ordering with the current CLI output.
2. Add recognizable short aliases: `hydrogen4h`, `hydrogen4xh`, `hydrogen4m`, `hydrogen4l`. These follow the existing `argon4h` pattern and support typing `hydrogen` in prompt completion. Check uniqueness in the full manifest.
3. Correct all three Argon entitlement advisories and the adjacent manifest comment. Do not copy the old Ultra-only restriction onto Hydrogen. Describe access as account/plan dependent and point users to `agy models` where useful.
4. Extend the shell candidate adapter and cover `--next-model` classification as described above.
5. Regenerate model documentation from the manifest. Update the hand-authored access paragraph in `docs/reference/providers/agy.md` and any prose that claims the adapter’s limitations are current upstream limitations. Read the project’s documentation-writing memory before those edits.

### Research plugin

Change the `gemini_model` default, corresponding description, README, and existing behavior tests. Install/release the updated SASE catalog before or with the updated research plugin so discovery surfaces and the new default agree. Verify which package supplies the active macro; editing a private linked checkout alone does not update an installed plugin.

### Deliberately bounded decisions

- Do not replace SASE-wide size aliases or every Antigravity call with Hydrogen as part of a completion update.
- Current provider tiers still select 3.7 Flash. Google’s current table lists older 3.7 Flash as Enterprise-only, and the local CLI list did not include it. That deserves a separate default-policy decision; retaining the tier values here is scope control, not evidence that they work for all accounts.
- Do not add Carbon or Orchestrator just because they appear in current upstream material. They were not requested, and Orchestrator changes the single-model assumption of this research slot.
- No Rust model enum, parser rule, binding, schema bump, or core-revision change is needed for the verified slug additions. If implementation expands into shared model-resolution behavior, follow SASE’s Rust backend boundary rather than duplicating it in Python.

## 6. Evidence and verification

Completed during this research:

- Read the model manifest, provider hooks and invocation path, shared completion catalog, picker, macro-argument adapter, Python LSP materializer, Rust filtering/catalog loader, shell candidate code, and research-plugin source/tests.
- Ran `agy --version`, `agy models`, and `agy --help` successfully.
- Confirmed shell model candidates contain only five aliases, with cache bypassed.
- Confirmed the installed `research_swarm` macro has the same `3.8-flash-high` default as the opened plugin source.
- Ran a disposable **in-memory manifest probe** using the workspace Python environment. It inserted the four Hydrogen IDs and short aliases, reloaded registry metadata, and exercised the existing catalog plus installed Rust bindings. All four resolved to `agy`; `hydrogen4` completion matched all four; `agy/gemini-4-hydrogen` filtering and provider-scoped `==` filtering returned all four qualified selectors; the LSP wire-row conversion included all four. No tracked implementation file was modified.

The existing `tests/test_manifest_synthetic_exercise.py` already proves much of the manifest-to-catalog path generically. Extend that style rather than scattering hard-coded model inventories throughout tests. Its current “every model surface” claim does not cover the shell candidate implementation. [Existing synthetic exercise](https://github.com/sase-org/sase/blob/9285c4f55eec790693c7bcae9dc88e87a847a21f/tests/test_manifest_synthetic_exercise.py)

Implementation acceptance criteria:

1. All seven Argon/Hydrogen variants appear in registry-backed selections and the LSP payload; short-alias matching inserts canonical selectors.
2. `%m:agy/hydrogen4xh`, concrete `==` completion, and `#research_swarm(gemini_model=…)` select the expected model. Alias-only `=` behavior remains intact.
3. Shell candidates include both families, preserve size aliases, refresh after manifest changes, and work without forbidden UI/provider-package imports. Verify `--next-model`’s spec kind if changed.
4. The rendered Gemini researcher uses `%m:agy/gemini-4-hydrogen-high`; an explicit xhigh/custom override still wins; counts, `__gem.md`, waits, and provider gating remain correct.
5. A fake subprocess assertion verifies the complete Hydrogen slug reaches `--model` unchanged with no added effort flag. A later small live smoke test can verify actual inference through the deployment account; this research did not do so.
6. Run generated-document refresh and the project-standard `sase tool run check` in each changed implementation repository. Use the existing shell emitter/smoke and plugin macro tests. Run targeted visual checks only if affected rendering/snapshots warrant them; `check-full` is explicit-only under this project’s rules.

After updating the installed packages, restart long-running SASE/editor processes so cached manifest metadata is rebuilt and the LSP model-catalog JSON is rematerialized. The Rust server rereads that file, but cannot discover new rows from an old Python-generated snapshot. Do not rewrite a running user’s catalog manually as the implementation.

Limitations: this is code and CLI research, not an implemented patch or full test run. Opening the configured `sase-nvim` repository failed because its registered primary workspace directory was absent. Its private client code was therefore not inspected; the Python and Rust model-completion interfaces were inspected directly. No peer research was used.

## Recommended solution

Implement **one catalog update plus one lightweight shell-completion fix in SASE, and one default-model update in `sase-research-artifacts`**. Keep Argon’s existing three variants, add Hydrogen’s four exact `agy models` slugs with readable short aliases, correct the outdated Argon access advisory, and make the existing Gemini research worker default to **`agy/gemini-4-hydrogen-high`**. Preserve its identity and override interface, expose xhigh explicitly, and reuse the current registry/Rust completion pipeline. This satisfies the requested surfaces without requiring a new provider, a new model-resolution design, or a broad change to SASE’s model defaults.
