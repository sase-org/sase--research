# Research Report: Adding Google Gemini 4 Argon and Hydrogen Support to SASE and Modernizing `#research_swarm`

**Researcher:** gem (`research.4k.gem`)  
**Date:** November 13, 2026  
**Artifact Target:** `research:202611/google_argon_hydrogen_model_support__gem.md`  

---

## 1. Executive Summary

This independent research report investigates the architectural, configuration, and implementation requirements for introducing comprehensive support in SASE for Google's newest models: **Gemini 4 Argon** and **Gemini 4 Hydrogen**. It also details how to upgrade the `#research_swarm` macro from the legacy Gemini 3.8 Flash model to the newly released Hydrogen model.

### Key Findings
1. **Model Profiles & Provider Architecture**:
   - **Gemini 4 Argon** (released October 2026) is Google's flagship frontier reasoning model for complex, long-horizon multi-step problem solving. In Google Antigravity (`agy`), it is exposed under `gemini-4-argon-{high,medium,low}` and is strictly gated to Google AI Ultra and eligible Gemini Enterprise subscriptions. SASE partially catalogued Argon in `models.yml` (commit `4d8940d`), but completion surfaces and tier routing need verification against the newly expanded catalog.
   - **Gemini 4 Hydrogen** (released November 12, 2026) is Google's new high-throughput, high-efficiency model designed as the direct successor to Gemini Flash. In `agy models`, it exposes four reasoning levels: `gemini-4-hydrogen-xhigh`, `gemini-4-hydrogen-high`, `gemini-4-hydrogen-medium`, and `gemini-4-hydrogen-low`. Unlike Argon, Hydrogen is generally available across standard tiers, requiring no entitlement advisory, and is fully eligible for tier defaults and shipped size-alias pools.
2. **Model Completion Surfaces in SASE**:
   - SASE's completion architecture relies on a centralized manifest: `src/sase/llm_provider/models.yml`.
   - Updating `models.yml` automatically flows into:
     - ACE TUI directive completion (`%model:`, `%m:`) via `sase.macro.model_completion`.
     - ACE TUI Model Picker Modal (`ModelPickerModal`) via `sase.llm_provider.registry`.
     - ACE TUI Macro Argument Model completion (`#macro(model=...)`) via `_file_completion_macro_args.py`.
     - Model alias shortcuts (`@`) and explicit model shortcuts (`=`).
     - Editor LSP completions via `sase-macro-lsp`.
     - CLI completions via `sase completion`.
     - Mirrored documentation tables via `tools/render_model_docs`.
   - **Required Code Change**: The pure helper `src/sase/ace/tui/widgets/_agent_list_helpers.py` (`short_model_name`) contains an explicit keyword matching list. Adding `"hydrogen"` to this list is mandatory to prevent Hydrogen models from truncating to `"gemini"` in TUI tree badges.
3. **Upgrading `#research_swarm`**:
   - `#research_swarm` lives in the linked repository `sase-research-artifacts` (`src/sase_research_artifacts/xprompts/research_swarm.md`).
   - The fifth researcher (`.gem`, writing `__gem.md`) currently defaults to `gemini_model="agy/gemini-3.8-flash-high"`.
   - All four other swarm researchers (`codex`, `claude`, `grok`, `muse`) use `@xhigh` models (`codex/gpt-6.1-sol@xhigh`, `claude/opus@xhigh`, `grok/grok-4.6@xhigh`, `muse/muse-spark-1.3-contributor@xhigh`).
   - Because `agy` rejects explicit `@effort` suffixes in favor of slug variants, and Hydrogen introduces Google's first Flash/workhorse `xhigh` slug (`gemini-4-hydrogen-xhigh`), `#research_swarm` should default `gemini_model` to `agy/gemini-4-hydrogen-xhigh`. This brings the Gemini researcher into parity with the rest of the swarm.

---

## 2. Model Specifications & Provider Realities

### 2.1 Google Antigravity (`agy`) Model Inventory

Querying the local Antigravity CLI via `agy models` reveals the current live models exposed by Google's backend:

