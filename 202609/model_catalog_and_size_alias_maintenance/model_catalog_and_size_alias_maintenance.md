# Model catalog and size-alias maintenance: one hand-edited file per update

Research synthesis · 2026-09-25 · lead researcher plus `cld`, `grk`, `mus`, and `gem`

**Recommendation:** Do it, but aim at the right target. The runtime is already
single-sourced:

- The size alias pools come from one YAML file.
- The model catalog comes from one hook per provider.
- The TUI prompt input, the model picker, and the Rust xprompt LSP all read one Python-built
  catalog.

The TUI and the LSP are therefore not two surfaces to unify. That work is already done.

The cost of an update is **hand-maintained copies of shipped values**. In the last ten
value-only updates, tests were 42% of the touched files and docs were 37%. Actual sources
of truth were a minority.

The fix, in order of value:

1. **Tests derive their expectations from data and assert rules, not slugs.** This
   removes the largest cost.
2. **Every docs table that mirrors model data is generated, and CI checks it for drift.**
   The generated-block pattern already exists; the drift check does not.
3. **Illustrative examples stop chasing the newest model.**
4. **One hand-edited manifest, `src/sase/llm_provider/models.yml`.** It holds the built-in
   model catalog (ids, short aliases, tier defaults, `supersedes`, optional `status`) and
   the size-alias pools as two sections. Built-in provider hooks become thin readers of
   it. The plugin hook contract, the completion wire payload, and the Rust LSP stay
   unchanged.

After this, a change like the Grok 4.7 commit goes from 19 edited files to **one**
hand-edited file, one regenerated file, and zero test edits. The workflow is: edit
`models.yml`, run `just fix`, run `just check`. Do not move the catalog into sase-core,
do not discover models from provider CLIs at runtime, and do not compute efforts
automatically.

---

## Provenance

The dispatch lists exactly one registered report for each expected suffix. Each report
was matched by `wait_name` and its existing `__<suffix>.md` label, and read through its
canonical research reference with `sase artifact read`. Each was then moved only within
this checkout. Their bytes are unchanged.

| Dispatch dependency | Preserved report                                              | Original canonical reference                                                                               | Registered snapshot                  |
| ------------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `research.c.cld`    | [cld](model_catalog_and_size_alias_maintenance__cld.md)       | `research:202609/model_catalog_update_ergonomics__cld.md`                                                  | `file:explicit:0a632663e68c18f80d050cdf` |
| `research.c.grk`    | [grk](model_catalog_and_size_alias_maintenance__grk.md)       | `research:202609/size_alias_and_model_completion_catalogs/size_alias_and_model_completion_catalogs__grk.md` | `file:explicit:452227777cceaf2e2961d8da` |
| `research.c.mus`    | [mus](model_catalog_and_size_alias_maintenance__mus.md)       | `research:202609/size_alias_and_completion_model_updates__mus.md`                                          | `file:explicit:17b2aa54905fd377957b7e5c` |
| `research.c.gem`    | [gem](model_catalog_and_size_alias_maintenance__gem.md)       | `research:202609/size_model_aliases_and_completion_catalog_maintenance__gem.md`                             | `file:explicit:45bb4a2afb6ca889bfdb2caf` |

I re-checked the claims the reports disagreed on against sase `master` at `266c8b37b`
and its git history, plus the linked `chezmoi` checkout. That covered commit fan-out,
drift checks, existing invariant tests, provider-module contents, LSP materialization,
and user-config pins. I also read `decisions:size-alias-effort-ladder` and
`decisions:rust-core-required`.

---

## 1. What is true today (verified)

### 1.1 The runtime is already one source per concern

| Concept                                | Source of truth                                                                                             | Derived automatically                                                                                                                                             |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Size alias pools `@xsmall`…`@xlarge`   | `src/sase/llm_provider/model_alias_defaults.yml` (its header says "single edit point")                     | Alias resolution, Launch Control, `%model:@…` completion rows and descriptions, and the one generated table in `docs/llms.md`                                   |
| Known models, short aliases, advisories | `llm_known_model_names()` / `llm_model_short_aliases()` / `llm_model_advisories()` in 7 provider modules   | Registry metadata payload, bare-name routing (`model_to_provider`), model picker, `%model` completion                                                             |
| Provider tier defaults (`large`/`small`) | `_TIER_TO_MODEL` literal in each provider module                                                           | `resolve_model_name(tier)`, metadata `model_resolutions`                                                                                                           |
| TUI prompt completion                  | —                                                                                                           | `build_model_completion_catalog()` (`directive_completion.py`, `_file_completion_workers.py`), filtered through `sase_core_rs`                                  |
| External editors (LSP)                 | —                                                                                                           | `sase xprompt-lsp` writes `model_completion_catalog_payload()` to `~/.sase/xprompt_lsp/model_catalog.json`; the Rust server re-reads it on every `%model` request |

