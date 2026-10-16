# Gas Town vs. SASE: where Gas Town is ahead, and what to borrow

**Researcher:** cld (one of five independent swarm reports) · **Date:** 2026-10-16

**Snapshots compared**

- **Gas Town:** `gastownhall/gastown` at `649b832b` (2026-07-23). The latest tag is `v1.2.1`, dated 2026-06-06 in `CHANGELOG.md`. The repo has 7,770 commits, about 249k lines of non-test Go and 226k lines of Go tests.
- **Gas City:** `gastownhall/gascity` at HEAD (2026-10-16, tag `v1.5.0`). Read only for context.
- **SASE:** `sase` `master` at `f3087c86ac`.

Gas Town paths below are relative to the Gas Town repo root, and SASE paths to the SASE repo root.

**Evidence tags.** Gas Town's docs often promise more than its code does, so every important claim below carries one of these tags:
- **[code]**: I checked it in source.
- **[doc-only]**: described in docs but not built.
- **[unwired]**: the code exists but nothing in production calls it.

---

## 0. Bottom line

1. **Gas Town is ahead in running agents unattended.**
   - It supervises *live* agents, not just dead PIDs.
   - It closes the loop on failed work: re-dispatch, promotion to a stronger model, circuit breakers.
   - It refuses to land work that wasn't tested on the integrated tip.
   - It lets agents message each other and has a coordinator agent that can dispatch work.
   - It escalates out-of-band by severity.
   - It plugs into standard ops tooling: OpenTelemetry, cost tracking, a live feed, a web dashboard.
   - It keeps sessions alive through quota exhaustion.

   SASE is ahead almost everywhere *correctness and human judgment* matter: host-owned completion, durable non-blocking gates, capacity admission, typed workflows, validated epic plans, provider routing, provenance, and headless adapters with no screen-scraping.

2. **The biggest gap is the landing path.**
   - SASE agents land straight on `master`, and the only verdict arrives after the push.
   - A 2026-10-01 swarm report found `master` red for 13 days and about 1,110 commits, with "nothing on the landing path [that] refuses a red change".
   - Gas Town's Refinery merges one MR at a time and tests the *merged* result first. It only declares a merge after proving that the target branch contains the submitted SHA.
   - This one borrowable idea attacks the most expensive failure SASE is having right now.

3. **Treat Gas Town as a source of ideas, not a reference architecture.**
   - **It is winding down.** The last commit was 2026-07-23. Yegge wrote in August 2026 that *"Gas Town fell apart at the seams with Opus 4.7"*. He also wrote that he had *"given up on building reusable harnesses"*, moving his own work to a private harness called Wheelhouse. The successor, Gas City, is an SDK that drops every hard-coded role.
   - **Several flagship features are not real.**
     - The Bors-style batch-then-bisect merge queue is **[unwired]**.
     - "Model-aware molecules" (per-step model choice) is marked DONE in its doc but is **[doc-only]**.
     - Capability-based routing and the formula marketplace (Mol Mall) are **[doc-only]**.
   - **Its supervisors kept causing incidents of their own:** "Deacon murder spree", "serial killer bug".
   - **Borrow selectively.** Take the mechanisms that are verified in code, and take the lessons from its failures.

4. **Top three recommendations:**
   1. A mechanical **landing lane**: it refuses a landing that adds new failures relative to the current tip, verified on the rebased tree, then proves the push.
   2. A **failure-policy engine** for bead work: automatic retry with promotion to a stronger model, attempt caps, then skip-and-escalate.
   3. **Live-turn liveness classification**: working, quiet, stalled, wedged, zombie, built from the stream-JSON events SASE already parses, plus a Problems view and stale-gate re-escalation.

   The full ranked lists are in §7 and §8.

---

## 1. Sources and method

**Gas Town (local checkout opened with `sase repo open gh:gastownhall/gastown`):**
- Docs: `README.md`, `CHANGELOG.md`, and `docs/` (about 24k lines: concepts, design, research, reference).
- Code checked for every headline claim:
  - `internal/daemon`, `internal/witness`, `internal/deacon`, `internal/refinery`, `internal/cmd`
  - `internal/mail`, `internal/nudge`, `internal/tmux`, `internal/quota`, `internal/estop`
  - `internal/telemetry`, `internal/formula`, `internal/proxy`, `plugins/`, `gt-model-eval/`
- Four parallel read-only deep dives (supervision, landing, communication/context, workflows/observability), each told to separate code from documentation. I re-checked their headline claims by hand: the batch path is uncalled, model escalation is wired, the `gt done` safety nets exist, the pricing table is stale, preset/formula/plugin counts.

**Gas City:** a local checkout (`README.md`, `docs/getting-started/coming-from-gastown.md`).

