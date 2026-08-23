---
create_time: 2026-08-23
updated_time: 2026-08-23
status: research
---

# Moving Task-Bead Types Out Of Always-Loaded Memory And Into An End-Of-Turn Finalizer

**Research question:** What is the best way to retire `sase/memory/task_types.md` as a
`type: short` always-loaded memory note and replace it with a project-configurable
finalizer (`use: builtin@tasks`) that is active only for SASE-managed projects and that
prompts an agent to consider filing task beads at the very end of its turn?

**Scope:** `sase` at `0ccfd7a6ff` (0.16.0) and `sase-core` at `dd198449b4`, both read
locally. Covers `src/sase/finalizers/`, `src/sase/main/init_memory/`,
`src/sase/main/repo_init_handler.py`, `src/sase/task_types/`, `src/sase/config/`, and
`crates/sase_core/src/finalizer/`. Prior art reviewed: `202608/finalizer_protocol_and_extensibility/`,
`202608/finalizer_completion_contracts/`, `202608/finalizer_integrity_and_capabilities/`,
and `202608/task_bead_type_registry/`. This is architecture research; no behavior was
changed.

## Bottom line

Build **`builtin@tasks`, a fourth host-owned builtin finalizer provider**, activated by
a project-local `finalizers.instances.tasks` block that `sase init` writes into
`sase/sase.yml` for `is_sase_managed: true` repositories only. Give the finalizer three
things the substrate does not have yet:

1. an **agent-facing `instructions` string on the host-side `sase final context`
   payload** (not on the Rust wire), rendered from the live agent-creatable task-type
   catalog;
2. a **typed, falsifiable payload** — a decision plus the bead IDs it claims — verified
   by the host against the bead store rather than trusted;
3. a **`trigger: always` / `submission_required: true` requirement whose
   `requirement_digest` is deliberately independent of bead state**, so filing a bead
   mid-declaration cannot invalidate the context the agent is holding.

This needs **no `sase-core` change**: the Rust `FinalizerTriggerKindWire::Always` variant
already exists and is legal with `submission_required: true`, and every `builtin@commit`
reference in the Rust crate is confined to tests. It also needs no new feature flag —
the pluggable-finalizer beta has already landed and retired.

The single non-obvious constraint the design must respect is that
`finalizers.defaults` is **replaced**, not merged, by the last config layer that sets it,
while `finalizers.instances.<id>.<field>` merges per field. `sase init` must therefore
write the *effective* defaults list, not `[commit, tasks]` blindly.

Net effect on Tier 1 context: **~1,745 of ~5,944 always-loaded memory tokens (≈29%)
disappear from every turn** and are replaced by a short, just-in-time prompt paid only
at the end of turns that actually reach the declaration.

---

## 1. What the text costs today, and where it lives

`sase memory list` in this workspace reports:

| File | Lines | Approx. tokens |
| --- | --- | --- |
| `AGENTS.md` (project, inlines every short note) | 361 | 4,353 |
| `~/AGENTS.md` (home, inlines every home short note) | 141 | 1,591 |
| `sase/memory/task_types.md` | 94 | **925** |
| `~/sase/memory/task_types.md` | 83 | **820** |

Total always-loaded context is 5,944 tokens. The task-type note accounts for 925 of the
project root's 4,353 (21%) and 820 of the home root's 1,591 (**52%**). Combined, this
one note is roughly **29% of everything SASE puts in Tier 1**, on every turn, in every
project, whether or not the agent ever discovers follow-up work.

The note is fully generated, in two variants, by
`src/sase/main/init_memory/root_rendering_task_types.py`:

- `render_generated_task_types_memory_body(include_project_memory=True)` renders the
  committed project catalog (`build_committed_task_type_snapshot_entries`), which also
  backs `sase/task_types.json`.
- `render_generated_task_types_memory_body(include_project_memory=False)` renders the
  machine-global builtin catalog for `~/sase/memory/`, deliberately excluding project
  and optional-plugin types so every project on the machine renders the same home note.

Both feed `generated_memory_note_relative_paths()`, `generated_short_notes()`, and
`render_expected_memory_files()`; the note body itself comes from the packaged template
`src/sase/main/init_memory/templates/memory-sase-task-types.template.md`.

**Consequence for the migration:** two roots must be handled, not one. Dropping the
project note alone leaves ~820 tokens of duplicated, staler catalog in `~/AGENTS.md`
that would then contradict the finalizer in projects that opt out.

