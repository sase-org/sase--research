# Enforcing `sase tool` use and wrapping monitors: design research

**Researcher mus · 2026-09-22 · sase master (post-`sase-135` E1 landing) · core pin per `sase-core-revision.txt`**
**Question.** How should we (1) enforce that sase agents use `sase tool` for certain commands (e.g. `just check`), with an override for breakage, and (2) have sase monitors wrap their command with `sase tool` (including arbitrary commands)? Is the proposed plan sound, and what should change?

Prior context: the consolidated roadmap (`202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`), the E1 landing record on `sase-135` (closed 2026-09-20, seven phases, `sase tool list/run/runs/show` + Rust ToolRun store + `sase/sase.yml` catalog), `docs/tool.md`, and `sase/memory/lint_and_test.md`. I did not consult the sibling `__cld`/`__gem` reports for this swarm.

## 1. Recommendation up front

**Do not build `sase tool ensure-not-agent` as specified. Do not transparently wrap every monitor. Instead:**

1. **Now (no new gate):** keep enforcement soft — the `lint_and_test.md` "prefer `sase tool run check`" rule, the `sase_monitor` skill canonical snippet (`-- sase tool run check` / `check-full`), and the read-only `tools/tool_adoption_report` metric are already moving the number (E1 landing note: 0 → 6 wrapped in days against a 637 raw / 220 ambiguous baseline). Add one documented break-glass env var (below) but enforce nothing yet. Gate adoption on the metric, not on calendar.
2. **Next, only if the metric stalls:** add **`sase tool require-wrapped`** (rename — see §3.1), a thin Python check called from the `just check` / `just check-full` recipes, not a command agents must remember to call. Semantics: *fail only when there is positive proof of an unwrapped agent-owned invocation*; explicitly allow humans, allow wrapped runs (`SASE_TOOL_RUN_ID` set), allow stale installs (warn and run), and allow `SASE_TOOL_ALLOW_DIRECT=1` break-glass. This inverts the proposal from "fail if agent detected" (which would also fail wrapped runs) to "fail if wrapping proof is absent in an agent context."
3. **Monitors:** ship **no new arbitrary-command machinery** — `sase tool run -- ARGV...` already runs arbitrary commands (verified §2.2). Keep wrapping at the call site (skill + `verify` profile), and if server-side help is wanted, scope it narrowly: **only the `verify` profile auto-prepends `sase tool run` to unwrapped catalog commands**, idempotently, never for `sleep`/waits, never for prepared-completion `-f` exact-command monitors, never for `monitor_execution_argv` bootstrap launches. Preserve shell semantics via a `sh -c` preserving form (§4.3) and accept single-log ownership (monitor log authoritative; ToolRun carries stages/fingerprints/owner id, no duplicate retained stdout/stderr).

The rest of this report justifies each adjustment. All are called out explicitly in §5.

## 2. What exists today (verified)

### 2.1 `sase tool` already runs arbitrary commands

- `src/sase/main/parser_tool.py`: `run` accepts `TOOL [-- ARGS...]` or `-- ARGV...`; ad-hoc uses the invocation cwd, named tools run at project root.
- `src/sase/tool/argv.py` (`resolve_run_argv`, `_parse_run_words`): `--` form needs no catalog entry; `display_argv` redaction is conservative; named-tool extra args denied unless `args: allow`.
- `docs/tool.md` documents `sase tool run -- sh -c 'echo hi; exit 3'`.
- Live check from an agent shell (`SASE_AGENT_NAME=research.28.mus`): `sase tool run -- printf 'wrap-ok\n'` records a ToolRun and prints `succeeded` + `show` pointer in compact agent default; `sase tool run -v -- sh -c 'echo TOOL_ID=$SASE_TOOL_RUN_ID...'` shows the child inherits `SASE_TOOL_RUN_ID=<run-id>`, preserves the agent name, and `exit 3` propagates as `failed exit=3`. So bullet 2's parenthetical ("you might need to implement this") is already satisfied — no new executor work is needed for the wrapping itself.

### 2.2 Ownership, identity, and the monitor scrub gap