The four reports agree on these points:

- No Rust code hardcodes model ids (cld, grk, and mus each checked the linked `sase-core`
  checkout).
- sase-nvim hardcodes no model ids (cld).

The model lists in the provider modules are **pure data**. The only per-model behavior I
found outside those lists is:

- Muse's `_CONTRIBUTOR_MODELS`, which feeds the advisory text;
- a four-row Claude usage-window label map in `usage/_claude_support_windows.py`;
- the `retry.claude.fallback_model: "sonnet"` default.

The CLI effort mechanics (`_EFFORT_CLI_ARGS`) are per-provider, not per-model. Moving the
lists to data therefore does not separate data from the code that interprets it. That was
mus's main objection, and it does not hold on the evidence.

The catalog is also **not a capability gate**. I checked:

- `resolve_model_provider("codex/gpt-7-future")` returns `("codex", "gpt-7-future")`.
- `resolve_model_provider("grok/")` returns `("grok", "")`.

Explicit `provider/model` already works for models SASE has never heard of. The catalog
only drives completion, pickers, short aliases, and bare-name routing. Adding a model is
a UX update, not an enablement blocker.

### 1.2 What an update costs

The alias YAML was created on 2026-07-31 (`f55ce07d1`). It has been touched by **29
commits in 8 weeks**. Retunes come from new models, the effort-ladder decision, and
budget policy (`research:202609/model_alias_budget_policy`), so frequent pool edits are
structural, not a phase. GPT-6 Astra entered `@xlarge` on 09-05 and was replaced by
GPT-6 Sol on 09-24.

These are the ten value-only updates from 2026-08-19 to 2026-09-25. I recounted them from
`git show --name-only`:

| Commit       | Change                                   | Files | Catalog changed | Pools changed |
| ------------ | ---------------------------------------- | ----- | --------------- | ------------- |
| `1cea18e00f` | Add Grok 4.7, retune `@large`/`@xlarge`  | 19    | ✓               | ✓             |
| `682089c845` | Add GPT-6 Sol, make it the Sol default   | 28    | ✓               | ✓             |
| `17084a6e27` | Retune onto Codex luna/terra             | 26    | ✓               | ✓             |
| `28b9ac3888` | Add GPT-6 Astra (also into `@xlarge`)    | 10    | ✓               | ✓             |
| `f546929e46` | Add Gemini 3.8 Flash + `@xsmall` member  | 9     | ✓               | ✓             |
| `97359b9015` | Refresh Muse Spark catalog               | 14    | ✓               |               |
| `65c8169f9d` | Retune sizes to the effort ladder        | 16    |                 | ✓             |
| `e65cc22eeb` | Put Grok in `@xlarge`                    | 13    |                 | ✓             |
| `68d727bbfd` | Muse contributor into small pools        | 6     |                 | ✓             |
| `a0d73f7ea3` | Send xhigh on `@xlarge` grok             | 4     |                 | ✓             |
| **Total**    |                                          | **145** (median 13.5) | 6 | 9  |

**Files touched by category (corrected):**

| Category        | Files | Share |
| --------------- | ----- | ----- |
| tests           | 61    | 42%   |
| docs and README | 53    | 37%   |
| src             | 27    | 19%   |
| memory          | 4     | 3%    |

Two reports got this split wrong. cld reported docs 48% and tests 29%. gem said "over 70%
tests". The direction of both is right (derived material dominates), but tests are the
largest bucket.

**Six test files account for 34 of the 61 test edits.** Each was edited in at least half
of the updates:

- `test_load_balanced_alias_defaults.py` (8 of 10)
- `test_ordered_fallback_aliases.py` (6)
- `test_xprompt_model_completion_catalog.py` (5)
- `test_model_picker_options.py` (5)
- `test_llm_provider_core.py` (5)
- `test_docs_getting_started_providers.py` (5)

**Catalog and pools change together half the time.** 5 of 10 updates changed both, 4
changed only pools, and 1 changed only the catalog. This settles the one-file-or-two
question below.

### 1.3 The hand-maintained copies

