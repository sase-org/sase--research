# What `sase tool stats` is for

**Research note** · 2026-09-30 · derived from
`research:202609/sase_tool_e6_e8_go_no_go/sase_tool_e6_e8_go_no_go.md` (the E6–E8
go/no-go) · checked against sase master `5385a8c8a7`

> **In one line:** `stats` reads the ToolRun ledger you already record and answers, as
> routine readouts, the questions that currently need hand-written SQL over
> `runs.sqlite`. Every number in the go/no-go report came from that kind of ad-hoc
> query.

It is **read-only**. It forecasts nothing, routes nothing, and admits nothing. Its job
is to tell you *whether* those features are worth building.

---

## 1. Today versus with `stats`

| Question | Today | With `stats` |
| --- | --- | --- |
| How long does `check` take? | `sase tool list`: one TYPICAL median (`15m 39s (n=30)`) | p50/p90 per tool, **stage**, machine, and provider |
| How often does it succeed? | Scroll through `sase tool runs` | Outcome and censoring mix (succeeded / failed / signaled / lost) |
| What are we losing? | Ad-hoc SQL | Kill, timeout, and lost counts, with **wasted hours** |
| Are runs repeating? | `sase tool receipts` (content-equivalent repeats only) | Repeat and concurrent-duplicate counts next to everything else |
| Is it getting worse? | Nothing | Trend over time and across recipe changes |
| Could we forecast it? | Nothing | A built-in chronological backtest: **coverage and band width** |

It also adds **demand instrumentation** to each recorded run: pytest grant width,
token-wait time, process-tree CPU seconds, and peak RSS. Elapsed time alone can't show
what a run actually cost the host.

## 2. The five jobs you'll use it for

### ① Prove reactive routing worked

Inline-then-escalate (`sase-1cx`) **landed today**. `stats` is how you check the
acceptance bar the go/no-go set, over one week on athena:

| Signal | Baseline (go/no-go, athena) | Target |
| --- | ---: | ---: |
| `check` runs signaled at 530–550 s (Muse ceiling kills) | 160 kills, ~24 h of compute | **0** |
| Same-agent kill→rerun pairs within 30 min | 57 | **0** |
| Handed-off runs finishing in under 2 min | 15% (38% under 5 min) | **< 5%** |
| Escalated runs that keep one ToolRun id | — | **100%** |

### ② Watch the hold triggers

E6's forecasting half, E7, and E8 are **held, not cancelled**. Each has a measurable
reconsider condition, and `stats` is where those signals would appear:

| Held work | Reconsider when `stats` shows… |
| --- | --- |
| **Rest of E6**: forecasts, ETAs, `timeout: auto` | a per-stage forecast with **≥80% p10–p90 coverage** and a **median band ≤3×** on athena `check` for two consecutive weeks (today: 75% coverage, **18.6×** band) |
| **E7** local admission | memory PSI above 10% in ≥10% of heavy-busy buckets for a week, an OOM kill from concurrent heavy runs, or concurrent same-fingerprint duplicates above ~1 h/week (today: 3 runs, 0.4 h in 9.5 days) |
| **E8** fleet surfaces | a second machine carrying more than ~25% of ToolRuns (today: athena runs 87%, the Mac none), plus the non-metric gates: E7 stable, `sase-x7` closed, and remote placement chosen as a goal |

### ③ Decide whether receipt reuse (E4b) pays

Reuse is gated on **≥2 h/week** of content-equivalent repeats for two consecutive weeks.
athena already shows **39 repeats (6.94 h)** in about 9.5 days, roughly 5 h/week.
Some of those may be kill→rerun pairs, though. Re-measure once routing has removed
them. If the number holds, reuse may save more hours than anything left in E6–E8.

### ④ See where the time actually goes

- **By stage.** The spread comes from the scoped test stage, not the lint stages. mypy
  runs p50 45 s with a p90/p50 of about 1.3×. A failing scoped test runs p50 663 s and
  p90 2,275 s.
- **By outcome.** 94% of athena `check` runs don't succeed (99% on apollo). A duration
  number is mostly *time until the first failure*.
- **By recipe.** athena saw seven `check` definition digests in ten days. Trend by digest
  catches suite or toolchain regressions and explains cohorts that look noisy.
- **By machine.** Half of apollo's settled `check` runs exceed 540 s, and apollo is
  CPU-pressured even with a single heavy run. That is a queue-capacity setting to tune,
  and `stats` makes it visible without SQL.

### ⑤ Price admission honestly

Whole-run `check` p50 rises from **183 → 235 → 323 → 469 s** as 0 / 1 / 2–3 / 4+ other
runs overlap. The go/no-go's best explanation is that pytest's worker-token pool grants
narrower slices under contention, but the ToolRun doesn't record the grant width, so
that stays a hypothesis. The demand instrumentation closes that gap. It turns "E7 might
help" into a measured answer.

## 3. What it would look like

A **mockup**: the go/no-go's athena findings laid out the way `stats` would report them.
The command and its layout are not designed yet.

```text
$ sase tool stats check                          # illustrative, not implemented
check · athena · 2026-09-20 → 09-29 · 1,394 runs · 7 definition digests

OUTCOMES     failed 1,092 · signaled 186 · succeeded 84 · lost 31
WASTE        160 ceiling kills (~24 h) · 57 kill→rerun pairs
HAND-OFFS    248 · 15% under 2 min · 38% under 5 min
STAGES       mypy          p50 45 s    p90/p50 1.3×
             feature-flags p50 63 s    p90/p50 1.3×
             scoped test   p50 663 s   p90 2,275 s   (failed runs)
OVERLAP      p50 183 → 235 → 323 → 469 s   (0 / 1 / 2–3 / 4+ other runs)
REPEATS      32 groups · 39 repeats · 6.94 h
BACKTEST     p10–p90 coverage 75% · median band 18.6×   (hold gate: ≥80%, ≤3×)
```

## 4. Status and what to watch

| | |
| --- | --- |
| **Built?** | No. `sase tool` has `failures`, `list`, `receipt(s)`, `run(s)`, `show`, `stop`, and `wait`, but no `stats`. |
| **Tracked?** | No bead, no plan. The one derived plan (`plan:202609/tool_inline_routing.md`) lists `stats` among E6's *parked* non-goals. The go/no-go recommends shipping it **now**, so it has no home yet. |
| **Size** | Small: 2–3 read-only phases (go/no-go §7 step 4). |
| **Blocker** | `sase-1bo` (READY, small). Stage rows are never pruned because of an ms/s mismatch, and the athena store grows about 30 MB/day. Fix it first so `stats` reads a bounded corpus. |
| **Where it lives** | Aggregation that the CLI and the Admin Center's reserved *Stats* view both need is core backend logic. It belongs in `sase-core` beside the ToolRun store, with thin Python and TUI consumers. |
| **Timing** | Ship it while the routing baseline is fresh. Its first job (①) starts this week. |

**Bottom line:** `stats` answers the question the go/no-go had to ask with ad-hoc SQL,
*"is this worth building yet?"*, and turns it into a command you can run every week. It
checks that routing worked, shows when a held epic has earned its turn, and prices reuse
and admission from measurements rather than guesses.