- `src/sase/tool/ownership.py`: resolves `owner_kind` from `SASE_MONITOR_ID` / `SASE_PROC_ID` / `SASE_TOOL_RUN_ID` (parent), with settled-owner stale checks; `compact_requested` returns compact only when the run owns its output, else streams. `SASE_AGENT_NAME` alone decides the direct-agent compact default.
- `src/sase/agent/identity.py` (`discover_agent_identity`, `require_agent_identity`, `resolve_audit_identity`): canonical agent detection is `SASE_AGENT_NAME` else `SASE_ARTIFACTS_DIR/agent_meta.json` name, else interactive fallback. This is the helper any gate should reuse — do not reimplement detection in shell.
- `src/sase/monitor/supervise.py` (`run_supervisor`): the detached supervisor **scrubs** per-agent identity (`scrub_agent_identity_env` removes `SASE_AGENT` / `SASE_AGENT_*`, plus pops `SASE_ARTIFACTS_DIR`) and then sets `SASE_MONITOR_ID`, `SASE_MONITOR_ARTIFACTS_DIR` (`MONITOR_ARTIFACTS_ENV`), and `SASE_MONITOR_DIAGNOSTICS_DIR`. Consequence: **a raw `just check` running inside a monitor has no `SASE_AGENT_NAME`**. Any gate that tests only `SASE_AGENT_NAME` misses exactly the long verify-monitor case the plan cares about most. Conversely a gate that treats any `SASE_MONITOR_ID` as "agent" over-blocks human-started monitors, because the scrub erases the human-vs-agent distinction — the caller is only recoverable via a monitor-store lookup (caller/lane), not from env.
- `src/sase/monitor/proc_adapter.py` (`MONITOR_ARGV_PREFIX = ("/bin/sh", "-c")`, `compile_monitor_argv`, `monitor_proc_argv`): monitors execute a **shell string** via `/bin/sh -c` (except host-owned epic launches with explicit `monitor_execution_argv`). `src/sase/main/monitor/common.py` (`start_command`) preserves one-word verbatim vs multi-word `shlex.join`. The existing `_warn_on_redundant_shell_wrapper` shows quoting is already the top incident source — any auto-wrap must be quoting-careful.

### 2.3 The soft-enforcement stack already landed

- `sase/memory/lint_and_test.md`: "Prefer `sase tool run check`" (+ `check-full` only when explicitly named per `decisions:check-full-is-explicit`); inside a verify monitor wrap as `-- sase tool run check-full`; prepared-completion `-f` monitors keep the **raw** `just check` / `just check-full` exact-command contract; stale-install fallback is "run raw `just` + record `sase update`."
- `src/sase/xprompts/skills/sase_monitor.md`: canonical snippet is `-- sase tool run check` (verify profile, `TESTING`/`TESTED`), with the same stale-install fallback.
- `tools/tool_adoption_report`: read-only, pairs `tool_calls.jsonl` by `tool_use_id`, classifies heavy (≥20 s) `check`/`check-full` as wrapped (`sase tool run` prefix) / raw (`just` exactly) / ambiguous (pipelines, multi-command — counted, not guessed). It deliberately does not read the ToolRun ledger, so ledger coverage is a separate signal.
- `tools/run_silent` + `tools/_run_silent_record.py`: `just check` stages already emit `run_silent` stage events; when `SASE_TOOL_RUN_EVENTS` is set (i.e. under a ToolRun) they are ingested into the run timeline (`src/sase/tool/stage_protocol.py`). Wrapping `check` therefore automatically yields per-stage timings with no Justfile change.
- `src/sase/tool/logs.py` (`prepare_run_paths`): when a run is owned by a monitor/proc (`owns_output=False`), only the events file is created — **no retained stdout/stderr logs**. `sase tool show -l` is empty for monitor-owned runs by design (one log owner). Follow-ups must use the monitor log, not `show -l`.
- E1 follow-ups (`sase-141`, `sase-143`, `sase-145`–`sase-148` per the `sase-135` landing note) are orthogonal to this design.

## 3. Critique of part 1: `ensure-not-agent` as proposed

### 3.1 The name and semantics are wrong and would break the wrapped path

`ensure-not-agent` ("fail if it detects a sase agent") read literally **fails wrapped runs too**: `sase tool run check` executed by an agent still has `SASE_AGENT_NAME` set (verified) plus `SASE_TOOL_RUN_ID`. The gate must distinguish *direct* vs *wrapped* agent invocations, i.e. require **proof of wrapping** (`SASE_TOOL_RUN_ID` present and referring to a live/recorded run), not absence of agency. A gate that only checks agency forces the Justfile to special-case the wrapped path anyway, duplicating `ownership.py` logic in shell. **Adjustment 1: rename to `sase tool require-wrapped` with allow-when-wrapped semantics.** The old name should not ship; it misdescribes the invariant and will confuse every future reader.

### 3.2 Detection must handle three cases the proposal omits

