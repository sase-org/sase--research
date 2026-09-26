# Updating Size Alias Pools and the Model Catalog With Fewer Edits

Research report · 2026-09-25 · researcher `cld`

**Recommendation:** Keep the plan, but aim it at a different target. The runtime data
is already single-sourced. The size alias pools live in one YAML file. The model catalog
lives in one hook per provider. The TUI prompt input, the model picker, the Rust xprompt
LSP, and the Neovim plugin all derive their lists from those sources. None of them keeps
its own copy.

The cost of an update comes from **hand-maintained derived material**:

- prose and tables in the docs;
- tests that restate the shipped values;
- illustrative example strings that get bumped to look current;
- a decision record that names the current models.

In the last ten value-only updates, a single source-of-truth edit fanned out to a median
of 13.5 files. Docs made up 48% of those edits and tests 29%.

I recommend four changes:

1. **One hand-edited model manifest** that holds the built-in model catalog and the size
   alias defaults together.
2. **A validator** that encodes the effort-ladder and redundancy rules, so the single
   edit is also safe.
3. **Generated docs blocks with a CI drift check.**
4. **Tests that derive their expectations from the manifest** instead of restating it.

The workflow then becomes: edit `models.yml`, run `just fix`, commit. For a change like
the Grok 4.7 commit, that is 1 hand-edited file instead of 19, with no test edits.

If you only do part of this, do items 3 and 4 together with the examples policy (§6.6).
Those account for most of the file count, and the generated-block pattern already exists
(`tools/render_model_alias_docs`).

---

## 1. What an update touches today (evidence)

### 1.1 Base rate

`git log --since=2026-06-01 -- src/sase/llm_provider/model_alias_defaults.yml` returns
**29 commits** in about 4 months. At least 7 more commits changed only a provider's
model catalog. In the last 30 days (2026-08-26 to 2026-09-25) there were **9**
alias-value or catalog-value commits. Seven providers are supported, and 2026's release
cadence (GPT-5.6 → GPT-6 Astra → GPT-6 Sol, Grok 4.6 → 4.7, Gemini 3.7 → 3.8 Flash, Muse
Spark 1.2 → 1.3) shows no sign of slowing. The pain is recurring, not incidental.

### 1.2 Files touched by value-only update commits

These commits only changed which models exist or which models the pools use. Structural
refactors are excluded.

| Commit       | Date  | Change                                   | Files  | src    | tests  | docs   | memory |
| ------------ | ----- | ---------------------------------------- | ------ | ------ | ------ | ------ | ------ |
| `1cea18e00f` | 09-25 | Add Grok 4.7, retune `@large`/`@xlarge`  | 19     | 3      | 5      | 10     | 1      |
| `682089c845` | 09-24 | Add GPT-6 Sol, make it the Sol default   | 28     | 8      | 6      | 13     | 0      |
| `68d727bbfd` | 09-20 | Muse contributor into small pools        | 6      | 2      | 0      | 4      | 0      |
| `65c8169f9d` | 09-20 | Retune sizes to the effort ladder        | 16     | 1      | 1      | 10     | 3      |
| `e65cc22eeb` | 09-20 | Put Grok in `@xlarge`                    | 13     | 2      | 1      | 9      | 0      |
| `17084a6e27` | 09-19 | Retune onto Codex luna/terra             | 26     | 3      | 14     | 8      | 0      |
| `97359b9015` | 09-19 | Refresh Muse Spark catalog               | 14     | 2      | 5      | 7      | 0      |
| `28b9ac3888` | 09-05 | Add GPT-6 Astra                          | 10     | 2      | 4      | 4      | 0      |
| `f546929e46` | 09-04 | Add Gemini 3.8 Flash + `@xsmall`         | 9      | 2      | 5      | 2      | 0      |
| `a0d73f7ea3` | 08-19 | Send xhigh on `@xlarge` grok             | 4      | 1      | 1      | 2      | 0      |
| **Total**    |       |                                          | **145**| **26** | **42** | **69** | **4**  |

