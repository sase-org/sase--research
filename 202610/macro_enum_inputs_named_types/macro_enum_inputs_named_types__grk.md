# Enum Macro Inputs: Finish the Type, Share Catalogs by Name

**Date:** 2026-10-04 · **Researcher:** grk · **Status:** independent design research

> **Verdict: do it, but do not add a new input type.** `enum` already parses, validates,
> and ships in docs, gates, and the typed-input form. The missing product is
> *completion plus shared vocabularies*. Treat inline `choices:` as the closed
> word-subtype it already is, thread those choices through every assist wire that
> currently drops them, and add a `catalog:` field for reusable named sets. Name
> catalogs `model` and `effort`, not `builtin@model_enum_values`. Keep `%model`
> open-with-fallback; a macro input that opts into `catalog: model` is closed.

---

## 1. The Question

The request is to add an `enum` macro input type so authors can constrain a parameter
to a declared set of single-word strings, complete those values in sase's TUI prompt
widget and in external editors via the macro LSP, and reuse the same value set across
macros, plugins, and sase itself — the motivating example being "this input only
accepts a model string `%model` would accept."

This report answers four things:

1. Is that a good idea?
2. What already exists, and where does it stop?
3. What should change in the requirements?
4. What is the recommended design, including naming?

---

## 2. Critique of the Plan

The plan is right about the product and wrong about the shape of the work.

**The product is good.** Prompt authors already write `#pr(status=draft)` and
`#mentor(kind=…)` as free `word`s. A closed word-set with completion is the natural
next type. It matches how people already experience enums in VS Code `launch.json`,
GitHub Actions `runs-on`, argparse `choices=`, and Click `Choice`. It is also the
right type for gates: custom gates already collect `InputType.ENUM` with the same
`InputChoice` model.

**It is not a new type.** `InputType.ENUM = "enum"` is live in
`src/sase/macro/models.py`. Loader, frontmatter LSP, docs (`docs/macros.md` § Enum
Choices), the typed-input form's `_EnumField` cycle button, gate input collection, and
`sase macro show` JSON all know it. Memory `macros.md` is the stale surface: it still
lists `word/line/text/path/int/bool/float` and omits `enum`, `agent`, and `code`.

**The motivating syntax is the weak part.** `type: builtin@model_enum_values` (or
`choices: builtin@model_enum_values`) overloads three namespaces at once:

- Input *types* (`word`, `enum`, `agent`)
- Worker *provider refs* (`builtin@commit`, `builtin@plan`, `plugin@hook-id`)
- Insertable *values* that already contain `@` (`@large`, `opus@high`)

Putting a provider-ref in the type slot teaches authors that catalogs are types.
Putting it in `choices` collides with real enum values. The `_enum_values` suffix is
noise: the catalog *is* the values.

**`%model` is a poor closed-enum prototype.** Unrecognized model names currently fall
back to the default provider and log a warning (`docs/llms.md`, Automatic Provider
Resolution). A true enum rejects unknown values. Reusing the model *completion catalog*
as an enum vocabulary is excellent. Cloning `%model`'s acceptance policy into enum
validation would make "enum" mean "suggestion list," which authors will not trust.

**Do not add `type: model` next to `type: agent`.** `agent` and `path` earn special
types because their pickers are structured (status/kind/tribes; filesystem). `model`
and `effort` are flat word lists. A catalog registry lets plugins add `github.pr_status`
without growing `InputType`. Special types are a trap: every new vocabulary becomes a
core enum variant, a TUI completion kind, an LSP context kind, and a docs row.

**Sharing does not need a new `sase_enums` entry-point group on day one.** File-hook
and artifact-ref providers are *workers* (`use: plugin@id`). Enum catalogs are *data*.
Plugin `default_config.yml` already merges into user/project config. Static plugin
vocabularies belong there. The only live catalog that must be code-backed today is
`model`, and sase already owns that pipeline.

---

## 3. Adjustments to the Requirements

