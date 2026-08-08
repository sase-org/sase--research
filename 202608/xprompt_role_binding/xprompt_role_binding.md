---
create_time: 2026-08-08
updated_time: 2026-08-08
status: research
---

# Invoking XPrompts by Tag: Role Binding and Resolution

**Research question:** what is the most reliable way to invoke an xprompt by the
semantic role it fills rather than by its name?

**Scope:** `sase` at master `72ec6aa3a`/`e62959e88`, the `sase-github` plugin at
`7dd02fc`, and `sase-core` at `origin/master`. Consolidated from two independent
research reports (`__a`, `__b`) plus a third verification pass. Every defect below was
re-verified against a live install in this workspace; verification status is marked
per finding.

---

## Bottom line

sase **already has tag-based invocation.** `src/sase/xprompt/tags.py` is the binding
mechanism for eleven core behaviors — bead automation, mentor review, fix-hook,
rollover, and VCS wrapping. The feature the question asks for mostly exists. What is
missing is a user-facing selector syntax, and — far more importantly — a resolution
contract that is actually reliable.

The resolver is not reliable enough to expose. Three independently verified failures:

1. **An unknown tag takes down the entire catalog.** Not the file — the catalog.
2. **The documented override story works only if you happen to save your file as
   `.yml`.** The same override as `.md` is silently ignored.
3. **`#propose` and the `propose` role can resolve to different files.** The
   name-collision tiebreak is inverted between the tag path and the name path.

So the recommendation is **not** "add a tag syntax." Syntax is the cheap last step.
The deliverable is a deterministic resolver; the `tag/` namespace falls out of it
almost for free afterwards, and is actively harmful before it.

**Recommended solution, in dependency order:**

| Phase | What | Why it's ordered here |
| --- | --- | --- |
| **0** | Stop `parse_tags` raising; route to `record_load_issue` | Standalone availability bug, ship independently |
| **1** | Deterministic `resolve_tag()` ranked on `XpromptSource.priority`; declared role registry with cardinality; config pin | The actual reliability work |
| **2** | Reserved `tag/` reference namespace — `#tag/propose`, `#!tag/land_epic` | Cheap once 1 lands; zero lexer changes |
| **3** | `sase xprompt tags` observability; migrate the 11 call sites | Makes it debuggable and retires the old APIs |

---

## Part 1 — Audit: what tags are today

### 1.1 The mechanism

`XPromptTag` is a **closed enum of 15 members**. Tags are declared in frontmatter
(`tags: vcs, rollover` or `tags: [vcs, rollover]`), parsed by `parse_tags()`, and
stored as `frozenset[XPromptTag]` on both `XPrompt` (`models.py:222`) and `Workflow`.

Two catalog-wide resolvers exist, plus a per-object predicate:

| API | Kind | 0 matches | 1 | N>1 |
| --- | --- | --- | --- | --- |
| `get_by_tag(tag, vcs_hint=…)` | catalog resolver | `None` | the match | `matches[-1]`, optionally steered by plugin module |
| `get_by_tag_strict(tag)` | catalog resolver | `None` | the match | **raises `ValueError`** |
| `XPrompt.has_tag` / `Workflow.has_tag` | per-object predicate | `False` | `True` | `True` |

`has_tag` is a method on the model objects (`models.py:231`,
`workflow_models.py:167`), not a lookup in `tags.py` — it answers "does *this* prompt
carry the tag", never "which prompt holds it".

### 1.2 Census — and it is environment-dependent

Source-level declarations across all three repos:

