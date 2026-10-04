# Research Report: First-Class `enum` Macro Input Types, Cross-Plugin Reusability, and Dual-Speed Completion Architecture

**Author:** Researcher `gem` (Swarm ID: `research.0a.gem`)  
**Topic:** Design, critique, and architecture for a first-class `enum` macro input type with shared/reusable value sets, TUI prompt bar assist, and Language Server Protocol (LSP) completion.  
**Target Repository:** `sase` / `sase-core`  
**Date:** October 2026  

---

## Executive Summary

This research investigates the design, ergonomics, and implementation architecture for introducing a first-class `enum` macro input type to SASE, enabling shared value sets across built-ins, plugins, and user macros, and delivering seamless autocomplete in both the Textual prompt input widget (ACE) and external editors via the SASE Macro Language Server (`sase-macro-lsp`).

### Key Findings & Baseline Reality

1. **A Dormant Prototype Exists:** Contrary to the initial assumption that `enum` must be built from scratch, SASE already contains a partial, dormant prototype:
   - Python models define `InputType.ENUM` and `InputChoice(value, label)` in [`models.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/macro/models.py).
   - Frontmatter YAML validation in Rust [`sase-core`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/sase/repos/linked/sase-core/crates/sase_core/src/editor/frontmatter.rs) already validates `choices: [...]` for `type: enum`.
   - The TUI [`TypedInputForm`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/ace/tui/widgets/typed_input_form.py) already features an enum cycling button.
2. **The Completion Leg is Severed:** Autocomplete and assist for `enum` do not function anywhere:
   - In both Python and Rust, `MacroInputHint` wire types strip `choices`.
   - In both ACE TUI and `sase-macro-lsp`, argument value completion classifies `enum` as a type hint or hardcodes `bool_completion_list()`.
   - The canonical [`workflow.schema.json`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/macros/workflow.schema.json) completely omits `enum` from allowed input types.
3. **Zero Sharing Mechanics:** There is currently no mechanism for macros to share or reuse enum sets. Every enum must inline its choices directly.
4. **The `%model` Dichotomy (Static Enums vs. Dynamic Catalogs):** Treating `%model` as a static enum creates a severe architectural tension. Models, aliases, and provider assignments are dynamic runtime entities that evolve via plugins, user config, and API availability. Hardcoding models as a closed static list risks false-positive validation rejections.

### Core Verdict & Recommendations

- **Endorsement:** Strongly endorse adding full `enum` support. It dramatically reduces cognitive load, prevents costly LLM turn failures from misspellings, and elevates macro authoring.
- **Adjustments to Requirements:**
  1. *Token vs. Label Separation:* Strictly enforce that enum **values** are single-word tokens (no whitespace) matching identifier syntax, while supporting human-friendly **labels** and **descriptions** for display in completion menus and hover docs.
  2. *Dual-Speed Value Resolution:* Distinguish between **Static Enums** (closed, static lists declared in config/files/plugins) and **Dynamic Provider Catalogs** (`builtin@models`, `builtin@machines`, `builtin@projects`). Dynamic providers offer rich, live autocomplete and soft validation, avoiding false-rejection breakage.
  3. *Syntax Standardization:* Use `enum: <ref>` (with shorthand `choices: <ref>`) and shortform `enum(<ref>)` or `enum(val1, val2)`. For built-in dynamic catalogs, standardize on `builtin@models` (with alias `builtin@model`) rather than the redundant `builtin@model_enum_values`.

---

## 1. Codebase Reality Check: The Dormant `enum` Implementation

An audit of `sase` and `sase-core` reveals that work on an `enum` input type was previously started but left unfinished before reaching the editor completion and sharing layers.

```
                    ┌──────────────────────────────────────────────┐
                    │            Macro Definition (YAML)           │
                    │   input:                                     │
                    │     mode: {type: enum, choices: [fast, slow]}│
                    └──────────────────────┬───────────────────────┘
                                           │
                    ┌──────────────────────▼───────────────────────┐
                    │      Frontmatter Validation (Rust Core)      │
                    │  crates/sase_core/src/editor/frontmatter.rs  │
                    │  STATUS: VALIDATES OK                        │
                    └──────────────────────┬───────────────────────┘
                                           │
                    ┌──────────────────────▼───────────────────────┐
                    │      Catalog Loader & Python Models          │
                    │  src/sase/macro/models.py                    │
                    │  STATUS: PARSES OK (InputArg.choices)        │
                    └──────────┬───────────────────────┬───────────┘
                               │                       │
      ┌────────────────────────▼────────┐     ┌────────▼────────────────────────┐
      │     TUI Prompt Assist Wire      │     │      Rust LSP Wire & Server     │
      │  _macro_arg_assist_models.py    │     │  crates/sase_xprompt_lsp/       │
      │  STATUS: BROKEN (choices stripped)    │  STATUS: BROKEN (hardcoded bool)│
      └─────────────────────────────────┘     └─────────────────────────────────┘
```

### 1.1 Where `enum` Already Exists
- **Python Models ([`src/sase/macro/models.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/macro/models.py#L35)):**
  `InputType.ENUM = "enum"` is declared alongside `WORD`, `LINE`, `PATH`, etc.
  `InputChoice(value: str, label: str | None = None)` represents individual declared choices.
  `InputArg.__post_init__` enforces that `type == ENUM` has non-empty choices, and non-ENUM types have empty choices.
  `InputArg.validate_and_convert(value)` validates that `value` exists in declared choices.
- **Python Parser ([`src/sase/macro/loader_parsing.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/macro/loader_parsing.py#L109)):**
  `_parse_input_choices()` parses both scalar arrays (`choices: [fast, slow]`) and mapping arrays (`choices: [{value: "fast", label: "Fast mode"}]`).
  Shortform and longform inputs parse `choices` into tuples of `InputChoice`.
- **Rust Core Frontmatter ([`crates/sase_core/src/editor/frontmatter.rs`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/sase/repos/linked/sase-core/crates/sase_core/src/editor/frontmatter.rs#L175)):**
  `InputType::Enum` is defined in Rust.
  `validate_input_choices()` validates that `choices` is present, non-empty, and only declared for `enum`.
  `input_type_schema()` exports the `enum` descriptor over the PyO3 binding (`frontmatter_input_type_schema`).
- **Rust Catalog Wire ([`crates/sase_core/src/macro_catalog/types.rs`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/sase/repos/linked/sase-core/crates/sase_core/src/macro_catalog/types.rs#L188)):**
  `CatalogInput` and `MobileXpromptInputWire` carry `choices: Vec<MobileInputChoiceWire>`.
- **TUI Form Widget ([`src/sase/ace/tui/widgets/typed_input_form.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/ace/tui/widgets/typed_input_form.py#L143)):**
  `_EnumChoiceButton` cycles choices when clicked in modal forms.

### 1.2 Where the Implementation Stops Short
1. **TUI Assist Strips Choices:**
   In [`src/sase/ace/tui/widgets/_macro_arg_assist_models.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/ace/tui/widgets/_macro_arg_assist_models.py#L11), `MacroInputHint` only has `(name, type, required, default_display, position, repeatable, description)`. `choices` is completely dropped.
2. **TUI Assist Classifies Enum as Non-Completable:**
   In [`src/sase/ace/tui/widgets/_macro_arg_assist_detection.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/ace/tui/widgets/_macro_arg_assist_detection.py#L234), `_completion_kind_for_input()` only handles `path`, `bool`, and `agent`. Any other type returns `"macro_arg_type_hint"`, which produces no suggestions.
3. **TUI Value Completion Only Knows Booleans:**
   In [`src/sase/ace/tui/widgets/_file_completion_macro_args.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/ace/tui/widgets/_file_completion_macro_args.py#L43), `macro_arg_value` exclusively invokes `_build_bool_completion_candidates()`.
4. **Rust LSP Drops Choices in Wire:**
   In [`crates/sase_core/src/editor/wire.rs`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/sase/repos/linked/sase-core/crates/sase_core/src/editor/wire.rs#L394), the Rust `MacroInputHint` struct omits `choices`.
5. **Rust LSP Hardcodes Booleans:**
   In [`crates/sase_xprompt_lsp/src/server/completion.rs`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/sase/repos/linked/sase-core/crates/sase_xprompt_lsp/src/server/completion.rs#L864), `CompletionContextKind::MacroArgumentValue` directly executes `bool_completion_list()`.
6. **Schema Omission:**
   [`src/sase/macros/workflow.schema.json`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/macros/workflow.schema.json#L27) lists `"word", "line", "text", "path", "agent", "int", "integer", "float", "bool", "boolean", "string"`. `enum` is invalid per schema.
7. **No Reusability Layer:**
   Neither the Python runtime nor `sase-core` has any registry, lookup table, or syntax to refer to a shared enum set by name or URI.

---

## 2. Critique of the Proposed Plan

### 2.1 "Enums as a Sub-Type of `word`"
The user states:
> *"These values are just single-word strings, so enums are sort of like a sub-type of the existing word macro input type."*

#### Analysis & Critique:
- **Syntactic Necessity in Inline Macros:**
  In SASE, macro references can take the bare colon syntax `#macro:arg1,arg2` or parenthesized syntax `#macro(arg1, name=val)`.
  In colon syntax, arguments are whitespace-delimited tokens. If an enum value contained whitespace (e.g. `"fast mode"`), it would break bare argument parsing unless quoted or encoded with `+` (as in `decode_macro_arg_value`).
  By enforcing that enum values are single-word tokens (no whitespace, matching `[a-zA-Z0-9_\-\.:@]+`), enum arguments work smoothly across all invocation forms without escaping.
- **The Value vs. Label Nuance:**
  While the machine *value* must be a single word, forcing the human *display* to be a single cryptic word degrades UX.
  For example, in a model picker, the machine value is `gemini-1.5-pro` or `sonnet`, but the user benefits from seeing `Claude 3.5 Sonnet (Anthropic)` in the completion menu.
  *Conclusion:* The machine value MUST be a single-word token, but the definition must support an optional human-readable `label` and `description`.

### 2.2 Reusability via `builtin@model_enum_values`
The user suggests:
> *"We need to support re-using enum values so plugin providers and sase itself can share enum value sets... I'm imagining that we can use something like `builtin@model_enum_values` to specify that a macro input uses this type but you should think hard about the best way to do this."*

#### Analysis & Critique:
1. **Naming & Conventions:**
   Across SASE, provider references follow `<source>@<slug>` (e.g., `builtin@commit`, `builtin@command`, `builtin@tailnet`, `github@pr`, `sase_listen@voice`).
   The name `builtin@model_enum_values` is needlessly verbose. `_values` and `_enum` duplicate concept information.
   *Recommendation:* Use `builtin@models` (or `builtin@model`). For other built-ins: `builtin@machines`, `builtin@projects`, `builtin@tribes`.
2. **The Nature of Models (Dynamic Catalogs vs. Static Enums):**
   This is the most critical design insight:
   - A traditional enum is **static and closed**: e.g. `[draft, ready, closed]`. It can be validated strictly at YAML parse time.
   - Models are **dynamic and open**: SASE supports multiple LLM providers (`anthropic`, `gemini`, `openai`, `agy`, `codex`, `qwen`, `opencode`). Users define custom aliases in config; providers add models dynamically; plugins register models; temporary CLI overrides change available models.
   - SASE's core editor philosophy states ([`crates/sase_core/src/editor/wire.rs#L510`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/sase/repos/linked/sase-core/crates/sase_core/src/editor/wire.rs#L510)):
     > *`/// Suggestions are assistance, never an accidental allowlist.`*
   - If a macro author declares an input of type `builtin@models`, and validation strictly rejects any string not found in a static snapshot, introducing a new model or alias would break existing macros until caches are flushed.
   - *Recommendation:* Dynamic value providers like `builtin@models` must perform **dynamic resolution** (via SASE's model alias/provider registry) rather than treating the catalog as a frozen static allowlist.

3. **Placement in Frontmatter Syntax:**
   Where should the reference go?
   - *Option A (Direct Type):* `target_model: builtin@models`
   - *Option B (Type Enum + Field):* `target_model: {type: enum, enum: builtin@models}`
   - *Option C (Polymorphic Choices):* `target_model: {type: enum, choices: builtin@models}`
   We evaluate these options below.

---

## 3. Adjustments to Requirements

Based on the critique, we adjust and formalize the requirements:

| Original Requirement | Adjusted Requirement | Rationale |
| :--- | :--- | :--- |
| Enums are single-word strings. | **Machine values are single-word tokens; UI labels are arbitrary strings.** | Preserves clean macro syntax (`#macro:val`) while allowing rich descriptions in autocomplete menus and hover docs. |
| Use `builtin@model_enum_values`. | **Standardize on `builtin@models` (with alias `builtin@model`).** | Conforms to SASE `<source>@<slug>` conventions without redundant suffix noise. |
| Enums only represent static choice lists. | **Support both Static Enums and Dynamic Provider Catalogs.** | Models, machines, and VCS projects change dynamically at runtime and must resolve through provider registries rather than frozen static lists. |
| Validation is a strict closed check. | **Static enums validate closed; dynamic providers validate resolvable.** | Static enums (e.g. `[fast, slow]`) reject unknown values. Dynamic catalogs validate via provider resolver (`resolve_model_provider_with_effort`), failing soft on transient errors. |
| Enum values only specified in macro files. | **Introduce a tiered Enum Registry (Builtin -> Plugin -> Project -> User).** | Allows projects and plugins to define domain enums once (e.g., `environments`, `pr_status`) and share them across many macros. |

---

## 4. Architectural Design: The Recommended Solution

We propose a unified, tiered Enum Architecture that spans macro frontmatter, workflow definitions, Python runtime validation, Rust core cataloging, the TUI prompt bar, and the Macro LSP.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ENUM RESOLUTION LAYERS                          │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Builtin Dynamic Catalogs:                                           │
│    builtin@models   --> sase.macro.model_completion (LLM Registry)     │
│    builtin@machines --> sase.dispatch.machine_catalog (Dispatch hosts) │
│    builtin@projects --> sase.macro.vcs_projects (VCS catalog)          │
│    builtin@tribes   --> sase.config (Agent tribes)                     │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Plugin Enums (via Entry Points or Plugin Config):                   │
│    sase_github@pr_status, sase_listen@voices, etc.                    │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Project-Defined Enums:                                              │
│    sase/config.yml (enums:) or sase/enums/*.yml                        │
│    e.g. project@environments, @environments                            │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Inline Enums:                                                       │
│    choices: [fast, slow] or [{value: fast, label: "Fast Mode"}]        │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Authoring Syntax Specifications

#### 1. Inline Static Enums
For macro-specific choices that are not shared:

```yaml
# Longform or Mapping Form
input:
  mode:
    type: enum
    choices: [fast, slow, dry_run]
    default: fast
    description: "Execution velocity"

  # Rich inline choices with human labels
  format:
    type: enum
    choices:
      - value: json
        label: "JSON (Machine-readable)"
      - value: yaml
        label: "YAML (Human-friendly)"
      - value: text
        label: "Plain Text"
    default: json
```

Shortform syntax:
```yaml
input:
  mode: enum(fast, slow, dry_run)
```

#### 2. Reusable / Shared Enum References
For sharing value sets across macros and plugins:

```yaml
# Standard Full Form
input:
  target_model:
    type: enum
    enum: builtin@models
    default: sonnet
    description: "LLM model to use for analysis"

  pr_status:
    type: enum
    enum: github@pr_status
    default: draft

  env:
    type: enum
    enum: @environments   # Shorthand for project@environments
```

Forgiving Shorthand (accepting `choices:` as a string reference):
```yaml
input:
  target_model:
    type: enum
    choices: builtin@models
```

Shortform syntax:
```yaml
input:
  target_model: enum(builtin@models)
  # Direct type shorthand (auto-inferred as enum when reference is recognized):
  target_model: builtin@models
```

### 4.2 The Enum Registry & Discovery Architecture

We introduce an `EnumRegistry` responsible for resolving references (`<namespace>@<slug>`) to a collection of `InputChoice` objects.

#### Namespacing & Precedence:
1. `builtin@<slug>`: Handled by built-in dynamic providers registered in Python/Rust core.
2. `<plugin>@<slug>`: Discovered via setuptools entry point group `sase_enums` or packaged in plugin configs.
3. `project@<slug>` (or `@<slug>` within the project): Loaded from the workspace's `sase/config.yml` under `enums:` or files in `sase/enums/<slug>.yml`.
4. `user@<slug>`: Loaded from `~/.config/sase/config.yml` under `enums:`.

#### Project/User YAML Enum Definition Format:
In `sase/config.yml`:
```yaml
enums:
  environments:
    - dev
    - staging
    - prod
  deployment_tiers:
    - value: edge
      label: "Edge POPs"
    - value: regional
      label: "Regional Data Centers"
```

#### Built-in Dynamic Providers:
- `builtin@models`:
  Queries SASE's LLM provider registry (`sase.macro.model_completion.build_model_completion_catalog()`).
  Yields canonical model names, provider-qualified names (`anthropic:claude-3-5-sonnet`), and active aliases (`sonnet`, `flash`, `@smart`, `@fast`).
  Labels include provider name and parameter tier.
- `builtin@machines`:
  Queries `sase.dispatch.machine_catalog.machine_completion_catalog_payload()`.
  Yields known remote hosts and execution nodes.
- `builtin@projects`:
  Queries known VCS project tags (`+sase`, `+sase-core`, etc.).
- `builtin@tribes`:
  Queries agent clan and tribe tags.

### 4.3 Wire Contract & Rust Backend Boundary

Under SASE Rule 1.3 (*Rust Core Backend Boundary*), shared catalog parsing and editor wire models live in `sase-core`.

#### 1. Wire Struct Updates ([`crates/sase_core/src/editor/wire.rs`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/sase/repos/linked/sase-core/crates/sase_core/src/editor/wire.rs)):
Update `MacroInputHint` to preserve `choices` and optional `enum_ref`:

```rust
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MacroInputHint {
    pub name: String,
    #[serde(rename = "type")]
    pub r#type: String,
    #[serde(default)]
    pub description: Option<String>,
    pub required: bool,
    pub default_display: Option<String>,
    pub position: u32,
    #[serde(default)]
    pub repeatable: bool,
    #[serde(default)]
    pub choices: Vec<MobileInputChoiceWire>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub enum_ref: Option<String>,
}
```

#### 2. Frontmatter Validation Updates ([`crates/sase_core/src/editor/frontmatter.rs`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/sase/repos/linked/sase-core/crates/sase_core/src/editor/frontmatter.rs)):
Update `validate_input_choices()` to accept either:
- A non-empty sequence of scalar / `{value, label}` choices.
- A valid string enum reference (`<namespace>@<name>`).
If an unknown reference is detected, report diagnostic: `unresolved_enum_reference`.

#### 3. Macro Argument Trigger Context ([`crates/sase_core/src/editor/completion/trigger_context.rs`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/sase/repos/linked/sase-core/crates/sase_core/src/editor/completion/trigger_context.rs#L418)):
```rust
fn completion_kind_for_input(input: &MacroInputHint) -> CompletionContextKind {
    match input.r#type.as_str() {
        "path" => CompletionContextKind::MacroArgumentPath,
        "bool" => CompletionContextKind::MacroArgumentValue,
        "agent" => CompletionContextKind::MacroArgumentAgent,
        "enum" => CompletionContextKind::MacroArgumentEnum, // New dedicated context
        _ => CompletionContextKind::MacroArgumentTypeHint,
    }
}
```

### 4.4 Language Server Protocol (`sase-macro-lsp`) Implementation

In [`crates/sase_xprompt_lsp/src/server/completion.rs`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/sase/repos/linked/sase-core/crates/sase_xprompt_lsp/src/server/completion.rs):

When the cursor sits in a macro argument position whose active input is `CompletionContextKind::MacroArgumentEnum`:
1. **Dynamic Model Enums:**
   If `input.enum_ref == Some("builtin@models")`:
   Reuse the existing, battle-tested `model_completion_list(token, config.model_catalog.as_deref())`. This immediately reuses the cached model catalog that the LSP already reads!
2. **Dynamic Machine Enums:**
   If `input.enum_ref == Some("builtin@machines")`:
   Reuse `load_machine_catalog()`.
3. **Static / Inline Enums:**
   If `input.choices` is populated:
   Generate `CompletionItem` entries:
   - `label`: `choice.value`
   - `kind`: `CompletionItemKind::EnumMember`
   - `detail`: `choice.label` (if provided)
   - `documentation`: Rich markdown explaining the choice.
   - `sort_text`: Ordered by declaration or matching priority.

### 4.5 Textual TUI Prompt Bar & Argument Assist

In `src/sase/ace/tui/widgets/`:

1. **Model Synchronization ([`_macro_arg_assist_models.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/ace/tui/widgets/_macro_arg_assist_models.py)):**
   Add `choices: tuple[InputChoice, ...] = ()` and `enum_ref: str | None = None` to `MacroInputHint`.
2. **Context Detection ([`_macro_arg_assist_detection.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/ace/tui/widgets/_macro_arg_assist_detection.py)):**
   In `_completion_kind_for_input()`, route `input_hint.type == "enum"` to `"macro_arg_value"`.
3. **Candidate Builder ([`_file_completion_macro_args.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/ace/tui/widgets/_file_completion_macro_args.py)):**
   When `ctx.completion_kind == "macro_arg_value"`:
   - If `active_input.type == "bool"`: call `_build_bool_completion_candidates(ctx.token)`.
   - If `active_input.type == "enum"`:
     - If `active_input.enum_ref == "builtin@models"`:
       Call `sase.macro.model_completion.build_model_completion_catalog()` to get live model candidates.
     - Else: iterate over `active_input.choices` matching prefix `ctx.token`.
     - Return `CompletionCandidate` entries with `display` (formatted value + label) and `insertion` (token).
4. **Visual Argument Hints ([`_macro_arg_assist_inputs.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/ace/tui/widgets/_macro_arg_assist_inputs.py)):**
   When hovering or displaying hints for an enum parameter, format the hint beautifully:
   - For small enums ($\le 3$ values): `mode: [fast|slow|dry_run]`
   - For referenced or large enums: `model: enum(builtin@models)` or `env: enum[@dev|staging|...]`
   - Active parameter highlighted with `▸` pointer and dimmed defaults.

---

## 5. Alternatives Considered

We evaluated three architectural options for syntax and resolution:

| Dimension | Option 1: Ad-hoc Built-in Strings in `choices:` | Option 2: Pure Custom Type Aliases (`type: model`) | Option 3: Unified Enum Registry with Ref Syntax (Recommended) |
| :--- | :--- | :--- | :--- |
| **Syntax Example** | `type: enum`<br>`choices: builtin@models` | `type: model`<br>`type: github@pr_status` | `type: enum`<br>`enum: builtin@models`<br>`choices: [inline...]` |
| **Shortform Sugar** | None (`choices` requires mapping) | `model: model`<br>`status: github@pr_status` | `model: enum(builtin@models)`<br>`mode: enum(fast, slow)` |
| **User/Project Enums** | Poor (no clean way to define static project enums) | Over-engineered (requires registering custom type ASTs) | Excellent (`project@environments` via `enums:` config section) |
| **Dynamic Catalogs** | Supported via special-case strings | Requires custom type handlers | First-class via `EnumRegistry` providers |
| **Implementation Complexity** | Low | High (modifies entire type grammar) | Moderate (extends existing `InputArg` & `frontmatter.rs`) |
| **Tooling & LSP Elegance** | Clunky | Clean but open-ended | Highly structured (`EnumMember` LSP items) |

### Why Option 3 Wins:
- It respects the existing foundation in `models.py` and `frontmatter.rs` without discarding prior work.
- It solves both inline one-off enums and shared/reusable enums.
- It cleanly distinguishes the structural concept (`type: enum`) from the value provider (`enum: ...` or `choices: [...]`).
- It allows shortform syntax `enum(fast, slow)` and `enum(builtin@models)` that feels native to Markdown frontmatter.

---

## 6. Implementation Roadmap & Execution Plan

A phased implementation ensures clean, verifiable progress without breaking CI gates:

### Phase 1: Wire & Model Alignment (No breaking changes)
1. Update `MacroInputHint` in [`src/sase/ace/tui/widgets/_macro_arg_assist_models.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/src/sase/ace/tui/widgets/_macro_arg_assist_models.py) to include `choices` and `enum_ref`.
2. Update `MacroInputHint` in `sase-core` ([`crates/sase_core/src/editor/wire.rs`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_16/sase/repos/linked/sase-core/crates/sase_core/src/editor/wire.rs)).
3. Update `workflow.schema.json` to formally include `enum` in allowed types and document `choices` and `enum`.
4. Ensure single-word validation in `InputArg.validate_and_convert()`: verify `not any(c.isspace() for c in value)`.

### Phase 2: Inline Enum Autocomplete (TUI + LSP)
1. Connect `_macro_arg_assist_detection.py` and `_file_completion_macro_args.py` in ACE TUI to return completion candidates for inline `choices`.
2. Update `crates/sase_xprompt_lsp/src/server/completion.rs` to emit `CompletionItemKind::EnumMember` for macro inputs with declared choices.
3. Test end-to-end: typing `#test_macro(mode=` pops up `[fast, slow]`.

### Phase 3: The Enum Registry & Reusable Enums
1. Implement `sase.macro.enums`:
   - `EnumRegistry` protocol.
   - Built-in dynamic provider for `builtin@models` (backed by `sase.macro.model_completion`).
   - Dynamic providers for `builtin@machines` and `builtin@projects`.
2. Support loading static enums from `sase/config.yml` (`enums:` section) and `~/.config/sase/config.yml`.
3. Add plugin entry point discovery for `sase_enums`.
4. Update frontmatter parser and validator to recognize `enum: <ref>` and string `choices: <ref>`.

### Phase 4: LSP Model Catalog Re-use
1. In `sase-macro-lsp`, wire `builtin@models` directly to the server's existing `load_model_catalog()`.
2. Add JSON snapshot generation for static/plugin enums in `_materialize_macro_lsp_catalogs()`.

### Phase 5: TUI Aesthetics & Polish
1. Rich styling in prompt bar arg assist overlay: format active enum parameters with distinctive badge `#D7AF87` and `[choice1|choice2]` display.
2. In `TypedInputForm`, allow searchable popup picker for enums with $>5$ options (such as models).

---

## 7. Conclusion

Adding a first-class `enum` macro input type is one of the highest-leverage ergonomics improvements available for SASE's macro system. Because substantial foundational work already exists in `models.py` and `frontmatter.rs`, completing this feature requires finishing the "last mile" of editor integration: threading `choices` through the assist wire, routing completion events to candidate builders, and introducing a clean `EnumRegistry` that bridges static user enums with dynamic system providers like `builtin@models`.

The resulting design is intuitive to author, reliable under failure, and visually beautiful in both terminal and GUI editors.