```text
gemini-4-argon-medium           Gemini 4 Argon (Medium)
gemini-4-argon-high             Gemini 4 Argon (High)
gemini-4-argon-low              Gemini 4 Argon (Low)
gemini-4-hydrogen-high          Gemini 4 Hydrogen (High)
gemini-4-hydrogen-xhigh         Gemini 4 Hydrogen (XHigh)
gemini-4-hydrogen-medium        Gemini 4 Hydrogen (Medium)
gemini-4-hydrogen-low           Gemini 4 Hydrogen (Low)
gemini-pro-orchestrator-g1-pro  Orchestrator (Argon)
gemini-3.8-flash-high           Gemini 3.8 Flash (High)
gemini-3.8-flash-medium         Gemini 3.8 Flash (Medium)
gemini-3.8-flash-low            Gemini 3.8 Flash (Low)
claude-opus-5-5-low             Claude Opus 5.5 (Low)
claude-opus-5-5-medium          Claude Opus 5.5 (Medium)
claude-opus-5-5-high            Claude Opus 5.5 (High)
claude-sonnet-5-5-low           Claude Sonnet 5.5 (Low)
claude-sonnet-5-5-medium        Claude Sonnet 5.5 (Medium)
claude-sonnet-5-5-high          Claude Sonnet 5.5 (High)
gpt-oss-120b-medium             GPT-OSS 120B (Medium)
```

### 2.2 Model Comparison: Argon vs. Hydrogen

| Attribute | Gemini 4 Argon | Gemini 4 Hydrogen |
| :--- | :--- | :--- |
| **Release Date** | October 2026 | November 12, 2026 |
| **Model Class** | Frontier Deep Reasoning | High-Efficiency Workhorse / Agentic Execution |
| **Context Window** | 1,000,000 tokens | 1,000,000 tokens (up to 1M output continuation) |
| **Thinking Slugs** | `high`, `medium`, `low` | `xhigh`, `high`, `medium`, `low` |
| **Account Entitlement** | Google AI Ultra / Gemini Enterprise Only | General Availability (Free, Plus, Pro, Ultra, API) |
| **SASE Advisory Needed** | Yes (`severity: info`, `label: needs Google AI Ultra`) | None (Unrestricted access) |
| **Tier Defaults Eligible** | No (would fail non-Ultra users) | Yes (can serve as `agy` large/small default) |
| **Size Alias Eligible** | No (excluded from shipped `@large` / `@xlarge`) | Yes (ideal for `@xsmall` or `@small`) |

### 2.3 Antigravity Parameter Semantics
- **Effort Encoding**: In SASE, provider `agy` (`src/sase/llm_provider/agy.py`) invokes the `agy` binary with `--model <slug>`. Antigravity does not support runtime `@effort` flags on the command line; effort is strictly selected via the hyphenated slug suffix (e.g. `-xhigh`, `-high`, `-medium`, `-low`). Any attempt to pass `@effort` on an `agy` model raises an explicit invocation error.
- **Short Aliases**: SASE assigns 5–8 character alphanumeric aliases for compact TUI display, fuzzy completion, and rapid CLI jump keys.
  - Argon: `gemini-4-argon-high` → `argon4h`, `gemini-4-argon-medium` → `argon4m`, `gemini-4-argon-low` → `argon4l`.
  - Hydrogen (Proposed): `gemini-4-hydrogen-xhigh` → `hydro4x`, `gemini-4-hydrogen-high` → `hydro4h`, `gemini-4-hydrogen-medium` → `hydro4m`, `gemini-4-hydrogen-low` → `hydro4l`.

---

## 3. Comprehensive Inventory of Model Completion Surfaces in SASE

A core objective of this research is identifying every surface in SASE where model completion occurs and determining the exact changes required.

```
+------------------------------------------------------------------------------------+
|                         src/sase/llm_provider/models.yml                           |
|                  (Single Source of Truth for Models, Tiers, Aliases)               |
+------------------------------------------+-----------------------------------------+
                                           |
                   +-----------------------+-----------------------+
                   |                                               |
                   v                                               v
+-------------------------------------+         +-------------------------------------+
|      sase.llm_provider.registry     |         |     tools/render_model_docs         |
|  - llm_known_model_names()          |         |  - docs/reference/providers/        |
|  - llm_model_short_aliases()        |         |    models.md                        |
|  - llm_model_advisories()           |         +-------------------------------------+
+------------------+------------------+
                   |
     +-------------+-------------+----------------------+--------------------+
     |                           |                      |                    |
     v                           v                      v                    v
+-------------------+   +--------------------+   +---------------+   +---------------+
| ACE TUI Input     |   | ACE Model Picker   |   | Macro Arg     |   | Macro LSP     |
| Directive Comp.   |   | Modal (OptionList) |   | Model Comp.   |   | Language Svr  |
| - %model:, %m:    |   | - 'm' key / Jump   |   | - #macro(m=)  |   | - IDEs / Vim  |
+-------------------+   +--------------------+   +---------------+   +---------------+
```