| Tag | Declared by | Consumed by |
| --- | --- | --- |
| `vcs` | `git.yml`, `gh.yml` (plugin) | `workflow_loader.py:226` (implies `wraps_all`), `…embedded_expand.py:199` |
| `rollover` | `commit`, `file`, `json`, `pr`, `propose`, `git`, `gh` (plugin) | `run_agent_exec_plan_artifacts.py:85` |
| `commit` | `commit.yml` | `_mentor_review.py:192` |
| `propose` | `propose.yml` | `_mentor_review.py:190` |
| `mentor` | `mentor.yml` | `workflows/mentor.py:74` (strict) **and** `:120` (tolerant) |
| `make_mentor_changes` | `make_mentor_changes.yml` | `_mentor_review.py:158` (strict) |
| `fix_hook` | `fix_hook.md` | `axe/fix_hook_runner.py:172` |
| `diff_file` | `pr_diff.yml` (plugin) | `workflows/mentor.py:87` (with `vcs_hint`) |
| `append_to_commit_and_propose` | `prdd.yml` (plugin) | `…embedded_expand.py:294` |
| `work_phase_bead` | `bd/work_phase_bead` (default_config) | `bead/xprompts.py:39` (strict) |
| `work_task_bead` | `bd/work_task` (default_config) | `bead/xprompts.py:44` (strict) |
| `land_epic` | `bd/land_epic` (default_config) | `bead/xprompts.py:49` (strict) |
| `crs` | **nothing** | `workflows/crs.py:92` |
| `append_to_pr` | **nothing** | `…embedded_expand.py:296` |
| `create_epic_bead` | **nothing** | **nothing** |

**15 holders with `sase-github` installed; 12 without.** Measured live: 15/106 in the
reporting agents' environments, 12/102 in this workspace where the plugin is absent.
Three enum members are dead everywhere: `crs` and `append_to_pr` have live consumers
that silently receive `None`; `create_epic_bead` is vestigial.

That the holder set varies by installed plugins is not a measurement artifact — it is a
design constraint. `#tag/diff_file` means something different depending on which VCS
plugins are present, which is precisely why the resolver needs explicit provider
context rather than incidental ordering.

Note `mentor` is resolved **both** strictly (`:74`, prompt construction) and tolerantly
(`:120`, reporting) — the same tag, two different cardinality contracts, in one module.

### 1.3 One enum doing three incompatible jobs

Two of the three have no single answer to "which xprompt is this tag?":

- **Set markers (cardinality N).** `vcs`, `rollover`. Seven prompts carry `rollover`.
  `#tag/rollover` is meaningless. Consumed only via `has_tag` predicates and metadata
  string matching — never resolved to "the one".
- **Role bindings, tolerant (cardinality 1, best-effort).** `commit`, `propose`,
  `fix_hook`, `diff_file`, `crs`, `append_to_*`. `get_by_tag` guesses when several.
- **Role bindings, strict (cardinality 1, enforced).** `mentor`,
  `make_mentor_changes`, and the three bead tags. `get_by_tag_strict` *refuses to work*
  when several.

Only the role categories are invocable. Nothing in the enum or the frontmatter declares
which is which, so nothing can validate it. **Declared cardinality is the missing
primitive** — more than syntax is.

### 1.4 Four parsers, four contracts, one YAML key

This is the single most important audit finding for deciding open-vs-closed vocabulary:

| # | Implementation | Contract | On unknown tag |
| --- | --- | --- | --- |
| 1 | `xprompt/tags.py::parse_tags` | closed enum → `frozenset[XPromptTag]` | **raises** |
| 2 | `xprompt/prompt_frontmatter.py::_parse_tags` (TUI editor) | free-form `list[str]` | accepts |
| 3 | `sase-core` `xprompt_catalog.rs::parse_tags` (editor/mobile catalog) | free-form `BTreeSet<String>` | accepts |
| 4 | `run_agent_exec_plan_artifacts.py:82-86` (rollover) | raw string match on serialized JSON | accepts |

Three of the four are already open. The TUI's docstring is explicit: *"Ad-hoc prompt
tags are free-form (core does not constrain them), so this keeps the raw strings rather
than validating against the xprompt tag enum."* Rollover never touches the enum at all —
it string-matches `"rollover" in wf_tags` on serialized metadata, meaning tags **already
cross the process boundary as free strings**.

A fifth call site, `agent/multi_prompt_xprompts.py:163`, runs the *closed* parser over
JSON-deserialized local xprompts at agent launch — so contract 1 and contract 4 already
meet on the same wire in opposite directions.

### 1.5 Four unrelated things are called "tags"

Any user-facing `tag` syntax lands in a crowded namespace:

1. `XPromptTag` — the subject of this note.
2. `PromptFrontmatter.tags` — the TUI's free-form list. *Same YAML key*, opposite
   contract (see D4).
3. **VCS workflow tags** — `_parsing_vcs_tags.py` calls the leading `#gh:sase`
   workspace reference a "tag" (`extract_vcs_workflow_tag`). Unrelated, heavily used.
4. `saved_tag_names` / ChangeSpec `pr_tags` — user labels like `BUG`, `FEATURE`.

Additionally, SASE prose often calls a plain `#name` reference a "tag", so a bare
`#mentor` is genuinely ambiguous between "the prompt named `mentor`" and "the prompt
tagged `mentor`". The syntax must make that visible.

### 1.6 What the docs promise

`src/sase/bead/xprompts.py:5-7`:

> users may override any of them by tagging an xprompt of their own with the same tag
> (the loader's precedence chain handles which one wins, and `get_by_tag_strict`
> rejects ambiguous setups)

And the error message actively instructs users down that path: *"Tag a built-in or
custom xprompt with `tags: <tag>` to enable this role."* Following that instruction
when a built-in already holds the tag produces a hard `ValueError`. Both halves of the
promise are false in practice (D2, D3).

The long-term memory note `sase/memory/xprompts.md` documents `tags` only as a
frontmatter field and makes no invocation claim, so **no published user-facing contract
is broken by changing this.**

---

## Part 2 — Why tag invocation is unreliable today

Six defects. Each was reproduced in this workspace against the installed build.

### D1 — An unknown tag crashes the entire catalog ✅ verified end-to-end

`parse_tags()` raises on any name outside the enum. `load_xprompt_from_file`
(`loader_sources.py:135`) calls it with no guard, inside the unguarded generator
`_load_ordinary_xprompts_from_dir`; `load_xprompts_from_files` has no per-file
`try`/`except` either. The exception escapes `get_all_xprompts()`.

Reproduced with an isolated `HOME` containing one good and one bad xprompt:

```
$ printf -- '---\nname: bad\ntags: research\n---\noops\n' > $TH/sase/xprompts/bad.md
WHOLE CATALOG DOWN: ValueError: Unknown xprompt tag 'research'. Valid tags: [...]
```

The sibling `good.md` and all 100+ built-ins become unresolvable. `.yml` workflows are
equally exposed — `workflow_loader.py:225` calls `parse_tags` *before* the `try` block
that guards input parsing; reproduced via `_load_workflow_from_file`.

Every other load failure in this package — bad YAML, unreadable file, bad inputs,
misplaced skill, reserved namespace — routes through `record_load_issue()` and surfaces
non-fatally in `sase doctor`. **Tag parsing is the sole exception.**

This is a standalone availability bug independent of tag invocation, and it
disqualifies any design that asks users to write their own tags.

### D2 — Override success depends on your file extension ✅ verified

`get_by_tag` returns `matches[-1]`, justified by:

> The dict is built from lowest to highest priority, so we return the **last** match.

That reasoning fails for two compounding reasons:

**(a) `dict.update` does not reorder existing keys.** `get_all_xprompts` builds
lowest→highest across nine numbered sources (`loader.py:198-240`), but a name present in
both a low- and high-priority source keeps its *low-priority insertion index* while
taking the high-priority *value*. Iteration order is first-appearance, not precedence.

**(b) `get_all_prompts` returns `{**converted, **workflows}`** (`loader.py:288`) — so
every xprompt sorts before every workflow regardless of source. Measured live in this
workspace:

```
   1 fix_hook            ['fix_hook']            built-in .md
   6 bd/land_epic        ['land_epic']           default_config
  93 propose             ['propose','rollover']  built-in .yml
 100 mentor              ['mentor']              built-in .yml
```

Indices 1–10 are xprompts; 87–100 are workflows. The split is total.

The consequence, verified by direct experiment:

| User writes (highest-priority source) | Candidates in order | `get_by_tag` winner | Outcome |
| --- | --- | --- | --- |
| `my_propose.**md**` tagged `propose` | `[my_propose, propose]` | `propose` | **override silently ignored** |
| `my_propose.**yml**` tagged `propose` | `[propose, my_propose]` | `my_propose` | override works |

