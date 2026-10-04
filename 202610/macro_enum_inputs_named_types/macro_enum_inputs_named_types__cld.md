# Enum Macro Inputs and Shared Value Sets — Design Research (cld)

_Researcher: `cld` · 2026-10-04 · scope: sase (Python) + sase-core (Rust core, macro LSP) +
one plugin's macros used as a real-world example_

## 0. Bottom line

1. **The `enum` input type already exists.** It shipped on 2026-08-07 alongside
   notification-gate per-option inputs (`8e52e46386`, `e1da6d1b76`). Python
   (`InputType.ENUM`, `InputChoice`, inline `choices:`), the Rust macro catalog, LSP
   frontmatter diagnostics, the mobile wire, and `docs/macros.md` § _Enum Choices_ all
   support it. What is missing is the payoff you actually want: **neither the prompt
   bar nor the LSP completes enum values.** Both send `enum` to a generic "type hint"
   path that offers nothing. Shared, reusable value sets are also missing, and the
   current implementation has several real defects (§2).
2. **The motivating example, "a valid `%model` value", is not an enum.** `%model`
   accepts an open grammar: `@alias`, `@alias@effort`, `provider/model@effort`, nested
   OpenCode paths, and bare known models. The valid set also depends on the machine
   (installed providers, user-defined aliases such as `@image`). If you model it as a
   closed list of strings, the list will either reject valid input or stop being
   closed. The right shape is a **domain type**: `type: model`. `type: agent` already
   works this way.
3. **Recommendation: named input types.** Keep `type: enum` + inline `choices` for
   one-off sets. Then let `type:` name a shared type:
   - Builtin types use bare names that mirror directive value roles: `type: model`,
     `type: effort`, and later `bead`, `tribe`, `machine`, `task_type`, `duration`.
   - User and project config declare closed enums by bare name (`input_types:` in
     `sase.yml`).
   - Plugins declare closed enums with the existing qualified grammar,
     `type: <dist>@<id>`.

   The guiding rule is simple: **if a directive accepts it, a macro input can be typed
   as it, and both complete and validate the same way.**
4. Ship in phases. First fix the existing defects (YAML coercion divergence, dropped
   longform `choices`, silent unknown-type fallback, schema drift). Then add enum
   completion everywhere. Then add `model`/`effort`, then config enums. Defer the
   plugin hook until more than one plugin needs it.

The rest of this report gives the evidence, a critique of the proposal, the requirement
changes I'm proposing (§4), the options I considered, and the full recommended design.

---

## 1. What already exists

| Layer                     | Where                                                                                       | Status                                                                                                      |
| ------------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Python model              | `src/sase/macro/models.py:24` (`InputType.ENUM`), `:71` (`InputChoice{value,label}`)        | ✅ Enum requires non-empty `choices`; other types must not declare them; duplicate values are rejected (`:111`) |
| Python validation         | `src/sase/macro/models.py:191`                                                              | ✅ Exact-match membership; the error lists the allowed values                                                |
| Python parsing (macros)   | `src/sase/macro/loader_parsing.py:109` `_parse_input_choices`                               | ✅ Scalars or `{value,label}` maps, in shortform and longform                                               |
| Python parsing (workflows)| `src/sase/macro/workflow_loader_parse.py:21`                                                | ❌ Longform drops `choices` (§2.2)                                                                           |
| Rust catalog              | `sase-core/crates/sase_core/src/macro_catalog/parsing.rs:654,688`                           | ✅ Parses `enum` and `choices` into `CatalogInput.choices` and the mobile wire                              |
| Rust LSP diagnostics      | `sase-core/crates/sase_core/src/editor/frontmatter.rs:883` `validate_input_choices`         | ✅ Flags missing or forbidden `choices` and an invalid default                                              |
| Mobile wire               | `sase_core/src/host_bridge.rs:851` `MobileXpromptInputWire.choices`                         | ✅                                                                                                          |
| TUI launch form           | `src/sase/ace/tui/widgets/typed_input_form.py:143`                                          | ✅ A button that cycles through the choices                                                                 |
| TUI prompt-bar completion | `_macro_arg_assist_detection.py:234`, `_macro_arg_assist_models.py:12`                      | ❌ `MacroInputHint` has no `choices`; enum falls through to `macro_arg_type_hint`                            |
| LSP completion            | `trigger_context.rs:418`, `sase_xprompt_lsp/src/server/completion.rs:864`                   | ❌ The editor `MacroInputHint` wire has no `choices`; enum → `MacroArgumentTypeHint` → empty list            |
| Docs                      | `docs/macros.md` § Enum Choices; `docs/workflow_spec.md` Supported Types                    | ✅ The workflow doc works around §2.2 by saying "declare choices with the shortform syntax"                 |