The note's content splits cleanly into three parts with different natural homes:

| Part | Natural home after migration |
| --- | --- |
| Per-type `when_to_use`, required/optional fields | finalizer instructions (live catalog) |
| "File discovered work as task beads" nudge + the three examples | finalizer instructions |
| "You MUST use `/sase_new_task`", `--size`, `-T`, `-f` mechanics | already in `/sase_new_task` — do not duplicate |

That last row matters: `/sase_new_task` already carries the full procedure (duplicate
search, weekly sweep, epic causal check, create/dep/ready). The finalizer instructions
therefore need to be *much shorter* than 925 tokens — a nudge, the catalog, and a
pointer.

## 2. What the finalizer substrate already provides

Read `src/sase/finalizers/` end to end. The pieces that are already load-bearing:

**Configuration.** `load_finalizer_config()` replays `load_config_layers()` and keeps
per-field provenance. Three keys: `defaults`, `required`, `instances`. Each instance has
`use`, `after`, `max_attempts`, `refusal`, `config`. `plugin:` layers are hard-rejected
from activating finalizers (`plugin_config_activation`), so only default, user, overlay,
and **project-local** layers can turn one on. Project-local config is
`sase/sase.yml` via `get_local_config_path()`.

**Selection.** `%final:tasks` / `%final:!tasks` / `%final:none` are ordered selector
operations resolved in Rust (`finalizer/selection.rs`). `required` pins an instance
against removal.

**Declaration.** `sase final context` (`publish_final_context`) computes requirements and
obligations, validates through Rust, and writes `final_context.json` with a
host-computed `manifest_template`. `sase final submit` re-reads the context under an
flock, rejects a stale `context_digest`, validates through Rust, then runs Python
per-provider payload validation.

**Recovery.** `ensure_final_declaration_or_recover()` gives exactly one extra LLM turn
when a required submission is missing, and fails closed after it. Pending handoffs
(plan/monitor/pipe/questions) are exempt via `has_pending_handoff`.

**Execution.** `execute_non_commit_finalizer()` dispatches `builtin@command` to a
bounded subprocess and everything else to the isolated plugin worker
(`describe → validate → execute → verify`).

**Triggers.** `build_context_requirements()` in `declaration_store.py` is the whole
trigger vocabulary today:

| Provider | trigger | submission_required |
| --- | --- | --- |
| `builtin@commit` | `dirty_repository` or `not_triggered` | true iff dirty repos exist |
| `builtin@command` | `always` | **false** |
| anything else | `provider_requested` | **true, unconditionally** |

### 2.1 The Rust core is provider-agnostic — no `sase-core` change is needed

`crates/sase_core/src/finalizer/` validates envelopes, digests, plan ordering, and
requirement coverage. It never interprets a payload body. Every `builtin@commit` string
in the crate is inside a `#[cfg(test)]` fixture. Two specific facts unlock the design:

- `FinalizerTriggerKindWire` already has an `Always` variant (`wire.rs:144-149`).
- `validate_finalizer_context` rejects only the combination `NotTriggered` **and**
  `submission_required` (`submission.rs:55-63`). `Always` + `submission_required: true`
  is legal today and simply has no producer.

This is exactly the shape `builtin@tasks` needs, and it lands entirely in Python. It is
consistent with the `rust_core_backend_boundary` note: payload *shape* validation for
`builtin@commit` (`_validate_commit_payload`) already lives in Python, and trigger
evaluation/ordering/digests — the genuinely shared parts — stay in Rust.

### 2.2 The `%final` selector solves the epic-phase-worker carve-out for free

Today's note carries an awkward inline exception:

> Unless your prompt explicitly forbids creating beads (epic phase workers, for
> example, must record `PROPOSED FOLLOW-UP:` notes on their own bead instead)…

That clause exists because always-loaded text cannot vary per launch. A finalizer can:
the epic phase-worker xprompt in `default_config.yml` adds `%final:!tasks` and the whole
clause disappears from the instructions. This only works if `tasks` is in
`finalizers.defaults` and **not** in `finalizers.required`.

## 3. The real gaps

**G1 — There is no agent-facing instruction channel.** `sase final context` emits
`selected_instances[]` with `instance_id`, `provider_ref`, `trigger`,
`submission_required`, and `policy`, plus a `manifest_template`. Nothing carries prose.
The pretty renderer (`declaration_format.py`) prints instance IDs and repo obligations
only. The provider protocol *has* a `describe` operation, but it is invoked in
`_execute_plugin_once` **after** the turn ends, so its output can never reach the agent.
This is the one genuinely missing primitive.

