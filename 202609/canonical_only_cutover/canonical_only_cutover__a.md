---
create_time: 2026-09-05
updated_time: 2026-09-05
status: research
---

# Retiring SASE's Legacy Compatibility Surface

## Executive summary

Removing SASE's operative backward-compatibility logic is feasible now, but it is not
just a code-deletion change. The current fleet is unusually well positioned for a hard
cutover: `athena`, `mac` (`kellys_mbp`), and `apollo` are on the same SASE and Rust-core
versions, and most durable stores have already migrated to their canonical layouts.
Artifact sharding, `.sase` project files, prompt-history sharding, Proc records, and
sharded chats are effectively complete everywhere.

The remaining blockers are concentrated and identifiable:

1. Athena and Apollo are still actively writing the legacy Telegram pending-action
   store. That compatibility path crosses `sase`, `sase-core`, and `sase-telegram` and
   must be retired as a coordinated writer-then-reader change.
2. Athena retains an old `~/.sase/tasks/` tree, the v1 code-swap lock, old plan/question
   request directories, and two Patch/project specs containing the old `COMMITS:`
   spelling. Its running ACE/axe processes also make a live upgrade unsafe.
3. Apollo retains a legacy `~/.xprompts/` directory and is running ACE/axe. Its
   canonical xprompt copies are newer and should win.
4. Mac has one `type: long` memory file; the managed chezmoi source also has obsolete
   worker model aliases and one repo-local `type: short` memory declaration.
5. The shared plans sidecar still has a small number of operative legacy headers and
   `plans:` artifact references.
6. Plugin consumers still depend on compatibility APIs. `sase-github` imports
   ChangeSpec fallbacks, `sase-telegram` depends on several legacy stores and names,
   and `sase-nvim` deliberately supports `.gp`, `.xprompts`, the old completion
   backend, old xprompt output fields, and `%(A, B)`.
7. Some compatibility readers exist for immutable history, especially bead event
   streams and Git-derived metadata. Deleting them without first creating canonical
   checkpoints would make historical data unreadable. Rewriting append-only history
   is the wrong migration.

The recommended endpoint is a coordinated, canonical-only SASE release deployed to all
three machines in one maintenance window. Before that release, update every writer and
plugin consumer, run a one-shot audited migration on each host and the shared sidecars,
and require a machine-readable zero-legacy preflight. Preserve old bytes as offline
archives, but move their decoding into a frozen migration tool or release tag rather
than keeping compatibility branches on normal runtime paths.

## Scope and method

This audit covers:

- the current SASE checkout and its Python tests;
- the linked Rust core, `sase-github`, `sase-telegram`, `sase-nvim`, and
  `sase-research-artifacts` repositories;
- the managed chezmoi configuration;
- the shared plans and research sidecars; and
- live, read-only checks on the local host plus the `mac` and `apollo` SSH targets.

The fleet scope follows the existing tailnet fleet record and was verified using
`~/.sase/machine_name`: the local machine is `athena`, `mac` is `kellys_mbp`, and
`apollo` is `apollo`. The checks below are a snapshot from 2026-09-05. Transient state,
particularly agents, gates, and pending Telegram actions, will continue to change until
the maintenance window.

The source search intentionally used broad terms such as `legacy`, `deprecated`, and
`compatibility`. It found 733 Python source files, 77 Rust source files, 571 Python test
files, and 11 Rust integration-test files with at least one explicit marker. Those are
candidate counts, not deletion counts. A zero-match grep would be a bad acceptance
criterion because many matches describe test data, historical releases, task beads,
ordinary Git commits, or resilience fallbacks that are still canonical concepts.

The main code ownership map is:

