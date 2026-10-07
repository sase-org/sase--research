# Task-bead impact audit: created or +1ed in the last 48 h

Researcher: mus · 2026-10-07 · independent report (`__mus`)

## Scope and method

- Window: 48 h before 2026-10-07 ~16:27 UTC, i.e. since 2026-10-05 ~16:27 UTC.
- Sources: `sase bead list --since 2d` (57 beads created, of which 11 are
  task beads) plus a scan of all `task_plus_one_recorded` events in
  `sase/repos/beads/events/streams/*.jsonl` with timestamps >= the cutoff
  (13 task beads +1ed in-window, 17 events total).
- Candidate set ("task beads" = `issue_type: task` only; plan/phase beads
  excluded): **23 beads** = 11 created + 13 +1ed − 1 overlap (sase-1h6).
- Evidence per bead: title, status, task type, size, impact/repro fields from
  `issues.jsonl`, and the in-window +1 evidence notes.
- Impact rubric: (1) breadth of breakage (agent launch path, daily workflow,
  all TUI users, CI signal, release blocking), (2) severity (data integrity,
  hard failure vs noise), (3) trajectory (growing vs static), (4) corroboration
  strength. Test-only flakes with a single witness rank below user-facing and
  CI-red defects even when sized large.

## Full candidate set

### Created in window (11)

| Bead | Type / size / status | Title (short) |
|------|----------------------|---------------|
| sase-1gv | flag S/open | Retire grok_rules_delivery (E1 sunset) |
| sase-1gw | flag S/open | Retire claude_helper_channel (E1 sunset) |
| sase-1gx | bug M/ready | Read-only bead paths auto-init stores, attempt SDD-init commits |
| sase-1gy | bug M/ready | Perf-check recipes recreate legacy in-tree sdd/ tree |
| sase-1gz | flake L/ready | sase-core federation_worker socket/symlink test fails under parallel gate |
| sase-1h0 | bug S/ready | InputItemModal and MacroItemModal unreachable (dead TUI code) |
| sase-1h1 | bug L/ready | Macro-arg detection wrong after quoted comma, none after quoted paren |
| sase-1h2 | bug S/ready | Circular ImportError breaks LaunchApproval dispatch |
| sase-1h4 | flag S/open | Retire instruction_shadow_render (E2 sunset) |
| sase-1h5 | bug S/ready | Beads pane refresh O(epics×issues), forced every 10 s |
| sase-1h6 | ci S/ready | just symvision red (`_runs` module-vs-function collision) — also +1ed |

### +1ed in window (13, events ≥ cutoff)

| Bead | +1s in window | Title (short) |
|------|---------------|---------------|
| sase-1fy | 3 | test_prompt_tab_focus_steal fails under xdist (NoMatches teardown) |
| sase-1gs | 3 | artifact link add / bead read fails bead-id validation |
| sase-10d | 1 | Cut sase-core release with 23f19f0, raise sase-core-rs floor |
| sase-13p | 1 | TUI import budget: 3292 modules vs 3290 cap (now 3570 vs 3570) |
| sase-14o | 1 | Two bead-store tests fail on any machine with beads |
| sase-15h | 1 | sase-core sudo_runner ETXTBSY flake under parallel tests |
| sase-17r | 1 | Fresh-workspace beads clone ~22 s p50 (`--dissociate` repack) |
| sase-18v | 1 | Snippet/restart CLI tests assert paths Rich truncates |
| sase-1br | 1 | test_block_spread_bracket_top_aligns scroll-settle flake |
| sase-1em | 1 | test_registry_rebuild_keeps_live_identity_pending_claim parallel flake |
| sase-1f0 | 1 | test_foreground_run_records_context_usage_and_grant peak_rss == 0 flake |
| sase-1gp | 1 | test_distinct_ace_apps_do_not_share_session_state parallel flake |
| sase-1h6 | 1 | (overlap with created set, above) |

## Ranked top 10 most impactful

### 1. sase-1h2 — circular ImportError breaks LaunchApproval dispatch (bug, S, ready, created in window)

Why most impactful: this breaks the agent-launch path itself. An approved
LaunchApproval (`launch-ac9ca583`) answered Approve yet `dispatch_status=failed`,
so approved agents never launched — it blocked the E1 (sase-1gu) acceptance
probes outright. Any `/sase_run` or bead-work launch reaching the lazy
`prompt_store_mutations` imports in a cold process can fail the same way
(import-order-dependent: `mutations` first fails, `prompt_store` first works).
A small, order-independence fix unblocks the core dispatch mechanism for all
agent work. Root cause is pinned to commit ad7f3a19a3 with a one-line repro.

### 2. sase-1gs — artifact link add / bead read fails bead-id validation (bug, L, ready, 3× +1ed)

Why: breaks the daily typed-link workflow for every agent. All
`sase artifact link add` calls fail pre-write and `sase bead read` fails unless
passed `--no-links`, because `validate_bead_id` (sase-core) rejects some stored
ref (likely an agent-name-style dotted segment). `/sase_new_task` requires typed
`related` links, so agents silently degrade to prose notes. Most corroborated
bead in the set alongside sase-1fy: three independent in-window reproductions
(sase-1gt.land, 0x4, sase-1g4.land) across different workspaces and commands.

### 3. sase-1h5 — Beads pane refresh is O(epics×issues), forced every 10 s (bug, S, ready, created in window)

Why: quantified, growing UI stall for every TUI user. Each visible-pane tick
costs ~2.8 s today (2.24 s replay + 0.56 s nested grouping loop) and scales
quadratically — ~8 s at 2× store, ~48 s at 4×, exceeding the 10 s refresh
interval while holding the GIL. The fix is cheap (single dict pass grouping,
drop `force=True`, let the mtime key decide). High impact-to-effort ratio on a
trajectory that only worsens as the store grows.