1. **Tests that restate shipped values.** Examples:
   - `test_packaged_defaults_select_correct_effort_per_provider` is a literal
     transcription of the YAML's `(model, effort)` pairs for all five aliases.
   - `test_shipped_large_round_robins_claude_codex_grok` pins the exact `@large` member
     tuple.
   - The effort-ladder test hardcodes policy data:
     `continued_from = {"grok/grok-4.6": "grok/grok-4.7"}`.
   - Per-model tests: `…includes_grok_47`, `…gemini_37_flash_variants`,
     `…gemini_38_flash_variants`, `…filters_gpt6_sol`, `…lsp_payload_includes_gpt6_sol`.
   - 32 `resolve_model_provider(...)` asserts in `test_llm_provider_core.py`.
   - `test_docs_getting_started_providers.py` pins a prose sentence about which pools
     reach Grok, and `%model:grok/grok-4.7`.
2. **Docs tables that mirror registry data.** In `docs/llms.md`, "Automatic Provider
   Resolution", "Model Short Aliases", and the per-provider tier tables are
   hand-maintained. Only the alias-defaults table is generated.
3. **Prose that restates pool membership.** It appears in `README.md`,
   `docs/getting_started.md`, `docs/agent_providers.md`, `docs/ace.md`,
   `docs/configuration.md`, and `docs/llms.md`. The Grok 4.7 commit edited 7 prose docs
   for an 8-line YAML change.
4. **Illustrative examples bumped to look current.** These include TUI placeholders
   (`e.g. codex/gpt-6-sol@medium` in three modals), argparse help
   (`parser_bead_lifecycle.py`, `parser_agent_search.py`), a docstring
   (`axe/run_agent_successor.py`), and the `default_config.yml` "grammar examples only"
   block, which still names `gpt-6-sol`/`grok-4.7`. Stale examples work fine: they
   only need to name a model that still exists.
5. **A decision record edited in place.** `decisions:size-alias-effort-ladder` names Grok
   4.7/4.6 and `gemini-3.8-flash-high` in its claim. The Grok 4.7 commit rewrote 33 of its
   lines, which conflicts with the convention that decision records are immutable.

### 1.4 Guardrails that exist, and the gaps

The following already exist, so the "validator" is mostly a refactor, not new machinery:

- `test_every_shipped_selector_member_names_a_registered_provider_model` (pool ⊆ catalog).
  grk thought this was missing; it is not.
- `test_shipped_size_aliases_follow_the_effort_ladder`, with its hardcoded predecessor map.
- Parse and shape tests plus the frozen graph-shape fixture
  (`tests/_model_alias_defaults_fixture.py`). Its docstring says shipped-value changes
  should need no change there.
- `tools/render_model_alias_docs`, which deliberately does not import `sase.llm_provider`
  and runs in the formatter venv.

The gaps:

- **No docs drift check.** `just fix` renders the block, but `fmt-check`, `just check`,
  and CI (`master-gate.yml`, `ci.yml`) never compare `docs/llms.md` to the YAML.
  mus cited `tests/test_render_model_alias_docs.py` as a guard. It compares the
  renderer's in-memory table with the runtime loader, never the file on disk, so a
  skipped `just fix` lands silently.
- **No redundancy rule** (every alias reaches at least 2 providers) beyond a
  provider-specific `@large` test.
- **Tier defaults are an unchecked third decision.** Antigravity's `_TIER_TO_MODEL` still
  points at `gemini-3.7-flash-*`, while 3.8 has been in the catalog and in `@xsmall` since
  09-04. This may be deliberate, but nothing surfaces it.

---

## 2. Critique: is this a good idea?

**Yes.** The update rate is about two per week, the median update touches 13.5 files, and
there is no end in sight. The friction shows up as more than file count:

- Missed spots: the `default_config.yml` example block and Antigravity's tier default.
- A decision record edited in place.
- More than 100-line prose diffs for 4–8-line YAML changes.
- Routing tests rewritten so often that reviewers stop reading them.

Four corrections to how the request is framed:

1. **"As few files as possible" is the wrong metric taken literally.** The right one is:
   - **one hand-edited file per update**;
   - **no knowledge needed of where else to look**;
   - **CI catches everything else**.

   Regenerated docs in the diff are good: they are the reviewer's view of the
   user-visible effect.
2. **The TUI/LSP half of the request is already solved.** Both read one catalog. Adding
   plumbing there solves an old problem.
3. **Moving values into one file without fixing tests and docs saves almost nothing.**
   gem's "test tax" point is the key insight. A manifest alone takes the Grok 4.7 commit
   from 19 files to 18, because only `grok.py` and the alias YAML merge.
