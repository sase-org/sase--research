# Robust file-hook matching for research artifact files

## Executive conclusion

The current `research-highlights` hook works, but it identifies the files *not* to
process through two negative heuristics: filename shape and producer agent name. Those
heuristics are demonstrably maintenance-prone. Adding Grok, Muse, and Gemini researchers
recently required extending both the suffix and agent-name exclusions, and the path
rules separately encode the current one- and two-directory swarm layouts.

The proposed positive marker is directionally right: a canonical report should say
"this file is eligible for research-report hooks" instead of making the hook infer that
fact from names. I would not, however, make arbitrary process environment part of the
file-hook matching contract. Environment is scoped to an agent run rather than one
file, disappears across process/retry boundaries unless it is copied elsewhere, and
would make finalizer reconciliation depend on hidden ambient state.

My recommended solution is a first-class, durable **file-hook intent tag** attached to
the exact `sase artifact create` registration. Concretely:

1. Add a repeatable `sase artifact create --file-hook-tag <slug>` option.
2. Persist the tag with the current agent run, bound to the artifact id, canonical
   source repository/path, and content digest.
3. Enrich commit/finalizer file events from those persisted intents and add a
   `filters.file_hook_tags` selector.
4. Make `#research` add `--file-hook-tag research-final` by default, controlled by a
   boolean input such as `file_hooks=true`.
5. Have every independent `#research_swarm` researcher invoke
   `#research(..., file_hooks=false)`, while the lead always registers the consolidated
   report with `research-final`.
6. Change `research-highlights` to match the positive tag, retaining only defensive
   sidecar, operation, producer, and broad Markdown-location constraints. Remove the
   researcher-name and `__<suffix>` exclusions.

This preserves the useful part of the environment-variable idea—an ergonomic default
with an explicit swarm override—but makes the durable file registration, not ambient
process state, authoritative.

## What exists today

### Research xprompts

`sase-research-artifacts/src/sase_research_artifacts/xprompts/research.md` is a Markdown
prompt-part. It accepts `report_target` and `suffix`, tells the agent where to write the
report, and requires this registration after the write:

```text
sase artifact create -p "<absolute-report-path>" \
  -l "research:<repo-relative-report-path>"
```

The label is already a structured-looking, exact identity for the report, and the
registration occurs after the final path and bytes are known. This is the strongest
available point at which to attach file-specific intent.

The independent segments in
`sase-research-artifacts/src/sase_research_artifacts/xprompts/research_swarm.md` all call
`#research(suffix=<provider>)`. The lead does **not** call `#research`; it has bespoke
consolidation instructions. It only explicitly registers its report today when a
critique agent is enabled. Therefore, setting an environment variable in `#research`
alone would mark standalone reports and researcher drafts, but would not mark the
normal consolidated report that the Highlights hook is meant to process.

Markdown xprompts also do not declare workflow `environment:`. That field belongs to
YAML workflows. Implementing the environment proposal literally would require changing
`research.md` into a YAML workflow with a `prompt_part` step (and updating wheel resource
contracts), or adding a new xprompt capability. The conversion is feasible, but it is
avoidable if the boolean input simply renders a CLI flag into the existing registration
command.

### File-hook events and matching

The current SASE file-hook event carries:

- project and repository/sidecar identity;
- repository-relative path and operation;
- cause and producer; and
- producing agent name.

See `sase/src/sase/config/file_hooks.py` (`FileHookEvent`, `FileHookFilters`, and
`hook_matches_event`) and `sase/src/sase/file_hooks/models.py` (`CapturedFileEvent`).
There is no environment, artifact id, artifact label, or file-specific semantic tag.
All filter dimensions are ANDed.

Artifact creation already captures the original repository-relative path before a
possible move, stores the explicit snapshot, and emits an artifact file-hook event.
The event matches on the original logical path but runs the command against the durable
stored copy (`sase/src/sase/file_hooks/artifact.py` and
`sase/src/sase/artifact_cli/create.py`). Commit and finalizer producers instead derive
events from the committed revision and run against repository paths
(`sase/src/sase/file_hooks/commit.py`).

### Why the current research hook is brittle

The plugin's `RESEARCH_HIGHLIGHTS_HOOK_SPEC` currently requires all of the following:

- sidecar `research`;
- producer in `commit`, `sdd`, or `finalizer`;
- operation `ADD`;
- a dated Markdown path;
- no `__<suffix>` filename at either of two known depths;
- no generated companion suffix; and
- an agent name not ending in any of `cdx`, `cld`, `grk`, `mus`, or `gem` under the
  current research clan naming scheme.

This is negative classification: an unrecognized future researcher suffix, a new
directory layout, or an unattributed commit can become eligible by accident. The core
matcher intentionally lets an unattributed event through a negative-only agent-name
list. Agent identity is also run-level, not file-level; a lead commit can add/move both
drafts and the final report, forcing the path rules to compensate.

Repository history supplies a concrete maintenance signal. Plugin commit `f524532`
had to add the `grk`/`mus`/`gem` exclusions and the root-level draft exclusion after the
swarm expanded. That is exactly the class of change a positive semantic selector should
eliminate.

### Why the hook excludes the artifact producer

This exclusion is intentional, not incidental. Explicit artifact bytes are stored at a
content-addressed name such as `report-<digest>.md`. File-hook matching sees the original
repo-relative path, but the command receives that digest-suffixed stored path. The
active command is:

```text
bob highlights create --include-id <markdown-file>
```

`bob highlights create` derives its default output filename and the `--include-id`
marker from the Markdown input stem. Running it on the durable stored copy would
therefore create a digest-bearing PDF/id. SASE's configuration documentation explicitly
recommends restricting basename-sensitive hooks to committed-file producers for this
reason. A better selector alone does not remove this constraint.

## Critique of the environment-variable plan

### What is good about it

- It changes the decision from “does this path/agent look like a final report?” to a
  positive declaration of intent.
- A default-on setting with an explicit false override fits standalone `#research` and
  swarm researchers well.
- The xprompt is the right product-level place to define the default because it knows
  whether the user requested a canonical research report.
- Separate swarm processes mean a researcher override would not contaminate the lead's
  environment merely because they belong to one swarm.

### What needs correction

1. **An environment variable describes a process, not a file.** If an agent writes
   several research-sidecar Markdown files, all commit events would inherit the same
   marker unless another mechanism binds the marker to one path.
2. **Ambient state is poor retry evidence.** Finalizer reconciliation deliberately
   re-derives commit events. A reliable retry should read persisted facts, not depend on
   whether the original xprompt-mutated environment survived into a later process.
3. **Arbitrary environment filtering would be unsafe and hard to audit.** Capturing a
   general environment mapping risks secrets, large batches, and inconsistent behavior.
   A single validated tag namespace is safer, but once that tag must be persisted, the
   registration is the natural authority.
4. **The lead is a gap.** The lead does not invoke `#research`, and today it does not
   always call `sase artifact create`. The proposal would not select the consolidated
   report without additional changes.
5. **The stored-copy filename problem remains.** Enabling the artifact producer with
   only an environment filter would cause incorrect Highlights filenames/ids.
6. **A Markdown-to-YAML migration is needless complexity.** The existing Markdown
   template can conditionally render a CLI option without changing xprompt type or
   introducing environment overwrite/unset semantics.
7. **The override name should express behavior, not transport.** An input named
   `set_environment=false` would expose an implementation detail. Prefer `file_hooks`,
   `run_file_hooks`, or `canonical_report`.

I would only use an environment variable as optional CLI sugar—for example, a
well-defined `SASE_ARTIFACT_FILE_HOOK_TAGS` default consumed by `sase artifact create`—
not as a filter that reads arbitrary process environment. I would not add that sugar in
the first implementation because the rendered CLI flag is clearer and fully scoped.

## Recommended design

### 1. Add an explicit hook-intent tag at registration

Proposed CLI:

```text
sase artifact create \
  -p <path> \
  -l research:<repo-relative-path> \
  --file-hook-tag research-final
```

`--file-hook-tag` should be repeatable and accept only a bounded lowercase slug syntax.
It names a semantic class, not a configured hook. The agent may say “research-final”;
the user's hook configuration remains responsible for deciding what command, if any,
that class activates. This avoids coupling the plugin to a local hook name such as
`research-highlights`.

Persist one idempotent intent record per `(artifact id, tag)` containing at least:

- artifact id and label;
- current agent-artifacts identity;
- canonical repository root and repo-relative source path;
- source SHA-256 at registration time; and
- normalized file-hook tags.