### 4. sase-17r — fresh-workspace beads clone ~22 s p50 (bug, M, ready, +1ed)

Why: a latency tax on nearly every agent launch. The first bead command in a
fresh workspace blocks ~22 s p50 (max 47 s) while `--dissociate` repacks ~1.2
GiB of loose `issues.jsonl` copies (~3 clones/hour on athena), and the pile
grows per bead commit. The in-window +1 adds fresh evidence that the
maintenance hook is not reaching the hidden clone either (1.84 GiB loose, all
repack thresholds exceeded). Fixing packing (or taking `issues.jsonl` off the
per-mutation path) buys back ~20 s on every cold agent start.

### 5. sase-1h6 — just symvision red on clean master (ci, S, ready, created AND +1ed)

Why: deterministic red in the `just check` lint stage erodes the CI signal all
landing depends on; currently triaged KNOWN/no-owner, i.e. normalized failure.
Uniquely, it sits in both halves of this audit (filed 10-06, independently
reproed 10-06 on an untouched tree). The root cause is found and the fix is a
rename (`sase/instructions/_runs.py` → public name) — E1/E2's new module
collides by name with two unrelated `_runs()` helpers. Small fix, restores a
green gate.

### 6. sase-10d — cut a sase-core release containing 23f19f0, raise the floor (bug, S, ready, +1ed)

Why: release-blocking. Published-wheel users pair sase with a binding missing
the sase-zu.8 machine-parity/index-completeness fixes (95 missing capabilities
per the +1's probe), while dev installs are unaffected — a silent
published-only regression. The bead states a sase release MUST NOT ship before
this lands. The in-window +1 (landing check at current pins, floor still
`>=0.35.0,<0.36.0`) confirms the gap persists and reframes it as carry-the-cohort
release-floor work. Narrower blast radius than ranks 1–5, hence #6.

### 7. sase-1h1 — macro-arg detection wrong after quoted comma/paren (bug, L, ready, created in window)

Why: user-facing correctness bug where the TUI disagrees with the runtime
binder and the LSP. Value menus for enum/bool/model args open for the wrong
input (`#m:"a,b",` selects `flag` instead of `env`) or not at all
(`#m("a)b",s` → None), because detection splits on raw commas and stops at the
first `)`. Every quoted-argument macro invocation in the prompt bar is
affected. Fix direction is concrete (use sase-core's structural
`macro_argument_spans` / completion-context builder plus golden fixtures).

### 8. sase-13p — TUI import budget saturated (ci, L, ready, +1ed)

Why: the startup-budget tripwire is firing deterministically — and the +1 shows
it getting worse (cap has since moved 3290 → 3570 and the run lands exactly on
it: `assert 3570 < 3570` with strict less-than). Three independent reproductions
(full lane, isolation ×2, reverted tree) rule out the usual suspects; import-graph
growth is the suspect. Startup bloat compounds silently, and a saturated
equality boundary means any added import re-reddens CI.

### 9. sase-1gx — read-only bead paths auto-initialize stores, attempt commits (bug, M, ready, created in window)

Why: a data-integrity hazard with the wrong failure polarity — display-only
lookups (`get_read_view` → `init_beads(commit=True)`, reachable via attachment
and plan-archive doctors) can write and commit generated SDD scaffolding into
an unrelated checkout. Read paths must never mutate; the blast radius is any
repo a lookup resolves to. Ranked below the active breakages only because it
requires a store-less cwd to trigger, but the fix (open-or-report-unavailable)
is a correctness invariant worth enforcing soon.

### 10. sase-1fy — prompt-tab focus-steal xdist failure (flake, L, ready, 3× +1ed)

Why: the noisiest CI flake in the set — joint-most corroborated (3 independent
in-window +1s across sase-1gt.4, sase-1gt.land relaying two phases, and
sase-1g4.land relaying two more phases): 5 failed + 5 teardown errors under
xdist, passing serially, recurring across epics that never touch focus/dock
code. Each occurrence costs a full-suite rerun and triage cycle. It also stands
in for the wider parallel-lane flake class (sase-1br, sase-1em, sase-1gp,
sase-1f0, sase-1gz, sase-15h each have a single witness); fixing its isolation
leak likely generalizes.

## Deliberately not ranked (and why)

- Flag sunsets sase-1gv / sase-1gw / sase-1h4: routine hygiene with kill
  switches and 2027-01 retire dates; no active breakage.
- sase-14o: deterministic but narrow — fails only in direct runs while
  `just check` stays green; same resolver-isolation fix family as two already-fixed beads.
- sase-1h0 (dead modals), sase-1gy (gitignored sdd/ regrowth): cleanup-grade,
  no user-visible failure.
- Single-witness load flakes sase-1gz, sase-15h, sase-1br, sase-1em, sase-1f0,
  sase-1gp and path-length CI failure sase-18v: real but each corroborated once
  and confined to test lanes; the class representative (sase-1fy) takes the
  ranked slot.

## Caveats

- "Created" uses bead `created_at`; "+1ed" uses `task_plus_one_recorded` event
  timestamps; cutoff 2026-10-05T16:27Z is the researcher's own clock reading —
  the lead should re-derive it from the official request time.
- Impact is judged from bead text and +1 evidence, not from re-running
  reproductions; several root-cause claims (e.g. sase-15h's fork/exec race) are
  explicitly unproven in the beads themselves.
- Sizes and statuses are as of the audit moment; fast-moving beads (notably
  sase-13p's cap) may already have shifted.
