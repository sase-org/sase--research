---
create_time: 2026-09-05
updated_time: 2026-09-05
status: research
---

# Removing SASE's Backward-Compatibility Layer

**Research question:** SASE carries a large amount of backward-compatibility code for
legacy functionality. Every machine that runs SASE is reachable over SSH from `athena`,
so legacy config and data files can be migrated rather than tolerated. What work is
actually required to remove all of it, and in what order?

**Scope and evidence:** `sase` @ `302875cbc`, `sase-core-rs` 0.32.23, `sase-github` @
`5aa3225`, `sase-telegram` @ `4b4fa4a`, `sase-nvim` @ `2250bbf`, and the live on-disk
state of all three fleet machines (`athena`, `kellys_mbp` via `mac`, `apollo`) on
2026-09-05. Every count below was measured directly: `grep`/`wc` over the checkouts, and
read-only probes over SSH (`sase version`, `sase doctor -j`, `sase config layers`,
`sase agent names purge-local-state` dry-run, `find` over `~/.sase`). Prior art read and
cited: `decisions:agents-sync-publish-only`, `decisions:v1-import-retired`,
`sase/memory/sase_flags.md`, `research:202609/sase_collaboration_architecture.md`.

---

## Executive summary

**The compatibility window that this code exists to protect does not exist.** All three
machines run byte-identical host and core builds — `sase 0.17.1+98.g302875cbc`,
`sase-core-rs 0.32.23`, `sase-github 0.2.9`, `sase-research-artifacts 0.2.0+9.g15a4b0954`
— from editable checkouts of the same commit, upgraded atomically by `sase update`, with
`~/.config/sase/sase.yml` rendered from one chezmoi source. The only skew in the entire
fleet is `sase-telegram` (0.4.9 wheel on `mac`/`apollo` vs `0.4.9+2.g4b4fa4a92` editable
on `athena`). There is no third-party consumer, no published-version straggler, and no
machine you cannot SSH into and fix in the same minute you land the change.

Three claims drive the recommendation:

1. **The backcompat surface is large but shallow, and it is overwhelmingly deletable
   without touching any machine.** 693 of 3,995 Python modules in `src/sase` (17%) carry
   a `legacy`/`deprecat` marker, but the concentrated core is small: **60 pure facade
   modules totalling 1,936 LOC** whose docstrings literally begin `"""Legacy`, 5 CLI
   command aliases, ~221 `def *legacy*` functions, and 12 `LEGACY_*` on-disk format
   constants. The facades have **one** real internal caller between them. Deleting them
   is a compile-time-safe change with zero data implications.

2. **The legacy state that *does* live on disk is concentrated, measured, and already
   has a supported one-command remedy — but nobody has run it on the fleet.**
   `sase agent names purge-local-state` reports **~10,000 imported artifacts, ~10,000
   dismissed bundles and ~6,500 chat files on each of `mac` and `apollo`** left behind
   by the deleted agents-sync import leg (`athena`: 79 / 809 / 0). Separately,
   `mac` and `apollo` still carry retired skill directories (`sase_artifact`,
   `sase_beads`, `sase_hg_commit`) across six provider directories each, which `athena`
   no longer has. **Fleet state has silently diverged**, and every removal decision that
   assumes "the migration already ran everywhere" is currently unverified.

3. **The root cause is a governance gap, not a code-quality problem, and deleting the
   code without closing that gap just restarts the accretion.**
   `sase/memory/sase_flags.md` states that a sunset flag is *mandatory* for any
   backward-compatible branch while callers migrate, and that removing a flag deletes
   the Off branch. There are exactly **5 flags in the registry, 3 of them `sunset`** —
   `ace_refresh_tokens`, `admin_center_flags`, `ref_sync_gesture` — and all three gate
   *new feature rollouts*, not deprecations. **Zero of the 685 remaining legacy-marked
   modules is behind a sunset flag.** Every one of them was landed with no flag, so no
   removal bead, no `remove_by` date, and no `FlagTriage` gate ever fires. The
   compatibility code is invisible to the very mechanism designed to retire it.

**Recommendation (detailed in §7): one epic, `Backcompat Zero`, in six phases, opening
with a fleet state-migration pass that runs *before* any code is deleted — so that
deletion becomes provably safe rather than optimistically safe — and closing with a lint
that makes the next unflagged compatibility branch impossible to land.**

---

## 1. The fleet: what "all my machines" actually means