**The identical override, at the identical source priority, wins or loses purely on
file extension.** `.yml` lands in the workflows half and sorts last; `.md` lands in the
converted half and sorts first. This is why the bug survived: anyone who tested with a
`.yml` saw it work.

The existing test encodes the assumption rather than testing it —
`tests/test_xprompt_tags_lookup.py:44` patches `get_all_prompts` with a hand-ordered
two-entry dict and asserts the last wins, so CI cannot see the inversion.

Secondary fragility: `vcs_hint` disambiguation resolves ties by comparing plugin module
names extracted from `source_path` string prefixes, and falls through to the same
`matches[-1]` whenever the competing definitions are not both plugin-backed.

### D3 — Strict tags make override structurally impossible ✅ verified by inspection

`get_by_tag_strict` raises on N>1. For `mentor`, `make_mentor_changes`,
`work_phase_bead`, `work_task_bead`, and `land_epic`, adding your own tagged xprompt
does not override the built-in — it **breaks the feature**:

```
ValueError: Multiple xprompts found with tag 'work_task_bead': [...]. Only one is allowed.
```

The only working override today is to shadow the *name* at a higher-priority source —
name-based invocation wearing a tag-shaped hat. The tag adds nothing.

Note this is a *raise at resolution time*, not at load time: a user who follows the
documented advice breaks `sase bead work` on the next run. That failure mode is the
reason the replacement resolver should not raise (see Part 5).

### D4 — The TUI writes free-form tags into a closed-vocabulary field ✅ verified

`PromptFrontmatter` treats `tags` as an unconstrained `list[str]`, serializes it back
into the `.md` frontmatter (`:197-198`), and offers it as an editable row in the
frontmatter panel. `frontmatter_schema.py` does not validate it at all.

**A user who types `tags: research` in the TUI xprompt-save flow writes a file that
triggers D1 on the next catalog load.** The two halves of the same field disagree about
whether the vocabulary is open, and the open half can brick the closed half.

### D5 — Tag bindings are barely observable ⚠️ partially overstated in the source reports

There is no `sase xprompt show tag/mentor`, no "who holds this tag, who lost and why",
and no CLI `--tag` flag. Debugging a mis-resolved role means reading `tags.py` and
reasoning about dict insertion order — which, per D2, is not what the docstring says.

**Correction:** an inverse query surface *does* partially exist. The structured catalog
already supports filtering by tag, implemented twice — `sase-core`
`xprompt_catalog.rs:337` (`filter_structured_sources`, matching on
`BTreeSet<String>`) and mirrored in Python at `_catalog_structured.py:112-130` (matching
on `tag.value`). Tags are also part of the catalog search haystack. So the gap is CLI
exposure and *ranking/provenance*, not the filter itself — and the duplicated
implementation is one more argument for a single shared contract.

### D6 — Three catalogs, and the name-collision tiebreak is inverted ✅ verified — new

The source reports noted that inline expansion and workflow resolution use different
catalogs. It is worse than that: the two paths **disagree about who wins a name
collision.**

| Path | Catalog | Name-collision winner |
| --- | --- | --- |
| Inline `#name` expansion (`processor.py:358`) | `get_all_xprompts()` only | **xprompt** |
| `get_xprompt_or_workflow` (`loader.py:307-314`) | xprompts checked first, then workflows | **xprompt** |
| Tag resolution (`get_all_prompts`, `loader.py:284-288`) | `converted` *excludes* names present in `workflows` | **workflow** |

Verified consequence — a user writes `~/sase/xprompts/propose.md` (same name as the
built-in workflow, highest-priority source, tagged `propose`):

```
#propose  (name path) -> MINE-USER-VERSION | /home/u/sase/xprompts/propose.md
'propose' in converted half? -> False
tag propose (role path) -> propose      | src/sase/xprompts/propose.yml
```