### Surface 1: ACE TUI Prompt Directive Completion (`%model:` / `%m:`)
- **Location**: `src/sase/ace/tui/widgets/_directive_completion_models.py`, `src/sase/macro/model_completion.py`.
- **Mechanism**: When typing `%model:` or `%m:`, SASE triggers `build_model_completion_catalog()`. It loads `get_llm_metadata_payload()`, which calls each provider’s `@hookimpl def llm_known_model_names()`. For `agy`, this dynamically reads `provider_model_names("agy")` from `models.yml`.
- **Filtering**: Filtering and sorting are performed by the Rust backend extension (`filter_model_completion_entries`).
- **Impact of Updating `models.yml`**: Immediate and automatic. Once added to `models.yml`, the new models and their short aliases are available in inline directive completion.

### Surface 2: ACE TUI Model Picker Modal (`ModelPickerModal`)
- **Location**: `src/sase/ace/tui/modals/model_picker_modal.py`, `src/sase/ace/tui/modals/model_picker_rows.py`, `src/sase/ace/tui/modals/model_picker_options.py`.
- **Mechanism**: Invoked via the leader keymap or modal shortcut (`m`). It groups models by provider, displays advisory badges, capacity hints, and short aliases. It calls `build_model_rows()`, which queries `model_to_provider_map()`, `model_short_alias_map()`, and `model_advisory_map()`.
- **Jump Navigation**: Key-based jump navigation (`test_model_picker_jump.py`) uses the visible row order. Placing Hydrogen after Argon ensures Argon’s existing jump target hints remain undisturbed.
- **Impact of Updating `models.yml`**: Fully automatic.

### Surface 3: Macro Argument Model Completion (`#macro(model=...)`)
- **Location**: `src/sase/ace/tui/widgets/_file_completion_macro_args.py`, `_macro_arg_assist_detection_contexts.py`.
- **Mechanism**: When entering arguments for a macro where an input has `type: model` (such as `claude_model=`, `gemini_model=`, or `lead_model=`), the prompt input bar detects `macro_arg_model` context. It calls `build_macro_arg_model_completion_candidates()`, which synthesizes a directive clause and invokes `build_directive_clause_candidates()`.
- **Impact of Updating `models.yml`**: Fully automatic. Typing `gemini_model=agy/` will immediately offer `gemini-4-hydrogen-xhigh`, `gemini-4-hydrogen-high`, etc.

### Surface 4: Prompt Input Model Alias (`@`) and Explicit Shortcut (`=`) Completion
- **Location**: `src/sase/ace/tui/widgets/model_alias_completion.py`, `src/sase/ace/tui/widgets/model_explicit_completion.py`.
- **Mechanism**: Typing `@` triggers alias completion (`@large`, `@xsmall`), while typing `=` or a bare provider name triggers explicit model shortcut completion. Both leverage `sase_core`'s Rust bindings `filter_model_alias_shortcut_entries` and `filter_explicit_model_shortcut_entries`.
- **Impact of Updating `models.yml`**: Fully automatic.

### Surface 5: Macro Language Server Protocol (Macro LSP)
- **Location**: `src/sase/integrations/macro_lsp.py`, `crates/sase_macro_lsp/`.
- **Mechanism**: Serves Neovim, VSCode, and other LSP clients. At startup, SASE serializes a static snapshot of `build_static_model_completion_catalog()` to `model_catalog.json` and passes it to the Rust binary via the `SASE_MACRO_MODEL_CATALOG` environment variable.
- **Impact of Updating `models.yml`**: Automatic upon LSP restart.