These are deliberate changes to the request. Each is called out as such.

1. **Do not add `InputType.ENUM`.** It exists. The requirement is: make enum values
   completable, diagnosable, and shareable.
2. **Enforce word-shape on choice *values*.** Today a choice may be any YAML scalar
   stringified, including whitespace. The request said enums are a subtype of `word`.
   That should be a load-time error, so `#foo:bar` never needs quoting. Labels may
   contain spaces; values may not. Hyphens, dots, slashes, `+`, and `@` stay legal
   (`gpt-5.4`, `codex/g`, `@large`).
3. **Keep matching case-sensitive and value-only.** Tests already lock this
   (`test_input_arg_enum_is_case_sensitive_and_ignores_labels`). Do not copy bool's
   `true/1/yes/on` folding. Labels are display-only.
4. **Catalog refs live in `catalog:`, never in `type:` and never as a scalar
   `choices:`.** `choices:` remains a non-empty list. `catalog:` is a namespaced id.
   Exactly one of the two is required for `type: enum`. Both, or neither, is an error.
5. **Name catalogs after the vocabulary, with a dotted owner when needed.** Builtin:
   `model`, `effort`, `pr_status`. Plugin: `github.pr_status`. Do not use
   `builtin@model_enum_values`. The optional fully-qualified builtin form is
   `builtin.model` for disambiguation, not `builtin@model`.
6. **`catalog: model` is closed.** It accepts the same *insertable* strings the
   `%model` completion catalog would insert (canonical names, `@` aliases,
   `provider/model`). It rejects unknown strings. `%model` itself stays open. Document
   that difference in one sentence wherever `catalog: model` is introduced.
7. **Do not mix a catalog with extra inline values in v1.** No
   `catalog: model` plus `choices: [my-local-model]`. If a project needs a subset or
   extension, it defines its own catalog that shadows or sits beside the builtin.
8. **Do not make `agent` or `path` catalogs.** They keep their special types and
   engines. `bool` stays a type because of aliases. `code` stays a gated structured
   type.
9. **Reuse the bool completion kind, generalized.** Do not add `macro_arg_enum` as a
   third TUI/LSP kind until a catalog needs a structured picker. Small static enums
   are `macro_arg_value` with the input's choices instead of `true`/`false`. `model`
   is the one catalog that should reuse the existing model-completion engine
   (provider prefixes, alias rows, details) rather than a flat prefix list.
10. **Static sharing goes through config, not a new plugin group.** Add
    `enums:` to config (plugin defaults → user → project, first-wins on id, same
    spirit as macro discovery). Add a `sase_enums` pluggy group only if a plugin must
    *generate* a live list. GitHub PR statuses are static (`draft`, `ready`, …) and
    do not need a hook.
11. **Bake static catalogs at load; re-resolve live catalogs at completion and
    launch.** `InputArg` keeps `choices` as the snapshot used by validation, show,
    and assist. An optional `catalog` field records origin for live refresh and for
    "unknown catalog" diagnostics. Empty live catalogs offer no rows and reject every
    value; they do not make `type: enum` illegal at load.
12. **Update the stale JSON Schema.** `src/sase/macros/workflow.schema.json` still
    lists `word|line|text|path|agent|int|float|bool|string` and has no `choices`.
    Yamlls and nvim's schema helper will lie until this moves with the feature.

---

## 4. What Already Exists

### 4.1 The type is real

| Layer | Enum support today |
| ----- | ------------------ |
| `InputType` / `InputChoice` / `InputArg` | Full: required non-empty unique choices, exact-value validate |
| Markdown/YAML loader | Shortform and longform; scalar or `{value, label}` |
| Rust frontmatter engine | Same rules; diagnostics `invalid_xprompt_frontmatter_input_choices` |
| Docs `docs/macros.md` | Documented with examples |
| Memory `macros.md` | **Omits enum** |
| Workflow JSON Schema | **Omits enum and choices** |
| Gates / mobile gate wire | Full, including `MobileInputChoiceWire` |
| Typed input form | Cycle button over values, labels for display |
| `sase macro show` | `ShowInput.choices` projected from `InputArg` |
| Jinja hover | Reads `choices:` from the file's own YAML |

