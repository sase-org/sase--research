# Best architecture for reliable SASE PyPI releases, and how to split the work

> **Research query:** Review the files agent `8y` tagged `pypi-release-reliability` in
> the research sidecar, then recommend the best design and a work split. Converging on
> the best architecture matters more than originality.

**Researcher:** `research.22.grk` · 2026-10-18 · sase `master` independently re-checked
the same day.

This report reviews the twelve tagged files, independently re-checks the live publish
path, PyPI, GitHub rulesets, CI, and the installability beads, and recommends one
architecture. It steals freely from those files. The recommendation is the
reassessment's four-epic program, with a small set of defects in that plan closed by
the Google comparison, the merge-queue primer, and the agent-testing note.

## Bottom line

1. **Keep the reassessment's architecture.** Fence `master` with GitHub's native merge
   queue (zero approvals, rebase, merge limit 1, build concurrency 2, `ALLGREEN`).
   Publish exactly the qualified release SHA through a candidate record. Make the gate
   trustworthy before enforcing the queue. Deliver as **four epics (A, B, C, D) plus
   Track 0**. Step 0 is already done.
2. **Treat three problems as three layers, not one "make master green" epic.**
   - **Installability.** `pip install sase` / `uv tool install sase` must install the
     newest release. Today it still silently resolves to **0.1.0**.
   - **Honest publishing.** Build, qualify, and upload one SHA. Today's `publish.yml`
     still checks out whatever `master` is when the job runs.
   - **Honest admission.** Nothing refuses a red landing. Master Gate still runs after
     the push. A currently-green tip is a window, not a fence.
3. **Fold eleven Google-inspired changes into those epics.** None of them reopens the
   queue, zero-approvals, rebase, or exact-SHA decisions. The two that are plan defects
   rather than extras: **flake-aware qualification** (otherwise Epic A refuses about
   half of good candidates) and **quarantine expiry that does not fail the required
   gate** (otherwise Epic B plants a calendar time bomb).
4. **Do not merge C and D.** C is a product feature proven on a sandbox. D is a
   one-time production cutover with human GitHub gates and a soak. Plan D now so it
   has an owner; start D only after B's mechanisms are live and C's sandbox suite
   passes.
5. **Ship Track 0 (0.18.0) on the existing beads.** Do not hold it for the queue.
   Land **A1 (exact checkout + digests + provenance-at-tag)** first if at all
   possible, because a Track 0 publish through today's `publish.yml` can still upload
   the wrong tree.

**In one line:** restore installability, then make every PyPI upload a qualified
candidate, then make the gate trustworthy, then land through a native queue that tests
the stacked result — as four epics, with the Google post-merge gaps closed inside those
epics.

## Corpus

Agent `8y` (2026-10-18) tagged twelve reports with `pypi-release-reliability` and
defined the tag in `TAGS.md`. Canonical files only; no `__<id>.md` files.