### Surface 6: Agent Tree & Row Display Helpers (`short_model_name`)
- **Location**: `src/sase/ace/tui/widgets/_agent_list_helpers.py:10`.
- **Mechanism**: Formats model strings into compact 4–10 character badges displayed in the agent tree and table columns.
- **Current Code**:
  ```python
  def short_model_name(model: str) -> str:
      """Extract short display name from a model string."""
      model_lower = model.lower()
      for keyword in (
          "wonder-full",
          "wonder",
          "argon",
          "flash",
          "fable",
          "opus",
          "sonnet",
          "haiku",
          "pro",
      ):
          if keyword in model_lower:
              return keyword
      parts = model.split("-")
      return parts[0] if parts else model
  ```
- **The Gap**: If `gemini-4-hydrogen-high` runs, `short_model_name()` currently matches none of the keywords and falls back to `parts[0]`, rendering `"gemini"`.
- **Required Edit**: Add `"hydrogen"` to the keyword list:
  ```python
  for keyword in (
      "wonder-full",
      "wonder",
      "hydrogen",
      "argon",
      "flash",
      "fable",
      "opus",
      "sonnet",
      "haiku",
      "pro",
  ):
  ```

### Surface 7: CLI Shell Completion
- **Location**: `src/sase/completion/`, `sase completion`.
- **Mechanism**: Subcommands accepting `--model` or `--next_model` query SASE's completion registry. When completion values are requested, they query the LLM registry.
- **Impact of Updating `models.yml`**: Automatic.

### Surface 8: Mirrored Documentation Tables
- **Location**: `docs/reference/providers/models.md`, `docs/reference/providers/agy.md`.
- **Mechanism**: SASE maintains generated Markdown tables between `<!-- BEGIN GENERATED: known-models -->` and `<!-- END GENERATED: known-models -->`.
- **Tooling**: Regenerated by `tools/render_model_docs` via `just fix` (or `just fmt-docs`), validated in CI by `just check` (`just fmt-docs-check`).

---

## 4. Upgrading `#research_swarm` to Gemini 4 Hydrogen

### 4.1 Swarm Architecture and Current Gemini Binding

The `#research_swarm` macro is defined in the linked repository `sase-research-artifacts` at:  
`src/sase_research_artifacts/xprompts/research_swarm.md`.

It orchestrates up to five independent research agents (`cdx`, `cld`, `grk`, `mus`, `gem`), followed by a consolidating lead researcher (`.final`) and optional linker/image/audio companions:

```text
research.<clan>.cdx (Codex, gpt-6.1-sol@xhigh)
research.<clan>.cld (Claude, opus@xhigh)
research.<clan>.grk (Grok, grok-4.6@xhigh)
research.<clan>.mus (Muse, muse-spark-1.3-contributor@xhigh)
research.<clan>.gem (Antigravity, agy/gemini-3.8-flash-high)  <-- CURRENT
      │
      ▼
research.<clan>.final (Lead Consolidator, @xlarge)
      │
      ▼
research.<clan>.linker (Publisher, @xlarge)
```

In `research_swarm.md`:
```yaml
  - name: gemini
    type: bool
    default: false
    description: Request the gemini (Antigravity) researcher.
  - name: gemini_model
    type: model
    default: "agy/gemini-3.8-flash-high"
    description:
      Model for `<clan>.gem`. Antigravity (`agy`) rejects explicit `@effort`
      suffixes; choose effort through the model slug (`-high`/`-medium`/`-low`).
```

### 4.2 Evaluating the New Hydrogen Model Default

With Hydrogen available, we evaluate two primary candidate configurations for `gemini_model`:

#### Option A: `agy/gemini-4-hydrogen-xhigh` (RECOMMENDED)
- **Rationale**:
  1. **Swarm Effort Parity**: All four sibling researchers in `#research_swarm` explicitly run at maximum reasoning effort (`@xhigh`).
  2. **Google's New Capability**: Prior Gemini Flash models only provided `-low`, `-medium`, and `-high`. Hydrogen is the first workhorse model from Google to introduce an `-xhigh` reasoning tier.
  3. **Research Quality**: Swarm researchers operate independently to produce thorough technical analysis. Limiting the Gemini researcher to `-high` leaves depth on the table relative to Claude Opus and GPT-6.1 Sol.
- **Trade-off**: Slightly higher execution latency and token spend than `-high`, but well within typical research swarm budgets.