| | `athena` | `mac` (`kellys_mbp`) | `apollo` |
|---|---|---|---|
| Reachable | local | `ssh mac` (tailnet) | `ssh apollo` (159.223.165.54) |
| `sase` host | `0.17.1+98.g302875cbc` | `0.17.1+98.g302875cbc` | `0.17.1+98.g302875cbc` |
| `sase-core-rs` | `0.32.23` | `0.32.23` | `0.32.23` |
| `sase-github` | `0.2.9` | `0.2.9` | `0.2.9` |
| `sase-research-artifacts` | `0.2.0+9.g15a4b0954` | `0.2.0+9.g15a4b0954` | `0.2.0+9.g15a4b0954` |
| `sase-telegram` | `0.4.9+2.g4b4fa4a92` (editable) | `0.4.9` (wheel) | `0.4.9` (wheel) |
| Python | 3.14.7 | 3.12 | 3.12.3 |
| `~/.config/sase/sase.yml` | chezmoi | chezmoi | chezmoi |
| Machine overlay | `sase_athena.yml` | `sase_kellys_mbp.yml` | *(none)* |
| Active today | yes | yes (procs 17:39) | yes (telegram 20:51) |

Three facts from this table shape everything downstream:

- **Version skew is not a real constraint.** `sase update` upgrades host, core and every
  plugin in one `uv tool upgrade` (`sase update --help`), so a machine is never
  half-migrated. The classic reason to keep a compatibility branch — "some caller is
  still on the old release" — has no instance here.
- **Config is a single source.** `~/.config/sase/sase.yml` renders from
  `chezmoi:home/dot_config/sase/sase.yml`. Any config-key migration is *one* edit plus
  `chezmoi apply` on three machines, not three hand-edits.
- **`apollo` has no machine overlay.** `sase_athena.yml` and `sase_kellys_mbp.yml` exist
  but `sase_apollo.yml` does not. Worth confirming that is intentional before a
  config-shape change lands; a missing overlay is exactly the kind of asymmetry that
  turns a "safe" removal into a broken machine.

The shared surfaces that *do* impose ordering are the git-backed sidecars — `beads`,
`plans`, `agents`, `research` — plus the agents-sync publication transport. Those are
written by one machine and read by the others, so any *format* change there needs the
two-landing rule in §7.4. Everything in `~/.sase/` is machine-local and can be migrated
in place over SSH.

---

## 2. Measured size of the surface

Baseline: `src/sase` is 152,294 LOC across 3,995 Python files; `tests/` is 219,721 LOC.

| Signal | Count |
|---|---|
| `src/sase` files matching `legacy\|deprecat` | 693 (17% of modules) |
| `legacy` line hits in `src/sase/**/*.py` | 2,801 (626 in comments/docstrings) |
| Pure facade modules (docstring starts `"""Legacy`) | **60 files / 1,936 LOC** |
| `def *legacy*` functions | 221 |
| `LEGACY_*` module constants | ~50 distinct, 12 encoding an on-disk or wire format |
| Legacy CLI command aliases | 5 (all verified live) |
| Deprecated top-level config keys | 8 mapped + 3 unsupported + 2 retired SDD selectors |
| `tests/` files mentioning legacy | 556 files / 2,061 hits |
| Test files *named* `*legacy*`/`*compat*`/`*changespec*`/`*migration*` | 30 files / 12,511 LOC |

The 17% file-level figure overstates the problem and the 1,936 LOC figure understates
it. The honest middle: roughly **2,000 LOC of pure dead facade, another ~3–5k LOC of
live-but-conditional legacy branches spread across ~120 modules, and ~12.5k LOC of tests
that exist only to hold those branches in place.**

---

## 3. Category inventory

### 3.1 Tier A — pure code facades (no on-disk state, no cross-repo caller)

The `ChangeSpec → Patch` and `Commit → Stitch` renames left a complete shadow package
tree. Representative:

- `src/sase/ace/changespec/` — 15 modules, 157 LOC in `__init__.py` alone, re-exporting
  ~60 names from `sase.ace.patch`
- `src/sase/core/changespec.py:1` — `"""Legacy ChangeSpec compatibility facade"""`
- `src/sase/main/parser_changespec.py`, `changespec_handler.py`, `parser_vcs.py`,
  `vcs_handler.py`, `parser_task.py`, `task_handler.py`, `task_render.py` — 4 LOC each,
  `from ... import *`
- `src/sase/ace/tui/actions/changespec/`, `src/sase/ace/tui/models/changespec_groups/`,
  `src/sase/ace/tui/widgets/changespec_*.py` — the TUI mirror

