---
create_time: 2026-08-08
updated_time: 2026-08-08
status: research
---

# Invoking XPrompts by Tag Instead of by Name

**Research question:** what is the most reliable way to let a prompt (and core code)
invoke an xprompt *by the semantic role it fills* rather than by its name?

**Scope:** the `sase` repo at master `72ec6aa3a`, the `sase-github` plugin at `7dd02fc`,
and the live catalog of this machine as observed on 2026-08-08 (`sase xprompt list`,
106 prompts). All census numbers below are measured from the running installation, not
read off the source tree.

## Bottom line

sase **already has a tag-based invocation system** — `sase.xprompt.tags` — and it is
already the binding mechanism for eleven core behaviors (bead automation, mentor
review, fix-hook, rollover, VCS wrapping). It is not user-invocable and it is not
reliable, for three measured reasons: an unknown tag is a hard crash of the entire
catalog, the "highest priority wins" resolver is a dict-insertion-order artifact that
provably inverts the documented precedence chain, and the strict variant makes the
documented "override it by tagging your own" workflow impossible.

The recommendation is therefore **not** "add a tag syntax." It is:

1. Make tag resolution deterministic against the Rust-owned source precedence that
   already exists (`XpromptSource.priority`), with an explicit config pin as the
   escape hatch.
2. Open the tag vocabulary and stop raising on unknown tags.
3. Expose the resolved binding as a reserved **`tag/` reference namespace** —
   `#tag/propose`, `#!tag/land_epic` — materialized in the loader as synthetic catalog
   entries, so it needs zero changes to the reference lexer and inherits completion,
   `xprompt show`, args, and `#!` for free.

Steps 1–2 are the actual deliverable; step 3 is cheap once they are done, and
worthless before.

---

## Part 1 — Audit: what tags exist today and what they do

### 1.1 The mechanism

`src/sase/xprompt/tags.py` defines `XPromptTag`, a **closed enum of 15 members**.
Tags are declared in frontmatter (`tags: vcs, rollover` or `tags: [vcs, rollover]`),
parsed by `parse_tags()`, and stored as `frozenset[XPromptTag]` on both `XPrompt`
(`models.py:222`) and `Workflow` (`workflow_models.py`). Three lookups exist:

| Function | Behavior on 0 matches | On 1 | On N>1 |
| --- | --- | --- | --- |
| `has_tag(tag)` | `False` | `True` | `True` (set membership) |
| `get_by_tag(tag, vcs_hint=…)` | `None` | the match | `matches[-1]`, optionally steered by plugin module |
| `get_by_tag_strict(tag)` | `None` | the match | **raises `ValueError`** |

### 1.2 Live census

Measured from `sase xprompt list` on 2026-08-08 — **15 of 106 prompts carry a tag**:

| Tag | Declared by | Consumed by |
| --- | --- | --- |
| `vcs` | `git`, `gh` (plugin) | `workflow_loader.py:226` (implies `wraps_all`), `workflow_executor_steps_embedded_expand.py:199` |
| `rollover` | `commit`, `file`, `gh`, `git`, `json`, `pr`, `propose` | `axe/run_agent_exec_plan_artifacts.py:85` — string match on serialized metadata, **not** `XPromptTag` |
| `commit` | `commit` | `ace/tui/actions/agent_workflow/_mentor_review.py:192` |
| `propose` | `propose` | `_mentor_review.py:190` |
| `mentor` | `mentor` | `workflows/mentor.py:74` (strict) |
| `make_mentor_changes` | `make_mentor_changes` | `_mentor_review.py:158` (strict) |
| `fix_hook` | `fix_hook` | `axe/fix_hook_runner.py:172` |
| `diff_file` | `pr_diff` (plugin) | `workflows/mentor.py:87` (with `vcs_hint`) |
| `append_to_commit_and_propose` | `prdd` (plugin) | `workflow_executor_steps_embedded_expand.py:294` |
| `work_phase_bead` | `bd/work_phase_bead` (config) | `bead/xprompts.py:39` (strict) |
| `work_task_bead` | `bd/work_task` (config) | `bead/xprompts.py:44` (strict) |
| `land_epic` | `bd/land_epic` (config) | `bead/xprompts.py:49` (strict) |
| `crs` | **nothing** | `workflows/crs.py:92` |
| `append_to_pr` | **nothing** | `workflow_executor_steps_embedded_expand.py:296` |
| `create_epic_bead` | **nothing** | **nothing** |

