# Canonical-Only Cutover: Retiring SASE's Backward-Compatibility Surface

**Research question:** SASE carries a large amount of backward-compatibility code for
legacy functionality. Every machine that runs SASE is SSH-reachable from `athena`
(`mac`, `apollo`), so legacy config and data can be migrated rather than tolerated.
What work is required to remove all of it, in what order, and how do all three machines
factor in?

**Sources:** consolidates `canonical_only_cutover__a.md` (research.1f.cdx) and
`canonical_only_cutover__b.md` (research.1f.cld) with independent lead verification.
Every number below was re-measured on 2026-09-05 against the working tree at
`457041681` (both source reports measured `302875cbc`, three commits back), `sase-core`
0.32.23, the linked plugin checkouts, and read-only SSH probes of all three machines.
Where the two reports disagreed, §4 states which one the evidence supports.

---

## 1. Executive summary

Both source reports reach the same top-line conclusion and the evidence supports it:
**there is no compatibility window to protect.** All three machines run the same host
and core build (`sase 0.17.1+98.g302875cbc`, `sase-core-rs 0.32.23`, `sase-github`
0.2.9, `sase-research-artifacts` 0.2.0+9.g15a4b0954), upgraded atomically by
`sase update`, with `~/.config/sase/sase.yml` rendered from one chezmoi source. There is
no third-party consumer. The classic reason to keep a compatibility branch — "some
caller is still on an old release" — has exactly one instance in the entire fleet
(`sase-telegram`, §3.4).

The work splits cleanly, and the split matters more than the total size:

| | What it is | Machine work | Verdict |
|---|---|---|---|
| **Fleet state** | ~54,000 dead files fleet-wide, plus per-machine drift | destructive, all 3 | **Do first.** Needs zero code change. |
| **Dead facades** | 60 modules / 1,936 LOC, 5 CLI aliases, alias maps | skill redeploy only | Delete outright. |
| **Finished migrations** | ~600 LOC of one-shot migrators + fallback readers | athena residue only | Delete after the sweep. |
| **Cross-repo couplings** | 4 repos; one live second store | plugin republish + rollout | Plugin-first ordering. |
| **Shared formats** | ~8 formats in git-backed sidecars | two landings each | Only tier needing sunset flags. |
| **Immutable bead history** | one field decoder over 27,881 append-only events | none | Keep, isolated. See §4.1. |

Three findings change the plan relative to what either report proposed:

1. **All three machines are running `axe` right now**, including `mac` — report `__a`
   states `mac` had no SASE service process and designates it the low-risk validation
   host on that basis. That is false (§4.3). Every machine needs a drain.
2. **The test cleanup is mostly a rename, not a deletion.** 44 test files are named
   `*changespec*` (9,783 LOC) but only **4** import the compatibility facades; the other
   40 are canonical `sase.ace.patch` tests carrying a stale filename (§4.2). Report
   `__b`'s "~12,500 LOC of tests exist only to hold these branches in place" overstates
   the deletable set and hides a mechanical rename chore.
3. **The bead event store has exactly one schema version.** All 27,881 events are
   `schema_version: 1` (§4.1). Report `__a`'s signed-checkpoint subsystem is
   over-engineered for the actual residue; report `__b`'s "forward-migrate the sidecar,
   then delete the reader" is the wrong mechanism for an append-only store. The correct
   answer is neither.

**Recommendation (§7): one epic, six phases, opening with a fleet state sweep before any
code is deleted and closing with an enforcement lint.** The highest-value first action
is `sase agent names purge-local-state --apply` on `mac` and `apollo` after a backup —
~26,000 dead files per machine, no code change, using the command
`decisions:agents-sync-publish-only` already designates as the sole supported remedy.

---

## 2. The fleet: what "all my machines" actually means

| | `athena` | `mac` (`kellys_mbp`) | `apollo` |
|---|---|---|---|
| Reachable | local | `ssh mac` | `ssh apollo` |
| `sase` / `sase-core-rs` | `0.17.1+98.g302875cbc` / `0.32.23` | same | same |
| `sase-telegram` | `0.4.9+2.g4b4fa4a92` (editable) | `0.4.9` (wheel) | `0.4.9` (wheel) |
| Python | 3.14.7 | 3.12.5 | 3.12.3 |
| Config source | chezmoi | chezmoi | chezmoi |
| Machine overlay | `sase_athena.yml` | `sase_kellys_mbp.yml` | **none managed** |
| `axe` running | **yes** | **yes** (5 lumberjacks) | **yes** |
| Legacy telegram store | 14 entries, mod 17:58 today | absent | mod 20:51 today |
| Purge backlog | 809 identities + caches | **26,326 files** | **26,721 files** |
| Retired skill dirs | 0 | 17 | 17 |
| `/sase_changespecs` copies | 8 | 9 | 9 |