An append-only/atomically rewritten marker under the agent's own artifacts directory
would keep this operational metadata local to the run and avoid immediately changing
the global artifact-file index schema. If hook tags are later promoted onto
`ArtifactFile`, that requires coordinated SASE/sase-core wire and schema work because
Rust currently reads and filters the global artifact-file index. Explicit artifact
storage itself is documented as Python-owned, so a run-local intent marker is a
reasonable first boundary.

If recording an explicitly requested tag fails, `sase artifact create` should return a
visible nonzero/partial error even if the immutable snapshot copy succeeded. Hook
*execution* remains non-gating; failure to record the requested selection fact is
different from a hook command failing later.

### 2. Enrich file events from persisted intent, not environment

Add `file_hook_tags` to `CapturedFileEvent`/`FileHookEvent` and to audit/batch payloads.
Commit, SDD, and finalizer producers should receive the current agent-artifacts path
explicitly, load only that run's intent records, and attach tags only when all of these
match:

- canonical repository root;
- repository-relative path; and
- content digest of the committed file.

The digest check proves that the registration followed the final write and prevents a
stale registration from selecting later edits at the same path. For an `ADD`-only hook
this is straightforward. Removal events cannot prove current content and should not
inherit tags by default.

Do not search the global artifact index by source path alone: an older agent may have
registered the same absolute workspace path, creating a stale false positive. Scope to
the current run first.

The finalizer already has the active artifacts directory when it reconciles commit
markers; thread that value into file-hook reconciliation instead of rediscovering
ambient state. This keeps the first dispatch and retry deterministic. Because the
commit batch id hashes the event payload, tag-enriched commit and finalizer events will
continue to converge on one batch when they re-derive the same facts.

### 3. Add a tag filter

Extend config with:

```yaml
filters:
  file_hook_tags: [research-final]
```

Use the existing positive-OR/negative-veto glob semantics if tags support patterns;
otherwise exact membership is preferable for a first release. All existing dimensions
remain ANDed. Unknown fields must continue to fail visibly rather than silently widen a
hook.

The research provider can then become approximately:

```yaml
filters:
  sidecars: [research]
  producers: [commit, sdd, finalizer]
  path_globs: ["20*/**/*.md"]
  file_hook_tags: [research-final]
  ops: [ADD]
```

The broad path check is useful defense in depth and documents the expected repository
area. The `__<suffix>` and agent-name exclusions should be removed; companion exclusions
are redundant if companions are never tagged, though retaining them for one transition
release is harmless.

### 4. Change the xprompts

Add this input to `#research`:

```yaml
- name: file_hooks
  type: bool
  default: true
  description: Mark the registered report as eligible for canonical research file hooks.
```

Conditionally render `--file-hook-tag research-final` on the existing `sase artifact
create` command. No environment is necessary and `research.md` can remain a Markdown
xprompt.

Every independent swarm segment should pass `file_hooks=false`, including future
provider segments. The existing segments would become, for example:

```text
#research(suffix=cdx, file_hooks=false)
```

The lead should unconditionally register the consolidated report once, with
`--file-hook-tag research-final`, after writing it. If critique is enabled, the critique
agent can consume that same snapshot; there should not be a second registration path.
The critique report should register without the tag unless product intent changes.

This is a justified requirement adjustment: **the lead's explicit registration must no
longer be conditional on critique**. Besides making file hooks reliable, it makes every
consolidated report available as the same kind of durable snapshot as the independent
inputs.

### 5. Preserve committed-path execution for Highlights

Keep `research-highlights` on `commit`/`sdd`/`finalizer` for now. The command then
receives the canonical report path and `bob highlights --include-id` derives the desired
stem. The artifact producer may still carry and match tags for other hooks whose output
does not depend on the basename.

A later generic improvement could give hook commands structured metadata such as
`SASE_FILE_HOOK_REL_PATH`, artifact id/label, and original basename, or support command
templates. With that in place—and with a way for Bob to use a logical id independent of
the physical stored filename—the research hook could safely run from the durable
artifact producer. That is valuable but not required to replace today's brittle
matching.

## Alternatives considered

### Match arbitrary environment values

This is the original direction. It is simple at first but creates hidden, run-scoped
state and requires environment capture/persistence to make retries reliable. It also
invites secret-handling questions. Reject as the primary contract.