**`#propose` and "the prompt tagged `propose`" resolve to different files.** The user's
override wins the name path and is silently *discarded* from the tag candidate set
entirely. Any invocation design must decide which catalog a tag reference lives in and
unify the collision rule; otherwise `#tag/propose` and `#propose` will diverge in
exactly the case a user is most likely to hit.

Combining D2 and D6, only two of the four ways to write an override behave as
documented:

| User writes | `#name` gives | role gives | Verdict |
| --- | --- | --- | --- |
| `my_propose.md` | — | built-in | override ignored |
| `my_propose.yml` | — | user's | works |
| `propose.md` | user's | built-in | **name and role diverge** |
| `propose.yml` | user's | user's | works |

---

## Part 3 — Requirements

- **R1 Determinism.** The same catalog always yields the same winner, independent of
  dict insertion order, filesystem iteration order, plugin install order, and *file
  extension*.
- **R2 Documented precedence.** The winner is what the published precedence chain says,
  and the losers are inspectable.
- **R3 Fail local, fail loud.** A malformed or ambiguous tag degrades that one
  definition, surfaces in `sase doctor`, and never takes down the catalog or silently
  picks the wrong thing.
- **R4 Overridable.** A user can rebind a role without editing built-ins, and can force
  a binding when inference is ambiguous.
- **R5 Parity with names.** Args, colon/`::` shorthand, `#!` standalone launch, HITL
  suffixes, completion, `xprompt show`, expansion trace.
- **R6 Honest cardinality.** `#tag/rollover` must be a clear error, not a coin flip.
- **R7 One cross-frontend contract.** CLI, ACE, editor/LSP, and mobile catalog agree.
  Per `sase/memory/rust_core_backend_boundary.md`, a web app or editor integration would
  need the same answer as the TUI — this is core backend logic.

---

## Part 4 — Design options

### Option A — Reserved `tag/` namespace, materialized in the loader ✅ recommended

`#tag/propose`, `#!tag/land_epic`. The loader registers a synthetic catalog entry keyed
`tag/<role>` whose value is the winning `XPrompt`/`Workflow`.

- **Lexer changes: none — verified in both copies.** The reference grammar is
  duplicated (`_parsing_references.py:21` and the independent `_XPROMPT_PATTERN` at
  `processor.py:65`) and *both* already accept `ns/name`. `__` → `/` normalization means
  `#tag__propose` works too. Args survive: `#tag/work_phase_bead:sase-e.2` parses as
  name `tag/work_phase_bead` + colon arg.
- **Precedent: strong and structural.** `memory/` is exactly this pattern — entries
  synthesized during load and merged into `get_all_xprompts()` (`loader.py:228-232`) —
  and `reserved_namespaces.py` already provides the "ordinary definitions may not claim
  this prefix" guard to copy, backed by the Rust binding
  `reserved_memory_namespace_issue`. `skills/` is a second instance, and its loader
  comment states the goal directly: skills "can never shadow (or be shadowed by) an
  ordinary xprompt of the same bare name."
- **R5 falls out** — everything downstream keys off the catalog.
- **D6 is handled** by registering the synthetic entry in whichever catalog the winner
  lives in, once the collision rule is unified.
- **Cost:** `tag/` must be reserved. No collision exists — built-ins ship `t.md` and
  `tribe.md`, neither of which occupies `tag/`.
- **Caveat (validated).** Because `memory/` entries *do* appear in ordinary `#`
  completion, naive synthesis would duplicate every role in the picker. Synthetic
  entries must be flagged so they surface only under a `#tag/` prefix or a dedicated
  "Roles" group. This is a real cost the mechanism does not absorb by itself.

### Option B — New sigil (`#@propose`, `#[propose]`, `#tag:propose`) ❌

Rejected. The grammar is duplicated in two places plus `naming.py`, so every completion,
highlighting, VCS-tag, and shorthand regex needs auditing for a purely cosmetic gain.
`@` is already overloaded (model aliases `%model:@coder`, launch at-refs, tribe
display), `#@` opens ACE's picker, and `#tag:propose` **already parses today** as "the
xprompt named `tag` with argument `propose`".

### Option C — Textual rewrite in `resolve_xprompt_aliases` ❌