### 4.2 Assist surfaces drop the payload

This is the actual bug, not a missing type.

- TUI `MacroInputHint` has `name, type, required, default, position, repeatable,
  description` and **no `choices`**.
- `input_hint_from_input_arg` never copies `InputArg.choices`.
- `StructuredCatalogInput` (mobile + LSP catalog builder) never copies them.
- `_mobile_helper_catalog.py` serializes inputs without a `choices` key.
- Rust `MobileXpromptInputWire` *has* `choices: Vec<MobileInputChoiceWire>`, but
  `assist_entries_from_catalog` maps that wire into `MacroInputHint` and **drops
  `choices`**.
- TUI `_completion_kind_for_input` and Rust `completion_kind_for_input` map
  `path` → path picker, `bool` → value list, `agent` → agent picker, **everything
  else → type hint**. `enum` falls through to a no-op.
- LSP `CompletionContextKind::MacroArgumentValue` always calls
  `bool_completion_list()`.
- LSP `value_matches_input_type` treats unknown types as valid (`_ => true`), so an
  enum argument `turbo` against `choices: [fast, slow]` produces **no diagnostic**.

Net: an author can declare `type: enum` and get a launch-time
`MacroValidationError`, a cycle button in the collection modal, and silence in the
prompt bar and in nvim.

### 4.3 Precedents for "word plus a catalog"

SASE already has three patterns. Enum should steal from all three, not invent a
fourth.

**Special types with engines:** `agent` and `path`. Structured pickers, live data,
their own completion kinds. Keep these. Do not fold them into enum.

**Directive vocabularies:** `%effort` uses `EFFORT_LEVELS_ORDERED` in
`src/sase/macro/effort.py`. `%model` uses `build_model_completion_catalog()`, a
Python-owned list materialized as JSON for the Rust LSP (schema v1, live overlay in
the TUI, launch-time snapshot for editors). That materialization path is the
template for `catalog: model`.

**Reusable plugin data via `plugin@id`:** file hooks and artifact refs. Those ids
name *providers that do work*. Reusing that sigil for a list of strings looks
consistent and is the wrong kind of object. Keep `plugin@id` for workers.

### 4.4 nvim is not a second implementation

`sase-nvim` is an LSP client (`lua/sase/lsp.lua`) plus a macro name picker. Argument
value completion, hover, and diagnostics come from `sase lsp` / `sase-macro-lsp`.
Fixing the Rust assist engine and the catalog wire is the nvim work. Do not add a
parallel enum completer in Lua.

### 4.5 Concrete first consumers

`#pr`'s `status` input is `type: word` with default `"draft"`
(`src/sase/macros/pr.yml`). That is an enum that has not admitted it yet
(`draft`, `ready`, and whatever `SASE_PR_STATUS` actually honors). `#tribe` is a
word that might stay a word (open set). Effort and model are the shared builtins
the request asked for.

---

## 5. Recommended Design

### 5.1 Authoring

```yaml
input:
  mode:
    type: enum
    choices: [fast, slow]
    default: fast
  environment:
    type: enum
    choices:
      - { value: staging, label: Staging }
      - { value: prod, label: Production }
  model:
    type: enum
    catalog: model
  effort:
    type: enum
    catalog: effort
    default: medium
  status:
    type: enum
    catalog: github.pr_status
    default: draft
```

Rules:

- `type: enum` requires exactly one of `choices` (non-empty list) or `catalog`
  (dotted id).
- Each choice value is a non-empty word: no Unicode whitespace, no empty string.
- Duplicate values error. Labels are optional, unique-not-required, never
  inserted, never matched.