**Live internal callers: one.** `src/sase/integrations/_mobile_helper_catalog.py:7`
imports from `sase.integrations.changespec_tags`, which is itself a facade, plus a
`TYPE_CHECKING` re-export at `src/sase/core/__init__.py:151`. Everything else importing
these paths is a test written to test the facade (50 import sites in `tests/`).

Also Tier A:

- **CLI aliases**, all verified working today: `sase changespec`→`patch`
  (`src/sase/main/parser_patch.py:46`), `sase vcs`→`stitch`
  (`parser_stitch.py:311`), `sase task`→`proc` (`parser_proc.py:20`),
  `sase artifact-file`→`artifact` (`parser_artifact.py:25`), `sase prompt sdd`→`archive`
  (`parser_prompt.py:336`). Dispatch lives in `src/sase/main/entry.py:182,473,509`.
- **Keymap action aliases** — `LEGACY_APP_KEY_ALIASES` at
  `src/sase/ace/tui/keymaps/registry.py:58` maps 12+ `*_changespec`/`commits_*` action
  names, with a migrator in `src/sase/main/config_handler.py:82-122` and a doctor check
  in `src/sase/doctor/checks_config_keymap_actions.py`. **No machine's config uses any
  of them** (verified: `sase config layers` reports 0 deprecated keys on all three).
- **UI aliases** — `LEGACY_ARTIFACTS_SUBTABS` (`src/sase/ace/tui/_artifact_tab_model.py:41`,
  maps retired `prs`/`bugs`/`plans`/`other` subtabs), `_LEGACY_TAB_ALIASES`
  (`modals/config_center_state.py:17`), `_LEGACY_KIND_TO_PANE_ID`
  (`core/artifact_entry_target.py:20`), `_LEGACY_SELECTOR_ALIASES` and
  `_LEGACY_STATE_VALUE_ALIASES` (`ace/testing/ace_page.py:28,34` — test-harness only).
- **The `/sase_changespecs` skill** — `src/sase/xprompts/skills/sase_changespecs.md`,
  self-described as "Compatibility shim for /sase_patches". This one has a *recurring*
  cost: it is deployed to 8 provider directories on `athena` and 6+ on each of `mac` and
  `apollo`, and its description line is loaded into every agent's skill list on every
  turn, on every provider, forever.

**Disposition: delete outright. No flag, no migration, no machine work.** The only user
-visible loss is muscle memory for four command aliases.

### 3.2 Tier B — one-shot migrations whose work is provably finished

| Migration | Code | Fleet state |
|---|---|---|
| `.gp` → `.sase` project spec | `src/sase/ace/patch/project_spec_migration.py` (130 LOC), `project_spec_path.py:17` | **0 `.gp` files on any machine**; 13/4/4 `.sase` files |
| single-file → sharded prompt history | `src/sase/history/prompt_store_migration.py` (76 LOC) | `prompt_history.json` **absent everywhere**; `prompt_history/` present everywhere |
| `tasks.jsonl` → `procs` store | `src/sase/procs/_migration.py` (~120 LOC) | marker `procs_migration.json` present everywhere; **leftover `~/.sase/tasks/` dir on `athena` only** |
| memory root relocation | `src/sase/main/init_memory/root_migration.py` (130 LOC), `memory/paths.py:10` | canonical everywhere |
| historical auto agent-name | `src/sase/agent/names/_migration.py` | marker `agent_name_auto_migration.json` present everywhere; registry `schema_version: 2` everywhere |
| unsharded → `YYYYMM/` chats & bundles | `src/sase/history/chat_storage.py:122-145`, `ace/dismissed_agents_paths.py:26-49` | 0 flat files, 3 shards on all three |
| legacy PR-mirror lane `checks` | `src/sase/external_mirror/state.py:68-94` | **2 stale files on `athena`**, clean elsewhere |
| legacy `code-swap.lock` inode | `src/sase/dev_update/code_swap_lock.py:49` | **present on `athena`**, clean elsewhere |
| legacy tribe store `agent_tags.json` | `src/sase/core/agent_tribe.py:82-190` | **245 KB on `athena`** alongside canonical `agent_tribes.json`; absent on `mac`/`apollo` |

**Disposition: run the residual cleanup on `athena` (§7.1), then delete the migration
code and its readers.** These are ~600 LOC of one-shot code plus their fallback readers.
Note the asymmetry: `athena` is the *dirtiest* machine for local migration leftovers
precisely because it is the oldest install.

### 3.3 Tier C — dead import-leg state (the big one)