**G2 — No builtin provider is "ask the agent a question and take a typed answer."**
`builtin@commit` demands a payload but is tied to repository obligations;
`builtin@command` runs a subprocess and demands nothing. A plugin provider would demand
a payload today (`provider_requested` / `submission_required: true`), but at the cost of
a Python subprocess per `validate` call and no way to ship it in-tree.

**G3 — `finalizers.defaults` is replaced, not merged.** In `config.py::_merge_layer`,
`state.defaults = _string_list(...)` overwrites on every layer that sets the key, while
`_merge_instance_fields` merges instance fields per key across layers. So a project-local
`finalizers: {defaults: [commit, tasks]}` silently drops a user-level
`defaults: [commit, lint]`. Writing `instances.tasks` is safe and additive; writing
`defaults` is destructive. `sase init` must compute the merged list rather than assume
`[commit]`.

**G4 — Requirement digests must not depend on bead state.** The context digest covers
`requirements[].requirement_digest`, and `submit_final_manifest` fails with
`stale_final_context` if the live context moves. Filing a bead is *safe* here — the bead
CLI auto-commits the `beads` sidecar itself (`chore(beads): …` in
`sase/repos/beads` history, via `bead/_sync_git.py`), so no new dirty-repository
obligation appears. But if `builtin@tasks` were to hash "beads created so far" into its
`requirement_digest`, every `/sase_new_task` call between `context` and `submit` would
invalidate the manifest and force a rebuild loop. The digest must be
`{instance_id, trigger: "always"}` and nothing more, exactly like `builtin@command`.

**G5 — Memory has only two types.** `MemoryNoteType = Literal["short", "long"]`
(`memory/notes.py:24`), enforced again in `xprompt/loader_memory.py`. There is no type
that means "generated, versioned, agent-facing, but *not* Tier 1 and *not* an audited
`sase memory read` target." This is the type the user plans to add; the design below
leaves a clean seam for it rather than pre-supposing its name.

## 4. Options considered

### 4.1 How the instructions reach the agent

| Option | How | Verdict |
| --- | --- | --- |
| **A. `instructions` on the host context payload** | Add `selected_instances[].instructions` in `_context_payload()`; also render it in `format_context_pretty` | **Recommended.** Pure Python. `FinalizerContextWire` is `#[serde(deny_unknown_fields)]`, but `_context_payload` is host JSON *outside* the signed wire, so no Rust change and no digest churn. |
| B. Put the text in the `/sase_final` skill | Skill bodies load only on invocation, so this already gets "end of turn" | Rejected: `/sase_final` is provider-neutral and global; project-specific task guidance there fires in projects with no `tasks` instance. |
| C. A separate `/sase_tasks` skill named by the context | Context says "now run `/sase_tasks`" | Rejected as the primary channel: an extra round trip and a second place to keep in sync. Viable later if instructions grow past a few hundred tokens. |
| D. Provider `describe` surfaced pre-submit | `sase final context` runs `describe` for each selected instance | Right long-term answer for *plugin* providers, wrong first step: a subprocess per instance per context publication, and the controller republishes context every cycle. Design A's field so D can fill it later, behind a `(provider_ref, config_digest)` cache. |
| E. Obligations | Emit one obligation per task type | Rejected: `FinalizerObligationWire` has no free-text field beyond `display_name`, and obligations are meant to be opaque host-issued IDs the agent must cover, not reference material. |

### 4.2 How the finalizer is activated for SASE-managed projects only

| Option | Verdict |
| --- | --- |
| **A. `sase init` writes `finalizers.instances.tasks` into project-local `sase/sase.yml`, gated on `is_sase_managed`** | **Recommended.** Exactly the `sase init repo` precedent: `repo_init_handler.py` already refuses on `not management.is_sase_managed`, edits the project config with the comment-preserving `set_key`, and commits with `chore: initialize SASE repositories`. `sase init` also runs as a post-commit hook, so existing managed projects self-heal. |
| B. Ship `tasks` in `defaults` in `src/sase/default_config.yml` and gate at trigger time | Simpler (zero init work) but implicit and invisible: `sase final list` would show `tasks` in unmanaged projects, and there is no per-project record of the choice. |
| C. Ship it as a plugin (`sase-tasks@tasks`) | Rejected: task beads are core SASE, and a plugin cannot activate itself — a config instance would still be required, so this adds a distribution without removing a step. |