- `default` must be a member of the *resolved* value set (already true for inline
  choices; extend the check to catalogs).
- Repeatable enums are allowed as the final positional input; each element is
  membership-checked independently, same as repeatable `word`.

Frontmatter LSP already knows `choices`. Add `catalog` as a legal input field,
complete catalog ids from the registry, and diagnose unknown ids the way unknown
input types are diagnosed.

### 5.2 Catalog identity

A catalog id is a dotted name:

```
<id>            := <segment>(.<segment>)*
<segment>       := [a-z][a-z0-9_]*
```

Resolution, first match wins, mirroring macros:

1. Project config `enums:` (and later `sase/enums/*.yml` if file-shaped catalogs
   prove useful; do not add the directory in v1)
2. User config `~/sase/sase.yml` / `~/.config/sase/sase.yml` `enums:`
3. Plugin `sase_config` default_config.yml `enums:`
4. Builtin registry (`model`, `effort`, `pr_status`, …)

A project catalog named `model` shadows the builtin. That is a feature, the same
way a project macro named `commit` shadows the builtin. `builtin.model` is reserved
as an explicit handle that never shadows.

**Why not `builtin@model`:** `@` is already (1) artifact refs, (2) size aliases,
(3) provider refs, (4) effort suffixes on model strings. A catalog id that uses `@`
cannot be taught in one sentence. Dotted names match Python packaging, config keys,
and `sase plugin show github`.

**Why not a new input type per catalog:** plugins cannot ship `type: pr_status`
without a sase-core release. They *can* ship `enums.github.pr_status` in
`default_config.yml` tomorrow.

### 5.3 Catalog kinds

Two kinds. Only two.

**Static.** A YAML list of `{value, label?}` (label optional). Frozen at process
start / config token, baked into `InputArg.choices` at macro load. Effort,
PR status, commit method, user-defined environment names. This is 95% of catalogs.

**Live.** A code-backed generator that returns the same wire shape the model
completion catalog already uses: `value`, `display`, `description`, plus optional
grouping fields. v1 ships exactly one: `model`. The TUI re-resolves on the same
config token / live overlay `%model` already uses. The LSP gets the existing
launch-time snapshot. Validation at *launch* uses the live set, not the set from
when the `.md` file was saved.

A live catalog may carry `engine: model` meaning "run the model completion
builder, not the flat prefix filter." No general engine plugin in v1.

### 5.4 Config shape

```yaml
enums:
  environment:
    description: Deployment target
    choices:
      - staging
      - { value: prod, label: Production }
  github.pr_status:
    description: Pull request status honored by #pr
    choices: [draft, ready]
```

Builtin live catalogs do not appear in YAML; they are registered in code next to
`EFFORT_LEVELS_ORDERED` and `build_model_completion_catalog()`. Builtin *static*
catalogs can live as YAML next to `src/sase/llm_provider/models.yml` or as Python
tuples; YAML is easier to share with plugins and with the frontmatter completer.

Unknown keys under a catalog entry fail config validation. A catalog whose
resolved choices violate word-shape fails at the catalog, not at each consumer.

### 5.5 Assist and diagnostics

Once `choices` ride on `MacroInputHint`:

1. `_completion_kind_for_input("enum")` returns `macro_arg_value` (TUI and Rust).
2. `build_macro_arg_completion_candidates` / LSP `MacroArgumentValue` prefix-filter
   `input.choices` when the active input is enum; keep `true`/`false` for bool.
   Display = `label or value`; insertion = `value`; detail = type or label.
3. `value_matches_input_type` for `enum` is membership in `input.choices`.
   Unresolvable values (`{{`, `$(`, artifact refs, placeholders) stay skipped, same
   as today.
4. Hover and the argument hint footer list the values, truncated with a count
   (`fast | slow | thorough · 12 more`) so a 200-row model catalog does not explode
   the prompt chrome.
5. `format_inputs` may keep `(model: enum)` in the compact signature; show/catalog
   rich surfaces print the catalog id or the first few values.
