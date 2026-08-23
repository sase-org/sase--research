---
create_time: 2026-08-23
updated_time: 2026-08-23
status: research
---

# `builtin@tasks`: Moving Task-Type Guidance Out Of Tier 1 And Into An End-Of-Turn Finalizer

**Research question:** What is the best way to retire `sase/memory/task_types.md` as a
`type: short` always-loaded note and replace it with a project-configurable finalizer
(`use: builtin@tasks`), active only for SASE-managed projects, that asks an agent at the
very end of its turn whether discovered work should become task beads?

**Scope:** `sase` at `0ccfd7a6ff` (0.16.0), `sase-core` at `dd198449b4`. Covers
`src/sase/finalizers/`, `src/sase/main/init_memory/`, `src/sase/main/init_registry.py`,
`src/sase/memory/`, `src/sase/config/`, `src/sase/xprompt/_directive_collect.py`, and
`crates/sase_core/src/finalizer/`. Architecture research only; no behavior was changed.

**Provenance note.** The two source reports (`__a`, `__b`) were written concurrently to
the same filename. `__a` (codex) hit a both-added merge conflict and was resolved by its
author against `__b` (claude), so `__a` already absorbed `__b`'s memory-cost table;
`__a`'s pre-merge original is unrecoverable. `__b` is the pristine original. Where the
two still disagree, this report resolves the conflict against the code.

---

## Bottom line

Add **`builtin@tasks` as the third host-owned builtin finalizer provider** — a
**declaration-only** provider that renders late guidance and validates a **falsifiable**
payload, but never creates a bead itself. Activate it from a project-local
`finalizers` block that a new `sase init finalizers` spec writes into `sase/sase.yml`
for `is_sase_managed: true` repositories only.

Three decisions carry the design:

1. **Put `tasks` in `defaults`, never in `required`.** This is the one place the two
   source reports directly contradict each other, and the Rust code settles it (§3).
2. **Deliver guidance as `selected_instances[].instructions` on the host-side context
   payload** — outside the signed Rust wire, so `sase-core` needs no change.
3. **Verify, don't trust.** The payload names bead IDs; the host resolves them against
   the bead store. A boolean "I considered it" degenerates into a reflex.

**No `sase-core` change is required.** `FinalizerTriggerKindWire::Always` already
exists, and `validate_finalizer_context` rejects only `NotTriggered` + `submission_required`
— so `always` + "must submit" is legal today and simply has no producer.

**Verified saving:** `sase memory list` in this workspace reports 5,944 always-loaded
tokens. `sase/memory/task_types.md` is 925 of the project root's 4,353 (21%) and
`~/sase/memory/task_types.md` is 820 of the home root's 1,591 (**52%**). Combined,
**1,745 tokens — 29% of all Tier 1 context — on every turn, in every project**,
replaced by a <300-token prompt paid only on turns that reach a declaration.

---

## 1. The verified cost baseline

`sase memory list` output, confirmed live:

| File | Lines | Approx. tokens |
| --- | --- | --- |
| `AGENTS.md` (project) | 361 | 4,353 |
| `~/AGENTS.md` (home) | 141 | 1,591 |
| ↳ `sase/memory/task_types.md` | 94 | **925** |
| ↳ `~/sase/memory/task_types.md` | 83 | **820** |

**Read this table correctly.** The 5,944 total is `4,353 + 1,591` — the two `AGENTS.md`
files *only*. The individual notes are listed at their standalone sizes because
`sase memory init` **inlines** them into those roots; they are not additive on top.
Both source reports state the 29% figure correctly, but the arithmetic is worth pinning
down because it is the entire justification for the change.

**Two roots, not one.** The note is generated in two variants by
`src/sase/main/init_memory/root_rendering_task_types.py`:
`render_generated_task_types_memory_body(include_project_memory=True)` renders the
committed project catalog (also backing `sase/task_types.json`), and `False` renders the
machine-global builtin catalog for `~/sase/memory/`. Retiring only the project note
leaves ~820 tokens of staler, duplicated catalog in `~/AGENTS.md` that would then
*contradict* the finalizer in any project that opts out.