Three enum members are dead on this machine. `crs` and `append_to_pr` have live
consumers that silently receive `None`; `create_epic_bead` is vestigial.

### 1.3 The one enum is doing three different jobs

This matters enormously for an invocation syntax, because two of the three jobs have
no single answer to "which xprompt is this tag?".

- **Set markers (cardinality N).** `vcs` and `rollover` describe a property held by
  many prompts. Seven prompts carry `rollover`. `#tag/rollover` is meaningless.
- **Role bindings, tolerant (cardinality 1, best-effort).** `commit`, `propose`,
  `fix_hook`, `diff_file`, `crs`, `append_to_*`. Resolved with `get_by_tag`, which
  guesses when there are several.
- **Role bindings, strict (cardinality 1, enforced).** `mentor`,
  `make_mentor_changes`, and the three bead tags. Resolved with `get_by_tag_strict`,
  which *refuses to work* when there are several.

Only the two role categories are candidates for invocation. The distinction is
currently implicit — nothing in the enum or the frontmatter declares cardinality, so
nothing can validate it.

### 1.4 Four unrelated things in this codebase are called "tags"

Any user-facing `tag` syntax lands in a crowded namespace. For the record:

1. `XPromptTag` — the subject of this note.
2. `PromptFrontmatter.tags` (`prompt_frontmatter.py:99`) — a `list[str]` the TUI
   frontmatter panel edits, documented as "free-form; core does not constrain ad-hoc
   prompt tags." This is the *same YAML key* as (1), with the opposite contract. See
   defect D4.
3. **VCS workflow tags** — `_parsing_vcs_tags.py` calls the leading `#gh:sase`
   workspace reference a "tag" (`extract_vcs_workflow_tag`,
   `replace_vcs_workflow_tags`). Unrelated concept, heavily used.
4. `saved_tag_names` / ChangeSpec `pr_tags` — user-defined labels like `BUG`,
   `FEATURE` (`ace/saved_tag_names.py`). Unrelated concept.

### 1.5 What the docs promise

`src/sase/bead/xprompts.py:5-7` states:

> users may override any of them by tagging an xprompt of their own with the same tag
> (the loader's precedence chain handles which one wins, and `get_by_tag_strict`
> rejects ambiguous setups)

Both halves of that sentence are wrong in practice — see D2 and D3. The long-term
memory note `sase/memory/xprompts.md` documents `tags` only as a frontmatter field and
makes no invocation claim, so no user-facing contract is broken by changing this.

---

## Part 2 — Why tag invocation is unreliable today

Five defects, each independently verified.

### D1 — An unknown tag crashes the entire catalog

`parse_tags()` raises `ValueError` on any name outside the enum. `load_xprompt_from_file`
(`loader_sources.py:135`) calls it with no guard, inside the generator
`_load_ordinary_xprompts_from_dir`, which is itself unguarded. The exception escapes
`get_all_xprompts()`, so **one bad tag in one file makes every xprompt in the
installation unresolvable.**

Reproduced against the installed build:

```
$ printf -- '---\nname: demo\ntags: research\n---\nbody\n' > $T/demo.md
$ python -c "…_load_ordinary_xprompts_from_dir(Path('$T'))…"
CRASH: ValueError Unknown xprompt tag 'research'. Valid tags: [...]
```