Three consequences:

- **Version skew is nearly a non-issue, with one exception.** `sase update` upgrades
  host, core and plugins in one `uv tool upgrade`, so a machine is never half-migrated.
  But `sase-telegram` is a *published wheel* on `mac` and `apollo` and an editable
  checkout on `athena`. Any telegram change requires a republish, not just a pull —
  `__b`'s "no published-version straggler" is not quite right.
- **Config is a single source.** Any config-key migration is one chezmoi edit plus
  `chezmoi apply` ×3. `apollo` having no managed overlay while a live `sase_apollo.yml`
  exists (per `__a`) is the kind of asymmetry that turns a "safe" removal into a broken
  machine; reconcile it into chezmoi before any config-shape change lands.
- **Every machine is dirty differently.** `athena` is dirtiest for local migration
  leftovers (oldest install); `mac`/`apollo` are dirtiest for import-leg residue and
  retired skills. No single machine's state proves the fleet's state. This is the
  strongest argument for making the sweep phase 0 rather than a cleanup afterthought.

---

## 3. Category inventory

### 3.1 Tier A — dead facades (no on-disk state)

The `ChangeSpec → Patch` and `Commit → Stitch` renames left a complete shadow package
tree: **60 modules whose docstring begins `"""Legacy`, totalling 1,936 LOC**, plus:

- `src/sase/ace/changespec/` (19 modules), `src/sase/core/changespec.py`, the
  `src/sase/ace/tui/actions|models|widgets/changespec*` mirror
- 8 four-line `main/` facades: `parser_changespec.py`, `changespec_handler.py`,
  `parser_vcs.py`, `vcs_handler.py`, `parser_task.py`, `task_handler.py`,
  `task_render.py`
- **5 live CLI aliases**: `changespec`→`patch` (`parser_patch.py:46`), `vcs`→`stitch`
  (`parser_stitch.py:311`), `task`→`proc` (`parser_proc.py:20`), `artifact-file`→
  `artifact`, `prompt sdd`→`archive`
- Alias maps: `LEGACY_APP_KEY_ALIASES` (`ace/tui/keymaps/registry.py:58`, 12+ actions,
  with a migrator at `main/config_handler.py:82-122` and a doctor check),
  `LEGACY_ARTIFACTS_SUBTABS`, `_LEGACY_TAB_ALIASES`, `_LEGACY_KIND_TO_PANE_ID`
- `src/sase/xprompts/skills/sase_changespecs.md` — "Compatibility shim for
  /sase_patches", **deployed to 26 provider directories fleet-wide**, its description
  line loaded into every agent's skill list on every turn, on every provider

**Live non-test callers of the facades: four**, not the "one" `__b` reports —
`integrations/_mobile_helper_catalog.py:7`, `core/__init__.py:151` (TYPE_CHECKING), and
two in the TUI Patch load path (`ace/tui/actions/patch/_loading.py:149`,
`_core.py:334`). The last two are the important ones — see §4.4.

**Disposition: delete outright.** No flag, no data migration. User-visible loss is
muscle memory for four command aliases.

### 3.2 Tier B — one-shot migrations, provably finished

| Migration | Code | Fleet state |
|---|---|---|
| `.gp` → `.sase` | `ace/patch/project_spec_migration.py` | 0 `.gp` on any machine |
| single-file → sharded prompt history | `history/prompt_store_migration.py` | `prompt_history.json` absent everywhere |
| `tasks.jsonl` → procs | `procs/_migration.py` | marker everywhere; **`~/.sase/tasks/` on athena only** |
| memory root relocation | `main/init_memory/root_migration.py` | canonical everywhere |
| agent-name registry | `agent/names/_migration.py` | `schema_version: 2` everywhere |
| unsharded → `YYYYMM/` chats & bundles | `history/chat_storage.py:122-145` | 0 flat files anywhere |
| PR-mirror lane `checks` | `external_mirror/state.py:68-94` | **2 stale files on athena** |
| `code-swap.lock` inode | `dev_update/code_swap_lock.py:49` | **athena only** |
| tribe store `agent_tags.json` | `core/agent_tribe.py:82-190` | **245 KB, athena only** |
| plan/question request dirs | gate fallbacks | **athena only** (`user_question/`, `plan_approval/`, July 2026) |
| legacy xprompt root `~/.xprompts/` | Rust content discovery + nvim globs | **apollo only** (2 files, Jul 3) |

