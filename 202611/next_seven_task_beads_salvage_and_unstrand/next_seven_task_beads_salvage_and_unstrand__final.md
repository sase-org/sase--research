# The next seven task beads: salvage what already landed-in-name, then unstrand the fleet

Consolidated report, 2026-11-11. Lead researcher merging five independent swarm reports
(`cdx`, `cld`, `grk`, `mus`, `gem`; all in this directory) plus the lead's own
verification pass run ~22:00 EST on apollo against sase master `671ff5bde0`
(release 0.19.0). The lead re-ran the decisive reproductions and adjudicated every
cross-report conflict before ranking; the verification log is in
[Lead verification](#lead-verification-what-i-re-checked-myself).

## Bottom line

Work these seven ready, unassigned task beads, in this order:

| # | Bead | Type · size | One-line reason |
|---|------|-------------|-----------------|
| 1 | **sase-zo** | bug · S · +10 | `sase repo list -p sase` still exits 2 on master; the complete, verified fix sits uncommitted in athena `sase_21` — salvage it before workspace retention eats it |
| 2 | **sase-1re** | bug · M · +1 | Done monitors with stale `followup_pending` own their beads forever; the only bead all five researchers ranked — it blinds the stranded-work detector the whole fleet depends on |
| 3 | **sase-1s2** | bug · S | Importing a runner module overwrites the process-wide SIGTERM handler; reproduced independently in fresh interpreters by two researchers |
| 4 | **sase-1o1** | bug · L | Continuation capture nests fork ancestry superlinearly; a live athena land session is already at 708 KB vs the 256 KiB cap — long land/monitor sessions dead-end when it hits |
| 5 | **sase-1qm** | bug · L | Host completion refuses checks that passed (`stale_worktree_fingerprint`); recurrences are rising (5 in Oct → 11 so far in Nov) and each one discards a 30–60 min green `just check` |
| 6 | **sase-1qi** | bug · M | `sase agent restart` cannot find crash-killed agents without `done.json`; its deferral behind Agent Hijack has expired, and boot recovery needs this primitive on day one |
| 7 | **sase-1db** | bug · M | The attachments-private store never verifies an existing remote is actually private before pushing bytes; disclosure is the one failure here that cannot be repaired after the fact |

Alongside the seven, one **owner action** dominates everything below rank 1 in
cost-benefit: **resume epic `sase-1ra`** (`sase bead work sase-1ra`) after trimming
`sase-1ra.11.1`'s stale gates. No `sase-1ra` agent has been live since athena's 11-07
reboot. Resuming it covers reboot recovery (`sase-1qj`), the zombie-epic invariant
(`sase-12u`), the remaining `sase-1r4` halves, and lets its land agent close roughly ten
beads that are already fixed on master but still listed `ready`. That is why those beads
do not occupy ranked slots here.

## How five lists became one

The researchers converged far more than their headline lists suggest. Their
disagreements were almost all about *ownership* (is a bead already covered by a live
epic?) and *evidence freshness* (does it still reproduce?). The lead resolved those with
fresh measurements rather than vote-counting.

Consensus matrix (rank in each researcher's list; `HM` = honorable mention, `✗` =
explicitly excluded, `–` = not discussed):

| Bead | cdx | cld | grk | mus | gem | Consolidated |
|------|-----|-----|-----|-----|-----|--------------|
| sase-zo | – | 1 | 1 | – | – | **1** |
| sase-1re | 3 | 7 | 4 | 1 | 7 | **2** (5/5) |
| sase-1s2 | 2 | ✗ | 3 | HM | 4 | **3** |
| sase-1o1 | HM | 2 | – | – | – | **4** |
| sase-1qm | ✗ | 6 | – | 2 | 1 | **5** |
| sase-1qi | – | – | 2 | 5 | – | **6** |
| sase-1db | 1 | ✗ | – | – | 6 | **7** |
| sase-1kp | 5 | – | – | 4 | ✗ | HM |
| sase-1nc | ✗ | 4 | ✗ | – | ✗ | HM |
| sase-1qj / sase-12u | ✗ | 3 / 5 | ✗ | ✗ | – | owner action |
| sase-1qr | 4 | – | HM | HM | – | ride-along w/ #6 |
| sase-1em | ✗ | ✗ | 7 | – | – | HM |
| sase-1ot | ✗ | – | ✗ | – | 2 | excluded (owner-rejected) |
| sase-1ce | ✗ | ✗ | ✗ | – | 5 | excluded (fixed on master) |
| sase-1s4 | ✗ | ✗ | HM | – | 3 | HM |

### Conflicts and how they were settled

- **sase-1ot (historical secret purge).** `gem` ranked it #2 claiming owner approval via
  gate `custom-57bc7a62`. The lead read the bead: the durable +1 from
  `sase-1ou.5.1.land` (2026-10-28) records gate `custom-b52a9f2c` with
  `outcome=owner_reject`, `rewrite_attempted=false`, and "future work only if the owner
  requests renewed remediation." A 2026-11-04 note additionally requires re-auditing
  under scanner rules v2 first (v2 alone superseded 15 v1 false-positive blocks).
  `gem`'s gate citation is stale; `cdx` was right. **Excluded — owner-gated, not agent
  work.**
- **sase-1ce (editor draft deletion).** `gem` ranked it #5; `cdx`, `cld`, and `grk` all
  verified the fix landed (`522b07a009`, 2026-11-04), and the lead confirmed that commit
  is on master. **Excluded — verify-and-close, don't work.**
- **sase-1o1 (continuation-capture growth).** `cdx` held it in reserve because "measured
  sessions had not yet reached the cap." `cld`'s same-day measurement supersedes that: a
  live bob-cli land session member carries a 708,391-byte `authored_local_request`
  against a validator cap of 262,144 bytes (re-confirmed by calling
  `validate_agent_delta` through the installed binding), on a trend of 126 KB (Oct 24) →
  254 KB (Nov 6) → 708 KB (Nov 11). Newer evidence wins. **Ranked #4.**
- **sase-1s2 (SIGTERM at import).** `cld` deferred it to the live contention epic
  (`sase-1rq`). But `cdx` found the contention epic explicitly filed this bead as a
  *separate* follow-up outside its completed local repairs, and the lead's fresh agent
  list shows every `sase-1rq` member WAITING, none editing this surface. **Ranked #3.**
- **sase-1qm (phantom fingerprint refusal).** `cdx` excluded it as "cause unconfirmed."
  That is true of the root cause, but `cld` added two fresh sase recurrences (11-07,
  11-10), seven bob-cli refusals this month, and a rising monthly count — frequency and
  cost are confirmed even though the mechanism is not. Confirmed recurring waste
  outranks root-cause certainty for ranking purposes. **Ranked #5.**
- **sase-1qj / sase-12u (reboot recovery, zombie epics).** `cld` ranked them; everyone
  else excluded them as owned by `sase-1ra` phases `.11`/`.12`. Both are right:
  the beads are owned, and the owner is dead — no `sase-1ra` agent has run since the
  11-07 reboot (lead re-verified tonight). Launching *new task workers* would
  double-book the epic; the correct move is the **owner action** of resuming it.
- **sase-1nc (TUI GC freezes).** `grk` and `gem` excluded it as owned by `sase-zn` /
  `sase-1nf`; `cld` showed every TUI-performance epic is a zombie or stalled with no
  live agent, and measured ~46 main-loop stalls ≥ 5 s in 2.5 h on athena (max 8.5 s;
  apollo max 11.4 s, including CPython's *automatic* collector). The ownership objection
  is void, but the work is a large, measurement-first investigation whose own
  prerequisite (`cld`: the stall log rotates away after ~2.5 h, destroying any
  before/after baseline) isn't met. **First honorable mention, with the log-rotation fix
  as the cheap first step.**

## Lead verification (what I re-checked myself)

All run 2026-11-11 ~22:00 EST, workspace `sase_11` on apollo, master `671ff5bde0`:

| Check | Result |
|-------|--------|
| `sase repo list -p sase` | **Still exits 2**: `Project 'sase' has no WORKSPACE_DIR in /home/bryan/.sase/projects/sase/sase.sase.` |
| `git branch --contains 522b07a009` | On master — `fix(ace): preserve failed editor drafts` landed; sase-1ce is done in source |
| `sase bead read sase-1ot` | Gate `custom-b52a9f2c`: `outcome=owner_reject`, `purge_pending=true`; rules-v2 re-audit required before any renewed remediation |
| athena `sase_21` / `sase_29` `git status` | **Both still dirty** with the unlanded fixes: `sase_21` has `workspace_handler_context.py`, `patch_sync.py`, and the new `tests/main/test_project_ref_canonicalization.py`; `sase_29` has 8 files including `tests/test_agent_auto_restart_signature_skew_replay.py` |
| `sase agent list -j` (apollo + athena, 41 rows) | **No `sase-1ra` agent live.** Live SASE work: `sase-1rq` chain (all WAITING), `sase-1n6.11` steward wait, `sase-1r2.land` wait, docs chops; the 0.19.0 `sase-1s7` agents from `cld`'s snapshot are gone; ~20 bob-cli agents |
| `sase bead read` (compact) of all 18 candidates | All still open and unassigned; snoozed set is only `sase-po`, `sase-1m7`, `sase-1p8` |

## The ranked seven

### 1 · sase-zo — salvage and land the verified display-name fix (ride-along: sase-1r4's Python half)

**bug · small · +10 · ready.** The most-corroborated open bug in the backlog, ranked #1
independently by both researchers who checked it (`cld`, `grk`), and re-verified broken
by the lead tonight. Decision `project-labels-never-keys` makes the display name the
identity every surface shows, yet `resolve_project_context` still treats the `-p` token
as a directory key, so `sase repo list -p sase` fails closed for every agent and human
following the documented contract.

What makes this unambiguous #1 is the discovery (`cld`, §1.1, lead-verified): phase
`sase-1ra.1` closed as *done* on Nov 4, but its monitor crashed at launch
(`already has a stop request; nothing to join`), host completion recorded the dirty work
as `carried_repo` to a successor that never started, and nothing reopened the bead. The
complete fix — registry-canonicalized `-p` accepting key/display-name/alias with seven
regression tests, all lint green — is still sitting uncommitted in athena `sase_21`.
The same failure stranded `sase-1ra.7`'s signature-skew diff (8 files) in `sase_29`.
**This is the cheapest high-impact item available (rebase, re-test, commit) and it is
time-sensitive**: the `sase-zw` disk-retention machinery exists precisely to reclaim
held workspace state.

Done when: `-p sase`, `-p SASE`, and `-p gh_sase-org__sase` all resolve; ambiguity lists
candidates and exits 2; the regression test is in-tree; both workspaces are clean; and —
the structural half — a `carried_repo` obligation whose staged successor never adopts
reopens the predecessor's bead (extend phase `sase-1ra.8`'s guard, mirroring
`sase-1oh.4`). The monitor-join race itself is already fixed (`c65055eff6`); the
reopen-guard gap is what remains.

### 2 · sase-1re — stop done monitors with stale `followup_pending` from owning beads forever

**bug · medium · +1 · ready · sase-core.** The only bead ranked by **all five**
researchers, and `mus`'s #1. A monitor member that is `done` but still reports
`followup_pending=true` (stale `next_action`, no `followup_outcome`) reduces to
`owned/monitor` in `crates/sase_core/src/stranded_work/classify.rs` instead of
`stranded` — forever. `cdx` reproduced the decisive classification through binding
0.44.1 with a synthetic cold/done/stopped monitor (flipping only the flag flips the
verdict); the 11-05 +1 named four live holders (`sase-1ih.2`, `sase-kp`, `sase-ru.6`,
`sase-s5`), two of which sit in `cld`'s zombie-epic census.

The leverage argument: ACE's STRANDED view, the recovery reconciler, and the
`sase-12u` zombie-epic cleanup all read this classifier. Every reboot-stranded or
zombie epic hiding behind a done-but-pending monitor is invisible until this is fixed,
so it multiplies the value of the entire recovery stack (#1's guard, the resumed
`sase-1ra` phases, #6). Fix: investigate why the follow-up never settled first, then
bound ownership using actual delivery/recovery facts, distinguishing a dead abandoned
follow-up from a real queued successor, a live monitor, and legitimate settlement grace
(`cdx`'s completion bar). Distinct from `sase-1ra.8` (orphaned *staged* monitors) —
coordinate, don't merge. Needs a core release and pin move; line it up with the steward
train.

### 3 · sase-1s2 — runner imports must stop replacing the process SIGTERM handler

**bug · small · ready.** Reproduced in fresh interpreters by `cdx` and `grk`
independently today: importing `sase.axe.run_agent_runner` (line 87) or
`mentor_runner` (line 30) swaps `SIG_DFL` for a soft handler that records a kill
*without exiting*. Every importer inherits it — pytest xdist workers, tool runs,
anything — so unrelated processes can survive SIGTERM and burn time or capacity until a
hard kill, and signal behavior becomes import-order-dependent (a passing isolated test
hides what the full lane just installed). The contention epic observed exactly this in
monitors `kyhnsmgpcjx9` and `aa3fzgn042n3` and filed this bead as a separate follow-up.

Highest ROI in the list: one line moved from import time into the runner-owned entry
lifecycle (the pattern already exists in `run_agent_runner_signals.py`), disjoint from
every live epic's files. Done when a fresh-interpreter import leaves SIGTERM at the
caller's handler, while real agent/mentor entries still install the soft handler and
settle correctly under real signals.

### 4 · sase-1o1 — continuation capture nests fork ancestry and is now over its cap in production

**bug · large · ready · sase-core + sase.** No longer latent. `persist_agent_delta`
records the `#fork`-expanded step prompt as `authored_local_request`; replay renders it
as the parent's user block, so every session member re-nests its whole ancestry —
superlinear growth in session length. The Rust validator still rejects anything over
262,144 bytes (`cld` re-proved this through the installed binding at 200 K/270 K/708 K).
A live athena land session is at **708,391 bytes — 2.7× the cap**. When such a turn
ends, agent-delta capture fails and the next monitor follow-up settles
`not-launchable` until someone hand-runs `sase monitor resume`.

It ranks #4 because it hits precisely the sessions everything else depends on — long
land and monitor sessions are how every epic lands — and because it is *certain* to
recur as sessions lengthen. Fix shape (`cld`): capture only the local pre-fork request;
make replay walk the parent chain (text-ref storage as fallback); keep fork-replay
output byte-stable with a 20-member under-cap regression; add a one-shot repair (or at
minimum an explicit capture error instead of the silent dead-end) for in-flight
over-cap sessions. Needs a core release and pin.

### 5 · sase-1qm — host completion refuses checks that passed

**bug · large · ready · sase-core + sase.** A prepared completion backed by a fully
green `just check` (exit 0, evidence complete, every dirty-file hash and HEAD matching
the sealed fingerprints byte-for-byte on hand audit) is refused with
`stale_worktree_fingerprint`, discarding 30–60 minutes of verification and costing a
recovery turn. Filed from one 11-01 incident; `cld` found the exact shape recurring in
sase on 11-07 and 11-10 (both diverted to recovery), seven bob-cli refusals this month
(six in one day, fingerprint-plus-missing-stages — worth confirming in the same
investigation), and a rising monthly count: 5 in October, 11 so far in November.

This is a throughput tax on the landing path of every epic, at the moment when
prepared completion is how all work lands (decision
`handoffs-end-through-host-completion`). Three fresh repro runs are available. Start by
diffing the sealed observation against the host-time observation for the sase runs
(suspect: cross-repo scope over main + sase-core), and make the refusal record name
*which* fingerprint component differed — today the agent can only guess. Location:
`crates/sase_core/src/continuation/completion_eval.rs` +
`src/sase/monitor/followup_prompt.py`.

### 6 · sase-1qi — `sase agent restart` cannot find crash-killed agents

**bug · medium · ready.** A kill or reboot that never writes `done.json` leaves the TUI
showing FAILED while `sase agent restart <name>` returns not-found:
`find_named_agent` deliberately `continue`s non-done records with dead PIDs
(`src/sase/agent/names/_lookup_named.py:148–150` — correct for wait resolution, wrong
for restart). The 11-01 reboot forced manual per-epic bead surgery for 27 stranded
waiters; the 11-07 reboot proved only hand-watchdogged epics come back.

Two researchers (`grk` #2, `mus` #5) converged on the same sequencing logic: the Nov 4
ranking parked this behind Agent Hijack, `sase-1qz` is now **closed**, so the deferral
has expired — and the `sase-1ra.11.1` boot reconciler (whose resumption is this
report's headline owner action) needs a working restart-by-name for dead members or it
inherits this gap on day one. Fix restart's lookup to include dead-without-done records
(a FAILED/exit-without-error class) without deleting the liveness skip waiters rely on.
**Ride-along:** `sase-1qr` (Rust scans drop `process_identity`, degrading the PID-reuse
guard to PID-only; `cdx` reproduced the dropped field through binding 0.44.1) is the
other half of agent-identity correctness and fits the same worker if budget allows —
three researchers flagged it just below their cut.

### 7 · sase-1db — verify an existing private-attachment remote is actually private before pushing

**bug · medium · ready.** `cdx`'s #1 and `gem`'s #6, and the only irreversible-consequence
item in the final set: `preflight_sidecars` compares visibility only when *creating* a
remote; an existing `attachments-private` remote is trusted on its configured role
alone, and discovery labels the store "(private)" without ever probing. A misconfigured
or legacy remote pointing at a public repo means sensitive attachment bytes are
published under a private label — and unlike every other defect in this list, a
disclosure cannot be repaired by a retry or a recovery turn.

It takes the last slot rather than a higher one because exposure *frequency* is unknown
(`cld` noted no incident since the last ranking) — but the boundary is verified missing
in current source, the prerequisite visibility probe and doctor check already landed
(`sase-1d5`, closed), and the remaining scope is a bounded medium fix with a favorable
consequence-to-effort ratio. Enforce rejection of a known-public "private" destination
before any upload at the shared write boundary (not just preflight/labels, so outbox
retries and alternate frontends can't bypass it), define honest unknown-visibility
handling, and cover existing-public remotes, visibility changes, cached results, and
queued/retried uploads. This is *prevention*, deliberately separate from the
owner-rejected historical purge (`sase-1ot`).

## Owner actions (decisions, not task launches)

1. **Resume `sase-1ra`** — the single highest-leverage move after #1. Trim
   `sase-1ra.11.1`'s gate list first (its `sase-1qz` gates are closed; the `sase-1r2`
   gate is down to one unrelated green-Full-CI phase — drop or narrow it), then
   `sase bead work sase-1ra`. This restaffs phases `.8`–`.12` (staged-zombie settle,
   skew core classifier, import ratchet, boot reconciler, zombie-epic invariant) and
   lets the land agent close the fixed-but-`ready` beads: `sase-1ce`, `sase-1q3`,
   `sase-1qe`, `sase-1pw`, `sase-1qu`, `sase-172`, `sase-1i6`, `sase-1al`, plus
   `sase-1by` and `sase-1hr` which now pass on master (and `sase-175` per `grk`). Until
   that happens, every "what's ready?" ranking keeps resurfacing finished work.
2. **Reclaim `sase-j0`** (+38, held by a claim dead since 10-26). With
   `check-full-is-explicit`, either retire the hard test-cost budgets or re-key them
   per worker; release the dead claim either way.
3. **`sase-1ot` stays owner-gated.** The durable record is an owner rejection; renewed
   remediation requires an owner request and a scanner-rules-v2 re-audit first. Do not
   let a ranking re-authorize a history rewrite.
4. **Triage the stalled-epic census.** `cld` classified 127 in-progress plans: 8 active,
   39 zombies (all children closed), 80 stalled with open children and no live agent —
   including both previous "top ten" epics. The resumed `sase-1ra.12` produces the
   report-only pass; the rows are owner decisions (relaunch / close / snooze).

## Honorable mentions (next in line, with their unblock conditions)

- **sase-1kp** (bug · L; `cdx` #5, `mus` #4) — `beads.db` doubles as Rust's mutation
  lock file and Python's WAL mirror; `cdx`'s descriptor experiment plus SQLite's own
  documentation confirm closing the Rust lock descriptor can drop Python's POSIX locks.
  Corruption-class severity on the store behind everything, but it needs a
  single-owner/lock-protocol design with a mixed-version migration — plan it
  deliberately (gem's "epic-sized" concern is fair) rather than slotting it as repair #8.
- **sase-1nc** (bug · L; `cld` #4) — ~one ≥ 5 s TUI freeze every three minutes on
  athena, and apollo shows CPython's automatic collector also pausing the main thread
  > 5 s, so it's heap/cycle volume, not just the idle-gating policy. First step is
  cheap and prerequisite: rotate `tui_stalls.jsonl` less aggressively so a
  before/after baseline exists; reclaim or close the zombie TUI-performance epics
  (`sase-zn`, `sase-132`, `sase-124`) so ownership is real.
- **sase-1em** (flake · L · +6; `grk` #7) — hottest live full-lane flake; its newest +1
  is from `sase-1s7.land` while landing 0.19.0 *today*. Coordinate with the
  `sase-1rq` contention lane rather than racing it; fix the shared registry state or
  hermeticize the test, never xfail.
- **sase-1s4** (bug · L; `gem` #3) — a leaked `.git/index.lock` in a real checkout
  wedges every subsequent commit and finalizer, but there is one incident and the
  mechanism is unknown; a large hunt ranks below fresh, precise reproductions.
- **sase-1qv** (`grk` #5) — slot-refusal policy still in Python despite a closeout
  claiming a Rust move (same lost-edit failure shape as #1); boundary hygiene plus a
  bead history that currently lies. **sase-1ha** (`grk` #6) — empty `possible_owners`
  in check-run triage is the multiplier on backlog dedup once the seven land.
  **sase-1rb** (`mus` #3) — 53 stale publication-protection blocks keep `sase doctor`
  WARN forever; bounded repair pass. **sase-1cg**, **sase-1mb** (`cdx` #6/#7) — both
  freshly reproduced (restart discarding a draft on failed stash write; write-first Git
  batch readers blocking past their deadline); small/medium and safe to slot into any
  idle capacity. **sase-1qx**, **sase-1rt** (`mus` #6/#7) — measured finalizer and
  reconcile latency reductions; real but pure throughput, behind correctness.

## Sequencing and conflict screen

Do not launch all seven at once; athena already carries the `sase-1rq`/`sase-1n6`/
`sase-1r2` wait graph plus ~20 bob-cli agents. Suggested order of operations:

1. **Salvage first** (#1): rebase the `sase_21`/`sase_29` diffs (bases `99932634cd` /
   `0cc9fad474`), focused tests, `just check` under `sase tool run`, commit.
2. **Resume `sase-1ra`** (owner action 1) immediately after, so its land agent cleans
   the tracker while new work proceeds.
3. **Small disjoint workers** (#3 `sase-1s2`, then #6 `sase-1qi` + `sase-1qr`
   ride-along) can run in parallel with the above — their files overlap nothing live.
4. **Core-touching repairs** (#2 `sase-1re`, #4 `sase-1o1`, #5 `sase-1qm`) each need a
   sase-core change, a published core, and a `sase-core-revision.txt` pin move — batch
   them with the steward train (`sase-1n6.11`) rather than racing it, and keep #2 in
   contact with the resumed `sase-1ra.8` (adjacent classifier surface).
5. **#7 `sase-1db`** is independent of all of the above (sidecar preflight/store
   boundary) and can start anytime a medium slot opens.

Re-run `sase agent list -j` on both hosts before each launch; if a resumed `sase-1ra`
member is editing `names/_lookup_named.py` or the stranded-work classifier, coordinate
before starting #6/#2.

## Provenance

- Researcher reports (this directory): `__cdx` (fresh binding/source reproductions,
  exclusion audit of already-landed fixes), `__cld` (unlanded-work forensics, live
  fleet census, 708 KB measurement), `__grk` (on-tree probes, epic-overlap screen,
  launch batching), `__mus` (conflict screen, latency/publication residuals), `__gem`
  (severity framework; two of its picks corrected by verification).
- Lead verification commands and results are tabulated above; bead reads were audited
  via `sase bead read`, and no beads were created, edited, claimed, or closed by this
  research. All bead statistics are a snapshot of a changing store.