Every other load failure in this package — bad YAML, unreadable file, bad inputs,
misplaced skill, reserved namespace — is routed through `record_load_issue()` and
surfaced non-fatally by `sase doctor` (`doctor/checks_config_xprompts.py:137`) and
`sase xprompt show` (`cli_show_resolve.py:98`). Tag parsing is the sole exception.
`.yml` workflows are equally exposed: `workflow_loader.py:225` calls `parse_tags` before
the `try` block that guards input parsing.

This alone disqualifies any design that asks users to write their own tags.

### D2 — "Highest priority wins" is a dict-ordering artifact, and it inverts

`get_by_tag` returns `matches[-1]`, justified by:

> Uses `get_all_prompts()` so the loader's existing precedence (local > user > plugin >
> builtin) naturally handles override order. The dict is built from lowest to highest
> priority, so we return the **last** match.

That reasoning does not hold, for two compounding reasons.

**(a) `dict.update` does not reorder existing keys.** A name present in both a
low- and a high-priority source keeps its *low-priority* insertion index while taking
the high-priority *value*. So the dict is ordered by first appearance, not by winning
source.

**(b) `get_all_prompts` returns `{**converted_xprompts, **workflows}`
(`loader.py:289`) — every xprompt sorts before every workflow, regardless of source.**
Measured indices in the live catalog:

```
   1 fix_hook            ['fix_hook']           built-in .md
   6 bd/land_epic        ['land_epic']          default_config
  87 file                ['rollover']           built-in .yml
  96 commit              ['commit','rollover']  built-in .yml
 104 prdd                ['append_to_commit…']  plugin .yml
```

Concretely: a user who writes `~/sase/xprompts/my_propose.md` with `tags: propose` —
the highest-priority file source there is — creates an *xprompt*, which lands in the
`converted` half. The built-in `propose.yml` is a *workflow* and lands after it.
`matches[-1]` returns the built-in. **The override is silently ignored.** This is
exactly the documented user story from §1.5.

The existing test suite encodes the assumption rather than testing it:
`tests/test_xprompt_tags_lookup.py:44` patches `get_all_prompts` with a hand-ordered
two-entry dict and asserts the last one wins. It never exercises the real loader
ordering, so the inversion is invisible to CI.

Secondary fragility: the `vcs_hint` disambiguation (`tags.py:102-118`) resolves ties by
comparing plugin module names extracted from `source_path` string prefixes. It has no
answer when the competing definitions are not both plugin-backed, and falls through to
the same `matches[-1]`.

### D3 — Strict tags make override structurally impossible

`get_by_tag_strict` raises on N>1. For `mentor`, `make_mentor_changes`,
`work_phase_bead`, `work_task_bead`, and `land_epic`, adding your own tagged xprompt
does not override the built-in — it **breaks the feature** with
`Multiple xprompts found with tag 'work_task_bead': [...]. Only one is allowed.`

The only working override today is to shadow the *name* (define your own
`bd/work_task` at a higher-priority source), which is name-based invocation wearing a
tag-shaped hat. The tag adds nothing.

### D4 — The TUI writes free-form tags into a closed-vocabulary field

`PromptFrontmatter` (`prompt_frontmatter.py:89-99`) treats `tags` as an unconstrained
`list[str]`, serializes it back into the `.md` frontmatter (`:197`), and the frontmatter
panel offers it as an editable row. `frontmatter_schema.py` does not validate it.
A user who types `tags: research` in the TUI xprompt-save flow writes a file that
triggers D1 on the next catalog load. The two halves of the same field disagree about
whether the vocabulary is open.

### D5 — Tag bindings are unobservable

`sase xprompt list --json` emits `tags` per entry and the statistics pane renders them
(`statistics_pane_xprompts.py:158`), but there is no way to ask the inverse question.
There is no `sase xprompt show tag/mentor`, no "who holds this tag", no "who lost and
why". Debugging a mis-resolved role means reading `tags.py` and reasoning about dict
insertion order — which, per D2, is not what the docstring says it is.