| Repository | Principal compatibility surfaces |
| --- | --- |
| `sase` | CLI parsers/handlers; ACE Patch/ChangeSpec facades and TUI names; Proc migration; config aliases; gates/notifications; prompt/chat/agent migration adapters; generated skills and docs |
| `sase-core` | Shared content discovery; project/Patch parsers; Python wire aliases; artifact, plan, Proc, pending-action, bead-event, agent-scan, and Git-history decoders |
| `sase-github` | Old SASE import fallbacks, `changespec_*` hook arguments, `.gp` lookup, and `sdd` sidecar override |
| `sase-telegram` | Private pending actions, `telegram_legacy`, old gate/question payloads, ChangeSpec imports/fields, `.gp` lookup, and timestamp-only cursors |
| `sase-nvim` | `.gp` and `.xprompts` recognition, old picker backend/catalog fields, legacy completion kinds, `@plans:`, and `%(A, B)` |
| `chezmoi` | Retired worker aliases, old memory type names and generated prose, deployed compatibility skills, and `.xprompts` ignore rule |

These migrations are recent rather than archaeological: Patch replaced ChangeSpec on
2026-08-09, Proc replaced the background-task command/store on 2026-08-13, the gate and
agent scanner wires changed in late August, and the agents-sync v1 import path was
retired on 2026-09-03. That timing explains both the large compatibility surface and why
a coordinated removal is practical now: the complete live fleet is already on one
post-migration version.

## What should count as backward compatibility

The cleanup should distinguish four classes:

| Class | Examples | Disposition |
| --- | --- | --- |
| Operative compatibility | CLI aliases, old config keys, dual writers, fallback paths, old wire fields | Migrate users/data, then delete |
| One-shot migration code | task-store migration, flat artifact migration, prompt-history import | Run everywhere, prove completion, then remove from the installed runtime |
| Immutable-history decoding | old bead events, historical Patch/Git metadata | Create a canonical checkpoint or projection; retain the old decoder only in a frozen offline migrator |
| Non-legacy fallback | optional plugin absence, network/error recovery, default selection, current task beads | Keep |

Two naming traps matter:

- A legacy SASE background **task** became a **Proc**, but a bead of type `task` is a
  current, canonical concept. Removing every `task` symbol would break the tracker.
- `COMMITS:` inside an old Patch/project spec is a legacy spelling for `STITCHES:`, but
  commit lists in plan provenance and ordinary Git terminology are not necessarily
  legacy. Each parser contract must be evaluated, not renamed by search-and-replace.

Internal facade modules used solely as test seams are also not automatically user-facing
compatibility. They can be consolidated during this work, but their removal is a code
organization decision rather than a data migration requirement.

## Fleet state

### Versions and activity

All three machines reported:

- SASE `0.17.1+98.g302875cbc`
- `sase-core-rs` `0.32.23`
- `sase-github` `0.2.9`
- `sase-research-artifacts` `0.2.0+9.g15a4b0954`

Athena has editable `sase-telegram` `0.4.9+2.g4b4fa4a92`; Mac and Apollo have the
released `0.4.9`. Athena and Apollo had ACE/axe processes running during the audit. Mac
had no matching SASE service process. This means Athena and Apollo must be explicitly
drained and stopped before data conversion; merely upgrading packages over the running
processes would preserve old writers in memory.

`sase config init -c` reported that config initialization was complete on all three
hosts, and `sase config layers` did not report deprecated, retired, unsupported, or
legacy keys. The apparent `machine_name` and `tasks` text in current YAML are canonical
nested configuration or a Telegram command name, not deprecated top-level settings.

### Migrations that are already complete