4. **Deleting value-pinned tests removes a tripwire.** Today a routing change cannot land
   without someone touching a test. Replace that with:
   - rules that encode the policy (ladder, redundancy, capability, membership);
   - the generated docs table, which is drift-checked in CI and so acts as the reviewed
     snapshot.

   Do not simply delete the tests.

---

## 3. Where the reports disagreed, and how I resolved it

| Question | Positions | Resolution |
| --- | --- | --- |
| Where should built-in model lists live? | cld, gem: one manifest with the pools. grk: a sibling YAML. mus: keep them in Python and add only validation and generation. | **One YAML manifest with two sections.** The lists are pure data (§1.1), so mus's "data next to its interpreter" argument does not hold. The docs renderer must stay provider-import-free, so it needs data files. Half of all updates touch both halves, and the ladder's continuation rule (`supersedes`) crosses them. grk's point that menu membership and routing are separate decisions is real, but separate *sections* serve it. This choice is the least important of the four; two sibling files under one validator would give about 90% of the benefit. |
| Is the size of the problem mostly tests, docs, or code? | cld: docs 48%. gem: tests >70%. mus: "only 1 of 45 test files asserts exact pool strings". | Recount: tests 42%, docs 37%, src 19%. mus's claim is literally narrow but misleading, because six test files churn on most updates. |
| Is there a docs drift check? | mus: yes (parity test). cld, grk: no. | **No.** The parity test never reads `docs/llms.md`. |
| Is pool ⊆ catalog enforced? | grk: no. cld: yes. | **Yes, in tests.** Keep it and fold it into the rules module. |
| Effort capability in YAML (gem's `effort_levels`)? | gem: per-provider list in YAML. cld, grk: keep `_EFFORT_CLI_ARGS` in Python. | **Keep it in Python.** The validator reads supported levels from the registry. gem's sketch shows the duplication risk: it omits Claude's `max`. |
| Advisories in YAML? | cld, grk: yes. mus: stay in Python. | **Optional.** They are rare (Muse only) and do not churn. Allow an `advisory:` key, but moving them is not required for the benefit. |
| Do the LSP/editors go stale? | cld, mus: yes, refreshed only at LSP launch. | True, but it is **user-facing, not maintainer-facing**. `docs/editor.md` already says "restart the LSP after config or plugin changes". Rewriting `model_catalog.json` after `sase` upgrades is a cheap optional follow-up, because the Rust server re-reads it on every request. |

**Factual errors in gem's sketch.** Do not copy its values:

- Claude's `small` tier is `sonnet`, not `haiku`.
- Antigravity's tiers are 3.7, not 3.8.
- Grok has no short aliases.
- Claude supports `max`.

---

## 4. Requirement adjustments (called out explicitly)

| #   | Adjustment | Why |
| --- | --- | --- |
| A1  | **Reframe the goal** as one hand-edited file per update, one regeneration command, and a CI gate for the rest. Regenerated files may appear in the diff. | Generated docs are review evidence. Optimizing raw diff count pushes toward hiding tables. |
| A2  | **Drop the TUI-vs-LSP unification from scope.** Both already consume one catalog. | Verified. No Rust, wire-schema, or `sase-core-revision.txt` change is needed. |
| A3  | **Add: the single edit must be safe.** Rules as code, with fix-it messages: membership, effort capability, effort ladder with continuation from `supersedes`, and redundancy. | Replaces the tripwire that value-pinned tests provided. The ladder's own "Cost" section says one swap can force edits in lower aliases, so the tool should say which rung to use. |
| A4  | **Add: a drift check** for every generated block, wired into `fmt-check`, `just check`, and both CI workflows. | Missing today. Generation without a check is just another copy. |
| A5  | **Add: illustrative examples are exempt from freshness.** They must name a model that still exists, not the newest one. | Removes 3–5 source files and several doc hunks per update. |
| A6  | **Include provider tier defaults in the manifest.** | They are a third copy that changes in the same commits (Grok 4.7, GPT-6 Sol), and Antigravity's has drifted unnoticed. |
| A7  | **Non-goals:** a catalog in sase-core; runtime discovery from provider CLIs; auto-computed efforts; generating every slug mention (README one-liners, blog posts, help text); changing the plugin hook API or the completion wire schema. | See §5. |
| A8  | **Add (small): retiring a model should not break old prompts.** `status: legacy` hides a model from completion and pickers while keeping bare-name routing. | Today, retiring a model means deleting it, which breaks bare `%model:<old>` in saved prompts and forces test edits. |
| A9  | **Stop editing decision records on retunes.** Rewrite `size-alias-effort-ladder`'s worked example once, through an approved `/sase_memory_write` path. | Records are immutable by convention. The rule does not change when a model does. |
| A10 | **Out of scope but real: user configs go stale too.** Verified in the linked chezmoi `sase.yml`: custom aliases `sol_or_grok` and `opus_or_grok` still target `codex/gpt-5.6-sol` and `grok/grok-4.6`, and the xprompt snippets `codex` and `m_agy` pin `gpt-5.6-sol` and `gemini-3.7-flash-high`. | With `supersedes` in the manifest, a `sase doctor` "pinned model is superseded" advisory becomes cheap. File it as a follow-up. |

---

## 5. Options considered

| Option | Verdict |
| --- | --- |
| **Hygiene only:** data-derived tests, generated tables, drift check, examples policy; model lists stay in Python. (mus; grk's phase 1) | **Do this first, whatever else you decide.** It removes most of the per-update file count. Its limit: generating the known-model and short-alias tables would require the renderer to import provider plugins, which it deliberately avoids. |
| **Built-in catalog as data, read by thin hooks** (cld, grk, gem) | **Recommended end state.** Adding a model becomes a data edit. The renderer and validator see catalog and pools together without importing providers. Third-party plugins keep using hooks. |
| **One manifest vs. sibling files** | **One manifest** (see §3), with an acceptable fallback of two files under one validator. Per-provider YAML files (grk's alternative B) add a directory walk and more files per update; reject. |
| **Catalog in sase-core (Rust)** | **Reject.** See the note below. |
| **Runtime discovery** (`agy models`, provider APIs) | **Reject.** Needs subprocesses, authentication, and network access on the completion path. Few CLIs support it, and vendor lists include unusable ids. It would make completion depend on which CLIs are installed. It could later become an advisory `sase doctor` diff. |
| **Auto-compute efforts from the ladder rule** | **Reject for now; validate instead, with an optional `--fix`.** The rule has exceptions: Antigravity has no suffix, and non-primary `\|\|` candidates and last-resort tails consume no rung. Generated efforts would hide changes in the most review-sensitive values. |
| **"Channel" references** such as `codex/:large` that follow a provider's flagship | **Defer.** It would also fix stale user pins (A10), but it changes selector grammar, completion, and docs. It also silently moves pinned users to a new generation, which hurts reproducibility. Revisit if the doctor advisory proves insufficient. |
| **Scaffolding script** (`sase dev model bump`) that edits all the copies | **Reject.** It treats the symptom and must be maintained against moving prose and tests. |
| **Infer the catalog from pool membership** | **Reject.** Pools are a small subset: 57 built-in completable ids versus 10 distinct pool members. |
| **`llm_provider.extra_models` user setting** | **Optional, small.** Explicit `provider/model` already works without it, so it only improves completion before a release. |

**Why not sase-core, given the Rust litmus test?** The boundary memory says that if an
editor integration must match the TUI, the logic belongs in Rust. Three things make the
current split the right one:

- The model catalog is **assembled from pluggy hooks**, so third-party providers can add
  models. Only Python can assemble it.
- The *behavior* both frontends must share, namely wire format, filtering, and ranking, is
  already in Rust (`sase_core::model_completion`, `filter_model_completion_entries`).
- The LSP receives the *data* as a materialized payload, so the frontends cannot diverge.

Moving the data into Rust would turn every model bump into a two-repo change plus a
wheel release and a pin bump. That is the opposite of the goal.

---

## 6. Recommended solution

### 6.1 One manifest: `src/sase/llm_provider/models.yml`

It replaces `model_alias_defaults.yml` and the model literals in the seven built-in
provider modules. The sketch below uses **current** values:

```yaml
# The single hand-edited file for built-in model catalog and size-alias updates.
# Run `just fix` after editing; `just check` validates rules and docs drift.
schema_version: 2

providers:            # built-in providers only; plugins keep using hooks
  claude:
    tiers: {large: opus, small: sonnet}
    models:           # order = completion/picker order
      - {id: opus}
      - {id: sonnet}
      - {id: haiku}
      - {id: claude-haiku-4-5, short: haiku45}
      - {id: claude-fable-5, short: fable}
  codex:
    tiers: {large: gpt-6-sol, small: codex-mini-latest}
    models:
      - {id: gpt-6-astra, short: astra}
      - {id: gpt-6-sol, short: gpt6sol, supersedes: gpt-5.6-sol}
      - {id: gpt-5.6-sol, short: gpt56sol}
      - {id: gpt-5.6-terra, short: gpt56terra}
      - {id: gpt-5.6-luna, short: gpt56luna}
      # … o3, o4-mini, gpt-4.1, …
  grok:
    tiers: {large: grok-4.7, small: grok-4.6}
    models:
      - {id: grok-4.7, supersedes: grok-4.6}
      - {id: grok-4.6}
  agy:
    tiers: {large: gemini-3.7-flash-high, small: gemini-3.7-flash-low}  # see §1.4
    models:           # exact `agy models` slugs; keep CLI order
      - {id: gemini-3.8-flash-high, short: flash38h}
      # …
  muse:
    tiers: {large: muse-spark-1.3, small: muse-spark-1.3}
    models:
      - {id: muse-spark-1.3, short: spark13}
      - id: muse-spark-1.3-contributor
        short: spark13c
        advisory: {severity: warn, label: trains on your data, detail: "…"}
      # …

size_aliases:         # today's `aliases:` section, unchanged grammar
  large:
    target: "claude/opus@high | codex/gpt-6-sol@xhigh | grok/grok-4.7@xhigh"
    description: "Large launch alias for planning-heavy work and default launches."
  # xsmall, small, medium, xlarge …
```

**Rules for the manifest:**

- **`supersedes`** is the one new concept. It does three jobs:
  - it replaces the test's hardcoded `continued_from` map;
  - it drives the ladder rule "a predecessor continues its successor's descent";
  - it enables the stale-pin advisory (A10).
- **`status: legacy`** (A8) hides a model from completion and the picker but keeps it
  resolvable. The validator warns if a pool references a legacy model.
- **Structural errors fail at load**, as today's loader does: unknown keys, duplicate ids
  or short aliases, and a `tiers` or `supersedes` target that is not a model of the same
  provider.
- **Policy violations** (the rules in §6.3) fail tests and checks, never SASE startup.
- **Loading** is lazy, behind `functools.cache` and the existing process-cached metadata
  payload, and stays off per-keystroke paths. cld measured about 5 ms with LibYAML on a
  synthetic 436-line catalog.
- **Effort mechanics stay in Python.** `_EFFORT_CLI_ARGS` is provider behavior, and the
  validator reads supported levels from the registry. Add a per-model `efforts:`
  restriction only when one actually needs enforcing. Muse's `max` works only on Spark
  1.3; the CLI enforces that today.

### 6.2 Thin hooks, unchanged contract

Give `LLMProvider` (or a small mixin) default implementations that answer from
`builtin_model_manifest().provider(<name>)`:

- `llm_known_model_names`
- `llm_model_short_aliases`
- `llm_model_advisories`
- `resolve_model_name(tier)`

Built-in modules then drop their literals. Third-party plugins keep implementing the hooks
in code.

Add a one-time **payload-parity test**: the registry metadata payload and
`model_completion_catalog_payload()` must be byte-identical before and after the
migration. Nothing downstream changes: TUI completion, picker, LSP JSON, and Rust.

The rename touches five references:

- `model_alias_policy.py`
- `sase.schema.json`
- `default_config.yml`
- `docs/llms.md`
- the renderer

To avoid the rename, keep the old filename and add a `providers:` section.

### 6.3 Rules module: policy as code

Put the rules in one module, for example `sase.llm_provider.model_manifest_rules`. Run it
from pytest and from the renderer's `--check`. Most of it moves existing tests into one
place:

| Rule | Check | Status today |
| --- | --- | --- |
| R1 Membership | Every `provider/model` pool member is a manifest model of that provider. Warn on `legacy`. | Exists as a test. Move it. |
| R2 Capability | A member's `@effort` is in the provider's supported levels. Antigravity carries no suffix. | Enforced only at invoke time. Add. |
| R3 Effort ladder | The `size-alias-effort-ladder` rule, with continuation from `supersedes`. Message example: `@small grok/grok-4.6@low: expected @medium (continues grok-4.7 from @large)`. | Exists with a hardcoded map. Move it to data. |
| R4 Redundancy | Every size alias reaches at least 2 providers through a pool, fallback, or last-resort tail. | Only a provider-specific `@large` test. Add. |
| R5 Shape | The frozen graph-shape contract (pool vs. fallback vs. last resort) remains a deliberate code change. | Exists. Keep it. |

An optional `--fix` writes the rungs R3 suggests. That gives the ergonomics of
auto-computed efforts while keeping the file explicit.

### 6.4 Generated docs plus a drift check

Generalize `tools/render_model_alias_docs` into `tools/render_model_docs`. It keeps
reading only YAML and never imports providers. Named blocks:

| Block | Location | Replaces |
| --- | --- | --- |
| `model-alias-defaults` | `docs/llms.md` | Exists |
| `known-models` | `docs/llms.md` § Automatic Provider Resolution | Hand-maintained table |
| `model-short-aliases` | `docs/llms.md` § Model Short Aliases | Hand-maintained table |
| `tier-defaults` | `docs/llms.md` | Per-provider `large`/`small` tables. Seeing this next to the catalog makes drift like Antigravity's visible in review. |
| `size-alias-provider-reach` (optional) | `docs/llms.md`, linked from README, getting-started, and agent-providers | Prose such as "Grok is reachable through `@small`/`@medium`/`@large` and the `@xlarge` fallback" |

**Drift check.** Add `--check`, which renders in memory and exits nonzero on any
difference. Expose it as a `fmt-docs-check` recipe and include it in:

- `fmt-check`;
- `just check`;
- the `master-gate.yml` and `ci.yml` steps that already run `fmt-md-check`.

Make it a recipe, not a pytest: `just check` runs *scoped* tests, which may not select a
docs test when only the YAML changed.

**Prose policy.** Prose should **link to the generated table, not restate it**. Change a
sentence only when behavior changes (for example, "`@xlarge` is now an ordered
fallback"), not when membership changes. Retarget
`test_docs_getting_started_providers.py` to assert the link and the behavior claims only.

### 6.5 Tests: derive expectations from data, assert behavior and rules

- **Catalog invariants, written against the registry payload rather than the YAML.**
  Replace the per-model tests and the 32 `resolve_model_provider` asserts with one
  parametrized test over every non-legacy `(provider, model)`. It checks that:
  - bare and qualified names route to the provider;
  - the completion catalog contains the model, including under the `provider/` filter;
  - the LSP payload contains it;
  - the picker has a row, with its short alias.

  Because it runs over the registry, it works **today, before the manifest exists**,
  survives the migration unchanged, and also covers plugin-contributed models.
- **Routing tests compute their expectations from the shipped data.**
  - `test_packaged_defaults_select_correct_effort_per_provider` should parse each alias's
    members and assert that the resolver picks that member at that effort when only its
    provider is available. This tests resolution behavior against real data, with no
    literal table.
  - Behavior-only tests stay on the frozen fixture, as its docstring intends.
- **Keep product-claim tests, rewritten off slugs.** Assert provider prefixes and modes,
  not ids:
  - `@medium` and below include a Muse contributor model;
  - only `@xsmall` has an Antigravity member;
  - `@large` round-robins Claude, Codex, and Grok;
  - `@xlarge` is an ordered fallback.
- **No separate golden file.** The generated alias table, checked for drift in CI, is the
  reviewed routing snapshot.

### 6.6 Examples policy and the decision record

**Examples.** Placeholders, help text, docstrings, config comments, and docs code blocks
are illustrative. Do not bump them.

- Replace the `default_config.yml` `model_aliases.builtin` example block with grammar-only
  examples, or point it at the generated table.
- Add a cheap lint, in the renderer's `--check` or a test. It scans docs and `src/`
  string literals for `%model:<x>` and `<provider>/<model>` tokens and fails only when a
  token names a model that **no longer exists**. It never fails because a model is not the
  newest.
- For quick-starts whose point is "try provider X", consider the provider-only form
  (`%model:grok/`). Routing returns `("grok", "")`, and provider launch falls back to
  `_TIER_TO_MODEL[tier]` when the override is empty. Verify this end to end before
  documenting it.

**Decision record.** `decisions:size-alias-effort-ladder` should state the rule without
naming current models. Make that change once, through `/sase_memory_write`; this report
changes no memory. After that, retunes never touch it.

### 6.7 Maintainer workflow after landing

For the Grok 4.7 case, **adding a model and promoting it**:

1. Edit `models.yml`:
   - add `{id: grok-4.7, supersedes: grok-4.6}` and set `tiers.large`;
   - swap it into `@large` and `@xlarge`;
   - adjust `grok-4.6`'s lower rungs. R3 names the exact rung, or `--fix` writes it.
2. Run `just fix` to regenerate the docs blocks.
3. Run `just check` to run the rules, the drift check, and the tests.
4. Commit `models.yml` and the regenerated `docs/llms.md`. Touch prose only if behavior
   changed.

| Grok 4.7 commit | Today | After |
| --- | --- | --- |
| Files touched | 19 | **2** (`models.yml` hand-edited, `docs/llms.md` regenerated) |
| Source files (YAML, `grok.py`, `default_config.yml`) | 3 | **1** |
| Test edits | 8 | **0** |
| Prose and README edits (`docs/llms.md` tables edited by hand) | 7 | **0–1** (the `@xlarge` switch to an ordered fallback is a behavior change and earns a sentence) |
| Memory edits | 1 | **0** |

The other update types are also one hand-edited file each:

- a change to both catalog and pools (5 of the last 10 updates);
- a pool-only retune (4 of 10);
- a catalog-only change (1 of 10).

### 6.8 Phasing

Do the no-regret work first, so it pays off even if the manifest slips:

| Phase | Content | Size |
| --- | --- | --- |
| 1. Stop the fan-out | Registry-based catalog invariants; data-derived routing tests; product claims on prefixes; drift check for the existing block, wired into `fmt-check`, `just check`, and CI; neutralize `default_config.yml` examples; examples policy; prose links instead of restating. | medium |
| 2. Manifest | `models.yml` schema v2 (catalog, tiers, `supersedes`, `status`, pools); loader; thin default hooks; migrate 7 providers; payload-parity test; rename the five references. | medium |
| 3. Rules and generated tables | Rules module R1–R5 with fix-it messages and optional `--fix`; `render_model_docs` with the known-models, short-alias, and tier blocks (optionally provider-reach); existence-only examples lint. | small–medium |
| 4. Optional follow-ups | Doctor stale-pin advisory (A10); rewrite the LSP `model_catalog.json` after upgrades; `extra_models`; import `BUILTIN_MODEL_ALIAS_NAMES` in `completion/candidates/catalog_build.py` instead of redefining it; `sase doctor` diff of installed-CLI model lists against the catalog. | small each |

Phase 1 alone removes most test and prose edits, and those are about three-quarters of
the files touched per update. The hand-edited `docs/llms.md` tables and the provider
modules remain until later phases. Phases 2 and 3 make the remaining edit a single data
file and let every table be generated without importing providers.

### 6.9 Risks

- **Plugin contract.** The hooks stay the public interface, and the manifest covers
  built-in providers only. The payload-parity test guards the wire shape.
- **Loss of test protection.** Rules plus the drift-checked generated table validate
  *policy* and show *values* in review. That is stronger than pinning one moment's
  snapshot.
- **Startup cost.** One lazy YAML parse per process, behind the existing metadata cache.
- **A typo in the manifest.** Structural validation at load time, plus the LSP's existing
  best-effort `_materialize_model_catalog`, means a typo breaks `just check` and not a
  user's editor startup.

---

## 7. Open questions for you

1. **One manifest (`models.yml`) or two sibling files?** I recommend one. Two is a fine
   fallback, and the other work matters more.
2. **Retirement semantics.** Is `status: legacy` (hidden but resolvable) acceptable, or do
   you want retired models removed outright?
3. **Is Antigravity's `large`/`small` tier on Gemini 3.7 deliberate?** If not, it is the
   first drift the new tier table will surface.
4. **The ladder decision record.** Should its worked example be made model-agnostic now,
   through an approved memory change?
5. **Epic scope.** Should the doctor stale-pin advisory and the LSP refresh on upgrade be
   part of the epic, or filed as separate tasks?

## Final recommendation

Build **one hand-edited manifest**, `src/sase/llm_provider/models.yml`, with two sections:

- the **built-in model catalog**: ids in display order, short aliases, tier defaults,
  `supersedes`, and `status`;
- the **size-alias pools**.

Built-in provider hooks read from it. The metadata payload, completion wire format, Rust
LSP, and plugin hook contract stay unchanged.

Make the single edit **safe and sufficient**:

- a rules module that turns the effort-ladder and redundancy decisions into checks with
  fix-it messages;
- one YAML-only renderer that generates every model table, with a drift check enforced in
  `just check` and CI;
- tests that derive expectations from the registry and the shipped data, and assert
  behavior and policy instead of today's slugs;
- a policy that illustrative examples and decision records do not track the newest model.

Land it in the order above, starting with tests, drift check, and examples. That work
removes most of the churn with no runtime change and makes the manifest migration a
low-risk data move. Do **not** move the catalog into sase-core, discover models at
runtime, compute efforts automatically, or generate every mention of a model id.

The result: a model or pool update is **one hand-edited file, `just fix`, `just check`**.