1. **Wrapped agent runs** (`SASE_AGENT_NAME` + `SASE_TOOL_RUN_ID`): must pass. Validate the id cheaply (non-empty; optionally `_parent_exists`-style store check, but never block on store failure — fail-open on read errors).
2. **Direct agent runs** (`SASE_AGENT_NAME` or `agent_meta.json` name, no `SASE_TOOL_RUN_ID`): must fail (or redirect — §3.4).
3. **Monitor-owned commands** (`SASE_MONITOR_ID` set, `SASE_AGENT_NAME` scrubbed): env alone cannot tell human-started from agent-started. Options, in increasing cost: (a) treat any monitor-owned unwrapped invocation as requiring wrapping (uniform; over-blocks human monitors — acceptable only if monitor wrapping is universal, which I do not recommend per §4); (b) look up the monitor record's caller/lane to decide (adds a store read + latency to every `just check`); (c) exempt monitor-owned commands from the Justfile gate entirely and enforce wrapping at `monitor start` time instead (recommended — the right layer, see §4). **Adjustment 2: the Justfile gate must not claim to cover monitors; monitor coverage belongs in the monitor path.**

### 3.3 A hard gate contradicts the executor's fail-open invariant and the stale-install reality

`executor.py` is deliberately fail-open: recording failure warns once and still runs the child exactly once with the same exit code. A Justfile gate that hard-fails when `sase tool` is broken (stale venv in an ephemeral `sase_<N>` clone, missing binding, corrupt store) turns every verification into a tool-availability gate — the opposite of the invariant, and exactly the scenario the proposal says must stay overridable. Relatedly, `lint_and_test.md` already promises "if `sase tool` is unavailable, run raw." A gate implemented *as* `sase tool <verb>` cannot satisfy that promise when the binary itself is the broken part. **Adjustment 3: the override must be readable without a working `sase` binary** — an env var checked in shell/Python before invoking anything version-sensitive (e.g. `SASE_TOOL_ALLOW_DIRECT=1`), not a `sase tool --allow-direct` flag. Fail-open on helper absence (warn + run) and fail-closed only on positive proof of unwrapped agency.

### 3.4 Don't make agents call the gate — call it from the recipe

Requiring every `just check` caller to remember a `ensure-not-agent` prefix repeats the adoption problem the gate is meant to solve, and adds a fork+exec to the hottest verification path. The gate belongs **inside** the `check` / `check-full` recipes (or a tiny Python helper they invoke), guarded against recursion by `SASE_TOOL_RUN_ID`. Even better, consider **redirect instead of refuse**: when an unwrapped agent invocation is detected, `exec sase tool run check` (loop-guarded) rather than exiting nonzero. Redirect preserves exit codes, needs no caller retraining, and degrades to a warning when the wrapper is unavailable. Refusal is only justified once the wrapped share stalls despite redirect + metric pressure. **Adjustment 4: implement as recipe-internal `require-wrapped` (or redirect), not as a caller-invoked prefix command.**

### 3.5 Bypass design

Requirements for the override: (a) works when `sase tool` is broken; (b) works for both interactive shells and monitor supervisors (env-propagated); (c) visible post-hoc (adoption report already counts raw vs wrapped, so bypass shows up without new telemetry); (d) hard to trigger accidentally, easy to trigger deliberately. That points to an explicit env var, e.g. `SASE_TOOL_ALLOW_DIRECT=1` (namespaced, greppable, matches existing `SASE_*` bypass precedents like `SASE_COMMIT_METHOD_ALLOW_OVERRIDE`, `SASE_ALLOW_UNSANDBOXED_BEAD_WRITES`, `SASE_INTERNAL_AGENT_NAME_BYPASS`). Do not require a reason string — agents confabulate reasons; the adoption metric + ToolRun absence is the audit. Document it in `lint_and_test.md` next to the stale-install fallback. No new flag bead is needed (this is permanent policy plumbing, not temporary beta behavior per `sase_flags.md`); if a transitional sunset is wanted while callers migrate, that is the only flag-shaped piece, and it should be short-lived.

## 4. Critique of part 2: "monitors wrap their command with `sase tool`"

### 4.1 No new arbitrary-command support is needed

Verified (§2.1): `sase tool run -- ARGV...` already executes arbitrary argv without shell expansion, with redaction, fingerprints, load sampling, and exit/signal passthrough. The remaining work is **policy** (which monitors, opt-in vs automatic, quoting), not executor machinery. **Adjustment 5: drop the "you might need to implement this" work item; close it as already satisfied by E1.**

