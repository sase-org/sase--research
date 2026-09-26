# Easing size-alias and completion-model updates (`@medium`, `%model`, LSP)

Research report — researcher mus. Goal: help decide the best way to let
maintainers update (a) the default values of the size model alias pools
(`@xsmall`…`@xlarge`, e.g. `@medium`) and (b) the models offered by completion
in the TUI prompt input widget and in external editors (via the xprompt LSP),
by touching as few files as possible. Ends with a plan critique and a
recommended solution.

## TL;DR

Most of the requested consolidation **already exists**, and the remaining pain
is discovery and drift, not file count:

- Size-alias pool defaults already have a single edit point:
  `src/sase/llm_provider/model_alias_defaults.yml`.
- Completion models already have a single edit point *per provider*:
  `llm_known_model_names()` in each provider module — and both the TUI prompt
  widget and the Rust LSP consume the same Python-registry-built catalog, so
  one provider-file edit updates both surfaces.
- The real leftover cost is (1) knowing the secondary places that duplicate
  model names (config comments, docs tables, usage-window keys, retry
  fallback), and (2) nothing failing loudly when they drift.

Recommendation: **do not centralize further**. Keep distributed ownership
(pools in YAML, provider models in provider modules, per the plugin-hook
contract), and add centralized *validation* (a referential-integrity test)
plus *generation* (extend the existing docs renderer to the model tables).
Details in "Recommended solution".

## What exists today

### Size-alias pools: one YAML file

`src/sase/llm_provider/model_alias_defaults.yml` declares all five built-in
aliases (`xsmall`, `small`, `medium`, `large`, `xlarge`), each with a `target`
pool expression and a `description`. `model_alias_policy.py` documents the YAML
as "the single change needed" and owns only name constants plus the loader.
User overrides merge on top (`llm_provider.model_aliases.builtin`), so shipped
changes never fight user config.

Surrounding machinery already supports cheap updates:

- `tests/_model_alias_defaults_fixture.py` freezes *distinct* alias values for
  resolution-behavior tests, with an explicit docstring: "Shipped-value changes
  … need no change here." Only graph-shape changes (target vs fallback,
  fallback retargeting) require test edits — an intentional contract, not
  coupling.
- `tools/render_model_alias_docs` regenerates the alias-defaults table in
  `docs/llms.md` from the YAML (`just fmt-docs`), guarded by markers
  `BEGIN/END GENERATED: model-alias-defaults` and a parity test
  (`tests/test_render_model_alias_docs.py`).
- Scalar launch defaults in `default_config.yml`
  (`default_model: "@large"`, `epic_lander_model`, `big_epic_lander_model`)
  point at aliases, not concrete models, so pool edits propagate for free.

### Completion models: one catalog, two consumers

`src/sase/xprompt/model_completion.py::build_model_completion_catalog()` builds
the ordered `%model` value list from the cached LLM registry metadata payload:
per-provider `known_model_names`, `model_short_aliases`, `model_advisories`,
plus implicit size aliases and user aliases via `build_alias_views`.

Both consumers read this one catalog:

- **TUI prompt widget**: `directive_completion.py` passes
  `catalog_builder=build_model_completion_catalog`; background workers
  (`_file_completion_workers.py`) call it directly. Covers `%model:`,
  `=alias`, and `==model` paths (alias shortcut candidates filter the same
  entry list).
- **External editors**: `_prepare_xprompt_lsp_environment()` in
  `src/sase/integrations/xprompt_lsp.py` materializes
  `model_completion_catalog_payload()` to
  `~/.sase/xprompt_lsp/model_catalog.json` at LSP launch; the Rust server
  (`crates/sase_xprompt_lsp`, `server/catalogs.rs::load_model_catalog`,
  `completion_items.rs`) re-reads that file per completion request.

Verified in the linked `sase-core` checkout: no non-test Rust code hardcodes
model names (only a `"opus"` unit-test fixture string and an `@large` doc
comment). The Rust side needs **zero** changes when models change — no
`sase-core-revision.txt` bump, no cross-repo dance. This respects the
Rust-core boundary correctly: the catalog is data over the wire, not shared
logic.