### D6 — Two catalogs, two resolution paths

Inline `#name` expansion resolves against **`get_all_xprompts()` only**
(`processor.py:358`). Workflow references are resolved separately against
`get_all_workflows()` by ten other call sites (`workflow_runner.py`,
`workflow_executor_steps_embedded_expand.py`, `sdd/_expand.py`, `used_xprompts.py`, …).
`get_all_prompts()` — the merged view `get_by_tag` uses — is consulted by *neither*
expansion path. Any invocation design must decide which catalog a tag reference lives
in, and a tag may resolve to either kind.

---

## Part 3 — Requirements

For "invoke by tag" to be *reliable* in the sense the question asks:

- **R1 Determinism.** The same catalog always yields the same winner. Independent of
  dict insertion order, filesystem iteration order, and plugin install order.
- **R2 Documented precedence.** The winner is the one the loader's published
  precedence chain says it should be, and the losers are inspectable.
- **R3 Fail local, fail loud.** A malformed or ambiguous tag degrades that one
  definition, surfaces in `sase doctor`, and never takes down the catalog or silently
  picks the wrong thing.
- **R4 Overridable.** A user can rebind a role without editing built-ins, and can
  force a binding when inference is ambiguous.
- **R5 Parity with names.** A tag reference must support everything a name reference
  supports: args, colon/`::` shorthand, `#!` standalone launch, HITL suffixes,
  completion, `xprompt show`, expansion trace.
- **R6 Honest cardinality.** `#tag/rollover` must be a clear error, not a coin flip.

---

## Part 4 — Design options

### Option A — Reserved `tag/` namespace, materialized in the loader

`#tag/propose`, `#!tag/land_epic`. The loader registers a synthetic catalog entry
under the key `tag/<role>` whose value is the winning `XPrompt`/`Workflow`.

- **Lexer changes: none.** `XPROMPT_REFERENCE_NAME_FRAGMENT`
  (`_parsing_references.py:21`) already accepts `ns/name`, and `__` → `/` normalization
  means `#tag__propose` works too.
- **Precedent: strong.** `memory/` is exactly this pattern — a reserved namespace whose
  entries are synthesized during load, with `reserved_namespaces.py` already providing
  the "ordinary definitions may not claim this prefix" guard to copy. `skills/` is a
  second instance.
- **R5 falls out for free.** Everything downstream keys off the catalog, so args,
  shorthand, `#!`, completion rows (`_prompt_input_bar_completion_rows_simple.py`),
  `sase xprompt show tag/mentor`, the catalog PDF, and `used_xprompts` all work with
  no per-surface changes.
- **D6 is handled** by registering the synthetic entry in whichever catalog the winner
  lives in — `get_all_xprompts()` for xprompt winners, `get_all_workflows()` for
  workflow winners — preserving inline-vs-standalone semantics.
- **Cost:** `tag/` must be reserved (breaking any existing `tag/*` xprompt; none exist
  in the live catalog, and `tribe.md`/`t.md` are unaffected).

### Option B — New sigil (`#@propose`, `#:propose`)

Rejected. The reference grammar is duplicated in at least two places
(`_parsing_references.py:36` and the independent `_XPROMPT_PATTERN` in
`processor.py:63`), and `@` is already overloaded: model aliases (`%model:@coder`),
launch xprompt at-refs (`normalize_launch_xprompt_at_refs`), and tribe display. Every
completion, highlighting, VCS-tag, and shorthand regex would need auditing for a purely
cosmetic gain over Option A.

### Option C — Textual rewrite in `resolve_xprompt_aliases`

Rewrite `#tag/propose` → `#propose` on raw text before processing
(`processor.py:125`). Cheapest possible insertion point, and satisfies R5 by
construction. But `resolve_xprompt_aliases` runs **before** `protect_fenced_blocks`
(`processor.py:351` vs `:418`), so it rewrites inside code fences — an existing wart of
the `xprompt_aliases` feature that a tag feature should not inherit. It also loses tag
provenance in errors and traces, and does nothing for the surfaces that read the
catalog directly (completion, `xprompt show`, `used_xprompts`). Viable as a fallback
for a surface Option A cannot reach; not viable as the primary mechanism.

