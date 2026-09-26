---
create_time: 2026-09-26
updated_time: 2026-09-26
status: draft
tags:
  - file-hooks
  - artifacts
  - xprompts
  - research-swarm
  - sase-research-artifacts
---

# Matching research artifact files for file hooks

## Question

How should SASE match *artifact files* (the durable snapshots created by
`sase artifact create`) so file hooks can run on the right research reports,
without firing on `#research_swarm` drafts? The working idea is:

1. `#research` sets an environment variable by default.
2. A new `#research` input turns that variable off.
3. `#research_swarm` uses that override on every researcher that runs before
   the lead.

This report evaluates that plan against the current matching machinery, names
the gaps, adjusts the requirements, and recommends an implementation.

## Verdict

The *policy* is right: the producing xprompt should declare hook intent, default
on for a normal `#research` write, and off for swarm researchers. An environment
variable is a reasonable way to *carry* that intent into `sase artifact create`.

The *mechanism* as stated is not enough, and it aims at the wrong bottleneck.

File-hook matching already has original repo-relative paths, sidecar role, agent
name, op, cause, and producer. Swarm drafts already miss `research-highlights`
on those dimensions. What actually blocks artifact-time hooks is the **command
argument**: artifact dispatch appends the content-addressed stored copy
(`<stem>-<12-hex>.md`), and Bob Highlights derives the PDF basename and marker
id from that basename. That is why the installed hook's `producers` list is
`[commit, sdd, finalizer]` and why an installed-provider regression test expects
`sase artifact create` to record `no_match`.

Setting `$SOME_VAR` in the agent process does not change that path. Matching
also has no environment-variable filter today, markdown `#research` cannot set
workflow `environment:`, and the lead segment does not call `#research` at all.

**Do this instead:** capture hook intent as event metadata (with the env var as
the producer-side default), pass the original source path into the hook command
for artifact events, then add `artifact` to `research-highlights` producers with
dedup against the later commit. Keep the `__<suffix>` path veto as a safety net.

## Current system

### `#research` is a markdown xprompt that registers a snapshot

`sase-research-artifacts` ships `#research` as
`src/sase_research_artifacts/xprompts/research.md`. It has two optional inputs:

| Input           | Type | Role                                                                 |
| --------------- | ---- | -------------------------------------------------------------------- |
| `report_target` | path | Exact month-relative path; wins when both are set                    |
| `suffix`        | word | Require `<stem>__<suffix>.md` when `report_target` is unset          |

After a successful write it registers:

```text
sase artifact create -p "<absolute-report-path>" -l "research:<repo-relative-report-path>"
```

`--move` is forbidden, so the research-sidecar file stays in place and the
artifact store holds a copy. That registration is the producer contract
`#research_swarm`'s lead consumes through `wait.artifacts` (see
`plan:202609/wait_artifacts.md`). The label is the canonical portable identity
(`research:202609/topic__grk.md`), not a display string.

`#research/prompt` ends with `#research` and would inherit whatever default
`#research` grows. `#research/more` extends an existing file and does **not**
register a snapshot.

### Markdown xprompts cannot set environment variables

YAML workflows may declare:

```yaml
environment:
  SASE_COMMIT_METHOD: create_commit
```

Values are Jinja-rendered against inputs and written into `os.environ` before
steps run, including when the workflow is embedded in another prompt
(`workflow_executor_steps_embedded_expand.py`). `#commit` / `#propose` / `#pr`
use this today.

`#research` is a `.md` file. `xprompt_to_workflow()` wraps the body as a single
`prompt_part` step and **does not copy an `environment` mapping**. Markdown
frontmatter schema has no `environment` field. Plugin `sase_xprompts` discovery
already loads `xprompts/*.yml`, so converting `#research` to YAML is the
supported way to inject env, not a new frontmatter feature.

Injection always *sets* the key (`os.environ[key] = rendered`). A false
override that renders to `""` still leaves the variable present unless capture
treats empty as absent.

### `#research_swarm` researchers register; the lead usually does not

Each researcher segment ends with `#research(suffix=<short>)` (`cdx`, `cld`,
`grk`, `mus`, `gem`). Those agents therefore create both a sidecar markdown
file *and* an explicit artifact whose label carries `__<short>.md`.

The lead (`research.<N>.final`):

- waits on every surviving researcher
- reads `wait.artifacts` (markdown rows whose label starts with `research:`)
- moves drafts to `<name>/<name>__<short>.md`
- writes `<name>/<name>.md`
- registers that consolidated file **only when `critique=true`**