Of the 26 `src/` edits, about half are the real sources of truth
(`model_alias_defaults.yml` and a provider's `.py`). The rest bump example strings:

- TUI input placeholders (`e.g. codex/gpt-6-sol@medium`);
- argparse help text (`parser_bead_lifecycle.py`, `parser_agent_search.py`);
- a docstring (`axe/run_agent_successor.py`);
- the commented override example in `default_config.yml`.

The GPT-6 Sol commit touched 5 source files for this reason only.

### 1.3 Where each concept lives today

| Concept                                         | Source of truth                                                                                              | Derived consumers (all automatic)                                                                                                                                                                                                                             |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Size alias pools (`@xsmall` … `@xlarge`)        | `src/sase/llm_provider/model_alias_defaults.yml`                                                             | `model_alias_policy.py` → alias views → `%model` completion entries (with descriptions and pool counts), Models panel, `docs/llms.md` generated table                                                                                                          |
| Known models per provider                       | Each provider's `llm_known_model_names()` hook (`claude.py`, `codex.py`, `agy.py`, `grok.py`, `muse.py`, `qwen.py`, `opencode.py`) | `_registry_metadata.py` → metadata payload → `model_to_provider` map (bare-name resolution), model picker (`model_picker_rows.py`), completion catalog (`_model_completion_catalog.py`)                                                                       |
| Short aliases, advisories                       | `llm_model_short_aliases()`, `llm_model_advisories()` hooks                                                  | Same payload → completion descriptions, picker labels, agent-name suffixes                                                                                                                                                                                     |
| Provider tier default (`large`/`small`)         | `_TIER_TO_MODEL` literal in each provider module                                                             | `resolve_model_name(tier)`, metadata `model_resolutions`                                                                                                                                                                                                       |
| TUI prompt input completion                     | —                                                                                                             | `build_model_completion_catalog()` (`directive_completion.py`, `_file_completion_workers.py`)                                                                                                                                                                  |
| External editors (LSP)                          | —                                                                                                             | `sase xprompt-lsp` materializes `model_completion_catalog_payload()` to `~/.sase/xprompt_lsp/model_catalog.json`. The Rust `sase_xprompt_lsp` re-reads it on each `%model` completion. `sase_core::model_completion` handles only wire format and filtering. |
| sase-nvim                                       | —                                                                                                             | No hard-coded model names (checked: only an LSP smoke test mentions a model).                                                                                                                                                                                  |
| sase-core (Rust)                                | —                                                                                                             | No catalog. Model strings appear only in test fixtures. The size names are a stable enum (`PhaseSizeWire`).                                                                                                                                                    |

**Takeaway:** the runtime side already follows "one source, many derived views". The
plan does not need new plumbing between completion surfaces. It needs the derived views
that are still written by hand to stop being written by hand.

### 1.4 The derived material that is still hand-maintained

1. **Docs tables that mirror registry data.** In `docs/llms.md`:
   - "Automatic Provider Resolution", every known model per provider (about line 1657);
   - "Model Short Aliases" (about line 1694);
   - per-provider tier tables (`| large | gpt-6-sol |` near line 486, Grok's near line
     1005).

   `docs/llms.md` alone has 38 mentions of current model IDs. Only the alias-defaults
   table is generated.
2. **Prose that restates pool membership.** For example: "Grok Build can still be
   reached automatically through the shipped `@small`, `@medium`, and `@large` pools, and
   through `@xlarge` when Claude and Codex are unavailable". Variants of this appear in
   `README.md`, `docs/getting_started.md`, `docs/agent_providers.md`, `docs/llms.md`,
   and `docs/ace.md`. Every pool retune rewrites all of them. The Grok 4.7 commit
   changed about 140 doc lines (insertions plus deletions) for a 4-line YAML change.
3. **A docs test that pins that prose word for word.**
   `tests/test_docs_getting_started_providers.py` asserts the exact sentence, so the
   prose rewrite also forces a test edit.
4. **Tests that restate shipped values.** Several `real_model_alias_defaults` tests
   assert literal pool members and efforts (`test_load_balanced_alias_defaults.py`,
   `test_provider_priority_routing.py`, `test_ordered_fallback_aliases.py`). There are
   also about 10 per-model tests ("catalog includes grok 4.7", "picker has gpt6sol row",
   and so on) and about 32 `resolve_model_provider(...)` asserts in
   `test_llm_provider_core.py`, one per model. The effort-ladder test even hard-codes
   data: `continued_from = {"grok/grok-4.6": "grok/grok-4.7"}`.
5. **Illustrative examples that get bumped to the latest model.** Placeholders, help
   text, docstrings, `default_config.yml` comments, and docs code blocks all fall here.
   None of them has to be current: `docs/ace.md` still uses `codex/gpt-4.1-mini`
   examples and works fine.
6. **The decision record `decisions:size-alias-effort-ladder`.** Its worked example
   names Grok 4.7 and 4.6, and the Grok 4.7 commit edited 33 lines of it. By SASE's own
   convention a decision record is immutable once accepted.
7. **No drift check for the one generated block.** `just fmt-docs` rewrites it, but
   `fmt-check`/CI never verifies it. If a maintainer edits the YAML and skips `just fix`,
   the docs drift silently.

The good news is that the codebase already contains the patterns needed to fix this:

- a generated-block renderer that reads YAML without importing the provider runtime
  (`tools/render_model_alias_docs`, `<!-- BEGIN GENERATED: … -->` markers);
- a frozen alias fixture that separates behavior tests from shipped values
  (`tests/_model_alias_defaults_fixture.py`, whose docstring says shipped-value changes
  should need no change there);
- invariant tests on the defaults (`test_model_alias_defaults.py`, including "every
  selector member names a registered provider model").

The work is to extend these patterns and finish the migration.

---

## 2. Critique: is this a good idea?

**Yes. The frequency is real and the fix is cheap relative to its payoff.** At about 2
updates a week and a median of 13.5 files each, the overhead is more than the diff size:

- **Missed spots:** the commented example in `default_config.yml` has already drifted
  from anything shipped.
- **Review noise:** a pool retune turns into a prose diff of more than 100 lines.
- **Policy violations:** the decision record gets edited in place.
- **Test churn that hides real regressions:** when every retune rewrites routing
  assertions, reviewers stop reading them.

Four caveats, which drive the requirement adjustments below:

1. **"As few files as possible" is the wrong metric if taken literally.** Generated docs
   appearing in the diff is good: reviewers see the user-visible effect of a retune. The
   right metric is **hand-edited files, plus zero knowledge of where else to look**.
   Anything derived is regenerated by one command and verified by CI.
2. **Don't over-build.** The runtime plumbing is fine. A remote or auto-discovered
   catalog, a Rust-core catalog, or a DSL that computes efforts would add machinery to a
   problem that is mostly docs and test hygiene.
3. **Removing value-pinned tests removes a tripwire.** Today a pool change can't land
   without someone touching a test. That tripwire should be replaced with rule-based
   validation (effort ladder, redundancy, capability) and the generated-docs diff, not
   simply deleted.
4. **The catalog is a UX surface, not a capability gate.**
   `resolve_model_provider("codex/gpt-7-future")` already returns
   `("codex", "gpt-7-future")`, so explicit `provider/model` works for models SASE has
   never heard of. Only bare-name resolution, completion, pickers, and short aliases
   need catalog entries. That lowers the urgency of adding models and argues against
   heavyweight "must be in the catalog" gates.

---

## 3. Requirement adjustments (called out explicitly)

| #      | Adjustment                                                                                                                                                                                              | Why                                                                                                                                                                                                                                                              |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A1** | Reframe "few files" as **one hand-edited file per update, one regeneration command, CI catches the rest**. Regenerated files may appear in the diff.                                                     | Generated docs are review evidence. Optimizing the raw diff count would push toward hiding tables behind links, which hurts readers.                                                                                                                             |
| **A2** | **Add: the single edit must be safe.** A validator encodes the effort-ladder and provider-redundancy rules, provider effort capability, and catalog membership, with actionable errors.                   | Fewer edit points is only a win if you can't silently break a rule the value-pinned tests used to catch. The effort ladder's own "Cost" section says replacing one model can force edits to the aliases below it. The tool should tell you which rung to use. |
| **A3** | **Add: a drift check.** Regeneration must be verified in `fmt-check`/CI, not only performed by `just fix`.                                                                                               | This gap exists today for the one generated block.                                                                                                                                                                                                               |
| **A4** | **Add: illustrative examples are exempt from freshness.** Examples must name a model that is still in the catalog, but they need not name the newest one.                                                 | This removes about 5 source files and several doc hunks per update that exist only to look current.                                                                                                                                                              |
| **A5** | **Explicit non-goal: moving the catalog into sase-core.**                                                                                                                                                | The Rust boundary rule covers shared *behavior*. The catalog is *data*, and the LSP already receives it as a materialized JSON payload. Moving it into Rust would turn every model update into a two-repo change plus a `sase-core-revision.txt` pin bump, the opposite of the goal. |
| **A6** | **Explicit non-goal: discovering models from provider CLIs at runtime.**                                                                                                                                 | It needs subprocesses, auth, and network, is slow on the completion path, and is fragile (few CLIs expose a model list; `agy models` is the exception). At most it could be a maintainer-assist script later.                                                     |
| **A7** | **Add (small): retiring a model should not break old prompts.** A `status: legacy` flag hides a model from completion and pickers while bare-name resolution keeps working.                              | Today "retire" means deleting it from the Python list. That breaks bare-name `%model:` in older prompts and configs and forces test edits.                                                                                                                       |
| **A8** | **Out of scope, but worth noting:** user configs that pin concrete models go stale.                                                                                                                     | Your chezmoi `sase.yml` custom aliases `sol_or_grok` and `opus_or_grok` still target `codex/gpt-5.6-sol` and `grok/grok-4.6`, one generation behind the shipped defaults. The manifest's `supersedes` field (below) makes a cheap `sase doctor` advisory possible. |

---

## 4. Options considered

| Option                                                                                                               | Verdict                                                                                                                                                                                                                                                                                                                                                                                           |
| -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A. Hygiene only:** generate the remaining docs tables, add the drift check, rewrite pool prose to reference the table, refactor tests to invariants, adopt the examples policy. No runtime change. | **Do this regardless.** It removes roughly 70–80% of the files per update. Limitation: the known-models and short-alias tables would be rendered by importing the provider runtime, which the renderer deliberately avoids today; it runs in the dependency-light formatter venv. |
| **B. Model catalog as data:** move `llm_known_model_names`, short aliases, advisories, and `_TIER_TO_MODEL` for built-in providers into a packaged YAML. Provider hooks read it.            | **Recommended.** Adding a model becomes a data edit. The renderer can generate every table without importing providers. The validator can see catalog and pools together. The hooks stay as the public plugin contract, so third-party provider plugins are unaffected.                                                                                                                         |
| **C. One manifest (B merged with `model_alias_defaults.yml`).**                                                        | **Recommended, but optional relative to B.** The most common operation (new model → add to catalog → promote into pools → demote the predecessor's rung) touches both halves. Keeping them in one file keeps the cross-references in one diff hunk and matches your "as few files as possible" goal. Two sibling files under one validator would deliver about 90% of the benefit. |
| **D. Catalog in sase-core (Rust) with a binding.**                                                                   | **Reject** (see A5). Every model bump would require a sase-core commit, a wheel, and a pin move.                                                                                                                                                                                                                                                                                                   |
| **E. Runtime discovery from provider CLIs or a remote catalog feed.**                                                | **Reject** (see A6). A remote feed also adds a trust and offline dimension that SASE doesn't need.                                                                                                                                                                                                                                                                                                |
| **F. Compute efforts automatically from the effort-ladder rule** (store only model membership and derive `@effort`). | **Reject for now; validate instead.** The rule has exceptions: Antigravity carries no suffix, non-primary `\|\|` candidates and last-resort tails don't consume a rung, and a predecessor continues its successor's descent. Generated efforts would hide surprises in the most review-sensitive values. A validator that says "`@medium` member `grok/grok-4.6@medium`: expected `@high`" gives the same ergonomics while keeping the file explicit. An optional `--fix` could write the suggested rungs. |
| **G. "Channel" or tier references in selectors** (for example `codex/:large`), so pools and user configs follow a provider's current flagship automatically. | **Defer.** It is appealing for A8, and `_TIER_TO_MODEL` is already a channel in all but name. But the effort ladder is defined on model identity, the selector grammar, completion, and docs would all change, and silently moving a user's pinned model to a new generation is a reproducibility regression. Revisit if stale user pins keep causing problems after the doctor advisory. |
| **H. User-extensible catalog** (`llm_provider.extra_models: {codex: [gpt-7]}`), so completion and bare names work before a release. | **Optional, small.** Explicit `provider/model` already works without it (§2, caveat 4), so this is only a completion convenience.                                                                                                                                                                                                                                                                  |

---

## 5. Recommended design

### 5.1 One manifest: `src/sase/llm_provider/models.yml`

This replaces `model_alias_defaults.yml` and the model literals in the seven built-in
provider modules. Sketch:

```yaml
# The single hand-edited file for model catalog and size-alias updates.
# Run `just fix` after editing; `just check` validates rules and docs drift.
schema_version: 2

providers:          # built-in providers only; third-party plugins keep using hooks
  claude:
    tier_defaults: {large: opus, small: sonnet}
    models:
      - {id: opus}
      - {id: sonnet}
      - {id: haiku}
      - {id: claude-haiku-4-5, short: haiku45}
      - {id: claude-fable-5, short: fable}
  codex:
    tier_defaults: {large: gpt-6-sol, small: codex-mini-latest}
    models:
      - {id: gpt-6-astra, short: astra}
      - {id: gpt-6-sol, short: gpt6sol, supersedes: gpt-5.6-sol}
      - {id: gpt-5.6-sol, short: gpt56sol}
      - {id: gpt-5.6-terra, short: gpt56terra}
      - {id: gpt-5.6-luna, short: gpt56luna}
      # …
      - {id: gpt-4o-mini, status: legacy}   # resolvable, hidden from pickers/completion
  grok:
    tier_defaults: {large: grok-4.7, small: grok-4.6}
    models:
      - {id: grok-4.7, supersedes: grok-4.6}
      - {id: grok-4.6}
  muse:
    tier_defaults: {large: muse-spark-1.3, small: muse-spark-1.3}
    models:
      - {id: muse-spark-1.3, short: spark13}
      - id: muse-spark-1.3-contributor
        short: spark13c
        advisory:
          severity: warn
          label: trains on your data
          detail: >-
            Meta uses this model's inputs and outputs to train and improve its AI
            models. …

size_aliases:       # today's model_alias_defaults.yml `aliases:` section, unchanged
  xsmall:
    target: >-
      claude/claude-haiku-4-5@xhigh | codex/gpt-5.6-luna@xhigh |
      agy/gemini-3.8-flash-high | muse/muse-spark-1.3-contributor@medium
    description: Extra-small launch alias for lookup, formatting, and tiny edits with obvious checks.
  # small, medium, large, xlarge …
```

Design notes:

- **Order is meaningful.** Model order within a provider is the completion and picker
  order. `agy` already preserves `agy models` CLI order this way.
- **`supersedes`** is the single new concept, and it does three jobs:
  1. It replaces the effort-ladder test's hard-coded
     `continued_from = {"grok/grok-4.6": "grok/grok-4.7"}`.
  2. It drives the ladder rule "a predecessor continues its successor's descent".
  3. It enables the stale-pin advisory (A8).
- **Leave effort mechanics in Python.** `_EFFORT_CLI_ARGS` (how a level becomes CLI
  flags) is provider behavior and stays in code. The validator reads each provider's
  supported levels from the registry instead of duplicating them. Only add a per-model
  `efforts:` override when a real per-model restriction needs enforcing (Muse's "max
  only on Spark 1.3" is currently left to the CLI and documented).
- **Loading.** Load lazily behind `functools.cache`, the same way
  `_load_model_alias_defaults()` works today, using `sase._yaml_safe.yaml_safe_load`,
  which prefers LibYAML. Measured on a synthetic 436-line catalog: `CSafeLoader` parses
  in about 5 ms and pure-Python `SafeLoader` in about 51 ms. It is parsed once per
  process and already sits behind the process-cached `_llm_metadata_payload()`, so it
  stays off the TUI's per-keystroke paths.
- **Hooks become thin.** Add a default implementation on `LLMProvider` (or a tiny
  mixin) that answers `llm_known_model_names`, `llm_model_short_aliases`,
  `llm_model_advisories`, and `resolve_model_name(tier)` from
  `builtin_model_manifest().provider(<entry-point name>)`. Built-in provider modules
  drop their literals. The metadata payload keeps exactly its current shape, so the
  completion catalog, picker, LSP wire, and Rust code stay untouched. Add a one-time
  parity test: the payload before and after migration is identical.
- **Structural errors fail loudly at load.** The current loader treats a malformed
  shipped YAML as an installation defect; keep that stance for unknown keys, duplicate
  IDs or short aliases, a `tier_defaults` entry or `supersedes` target that isn't a
  same-provider model, and pool members naming an unknown provider/model.
- **Renaming the file is a one-time migration.** Update the references in
  `sase.schema.json`'s `model_aliases.builtin` description, `docs/llms.md`, the
  renderer, the tests, and `decisions:size-alias-effort-ladder`.

### 5.2 Validator: policy rules as code, not as restated values

Implement these in one module, for example `sase.llm_provider.model_manifest_rules`.
Run them from the test suite and from the renderer's `--check`, so `just check` reports
them. Errors must name the fix:

| Rule                  | Check                                                                                                                                                                                              |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1 Membership         | Every `provider/model` pool member is a manifest model of that provider (this check exists today). Warn, don't fail, when a pool references a `status: legacy` model.                              |
| R2 Capability         | A member's `@effort` is in the provider's supported levels. Providers without an effort mechanism (agy) carry no suffix.                                                                            |
| R3 Effort ladder      | The rule from `decisions:size-alias-effort-ladder`, with continuation taken from `supersedes`. Output example: `@small member grok/grok-4.6@low: expected @medium (grok-4.6 continues grok-4.7 from @large at xhigh)`. |
| R4 Redundancy         | Every size alias reaches ≥2 providers through a pool, a fallback, or a last-resort tail.                                                                                                            |
| R5 Shape              | Keep the frozen graph-shape contract from `_model_alias_defaults_fixture.py`. Changing an alias between pool, fallback, and last-resort remains a deliberate code change.                            |

Rules R2–R4 are enforced **in tests and checks, not at runtime load**. A policy
violation should block a merge, not prevent SASE from starting.

### 5.3 Generated docs plus a drift check

Generalize `tools/render_model_alias_docs` into `tools/render_model_docs`. It keeps
running in the formatter venv and reads only YAML, never provider modules. It renders
named `<!-- BEGIN GENERATED: <name> -->` blocks:

| Block                          | Location                                                                     | Replaces                                                                                                                                                  |
| ------------------------------ | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `model-alias-defaults`         | `docs/llms.md`                                                               | (exists)                                                                                                                                                  |
| `known-models`                 | `docs/llms.md` § Automatic Provider Resolution                               | Hand-maintained table (includes the `fakey` row; hidden providers can be flagged in the manifest)                                                          |
| `model-short-aliases`          | `docs/llms.md` § Model Short Aliases                                         | Hand-maintained table                                                                                                                                     |
| `tier-defaults`                | `docs/llms.md` provider sections (or one combined table)                     | Per-provider `large`/`small` tables                                                                                                                       |
| `size-alias-provider-reach`    | `docs/llms.md`; link to it from `README.md`, `docs/getting_started.md`, `docs/agent_providers.md` | Prose such as "reachable through `@small`/`@medium`/`@large` pools and the `@xlarge` fallback". Generate one row per provider, marking pool member, fallback position, or last resort. |

Add `--check`, which renders in memory and exits nonzero on differences. Wire it into
`fmt-check` (CI) and `just check`. This closes the existing drift gap (§1.4 item 7).

For prose, **reference the generated table; don't restate it.** For example: "Grok Build
is never auto-detected, but shipped size aliases can still route to it; see
[which providers each size alias reaches](llms.md#size-alias-provider-reach)." Change a
sentence only when *behavior* changes (for example "`@xlarge` is now an ordered
fallback"), not when membership changes. Delete the prose-pinning assertions in
`tests/test_docs_getting_started_providers.py`, or retarget them to "the page links the
generated table".

Delete or de-specify the commented `builtin:` override example in `default_config.yml`
(about line 1546). It already disagrees with the shipped values. Either point to the
manifest, or keep a deliberately illustrative example that nobody bumps.

### 5.4 Tests: derive expectations from data; assert behavior and rules

- **Replace per-model tests with one parametrized invariant over the manifest.** For
  each non-legacy `(provider, model)`:
  - the bare and `provider/`-qualified names resolve to the provider;
  - the completion catalog contains it, including under the `provider/` filter;
  - the LSP payload contains it;
  - the picker has a row, with its short alias when one is declared.

  This replaces `test_model_completion_catalog_includes_grok_47`, the agy 3.7/3.8 tests,
  both GPT-6 Sol tests, the picker `*_row_includes_alias` tests, and the 32 per-model
  `resolve_model_provider` asserts. Adding a model then needs no test edits.
- **Rewrite `real_model_alias_defaults` routing tests to compute expectations from the
  manifest.** "Priority routing picks the grok member of `@large`" should look up that
  member instead of hard-coding `("grok", "grok-4.7", "xhigh")`. Keep behavior-only tests
  on the frozen fixture, as the fixture's docstring already intends.
- **Remove the `continued_from` dict** from the ladder test; it becomes rule R3 over
  `supersedes`.
- **Keep the tripwire, but move it.** Reviewers see alias changes in the manifest diff
  and the regenerated docs diff. If you also want a machine-checked "did you mean to
  change routing?" signal, add one generated golden file (resolved members per alias,
  written by `just fix`). It shows up as a generated diff, not a hand edit. I consider
  it optional.

### 5.5 Examples policy (A4)

- Placeholders, help text, docstrings, config comments, and docs code examples are
  **illustrative**. Don't bump them for freshness.
- Add a cheap lint, in the same renderer `--check` or a test, that scans docs and
  `src/` string literals for `%model:<x>` and `<provider>/<model>` tokens. It fails
  only if a token names a model that is **not in the manifest**. That catches removals
  without pressuring anyone to chase the newest model.
- For quick-start commands whose purpose is "try provider X" (`README.md`,
  `docs/getting_started.md`), consider a provider-scoped form.
  `resolve_model_provider("grok/")` returns `("grok", "")`; if launch treats that as the
  provider's tier default, the quick-start never needs a version. **Verify** that
  behavior before relying on it.

### 5.6 Decision record

`decisions:size-alias-effort-ladder` should state the rule and not track current
membership. Going forward, retunes should **not** edit it. Records are immutable by
convention, and an aging worked example is harmless. If you want the Grok 4.7/4.6
example made model-agnostic once, do it through an approved plan, following the
`/sase_memory_write` routing. This report does not change any memory.

### 5.7 Optional follow-ups (only if wanted)

- **Stale-pin advisory (A8).** `sase doctor` warns when user config (custom aliases,
  `model_aliases.builtin`, `big_epic_lander_model`) pins a model that the manifest marks
  as superseded. This would currently flag your `sol_or_grok` and `opus_or_grok` custom
  aliases.
- **Refresh the LSP catalog on upgrade.** The LSP JSON is written only when the LSP
  launches, so after a `sase` upgrade editors show the old catalog until the server
  restarts. The Rust server already re-reads the file on every request, so rewriting
  `model_catalog.json` from the upgrade flow would refresh running editors for free.
- **`llm_provider.extra_models`** user-config extension (option H).
- **Nit:** `completion/candidates/catalog_build.py` redefines `_BUILTIN_MODEL_ALIASES`
  instead of importing `BUILTIN_MODEL_ALIAS_NAMES`. The size names are stable, so this
  is harmless, but it is one more copy.

---

## 6. Maintainer workflow after the change

**Adding a model and promoting it (the Grok 4.7 case):**

1. Edit `src/sase/llm_provider/models.yml`:
   - add `{id: grok-4.7, supersedes: grok-4.6}` and set `tier_defaults.large`;
   - swap `grok-4.6` for `grok-4.7` in `@large`/`@xlarge`;
   - adjust `grok-4.6`'s rungs in `@medium`/`@small`. The validator's R3 message tells
     you the exact rung, or `--fix` writes it.
2. Run `just fix` to regenerate the docs blocks.
3. Run `just check` to run the validator, the docs drift check, and the tests.
4. Commit: the manifest, `docs/llms.md` (regenerated), and prose only if behavior
   changed.

| Grok 4.7 commit | Today | After                                                                                                   |
| --------------- | ----- | ------------------------------------------------------------------------------------------------------- |
| Hand-edited     | 19    | **1** (`models.yml`)                                                                                    |
| Regenerated     | 1     | 1–2 (`docs/llms.md`, possibly `docs/ace.md` if a block goes there)                                      |
| Test edits      | 5     | **0**                                                                                                   |
| Prose edits     | ~9    | **0** (the `@xlarge` switch to an ordered fallback is a behavior change and would still earn one sentence) |
| Memory edits    | 1     | **0**                                                                                                   |

**Pool-only retune** (for example Muse contributor into `@medium`): edit 1 file, run
`just fix`, commit.

---

## 7. Phasing, size, and risks

| Phase                          | Content                                                                                                                                                              | Size         |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| 1. Manifest                    | `models.yml` schema v2, loader, thin default hooks, migrate the 7 built-in providers and alias defaults, payload-parity test, rename references.                          | medium       |
| 2. Rules + tests               | Validator R1–R5 with actionable messages; parametrized catalog invariants; rewrite value-pinned routing tests to derive from data; delete per-model and prose-pinning tests. | medium       |
| 3. Docs generation + policy    | `render_model_docs` with 5 blocks and `--check` wired into `fmt-check`/`just check`; rewrite pool prose to link; examples lint; de-specify `default_config.yml` comments. | small–medium |
| 4. Optional                    | Doctor stale-pin advisory, LSP refresh on upgrade, `extra_models`.                                                                                                     | small each   |

Phases 2 and 3 carry most of the benefit. Phase 1 is what lets Phase 3 render every
table from YAML inside the dependency-light formatter venv, and lets the validator see
the catalog and the pools together.

Risks and mitigations:

- **Plugin contract drift.** The hooks remain the public interface, and the manifest
  covers built-ins only. The payload-parity test guards against shape changes.
- **Less test protection.** Rules R1–R5, the generated-docs diff, and optionally a
  golden resolution file replace literal pins. That is stronger than today, because it
  validates the policy rather than a snapshot of one moment.
- **Startup cost.** About 5 ms with LibYAML, once per process, lazily loaded. Keep it
  behind the existing metadata cache.
- **Migration churn.** Renaming `model_alias_defaults.yml` touches its references once.
  If you'd rather avoid that, keep the old filename and add a `models:` section (the
  name becomes a slight misnomer), or use two sibling files under one validator.

---

## 8. Open questions for you

1. **One manifest or two sibling files?** I recommend one (`models.yml`); two is an
   acceptable fallback.
2. **Retirement semantics:** is keeping retired models resolvable but hidden
   (`status: legacy`) acceptable, or do you want hard removal?
3. **Do you want the golden resolution file** (§5.4) as an explicit "routing changed"
   signal, or is the manifest plus generated-docs diff enough review evidence?
4. **Should the stale-pin doctor advisory and `extra_models`** be part of the epic or
   filed as separate tasks?

## 9. Final recommendation

Build **one hand-edited model manifest** (`src/sase/llm_provider/models.yml`) that holds
the built-in model catalog (IDs, short aliases, advisories, tier defaults, `supersedes`,
`status`) and the size alias pools. Built-in provider hooks read from it, and the
metadata payload keeps its current shape, so the TUI completion, model picker, and Rust
LSP need no changes.

Pair it with:

- a validator that turns the effort-ladder and redundancy decisions into rules with
  fix-it messages;
- one renderer that generates every docs table from the manifest, with a `--check`
  enforced in CI;
- tests that derive expectations from the manifest instead of restating it;
- a policy that illustrative examples need not name the newest model.

Do **not** move the catalog into sase-core, discover models at runtime, or compute
efforts automatically. A typical model or alias update then becomes one file, one
`just fix`, and no test or prose edits.