### Option D — Generate `xprompt_aliases` entries from tags

Config-level, static, no override chain, no plugin participation, no ambiguity
reporting. Fails R1–R4. Rejected.

### Option E — API only, no prompt syntax

Fix the resolver (Part 5, phase 1), add `sase xprompt resolve --tag <t>`, and leave
invocation to core code. This is the honest minimum: it removes every defect in Part 2
without adding surface area. It just does not answer the question as asked.

### Comparison

| | A `tag/` namespace | B sigil | C text rewrite | D aliases | E API only |
| --- | --- | --- | --- | --- | --- |
| Lexer changes | none | many | none | none | none |
| R5 parity | free | per-surface work | partial | no | n/a |
| Provenance in trace | yes | yes | lost | lost | yes |
| Fence-safe | yes | yes | **no** | no | n/a |
| Handles D6 | yes | needs work | yes | no | n/a |
| Precedent in repo | `memory/`, `skills/` | none | `xprompt_aliases` | itself | — |

---

## Part 5 — Recommendation

**Adopt Option A, on top of a rebuilt resolver.** Three phases; phase 1 is the one that
actually buys reliability and is independently shippable.

### Phase 1 — Make resolution deterministic (`src/sase/xprompt/tags.py`)

Replace `get_by_tag` / `get_by_tag_strict` with one `resolve_tag()` that ranks
candidates explicitly instead of trusting dict order.

**Rank source.** Do not invent a new precedence table. `resolve_xprompt_file_sources()`
returns the *Rust-owned first-wins order*, and each `XpromptSource` already carries
`priority: int` and `scope: str` (`core/content_layout_wire.py:142-155`). Rank
file-backed definitions by the `priority` of the source directory containing
`source_path`; rank the non-file buckets with explicit constants in the order
`get_all_xprompts` already applies them (project config → user config → plugin →
`default_config` → internal). `_catalog_sources.classify()` already computes the coarse
bucket (`built-in` / `plugin` / `config` / `project`) and can seed this.

**Ordering key.** `(source_rank, kind_rank, name)` — with `name` as a deterministic
final tie-break. Never dict position. This kills D2 including the
xprompts-before-workflows inversion, because kind stops being a hidden ordering term.

**Cardinality.** Add a declared cardinality to the tag registry: `ROLE` (exactly one
winner) vs `MARKER` (set membership). `vcs` and `rollover` are markers; the rest are
roles. `resolve_tag()` on a marker is an error with a clear message (R6). Marker
membership stays on `has_tag`.

**Ambiguity.** A same-rank tie on a `ROLE` tag is genuine ambiguity: pick the
name-sorted winner so behavior stays reproducible, **and** `record_load_issue()` so
`sase doctor` reports it. This replaces `get_by_tag_strict`'s raise (D3) — a user who
adds their own `work_task_bead` at a higher-priority source now wins cleanly instead of
breaking `sase bead work`.

**Pin.** Add config `xprompt_tag_bindings: {work_task_bead: my_work_task}` that
outranks all inference. This is R4's escape hatch and the answer for anyone who hits an
ambiguity they do not want to resolve by moving files.

**Open the vocabulary and stop raising (D1, D4).** `parse_tags` should validate *shape*
(identifier-ish), keep unknown names as opaque strings, and `record_load_issue()` rather
than raise. Keep `XPromptTag` as the reserved-role constants that core code binds
against; `has_tag` accepts both an enum member and a string. This is what unifies the
TUI's free-form `tags` with core's role tags, and it is the precondition for letting
anyone write `#tag/<their-own-role>`.

