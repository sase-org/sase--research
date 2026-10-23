# PyPI release reliability E3 readiness: what E1 and E2 changed, and how to start trustworthy signal

Researcher: mus (independent 5-researcher swarm, `research.2a.*`).
No peer report from this swarm was located, opened, or consulted.
Shared inputs only: the converged design doc, bead store, plans, tree, and workflows.

Research question: are we ready for the E3 (trustworthy signal) epic described by
`pypi_release_reliability_design_and_work_split.md` in the research sidecar repo?
What did E1 and E2 already do, what developer-facing behavior changed, and what
should the E3 design start from?

## Bottom line

1. **E1 is done and closed.** Epic `sase-1my` and all six phases
   (`sase-1my.1`–`sase-1my.6`) are `CLOSED` (resolution `done`, closed
   2026-10-19). The installable-family promise has live proof (V-E1a/b/c), with
   known follow-ups triaged and the 7-day soak plus TestPyPI drill explicitly
   declined by the owner rather than left pending.
2. **E2 is mid-flight, not done.** Epic `sase-1n6` is `IN_PROGRESS`.
   Closed: `sase-1n6.1` (core-cut resilience), `sase-1n6.2` (exact build +
   manifest), `sase-1n6.3` (exact core pin), `sase-1n6.4` (exercise),
   `sase-1n6.7` (observe-only steward), `sase-1n6.8` (release-green record +
   metrics). Open: `sase-1n6.5` (qualify vs published core, with child epic
   `sase-1n6.5.1` still in progress), `sase-1n6.6` (digest-checked publish),
   `sase-1n6.9` (cutover to `release.yml` + steward merges), `sase-1n6.10`
   (first steward release + decision record).
3. **E3 has no epic bead and no code yet.** Search finds no
   "trustworthy signal" epic, no shared bounded-rerun helper, no quarantine
   file, and no `culprit-check.yml`. `ci.yml` (50 `run:` steps) and
   `master-gate.yml` only share `fail-fast: false` on matrix legs; there is no
   rerun/quarantine/culprit logic in either workflow today.
4. **E3 is startable now, and the design says to start now** — E1–E3 run in
   parallel by design, with E3.1 (rerun helper) feeding E2.3 and E3.1+E3.5
   gating E4. But E3 must be sequenced around the still-open E2 seam work:
   E2.3/E3.1 meet at the rerun helper's input contract (E3.1 defines it first),
   E3.7 waits for E2.3 (both touch `ci.yml`), and the deployed qualification
   proofs are still blocked on a source-containment gap plus an unlanded
   identity-syntax repair.