Two existing pieces of infrastructure matter a lot for this design:

- **`<plugin>@<id>` is already a shared grammar.** `src/sase/plugins/qualified_id.py`
  ("Shared `<plugin>@<id>` parsing for every `use:` config consumer") covers
  `builtin@commit`, `builtin@plan`, `builtin@tailnet`, task-type overrides, and
  artifact/file-hook providers. Its id regex is `[a-z0-9][a-z0-9_-]*`, and the plugin
  part is the PEP 503-normalized distribution name or the literal `builtin`.
- **Directive value roles already act as named value domains.**
  `DirectiveValueRole` (`sase_core/src/editor/wire.rs:513`) lists `Model`, `Agent`,
  `Clan`, `Session`, `Tribe`, `Hood`, `Bead`, `Machine`, `Tab`, `FinalizerInstance`,
  `Duration`, `WaitTime`, `Bool`, and others. Each one already has completers in both
  the TUI (`directive_completion.py`) and the LSP. The model catalog (aliases,
  providers, effort, advisories, pool counts) is built in Python
  (`src/sase/macro/model_completion.py`) and written to JSON for the Rust LSP
  (`integrations/macro_lsp.py:479`). Filtering is already Rust-backed and shared by
  both frontends.

---

## 2. Defects and gaps in the current enum support

Each item below was reproduced or read directly from the code.

### 2.1 Python and Rust disagree on YAML scalars (correctness bug)

PyYAML uses YAML 1.1. `serde_yaml` 0.9 in sase-core uses YAML 1.2. I reproduced the
Python side:

```text
choices: [yes, no]  default: yes
→ Python choices = ['True', 'False'], default = True (a bool)
→ #x:yes  →  "Argument 'answer' expects one of True, False, got 'yes'"
```

On the Rust side, `yes`/`no` stay as strings, `true` becomes `"true"` (Python produces
`"True"`), and float choices are dropped silently because `value_as_string`
(`parsing.rs:777`) handles only str, i64, and bool. The result is that **the LSP would
suggest `yes`, and the runtime would reject it.** This is the kind of cross-frontend
drift that `decisions:rust-core-required` exists to prevent.

### 2.2 Longform workflow inputs drop `choices`

`parse_workflow_inputs` (`workflow_loader_parse.py:21`) never reads `choices`. A
longform workflow input with `type: enum` therefore always raises "declares no choices"
in `InputArg.__post_init__`. The docs currently work around this with "declare
`choices` with the shortform syntax". There are also two near-duplicate longform
parsers that differ only in how they handle `default`.

### 2.3 Unknown types silently become `line`

`parse_input_type` (`loader_parsing.py:106`) ends with
`type_map.get(..., InputType.LINE)`. I confirmed that `type: model` and the typo
`type: enmu` both load as `line` with no warning. The Rust LSP reports
`invalid_xprompt_frontmatter_input_type` instead. **This matters for the new feature:**
a macro that uses `type: model` on today's sase silently loses its validation, and a
typo in a named type never errors.

