---
create_time: 2026-08-14
updated_time: 2026-08-14
status: research
tags: [ace, artifacts, patch, contract, query-language, relations, tui, sase-core]
---

# One Artifacts Contract: Query, Relations, and Patch Inside It

**Research question.** Unify every ACE Artifacts sub-tab behind one API/contract so a
sidecar or artifact repo declares how its tab behaves, and so any new sub-tab feature is
implemented once and inherited by every configured provider — including providers
belonging to users we will never see. **Patch is in scope** and must move to the same
look and feel as its siblings. Before that, generalize Patch's best features — the
boolean search syntax, saved queries, the ancestors/children/siblings jumpers — into
contract features rather than Patch features.

**Scope and evidence.** Consolidates two independent research passes —
[`__a`](artifacts_query_and_pane_contract__a.md) (`research.0j.cdx`) and
[`__b`](artifacts_query_and_pane_contract__b.md) (`research.0j.cld`) — plus a third
verification pass by this lead. Both supersede
[`artifacts_pane_contract.md`](../artifacts_pane_contract/artifacts_pane_contract.md)
(2026-08-12), whose central recommendation — keep Patch out — the owner has overruled.
Sources read at `sase` `e4baf0771` (master, clean), `sase-core` `4170150` (v0.27.2),
`sase-research-artifacts` `a7d9e0499`. Every claim reproduced below was re-checked
against those trees by the lead; claims carried from `__a`/`__b` without independent
verification are marked *(unverified here)*.

Where the two passes disagreed, §2 resolves it with reproduced evidence, and in two of
three cases **neither report was right**.

---

## Bottom line

Build **one behavioral contract with multiple adapters** — not one generic widget, not a
plugin callback API. Both passes reached this independently, which is the strongest
signal in this report:

```text
sidecar provider declaration      fields, relations, safe presentation hints
        ▼
sase-core query + relation core   typed rows, profile-driven AST, relation index
        ▼
ACE ArtifactsPaneContract         common shell + derived capabilities + pane session
        ▼
built-in or declarative adapter   Patch is rich; document providers get defaults free
```

Land it in `__b`'s five dependency-ordered layers, because that is the schedule that
actually splits into beads: **L0** one stable `ArtifactEntryTarget` on every pane
including Patch → **L1** `ArtifactsPaneContract` + closed `PaneCapability` → **L2** one
query engine → **L3** relations and grouping → **L4** the declarative `ref.pane` block.

Three corrections this pass makes to both reports:

1. **The Patch query parser is already in Rust.** `sase/core/query_facade.py` calls
   `sase_core_rs.parse_query`; `crates/sase_core/src/query/` is 3,428 lines of
   tokenizer, parser, matchers, searchable corpus and batch evaluator, with a parity
   test. The L2 job is **de-Patch-ifying an engine that already exists in the right
   place**, not writing a new Python one (`__b`) or moving one there (`__a`).
2. **The provider spec needs no `schema_version` bump.** The no-bump constraint `__b`
   found is real and correctly quoted, but it constrains the *version integer*, not
   *additive fields*. There is no `deny_unknown_fields` on the provider-spec wire, so
   optional additive fields are free at v1 today — that is exactly how `icon` shipped.
3. **Capabilities must be derived from declared data, not declared by the provider.**
   `__a` is right and `__b`'s L4 "safe capability subset" is wrong, and this is the
   difference that decides whether the owner's actual goal is met — see §2.3.

The single highest-leverage fact for the stated goal: **`ref.properties` already carries
`type`, `values` and `source`, is already validated in Rust, and is already on the tab
descriptor.** Every declared property becomes queryable, completable and facetable the
moment L2 reads it — with no spec change, no wire change, and no work by the sidecar
author. That is the "one implementation, every unknown user's sidecar benefits" payoff,
and it is available at schema version 1.

---

## 1. Where both passes independently agree

High confidence; treat as settled.

| Agreement | Consequence |
| --- | --- |
| Patch joins the contract as the **richest built-in adapter**, not an exception | Unification means shared shell, chrome and interaction grammar — not identical rows |
| Patch is **contract-in, spec-out** — `patch` is in `RESERVED_KINDS` (`provider_spec.rs:27`, verified), so it can never be a document provider | It consumes `ArtifactsPaneContract` from a built-in Python table; it never declares one. Write this asymmetry into the docs |
| Providers declare **facts, not UI code** | No callbacks, widgets, colours, keybindings, command strings or Python entry points in sidecar config, ever |
| No provider code may run during **render, navigation, completion or query evaluation** | Declarations are compiled at discovery; the host always knows which path can block |
| Relations are **typed directed edges** the host indexes, with the jumper UI host-owned | Providers name a property; the core derives inverses and detects cycles |
| Saved queries become **pane-scoped**, migrated not reproduced | Slot `1` on Research must not jump to Patches |
| Presentation stays **Python**; a **Python-side presentation digest** is required | A Rust-modelled pane block would produce a core-version-dependent digest |
| One invalid provider must produce a **visible degraded tab**, never a vanished one | Diagnostics travel with the snapshot |
| Marks-by-index must be **replaced, not preserved** | Not a Patch feature; a Patch defect that breaks under refresh and re-sort |

---

## 2. Three disagreements, resolved

### 2.1 Where the query engine lives — *neither report had this right*

`__a` proposes moving parsing/validation/evaluation into `sase-core` as Phase 1. `__b`
proposes building `sase/artifact_query/` in Python, proving it across five panes and
three CLI surfaces, then lifting it — arguing that lifting first would freeze a field
schema that three existing dialects disagree about.