| Store or format | Athena | Mac | Apollo | Conclusion |
| --- | ---: | ---: | ---: | --- |
| Flat artifact directories | 0 | 0 | 0 | Remove flat-layout reader after final preflight |
| Sharded artifact directories | 11,556 | 10,039 | 10,263 | Canonical layout is established |
| Artifact alias rows | 0 | 0 | 0 | Old alias-table migration has no remaining fleet input |
| Artifact schema | 25 | 25 | 25 | All current; migration not recommended by status command |
| `.gp` project files | 0 | 0 | 0 | Remove `.gp` discovery after plugin/editor cutover |
| `.sase` project files | 13 | 4 | 4 | Canonical extension is established |
| Legacy project lifecycle values | 0 | 0 | 0 | Remove `active/inactive/archived/closed` normalization |
| `prompt_history.json` | absent | absent | absent | Remove single-file lazy import |
| Prompt-history shards | 3 | 1 | 1 | Canonical layout is established |
| Old prompt-entry fields | 0 | 0 | 0 | Remove `branch_or_workspace`/`workspace` fallbacks |
| Unsharded top-level chat Markdown | 0 | 0 | 0 | Remove unsharded chat lookup after final preflight |
| Proc migration marker | present | present | present | Migration ran on every host |
| Proc rows with old `task_id` or legacy lifecycle | 0 | 0 | 0 | Canonical Proc payloads are established |

The artifact counts came from the installed artifact-layout status API. The other rows
were filesystem and record-shape checks; they did not modify any store.

### Host-specific work still required

#### Athena

- `~/.sase/tasks/` is a real directory, not a symlink, and still contains
  `tasks.jsonl` plus logs. `~/.sase/procs/` and the migration marker also exist. The
  current migrator can mark completion when the new store already exists without
  removing the old tree, so this must be compared against the canonical Proc store,
  archived, and deleted before removing `src/sase/procs/_migration.py`.
- `~/.sase/locks/code-swap.lock` remains beside canonical `code-swap-v2.lock`. Confirm
  that no process owns the old inode, then remove it before deleting the handoff logic
  in `dev_update/code_swap_lock.py`.
- `~/.sase/user_question/` and `~/.sase/plan_approval/` contain July request/response
  files. Their newest files were dated 2026-07-16; they are not current requests, but
  they should be archived only after a cross-check against active agent and notification
  IDs. Current requests live under `~/.sase/interaction_requests/`.
- Two `.sase` files still contain the Patch-section spelling `COMMITS:`:
  `sase-core/sase-core.sase` and
  `gh_sase-org__sase/gh_sase-org__sase-archive.sase`. Rewrite those sections through a
  parser-aware migration, not a blind replacement.
- A stale `.sase/home` exists in this ephemeral workspace. Doctor identifies it as the
  former prompt-staging location; verify no live agent references it and remove it.
- The installed doctor reports the retired model aliases `medium_worker`,
  `small_worker`, and `xsmall_worker`.

#### Mac (`kellys_mbp`)

- `~/sase/memory/sase_beads.md` still declares `type: long`. Regenerate it or change
  the canonical source to `type: reference`, then remove the `short`/`long` serde
  aliases from the Rust memory loader.
- No old Telegram pending-action file, task tree, `.gp` file, single-file prompt
  history, or legacy xprompt root was found. Mac is therefore the lowest-risk final
  validation host even though Apollo is a better unattended canary.

#### Apollo

- `~/.xprompts/` contains `sshot.yml` and `pick_plan.md`. Canonical copies under
  `~/sase/xprompts/` are newer. In particular, canonical `sshot.yml` uses
  `@file:{{ fetch.local_path }}` rather than the old inline form. Preserve a backup,
  confirm no unique local edits, and remove the legacy root.
- ACE/axe is active and the Telegram hook is running. Stop it before the pending-action
  migration and package replacement.

### Shared and managed sources

The managed chezmoi config defines the three retired worker aliases at
`home/dot_config/sase/sase.yml`. Move their values to canonical
`llm_provider.model_aliases.builtin.medium`, `.small`, and `.xsmall`, then regenerate
and deploy config to all hosts. The chezmoi repository's own `sase/memory/sase.md`
declares `type: short`; that is repo-local SASE memory and should become `type: core`.
Generated README text that still teaches `short`/`long` should be regenerated from the
canonical memory templates. The global Git ignore entry for `.xprompts/*` becomes dead
after Apollo's directory is removed.