Adopt A **plus** B's trigger gate as defense in depth: `builtin@tasks` should report
`trigger: not_triggered, submission_required: false` when the project is not SASE-managed
or has no bead store, so a stray user-level instance cannot demand task declarations in
an unrelated repository.

### 4.3 What the agent must submit

| Option | Verdict |
| --- | --- |
| `{"considered": true}` | Rejected: unfalsifiable, so it degenerates into a reflex. |
| Free-text rationale only | Weak: nothing ties the claim to reality. |
| **Typed decision + claimed bead IDs, host-verified** | **Recommended.** The host can check each ID against the bead store and reject fabrications, which is what turns the declaration into evidence rather than a promise. |

## 5. Recommended solution

### 5.1 Configuration written by `sase init`

```yaml
# sase/sase.yml, in a SASE-managed project
finalizers:
  defaults: [commit, tasks]     # written as the *effective* list (see G3)
  instances:
    tasks:
      use: builtin@tasks
      after: []
      max_attempts: 1
      refusal: fail
```

Implementation notes:

- Add `builtin@tasks` to `_BUILTIN_PROVIDER_REFS` (`finalizers/config.py`) and
  `BUILTIN_PROVIDER_REFS` / a `FinalizerProviderRecord` in `finalizers/providers.py`
  with capabilities `("execute", "verify")`. The `use` pattern in
  `src/sase/config/sase.schema.json` (`^[A-Za-z0-9_.-]+@[a-z][a-z0-9_-]*$`) already
  admits it; only the human-facing description needs updating.
- Add a `_TASKS_CONFIG_KEYS` allowlist and a `parse_tasks_finalizer_config()` mirroring
  `parse_command_finalizer_config()`, so an unknown `config.` key is a `sase final
  doctor` error rather than silent.
- **`defaults` must be computed, not assumed.** The init step should read the effective
  `load_finalizer_config().defaults`, append `tasks` if absent, and `set_key` the result.
  Idempotent: no write when `tasks` is already present.
- Register a new `InitCommandSpec(name="finalizers", label="Finalizers", …)` in
  `iter_init_command_specs()`, ordered **after** `config` (owner identity) and before or
  beside `repo`. Give it the same `plan_*` / `run_*` pair so `sase init --check` and
  `sase init --diff` work unchanged. Fold the written path into the existing
  `commit_workspace_paths` call so the config edit lands as one `chore:` commit.

### 5.2 Host trigger

In `build_context_requirements()`, add a branch before the generic fallback:

```python
if entry.provider_ref == "builtin@tasks":
    active = project_is_sase_managed(...) and bead_store_available(...)
    trigger = "always" if active else "not_triggered"
    requirements.append(FinalizerPayloadRequirementWire(
        instance_id=entry.instance_id,
        trigger=trigger,
        submission_required=active,
        requirement_digest=finalizer_json_digest(
            {"instance_id": entry.instance_id, "trigger": trigger}
        ),
    ))
    continue
```

The digest deliberately omits bead state (G4). `project_is_sase_managed` already exists
in `sase/feature_flags/managed.py`; reuse it rather than re-reading YAML.

### 5.3 Agent-facing instructions

Add `instructions: str` to each entry of `selected_instances` in
`declaration.py::_context_payload()`, populated by a small host-side renderer keyed on
`provider_ref`:

- `builtin@commit` → the repository decision rules currently duplicated in the
  `/sase_final` skill (a free cleanup, not required for this change).
- `builtin@command` → empty.
- `builtin@tasks` → the rendered block below.
- external providers → empty for now; this is the field option D fills later.

Render it in `format_context_pretty()` too, so `sase final context` without `-f json` is
still usable by a human debugging a turn.

Source the `builtin@tasks` body from a packaged template
(`templates/finalizer-tasks.template.md`) with one substitution, reusing the existing
`_render_task_type_note_entries()` / `format_agent_creatable_type_listing()` renderers so
the catalog can never drift from `sase bead task-type list`. Target well under 300
tokens — roughly:

> Before you finish: did this turn surface work that belongs on its own task bead?
> Agent-creatable types in this project:
> `bug` — a defect found while doing unrelated work · `ci` — a confirmed failure ·
> `feature` — an out-of-scope idea · `flake` — fails then passes on an unchanged tree ·
> `memory` — an out-of-date sase note or skill.
> File one for: a lint/test failure you did not cause; an out-of-date sase memory note
> or skill; a bug or clear objective improvement in a tool this project owns.
> If yes, use `/sase_new_task` **now**, then declare the resulting bead IDs. If no,
> declare `none` with a one-line reason.