Confirmed by direct probe. Note the split: `athena` carries almost all local-migration
residue; `apollo` carries the one legacy xprompt root. `__b` missed the apollo xprompt
root and the athena request dirs; `__a` found both.

**Disposition: clear the residue in phase 0, then delete ~600 LOC of migrators and their
fallback readers.**

### 3.3 Tier C — dead import-leg state (the biggest single win)

`decisions:agents-sync-publish-only` records that epic `sase-ws` deleted the entire
agents-sync import leg and left `sase agent names purge-local-state` as the sole
supported operation on leftover state. **It has never been applied on the fleet.**
Re-verified dry-runs:

| | dismissed bundles | imported artifacts | chat files | total |
|---|---|---|---|---|
| `athena` | 809 identities | 79 | 0 | + 3 journals, 2 caches, 2 receipts |
| `mac` | 9,924 | 9,894 | 6,501 | **26,326** |
| `apollo` | 10,076 | 10,076 | 6,562 | **26,721** |

`__a` did not surface this at all — its fleet table reports the artifact *sharding*
migration as complete (true) without noticing that ~10,000 of those sharded artifacts on
each remote are dead import-leg residue. This is `__b`'s strongest unique contribution
and it is fully confirmed.

**Disposition: `--apply` after a tarball backup.** It is the most destructive step in
the plan (~6,500 chat transcripts per machine, no path back per the decision record) and
warrants explicit per-machine confirmation, not routine hygiene.

### 3.4 Tier D — cross-repo couplings

- **Telegram pending actions — a live second store, and the only hard blocker.**
  `sase-telegram/src/sase_telegram/pending_actions.py:12` hardcodes
  `~/.sase/telegram/pending_actions.json` as the plugin's *primary* store. The host
  merges it read-only (`src/sase/notifications/pending_actions.py:346`) and tags records
  `telegram_legacy` (`:376`). Modified **today** on `athena` (17:58, 14 entries) and
  `apollo` (20:51). Removing the host merge before the plugin is ported drops inbound
  Telegram approvals on the floor.
- **Guarded facade imports — not blockers.** All three plugin call sites are
  `except ImportError` fallbacks: `sase-github/.../new_pr_desc_get_context.py:12-13`,
  and `sase-telegram/.../sase_tg_inbound.py:714,891`. Verified: deleting
  `src/sase/ace/changespec/` leaves them dead-but-harmless. They still get removed in
  the same epic, but they do **not** constrain ordering.
- **`sase-nvim`**: `syntax/sase_gp.vim`, `.xprompts`/`xprompts` YAML-schema globs
  (`plugin/sase_yamlls.lua:83-86`), `completion_backend = "legacy"` dispatcher
  (`lua/sase/complete.lua:14`), legacy `kind = "changespec"` fixtures, `@plans:` and
  `%(A, B)` syntax.
- **`sase-telegram` internal shapes**: `_LEGACY_AWAITING_KEY`, `_LEGACY_EQUAL_TIMESTAMP_ID`,
  the `bundle.legacy` branch, reading the host's `_resolve_legacy_bundle`
  (`src/sase/notification_gates/paths.py:140`).

### 3.5 Tier E — shared formats (the only tier needing sunset flags)

Formats committed to git-backed sidecars or long-lived local records, read by all three
machines. Ordering genuinely matters here:

- **`COMMITS:` → `STITCHES:`** (`ace/patch/storage.py:8-14`), plus
  `LEGACY_PATCH_HEADING = "## ChangeSpec"` and `LEGACY_REVIEW_URL_LABEL = "CL"`.
  **Two** live project specs on athena, not one: `sase-core/sase-core.sase` and
  `gh_sase-org__sase/gh_sase-org__sase-archive.sase` — and the archive file contains
  **both** spellings, so the rewrite must be parser-aware, not `sed`.
- **Plan path prefixes** — `_LEGACY_PLAN_PREFIXES` / `_LEGACY_PLAN_MARKERS`
  (`sdd/associations/_normalization.py:17`, `sdd/plan_header_writes.py:23`), four historic
  roots; committed content in the `plans` sidecar (4,101 tracked files, 8 with legacy
  frontmatter per `__a`).
- **Memory frontmatter** — `_LEGACY_NOTE_TYPES = {"short": "core", "long": "reference"}`
  (`memory/notes.py:36`). **One live consumer fleet-wide:**
  `mac:~/sase/memory/sase_beads.md` declares `type: long`. `athena` has no such file at
  all — this is stale drift, not a canonical copy. Deleting the alias without fixing
  `mac` breaks memory loading there.