`decisions:agents-sync-publish-only` records that epic `sase-ws` deleted the entire
agents-sync import leg and left `sase agent names purge-local-state` as "the sole
supported operation on leftover imported local state." **That command has never been
applied on the fleet.** Dry-run results today:

| | dismissed bundles | imported artifacts | chat files | caches / journals / receipts |
|---|---|---|---|---|
| `athena` | 809 | 79 | 0 | 3 journals, 2 cache dirs, 2 receipts |
| `mac` | 9,924 | 9,894 | 6,501 | 2 journals, 2 cache dirs, 2 receipts |
| `apollo` | 10,076 | 10,076 | 6,562 | 2 journals, 2 cache dirs, 2 receipts |

Corroborating on-disk evidence: `~/.sase/agents_sync/cache/objects/**/payload/manifest.json`
(the `_LEGACY_MANIFEST_PATH` of `src/sase/agents_sync/git_sync_ops.py:31`) exists on all
three, including `apollo` caching `users/bbugyi200/machines/athena/manifest.json`.

**Disposition: `--apply` the purge on each machine, in that order, after a backup.**
This is the single largest concrete win in the whole project and it requires *no code
change at all* — the code was already deleted; only the data was left behind. It is also
the most destructive step in the plan: ~6,500 chat transcripts per machine. Treat it as
requiring explicit confirmation and a tarball, not as routine hygiene.

### 3.4 Tier D — cross-repo couplings (these are the real work)

These cannot be deleted unilaterally; each needs a coordinated change in a linked repo.

- **Telegram pending actions — still actively written.**
  `sase-telegram/src/sase_telegram/pending_actions.py:12` hardcodes
  `~/.sase/telegram/pending_actions.json` as the plugin's *primary* store. The host
  merges it read-only via `_merge_legacy_telegram`
  (`src/sase/notifications/pending_actions.py:346`) and tags records with the transport
  id `telegram_legacy` (`pending_actions.py:376`, matched at
  `sase-telegram/src/sase_telegram/inbound.py:550`). The file was modified **today** on
  both `athena` (17:33) and `apollo` (20:51). This is not leftover data — it is a live
  second store. **Removing the host-side merge requires first porting `sase-telegram` to
  the shared `~/.sase/pending_actions/actions.json`, then draining both stores.**
- **`sase-github` import fallback.**
  `sase-github/src/sase_github/scripts/new_pr_desc_get_context.py:12-13` —
  `except ImportError: from sase.ace.changespec import find_all_changespecs as find_all_patches`,
  commented "Older supported SASE releases expose only ChangeSpec names." Guarded, so
  deleting the facade leaves it dead-but-harmless; still needs removing in the same epic.