**Verified: the syntax layer is already in Rust and already shared.**

```text
src/sase/core/query_facade.py:33   parse_query -> require_rust_binding("parse_query")
crates/sase_core/src/query/        tokenizer, parser, types, matchers, searchable,
                                   evaluator, tests  — 3,428 LOC
crates/sase_core/tests/query_evaluator_parity.rs     parity harness already exists
```

Non-TUI callers already depend on it: `main/search_handler.py`, `main/axe_handler.py`,
`main/ace_handler.py`, `axe/lumberjack.py:103`, `axe/cli.py:310`. The repo's own
Rust-boundary litmus test is therefore already satisfied for the Patch language.

That makes `__b`'s plan a regression *for Patch specifically*: it would fork a Rust
engine back into Python, and it guarantees an interim state with two engines (Rust for
Patch, new Python for everyone else) — the exact condition the epic exists to remove.
And it makes `__a`'s Phase 1 a description of work that is already half-done.

What is actually Patch-shaped inside the Rust module, and what each becomes:

| Rust site | Patch coupling today | Contract form |
| --- | --- | --- |
| `query/tokenizer.rs:9,415` | `VALID_PROPERTY_KEYS` const allowlist | Field set supplied by the compiled profile |
| `query/tokenizer.rs:317,345,359` | `%`→`status`, `^`→`ancestor`, `~`→`sibling` emitted inline | `sigil → field` map on the profile |
| `query/matchers.rs:38,55,94` | `strip_reverted_suffix`, `(!: …)` error marker, name match | Declared predicates (`__b` §3.1) registered by the profile |
| `query/searchable.rs` | hand-written Patch corpus flattener | `join(values where field.searchable)` |
| `query/evaluator.rs:90,102` | `QueryCorpus::new(Vec<ChangeSpecWire>)` | Generic over a typed row |

**Resolution — and it dissolves `__b`'s objection rather than overriding it.** Keep the
syntax layer in Rust and make it **profile-parameterized, where the compiled profile is
a call argument rather than a persisted wire.** A per-call argument freezes nothing:
the field-schema shape can churn across releases without a `schema_version` bump,
because it is never serialized into a spec or a saved file. `__b`'s freezing risk is
real and this is the shape that avoids it; `__a`'s destination is right and this is how
to get there without a v2.

Authoring stays in Python — an `ArtifactQuerySchema` per pane, compiled down to the
profile at pane construction — so `__b`'s "prove it across five panes before committing
the shape" discipline is preserved in full. What crosses the binding is a profile, not a
schema.

Only completion, highlighting and the Textual bar stay unambiguously Python.

### 2.2 The wire-version constraint — `__b` quoted it correctly, then over-read it

Verified verbatim at `provider_spec.rs:18-25`:

> Adding `icon` as a required field is a breaking wire change, and the textbook move
> would be to bump this from 1 to 2. Do not: CI installs the published floor
> `sase-core-rs` and runs it against this checkout, which would reject a
> `schema_version: 2` spec before core carrying the bump is ever released.

`__a`'s rollout ("release core support, temporarily accepting v1 and v2") **does not
work as written**: the rejector is the *floor* core, so a new core accepting both changes
nothing while CI installs the floor. `__b` is right to flag this.

But `__b`'s conclusion — "the wire version must not be bumped", "this kills the option
of modelling `ref.pane` in Rust at all" — is stronger than the evidence. Verified: no
`deny_unknown_fields` anywhere on the provider-spec wire (it appears only in
`runner_limit_override.rs` and `axe_overrun/wire.rs`), and the floor is a ratchet
(`pyproject.toml:46` → `sase-core-rs>=0.27.2,<0.28.0`, with
[`core_dependency_window_ratchet`](../core_dependency_window_ratchet/core_dependency_window_ratchet.md)
already covering how to automate it). The actual rule:

| Change | Cost |
| --- | --- |
| **Additive optional field** (`#[serde(default)]`) | **Free today at v1.** Floor cores ignore it; new cores validate it |
| Making a field **required** / enforcing new semantics | Two releases: core ships the validator → floor ratchets → specs emit it |
| `schema_version: 2` itself | Only after the floor is at-or-above the core that understands it |