Cheapest insertion point, but **verified**: `resolve_xprompt_aliases` runs at
`processor.py:351`, `protect_fenced_blocks` at `:418` — so it rewrites inside code
fences, an existing wart of `xprompt_aliases` that a tag feature should not inherit. It
also loses provenance in errors and traces and does nothing for catalog-reading surfaces
(completion, `xprompt show`, `used_xprompts`). Viable only as a fallback for a surface
Option A cannot reach.

### Option D — Generate `xprompt_aliases` entries from tags ❌

Static name substitution. No override chain, no plugin participation, no cardinality,
no provenance, no ambiguity reporting. Its merge rules would become a second resolution
system. Fails R1–R4.

### Option E — API only, no prompt syntax ⚠️

Fix the resolver, add `sase xprompt resolve --tag <t>`, leave invocation to core code.
This is the honest minimum — it removes every defect in Part 2 without adding surface
area. It simply does not answer the question as asked. **Phases 0–1 below are exactly
this**, which is why they are independently shippable.

### Option F — Separate singular `role:` field ⏸️ defer

A singular `role:` would model callable bindings more precisely than the many-valued
`tags:`. Reasonable future cleanup, but introducing it first migrates every definition
and API without solving priority or provenance on its own. Encode role/marker policy in
a registry now; consider the schema split later.

### Comparison

| | A `tag/` ns | B sigil | C rewrite | D aliases | E API only |
| --- | --- | --- | --- | --- | --- |
| Lexer changes | none | many | none | none | none |
| R5 parity | free | per-surface | partial | no | n/a |
| Provenance in trace | yes | yes | lost | lost | yes |
| Fence-safe | yes | yes | **no** | n/a | n/a |
| Handles D6 | yes (once unified) | needs work | no | no | n/a |
| Picker pollution | needs flag | no | no | no | none |
| Precedent in repo | `memory/`, `skills/` | none | `xprompt_aliases` | itself | — |

---

## Part 5 — Recommended solution

**Adopt Option A on top of a rebuilt resolver.** Four phases; phases 0 and 1 carry all
the reliability value and ship independently of any syntax decision.

### Phase 0 — Stop the bleeding (independent of everything else)

`parse_tags` must validate *shape* (identifier-ish) and never raise. Unknown names route
through `record_load_issue()` like every other load failure in the package. Fix all
five call sites (`loader_sources.py:135`, `:382`, `workflow_loader.py:225`,
`multi_prompt_xprompts.py:163`, plus the `.yml` path).

This is a standalone availability bug (D1) that also closes D4, and it should be filed
and fixed regardless of whether tag invocation is ever adopted.

### Phase 1 — Deterministic resolution

Replace `get_by_tag`/`get_by_tag_strict` with one `resolve_tag()`:

**Rank source — do not invent a new precedence table.** `resolve_xprompt_file_sources()`
returns the Rust-owned first-wins order, and each `XpromptSource` already carries
`priority: int` and `scope: str` (`core/content_layout_wire.py:143-145`). Rank
file-backed definitions by the priority of the source directory containing
`source_path`; rank non-file buckets with explicit constants matching the order
`get_all_xprompts` already applies (project config → user config → plugin →
`default_config` → internal). `_catalog_sources.classify()` already computes the coarse
bucket and can seed this.

**Ordering key: `(source_rank, kind_rank, name)`** — never dict position. This kills D2
including the extension-dependence, because kind stops being a hidden ordering term and
becomes an explicit, documented tiebreak.

**Unify the collision rule (D6).** Pick one answer for "xprompt named X vs workflow
named X" and apply it in `get_all_prompts`, `get_xprompt_or_workflow`, and the inline
processor. The name paths already agree that xprompts win; `get_all_prompts` is the
outlier and should change to match, so `#propose` and the `propose` role cannot diverge.

**Declared cardinality.** Add a registry entry per role: `ROLE` (exactly one winner) vs
`MARKER` (set membership). `vcs` and `rollover` are markers; the rest are roles.
`resolve_tag()` on a marker is an error with a clear message (R6). Marker membership
stays on `has_tag`.