**Web sources (non-repo content):**
- yegge.ai essays [*Fences, not Sandboxes*](https://yegge.ai/essays/fences-not-sandboxes/) (2026-08-24) and [*The Shape of Things to Come, Part 1*](https://yegge.ai/essays/the-shape-of-things-to-come/) (Aug 2026).
- [*Announcing Gas City 1.0*](https://blog.gascity.com/posts/announcing-gas-city-1-0/) (2026-04-28).
- The [Beads 1.2.1 incident report](https://blog.gascity.com/posts/beads-1-2-1-incident-report/) (2026-08-20).
- The [blog.gascity.com author index](https://blog.gascity.com/authors/steve/), [yegge.ai/gastown](https://yegge.ai/gastown), and [ai.engineer/orgs/gas-town](https://ai.engineer/orgs/gas-town).
- The Medium originals returned HTTP 403, so I used the mirrors and index blurbs instead.

**SASE:**
- `docs/` concepts and reference pages, `src/sase/` (spot-verified), and `sase doctor -L`.
- Decision records read through `sase memory read`: `single-turn-agents`, `gates-never-block`, `host-owned-completion`, `adapters-normalize-harnesses`, `record-before-admit`, `corpus-before-mechanism`.
- Two parallel read-only inventories that mapped each Gas Town capability to SASE files.

**Earlier research used as background:**
- `research:202605/sase_vs_gastown.md` (May 2026). Much of it is now stale: SASE has since added goals, gates, holds, receipts, ToolRuns, auto-restart and remote dispatch, and Gas Town shipped 1.0 through 1.2.
- `research:202610/master_ci_red_why_and_how_to_stay_green/…md` (2026-10-01), which measures the landing-path problem.

---

## 2. What Gas Town is in October 2026

**Timeline:**
- **Launch, 2026-01-01.** Yegge launched it after "several orchestrators during 2025", built on his Beads issue graph. Twelve days later he reported "over 100 PRs from nearly 50 contributors".
- **v1.0, about 2026-04-03.** Billed "from Clown Show to v1.0".
- **v1.1.0 (2026-05-06), v1.2.0 (2026-05-27), v1.2.1 (2026-06-06).** Then `main` stops on 2026-07-23. The last weeks are mostly agent-authored PR-sheriff and merge-queue fixes.

**Scale (from ai.engineer):**
- About 17.8k GitHub stars and 1.6k forks (Aug 2026).
- More than 2,600 Discord members and more than 500 contributors across Beads, Gas Town and Gas City (April 2026).
- Kilo sells a hosted "Gas Town by Kilo" with the Wasteland federation built in.

**Successor: Gas City (v1.5.0, active today).** Its migration guide says:
- *"the orchestrator hardcodes **zero roles** — every role you knew is now configuration."*
- Deacon/Witness watchdog logic becomes **"orchestrator health patrol + reconciliation"** — that is, deterministic infrastructure.
- Plugins become "orders" (exec orders need "no prompt, no session, no extra role agent").
- Formulas can run "as a graph across many agents, out of your session".
- Runtimes include tmux, subprocess, exec, ACP, Kubernetes and herdr.
- `docs/getting-started/coming-from-gastown.md`

**Yegge's own verdict (Aug 2026):**
- He moved to a private, closed-source harness, Wheelhouse, which is "roughly the same shape as Gas Town, but without the scars".
- Wheelhouse runs 50–60 agents with 18 long-lived "officer" seats; "Only Fable is allowed to talk to humans".
- Its merge queue can push "500 commits per day … (though we average 270/day)". At queue depth 100 they "abandon the bisection and just smash it all in with a megabatch. And then we do swarm diagnosis."
- His operating rule: **"crons watch, models act."**
- His cost: $87k–122k a month at list price, about $2.8k–5k a month out of pocket via many Max accounts. He himself calls that account rotation "almost certainly a violation" for a multi-person company.

**What follows from this:** the supervision, landing and dispatch ideas survived Yegge's rewrite (Wheelhouse) and the platform rewrite (Gas City). The tmux, LLM-patrol and hard-coded-role parts did not.

---

## 3. The architectures side by side

| Dimension | Gas Town | SASE |
|---|---|---|
| **Execution model** | Long-lived tmux sessions. "GUPP": *if work is on your hook, you run it* (pull-based). NDI: nondeterministic idempotence through persistent beads plus overseers | **Single-turn** agents. Continuation is always mechanical (monitor, pipe, plan, questions, gate shell) (`decisions:single-turn-agents`) |
| **Driving the CLI** | Keystroke injection: `tmux send-keys` in 512-byte chunks, readiness by matching `❯ `, submit-verify (`internal/tmux/tmux.go:1777`, `submit_verify.go`) **[code]** | Headless stream-JSON subprocess per provider, normalized to one turn (`decisions:adapters-normalize-harnesses`) |
| **State** | Dolt SQL server per town; beads, mail and convoys are rows; wisps are `dolt_ignore`d | Files plus Rust-owned SQLite stores; beads in a git sidecar; ToolRun ledger; goal ledger |
| **Coordinator** | **Mayor**: a Claude session that files beads and `gt sling`s them to workers | None; the human (TUI, Telegram, mobile) is the coordinator. Agent launch requests need a human click |
| **Supervision** | Go daemon (3-min heartbeat) → Boot (LLM triage) → Deacon (LLM patrol) → per-rig Witness/Refinery | Service host restarts *daemons*. PID liveness and orphan reaping for agents. Update-skew auto-restart only |
| **Landing** | Polecat runs `gt done` → MR bead → Refinery LLM merges one at a time after tests on the merged tip | The host finalizer commits and pushes straight to `master` (rebase, retry). CI only reports after the push |
| **Workflows** | TOML formulas → molecules/wisps; mostly a checklist printed into the prompt | Typed YAML macro workflows (agent/bash/python/parallel steps, if/for/while, HITL), plus plans → epics → beads with Kahn waves |
| **Human loop** | Escalation beads, plus email, SMS and Slack by severity | Durable gate turns, autonomy profiles, mentors, LaunchApproval, sudo gate |
| **Observability** | OTel logs and metrics, `gt feed` TUI with a Problems view, htmx dashboard, `gt costs` | ACE TUI, Admin Center statistics, local telemetry SQLite, ToolRun triage |
| **Distribution** | Homebrew, `go install`, Docker Compose, Windows (minimal), hosted (Kilo) | `uv tool install`; Linux and macOS; alpha |

**The root difference.** Gas Town is a *process model*: persistent role agents supervised by other agents. SASE is a *transaction model*: a one-turn agent, plus a host that owns completion and every continuation.

That difference explains some of Gas Town's advantages — mid-task nudges, an always-on Mayor — and those cannot be copied without breaking SASE's decision records.

Most of the gaps that matter do **not** depend on the process model: the landing gate, failure policy, liveness classification, escalation, telemetry export, crash-time snapshots and workflow overlays. Those are the ones to borrow.

---

## 4. Where Gas Town is better, area by area

Each subsection gives what Gas Town does (with evidence), what SASE does today, and how far to trust Gas Town's implementation.

### 4.1 Landing: tests on the integrated tip, and proof of merge

**Gas Town:**
- **The Refinery is an LLM agent working through a 1,285-line formula** (`internal/formula/formulas/mol-refinery-patrol.formula.toml`, v16) **[code]**. For each MR in score order it:
  - merges the target into a temp branch (`git merge --no-ff origin/<target>`);
  - runs the rig's setup, typecheck, lint, build and test commands on the *merged* result;
  - classifies a failure as branch-caused (send `FIX_NEEDED` mail to the polecat and keep the MR) or already on the target (file a P1 bug and merge anyway).
- **Priority scoring with anti-starvation** (`internal/refinery/score.go`) **[code]**: 1000 + 10 per hour of convoy age + 100 × (4 − priority) − 50 per retry + 1 per hour of MR age.
- **Post-merge proof** **[code]**: `gt mq post-merge` refuses to close beads or delete branches unless the target contains the MR's submitted `commit_sha` (`internal/cmd/mq.go:601-617`).
- **`merge-blocks` dependencies** **[code]**: these resolve only when the blocker's close reason starts with "Merged in " (`internal/convoy/operations.go:236-268`). Downstream work therefore waits for *merged* code, not just a closed bead.
- **Integration branches for epics** **[code]**: `gt mq integration land` uses a flock, a temp worktree and an ancestry check that makes retries safe (`internal/cmd/mq_integration.go`). A `.githooks/pre-push` hook blocks accidentally landing `integration/*` on the default branch.
- **Batch-then-bisect is [unwired].** `ProcessBatch` / `ProcessMRInfo` / `doMerge` in `internal/refinery/batch.go` and `engineer.go` have no non-test callers, yet `README.md` advertises it.

**SASE today:**
- The `builtin@commit` finalizer rebases onto `origin/<default>`, commits and pushes, retrying on push races (`src/sase/vcs_provider/plugins/_git_commit_dispatch.py`). Nothing serializes landings across agents.
- Master Gate runs **on push**. The 2026-10-01 swarm found:
  - 42% of pushes landed before the previous commit's gate finished;
  - ordinary `sase final submit` records `verdict_provenance: "unverified"` instead of refusing;
  - local `just check` passed 26 of the last 1,000 runs on athena, so a red result "carries no information";
  - no branch protection on `master`.

  SASE is landing about 60 commits a day (1,853 in the last 30 days), peaking at about 111.
- The open `sase-1lh` epic, *Green Master Gate and Full CI, then ship v0.18.0*, fixes the current reds. I found no bead that adds a mechanical refusal on the landing path (`sase bead search "merge queue"` returns nothing).

**Why Gas Town is ahead:** it has a point where a red change is refused, plus a proof step. SASE has neither, and is paying for it in repeated "make master green" epics: `sase-1lh`, `-1kx`, `-1kl`, `-1jz`, `-1i5.9.1.2`, `-1c1.13`, `-10w.5`.

**Caveats:**
- Gas Town's merge safety is enforced by prompt text. The LLM decides "pre-existing vs. caused" and *may merge red*.
- Its role template and formula contradict each other on conflict handling.
- The project landed its own PRs through GitHub, not its Refinery (`docs/pr-sheriff/` evidence: "without refinery or merge queue").
- Borrow the *mechanisms* (verify on the integrated tip, prove the SHA, merged-only dependencies). Don't borrow LLM-judged merging.

### 4.2 Closing the loop on failed work

**Gas Town:**
- **Re-dispatch with model promotion [code].** `deacon.Redispatch` → `resolveAgentForRedispatch` reads `.gastown/model-escalation.json`. Rules such as `promote_after_failures: 2 → opus` re-sling a failed bead on a stronger agent (`internal/deacon/redispatch.go:218-445`, called from `internal/cmd/deacon.go:1525`). After the attempt cap, it escalates to the Mayor instead.
- **Respawn circuit breaker [code].** After `MaxBeadRespawns=3`, it sends `SPAWN_BLOCKED` to the Mayor at urgent priority. If the work is already on main, it closes the bead instead (`internal/witness/handlers.go:2755-2810`).
- **Prior-attempt reuse [code].** A re-slung bead gets the previous attempt's branch injected so the new worker can cherry-pick it (`internal/cmd/sling_dispatch.go:318-325`).
- **"Mountain" convoys: failure counting [code], stall audit [doc-only].**
  - Built: after three failures a bead is labelled `mountain:skipped` and the convoy continues with independent work (`internal/witness/mountain.go`).
  - Not built: the Deacon's stall audit.
  - Bug: `gt mountain pause` has no effect, because nothing reads the label.

**SASE today:**
- Auto-restart covers **only update-skew deaths before the model turn**, once per lineage. It "never restarts on provider errors, rate limits, OOM, timeouts, kills, or test failures" (`docs/reference/agent-auto-restart.md`).
- Provider retry covers only transient API errors. Claude's `fallback_model` is `"sonnet"` (`src/sase/default_config.yml:1807`): a *downgrade*, which is right for an overload but wrong for a task that failed.
- A failed epic phase parks its dependents and the lander until a human retries. `sase bead work <epic>` reschedules non-closed phases.
- Standalone ready tasks wait for human triage (`TaskTriage` gate).

**Why Gas Town is ahead:** a failure produces a *policy decision* — retry stronger, cap, skip, escalate — without a human in the loop. In SASE, every failed phase costs a human context switch.

### 4.3 Supervising live agents, not just dead PIDs

**Gas Town [code]:**
- **A three-level tmux health check** (`internal/tmux/tmux.go:2421`): session dead, agent process dead, or agent hung (`window_activity` past a threshold).
- **Heartbeat v2:** refreshed by *every `gt` command* through `persistentPreRun` (`internal/cmd/root.go:151,224`), plus self-reported state (`gt heartbeat --state working|idle|stuck`).
- **GUPP violation:** hooked work, agent alive, no bead update for 30 minutes (`internal/daemon/lifecycle.go:1090-1156`).
- **Zombie taxonomy** (`internal/witness/handlers.go:1535-1560`): stuck-in-done, agent-dead-in-session, bead-closed-still-running, idle-dirty-sandbox, self-reported-stuck, submitted-still-running, and others.
- **Restart-first policy.** It re-checks the session right before acting, deduplicates cleanup wisps (lowest ID wins), and checks whether the branch was already merged (including squash merges) before treating work as lost.
- **The `gt feed` Problems view** groups agents into GUPP-violation, stalled, zombie, working and idle, with one key to nudge (`n`) or hand off (`h`).

**SASE today:**
- PID and boot-time liveness, stale-claim cleanup (`src/sase/ace/scheduler/stale_running_cleanup.py`), orphan systemd-scope reaping, and a teardown watchdog that only fires *after* an accepted declaration.
- `docs/contribute/llm-invocation.md:378`: *"A provider that wedges before submitting its declaration is not covered."*
- There is no per-turn wall-clock or no-progress budget for agents. Monitors have one: `wall_clock` / `no_progress` timeout kinds exist only for monitors (`src/sase/core/continuation_wire.py:35`).

**Why Gas Town is ahead:** a quietly wedged agent gets noticed. SASE is actually *better placed* to do this — it gets structured stream-JSON events, not screen scrapes — but has not built it.

**Caveat:** Gas Town's history is a list of over-eager killers: the "Deacon murder spree", the "serial killer bug" that killed healthy witnesses, and the session-hygiene plugin. The lesson it learned the hard way is to **classify and report deterministically, and act conservatively**.

### 4.4 A coordinator agent and agent-to-agent messaging

**Gas Town [code]:**
- **The Mayor** is a Claude session in `hq-mayor`, shaped entirely by `internal/templates/roles/mayor.md.tmpl` ("File it, sling it"). Its tools are the `gt`/`bd` CLIs: mail, sling, convoy, escalate.
- **Mail stored as beads** (`internal/mail/router.go:1113-1213`):
  - two-phase, crash-safe acks (`internal/mail/delivery.go`);
  - `queue:` addresses with exactly one claimant, `@group` broadcast, reply-to and threads.
- **Delivery to a busy agent waits for its turn boundary:**
  - wait up to 3 seconds for idle, then queue a nudge;
  - Claude's `UserPromptSubmit` hook runs `gt mail check --inject` and drains the queue;
  - other runtimes get a 10-second poller.
- **Wheelhouse keeps the pattern:** 18 long-lived "officer" seats, and only one model talks to humans.

**SASE today:**
- No mailbox, ack, queue or broadcast, and no way to inject text into a live agent.
- Siblings coordinate through data at the start or end of a turn: `%wait`, `sase var`, `#fork`, `@agent:` references, `sase pipe`, and bead notes (`PROPOSED FOLLOW-UP:`).
- Launch requests from agents (`/sase_run` → LaunchApproval) **never auto-resolve.** `src/sase/autonomy/gates.py:21-29` lists only `plan`, `epic_plan` and `question` as auto-resolvable.
- The only human-free dispatch is approving an epic plan under `%auto`.

**Why Gas Town is ahead:** the human can hand off the *coordination* job itself ("tell the Mayor what you want"), and agents can talk to each other. In SASE, the human is the integration point.

**Caveat:** a literal always-on Mayor and mid-turn nudges break `decisions:single-turn-agents`, which can only be reopened by a true suspend/resume primitive. §8 proposes a version that fits SASE: a mechanically woken coordinator *session* with a launch budget, and inboxes delivered at the start of a turn.

### 4.5 Escalation: severity, out-of-band channels, re-escalation

**Gas Town [code]:**
- **Commands:** `gt escalate -s MEDIUM|HIGH|CRITICAL`, deduplicated by `--fingerprint` (`internal/cmd/escalate_impl.go:88-112`).
- **Routing by severity** from `settings/escalation.json`: medium → bead plus Mayor mail; high → plus email; critical → plus SMS. The implemented channels are SMTP, Slack webhook, SMS webhook and a log file (`:686-866`).
- **Stale re-escalation:** `gt escalate stale` bumps severity after 4 hours unacknowledged, at most twice. The Deacon LLM runs it, not a timer.

**SASE today:**
- Notifications come in three classes (priority, error, ordinary) with routing rules.
- Channels: TUI, Telegram, FCM push and `notify-send`.
- `sase notify +1` deduplicates.
- No severity scale, no email, SMS or Slack, and **no automatic re-escalation of an unanswered gate**.

**Why Gas Town is ahead:** an urgent blocker can reach the human through a louder channel, and a forgotten one comes back. This is a small change for SASE.

### 4.6 Operations observability

**Gas Town [code]:**
- **OpenTelemetry over OTLP HTTP:**
  - 23 counters, plus a `bd` duration histogram (`internal/telemetry/recorder.go:150-221`);
  - lifecycle log events (session, sling, done, mail, mol, convoy);
  - a per-spawn `run.id`, with work context flowing into `OTEL_RESOURCE_ATTRIBUTES` for child processes;
  - optional per-turn token events from transcript tailing (`internal/cmd/agent_log.go`).
- **`gt feed`:** a Bubble Tea TUI with agent tree, convoy panel, event stream and Problems view, fed by curated `.events.jsonl`.
- **`gt dashboard`:** about 11.9k lines of htmx/SSE with a command palette limited to an allowlist (`internal/web/commands.go:27`).
- **`gt costs`:**
  - token and cost totals by role and rig, recorded by a Stop hook;
  - but the pricing table is **hard-coded "as of Jan 2025"** and Claude-only (`internal/cmd/costs.go:198-214`).
- **`gt audit --actor`:** one timeline merging git, beads and events.

**SASE today:**
- A rich ACE TUI and Admin Center (eight stats views, including success rate and runtime per provider/model/effort).
- About 40 metrics in a local SQLite telemetry store, ToolRun failure signatures, `sase bead history`.
- **No OpenTelemetry export** (zero hits under `src/sase` or `docs`), **no dollar cost model**, **no Codex token usage**, **no web UI** (the blog calls it future work), and no general event feed. The only stream is the mobile gateway's SSE endpoint.

**Why Gas Town is ahead:** you can point Grafana or VictoriaMetrics at a town, put a dollar figure on a convoy, and watch one event stream.

### 4.7 Quota exhaustion without losing the session

**Gas Town [code]:**
- **Pause, not crash.** Usage-limit text in the pane triggers a fixed `PauseBackoff`, and it doesn't count toward the crash-loop budget (`internal/daemon/usage_limit.go`, CHANGELOG 1.2.0).
- **`quota_dog` account rotation (opt-in):**
  - it swaps the macOS Keychain OAuth token *while keeping `CLAUDE_CONFIG_DIR`*, so the pane respawns with `--resume` and keeps the conversation (`internal/quota/executor.go`);
  - macOS-only (`keychain_stub.go`), and carries the terms-of-service risk Yegge himself flags.
- **`gt estop` / `gt thaw`:** sends `SIGTSTP`/`SIGCONT` to every agent process group with context preserved, and the daemon stands down while it is active (`internal/estop/estop.go`). It is manual only.

**SASE today:**
- A hard provider disable that respects reset hints, plus `sase agent drain`, which reroutes stranded agents to other providers.
- But drain, like restart, "deletes the old run's artifacts", so in-flight progress is lost (`docs/reference/providers/usage.md` §Draining).
- Holds and maintenance mode stop *new* work. **Nothing freezes running agents.**

**Why Gas Town is ahead:** a usage wall costs wall-clock time, not work. SASE's systemd scopes make a freeze/thaw primitive cheap (cgroup v2 freezer).

### 4.8 Keeping work through a crash

**Gas Town [code]** (in `internal/cmd/done.go`, 2,748 lines, unless noted):
- **Checkpoint dog:** commits `WIP: checkpoint (auto)` in every live polecat worktree every 10 minutes (`internal/daemon/checkpoint_dog.go:19`), squashed later.
- **`gt done` safety nets:**
  - auto-pops orphaned stashes (`:723-777`);
  - auto-saves uncommitted work, but never commits deletions (`:779-841`);
  - a **zero-commit "sleepwalk" guard**, whose error message deliberately avoids naming the bypass flag (`:1016-1044`): *"LLM agents read error messages and self-bypass"*;
  - push verification, where the remote tip must equal HEAD or the bead reopens with `verified_push_failed` (`:2055-2097`);
  - resumable done-intent and checkpoints (`:915-932`).
- **A Stop hook** runs `gt done` if the polecat forgot.

**SASE today:**
- Stronger *at finish time*:
  - the declaration protocol, absorption of raw commits, a `dirty_work_discarded` guard;
  - bounded, fingerprinted commit attempts and a crash-resumable `commit_state.json`.
- Held workspace claims (14 days), a self-heal ladder and a rescue store keep a crashed agent's dirty tree on disk (`src/sase/axe/runner_workspace_heal.py`).
- **Missing:**
  - periodic snapshots *during* a long turn;
  - automatic recovery of orphaned stashes;
  - refusing a "done" that produced no diff and gave no reason;
  - an explicit remote-SHA-equals-expected check on code pushes (it relies on the push exit status).

### 4.9 Customizing workflows per repo, and resuming them

**Gas Town:**
- **Formula overlays [code]:** `replace`, `append` or `skip` for one step, per town or per rig, without forking the formula. `skip` hands its dependencies on to later steps (`internal/formula/overlay.go`, `gt formula overlay`).
- **Composition:** `extends` and `compose.expand` work **[code]**; `compose.aspects` is parsed but ignored.
- **Poured molecules [code]:** each step becomes a child bead, so a crash resumes at the last finished step. Root-only wisps trade that away to save rows (about 6,000 a day down to about 400).
- **Directives [code]:** per-role "operator policy" files at town and rig level, injected by `gt prime` (`internal/config/directives.go`).

**SASE today:**
- Per-project overrides replace the **whole file** (discovery order project → home → bundled).
- `workflow_state.json` is a status record, and `execute()` always starts at step 0. Resuming means passing a skipped step's output by hand.

SASE workflows are far more *expressive* than formulas (§5). Gas Town wins only on *patching* and *resuming*.

### 4.10 Continuity tools

**Gas Town [code]:**
- **`gt seance --talk <id> [-p "question"]`** runs `claude --fork-session --resume <id>`, so you can question a predecessor session *read-only* without loading its whole transcript into a new agent (`internal/cmd/seance.go:57`).
- **Crew roles turn compaction into a handoff:** the `PreCompact` hook runs `gt handoff --cycle` (`internal/hooks/config.go:357`). `gt prime` rebuilds role, hook, mail and checklist from bead state: "the beads state IS the handoff".

**SASE today:** `#fork` and `#fork_by_chat` inject earlier transcripts into a new agent. `sase chat show` reads them. Instruction bundles go through the system or developer channel, so they survive compaction. There is no read-only Q&A against a resumed predecessor session.

### 4.11 Provider reach

**Gas Town [code]:** 13 built-in presets (`internal/config/agents.go:25-54`): claude, gemini, codex, kiro, cursor, auggie, amp, opencode, copilot, pi, omp, vibe (Mistral), groq-compound. Tier 0 drives *any* interactive CLI through keystrokes.

**SASE:** 8 providers, all headless: claude, codex, grok, muse, agy, opencode, qwen, fakey.

**The trade-off:** Gas Town's reach costs fragility. Its own inventory counts 17 of 28 integration points that depend on Claude Code UI internals (`docs/design/agent-api-inventory.md`). The gap worth closing is specific presets that have headless modes (Copilot, Cursor, Amp), not adopting keystroke injection.

### 4.12 Doctor auto-repair

- **Gas Town:** about 88 checks across 75 files in `internal/doctor/`, 62 with a `Fix` **[code]**.
- **SASE:** 108 checks (`sase doctor -L`), but only about 9 fixers across `sase doctor`, `sase bead doctor` and `sase artifact doctor`. The design deliberately favors read-only checks plus a suggested next step.

### 4.13 Fencing credentials for unattended workers

**Gas Town:**
- **An mTLS proxy for containerized polecats [code]:**
  - only allowlisted `gt`/`bd` subcommands run, in a stripped environment;
  - git smart-HTTP is parsed so a worker can push only `refs/heads/polecat/<name>-*` (`internal/proxy/git.go:316`).
- **`exec-wrapper` plugins** can insert sandbox wrappers [code].
- **Still partial:** the certificate identity isn't wired into commands **[unwired]**, and Daytona sandboxing is **[doc-only]**.

**SASE:** all providers run with approvals bypassed. The guards that exist are a typed sudo gate, guarded recipes, a human-only global install, LaunchApproval and host-owned pushes. There is no containment.

**Yegge's lesson from the Beads 1.2.1 incident** (an agent cut an unauthorized release): *"a promise is weaker than a fence"*, and *"the problem was that she had all the permissions to do so in the first place."*

### 4.14 Evidence for running a role on a cheaper model

`gt-model-eval/` is a standalone promptfoo suite **[code]**, not part of Gas Town's CI:
- 94 cases: simulated shell output in, a `{action, reason}` decision out.
- Subjects: Opus, Sonnet and Haiku, graded by Opus.
- Purpose: decide whether patrol roles can move to cheaper models.

SASE has size aliases and an effort ladder, but no eval harness to justify which role can run cheaper.

### 4.15 Reach, onboarding and community

Gas Town has:
- Homebrew (installs `gt`, `bd` and `dolt` together), Docker Compose, a Windows path and a hosted offering;
- about 17.8k stars, more than 2,600 Discord members, and a documented on-ramp ("tell the Mayor what you want to build").

SASE is an alpha installed with `uv tool install`, on Linux and macOS. This matters for the planned launch post (`research:202610/sase_launch_post_outline/…`), not for daily use.

---

## 5. Where SASE is already better (don't over-borrow)

- **Completion integrity:**
  - an atomic declaration, host-selected finalizers that verify independently, and absorption of raw commits;
  - discarded-work guards, fingerprinted attempts, resumable checkpoints, publication-verified bead commits and a rescue store.

  In Gas Town, "done" is ultimately a CLI the agent chooses to run, and the merge verdict is an LLM's judgment.
- **Human checkpoints that don't hold resources:** gate shells, autonomy profiles, plan and epic approval, mentors, and a typed sudo gate with PAM and a ledger.
- **Capacity admission:**
  - a weighted priority queue with explicit `waiting.json` state;
  - holds with TTLs and deadlock notifications;
  - a file-lock gate that doesn't depend on the scheduler.

  Gas Town's scheduler drains about one bead per 3-minute heartbeat by default (`batch_size=1`).
- **Real execution graphs:** `sase bead work` builds Kahn waves, pre-registered waiters, recursive child epics and cross-project bead dependencies. Gas Town's default molecules are a *checklist printed into the prompt*; the `needs` and `acceptance` fields are advisory unless the formula is poured.
- **Workflow expressiveness:** typed inputs and outputs, `if`/`for`/`while`/`repeat-until`, `parallel`, `finally`, HITL, and bash/python steps mixed with agent steps.
- **Provider routing:** size aliases spanning several providers with weighted pools and ordered fallback; usage-limit disables that respect reset hints; drain/reroute; usage-window probes.
- **Robust adapters:** stream-JSON instead of screen-scraping and timed keystrokes.
- **Provenance:** commit footers (`SASE_AGENT`, `SASE_BEAD`, `SASE_PLAN`), published agent pages, audited memory, bead and repo reads, and bead event histories.
- **Measured verification:** the ToolRun ledger, triage verdicts, failure signatures and fingerprint-bound receipts.
- **Docs that match the code:** decision records with reopen conditions and generated docs. Gas Town's docs drift in both directions:
  - the plugin system is documented as "not implemented" but is;
  - model-aware molecules are documented as "DONE" but aren't;
  - the git author name, the Codex prompt mode and proxy identity are all described wrongly.
- **Remote fleet:** credentialed `%dispatch` to your own machines with one unified agent list.

---

## 6. Gas Town's cautionary lessons

1. **Watchdogs need tight limits on what they may destroy.**
   - Every supervisor layer in Gas Town caused incidents.
   - The fix each time was to take kill decisions away from thresholds: detect and report in Go, re-check right before acting, deduplicate concurrent actors.
   - Gas City then moved patrol into deterministic orchestrator code. Yegge's rule is "crons watch, models act".
2. **Don't use LLM sessions for mechanical checks.**
   - Boot's idle check "saves ~480 Claude sessions/day" (`internal/daemon/daemon.go:1320-1396`).
   - Plugins with a deterministic `run.sh` were still sent to an LLM by mail.
   - Gate types other than cooldown depend on an LLM reading cron text correctly.
3. **Docs ahead of code erode trust.**
   - The README sells a batch-bisect queue that is never called.
   - The CHANGELOG lists a rate-limit watchdog that was later deleted.
   - SASE's decision-record discipline is the antidote.
4. **Context bloat from re-injected inboxes.** Re-injecting hundreds of open plugin mails on every prompt "ballooned agent context to 60–70%" and froze the Deacon (CHANGELOG 1.0.1). Any SASE inbox needs read and expiry semantics from day one.
5. **Error text written for LLMs is an attack surface.** SASE's install guard already does this right: its refusal sends the bypass through `/sase_gate` (`tools/_sase_install_env.py:76-84`). Keep that discipline for any new refusal, such as a zero-diff guard or the landing lane.
6. **The factory can eat the product.**
   - Yegge says Gas Town broke when Opus 4.7 kept "fiddling with Gas Town itself", and that Wheelhouse's factory-to-product ratio "seems to be approaching 1:1".
   - SASE is mostly built *by* SASE (about 60 commits a day), so the same risk applies. The red-master treadmill is one symptom.
7. **Fences beat promises.**
   - The Beads release incident came from an agent that had the permissions in the first place.
   - For SASE's own release, publish and tag paths, use mechanical refusals: GitHub tag and branch rulesets, scoped tokens.

---

## 7. Ranked list: ways Gas Town is better than SASE

Ranked by how much it would change your outcomes, times the size of the gap, times how sure I am that Gas Town's version actually works. Items whose Gas Town evidence is partly unbuilt are flagged.

1. **It refuses to land untested integration and proves each merge.**
   - Tests on the merged tip, one merge at a time; `merge-blocks` resolves only on "Merged in"; post-merge SHA-ancestry proof; integration branches for epics. (§4.1)
   - SASE's landing path has no refusal point, and the cost is measured in days of red `master`.
   - The merge verdict is LLM-judged; batch-bisect is [unwired].
2. **It closes the loop on failed work automatically.**
   - Re-dispatch promoted to a stronger model, respawn circuit breaker, prior-attempt branch reuse, skip-after-N in mountain convoys. (§4.2)
   - SASE parks failed phases for a human and its retry fallback goes *down* a model tier.
3. **It supervises live agents.**
   - Stall/hung/zombie classification, heartbeat refreshed by any `gt` command, and a Problems view with nudge and handoff keys. (§4.3)
   - SASE cannot see a turn that wedges before it declares.
4. **A coordinator agent can dispatch work, and agents can message each other.**
   - Mayor plus `gt sling`; durable mail with acks, queues and broadcast; nudges delivered at turn boundaries. (§4.4)
   - SASE needs a human click for every launch an agent requests, and siblings can't talk mid-flight.
   - A literal port conflicts with single-turn agents.
5. **It escalates by severity out-of-band and re-escalates stale items.** (§4.5)
6. **It plugs into standard ops tooling.**
   - OTel export with run correlation, cost accounting, a live event feed, a web dashboard, and an actor audit timeline. (§4.6)
   - Gas Town's pricing table is stale.
7. **It survives quota exhaustion without losing work.**
   - Pause instead of crash, session-preserving account rotation, and estop/thaw of running agents. (§4.7)
   - Rotation is macOS-only and a terms-of-service risk.
8. **It keeps work through crashes.** 10-minute WIP checkpoint commits, orphaned-stash recovery, the zero-commit sleepwalk guard, resumable `gt done`, and verified pushes. (§4.8)
9. **It lets repos patch a single workflow step and resume a workflow from its last step.** Step overlays and directives; poured molecules. (§4.9)
10. **It offers continuity tools.** Seance (read-only fork-and-resume Q&A with a predecessor) and compaction turned into a fresh handoff. (§4.10)
11. **It supports more providers.** 13 presets, including Copilot, Cursor, Amp, Kiro and Mistral, and Tier 0 driving of any CLI. This comes at a fragility cost. (§4.11)
12. **Its doctor fixes more.** 62 auto-fixers vs. about 9. (§4.12)
13. **It has a design for fencing credentials.** An mTLS command proxy and branch-scoped push authorization. Partly [unwired] or [doc-only]. (§4.13)
14. **It gathers eval evidence before running a role on a cheaper model** (gt-model-eval). It is manual, not in CI. (§4.14)
15. **It reaches more users.** Homebrew, Docker, Windows, a hosted offering, and a large community. (§4.15)

---

## 8. Ranked list: recommended changes to SASE

The order weighs leverage against effort and fit with SASE's decision records. **Size** is a rough T-shirt estimate. Per the Rust-core boundary rule, policy marked **(core)** belongs in `sase_core`, with Python and TUI as thin adapters.

### R1. A mechanical landing lane that ratchets against the tip — addresses #1 · L · (core)

Make "green before it lands" mechanical without shrinking throughput below what SASE needs today.

1. **Per-repo landing lease.**
   - The commit finalizer takes a short lease per repo for the rebase → verify → push → prove sequence, so two landings never race past each other's verdicts.
   - SASE averages about 60 landings a day (peak about 111) against a Master Gate p50 of 12.7 minutes. A strict serial queue running the *full* gate per landing would top out around 113 a day and saturate on peak days. So verify with the agent's selected checks on the rebased tree, not the full gate.
2. **Ratchet, don't demand absolute green.**
   - Refuse a landing whose verified failure set on the *rebased* tree contains failures not present at the tip's baseline. The independent witness is the latest Master Gate or Full CI result for the tip.
   - This works even while `master` is red, which is when it matters most.
   - Use the existing receipt and triage machinery, keyed to the rebased-tree fingerprint, so that inherited reds stop being labelled NEW. The 2026-10-01 report found one inherited failure mislabelled NEW for 39 agents.
3. **Prove the push.** After pushing, confirm the remote default branch contains the expected SHA (Gas Town's `mq post-merge` rule). Only then close beads and resolve `%w(bead=…)` waiters, so dependents wait for *landed* code.
4. **Only when queue depth demands it, batch.**
   - Land N queued changes as one verified batch.
   - On failure, don't bisect. Land the members that pass individually and send the failure to a diagnosis agent.
   - This follows Yegge's megabatch-plus-swarm-diagnosis result, and Gas Town never wired its bisect anyway.
5. **Stop-the-line mode.** When the tip is red past a threshold, the lane accepts only commits that reduce failures, or reverts.

Refusals must route through a gate (`/sase_gate`) and must not advertise a self-bypass (§6.5).

### R2. A failure-policy engine for bead work — addresses #2 · M · (core)

1. **Per-epic or per-bead policy**, for example `on_failure: retry(max=2, promote=true) → skip_and_continue | park → escalate(sev=high)`.
2. **Promotion climbs the effort ladder.** Size-alias rung up, or the next model in an ordered `||` list. That is the reverse of today's transient-error fallback, which can stay a downgrade for overloads only.
3. **The retry gets the failed attempt's diff and transcript summary** (`#fork` plus the rescue-store diff), like Gas Town's prior-branch injection.
4. **Skip-and-continue** lets independent waves keep moving. The lander records skipped phases as explicit `PROPOSED FOLLOW-UP` work.
5. **A storm breaker**, like auto-restart's, caps retries across the fleet. Every attempt goes into bead history.

### R3. Live-turn liveness classification and a Problems view — addresses #3 · M · (core classification, TUI view)

1. **Build a progress signal from what adapters already stream:** last stream-JSON event, last tool call (`tool_calls.jsonl`), and last workspace write.
2. **Classify each running agent** as `working`, `quiet`, `stalled`, `wedged` (process alive, no events past a threshold) or `zombie` (claim alive, runner gone).
3. **Optional per-turn budgets:** `wall_clock` and `no_progress`, reusing the monitor timeout kinds that already exist.
4. **Act like Gas Town, but more cautiously:** notify first; act only after two observations and a re-check; let only explicit config auto-restart. Never auto-kill on first sight.
5. **TUI:** a Problems grouping in the Agents tab with one-key actions: kill, restart with `#fork`, hand off.

### R4. Stale-gate re-escalation and severity routing — addresses #5 · S

- Add `severity` to notifications and gates, default `normal`.
- Re-raise an unanswered gate after N hours on a louder channel: TUI → Telegram → push → optional email or Slack webhook. Do it at most twice, with fingerprint dedupe (extending `notify +1`).
- Let agents raise `sase notify create --severity high` for blockers. This is cheap and immediately useful for gates left unanswered overnight.

### R5. A coordinator *session*, compatible with single-turn agents — addresses #4 · L

- Instead of an always-on Mayor, define a **coordinator agent session**: a chain of single turns.
- **Mechanical wake events** start each turn: an epic phase fails, a gate goes stale, `master` turns red, a task bead reaches the triage bar, or a daily digest is due.
- **Each turn** reads state through existing skills (`sase_agents_status`, `sase_beads`, `sase_notify`), writes a summary to Telegram, files and links beads, and may **launch within a budget**.
- **The budget is a new autonomy rule** allowing LaunchApproval auto-resolution within limits: N launches a day, size ≤ M, tags such as `ci`/`flake` only. Every auto-launch is recorded in `sase autonomy log`.
- This keeps `gates-never-block` and `single-turn-agents` intact, because continuation stays mechanical. It also matches Wheelhouse's single-voice pattern ("only Fable talks to humans").
- **Optionally, a per-session or per-agent inbox delivered at the *start* of the next turn** as a prompt preamble, with read and expiry semantics (lesson §6.4). This is the single-turn-compatible half of Gas Town mail.

### R6. Export operations data and put a price on work — addresses #6 · M · (core)

1. **Opt-in OTLP export** from the Rust telemetry store, with a per-run `run.id` and bead, epic and goal attributes.
2. **A config-driven pricing table** — not hard-coded; see Gas Town's stale table — joined to `usage.json`, giving dollars per agent, epic and goal. Add Codex token capture to close the known gap.
3. **`sase events --follow`**, reusing the mobile-gateway SSE stream, as a CLI or TUI feed.
4. **A web dashboard can wait.** The mobile gateway plus the TUI covers the need.

### R7. Freeze/thaw, and suspend instead of drain — addresses #7 · S–M

1. **`sase agent freeze|thaw [--all|--provider P]`** using the cgroup v2 freezer on the existing `sase-agent-*` systemd scopes. This gives a true e-stop that keeps context and workspace.
2. **For usage-limit disables, a `suspend` alternative to drain** for agents mid-turn: freeze until the parsed reset time, then thaw. Drain stays the option when time matters more than progress.
3. **Do not adopt multi-account rotation** (terms-of-service risk, Yegge's own warning).

### R8. Snapshots during a turn, and a zero-diff guard — addresses #8 · S–M

1. **Every N minutes during a long turn**, the runner records `git stash create` / `write-tree` snapshots into the rescue store as refs. It never commits on the branch, so host-owned completion stays intact. A crash then loses at most N minutes.
2. **On workspace heal, offer orphaned stashes back** automatically: restore commands, not silent pops.
3. **A zero-diff declaration guard:** a declaration that closes a bead or claims implementation with no diff must include an explicit `no_change_reason`. Word the refusal so it doesn't name a bypass.
4. **Verify remote SHA equals expected after code pushes** (shared with R1.3).

### R9. Step overlays and deterministic resume for macro workflows — addresses #9 · M · (core resolution)

1. **Project or home overlays** that `replace`, `append` or `skip` a named step of a bundled workflow; `skip` passes its outputs through.
2. **`sase workflow resume <run>`**, which starts at the first unfinished step using the recorded `workflow_state.json` outputs, for workflows whose steps declare that they can be resumed.

### R10. A seance-style read-only Q&A with a past agent — addresses #10 · S

- **`sase chat ask <agent> "question"`**: fork-resume the predecessor's provider session read-only (Claude `--fork-session --resume`, Codex's resume), answer once, and discard.
- It is far cheaper than injecting a whole transcript with `#fork` when you need one fact.

### R11. More doctor fixers — addresses #12 · S (ongoing)

Turn the most frequently failing `sase doctor` checks into `--fix` actions with `-y`. Rank candidates by observed failure frequency, not by guessing (this follows `corpus-before-mechanism`).

### R12. A role-downgrade eval harness — addresses #14 · M

- Replay recorded, labelled decisions from roles that SASE runs at volume against cheaper models: triage verdicts, mentor findings, lander follow-up triage, bead-triage gate proposals.
- Use `fakey` and stored transcripts.
- The result is evidence for moving routine roles down the size ladder. It fits the existing "evals through goals" reading list.

### R13. Fences for unattended work — addresses #13 · S (rulesets) to L (containment)

1. **Now:**
   - GitHub tag and release rulesets on `sase-org/sase` and the sidecars, so only the release workflow can tag. This is Yegge's Beads lesson.
   - A required-status ruleset only once R1 exists, since today's direct pushes would conflict.
2. **Later:** optional systemd sandbox properties on agent scopes (`ProtectHome=`, `ReadWritePaths=<workspace>`), plus a scoped push credential per agent. Gas Town's branch-scoped push proxy is a good model if SASE ever runs untrusted or remote workers.

### R14. Headless presets for Copilot, Cursor and Amp — addresses #11 · S each

Add `sase_llm` adapters only where the CLI has a stream-JSON or print mode. Don't adopt tmux keystroke injection.

### R15. Distribution for the launch — addresses #15 · S–M

A Homebrew tap and a one-command Docker quickstart (container with `uv` plus one provider CLI), timed with the planned launch post. Low priority for daily use.

### Explicitly *not* recommended

- tmux keystroke injection and screen-scraping.
- LLM patrol agents for mechanical checks.
- Dolt as the state store.
- An always-on Mayor process.
- Multi-account quota rotation.
- Bisecting merge queues at SASE's current volume.
- Wasteland-style public federation.
- Agent "CVs" for named workers. SASE agents aren't persistent identities; keep per-model and per-alias outcome stats instead.

---

### Recommendation ↔ gap map

| Recommendation | Gas Town gaps addressed (§7 rank) | Fits SASE decisions? |
|---|---|---|
| R1 landing lane | 1, 8 (push proof) | Yes. Extends `host-owned-completion`; uses `receipts-prove-before-they-skip` and triage |
| R2 failure policy | 2 | Yes. The host decides; agents stay single-turn |
| R3 liveness | 3 | Yes. Detection on the host; action limited by explicit policy |
| R4 escalation | 5 | Yes. Gates still never block |
| R5 coordinator session | 4 | Yes, *as designed*. It needs a new autonomy rule for budgeted launch approval |
| R6 telemetry and cost | 6 | Yes (Rust core) |
| R7 freeze and suspend | 7 | Yes. Freezing a scope is not an agent waiting |
| R8 snapshots and zero-diff guard | 8 | Yes. Snapshots are host-side and never commit |
| R9 overlays and resume | 9 | Yes |
| R10 chat ask | 10 | Yes. A separate one-shot invocation |
| R11–R15 | 12, 14, 13, 11, 15 | Yes |

**Suggested order:** R4 and R7 are small, independent quick wins. R1 is the largest leverage and should start as soon as `sase-1lh` makes the tip green. R2 and R3 together cover unattended epics, and they make R5 safe to build.