### 2.4 The type vocabulary has drifted across five places

| Place                                         | Lists                                                     |
| --------------------------------------------- | --------------------------------------------------------- |
| Python `parse_input_type`                     | word line text path agent int/integer bool/boolean float enum code |
| Rust `macro_catalog::parse_input_type`        | same as above                                             |
| Rust `editor/frontmatter.rs` (LSP)            | same as above, no `string`                                |
| `src/sase/macros/workflow.schema.json:27,53,62` | word line text path agent int integer float bool boolean **string**; **no enum, code, or `choices` key** (`additionalProperties: false`) |
| `src/sase/config/sase.schema.json:944,965,974`  | as above **minus `agent`**; no enum, code, or `choices`   |

`type: string` is accepted by both schemas and used by the bundled
`eval_ifs_loops.yml`. Python silently maps it to `line`, and the LSP flags it as
invalid. Adding named types makes this drift worse unless the list comes from one
source.

### 2.5 No completion for enum values in either frontend

Covered in §1. Note also that `bool` is just the closed set `true|false`. Both
frontends have a special `bool_completion_list` that would fold naturally into a
generic choices path.

### 2.6 Minor inconsistencies

- Vocabulary: macro and gate inputs say `choices`, while task-type fields
  (`task_type/spec.rs:78`) and the artifacts-pane contract say `values`. I recommend
  keeping `choices` for inputs because it's already shipped, documented, and on the
  mobile wire. Don't introduce a third word.
- The signature display shows `level: enum`, which tells you nothing. For small
  enums, show `level: debug|info|warn|error`.

---

## 3. Which inputs actually need this

`sase macro list` loads 114 macros (bundled, home, config, and plugins). Input types:
`word` 37, `text` 13, `bool` 12, `int` 12, `line` 10, `path` 7, `agent` 1, **`enum` 0**.
I sorted the `word` and `line` inputs that really have a restricted domain:

| Kind                           | Examples (macro → input)                                                                                                       | Count |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ | ----- |
| **Model expression**           | `research_swarm` → `codex_model`, `claude_model`, `grok_model`, `muse_model`, `gemini_model`, `lead_model`, `image_model`, `linker_model`, `audio_model` | 9     |
| Bead id                        | `bd/work_task`, `bd/work_phase_bead`, `bd/land_epic` → `bead_id`                                                               | 3     |
| Patch / PR name                | `pr`, `mentor`, `fix_hook`, `make_mentor_changes` → `name`/`cl_name`                                                           | 4+    |
| Workspace / VCS prefix         | `mentor`, `fix_hook`, `make_mentor_changes` → `vcs_type` ("Registered workspace directive prefix")                             | 3     |
| Other live catalogs            | `tribe` → `tribe`; `prs/compare` → `task_type`; `bd/review_tasks` → `project`; `actstat` → `repo`; `t` → `time` (duration)       | 5     |
| **Closed static set**          | `research/audio` → `edition` and `research_swarm` → `audio_edition` (`brief`/`full`, **the same set in two macros**); `pr` → `status` (`draft`/…) | 3     |

What this tells us:

- **Live domains outnumber static enums about 8:1.** The biggest group is model
  strings, and they're the user's own motivating case: `#research_swarm` sends nine
  `word`-typed model strings into `%m:{{ claude_model }}`. Today a typo like
  `claude_model=opsu` is accepted at bind time. `%model` then quietly falls back to the
  default provider (`docs/llms.md`: "silently falls back to the default provider
  rather than erroring"), and five agents start on the wrong model.
- **Shared static sets do exist, but there's only one today:** the `brief|full`
  edition set, copied as prose into two macro descriptions in one plugin. It also
  shows a benefit beyond completion: `research_swarm` passes `audio_edition` into
  `#research/audio(edition=…)`, so a shared type would make **macro composition
  type-consistent**.
- Most live domains are backed by registries plugins already extend (LLM providers,
  workspace providers, task-type plugins). Plugins share those value sets
  **implicitly**: install an LLM plugin and `type: model` gains its models. No new
  plugin API is needed for that.

---

## 4. Critique of the proposal and the requirement changes I'm proposing

**Is this a good idea? Yes.** Inputs are a macro's API. Swarm macros launch 5–9 agents
per call, so catching a typo at bind time saves real money and time, and completion in
the prompt bar and editor makes macros discoverable. sase already has the hard parts:
catalogs, value-role completers, and a Rust LSP. This is mostly wiring plus one
registry.

**What I'd change:**

> **Change R1: name the feature "named input types", with enum as one kind.** The
> request treats shared value sets as enum value lists. The evidence (§3) shows most
> reusable sets are live domains, not closed lists. Named types cover both. A closed
> enum is a type whose domain is a fixed list. `model` is a type whose domain is a
> grammar plus a live catalog.

> **Change R2: `model` is a builtin domain type, not an enum reference.** Instead of
> `builtin@model_enum_values`, write `type: model`. A `model` input accepts exactly what
> the `%model` positional accepts, completes from the same catalog, and is validated by
> the same resolver. The one difference is stated in R6.

> **Change R3: builtin types use bare names. The `@` form is for plugins.**
> `builtin@model` is accepted as an alias of `model`, but authors should write
> `model`, just as they write `word`. The suffix in `model_enum_values` repeats what
> the field already says. Plugin types use the existing `<dist>@<id>` grammar.
> Config-declared types use bare names that can't shadow a builtin.

> **Change R4: enforce the "single-word" rule for enum values.** You said values are
> single words, but the current code accepts any scalar. For named types, require
> values to be non-empty with no whitespace, and lint shorthand-hostile characters
> (`, ( ) [ ] " ' `` ` ``) so `#name:value` and `#name:a,b` always work without
> quoting. Keep inline-choice gate inputs as they are, since gate labels and values
> are a separate concern.

> **Change R5: a type defines its domain; an input defines everything else.** Type
> specs hold the values with their labels and descriptions. `default`, `description`,
> `required`, and `repeatable` stay on the input. Narrowing a shared type is optional
> later work (§7.8).

> **Change R6: be strict with what the caller typed and lenient with what the author
> shipped.** For catalog-backed types like `model`:
> - A value the caller supplies explicitly fails at bind time if it doesn't resolve,
>   with "did you mean…" suggestions. This is stricter than `%model`'s silent
>   fallback, and that's on purpose.
> - A default the author shipped is only a warning in the LSP and `sase doctor`. That
>   way `research_swarm`'s `muse/…` default doesn't break the macro on a machine
>   without muse when `muse=false`.

> **Change R7: fix §2 before adding features.** Otherwise named types will inherit
> the YAML divergence and the silent `line` fallback.

---

## 5. Design options considered

| Option | Syntax | Pros | Cons | Verdict |
| ------ | ------ | ---- | ---- | ------- |
| **A. Your sketch** | `type: enum` + `choices: builtin@model_enum_values` (or `type: builtin@model_enum_values`) | Reuses the familiar `@` provider grammar | Forces model into a closed list; `choices` becomes polymorphic (list or ref); redundant suffix; `builtin@` noise on every builtin | ❌ |
| **B. `choices:` as a reference** | `type: enum`, `choices: {use: builtin@effort}` | `type: enum` keeps meaning "closed set" | Verbose; can't express grammar types like `model`; awkward in shortform | ❌ |
| **C. Named types (recommended)** | `type: model` · `type: effort` · `type: deploy_env` · `type: sase-research-artifacts@audio_edition` | Reads like a programming language (`enum Effort` → `x: Effort`); works in shortform (`model: model`); one concept covers enums and domains; matches directive roles | Needs a registry and resolution rules (below) | ✅ |
| **D. `use:` on the input** | `model: {use: builtin@model, default: "@large"}` | Matches config `use:` + deep-merge | "Merge my input with a type" is confusing for authors; inputs aren't provider instances | ❌ for authoring; keep `use:` for config overriding a plugin type (Phase 4) |
| **E. Types defined as macros** | a `#types/edition` macro file | Free discovery and LSP indexing | Mixes up two concepts; macro shadowing rules are wrong for types | ❌ |
| **F. Dynamic plugin value providers now** | hook returns values at completion time | Most general | LSP is Rust, so plugin callbacks need a bridge; no corpus yet (`decisions:corpus-before-mechanism`, by analogy) | ⏸ defer |

Free, within one file: standard YAML anchors (`choices: &editions [brief, full]` …
`choices: *editions`) already allow reuse in a single macro file. PyYAML supports them;
check `serde_yaml` parity before documenting it.

---

## 6. Recommended design

### 6.1 Authoring syntax

```yaml
---
name: deploy
input:
  # Anonymous enum (exists today; now with completion and per-choice docs)
  env:
    type: enum
    choices:
      - { value: staging, description: Pre-prod cluster }
      - { value: prod, label: Production, description: Customer traffic }
    default: staging

  # Builtin domain types: same domain, completion, and validation as the directive
  model: { type: model, default: "@large" }      # ≡ what %model accepts
  effort: { type: effort, default: high }        # ≡ what %effort accepts

  # Config-declared named enum (sase.yml → input_types.region)
  region: region

  # Plugin-declared named enum (qualified, never ambiguous)
  edition: { type: sase-research-artifacts@audio_edition, default: brief }
---
```

Before and after for the real-world example:

```yaml
# before (sase-research-artifacts research_swarm.md)
- name: claude_model
  type: word
  default: "claude/opus@xhigh"
- name: audio_edition
  type: word
  default: brief
  description: Narration edition … (`brief` … or `full` …)

# after
- name: claude_model
  type: model
  default: "claude/opus@xhigh"
- name: audio_edition
  type: sase-research-artifacts@audio_edition   # same type as #research/audio's `edition`
  default: brief
```

### 6.2 The type registry

One registry, keyed by canonical id, with three kinds:

| Kind       | Domain                                      | Validation                                       | Completion source                     | Who can declare |
| ---------- | ------------------------------------------- | ------------------------------------------------ | ------------------------------------- | --------------- |
| `scalar`   | word, line, text, path, int, float, bool, code | today's rules                                    | bool→choices; path→files              | builtin only    |
| `enum`     | fixed ordered list of `{value, label?, description?}` | exact membership (canonical spelling)            | the list                              | inline, builtin, config, plugin |
| `domain`   | live catalog and/or grammar                 | per-domain resolver (see §6.3)                   | an existing directive value-role completer | builtin only (v1) |

**Name resolution:**

1. `type: <bare>` resolves to a builtin (reserved, can't be shadowed). If there's no
   builtin, it resolves to a config-declared type (user and project config,
   deep-merged).
2. `type: builtin@<id>` is the same as the bare builtin.
3. `type: <dist>@<id>` resolves to a plugin-declared type, parsed with
   `parse_plugin_qualified_id`. Plugin types are **never** reachable by bare name.
   That keeps a macro's meaning from changing when someone installs an unrelated
   plugin that happens to define `region` too.
4. If nothing matches, it's an **error** naming the closest known types. This replaces
   the silent `line` fallback (§2.3). It changes behavior users can see, so follow
   `sase/memory/sase_flags.md` for the rollout. Accept `string` as a deprecated alias
   of `line`, because both schemas advertise it.

### 6.3 Builtin types

The guiding rule: **every directive value role that is a real value domain gets a
macro input type with the same meaning.** Directives and macros then share one
vocabulary, and the model catalog, agent snapshot, and machine catalog serve both.

| Type | Mirrors | Kind | Explicit-value validation | Notes |
| ---- | ------- | ---- | ------------------------- | ----- |
| `agent` | `%wait:` (`DirectiveValueRole::Agent`) | domain | today: word rules | already exists |
| `model` | `%model:` positional (`::Model`) | domain | **resolve through the same Python resolver as `%model`**: `@alias[@effort]`, `provider/model[@effort]`, nested provider paths, and bare known models pass. An unknown `@alias` fails (as `%model` does). An unknown bare token **fails with suggestions** (R6). An unknown model under a known provider passes with a warning, because new models ship before catalogs update. | Selectors (`\|`, `\|\|`) aren't `%model` grammar, so reject them |
| `effort` | `%effort:` | enum | membership in `EFFORT_LEVELS_ORDERED` (`src/sase/macro/effort.py:20`) | the single source of truth already exists |
| `bead` | `%id(bead=)` (`::Bead`) | domain | syntax only (beads may belong to other projects) | Phase 4 |
| `tribe`, `machine`, `tab`, `duration` | `#tribe`, `%dispatch`, `%tab`, `%wait(time=)` | domain | per role | Phase 4, add as the corpus asks |
| `task_type` | `-T 'task(<slug>)'` | domain (closed, dynamic) | membership in the live task-type catalog | Phase 4 |

### 6.4 Declaring shared closed enums

**Spec shape (one Rust wire, `InputTypeSpecWire`, `schema_version: 1`):**

```yaml
id: audio_edition            # [a-z0-9][a-z0-9_-]*
label: Audio edition         # optional display name
description: Narration length for sase-listen guide-backed editions.
choices:                     # ordered; each value obeys R4
  - { value: brief, description: About 4 minutes (default) }
  - { value: full,  description: About 16 minutes }
```

**Where specs can be declared:**

- **Config (Phase 3):** a top-level `input_types:` map in user and project `sase.yml`,
  keyed by id (the `id` field is implied by the key). I'm calling it `input_types`
  rather than `macro_types` because gate inputs already share `InputType` and
  `InputChoice` (`notification_gates/model_inputs.py`), so the registry isn't
  macro-specific, even though v1 only wires macros. A plugin's `default_config.yml`
  should **not** declare `input_types`: the deep-merge loses provenance and would let
  two plugins collide silently. A doctor check enforces this.
- **Plugins (Phase 4, once a second plugin needs one):** an `sase_input_types`
  entry-point group with an `input_type_specs()` hook, mirroring `sase_task_types` and
  `task_type_specs()` exactly: validated in Rust, discovered by Python, qualified as
  `<dist>@<id>`, duplicates reported as diagnostics rather than taking precedence, and
  a `sase doctor -C macros.input_types` check. Static lists only in v1.

### 6.5 Completion and editor experience (the payoff)

**Prompt bar (TUI):**

- `#deploy:` immediately opens a menu of `staging · prod`. Each row shows the label,
  and the description appears in the subtitle. `#deploy(env=pr` filters to `prod`.
  Fuzzy matching and ordering come from the shared Rust filter.
- `type: model` uses the exact `%model` menu (provider grouping, alias chips, effort,
  advisories, pool counts). Today `_offers_model_values`
  (`directive_completion.py:222`) only fires for `directive_name == "model"`. Refactor
  it to key off the value role so macro-argument contexts can call it.
- **Context precedence:** inside an argument typed `model`, `@` must open the model
  alias menu, not the artifact-reference `@` menu. A typed argument should always
  beat a generic trigger character.
- `bool` moves onto the generic choices path (`true|false`), which removes
  `_build_bool_completion_candidates` and the LSP's `bool_completion_list`.
- Signatures: `#deploy(env: staging|prod, model: model)`. Show enums with four or fewer
  values inline; otherwise show the type name.

**LSP (any editor):**

- Completion: the same candidates, from the same Rust filter.
- Hover over an argument: the type name, its provenance (for example
  `sase-research-artifacts@audio_edition`), and a table of choices with descriptions.
- Diagnostics in prompt text: `#deploy:prdo` → *"`env` expects `staging | prod`; got
  `prdo`"*, plus a **"Replace with `prod`" code action**.
- Frontmatter diagnostics: unknown type (with suggestions), duplicate or non-word
  values, a default outside the domain, and a plugin type that isn't installed. That
  last one is a warning, since the macro still loads and validation just weakens to
  `word`.

**Launch forms and mobile:** the cycle button is fine for 2–5 choices. Above that, and
for any domain type, use a picker; `model` reuses the existing model picker. Add
`domain` to `MobileXpromptInputWire` so the mobile app can show the right picker.

### 6.6 Architecture and the Rust boundary

By the boundary litmus test, validation, resolution, and completion filtering of input
values are core behavior: the TUI, the LSP, and mobile must agree.

**Rust (`sase_core`) owns:**

- `InputTypeSpecWire` and its validation (ids, values, duplicates, R4).
- A **single input-declaration parser** that the Python loader also calls through a
  binding. This retires `loader_parsing.py`'s longform/shortform input code,
  `workflow_loader_parse.py`'s copy, and lets the two Rust copies converge. It fixes
  §2.1–§2.4 at the root: YAML 1.2 scalar handling everywhere, one type vocabulary, and
  generated JSON-schema enum lists.
- Type resolution (`bare` → `builtin` → `config`; `<dist>@<id>` → plugin) against a
  registry snapshot passed in as wire data.
- Enum membership checks and "did you mean" suggestions.
- `input_type → DirectiveValueRole` mapping, so completion contexts become
  `MacroArgumentChoices` or `MacroArgumentRole(role)` instead of
  `Value`/`Agent`/`TypeHint`.
- Wire additions, all additive: `MacroInputHint.choices` and `MacroInputHint.domain`
  in `editor/wire.rs:394` and the Python mirror (`_macro_arg_assist_models.py:12`),
  `InputChoice.description`, and `MobileXpromptInputWire.domain`.

**Python owns:**

- Discovering config `input_types` and (later) plugin hooks.
- The `model` resolver. Model-alias resolution and the LLM plugin registry are
  Python-side today, and the `%model` path already calls them.
- Writing an **`input_type_catalog.json`** for the LSP, next to
  `model_catalog.json`, through a new `_materialize_input_type_catalog` in
  `integrations/macro_lsp.py`. It's best-effort and re-read on each request, like the
  other catalogs.

**Value representation:** `InputArg.type` stays the base scalar kind. Enums and model
values are words. Add `InputArg.type_ref: str | None`, holding the canonical type id,
for provenance and domain dispatch. Keep `InputType.AGENT` for compatibility, but treat
it as `WORD` + `builtin@agent` internally.

---

## 7. Phased plan

| Phase | Scope | Why this order |
| ----- | ----- | -------------- |
| **0. Correctness** | Fix the YAML scalar parity (stopgap: reject bool/float choice scalars with "quote it"; real fix: the Rust parser in Phase 1). Make longform workflow inputs read `choices`. Turn unknown types into a diagnostic (with a flag-gated rollout per `sase_flags.md`, and `string` → `line` as a deprecated alias). Generate or fix both JSON schemas (`enum`, `agent`, `code`, `choices`). | Named types would inherit every one of these bugs |
| **1. Enum completion everywhere** | `MacroInputHint.choices`/`domain`. A generic choices completion path in the TUI and LSP, with `bool` folded in. Hover, prompt-text diagnostics with a quick fix, `InputChoice.description`, and inline enum signatures. Move input-declaration parsing into Rust. | This is the payoff you asked for, using only features that already exist |
| **2. Builtin `model` + `effort`** | A role-keyed completer refactor, the `model` resolver with R6 strictness, and the `effort` enum. Migrate `research_swarm`'s nine model inputs and `pr.status`. | The highest-value item in the corpus |
| **3. Config `input_types`** | Spec wire, config schema, registry snapshot, LSP catalog file, and a doctor check. Document it in `docs/macros.md` and `docs/configuration.md`. | Lets users share sets across their own macros |
| **4. Plugin types and more domains** | `sase_input_types` + `input_type_specs()` (first user: `sase-research-artifacts@audio_edition`). `use:` overrides from config, like task types. `bead`/`tribe`/`machine`/`task_type`/`duration` domains as macros need them. | Build each mechanism only when something needs it |
| **5. Optional** | Narrowing with `choices` on a named type (§7.8), per-choice `aliases` that canonicalize at bind time, and wiring named types into gate inputs. | Nice-to-have |

### 7.8 Optional: narrowing

For any word-like type, `choices` could mean "restrict to this subset":
`{type: effort, choices: [low, medium, high]}`, or for model,
`{type: model, choices: ["@small", "@large"]}`, where each choice is validated against
the base type. It's orthogonal and backward compatible, since `choices` on non-enum
types is an error today. I'm deferring it because no macro in the corpus needs it yet.

---

## 8. Risks and open questions

- **Validation depends on the machine.** A `model` value that resolves on one host may
  fail on another, and with `%dispatch` the expanding host and the running host can
  differ. R6 limits the damage, but error messages should name the machine whose
  catalog rejected the value. **Open question:** should bind-time validation of
  `model` be skipped for `%dispatch` launches and left to the remote launch?
- **The LSP catalog goes stale.** It's written once at LSP startup, the same trade-off
  `model_catalog.json` already makes. Document it.
- **Behavior changes:** the stricter unknown-type check and the YAML 1.2 switch could
  change how `default: yes/no/on/off` loads on non-bool inputs. Phase 0 needs a corpus
  scan and doctor warnings first.
- **Scope creep:** gates and task types have their own enum fields. Keep the registry
  domain-neutral (hence `input_types`), but only wire macros in v1.
- **CLI:** a read-only `sase macro type list|show` would help discovery. Read
  `sase/memory/cli_rules.md` before proposing it. A doctor check alone may be enough.

---

## 9. Recommended solution

Build **named input types**, not a separate shared-enum mechanism:

1. **Keep** `type: enum` + inline `choices` as anonymous enums. Add per-choice
   `description`, and enforce single-word values for new named types.
2. **Add builtin types named after the directives they mirror**, starting with
   `type: model` (exactly what `%model` accepts, validated by the same resolver, but
   failing on unknown bare tokens instead of silently falling back) and
   `type: effort`. Builtin names are bare; `builtin@model` is an accepted alias, not
   the spelling to recommend.
3. **Let users share closed enums** through `input_types:` in `sase.yml`, referenced by
   bare name. Later, let plugins declare them through a task-type-style
   `input_type_specs()` hook, referenced only as `<dist>@<id>` using the existing
   `plugins/qualified_id.py` grammar.
4. **Make completion the centerpiece.** The prompt bar and the LSP both complete enum
   and domain values through the existing directive value-role completers and the
   shared Rust filter, with hover docs, "did you mean" diagnostics, and quick fixes.
5. **Put the logic in sase-core.** One Rust input-declaration parser and type resolver
   for Python, the LSP, and mobile. That fixes the YAML divergence, the dropped
   `choices`, the silent `line` fallback, and the five-way type-list drift.
6. **Ship in this order:** correctness fixes → enum completion → `model`/`effort` →
   config enums → plugin enums (when a second plugin needs them).

The result is a single idea authors can learn in one sentence: _a macro input's
`type` names a value domain, and anything a directive accepts can be a type._ It also
directly fixes the most expensive failure in the current corpus: a mistyped model in
a swarm macro that silently launches several agents on the wrong provider.