**The content splits three ways, and only two parts move:**

| Part | Home after migration |
| --- | --- |
| Per-type `when_to_use`, required/optional fields | finalizer instructions (live catalog) |
| "File discovered work as task beads" nudge + 3 examples | finalizer instructions |
| `/sase_new_task` mechanics: `--size`, `-T task(<slug>)`, `-f` | **already in `/sase_new_task` (147 lines) — do not duplicate** |

That third row is why the finalizer instructions can be *much* shorter than 925 tokens.
The whole duplicate-search / epic-corroboration / sizing procedure already lives in the
skill and loads only on invocation.

---

## 2. What the substrate already provides

Read end to end, `src/sase/finalizers/` already carries almost everything:

- **Config.** `load_finalizer_config()` replays `load_config_layers()` with per-field
  provenance across `defaults` / `required` / `instances`. `plugin:` layers are
  hard-rejected from activating finalizers (`plugin_config_activation`), so only
  default, user, overlay, and **project-local** (`sase/sase.yml`) layers can turn one on.
- **Selection.** `%final:tasks` / `%final:!tasks` / `%final:none` are ordered selector
  ops resolved in Rust. The directive is real and repeatable
  (`_MULTI_VALUE_DIRECTIVES = {"final", "wait"}`).
- **Declaration.** `sase final context` computes requirements/obligations, validates
  through Rust, writes `final_context.json` with a host-computed `manifest_template`.
  `sase final submit` re-reads under flock, rejects a stale `context_digest`, validates
  through Rust, then runs Python per-provider payload validation.
- **Recovery.** `ensure_final_declaration_or_recover()` grants exactly one extra LLM
  turn when a required submission is missing, then fails closed.
- **Triggers.** `build_context_requirements()` is the entire vocabulary today:

| Provider | trigger | submission_required |
| --- | --- | --- |
| `builtin@commit` | `dirty_repository` / `not_triggered` | true iff dirty repos exist |
| `builtin@command` | `always` | **false** |
| anything else | `provider_requested` | **true, unconditionally** |

### 2.1 The Rust core is provider-agnostic

`crates/sase_core/src/finalizer/` validates envelopes, digests, plan ordering, and
requirement coverage — it never interprets a payload body, and every `builtin@commit`
string in the crate sits inside a `#[cfg(test)]` fixture. Payload *shape* validation for
`builtin@commit` (`_validate_commit_payload`) already lives in Python. Putting
`_validate_tasks_payload` beside it is consistent with the `rust_core_backend_boundary`
rule: trigger evaluation, ordering, and digests — the genuinely shared parts — stay in
Rust.

---

## 3. The decisive conflict: `required` vs `defaults`

The two reports give opposite advice. `__a` recommends `required: [tasks]` so
`%final:none` cannot silently restore the old failure mode. `__b` recommends `defaults`
only, so the epic phase-worker xprompt can use `%final:!tasks`.

**`crates/sase_core/src/finalizer/selection.rs` settles it.** A `Remove` selector against
a required instance is not a silent no-op — it is a hard validation error:

```rust
FinalizerSelectorOpWire::Remove { instance_id } => {
    validate_known_instance(instance_id, &instances, "selector")?;
    if required_set.contains(instance_id) {
        return Err(FinalizerError::validation(format!(
            "required instance '{instance_id}' cannot be removed")));
    }
    selected.retain(|value| value != instance_id);
}
FinalizerSelectorOpWire::Clear => {
    if let Some(required_id) = required.first() {
        return Err(FinalizerError::validation(format!(
            "selector clear would remove required instance '{required_id}'")));
    }
    selected.clear();
}
```

So `required: [tasks]` makes `%final:!tasks` **fail at launch**. `__a`'s recommendation
and `__b`'s carve-out are mutually exclusive, and `__a` did not notice that its own
choice forecloses the cleanest available fix.

**Resolution: `defaults: [commit, tasks]`, not `required`.** The payoff is that today's
awkward always-loaded clause —