Net: renaming/adding a provider model = edit that provider's
`llm_known_model_names()` (+ short aliases) and both completion surfaces
follow. If the model also appears in alias pools, edit the YAML too.

## Full inventory: every place a model change can touch

Primary (functional — behavior or completions change):

1. `src/sase/llm_provider/model_alias_defaults.yml` — pool members/efforts.
2. `src/sase/llm_provider/<provider>.py` ×7 (`claude`, `codex`, `muse`,
   `grok`, `agy`, `qwen`, `opencode`; `fakey` is test-only) — each owns three
   coupled lists: `llm_known_model_names()`, `llm_model_short_aliases()`, and
   module `_TIER_TO_MODEL` (large/small launch defaults), plus `_EFFORT_CLI_ARGS`
   and advisories (e.g. Muse contributor warnings).
3. `src/sase/llm_provider/usage/_claude_support_windows.py` — subscription
   usage windows keyed by exact slug (`claude-haiku-4-5`, `sonnet`, `opus`). A
   rename silently breaks usage accounting, the nastiest drift on this list.
4. `default_config.yml` `retry.claude.fallback_model: "sonnet"` — a bare model
   name used as a retry fallback. Goes stale the same way.

Secondary (docs/examples/comments — drift is cosmetic but erodes trust):

5. `default_config.yml` commented `model_aliases.builtin` examples — already
   stale (medium example omits `muse`/`agy` members present in shipped
   defaults, uses `@low`/`@medium` efforts the shipped pools don't). The
   comment says "grammar examples only", but readers copy them.
6. `docs/llms.md` hand-maintained tables: known-model→provider and short-alias
   tables (~lines 1657–1700). Only the alias-defaults table is generated.
7. Prose/examples across `docs/configuration.md` (~`gemini-3.7-flash-high`,
   `muse-spark-1.3`), `agent_providers.md`, `xprompt.md`, `getting_started.md`,
   blog posts; CLI `--help` epilogs (`parser_monitor.py`, `parser_pipe.py`
   cite `opus`/`codex/gpt-5`); TUI placeholder strings
   (`models_panel_override.py` "e.g. codex/gpt-6-sol@medium"); widget/parser
   docstrings.

Non-issues verified:

- `sase doctor` alias checks (`checks_config_model_aliases.py`,
  `checks_config_common.py`) reference alias *names* (`@medium`) and grammar,
  never concrete models.
- The size template (`memory-sase-sizes.template.md`) references size names
  only — no model slugs.
- Only 1 of 45 model-name-mentioning test files asserts exact shipped pool
  strings; the rest use the frozen fixture or unrelated values.

## Plan critique

**Is it a good idea? Yes — but narrow it.** The request as stated ("update both
by updating as few files as possible") invites over-centralization. Two
counter-pressures matter:

1. **Provider model lists must stay with provider modules.** They are plugin
   data: third-party providers contribute through the
   `llm_known_model_names()` hook, and each list sits next to the code that
   interprets it (CLI model flags, effort-arg maps, tier defaults, auth
   evidence). Pulling all names into one central `models.yml` would break the
   hook contract, split data from its interpreter, and create a merge
   bottleneck — while saving nothing, since a rename already touches exactly
   one provider file.
2. **"Few files" is already achieved for behavior; the pain is silent drift
   in secondary copies.** Today's actual cost of a model rotation is: 1
   provider file + optionally the alias YAML + `just fmt-docs` + a nagging
   feeling you missed a docs table. Optimizing further by moving code around
   has negative ROI; making misses *loud* has high ROI.

**Requirement adjustments I would make (calling them out):**

- (a) Drop any goal of "one file for all models". Replace with: "one
  *authoritative* file per concern, everything else generated or tested."
  That is: pools → YAML (done); provider models → provider module (done,
  document it); docs tables → generated (to do); consistency → tested (to do).
- (b) Add an explicit non-goal: no changes to the plugin hook API and no Rust
  changes. Both surfaces are already catalog-driven; churning them risks the
  boundary for no gain.
- (c) Treat LSP staleness explicitly. The Rust server re-reads the catalog
  JSON per request, so rewriting `model_catalog.json` updates external editors
  *without* an LSP restart — but nothing re-materializes it today except LSP
  launch. Decide: document "restart editor/LSP after model updates" or add a
  refresh trigger. The TUI path is config-token-cached and picks up changes on
  config reload. Either is fine; leaving it unspecified guarantees confusion.
- (d) Scope the effort-ladder decision (`size-alias-effort-ladder`) out.
  Pool-member `@effort` suffixes interact with first-appearance-xhigh
  behavior; changing efforts while "simplifying" risks altering which rung a
  size launches at. Any tooling touching pool targets should preserve effort
  suffixes verbatim and say so.

## Recommended solution

In priority order. Items 1–2 are the core; the rest are small follow-ups.

1. **Add a referential-integrity test** (highest value, small):
   new `tests/llm_provider/test_model_catalog_integrity.py` asserting —
   against the *shipped* YAML and the live registry — that every
   `provider/model[@effort]` pool member resolves (known model or resolvable
   alias, valid effort), every `_TIER_TO_MODEL` value is a known model of its
   provider, and every usage-window key in `_claude_support_windows.py`
   matches a known model. Failure message names the file to edit. This
   converts today's silent drift (stale retry fallback, dead pool members
   after a rename) into a red test at the commit that causes it.
2. **Generate the remaining model tables in `docs/llms.md`.** Extend
   `tools/render_model_alias_docs` (or a sibling renderer run from the same
   `just fmt-docs` recipe) to emit the known-model→provider and short-alias
   tables from the registry under new `GENERATED` markers, and add a CI
   freshness check so hand-edits to those regions fail. This removes the
   largest hand-maintained duplication (item 6 above).
3. **Scrub `default_config.yml` examples.** Replace the stale commented
   `model_aliases.builtin` block with grammar-only examples using obviously
   fake model names (or point at the generated docs), so nobody copies dead
   values. Fix the `tmux_agent.providers.claude.model` example pin
   (`gemini-3.7-flash-high`) the same way.
4. **Make `retry.claude.fallback_model` alias-aware or self-healing.**
   Cheapest correct option: resolve it through the normal `%model` path at
   runtime (so `@small` works) and fall back with a warning when it names an
   unknown model, rather than failing or misrouting. Covered by the integrity
   test in item 1 either way.
5. **Key usage windows by family, not exact slug** (or at minimum cover them
   in item 1's test). Prefix/family matching (`claude-haiku-*`) survives
   dated-version rollovers (`haiku-4-5` → next) without edits.
6. **Publish the maintainer checklist** (docs, ~10 lines): "rotating a model:
   edit provider file → update pools YAML if member → `just fmt-docs` →
   integrity test runs in CI." The checklist is the actual deliverable for
   the 'how often we need to do it' complaint; items 1–2 make each step
   verifiable.

**What this achieves:** a pool-values rotation stays a 1-file edit (+ generated
docs refresh); a provider model rename stays a 1-provider-file edit (+ YAML
only if pooled); every other copy either generates itself or breaks a test
that names the fix. No hook API changes, no Rust changes, no revision-pin
churn, no new config schema — and no new central file for plugins to fight
over.

## Sources inspected

- `src/sase/llm_provider/model_alias_defaults.yml`,
  `model_alias_policy.py`, `model_alias_config.py`
- `src/sase/llm_provider/{claude,codex,muse,grok,agy,qwen,opencode,fakey}.py`
  (known names, short aliases, `_TIER_TO_MODEL`)
- `src/sase/xprompt/model_completion.py`, `_model_completion_catalog.py`
- `src/sase/ace/tui/widgets/{directive_completion,model_alias_completion}.py`,
  `_file_completion_workers.py`
- `src/sase/integrations/xprompt_lsp.py` (catalog materialization)
- Linked `sase-core`: `crates/sase_xprompt_lsp/src/` (non-test sources;
  catalog-driven, no hardcoded models)
- `src/sase/default_config.yml` (llm_provider section, retry fallback,
  stale examples), `src/sase/doctor/checks_config_*.py`,
  `memory-sase-sizes.template.md`
- `tests/_model_alias_defaults_fixture.py`,
  `tests/llm_provider/test_model_alias_defaults.py`,
  `tests/test_render_model_alias_docs.py`, `tools/render_model_alias_docs`,
  `docs/llms.md`, `Justfile` fmt-docs recipe
