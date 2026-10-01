# Why master CI is red, and how to keep it green

- **Researcher:** grk (`research.34.grk`)
- **Date:** 2026-10-01
- **Question:** Why is `master` failing in CI? What fixes it, and what stops this from recurring?
- **HEAD at research time:** `781063e38e` (`origin/master`)
- **Primary signal:** GitHub Actions workflow **Master Gate** (`.github/workflows/master-gate.yml`)

## Recommended solution

Stop landing product on a red tip. Ship **one repair-only stitch** that closes the already-tracked Master Gate beads below, watch **one SHA** go green, then keep `sase-1c1.13` as the only lander until Master Gate stays green.

Do that work in this order. Each item is a known, deterministic break; together they explain every lint failure and all but one of the current test failures.

| Priority | Bead | Change | Why it is first |
| --- | --- | --- | --- |
| 1 | `sase-1dn` | Privatize `HandoffSubmitResult`, `StarterResolution`, `owner_ref` (file-local; tests already import the public names) | Unblocks the **lint** job. Master Gate cannot go green while `just lint` dies in symvision. |
| 2 | `sase-1dh` | Update `tests/ace/tui/widgets/test_agent_header_panel.py` re-exports: drop `test_hint_document_forces_expansion`, add the two `test_hint_mode_*` names | Stops an `ImportError` at collection that poisons `pytest -m contract --collect-only`. |
| 3 | `sase-1cm` | Teach launch fakes `history_text` (better: `**kwargs`) | Restores `test_partial_launch_cleanup`, both `test_force_reuse_launch_seam_rejection` nodes, and the same call-shape family. |
| 4 | `sase-1de` | Review `quarantine_local_object` in the artifact-directory audit; update the repositories schema test for the attachments-private wording | Two whole-repo contract tests red since bead-attachments GA. |
| 5 | `sase-1dr` leftovers | Caption `memory/history:at`; refresh memory help + JSON-id fixtures for `blob_oid` / `included_blob_oids`; expect 4 index updates in the home-mode started-at test; refresh the contract manifest | The in-progress memory-history epic landed CLI and event-shape changes without the matching pins. |
| 6 | Help pin | Assert `--images` (or the choices form), not the contiguous substring `-i, --images` | `sase bead show` still defines `-i/--images`; argparse 3.12 prints `-i {auto,cells,kitty,never}, --images {…}`. |
| 7 | HEAD-only | Repair `test_midword_peek_reveals_then_finishes_word` after `781063e38e` split `prompt_prediction_wire` | New on this SHA. `_next_word_peek_pending()` is false after typing `e`. |

Re-run `test_beads_sync_reports_visible_and_missing` in isolation on HEAD. It expects `LinkRequestState.MISSING` and got `PENDING`. It did not fail on the previous SHA, so treat it as load-sensitive until it reproduces serially.

**Then** implement `sase-1cb`: when `sase stitch create` rebases onto a moved `origin/master`, run a bounded semantic check on the **combined** tree and refuse the push if that tree is broken. That is the prevention that survives the next week of concurrent landings.

Do not wait for Full CI (`sase-1c1.12` visual-test, perf-floors) to start this repair. Master Gate is the per-SHA gate; Full CI is the scheduled heavy lane. They share lint and the fast suite, so greening Master Gate also takes a bite out of Full CI.

---

## 1. What “master is failing” means

CI on this project is two-speed (`decisions:ci-two-speed-split`):

- **Master Gate** runs on every push to `master`, grouped by SHA, never cancelled. Jobs: `core-wheel` → `lint` + 8 shards of `just test`. Timeouts are 20 minutes.
- **Full CI** calls `ci.yml` every two hours. Extra lanes: visual snapshots, perf-floors, 3.12/3.13/3.14, coverage/cost. Release (`ci_watch`) requires a green Master Gate **on this SHA** and a Full CI no older than six hours.

The branch is failing **Master Gate**. `core-wheel` is green. `lint` is red. Most test shards are red. Deploy Docs is green and is not a gate.