> Unless your prompt explicitly forbids creating beads (epic phase workers, for
> example, must record `PROPOSED FOLLOW-UP:` notes on their own bead instead)…

— exists *only* because always-loaded text cannot vary per launch. Add `%final:!tasks`
to the `bd/work_phase` xprompt in `default_config.yml` and the clause disappears
entirely. `__a`'s counter-concern about `%final:none` is real but minor: that selector
is explicit user intent, not an accident.

One caveat worth knowing: **`%final` currently appears nowhere in `default_config.yml`**.
This would be the first production selector usage, so there is no precedent to copy and
the xprompt-side wiring deserves its own test.

If you later decide phase workers should still be *prompted* (recording a note rather
than skipping the question), `__a`'s answer is the upgrade path: keep `tasks` selected
and add a host-detected mode whose satisfying action is `proposed_follow_up` (§6). That
is strictly more machinery than a selector, so it does not belong in v1.

---

## 4. The real gaps

**G1 — No agent-facing instruction channel.** `sase final context` emits
`selected_instances[]` (`instance_id`, `provider_ref`, `trigger`, `submission_required`,
`policy`) plus a `manifest_template`. Nothing carries prose. The provider protocol *has*
a `describe` operation, but `_execute_plugin_once` calls it **after** the turn ends, so
its output can never reach the agent. This is the one genuinely missing primitive.

**G2 — No builtin provider is "ask the agent a question, take a typed answer."**
`builtin@commit` demands a payload but is bound to repository obligations;
`builtin@command` runs a subprocess and demands nothing.

**G3 — `finalizers.defaults` is replaced, not merged.** In `config.py::_merge_layer`,
both `defaults` and `required` go through `_string_list(...)` and **overwrite** on every
layer that sets the key; `_string_list` never consults `ConfigLayer.list_strategy`.
Instance fields, by contrast, merge per key. So a project-local
`defaults: [commit, tasks]` silently drops a user-level `defaults: [commit, lint]`.
Writing `instances.tasks` is additive and safe; writing `defaults` is destructive.

*The two reports diverge on the remedy.* `__a` says fix the layering so project-local
lists concatenate; `__b` says work around it by writing the effective merged list.
**Take `__b`'s remedy now and `__a`'s as a separate follow-up.** Changing list semantics
for `defaults`/`required` is a behavior change to every existing config stack and has no
business riding along on a memory migration — but `__a` is right that leaving it is a
standing footgun for every future writer.

**G4 — The requirement digest must not depend on bead state.** The context digest covers
`requirements[].requirement_digest`, and `submit_final_manifest` fails with
`stale_final_context` if the live context moves. Filing a bead is otherwise safe here —
the bead CLI auto-commits its own sidecar (`bead/_sync_git.py`), so no new
dirty-repository obligation appears. But if `builtin@tasks` hashed "beads created so
far", every `/sase_new_task` call between `context` and `submit` would invalidate the
manifest.

*Reconciling the reports:* `__a` wants the guidance digest, catalog digest, and
payload-schema digest bound into `requirement_digest`; `__b` wants it minimal. These are
**not actually in conflict** — every input `__a` names is stable across a single turn.
The rule that satisfies both: **bind turn-stable inputs, exclude turn-mutable state.**
Recommendation for v1: keep it minimal (`{instance_id, trigger}`, exactly like
`builtin@command`), because the guidance is rendered by the same host process from the
same committed snapshot within one turn, so digest-binding it buys no real integrity.

**G5 — Memory has only two types.** `MemoryNoteType = Literal["short", "long"]`
(`memory/notes.py:24`), enforced again in `xprompt/loader_memory.py`, and
`memory-README.template.md:24` documents the pair as exhaustive. There is no type
meaning "generated, versioned, agent-facing, but not Tier 1 and not an audited
`sase memory read` target." That is the type the user plans to add, and it is the seam
this design must leave open.

### 4.1 Two gaps neither report surfaced