- **`sase-nvim` legacy formats.** `sase-nvim/syntax/sase_gp.vim` (`.gp` syntax) and
  `sase-nvim/plugin/sase_yamlls.lua:70,82` ("Legacy project config remains schema-backed
  during migration"), plus a legacy completion dispatcher at `lua/sase/complete.lua:14`.
- **`sase-telegram` internal legacy shapes** — `_LEGACY_AWAITING_KEY`
  (`inbound.py:158`), `_LEGACY_EQUAL_TIMESTAMP_ID` (`outbound.py:20`), and the
  `bundle.legacy` branch (`gate_flow.py:72`, `inbound.py:381`) reading the host's
  `_resolve_legacy_bundle` (`src/sase/notification_gates/paths.py:140`).

### 3.5 Tier E — shared-format readers (need the two-landing rule)

Formats written into git-backed sidecars or long-lived local records, read by all
machines:

- **`COMMITS:` → `STITCHES:`** — `src/sase/ace/patch/storage.py:8-14`. Still live data:
  `~/.sase/projects/gh_sase-org__sase/gh_sase-org__sase-archive.sase` on `athena` uses
  the legacy heading, and only one project file on the fleet uses `STITCHES:`. Also
  `LEGACY_PATCH_HEADING = "## ChangeSpec"` and `LEGACY_REVIEW_URL_LABEL = "CL"`
  (`ace/patch/review_field.py:4`).
- **Plan path prefixes** — `_LEGACY_PLAN_PREFIXES` / `_LEGACY_PLAN_MARKERS`
  (`src/sase/sdd/associations/_normalization.py:17`,
  `src/sase/sdd/plan_header_writes.py:23`) each accept four historic plan roots
  (`.sase/sdd/plans/`, `sase/repos/plans/`, `sdd/plans/`, `plans/`). This is committed
  content in the `plans` sidecar.
- **Bead notes** — `LEGACY_NOTE_ID_PREFIX = "__legacy_note__"`
  (`src/sase/bead/note_codec.py:23`) plus untyped-legacy-bead triage handling
  (`sase.schema.json:3455`). This is committed content in the `beads` sidecar.
- **Memory frontmatter** — `_LEGACY_NOTE_TYPES = {"short": "core", "long": "reference"}`
  (`src/sase/memory/notes.py:36`) and `_LEGACY_TASK_TYPES_NOTE_TYPES_HEADING = "## Types"`
  (`src/sase/main/init_memory/root_rendering_task_types.py:45`).
- **Gate request schema** — `LEGACY_GATE_REQUEST_SCHEMA_VERSION = 2` vs
  `GATE_REQUEST_SCHEMA_VERSION = 3` (`src/sase/notification_gates/model_validation.py:11`),
  consumed in `hashing.py:139`.
- **Plan chain suffixes** — `_LEGACY_DOTTED_SUFFIX_MAP` / `_LEGACY_DASH_SUFFIX_MAP`
  (`src/sase/plan_chain.py:36-48`), 35 legacy hits in that one file.
- **Chat links** — `_LEGACY_TIMESTAMP_LINE_RE` (`src/sase/history/chat_links.py:24`).

**Disposition: for each, write a forward-migration pass over the sidecar, land the
writer, roll the fleet, then delete the reader.** These are the only categories where
ordering genuinely matters.

### 3.6 Tier F — config

Good news: **the fleet's config is already clean.** `sase config layers` reports 0
deprecated keys on all three machines, and `~/.config/sase/sase.yml` uses the modern
`llm_provider.model_aliases.{builtin,custom}` and `axe.*.chops` map forms.

Still to remove from the *code*, since nothing uses them:

- `DEPRECATED_TOP_LEVEL_KEYS` (`src/sase/config/layers.py`) — 8 entries:
  `amd_agents_template`, `amd_agents_minimal_template`, `memory_sase_template`,
  `memory_readme_template`, `linked_repos`, `sibling_repos`, `machine_name`, `tasks`
- `UNSUPPORTED_TOP_LEVEL_KEYS` — `amd_h1_title`, `glossary`, `workflows`
- `RETIRED_SDD_SELECTOR_KEYS` — `storage`, `version_controlled`
- `external_mirror.exclude_labels` / `pr_authors` folds
  (`src/sase/external_mirror/config.py`, doctor check `checks_config_external_mirror.py`)
- ~20 `"deprecated": true` blocks in `src/sase/config/sase.schema.json`

**One real config fix is outstanding:** `sase doctor -C config.model_aliases` reports 3
retired builtin aliases in the shared config — `medium_worker`, `small_worker`,
`xsmall_worker` should move to `medium`, `small`, `xsmall`. Because the file is
chezmoi-managed, this is one edit in `chezmoi:home/dot_config/sase/sase.yml` plus
`chezmoi apply` on three machines.

### 3.7 Tier G — fleet drift discovered while probing

Not part of the code cleanup, but it invalidates the assumption the cleanup rests on:

- `mac` and `apollo` still have retired skill directories that no longer exist in
  `src/sase/xprompts/skills/` — **`sase_artifact`, `sase_beads`, `sase_hg_commit`** —
  each present in 6+ provider directories (`.claude`, `.qwen`, `.gemini`,
  `.gemini/jetski`, `.gemini/antigravity-cli`, `.config/opencode`, `.config/muse`,
  `.grok`). `athena` has none of them. The retirement path exists
  (`src/sase/main/_init_skills_manifest.py:559` `_discover_legacy_sase_namespace_files`,
  `state="retired"`) but has not been driven on those machines.
- `athena` alone carries `~/.sase/tasks/`, `agent_tags.json`,
  `axe/lumberjacks/checks/external_pr__*.json`, and `locks/code-swap.lock`.

**Every machine is dirty in a different way.** That is the strongest argument for making
the fleet sweep the *first* phase rather than a cleanup afterthought.

---

## 4. Root cause: the flag rule is not enforced

`sase/memory/sase_flags.md` is unambiguous: *"A flag is also mandatory for deprecated or
backward-compatible branches while callers migrate,"* with `kind: sunset`, a
`remove_by_date`, a `remove_by_release`, a `--remove-when` gate, a typed flag bead, and
a `FlagTriage` gate that fires when both thresholds pass.

Measured reality:

- The registry holds **5** flags (`src/sase/feature_flags/registry.py:24-28`); 3 are
  `sunset`: `ace_refresh_tokens`, `admin_center_flags`, `ref_sync_gesture`. All three
  gate *new* behavior being rolled forward, not old behavior being retired.
- Of the 693 legacy-marked modules, **8** reference feature-flag machinery — and all 8
  *are* the feature-flag machinery (`feature_flags/*.py`, `doctor/checks_flags.py`,
  `main/parser.py`, the schema).
- Therefore: **not one of the ~685 compatibility branches catalogued above has a flag, a
  removal bead, or a deadline.** None will ever surface in `FlagTriage`.

The one time SASE *did* retire a compatibility leg properly — `v1_import_retired` /
bead `sase-wc`, epic `sase-ws` — it worked exactly as designed, and
`decisions:agents-sync-publish-only` records the outcome. That is the template. The
problem is that it was applied once, by hand, to one subsystem.

The corollary matters for scoping: **a one-time deletion pass without an enforcement
change buys perhaps 18 months.** The rename-shadow packages in Tier A are already the
second generation of this pattern (`ChangeSpec`→`Patch` followed `Commit`→`Stitch`).

---

## 5. Risks and what could go wrong

1. **The purge is destructive and irreversible.** ~6,500 chat transcripts and ~10,000
   artifacts per machine. `decisions:agents-sync-publish-only` explicitly states there is
   no path back. Mitigation: `tar` `~/.sase/{chats,artifacts,dismissed_bundles,agents_sync}`
   to durable storage on each machine before `--apply`, and diff the dry-run report
   against the tarball manifest.
2. **`sase-telegram` is the only genuinely blocking dependency.** It writes a live
   legacy store today. Removing the host merge before the plugin is ported drops inbound
   Telegram approvals on the floor — on `apollo`, which is running Telegram chops right
   now. Sequence it explicitly.
3. **Shared-sidecar formats can strand a machine mid-rollout.** If `athena` lands a
   writer that emits only `STITCHES:` while `apollo` still runs a reader that was just
   taught to reject `COMMITS:`, the ordering is wrong. The two-landing rule in §7.4 is
   the guard.
4. **`apollo` has no machine overlay.** Confirm before landing config-shape changes.
5. **Deleting facades will break ~50 test imports and ~30 test files (12.5k LOC).**
   Those tests are the *point* of the deletion, not collateral — but `just check-full` is
   a monitor-only landing gate per `decisions:two-speed-verification`, so budget for it.
6. **Symvision will flag newly-unused symbols** as facades are removed. Per
   `sase/memory/symvision.md` this is expected; resolve by deleting, not by whitelisting.

---

## 6. Alternatives considered

- **Do nothing / let it decay.** Rejected: the surface is already at 17% of modules and
  compounds with every rename. `decisions:agents-sync-publish-only` documents the
  concrete maintenance tax — an unrelated ACE test broke because a dead producer site
  still existed.
- **Wrap every legacy branch in a sunset flag first, then let `FlagTriage` retire them
  over ~90 days.** Rejected as the primary path: it is the *by-the-book* reading of
  `sase_flags.md`, but creating ~120 flag beads for branches with a provably empty
  caller set is ceremony with no information content. The flag rule exists to protect a
  migration window; there is no window here. Reserve flags for Tier E only, where the
  fleet-rollout ordering makes the window real.
- **One big-bang PR.** Rejected: 30 test files and 5 repos: unreviewable, and it would
  put the destructive purge and the code deletion in the same blast radius.
- **Delete the code first, clean the machines after.** Rejected — this is the tempting
  order and it is backwards. Tier B/C decisions all rest on claims like "the `.gp`
  migration already ran everywhere." Those claims are *currently true* for `.gp` and
  *currently false* for the skills prune and the import purge. Verify first, then delete.

---

## 7. Recommended solution

**One epic — `Backcompat Zero` — in six phases, opening with a fleet sweep and closing
with an enforcement lint.** Phase 0 is not code; it is the evidence that makes phases
1–5 safe.

### 7.0 Phase 0 — Fleet state sweep (no code changes)

Run on `athena`, then `mac`, then `apollo`. Nothing is deleted from the codebase until
this phase reports clean on all three.

1. **Back up** `~/.sase/{chats,artifacts,dismissed_bundles,agents_sync,projects}` to
   durable storage on each machine.
2. **`sase agent names purge-local-state --apply`** on each machine. Expected removals:
   `athena` 809/79/0, `mac` 9,924/9,894/6,501, `apollo` 10,076/10,076/6,562, plus caches,
   journals and receipts. This is the destructive step — confirm per machine.
3. **`sase init skills`** on each machine to prune the retired
   `sase_artifact` / `sase_beads` / `sase_hg_commit` directories from `mac` and `apollo`.
4. **`athena`-only residue:** remove `~/.sase/tasks/`, `~/.sase/agent_tags.json`,
   `~/.sase/axe/lumberjacks/checks/external_pr__*.json`, `~/.sase/locks/code-swap.lock`
   after confirming their canonical counterparts are populated.
5. **Config:** migrate `medium_worker`/`small_worker`/`xsmall_worker` →
   `medium`/`small`/`xsmall` in `chezmoi:home/dot_config/sase/sase.yml`; `chezmoi apply`
   on all three; confirm `sase doctor -C config.model_aliases` is `OK` everywhere.
   Decide whether `apollo` needs a `sase_apollo.yml` overlay.
6. **Record the evidence.** Land a `check_fleet_legacy_state` doctor check that reports
   what remains, and capture the three machines' output. Deletion PRs cite it.

Deliverable: a one-page state table proving every Tier B migration has completed and
every Tier C artifact is gone, fleet-wide.

### 7.1 Phase 1 — Free deletions (Tier A)

Delete `src/sase/ace/changespec/`, `src/sase/ace/tui/actions/changespec/`,
`src/sase/ace/tui/models/changespec_groups/`, `src/sase/core/changespec.py`, the eight
4-LOC `main/` facades, the `changespec_*` widgets, `workspace_provider/changespec.py`,
`integrations/changespec_tags.py`, `workflows/commit/changespec_*.py`,
`doctor/checks_changespec_refs.py`. Remove the 5 CLI aliases and their `entry.py`
dispatch. Remove `LEGACY_APP_KEY_ALIASES` and its migrator/doctor check, the UI alias
maps, and `src/sase/xprompts/skills/sase_changespecs.md`. Fix the one real caller at
`integrations/_mobile_helper_catalog.py:7`. Delete the ~30 facade-only test files.
Redeploy skills fleet-wide (`sase init skills` ×3) so `/sase_changespecs` stops loading
into every agent turn on every provider.

Expected: ~2,000 LOC of `src` and ~12,500 LOC of `tests` removed. No machine data
touched beyond the skill prune.

### 7.2 Phase 2 — Finished migrations (Tier B) and config code (Tier F)

Delete `project_spec_migration.py` and `LEGACY_PROJECT_SPEC_EXTENSION`,
`prompt_store_migration.py` and `legacy_prompt_history_file()`, `procs/_migration.py`,
`init_memory/root_migration.py` and `LEGACY_MEMORY_RELATIVE_ROOT`, the
`agent_tags.json` fallback in `core/agent_tribe.py`, `_migrate_legacy_pr_mirror_state`,
the legacy `code-swap.lock` handoff, the unsharded-fallback branches in
`chat_storage.py` and `dismissed_agents_paths.py`, and `include_legacy=True` defaults in
`core/paths.py:304`. Delete `DEPRECATED_TOP_LEVEL_KEYS`, `UNSUPPORTED_TOP_LEVEL_KEYS`,
`RETIRED_SDD_SELECTOR_KEYS`, the `external_mirror` folds, and the `"deprecated": true`
schema blocks. Each deletion cites the Phase 0 evidence line that proves it is unused.

### 7.3 Phase 3 — Cross-repo couplings (Tier D), plugin-first ordering

1. Port `sase-telegram` to the shared `~/.sase/pending_actions/actions.json`; drain and
   delete `~/.sase/telegram/pending_actions.json` on `athena` and `apollo`; then remove
   `_merge_legacy_telegram` and the `telegram_legacy` transport from the host.
2. Remove the `ImportError` fallback in `sase-github/.../new_pr_desc_get_context.py`.
3. Remove `.gp` syntax and legacy schema paths from `sase-nvim`.
4. Remove `sase-telegram`'s `_LEGACY_AWAITING_KEY` / `_LEGACY_EQUAL_TIMESTAMP_ID` /
   `bundle.legacy` branches together with the host's `_resolve_legacy_bundle`.

Land plugin changes first, `sase update` all three machines, verify a live Telegram
round-trip, then land the host-side deletion.

### 7.4 Phase 4 — Shared formats (Tier E), two-landing rule

For each of `COMMITS:`/`## ChangeSpec`/`CL:`, plan path prefixes, `__legacy_note__`,
memory `type: short|long`, `## Types`, gate schema v2, and plan-chain suffix maps:

> **Landing 1** — write a forward-migration pass that rewrites existing records in the
> sidecar (or `~/.sase/projects/`) to canonical form. Land it with the reader still
> accepting both. Run it. Commit the rewritten sidecar.
> **Roll** — `sase update` on all three machines; confirm identical versions.
> **Landing 2** — delete the legacy reader and its constant.

This is the only category that warrants sunset flags — one per format, created with
`sase flag new <key> -k sunset`, closed by deleting the Off branch in Landing 2, exactly
as `sase_flags.md` prescribes. It is also the only category where a mistake can strand a
machine, so it goes last, when the rest of the surface is quiet.

### 7.5 Phase 5 — Enforcement, so this does not recur

1. **A `tools/check_backcompat` lint**, wired into `just check`: fail any new
   `legacy`/`deprecated`/`compat` marker on a code path in `src/sase` that is not
   registered against a `sunset` feature flag. Seed its allowlist from whatever survives
   Phase 4, so the allowlist is the complete, shrinking list of known debt rather than a
   permanent amnesty.
2. **A rename policy in memory:** a rename lands as a rename. No shadow package, no
   command alias — or, if an alias is genuinely wanted, it ships behind a `sunset` flag
   with a `remove_by` date on day one. This is the specific rule whose absence produced
   Tier A twice.
3. **A `decisions:` record** — `backcompat-is-deleted-not-flagged` — stating the claim
   (single-user fleet at one commit, updated atomically, all machines SSH-reachable ⇒
   compatibility branches are deleted outright and only cross-machine *format* changes
   get a sunset flag), the rejected alternative (flag everything), the cost (a mistake
   means SSH-ing into three machines to fix state by hand), and the reopen condition
   (SASE gains a user or machine that this host cannot reach and update).

### 7.6 Sequencing and effort

| Phase | Scope | Machine work | Blocking? |
|---|---|---|---|
| 0 Fleet sweep | no code | **all 3, destructive** | gates everything |
| 1 Free deletions | ~2k src + 12.5k test LOC | `sase init skills` ×3 | after 0 |
| 2 Finished migrations + config | ~600 src LOC | none (done in 0) | after 0 |
| 3 Cross-repo | 4 repos | `sase update` ×3, Telegram verify | after 1 |
| 4 Shared formats | ~8 formats, 2 landings each | `sase update` ×3 per format | after 3 |
| 5 Enforcement | lint + memory + decision | none | after 4 |

Phases 1 and 2 are independent and parallelizable. Phase 4 is the long tail and the only
part that should move slowly.

**The single highest-value action, and the one to take first, is Phase 0 step 2 —
`sase agent names purge-local-state --apply` on `mac` and `apollo`.** It removes ~26,000
dead files per machine, requires no code change, uses a command that already exists and
is already the documented remedy, and it converts the central assumption of this entire
plan from "probably true" into "measured."

---

## Appendix — reproducing the evidence

```bash
# Fleet version parity
for h in mac apollo; do ssh "$h" '~/.local/bin/sase version'; done; sase version

# Legacy surface size
grep -rIl -iE "legacy|deprecat" src/sase --include=*.py | wc -l   # 693 / 3995
grep -rIl '^"""Legacy' src/sase --include=*.py | xargs wc -l | tail -1   # 1936

# Facade caller count (excluding the facades themselves)
grep -rIn "from sase\.ace\.changespec\|from sase\.core\.changespec" src/sase --include=*.py \
  | grep -v "src/sase/ace/changespec/\|src/sase/core/changespec.py"

# Flag coverage of legacy code (all 8 hits are the flag machinery itself)
for f in $(grep -rIl -iE "legacy|deprecat" src/sase --include=*.py); do \
  grep -l "feature_flag\|is_flag_enabled" "$f"; done

# Dead import-leg state, per machine
sase agent names purge-local-state | grep -oE "Would remove [a-z ]+" | sort | uniq -c
for h in mac apollo; do ssh "$h" '~/.local/bin/sase agent names purge-local-state \
  | grep -oE "Would remove [a-z ]+" | sort | uniq -c'; done

# Stale retired skills on mac/apollo (absent on athena)
for h in mac apollo; do ssh "$h" 'find ~ -maxdepth 5 -type d -path "*skills*" \
  \( -name sase_artifact -o -name sase_beads -o -name sase_hg_commit \)'; done

# Config cleanliness + the one outstanding fix
sase config layers | grep -i deprecat        # empty on all three
sase doctor -C config.model_aliases -v       # 3 retired *_worker builtin aliases
```