6. For `catalog: model`, the value slot delegates to the existing model completion
   builder (provider drill-down, alias rows, advisory markers). Insertion is still a
   single word. Do not invent a second model picker.

Parity rule: the TUI prompt bar, `sase lsp`, and the helper-bridge path consume the
same Rust completion function. nvim comes along.

### 5.6 Where the logic lives (rust-core boundary)

Shared backend behavior belongs in `sase-core` (`AGENTS.md` rust_core_backend_boundary,
`docs/rust_backend.md`):

- Frontmatter: `catalog` XOR `choices`, word-shape, unknown catalog id
- Assist: choices on `MacroInputHint`, enum membership, enum value completion
- Call diagnostics: `invalid_xprompt_arg_type` for a non-member

Python owns:

- Catalog registry and config merge
- Live `model` generation (already)
- Baking static catalogs into `InputArg` at load
- Materializing catalog ids + baked choices into the LSP/mobile catalog payload
  (fill the `choices` field that the wire already has)
- TUI live overlay for `catalog: model`

Pin `sase-core-revision.txt` past the core commit before sase callers land.

### 5.7 What this is not

- Not a JSON Schema `$ref` / `$defs` system. Macro YAML should stay a one-screen
  language.
- Not OpenAPI `components.schemas`. Too much ceremony for five effort levels.
- Not GraphQL enums with descriptions-as-API. Labels are enough.
- Not "complete from a list but accept anything." That is `type: word` plus a
  future optional `suggest:` field. If someone needs that, it is a different
  feature. Enum means closed.
- Not changing `%model` to fail closed.
- Not a new completion kind per catalog.
- Not nvim-specific protocol.

---

## 6. Alternatives Considered

| Approach | Why it loses |
| -------- | ------------ |
| New `InputType` values (`model`, `effort`, `pr_status`) | Core churn per vocabulary; plugins cannot add types |
| `type: builtin@model_enum_values` | Provider-ref in the type slot; `@` collision; ugly |
| Scalar `choices: builtin@model` | `@large` is a legal value; YAML cannot tell ref from value |
| `choices: $model` | New sigil, fights Jinja and shell instincts |
| `sase_enums` pluggy group in v1 | Static data already has a merge path; no live plugin catalog yet |
| Completion-only, no launch validation | Authors will not trust a type that the runner ignores |
| Bake live catalogs at file load only | Stale model lists after `sase plugin install` / alias edits |
| Fold `agent` into `catalog: agent` | Loses the structured picker; tribes/status grouping is not a flat enum |
| Case-insensitive enum match | Breaks `Prod` vs `prod` as distinct ops values; disagrees with existing tests |

The closest external analog for *named reusable closed sets* is JSON Schema
`$defs` plus `enum`. The closest analog for *editor UX* is VS Code completing
schema enums. The closest analog *inside SASE* is `%effort`'s frozen tuple plus
`%model`'s materialized catalog. The design is those two, exposed to macro
inputs through one field.

---

## 7. Implementation Sketch (for the eventual plan, not this report)

Phased so each slice is shippable.

**Phase A — Honor the choices we already parse.** Add `choices` to TUI
`MacroInputHint`, `StructuredCatalogInput`, the mobile catalog JSON, and Rust
`MacroInputHint`. Stop dropping them in `assist_entries_from_catalog` and
`_macro_input_hint_to_wire`. Map `enum` → `macro_arg_value`. Complete and
validate membership. Enforce word-shape on values. Update
`workflow.schema.json` and memory `macros.md`. Convert `#pr` `status` to an
inline enum as the first dogfood. This phase alone makes the type real in the
prompt bar and in nvim.

**Phase B — Named static catalogs.** `catalog:` field, config `enums:`, builtin
`effort` and `pr_status`, frontmatter completion of catalog ids, load-time bake,
unknown-catalog diagnostics. Plugins contribute through `sase_config`.