#### Option B: `agy/gemini-4-hydrogen-high`
- **Rationale**: `-high` is Google's declared default thinking depth for Hydrogen, providing faster turn times and lower token consumption.
- **Trade-off**: Creates an asymmetry where the other four swarm members reason at `xhigh` while Gemini reasons at `high`.

### 4.3 Input Parameter Naming & Backward Compatibility
- **Retain Parameter Name `gemini_model`**:
  - The model family remains Google Gemini (`Gemini 4 Hydrogen`).
  - Existing scripts, aliases, user documentation, and macros use `gemini=true` and `gemini_model=...`.
  - The clan identifier remains `research.<clan>.gem`, the draft report remains `__gem.md`, and the prompt directive remains `#research(suffix=gem)`.
  - Renaming the parameter to `hydrogen_model` would break existing saved prompts and configuration without added benefit.
- **Update Parameter Description**:
  - Update description to explicitly name Gemini 4 Hydrogen and document the `-xhigh` slug availability.

### 4.4 Companion Changes in `sase-research-artifacts`
1. `src/sase_research_artifacts/default_config.yml`:
   The custom `@image` alias currently pools:
   ```yaml
   image:
     model: "codex/gpt-6.1-sol@xhigh | grok/grok-4.6@xhigh | agy/gemini-3.8-flash-high"
   ```
   This should also be updated to `agy/gemini-4-hydrogen-high` or `agy/gemini-4-hydrogen-xhigh`.
2. Tests:
   `tests/test_macro_loading.py` and `tests/test_default_config.py` assert the default model string and must be updated to the new slug.
3. Documentation:
   Update `README.md`, `docs/macros.md`, and `docs/configuration.md`.

---

## 5. Detailed Step-by-Step Implementation Plan

### Phase 1: Primary `sase` Repository Updates

#### Step 1.1: Edit `src/sase/llm_provider/models.yml`
Under `providers.agy`:
1. Add Hydrogen model slugs in CLI order (keeping Argon preceding Hydrogen):
   ```yaml
   providers:
     agy:
       models:
         - gemini-4-argon-high
         - gemini-4-argon-medium
         - gemini-4-argon-low
         - gemini-4-hydrogen-xhigh
         - gemini-4-hydrogen-high
         - gemini-4-hydrogen-medium
         - gemini-4-hydrogen-low
         - gemini-3.8-flash-high
         ...
   ```
2. Add short aliases under `providers.agy.short_aliases`:
   ```yaml
         gemini-4-hydrogen-xhigh: hydro4x
         gemini-4-hydrogen-high: hydro4h
         gemini-4-hydrogen-medium: hydro4m
         gemini-4-hydrogen-low: hydro4l
   ```
3. Update `providers.agy.tiers`:
   Update tier defaults from the legacy Gemini 3.7 Flash to Gemini 4 Hydrogen:
   ```yaml
       tiers:
         large: gemini-4-hydrogen-high
         small: gemini-4-hydrogen-low
   ```
4. Update shipped size aliases under `aliases`:
   In `xsmall`, replace `agy/gemini-3.8-flash-high` with `agy/gemini-4-hydrogen-high`:
   ```yaml
     xsmall:
       target:
         "claude/claude-haiku-5-5@xhigh | codex/gpt-6-luna@medium |
         agy/gemini-4-hydrogen-high | muse/muse-spark-1.3-contributor@medium"
   ```

#### Step 1.2: Edit `src/sase/ace/tui/widgets/_agent_list_helpers.py`
Add `"hydrogen"` to the `short_model_name()` keyword loop:
```python
    for keyword in (
        "wonder-full",
        "wonder",
        "hydrogen",
        "argon",
        "flash",
        "fable",
        "opus",
        "sonnet",
        "haiku",
        "pro",
    ):
```

#### Step 1.3: Update Tests in `sase`
1. `tests/ace/tui/widgets/test_agent_list_helpers.py`:
   Add test for Hydrogen badge formatting:
   ```python
   def test_short_model_name_recognizes_gemini_hydrogen() -> None:
       """Gemini 4 Hydrogen IDs should render with the compact hydrogen label."""
       assert short_model_name("gemini-4-hydrogen-high") == "hydrogen"
       assert short_model_name("gemini-4-hydrogen-xhigh") == "hydrogen"
   ```