- **Gate request schema v2 vs v3** (`notification_gates/model_validation.py:11`).
- **Plan chain suffixes** (`plan_chain.py:36-48`), **chat link timestamps**
  (`history/chat_links.py:24`), **`## Types` heading**, **`__legacy_note__`** (§4.1).

### 3.6 Tier F — config: already clean on disk

`sase config layers` reports **0** deprecated keys on all three machines; the rendered
config already uses `llm_provider.model_aliases.{builtin,custom}` and `axe.*.chops` map
form. Only the *code* remains: `DEPRECATED_TOP_LEVEL_KEYS` (8 entries),
`UNSUPPORTED_TOP_LEVEL_KEYS` (3), `RETIRED_SDD_SELECTOR_KEYS` (2), the `external_mirror`
folds, and ~20 `"deprecated": true` schema blocks.

**One real fix outstanding:** `sase doctor -C config.model_aliases` reports WARN with 3
retired builtin aliases — `medium_worker`/`small_worker`/`xsmall_worker` → `medium`/
`small`/`xsmall`. One chezmoi edit plus `chezmoi apply` ×3.

### 3.7 Measured surface size

| Signal | Count |
|---|---|
| `src/sase` | 152,462 LOC / 3,999 modules |
| modules matching `legacy\|deprecat` | 693 (17%) |
| pure facade modules (`"""Legacy` docstring) | **60 / 1,936 LOC** |
| inline legacy markers in *non-facade* src modules | 766 |
| `LEGACY_*` constants | 65 (12 encoding an on-disk/wire format) |
| `sase-core` Rust: legacy-marked files / line hits | 93 of 246 / 909 |
| test files importing the facades | **37 / 8,140 LOC** |
| test files *named* `*changespec*` | 44 / 9,783 LOC — **only 4 import the facade** |

Honest middle: ~2,000 LOC of pure dead facade, ~3–5k LOC of live-but-conditional
branches across ~120 modules, ~8k LOC of genuinely facade-bound tests, and ~10k LOC of
canonical tests carrying stale filenames.

---

## 4. Adjudicating the disagreements

### 4.1 Immutable bead history: both reports are wrong, in opposite directions

`__a` devotes a section to arguing that Rust "decodes earlier status, size, type, note,
and event shapes," so dropping those decoders requires a signed, versioned checkpoint
subsystem that materializes current bead state and is verified against a full replay.
`__b` files `__legacy_note__` under Tier E with the generic disposition "write a
forward-migration pass over the sidecar, land the writer, delete the reader."

Measured over the real store (27,881 events across 1,247 stream files):

```
schema_versions: {1: 27881}      # one version. no legacy envelopes.
notes field shapes: {str: 6494, null: 2578}
non-empty string-form notes payloads: 2829
```

- **`__a` is over-scoped.** `BEAD_EVENT_SCHEMA_VERSION` is 1 and every committed event
  is version 1. There is no multi-generation event decoding to checkpoint away. The
  checkpoint subsystem is real engineering work solving a problem the store does not
  have.
- **`__b` is mechanically wrong.** You cannot "forward-migrate the sidecar" for beads:
  `beads/events/**` is append-only and rewriting it violates the audit model that
  `sase bead` depends on. 2,829 events carry non-empty string-form `notes` that only
  `parse_legacy_note_blob` (`sase-core/.../bead/wire.rs:360`) can read, and those bytes
  are permanent.
- **Correct disposition:** the bead residue is *one field decoder*
  (`parse_legacy_note_blob` + `LEGACY_NOTE_ID_PREFIX` + its Python mirrors in
  `bead/note_codec.py` and `bead/_db_codec.py`). Either (a) append a normalization event
  per affected bead so the reducer never needs the blob path for post-cutover replays,
  keeping the decoder only for pre-cutover replay, or (b) accept it as a permanently
  retained history codec, moved into an `archive` module with no writers — which is the
  fallback `__a` itself names and then declines. **Option (b) is recommended:** it is
  ~200 LOC, has no writers, cannot regress current behavior, and buying its removal with
  2,829 synthetic events is a bad trade.

**Related naming trap:** `issues.jsonl` is bound to a Rust variable literally named
`legacy_path` (`bead/read.rs:280`), but core emits `WARNING: issues.jsonl missing` when
it is absent and drift-checks it against the event streams (`read.rs:354`). It is an
actively maintained projection, not backcompat. Deleting on grep evidence would break
`sase bead doctor`.

### 4.2 Test cleanup is mostly a rename

`__b` scopes the test work as "30 files / 12,511 LOC that exist only to hold those
branches in place" and books their deletion as the payoff. Measured:

- 44 test files are named `*changespec*` (9,783 LOC) — **4** import the facades; **46**
  import canonical `sase.ace.patch`. `tests/test_changespec_add_operations.py` opens
  `"""Tests for adding Patches to project files."""` and imports
  `sase.ace.patch.parser`.
- 37 test files fleet-wide import the facades at all (8,140 LOC in those files, not all
  of it facade-bound).

So the real shape is **~37 files to rewrite or delete and ~40 to `git mv` plus fix
docstrings**. That is *more* total churn than `__b` estimated but far less deletion, and
it is a distinct, mechanical, reviewable chunk of work that neither report scheduled.
Budget for `just check-full` as a monitor-only landing gate per
`decisions:two-speed-verification`, and expect Symvision to flag newly-unused symbols —
per `sase/memory/symvision.md`, resolve by deleting, not whitelisting.

### 4.3 `mac` is not idle

`__a` reports "Mac had no matching SASE service process" and builds on it: `mac` becomes
"the lowest-risk final validation host," and the rollout order is Apollo → Athena → Mac
with old writers stopped throughout. Direct check:

```
mac: sase axe start / lumberjack run {hooks,waits,checks,external_mirror}  (5 procs)
```

All three machines are running `axe`. Every machine needs a drain, and no machine is
free. This does not invalidate `__a`'s drain-then-migrate structure — it makes it
mandatory on `mac` too.

Rollout order should be per-phase rather than global. For the **telegram** change, `mac`
is the right canary precisely because it has *no* legacy store; `apollo` goes last
because it is unattended and holds a live writer. For **package rollout** generally,
`apollo` first as an unattended canary (per `__a`) remains sensible.

### 4.4 A production test seam on the Patch load path

Neither report found this. `src/sase/ace/tui/actions/patch/_loading.py`:

```python
def _is_mock(value: object) -> bool:          # :65
    mock_module = sys.modules.get("unittest.mock")   # production code
def _compat_loader(self, legacy_loader, canonical_loader):   # :119
    if getattr(self, "current_tab", None) == "changespecs":  # legacy tab id
        return legacy_loader
    if _is_mock(legacy_loader): return legacy_loader
    ...
```

Production TUI code inspects `sys.modules` for `unittest.mock` to decide whether to call
`changespec_module.find_all_changespecs` or `patch_module.find_all_patches`, because
facade-era tests mock the legacy name. This is test-seam compatibility that has leaked
into the Patch-load hot path, and it is the single strongest concrete argument for the
Tier A deletion. It also explains why §4.2's rename work cannot be purely mechanical:
the ~4 facade-bound tests must be rewritten against canonical names *before*
`_compat_loader`/`_is_mock` can go.

### 4.5 Smaller factual splits

| Claim | `__a` | `__b` | Verified |
|---|---|---|---|
| `.sase` files with `COMMITS:` | 2 | 1 | **2** (`__a`), and one file mixes both spellings |
| Live facade callers | "test seams" | 1 | **4**, two on a hot path |
| `apollo:~/.xprompts/` | present | not mentioned | **present** (2 files) |
| `mac` memory `type: long` | present | not mentioned | **present**, fleet's only consumer |
| Import-leg purge backlog | not mentioned | ~26k/machine | **26,326 / 26,721** |
| Retired skill dirs on remotes | not mentioned | "6+ dirs each" | **17 each; 0 on athena** |
| Flags: 5 total, 3 sunset, none gating legacy | consistent | explicit | **confirmed** |

### 4.6 Root cause: the flag rule is not enforced

`__b`'s governance finding is correct and is the reason this surface exists.
`sase/memory/sase_flags.md` makes a `sunset` flag *mandatory* for backward-compatible
branches, with `remove_by_date`, `remove_by_release`, a typed flag bead, and a
`FlagTriage` gate. `sase flag list` returns 5 flags; the 3 `sunset` ones
(`ace_refresh_tokens`, `admin_center_flags`, `ref_sync_gesture`) all gate *new* rollouts.
**None of the ~685 legacy-marked modules has a flag, a removal bead, or a deadline**, so
none will ever reach `FlagTriage`. The one time SASE retired a compatibility leg properly
— `v1_import_retired` / epic `sase-ws`, recorded in `decisions:agents-sync-publish-only`
— it worked as designed; it was just applied once, by hand, to one subsystem.

Corollary: a one-time deletion pass without an enforcement change buys ~18 months. Tier A
is already the second generation of this pattern (`Commit`→`Stitch`, then
`ChangeSpec`→`Patch`).

---

## 5. Risks

