---
create_time: 2026-08-09
updated_time: 2026-08-09
status: research
---

# Automating the `sase-core-rs` Dependency-Window Ratchet

**Research question:** SASE agents are repeatedly tasked — by task beads, by dedicated
epic phases, and by mid-task discovery — with raising the `sase-core-rs` version window
in `sase`'s `pyproject.toml`. What is the cheapest correct way to take that work off
agents entirely?

**Scope:** `sase` at master `db202d159`, linked `sase-core` at master `b8b6570`
(v0.21.3 + unreleased commits), PyPI release metadata for `sase-core-rs` (85 versions),
the GitHub release-PR history of `sase-org/sase-core`, the 67 `sase` commits that have
moved the dependency line, and the sase bead store. Measured 2026-08-09. This report
consolidates two independent research passes (`__a`, `__b` in this directory) plus a
third verification pass; where the two disagreed, the disagreement is resolved below
with reproduced evidence.

---

## Bottom line

The recurring work exists because a **release-time package invariant is enforced during
feature integration**, and because the core release that would satisfy it is gated on a
human clicking Merge.

The recommendation is a **release-boundary window ratchet** — move the published-floor
decision off feature PRs and onto the pending `sase` release PR, where it coalesces
~8 core releases into one edit — layered with a **cheap early-warning probe** in
`just check` so a feature agent learns which core release it needs *before* it commits,
and a **workflow-driven merge** of `sase-core` release PRs so that release arrives in
minutes rather than hours. Detail in [§7](#7-recommended-solution).

Three findings drive that shape, and the third is the one that decides between the two
prior reports:

1. **The volume is real, and the right unit is beads, not commits.** 67 commits have
   moved the line since 2026-04-29; 20 touched nothing but the three metadata files.
   More importantly, **21 closed beads since 2026-07-23 have a floor bump as their
   entire titled purpose — 16 of them phase beads** — plus 4 live right now. That is
   ~1.2 dedicated agent launches per day, each paying a bead, a workspace claim, and a
   full context load.
2. **The dominant latency is human.** Across 10 consecutive `sase-core` releases,
   merge → PyPI is a near-constant 9.5 min, but release-PR-open → merged has a median of
   ~43 min, a mean of ~2h20m, and a worst case of 9h36m. `sase-core` has
   `allow_auto_merge: false` and an unprotected master, so all of that variance is
   attention, not policy.
3. **The required floor is *not* fully computable from the existing probes.** Replaying
   the 12 most recent floor bumps against `check_sase_core_rs_bindings` +
   `validate_sase_core_rs`, **5 of 12 (42%) pass both probes against the pre-bump floor**
   — the bump was driven by a behavior change the probes cannot see. A bisect over that
   oracle would confidently return a floor that is too low. This is the single most
   important correction to the prior analysis, and it is why the *authoritative* policy
   should be conservative (newest published core at release time) with the probes
   demoted to early warning.

---

## 1. What the work is

A pure bump is a three-file mechanical change with an identical shape every time
(`491579083`, `7bdeee08e`, `6488d4a49`, `8cc3913fc`, `10843b522`):

```
 pyproject.toml                                  |  2 +-
 tests/test_sase_core_rs_telemetry_smoke_tool.py |  2 +-
 uv.lock                                         | 14 +++++++-------
```

| Site | Change | Notes |
| --- | --- | --- |
| `pyproject.toml:46` | `"sase-core-rs>=X,<Y"` | this *is* the decision |
| `uv.lock` | regenerated | mechanical; `uv lock --upgrade-package sase-core-rs==V` keeps unrelated pins stable |
| `tests/…_telemetry_smoke_tool.py:35` | `== "0.21.3"` | **should not exist** — see below |

Verified: those are the only two places the version is written as a literal in the
tree. The test literal is a golden assertion that `declared_minimum_version` reads
`pyproject.toml` correctly, and the very next test in the same file
(`test_declared_minimum_requires_inclusive_floor`) already proves the parser against a
`tmp_path` fixture. It adds no coverage; it only guarantees every bump must also edit a
test file.

### Verified cost multiplier

Touching `pyproject.toml` escalates `just check` from the scoped lane to the **full
2482-file suite**:

```
$ tools/select_tests --explain          # after touching pyproject.toml
test selection escalated to the full suite
  (rules: contract-set-only, core-identity-changed, packaging-config); 2482 test files in scope
```

So the cheapest possible bump still costs the most expensive verification lane in the
repo — and, in a fresh ephemeral workspace, a `just install` that rebuilds the Rust core
from source first.

### Volume, reconciled

The two prior reports quoted different numbers over different windows; both are correct
and were reproduced:

| Metric | Value | Window |
| --- | --- | --- |
| commits moving `pyproject.toml:46` | **67** | since 2026-04-29 |
| — of those, in the recent burst | **50** | 2026-07-24 .. 2026-08-09 |
| commits touching *only* metadata files | **20** of 67 | since 2026-04-29 |
| bump-focused commit subjects | **34** of 67 | since 2026-04-29 |
| `sase-core` releases published | 68 | 2026-07-24 .. 2026-08-09 |
| `sase` releases | 8 | same window |
| **closed beads whose title is floor work** | **21** (16 phase, 4 task, 1 plan) | 2026-07-23 .. 2026-08-09 |
| live floor beads right now | 4 | — |

The 68:8 ratio is the coalescing opportunity: a release-boundary ratchet turns ~50
window edits into at most 8.

### It is live right now

`sase-i8.8` ("Raise the sase-core-rs dependency window") is an `in_progress` phase bead
with `DEPENDS ON`/`BLOCKS` edges whose entire description is the three-file edit.
`sase-hz` is a `ready` task bead carrying ~40 lines of hand-written forensics.
`sase-ic` was closed `canceled` with the reason *"I think this was maybe resolved
already?"* — the churn reaches the project owner's triage queue too. The floor is
`0.21.3`; PyPI's latest is `0.21.3`; `parse_merge_summary` is unreleased pending
`sase-org/sase-core#101`, open since 13:38Z today.

---

## 2. Where the tokens go

**A. Diagnosis.** Most token-expensive. `sase-hz`'s description is hand-written
archaeology across two repos' histories. Its conclusion ("raise to `>=0.21.1`") is
reproducible mechanically in seconds:

```
$ git log --oneline --reverse -S'glossary_validate' -- crates/sase_core_py/src/lib.rs | head -1
f6a29d3 feat(core): add glossary catalog domain
$ git tag --contains f6a29d3 --sort=v:refname | head -1
v0.21.1
```

**B. The wait.** The structural cost, and the reason plans allocate a *separate phase*.
Two hard gates enforce it: `just check` → `just validate` →
`tools/validate_sase_core_rs_version --published-minimum` does a live PyPI lookup and
fails if the declared minimum is unpublished; and `uv lock` cannot resolve a floor that
does not exist on the index. So an agent's options are to block and poll, or file a bead
so a *later* agent reloads the whole context.

**C. The edit and re-verification.** Trivial edit, full-suite verification (§1).

**D. Planning overhead.** 47 plan files carry explicit bump language; 16 closed phase
beads exist for nothing else.

---

## 3. What already exists

| Asset | What it does | Gap |
| --- | --- | --- |
| `tools/check_sase_core_rs_bindings` | Statically collects the 265 `require_rust_binding` names from `src/sase`, asserts an installed wheel exposes them. `--list` needs no wheel. **Stdlib-only** (verified: `argparse, ast, importlib, sys, dataclasses, pathlib`). | Only ever run against one version in CI; never asked "which version *would* satisfy this?" |
| `tools/validate_sase_core_rs` | Probes wire-schema versions and behavior contracts. **Stdlib-only** (verified). | Same. |
| `tools/validate_sase_core_rs_version` | Compares the *checkout's* Cargo version to the specifier (exit 3 = behind, 4 = ahead); `--published-minimum` verifies the floor exists on PyPI. | Compares to the checkout, not to what the tree needs. |
| `Justfile _core-overrides-arg` + `_setup` | Lifts the published window for dev installs; already prints `WARNING: bump the published sase-core-rs window in pyproject.toml` when the checkout runs ahead. | Warning only, and only about the *checkout*, not about published availability. |
| `.github/workflows/publish.yml` → `sync-lockfile` | Detects `release-please--branches--master`, checks it out, runs `uv lock`, commits, pushes back, using `SASE_RELEASE_TOKEN`. | **Direct precedent for a bot-authored release-branch metadata commit.** |
| `.github/workflows/ci.yml` → `published-core-minimum-smoke` | Installs the exact declared floor from PyPI and runs 5 smokes + the binding check. | Runs on every feature PR and every master push; **explicitly skipped on the release-please PR** — exactly inverted from where it belongs. |
| Axe (`sase axe chop`) | Live chops `ci_watch`, `refresh_docs[…]`, `toobig_split[sase]`, `bead_task_triage` are the same shape: script decides, runner proposes. | No chop watches the core floor. |

The key enabler both prior reports identified and that verification confirms: because
both probes import nothing from `sase`, *"does published `sase-core-rs==V` satisfy this
tree?"* is a bare venv plus two commands. That is what makes an early-warning gate
essentially free. §6 explains why it is *not* enough to set the floor.

---

## 4. Two structural causes

**Cause 1 — a release invariant enforced at feature time.** Development and every
source-based CI lane build `sase_core_rs` from the `sase-core` checkout and deliberately
override the published window. The window in `pyproject.toml` only matters when building
or installing a *published* `sase` distribution. Yet `published-core-minimum-smoke` runs
on every ordinary PR and every master push, so the moment Python touches a new binding or
corrected behavior, the feature agent is forced into the release-metadata ratchet.

The `if:` guard on that job is instructive:

```yaml
# The release-please PR branch only ever carries version/changelog bumps and
# its merge triggers a full master-push run, so its CI is pure runner burn.
if: github.event_name != 'pull_request' || github.event.pull_request.head.ref != 'release-please--branches--master'
```

The gate runs everywhere *except* the one branch whose metadata it validates. Fixing that
inversion is most of the fix.

**Cause 2 — the core release is gated on attention.** Reproduced from the GitHub API:

| Version | PR | PR open → merged | Merged → PyPI |
| --- | --- | --- | --- |
| 0.19.0 | #91 | 5m39s | 13m20s |
| 0.19.1 | #92 | 33m32s | 8m24s |
| 0.19.2 | #93 | 4m24s | 9m17s |
| 0.19.3 | #94 | 5m44s | 9m50s |
| 0.20.0 | #95 | **7h41m** | 8m18s |
| 0.20.1 | #96 | 2h07m | 9m22s |
| 0.21.0 | #97 | 2h20m | 7m45s |
| 0.21.1 | #98 | **9h36m** | 8m36s |
| 0.21.2 | #99 | 18m01s | 9m10s |
| 0.21.3 | #100 | 53m01s | 10m35s |

**Merged → PyPI: mean 9.5 min (7m45s–13m20s).** **PR open → merged: median ~43 min,
mean ~2h20m, max 9h36m.** Verified: `allow_auto_merge: false`, master unprotected,
release-plz PRs are opened with `SASE_RELEASE_TOKEN` so their CI *does* run and passes.

---

## 5. Where the two prior reports disagreed

| | `__a` (release-boundary ratchet) | `__b` (computed floor ratchet) |
| --- | --- | --- |
| **Where the floor is set** | On the pending release-please PR | On the feature PR, via `just check` |
| **Which version** | Newest fully published stable core | Lowest version satisfying the probes |
| **Feature-PR published-floor gate** | Remove it | Keep it, but make it precise |
| **Top single lever** | Move the gate | Auto-merge `sase-core` release PRs |

They are not really competitors: `__a` diagnoses *when* the invariant should be enforced,
`__b` diagnoses *what it costs and how fast the answer can be produced*. The genuine
conflicts are the version-selection policy (§6) and the auto-merge mechanics (§7 R3).
Everything else composes.

One asymmetry worth naming: `__b`'s design keeps master red while a core release is
pending — it only shortens the redness. `__a`'s design removes that state entirely, but
at the cost of moving diagnosis to release time, when the feature agent is long gone.
The recommendation takes `__a`'s gate placement and `__b`'s early warning so neither cost
is paid.

---

## 6. The decisive experiment: can the required floor be computed?

`__b`'s central claim is that the floor is "already fully computable, and nobody computes
it" — bisect published versions against the two stdlib probes. That claim was tested
directly by replaying the 12 most recent floor bumps: check out the tree *at* the bump
commit, and run both probes against the wheel for the *pre-bump* floor. If a probe fails,
the oracle would have caught the staleness.

| Commit | old → new | bindings | schema probes | oracle |
| --- | --- | --- | --- | --- |
| `d7e9ae8ae` | 0.21.2 → 0.21.3 | PASS | FAIL | detects |
| `b73609337` | 0.21.1 → 0.21.2 | PASS | FAIL | detects |
| `466a24c38` | 0.21.0 → 0.21.1 | MISSING | FAIL | detects |
| `25be8cc68` | 0.20.1 → 0.21.0 | MISSING | FAIL | detects |
| `92f0ff377` | 0.20.0 → 0.20.1 | MISSING | FAIL | detects |
| `491579083` | 0.19.3 → 0.20.0 | MISSING | FAIL | detects |
| `7bdeee08e` | 0.19.2 → 0.19.3 | PASS | PASS | **blind** |
| `94430f0f9` | 0.19.0 → 0.19.2 | PASS | PASS | **blind** |
| `5b3f3494b` | 0.18.4 → 0.19.0 | MISSING | PASS | detects |
| `d9c13549f` | 0.18.3 → 0.18.4 | PASS | PASS | **blind** |
| `6b0976bcb` | 0.18.2 → 0.18.3 | PASS | PASS | **blind** |
| `7ffd5471a` | 0.18.1 → 0.18.2 | PASS | PASS | **blind** |

**7/12 detected, 5/12 blind (42%).** The blind cases are all pure behavior changes, per
`sase-core`'s changelog:

- 0.18.2 — *stop a slow git log from silently emptying the commit inventory*
- 0.18.3 — *archive close metadata instead of destroying it on reopen*
- 0.18.4 — *reject a malformed plan header block during validation*
- 0.19.2 — *donate a per-tab icon from the newest declaring row*
- 0.19.3 — *append a snooze note recording wake conditions*

None adds a symbol; none bumps a wire-schema version. A symbol-existence + schema-version
oracle cannot see them, and a bisect over it would return a floor that is **too low** —
precisely the class of bug the strict gate exists to prevent (`check_sase_core_rs_bindings`'
own docstring records that sase 0.11.0 shipped calling an unreleased binding and every
published install crashed on first render).

Corroborating from the other direction: only **11 of 67** floor-bump commits also added a
`require_rust_binding(` call. The binding set is a minority driver.

The sound oracle is *"does the published wheel pass sase's contract-marked tests?"* — far
too expensive to bisect across 85 versions per change. That expense is what makes the
conservative policy correct:

> **Track the newest published core at release time.** It is correct by construction
> (never too low), needs no search, and is immune to the blindness above. It narrows the
> accepted window for published `sase` installs — but `sase` and `sase-core` already
> release in near-lockstep (68 core / 8 sase releases in 17 days), and only 4 of 8 sampled
> `sase` releases had a floor below the newest core available at the time, so little real
> compatibility surface is lost.

The probes keep their value as a **free, fast, incomplete early warning** — they catch
58% of cases *before commit*, which is exactly what would have prevented `sase-hz` from
being written. They must not be promoted to the floor-setting authority.

---

## 7. Recommended solution

Five pieces. R1–R2 remove the work from feature agents; R3 removes the hours; R4–R5 are
hygiene and unattended operation. R1 + R2 alone deliver most of the value.

### R1 — Move the published-floor gate to the release boundary *(the core fix)*

Invert the `published-core-minimum-smoke` trigger:

- **Ordinary feature PRs and master pushes:** stop requiring it. They already build the
  current `sase-core` source and fail if current Python and current core are incompatible
  — that is the correct question at that stage. If you want signal without blocking, run
  it as a non-required advisory job.
- **`release-please--branches--master`:** make it required, and expand it — install the
  exact declared core wheel from PyPI, then run `check_sase_core_rs_bindings`, the
  existing smokes, the contract-marked tests, and (this is one candidate, not dozens) the
  full non-visual suite.

The existing post-tag fresh-install smoke stays as the last line of defense. The release
PR must go red before merge if the selected core is absent or incompatible, so no `sase`
tag is ever cut whose package cannot install.

### R2 — Ratchet the window on the release-please branch

Extend the existing `sync-lockfile` job (rename to `sync-release-metadata`). It already
locates the pending release branch, checks it out with `SASE_RELEASE_TOKEN`, commits, and
pushes — add the window update ahead of the lock refresh:

1. Select the newest fully published stable `sase-core-rs` (PyPI JSON API; verify the
   *distribution files* are visible, not just `info.version`, so a partial upload cannot
   be ratcheted onto).
2. Rewrite only the `sase-core-rs` requirement in `pyproject.toml`, parsing with
   `packaging.version.Version`; compute the ceiling from one tested policy function
   (`0.MINOR.PATCH` → `<0.(MINOR+1).0` today, so the pre-1.0 → 1.0 transition is a
   one-line change, not YAML string arithmetic).
3. `uv lock --upgrade-package sase-core-rs==V` so unrelated pins stay put; fail if the
   lock diff exceeds the expected entries.
4. Assert idempotence, reject downgrades and pre-releases, support `--check`.

Do **not** open a separate dependency PR. The release PR is already the review surface for
the artifact that ships, and it is a durable accumulator — many feature commits and ~8
core releases collapse into one metadata update. This is also why Dependabot/Renovate are
the wrong tool here: both are capable of the text transformation (Dependabot lists `uv`;
Renovate's PEP 621 manager maintains `uv.lock`), but both operate per-dependency-release,
which at 3–5 core releases/day reproduces the churn in a new place.

### R3 — Collapse the core release wait

`__b` recommends flipping `allow_auto_merge` on `sase-core`. **That will not work as
stated.** GitHub only offers auto-merge on PRs that *cannot be merged immediately*;
`sase-core` master is unprotected, so release PRs are immediately mergeable and
auto-merge is neither offered nor meaningful — `gh pr merge --auto` would degrade to an
immediate merge that does not wait for CI. Two working options:

- **(a) No policy change (recommended):** add a job to `release-plz.yml` that, for the
  release PR it just created, runs `gh pr checks <n> --watch` and then
  `gh pr merge --squash --delete-branch`. Self-contained, changes nothing for human PRs.
- **(b) Policy change:** add a ruleset on `sase-core` master requiring the existing
  `cargo fmt + clippy + test` and `maturin build + import smoke` checks, set
  `allow_auto_merge: true`, and use `gh pr merge --auto --squash`. More correct long-term,
  but it also constrains direct pushes to master.

Either turns median-43-min / worst-9h36m into green-CI-plus-~10-min, making
core-change → PyPI a predictable ~15 minutes.

Risk is low: release-plz only opens a release PR when releasable commits exist, the PR
contains only a version bump and changelog, core CI already gates it (verified passing on
#100 and #101), and the publish job independently verifies the tag and wheel metadata and
is self-healing on a 6-hour schedule.

Note the interaction: **R1 lowers R3's urgency.** Once feature PRs no longer block on a
published core, the wait stops being on the critical path and becomes a release-lane
latency. `__b` ranks R3 first because it assumes the feature-PR gate stays; under R1 it is
valuable but no longer the top lever.

### R4 — Delete the golden literal, add the early warning

- Change `tests/test_sase_core_rs_telemetry_smoke_tool.py:35` to derive its expected value
  from `pyproject.toml` instead of the hardcoded `"0.21.3"`. This drops the bump from
  three files to two and removes the one edit site with no mechanical justification.
- Add a **non-fatal** `core floor` step to `just check` that runs the two stdlib probes
  against the currently declared floor and, when they fail, names the core commit that
  provides the missing capability and whether it is released
  (`git log -S'<name>' -- crates/sase_core_py/src/lib.rs` + `git tag --contains`, both
  verified working). Emit a small JSON verdict — `ok` / `stale_actionable` /
  `blocked_unpublished` — with directional exit codes matching the convention
  `stale_core_binding_guard.md` established, and cache per-version verdicts (a published
  version's export set never changes, so steady state is one wheel download per core
  release).

  **Warn, never fail.** Given the 42% blind rate, a hard gate on this signal would be
  both incomplete and a re-creation of the very blocker R1 removes. Its job is to tell the
  feature agent *before it commits* "you need core ≥ 0.22.0, which is not out yet" —
  which is exactly the forensic work `sase-hz` spent an agent producing.

### R5 — Axe chop `core_floor_ratchet` (optional, after R1–R2 prove out)

A chop on a slow lumberjack that runs the R4 verdict per project and, on
`stale_actionable`, proposes a single tightly-scoped agent (`just bump-core-floor &&
just check-full && commit`), keyed `once_per` target version so it proposes exactly once
per core release. `blocked_unpublished` records and stays quiet. This is the residual path
for the case where a floor genuinely must move between `sase` releases; with R1–R2 it
should rarely fire. Axe is the right host — `ci_watch`, `refresh_docs[…]`, and
`toobig_split[sase]` are the same script-decides/runner-proposes shape and the framework
already provides cadence, dedupe, guards, and per-project fan-out.

### Suggested order

1. **R4's literal deletion** — trivial, immediately reduces every future bump.
2. **R1** — the trigger inversion. Highest value, smallest diff, and it is what actually
   stops feature agents being conscripted.
3. **R2** — the release-branch ratchet. Run one `sase` release in report-only mode
   (print the proposed version and diff, push nothing) before enabling.
4. **R4's warning gate** — restores early diagnosis that R1 would otherwise defer.
5. **R3** — collapse the core wait.
6. **R5** — the chop, only if a residual gap is observed.

---

## 8. Options rejected

| Option | Why not |
| --- | --- |
| Better prompt for the bump agent | Leaves the work agent-shaped: still a bead, a launch, a workspace claim, and a full context load, ~1.2×/day. The task has no judgement in it; it should not have an agent in it. |
| Dependabot / Renovate | Both handle the text transformation, neither expresses the policy (a semantic `>=` floor tied to capability, plus a next-breaking ceiling), and both fire per core release — 3–5 lock-churning PRs/day. Worth keeping only as a slow daily backstop *behind* R2. |
| One `sase` PR dispatched per `sase-core` publish | ~68 downstream events in the sample window, plus cross-repo credentials. Acceptable only as a *wake* signal for the R2 reconciler, never as the update itself. |
| Bisect for the lowest satisfying version | §6: 42% blind rate against the available probes. Preserves the widest window but can set the floor too low. Revisit only if the probe suite grows to cover behavior contracts, or as an `--oldest-passing` opt-in behind R2. |
| Drop the upper bound, or pin core exactly | Unbounded lets a future breaking core be selected for an old `sase` release; exact-pin destroys resolver flexibility. |
| Publish a core dev release per master commit | Removes the wait, but pollutes the public PyPI project end users install from and multiplies the wheel matrix cost by an order of magnitude. |
| Runtime feature detection / graceful degradation | Trades a loud build-time failure for a quiet runtime one — the exact failure mode the strict gate was created for. |
| Merge `sase-core` into `sase` (monorepo) | The deepest fix — the whole problem class is cross-repo release coupling. Also a large migration: Rust toolchain in every `sase` CI lane, slower installs, loss of independent core cadence. Disproportionate. |
| Relax the CI gate so master stays green while waiting | Tempting, but deletes the only signal that catches this class before users. R1 achieves the same relief without weakening coverage, by moving the gate rather than removing it. |

---

## 9. Failure modes and safeguards

| Failure | Safeguard |
| --- | --- |
| Core tag exists but PyPI upload not yet visible | Ratchet only when the exact-version JSON *and* the required distribution files are visible; bounded retry |
| Partial upload | Verify the wheel/sdist set, not only `info.version` |
| Stale or out-of-order wake events | Ignore the event's version; re-read PyPI, serialize with one concurrency group, refuse downgrades |
| Newest core is breaking for current `sase` | Source-core CI should already be red; the release-PR published-wheel lane is the authoritative block |
| No pending release PR | Exit 0; the next master push recreates the candidate |
| `uv lock` churns unrelated deps | `--upgrade-package sase-core-rs==V`; fail if the diff exceeds expected entries |
| Ceiling policy changes at core 1.0 | One tested policy function, not YAML string arithmetic |
| Cross-repo wake-up needs credentials | `GITHUB_TOKEN` cannot reach another repo; prefer a narrowly-scoped GitHub App over widening `SASE_RELEASE_TOKEN` |
| Automation silently weakens coverage | Make the release compatibility lane a required check; keep the post-tag fresh-install smoke |

## 10. Acceptance criteria

- A feature PR can use a newly landed core binding or behavior without editing
  `pyproject.toml`, `uv.lock`, or a version literal — and without waiting on a core release.
- Normal CI still tests that PR against current `sase-core` source.
- A pending `sase` release PR receives exactly one canonical window update regardless of
  how many core versions published during the interval.
- The release PR cannot merge unless its exact PyPI core floor passes bindings, schema
  probes, and the contract-marked suite.
- Re-running the synchronizer produces no diff; stale events cannot downgrade the floor.
- A feature agent that needs an unreleased core capability is told so by `just check`,
  by name and by core release, without producing a forensic bead.
- No new bead is created whose title is "raise the sase-core-rs floor".

## 11. Open decisions for the owner

1. **Version-selection policy.** Newest-published (recommended, §6) narrows the supported
   window for published `sase` installs. Confirm that is acceptable, or accept the 42%
   soundness gap of a probe-based minimum.
2. **R3 variant.** Workflow-driven merge (no policy change) vs. a `sase-core` master
   ruleset plus real auto-merge.
3. **Advisory vs. removed** for `published-core-minimum-smoke` on feature PRs. Advisory
   keeps signal at some runner cost; removal is cheaper.
4. **Planning guidance.** Once R1–R2 land, plans should stop allocating a dedicated
   "raise the sase-core-rs dependency window" phase. That is a change to plan-authoring
   guidance and possibly to `sase/memory/`, which requires explicit in-conversation user
   permission — noted here as a proposal, not an action.
5. **Adjacent gap (noted, not recommended).** `%wait` supports agents, beads, time floors,
   and runner thresholds, but has no predicate for external state — there is no
   `%wait(published=sase-core-rs>=0.22.0)`. It would let a plan express "this phase starts
   when the core release exists" as a machine wait rather than a polling phase bead. R1
   and R3 together make it much less urgent.

---

## Appendix: reproductions

All run 2026-08-09, `sase` master `db202d159`, `sase-core` master `b8b6570`.

**Full-suite escalation from a one-character `pyproject.toml` edit:**

```
$ tools/select_tests --explain
test selection escalated to the full suite
  (rules: contract-set-only, core-identity-changed, packaging-config); 2482 test files in scope
environment inputs changed: core-cargo, environment-metadata, extension, pyproject, uv-lock, validator:core-bindings
```

**The oracle-blindness replay** (§6) — for each bump commit, check out that tree and run
both probes against the *pre-bump* floor's published wheel:

```
$ uv venv --python 3.12 /tmp/pc-$OLD && uv pip install --python /tmp/pc-$OLD/bin/python "sase-core-rs==$OLD"
$ git checkout -q $BUMP_SHA
$ /tmp/pc-$OLD/bin/python tools/check_sase_core_rs_bindings   # binding names
$ /tmp/pc-$OLD/bin/python tools/validate_sase_core_rs         # wire schemas + behavior
# 12 most recent bumps: 7 detected, 5 pass both probes (floor moved for invisible behavior)
```

**Only 11 of 67 bumps added a binding call:**

```
$ git log --format='%h' -L 46,46:pyproject.toml | grep -E '^[0-9a-f]{7,}$' > /tmp/bumpshas.txt
$ while read s; do git show "$s" -- src/ | grep -qE '^\+.*require_rust_binding\(' && echo "$s"; done < /tmp/bumpshas.txt | wc -l
11
```

**Bead-level cost:**

```
$ sase bead search 'sase-core-rs' -s closed -f json -n 400 | <filter titles for floor/window language>
closed matched: 135 | title is floor/window work: 21   (phase: 16, task: 4, plan: 1)
```

**`sase-core` merge policy:**

```
$ gh api repos/sase-org/sase-core --jq '{allow_auto_merge, default_branch}'
{"allow_auto_merge":false,"default_branch":"master"}
$ gh api repos/sase-org/sase-core/branches/master/protection
Branch not protected (HTTP 404)
```

**The live failure:**

```
$ /tmp/pub-core-21.3/bin/python tools/check_sase_core_rs_bindings
sase_core_rs 0.21.3 is missing 1 of 265 required binding(s):
  parse_merge_summary
$ git -C sase-core log --oneline --reverse -S'parse_merge_summary' -- crates/sase_core_py/src/lib.rs | head -1
459bbc6 feat(vcs-log): add parent ids and merge summaries
$ git -C sase-core tag --contains 459bbc6
            # empty -> unreleased; pending sase-org/sase-core#101 (chore: release v0.22.0)
```

**Source-regex is not ground truth** (a rejected prototype from `__b`, retained as a
warning): a `#[pyo3(name = "…")]` regex over `crates/sase_core_py/src/lib.rs` finds 280
names where the built wheel exposes 309 (0.21.0) / 313 (0.21.1), missing `#[pyclass]`
types, functions without an explicit `#[pyo3(name)]`, and anything added via `m.add(…)`.
`dir(sase_core_rs)` on the wheel is the only sound introspection.