2. `tests/llm_provider/test_agy_provider_core.py`:
   Add Hydrogen slugs to `_AGY_MODELS` and aliases to `test_agy_provider_metadata_hooks()`.
3. `tests/llm_provider/test_agy_usage_probe.py`:
   Add Hydrogen slugs to `_GEMINI_IDS`.
4. `tests/llm_provider/test_model_advisories.py`:
   Add `_HYDROGEN_SLUGS` and test that they carry no advisory.

#### Step 1.4: Regenerate Documentation and Validate Policy
Run:
```bash
just fix
just check
```
`just fix` will run `tools/render_model_docs` to update `docs/reference/providers/models.md` and `sase.llm_provider.model_policy` to verify size alias invariants.

---

### Phase 2: Linked `sase-research-artifacts` Repository Updates

#### Step 2.1: Open Linked Repository
```bash
sase repo open sase-research-artifacts -r "Update #research_swarm to Gemini 4 Hydrogen"
```

#### Step 2.2: Edit `src/sase_research_artifacts/xprompts/research_swarm.md`
Update `gemini_model` input specification:
```yaml
  - name: gemini_model
    type: model
    default: "agy/gemini-4-hydrogen-xhigh"
    description:
      Model for `<clan>.gem`. Antigravity (`agy`) rejects explicit `@effort`
      suffixes; choose effort through the model slug (`-xhigh`/`-high`/`-medium`/`-low`).
```

#### Step 2.3: Edit `src/sase_research_artifacts/default_config.yml`
Update `@image` model pool:
```yaml
      image:
        model: "codex/gpt-6.1-sol@xhigh | grok/grok-4.6@xhigh | agy/gemini-4-hydrogen-xhigh"
```

#### Step 2.4: Update Tests and Docs in `sase-research-artifacts`
1. `tests/test_macro_loading.py`:
   Update assertions on `xp.inputs[13].default` and `%m:agy/gemini-4-hydrogen-xhigh`.
2. `tests/test_default_config.py`:
   Update assertion on `image` pool members.
3. Update `docs/macros.md`, `docs/configuration.md`, and `README.md`.

#### Step 2.5: Verify
Run `just check` within the `sase-research-artifacts` checkout.

---

## 6. Verification Checklist & Risk Mitigations

| Risk / Consideration | Mitigation |
| :--- | :--- |
| **Non-Ultra Account Failures** | Argon remains flagged with the Ultra advisory and excluded from shipped tier/size defaults. Hydrogen carries no advisory and is safe for general defaults. |
| **Effort Syntax Incompatibilities** | Ensure `agy/gemini-4-hydrogen-xhigh` contains no trailing `@...` suffix, as `agy` relies solely on slug-based effort selection. |
| **TUI Badge Truncation** | Verify `short_model_name("gemini-4-hydrogen-high")` resolves to `"hydrogen"`, tested via unit tests. |
| **Cross-Repo Commit Obligations** | Because both `sase` and `sase-research-artifacts` are modified, the turn's host completion manifest must declare commit decisions for both repositories. |
| **Modal Picker Jump Stability** | Preserve Argon's position before Hydrogen in `models.yml` so `test_model_picker_jump.py` visible key sequences remain intact. |

---

## 7. Recommended Solution Summary

1. **Catalog Additions**:
   - Add all 4 Hydrogen slugs (`gemini-4-hydrogen-{xhigh,high,medium,low}`) to `models.yml` under `agy`.
   - Assign short aliases `hydro4x`, `hydro4h`, `hydro4m`, `hydro4l`.
   - Update `agy` tier defaults to `gemini-4-hydrogen-high` (large) and `gemini-4-hydrogen-low` (small).
   - Update `@xsmall` alias to use `agy/gemini-4-hydrogen-high`.
2. **TUI Display**:
   - Add `"hydrogen"` to `_agent_list_helpers.py` (`short_model_name`).
3. **Macro Modernization**:
   - Update `#research_swarm`'s `gemini_model` default to `"agy/gemini-4-hydrogen-xhigh"`, matching the `@xhigh` standard of the swarm.
   - Retain the parameter name `gemini_model` and short suffix `gem` for backward compatibility.
   - Update the `@image` pool in `default_config.yml` to reference Hydrogen.
4. **Tooling**:
   - Run `just fix` to automatically regenerate documentation tables and verify model policy.
