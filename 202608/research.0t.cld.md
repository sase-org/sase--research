---
create_time: 2026-08-21
updated_time: 2026-08-21
status: research
---

# Remaining SASE Feature Flags: Close-Out Research

**Question:** What still has to happen to delete every open SASE feature flag except
`artifact_links` and `pluggable_finalizers`, which already have agents on them?

**Scope:** SASE at `4ebdd05ad` (v0.16.0 + 1203), 2026-08-21. Registry, flag beads,
call sites, both-states tests, durable config, this ACE process's env snapshot, and
the live `epic_resume` chop. No runtime behavior was changed.

## Bottom line

There are **nine** live flags. Two are already being retired (`artifact_links` /
`sase-rc` under `099--plan`; `pluggable_finalizers` / `sase-ro` under epic `sase-rr`).
The other seven are all `open`, all `live` (~85–88 days from `FlagTriage`), and all
due `0.18.0`. **Do not wait for the gate.** Flag beads stay `open` (they never go
`ready`) and `sase bead work <id>` can launch a removal worker today.

Durable config has **no** `feature_flags:` overrides. `sase flag list` inside an
agent marks every key `ENV:SASE_FEATURE_FLAGS` / `overridden: yes` even at default;
that is the known env-snapshot provenance bug, not a real opt-in. This ACE process
(`pid` launched as `sase ace --restart-axe`) actually forces three betas on:
`artifact_links`, `pluggable_finalizers`, and `completion_refresh_on_update`. That
soak dies with the ACE process unless it is written to `~/.config/sase/sase.yml`.

Playbook already exists: `29c537206` (ConfigHub) and `4119b0d8d` (Launch) deleted the
Off branch, dropped the registry member, synced the schema, updated tests/docs, and
closed the flag bead in the same change.

**Recommended dispositions** (details in the next-steps list):

| Priority | Flag | Kind | Durable | Disposition |
| --- | --- | --- | --- | --- |
| 1 | `plugin_catalog_scoped_latest` | beta | off | **Remove now** (`enabled` wins) |
| 2 | `prettier_enabled` | sunset | on | **Remove now** (migrate test harnesses off `SASE_DISABLE_PRETTIER`) |
| 3 | `commit_finalizer_shared_clone_exempt` | sunset | on | **Remove now** unless a false race is already known |
| 4 | `completion_refresh_on_update` | beta | off* | **Remove now** (On is non-fatal; already on in this ACE) |
| 5 | `ref_sync_gesture` | sunset | on | **Remove now** if `@kind::` has not eaten a real colon; else Extend to 0.18.0 |
| 6 | `epic_resume_gate` | beta | off | **Enable, soak, then Remove** — chop is a 5-minute `flag_disabled` no-op |
| 7 | `coder_inherits_planner_chat` | beta | off | **Keep as config**, or Remove with `winner=disabled` |

\*On in this ACE env only.

## How removal actually works

One rule, with one gate-shaped nuance:

- Memory/docs: **Remove deletes Off and makes On unconditional.**
- The `FlagTriage` form also collects a required `winner` of `enabled` or `disabled`,
  and the worker brief is "the `{winner}` branch wins: delete the losing branch."

Use `winner=enabled` for every flag whose On branch is the product. The one exception
is `coder_inherits_planner_chat`, whose documented default is Off (plan file is the
hand-off; On *restores* old `#fork`). Picking `winner=enabled` there would resurrect
the old behavior as the only path.

Each Remove change, matching the ConfigHub/Launch retirements:

1. Delete the `FeatureFlag` member and registry definition.
2. Run `tools/sync_feature_flags_schema --write`.
3. Delete the Off branch at the call site(s) and drop `override_flags(...)` both-states
   tests; keep the On path as ordinary tests.
4. Update `tests/feature_flags/test_consumers.py` (it enumerates live keys).
5. Strip the flag from docs (`docs/configuration.md`, plus the per-flag pages below).
6. Close the flag bead in the **same** change. Closing it while the definition
   survives is an integrity error.

`Keep` is the other honest close-out: convert to a normal config field, then close
the bead. Use it only when users should choose the value forever.

## Already in flight (do not duplicate)