Athena and Mac have managed machine overlays; Apollo has a live
`sase_apollo.yml` overlay but no corresponding managed source in the opened chezmoi
tree. Reconcile and add the Apollo overlay to the same managed source of truth before
the cutover so the final fleet audit is reproducible.

The shared plans sidecar contains 4,101 tracked Markdown files. The audit found eight
files with old `plan:`, `prompt:`, or `parent:` frontmatter; six are mixed with canonical
header bullets, so two are legacy-only. Thirty files contain `@plans:`/`plans:` text.
Only operative artifact references should be rewritten to canonical `plan:` syntax;
historical prose should remain historical. A dry-run plan-link refresh scanned 4,096
plan files and found no parent migrations, although 1,637 projections would be refreshed
and 90 unpublished parents remain warnings. Run the parser-aware refresh/migration and
resolve only errors that block canonical reads.

The research sidecar contains 35 `plans:` occurrences, mostly documentation. Treat them
the same way: migrate parsed references, not quoted history. Counts of `ChangeSpec`,
`task`, or `commit` in plans and research are not evidence of operative compatibility.

## Runtime compatibility that must be removed

### 1. ChangeSpec to Patch

This is the largest public rename surface:

- remove the `sase changespec` command alias and the generated
  `sase_changespecs` compatibility skill;
- remove the `src/sase/ace/changespec/` facade tree and remaining
  `changespec_*` action, property, keymap, query, tag, and workspace aliases;
- remove `ChangeSpec`, `changespec_name`, and `changespec_parent` wire/binding aliases
  after all callers use `Patch`, `patch_name`, and `patch_parent`;
- remove Python conversion fallbacks that accept both `commits` and `stitches`, and
  remove the Rust parser's `## ChangeSpec` and Patch-spec `COMMITS:` branches after the
  two Athena files are migrated;
- update docs, completion catalogs, generated skills, and tests so legacy syntax fails
  instead of silently normalizing.

Consumer order matters. `sase-github` currently catches `ImportError` and imports
ChangeSpec names from old SASE releases; its workspace hook arguments are still named
`changespec_*`. `sase-telegram` imports the old project-spec/tag modules and falls back
to `entry.changespec_name`. Release canonical-only versions of both plugins while SASE
still exposes the aliases, then raise their minimum SASE version before deleting the
host API.

### 2. Background Task to Proc

Remove `sase task`, `parser_task.py`, `task_handler.py`, Proc parser aliases, the old
supervisor/store adapters, `read_tasks_snapshot`/`append_task` bindings, and the
`SASE_TASK_STORE_LOCK_TIMEOUT` environment alias. Delete the on-disk task migrator only
after Athena's leftover tree has been reconciled.

Do not remove task beads, task-type plugin hooks, Task Triage gates, or prose that refers
to tracked work. Those are current product behavior and are unrelated to the old
background-process command.

### 3. VCS and commit-era aliases

Remove the `sase vcs` command alias, old VCS handler/parser names, `commits_*` TUI keymap
aliases, `ace.artifacts.commits` config alias, and old Patch wire fields. Keep ordinary
Git commit vocabulary and plan-provenance commit sections where those are the canonical
domain concept. The already removed `sase commit` command is a useful precedent: old
syntax can become a hard error once managed callers are gone.

### 4. Config and model aliases

After managed config is canonical on every host, delete:

- top-level `amd_agents_minimal_template`, `amd_agents_template`, `linked_repos`,
  `sibling_repos`, `machine_name`, `memory_readme_template`,
  `memory_sase_template`, and `tasks` remapping;
- ignored retired top-level `amd_h1_title`, `glossary`, and `workflows` keys;
- `sdd.storage` and `sdd.version_controlled` selectors;
- `ace.artifacts.commits`, `ace.keymaps.gate.activate_control`,
  `external_mirror.exclude_labels`, and `external_mirror.pr_authors` aliases;