Typo protection lost by opening the vocabulary comes back as a `doctor` check: warn on
a tag within edit-distance 1 of a reserved role, and on any reserved role with zero
holders (which today would immediately flag `crs`, `append_to_pr`, `create_epic_bead`).

**Test the real ordering.** `tests/test_xprompt_tags_lookup.py` must stop patching
`get_all_prompts` with hand-ordered dicts and instead build definitions across real
source buckets in `tmp_path`. The current test is the reason D2 survived.

### Phase 2 — The `tag/` reference namespace

- Reserve `tag/` in `reserved_namespaces.py`, mirroring
  `reject_reserved_memory_namespace`.
- In `get_all_xprompts()` / `get_all_workflows()`, after all sources are merged,
  synthesize `tag/<role>` → winner for each `ROLE` tag with at least one holder,
  registering into the catalog matching the winner's kind (D6).
- Record the tag→name hop in `ExpansionTrace` so `sase xprompt expand --trace` shows
  `tag/propose → propose (built-in propose.yml)`.
- Completion, `sase xprompt show tag/propose`, the catalog PDF, and `used_xprompts`
  need no changes — they read the catalog.

### Phase 3 — Observability and adoption

- `sase xprompt tags` — list every tag, its cardinality, its holders in rank order,
  the winner, and the reason (rank / pin / tie-break). This is the D5 fix and the
  thing that makes the feature debuggable.
- Migrate the eleven call sites in §1.2 to `resolve_tag()`.
- Extend `doctor/checks_config_xprompts.py` with the tag-health check.

### Explicitly not recommended

**Do not emit `#tag/<role>` into rollover metadata.** `embedded_workflow_refs_from_metadata`
(`run_agent_exec_plan_artifacts.py:56`) currently re-emits concrete names like
`#commit`. Making rolled-over prompts re-resolve by tag would mean a restarted agent
could silently switch which commit workflow it uses. Rollover should keep pinning names.

### Boundary note

Per `sase/memory/rust_core_backend_boundary.md`, tag resolution passes the litmus test
for core backend logic — a web app or editor integration would need the same answer as
the TUI. Precedence ranking is *already* Rust-owned via `content_layout`. The resolver
should consume `XpromptSource.priority` rather than re-deriving an ordering in Python,
and whether `resolve_tag()` itself belongs in `sase_core` is a decision the
implementation plan should make deliberately rather than by default.

---

## Open questions

1. **Is `#tag/x` the right spelling, or is it too verbose for daily use?** The
   namespace approach costs four characters over a bare name. A shorter reserved
   prefix is possible but `t/` collides visually with the existing `t` xprompt.
2. **Should `MARKER` tags get a plural form** — e.g. `#tags/rollover` expanding to all
   holders? Nothing needs it today; noting it so the `tag/` grammar is not designed in
   a way that forecloses it.
3. **What happens to the three dead reserved tags?** `create_epic_bead` has no consumer
   and should probably be deleted; `crs` and `append_to_pr` have consumers that expect
   `None` and should either get built-in holders or be documented as opt-in.

## Appendix — evidence commands

```bash
# live tag census
sase xprompt list | python -c "
import json,sys,collections
by=collections.defaultdict(list)
for x in json.load(sys.stdin):
    for t in (x.get('tags') or []): by[t].append(x['name'])
[print(f'{t:32} {by[t]}') for t in sorted(by)]"

# ordering artifact behind D2
python -c "
from sase.xprompt.loader import get_all_prompts
for i,(n,w) in enumerate(get_all_prompts().items()):
    if w.tags: print(i, n, sorted(t.value for t in w.tags), w.source_path)"

# D1 repro
T=$(mktemp -d); printf -- '---\nname: demo\ntags: research\n---\nbody\n' > $T/demo.md
python -c "
from pathlib import Path
from sase.xprompt.loader_sources import _load_ordinary_xprompts_from_dir
list(_load_ordinary_xprompts_from_dir(Path('$T')))"
```
