# Why sase-core CI Keeps Going Red, and What Would Stop It

_Researcher: cld · 2026-10-29 · Scope: `sase-org/sase-core` CI workflow, 2026-09-16 → 2026-10-29_

## Bottom Line

sase-core's master was red **27% of wall-clock time** since mid-September (275 of 1,027
hours), and **29% in October** (196 of 676 hours). In October, **40% of master pushes
failed CI** (93 of 235), up from 22% in the second half of September. The failures are
not one problem. They fall into five classes with different causes:

| Class | What it is | Episodes | Red pushes | Episode-hours | Longest | Caught by a local Linux gate? |
| --- | --- | --: | --: | --: | --: | --- |
| **A. Fast static** | rustfmt (7), clippy `-D warnings` (9), hakari feature drift (2), compile error (1) | 19 | 44 | 90 h | 15.1 h | **Yes**: seconds to ~2 min |
| **B. Deterministic tests** | a test that fails on every run, on Linux too | 9 | 40 | 48 h | 13.8 h | **Yes**: full `just check` |
| **C. macOS-only** | case-insensitive FS, no `/proc`, non-UTF-8 names refused, `libc::mode_t` width, timing | 8 | 27 | 87 h | **27.4 h** | **No**, except that a cross-target `cargo check` catches the libc compile errors |
| **D. Flaky / timing** | passes on rerun; load- or timing-sensitive | 34 | 39 | 46 h | 8.6 h | **No** |
| **E. CI config/infra** | unresolvable action pin, BSD `sed`, runner cancellation | 4 | 6 | ~7 h* | 6.4 h | No |

_\*Excludes a 15 h cancellation that overlapped a rustfmt episode. Episode-hours overlap
when two failures are open at once, so the 294 h column total is more than the 275 h
wall-clock red time. "Episode" means one failure signature, from its first red push until
the push that cleared it._

Three findings decide the recommendation:

1. **Classes A and B (28 episodes, about 138 h, roughly half of all red time) never came
   from a commit whose exact content had passed `just check`.** The athena ToolRun
   ledger covers 231 agent commits to sase-core. The 150 that landed content which had
   passed a local `check` introduced **zero** fmt, clippy, features, compile, or
   deterministic-test failures. Every attributable A/B introducer had one of three
   histories: no sase-core check at all, edits after its last check, or a last check
   that **failed**.
2. **The commit hook that exists does nothing in sase-core.** Every host-owned commit
   runs SASE's `commit_hooks.before`. In sase that is `just fix`. In sase-core it
   resolves to the user-level `sase_git_fix`, which is a no-op there for two reasons: it
   looks for a capital-J `Justfile` (sase-core has a lowercase `justfile`), and sase-core
   has no `fix` recipe. All 40 sase-core before-hooks recorded since 2026-10-20 ran
   `sase_git_fix`, took about 0.05 s, and did nothing.
3. **Most unverified sase-core commits come from agents rooted in the sase repo that also
   edited the linked sase-core checkout.** 9 of the 11 attributable A/B introducers on
   athena had this shape. Those agents ran **sase's** `check`, which does not fmt,
   clippy, or test sase-core's working tree.