1. **The purge is irreversible.** ~6,500 chat transcripts and ~10,000 artifacts per
   remote machine, with no path back. Tarball
   `~/.sase/{chats,artifacts,dismissed_bundles,agents_sync,projects}` per machine and
   diff the dry-run against the manifest before `--apply`.
2. **`sase-telegram` is the only genuinely blocking dependency**, it writes a live store
   today, and it is a *published wheel* on two machines — the port requires a republish
   plus `sase update` ×3, not just a pull.
3. **Shared-sidecar formats can strand a machine mid-rollout** (Tier E). The two-landing
   rule in §7.4 is the guard, and it is why that tier goes last.
4. **`apollo` has no managed machine overlay** while a live `sase_apollo.yml` exists.
   Reconcile into chezmoi before any config-shape change.
5. **Deleting facades breaks 37 test files and forces ~40 renames** (§4.2). That is the
   point of the work, but it is the bulk of the review burden.
6. **Grep is not evidence.** `issues.jsonl`/`legacy_path` (§4.1), bead type `task` vs the
   retired background-task command, and `COMMITS:` in plan provenance vs Patch specs are
   all live concepts sitting under legacy-looking names. Each parser contract must be
   evaluated, not renamed by search-and-replace. A zero-match grep is a bad acceptance
   criterion; the census in §7.0 is the right one.

---

## 6. Alternatives considered

- **Do nothing.** Rejected: 17% of modules and compounding with each rename;
  `decisions:agents-sync-publish-only` documents the concrete tax (an unrelated ACE test
  broke because a dead producer site still existed).
- **Wrap every legacy branch in a sunset flag and let `FlagTriage` retire them.**
  Rejected as the primary path — it is the by-the-book reading of `sase_flags.md`, but
  ~120 flag beads for branches with a provably empty caller set is ceremony with no
  information content. The flag rule protects a migration window; there is no window
  here. Reserve flags for Tier E, where the window is real.
- **Delete code first, clean machines after.** Rejected. Tier B/C decisions rest on
  claims like "the migration already ran everywhere" — *currently true* for `.gp`,
  *currently false* for the skills prune and the import purge. Verify, then delete.