**G6 — Handoff turns never declare, and they are the turns richest in discovered work.**
`has_pending_handoff()` exempts `.sase_plan_pending`, `.sase_questions_pending`,
`.sase_monitor_pending`, and `.sase_pipe_pending` from the declaration requirement, in
both `controller_context.py` and `declaration_recovery.py`. So a turn that ends in
`/sase_plan`, `/sase_questions`, `/sase_monitor`, or `/sase_pipe` gets **no tasks prompt
at all**.

This matters more than it sounds. This repo's own build memory *requires* `just check-full`
to be run through `/sase_monitor` — so the canonical "I just discovered a flake" turn is
structurally exempt. Today's always-loaded text covers those turns; the finalizer will
not. The partial mitigation is that the monitor's `--next` follow-up agent *does* reach a
normal declaration with the failure in recent context. Plan turns have no such
backstop. **Measure this**: if task-bead creation drops, handoff turns are the first
place to look.

**G7 — Bead attribution is a join across two naming schemes.** `sase bead list --format
json` returns `created_by` as a fully-qualified `owner.host.shell` string (e.g.
`bbugyi200.athena.sase-cu`), while the finalizer context's `agent_id` comes from
`resolve_local_agent_name()`, which returns the **bare concrete agent shell** — the
identity module's own docstring notes that "the `SASE_AGENT=` footer projects that shell
to its sase agent." Verifying "this run created that bead" therefore needs an explicit
projection, not a string compare. This is concrete evidence for `__b`'s instinct to ship
the identity check as a **non-fatal diagnostic** in v1 rather than a hard failure.

---

## 5. Corrections to the source reports

- **`builtin@tasks` would be the *third* builtin, not the fourth.**
  `BUILTIN_PROVIDER_REFS` is a two-element frozenset (`builtin@commit`,
  `builtin@command`). `__b` says "fourth."
- **`sase init` does not run as a post-commit hook.** `__b` claims existing managed
  projects "self-heal" through one. There is no `src/sase/hooks/` directory and no
  post-commit invocation of any init handler anywhere in the tree. **Existing managed
  projects will need an explicit `sase init` / `sase init --all` run**, which is a real
  rollout step that must be planned, not assumed.
- **`required: [tasks]` forecloses `%final:!tasks`** (§3) — `__a`.
- The 29% token figure in both reports is correct, but the 5,944 denominator is the two
  `AGENTS.md` roots only; the notes are inlined, not summed (§1).

---

## 6. Recommended design

### 6.1 Config written by `sase init`

```yaml
# sase/sase.yml, in a SASE-managed project
finalizers:
  defaults: [commit, tasks]     # written as the *effective* merged list (G3)
  instances:
    tasks:
      use: builtin@tasks
      after: []
      max_attempts: 1
      refusal: fail
```

- Add `builtin@tasks` to `_BUILTIN_PROVIDER_REFS` (`finalizers/config.py`) and to
  `BUILTIN_PROVIDER_REFS` / a `FinalizerProviderRecord` in `finalizers/providers.py`
  with capabilities `("execute", "verify")`. The `use` pattern in
  `config/sase.schema.json` (`^[A-Za-z0-9_.-]+@[a-z][a-z0-9_-]*$`) already admits it.
- Add a `_TASKS_CONFIG_KEYS` allowlist and `parse_tasks_finalizer_config()` mirroring
  `parse_command_finalizer_config()`, so an unknown `config.` key is a `sase final
  doctor` error rather than silence.
- **Compute `defaults`, never assume it** (G3): read effective
  `load_finalizer_config().defaults`, append `tasks` if absent, `set_key` the result.
  Idempotent — no write when already present.

**Ownership: a new `InitCommandSpec(name="finalizers")`, not the memory initializer.**
`__a` argues for folding this into `init_memory` for atomicity; `__b` argues for a
separate spec. `__b` is right, and the registry makes it cheap:
`iter_init_command_specs()` is an ordered 4-tuple (`config`, `memory`, `repo`, `skills`)
with a uniform `plan`/`run` contract, and `sase init --check` / `--diff` come free.
Order it **after `memory`**. `__a`'s atomicity concern is satisfied anyway, because a
single `sase init` invocation runs every spec — atomicity lives at the command level,
not the spec level. Keeping activation separate from memory generation also stops the
future memory-type work from tangling with finalizer config.