### Add only `SASE_FILE_HOOK_TAGS`

A single controlled tag variable is much safer than arbitrary environment matching.
If captured into every event it still marks every file in the run, however. It can be a
future default source for `sase artifact create`, but should not replace file-specific
registration intent.

### Match artifact labels

Artifact labels are already available after registration and `research:<path>` is
useful evidence. Matching `research:*` still cannot distinguish canonical reports from
swarm drafts without returning to suffix/path heuristics. Overloading the display label
with `research-final:` also disturbs the lead's current `wait.artifacts` contract.
Keep labels for identity/display and use a separate operational tag.

### Parse report frontmatter

The research provider already exposes typed frontmatter such as `status`. Requiring
`status: final` could be semantically appealing, but agents do not consistently author
frontmatter today, file-hook matching would need content parsing, and removal events
have no content. Frontmatter can complement the report model later; it is not a reliable
trigger by itself.

### Keep improving filename and agent-name exclusions

This has the smallest implementation cost but scales linearly with new researchers and
layouts and fails open for unknown cases. It is suitable only as a compatibility
fallback during rollout.

### Run directly on the artifact producer

This provides durable bytes and immediate execution, but the current digest-suffixed
stored filename changes Bob's output and embedded id. It becomes attractive only after
hook execution can preserve or explicitly supply the logical filename.

## Compatibility and rollout

1. Land the SASE tag/intention primitive, config schema, docs, CLI option, audit fields,
   and deterministic reconciliation first.
2. Release SASE, then raise the `sase-research-artifacts` minimum SASE version to that
   release; plugin provider specs must not contain a filter older hosts silently cannot
   honor.
3. Update `#research`, every researcher segment, the lead's unconditional registration,
   provider spec, plugin docs, and package/wheel contracts.
4. During one transition release, the provider may retain the old path/agent exclusions
   in addition to the positive tag, but the positive tag must be required. Remove the
   duplicated negatives after deployed hosts and plugin versions converge.
5. Observe `sase file-hook history` for tagged matches and expected untagged misses.

The artifact-file index is currently read through a Rust-backed query facade. If tags
are stored on the global `ArtifactFile` row rather than in a run-local intent marker,
coordinate the Rust `ArtifactFileWire`, schema-version constants, Python mirrors,
bindings/tests, and SASE's `sase-core-revision.txt` pin. Do not add a Python-only
fallback for a changed Rust wire.

## Required tests

- CLI validation: repeated valid tags, malformed/oversized tags, and no behavior change
  when the option is absent.
- Intent persistence: exact agent run, repo root, relpath, artifact id, and digest;
  idempotent retry; visible failure when persistence fails.
- Matching: positive tag match, missing tag miss, tag ANDed with sidecar/path/op/producer,
  and no arbitrary environment captured in audits.
- Provenance: same path from an older run does not match; digest mismatch after a
  post-registration edit does not match; unrelated files in the same commit do not
  inherit the tag.
- Reconciliation: commit and finalizer derive identical enriched events and reuse one
  deterministic batch.
- Artifact producer: tag is available, but `research-highlights` still excludes that
  producer and receives the canonical repo path through the commit route.
- Xprompt: `#research` defaults to the tag; `file_hooks=false` omits it; all independent
  researcher segments pass false; the lead registers exactly once with the tag; critique
  and image outputs do not inherit it.
- Plugin provider: an unknown new researcher suffix remains uninteresting without any
  provider/agent/path exclusion update, proving the main maintenance benefit.
- Packaging: wheel and sdist contain the unchanged/updated xprompt resource names and
  the released host minimum supports `filters.file_hook_tags`.

## Final recommendation

Adopt the positive-marking idea, but move the authority from environment to the exact
artifact registration. Implement a validated `--file-hook-tag research-final`, persist
it as a digest-bound per-run hook intent, enrich commit/finalizer events from that
durable record, and match it with `filters.file_hook_tags`. Let `#research` expose a
default-true behavioral input that conditionally renders the tag; pass false for every
independent swarm researcher; and always register/tag the lead's consolidated report.

This solution directly identifies the intended file, survives reconciliation, avoids
capturing environment, removes the expanding researcher-name/suffix denylist, and keeps
the existing canonical-path execution that `bob highlights --include-id` requires.