- **A signed bead-checkpoint subsystem** (`__a`'s recommendation). Rejected on the
  measurement in §4.1: one event schema version, one field decoder. Not worth the
  complexity.
- **One big-bang PR.** Rejected: 5 repos, 37+ test files, and it would put the
  destructive purge in the same blast radius as the code deletion.

---

## 7. Recommended solution

**One epic — `Backcompat Zero` — in six phases.** Phase 0 is not code; it is the
evidence that makes phases 1–5 provably rather than optimistically safe.

### 7.0 Phase 0 — Fleet state sweep (no code changes)

Nothing is deleted from the codebase until this reports clean on all three machines.

1. **Back up** `~/.sase/{chats,artifacts,dismissed_bundles,agents_sync,projects}` to
   durable storage on each machine.
2. **Drain and stop `axe`** on all three (including `mac` — §4.3), so no old writer
   survives in memory across the conversion.
3. **`sase agent names purge-local-state --apply`** per machine, confirmed individually.
   Expect athena 809 identities + caches/journals/receipts, mac 26,326, apollo 26,721.
4. **`sase init skills`** on `mac` and `apollo` to prune the 17 retired
   `sase_artifact`/`sase_beads`/`sase_hg_commit` directories each. Dry-run on one machine
   first to confirm `_discover_legacy_sase_namespace_files` actually removes them.
5. **`athena`-only residue:** `~/.sase/tasks/`, `agent_tags.json`,
   `axe/lumberjacks/checks/external_pr__*.json`, `locks/code-swap.lock`, and the July
   `user_question/` + `plan_approval/` request dirs — each after confirming its canonical
   counterpart is populated and no active agent/notification ID references it.
6. **`apollo`-only residue:** back up and remove `~/.xprompts/` (`sshot.yml`,
   `pick_plan.md`); canonical `~/sase/xprompts/` copies are newer.
7. **`mac`-only residue:** regenerate or retype `~/sase/memory/sase_beads.md`
   (`type: long` → `type: reference`) — it is the fleet's only consumer of the memory
   type alias. Use `/sase_memory_write`; memory files are not ordinary files.
8. **Config:** migrate `*_worker` → `medium`/`small`/`xsmall` in
   `chezmoi:home/dot_config/sase/sase.yml`; `chezmoi apply` ×3; confirm
   `sase doctor -C config.model_aliases` is OK everywhere. Reconcile `sase_apollo.yml`
   into managed chezmoi source.
9. **Land a `check_fleet_legacy_state` doctor check** that reports exact paths, record
   counts, old writers and plugin versions machine-readably, and capture all three
   machines' output. Every deletion PR cites a line from it.

Deliverable: a one-page state table proving every Tier B migration has completed and
every Tier C artifact is gone, fleet-wide.

### 7.1 Phase 1 — Free deletions (Tier A)

Delete the 60 facade modules, the 8 four-line `main/` facades, the 5 CLI aliases and
their `entry.py` dispatch, `LEGACY_APP_KEY_ALIASES` + its migrator + doctor check, the UI
alias maps, and `xprompts/skills/sase_changespecs.md`. Fix the four real callers —
including `_compat_loader`/`_is_mock` on the Patch load path (§4.4), which requires
rewriting the ~4 facade-bound tests against canonical names first. `git mv` the ~40
stale-named canonical test files and fix their docstrings as a **separate commit** from
the deletions, so review stays legible. Redeploy skills ×3 so `/sase_changespecs` stops
loading into every agent turn on 26 provider directories.

### 7.2 Phase 2 — Finished migrations (Tier B) + config code (Tier F)

Delete `project_spec_migration.py`, `prompt_store_migration.py`, `procs/_migration.py`,
`init_memory/root_migration.py`, the `agent_tags.json` fallback,
`_migrate_legacy_pr_mirror_state`, the `code-swap.lock` handoff, the unsharded-fallback
branches in `chat_storage.py` and `dismissed_agents_paths.py`, `include_legacy=True`
defaults in `core/paths.py:304`, the legacy xprompt roots in Rust content discovery, and
the four config key-set constants + schema `"deprecated"` blocks. Each deletion cites the
phase-0 census line proving it is unused. Parallelizable with phase 1.

### 7.3 Phase 3 — Cross-repo couplings (Tier D), plugin-first

1. Port `sase-telegram` to the shared `~/.sase/pending_actions/actions.json`; **publish a
   new wheel**; `sase update` ×3. Canary on `mac` (no legacy store), then `athena`
   (attended), then `apollo` (unattended, live writer) — the reverse of `__a`'s global
   order, for this change specifically.
2. Drain both stores: let existing callbacks resolve or expire for a full 24-hour
   `STALE_THRESHOLD_SECONDS` window, observe zero writes to
   `~/.sase/telegram/pending_actions.json`, then delete it on `athena` and `apollo`.
3. Only then remove the host's `_merge_legacy_telegram` and the `telegram_legacy`
   transport, plus `_LEGACY_AWAITING_KEY`, `_LEGACY_EQUAL_TIMESTAMP_ID`, the
   `bundle.legacy` branch and `_resolve_legacy_bundle`.
4. Remove the guarded `ImportError` fallbacks in `sase-github` and `sase-telegram`
   (non-blocking — they are already dead once phase 1 lands).
5. Remove `.gp` syntax, `.xprompts` schema globs, the legacy completion dispatcher and
   `kind = "changespec"` fixtures from `sase-nvim`. Upgrade the editor plugin *before* the
   runtime rejects old catalogs, or a stale editor keeps generating legacy forms.

### 7.4 Phase 4 — Shared formats (Tier E), two-landing rule

For each of `COMMITS:`/`## ChangeSpec`/`CL:`, plan path prefixes, memory
`type: short|long`, `## Types`, gate schema v2, plan-chain suffix maps, chat-link
timestamps:

> **Landing 1** — write a *parser-aware* forward-migration that rewrites existing records
> to canonical form (the archive `.sase` file mixes both spellings — §3.5). Land it with
> the reader still accepting both. Run it. Commit the rewritten sidecar.
> **Roll** — `sase update` ×3; confirm identical versions.
> **Landing 2** — delete the legacy reader and its constant.

This is the only tier that warrants sunset flags — one per format, `sase flag new <key>
-k sunset`, closed by deleting the Off branch in Landing 2, exactly as `sase_flags.md`
prescribes. It goes last, when the rest of the surface is quiet.

**Explicit exception:** the bead note-blob decoder (§4.1) is *not* migrated. Move
`parse_legacy_note_blob`, `LEGACY_NOTE_ID_PREFIX` and their Python mirrors into an
`archive` module with no writers, documented as a permanent history codec for 2,829
append-only events. Do not rewrite `beads/events/**`.

### 7.5 Phase 5 — Enforcement

1. **`tools/check_backcompat`** wired into `just check`: fail any new
   `legacy`/`deprecated`/`compat` marker on a `src/sase` code path not registered against
   a `sunset` flag. Seed the allowlist from whatever survives phase 4, so it is a
   complete, shrinking debt list rather than permanent amnesty.
2. **A rename policy in memory:** a rename lands as a rename — no shadow package, no
   command alias; or if an alias is genuinely wanted, it ships behind a `sunset` flag with
   a `remove_by` date on day one. This is the specific rule whose absence produced Tier A
   twice.
3. **A `decisions:` record — `backcompat-is-deleted-not-flagged`:** claim (single-user
   fleet at one commit, atomically updated, all machines SSH-reachable ⇒ compatibility
   branches are deleted outright; only cross-machine *format* changes get a sunset flag),
   rejected alternative (flag everything), cost (a mistake means SSH-ing into three
   machines to fix state by hand), reopen condition (SASE gains a user or machine this
   host cannot reach and update). A second record should capture the §4.1 exception:
   append-only stores keep their field decoders rather than rewriting history.

### 7.6 Sequencing

| Phase | Scope | Machine work | Blocks on |
|---|---|---|---|
| 0 Fleet sweep | no code | **all 3, destructive, drain required** | — |
| 1 Free deletions | ~2k src LOC; 37 tests rewritten, ~40 renamed | `sase init skills` ×3 | 0 |
| 2 Finished migrations + config | ~600 src LOC | none (done in 0) | 0 |
| 3 Cross-repo | 4 repos, 1 wheel republish | `sase update` ×3, 24h drain | 1 |
| 4 Shared formats | ~8 formats × 2 landings | `sase update` ×3 per format | 3 |
| 5 Enforcement | lint + memory + 2 decision records | none | 4 |

Phases 1 and 2 are independent and parallelizable. Phase 4 is the long tail and the only
part that should move slowly.

**Acceptance:** every host passes the same versioned census with zero operative findings;
no process writes a retired path during a full observation window; representative legacy
commands, config keys, paths, wire fields and directive syntax fail as unknown rather than
normalizing; the runtime contains no legacy writer, normalizer or migrator; the sole
retained decoder is the documented, writer-free bead note codec; and ordinary resilience
fallbacks plus current task-bead behavior still pass regression tests.

**First action:** `sase agent names purge-local-state --apply` on `mac` and `apollo`,
after a tarball backup. ~26,000 dead files per machine, no code change, already the
documented remedy — and it converts the central assumption of this entire plan from
"probably true" into "measured."

---

## Appendix — reproducing the key evidence

```bash
# Fleet parity, services, and the one real skew
for h in mac apollo; do ssh $h '~/.local/bin/sase version'; done; sase version
for h in mac apollo; do ssh $h 'ps -eo pid,command | grep -E "sase (ace|axe)" | grep -v grep'; done

# Bead event store: one schema version, 2829 legacy note blobs  (§4.1)
find ~/projects/github/sase-org/sase/sase/repos/beads/events -name '*.jsonl' -print0 \
  | xargs -0 cat | python3 -c "
import sys,json,collections
v=collections.Counter(); n=0
for L in sys.stdin:
    e=json.loads(L); v[e['schema_version']]+=1
    iss=(e.get('payload') or {}).get('issue') or {}
    if isinstance(iss.get('notes'),str) and iss['notes'].strip(): n+=1
print(v, 'legacy-blob payloads:', n)"

# Tests: named for changespec vs actually bound to the facade  (§4.2)
find tests -name '*changespec*.py' -not -path '*__pycache__*' | wc -l          # 44
find tests -name '*changespec*.py' -not -path '*__pycache__*' \
  | xargs grep -l 'sase\.ace\.changespec\|sase\.core\.changespec' | wc -l      # 4

# The production test seam  (§4.4)
sed -n '60,131p' src/sase/ace/tui/actions/patch/_loading.py

# Import-leg backlog  (§3.3)
for h in mac apollo; do ssh $h '~/.local/bin/sase agent names purge-local-state \
  | grep -oE "Would remove [a-z]+ ?[a-z]*" | sort | uniq -c'; done

# Live legacy telegram store  (§3.4)
for h in mac apollo; do ssh $h 'ls -l ~/.sase/telegram/pending_actions.json'; done

# Per-machine drift  (§2)
for h in mac apollo; do ssh $h 'find ~ -maxdepth 6 -type d \
  \( -name sase_artifact -o -name sase_beads -o -name sase_hg_commit \) | wc -l'; done
ssh mac 'grep -n "^type:" ~/sase/memory/sase_beads.md'
ssh apollo 'ls ~/.xprompts/'
grep -rln '^COMMITS:' ~/.sase/projects/*/*.sase                  # 2 files on athena

# Governance  (§4.6)
sase flag list                     # 5 flags, 3 sunset, all gating new rollouts
sase config layers | grep -i deprecat   # empty on all three
sase doctor -C config.model_aliases     # WARN: 3 retired *_worker aliases
```