**Phase C — Live `model`.** `catalog: model` delegates to the existing model
completion catalog. Launch validation is closed against that catalog. TUI uses
the live overlay; LSP uses the launch snapshot. Document the `%model` fallback
difference.

Do not gate Phase A on C. Most enums people will write are five-value static
lists. Model-sharing is the headline example, not the first slice.

Tests that must exist before calling it done:

- Loader: word-shape rejection, catalog XOR choices, unknown catalog
- Launch: membership, repeatable enum, default not in catalog
- TUI: prefix-complete enum values, labels in the menu, insertion of values
- LSP: same, plus `invalid_xprompt_arg_type` for a non-member
- Catalog wire: mobile/LSP payload includes choices (today it does not)
- `#pr:ready` still works after `status` becomes enum
- `catalog: model` accepts `@large` and `codex/g`, rejects `not-a-model`
- `%model:not-a-model` still warns and launches (no accidental coupling)

---

## 8. Risks and Limits

- **Large catalogs in chrome.** A model list in the argument hint footer will
  overflow. Truncate; let Ctrl+T / completion own the full set.
- **Hidden models.** `fakey` is hidden from pickers but still a legal `%model`
  value. Closed `catalog: model` should follow the *completion* catalog (hidden
  omitted) or the *resolution* catalog (hidden included). Recommend: match the
  completion catalog, and keep a `Custom…`-equivalent out of enum (enum has no
  custom). Authors who need fakey type it into `%model`, not into a closed
  macro input.
- **Shadowing.** A project `enums.model` that is a two-value list will surprise
  anyone who expected the LLM catalog. Show the catalog source in hover
  (`catalog: model · project`).
- **Stale LSP snapshots.** Same as today's model shortcuts: restart the LSP
  after plugin/config changes. Do not build a second live channel for editors
  in v1.
- **Label/value confusion.** Display labels in the menu, insert values. Never
  accept a label as input. Tests already specify this; keep them.
- **Schema drift.** `workflow.schema.json` is already behind `enum`/`code`. If
  Phase A forgets it, yamlls will red-squiggle valid macros.

---

## 9. Is This a Good Idea?

Yes. Closed word-sets with completion are how every serious prompt language
grows up, and SASE has already paid for the type. The current hole — parse and
validate, then forget the values on every interactive surface — is the kind of
gap users feel as "enums don't work." Sharing via named catalogs is the part
that makes plugins and `#pr` and `%model` the same story.

The approach I would *not* take is a new type, a provider-ref in the type slot,
or a pluggy group for static lists. The approach I would take is: finish the
wire, then add `catalog:`, then plug `model` in as the one live catalog.

---

## 10. Recommended Solution

1. Keep `type: enum` with inline `choices:` as the closed word-subtype of
   `word`.
2. Thread `choices` through TUI hints, structured/mobile/LSP catalog wire, and
   Rust `MacroInputHint`. Complete and diagnose them with the existing
   `macro_arg_value` kind.
3. Add `catalog:` as the reuse mechanism. Ids are dotted names (`model`,
   `effort`, `github.pr_status`), resolved first-wins through project config,
   user config, plugin config, then builtins. `builtin.model` never shadows.
4. Ship builtin catalogs `effort` (static, from `EFFORT_LEVELS_ORDERED`) and
   `model` (live, from the existing model completion catalog, closed at the
   macro boundary). Convert `#pr` `status` to enum as dogfood.
5. Reject `builtin@model_enum_values` as a type or as a choices scalar. Reject
   `type: model`. Reject a new `sase_enums` group until a plugin needs a live
   generator.
6. Implement in three slices: honor inline choices everywhere, then named
   static catalogs, then live `model`. Each slice is user-visible without the
   next.

That is the design I would implement: intuitive (`type: enum` plus either a
list or a name), reliable (one membership check, one wire, rust-core shared
with the LSP), and beautiful (short ids, labels in the menu, values in the
prompt, no `@` in a third namespace).