| File | Role in this recommendation |
| --- | --- |
| [`merge_queue_fenced_master_and_exact_sha_releases.md`](merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md) | Original plan: native queue, exact-SHA publish, gate trust first |
| [`merge_queue_fence_reassessment_and_epic_split.md`](merge_queue_fence_reassessment_and_epic_split/merge_queue_fence_reassessment_and_epic_split.md) | **Architecture of record.** Six requirement changes, N1–N13, four epics |
| [`merge_queue_fence_reassessment_explained.md`](merge_queue_fence_reassessment_explained.md) | Plain-language restatement of the same plan |
| [`github_native_merge_queue_primer.md`](github_native_merge_queue_primer/github_native_merge_queue_primer.md) | How GitHub's queue actually behaves; CI wiring; watcher; settings |
| [`merge_queue_impact_on_testing_agent_fixes.md`](merge_queue_impact_on_testing_agent_fixes.md) | Human loop after D5: ~15–30 min, landed notification, preview path |
| [`master_ruleset_step0_setup_steps.md`](master_ruleset_step0_setup_steps.md) | Step 0 procedure; **already executed** |
| [`sase_v0_18_0_pypi_release_status.md`](sase_v0_18_0_pypi_release_status.md) | Snapshot of the 0.18.0 blockage (Oct 13; numbers now stale) |
| [`google_release_engineering_vs_sase_release_plan.md`](google_release_engineering_vs_sase_release_plan/google_release_engineering_vs_sase_release_plan.md) | Post-merge gaps; eleven ranked plan changes |
| [`gastown_vs_sase_lessons_to_borrow.md`](gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow.md) | "Fences beat promises"; verify integrated tree; prove the SHA |
| [`gascity_advantages_over_sase_and_what_to_borrow.md`](gascity_advantages_over_sase_and_what_to_borrow/gascity_advantages_over_sase_and_what_to_borrow.md) | External proof a queue stays green (~37/38 vs SASE's then-red gate) |
| [`agent_factory_merge_discipline_reading_list.md`](agent_factory_merge_discipline_reading_list/agent_factory_merge_discipline_reading_list.md) | Scale argument; Stovepipe-style release ref; landing watcher as protocol |
| [`sase_sh_docs_redesign.md`](sase_sh_docs_redesign/sase_sh_docs_redesign.md) | Working install is a launch prerequisite; docs must match PyPI |

**Not tagged, noted and left aside:** `just_install_pypi_dev_venv_split/` (developer
install split, not the public release pipeline) and `sase_listen_first_pypi_release.md`
(plugin-first-release). They do not change the architecture.

All twelve tagged files were read through `sase artifact read`. `TAGS.md` is outside
the `research:` glob and was read from the opened sidecar.

## Independent live checks (2026-10-18)

These are this researcher's own reads, not copied from the tagged reports.

| Signal | This check | Implication |
| --- | --- | --- |
| PyPI `sase` latest | **0.17.1**, requires `sase-core-rs>=0.32.16,<0.33.0`, not yanked | Same outage as the tagged reports |
| PyPI `sase-core-rs` | Latest **0.41.0**, 51 versions, oldest **0.34.23** | The 0.32.x window is gone forever; only a new sase release repairs installs |
| `pyproject.toml` floor | `sase-core-rs>=0.35.0,<0.36.0` | HEAD still cannot install against current PyPI core 0.41.0 without a ratchet |
| `sase-core-revision.txt` | `72bf9203…` (moved since the reassessment's `916d5e3a`) | Core lag is a standing shape, not a one-commit incident |
| Release PR #299 | Still **OPEN**, `chore(master): release 0.18.0` | Track 0 is unfinished |
| `master` ruleset | **`master-integrity` active** since 2026-10-17T22:54Z; rules `deletion` + `non_fast_forward` only | **Step 0 is done.** Do not recreate it. Do not add queue rules to this ruleset |
| `publish.yml` `build` job | `actions/checkout@v4` with **no `ref`** | Still builds the tip at job time |
| `publish.yml` `publish` job | `skip-existing: true`, `environment: pypi`, trusted publishing, no digest compare | Partial retries can mix two builds |
| Install smokes in Publish | Ubuntu only; import, `core health`, `doctor`, `--help` | Nobody exercises a real workflow or macOS before upload |
| `.github/workflows/install-smoke.yml` | Daily `uv tool install sase` vs documented floor (sase-1le.3) | A6's canary already exists and is **supposed to be red** until 0.18.0 |
| Master Gate, last 10 | 5 newest **success**, then 5 **failure**; ~12 min | A green window, the same pattern Gas Town research called "green was reached but not held" |
| Full CI, last 8 | **4 success / 4 failure**, newest a failure | Qualifying "the latest Full CI" is still a coin flip; N1 is right |
| Beads | `sase-16p` READY, `sase-10d` READY, `sase-1jz` IN_PROGRESS | Track 0 and visual-lane repair already have owners |

The Oct 13 status note (`sase_v0_18_0_pypi_release_status.md`) is useful as a
pipeline map and stale as a scoreboard. Full CI has since gone green on some SHAs
and red on others. That is evidence for flake-aware qualification, not evidence
that the 6-hour `ci_watch` freshness rule is a good long-term gate.

## What the tagged files agree on

Every substantial report in the tag, plus Gas Town / Gas City as the reason the work
exists, agrees on this core:

- **The hole is the landing path.** The `builtin@commit` finalizer pushes to `master`.
  Master Gate reports breakage afterwards. Nothing refuses a red change. Repair epics
  go green for about a day and a half, then the tip reddens again.
- **PRs without a queue do not keep `master` green.** Each PR is tested against a stale
  base. "Require branches to be up to date" at ~43 landings/day is rebase churn.
- **Human approvals deadlock.** Agents push as the maintainer. GitHub will not let you
  approve your own PR. PRs are admission tickets, not review requests.
- **A host-side landing lane is the wrong fence.** Local `just check` is slow and red
  most of the time, and a lock on one machine cannot order athena against apollo. Gas
  Town's *mechanisms* (test the integrated tree, prove the SHA, dependents wait for
  merge) are the right borrow. Its LLM-judged merge and unwired bisect are not.
- **Releasing and keeping the tip green are separate goals.** A perfectly green Master
  Gate would still have published nothing while Full CI and the core floor were red,
  and while `publish.yml` built the wrong commit.
- **Exact-SHA publishing is non-negotiable.** Build once from the release commit,
  qualify that commit, upload those files, confirm by digest.
- **The gate must be trustworthy before it is enforced.** A 30–40% false-red rate
  turns a queue into a random ejector. Target under 3% false reds per gate build.
- **Capacity is not the binding constraint.** Measured runner waits and a K=2
  simulation put landing around 13 min p50 / 27–34 min p95 if false reds stay ≤10%.
  Flakes, not runners, bind.
- **Code placement follows the Rust-core boundary.** The landing record lives in
  `sase_core`. The GitHub adapter lives in `sase-github`. Python/TUI consume. The
  reconciler is deterministic: no LLM verdict on merges.

The last year of factory-merge reading (Uber Stovepipe, Anthropic's two-speed
monorepo vs Claude Code repos, Mergify TLA+) backs the same shape at sase's volume.
Anthropic dropped a *global* queue at tens of thousands of merges a day. SASE is at
~43. Claude Code still re-runs checks against main with the change applied. That is
the regime sase is in.

## What the tagged files changed, and what I keep

The original same-day plan and the reassessment disagree in six places. I keep the
reassessment on all six, with the Google report's repairs applied on top.

| Topic | Original | Reassessment | This recommendation |
| --- | --- | --- | --- |
| Merge method | Merge commits (April 2026 incident named squash) | **Rebase**, linear history; squash fallback | **Rebase.** June changelogs duplicated three entries and dropped one under merge commits. Today's history is already linear. Merge limit 1 covers the incident's "groups of more than one PR" |
| Installability | Unmentioned | **Requirement zero:** retention invariant + daily canary + train *creates* the core release | Keep. Independently confirmed still broken |
| Drift / red base | Unmentioned | Witness, circuit breaker, queue jump, +30d clock canary | Keep. A red base fails every merge group |
| Landing mode | Feature flag | **Per-project config** `landing.mode: push \| queue` | Keep. Flag rules forbid forever-choices as flags. Default stays `push` until D5 |
| When beads close | On proof of merge | Close as today; **`delivered(bead)`** gates dependents | Keep. Templates and the finalizer close during the turn |
| What blocks a release | Implied: Full CI | **N1 inventory:** admission / release-blocking / advisory | Keep. Live Full CI is 4/8 green; using it as a merge-and-release club is what stalled PyPI |
| 0.18.0 | In Phase 0 | **Track 0**, existing beads | Keep. `sase-16p` / `sase-10d` / `sase-1jz` already own it |
| Epics | Phases 0–3 in one program | **A, B, C, D** plus Step 0 and Track 0 | Keep four. See [work split](#recommended-work-split) |

I also keep these reassessment requirements as written: N2 (linear history + SHA
mapping, because rebase rewrites the agent SHA), N5 (event-aware `integration-ready`
aggregate), N6 (SHA-keyed qualification, never `ci-${{ github.ref }}` with
cancel-in-progress), N7 (durable landing protocol, turn ends at **armed**), N8 (pilot
merge limit 1), N9 (ordinary rollback keeps the fence; never relax force-push /
deletion), N10 (`sase/master` only; core lands before the dependent PR is armed),
N11 (human-gated GitHub changes), N12 (one owner per goal; tag ruleset waits), N13
(acceptance, not calendars).

The primer supplies the GitHub facts the plan must not get wrong:

- Required checks run under the **same names** on `pull_request` and `merge_group`.
  A job skipped by `if:` reports Success. A workflow skipped by `paths:` stays
  Pending. The dangerous case is `if: github.event_name == 'pull_request'` on a
  required job.
- `GITHUB_SHA` on `merge_group` is the group commit. Do not check out
  `pull_request.head.sha`.
- Observed in Homebrew and github/docs: **landed SHA = tested group SHA**. Assert
  it in the watcher; docs do not promise it.
- Suggested pilot settings match github/docs: MERGE-or-rebase, concurrency 2,
  merge 1, `ALLGREEN`, 60-minute timeout. For sase: **rebase**, not merge.
- Queue rule plus sibling rules (require PR with 0 approvals, restrict updates,
  empty bypass). Probe on the sandbox, not on production `master`.
- **A ruleset bypass list exempts every rule in that ruleset.** Put queue rules in
  a **separate** ruleset from `master-integrity`, or D2's maintainer bypass silently
  relaxes N9. The Step 0 note already inferred this; make it a hard constraint.

## Defects in the reassessment that must be closed before coding

The Google comparison is the only tagged file that found defects *in the plan as
written*, not just gaps versus an ideal. I adopt the ones that fail a "would this
make A or B false on day one?" test.

### Must-fix (plan bugs)

1. **Qualification is all-or-nothing and flake-blind (Google rank 1).** Full CI ran
   six times on unchanged SHA `ae9f044bb3` and passed three. Each red job failed one
   or two of ~56k tests, different tests each time. Nothing in `ci.yml`,
   `master-gate.yml`, or the justfile reruns a failed test. Epic A's "publish only if
   the blocking set is green" would refuse about half of good candidates. **Apply B1's
   bounded in-job rerun to every release-blocking `ci.yml` job in A2.** A node that
   fails twice still blocks publication.
2. **Quarantine expiry fails the required gate (Google rank 4).** B2 as written:
   expired quarantine entries fail lint, and lint is a required gate job. Every
   15-day expiry then fails every merge group, and B4's +30-day shifted-clock canary
   flags every live entry as a time bomb. **Expiry escalates (hygiene check, bead
   priority, digest) and never fails admission. Exclude expiry from the shifted-clock
   run.**
3. **Exact checkout without tag-triggered upload makes provenance false (Google
   rank 7).** Trusted-publishing attestations name the commit that *triggered* the
   workflow. `publish.yml` is scheduled on `master`. After A1 checks out the release
   SHA, the attestation usually certifies a later commit that was never built.
   **Run the uploading job at the tag ref. Restrict the `pypi` environment to `v*`
   tags. After publish, check each attestation's source digest.**

### Should-fold (same epics, real user risk)

4. **Nobody runs the artifact users install (Google rank 3).** Today's smokes prove
   import on Ubuntu. The 0.1.0 outage lasted weeks because nothing asserted "the
   newest PyPI version starts and speaks". Install the candidate wheel **and** sdist
   from the built files (deps from public PyPI), run a short no-LLM exercise (`sase
   core health`, a real CLI workflow, a headless TUI frame), on **`ubuntu-latest` and
   `macos-latest`**. Keep the existing daily public-install canary (`install-smoke.yml`)
   and have it assert the expected version.
5. **A version is claimed before it is qualified (Google rank 5).** release-please
   currently cuts at true head and tags on merge. A failed qualification still leaves
   a public GitHub release. **Now:** `draft: true` + `force-tag-creation: true`;
   un-draft after PyPI confirmation. **In D:** run the release-blocking set on the
   release PR's `merge_group` so a red candidate never lands. Spike tag-on-green
   (Stovepipe / Google "cut at green") with an adoption trigger of fewer than two in
   three nightly candidates qualifying over two weeks.
6. **There is no undo (Google rank 6).** Yank-then-fix-forward runbook;
   `release_watch` proposes yanks through `/sase_gate`; yank the uninstallable window
   (and 0.1.0 if it is outside the support horizon) so a broken latest fails loudly
   instead of silently resolving to February. Drill on TestPyPI. A maintenance-branch
   hotfix lane is a spike, not a blocker.
7. **Release-blocking checks have no post-submit owner (Google rank 2).** Keep the
   3.13/3.14 + packaging class on the 2-hour Full CI tick. Do **not** take D4's
   "maybe nightly" option for this class; advisory checks may go nightly. Add a
   deterministic culprit finder using A2's `ref` input. Revert-first through the
   queue once D exists; until then, one build-cop turn. Replace the 48-hour clock
   with a time-to-release-green SLO (p90 under 6 h); 48 h is human escalation only.
8. **Agent-done is not testable-done (testing-impact note).** After D5 the human
   waits ~13–30 min. Add a **landed notification** and a visible armed/queued/landed/
   ejected state on the agent row (Epic C). Add a **preview command** that runs sase
   from a throwaway worktree at the PR head; never check the PR out in the primary
   tree, because rebase rewrites the SHA and `sase dev update` only fast-forwards.
   Measure V-D4 from agent-finish to testable, not from queue entry.

### Later / cheap hardening

9. Release-health consequence (Google rank 8): while the public install canary is
   red, hold packaging/dependency landings via the N3 hold; the fix jumps the queue.
10. Downgrade contract (rank 9): N's durable state is readable by N−1, or N−1
    refuses loudly. Follow-up if it does not fit A2.
11. Pin toolchains and bake SHA/core/candidate into `sase version --json` (rank 10).
12. Instability metrics in the B5 digest (rank 11): lead time to PyPI, change-fail
    rate, recovery time, time to release-green, gate escape rate.

### Explicitly do not copy

From Google: required human review, percentage rollouts, affected-test selection, a
monorepo, a release branch for every release, push-on-green for every build,
stop-the-line on any red.

From Gas Town: LLM-judged merges, batch-then-bisect (unwired at the source),
tmux/role supervisors, inboxes without expiry.

From earlier researchers: host landing lane as the production fence; required PRs
without a queue; "up to date"; folding `visual-test` into the gate by default;
deleting production `master` as a test; a long-lived beta flag named "master
fenced"; merging A into the queue epics.

## The architecture

```text
                    ┌─────────────────────────────────────────┐
                    │  Track 0  restore pip install sase      │
                    │  existing beads: sase-16p, sase-10d,    │
                    │  sase-1lh chain, sase-1jz (green proof) │
                    └─────────────────────────────────────────┘
 Step 0 DONE        A, B, C in parallel
 master-integrity   ┌────────────┐  ┌────────────┐  ┌──────────────────┐
 force-push/delete  │ Epic A     │  │ Epic B     │  │ Epic C           │
                    │ exact SHA  │  │ trustworthy│  │ queue landing    │
                    │ candidate  │  │ gate       │  │ as a product     │
                    │ + install  │  │ rerun,     │  │ feature, sandbox │
                    │ guards     │  │ quarantine,│  │ only             │
                    │            │  │ drift      │  │                  │
                    └─────┬──────┘  └─────┬──────┘  └────────┬─────────┘
                          │               │                  │
                          │         B mechanisms live        │
                          │               └────────┬─────────┘
                          │                        │
                          └──────────►  Epic D  ◄──┘
                                     cut sase/master over
                                     (human gates at D2, D5)
```

### Layer 0 — Installability (Track 0 + A5 + A6)

Users and the sase.sh front door. `uv tool install sase` must install the documented
version and `sase core health` must pass.

- Cut a `sase-core-rs` release that contains the current pin.
- Ratchet the published floor on the release PR (already happening on #299; keep
  doing it).
- Publish 0.18.0. Prefer A1 in production first; if Track 0 publishes through
  today's job, download from PyPI and compare version + commit with the tag.
- Retention: `pypi_retention.py plan` never deletes a `sase-core-rs` version inside
  the declared range of the last N ≥ 2 published sase releases, and fails closed
  when it cannot compute that set. This is the actual cause of the outage (epic
  `sase-13t` deleted the 0.32.x window after grepping *checkouts*, not frozen
  published metadata).
- Daily canary: already present as `install-smoke.yml`. Keep it. A red canary is
  the signal, not a thing to skip.

Do not wait for the queue. Do not wait for visual-test to be perfect. N1 already
makes visual advisory. `sase-1jz` continues as the visual-lane owner; it is not a
release-merge blocker.

Docs (`sase_sh_docs_redesign.md` R0): do not launch a new sase.sh front door while
the first command installs 0.1.0. A version line on the home page is enough once
0.18.0 exists.

### Layer 1 — Honest publishing (Epic A)

Given a SHA, publish exactly that SHA's qualified files, or refuse.

Candidate record, threaded through every checkout including nested `build-core.yml`:

- version, tag, peeled SHA
- tree and core pin
- policy version (the N1 inventory)
- run IDs and attempts
- artifact sha256 digests

Rules:

- Retries resume with the original qualified files.
- An existing PyPI filename is accepted only on digest match. `skip-existing`
  without that check is how two builds mix.
- A rebuild is a new candidate and must be qualified again.
- Tags never move.
- Upload runs at the tag ref so attestations name the qualified SHA.
- After publish: download, compare digests, clean install of that version.

Release-blocking set (N1), on that SHA, with B1 reruns:

- Master Gate contents (already implied by a gate-green SHA)
- install smokes on the **built** wheel and sdist
- core-floor smoke
- `test (3.13)` and `test (3.14)` (the wheel declares those versions)

Advisory, run on every candidate, file a `ci` bead, 48 h then SLO:

- `visual-test`, `perf-floors`, `tutorial-tests`, `ace-page-group-isolation`

The train *requests* the sase-core release it needs (`CORE_LAG`), instead of dying
at `CORE_FLOOR_BLOCKED`.

`release_watch` states: prepared, qualifying, failed, qualified,
publishing/partial, published-and-confirmed. Lookups by workflow + event + SHA,
never "latest green on master". A GitHub release alone is not delivered.

### Layer 2 — Honest admission (Epic B, then C, then D)

**B, on today's push-triggered Master Gate.** Bounded rerun (≤3 nodes, once,
serial; never collection/harness/zero-tests). Expiring quarantine that does not
fail lint. `.python-version` = 3.12. Fail fast on core-pin mismatch. Nightly tip
canary plus +30 d clock canary with quarantine expiry excluded. Weekly false-red
digest with numerator, denominator, adjudication. Visual promotion is a measured
study against the 20-minute per-job contract; default is no.

**C, as a SASE product feature, proven only on a sandbox repo.** Core landing
record and `delivered(bead)` in `sase_core`. sase-github adapter: idempotent PR
by operation ID; arm with `expectedHeadOid` / `--match-head-commit`; treat
`gh pr merge` exit 0 as **armed**, not merged. Finalizer under `queue`: record
intent, push `sase/land/<op>`, one-commit PR, arm, end the turn. Deterministic
reconciler (axe chop, no LLM). Ejection classes: conflict / flake / deterministic
/ red-base (red-base needs a witness; no repair turn). Circuit breaker after 3
identical ejections: hold admission, one build-cop, one notification. Sandbox
ruleset: rebase, linear history, K=2, merge limit 1, event-aware aggregate.
Landed notification + preview worktree belong here so D5 does not surprise the
human loop.

**D, production cutover of `sase/master` only.** `merge_group` trigger + N5
aggregate on Master Gate. Drop `ci.yml`'s ordinary `pull_request` trigger. Keep
the push-triggered gate as a named audit until V-D3 holds. Enable the queue in a
**second** ruleset (not `master-integrity`), maintainer on bypass for the pilot.
Pilot allowlist: docs, `toobig`, ratchets, from both hosts. Enforce only when
false-reds are under 3% over ≥7 days with a declared sample. Empty bypass. Set
`landing.mode: queue`. Nightly train: core step → arm release PR → qualify →
publish → confirm. Decision record supersedes the merge-queue *clause* of
`ci-two-speed-split` **on the merits** (a queue produces a per-SHA signal and
fits capacity). Do not claim the record's reopen trigger fired: gate p50 is
~12.5 min against a ~17 min arrival gap. Also record: "CI is alerting" (required
checks guard user invariants; 100% green is not a goal) and "a PyPI release never
waits on an unfinished flag".

sase-core, plugins, and chezmoi keep today's landing mode until a later, separate
decision.

## Recommended work split

### Already done — do not re-open

**Step 0.** `master-integrity` ruleset, active, `master` only, empty bypass,
`deletion` + `non_fast_forward`. Verified by API read-back. Destructive tests stay
on the sandbox. When D2 arrives, put queue rules in a new ruleset.

### Track 0 — restore installability (existing beads, start now)

**Owner beads:** `sase-16p`, `sase-10d`, the `sase-1lh` chain, with `sase-1jz` as
the visual-lane epic that unblocks a *policy* Full CI, not as a merge fence.

**Critical path:**

1. Publish a `sase-core-rs` that contains the current pin (today `72bf9203…`;
   this number moves — always re-probe).
2. Ratchet #299's floor to a complete, unyanked core release.
3. Get one gate-green release commit. Today's Master Gate is in a green window;
   treat it as perishable.
4. Publish 0.18.0. Prefer waiting hours for A1. If user-installability wins, merge
   #299 and dispatch `publish.yml`, then verify tag SHA vs uploaded metadata by
   hand.

**Exit:** in a clean environment, `uv tool install sase` reports the new version
and `sase core health` passes. The existing `install-smoke.yml` turns green.

**Out of Track 0:** the queue, quarantine, landing records, docs IA.

### Epic A — exact-candidate releases and install guards

**Repos:** sase; sase-core for retention. **Size:** medium–large. **Start:** now.
**Decision record:** "PyPI publishes exactly the qualified release SHA."

| Phase | Work | Google / other folds |
| --- | --- | --- |
| A1 | Export SHA/tag/version from the successful release-please retry. Checkout that SHA. Assert tag = SHA = pyproject = `__version__`. Build wheel+sdist once, record digests. Upload job at the **tag** ref. Restrict `pypi` env to `v*` | ranks 7, 10 (identity in `sase version --json` if cheap) |
| A2 | `ci.yml` `ref` input through every checkout and `build-core.yml`. Qualify the N1 blocking set on that SHA. Bounded rerun on blocking jobs. Wheel **and** sdist smokes. macOS + Ubuntu exercise. `qualify-<sha>` concurrency, `cancel-in-progress: false` | ranks 1, 3; N6 |
| A3 | Replace `publish_existing` with an explicit tag. Resume from retained artifacts. Digest-match `skip-existing`. Never retag. Confirm download+install. Yank runbook + TestPyPI drill | ranks 6, 7 |
| A4 | `release_watch` candidate states; SHA lookups; draft GitHub releases until confirmed | rank 5 (draft now) |
| A5 | `CORE_LAG` + request core release. Retention invariant, fail closed | — |
| A6 | Keep/extend `install-smoke.yml`; assert version == latest; `sase core health` | rank 3 (public canary) |
| A7 | Decision record and docs | — |

**File ownership:** `publish.yml`, `ci.yml` `workflow_call` inputs and checkouts,
`build-core.yml` ref plumbing, `tools/release_watch*`, sase-core
`pypi_retention.py`.

**Verification:** the reassessment's V-A1–A8, plus: planted flake in `test (3.14)`
recovers; planted deterministic failure blocks; attestation names the release
commit after `master` has moved; a macOS exercise failure withholds.

**Does not need:** a green gate, a queue, or 0.18.0 to have shipped — except A6's
canary, which is expected red until Track 0.

### Epic B — a trustworthy gate

**Repo:** sase. **Size:** medium. **Start:** now.
**Decision record:** "CI reruns a failed node once and quarantines flakes with an
expiry", beside `triage-annotates-does-not-change-exit-codes`.

| Phase | Work | Folds |
| --- | --- | --- |
| B1 | Bounded rerun as reassessment | Shared mechanism with A2 |
| B2 | Expiring quarantine; **expiry does not fail lint** | Google rank 4 |
| B3 | `.python-version` = 3.12; core-pin fail-fast | — |
| B4 | Nightly tip + +30 d clock; expiry excluded from the clock run | rank 4 |
| B5 | False-red digest + DORA-ish release metrics | rank 11 |
| B6 | Visual promotion study; default no | N1 |
| B7 **new** | After A2: culprit finder on the release-blocking class; keep 2 h cadence for that class; time-to-release-green SLO | Google rank 2 |

**Out of scope:** queue wiring, gate triggers, Full CI cadence for advisory jobs
(D). `sase-1jz` continues independently; B6 consumes its measurements.

**File ownership:** test infrastructure, Master Gate *test steps*, quarantine
file. Not Master Gate triggers (D).

**Exit:** mechanisms live and a published baseline. The 7-day <3% soak is **D5's
entry criterion, not B's exit**.

### Epic C — queue-aware landing as a product feature

**Repos:** sase-core, sase-github, sase, plus a public sandbox in `sase-org`
created by a human (N11). **Size:** extra-large. **Start:** now.
**Decision record:** "Landed is a host-owned state distinct from turn completion",
refining `host-owned-completion`.

Phases C1–C6 as the reassessment wrote them, plus:

- **C3b.** Landed notification and armed/queued/landed/ejected on the agent row.
- **C3c.** Preview command: throwaway worktree at PR head.
- **C2 fix.** `_submit_via_pr_merge`: exit 0 means armed.
- **C4 waits.** Every `%w(bead=…)`, epic-segment wait, blocker/ready, land-agent
  check uses `delivered(bead)`.
- **C6 harness** settles the primer's unknowns: landed SHA vs group SHA under
  rebase + merge limit 1; whether "require merge queue" alone blocks direct
  pushes; bypass-actor push vs `gh pr merge --auto`; skipped jobs as required
  checks; `jump` permissions; workflow triggers for maintainer-authored PRs.

**File ownership:** finalizer, waits, sase-core landing record, sase-github.
Move `sase-core-revision.txt` when the wire/API lands.

**Nothing in C touches `sase/master`.** Config default remains `push`. Any `beta`
flag dies before C's exit.

### Epic D — cut `sase/master` over

**Repos:** sase (triggers, aggregate, `release_watch`), `bugyi-chops` (`ci_watch`),
chezmoi (`sase_athena.yml`), GitHub settings via `/sase_gate`.
**Size:** medium, two human gates, a soak.
**Entry:** B mechanisms live, C sandbox suite green. **Plan D on day one** so the
land agent owns the cutover.

| Phase | Work | Human? |
| --- | --- | --- |
| D1 | `merge_group` + N5 aggregate on Master Gate; drop ordinary `ci.yml` `pull_request`; keep push gate as named audit | no |
| D2 | Allow auto-merge and rebase; delete-branch-on-merge. **New** ruleset: require queue (rebase, K=2, merge limit 1, `ALLGREEN`, 60 min), linear history, `integration-ready`. Maintainer on bypass. Leave `master-integrity` untouched | **yes** |
| D3 | Allowlist pilot from both hosts; measure ejection classes, p50/p95, runner wait, `merge_group` false-red; prove SHA mapping | no |
| D4 | Writer/credential matrix (J). `ci_watch` arms with rebase, looks up by SHA. Optional: release-blocking set on the release PR's `merge_group` (rank 5). Advisory Full CI may go nightly; blocking class stays 2 h | no |
| D5 | Entry: <3% false red over ≥7 days + declared sample. Empty bypass. `landing.mode: queue` | **yes** |
| D6 | Retire heavy push audit once V-D3 holds. Nightly train. Build-cop + 48 h human page. Decision records. Incident runbook. Installability hold (rank 8) | no |

**File ownership:** Master Gate *triggers* and aggregate, `ci.yml` `pull_request`
trigger, `ci_watch`, GitHub settings.

**Production verification:** V-D1–D7 from the reassessment, with V-D4 measured
from agent-finish to testable.

### Decision records to write (owned by the epic that makes them true)

1. **A:** "PyPI publishes exactly the qualified release SHA."
2. **B:** bounded rerun + expiring quarantine, beside
   `triage-annotates-does-not-change-exit-codes`.
3. **C:** landed ≠ turn completion, refining `host-owned-completion`.
4. **D:** "`master` lands only through the merge queue", superseding the queue
   clause of `ci-two-speed-split` on the merits, plus "CI is alerting" and
   "releases do not wait on unfinished flags".

Keep two-speed CI. The fast gate remains the admission check. The exhaustive lane
stays off the push path. What changes is that **release no longer waits on "some
recent Full CI somewhere on master"**; it waits on the N1 blocking set on **this
SHA**, with flakes rerun.

### Ordering and conflict avoidance

```text
A1  ──►  Track 0 publish   (if A1 misses, verify after the fact)
A2  ──►  B6 (both touch ci.yml; B6 after A2)
A2  ──►  B7 culprit finder
B live + C exit  ──►  D start
A2+A3 deployed   ──►  relax ci_watch's "fresh Full CI on some SHA" rule
                         (not before: otherwise a window with neither protection)
D5               ──►  only after soak evidence, never by calendar
```

Parallelism is real: A, B, and C do not share files if the ownership table is
honored. D is serial behind B and C and is the only epic that changes how
`sase/master` moves.

### Why four epics, not three or one

- **One epic** holds 0.18.0 and exact-SHA publishing hostage to a week-long soak
  and two human GitHub gates. Single-turn agents cannot sit in that epic.
- **Three (C+D merged)** mixes sandbox proof with production proof, keeps C's
  scaffolding alive through the pilot, and turns a reusable product feature into a
  one-off cutover. The "cutover needs an owner" risk is cheaper as "plan D now".
- **Splitting C by repo** leaves an unverifiable core record or an adapter with
  no waits.
- **Merging A and B** mixes an urgent user outage with a weeks-long flake program.

If the project later insists on three, merge **C and D only**, keep A separate,
and never call a flagged queue mode "`master` fenced".

## What would change this recommendation

| If… | Then… |
| --- | --- |
| Sandbox shows a bypass actor cannot push to a queue-protected branch | Merge D2 and D5 into one hard cutover; keep the entire pilot on the sandbox |
| Rebase misbehaves in the queue | Squash. Return to merge commits only after changelog tooling and first-parent tools are fixed |
| False reds stay above ~10% after B | Delay D indefinitely. A, B, and C are still worth shipping |
| Automatic core release is unreliable | Gate refuses any change whose core pin is unpublished |
| Fewer than two in three nightly candidates qualify for two weeks | Adopt tag-on-green (Stovepipe / Rapid "cut at green") |
| Queue waits blow up epic wave time | New decision on batching; do not silently raise merge limit |

## Confidence and limits

**High confidence (read in this turn):**

- The twelve tagged reports, via `sase artifact read`.
- `publish.yml` checkout, smokes, `skip-existing`, `pypi` environment.
- Live PyPI JSON for `sase` 0.17.1 and `sase-core-rs` 0.41.0 / 51 versions /
  oldest 0.34.23.
- Live ruleset `master-integrity` (`deletion`, `non_fast_forward`).
- PR #299 still open.
- Master Gate and Full CI run lists for 2026-10-18.
- Beads `sase-16p`, `sase-10d`, `sase-1jz`.
- `install-smoke.yml` already encoding the docs/install disagreement.
- `ci-two-speed-split` still accepted, with a merge-queue rejection that a new
  record must supersede on the merits.

**Medium confidence (from the tagged files, not re-simulated here):**

- Queue latency simulation (13 / 27–34 min). Treat as D3 hypotheses.
- Full CI 3-of-6 flake rate on `ae9f044bb3` (Google report, 2026-10-18). Today's
  4-of-8 Full CI mix is consistent with that shape.
- Landed SHA = group SHA under rebase (primer measured merge and squash; C's
  V-C9 must prove rebase + merge limit 1).

**Not done:** no ruleset, workflow, bead, or plan was changed. No CI was
dispatched. No package was yanked or published.

## Sources

**Tagged research (audited reads):** the twelve files in [Corpus](#corpus), plus
`TAGS.md` from the opened research sidecar.

**Live / checkout, 2026-10-18:**

- `.github/workflows/{publish,master-gate,full,install-smoke,ci}.yml`
- `pyproject.toml` (`sase-core-rs>=0.35.0,<0.36.0`)
- `sase-core-revision.txt` (`72bf9203…`)
- `sase/memory/decisions/ci-two-speed-split.md`
- PyPI JSON: `sase`, `sase/0.17.1`, `sase-core-rs`
- `gh api repos/sase-org/sase/rulesets`,
  `…/rules/branches/master`
- `gh pr view 299 -R sase-org/sase`
- `gh run list` for Master Gate and Full CI
- `sase bead read sase-16p`, `sase-10d`, `sase-1jz`

**Prior decisions this program writes beside, not against:**
`host-owned-completion`, `receipts-prove-before-they-skip`,
`triage-annotates-does-not-change-exit-codes`, `check-full-is-explicit`,
`rust-core-required`, `sase_flags.md` (no forever-flags).
