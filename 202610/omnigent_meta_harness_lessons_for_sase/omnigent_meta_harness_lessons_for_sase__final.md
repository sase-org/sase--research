# Omnigent vs SASE: What the Meta-Harness Teaches SASE

**Date:** 2026-10-07 · **Subjects:** `sase` 0.17.1 at `62604c10b7` (master) and
**Omnigent** 0.18.0.dev0 at `ee2488aee` (the request's "omniagent" is
[omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent)) · **Inputs:** five
independent reports (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`). The lead also checked
the disputed claims against both checkouts, the locally installed vendor CLIs, this
host's kernel settings, and first-party docs.

---

## 1. Bottom Line

The two projects wrap the same vendor CLIs (Claude Code, Codex, OpenCode, Antigravity,
Qwen, Grok Build), but each makes a different object durable:

- **Omnigent's durable object is the live session.** It is a meta-harness: a server,
  one runner per session, and a vendor harness behind one event vocabulary. You can
  reach it from a terminal, browser, phone, desktop app, Slack, or REST/Python. Its
  governance is a policy engine (ALLOW/DENY/ASK), optional OS sandboxes, an egress
  proxy, and a credential proxy. It is built for teams. Databricks launched it in June
  2026, and the repo has about 10.6k stars and over 1,100 commits in the last 30 days.
- **SASE's durable object is the work record.** Each agent is one provider turn in its
  own numbered clone. Beads, Patches, goals, artifacts, ToolRuns, and memory live
  outside any transcript. Gates end the turn rather than wait inside it, and the host
  owns completion. It is built for one operator running many agents.

All five researchers reached the same core judgment, and the lead's checks support it:

1. **Do not turn SASE into Omnigent.** Long-lived steerable sessions, a chat database as
   the source of truth, and multi-tenant co-drive would undo decisions that are paying
   off: `single-turn-agents`, `gates-never-block`, `host-owned-completion`, and
   file-backed work state. Omnigent's own code shows what that model costs:
   - `omnigent/server/DBSPEC.md` says the authoritative turn and steering state "lives
     in-memory in the runner process … and is never written to the DB".
   - `docs/network-resilience.md` pins eight known failures (R1–R8) as strict xfails.
     Examples: approval cards lost on restart, messages lost while the host is offline,
     and Stop reporting success while the host is unreachable.
2. **Borrow Omnigent's control mechanisms.** It took wrapping many harnesses seriously:
   - per-tool-call guardrails enforced through each CLI's own hooks;
   - an environment allowlist for every agent process;
   - a capability record for each harness, checked by a live conformance bench;
   - cross-vendor review that sees only the contract;
   - cost accounting with budget gates;
   - opt-in OS sandboxes.

SASE's biggest gap is mechanical enforcement inside a turn. Every SASE provider runs with
its bypass flag and a full copy of the operator's environment. Several of SASE's most
important rules exist only as prose in core memory. Examples: "agents never commit",
"stay in your workspace", "read sidecars only through `sase artifact read`". SASE has
fixed this kind of problem before. The `guarded-recipes` decision turned a ~90%-compliant
instruction into a guard whose refusal prints the remedy. The top recommendation repeats
that move with provider hooks, which SASE already uses for one rule (the Claude helper
guard).

---

## 2. Side by Side

| Dimension | SASE | Omnigent |
| --- | --- | --- |
| Primary user | One operator across a few tailnet machines | Teams: accounts, OIDC, invites, sharing |
| Unit of work | One provider turn, chained into sessions, clans, and epics | A long-lived multi-turn session bound to a runner |
| Durable state | Files and sidecar git repos (beads, Patches, goals, artifacts, ToolRuns, memory), plus the required Rust core | SQLite `chat.db`. Turn, steer, and approval state is in runner/server memory |
| Harnesses | 7 headless CLI providers plus `fakey`, as pluggy `sase_llm` entry points | 12 native-CLI packages plus SDK, ACP, and native-server modes. A generic `acp:<slug>` harness and community entry points |
| Multi-agent | Structural: macro swarms, `%wait`, clans, epics with phase waves and a land agent, LaunchApproval, holds, admission | Prompt-driven: the Polly supervisor calls `sys_session_send`. The parent is woken by an inbox notice. Worktrees come from a skill |
| Human-in-the-loop | Gate turns end the agent's turn. A durable bundle takes a write-once response from TUI, Telegram, mobile, or CLI | An in-turn ASK parks the tool call (hook HTTP request held up to 1 day). First answer wins across devices |
| Completion | Host-owned finalizers verify postconditions. The agent declares; it does not commit | The agent commits and opens PRs itself. A PR registry observes them. A human merges |
| Governance | Controls at orchestration boundaries: gates, LaunchApproval, sudo gates, holds, capacity, guarded recipes, Claude helper guard | Policy engine at request, tool_call, tool_result, response, and LLM phases. Session → agent → server scopes |
| Isolation | Per-agent full clones. No OS sandbox. Bypass flags. `os.environ.copy()` | Optional bwrap+seccomp, Seatbelt, or Job Objects. L7 egress proxy, credential proxy, two-layer env allowlist, 9+ cloud sandbox providers |
| Cost | Subscription usage windows, auto-disable on limit, per-run token counts | Token pricing from a model catalog. Session, user-day, period, and sub-agent budgets. A "downgrade gate" |
| Knowledge | Core/reference memory, memory webs, audited reads, decision records, instruction bundles with delivery verification | `AGENTS.md` and skills. Optional Hindsight memory. Declared `InstructionDelivery`, but delivery is not verified |
| Surfaces | Textual TUI, CLI, Telegram, Android via the Rust gateway, Neovim | Web, desktop, iOS/Android, VS Code, Slack, REST/OpenAPI, Python SDK |
| Verification culture | `just check`, triage verdicts, receipts, `sase instructions verify`, TUI goldens, immutable decisions | Harness bench (12 probes, DRIFT verdicts), resilience lab with fault proxies, feature map with an every-entry-point rule |

---

## 3. Where the Reports Disagreed, and What the Code Says

The lead re-checked every claim that a ranking depends on. Several confident claims in
the inputs did not survive.

| # | Claim in the inputs | Verdict and evidence |
| --- | --- | --- |
| 1 | Omnigent sandboxes native CLIs by default, and bwrap is "mandatory" on Linux (gem, grk) | **Overstated.** The README says this. The code does not. The generated `claude-native` spec, and the shell terminals for every native wrapper, declare `os_env.sandbox: {type: none}` with the comment "the native CLI already runs unsandboxed on the user's workspace" (`omnigent/harnesses/claude_native/main.py`, `omnigent/native/native_coding_agents.py`). Spec-defined agents get bwrap only when the binary is present, and otherwise fall back to `none` (`omnigent/sandbox/bwrap.py`). The sandbox is real, but it is strongest for SDK and headless workers. Even Omnigent has not fully sandboxed native coding CLIs (cld was right). |
| 2 | Unpriced models fail closed with DENY (grk) | **Wrong in practice.** The module docstring says DENY. All four evaluators return `_UNPRICED_ASK` ("approve to continue without it") (`omnigent/policies/builtins/cost.py`). cdx and cld were right. |
| 3 | "The first deciding policy wins" (Omnigent website) | **Wrong.** The engine short-circuits on DENY, collects ASKs, and keeps going after ALLOW. ASK side effects apply only on approval (`omnigent/runtime/policies/engine.py`). |
| 4 | The hard cost cap terminates the run (gem) | **Wrong.** `max_cost_usd` is a downgrade gate. It denies only while the session is on an "expensive" model, and a single turn can overshoot before the next check. |
| 5 | Vendor CLIs in SASE "abort or stall" on permission prompts, so SASE needs a PTY bridge (gem) | **False premise.** Every SASE provider launches with its bypass flag: `--dangerously-skip-permissions` for claude, agy, and opencode; `--dangerously-bypass-approvals-and-sandbox` for codex; `--yolo` for qwen and muse; `bypassPermissions` for grok. Nothing prompts. The real risk is the reverse: nothing is checked. |
| 6 | SASE needs a community provider-plugin API (mus) | **Already exists.** `sase_llm` is one of eleven entry-point groups (`docs/plugins.md`). What is missing is a capability contract. |
| 7 | SASE lacks queued follow-ups and joins (mus, cld) | **Mostly exists.** `%i(suffix, session=parent)` adds a WAITING member behind a running parent. `%wait:<clan>` waits for a whole clan generation, and this research swarm is itself one such join. What is left is narrow: LaunchApproval's `resume_requester` resumes the requester when the **gate settles**, not when the launched children **finish** (`src/sase/agent/launch_request_continuation.py`). |
| 8 | SASE has no cost data | **Partly wrong, and the cheapest fix in this report.** Claude's stream-json `result` event includes `total_cost_usd`. `_subprocess_claude.py` sums only the token keys into `usage.json`, which is a `dict[str, int]` (`_subprocess_artifacts.write_usage_artifact`). The cost figure is dropped. |
| 9 | Codex lacks a pre-tool hook, so hook enforcement is Claude-only | **Wrong.** Omnigent installs `PreToolUse`, `PostToolUse`, and `UserPromptSubmit` command hooks into a per-session `CODEX_HOME`. One converter (`omnigent/native/native_policy_hook.py`) serves both Claude and Codex. The local `codex-cli 0.161.0` has `--dangerously-bypass-hook-trust` for automation. Whether Codex hooks still fire under SASE's bypass flag is untested and should be the first probe. |
| 10 | Mentors are the place to add cross-vendor review | **Not today.** The `sase` project's `sase/sase.yml` configures no `mentor_profiles`. Master took 1,985 commits in the last 30 days with zero merges. The epic **land agent** (`epic_lander_model: "@large"`) is the review point that actually runs. |
| 11 | Omnigent's durability gaps are speculative | **Verified.** This is the DBSPEC statement and the R1–R8 xfails quoted in §1. |

---

## 4. What SASE Already Does Better (Keep)

These are constraints on any change below:

1. **Work state outside transcripts.** Beads, plans, epics, Patches, goals, artifacts,
   and ToolRuns. Omnigent has no plan or issue graph. Its "projects" are new-chat
   defaults.
2. **Host-owned completion.** Omnigent agents commit and open PRs themselves, and a PR
   observer records them afterward. SASE's declaration plus verified finalizer is a real
   trust boundary.
3. **Gates that end the turn.** They survive restarts, hold no provider process, and use
   no budget while waiting. Omnigent's parked-ASK model is the source of R1 and R2.
4. **Admission control.** Holds, weighted capacity, and launch plans. Omnigent's
   automation timers run in-process with "no distributed leasing", so a deployment with
   several replicas fires each task once per replica. Missed fires are never replayed
   (`docs/AUTOMATIONS.md`).
5. **Instruction-delivery verification and audited memory.** Omnigent declares
   `NOT_DELIVERED` for several native harnesses. SASE reads provider session records to
   show what was actually loaded.
6. **Immutable decision records.** cld found Omnigent docs drifting from its code in
   several places, such as harness counts, a "PROPOSED" spec that is already
   implemented, and design docs cited by code but missing from the tree. Findings 1–3 in
   §3 are more examples.
7. **Full clones per agent by default.** In Omnigent, each child gets its own worktree
   only because Polly's `fanout` skill creates one. Its `worktree_guard` policy is
   opt-in.

Omnigent independently arrived at SASE's continuation model for orchestration. Polly's
prompt says "act in the same turn you announce", no polling, no timers. It ends its turn
after dispatch and is woken mechanically by inbox notices. That is evidence for
`single-turn-agents`, not against it.

---

## 5. Ranked Recommendations

The ranking weighs value to one operator running many agents across several vendors,
fit with SASE's decisions, and cost. Effort: **S** is days, **M** is one or two weeks
of epic work, and **L** is several epics.

Per SASE's own conventions:

- Every user-facing item ships behind a flag bead.
- Shared evaluation logic goes in `sase_core`, with Python adapters calling it.
- Any rule that can refuse work starts in report-only mode.

"Backed by" lists which input reports independently proposed the item.

### 1. Turn the prose rules into deny-and-redirect guardrails using provider hooks — M

**Backed by:** cld #1, cdx #2, grk #3, gem #3, and mus #1 (as a policy layer).

**What Omnigent shows.** One policy evaluator runs inside different native CLIs through
their own hook systems. Claude and Codex share a converter for `PreToolUse` payloads. A
tool-call DENY fails closed. The useful builtins are deterministic and parse argv:

- `blast_radius` blocks force-push, catastrophic `rm -rf`, and hard reset to a remote.
- `worktree_guard` blocks absolute paths and `..` escapes.
- `read_only_os` blocks write tools for report-only agents.
- `github_policy` limits repos and branches, for MCP calls and for parsed `git`/`gh`
  commands.

**SASE today.** All seven providers run with bypass flags. The Claude helper guard
(`src/sase/llm_provider/_claude_helper_guard.py`) already proves the mechanism: a
stdlib-only `PreToolUse` script that denies root-only operations to native helpers. It
is used for that one rule.

**Proposed shape:**

- **Inside a turn, the only verdicts are ALLOW and DENY.** There is no in-turn ASK,
  because a SASE gate never blocks an agent. Each DENY returns a redirect naming the
  sanctioned path, which is the `guarded-recipes` pattern:
  - commit through `/sase_final`;
  - run privileged work through `/sase_sudo`;
  - open other repos through `sase repo open`;
  - read sidecar artifacts through `sase artifact read`;
  - ask before destructive work through `/sase_gate`.

  That last redirect is how Omnigent's ASK maps onto SASE. The agent opens a gate, its
  turn ends, and the answer resumes it.
- **Starter rules,** all deterministic and based on argv or paths:
  - `no_raw_vcs_mutation`: deny `git commit|push|rebase|reset --hard` and
    `gh pr create|merge`, but allow `sase stitch create`, which the explicitly invoked
    `/sase_git_commit` skill uses.
  - `workspace_escape`: deny writes outside the claimed workspace, its opened repos, the
    managed temp root, and the `~/.sase` paths the `sase` CLI itself writes.
  - `blast_radius`: port Omnigent's argv semantics.
  - `role_read_only`: for research, question, and reviewer roles.
  - `sidecar_direct_read` and `repo_web_fetch`: deny reading sidecar paths directly and
    deny `raw.githubusercontent.com` / GitHub file-content fetches.
- **Coverage.** Claude first, because the hook path exists. Codex second, after the
  probe in §3 #9 confirms its hooks fire under SASE's flags. Publish a per-provider
  coverage table, like the helper-coverage table in `docs/agent_providers.md`. A
  provider without hooks stays prompt-only, and the table says so.
- **Evidence loop.** Record every would-deny and deny as a run annotation in the Tools
  or FINAL card. Use those records to promote each rule from report-only to enforcing.
- **Thrash and loop detection** goes here as observe-only signals over
  `tool_calls.jsonl`: N consecutive failing calls, repeated identical commands, extreme
  call counts. Per `triage-annotates-does-not-change-exit-codes`, these notify and
  annotate. They never change an outcome. (Omnigent: `detect_thrashing`, `detect_loop`,
  and `max_tool_calls_per_session`.)

**Done when:**

- a canary `git push --force` from a Claude agent is denied, and the redirect text
  appears in the transcript;
- report-only mode logs would-denies without blocking;
- the coverage table matches what the probes observe (see #3).

### 2. Give provider processes a minimal environment — S

**Backed by:** cld #4, grk #2, cdx #7, and gem #2 (partly).

**What Omnigent shows.** `omnigent/inner/agent_env.py` builds each agent's environment
as deny-by-default: a safe base, plus the harness's own credential family, plus
`env_passthrough` entries declared in the spec. Its docstring records why: five
harnesses leaked every secret on the host until issue #3445 fixed it. A second
allowlist (`_RUNNER_ENV_ALLOWLIST`) filters what the host passes to the runner.

**SASE today.** `claude.py`, `codex.py`, `agy.py`, and `muse_provider.py` all start from
`env = os.environ.copy()`. SASE research agents read untrusted web pages while holding a
shell and every token the operator has exported. Because completion is host-owned, SASE
agents need *fewer* credentials than Omnigent agents do. Pushes and PRs belong to
finalizers.

**Proposed shape.** For each provider, build the environment from:

- a base allowlist;
- the provider's own auth variables;
- the `SASE_*` variables;
- an `agent_env.passthrough` list in config, per project and per role.

Log the dropped variable names (never their values) once per run, and run report-only
for a soak period.

**Done when:** an agent running `env` cannot see another provider's API key or
`GH_TOKEN` unless config passes it through, and a diagnosable log line names each
dropped variable.

### 3. One declared capability record per provider, checked by conformance probes — M

**Backed by:** cdx #1, grk #1 and #15, cld #3, and mus #3 (as a capability contract).

**What Omnigent shows.** `HarnessCapabilities` declares each harness's behavior as data:

- integration mode;
- elicitation;
- resume, interrupt, streaming, and steering;
- images and compaction;
- fork history;
- `InstructionDelivery` (composed-per-turn, session-snapshot, first-user-prefix,
  not-delivered, unknown).

`tests/harness_bench/` has 12 probes, including policy ALLOW/ASK/DENY, cost tracking,
interrupt, and fork replay. A `reconcile()` step reports **DRIFT** when declared and
observed behavior differ, and it has already corrected real declarations. Two cautions
from its README carry over:

- A clean exit can mean that no live probe ran. Automation must require complete
  observations.
- The DENY probe must exercise the tool-call path, not deny the whole request.

**SASE today.** Provider facts are scattered:

- prose tables in `docs/agent_providers.md` and `docs/llms.md`;
- `llm_usage_capabilities()`;
- the helper-channel probe cache;
- one-off `_subprocess_*` parsers.

`sase instructions verify` is the closest thing to a bench, but it only observes and
never gates. Instruction bundles are still E2 shadow-only. The
`adapters-normalize-harnesses` decision depends on per-CLI behavior that any vendor
release can break silently: disabled background and wake, wait guards, helper channels,
tool-call and usage capture, and instruction channels.

**Proposed shape:**

- **One versioned record per `sase_llm` provider,** with these fields:
  - `single_turn_enforcement` (mechanical, guard, or prompt-only);
  - `background_disabled` and `wake_disabled`;
  - `helper_channel`;
  - `policy_hook` (for #1);
  - `tool_call_capture`, `usage_capture`, and `cost_capture` (for #5);
  - `instruction_delivery`, using Omnigent's vocabulary;
  - `native_sandbox_modes` (for #6);
  - `max_sync_wait`.
- **Cheap live probes:**
  - a wake-up request is refused or blocked;
  - no background task outlives the turn;
  - a forced tool call lands in `tool_calls.jsonl`;
  - `usage.json` is populated;
  - the helper guard blocks `sase final` from a helper;
  - the policy hook denies a canary command.
- **Where probes run:** `sase doctor -D`, after a vendor CLI upgrade, and on a
  scheduled AXE job.
- **On DRIFT:** notify. Optionally soft-disable the provider for non-critical roles.
- Fold `instructions verify` in as one probe family, so there is a single source of
  truth.

**Done when:**

- one matrix separates supported, partial, unknown, skipped, and drifted;
- a missing probe never counts as a pass;
- launching a role that needs an unsupported capability fails before spawn;
- doctor, Launch Control, and the docs tables all read from the same record.

### 4. Cross-vendor review that sees only the contract, at the epic land step — S–M

**Backed by:** cld #2, cdx #5, gem #6, grk #10 and #14, and mus #5.

**What Omnigent shows.** Polly's `cross-review` skill (`examples/polly/`) works like
this:

1. Run deterministic checks first.
2. Snapshot the diff with its base and head SHAs.
3. Send it, with the acceptance contract, to a reviewer from a **different vendor**.
   The reviewer gets "never the implementer's transcript or worktree. The cross-vendor
   independence is the whole point."
4. Send blocking findings back to **the same implementer conversation**.
5. Cap the loop. Polly never merges.

A GitHub workflow runs the same pattern on Omnigent's own PRs.

**SASE today.** The land agent runs on `@large` or `@xlarge` with no rule about which
providers wrote the code, and it starts from the implementers' bead notes, which is the
narrative contamination Polly avoids. Mentor profiles have no model or provider field,
and none are configured. The size aliases already span several providers
(`size-alias-effort-ladder`), so the pool for diversity exists. SASE's research swarm
already applies multi-vendor independence to research; this would apply it to code.

**Proposed shape:**

- Add an **author-relative exclusion** to alias resolution: resolve this alias but skip
  the vendors that wrote commits X..Y. Use Patch and agent metadata to find those
  vendors.
- Judge independence by the **resolved model vendor or family**, not the harness name.
  OpenCode, for example, can reach the same vendor's models (cdx).
- **Contract-only first pass:** the diff snapshot, plus the plan's acceptance criteria
  and bead descriptions. Bead notes and chats are shown only after the independent
  verdict is written.
- Send blocking findings to a **session successor of the original phase agent**, rather
  than having the land agent fix everything itself. Cap the number of rounds.

**Done when:**

- review evidence is tied to an exact diff, and a later edit invalidates it;
- a wrapper over the same vendor is not counted as independent;
- when no independent model is available, the review reports that limitation instead
  of producing a review anyway.

### 5. Record the cost data SASE already receives, roll it up, then budget admission — M

**Backed by:** cld #5, cdx #2, grk #3, mus #1, and gem #3.

**What Omnigent shows:**

- `record_usage` prices tokens, including cache reads and writes, from a model catalog.
- Soft ASK thresholds are approved once on the root, so sub-agents do not re-ask.
- The hard cap is a **downgrade gate**, not a kill.
- Sub-agent budgets are attached when work is dispatched.
- Unpriced usage triggers an ASK, never a silent $0.
- Its docstring admits that a single turn can overshoot before the next check.

**SASE today.** SASE is strong on subscriptions: `sase usage` reads 5-hour and weekly
windows, auto-disables a provider on its limit, and routes around exhausted providers.
It has no dollar or window-% rollup per epic, clan, goal, or tribe, and nothing budgets
admission. Claude's `total_cost_usd` is already being discarded (§3 #8).

**Proposed shape, in order:**

1. **Capture.** Write the provider-reported cost and the actual model into
   `usage.json` / `run_metadata.json`. Unknown values are recorded explicitly, never as
   zero.
2. **Roll up** by clan, epic, tribe, and goal (the goal ledger is the natural owner).
   Use separate units and never mix them:
   - window-% of each subscription;
   - API-equivalent dollars at list price;
   - "unknown".

   Show the rollup in Statistics and on gate previews, for example "this epic used ~18%
   of Claude weekly".
3. **Admission.** Add an optional `budget:` on `sase bead work` and `%clan`:
   - Crossing a soft threshold raises a gate turn.
   - Crossing the hard threshold **steps the size alias down** for the remaining phases
     (`@large` → `@medium`), adapting Omnigent's downgrade gate. It does not refuse.

   Budgets are enforced only at SASE-owned boundaries: launch, successor, and finalizer.

**Done when:**

- duplicate delivery never double-counts;
- two concurrent children cannot both spend the same remaining budget;
- unknown pricing is visible;
- no exact dollar cap is promised while spend from in-flight turns is unbounded.

### 6. Execution profiles: vendor sandboxes for read-only roles first, SASE's own sandbox later — M, then L

**Backed by:** gem #1 and #2, grk #2, cdx #3 and #7, cld #10, and mus #9.

The inputs disagreed most on ranking here. gem ranked sandboxing first ("critical"),
and cld ranked it tenth. The lead's position: the threat is real, but #1–#2 capture most
of the value at a fraction of the cost, and an OS sandbox around a full coding CLI is
harder than it looks. Omnigent itself ships its native wrappers unsandboxed (§3 #1).

**Step A (M): use the sandboxes the vendors already ship, for read-only and
untrusted-input roles.** These roles are research, reviewer or mentor, and question
agents.

- `codex exec --sandbox read-only|workspace-write` is available locally.
- Claude Code has a built-in sandbox, set with `sandbox.enabled` in settings. It uses
  bubblewrap on Linux and Seatbelt on macOS, and has domain allowlists. Its
  [docs](https://docs.claude.com/en/docs/claude-code/sandboxing) note two limits: it
  covers Bash and child processes but not the built-in Read and Edit tools, and it does
  not hide `~/.ssh` or `~/.aws` unless configured to.
- SASE already has a precedent: `SASE_MUSE_SANDBOX=on` keeps Muse's sandbox for
  research agents.

**Design constraint the inputs missed.** SASE agents write through the `sase` CLI
itself. They write to `~/.sase` for artifact creation, the audit log for memory reads,
and finalizer context, and to `.git` when `/sase_git_commit` is invoked explicitly. The
Muse launcher's docstring already records that a read-only `.git` breaks in-run
`sase stitch create`. So every profile needs explicit writable paths for SASE's own
state. cdx adds that the provider process and the host finalizer should be separated, so
that a restricted agent can still finish.

**Host prerequisite.** On this host (apollo), `bwrap` is not installed and
`kernel.apparmor_restrict_unprivileged_userns = 1`. Any bwrap-based sandbox, whether
Claude Code's or SASE's own, needs an install step and an AppArmor allowance here. The
capability probes (#3) should report which modes actually work on each machine.

**Step B (L, later): a SASE-owned sandbox and credential broker for unattended AXE jobs
and `%proc` runs.** Use bwrap on Linux and Seatbelt on macOS, around the provider
process, with an explicit map of writable paths. Add a host-scoped credential broker for
`gh` and git over HTTPS that hands out placeholders bound to one host. This follows
Omnigent's `designs/SANDBOX_CREDENTIAL_PROXY.md` design: real secrets stay in the parent,
and an `oa_cred_*` placeholder works only on its bound host.

Prefer a fixed host-owned operation over a general egress proxy wherever one is enough.
Build only one backend before considering any cloud provider.

**Done when:**

- a research agent cannot write outside its declared roots or read a sentinel file
  outside them;
- escaping symlinks and helper processes are tested;
- finalization and audited `sase` operations still work;
- an incompatible provider fails before launch;
- running unrestricted remains an explicit choice.

### 7. A read-only browser view of agent records over the existing gateway — M–L

**Backed by:** cdx #4, grk #5 and #11, gem #8, and mus #10.

Omnigent's real advantage here is reach: the same session from any device. SASE already
has most of the backend:

- a paired, authenticated Rust mobile gateway with SSE plus `resync_required`;
- launch, kill, and retry;
- gate actions;
- fleet routes.

So "add remote access" or "build a REST API" would misdescribe the gap (cdx). What is
missing is a browser client and a published client contract. Plan:

1. Publish the gateway's committed API snapshot as OpenAPI.
2. Build a read-only web view of **durable records**: prompt, live reply, diff,
   artifacts, ToolRun outcomes, and pending gates.
3. Add gate answers.
4. Add launch and retry.

Treat durable state as authoritative and the stream as a convenience. Share records, not
a live vendor PTY, and keep co-drive out entirely. If collaborators ever appear, design
scoped, revocable read-only links separately; device pairing is not a collaborator
grant.

### 8. A feature entry-point map for features with many entry points — S–M

**Backed by:** cld #9, grk #4, and mus #6.

Omnigent's `feature-map/*.md` files list sub-feature IDs, every user entry point, the
test that drives each one, and known traps. They come with a rule: "a fix is verified
only when every entry point listed for the feature has proof".

SASE needs this more than most projects. The same action is often reachable from a
keymap, the palette, the CLI, a Telegram button, and the mobile gateway, and agents
usually prove one path. Start with the Agents tab and gates. This could become a
`features` memory web, read on demand. It does not conflict with
`corpus-before-mechanism`, because the map is the corpus, not retrieval machinery.

### 9. A join continuation for agent-initiated fan-out — S–M

**Backed by:** cld #6.

Add a `requester_continuation.mode: join_launched` to LaunchApproval. The requester's
successor waits on every approved slot and starts only when all of them are terminal.
Its prompt includes a generated block for each child: status, a reply excerpt, artifact
refs, and the FINAL summary. This mirrors Omnigent's `sys_session_send` plus inbox wake
without long-lived agents. The value is narrow because macro fan-outs already join
through `%wait:<clan>` (§3 #7).

### 10. A few task-shaped recipes instead of a second agent-spec language — S–M

**Backed by:** cdx #6, grk #7, and mus #2.

Omnigent's agent YAML (prompt, harness, tools, policies, sub-agents) and named agents
like Polly make composition easy to discover. SASE's macros and workflows are more
expressive, so do not build a second YAML runtime. Ship a handful of named, previewable
recipes built from existing parts:

- cross-vendor review (#4);
- investigate without edits (with #6's profile);
- parallel implementation;
- research swarm.

Before launch, each recipe shows its inputs, provider requirements, restrictions,
expected artifacts, and completion behavior. A portable export bundle (mus) can come
later if anyone needs to share recipes.

### 11. A generic ACP provider, once there is a concrete new CLI to add — M–L

**Backed by:** cld #8 and grk #6.

Omnigent uses one `acp:<slug>` harness for goose, qwen, grok, jcode, and others. An ACP
`session/prompt` naturally ends in a single turn. ACP's `session/request_permission`
would be a ready hook point for #1. SASE already speaks ACP for Grok usage. Keep the
custom Claude and Codex providers. Build this only when a specific new vendor would
otherwise need a new `_subprocess_*` parser.

### 12. Small operator-experience items — S each

- **Drain, then upgrade.** `sase upgrade` drains running agents, stops the service host,
  then upgrades. Add an install ledger and `sase uninstall --purge` with preview and
  backup (Omnigent: `omni upgrade`, `install_ledger.json`; grk #8).
- **CLI stream contract.** stdout carries data and stderr carries banners and progress
  (Omnigent `designs/CLI_CONTRACT.md`; grk #12).
- **Compaction-aware transcript reads.** When `sase instructions verify` or replay reads
  multi-megabyte vendor JSONL, start from the last compaction boundary (grk #13).
- **Adopt a session.** Wrap an ad-hoc Claude or Codex session in a SASE agent session
  (Omnigent `session_import/local.py`; cld #11).
- **Attachment caps.** Limit size and count for files that enter agent workspaces
  through the gateway or Telegram (mus #8).

### Summary

| Rank | Change | Effort | Decision it must respect |
| --- | --- | --- | --- |
| 1 | Hook-enforced deny-and-redirect guardrails, plus thrash signals | M | `gates-never-block`, `host-owned-completion`, `guarded-recipes` |
| 2 | Minimal provider environments | S | `host-owned-completion` |
| 3 | Capability record and conformance probes (DRIFT) | M | `adapters-normalize-harnesses` |
| 4 | Cross-vendor, contract-only review at land | S–M | `size-alias-effort-ladder` |
| 5 | Cost capture, rollups, budget admission with alias step-down | M | `hold-pull-fail-open`, admission |
| 6 | Execution profiles: vendor sandboxes now, SASE sandbox and credential broker later | M → L | `single-turn-agents` (finalizer stays host-side) |
| 7 | Read-only web view of records over the gateway, plus published OpenAPI | M–L | Rust-core boundary |
| 8 | Feature entry-point map | S–M | `corpus-before-mechanism` |
| 9 | `join_launched` continuation | S–M | `single-turn-agents` |
| 10 | Named task recipes (no new YAML runtime) | S–M | — |
| 11 | Generic ACP provider (on demand) | M–L | `adapters-normalize-harnesses` |
| 12 | Upgrade, uninstall, CLI-contract, and transcript polish | S each | — |

**Suggested order.** Start with #2, #1 in report-only mode, and #3's probes. All three
reuse existing plumbing, and #3's probes tell #1 and #6 which providers they can rely on.
#4 and the capture step of #5 are cheap and can run in parallel. The rest follow
whenever their area is next touched.

---

## 6. Not Recommended, or Deferred

| Idea | Why not |
| --- | --- |
| Long-lived steerable sessions; steering mid-turn (mus #4) | Contradicts `single-turn-agents` and causes Omnigent's R1–R8. Queued successors already exist. |
| PTY/elicitation bridge for vendor prompts (gem #5) | The premise is false (§3 #5). A parked approval is the in-turn blocking that `gates-never-block` rejected. |
| A chat DB as the source of truth; multi-tenant accounts, OIDC, co-drive | Conflicts with git-portable SDD and the single-operator trust model. Share records instead (#7). |
| Copy-on-write overlay workspaces (gem #4) | No measurement shows clone latency is a bottleneck (SASE clones use git alternates). Omnigent's version needs bwrap, and unprivileged user namespaces are restricted on this host. Revisit if clone time ever shows up in launch telemetry. |
| A cloud-sandbox fleet (gem #7) | Each provider adds auth, provisioning, and cleanup work. At most one execution target, after #6 step B (grk #9, cdx #8). |
| LLM-judged policies (`prompt_policy`, `intent_based_authorization`) | Nondeterministic and fail open. Omnigent's own docstrings say they are "not a security control". SASE has mentors and gates for judgment. |
| Hindsight-style memory; per-message LLM model routing | Blocked by `corpus-before-mechanism`. Deterministic size aliases are easier to reason about. Revisit routing with #5's data. |
| CEL policy language; feature flags as environment variables | Extra runtime for problems that in-process rules and flag beads already solve. |
| Required independent review for every small edit | Costs latency and quota. Make it selectable (#4) and measure it. |

---

## 7. Caveats

- **Nothing was run end to end.** That includes the harness bench, the sandboxes, the
  hooks under bypass flags, and Omnigent's resilience lab. Conclusions come from code,
  docs, local `--help` output, and host settings.
- **Omnigent changes quickly** (about 1,137 commits in 30 days). Its docs disagree with
  its code in several places (§3 #1–#3). Where they disagree, this report trusts the
  code at `ee2488aee`. Databricks' managed docs call it Beta; the repo calls itself
  alpha.
- **Claude Code sandbox details** come from Anthropic's docs and were not exercised on
  this host. That bwrap is missing and unprivileged user namespaces are restricted was
  observed directly on apollo; athena and the Mac were not checked.
- **SASE gaps were checked in the main repo only.** "No dollar budgets" and "no join on
  child completion" could be met by a plugin without showing up there.
- **Effort estimates are judgments.** None comes from a measured plan.

---

## Sources

**Input reports** (same directory): `…__cdx.md` (runtime control and accountability),
`…__cld.md` (meta-harness deep dive), `…__grk.md` (stack position and productization),
`…__mus.md` (product surfaces), `…__gem.md` (security posture). Related earlier
consolidation: `202610/openai_harness_engineering_vs_sase/…__final.md` (the
guard-promotion precedent and the landing-path findings).

**Omnigent** at
[`ee2488aee`](https://github.com/omnigent-ai/omnigent/tree/ee2488aee1d458033f854871b40bf3107d2fb748),
by repo path:

- `README.md` and `AGENTS.md`
- `omnigent/server/DBSPEC.md` and `docs/network-resilience.md`
- `omnigent/harness_capabilities.py`, `tests/harness_bench/`, and
  `docs/harness-bench-design.md`
- `omnigent/runtime/policies/engine.py`, `omnigent/policies/builtins/{cost,safety,orchestration}.py`,
  and `docs/POLICIES.md`
- `omnigent/native/native_policy_hook.py` and `omnigent/harnesses/codex_native/{hook,app_server}.py`
- `omnigent/harnesses/claude_native/main.py`, `omnigent/native/native_coding_agents.py`,
  and `omnigent/sandbox/bwrap.py`
- `omnigent/inner/{agent_env,sandbox,credential_proxy}.py` and
  `designs/SANDBOX_CREDENTIAL_PROXY.md`
- `examples/polly/config.yaml`, `examples/polly/skills/cross-review/SKILL.md`, and
  `feature-map/README.md`

**SASE** at `62604c10b7`:

- `src/sase/llm_provider/{claude,codex,agy,opencode,qwen,grok,muse_provider,_muse_launch}.py`
  (bypass flags, environment, Muse sandbox)
- `src/sase/llm_provider/_subprocess_claude.py` and `_subprocess_artifacts.py`
  (dropped `total_cost_usd`)
- `src/sase/llm_provider/_claude_helper_guard.py` and
  `src/sase/agent/launch_request_continuation.py`
- `docs/agent_sessions.md`, `docs/plugins.md`, and `docs/instruction_bundles.md`
- `src/sase/default_config.yml` (`epic_lander_model`) and `src/sase/config/sase.schema.json`
  (`mentor_profiles`)
- decision records `guarded-recipes`, `host-owned-completion`, and `gates-never-block`

**Web:**

- [Claude Code sandboxing docs](https://docs.claude.com/en/docs/claude-code/sandboxing)
- [Databricks: Omnigent on Databricks](https://docs.databricks.com/aws/en/omnigent/)
- [IT Brief: Databricks launches open-source Omnigent](https://itbrief.com.au/story/databricks-launches-open-source-omnigent-for-ai-agents)
- [OpenSourceForU launch coverage](https://www.opensourceforu.com/2026/06/databricks-launched-omnigent-an-open-source-meta-harness-for-ai-agents/)