The lead never calls `#research`. A default-on env var on `#research` therefore
never reaches the consolidated report unless the lead segment sets it some
other way.

The critique agent writes `<name>__critique.md` and registers it. That filename
is already excluded by the Highlights path vetoes.

### `research-highlights` matching is path + agent + producer

The plugin template (`RESEARCH_HIGHLIGHTS_HOOK_SPEC`) is:

```yaml
filters:
  sidecars: [research]
  producers: [commit, sdd, finalizer]
  path_globs:
    - "20*/**/*.md"
    - "!20*/*__*.md"       # month-dir drafts
    - "!20*/*/*__*.md"     # drafts moved under <name>/
    - # plus infographic companion vetoes
  agent_name_globs:
    - "!research.*.cdx"
    - "!research.*.cld"
    - "!research.*.grk"
    - "!research.*.mus"
    - "!research.*.gem"
  ops: [ADD]
```

Documented intent, from `provider.py`: the ref inventory *keeps* `__<suffix>`
drafts (citing a researcher's draft is legitimate); Highlights *excludes*
them. Producer restriction is separate: skip artifact-copy dispatch so Bob
does not see digest-suffixed basenames.

`FileHookFilters` knows only `projects`, `sidecars`, `path_globs`,
`agent_name_globs`, `ops`, `causes`, `producers`. There is no env, label,
kind, or intent field. `hook_matches_event()` never reads `os.environ`.

Agent attribution at capture time is
`$SASE_ARTIFACTS_DIR/agent_meta.json`'s `name`, then `$SASE_AGENT_NAME`.
Unattributed events match a negative-only agent list and miss a list that
contains any positive pattern.

### Artifact events already match on the original path

`capture_artifact_file_event()` records the source file's repo-relative path,
sidecar role, project, and agent. Dispatch then **replaces `abs_path` with the
stored copy** while keeping `rel_path`. Matching therefore sees
`202609/topic.md`; the detached command sees
`.../topic-<sha256-prefix>.md`.

`tests/test_file_hook_dispatch_regression.py` pins both sides:

- A hook *without* a producers filter dispatches on `sase artifact create` of
  a consolidated report, with `rel_path` original and `abs_path` stored.
- The same draft path is a quiet `no_match`.
- The *installed* `research-highlights` provider records `no_match` on
  artifact create, then dispatches on commit with `abs_path` equal to the
  sidecar file (original basename).
- `bob highlights create --dry-run` on `canonical_highlights_probe.md` yields
  id/pdf `canonical_highlights_probe`; the same bytes named
  `canonical_highlights_probe-ad048d84997e.md` yield that digest in both id
  and pdf.

The hook runner appends `abs_path` as the final shell argument and runs in a
**detached** batch process with `env=os.environ.copy()` of the runner, not of
the agent. Agent env vars are invisible to the hook command unless they are
copied into the batch.

Commit / finalizer dispatch happens in the stitch/finalizer process. Xprompt
`environment:` lives in the agent's `os.environ` for that run. It is not
automatically available later unless it is persisted (for example on
`agent_meta.json`).

### Why today's draft exclusion looks brittle

It is two veto lists that must track swarm shape:

1. **Path `__` veto.** Catches every `*__*.md` at depth 1 and 2, including
   `__critique.md` and any future suffix. A draft three directories down would
   leak. A publishable report that happens to contain `__` in the stem is
   excluded even when it should highlight.
2. **Agent-name veto.** Enumerates researcher shorts in
   `_SWARM_RESEARCHER_SUFFIXES`, duplicated from the swarm template. This is
   the safety net when a researcher writes `topic.md` without `__<short>`.
   Adding `research.*.foo` without updating the hook lets a misnamed draft
   through. Tests currently expect `research.*.final` and `research.*.critique`
   to *pass* the agent filter.

The `__` convention itself is load-bearing. `plan:202609/research_suffix_input.md`
introduced `suffix` so the lead can identify authorship from the filename
rather than transcripts. Replacing that convention with an env var is a
different problem from *using* the convention plus an intent signal.

## Critique of the proposed plan

### What is good

- **Producer-side opt-in.** "This write is hook-eligible" belongs on
  `#research`, not only on glob config that must chase every swarm change.
- **Default on.** Standalone `#research` and `#research/prompt` should publish
  Highlights without an extra flag.
- **Explicit swarm opt-out at the call site.** Every researcher segment is
  generated in one template. Passing `file_hook=false` there is a single
  place to maintain, including when a new provider is added, *if* the new
  segment is built from the same pattern.
- **Environment is how SASE already publishes launch policy to later
  commands** (`SASE_COMMIT_METHOD`). `sase artifact create` already runs in
  the agent process and can see that env at capture time.

### Why it is not sufficient

1. **No matcher consumes the variable.** Shipping `#research` env without a
   new `FileHookEvent` field and filter is a dead write. Do not match by
   reading live `os.environ` inside `hook_matches_event()`: that is
   unauditable, racy, and false for commit/finalizer/detached replay.

2. **It does not fix digest-suffixed command arguments.** Enabling
   `producers: [artifact]` without changing `abs_path` still leaks the 12-hex
   suffix into Bob's PDF identity. That is the documented reason the template
   omits `artifact`.

3. **`#research` cannot set `environment:` until it is a YAML workflow.**
   Adding an input to the markdown file does nothing to `os.environ`.

4. **Agent-scoped vs file-scoped.** An env var applies to every
   `sase artifact create` (and, if persisted, every later commit event) from
   that agent. Extra markdown the same agent registers would inherit
   Highlights. The registration command is the natural file-scoped choke
   point.

5. **The lead is outside `#research`.** Default-on env never stamps the
   consolidated report. Artifact-time Highlights for the lead also require a
   registration that today happens only when `critique=true`. Commit remains
   the fallback for the common `critique=false` path.

6. **Double-firing.** If both artifact create and the later commit match, Bob
   runs twice. The current producer split exists to prevent that. Any plan
   that adds `artifact` needs dedup (same hook + `rel_path`, reuse the
   existing batch if present) or must drop commit for this hook.

7. **Opt-out is fail-open if it is the *only* draft gate.** Forgetting
   `file_hook=false` on a new researcher segment would highlight drafts.
   Today's `!20*/*__*.md` fail-closes on the filename convention the swarm
   already requires. Keep that veto.

8. **Blank vs unset.** A Jinja `""` still sets the key. Capture must treat
   empty as no intent (`os.environ.get("SASE_FILE_HOOK_INTENT") or None`).
   Do not teach generic workflow injection to delete blank keys unless that
   is designed separately; it would change `#commit`-style workflows.

9. **Commit-time blindness.** Host finalizers do not inherit the agent's
   xprompt env. Intent used as a required AND filter would drop manual
   commits and lead commits unless it is copied onto `agent_meta.json` and
   reapplied at commit capture.

10. **`#research/more` and `ops: [ADD]`.** Extending a report is a MODIFY
    (or a non-event if the user never registers). Env on `#research` does not
    help. Pre-existing gap; not introduced by this plan.

### Is this a good idea?

As a *policy* for swarm vs solo research: yes.

As *the* matching design: no. An env var is a good defaulting channel into a
first-class event field. It is a poor matcher by itself, and it does not
unlock artifact-file hooks until the stored-copy basename problem is fixed.

## Requirement adjustments

These change the stated requirements. Each is called out on purpose.

1. **Match captured metadata, not live environment.** `SASE_FILE_HOOK_INTENT`
   is read once at event capture and stored on `CapturedFileEvent` /
   `FileHookEvent` (and producer audits). `filters.intents` compares that
   field.

2. **For artifact events, pass the original source path to the hook command
   when the source still exists.** `#research` already forbids `--move`. The
   stored copy remains the durable snapshot; Highlights needs the original
   basename. Put the stored path on the batch as metadata and in the detached
   run environment (`SASE_FILE_HOOK_STORED_PATH`, `SASE_FILE_HOOK_REL_PATH`,
   `SASE_FILE_HOOK_LABEL`).

3. **Keep the `__<suffix>` path veto.** Intent is the positive signal; the
   glob remains a cheap draft/critique/companion backstop. Do not replace the
   suffix convention. It is also the lead's authorship marker.

4. **Do not require intent on every producer on day one.** Required
   `filters.intents: [research-highlights]` would skip unattributed/manual
   commits (today those *pass* a negative-only agent list) and skip the lead
   until the lead is stamped. First enable artifact producer with original
   path + existing globs; add intent as an extra AND once the lead and
   `agent_meta` persistence exist.

5. **Dedup artifact then commit.** Same hook name + `rel_path` (and for
   commit, commit SHA reconciliation already reuses batches) must not spawn
   Bob twice.

6. **Stamp the lead explicitly if artifact-time Highlights should cover
   consolidated reports.** Either the lead segment sets
   `SASE_FILE_HOOK_INTENT`, or it calls `#research` for `<name>/<name>.md`
   (for example `#research(report_target=<name>/<name>.md)` after the
   directory exists). Registering only when `critique=true` is not enough
   for artifact-time hooks; keep commit as fallback until that changes.

7. **Name the input `file_hook` (bool, default `true`)**, override
   `file_hook=false`. Value of the env var should be the hook id
   (`research-highlights`), not `1`/`0`, so other hooks can reuse the
   channel later. A boolean env named after Highlights would paint the
   generic `#research` xprompt into one consumer.

8. **Convert `#research` to YAML** rather than adding `environment` to
   markdown frontmatter / Rust frontmatter schema. Out of scope for this
   feature.

9. **Do not live-match in `hook_matches_event` against `os.environ`.**

## Alternatives

| Approach | What it solves | What it costs |
| -------- | -------------- | ------------- |
| A. Status quo, generate both glob lists from one suffix tuple | DRY agent vetoes | Still no artifact-time hooks; `__` depth and stem collisions remain |
| B. Proposed live env var + `#research` override | Policy at the call site | No matcher; no basename fix; lead/commit blind; agent-scoped |
| C. Original-path artifact dispatch + add `artifact` producer | Unblocks artifact-time Highlights with matching that already works | Need dedup; drafts still rely on `__` + agent vetoes |
| D. `filters.label_globs` on `research:**/*.md` / `!research:**/*__*.md` | File-scoped identity already required by `#research` | Labels exist only on artifact create, not on commit events |
| E. `sase artifact create --intent` with env as default when omitted | File-scoped override; env remains the xprompt default | CLI + event field; still need original-path |
| F. Required `filters.intents` once lead + agent_meta stamp | New researcher cannot leak even if they omit `__` | Manual/unattributed commits stop highlighting unless listed |
| G. Positive `agent_name_globs: [research.*.final]` only | Simple | Drops standalone `#research` (arbitrary agent names) and manual commits |

C is the missing prerequisite. D and E are the right matching dimensions.
B without C/D/E should not ship.

## Recommended solution

Ship in three layers, plugin then host, so artifact-time Highlights start
working before intent is fully wired.

### Layer 1 — Host: make artifact files hookable (prerequisite)

In `sase` (Python file-hook path; matching already lives here, not in
sase-core):

1. On artifact dispatch, if `captured_source.abs_path` still exists, use it
   as the run's `abs_path` (command argument). Always record `stored_path`
   on the batch. If the source is gone (`--move` or deleted), fall back to
   the stored copy.
2. Export `SASE_FILE_HOOK_REL_PATH`, `SASE_FILE_HOOK_STORED_PATH`, and
   `SASE_FILE_HOOK_LABEL` (when known) into the detached run environment.
3. Capture `label` from `sase artifact create -l` onto the event.
4. When a later commit/finalizer event matches a hook that already
   dispatched for the same `rel_path` (artifact producer, still within
   retention), reuse / skip rather than spawn again.

Then the plugin can add `artifact` to `research-highlights` `producers`
**without any env var**. Existing path + agent vetoes already drop drafts
(`test_draft_reports_are_recorded_filter_misses`). Consolidated
`#research` registration starts Highlights immediately; the lead without
registration still highlights at commit.

This is the smallest change that actually "makes it easier to set file
hooks for artifact files."

### Layer 2 — Plugin: `#research` intent + swarm override

Convert `research.md` → `research.yml`:

```yaml
description: Write the current research to a new dated file in the research artifact repo.
input:
  - name: report_target
    type: path
    default: null
    # existing description
  - name: suffix
    type: word
    default: null
    # existing description
  - name: file_hook
    type: bool
    default: true
    description:
      When true (default), set SASE_FILE_HOOK_INTENT=research-highlights so
      file hooks may treat this agent's registered report as hook-eligible.
      Pass false from #research_swarm researchers so drafts do not publish
      Highlights.
environment:
  SASE_FILE_HOOK_INTENT: "{{ 'research-highlights' if file_hook else '' }}"
steps:
  - name: main
    prompt_part: |
      # existing body unchanged, including artifact create instructions
```

Capture rule: `intent = (os.environ.get("SASE_FILE_HOOK_INTENT") or "").strip() or None`.

`#research_swarm` researcher call sites (already one per segment):

```text
{{ prompt }} #research(suffix=cdx, file_hook=false)
```

and the same for `cld` / `grk` / `mus` / `gem`. The lead segment should set
the same env (or call `#research` for the consolidated path) if Layer 3
will require intent. Until then, commit fallback covers the lead.

Do not add `file_hook` to `#research/image` or `#research/more` in this
change.

### Layer 3 — Host + plugin: match on captured intent (optional hardening)

Add `intent: str | None` to the event and `filters.intents` with the same
positive-OR / `!` veto rules as agent names.

Recommended *eventual* `research-highlights` filters:

```yaml
filters:
  sidecars: [research]
  producers: [artifact, commit, sdd, finalizer]
  ops: [ADD]
  path_globs:
    - "20*/**/*.md"
    - "!20*/*__*.md"
    - "!20*/*/*__*.md"
    # companion vetoes
  agent_name_globs:
    - "!research.*.cdx"
    # ... keep until intent has been on for a release
  intents:
    - "research-highlights"
```

**Do not AND `intents` until** commit capture copies intent from
`agent_meta.json` (write the key when the xprompt injects it) **and** the
lead is stamped. Otherwise manual commits and unstamped lead commits go
quiet.

A later cleanup can drop `agent_name_globs` once intent + path veto have
replaced that safety net. Keep path `__` vetoes indefinitely; they are the
authorship convention, not just a hook hack.

Optional file-scoped escape hatch, if an agent with intent set must
register a non-hook file:

```text
sase artifact create -p ... -l ... --intent ""
```

Env supplies the default when `--intent` is omitted. Worth doing if Layer 2
shows agents registering extra markdown; skip until then.

### What not to do

- Do not match live `os.environ` in the matcher.
- Do not add `environment` to markdown xprompt frontmatter for this.
- Do not drop path vetoes when adding the override.
- Do not enable `artifact` producer without original-path dispatch.
- Do not make `filters.intents` required before the lead and commit
  capture can see the value.
- Do not use a boolean env var named after Highlights.

### Suggested implementation order

1. Host original-path + stored-path metadata + artifact/commit dedup.
2. Plugin: add `artifact` to `research-highlights` producers; extend
   regression tests (installed provider should now dispatch on create of a
   consolidated report, still `no_match` on `__` drafts, Bob dry-run id
   stays unsuffixed).
3. Plugin: YAML `#research` + `file_hook` + swarm `file_hook=false`.
4. Host: capture intent/label; persist intent on `agent_meta.json`.
5. Only then consider `filters.intents` and shrinking agent-name vetoes.
6. Decide separately whether the lead should always `sase artifact create`
   the consolidated report (also helps critique/`wait.artifacts` symmetry).

### Tests that must keep passing or be added

- `tests/test_file_hook_dispatch_regression.py`: installed provider,
  draft `no_match`, Bob basename, commit batch reuse.
- `sase-research-artifacts/tests/test_filters.py`: glob divergence
  (inventory keeps drafts; hook excludes them) and agent veto table.
- New: original-path used as command arg when source exists; stored path
  recorded; digest-suffixed stored name never appended when source
  remains.
- New: `#research(file_hook=false)` renders empty intent; swarm researcher
  segments contain `file_hook=false`; lead/default `#research` does not.
- New: artifact then commit of the same `rel_path` spawns one Bob run.

### Split of work

| Repo | Work |
| ---- | ---- |
| `sase` | Event fields, capture, original-path dispatch, dedup, optional `filters.intents`, `agent_meta` persistence, schema |
| `sase-research-artifacts` | YAML `#research`, `file_hook` input, swarm overrides, producer list, docs, plugin tests |
| `sase-core` | Not required for Layer 1–2. Matching is Python today. Move later only if another frontend needs the same filters |

## Open questions

- Should manual (no-agent) commits of `20*/**/*.md` still highlight? Today
  they can. Required intents would stop that. Prefer keeping path-glob
  fallback until that is an explicit product choice.
- Should the lead always register the consolidated report, independent of
  Highlights? `wait.artifacts` for critique already wants that when
  `critique=true`; always-on registration would make artifact-time hooks
  and critique share one producer contract.
- Is Highlights desired on `#research/more` (MODIFY)? Out of scope; the
  current `ops: [ADD]` would ignore it even with perfect intent.
- Depth-3+ `__` paths: if reports ever nest deeper than
  `<month>/<name>/file.md`, extend the veto to `!20*/**/*__*.md` (a
  negative `**` pattern) rather than another fixed-depth line.

## Bottom line

Use `#research` to default `SASE_FILE_HOOK_INTENT=research-highlights`, and
pass `file_hook=false` from every pre-lead `#research_swarm` researcher.
That is the right policy.

Do not treat that variable as the matcher. Capture it. Fix artifact
dispatch so the hook command receives the original sidecar file. Add
`artifact` to `research-highlights` producers with commit dedup. Keep the
`__<suffix>` path veto. Stamp the lead before making intent a required
filter.

The env-var override is a good *part* of the design. It is not the
design.