Gate on the **raw local** `is_sase_managed: true` (the `_linked_repo_config.py:304` /
`repo_init_handler` precedent), not the merged config, so a machine-level or copied
config block cannot fake managed status.

### 6.2 Host trigger

Add a branch to `build_context_requirements()` before the generic fallback:

```python
if entry.provider_ref == "builtin@tasks":
    active = project_is_sase_managed(...) and bead_store_available(...)
    trigger = "always" if active else "not_triggered"
    requirements.append(FinalizerPayloadRequirementWire(
        instance_id=entry.instance_id,
        trigger=trigger,
        submission_required=active,
        requirement_digest=finalizer_json_digest(
            {"instance_id": entry.instance_id, "trigger": trigger}),
    ))
    continue
```

`project_is_sase_managed` already exists in `sase/feature_flags/managed.py`. This
trigger gate is **defense in depth on top of** the init-written config: a stray
user-level instance in an unrelated repo degrades to `not_triggered` instead of
demanding a declaration. Digest deliberately omits bead state (G4).

### 6.3 Agent-facing instructions (G1)

Add `instructions: str` to each `selected_instances` entry in
`declaration.py::_context_payload()`. This is host JSON **outside** the signed
`FinalizerContextWire`, so `#[serde(deny_unknown_fields)]` is not implicated and no Rust
change or digest churn follows. Render it in `format_context_pretty()` too.

Populate by `provider_ref`: `builtin@tasks` → the block below; `builtin@commit` → the
repository decision rules currently duplicated in the `/sase_final` skill (a free
cleanup); `builtin@command` and external providers → empty. That empty external slot is
where a cached, pre-submit `describe` can land later — the right long-term answer for
plugin providers, but wrong as a first step (a subprocess per instance per context
publication, and the controller republishes context every cycle).

Source the body from a packaged template (`templates/finalizer-tasks.template.md`) with
one substitution, reusing `_render_task_type_note_entries()` /
`format_agent_creatable_type_listing()` so the catalog can never drift from
`sase bead task-type list`. Target well under 300 tokens:

> Before you finish: did this turn surface work that belongs on its own task bead?
> Agent-creatable types here: `bug` — a defect found while doing unrelated work ·
> `ci` — a confirmed failure · `feature` — an out-of-scope idea · `flake` — fails then
> passes on an unchanged tree · `memory` — an out-of-date sase note or skill.
> File one for: a lint/test failure you did not cause; an out-of-date sase memory note
> or skill; a bug or clear objective improvement in a tool this project owns.
> If yes, use `/sase_new_task` **now**, then declare the resulting bead IDs.
> If no, declare `none` with a one-line reason.

Everything about `--size`, `-T task(<slug>)`, `-f`, duplicate search, and epic
corroboration stays in `/sase_new_task`.

### 6.4 Payload and verification

The two reports propose different shapes. `__b`'s single `decision` enum cannot express
"I filed one bead *and* corroborated another," which is a real turn. `__a`'s `outcomes[]`
list can. **Take `__a`'s shape with `__b`'s verification:**

```json
{"outcomes": [{"kind": "created", "ref": "sase-a1"},
              {"kind": "corroborated", "ref": "sase-b2"}],
 "no_task_reason": null}
```

- Kinds: `created`, `corroborated` (and `proposed_follow_up` only if you later adopt the
  phase-worker mode from §3 instead of `%final:!tasks`).
- Empty `outcomes` **requires** a nonblank `no_task_reason`; a nonempty list forbids it.
- `_validate_tasks_payload()` sits beside `_validate_commit_payload()`: reject unknown
  keys and kinds, malformed or duplicate refs, and reuse the existing 4,000-byte cap on
  the reason.