- old dotted `path` versus canonical `key_path` config wire handling;
- lumberjack `chops` list-to-keyed-map normalization; and
- the `medium_worker`, `small_worker`, and `xsmall_worker` model-routing aliases.

The three currently enabled sunset feature flags—`ace_refresh_tokens`,
`admin_center_flags`, and `ref_sync_gesture`—are a related cleanup opportunity. The
fleet resolves all three on, so delete their old branches and then delete the flags.
`provider_drain` and `typed_launch_units` are beta flags, not legacy evidence, and need
their own lifecycle decision.

### 5. Content, history, and store layouts

Once the fleet preflight is clean, remove these readers and migrators:

- legacy xprompt roots `.xprompts/`, `xprompts/`, and project-specific
  `~/.config/sase/xprompts/<project>/` from Rust content discovery, the Python wrapper,
  the LSP, and Neovim;
- root-level legacy `memory/` and `sase.yml` discovery;
- memory `type: short`/`long` aliases;
- `.gp` project discovery and lifecycle normalization;
- flat artifact paths, alias-table migration, and flat agent-artifact scan paths;
- single-file prompt history and old PromptEntry fields;
- unsharded/imported chat lookup plus `#resume`/`#resume_by_chat` aliases if no managed
  caller remains;
- old agent-name registry schema readers;
- old plan frontmatter link readers;
- the task-to-Proc store migration; and
- legacy glossary-read-log migration.

Delete migrations in the same release or immediately afterward. Leaving dormant
migrators installed makes it impossible to prove that a legacy layout is unsupported.
Keep a tagged pre-cutover release and the fleet backup as the migration path for a
machine restored from an old backup.

### 6. Gates, notifications, scanner wires, and locks

These are transient compatibility paths and require quiescence rather than bulk data
conversion:

- legacy PlanApproval/UserQuestion request directories and per-kind gate fallbacks;
- old gate bundles and request fields;
- flat scanner fields such as `monitor_*`/`gate_*` now represented by nested
  `family_shell` data;
- pre-v7 agent scan/wire normalization;
- the legacy code-swap lock inode/handoff; and
- Telegram's private pending-action store and `telegram_legacy` transport.

The Telegram path is the critical blocker. At audit time:

| Host | Legacy `~/.sase/telegram/pending_actions.json` | Shared `~/.sase/pending_actions/actions.json` |
| --- | ---: | ---: |
| Athena | 13 entries; modified 2026-09-05 | 3,080 entries |
| Mac | absent | 93 entries |
| Apollo | 8 entries; modified 2026-09-05 | 92 entries |

The same-day modification on Athena and Apollo proves that this is not dead residue.
First change `sase-telegram` to create and resolve only transport-neutral records in the
shared host store. Let existing callbacks resolve or expire for at least their normal
24-hour window, then migrate or deliberately invalidate the remaining callback tokens.
Only after a zero-write observation window should SASE core stop merging the old file
and stop returning the `telegram_legacy` transport.

### 7. Neovim and other plugin surfaces

`sase-nvim` needs a coordinated breaking cleanup:

- remove `.gp` detection and syntax claims;
- remove `.xprompts`/`xprompts` LSP and YAML-schema globs;
- remove `completion_backend = "legacy"`, the picker fallback dispatcher, and old
  `sase xprompt list` field normalization;
- remove legacy `kind = "changespec"` completion fixtures;
- stop advertising `@plans:` and `%(A, B)`; and
- update help and tests to canonical paths and `%{A | B}`.

The editor plugin should be upgraded before the runtime rejects the old catalogs. A
mixed old editor/new runtime is otherwise likely to keep generating or requesting
legacy forms. `sase-research-artifacts` did not show a comparable operative legacy
surface, but it still needs integration testing against the final artifact-ref API.