5. **The largest E3 readiness risk is not E3 scope but E2 evidence quality.**
   The containment issue on `sase-1n6` (notes #1–#8) is still open: the
   exact-build/core-pin seam does not yet prove the selected published core
   tag contains `sase-core-revision.txt`, and the Oct-20 rehearsal trio at
   `4adee846d3c` produced no candidate/qualification evidence (identity
   `SyntaxError`, Full CI build-core setup failure). E3's culprit/attribution
   work will inherit that "no evidence vs red evidence" distinction, so E3
   should harden it rather than assume E2 will fix it first.

## Shared context: the design of record

The converged design (`research:202610/pypi_release_reliability_design_and_work_split/pypi_release_reliability_design_and_work_split.md`,
read via audited `sase artifact read`) organizes the program around three
promises with separate fences, detectors, and owners:

- Installable (E1): `uv tool install sase` installs the newest family release
  and it works.
- Releasable (E2): a qualified release reaches PyPI about daily.
- Landable (E3–E6): `master` stays gate-green.

Key design choices relevant to E3 readiness:

- The release unit is a qualified *pair*: sase wheel+sdist plus the exact
  `sase-core-rs==X.Y.Z` and wheel digests tested. Build once at the tag,
  qualify against the *published* core wheel, publish retained bytes, confirm
  from PyPI, then un-draft. Tags never move; a failed candidate burns a
  version cheaply (next PR becomes x.y.z+1).
- One stateless steward (`tools/release_watch`, scheduled
  `release-steward.yml` on athena + on-demand) drives releases and the core
  cut: recompute from PyPI JSON, tags, draft releases/manifests, workflow
  runs keyed by SHA, and the release PR; take at most one idempotent action
  per tick; report one typed blocking reason with an owner action
  (`RELEASED`, `RELEASABLE`, `NOTHING_TO_RELEASE`, `CORE_LAG`, `CORE_CI_RED`,
  `CORE_CUT_RED`, `CORE_INCOMPATIBLE`, `GATE_RED`, `QUALIFY_RED`,
  `EXERCISE_RED`, `DEPENDENCY_UNPUBLISHED`, `PUBLISH_PARTIAL`,
  `INSTALL_BROKEN`, `WATCHER_BROKEN`/unknown). After 24h in one blocked
  state it files or `+1`s one typed task bead.
- Slow release qualification stays out of the merge queue (and out of the
  release PR's own `merge_group`): a burned version costs nothing, a daily
  90-minute queue stall costs every agent wave.
- Work split is Track 0 (`sase-1mk`, ship 0.18.0) plus E1–E6. E1–E3 start
  now; E4 needs E3.1+E3.5 live; E5 starts once E1–E3 are moving; E6 needs
  E3+E4 live, E5 exit, and a go/no-go review.

E3's own scope in the design (Size M–L, start now):

- E3.1 shared bounded-rerun helper; E3.2 escalating quarantine; E3.3 parity;
  E3.4 drift canaries; E3.5 culprit attribution + `culprit-check.yml`; E3.6
  false-red digest + DORA-style metrics; E3.7 visual-promotion study after
  E2.3 (default: no).

## E1: done — scope, proof, and what developers feel

Epic `sase-1my` ("Installable family — retention by need, published floors,
family canary"), plan `plans/202610/e1_installable_family.md`, all six
phases closed 2026-10-19. Land triage and verification notes live on
`sase-1my` notes #1–#3 and the `sase-1my.land` closeout.

### What each phase delivered

- **E1.1 `sase-1my.1` — protected-set retention in sase-core, failing closed.**
  `pypi_retention.py plan` computes a protected set and refuses any plan that
  touches it, failing closed on unreadable metadata, partial enumeration, or
  a failed support-manifest read. Live proof V-E1a: with `--keep 30`,
  `sase-core-rs` 0.42.0 and 0.42.1 stay protected for sase 0.18.0 (five files
  each, excluded from deletion); a planted `--list 0.42.0` and a planted
  `win_amd64` wheel deletion were refused with the 0.18.0 window named;
  simulated-unreachable PyPI failed closed. Core follow-ups landed alongside:
  `setup-uv` v4 fix in `ci.yml`/`pypi-headroom.yml`, `pypi_delete`
  package-name canonicalization with a protected-package guard, backfill
  `EXPECTED_DIST_SUFFIXES` derivation, threshold-free headroom issue
  title/labels.
- **E1.2 `sase-1my.2` — family install canary on Linux and macOS.**
  `.github/workflows/install-smoke.yml` (446 lines) runs daily plus
  `workflow_dispatch` with `probe_expect`/`alert` inputs. It does a clean
  `uv tool install` of sase plus each family plugin on `ubuntu-latest` and
  `macos-latest`, asserts newest-PyPI plus exact-version installs, runs
  `sase core health` and the documented first commands, and uploads one
  `install-canary-<os>.json` artifact per leg (schema_version, os, run_id,
  attempt, sha, mode, verdict, packages, failing_step). The alert job only
  reports green when the smoke job succeeded and both OS artifacts exist,
  parse, and say green; a probe run (`probe_expect=sase==0.0.0`) is red on
  both legs with the alert off. Live proof V-E1b: dispatch `39298640599`
  green on both OSes; probe `39298650862` red on both legs. Developer note:
  the canary is a detector, never a merge gate; red canary becomes the
  steward's `INSTALL_BROKEN` severity-1 state.
- **E1.3 `sase-1my.3` — `release-dependency-floor` check on plugin release
  PRs.** New reusable
  `.github/workflows/release-dependency-floor.yml` plus
  `tools/check_release_dependency_floor`: plugin release PRs (head ref
  `release-please--*`, or probe `sase>=99`) fail when a declared sibling
  floor is not on PyPI; otherwise exit 0. `ci_watch` refuses release PRs
  with red checks. Live proof V-E1c: probe `39292291601` failed with
  `DEPENDENCY_UNPUBLISHED` naming newest published 0.18.0; normal run
  `39292296600` succeeded. sase's own release PR keeps the existing
  `release-core-floor-smoke` instead of calling this workflow.
- **E1.4 `sase-1my.4` — storage runway + headroom alert.** PyPI size request
  filed (cheap insurance; ~3.88 GiB of 10 GiB at design time, so not urgent),
  runway line in `docs/pypi-retention.md`, headroom alert wiring. Never lets
  quota pressure override the protected set.
- **E1.5 `sase-1my.5` — recovery runbook + release-safety docs + TestPyPI
  drill tooling.** `docs` recovery runbook (yank then fix forward, core
  backfill via a new patch cut from an old core tag, optional yank of sase
  0.1.0 so a future broken window fails loudly), `release-safety.md`
  (attempt/SHA/artifact contract, hourly-then-4h floor-check schedule with
  50-attempt cap, family install command, research-artifacts addition), and
  dormant dispatch-only `testpypi-drill.yml` + checker. The drill itself was
  *not* run (human TestPyPI publisher setup remains human-owned); sase 0.1.0
  is confirmed yanked.
- **E1.6 `sase-1my.6` — live acceptance, decision record, 7-day soak.**
  Exit proofs above plus isolated public-index resolve (sase 0.18.0,
  `sase-core-rs` 0.42.1, `sase-github` 0.2.24, `sase-telegram` 0.4.29,
  `sase-research-artifacts` 0.2.0; all 9 recognized family plugin entry
  points load). Contract manifest re-curated (77-file set at the time,
  118.48 serial seconds; 861 passed in that run). The 7-day scheduled-canary
  soak was declined as a task (a pure wait fits no task type); the fixed
  canary's alert issue mirrored into a task bead is the durable detector.

### Developer-facing behavior changes from E1

- Retention is consumer-derived and fail-closed: a delete plan that would
  remove the only compatible core, one required platform wheel, or the exact
  core pinned by a supported release is refused, and unreadable PyPI also
  refuses. Developers deleting PyPI files now get a refusal naming the
  protected window instead of silent success.
- Plugin release PRs have a new red check: an unpublished sibling floor
  blocks the release PR through `ci_watch`. This would have held
  `sase-github` 0.2.24 (which declared `sase>=0.18.0` before 0.18.0 existed).
- `uv tool install sase` semantics are now asserted daily on two OSes for
  newest-version and exact-version, including plugins and entry-point
  loading — resolver backtracking can no longer look green.
- Recovery is documented and human-gated (yank, fix forward, core backfill,
  optional 0.1.0 yank already done). An install outage holds unrelated
  packaging churn but never blocks a separately qualified *recovery*
  candidate.

## E2: mid-flight — what is landed vs what is still open

Epic `sase-1n6` ("Exact-candidate release train and steward"), plan
`plans/202610/e2_release_train_steward.md`, decisions: `steward_host =
workflow`, `release_cadence = daily`, `memory_release_record = yes`.
Status at research time (`sase bead read sase-1n6` + children, git log
since 2026-10-19):

### Landed (closed)

- **`sase-1n6.1` core-cut resilience + in-flight retention source.** Core
  `release-plz.yml` merge job reruns failed jobs once with a typed failure
  and keeps the dispatch entry point. E1's retention source rides along.
- **`sase-1n6.2` exact build + sealed candidate manifest** (commit
  `110214f51c`). New 295-line `.github/workflows/release.yml`:
  `workflow_dispatch` (`mode`/`core_version`/`rebuild`) with identity
  assertion, one build, stash of dists + manifest on the draft release, and
  a not-yet-qualified red gate. New `tools/release_candidate`
  (seal/verify/observe/show/evaluate/download/core-files/core-suffixes) and
  `docs/contribute/release-train.md`. Verified locally (seal/verify OK on
  real repo state; evaluate red with required-evidence-missing as
  specified); release-please `draft:true` + `force-tag-creation:true`
  verified in action v5 / lib 17.11.2 source. Human gate raised for the
  trusted-publisher + `v*` tag-policy steps (legacy `publish.yml`
  unaffected until handover).
- **`sase-1n6.3` exact core pin + shared core-ensure rule** (commit
  `befa41b575`). `tools/_release_core.py` core-ensure
  (`PINNED`/`CORE_LAG`, GitHub then urllib then local-git, skips pre-suffix
  tags); `tools/ratchet_core_pin` writes `sase-core-rs==X.Y.Z`, refuses
  backwards moves, leaves `CORE_LAG` unchanged; sase `master` converted to
  `sase-core-rs==0.42.0` (`pyproject.toml:48`, `uv.lock` specifier
  `==0.42.0`); `publish.yml` uses `ratchet_core_pin`; window-assuming tools
  (`ratchet_core_window` callers, validators, setup-sase, telemetry smoke)
  updated. 154 phase-owned tests passed.
- **`sase-1n6.4` exercise the exact files** (commit `cc59e6f114`). New
  `tools/exercise_release` (858 lines) + release.yml exercise jobs: install
  the stashed wheel *and* sdist into clean envs with public PyPI deps on
  Linux and macOS, run a short no-LLM workflow in an isolated home
  (deterministic provider), cross host/worker, render a headless TUI frame,
  upgrade from N-1, `pip check`. A planted macOS-only startup crash
  withholds publication.
- **`sase-1n6.7` steward in observe mode** (child epic `sase-1n6.7.1`,
  commits `812cdd9e21`, `112a5f4757`, `50053ef69bd`, `23cccbc969`,
  `dab5776583`, `400572eab6`, `54a9c14d23`). `tools/release_watch` replaced
  by a stateless observe-only tick (one read/decide/execute/report cycle),
  plus scheduled host `.github/workflows/release-steward.yml` (133 lines),
  health reader/snapshot composition, restart-safe actions + issue sinks,
  qualification evidence transport repair with proofs. Scheduled
  observe-only ticks proven (`39407994122` CORE_LAG, `39447512070`
  CORE_CUT_RED; `--tick --json`, no `--live`, no action). Dispatch
  write-access via `SASE_RELEASE_TOKEN` not yet tested.
- **`sase-1n6.8` release-green record + metrics** (commit `b15cc3fb5b`).
  Read-only `tools/release_metrics` + `tools/_release_metrics.py`,
  exact-SHA green evidence, release-green bookmark (Stovepipe), dashboard
  inputs: days-since-release, landing-to-PyPI lead time, time-to-release
  green, core-lag hours, burned versions, change-fail rate.

### Still open (in progress)

- **`sase-1n6.5` qualify vs published core** (child epic `sase-1n6.5.1`
  in-progress; key commit `54a9c14d23` landed but acceptance open).
  `release.yml` qualify-prepare binds the sealed manifest, qualify-ci runs
  reusable `ci.yml` at the identity SHA against the published core,
  `tools/collect_qualification_jobs` + evaluator produce
  verdict/observation/token/run-id/attempt/candidate-id/generation +
  intended/tested-core-version outputs. Publish must depend on the qualify
  verdict + exercise, never the qualify-ci aggregate (explicit status
  condition needed so a red advisory job cannot silently skip publication).
  Live acceptance is *not* met: Oct-20 rehearsals at `4adee846d3c` (green
  `39495874381`, probe `39495879106`, Full CI `39495882967`) all completed
  failure before evidence — identity inline-Python `SyntaxError` in both
  rehearsals, build-core setup-uv cache-glob failure in Full CI. Repair
  (close paren + contract test compiling the embedded command) exists only
  as local workspace changes at research time.
- **Source-containment gap (open DISCOVERED ISSUE #1 on `sase-1n6`, notes
  #1–#8).** The build passes `--core-source-pin` from `pyproject.toml` grep
  instead of `sase-core-revision.txt`; `seal_kwargs` accepts an arbitrary
  pin and `evaluate_manifest` only checks nonempty version/live file list.
  Reproduced: `core_source_pin="not-a-source-commit"` seals OK. Current
  pins (`6f354df4d96…`, then `ce6104b19c…`) are on sase-core `origin/master`
  but contained in no published tag (latest v0.42.1; sase-core PR #333
  OPEN). Qualification therefore cannot yet prove containment. Bounded
  ~36h next-daily-cut retry is the assigned path; keep the issue open until
  a tagged cut contains the pin.
- **`sase-1n6.6` digest-checked publish (blocked on .5).** Upload only
  missing files after digest checks, confirm every file + exact install from
  PyPI, run the family canary, then un-draft; resume mode re-enters at
  publish. Needs a new PyPI trusted-publisher entry keyed by workflow
  filename `release.yml` (human-gated) plus `pypi`-environment `v*` tag
  rule; `publish_existing` removal and old-version re-dispatch at tag come
  with it.
- **`sase-1n6.9` cutover to `release.yml` + steward merges (blocked on
  .5–.8).** Turn off `ci_watch` merging for sase, relax the Full-CI
  freshness rule only after qualification + publish confirmation are
  deployed. Plugin release merges stay on `ci_watch` (now protected by E1's
  floor check) until an optional later move.
- **`sase-1n6.10` first steward release + decision record.** Exit needs at
  least one real release through the steward with no human action beyond
  pre-authorized ones, PyPI digests + attestation SHA equal to the
  manifest, and every refusal naming a typed reason + owner. The
  `decisions:exact-release-pair` memory record plus partial supersession of
  `ci-two-speed-split` / `rust-core-required` is authorized but was not
  observed as written at research time.

### Developer-facing behavior changes from E2 so far

- `pyproject.toml` + `uv.lock` now declare `sase-core-rs==0.42.0` exactly;
  `just install-venv` works with and without `SASE_CORE_WHEEL`. A core
  security fix now waits for the next sase release (acceptable at 1–3-day
  cadence); no silent core drift inside an installed sase.
- Releases are tag-dispatched (`gh workflow run release.yml --ref vX.Y.Z`)
  with build-once, seal-manifest, stash-on-draft semantics; rehearse mode
  exists but only runs once the workflow is on `master`. Developers inspect
  via `release_candidate seal/verify/observe/show/evaluate`, `collect_ _
  qualification_jobs`, `exercise_release`, `release_metrics`.
- `release-please` drafts + force-tags (verified in vendored action
  source); tags are made at once so later runs still find the previous
  release. `publish.yml` is unchanged behaviorally until the E2.6 handover.
- The steward is currently observe-only: scheduled ticks report typed
  states, execute nothing, and escalate after 24h in one blocked state.
  `ci_watch` still merges sase release PRs today.

## E3 readiness verdict

**Ready to start, not ready to exit.** Concretely:

- Entry criteria from the design are satisfied: E1 is closed (family canary
  feeds E2's publish confirmation), and E3 is explicitly parallel to E2, not
  gated on E2's exit. The file-ownership map keeps E3 off E2's active files:
  E3 owns test infra, Master Gate *test steps*, `ci.yml` *test jobs*, the
  quarantine file, and `culprit-check.yml`; E2 owns `ci.yml` *inputs and
  checkouts*, `build-core.yml` ref plumbing, `release.yml`, and steward
  wiring. The one shared touchpoint (E2.3/E3.1 rerun helper contract) is
  ordered: E3.1 defines the input contract first.
- E3 exit is far off by design: it needs the mechanisms live plus a
  published false-red/escape baseline, while the under-3%-over-7-days soak
  is E6's entry bar, not E3's. Do not promise a soak as part of E3.
- Three E2 loose ends constrain E3's first slices: (a) the containment gap
  means "green rehearsal" cannot yet prove source containment — E3.5 must
  treat missing/incomplete evidence as red, not as green-to-bisect; (b) the
  unlanded identity-syntax repair blocks any deployed proof at a new SHA —
  E3 live proofs should not be coupled to the same SHA/gating until that
  lands; (c) `SASE_RELEASE_TOKEN` dispatch write-access and the PyPI
  publisher/`v*` rule are still untested/human-gated — E3 must not assume
  steward-triggered qualification runs exist yet.
- No capacity conflict was observed between E3 and the open E2 phases except
  `ci.yml`: E3.7 explicitly waits for E2.3 there, and two agents must never
  rewrite the same workflow concurrently.

## Starting design for E3 (from the design of record, grounded in this tree)

E3's decision record (to write with `/sase_memory_write` at epic start):
"CI reruns a failed node once and quarantines with an escalating expiry,"
next to `triage-annotates-does-not-change-exit-codes`. It does not change
ToolRun triage or receipts.

### E3.1 shared bounded-rerun helper — build first

- **Rule (from design):** rerun only when <=3 nodes fail, only once; never
  rerun collection errors, harness errors, or zero-test runs; keep the first
  attempt and emit `FLAKY:`; an isolated pass is diagnostic, not
  exoneration — track recovered signatures and escalate repeats; designate
  safety-critical tests that get no rerun.
- **Where it lives:** one helper consumed by Master Gate shards, `ci.yml`
  test jobs, qualification (`ci.yml` via E2.3 inherits it), and the publish
  smokes. Define the input contract before E2.3 consumes it (job inventory
  version, attempt-aware evidence fields, verdict vocabulary).
  Precedent in-tree: `collect_qualification_jobs` (440 lines) +
  `tools/_release_qualification*.py` already do attempt-aware evidence for
  qualification; generalize the rerun predicate, not the whole collector.
- **Verification:** planted flake recovers with `FLAKY:`; deterministic
  failure, collection error, and order-dependent failure stay red.
- **E3 readiness note:** the Oct-20 rehearsal failures are the negative
  controls — identity `SyntaxError` (harness/setup) and setup-uv cache-glob
  (setup, not test-only) must *not* be rerun-eligible under this rule.

### E3.2 escalating quarantine

- **Rule:** expiry fails a non-required hygiene check, raises the bead's
  priority, and appears in the digest; never fails admission; expiry is
  excluded from the shifted-clock run. Fixes the "time bomb" pattern where
  an expiry silently becomes a gate.
- **Start point:** no quarantine file exists today; create it as E3-owned
  alongside the rerun helper, with bead-escalation wiring (priority bump,
  not auto-assign) from day one.
- **Verification:** an expired entry fails hygiene only, the gate stays
  green, and the bead escalates.

### E3.3 parity

- **Rule:** `.python-version` = 3.12, fast fail on core-revision mismatch,
  `if: always()` only on reporting steps.
- **Start point:** audit `ci.yml`/`master-gate.yml` for `if: always()`
  misuse and for matrix legs that could drift from 3.12; add the
  core-revision mismatch fast-fail next to E2's exact-pin validator rather
  than inventing a second pin check.

### E3.4 drift canaries

- **Rule:** nightly gate run on the tip plus one run with time injected
  +30 days; inject time into the relevant tests, never shift the machine
  clock (breaks TLS/OIDC/caches).
- **Verification:** a planted time bomb fails the +30-day run while the
  gate stays green.

### E3.5 culprit attribution + `culprit-check.yml` — co-gates E4

- **Rule:** Master Gate already runs once per SHA and is never cancelled,
  so the first red SHA with a green parent is the suspect; a dispatchable
  `culprit-check.yml` confirms k-of-k at the suspect and k-of-k passing at
  its parent. Every red is labeled recovered / culprit / drift / unknown.
  Release-lane bisection starts from release-green (E2.8 record), never
  from an arbitrary green ancestor (green is not hereditary).
- **Start point:** no `culprit-check.yml` exists; it is new E3-owned
  workflow + tool surface. Reuse the release-green bookmark schema
  (`tools/_release_metrics.py`, exact-SHA green evidence) as the baseline
  input rather than building a second green-record.
- **Verification:** a planted break is labeled `culprit=<sha>` within one
  gate run plus the check; a flake is `recovered`; a time bomb is `drift`.
- **E3 readiness note:** until the containment gap closes, release-lane
  "green" from rehearsals without manifests must map to `unknown`, not to a
  baseline for bisection.

### E3.6 false-red digest + metrics

- Baseline: false-red rate with numerator/denominator, escape rate, red
  minutes per day, time-to-release-green (p90 < 6h target from E2.8),
  core-lag hours, burned versions. This baseline is the E6 go/no-go input
  (with E4's time-to-revert and escape rate), so define denominators now.
- Soak discipline: ~100 independent zero-failure observations bound the
  rate near 3%, but correlated runs weaken that — record the sampling
  method, not just the percentage.

### E3.7 visual-promotion study — last, after E2.3

- Default is no promotion; record the decision. Both E2.3 and E3.7 touch
  `ci.yml`, so serialize them.

## Risks, open questions, and what would reopen this assessment

- If `CORE_INCOMPATIBLE` recurs (newest core carries a break the pin has
  not absorbed), the design already prescribes cutting core releases at the
  pinned commit; E3 attribution must then distinguish "new core broke us"
  from "we broke against a fixed core."
- If burned versions exceed ~1/week, add a pre-merge preflight on the
  release PR head first, then tag-on-green — do not put the slow lane in
  the queue.
- If fewer than 2 of 3 nightly candidates qualify over 2 weeks after
  lockstep + reruns, adopt tag-on-green (Stovepipe / Google "cut at green").
- If false reds stay above ~10% after E3, delay E6 indefinitely; E1–E4
  still ship. If red time is already small at go/no-go (~<2% of minutes,
  no deterministic break reaching a release in 4 weeks), defer E6 with a
  reopen trigger; E5 still ships as a product feature.
- Confirm before E5 adapter work (not E3, but adjacent): whether GitHub's
  asynchronous merge API reached GA on 2026-10-01 as a replacement for
  `gh pr merge`; and whether `release-please-action@v5` bundles a
  release-please with `force-tag-creation` plus how it handles an `==`
  pin rewritten by the metadata step.

## Method, confidence, limits

- Inputs read for this report: the converged design via audited
  `sase artifact read` (full 1181-line doc, both halves); bead reads for
  `sase-1my`, `sase-1n6`, `sase-1n6.2/.3/.5/.6/.7/.9/.10`; `sase bead
  search` for E1/E2/E3/quarantine/bounded-rerun/culprit/revert; `git log`
  since 2026-10-19 with `--stat` on `110214f51c`, `befa41b575`,
  `cc59e6f114`, `54a9c14d23`, `812cdd9e21`; live-tree reads of
  `.github/workflows/{release,release-steward,install-smoke,
  release-dependency-floor,ci,master-gate}.yml`, `tools/` release surface,
  `pyproject.toml`/`uv.lock`/`sase-core-revision.txt`,
  `docs/contribute/release-train.md`, and the sase-core
  `.github/scripts/pypi_*.py` set. No swarm peer report was opened.
- High confidence: E1 closed with live proofs; E2 landed-vs-open split;
  exact-pin + canary + floor-check behavior; absence of E3 helper/
  quarantine/culprit-check in the current tree (`fail-fast: false` is the
  only related CI setting).
- Medium confidence (inherited from the design doc's own grading, not
  re-measured): 85% core-lag replay, 15–38h chain estimate, 73.6% vs 33.9%
  rerun figures, merge-limit semantics, Sigstore certificate fields.
- Not done: no workflow, bead, memory, or PyPI state was changed; nothing
  dispatched, merged, yanked, or filed; no live PyPI JSON re-check (design
  doc's 2026-10-18 live state is taken as given).

## Sources

- Design of record:
  `research:202610/pypi_release_reliability_design_and_work_split/pypi_release_reliability_design_and_work_split.md`
- Epic plans: `plans/202610/e1_installable_family.md`,
  `plans/202610/e2_release_train_steward.md`
- Beads: `sase-1my(.1–.6)`, `sase-1n6(.1–.10)`, `sase-1n6.5.1` lineage,
  `sase-1mk` Track 0 context
- Tree: `.github/workflows/release.yml` (904 lines),
  `release-steward.yml`, `install-smoke.yml`,
  `release-dependency-floor.yml`, `ci.yml`, `master-gate.yml`;
  `tools/release_candidate`, `tools/_release_core.py`,
  `tools/ratchet_core_pin`, `tools/exercise_release`,
  `tools/collect_qualification_jobs`, `tools/release_watch*`,
  `tools/release_metrics`, `tools/check_release_dependency_floor`;
  `docs/contribute/release-train.md`; sase-core
  `.github/scripts/pypi_retention.py` family.