- **`artifact_links`** (`sase-rc`, beta, ACE-on): store, `sase artifact read` / `link`,
  prompt `cites`, Links tables. Agent `099--plan` is end-to-end reviewing it.
- **`pluggable_finalizers`** (`sase-ro`, beta, ACE-on): epic `sase-rr` ("Retire the
  pluggable finalizers beta and legacy controller"); `sase-rr.1` is running, later
  phases are waiting.

A Flags sub-tab on Admin Center Config is also landing (`sase-ri.land.w2.f2.f2`). That
is UI for flipping flags, not a prerequisite for deleting them.

## The seven remaining flags

### `plugin_catalog_scoped_latest` — `sase-qq` · beta · default off

**On:** eager PyPI latest is O(installed); Updates > Plugins lazily fetches the
highlighted uninstalled row; `sase plugin show` still fetches one; `sase plugin list`
needs `-A|--all-latest` for a full probe.

**Off:** every catalog entry is eagerly probed (the pre-scale network storm).

**Evidence it is done:** both-states tests in `tests/test_plugin_latest.py` and
`tests/ace/tui/test_plugins_browser_pane_detail.py`; CI job
`just plugin-catalog-scale-check` pins `fetch_calls = installed_count` at n=1000 and
n=2000. Epic `sase-qn`'s land note already recorded the decision: kind cannot be
flipped to sunset in place (`kind_mismatch`), and FlagTriage Remove *is* default-on
scoped enrichment. The default remaining Off is leftover, not a soak.

**Call sites:** `src/sase/plugins/latest.py`,
`src/sase/ace/tui/modals/plugins_browser_latest.py`.

This machine's installed catalog is only four plugins, so Off is not painful here.
The CI floor is the reason to delete Off anyway.

### `prettier_enabled` — `sase-qf` · sunset · default on

**On:** markdown is prettier-formatted when prettier is installed (it is, v3.8.1).

**Off:** skip prettier. `SASE_DISABLE_PRETTIER` is the inverted legacy alias
(`src/sase/feature_flags/env.py`).

**User soak:** no `SASE_DISABLE_PRETTIER` in user config or shell env. The escape
hatch is unused outside tests.

**Test soak (this is the real work):** visual snapshots
(`tests/ace/tui/visual/conftest.py`), the fakey harness, and several prompt-editing
tests export `SASE_DISABLE_PRETTIER=1` so rendering does not depend on PATH. Before
the flag dies those must mock `shutil.which("prettier")` (or equivalent) instead.
`format_with_prettier` already no-ops when prettier is missing, so the product Off
branch is not needed once tests stop using the env alias.

Do not Keep this as config. "Skip prettier" is test scaffolding, not a user setting.

### `commit_finalizer_shared_clone_exempt` — `sase-qi` · sunset · default on

**On:** in machine-wide shared clones (`sdd` / opened-external), foreign-agent
commits and already-published / pending-publication HEAD moves are races, not
discards.

**Off:** `_legacy_published_store_state_is_exempt` — only `kind=="sdd"` and
ahead==0; a foreign footer is never enough. Workspace (`main` / `sibling`) clones
are never exempt in either branch.

The helper **fails open to On** on resolver errors. Both-states tests live in
`tests/llm_provider/test_commit_finalizer_sdd_publication_exempt.py` and
`test_commit_finalizer_hidden_agents_sidecar.py`. Docs:
`docs/commit_workflows.md`.

Remove unless a real discard has already been mislabeled as a race. Deleting Off
means deleting `_legacy_published_store_state_is_exempt` and the flag helper.

### `completion_refresh_on_update` — `sase-qg` · beta · default off

**On:** after a successful `sase update`, regenerate / `zcompile` / restamp installed
scripts. Failures are reported and **never fail the update**. Chezmoi-owned stamps
are skipped (the On branch is a no-op on those files).

**Off:** scripts refresh only via `sase completion install`.

This ACE session already has the flag on; `~/.zfunc/_sase` and `_sase.zwc` were
rewritten 2026-08-21 07:15. Durable yaml still has it off, so a clean ACE restart
drops the soak.

`sase-ow` (measure fish latency) and `sase-oy` (chezmoi-deploy completions) are
adjacent, not blockers. Docs: `docs/completion.md`. Call site:
`src/sase/completion/install.py`. Tests already cover both states.

Safe to Remove: the Off branch exists only to avoid rewriting files during an
unrelated command, and the On path is explicitly non-fatal.

### `ref_sync_gesture` — `sase-qu` · sunset · default on

**On:** in insert mode, a second `:` at an empty `@<kind>:` payload is consumed,
syncs that kind's sidecar (clone / force-pull past TTL / rescan), and reopens the
menu with `[✦]` badges. Guards: insert mode, empty payload, known kind, prompt
mode. Repeating while a sync runs is a no-op. `@file:default:` still inserts a
literal colon.

**Off:** the second colon is literal; no sync.

Shipped 2026-08-19 (`12df170f9`); bead `remove_when` asks for **two minor releases**
with no "colon eaten" report. That gate is 0.17 + 0.18, not calendar age. The plan
file `plan:202608/ref_sync_gesture.md` is still `wip` even though the code landed.
Call site: `src/sase/ace/tui/widgets/_artifact_ref_sync.py`. Both-states tests:
`tests/ace/tui/widgets/test_artifact_ref_sync_trigger.py`.

If `@kind::` has been used without misfires, early Remove is reasonable — the
guards make accidental consumption hard. If that soak has not happened, Extend to
`0.18.0` rather than inventing a config field. This is not a forever preference.

### `epic_resume_gate` — `sase-qh` · beta · default off

**On:** the `epic_resume` chop raises one `EpicResume` gate per stalled epic
(failed member, no live member, failure older than
`bead.epic_resume.settle_seconds`, default 120s). Resume runs
`sase bead work <epic-id> --yes-to-all`.

**Off:** no gate; recovery is manual `sase bead work`.

Verified soak: the chop runs every five minutes and every recent tick is
`status=no_op reason=flag_disabled` (gated=0, stalled=0, epics=0). The On branch
has **never** run on this machine. Tests cover the disabled early-return
(`tests/test_axe_chop_epic_resume.py`) and the gate shape
(`tests/test_epic_resume_gate.py`), not production false-positive rate.

Do not Remove until the flag is on in the axe process (user config or
`sase -f epic_resume_gate ace --restart-axe`) and at least one real stall has
gated without firing on a handoff race. Then Remove with `winner=enabled`. This
is product behavior, not a forever setting — do not Keep it as config.

### `coder_inherits_planner_chat` — `sase-qe` · beta · default off

**On:** after plan approval, prepend `#fork:<planner>--plan` so the coder inherits
the planner chat **in addition to** the plan file.

**Off (today's default):** the coder starts from `@plan` only.

Docs (`docs/xprompt.md`) call On "restore the old behavior." Tests default-assert
`#fork:` is absent (`test_coder_prompt_excludes_resume_prefix_by_default`). The
bead's `remove_when` is written as if On should win after soak. Those two stories
disagree, and On has never been durably enabled.

This is the only remaining flag that may be a **forever choice** (context cost vs
plan fidelity). Two honest close-outs:

1. **Keep** — add something like `plan.coder_inherits_planner_chat` (default
   `false`) and delete the flag. Users who want `#fork` keep a setting.
2. **Remove with `winner=disabled`** — plan-file-only becomes the only path;
   delete the `#fork` prefix. Correct if the new default already won.

Do **not** Remove with `winner=enabled` without first soaking forked coders on
real epics. That would silently undo the documented hand-off design.

## Shared next-step recipe

For every Remove (waves 1–5 below):

```text
sase bead work <flag-bead-id>          # open flag beads are launchable
# in the worker:
#   delete Off branch + registry member
#   tools/sync_feature_flags_schema --write
#   update tests/feature_flags/test_consumers.py and both-states tests
#   strip docs
#   sase bead close <id> --note "..."
just check
```

Do not batch unrelated flags into one change. Do not wait for `FlagTriage`.

---

## Next steps by flag

### `plugin_catalog_scoped_latest` (`sase-qq`) — do first

1. Launch `sase bead work sase-qq`.
2. Delete Off (`scope="all"` eager path). Make `_resolve_eager_scope` always
   `"installed"` when unset; keep `-A|--all-latest` and `sase plugin show`'s
   single-entry fetch.
3. Drop `override_flags(plugin_catalog_scoped_latest=...)` tests; keep the scale
   floor.
4. Update `docs/plugins.md` (remove the "flag on" qualifier).
5. Close `sase-qq` in that change.

### `prettier_enabled` (`sase-qf`)

1. Rewrite visual/fakey/prompt tests that set `SASE_DISABLE_PRETTIER` to mock
   `shutil.which("prettier")` instead. Confirm `just test-visual` still matches
   goldens.
2. Launch `sase bead work sase-qf`.
3. Delete `_prettier_is_enabled`, the flag, and the `_LEGACY_ENV_MAPPINGS` entry.
   Keep "prettier missing or failed → return original text."
4. Drop doctor/CLI coverage of `SASE_DISABLE_PRETTIER`.
5. Close `sase-qf`.

### `commit_finalizer_shared_clone_exempt` (`sase-qi`)

1. Confirm no real discard was misreported as a shared-clone race (finalizer
   logs / any `missing_agent_provenance` false positive). If one exists, stop and
   Extend instead.
2. Launch `sase bead work sase-qi`.
3. Delete `_legacy_published_store_state_is_exempt` and
   `_shared_clone_exemption_enabled`; keep the On classifier.
4. Update `docs/commit_workflows.md`.
5. Close `sase-qi`.

### `completion_refresh_on_update` (`sase-qg`)

1. Optional but cheap: persist `feature_flags.completion_refresh_on_update: true`
   in user config so the soak survives ACE restart, then run one `sase update`.
2. Launch `sase bead work sase-qg`.
3. Make `maybe_refresh_installed_completions` unconditional (still skip
   chezmoi-owned stamps; still non-fatal).
4. Update `docs/completion.md` and `docs/plugins.md`.
5. Close `sase-qg`. Leave `sase-ow` / `sase-oy` alone.

### `ref_sync_gesture` (`sase-qu`)

1. Decide from actual use: has `@<kind>::` consumed a colon the user meant to
   type? If yes, file that and Extend. If no (or unused but the guards look
   sufficient), Remove.
2. Launch `sase bead work sase-qu`.
3. Delete the `if not current_flags().enabled(...)` early-return; keep the
   insert-mode / empty-payload / known-kind guards.
4. Update `docs/ace.md` and `docs/artifact_references.md`; mark
   `plan:202608/ref_sync_gesture.md` done if the code is accepted as shipped.
5. Close `sase-qu`.

### `epic_resume_gate` (`sase-qh`) — soak first, then Remove

1. Enable durably: `feature_flags.epic_resume_gate: true` in user config (axe
   must see it; a one-shot `sase -f epic_resume_gate axe chop run epic_resume`
   is not a soak).
2. Restart axe so the five-minute chop leaves `reason=flag_disabled`.
3. Wait for one real stalled epic to raise `EpicResume`. If it fires on a
   handoff race, raise `bead.epic_resume.settle_seconds` and keep soaking.
4. After a true-positive resume and no false gates, `sase bead work sase-qh`,
   delete the flag check, update `docs/axe.md` / `docs/configuration.md` /
   `docs/notifications.md` / the chop description in `default_config.yml`.
5. Close `sase-qh`.

### `coder_inherits_planner_chat` (`sase-qe`) — product decision, then close

Pick one:

- **Keep (recommended if `#fork` should remain available):** convert to a
  config field defaulting off (`plan.coder_inherits_planner_chat` or similar),
  wire `run_agent_exec_plan_accept.py` to that field, delete the flag, close
  `sase-qe`. This is FlagTriage's Keep worker.
- **Remove with `winner=disabled`:** delete the `#fork` prefix; plan-file-only
  is the only hand-off. Close `sase-qe`.
- **Do not** Remove with `winner=enabled` unless forked follow-up coders have
  actually landed several epics. That soak has not started.

### Explicitly out of scope

- `artifact_links` / `sase-rc` — `099--plan`
- `pluggable_finalizers` / `sase-ro` — epic `sase-rr`
- `sase-o2` (pinned `SASE_FEATURE_FLAGS` vs `scope: project`) and `sase-o3`
  (FlagTriage call-site preview) — flag infrastructure, not a live flag