### 8. Smaller public aliases and tombstones

A final API review should decide and then remove every explicitly compatibility-only
entry point, including:

- umbrella `sase init config|memory|repo|skills` aliases for the canonical grouped
  `config init`, `memory init`, `repo init`, and `skill init` commands;
- `artifact-file` for `artifact` and `@plans:` for `@plan:`;
- retired prompt `--sdd` and prompt-store `sdd` aliases;
- directive aliases `%name`/`%n`, `%tribe`/`%t`, `%time`, and `%edit`;
- old alternative syntax `%(A, B)` and obsolete snippet placeholders;
- old underscore VCS reference normalization; and
- `%auto` arguments retained only for old plan/tale/epic launch behavior.

Some of these currently produce a targeted migration error rather than executing old
behavior. If the goal is literally no legacy recognition logic, replace them with the
ordinary unknown-command/directive path after managed prompts and docs are clean. A
small release-note table is a better permanent record than runtime tombstones.

## Immutable history is the hard boundary

The bead store's canonical source is append-only `beads/events/**`; `issues.jsonl` is a
generated projection. Rust currently decodes earlier status, size, type, note, and event
shapes so that it can replay that history. Removing those decoders directly would make
valid historical stores unrebuildable, while rewriting events in place would violate
the append-only audit model.

For a literal canonical-only runtime, introduce a signed/versioned checkpoint that
contains the fully materialized current bead state plus the last consumed event for
each stream. The new runtime starts at that checkpoint and reads only current event
schemas after it. Preserve all earlier event bytes in the sidecar for audit, but require
the frozen pre-cutover tool to replay them. The checkpoint creator must verify that its
projection equals a full replay before it is accepted. This is additional core work,
not a search-and-delete task.

Historical Git footers, ChangeSpec names in old commits, and legacy plan/research prose
have the same shape of problem. Do not rewrite Git history. Materialize the canonical
Patch/stitch/agent projection in a new commit or index, record its source boundary, and
make normal readers start there. Keep the old decoder in a tagged migration binary for
forensics and disaster recovery, not in the main SASE process.

If zero compatibility code is not worth the checkpoint complexity, the principled
alternative is to declare one explicit exception: isolate immutable-history codecs in
an `archive` module with no writers and no effect on current validation. That still
removes all user-facing and live-store compatibility, but it is not literally zero
legacy decoding. The recommended solution below chooses the literal endpoint by using
checkpoints.

## Sequencing and dependencies

This should be one multi-repository epic with ordered phases, not independent cleanup
patches:

1. **Build the census and migrators.** Add a machine-readable `doctor` legacy section
   that reports exact paths, config provenance, record counts, old writers, plugin
   versions, and active processes. Keep conversion in a one-shot script/tool whose
   output includes before/after hashes and backup paths.
2. **Canonicalize writers and consumers.** Change SASE, Telegram, GitHub, generated
   skills, and Neovim to emit/use canonical APIs while the old runtime can still read
   both. Add minimum-version constraints between packages.
3. **Migrate managed/shared sources.** Fix chezmoi, the Apollo overlay, memory types,
   plan headers/references, Patch `COMMITS:` sections, and deployed skills. Deploy the
   canonical config to all machines.
4. **Checkpoint immutable stores.** Create and verify bead and historical metadata
   checkpoints. Store migration evidence and backups outside paths the new runtime will
   scan.
5. **Drain the fleet.** Stop new launches; wait for or cancel active agents and gates;
   stop ACE, axe, gateway/Telegram workers, and code-swap processes on Athena and
   Apollo; verify Mac is idle. Observe zero writes to old stores for a full pending
   action TTL.
6. **Run the host migrations.** Back up `~/.sase` and relevant `~/sase` content on all
   hosts; reconcile Athena's tasks tree and old request/lock files; remove Apollo's
   legacy xprompt root; refresh Mac's memory file; and rerun the census until every host
   is clean.