That this failure mode is not hypothetical is on record: bead **`sase-lm`** ("floor is
0.26.10 but task wire schema v2 shipped in 0.27.0, failing 64 tests") is a live instance
of a wire bump landing ahead of its floor. Treat the two-release ordering as a hard
rule, not a caution.

Almost everything this epic needs from the spec is additive and optional, so it proceeds
at v1. `ref.pane` should still stay Python-only — but for `__b`'s *second*, better
reason (a Rust-modelled block digests against whichever core is installed, so the
content digest becomes core-version-dependent), not because the wire can never move.

**Do add** `REF_PANE_CONFIG_KEY` to `_KNOWN_REF_CONFIG_KEYS` (`sidecar_ref_config.py:65`)
or inline `ref: pane:` will fail validation while a `use:`-provided plugin spec silently
succeeds — the two paths already diverge *(carried from `__b`, unverified here)*.

### 2.3 Derived capabilities vs. declared capabilities — `__a` wins

`__a` §3.5: providers declare data facts and the **host derives** capabilities — an
inventory plus fields implies filter/history/saved views; a hierarchy relation implies
`<`/`>`; stable refs imply copy-reference; revision metadata implies versions.
`__b` §4.4 has providers declaring "`capabilities` from a safe subset" in `ref.pane`.

This is not a style difference; it decides whether the owner's stated goal is met.
Derivation gives three things declaration cannot:

1. A provider **cannot claim a feature its data cannot support** — no diagnosing "why is
   `~` a no-op on this tab".
2. It keeps boolean soup out of provider YAML.
3. **A new host capability lights up for providers written before it existed**, with no
   provider release. That is precisely "all custom sidecar repos, even ones configured
   for users we don't know about, get new functionality for the cost of a single
   implementation."

Keep `__b`'s closed `PaneCapability` enum as the *vocabulary* every downstream surface
reads. Change only who computes the set: the host, from declared data. The one thing
providers may legitimately *suppress* is a capability they don't want (an opt-out flag),
never assert one they haven't earned.

---

## 3. Patch's "coolest features", generalized

The owner's precondition. Each row: what exists, why it is Patch-shaped, what it becomes.

| Feature | Today | Contract form |
| --- | --- | --- |
| **Boolean grammar** — `AND`/`OR`/`NOT`/`!`/parens/implicit-AND/`c"…"` | Rust tokenizer + parser; flat `VALID_PROPERTY_KEYS` allowlist | Profile-driven fields; grammar unchanged. `boolean=False` degrades to today's flat token dialect exactly, so the other panes migrate byte-identically then opt in |
| **Sigil shorthands** `%d +p ^a ~s &n` | Emitted inline in the Rust tokenizer | Per-profile `sigil → field` map. Beads could declare `#`→`type` without touching the tokenizer. Keep the vocabulary **host-validated and closed** (`__a` §3.2) — not arbitrary punctuation owned by providers |
| **State markers** `!!! @@@ $$$ *` | Hard-coded Patch predicates | **Declared zero-arg predicates**: name + sigil + label + matcher. Candidates exist everywhere the moment the mechanism does (`@@@` on Beads = has a launched agent; `!!!` on Stitches = has a failed hook) |
| **Saved slots 0–9** | Global flat `~/.sase/saved_queries.json`; loading one **hard-switches to Patches** (`actions/patch/_query.py:58-67`, verified) | `{pane_id: {slot: …}}`, gated by `QUERY_SLOTS`, with the source text **plus** canonical form **plus** profile digest (`__a` §5) so a renamed field yields a visible invalid view instead of silent reinterpretation. Stay behind the `0` prefix and the `*` picker — bare digits are spent on sub-tab selection |
| **`#N` save grammar** | Implemented only inside a modal dismiss callback (`actions/base.py:493-544`) — undiscoverable, untestable | Moves to the shared filter bar's submit handler, where completion can advertise it |
| **Prev/next history** `^`/`_` | Global, gated only on `current_tab != "artifacts"`, so `^` on Beads rewinds the *Patch* query behind a hidden pane | Keyed by `pane_id`, gated by `QUERY_HISTORY`. Smallest generalization; fixes a live cross-pane bug on the way |
| **Per-query selection memory** | `canonical_query → patch name`, 60 lines, no other pane has it | `{pane_id: {canonical_query: ArtifactEntryTarget}}` — the clearest argument for doing **L0 identity first**, since the persisted value must be a target Patch does not yet have |
| **Ancestors / children / siblings** | `ancestors_children_panel.py` (612 lines) over `PatchGraphIndex`; `navigation/_tree.py` (346) drives `<`/`>`/`~` and the multi-key child buffer | `RelationFamily` set on the contract; host owns key assignment, panel, hints and fallback. Panel becomes `RelationPanel` in the shared shell |
| **Out-of-set jumps** | `_change_query_for_navigation` **rewrites the query** to `ancestor:<name>` (`_tree.py:293-346`) | `__b`'s sharpest structural finding: **the jumper and the query language are one feature**, which is why L3 cannot precede L2. Generalize the rewrite as the mechanism (`__b`) but present it as a **reversible identity lens** with a "return to query" affordance (`__a` §3.6) — jumping a graph should not destroy a composed query |
| **Grouping + folding** `o`/`O`, `l`/`h`/`L`/`H`, collapsed banners as jump targets | Already on the **generic** `GroupFoldRegistry` — docstring reads *"shared by Agents and Patches"*, keyed `tuple[str, ...]`, verified | `grouping: tuple[GroupingMode, ...]` on the contract; providers declare `group_by`. The one layer here that needs a third consumer, not a design |

Two relation shapes are needed, and `__a` is the only pass that separates them
correctly: **hierarchy** (directed, transitive, parent/child) and **family** (an
equivalence class over a grouping key). Patch "siblings" are a family — a normalized
base name including reverted variants — not graph siblings. Collapsing both into a
parent pointer would lose Patch semantics. Add **link** for ordinary typed edges
(produced-by, owns, documents), including cross-kind ones.

**Allow cross-pane relation targets in the wire from day one** even if the first UI only
opens them (`__a` §10.4). Retrofitting pane identity into relation targets later is
expensive.

### 3.1 The first non-Patch family already exists, and this file is in it

Neither pass noticed: the research sidecar already encodes a family relation in
filenames. A swarm bundle is `<name>/<name>__a.md`, `<name>__b.md`, `<name>.md` — the
consolidated report is the parent, the drafts are the family. It is structurally
identical to Patch's `__<N>` siblings, generalizing to `__([a-z]+|\d+)$`.

That makes it the ideal **first non-Patch conformance case for L3**: it needs no new
frontmatter, no schema change and no work from the sidecar author, and it proves the
family primitive on a real third-party provider rather than on a built-in. It is also a
feature the owner would actually use — jumping between a consolidated report and its two
source drafts is the same motion as jumping a Patch family.

---

## 4. The contract

### L0 — one identity (mechanical, invisible, unblocks everything)

Patch already has a stable identity *outside* the TUI: `builtin_entry_patch.py:60` mints
`stable_id=f"patch:{project}/{patch.name}"`. The TUI just doesn't use it. Verified:
`ArtifactsView.entry_navigator` raises `ValueError("Patches use the existing Patch
navigation model")` (`view.py:189-195`).

- `patch_row_target(patch) -> ("patch", project, name)`, matching the four siblings.
- `marked_indices: set[int]` → `_artifacts_marked_targets["patches"]`;
  `action_toggle_mark` loses its pane branch. `EntryJumpAnchor` becomes
  `ArtifactEntryTarget | PatchBannerJumpAnchor`.
- Patches finally gets an `@patch:` copy target — a live ref kind with a resolver, with
  no way to copy one from the pane that displays them.
- **Close the protocol hole while here**: `ArtifactEntryNavigator` is a `Protocol` whose
  `request_entry_target` / `conditional_footer_entries` are implemented on only two of
  four panes, papered over with `getattr(pane, …, None)`
  (`actions/artifacts_navigation.py:101,117`) *(carried from `__b`, unverified here)*.
  Make it an ABC.

Only user-visible change: marks survive refresh. That is a fix.

### L1 — `ArtifactsPaneContract`

`__b`'s dataclass, with capabilities **derived** per §2.3. Lives beside
`ArtifactsTabDescriptor` in the widget-free `artifact_tabs.py`; carries id, label, icon,
accent, order, digit, `ref_kind`, `target_prefix`, `project_scoped`,
`presentation_digest`, `capabilities`, `query_schema`, `relations`, `grouping`,
`detail_fields`, `status_counters`, `empty_state`, `copy_targets`.

Every downstream surface reads `capabilities` instead of comparing pane ids: footer,
`_app_action_availability.py`, the help modal's hand-written per-pane sections, the
command palette, the copy registry, the conformance test. **Measured: 26 `ref:`-prefix
dispatch sites across 13 files in `src/sase/ace/tui/`** — `__a` said "twelve files",
`__b` said "13 sites"; both approximately right, precisely 13 files / 26 sites. Two live
inside `view.py` alone, including a `plans-detail-scroll` fallback for every provider
pane.

Digits and accents stay **host-assigned**, never provider-assigned.

### L2 — one query engine

Per §2.1: profile-parameterized Rust syntax layer; `ArtifactQuerySchema` authored in
Python and compiled to a per-call profile. Three properties make it safe to land
incrementally, and they are `__b`'s, kept whole:

1. **It is a superset of all three dialects.** `boolean=False` reproduces today's flat
   token language exactly, so each pane migrates independently and revertibly, then opts
   into `OR` and parens.
2. **Every canonical form is preserved**, so saved queries and history files stay
   readable across the migration.
3. **Free text stops being special** — `searchable=True` flags replace the hand-written
   corpus builder.

There are **three** languages, not two, and the third is the accelerator. Verified:
`ace/agent_query/tokenizer.py:1-11` is a self-declared fork of `ace/query/tokenizer`
whose stated differences include exactly the thing the unified design needs — a **typed
property-key registry** (`SUBSTRING_/ENUM_/BOOL_/DURATION_PROPERTY_KEYS`, lines 34-60),
plus comparison operators and duration literals. `ace/query` still has a flat frozenset
(`tokenizer.py:31`). Most of the typed-key design has already been written once, by
hand, for the Agents tab.

`FilterBar` is likewise already the right shape: `ACCENT`, `KEY_COMPLETIONS`,
`STATIC_VALUE_COMPLETIONS`, `VALUE_HINTS`, `REPEATABLE_VALUE_KINDS`, `NEGATABLE_KEYS`,
`FREE_TEXT_HINT`, `PERSISTENT` — a field schema written as class attributes, satisfied
by all four subclasses in under 100 lines each (verified). Two bugs fall out for free
when it is configured from the contract instead: **`FileFilterBar` alone omits
`NEGATABLE_KEYS`**, so `-key:` silently works on three panes and not the fourth; and
**`plan_filter_bar.py:31` reads `ARTIFACTS_ACCENTS["plans"]` at class-definition time**,
so a Research filter bar renders Plans-purple. Both verified.

Sizes (measured): `ace/query` + `ace/agent_query` = 3,269 Python LOC; `filter_tokens.py`
262 + three `filter_query` modules 1,133 + `files_filtering.py` 437; plus 3,428 Rust
LOC. The artifacts widget package alone is 13,506 lines.

### L3 — relations and grouping

`RelationFamily` (name, label, prefix, ordered, `query_template`) + a `RelationSource`
protocol; providers declare edges by naming properties:

```yaml
relations:
  ancestors: {kind: parent_chain, property: parent}
  children:  {kind: inverse, of: ancestors}
  siblings:  {kind: family, property: repo_relative_path, suffix_pattern: '__([a-z]+|\d+)$'}
```

Anything needing a real traversal (Beads' dependency graph) stays a built-in
`RelationSource`, gated by capability. Missing targets remain representable as dangling
links with a diagnostic — they must not invalidate the pane.

Relations that exist in the data today and are unreachable: Beads epic→phases / `deps` /
plan link; Documents proposal→active→archive and plan↔bead; Files logical→versions;
Stitches commit→parent and commit→patch.

**Preserve the prebuilt-index discipline.** `update_relationships_from_index` exists
precisely so 100 selections don't rebuild the graph 100 times; the shared layer must
keep that, and the relation panel is the specific hot-path risk in this epic.

### L4 — the declarative `ref.pane` block

Row template, `group_by`, `default_sort`, facets, empty state, label, description, order,
and the query/relation hints above. Python-only at
`DOCUMENT_REF_PROVIDER_SPEC_SCHEMA_VERSION`; the Rust wire stays at 1.

Constraints that keep the plugin surface bounded: presentation refers only to declared
properties; list fields are priority hints and detail stays lossless; facets are typed;
identity is stable across content edits; a malformed document degrades **per entry** and
never removes the tab; **no colours, keybindings, command strings, Python entry points,
mutation or approval flows**. Anything needing those is a built-in pane — a `sase`
change, not a plugin change. Unknown optional hints fall back to host defaults; unknown
*required* constructs produce a visible disabled pane, never a silent disappearance.

The guarantee a sidecar author gets from `ref.kind` + `inventory.globs` alone becomes
substantial: a tab with a stable digit and non-colliding accent; lazy off-thread
coalesced loading; shared project scope; `j`/`k`/`enter`/`f`/`R`; marks, hint-jump,
detail scrolling; a boolean query language over declared properties with completion,
negation, canonicalization, highlighting, saved slots, history and per-query selection
memory; relation jumpers over any parent/family property declared; grouping and folding;
a copy-mode group; a generated help section; palette entries; `@kind:<path>`
round-tripping; and `Referenced By` write-back.

---

## 5. The typed-values gap, and the cheapest possible proof

Verified: `ArtifactEntryWire.properties` is `BTreeMap<String, String>`
(`crates/sase_core/src/artifact_ref/entry.rs:40`), so a spec may declare
`type: datetime` or `string_list` and the entry wire flattens every value to a string.
Both passes found this; `__a`'s `ArtifactValueWire` is the fix. Sorting by a real
`updated_time` or filtering `tags:` as a list is not expressible until it lands. L2 can
coerce on read in Python meanwhile.

The real-world provider makes this concrete. `sase-research-artifacts`
`provider.py:33-51` declares exactly four properties:

```python
"create_time":  {"type": "datetime",    "source": "markdown_frontmatter"},
"updated_time": {"type": "datetime",    "source": "markdown_frontmatter"},
"status":       {"type": "string",      "source": "markdown_frontmatter"},
"tags":         {"type": "string_list", "source": "markdown_frontmatter"},
```

Two observations neither pass made:

- **`tags` is the concrete casualty** — the one declared field in a real third-party
  sidecar whose type the entry wire demonstrably discards today.
- **`status` is declared `string`, not `enum`.** So `__b`'s "the whole of
  `ref.properties` becomes queryable with no spec change" is true but oversells the
  *quality*: you get substring matching on status, not enum completion or a facet. The
  fix is a one-line change in the sidecar (`"type": "enum", "values": [...]`), and it is
  the cheapest possible end-to-end demonstration of the entire thesis — a sidecar author
  edits four characters and gains completion, a facet and a grouping mode.

`__a`'s snapshot **generation token** is worth adopting alongside: it gives async
completions a cheap correctness check (recheck pane + generation + stable id before
applying) and is the primitive that makes "render cached immediately, refresh in
background, show a stale badge" safe. A stale badge beats a frozen UI.

---

## 6. What Patch inclusion actually costs: the keymap

`__b`'s contribution, and the most operationally valuable artifact in either report —
`__a` does not cover it. **The two surfaces assign the same keys to inverted meanings.**

| Key | Patch today | Other panes today | Contract verb | Resolution |
| --- | --- | --- | --- | --- |
| `y` | **`refresh`** | `stitches_copy_sha`, `files_copy_reference` | `artifacts_copy_reference` | Patch refresh → `R`; `y` copies `@patch:` — a target Patch does not have today |
| `R` | `start_rewind` | `*_refresh` | `artifacts_refresh` | `start_rewind` → bang mode (`!R`) or leader |
| `f` | `edit_hooks` | `*_filters` | `artifacts_filters` | `edit_hooks` → leader; `f` opens the filter bar everywhere |
| `s` | `change_status` (**mutates**) | `*_cycle_*` (**filters**) | — | Genuine semantic conflict; Beads already sides with Patch. Keep `s` = mutate where `MUTATE` is declared; move facet-cycling |
| `l`/`h` | fold in/out | `beads_expand`/`collapse` | `artifacts_expand`/`collapse` | Same concept; unify |
| `L` | `expand_all_folds` | `plans_open_bead`, `beads_open_plan` | `artifacts_link_jump` | Fold-snap moves under the `z` fold prefix Patch already owns |
| `o` | `mark_pr_origin` **and** `cycle_grouping_mode` | `files_open_external`, `beads_open_bug` | `artifacts_open_external` | **Already broken** — see §7 |
| `d` | `show_diff` | `stitches_toggle_sdd` | — | Legitimately pane-local; leave |
| `m` `u` `'` `enter` `j` `k` `g` `G` | ✓ | ✓ | unchanged | Already agree |

Ship the rename with **all three** mitigations or none: action-name aliases in the
keymap loader so existing `~/.config/sase/sase.yml` overrides keep working, a
`sase doctor` advisory naming each replacement, and a one-shot `sase config` migration.
`y` flipping from refresh to copy on the owner's primary surface is the single most
jarring change in this plan and deserves a `CHANGELOG.md` line and a first-run toast.

Two smaller Patch adjustments:

- **Project scope becomes symmetric, and Stitches already ships the pattern.** Patch is
  excluded from the shared scope key today, yet `_resolve_initial_artifacts_scope`
  already reads `get_sole_project_filter(self.parsed_query)` — the Patch query *seeds*
  the shared scope at startup. Adopt the documented Stitches behavior verbatim: `p`
  rewrites the `project:`/`+` token, preserving every other committed token, with "All
  projects" removing it. No new concept, no new state *(carried from `__b`, unverified
  here)*.
- **Modal → inline query bar.** Patch is the only Artifacts pane that edits its query in
  a modal (`QueryEditModal`). Migrating to the inline `FilterBar` is most of what "same
  look and feel" means, and it delivers four things Patch lacks: a completion menu over
  its own keys and values, a live match count, a coverage label, and
  `Escape`-restores-last-committed.

---

## 7. Live defects — land these first, independent of the epic

Verified by this pass unless noted.

**Accent collision, drift, and a module-global leak** (`artifact_tabs.py`). Verified by
inspection: `ARTIFACTS_ACCENTS["ref:plan"]` is `#AF87FF` (line 64) and
`_PROVIDER_ACCENTS[0]` is also `#AF87FF` (line 77), so any unpinned kind sorting before
`plan` renders in the Plans colour. Accents are assigned `index % 6` over the *sorted
kind list*, so installing a `design` sidecar repaints `research` from `#5FAFFF` to
`#5FD7AF` — the same bug class already fixed for digits and left in place for accents.
And `ARTIFACTS_ACCENTS.setdefault(tab_id, accent)` (line 365) mutates a module-level
dict during resolution, which `reset_artifacts_subtabs_cache()` does not undo; an
existing test works around this by popping keys by hand in a `try/finally`. Fix: derive
deterministically from a hash of the kind, collision-resolve against the pinned set,
return it on the descriptor, never write to a global.

**Provider discovery fails silently and caches its own failure** *(reproduced in `__b`,
not re-executed here)*. With `sase_core_rs` unimportable, `resolve_artifacts_subtabs()`
returns four tabs — **the built-in Plans tab disappears too** — with no error anywhere in
the UI, and because the source token is a stable `("unavailable",)` sentinel the
degraded answer survives an explicit cache reset. Separately, with the
`sase-research-artifacts` plugin missing from a venv, `research` falls through to
`_default_document_spec` and builds a tab with empty `properties` and empty `detail`; the
diagnostic exists (`code="missing_ref_provider"`) and `sase doctor` fires on it, but ACE
discards it. Fix: narrow the two bare `except Exception` blocks, render a degraded tab
carrying its own error, and stop caching the sentinel.

**`o` is double-booked on the Patch pane.** Verified: `default_config.yml:355` binds
`mark_pr_origin: "o"` and `:410` binds `cycle_grouping_mode: "o"`; `metadata.py` lists
them at indices 27 and 154, both `priority=False`, and `mark_pr_origin` is enabled across
the whole Artifacts tab, so it always wins and **forward grouping-cycle is unreachable**
while `O` works — despite `docs/ace.md:614` and the info-panel badge promising both.
Already filed by `__b` as **`sase-m5`** (task, medium, READY); do not duplicate it.

**Detail fields are not parameterized.** `ordered_plan_property_items` ignores
`ref.detail.fields`, so the research provider's declared `status`/`create_time`/
`updated_time`/`tags` are not what its detail band shows. No spec change, no Rust change,
no new data path — and both passes independently rate it the highest value-per-line
change available.

*No artifacts-contract beads are open, ready or in progress* (checked). The field is
clear apart from `sase-m5`. These defects are folded into Phase 0 below rather than filed
separately, since the recommended plan already carries them and `/sase_new_task` would
flag the overlap.

---

## 8. Sequencing

`__a` says Patch must be migrated **first** because it is the design stress test and
migrating easy panes first yields an abstraction that breaks when Patch arrives. `__b`
says migrate the four token panes **first** with `boolean=False`, so the engine is proven
on four surfaces before the hardest one. Both are right about different things, and
neither states the other half:

> **Design against Patch from Phase 0; cut Patch over last.**
> Freeze golden query, relation and persistence fixtures from the *current Patch
> behavior* before any code moves — that is what stops the profile shape from being
> wrong. Then migrate the cheap panes first, because they are individually revertible
> and Patch is the owner's primary surface and the most expensive rollback.

| Phase | Content | Size | User-visible |
| --- | --- | --- | --- |
| **0 · Fixtures + live defects** | Golden fixtures from the current Patch evaluator (precedence, quoting, sigils, invalid queries, selection results), relation fixtures (parent chains, cycles, missing parents, families, cross-kind), captured saved-query/history files; conformance harness any adapter can run. Plus §7's accents, silent discovery, and `sase-m5` | S–M | **Yes** — fixes silently-missing tabs |
| **0.5** | Parameterize `ordered_plan_property_items` by `ref.detail.fields` | XS | **Yes** — Research shows its own properties |
| **1 · L0** | One `ArtifactEntryTarget` everywhere; Patch implements the navigator; marks and jump anchors migrate; `ArtifactEntryNavigator` becomes an ABC; Files/Stitches gain the two missing methods; `@patch` copy target | M | Marks survive refresh; deep links work on Files/Stitches |
| **2 · L1** | `ArtifactsPaneContract` + derived `PaneCapability`; snapshot-pane base absorbing the loader written three times; every surface reads capabilities; all 13 files of `ref:` dispatch collapse; per-provider copy groups and help sections | L | Provider panes stop calling themselves Plans |
| **3 · L2** | Profile-parameterize the Rust query module; `ArtifactQuerySchema` in Python; migrate the four token panes at `boolean=False` (behaviour-identical), **then** Patch at `boolean=True`; inline bar replaces `QueryEditModal`; slots/history/selection memory namespaced with file migration; `ref.properties` drives completion | XL — **split into an epic** | **Yes** — the phase users feel |
| **4 · L3** | `RelationSet` + `RelationPanel`; Patch's three families move onto it; Beads gets epic/phase + deps, Files versions, Documents plan↔bead, **research gets its `__a`/`__b` family** (§3.1); grouping declared on the contract with `GroupFoldRegistry` as the one implementation | L | Jumpers on every pane |
| **5 · L4** | `ref.pane` at document-spec schema 2 (Python only), `REF_PANE_CONFIG_KEY` in the allowlist, `presentation_digest`; `sase-research-artifacts` ships its `pane` block and flips `status` to `enum` | L | Research is a real Research tab |
| **6** | Parametrized conformance test over `resolve_artifacts_subtabs()` with a **synthetic third provider** carrying no SASE-specific Python; ACE-surfaced provider diagnostics; docs; visual snapshot refresh | M | No |
| **later** | Typed `ArtifactValueWire` in `sase-core`; retire the pane-local token parsers and legacy saved-query readers after a measured deprecation window | L | No |

Phase 3 will not fit a single agent. Split it one bead per migrated pane, plus one for
the persistence-file migration, plus one for the Patch cutover.

**Verification notes.** Phases 1–4 touch `tests/ace/tui/test_artifacts_*` broadly, so
`just check`'s scoped lane will escalate — run `just check-full` through `/sase_monitor`
before landing each. Expect `tests/ace/tui/visual/snapshots/png/` goldens to move in
Phases 3 and 5; review those diffs rather than accepting blind. Hold the `SASE_TUI_PERF=1`
navigation p95 under 16 ms on every converted pane, measured after each conversion; read
`sase/memory/tui_perf.md` first. Beyond that, the contract should make the fast path
obvious and the slow path impossible to invoke by accident: build typed values,
searchable text, completions and relation indexes once per snapshot off the event loop;
cache compiled profiles by digest and results by `(pane_id, generation, profile_digest,
canonical_query)`; and never let a keystroke resolve providers, glob files, call Git,
parse Markdown or stat the filesystem.

---

## 9. Open decisions

Eleven distinct questions across both passes. Four change the plan; the rest are
defaults worth confirming once.

**Plan-shaping:**

1. **Derived vs declared capabilities** (§2.3). *Recommendation: derived, with opt-out
   only.* This is the decision that determines whether unknown users' sidecars inherit
   future features for free — the owner's stated goal.
2. **`s` on Patch.** The only verb where Patch's meaning (mutate status) and the other
   panes' (cycle a facet) genuinely conflict; Beads already sides with Patch.
   *Recommendation: `s` = mutate wherever `MUTATE` is declared; facet-cycling moves
   everywhere.*
3. **`y` = copy on Patch.** Loses today's refresh binding on the primary surface.
   *Recommendation: do it — a pane full of `@patch:`-addressable rows with no way to copy
   one is the more surprising state — but only with all three mitigations from §6.*
4. **Query profile as a call argument, not a wire** (§2.1). *Recommendation: confirm.*
   It is what lets L2 proceed at schema version 1 and keeps the field-schema shape
   unfrozen while it settles.

**Defaults to confirm:**

5. **Reveal UX.** *Reversible identity lens with a visible "return to query"* rather than
   destructive query rewrite; the rewrite stays the underlying mechanism.
6. **Saved slots.** *Per-pane*, matching history and selection memory, with the `*`
   picker showing the active pane first and others below.
7. **`boolean: true` reach.** *Opt-in per pane; default `false` for providers* so a
   schema-1 provider's behavior never changes silently; `true` for Patch and, after a
   settling period, the four built-ins.
8. **Persistent filter bar on Patch.** *Yes* — Stitches sets `PERSISTENT = True` because
   the query *is* the view, and Patch's query is already always visible. Declared rather
   than accidental.
9. **List matching.** *Contains-any first*; defer contains-all until a real use case.
10. **Provider macros.** *Host-defined closed vocabulary only.* Patch's `%`/`!!!` set
    starts as a legacy profile macro group; expand only with collision rules and a
    discoverability story.
11. **Trusted custom actions.** *Keep out of portable sidecar config permanently.*
    Revisit only as a separate installed-plugin contract that returns host-validated
    action descriptors.

---

## 10. Risks

- **Phase 3 is the whole plan's risk**: three languages, four panes, three persistence
  files, one modal-to-inline UI change, and a Rust refactor. Mitigation is structural —
  the `boolean=False` degradation path makes each pane migration byte-identical and
  independently revertible, and the existing `query_evaluator_parity.rs` harness plus
  Phase 0's golden fixtures give the Rust de-Patch-ification a hard oracle.
- **Keymap churn is user-visible and unavoidable.** Aliases + doctor advisory + one-shot
  config migration; do not ship the rename without all three.
- **Providers gaining a query language enlarges the plugin blast radius.** A malformed
  `properties` block must degrade per entry, never remove a tab. Load-bearing from L2 on.
- **The relation panel is the hot-path risk.** Preserve `update_relationships_from_index`
  rather than rebuilding a graph per selection.
- **`o` was broken and nobody noticed.** That is the honest signal about how untested
  this surface is at the binding level. The Phase 6 conformance test should assert that
  every contract-declared key resolves to the action the contract names, on every pane,
  built-ins included.

---

## Rejected alternatives

**Keep Patch permanently exempt** (the prior report's position). Cheap now; guarantees
two navigation, query, persistence, footer, help and action-availability systems forever.
Every future cross-pane feature either excludes the most capable pane or is built twice —
and the exemption becomes permanent because each new feature widens the gap. It also
removes the best stress test from the contract.

**Bring Patch in but keep three query languages.** Avoids the biggest refactor; leaves
Patch with a modal editor and no completion, providers with a flat dialect and no `OR`.
"Unified" would be skin-deep.

**Adopt the flat token language everywhere.** Simplest; a strict downgrade for the
owner's primary surface — loses `OR`, parens, case-sensitive literals and every sigil.

**Adopt the Patch language everywhere as-is.** Keeps the grammar but its keys are a
hard-coded allowlist and its corpus a hand-written flattener; a provider can extend
neither, and it loses `FilterBar`'s completion and live count.

**Force every pane through the current document/Plan widget.** Optimizes class count
rather than behavior; Patch mutation and graph UX, File versions, Bead hierarchy and
Stitch detail would turn the generic widget into a pile of pane-id conditionals. Shared
shell plus specialized renderers is the smaller abstraction over time.

**Let providers ship Textual widgets or Python callbacks.** Maximum flexibility;
forfeits portability, security, performance guarantees, failure isolation, host
keymap/help consistency and future-frontend parity — i.e. every property the epic exists
to buy.

**Keep provider values as strings.** Recreates today's duplicated matchers and makes
numeric/date sorting and validation inconsistent. Types must survive the wire if the
query engine is genuinely shared.

**Save raw query strings without profile identity.** Works until a provider renames a
field or changes a type. Silent reinterpretation is worse than a visibly invalid saved
view; source + canonical + profile digest is the minimum durable record.

The design has precedent worth borrowing from rather than inventing: Backstage models
catalog relations as directed typed source/target edges with derived inverses, treating
relations as deduced output rather than author-written state; Kubernetes field selectors
make a kind's selectable fields explicit so an unsupported field is an error rather than
a silent no-op, and let custom resources declare their own; VS Code's Tree View API keeps
the view host-owned while a data provider supplies items, with commands contributed
separately. SASE should be *more* declarative than the last of these, because a
repository config is portable data rather than trusted installed code.

---

## Recommended solution

Bring Patch into the Artifacts contract by **taking the query language away from Patch**
— and note that the language is already mostly where it belongs. The Rust `query` module
is a working tokenizer, parser, matcher set, corpus and evaluator with a parity harness;
it is simply typed to `ChangeSpecWire` with a hard-coded key allowlist and inline sigil
emissions. Making it profile-parameterized, with the compiled profile passed as a **call
argument rather than a persisted wire**, is the whole of L2's core work — and it needs no
`schema_version` bump, because a per-call profile freezes nothing and additive optional
spec fields are already free at v1.

Build in five dependency-ordered layers. **L0** gives every pane, Patch included, one
stable `ArtifactEntryTarget`, replacing index-based marks and jump anchors and making
`ArtifactEntryNavigator` an enforced ABC — small, invisible, a hard prerequisite for
everything above. **L1** is `ArtifactsPaneContract` with a closed `PaneCapability`
vocabulary that every downstream surface reads instead of comparing pane ids, collapsing
26 `ref:`-dispatch sites across 13 files — with capabilities **derived from declared
data**, which is what makes a future host feature light up in a sidecar written before
that feature existed. **L2** is the one query engine, a strict superset of all three
dialects that degrades to today's exact behaviour at `boolean=False` and makes the
already-declared, already-Rust-validated `ref.properties` queryable and completable with
no spec change at all. **L3** generalizes the ancestors/children/siblings jumpers into
named relation families over any pane's graph — including the query-rewrite fallback that
makes out-of-set jumps work, which is why L3 cannot precede L2 — presented as a
reversible lens rather than a destructive rewrite, and folds Patch's grouping onto the
`GroupFoldRegistry` already shared with Agents. **L4** is the declarative `ref.pane`
block, Python-side, where a provider fills in row template, grouping, sort, facets and
empty state and never ships code.

Design against Patch from Phase 0 — freeze golden query, relation and persistence
fixtures from its current behavior before anything moves, because that is what keeps the
profile shape honest — then migrate the four cheap panes before cutting Patch over last,
because it is the owner's primary surface and the most expensive rollback. Patch is
contract-in and spec-out: `patch` is a reserved kind in core, so it consumes the contract
from a built-in Python table and never becomes a document provider. Its cost is
concentrated in six keys — `y`, `R`, `f`, `s`, `L`, `o` — and must ship with aliases, a
doctor advisory and a one-shot config migration together.

Land Phase 0 now regardless of the epic's timing: accents that collide and drift,
provider discovery that fails silently and caches its own failure, and a `o` binding that
has silently shadowed forward grouping-cycle are live today and cost almost nothing to
fix. Then L0, L1, L2 in order, **before any new sub-tab functionality is added** — every
feature added ahead of the query layer gets written five times.