**Open vocabulary, declared semantics — these are orthogonal.** Report `__a` proposed
keeping the closed enum and aligning Rust to it; report `__b` proposed opening the
vocabulary. The evidence favors opening (§1.4: three of four parsers are already open,
and tags already cross the process boundary as raw strings; closing Rust would *add* a
failure mode the editor catalog does not currently have). But `__a`'s real insight
survives intact and is independent: what you need is not a closed *vocabulary*, it is a
**declared registry of role semantics**. Open the parser; keep `XPromptTag` as the
reserved role constants core binds against; let `has_tag` accept an enum member or a
string. Unknown tags become opaque strings — which is what unifies the TUI's free-form
tags with core's roles and is the precondition for user-authored roles.

Typo protection lost by opening comes back as a `doctor` check: warn on a tag within
edit-distance 1 of a reserved role, and on any reserved role with zero holders — which
today immediately flags `crs`, `append_to_pr`, and `create_epic_bead`.

**Ambiguity — do not raise.** Distinguish the two cases:

- **Cross-rank** (user's definition outranks the built-in): highest rank wins silently.
  This is the override story and it must simply work.
- **Same-rank tie**: return a deterministic winner (name-sorted) *and*
  `record_load_issue()` so `sase doctor` reports it, *and* record the broken tie in the
  expansion trace.

This resolves the sharpest disagreement between the two reports. `__a` argued a selector
should fail on a tie rather than guess; `__b` argued for a reproducible winner plus a
doctor issue. `__b`'s position is right for one decisive reason: **the raise is the
defect.** D3 exists precisely because `get_by_tag_strict` turns a second holder into a
runtime crash of `sase bead work`. Replacing one raise with another raise reproduces the
failure the redesign exists to remove. `__a`'s concern is legitimate and is met by
loudness rather than by failure — doctor issue, trace entry, and a warning surfaced at
expansion time. A same-rank tie is rare, always local misconfiguration, and always has a
deterministic escape hatch:

**Pin.** Config `xprompt_tag_bindings: {work_task_bead: my_work_task}` outranks all
inference. This is R4's escape hatch and the answer for anyone who hits an ambiguity
they do not want to resolve by moving files.

**Test the real ordering.** `tests/test_xprompt_tags_lookup.py` must stop patching
`get_all_prompts` with hand-ordered dicts and instead build definitions across real
source buckets in `tmp_path` — including the `.md`-vs-`.yml` case and the same-name
case. The current test is the reason D2 and D6 survived.

### Phase 2 — The `tag/` reference namespace

- Reserve `tag/` in `reserved_namespaces.py`, mirroring
  `reject_reserved_memory_namespace`. Reservation is already Rust-backed via
  `content_layout.reserved_memory_namespace_issue`, so add the sibling there.
- After all sources merge, synthesize `tag/<role>` → winner for each `ROLE` with at
  least one holder, registering into the catalog matching the winner's kind.
- **Flag synthetic entries as selector records** so they appear only under a `#tag/`
  prefix or a "Roles" completion group — not in the bare `#` list. Without this,
  every role is duplicated in the picker.
- Record the tag→name hop in `ExpansionTrace`, and keep the selector in
  `used_xprompts` metadata alongside the canonical target (e.g.
  `invoked_as: "tag/work_phase_bead"`), so a run stays reproducible even if the binding
  later changes:

  ```text
  #tag/work_phase_bead -> #bd/work_phase_bead
    reason: highest-ranked holder for role work_phase_bead
    source: default_config
  ```

- Completion, `sase xprompt show tag/propose`, the catalog PDF, and `used_xprompts` then
  need no per-surface work — they read the catalog.

### Phase 3 — Observability and adoption

- `sase xprompt tags` — every tag, its cardinality, its holders in rank order, the
  winner, and the reason (rank / pin / tie-break). This is the D5 fix and what makes
  the feature debuggable. Expose the existing structured-catalog tag filter on the CLI
  at the same time.
- Migrate the 11 call sites in §1.2 to `resolve_tag()`; keep `get_by_tag*` as
  compatibility wrappers during the transition.
- Extend `doctor/checks_config_xprompts.py` with the tag-health check.
- Align the Rust catalog to the shared registry so completion, hover, and diagnostics
  cannot disagree with execution.

### Explicitly not recommended

**Do not emit `#tag/<role>` into rollover metadata.**
`embedded_workflow_refs_from_metadata` (`run_agent_exec_plan_artifacts.py:56-92`)
re-emits concrete names like `#commit`. Making rolled-over prompts re-resolve by tag
would let a restarted agent silently switch which commit workflow it uses. Rollover must
keep pinning names — a resolved binding is a point-in-time decision, and rollover exists
to reproduce a run, not to re-derive it.

### Boundary note

Tag resolution passes the `rust_core_backend_boundary` litmus test: an editor or web
frontend needs the same answer as the TUI, and the editor catalog already parses tags
independently (§1.4) and already filters by them in duplicated Python/Rust code (D5).
The **registry and ranking rule belong in `sase-core`**. Pragmatically, phases 0–1 can
land in Python consuming `XpromptSource.priority` — that is already the Rust-owned
ordering — with the registry moved into core when phase 2 lands, since namespace
reservation is Rust-side anyway. This sequencing keeps the reliability fix unblocked by
a cross-repo change while ending at the right architecture.

---

## Verification plan

Beyond the phase-1 ordering tests: every argument spelling after `#tag/<role>`; inline
vs `#!` marker validation and HITL suffixes; references inside fenced/disabled zones and
introduced by recursive expansion; project-scoped catalog selection; a higher-priority
different-name override winning; the `.md`-vs-`.yml` case; the same-name divergence case
(D6); same-rank ties producing a stable winner *and* a doctor issue; pin precedence;
VCS-scoped selection across two provider plugins, with and without provider context;
rejection of `vcs`/`rollover` as markers; unknown-tag load issues with no catalog crash
and no same-name fallback; `show`/trace/`used_xprompts` provenance; and Python/Rust
conformance fixtures fed the same catalog expecting the same winner.

---

## Open questions

1. **Is `#tag/x` too verbose for daily use?** It costs four characters over a bare name.
   A shorter prefix is possible but `t/` collides visually with the existing `t`
   xprompt.
2. **Should `MARKER` tags get a plural form** — `#tags/rollover` expanding to all
   holders? Nothing needs it today; noted so the `tag/` grammar is not designed in a way
   that forecloses it.
3. **What happens to the three dead reserved tags?** `create_epic_bead` has no consumer
   and should probably be deleted; `crs` and `append_to_pr` have consumers expecting
   `None` and should either get built-in holders or be documented as opt-in.
4. **Should the collision-rule unification (D6) be its own change?** It touches name
   resolution, not just tags, and could regress prompts that rely on the current
   workflow-wins behavior in `get_all_prompts`. Worth landing separately with its own
   audit.

---

## Appendix — reproduction commands

```bash
# live tag census with dict indices (shows the xprompt/workflow split)
.venv/bin/python -c "
from sase.xprompt.loader import get_all_prompts
for i,(n,w) in enumerate(get_all_prompts().items()):
    if w.tags: print(i, n, sorted(t.value for t in w.tags), w.source_path)"

# D1: one bad tag takes down the whole catalog (isolated HOME)
TH=$(mktemp -d); mkdir -p $TH/sase/xprompts
printf -- '---\nname: good\n---\nfine\n' > $TH/sase/xprompts/good.md
printf -- '---\nname: bad\ntags: research\n---\noops\n' > $TH/sase/xprompts/bad.md
(cd $TH && HOME=$TH .venv/bin/python -c "
from sase.xprompt.loader import get_all_xprompts
try: print('OK', len(get_all_xprompts()))
except Exception as e: print('CATALOG DOWN:', e)")

# D2/D6: override direction by extension, and name-vs-role divergence
#   see the tables in Part 2 — build a candidate dict via
#   {**{n: xprompt_to_workflow(x) for n,x in xprompts.items() if n not in workflows},
#     **workflows} and call get_by_tag(XPromptTag.propose)
```