7. **Deploy an atomic canonical-only package set.** Install mutually compatible builds
   of Rust core, SASE, GitHub, Telegram, research-artifacts, and Neovim. Use Apollo as
   the first unattended canary, then Athena, then Mac, while all old writers remain
   stopped.
8. **Delete compatibility code and fixtures.** Remove aliases, readers, migrators,
   compatibility tests, stale docs, and the three sunset feature flags. Negative tests
   should prove that representative legacy inputs are rejected, not normalized.
9. **Verify and restart.** Run each repository's normal checks, the full landing lanes,
   parser/wire parity tests, and a fleet acceptance suite covering config load, Patch
   and Proc views, agent launch/finalization, Telegram callbacks, xprompt LSP completion,
   artifact resolution, plan links, and bead checkpoint replay. Restart Apollo, Athena,
   and Mac only after the zero-legacy census passes on each.

The rollback unit is the complete package set plus per-host backup, not an individual
wheel. Rolling back only SASE while leaving a canonical-only plugin, or vice versa,
would reintroduce the very mixed-version behavior being removed.

## Acceptance criteria

The retirement is complete when:

- every fleet host passes the same versioned legacy census with zero operative findings;
- no process writes any retired path during a full observation window;
- all managed config and generated skills come from canonical source and Apollo's
  overlay is managed;
- shared plans/research references validate without legacy parser branches;
- current stores rebuild from canonical checkpoints and post-checkpoint events;
- canonical-only plugins declare and enforce compatible minimum versions;
- representative old commands, config keys, paths, wire fields, and directive syntax
  fail as unknown/invalid;
- the main runtime contains no legacy writer, normalizer, migrator, or historical replay
  branch;
- a frozen pre-cutover tool and backups are sufficient to restore or inspect old data;
  and
- ordinary resilience fallbacks and current task-bead behavior still pass regression
  tests.

## Evidence reviewed

- Current Python and Rust source, tests, schemas, bindings, and recent Git history.
- Linked plugin source and documentation for GitHub, Telegram, Neovim, and research
  artifacts.
- Managed chezmoi config and generated-skill sources.
- `sase config init`, `sase config layers`, doctor output, artifact layout status, and
  read-only filesystem/record scans on Athena, Mac, and Apollo.
- Shared plan-link validation/refresh dry runs and parser-oriented searches of the plans
  and research sidecars.
- `tailnet_agent_fleet/tailnet_agent_fleet.md` for the established fleet model, checked
  against live SSH identity and version results.

## Recommended solution

Create a single **canonical-only SASE release epic** whose contract is “no live legacy
inputs, no compatibility writers, and no old-history replay in the normal runtime.” Do
not begin with broad code deletion. First land one fleet census and one-shot migrator,
then update `sase-telegram`, `sase-github`, `sase-nvim`, generated skills, and managed
config to canonical-only outputs while the current runtime still accepts them.

Next, create verified canonical checkpoints for append-only bead and historical
Git/Patch projections; this avoids rewriting history while allowing the new runtime to
drop all old decoders. During a scheduled fleet maintenance window, stop SASE services
on Athena and Apollo, confirm Mac is idle, wait one Telegram callback TTL, back up every
host, and run the host-specific migrations. Require the census to be clean on
`athena`, `kellys_mbp`, and `apollo` before installing anything.

Deploy a pinned, mutually compatible package set to Apollo first, Athena second, and Mac
third, with old writers stopped throughout. Once fleet acceptance passes, delete the
CLI/config/directive aliases, legacy layouts and wire fields, one-shot migrators,
compatibility skills, plugin fallbacks, editor support, tests, docs, and sunset-flag old
branches. Keep only the backups and a frozen pre-cutover release/tool for offline
recovery. This is the shortest path to a genuinely canonical-only codebase without
silently losing the history accumulated on any of Bryan's machines.
