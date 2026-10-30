# Is bob-cli-ep.1 stalled? Status and ETA (Oct 30, 2026)

I checked everything below live on Oct 30 between 18:35 and 18:44 EDT. All times are EDT.
Sources: `sase agent list -a -j`, `sase agent show bob-cli-ep.1`, `sase bead read
bob-cli-ep..`, the approved plan `plan:202610/capture_hash_type_marker.md`, bob-cli's
`justfile`, and the session's artifact directories under
`~/.sase/projects/gh_bobs-org__bob-cli/artifacts/ace-run/202610/30/`.

## Short answer

- **It is not stalled.** At 18:39:33 the full verification gate passed: `just
  docs-check && just check && just all`, exit 0, 15m25s of a 45-minute budget. This was
  the first fully green run in the session. Fourteen seconds later the host started the
  follow-up turn `bob-cli-ep.1--g`. By 18:43 that turn had started a new monitor,
  `bob-cli-ep.1--mon-f` (status `BUILDING`), to rebuild the debug `bob` binary for the
  required timing checks.
- **What it's doing:** the closeout steps for the phase. Implementation and tests are
  done. Still to do: rebuild the binary, run three timing checks on apollo, record the
  results in `docs/completion.md`, rerun `just docs-check`, check zsh completion
  insertion, audit for leftover `t:` text, then close the bead.
- **My ETA: the bead closes around 19:05–19:15**, about 25–35 minutes after 18:43. The
  earliest plausible finish is about 18:55, if the agent folds the remaining steps into
  fewer turns. The main risk is the timing gate. It allows only 5 ms of p95 headroom, on
  a debug build, while three other agents compile on the same host (see §4). If it
  fails, expect a performance-fix loop that could run past 20:00.
- **The epic won't land at that point.** `bob-cli-ep.2` (the Mac phase) and
  `bob-cli-ep.land` are both waiting on `.1`. `.2` includes a manual smoke test on the
  mac with screenshots.

## 1. What bob-cli-ep.1 is

Epic `bob-cli-ep` ("Capture `#<type>` replaces the `t:<type>` task-type marker") has two
phases:

| Bead | Scope | Agent / model | State at 18:43 |
| --- | --- | --- | --- |
| `bob-cli-ep.1` (large) | bob-cli: `#<type>` lexer, refusal, completion, help, docs, tests | session `bob-cli-ep.1`, codex `gpt-6-luna@xhigh`, workspace `bob-cli_12` on apollo | IN_PROGRESS, turn `--g` RUNNING |
| `bob-cli-ep.2` (medium) | Bob Mac Capture fixtures, tests, docs, manual smoke on the mac | `muse-spark-1.3-contributor` | WAITING on `.1` |
| `bob-cli-ep.land` | epic lander | `gpt-6-astra` | WAITING on `.1`, `.2` |

`bob-cli-ep.1` isn't a single long process. It is an agent session: a chain of short
code turns (`--1` … `--g`), each of which hands its long commands to a monitor turn
(`--mon` … `--mon-f`). `sase agent list` shows only the session's current member. That
is why the session showed up as a `TESTING` monitor row, with no `bob-cli-ep.1` row,
for the 15 minutes the gate ran.

## 2. Timeline so far

| Window | Members | What happened |
| --- | --- | --- |
| 15:05–15:11 | `--plan`, `--gate` | Plan turn; gate cleared at 15:11:14 |
| 15:11–16:02 | `--code` | Main implementation (≈50 min). The p95 baseline for the timing gate (55.6 / 44.7 / 68.6 ms) was recorded during this window |
| 16:01–17:50 | `--mon` … `--mon-a`, turns `--1` … `--c` | Focused-test loop: 11 monitor runs, ≈1h50m (detail below) |
| 17:51–17:57 | `--mon-b` | First full gate: failed at `cargo fmt --check` (exit 1) |
| 17:58–18:12 | `--mon-c` | `docs-check` passed; `check` failed: 5 lib tests still asserted the retired `t:` behavior (4119 passed / 5 failed) |
| 18:17–18:21 | `--mon-d` | Focused rerun of capture parser + completion unit tests: green |
| 18:24–18:39 | `--mon-e` | `docs-check`, `check`, `all`: **all green**. 4124 lib tests and 2561 CLI tests passed in both `check` and `all` |
| 18:39:47 → now | `--g`, `--mon-f` | Closeout: rebuild debug `bob` for timing (monitor started 18:43:11, 15-minute timeout) |