**Recommendation, in one line:** turn sase-core's no-op `commit_hooks.before` into a
**landing gate**. It auto-formats, then requires a passing `check` verdict receipt for
the exact tree being committed, and runs `sase tool run check` itself if no receipt
exists. Add a cross-target macOS `cargo check` to `check`. Separately, run the flake and
red-master hygiene listed below. A literal git `post-commit` hook cannot fix this,
because it runs after the commit exists and cannot block it. See
[§6](#6-why-not-a-literal-git-post-commit-or-pre-push-hook).

---

## 1. Data and Method

| Source | What I used it for |
| --- | --- |
| `gh run list` on the `CI` workflow, last 1,000 runs (2026-09-16 → 2026-10-29) | Pass/fail per push and PR; red-time computation |
| GitHub jobs API, `filter=all` (all attempts) for every failed run (309 runs, 467 failed jobs) | Which job and step failed |
| Logs of all 467 failed jobs, ANSI-stripped | Failing test names, clippy/rustc errors, panic messages, rustc version |
| sase-core first-parent history with `SASE_BEAD` / `SASE_AGENT` / `SASE_MODEL` body lines | Who introduced each failure (host, bead, model) |
| athena ToolRun ledger (`sase tool runs -a -j`: 5,332 runs, 422 sase-core `check` runs, 2026-09-25 → 2026-10-29) | Whether the committed content was ever checked, and with what verdict |
| sase repo history (bead overlap) | Whether a sase-core commit came from a sase-rooted cross-repo agent |
| Commit-hook evidence JSON under `~/.sase/projects/*/artifacts/**/commit_hooks/` | What `commit_hooks.before` actually ran in sase-core |
| A local experiment (see §4) | Whether macOS compile errors can be caught from Linux |

**Exact-tree matching.** Each ToolRun's `fingerprint_after` records `head` plus every
dirty path with a SHA-256 `content_hash`. I verified that this is plain SHA-256 of the
file bytes. For each landed commit I hashed every path in `git diff --no-renames
parent..commit` and looked for a `check` run on the same machine, settled before the
commit, whose dirty-path hashes equal the committed blobs. "Stale base" means the content
matched but the run's `head` was an older master: the host rebased after the check.

**Episode attribution.** CI runs once per push, and in this window nearly every commit
was pushed alone. An episode's introducer is the first-parent range between the last
push without that signature and the first push with it. Usually that range is one
commit.

---

## 2. Classes A and B: Failures a Local Gate Would Have Stopped

### 2.1 Fast static failures (A): 19 episodes, about 90 h red

| When | Introducer | Failure | Red for | Local check history |
| --- | --- | --- | --: | --- |
| 10-05 19:30 | `af5df614` (sase-1g4.5) | rustfmt diff in `editor/frontmatter` | **15.1 h** | Cross-repo agent; ran only sase's `check` |
| 10-07 02:35 | `21c539fd` (sase-1h7.3) | rustfmt diff in `agent_launch/` | **13.8 h** | Cross-repo; only sase's `check` |
| 10-03 21:05 | `3d406d4c` (apollo) | clippy `if_same_then_else` in `sase_xprompt_lsp` | **12.8 h** | apollo ledger not visible |
| 09-22 15:15 | `035851e0` | hakari feature drift for `cc` | 7.6 h | Pre-ledger |
| 09-27 02:56 | `b57cd213` (apollo) | clippy: `MutexGuard` held across `await` | 6.7 h | Not visible |
| 10-05 06:58 | `0d27dada` (sase-1g4.2.1.1) | clippy `type_complexity` | 6.0 h | Cross-repo; no core check |
| 09-27 19:35 | `297bc1e3` (apollo) | clippy `too_many_arguments` | 5.1 h | Not visible |
| 10-17 13:44 | `733256ed` (apollo) | clippy: `chunks_exact` with a constant size | 3.4 h | Not visible |
| 10-06 12:10 | `b19690e3` (sase-1eq.12.2) | **compile error** E0560 (removed field) | 2.2 h | Cross-repo; no core check |
| 10-06 23:50 | `7af3a73a` (sase-1h8.5) | rustfmt | 2.0 h | Cross-repo; a combined `just install && just check && … sase tool run check` **failed** |
| 10-09 05:18 | `e92f7f83` | clippy `dead_code` | 1.7 h | Check passed, then `store.rs` was edited |
| (and 8 shorter ones) | | rustfmt ×4, clippy ×2, features ×1, … | | |

In CI these gates cost **5 s (fmt-check), 3 s (features), and 75 s (clippy, warm)** on
ubuntu. Yet they produced a quarter of all red pushes and three of the ten longest red
stretches.

**Toolchain drift did not cause these failures.** Every clippy failure fired under the
same rustc as the CI runs before it: 1.98.1, 1.99.0, or 1.99.1. In every attributable
case the introducing commit simply had no passing clippy run. `rust-toolchain.toml`
still pins `channel = "stable"`, so a future stable release could add new lints on
master with no code change. That risk is latent and was not observed in this window.

### 2.2 Deterministic test regressions (B): 9 episodes, about 48 h red

| When | Introducer | Test | Red for | Local check history |
| --- | --- | --- | --: | --- |
| 10-07 16:20 | `f8d05efc` (sase-1h8.9) | `editor::directive::tests::contract_covers_the_audited_directive_matrix` (new `for_epic` keyword, contract not updated) | **13.1 h**, 12 pushes | Cross-repo; its only sase-core `check` **failed**, on exactly the landed content |
| 10-08 05:25 | revealed by `ec92ecce` | `bead_read_parity::event_store_supports_read_queries_without_legacy_projection` | **13.8 h** | Hidden behind the failure above (see next paragraph) |
| 10-17 03:08 | `305b7b80` (apollo) | `plan_validate_parity::plan_validate_matches_python_facade_fixture` | 5.9 h | Not visible |
| 09-18 14:09 | `549b1686` | `directive_contract_and_completion_bindings_return_plain_json_shapes` | 4.7 h | Pre-ledger |
| 10-01 00:20 | `a031ee4f` (apollo) | `file_history::shallow_clone_marks_health_and_incomplete` (git identity on ubuntu only) | 4.4 h | Not visible; led to the hermetic test env in `check.sh` |
| 10-05 04:20 + 13:00 | `0279de6b`, `fe2ef0e6` (sase-1eq.10, sase-1g4.2.1) | 14 tests after the xprompt→macro rename | 2.6 h + 2.0 h | Cross-repo; **three failed** local checks, then landed |
| 09-25 18:55 | `2a0fc2ab` (sase-17m.8) | 37 gateway fleet and auth tests | 1.4 h | Check **failed**; 6 paths edited afterwards |

**Masking makes B worse.** `scripts/check.sh test` runs `cargo test --workspace` without
`--no-fail-fast`, so cargo stops at the first failing test binary. On `f8d05efc` the
`sase_core --lib` binary failed, and `tests/bead_read_parity.rs` never ran. That second
regression, most likely from the same snapshot-plus-tail change, appeared only after
`ec92ecce` fixed the first. The result was about 27 consecutive red hours from what was
effectively one change. Local `just check` has the same masking.

### 2.3 How sase-core changes actually land: the verification ledger

Athena-agent commits to sase-core from 2026-09-25 to 2026-10-29, excluding release
commits (n = 231):

| What the landed content had | Commits | Share | Of which cross-repo |
| --- | --: | --: | --: |
| A **passing** sase-core `check` on identical content | 150 | 65% | 54 |
| A matching sase-core `check` that **failed**, and no passing one | 39 | 17% | 18 |
| Edits after the agent's last sase-core `check` | 25 | 11% | 10 |
| **No** sase-core `check` at all for that bead | 17 | 7% | 12 |

Push-CI red rate by row: about 24% for passing content (almost all inherited red,
flakes, or macOS), **64%** for failed-check content, and 56% for no-match content (this
row includes the 59 apollo commits the ledger cannot see).

Two observations:

- **"Stale base" is not a meaningful risk.** 46 commits were checked on an older master
  and rebased by the host. Their red rate, 25%, is the same as exact-base commits (23%).
  Semantic merge conflicts did not drive these failures; missing or ignored verification
  did.
- **Landing on a failed check is normal today.** sase-core's `AGENTS.md` says that a test
  failing under `just check` "is probably a load flake. Before you treat it as yours,
  look for its `sase-core flake:` bead." That guidance is reasonable, but nothing checks
  that the agent actually did so. `f8d05efc` landed a deterministic contract-test failure
  that way. Today's receipt plumbing records an ordinary `sase final submit` as
  `"unverified"` and never refuses it (`src/sase/finalizers/declaration.py`,
  `_verdict_provenance`). sase-core's `check` tool also has **no `receipt:` policy**, so
  `sase tool receipts` reports `0 retained` for sase-core.

---

## 3. The Hook That Exists Is a No-Op in sase-core

The host commit workflow (`src/sase/workflows/commit/workflow.py`) runs
`run_before_commit_hook(cwd)` after staging and before the commit. A non-zero exit
returns `RunResult.FAILED` with `before_hook_failed`. This is the "pre-commit hook" SASE
already owns. Its configuration differs by repo:

| Repo | Effective `commit_hooks.before` | What it does |
| --- | --- | --- |
| sase | `just fix` (from `sase/sase.yml`) | ruff, docs, keep-sorted, and other formatters |
| sase-core | `sase_git_fix` (user-level `~/.config/sase/sase.yml`) | `[[ -f Justfile ]] && just --summary \| grep -qx fix`. sase-core has `justfile` and no `fix` recipe, so it **exits 0 and does nothing** |

The evidence logs confirm it: 40 of 40 sase-core before-hooks since 2026-10-20 ran
`sase_git_fix`, exited 0, and took about 0.05 s. **17 of the 40 came from sase-rooted
cross-repo agents**, for example `sase-1ok.1` from `sase_14/sase/repos/linked/sase-core`.
So the hook already runs in the linked checkout for cross-repo commits, and it resolves
sase-core's config, not sase's (otherwise `just fix` would have run and failed there).
The mechanism is in place. It just has nothing configured to do.

---

## 4. Class C: macOS-Only Failures Hold Master Red the Longest

8 episodes and 87 episode-hours, including 4 of the 10 longest red stretches. Six of the
eight were introduced by commits that **passed** local `just check` on Linux. A Linux
hook alone cannot stop this class.

| Introducer | Failure | Root cause | Red for |
| --- | --- | --- | --: |
| `3f8baa79` (passed locally) | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget`: "WAL setup renewed an exhausted budget: 999.2295ms" | Wall-clock budget assertion; failed on every macOS run for 10 pushes until `0fd85e4a` | **27.4 h** |
| `32d80d6f` (passed) | `goal::ledger::tests::merge_writes_normalized_ids…`: `!root.join("items").join("7K2MQ").exists()` | APFS is case-insensitive | **20.2 h** |
| `bc71eb2c` (passed) | `launch_scratch_liveness::live_holder_matches_environ_path`, `managed_tmp_roots::…` | Linux process/environ assumptions | **12.2 h** |
| `72bf9203` (passed) | `project_stats::snapshot::tests::odd_filenames_and_non_utf8_paths_are_preserved` | APFS refuses non-UTF-8 file names | **12.0 h** |
| `43001664` | `project_spec::…case_variant_keys_and_home` | Case-insensitive FS | 5.2 h |
| `916d5e3a` → `dd56b94a` (both passed) | E0308 mismatched types, then E0617 "can't pass `u16` to variadic function" in `mobile_pairing/fs.rs` | `libc::mode_t` is `u16` on macOS and `u32` on Linux. The first fix created the second error | 4.4 h + 4.7 h |
| `1fee6419` | `live_holder…through_symlink…` | macOS path canonicalization | 1.1 h |

The `mobile_pairing` sequence shows the cost. Three macOS-only reds happened back to back
over about 21 hours, because agents on Linux could only test a macOS fix by pushing it
and waiting for CI.

**Experiment: macOS compile errors are catchable on Linux in about 2 minutes.** Plain
`--target aarch64-apple-darwin` fails because the bundled SQLite's C build needs a macOS
toolchain. `cargo check` never links, though, so a stub C compiler and archiver are
enough:

```bash
# stubcc: write an empty object at -o; stubar: write "!<arch>\n" at the archive path
RUSTC_WRAPPER= CC_aarch64_apple_darwin=stubcc AR_aarch64_apple_darwin=stubar \
  ./scripts/check.sh check -p sase_core --lib --target aarch64-apple-darwin
```

At `cd62c83d` this finished cold in **2 m 12 s**. On a `git archive` snapshot of the
breaking commit `916d5e3a`, it reproduced CI's exact errors (`E0308 mismatched types` at
`mobile_pairing/fs.rs:441:64` and `:517:44`) in **1 m 52 s**. `RUSTC_WRAPPER=` is needed
on athena because its sccache wrapper rejects the stub archive. The
`aarch64-apple-darwin` target is already installed on athena. This catches the libc-type
class but not runtime behaviour (FS case folding, `/proc`, timing).

---

## 5. Class D (Flakes) and Class E (CI Config)

**Flakes are the most frequent class (34 episodes) but mostly last one push.** The top
offender has no flake bead:

| Test | Failed jobs (window) | Flake bead |
| --- | --: | --- |
| `bead_read_model_parity::concurrent_readers_see_consistent_snapshots` ("concurrent read served a state no replay ever produced") | **37 jobs**, both OSes, from 10-08 to today. It is also the failure on the current tip `cd62c83d` | **None found** |
| `tool_run::store::tests::private_argv_is_not_serialized_on_queries` | 11 | `sase-17n` (closed) |
| `sudo_runner::tests::cli::native_launcher…` / `python_hosted_launcher…` (ETXTBSY "Text file busy") | 15 | `sase-15h` (open) |
| `bead::mutation::tests::replay_goldens::*` (`lock_wait_ms` timing baked into goldens) | 10 | Fixed in `ce85b670` / `d2a954b0` |

The assertion in `concurrent_readers_see_consistent_snapshots` reads like a real snapshot
race, not test noise. Either way it needs an owner. The existing
`runner-starvation-retry.yml` reruns only jobs that never got a runner, so it does
nothing for flakes.

**CI config (E):** `astral-sh/setup-uv@v10` did not resolve (`9876b3ae`, 6.4 h; fixed by
pinning `v10.3.0` with a pin test); BSD `sed` mis-parsed `rust-toolchain.toml` on macOS
(`b13332f3`); and occasional runner cancellations. These are already handled
case-by-case and are not where the volume is.

**Knock-on effects.** 121 of 321 October PR runs failed, and all 121 were release-plz
`chore: release vX` PRs that inherit a red master. `AGENTS.md` notes that "a red commit
also fails every release-plz run". So every red hour also delays core releases and
sase's `sase-core-revision.txt` ratchet.

---

## 6. Why Not a Literal git `post-commit` (or `pre-push`) Hook?

- **`post-commit` cannot prevent anything.** git runs it after the commit is created and
  ignores its exit status. It can only notify, and CI already does that.
- **Plain git hooks don't reach the commits that matter.** Agents never run `git commit`.
  The host finalizer commits through `sase stitch create` in ephemeral `sase_<N>` clones.
  `.git/hooks/*` is not versioned or cloned, so every workspace would need a
  `core.hooksPath` set up. SASE's own `commit_hooks.before` already runs in exactly the
  right place (the staged tree, in the repo being committed, for core-rooted and
  cross-repo agents alike) and leaves auditable evidence.
- **Re-running the full check on every commit wastes host capacity**, which the
  `two-speed-verification` / `check-full-is-explicit` decisions treat as the binding
  constraint. With receipts, the gate costs milliseconds for the 65% of commits that are
  already verified, and runs the 4–11 minute `check` only for the 35% that are not.

---

## 7. Recommended Solution

Ordered by return on effort. Steps 1 and 2 are the "hook" you asked about.

### Step 1: A receipt-backed landing gate in sase-core's `commit_hooks.before` (stops A and B)

In `sase-core/sase/sase.yml`:

```yaml
commit_hooks:
  before: "./scripts/land_gate.sh"
tools:
  check:
    # ...existing entry...
    receipt:
      accept: [pass, no_new_failures]   # mirror sase; known flakes need a witness
      ttl: 2h
```

A sketch of `scripts/land_gate.sh` (POSIX-simple, no new dependencies):

```bash
#!/usr/bin/env bash
# Host-owned before-commit gate for sase-core. Fast when the exact staged
# tree already has a passing `check` receipt; otherwise verify it here.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
cargo fmt --all                                   # cheap auto-fix (sase's `just fix` analogue)
if sase tool receipt check >/dev/null 2>&1; then  # covered: exact tree already passed
  exit 0
fi
./scripts/check.sh fmt-check                      # seconds: fail fast on the cheapest gates
./scripts/check.sh features
exec sase tool run check                          # full gate on the tree about to land
```

Why this shape:

- **It addresses the measured cause directly.** None of the 150 passing-content commits
  introduced an A/B failure, and every attributable A/B introducer lacked a passing
  check. The gate makes "passing check on the landed content" true by construction,
  including for the cross-repo agents that today only run sase's check.
- **It is cheap in the common case.** `cargo fmt` is a no-op whenever `check` passed,
  because `check` includes fmt-check. Running fmt first therefore never invalidates a
  real receipt. The receipt lookup takes milliseconds. Back-of-envelope cost for the
  unverified 35%: about 81 commits × about 6 min ≈ 8 hours of host time over 5 weeks,
  roughly 15 min/day. That compares with 196 red hours in October.
- **It replaces the honor system for "is this my failure?".** With `no_new_failures`
  accepted, a known flake with an independent witness still lands. A genuinely new
  failure (like `f8d05efc`) is refused.
- **On refusal, route to repair; never land red.** A non-zero hook already returns
  `before_hook_failed`. Make sure that path hands off to the existing commit-repair or
  repair-handoff flow (`src/sase/finalizers/commit_dispatch_repair_handoff.py`), so a
  fresh agent fixes the code and re-lands, rather than stranding the work (the `sase-yo`
  class of bug).

To verify while implementing:

- Formatter edits made by the hook are included in the commit, following the `just fix`
  precedent in sase.
- A sase-rooted agent's `sase tool receipt check` run inside the linked checkout resolves
  project `sase-core`. The ledger already records such runs as `sase-core`.
- The stitch's time budget fits an 11-minute `check`. Finalizer subprocesses are clamped
  at 1,800 s, and hooks have no timeout of their own.

**Optional small fix:** make `sase_git_fix` accept a lowercase `justfile` too. This is
not needed once sase-core sets its own hook, but other repos have the same blind spot.

### Step 2: Put a macOS cross-target compile check inside `check` (stops C1, shortens C)

Add `./scripts/check.sh macos-check` using the stub-CC recipe in §4, scoped to the crates
with OS-specific code (`sase_core`, `sase_gateway`). Include it in `cmd_all`, so it
becomes part of the receipt. Skip it with a loud warning when the `aarch64-apple-darwin`
target is not installed. Cost: about 2 minutes cold, less when warm. This would have
prevented the `mobile_pairing` sequence (two episodes, about 9 h) and lets agents verify
macOS compile fixes locally. Also add a short **portability checklist** to sase-core's
`AGENTS.md`: case-insensitive APFS, no `/proc`, non-UTF-8 names refused, `mode_t` is
`u16`, and wall-clock budgets need macOS headroom. Gate Linux-only tests with
`#[cfg(target_os = "linux")]`.

### Step 3: Flake hygiene (shrinks D)

- File and fix `concurrent_readers_see_consistent_snapshots` (37 failed jobs, no bead).
  This is the single highest-volume red-master source right now.
- Run CI tests with `cargo nextest run --retries 1` (or an equivalent single rerun of
  failed test names). A flake that passes on retry is then reported as FLAKY instead of
  turning master red. Keep the rule against weakening assertions.
- Add `--no-fail-fast` to the CI test step, and consider it for local `just check`, so
  one change's regressions all show up together (§2.2).

### Step 4: Close the latent gaps (cheap)

- Pin `rust-toolchain.toml` to an exact version, for example `1.99.1`, and bump it on
  purpose. CI's `dtolnay/rust-toolchain` already reads this file.
- Watch red masters. Classes C and D will still occasionally turn master red, and today
  nobody owns a red master: nine episodes stayed red for 12–27 hours. A sase-core watcher
  that files or launches a repair agent on the first red push would cut that tail. This
  could be a `workflow_run` failure trigger feeding a SASE notification, or a ci_watch
  entry.

### Step 5 (only if 1–4 don't get master under ~5% red): require CI before landing

The only full answer to class C is having macOS CI pass before code reaches master. That
means landing through PRs with required checks or a merge queue. master is currently
unprotected (`branches/master/protection` → 404, no rulesets). The repo is public, so
macOS minutes are free, but the macOS job's median is 26 minutes (max 37). That would
serialize landings and conflicts with the host-owned direct-push flow and the
`ci-two-speed-split` decision, which rejected a merge queue for sase. Treat this as the
fallback, not the first move.

### Expected effect

Applied to this window's data:

| Step | Classes affected | Red time addressed |
| --- | --- | --- |
| 1 | A + B (28 of 74 episodes) | ~138 of 294 episode-hours (~47%), including 5 of the 10 longest stretches |
| 2 | C1 (2 episodes, ~9 h); local reproduction for C2 work | ~9 h |
| 3 | The single biggest flake | 16 red pushes |

Together these should move master from about 29% red toward single digits. What remains
would be macOS runtime behaviour and residual flakes, and step 4's watcher keeps those
short.

---

## 8. Caveats

- **apollo is invisible.** The ToolRun ledger is per machine. The 59 apollo-agent commits
  (and 9 of the A/B introducers) could not be classified. Their CI red rate, and the fact
  that they include 5 of the 9 clippy episodes, suggest the same pattern, but that is
  unproven.
- **Episode durations are push-to-push.** A failure that is fixed in code but not yet
  pushed counts as red. Overlapping episodes double-count, which is why I quote wall-clock
  red time separately.
- **Masking blurs attribution.** Because cargo stops at the first failing binary, a
  "revealer" commit sometimes gets credit for an earlier break (`ec92ecce`).
- **Classification is heuristic.** Signatures come from test names and first rustc
  errors. Tests in class C were assigned to root causes by reading their assertions, not
  by reproducing them on macOS.
- **Older ToolRun logs are pruned.** For some failed local checks I could confirm the
  verdict but not the failing test.

## 9. Proposed Follow-Ups (for the lead to file and deduplicate)

1. sase-core: add `commit_hooks.before` landing gate plus a `receipt:` policy for `check`
   (Step 1).
2. sase-core: `check.sh macos-check` cross-target compile step and an AGENTS.md
   portability checklist (Step 2).
3. Flake bead: `bead_read_model_parity::concurrent_readers_see_consistent_snapshots`
   (37 failed CI jobs since 10-08; failing on the current tip).
4. sase-core CI: `--no-fail-fast` plus nextest single retry with FLAKY reporting.
5. sase: `sase_git_fix` should recognise a lowercase `justfile` (latent no-op in other
   repos).
6. sase-core: pin the exact Rust toolchain.