| Window | Master Gate on `master` |
| --- | --- |
| HEAD `781063e38e` | [run 36875333649](https://github.com/sase-org/sase/actions/runs/36875333649) — **failure** (`core-wheel` ok; `lint` + shards 2–8 failed; shard 1 passed) |
| Parent `429d6577de` | [run 36872281569](https://github.com/sase-org/sase/actions/runs/36872281569) — **failure** (same lint; 11 unique test nodes) |
| Last 100 runs | **100 / 100 failed** |
| Last success | [run 35299164480](https://github.com/sase-org/sase/actions/runs/35299164480) at `f90c6b549f`, **2026-09-18** — 13 days and **1,107 commits** ago |

Full CI is independently red ([run 36822667366](https://github.com/sase-org/sase/actions/runs/36822667366): lint, test 3.12/3.13/3.14, visual-test, perf-floors). Epic `sase-1c1` (*Green sase master CI and ship sase 0.18.0*) is in progress; phase `sase-1c1.13` is the observe-green-master step, still blocked.

This is not one flaky test. It is a **pile of deterministic contract drift** that product landings keep adding to, because landing agents treat the existing red as `KNOWN` and push anyway.

---

## 2. Current Master Gate inventory (HEAD `781063e38e`)

### Lint (every recent SHA)

`just lint` dies in **symvision unused-public**:

- `HandoffSubmitResult` — `src/sase/tool/handoff_launch.py`
- `StarterResolution` — `src/sase/tool/starter.py`
- `owner_ref` — `src/sase/tool/owner.py`

Introduced by `018061f6f2` (`sase-1cx.3`). Hidden until a later epic unmasked the unused-public stage (symvision stops at the first error category). No non-test production import uses these names; the fix is to privatize them. Tracked by **`sase-1dn`**.

Ruff and mypy are clean on this SHA. `toobig` is not the current lint failure (`src/sase/tool/executor.py` has already been split; open bead `sase-1a9` is stale).

### Tests — 13 unique failing nodes

Grouped by cause, not by shard.

#### A. Launch signature drift (`history_text`) — `sase-1cm`

`launch_agents_from_cwd` now always receives `history_text=` (`src/sase/main/query_handler/_launch.py:330`). Test fakes still declare `(query, origin=None)` or assert `assert_called_once_with(prompt, origin="typed")`.

| Node | Error |
| --- | --- |
| `tests/test_partial_launch_cleanup.py::test_launch_query_rolls_back_partial_multi_prompt_launch` | `TypeError: fail_launch() got an unexpected keyword argument 'history_text'` |
| `tests/test_force_reuse_launch_seam_rejection.py::test_plain_sase_run_without_request_sidecar_still_rejects_forced_reuse` | expected `origin='typed'`, actual also has `history_text=None` |
| `tests/test_force_reuse_launch_seam_rejection.py::test_sidecar_without_authorization_still_rejects_forced_reuse` | same |

This bead already closed once for the `origin=` kwarg (`8c38eb6a9a`) and was reopened when `history_text` landed. The durable fix is `**kwargs` on the fakes, not another one-kwarg patch.

#### B. Stale test facade — `sase-1dh`

`tests/ace/tui/widgets/test_agent_header_panel.py` still imports `test_hint_document_forces_expansion`. Commit `c6b802a647` deleted that test and added `test_hint_mode_keeps_collapsed_header_unchanged` / `test_hint_mode_numbers_expanded_header_first`. Collection raises `ImportError`. Confirmed in the workspace tree at HEAD.

#### C. Bead-attachments contract leftover — `sase-1de`

| Node | Error |
| --- | --- |
| `tests/test_agent_artifact_directory_operation_audit.py::test_artifact_directory_operation_sites_are_reviewed` | unreviewed site `src/sase/bead/attachments/lifecycle.py:quarantine_local_object` |
| `tests/test_config_schema_repositories.py::test_config_schema_documents_intrinsic_agents_sidecar_contract` | schema text no longer contains the literal `~/.sase/projects/<project_key>/repos/agents`; it now says attachments **and** attachments-private live at `…/repos/<role>` |

#### D. Memory-history epic leftovers — `sase-1dr` (in progress; landing note #1)

| Node | Error |
| --- | --- |
| `tests/completion/test_kind_coverage.py::test_every_value_slot_is_kinded_choiced_or_hinted` | uncaptioned slot `memory/history:at` |
| `tests/main/test_memory_log.py::test_memory_log_json_id_outputs_raw_event` | raw event gained `blob_oid` / `included_blob_oids` |
| `tests/main/test_parser_command_help.py::test_memory_help_marks_primary_command_and_init_alias` | `sase memory` help now lists `history` |
| `tests/test_axe_run_agent_runner_started_at.py::TestRunStartedAtRecording::test_home_mode_running_marker_cleanup_updates_artifact_index` | `setup_index_update.call_count` is 4, test still expects 3 (`sase-1dr.1` added `write_agent_meta`) |
| `tests/test_contract_manifest.py::test_contract_manifest_matches_marker_selection` | marker payload gained the same blob fields; also historically exploded when contract collection hit the `sase-1dh` ImportError |

#### E. Help-spelling pin (untracked as its own bead)

`tests/test_bead/test_show_images.py::test_parser_help_covers_images_and_open` asserts `"-i, --images" in show_help`. The parser **does** define `-i/--images` with choices `auto,cells,kitty,never` (`src/sase/main/parser_bead_queries.py:374`). Python 3.12’s usage/help inserts the choices between the short and long options, so the contiguous substring is gone. Same class as `sase-14p` (argparse spelling differs across 3.12/3.13).

#### F. New on HEAD `781063e38e` only

| Node | Error | Likely owner |
| --- | --- | --- |
| `tests/ace/tui/widgets/test_prompt_next_word_midword.py::test_midword_peek_reveals_then_finishes_word` | `_next_word_peek_pending() is True` fails after typing `e` | The HEAD stitch splits `prompt_prediction_wire` into `prompt_prediction_wire_prediction.py` / `_replay.py` / `_shared.py` (toobig, agent `toobig-6o.prompt_prediction_wire.0`). No bead yet. |
| `tests/ace/tui/test_link_follow_seam.py::test_beads_sync_reports_visible_and_missing` | `PENDING` vs expected `MISSING` | Absent from parent SHA. Re-run serially before filing; may be shard-load, not the wire split. |

---

## 3. Why this keeps happening

The failures above are symptoms. These five mechanisms refill the queue faster than `sase-1c1.13` can drain it.

### 3.1 Landings push a tree that was never tested

`sase stitch create` commits, rebases onto `origin/master` with autostash, and pushes. `just fix` runs **before** the commit, therefore **before** the rebase. Two independently correct commits that touch different files rebase cleanly and still fail to import. Tracked as **`sase-1cb`**, with prior point-fixes `sase-lg`, `sase-183`, `sase-1b7`. Master Gate only sees the damage after it is already on `master`.

### 3.2 Scoped `just check` does not see these tests

Agent default verification is `just check`: whole-repo lint except `toobig`, plus a **diff-scoped** test lane. Whole-repo contract tests (schema wording, audit sites, completion kinds, CLI help, launch fakes in unrelated files, facade re-exports) sit outside the import-graph closure of a typical product diff. They first fail on Master Gate’s full `just test` shards.

### 3.3 Red master is treated as `KNOWN`, so it stays red

Open CI beads (`sase-1dn`, `sase-1dh`, `sase-1cm`, `sase-1de`, plus `sase-1dr` leftovers) let later landers classify the same nodes as pre-existing and keep shipping. `sase-1cm` even closed after an `origin=` fix and had to be reopened for `history_text`. Product epics (`sase-1dq`, `sase-1dr`, toobig splits) are still landing on a 13-day-red tip. `sase-1c1` was supposed to freeze this; it did not.

### 3.4 Pins are one commit behind the behavior

The recurring pattern is “behavior changed, pin did not”:

- New kwarg on a launch function → fakes still list explicit parameters.
- Test renamed in a split module → facade still re-exports the old name.
- CLI flag / event field / schema sentence changed → a substring assertion or checked-in snapshot did not.
- New public symbol added for a real type → symvision unused-public, masked by an earlier category, then unmasked after the epic closed.

### 3.5 No merge queue, and Master Gate is post-push

There is no pre-push required check. Direct-to-master stitches are the release path. `ci_watch` correctly refuses to ship 0.18.0 until Master Gate is green **on HEAD**, which is why the release epic is stuck while the test list grows.

---

## 4. What will not fix this

- Rerunning Master Gate on the same SHA. These nodes fail the same way on sequential SHAs.
- Waiting for Full CI / visual goldens (`sase-1c1.12`). Necessary for release, irrelevant to the current Master Gate lint + fast-suite red.
- Closing `sase-1a9` (executor.py toobig). Already split; not in the current lint log.
- Broadening `just check` into `just check-full` for every agent. Host capacity is the constraint (`decisions:check-full-is-explicit`). Add a **cheap always-on contract subset**, do not escalate every landing to the exhaustive lane.
- Point-fixing only the HEAD midword test. That restores one node and leaves lint plus a dozen others red.

---

## 5. Prevention (after the repair stitch)

**Landing path**

1. Implement `sase-1cb`. When the post-commit rebase actually moved the base, run a bounded check on the combined tree (scoped mypy + an AST `from … import` resolver were already prototyped in that bead) and **do not push** on failure.
2. Until that ships: a human or `sase-1c1.13` freeze on product stitches whenever Master Gate is red on HEAD.

**Verification path**

3. Add a Master-Gate-shaped **always-run contract pack** to `just check` (header-panel facade import, launch-fake call shape, completion kind coverage, config-schema sidecar sentence, artifact-directory audit, `pytest -m contract --collect-only`). Small, deterministic, whole-repo. This is the set that scoped selection keeps missing.
4. Launch-test fakes take `**kwargs` from now on. The `origin` then `history_text` reopen of `sase-1cm` is the proof.

**Lint path**

5. Make the unused-public symvision stage visible even when an earlier category failed, or require landings to run a second `just symvision` pass. `sase-1cx` closed “clean” because a private-import error masked these three symbols.
6. A facade-import lint: re-export modules must resolve. `sase-1dh` is the second recent instance of this class (`sase-1b7` was a benchmark re-export).

**Process**

7. Landing notes that say “KNOWN: sase-1dn / sase-1dh / …” on a **master-red** tree are not a pass. Either the lander fixes those beads or it does not push. File new `task_type=ci` beads only for newly introduced nodes.
8. Keep `sase-1c1.13` as the sheriff until `ci_watch` can see a green Master Gate SHA and a fresh Full CI. Visual-test and perf-floors stay on that phase’s successor, not as an excuse to keep product moving.

---

## 6. Suggested repair stitch (concrete)

One commit, conventional message along the lines of `fix(ci): restore Master Gate lint and fast-suite pins`.

1. Rename the three tool types/functions to `_HandoffSubmitResult`, `_StarterResolution`, `_owner_ref` (or give them real in-package callers). Update the two test imports in `tests/tool/test_inline_escalation.py`.
2. Edit the header-panel facade import list and `__all__`.
3. Change `fail_launch` and the force-reuse `assert_called_once_with` to accept/ignore `history_text`.
4. Add `quarantine_local_object` to the reviewed audit set (or route it through the reviewed helper); loosen the schema test to the `<role>` wording that is now true.
5. Add a `ValueKind` / hint for `memory history --at`; update the JSON-id fixture; allow `history` in memory help; expect 4 index updates; `just refresh-contract-manifest`.
6. Change the images help assertion to `'--images' in show_help`.
7. Restore midword peek-pending after the wire split (follow the re-export surface in `src/sase/core/prompt_prediction_wire.py`; the test still talks to `PromptTextArea`).

Then **do not land anything else** until [Master Gate on that SHA](https://github.com/sase-org/sase/actions/workflows/master-gate.yml) is green. Dispatch Full CI by hand if the two-hour schedule is too slow for `sase-1c1.14`.

---

## Sources

- GitHub Actions: Master Gate runs `36875333649` (HEAD), `36872281569` (parent), last success `35299164480`; Full CI `36822667366`.
- Workflows: `.github/workflows/master-gate.yml`, `full.yml`; decision `decisions:ci-two-speed-split`.
- Beads (audited reads): `sase-1dn`, `sase-1cm`, `sase-1dh`, `sase-1de`, `sase-1cb`, `sase-1dr`, `sase-1c1`, `sase-1c1.12`, `sase-1c1.13`, `sase-1a9`.
- Workspace tree at `781063e38e`: header-panel facade, `_launch.py` `history_text`, `parser_bead_queries.py` `-i/--images`, `prompt_prediction_wire.py` split, launch-test fakes.