### 4.2 Transparent universal wrapping is the wrong scope

Wrapping *every* monitor command would:

- **Pollute the ledger** with `sleep 300` waits, deploy polls, and diagnostics one-liners — each minting fingerprints, load samples, and retention debt for zero analytical value, and skewing the adoption denominator.
- **Break the prepared-completion `-f` contract**, which pins the raw `just check` / `just check-full` exact command (see `lint_and_test.md`). Rewriting those commands invalidates prepared intents.
- **Collide with `monitor_execution_argv` bootstrap launches** (host-owned code-swap path in `monitor_proc_argv`) — never rewrite explicit argv.
- **Risk double-wrapping** the already-canonical skill form (`-- sase tool run check` → `sase tool run -- sase tool run check`), creating parent/child ToolRun chains and confusing `LAST`/`TYPICAL`. Any server-side rewrite must be idempotent (detect the `sase tool run` prefix the same way the adoption classifier does).
- **Interact with merged-output supervision**: monitors merge stderr into stdout (`stderr=STDOUT` in `_popen_monitored_command`) while the tool distinguishes the streams; owned-by-monitor runs correctly stream (not compact) so idle-timeout byte counting keeps working, but authors must know `show -l` will be empty (§2.3) and the monitor log stays authoritative.

**Adjustment 6: scope auto-wrapping to the `verify` profile (or an explicit opt-in flag), never universal.** Concretely: in `handle_monitor_start` / `start_monitor`, when the resolved profile is `verify` (or a new `--tool-run` opt-in) *and* the command is an unwrapped catalog invocation (`just check`, `just check-full`, bare `check`), rewrite to the named-tool form (`sase tool run check[last]`); pass through `sleep`, pipelines the classifier would call ambiguous, prepared-completion-bound commands, and explicit argv untouched. Everything else keeps the current skill-level convention. This delivers E2's "exactly one ToolRun linked to exactly one monitor" for the verification lane without touching waits, follow-ups, or bootstrap.

### 4.3 Quoting: preserve shell semantics with one extra `sh` layer

Monitor commands are shell strings; tool argv is literal. Two safe rewrites:

- Catalog case (preferred): map `just check` → `sase tool run check` (named tool, runs at project root — note the cwd change from ad-hoc semantics; for `check` this is correct since the named tool pins project root).
- General shell case: `sase tool run -- /bin/sh -c <original-string>` (or `sh -c`). This preserves pipelines/redirections/`&&` verbatim at the cost of one extra `sh` process. Do **not** `shlex.split` the original string into literal argv — that silently changes globbing, quoting, and redirection meaning and converts clean `wrapped` classifications into `ambiguous` ones.

Signal behavior is compatible: supervisor TERM→KILL escalation hits the wrapper's process group; the wrapper forwards TERM/INT to the child pgid and settles `signaled`/`interrupted` (exit 143/130); the supervisor maps its own `termination.requested` to monitor `stopped` regardless of the child's code. Overhead was already accepted in E1 (DoD-13 cold-start case passes).

## 5. Explicit adjustments to the requirements (normative)

1. **Rename** `ensure-not-agent` → **`require-wrapped`**; semantics allow-when-wrapped, not fail-when-agent.
2. **Monitor-owned invocations are out of scope for the Justfile gate**; enforce monitor wrapping in the monitor path (§4.2), because scrubbed env cannot attribute agency.
3. **Override is an env var** (`SASE_TOOL_ALLOW_DIRECT=1`), checked before any version-sensitive code; no `sase tool` flag as the break-glass (it fails exactly when needed most). Document alongside the stale-install fallback.
4. **Gate lives inside the `check`/`check-full` recipes** (helper, recursion-guarded), not as a caller-invoked prefix. Prefer redirect (`exec sase tool run ...`) over refuse until evidence demands refusal.
5. **No new arbitrary-command executor work**: `run -- ARGV...` already satisfies it.
6. **No universal monitor wrapping**: `verify`-profile (or explicit opt-in) catalog commands only; exempt waits, `-f` prepared completions, explicit `execution_argv`, and already-wrapped commands (idempotence check).
7. **Accept single-log ownership**: monitor-owned ToolRuns carry events/stages/fingerprints/owner id but no retained stdout/stderr; `show -l` stays empty there and the monitor log remains the output of record. Do not "fix" this with duplicate logs (violates the E-roadmap one-log-owner invariant).
8. **No Rust core change** for either piece: detection + policy are Python/skill-layer concerns. Per the Rust boundary rule, only promote to `sase-core` if a second frontend needs identical enforcement — none does today. No new supervisor, queue, or store.