Everything about `--size`, `-T task(<slug>)`, `-f`, duplicate search, and epic
corroboration stays in `/sase_new_task` and is *not* repeated here.

### 5.4 Payload and verification

`manifest_template()` gains a `builtin@tasks` branch:

```json
{"instance_id": "tasks", "payload": {"decision": "none", "reason": "<one line>"}}
```

Accepted shapes:

```json
{"decision": "none",         "reason": "<nonblank>"}
{"decision": "filed",        "beads": ["sase-a1", "sase-b2"]}
{"decision": "corroborated", "beads": ["sase-a1"]}
```

`validate_provider_payloads()` gets `_validate_tasks_payload()` alongside
`_validate_commit_payload()`: exactly one `decision`, no unknown keys, `reason` nonblank
and bounded (reuse the 4,000-byte cap), `beads` nonempty and well-formed for the two
non-`none` decisions.

Then — and this is what makes the declaration worth its tokens — `builtin@tasks`
`execute`/`verify` resolves each claimed ID against the bead store and confirms it is a
**task** bead touched by this run. `sase bead list --format json` already returns
`id`, `issue_type`, `created_at`, `created_by` (e.g. `bbugyi200.athena.0b6`), and
`plus_one_count`, and the finalizer context already carries `run_id` and `agent_id`. A
fabricated or unrelated ID fails the instance. `decision: "none"` executes as a no-op
success that records the reason as evidence.

Start with `max_attempts: 1` and `refusal: fail`. Consider emitting a non-fatal
diagnostic (rather than a hard failure) on the *identity* check in the first release, so
an agent-id mismatch in an unusual family/clan launch does not fail otherwise-good turns
until the matching rule is proven.

### 5.5 Memory removal, in two steps that match the planned memory type

**Step 1 (with this change).** Stop generating `sase/memory/task_types.md` in both
roots: drop it from `generated_memory_note_relative_paths()`, `generated_short_notes()`,
and the `expected` list in `render_expected_memory_files()`; delete the
`generated_task_types_body` plumbing through `root_rendering.py`. Keep
`render_generated_task_type_snapshot_json()` and `sase/task_types.json` exactly as they
are — the committed catalog snapshot is independent of the note and is what
`sase bead task-type` diffing relies on. `sase memory init` must actively remove a
stale note (it already blocks on unexpected content at generated paths, so this needs an
explicit retirement path, not silence).

**Step 2 (when the new memory type lands).** Reintroduce
`sase/memory/task_types.md` with the new frontmatter type — a note that is neither
inlined into `AGENTS.md` nor an audited `sase memory read` target — and let the instance
name it:

```yaml
    tasks:
      use: builtin@tasks
      config:
        memory: task_types.md
```

`builtin@tasks` then prefers that note's body over the packaged template. This is why
the instructions renderer should read from a resolvable source from day one rather than
inlining a Python string literal: step 2 becomes a config key plus a loader, not a
rewrite. It also generalizes — a later `builtin@note` provider is just this mechanism
without the bead verification.

Update `memory-README.template.md`'s frontmatter-schema section in the same change that
introduces the type; it currently documents `short` and `long` as exhaustive.

### 5.6 Prompt and skill updates

- `sase/memory/sase.md` (Tier 1, ~775 tokens) already says to end with `/sase_final`.
  No change needed — agents will meet the tasks requirement through the path they
  already take. This matters: because the requirement is `always`, a turn that skips
  `/sase_final` now burns the one declaration-recovery turn, where previously a clean
  turn needed no declaration at all.
- `/sase_final` skill: extend step 2 to "if `submission_required` is false, stop", plus
  "read `instructions` on each selected instance and satisfy it before building the
  manifest." Add one line: any repository mutation you make while satisfying an
  instruction (there should be none for `tasks`, since the bead CLI commits its own
  sidecar) requires rerunning `sase final context`.
- Epic phase-worker xprompt in `default_config.yml`: add `%final:!tasks` and drop the
  `PROPOSED FOLLOW-UP` carve-out sentence from the finalizer instructions entirely.
- `sase/memory/sase_beads.md` (Tier 2) keeps its epic-phase-worker paragraph; it is read
  on demand and is not part of the token cost being removed.

