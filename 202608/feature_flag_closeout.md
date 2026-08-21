---
create_time: 2026-08-21
updated_time: 2026-08-21
status: research
tags: [feature-flags, deprecations, rollout, closeout]
---

# SASE Feature-Flag Closeout

**Question:** What remains before every open SASE feature flag can be removed, excluding
`artifact_links` and `pluggable_finalizers`, which already have owners?

**Snapshot:** `sase` `4ebdd05ad`, version `0.16.0`, on 2026-08-21. `sase flag list`
reports nine healthy open flags and no diagnostics. All removal beads are still `live`
(not due): their dates are 2026-11-14 through 2026-11-18 and their release threshold is
`0.18.0`. Those thresholds control when FlagTriage asks; they do not prevent an earlier,
evidence-backed removal.

## Bottom line

| Flag                                   | Default / effective in this run | Recommendation                               | Main blocker                                                                                           |
| -------------------------------------- | ------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `prettier_enabled`                     | on / on                         | Remove now                                   | Replace test-only uses of the deprecated env escape hatch.                                             |
| `plugin_catalog_scoped_latest`         | off / off                       | Remove after one smoke pass                  | The good path is implemented and scale-guarded but has not been the default.                           |
| `commit_finalizer_shared_clone_exempt` | on / on                         | Short soak, then remove                      | No genuine persisted log hit was found to audit for false-positive race classification.                |
| `completion_refresh_on_update`         | off / on                        | Exercise an unmanaged install, then remove   | This host's bash/fish/zsh stamps are chezmoi-owned, so the enabled path skips regeneration.            |
| `coder_inherits_planner_chat`          | off / off                       | Run a measured trial; then promote or delete | No rollout evidence yet, and context cost is an inherent tradeoff.                                     |
| `epic_resume_gate`                     | off / off                       | Enable for a controlled soak, then remove    | The real-stall/false-positive removal criterion has not been exercised.                                |
| `ref_sync_gesture`                     | on / on                         | Keep through 0.17; remove for 0.18           | It shipped on 2026-08-19 and explicitly requires two minor releases without colon-consumption reports. |

For every successful removal, the mechanical finish is the same: delete the Off branch,
make the On branch unconditional, remove the enum/registry/schema entry, update tests
and docs, run `tools/sync_feature_flags_schema --write`, verify, and close the dedicated
flag bead in the same change. Since every removal touches the registry and generated
schema, serialize or rebase these changes after the two already-running flag workers
land. `commit_finalizer_shared_clone_exempt` also overlaps the finalizer area and should
be rebased after the `pluggable_finalizers` work.

## Practical findings

### Ready with limited cleanup

`prettier_enabled` (`sase-qf`, sunset, medium) is already the default and effective
behavior. Neither the current environment nor the audited chezmoi checkout exports
`SASE_DISABLE_PRETTIER`; its remaining production support is the legacy mapping in
`src/sase/feature_flags/env.py` and the guard in `src/sase/file_references.py:517`. The
real cleanup is test infrastructure: 15 test files still mention the alias, including
visual/fakey determinism fixtures. Replace those with explicit mocking or a controlled
PATH, delete the legacy-env diagnostics/tests, and keep the existing "prettier missing
or failed" graceful fallback. This is safe to start now.

`plugin_catalog_scoped_latest` (`sase-qq`, beta, small) should also move directly to On.
The Off path in `src/sase/plugins/latest.py:318` eagerly probes every catalog entry; the
On path probes installed plugins only and lazily fetches the highlighted uninstalled row
off-thread (`src/sase/ace/tui/modals/plugins_browser_latest.py:40`). Its bead already
records the important fact: the scale check fixes fetches at the installed count (5 for
catalogs of both 1,000 and 2,000 entries) and enforces linear scan work in CI. A brief
online/offline Config Center and `sase plugin list/show` smoke pass is enough remaining
evidence; then delete the full-eager branch and the lazy-fetch flag guard.

### Needs real use before promotion

`commit_finalizer_shared_clone_exempt` (`sase-qi`, sunset, medium) makes the bug fix in
`src/sase/llm_provider/commit_finalizer_git_progress.py:219` the default. It exempts
machine-wide SDD/external clones when HEAD moves through a foreign-agent commit or an
already/pending-published transition; the Off branch restores strict single-owner
classification. Unit tests cover both states and keep main/sibling repos strict, but a
search of persisted SASE logs found no genuine warning from this exemption since it was
added on 2026-08-18. Let normal concurrent-agent traffic produce several warnings, audit
each against git provenance, then delete `_legacy_published_store_state_is_exempt` and
`_shared_clone_exemption_enabled`. If warnings are not durably retained, first add a
small structured counter/event so the stated removal criterion can actually be judged.