The focused-test loop was slow but kept converging. Failing-test counts per monitor run:
11 → compile error (E0308) → compile error → bad command (`&&` passed as a literal
argument, 3 s) → 4 → 20 (CLI suites added to the run) → 1 → 9 → 1 → 2 → 0. Turn
lengths ranged from 2.5 to 16 minutes, with a median of about 5.5 minutes. Each monitor
handed off to the next turn within seconds, and no turn sat idle.

## 3. What's left (the turn `--g` prompt)

The prompt for `--g` comes from the `next_action` that `--mon-e` recorded. It asks for,
in order:

1. **Rebuild** the workspace debug `bob` in the same `CARGO_TARGET_DIR` used for the
   baseline (`…/gh_bobs-org__bob-cli-ws12-261030_181112/build`). This is in progress as
   `--mon-f`.
2. **Time three commands on apollo** using `Fix the parser #f`: `capture-complete`,
   `capture-parse`, and the zsh completion protocol. Each gets one warmup run and then
   20 samples. The pass bar is a nearest-rank p95 of at most **60.6 / 49.7 / 73.6 ms**,
   which is the baseline plus the plan's 5 ms "PT3" allowance.
3. **Update `docs/completion.md`** with the verified date, method, and values. The turn
   noted that its docs memory requires `just docs-check` after a doc edit, so expect
   another monitor run.
4. **Check that zsh completion inserts `\#fix`** with `interactive_comments` set (plan
   §2.4).
5. **Review the full diff and audit `t:`.** Running `git grep 't:'` over capture source,
   docs, and tests should find only intentional retirement copy, escapes, and unrelated
   text such as `[t:: 30m]`.
6. **Run `sase bead epic-symbols bob-cli-ep.1`**, then close only `bob-cli-ep.1`, and
   end with `/sase_final`. The host commits the result.

## 4. ETA reasoning

Most likely sequence, with durations taken from this session:

| Step | Basis | Expected end |
| --- | --- | --- |
| `--mon-f` debug build | dev builds took 2m09s–2m18s in fresh target dirs | ≈18:46 |
| `--h`: timing checks (63 runs under 75 ms each) + doc edit, then start `docs-check` monitor | median turn ≈5.5 min | ≈18:53 |
| `docs-check` monitor | ≈4–5 min in `--mon-c` / `--mon-e` (includes a ≈2m15s build) | ≈18:58 |
| final turn: zsh check, diff/`t:` audit, `epic-symbols`, bead close, `/sase_final` | 3–10 min | **≈19:05–19:10** |

I'm calling it **19:05–19:15**. The faster path (about 18:55) needs the agent to run
the timing and `docs-check` in the foreground inside one turn. Nothing in this session
suggests it will.

**Risk: the timing gate.** The budget is only +5 ms over the baseline. It's measured on a
debug build, and apollo is busy: `bob-cli-eq.5` and `bob-cli-es.1` (bob-cli phases in
other epics) and `bi` (sase) all held runner slots at 18:40. A p95 miss sends the
session into a performance-investigation loop. Judging by the 1h50m focused-test loop,
that could push past 20:00, or end the phase with the bead left open for review.

**After `.1` closes:** `bob-cli-ep.2` starts on the Mac Capture repo. Its verification
includes `just portable-check`, `just docs-check` against the landed bob-cli commit, a
scratch mac compile, CI, and a manual smoke on the mac with screenshots. After that,
`bob-cli-ep.land` lands the epic. Expect the whole epic to take well beyond tonight's
`.1` ETA.

## 5. How to re-check quickly

```bash
sase agent list -j | jq -r '.[] | select(.name|startswith("bob-cli-ep")) | "\(.name) \(.status) \(.started_at)"'
sase bead read bob-cli-ep.1 -r "check whether phase closed"
```

If `--mon-f` or a later monitor row stops advancing, tail its `live_reply.md` in the
artifact directory and compare it with the log's modification time. That is how I
confirmed `--mon-e` was live: the log had been written within the last 5 seconds.