Then — and this is what makes the declaration worth its tokens — `execute`/`verify`
resolves each ref against the bead store and confirms it is a **task** bead. A fabricated
or unrelated ID fails the instance. `sase bead list --format json` exposes `id`,
`issue_type`, `created_at`, `created_by`, and `plus_one_count`, and the context carries
`run_id` (`SASE_AGENT_TIMESTAMP`) and `agent_id`.

**Ship the existence/type check as fatal and the identity check as a non-fatal
diagnostic in v1** (G7): `created_by` and `agent_id` use different naming schemes, so
the join needs proving before it can fail otherwise-good turns.

**The executor must be non-mutating.** All bead creation and corroboration remain agent
actions through `/sase_new_task`. This also means ordering relative to `commit` is
semantically unimportant in v1: payload validation happens before any executor runs.

**Open question worth deciding deliberately** (`__b` raises it, and it is the right call
to leave open): should `outcomes: []` require a reason at all? Requiring one risks
boilerplate ("no follow-up work discovered") on most turns. Require it initially, and
drop the requirement if the reasons prove uniformly vacuous.

### 6.5 `/sase_final` skill changes

- Read `instructions` on each selected instance and satisfy it before building the
  manifest.
- **Refresh rule:** any repository mutation made while satisfying an instruction requires
  rerunning `sase final context -f json` before submitting. For `tasks` specifically the
  bead CLI commits its own sidecar, so this should be a no-op — but the rule must be
  stated, because the first context is what *discloses* the guidance and reusing its
  manifest after a mutation would be correctly rejected as stale.

---

## 7. The memory-type seam

Do not embed the prose in Rust, in the provider registry, or permanently in the generic
`/sase_final` skill. Both reports converge here, and the shape is the same: read the
guidance body through a **resolvable source** from day one rather than a Python string
literal, so the future memory type becomes a config key plus a loader instead of a
rewrite.

```python
class FinalizerGuidanceSource(Protocol):
    def render(self, instance_id: str, context: GuidanceContext) -> Guidance: ...
```

v1 source: packaged template + `sase/task_types.json`. When the new memory type lands:

```yaml
    tasks:
      use: builtin@tasks
      config:
        memory: task_types.md      # note of the new, non-Tier-1 type
```

`builtin@tasks` then prefers that note's body over the packaged template. This
generalizes cleanly — a later `builtin@note` provider is the same mechanism minus the
bead verification. Update `memory-README.template.md`'s frontmatter-schema section in
whichever change introduces the type; it currently documents `short`/`long` as
exhaustive. Do **not** try to guess the type's name or frontmatter now; the interface is
the deliverable, not the prediction.

---

## 8. Retiring the note safely

Keep `sase/task_types.json` and its validation exactly as they are — the committed
snapshot is what makes late guidance deterministic (it spans builtins, project-local
types, and `plugins.required`, while excluding whatever optional plugins happen to be
installed on one machine). Only the *rendering* moves.

Remove the note from `generated_memory_note_relative_paths()`, `generated_short_notes()`,
and `render_expected_memory_files()` at **both** roots, and update
`memory-sase-beads.template.md` so its long note points at
`sase bead task-type list/show` rather than promising a generated short note.

**The old note has no generated-file marker, so do not blindly unlink the path.** Use
`__a`'s one-release retirement rule, which is the more careful of the two proposals:

1. delete automatically when frontmatter and body **exactly match** a known packaged
   render;
2. if the path exists with different content, **block with an actionable message** rather
   than deleting possible user edits;
3. exclude a retired exact match from AMD/instruction discovery in the same planning
   pass, so `AGENTS.md`, the provider shims, and the memory README converge immediately.

Retain the legacy render digest only as long as migration needs it, then delete that
compatibility code.

### 8.1 This step needs a feature flag

Neither source report worked the flag question, and this repo's own rule is explicit:
user-reaching behavior gets a flag before it is ready. `__b` waves it off on the grounds
that the pluggable-finalizer beta already retired — true, but that flag covered the
*substrate*, not this behavior change.

The precise reading of `sase/memory/sase_flags.md` is: *"If users are meant to choose the
value forever, it was never a feature flag."* The per-project `finalizers.instances.tasks`
config **is** the permanent choice, so the **provider needs no flag** — hand-configuring
it in this repo and soaking is already opt-in.