### 5.7 Phasing

1. **Substrate.** `instructions` on the context payload + pretty renderer + tests. No
   behavior change; every existing provider renders empty.
2. **Provider.** `builtin@tasks` registration, trigger branch, manifest template,
   payload validation, execute/verify. Configure it in this repo's `sase/sase.yml` by
   hand and soak for a few days of real turns.
3. **Init.** The `finalizers` init spec with effective-defaults merging, `--check` and
   `--diff` support, and the SASE-managed gate.
4. **Memory retirement.** Remove both generated notes, add the retirement path to
   `sase memory init`, regenerate `AGENTS.md` and every provider shim, and measure the
   Tier 1 delta with `sase memory list`.
5. **Memory type (separate work).** New frontmatter type + `config.memory` on the
   instance.

Steps 1–3 are independently landable and reversible. Step 4 is the one that changes what
agents see, so it should follow a soak, not precede it.

## 6. Risks and open questions

- **Every turn now requires a declaration.** Today a clean, commit-free turn submits
  nothing. With `trigger: always`, every non-handoff turn does. The recovery machinery
  handles a forgotten `/sase_final`, but at the cost of a full extra LLM turn. Watch
  `sase_finalizer_recoveries_total{kind="declaration"}` after step 2; a spike means the
  Tier 1 `/sase_final` instruction is not landing reliably enough to make `always` safe.
- **A nudge at the end of a turn is a weaker nudge.** Always-loaded text primes an agent
  to *notice* a flake while it is happening; an end-of-turn prompt asks it to recall.
  This is the core trade the user is making, and it is probably the right one — but the
  honest mitigation is that `just check` failures and `sase memory read` are already the
  moments that generate most task beads, and both are recent context at declaration
  time. Worth measuring: task-bead creation rate per 100 turns, before and after.
- **`defaults` replacement (G3)** is a latent footgun beyond this change. Consider a
  follow-up that either unions `defaults`/`required` across layers or adds an explicit
  additive form; until then, every writer of `finalizers.defaults` must write the
  effective list.
- **Home-root behavior.** After step 4, `~/AGENTS.md` carries no task-type guidance at
  all. Agents working in a SASE-managed project get it from the finalizer; agents
  working outside one get nothing, which is correct (no bead store) but is a real
  behavior change for ad-hoc work in unmanaged directories.
- **Boundary question.** `_validate_tasks_payload` in Python follows the
  `_validate_commit_payload` precedent, but a web or editor frontend that wants to
  pre-validate a declaration would need it in `sase-core`. Acceptable now; revisit if a
  second frontend appears.
- **Open:** should `decision: "none"` require a reason at all? Requiring one costs a
  sentence per turn and risks boilerplate ("no follow-up work discovered"); omitting it
  makes `none` a single keystroke. Recommendation: require it initially, and drop the
  requirement if the reasons turn out to be uniformly vacuous.

## 7. Test matrix

- `builtin@tasks` selected but project not SASE-managed → `not_triggered`,
  `submission_required: false`, and Rust context validation still passes.
- `builtin@tasks` in a managed project → `always` + `submission_required: true`, context
  digest stable across two publications with no intervening change.
- Filing a bead between `context` and `submit` does **not** produce
  `stale_final_context` (the G4 regression guard).
- Payload: each valid decision accepted; unknown keys, missing reason, empty `beads`,
  and both `reason` and `beads` together rejected with distinct codes.
- Verify: a fabricated bead ID fails the instance; a real bead created by a different
  run is rejected (or diagnosed, per §5.4); a `+1` on an existing bead satisfies
  `corroborated`.
- `%final:!tasks` removes the instance; `tasks` in `finalizers.required` makes removal a
  launch-time error.
- `sase init` on a managed project with no `finalizers` block writes
  `defaults: [commit, tasks]`; on one with user-level `defaults: [commit, lint]` writes
  `[commit, lint, tasks]`; on an unmanaged project writes nothing; second run is a no-op.
- `sase init --check` reports drift; `sase init --diff` renders the config edit.
- `sase memory init` after retirement removes both generated notes and regenerates
  `AGENTS.md` plus every provider shim; `--check` reports drift on a stale note.
- `sase final doctor` flags an unknown `builtin@tasks` `config.` key.
- `sase final context` pretty output shows the instructions block; JSON output carries
  `selected_instances[].instructions`.
- The declaration-recovery turn still succeeds when only the `tasks` payload is missing.