## 6. Recommended solution (phased)

**Phase 0 — docs + metric (this week, no behavior change).**
Document `SASE_TOOL_ALLOW_DIRECT=1` in `lint_and_test.md` as the break-glass (with the existing stale-install fallback), and publish the adoption-report wrapped share as the gating metric for Phase 1. No Justfile, monitor, or CLI change.

**Phase 1 — recipe-internal `require-wrapped` (only if wrapped share stalls over ~2 weeks).**
New thin helper (e.g. `src/sase/tool/require_wrapped.py` + `sase tool require-wrapped` facade for manual use and tests) reusing `discover_agent_identity` + `SASE_TOOL_RUN_ID` (+ `SASE_MONITOR_ID` pass-through per Adjustment 2): exit 0 for humans, wrapped runs, break-glass set, or helper/store unreadable (warn); nonzero with a one-line remedy (`run sase tool run check` / `SASE_TOOL_ALLOW_DIRECT=1 to bypass`) only on positive unwrapped-agent proof. Wire into `check`/`check-full` recipes first as warn, then refuse (or redirect). Tests: direct-agent refused, wrapped-agent passes, human passes, break-glass passes, missing-helper warns-and-runs, monitor-owned exempt. No flag bead (permanent plumbing); sunset only if a raw branch must temporarily stay reachable.

**Phase 2 — narrow monitor assist.**
In the monitor start path, when profile is `verify` (or explicit opt-in) and the command is an unwrapped catalog word, rewrite to the named-tool form idempotently; otherwise pass through. Keep the skill snippet as the primary vehicle. Add smoke coverage: verify-profile `just check` becomes `sase tool run check`; `sleep`, `-f` completions, explicit argv, and already-wrapped commands unchanged; monitor-owned ToolRun records `owner_kind=monitor` with empty `show -l` and a pointer to the monitor log.

**Explicit non-goals:** no `ensure-not-agent` name; no universal auto-wrap; no second retained log; no new queue/supervisor/store; no Rust contract change; no `--allow-direct` tool flag as break-glass.

## 7. Open questions for the owner

1. Is the adoption-report wrapped share an acceptable gate for Phase 1 (e.g. "stay soft while wrapped share rises week-over-week; build `require-wrapped` only on a 2-week stall")? If a hard date is preferred, name it.
2. Redirect vs refuse for unwrapped agent `just check`: is silent `exec sase tool run check` acceptable, or must the agent see an explicit failure telling it to re-run wrapped?
3. Should human-started verify monitors also be wrapped (uniformity, simpler rule) or stay raw (least surprise for humans)? My recommendation is wrap (uniform + the ledger wants the corpus), but it over-blocks humans who intentionally run raw under a monitor.
4. Catalog mapping confirmation (per roadmap §7): named tools stay repo-owned in `sase/sase.yml` — so the monitor rewrite targets `sase tool run check`, never a machine-local alias. Confirm.

## 8. Verification appendix (what I actually checked)

- Read: `sase_tool_epic_roadmap.md` (consolidated E1–E8 + record-before-admit), `sase-135` bead (closed, E1落地 + adoption 637/6/220 + follow-ups `sase-141`–`148`), `src/sase/main/parser_tool.py`, `src/sase/main/tool_handler.py`, `src/sase/tool/{argv,executor,executor_process,ownership,logs}.py`, `src/sase/main/monitor/{common,start}.py`, `src/sase/monitor/{proc_adapter,supervise}.py`, `src/sase/agent/{identity,env_hygiene}.py`, `docs/tool.md`, `src/sase/xprompts/skills/sase_monitor.md`, `tools/tool_adoption_report` + `tools/run_silent`, `sase/sase.yml` `tools:` (five named tools), `Justfile` `check`/`check-full` recipes, `sase_flags.md` and `decisions:check-full-is-explicit` + `glossary:tool-run/tool-catalog` via `sase memory read`.
- Ran: `sase tool run -- printf ...` (compact default as agent, `succeeded` + show pointer); `sase tool run -v -- sh -c 'echo TOOL_ID=$SASE_TOOL_RUN_ID...'` (child sees run id, agent name preserved, `failed exit=3` passthrough). Agent env observed: `SASE_AGENT_NAME=research.28.mus`.
- Deliberately did not open the sibling `__gem`/`__cld` reports in `202609/` (filenames observed only to avoid collision).