**The retirement does need one.** Removing `~/sase/memory/task_types.md` is
machine-global and therefore *not* covered by the per-project config gate: it strips
guidance from agents in projects that never opted in. That is exactly "behavior that
reaches users before it is ready."

Create it with `sase flag new` (never by hand), kind **`beta`** (default off):
On = note retired, Off = note still generated. At removal the Off branch is deleted and
retirement becomes unconditional — which is precisely the desired end state.

---

## 9. Phasing

1. **Substrate.** `instructions` on the context payload + pretty renderer + tests. No
   behavior change; every existing provider renders empty.
2. **Provider.** `builtin@tasks` registration, trigger branch, manifest template, payload
   validation, execute/verify. Hand-configure `sase/sase.yml` in this repo and soak for
   several days of real turns.
3. **Init.** The `finalizers` spec with effective-defaults merging, `--check`/`--diff`,
   and the raw-local managed gate. **Plan the explicit `sase init --all` rollout** —
   nothing self-heals (§5).
4. **Selector.** `%final:!tasks` on the `bd/work_phase` xprompt; drop the carve-out
   sentence.
5. **Memory retirement,** behind the beta flag: both roots, the retirement path in
   `sase memory init`, regenerate `AGENTS.md` and every provider shim, and measure the
   Tier 1 delta with `sase memory list`.
6. **Memory type** (separate work): new frontmatter type + `config.memory` on the
   instance.

Steps 1–4 are independently landable and reversible. Step 5 is the one that changes what
agents see — it follows the soak, it does not precede it.

---

## 10. Risks

- **Every turn now requires a declaration.** Today a clean, commit-free turn submits
  nothing; with `trigger: always`, every non-handoff turn does. A forgotten `/sase_final`
  costs a full recovery turn. Watch
  `sase_finalizer_recoveries_total{kind="declaration"}` after step 2 — a spike means the
  Tier 1 `/sase_final` instruction is not landing reliably enough to make `always` safe.
- **An end-of-turn nudge is a weaker nudge.** Always-loaded text primes an agent to
  *notice* a flake as it happens; a terminal prompt asks it to *recall* one. This is the
  core trade, and it is probably the right one — most task beads originate from
  `just check` failures and `sase memory read`, both of which are recent context at
  declaration time. Measure task-bead creation per 100 turns across the change.
- **Handoff turns are uncovered (G6)** — and include the monitored `just check-full` run
  and every `/sase_plan` turn. This is the sharpest edge of the previous risk.
- **`defaults` replacement (G3)** remains a latent footgun for every future config
  writer, independent of this change.
- **Home-root behavior change.** After step 5, `~/AGENTS.md` carries no task-type
  guidance. Agents in managed projects get it from the finalizer; agents doing ad-hoc
  work outside one get nothing. Correct (no bead store), but a real change.
- **Boundary.** `_validate_tasks_payload` in Python follows the `_validate_commit_payload`
  precedent, but a web or editor frontend wanting to pre-validate a declaration would
  need it in `sase-core`. Acceptable now; revisit if a second frontend appears.

---

## 11. Test matrix

**Selection and config**
- `required: [tasks]` + `%final:!tasks` → launch-time validation error (the §3 guard, so
  a future refactor cannot silently reintroduce it).
- `%final:!tasks` removes the instance when `tasks` is in `defaults` only.
- Project-local `defaults` written as the effective merged list: no `finalizers` block →
  `[commit, tasks]`; user-level `[commit, lint]` → `[commit, lint, tasks]`; second run is
  a no-op.
- `sase final doctor` flags an unknown `builtin@tasks` `config.` key.

**Trigger and digest**
- Not SASE-managed → `not_triggered`, `submission_required: false`, Rust context
  validation still passes.
- Managed → `always` + `submission_required: true`; context digest stable across two
  publications with no intervening change.
- **Filing a bead between `context` and `submit` does not produce `stale_final_context`**
  (the G4 regression guard).