`completion_refresh_on_update` (`sase-qg`, beta, small) is effectively enabled in this
run, but `sase completion list --json` shows all three installed scripts are owned by
chezmoi. `_refresh_stamped_completions` deliberately skips those, so this machine is not
soaking regeneration, zcompile, or restamping. Test one real version transition in a
disposable home with unmanaged bash, fish, and zsh stamps; verify idempotence,
stale-file replacement, zcompile freshness, and that one-shell failure remains nonfatal.
Then make `maybe_refresh_installed_completions` unconditional and remove only the
disabled-state tests; retain the per-shell failure handling and chezmoi skip.

`coder_inherits_planner_chat` (`sase-qe`, beta, medium) has one narrow call site at
`src/sase/axe/run_agent_exec_plan_accept.py:405`: On prepends `#fork:<planner>`, while
Off hands the approved plan file to a clean coder. The current environment and chezmoi
config do not opt in, and recent archived coder handoffs remain plan-file-only, so the
bead's "several epics" criterion is unmet. Run a small sample of comparable epics with
On, record inherited context/tokens and any plan-fidelity difference, then make a
product decision. If inheritance is consistently worth its cost, promote On; if cost
depends on the user/workload, convert it to a permanent config field; if it adds no
value, delete the On path instead of institutionalizing extra context.

`epic_resume_gate` (`sase-qh`, beta, small) returns immediately with
`reason=flag_disabled` at `src/sase/scripts/sase_chop_epic_resume.py:404` in the current
configuration. The detector/gate implementation is extensive and well unit-tested, but
the removal criterion is specifically operational: real failed phase agents must gate
without false positives during handoff races or fast retries at the 120-second settle
window. Enable it in the long-running Axe process, induce at least one controlled
stalled epic, and observe several natural failures. Verify one gate per failed-member
generation, cancellation on recovery, and no gate for quick retry/handoff. Then delete
the early return and update the two default-config comments that still call it
beta/opt-in.

### Intentionally release-gated

`ref_sync_gesture` (`sase-qu`, sunset, small) is already unconditional-on by default,
has focused trigger/flow/panel/domain tests, and runs the actual sync as a tracked proc.
The only Off branch is the trigger guard at
`src/sase/ace/tui/widgets/_artifact_ref_sync.py:110`, plus the disabled-state test and
docs describing the fallback. It landed on 2026-08-19, so its explicit "two minor
releases" criterion cannot yet be true. Keep it enabled through 0.16 and 0.17; watch
user reports and TUI stall logs for accidental colon consumption or typing-path stalls.
If clean, remove the guard/fallback prose and close it with the 0.18 work.

## Next steps by flag

1. **`prettier_enabled` / `sase-qf`:** Replace test-only `SASE_DISABLE_PRETTIER` usage,
   delete the legacy env mapping and runtime guard, sync the schema, verify formatting
   fallbacks, and close the bead.
2. **`plugin_catalog_scoped_latest` / `sase-qq`:** Run one online/offline CLI + Config
   Center smoke pass and the scale regression check; make installed-only eager lookup
   and highlighted-row lazy lookup unconditional; delete the full-eager branch; close.
3. **`commit_finalizer_shared_clone_exempt` / `sase-qi`:** Collect and audit several
   real shared-clone exemption events (adding durable telemetry first if necessary),
   rebase on the finalizer work, delete the strict fallback/helpers, retain main/sibling
   fail-closed tests, and close.
4. **`completion_refresh_on_update` / `sase-qg`:** Soak an unmanaged bash/fish/zsh
   install through a real version transition in a disposable home; then remove the flag
   check, retain failure isolation and chezmoi skips, and close.
5. **`coder_inherits_planner_chat` / `sase-qe`:** Trial several forked coder handoffs,
   measure tokens/context and plan fidelity, then choose unconditional On, permanent
   config, or deletion of the experiment; remove the flag and close accordingly.
6. **`epic_resume_gate` / `sase-qh`:** Enable it in Axe, exercise a controlled stall and
   natural failures, verify the 120-second race filter and gate lifecycle, remove the
   early-return guard and beta docs, and close.
7. **`ref_sync_gesture` / `sase-qu`:** Leave enabled through two minor releases, monitor
   colon-consumption reports and TUI stalls, then remove the trigger guard/Off-state
   test and fallback docs for 0.18 and close.
