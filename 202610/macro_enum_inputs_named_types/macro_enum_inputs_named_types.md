# Macro Enum Inputs: Finish the Enum, Add Named Input Types, Make Completion the Payoff

> **Research query:** What is the best way to add an `enum` macro input type, whose
> inputs declare an allowed set of single-word values (a sub-type of `word`), so macro
> inputs get customizable completion in the prompt input widget and in external editors
> via LSP? How should sase and plugin providers share reusable value sets, such as one
> limiting an input to the model strings `%model` accepts (perhaps referenced as
> `builtin@model_enum_values`), in a design that is intuitive, reliable, and beautiful?
> Critique the plan, adjust the requirements where justified, and end with a recommended
> solution.

![Infographic summarizing the proposed design: enum already exists but lacks shared sets and completion, models are an open domain validated by routing without silent fallback, one rule that an input's type names what its value is, one sase-core Rust layer feeding the prompt widget, LSP, and typed forms, and a four-step rollout](macro_enum_inputs_named_types_infographic.png)

## Bottom line

1. **`enum` already exists, but it is unfinished.** `InputType.ENUM`, `InputChoice{value,
   label}`, inline `choices:`, Rust frontmatter diagnostics, the mobile wire, the typed
   launch form, and `docs/macros.md` § _Enum Choices_ all shipped in August 2026. What is
   missing is what you actually want. **Neither the prompt bar nor the LSP completes enum
   values.** Every assist wire drops `choices`, and editor diagnostics treat any enum
   value as valid. There is also **no way to share** a value set. The existing code has
   [about seven real defects](#defects-in-the-current-enum). All four researchers found
   this independently, and I confirmed it in code.
2. **The motivating example is not an enum.** `%model` accepts an open grammar:
   `@alias`, `alias@effort`, `provider/model@effort`, nested provider paths, and bare
   known models. Its valid set depends on the machine and the config. A closed list
   would either reject valid input or stop being closed. Every researcher agreed on this.
   The design question is what to do about it.
3. **Recommendation: [named input types](#recommended-design).** An input's `type:` names
   a value domain. Keep the anonymous `type: enum` + inline `choices:`. Add **builtin
   domain types with bare names** that mirror directive value roles (`model`, `effort`,
   joining the existing `agent`). Add **plugin-shared enums referenced as `<dist>@<id>`**,
   using the `<plugin>@<id>` grammar sase already has.
   `builtin@model_enum_values` becomes simply `model`.
4. **`type: model` gets a [precise, already-existing contract](#the-model-contract).** A
   value is valid exactly when `%model` would route it **without silently falling back to
   the default provider**. `sase doctor -C config.model_macros` already implements this
   predicate (`_model_token_routes` in `src/sase/doctor/checks_config_macros.py`). None
   of the four reports noticed it. It turns the hardest open question into reuse.
5. **[Ship in this order](#phased-plan-and-acceptance-tests):** fix the existing enum,
   then complete and diagnose enums everywhere, then add `model`/`effort`, then
   plugin-shared enums once a real consumer needs them. Defer config-defined sets,
   suggest-only fields, and plugin callbacks until real usage asks for them
   (`decisions:corpus-before-mechanism`, by analogy).

```yaml
input:
  mode:    {type: enum, choices: [fast, thorough], default: fast}   # anonymous enum (exists)
  model:   {type: model, default: "@large"}                          # builtin domain ≡ %model
  effort:  effort                                                    # builtin enum ≡ %effort
  edition: sase-research-artifacts@audio_edition                     # plugin-shared enum
```

---

## Is this a good idea

**Yes.** Inputs are a macro's API. Swarm macros launch 5–9 agents per call, so catching
a typo at bind time saves real money. `docs/llms.md` says plainly that a bare `%model`
token that isn't an alias, a `provider/model`, or a known model _"silently falls back to
the default provider rather than erroring."_ Today `#research_swarm(claude_model=opsu)`
launches on the wrong provider without complaint. Completion also makes macros
discoverable in the prompt bar and in Neovim. sase already has the hard parts: catalogs,
value-role completers, a Rust LSP, and a qualified-id grammar (see
[what exists today](#what-exists-today)).

**But the request needs three corrections:**

1. **It is finishing work, not a new type.** Most of the value comes from routing
   `choices` through wires that already exist.
2. **Model needs a domain type, not a value list.** Calling it an enum would force a
   choice between rejecting valid `provider/new-model` strings and accepting typos (see
   [the `model` contract](#the-model-contract)).
3. **Sharing should be "named types", not "a reference in a choices field".** Most
   reusable domains in the corpus are live (models, agents, beads, tribes). A mechanism
   that only shares static lists solves the minority case and mislabels the majority
   (see [why named types win](#why-named-types-win-the-syntax-question)).

**What I would not build:** a suggest-only `completion:` field, executable plugin value
callbacks, a `sase_enums` entry-point group, project/user `enums:` registries, or a new
shortform mini-grammar like `enum(a, b)`. None of these has a consumer in the corpus yet.
The full list of [requirement adjustments](#explicit-requirement-adjustments) is below.

---

## What exists today

Verified in code against sase `aeccf843` and the pinned sase-core `2f16dc4a`:

| Layer | Status | Evidence |
| --- | --- | --- |
| Python model | ✅ `InputType.ENUM`; non-empty, duplicate-free `choices`; exact, case-sensitive membership | `src/sase/macro/models.py:24,71,111,191` |
| `.md` macro parsing | ✅ Shortform dict and longform list both read `choices` (scalars or `{value,label}`) | `src/sase/macro/loader_parsing.py:109,172,328` |
| Workflow longform parsing | ❌ Drops `choices`, so `type: enum` always fails with "declares no choices" | `src/sase/macro/workflow_loader_parse.py:21-72` |
| Rust catalog + mobile wire | ✅ `CatalogInput.choices`, `MobileXpromptInputWire.choices` | `sase_core/src/macro_catalog/*` |
| Rust frontmatter (LSP) | ✅ Missing or forbidden `choices`, invalid default | `sase_core/src/editor/frontmatter.rs` |
| TUI typed launch form | ✅ A button that cycles through choices (no good for large sets) | `ace/tui/widgets/typed_input_form.py:142` |
| TUI prompt-bar hints | ❌ `MacroInputHint` has no `choices`; `enum` falls to `macro_arg_type_hint` (no candidates) | `_macro_arg_assist_models.py`, `_macro_arg_assist_detection.py:234` |
| Rust editor hint wire | ❌ `MacroInputHint` has no `choices`; `assist_entries_from_catalog` drops them | `sase_core/src/editor/wire.rs:394`, `completion/assist_candidates.rs` |
| LSP completion dispatch | ❌ `MacroArgumentValue` always returns `bool_completion_list()`; `MacroArgumentAgent` returns **empty** | `sase_xprompt_lsp/src/server/completion.rs:864-867` |
| LSP invocation diagnostics | ❌ `value_matches_input_type` ends in `_ => true`, so a non-member enum value is never flagged | `sase_core/src/editor/diagnostics.rs:504-522` |
| Authoring schemas | ❌ `workflow.schema.json` and `sase.schema.json` omit `enum`/`code`/`choices` but list `string` | `src/sase/macros/workflow.schema.json:27,53,62` |
| Sharing | ❌ None | — |

Two pieces of existing infrastructure shape the design:

- **Directive value roles are already named value domains.** `DirectiveValueRole`
  (`wire.rs:513`) has `Model`, `Agent`, `Tribe`, `Bead`, `Machine`, `Tab`, `Duration`,
  `Bool`, and others. Both the TUI and the LSP already have completers for them. The LSP
  only lacks a route from a macro argument to a role. Its doc comment says _"Suggestions
  are assistance, never an accidental allowlist."_ That is the right rule for
  directives. A typed macro input is the explicit opt-in to an allowlist.
- **`<plugin>@<id>` is already the shared qualified grammar** (`src/sase/plugins/qualified_id.py`:
  _"Shared `<plugin>@<id>` parsing for every `use:` config consumer"_). It is used for
  worker providers (`builtin@commit`, file hooks) and also for **data specs**: project
  task types (`bead.task_types`) use `use: <plugin>@<slug>`. `plugins.required` already
  enforces that every non-`builtin` prefix in project config names a required
  distribution.

**Corpus** (counts from `cld`; I spot-checked them with `sase macro show`): 114 loaded
macros, **0 use `enum`**. `research_swarm` has **nine** `word`-typed `*_model` inputs.
The only shared static set is `brief|full`, used by `research_swarm.audio_edition` and
`research/audio.edition` (both in `sase-research-artifacts`, both `word` today).
`#pr.status` is an enum that does not say so yet. **Live domains outnumber static enums
about 8:1.** That ratio is the strongest argument for the
[design below](#recommended-design).

---

## Defects in the current enum

I reproduced these by running the real `parse_shortform_inputs` and `InputArg` from the
workspace venv:

```text
choices: [yes, no], default: yes   → choices ['True', 'False'], default True (bool)
  #x:yes                           → "Argument 'answer' expects one of True, False, got 'yes'"
choices: [1.0, true, "two words", ""], default: turbo
                                   → loads fine; invalid default and empty/whitespace values accepted
choices: [fast, "null"]            → loads; "null" can never be supplied (the binder treats it as pass-through)
```

1. **YAML 1.1 vs 1.2 divergence.** PyYAML turns unquoted `yes/no/on/off/true` into bools,
   and `str()` makes them `True/False`. sase-core uses `serde_yaml 0.9` (YAML 1.2), which
   keeps `yes` as a string, and its `value_as_string` silently drops floats. **The LSP
   would suggest `yes`, and the runtime rejects it.** This is exactly the drift that
   `decisions:rust-core-required` exists to prevent.
2. **Invalid defaults are not caught at load or bind time.** `input_binding.py:125`
   inserts the default without validating it. The Rust frontmatter check catches it, so
   the editor and the runtime disagree.
3. **Values are not words.** Empty strings and whitespace pass. That contradicts your
   word-subtype requirement and breaks `#name:value` shorthand.
4. **The literal `null` is unreachable** because it is a binder sentinel.
5. **Workflow longform drops `choices`.** The docs work around this by saying "use
   shortform".
6. **Unknown types silently become `line`** in Python (`type_map.get(..., InputType.LINE)`),
   but they are an error in the LSP. A future `type: model` macro running on an older
   sase would quietly lose all validation, and a typo like `type: enmu` never errors.
7. **Type vocabulary is spread over five places**: Python, two Rust parsers, and two JSON
   schemas. `type: string` is accepted by the schemas and by `eval_ifs_loops.yml`, mapped
   to `line` by Python, and flagged by the LSP.

Stale surfaces: the `macros.md` memory still lists inputs as `word/line/text/path/int/bool/float`.
`docs/macros.md` says editor completion can show enum labels, but no editor completes
enums.

---

## Where the reports disagreed and how I resolved it

_Consolidated report · 2026-10-04 · merges independent research from `cdx`, `cld`, `grk`,
and `gem`, plus the lead's own verification against sase `aeccf843` and the pinned
sase-core `2f16dc4a` (sase's `sase-core-revision.txt` matches it)._

| Question | cdx | cld | grk | gem | **Resolution** |
| --- | --- | --- | --- | --- | --- |
| Where the shared reference goes | `choices: {use: builtin@models}` | `type: model` / `type: <dist>@<id>` | `catalog: model` (dotted ids) | `enum: builtin@models` (+ scalar `choices:` shorthand) | **Named types (cld).** See [below](#why-named-types-win-the-syntax-question). |
| What `model` accepts | Closed "known selectors"; open use = `word` + `completion:` | %model resolver; typos fail; unknown model under known provider OK | Closed against the *completion* catalog | Soft validation via resolver | **Same rule as doctor's `_model_token_routes`** ([the `model` contract](#the-model-contract)) |
| `@` in reference ids | Uses `<dist>@<id>` | Uses `<dist>@<id>` | Avoid `@`; dotted `github.pr_status` | Uses `@`; `project@`, `@env` | **Keep `<dist>@<id>`.** grk's "`@` is only for workers" is wrong (task types use it for data specs). In the `type:` slot it never collides with `@alias` *values*. |
| How plugins declare sets | Declarative manifests via resource discovery | Entry point `input_type_specs()` like task types (later) | `enums:` in plugin `default_config.yml` | Entry point `sase_enums` + config | **A declarative `input_types.yml` beside the plugin's `macros/`, read by Rust** ([plugin-shared enums](#plugin-shared-enums)) |
| Can a local set shadow a builtin? | Explicit refs never shadowed | No; builtins reserved | Yes, project wins | Precedence list | **No** (same as task-type rule D4). Plugin types are always qualified. |
| Word-shape on existing inline enums | Compat adapter; strict only for new shared sets | Strict for named; leave gates alone | Load error | Enforce | **Enforce in the macro/workflow loader, not in `InputArg`**, so gate inputs are unaffected ([value rules](#value-rules-for-every-enum)) |
| Config-defined sets in v1 | Optional later | Phase 3 | v1 | v1 | **Defer until a consumer exists** |
| Completion route | Shared Rust context + edits | Type → `DirectiveValueRole` | Reuse `macro_arg_value` | New `MacroArgumentEnum` | **Rust derives it from the hint:** choices → generic choice list (bool folds in); role → existing directive completer |

### Why named types win the syntax question

The deciding facts are verifiable, not matters of taste:

- **Precedent in sase:** `type: agent` is already a named domain type: a word with a
  live completer. `model` belongs next to it, not inside `enum`.
- **Precedent outside sase:** GitHub Actions `workflow_dispatch` inputs have
  `type: choice` + `options:` (an inline enum) next to `type: environment` (a named
  domain filled from live repo config). That is the same split proposed here.
- **Shortform works.** The shortform input syntax is `name: <type string>`
  (`_parse_shortform_input_value`). `model: model` and
  `edition: sase-research-artifacts@audio_edition` work with no new grammar. Every
  field-based spelling forces the dict form.
- **Honesty.** `{type: enum, choices: builtin@models}` claims `model` is closed, which it
  is not. `type: model` makes no such claim.
- **Your own words:** "use something like `builtin@model_enum_values` to specify that a
  macro input *uses this type*." The design keeps your instinct and drops the
  redundant suffix.
- **The alternatives disagree about the field name** (`choices.use` / `catalog` /
  `enum`). That suggests the concept has no natural home there. cdx's `use:` also already
  means "deep-merge sibling keys onto the referenced provider or spec" in task types and
  file hooks, which is a different meaning.

### Accuracy notes on the inputs

gem's examples include `enum: @environments`, which is invalid YAML (`@` cannot start a
plain scalar), and `anthropic:claude-…`, which is not sase model syntax. grk's "hidden
models omitted" would reject `%model:fakey-large`, which `docs/llms.md` says works. I
relied on cdx's and cld's code-level findings, which I re-verified, more than on gem's.

---

## Recommended design

### The rule authors learn

> **`type` names what the value is**: a scalar keyword (`word`, `int`, …), `enum` with
> inline `choices`, a builtin domain (`agent`, `model`, `effort`), or a plugin's shared
> enum (`<dist>@<id>`). Bare names are sase's; qualified names are plugins'.

```yaml
---
name: deploy
input:
  env:                                   # anonymous enum (exists; gains completion + docs)
    type: enum
    choices:
      - {value: staging, description: Pre-prod cluster}
      - {value: prod, label: Production, description: Customer traffic}
    default: staging
  model: {type: model, default: "@large"}            # quote: '@' cannot start a YAML scalar
  effort: effort
  edition: sase-research-artifacts@audio_edition
---
```

### Type resolution

1. **Scalar keywords and `enum`** work as they do today. `enum` requires inline
   `choices`. `choices` on any other type is still an error (narrowing a named type is
   [future work](#phased-plan-and-acceptance-tests)).
2. **A bare name** resolves to a builtin type. Builtin names are reserved. To avoid
   future collisions, reserve **every `DirectiveValueRole` name now** (`model`, `agent`,
   `tribe`, `bead`, `machine`, `tab`, `duration`, `clan`, `session`, `hood`, …), even
   before each is implemented.
3. **`builtin@<id>`** is an accepted alias of the bare builtin. Hover and formatters show
   the bare form.
4. **`<dist>@<id>`** resolves to a plugin-declared type. The distribution name is
   normalized with `canonical_plugin_prefix` (PEP 503). Plugin types are **never**
   reachable by a bare name, so installing an unrelated plugin cannot change what an
   existing macro means.
5. **An unknown name is an error** that names the closest known types. This replaces the
   silent `line` fallback, and users can see the change, so ship it behind a `sunset`
   flag per `sase_flags.md`. Keep `string` as a deprecated alias of `line`.
6. **Errors stay per macro.** An unresolved type breaks only the macros that use it,
   never the whole catalog. A project macro that refers to a plugin type follows the
   existing `plugins.required` rule. The error says which plugin to install or declare.

### Builtin types

| Type | Mirrors | Kind | Validation | Completion |
| --- | --- | --- | --- | --- |
| `agent` | `%wait:` (`Agent`) | domain | word rules (today) | existing agent completer. The LSP currently returns **empty** for macro args; mapping to the role fixes this for free |
| `model` | `%model:` positional (`Model`) | domain | [the `model` contract](#the-model-contract) | the exact `%model` menu (provider drill-down, alias rows, effort, advisories) |
| `effort` | `%effort:` | closed enum | membership in `EFFORT_LEVELS_ORDERED` (`src/sase/macro/effort.py:20`) | ordered list `none … max` |
| later: `tribe`, `bead`, `machine`, `duration`, `task_type` | their directive roles | domain | per role | existing role completers. Add each when a macro needs it |

Guiding rule: **if a directive accepts it, a macro input can be typed as it, and both
complete and validate the same way.**

### The model contract

A `model` value is valid exactly when `%model` would route it **without the
silent-default fallback**. This is the predicate `sase doctor` already uses
(`_model_token_routes`):

- a token that resolves to a provider, including known bare models and models hidden
  from the picker (`fakey-large` is legal `%model`);
- a configured alias, with or without `@`, **even if its provider plugin is not installed
  on this machine**;
- any explicit `provider/model…`. An editor hint is fine if the model is not in the local
  catalog, because new models ship before catalogs update;
- with an optional `@<effort>` suffix that must be a valid effort level.

**Rejected:** a bare unknown token (`opsu`), an unknown `@alias`, or a bad effort
suffix. The error offers "did you mean". Validation **never consumes an alias
round-robin cursor** (`consume=False`), never makes network calls, and never checks
provider availability or disable state. "Known", "accepted", and "executable right now"
are three different promises (cdx). The type promises only "accepted without fallback".

This is deliberately stricter than `%model`, and that is the point of typing the input.
`%model` itself stays open; do not change it. Because aliases and `provider/` forms pass
on any machine, the predicate barely depends on the machine. That mostly answers cld's
`%dispatch` concern (see [open questions](#risks-and-open-questions)). Authors of shared
macros should use explicit `provider/model` or alias defaults, as `research_swarm`
already does.

**Defaults:** an author-shipped `model` default that fails the predicate is a **warning**
in the LSP and `sase doctor`, not a bind error (cld R6). Defaults for closed enums must
be members; that is an error.

**Where it lives:** move the predicate into sase-core as a classifier over a model
validity snapshot (providers, model→provider map, alias names, effort levels). Python
already builds that data for `model_catalog.json`. The macro binder, the LSP, and
`sase doctor` all call the one Rust classifier. Add a parity test against
`resolve_model_provider_with_effort`.

### Plugin-shared enums

A plugin ships `input_types.yml` **next to its `macros/` directory**, in the same module
that macro discovery already loads:

```yaml
# sase_research_artifacts/input_types.yml
schema_version: 1
types:
  audio_edition:
    description: Narration length for guide-backed audio editions.
    choices:
      - {value: brief, description: About 4 minutes}
      - {value: full,  description: About 16 minutes}
```

Macros refer to it as `sase-research-artifacts@audio_edition`. That includes the
plugin's own macros: always use the qualified form in v1.

Why a data file rather than a hook or a `default_config.yml` key:

- **One loader, every frontend.** The `sase lsp` wrapper already exports each plugin's
  macro directory and config path to the Rust loader (`_discover_plugin_macro_dirs`,
  `_discover_plugin_config_paths` in `src/sase/integrations/macro_lsp.py`). Rust reads
  the file directly, so there is no new Python materialization step and no stale JSON.
  The Python runtime calls the same Rust loader through a binding. Add a `distribution`
  field to each exported entry so Rust can qualify ids.
- **Types travel with the macros that use them.** If a plugin's macros load, its types
  load too. A hook-based registry could leave the LSP seeing a macro but not its type,
  which produces false "unknown type" errors.
- **Provenance stays intact.** Plugin `default_config.yml` files are deep-merged into one
  config, which loses track of which plugin defined what (cld's objection to grk).
- **This copies the task-type rules where they fit:** Rust validates, `<dist>@<id>`
  qualifies, and duplicates are reported as diagnostics instead of silently winning.

Only static lists are supported in v1. A plugin that needs a **live** domain should first
check whether a builtin domain covers it. Model, agent, and machine registries already
grow when plugins are installed, so plugins share those domains implicitly.

### Value rules for every enum

These rules apply to every enum, inline or shared:

- Values must be **strings**. Reject non-string YAML scalars with a "quote it"
  diagnostic. This sidesteps YAML 1.1 vs 1.2 at the source.
- Values must be non-empty, contain no Unicode whitespace, not equal `null`, and be
  unique. Matching is exact and case-sensitive, and labels are never accepted as input
  (existing tests lock this).
- **Warn** on characters that need quoting in shorthand (`,` `+` `(` `)` `[` `]` quotes,
  backtick). `+` means a space in bare `#name:a,b`. Completion quotes these values
  automatically, but people typing by hand will be surprised.
- `label` (short display text) and a new optional `description` (hover and completion
  detail) are free text and never inserted.
- Repeatable enum inputs check each element against the set.
- One resolution per invocation: validation and rendering use the same snapshot.

**Rollout:** enforce these rules in the macro and workflow loaders (eventually the
single Rust input parser), **not** in `InputArg.__post_init__`. Gate inputs share
`InputArg` and are filled through forms, where spaces are harmless. No bundled macro uses
`enum`. Before tightening, scan the installed plugins and the home and project macros. If
that finds no offenders, tighten directly. Otherwise use a `sunset` flag.

### Completion and editor experience

**Prompt bar (TUI):**

```text
#research/audio(edition=▏
 ┌ edition · sase-research-artifacts@audio_edition ──────────┐
 │ ▸ brief     About 4 minutes                       default │
 │   full      About 16 minutes                              │
 └───────────────────────────────────────────────────────────┘
```

- `#m:` / `#m(k=` opens the value menu right away. With an empty prefix the rows keep
  declared order. Filtering is case-insensitive prefix first, then the shared Rust fuzzy
  filter, and inserts the canonical spelling. Labels go in the right column, the
  description in the detail line, and the default gets a quiet badge but is not
  preselected.
- Accepting a `name=` candidate chains straight into its value menu, as `bool`/`path`/`agent`
  already do.
- A `model` argument uses the **exact** `%model` menu. Generalize `_offers_model_values`
  (`directive_completion.py:222`, currently keyed on `directive_name == "model"`) so it
  keys off the value role. Inside a `model` argument, `@` opens the alias menu, not the
  generic `@` menu. The argument's type wins over the trigger character.
- `bool` becomes a choice list (`true|false`), which removes the special bool completion
  paths on both sides.
- Signature hints: `#deploy(env: staging|prod = staging, model: model)`. Show up to four
  choices inline; for longer sets show the type name and a count.
- The typed launch form keeps the cycle button for ≤5 choices and uses a searchable
  picker above that. `model` reuses the existing model picker; do not build a second
  one.

**LSP (Neovim and any other client):** the same candidates come from the same Rust
function, and `sase-nvim` needs no changes because it is a standard LSP client.

- Items: `CompletionItemKind.EnumMember` for closed sets and the existing kinds for
  domains. Each has a `textEdit` that replaces the whole current value span (found with
  the argument parser, not a regex), `filterText` set to the value, `sortText` set to the
  declared index, `labelDetails` set to the label, and the description as documentation.
  Return `isIncomplete` when the list is truncated. No new trigger characters are
  needed, because `:` `(` `,` `=` already trigger.
- Invocation diagnostic: `edition: "breif" is not one of brief | full`, with a
  **"Replace with `brief`"** code action. Closed-set diagnostics are **errors**, because
  their data is file-backed and loaded by the same loader. `model` diagnostics are
  **warnings**, because the LSP's model snapshot is fixed at launch and the runtime is
  the authority.
- Hover on an argument shows the type, where it comes from (`plugin
  sase-research-artifacts`), and a choice table, truncated with a count for large sets.
- Frontmatter authoring: complete `type:` with builtin and installed plugin types and
  their descriptions. Diagnose unknown types with suggestions, plus non-word,
  duplicate, or non-string values and defaults outside the set.

### Architecture and wire at the Rust boundary

Validation, resolution, completion, and diagnostics must agree across the TUI, the LSP,
and mobile, so by the boundary litmus test they are core logic.

| sase-core (Rust) owns | sase (Python) owns |
| --- | --- |
| One input-declaration parser and type vocabulary; schema enum lists generated from it | Discovering plugin modules and passing paths plus distribution names |
| A builtin type table: name → base kind + `DirectiveValueRole` + validator | Building the model validity snapshot from the LLM registry (shared with `model_catalog.json`) |
| Loading and validating `input_types.yml`; registry resolution and errors | Agent and other live snapshots it already builds |
| Enum membership, did-you-mean, and the `model` classifier | TUI presentation, the typed-form picker, and doctor rendering |
| Completion context, candidates, accept edits, diagnostics, hover | Thin adapters only. No Python validator. |

Wire changes are additive. **`type` stays the base kind**, so older consumers degrade
gracefully: a named enum still looks like `enum` with choices, and `model` looks like
`word`.

```text
InputChoiceWire  = { value, label?, description? }
MacroInputHint  += { choices: [InputChoiceWire]   // resolved closed set; empty for open domains
                     type_ref: string?           // "model", "sase-research-artifacts@audio_edition"
                     value_role: DirectiveValueRole? }
InputArg (Py)   += type_ref: str | None           // type stays the base InputType
```

Also add `choices` to `StructuredCatalogInput` and the mobile helper catalog JSON. Stop
dropping them in `assist_entries_from_catalog`. Every core change needs
`sase-core-revision.txt` moved past it before the sase callers land.

For YAML parity, the durable fix is that Rust parses input declarations from the raw
frontmatter text (cld). Until then, both sides reject non-string choice values. The LSP
can also warn on unquoted `yes/no/on/off` in a `choices` list, because it has the
source text.

---

## Explicit requirement adjustments

1. **Reframe "add an enum type" as "finish the enum".** Keep `choices`, `InputChoice`, and
   labels. Do not add a second spelling such as `values`.
2. **Shared sets are named types.** You write `type: <name>`, not a reference inside
   `choices`. Builtins use bare names. Plugins use `<dist>@<id>`.
3. **Replace `builtin@model_enum_values` with `type: model`, a domain type, not an
   enum.** Its contract is "routes without silent fallback". `builtin@model` is
   accepted as an alias.
4. **Enforce the word subtype for macro and workflow enums,** add the string-only and
   not-`null` rules, and leave gate inputs out of it.
5. **Add per-choice `description`.** Labels are kept.
6. **Treat defaults differently by kind.** Closed-set defaults must be members; domain
   defaults only warn.
7. **Fix the existing defects first,** including unknown-type errors (behind a sunset
   flag) and schema drift.
8. **Include parity in "done".** TUI, LSP, typed form, schemas, docs, and the stale
   `macros.md` memory all agree, or the feature is not finished.
9. **Out of v1:** config-defined sets, a suggest-only `completion:` field, plugin value
   callbacks, narrowing, and gate-input named types.

---

## Phased plan and acceptance tests

| Phase | Scope | Must-pass tests |
| --- | --- | --- |
| **0. Correctness** | Workflow longform reads `choices`. Python validates defaults. String-only / word / not-`null` value rules. Unknown type → error (sunset flag; `string` → `line` alias). Fix or generate both JSON schemas. Update `macros.md` memory and `docs/workflow_spec.md`. | `[yes, no]` gives a "quote it" error on both sides; invalid default rejected at load; longform workflow enum loads; `type: enmu` errors with a suggestion; tests in both flag states |
| **1. Enum completion everywhere** | `choices`/`type_ref`/`value_role` on all hint wires. Rust choice-list completion (bool folded in). LSP EnumMember items with full-span edits. Invocation diagnostic and quick fix. Hover. Signature format. Picker for large sets. Map `agent` → role in the LSP. Dogfood: `#pr.status` → inline enum. | Golden cursor→candidates→edit fixtures shared by TUI and LSP; positional, named, colon, and repeatable forms; quoting of `,`/`+`; non-BMP edit positions; `#pr:ready` still works; **after applying an edit, runtime and editor accept the same exact value** |
| **2. `model` + `effort`** | Builtin type table. Rust `model` classifier over the snapshot (doctor reuses it). Role-keyed TUI model menu. `@` precedence. | `@large`, `claude/opus@xhigh`, `codex/new-model`, and hidden `fakey-large` accepted; `opsu` rejected with "did you mean opus"; unknown `@alias` rejected; cursor never consumed; `%model:opsu` still falls back unchanged |
| **3. Plugin-shared enums** | `input_types.yml` loader, qualified resolution, `plugins.required` integration, doctor check, frontmatter completion of type names. First consumer: `sase-research-artifacts@audio_edition`; migrate `research_swarm`'s nine model inputs to `type: model`. | Missing plugin → per-macro error naming the plugin; duplicate id → diagnostic; same type in two macros validates the same; LSP sees the type with no extra materialization |
| **4. Only on demand** | `input_types:` in user/project config (bare names, cannot shadow reserved names). More domains (`tribe`, `bead`, `machine`, `duration`, `task_type`). Narrowing (`{type: effort, choices: [low, high]}`). Named types on gate inputs. | — |

Phase 1 alone makes enums real in the prompt bar and in Neovim. The model work is the
headline example, but it is not the first slice.

---

## Risks and open questions

- **The LSP snapshot goes stale.** `model_catalog.json` is written once when the LSP
  starts, and rereading it does not refresh it. Mitigation: `model` diagnostics are
  warnings in the editor, and refreshes swap in a complete new snapshot atomically. Do
  not build a live editor channel in v1.
- **Behavior changes.** Unknown-type errors and stricter value rules can break user
  macros that were silently degraded before. Scan the corpus first, run doctor warnings
  for a cycle, and use a sunset flag where a compatibility path is needed.
- **Large catalogs in the UI.** Truncate hints, hovers, and error messages to a count.
  Let the completion menu hold the full set.
- **Open question:** should a plugin's own macros get a bare shorthand for its own types?
  Recommendation: not in v1. Explicit beats clever, and the long ids are greppable.
- **Open question:** should bind-time `model` validation be skipped for `%dispatch`
  launches? Recommendation: no. The predicate barely depends on the machine. Revisit
  only if a real case appears.

---

## Recommended solution

Build **named input types**, not a separate shared-enum mechanism:

1. **Finish the enum you already have.** Fix the
   [seven defects](#defects-in-the-current-enum). Make values strict string words. Route
   `choices` through every hint wire. Complete and diagnose enum values in the prompt bar
   and the LSP from one Rust function, with labels, descriptions, quick fixes, and hover.
2. **Let `type:` name a domain.** Builtins are bare names mirroring directive value
   roles. Start with `model`, valid when it routes without silent fallback (the predicate
   `sase doctor` already uses), and `effort`, the closed `EFFORT_LEVELS_ORDERED` list.
   `builtin@model_enum_values` becomes `model`.
3. **Let plugins share closed enums** through a declarative `input_types.yml` shipped
   next to their macros ([plugin-shared enums](#plugin-shared-enums)). Macros refer to
   them as `<dist>@<id>`, Rust reads them directly, and every frontend therefore sees the
   same types.
4. **Keep the logic in sase-core** and keep Python to discovery and snapshots. That fixes
   YAML drift and type-vocabulary drift at the root.
5. **Ship in this order:** correctness → enum completion → `model`/`effort` → plugin
   enums. Add config sets and further domains only when a macro needs them.

The result is one idea authors can learn in one sentence (_a macro input's `type` names
what its value is_). It is reliable because there is one parser, one validator, and one
completer for every frontend. It also reads well: `model: model`, `effort: effort`, and
`edition: sase-research-artifacts@audio_edition`.