**Payload and verify**
- Mixed `created` + `corroborated` outcomes accepted; unknown keys/kinds, duplicate refs,
  empty `outcomes` without a reason, and both a reason and outcomes together each
  rejected with distinct codes.
- Fabricated bead ID fails the instance; a non-task bead ID fails; a `+1` on an existing
  bead satisfies `corroborated`; an agent-identity mismatch emits a diagnostic, not a
  failure (G7).
- The executor mutates no bead or repository state.
- Declaration recovery still succeeds when only the `tasks` payload is missing.
- **A turn with a pending handoff marker requires no tasks declaration** (G6 — pin the
  known gap so it is a decision, not a surprise).

**Init and memory**
- `sase init --check` reports the missing finalizer config on a managed project;
  `--diff` renders the edit; apply is comment-preserving and idempotent; unmanaged
  projects and non-project contexts are untouched; `sase init --all` reconciles every
  enabled managed project.
- Retirement removes the exact generated note at **both** roots; a modified note blocks
  rather than being deleted; `sase/task_types.json` still generates and validates; no
  generated provider shim retains the section; the memory README no longer inventories
  the note.
- Flag off → note still generated; flag on → retired (both-states coverage is mandatory
  for every flag).

---

## 12. Recommended solution

Add **`builtin@tasks`**, a third builtin, **declaration-only** finalizer provider,
selected through `finalizers.defaults` — **not `required`** — in a project-local
`sase/sase.yml` block that a new `sase init finalizers` spec writes for
`is_sase_managed: true` repositories only, with a host-side trigger gate as defense in
depth.

Deliver its guidance through a new generic `selected_instances[].instructions` field on
the host context payload (outside the Rust wire, so `sase-core` is untouched), rendered
from the committed `sase/task_types.json` catalog through a small
`FinalizerGuidanceSource` interface — the seam the upcoming memory-file type slots into
without redesigning config, declarations, or execution.

Require a **falsifiable** payload: an outcomes list naming real bead IDs that the host
resolves against the bead store, or an explicit empty list with a one-line reason. The
agent takes every judgment-bearing action through `/sase_new_task` during the turn; the
provider validates and verifies but never mutates.

Then add `%final:!tasks` to the epic phase-worker xprompt — deleting the carve-out clause
that only ever existed because always-loaded text cannot vary per launch — and retire the
generated note at **both** memory roots behind a `beta` flag, using exact-match deletion
with a hard block on modified content.

Net: **1,745 tokens — 29% of Tier 1 — leave every turn in every project**, replaced by a
sub-300-token prompt paid only where it is actionable. Write the project-local `defaults`
as the effective merged list to avoid the layering footgun, plan the explicit
`sase init --all` rollout because nothing self-heals, and measure both
`sase_finalizer_recoveries_total` and task-bead creation per 100 turns — with particular
attention to whether handoff turns, which never declare, start losing discovered work.

---

## Sources

Primary evidence: `src/sase/finalizers/{config,providers,declaration,declaration_store,declaration_recovery,selection}.py`,
`src/sase/main/{init_registry,init_memory_handler,repo_init_handler}.py`,
`src/sase/main/init_memory/root_rendering_task_types.py`,
`src/sase/main/init_memory/templates/{memory-README,memory-sase-task-types,memory-sase-beads}.template.md`,
`src/sase/memory/notes.py`, `src/sase/agent/{identity,pending_handoff}.py`,
`src/sase/xprompt/_directive_{collect,types}.py`, `src/sase/default_config.yml`, and
`sase-core/crates/sase_core/src/finalizer/{wire,selection,submission}.rs`.

Live measurements: `sase memory list`, `sase bead list --format json`, `sase flag list`.
Audited memory read: `sase/memory/sase_flags.md`.

Prior art (consumed by the source reports through audited artifact reads):
`202608/finalizer_protocol_and_extensibility/`, `202608/finalizer_completion_contracts/`,
`202608/finalizer_integrity_and_capabilities/`, `202608/task_bead_type_registry/`.
