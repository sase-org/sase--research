# Closing the Remaining SASE Feature Flags

**Scope:** live SASE flags on 2026-08-21, excluding `artifact_links` and
`pluggable_finalizers`, which already have owners. The registry is healthy and contains
nine open flags; the seven below are all still `live`, with removal thresholds around
November 2026 / v0.18.0. Those thresholds schedule triage, not the earliest safe removal.

## Executive recommendation

Start removal work now for `prettier_enabled` and
`plugin_catalog_scoped_latest`. Give `commit_finalizer_shared_clone_exempt` a short,
observable production audit first. The remaining four need explicit soak evidence or a
product decision before their flag can honestly disappear.

| Flag | Default | Recommended disposition | What remains |
| --- | --- | --- | --- |
| `prettier_enabled` (`sase-qf`) | On (sunset) | Remove now | Migrate tests off `SASE_DISABLE_PRETTIER`; keep graceful fallback when prettier is absent or fails. |
| `plugin_catalog_scoped_latest` (`sase-qq`) | Off (beta) | Smoke, then remove with On winning | Verify online/offline CLI and Config Center behavior; the scoped path already has both-state and catalog-scale coverage. |
| `commit_finalizer_shared_clone_exempt` (`sase-qi`) | On (sunset) | Short audited soak, then remove | Confirm real shared-clone exemptions are races rather than discarded work; add structured evidence if current logs cannot answer that. |
| `completion_refresh_on_update` (`sase-qg`) | Off (beta) | Soak unmanaged installs, then remove with On winning | Several real updates must refresh bash/fish/zsh successfully. This ACE's override is weak evidence because chezmoi-owned stamps are skipped. |
| `epic_resume_gate` (`sase-qh`) | Off (beta) | Enable and soak, then remove with On winning | Exercise a true stalled epic and normal handoff/retry races; verify the settle window prevents false gates. |
| `coder_inherits_planner_chat` (`sase-qe`) | Off (beta) | Decide after a measured trial | Compare plan fidelity and token/context cost. If value varies by user, convert to config; otherwise keep only the winning path. |
| `ref_sync_gesture` (`sase-qu`) | On (sunset) | Keep through v0.17; reassess for v0.18 | It shipped only on 2026-08-19 and its bead requires two minor releases without accidental-colon reports. |

## Why these dispositions

`prettier_enabled` is a mature default with one production guard. No current user or
durable configuration needs the legacy escape hatch; the remaining consumers are test
fixtures that use `SASE_DISABLE_PRETTIER` for deterministic rendering. Removing the flag
should not remove the existing no-op behavior when prettier is unavailable.

`plugin_catalog_scoped_latest` fixes the old O(catalog) eager PyPI probing behavior. Its
enabled path limits eager work to installed plugins and lazily fetches the highlighted
uninstalled entry; CI already holds fetch count constant as catalog size grows. A bounded
online/offline smoke pass is more useful than prolonged default-off soak.

For `commit_finalizer_shared_clone_exempt`, unit coverage is strong but neither draft
found durable production evidence of genuine exemption events. Because misclassification
could hide discarded work, retire it only after several events are attributable from git
provenance. Rebase this work after the ongoing finalizer changes.

The two reports disagreed most on `completion_refresh_on_update`: one recommended
immediate removal because failures are nonfatal; the other observed that current files
are chezmoi-owned and therefore skipped. The bead's actual criterion requires several
successful updates on every supported shell, so enabled-in-process is not enough. A
disposable home with unmanaged stamped completions closes the evidence gap cheaply.

`epic_resume_gate` likewise has extensive tests but no operational soak: while disabled,
the periodic chop exits with `reason=flag_disabled`. Its acceptance criterion is about
real stalls and false positives during fast retry/handoff races, so those must be
observed before promotion.

`coder_inherits_planner_chat` is the only flag whose On path may be a permanent user
preference rather than a universal successor. The documented default is plan-file-only;
On restores `#fork` and adds planner context. Trial several comparable epics and record
token cost plus plan-fidelity outcomes. Then either promote On, delete the experiment
with Off winning, or use FlagTriage's Keep path to replace the flag with a normal config
field. Do not silently make On unconditional without that decision.

`ref_sync_gesture` has focused safeguards and tests, but its authored removal gate is
release-based. Treat v0.16 and v0.17 as the two-release observation window, monitor
accidental `@kind::` colon consumption and typing-path stalls, and target retirement in
the v0.18 work if clean.

## Shared removal mechanics

For each retired flag, make the winning behavior unconditional, delete the losing
branch and registry member, run `tools/sync_feature_flags_schema --write`, update the
consumer inventory/tests/docs, and close the dedicated flag bead in the same change.
Keep removals separate and rebase/serialize registry and schema edits with the two
already-running workers.

## Next steps by flag

1. **`prettier_enabled` / `sase-qf`:** Replace test-only
   `SASE_DISABLE_PRETTIER` exports with explicit prettier availability mocks; run visual
   coverage; delete the legacy env mapping and flag guard; retain missing/failing
   prettier fallback; sync schema and close.
2. **`plugin_catalog_scoped_latest` / `sase-qq`:** Run online/offline `plugin
   list/show` and Config Center smoke tests plus the scale check; make installed-only
   eager lookup and highlighted-row lazy lookup unconditional; delete full-catalog
   eager probing; sync schema and close.
3. **`commit_finalizer_shared_clone_exempt` / `sase-qi`:** Capture and audit several
   real shared-clone exemption events, instrumenting a durable counter/event if needed;
   if clean, rebase after finalizer work, delete the strict fallback/helpers while
   retaining main/sibling fail-closed coverage, and close. Extend if any real discard
   is masked.
4. **`completion_refresh_on_update` / `sase-qg`:** In a disposable home, install
   unmanaged bash/fish/zsh completions and run several real version updates; verify
   regeneration, zcompile/restamping, idempotence, stale replacement, and nonfatal
   per-shell failures; then remove the guard while retaining chezmoi skips and failure
   isolation, and close.
5. **`epic_resume_gate` / `sase-qh`:** Enable it durably for Axe, restart Axe, induce
   one controlled stall and observe natural failures/retries; verify one gate per failed
   generation, recovery cancellation, and no handoff-race gate; remove the disabled
   early return and beta docs, then close.
6. **`coder_inherits_planner_chat` / `sase-qe`:** Run several forked coder handoffs
   and compare context/tokens and plan fidelity. Choose one outcome: unconditional On,
   plan-file-only Off, or a permanent default-off config field; delete the feature flag
   and close its bead with that decision recorded.
7. **`ref_sync_gesture` / `sase-qu`:** Leave On through v0.17 and monitor colon
   consumption and TUI stalls; at v0.18, if clean, delete the trigger flag guard,
   disabled-state test, and fallback prose, then close; otherwise extend with the
   concrete failure evidence.
