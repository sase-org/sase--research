---
create_time: 2026-08-25
updated_time: 2026-08-25
status: research
---

# Bare Agent CLI Compatibility: Making SASE Projects Usable Without a SASE Agent

**Research question:** What would it take for a user who has fully adopted SASE in a
project to still run a supported agent CLI directly (`claude`, `codex`, `qwen`, …) in
that project — supporting as many SASE features as possible, and making the unsupported
ones self-evidently unavailable without growing the always-loaded instruction files?

**Scope:** SASE at `446e9a43c` (version 0.16.0), workspace `sase_31`, 7 registered agent
CLIs. Findings are empirical: every claim below was produced by running the command with
every `SASE_*` variable stripped from the environment, which is exactly what a bare
`claude` in the primary checkout sees. No runtime behavior was changed.

**Terminology.** This report calls the two modes **hosted** (the process was launched by
SASE and carries the host's environment) and **standalone** (the user launched the agent
CLI themselves). "Bare CLI" and "standalone" are used interchangeably.

## Bottom line

Standalone usability is not blocked by architecture. It is blocked by **four unrelated
ad-hoc gates**, only one of which is load-bearing, and by **instruction text that
describes hosted mode as if it were the only mode**.

The recommendation has three parts, in descending value per unit of effort:

1. **Make it work.** Two commands — `sase memory read` and `sase skill use` — hard-fail
   standalone for no architectural reason. Both already have a working fallback path
   living in the same module (`resolve_audit_identity`), already used in production by
   `sase repo open` and `sase artifact read`. Switching them is a one-line change each
   and unblocks the single worst failure in the whole surface.
2. **Teach at the point of failure, not in the instruction file.** For the handful of
   features that genuinely cannot work standalone, the fallback belongs in the CLI's own
   error message. An error costs zero context until the agent hits it, needs no provider
   support, and works identically across all 7 CLIs. `sase pipe` already does this
   correctly and is the model to copy.
3. **Put mode-specific procedure in skill bodies, not `AGENTS.md`.** Skill bodies are
   read on demand; only the ~30-word description is always loaded. A "Standalone" section
   inside `/sase_final` or `/sase_monitor` costs a hosted agent literally nothing.

Explicitly **not** recommended: a hook-based solution. SASE has a documented policy that
it does not install agent-CLI hooks (`docs/llms.md:279`), hooks exist for only some of
the 7 providers, and the whole point of the exercise is to avoid provider-specific
scaffolding.

## 1. What a bare CLI actually sees today

A user who adopts SASE gets three always-loaded directives from the shipped core memory
note (`sase/memory/sase.md`, rendered into `AGENTS.md` and every provider shim). This is
the entire globally-shipped Tier 1 surface — everything else in this repo's `AGENTS.md`
is sase-repo-local memory.

| Directive | Points at | Standalone result |
| --- | --- | --- |
| "read reference memory with your `/sase_memory_read` skill, **never by opening the file directly**" | `sase memory read` | **Hard fail** |
| "agents MUST use your `/sase_repo` skill first" | `sase repo open` | Works |
| "Before any normal response … use your `/sase_final` skill as the last action" | `sase final context` | **Hard fail** |

Two of the three always-loaded SASE directives name a command that refuses to run.

The memory one is the most damaging, because the instruction is a **prohibition paired
with a broken permission**. The agent is told not to read `sase/memory/*.md` directly and
is handed a tool that answers:

```
sase memory read: memory reads require agent attribution; set SASE_AGENT_NAME,
or provide SASE_ARTIFACTS_DIR/agent_meta.json with a name
```

There is no stated fallback. A well-behaved agent has two options — violate the
prohibition, or do the work without the reference memory it was told it needed.

The live audit logs quantify how total this exclusion is:

| Log | `interactive` events | agent events |
| --- | --- | --- |
| `repo_opens.jsonl` | 48 | 5 837 |
| `memory_reads.jsonl` | **0** | 8 728 |

`sase repo open` has recorded 48 real human/standalone opens because it degrades. `sase
memory read` has recorded zero in 8 728 events, because it cannot.

Beyond the always-loaded surface, **13 of the 19 deployed `sase_*` skills** open their
body with `sase skill use <name> --reason "…"` (generated from
`SKILL.frame.template.md` whenever `log_skill_use` is not `false`). Standalone, the very
first command of each of those 13 skills errors out.

## 2. Full standalone command inventory

Every command below was run with all `SASE_*` variables stripped, from the workspace
root. `OK` means it produced its normal output.

### Works standalone today

`sase repo list` · `sase repo path` · `sase repo open` · `sase memory show` ·
`sase memory list` · `sase agent list` · `sase project current` · `sase bead list` ·
`sase bead task-type list` · `sase chat list` · `sase notify list` · `sase proc list` ·
`sase monitor list` · `sase plan list` · `sase plan validate` · `sase artifact list` ·
`sase prompt list` · `sase stitch list` · `sase stitch create` · `sase flag list` ·
`sase config show` · `sase var list` · `sase gate create` · `sase gate wait` ·
`sase run` · `sase tmux-agent` · `just check` / `just check-full`

That is most of the read surface and, importantly, the entire **commit** path and the
entire **gate** path.

### Fails standalone

| Command | Message | Gate mechanism |
| --- | --- | --- |
| `sase memory read` | `memory reads require agent attribution; set SASE_AGENT_NAME, or provide SASE_ARTIFACTS_DIR/agent_meta.json with a name` | `require_agent_identity()` |
| `sase skill use` | `skill use logs require agent attribution; …` | `require_agent_identity()` |
| `sase final context` / `submit` | `sase final context requires SASE_ARTIFACTS_DIR` | `require_artifacts_dir()` + `_run_identity()` |
| `sase questions` | `Error: SASE_AGENT is unset` | `handoff_guard()` |
| `sase plan propose` | `Error: SASE_AGENT is unset` | `handoff_guard()` |
| `sase pipe` | `` `sase pipe` is only available inside a sase agent `` | `handoff_guard()` + custom message |
| `sase var set` | `sase var set must be run from inside a SASE agent (SASE_AGENT=1 is required)` | bare `os.environ` check |
| `sase artifact create` | `sase artifact create must be run from inside a SASE agent (SASE_AGENT=1 is required)` | bare `os.environ` check |
| `sase monitor start` | `no agent given and SASE_AGENT_NAME is unset; pass -a/--agent explicitly` | lane resolution |

Note the message quality spread. `sase pipe` names the condition in the user's
vocabulary. `sase questions` says `SASE_AGENT is unset`, which is true and useless — it
describes an environment variable, not a situation, and offers no alternative. None of
the nine tells the agent what to do instead.

## 3. Root cause: there is no single "am I hosted?" predicate

The nine failures above are produced by **four different mechanisms** that were written
independently:

1. `sase.agent.identity.require_agent_identity()` — raises unless `SASE_AGENT_NAME` or
   `agent_meta.json` resolves. Callers: `memory/cli_read.py:32`,
   `skills/cli_use.py:24`, `memory/proposals/identity.py:37`.
2. `sase.agent.pending_handoff_write.handoff_guard()` — requires `SASE_AGENT` **and**
   `SASE_ARTIFACTS_DIR`. Callers: `pipe_handler.py:230`, `plan_propose_handler.py:51`,
   `questions_command_handler.py:54`.
3. Bare `os.environ.get("SASE_AGENT")` comparisons, spelled inconsistently —
   `!= "1"` in `artifact_cli/create.py:16` and `main/var_handler.py:378`, truthiness in
   `monitor/handoff.py:33`, `launch_request.py:174`, `artifact_cli/read.py:272`.
4. `finalizers/declaration.py:_run_identity()` — requires `SASE_AGENT_TIMESTAMP`,
   a resolvable agent name, **and** `SASE_FINAL_TURN_NONCE`.

Because there is no shared predicate, there is no shared place to attach a fallback,
a message, or a policy. Every new agent-only command re-invents the check and re-invents
(or forgets) the error text. This is the structural finding: **the mode is real and is
checked in ten places, but it is not a named concept anywhere in the codebase.**

For reference, a hosted agent carries **41** `SASE_*` variables. A standalone one
carries zero.

## 4. What SASE already gets right

Four existing behaviors are the correct pattern and should be the template.

**Graceful audit identity.** `sase.agent.identity` already ships two resolvers side by
side. `require_agent_identity()` raises; `resolve_audit_identity()` never does — it falls
back to an `interactive` identity stamped with the local username. Its docstring already
names the precedent:

> Unlike `require_agent_identity`, this never raises: a human shell with no agent
> attribution resolves to an `"interactive"` identity stamped with the local username,
> matching the convention already used by the artifact-read, repo-open, and
> artifact-consumption audit logs.

The `MemoryReadEvent` schema **already has** an `agent_source` field
(`memory/read_log.py:102`), identical to `RepoOpenEvent`. Nothing needs to change but
the resolver call.

**Graceful degradation to a non-agent default.** `sase.bead.attribution.acting_agent_name()`
returns `None` rather than raising, so bead creation "degrades to the store owner instead
of failing". `sase_git_commit`'s invocation-marker writer is `[[ -n "${SASE_ARTIFACTS_DIR:-}" ]] || return 0`.
`monitor/handoff.py:maybe_handoff_monitor_from_agent()` is documented as "a no-op outside
an agent process".

**Hooks that branch on mode.** The deployed Claude Code hooks already guard themselves:

```
"command": "[ -n \"$SASE_AGENT\" ] && printf '{…\"permissionDecision\":\"deny\",
  \"permissionDecisionReason\":\"Plan mode is disabled. Use the /sase_plan skill instead.\"}'; exit 0"
```

Plan mode and `AskUserQuestion` are therefore **only** disabled inside a SASE agent. A
bare `claude` keeps both native tools. But the generated instruction text says
flatly *"Use instead of plan mode (which is disabled)"* and *"`AskUserQuestion` has been
disabled"*. **The runtime is already mode-aware and correct; the instruction text is
mode-blind and wrong.** That gap is the cleanest illustration of the whole problem.

**A first-class standalone launcher.** `sase tmux-agent <provider>` exists precisely to
open a bare agent CLI. Its dry run reports:

```
window: ai
directory: /home/bryan/projects/github/sase-org/sase
env: (none)
command: claude --dangerously-skip-permissions --effort xhigh
```

Two things follow. First, SASE already treats standalone use as a supported workflow, so
this is a gap in a shipped feature, not a new feature request. Second, the launch
directory is the **primary checkout**, not a numbered workspace — which means the core
memory's "Ephemeral `sase_<N>` Workspace Directories" section is false for exactly the
agents launched by SASE's own standalone launcher.

## 5. Feature-by-feature: supportable, substitutable, or unavailable

| Feature | Verdict | Standalone answer |
| --- | --- | --- |
| Reference memory read | **Supportable** | Fall back to `interactive` identity; log it |
| Skill-use logging | **Supportable** | Same |
| Memory proposals | **Supportable** | Same |
| Repo open / audit | Already works | — |
| Beads (read + write) | Already works | Attribution falls back to store owner |
| Gates | Already works, and works *better* | A standalone agent can block on `sase gate wait` inline; a hosted one cannot |
| Commit | Already works | `sase stitch create` (via `/sase_git_commit`) |
| Plans (author + validate) | Already works | `sase plan validate` needs nothing |
| Plan proposal | **Partly supportable** | Gate creation is durable and host-independent; only the SIGTERM handoff is hosted. Could create the `PlanApproval` gate and return |
| Monitors | **Substitutable** | The CLI's own background execution. The single-turn constraint that motivates `/sase_monitor` does not exist standalone |
| Questions | **Substitutable** | The CLI's native ask tool (already permitted by the guarded hook), or `/sase_gate` + `sase gate wait` |
| Agent launch | **Substitutable** | `sase run` directly — which `/sase_run` already documents as the correct user-initiated path |
| Artifact create | **Partly supportable** | Needs a per-agent artifact record; could synthesize an interactive one, or degrade to "keep the file and cite its path" |
| Output variables (`sase var set`) | **Unavailable** | Nothing consumes them; report the value in the reply |
| Turn pipe (`sase pipe`) | **Unavailable** | Agent-family concept with no standalone meaning; use `sase run` |
| Final declaration | **Unavailable** | Host-owned by decision (`decisions:host-owned-completion`). Commit directly with `/sase_git_commit` |

Only three rows are genuinely unavailable, and one of them (`final`) is unavailable
*because of an accepted architectural decision*, not an oversight. That is a small
residue.

Note the `final` → `/sase_git_commit` substitution needs a matching correction to that
skill's own description, which currently reads *"NEVER invoke this skill unless the user
explicitly asks you to commit or the host explicitly instructs you to"*. Standalone,
there is no host and no finalizer, so `/sase_git_commit` is the **primary** commit path,
not an exception. Left as-is, a standalone agent reads the pair as "never commit."

## 6. Recommendations

### 6.1 Name the mode (foundation, small)

Add one predicate — e.g. `sase.agent.identity.in_hosted_run()` — and route all ten
existing checks through it. This is refactoring, not behavior change, but nothing else in
this report is maintainable without it: it is the only place a policy, a message, or a
fallback can be attached once.

Decide the definition deliberately. `SASE_AGENT` truthiness, `SASE_AGENT == "1"`, and
`SASE_ARTIFACTS_DIR` presence are used interchangeably today and are not equivalent —
`monitor/spawn.py:105` and `supervise.py:196` deliberately strip `SASE_ARTIFACTS_DIR`
while leaving other variables, so a monitored child is in a fourth state that none of the
current checks anticipates.

### 6.2 Make the supportable things work (highest value, smallest diff)

- `memory/cli_read.py:32` — `require_agent_identity()` → `resolve_audit_identity()`.
- `skills/cli_use.py:24` — same.
- `memory/proposals/identity.py:37` — same, if unattributed proposals are acceptable.

Each is one line. The event schema already carries `agent_source`, so `interactive` reads
land in `memory_reads.jsonl` and show up in `sase memory log` alongside agent reads —
strictly more audit coverage than today's zero. This single change removes the worst
failure in the entire surface: the prohibition-with-no-permission on reference memory.

Verify with `sase memory log --agent <username>` and by confirming
`memory_reads.jsonl` gains `"agent_source": "interactive"` rows.

A **zero-code interim workaround** exists and is worth documenting today:
`SASE_AGENT_NAME=$USER claude` unblocks both `sase memory read` and `sase skill use`
(verified). It is a stopgap, not a fix — it claims agent identity the session does not
have, and it pollutes the audit log with a fake agent name rather than an honest
`interactive` one.

### 6.3 Teach at the point of failure (zero instruction-file cost)

For every command that stays hosted-only, the error must answer *"what do I do instead?"*
in one line. Concretely:

```
sase questions: only available inside a sase agent.
  Standalone: use your CLI's own question/prompt tool, or create a durable
  gate with `sase gate create` and block on `sase gate wait`.
```

```
sase final context: only available inside a sase agent — there is no host
  finalizer to declare to. Standalone: commit directly with `/sase_git_commit`.
```

```
sase monitor start: no agent to hand off to. Standalone: run the command with
  your CLI's own background execution — SASE's single-turn constraint does not
  apply here.
```

```
sase var set: only available inside a sase agent — nothing downstream reads
  standalone output variables. Report the value in your reply instead.
```

This is the highest-leverage idea in the report, because it satisfies the constraint
exactly: **cost is zero until the agent needs the information, and it is provider-neutral
by construction.** It also self-maintains — the guidance lives next to the gate it
explains, so it cannot drift the way a paragraph in `AGENTS.md` does.

Once §6.1 exists, the shared predicate can carry a small message registry so every gated
command gets a consistent `only available inside a sase agent — standalone: <X>` shape
for free.

### 6.4 Put procedure in skill bodies, not instruction files (near-zero cost)

Each affected `SKILL.md` gets one short `## Standalone` section. Skill bodies are loaded
only on invocation; only the description is always in context. A hosted agent that never
invokes `/sase_monitor` pays nothing.

Priority order: `sase_final` (commit directly), `sase_monitor` (native background),
`sase_questions` (native ask / gate), `sase_plan` (author and validate; propose is
hosted), `sase_run` (`sase run` directly), `sase_git_commit` (standalone, this is the
primary path).

Two skill **descriptions** — which *are* always loaded — assert hosted-only facts and
should be softened to name the condition:

- `sase_monitor`: *"Use this INSTEAD of any built-in monitor, provider-native
  background-execution, or scheduled wake-up tool - those do not work in SASE"* → true
  hosted, false standalone.
- `sase_plan`: *"Use instead of plan mode (which is disabled)"* → the hook only disables
  plan mode when `SASE_AGENT` is set.

Adding a conditional clause ("inside a SASE agent") costs a handful of tokens and removes
a flat contradiction with the runtime.

### 6.5 Correct the two mode-blind core-memory statements (net-neutral, arguably net-negative)

Two sentences in `sase/memory/sase.md` are false standalone and can be fixed **without
adding length**:

- The `/sase_final` paragraph opens *"Before any normal response that ends this SASE
  provider turn"*. Adding "SASE-hosted" — *"…that ends a SASE-hosted provider turn"* — is
  three words and makes the whole 16-line section correctly self-scoping. This is the
  single highest-value text edit available.
- The "Ephemeral `sase_<N>` Workspace Directories" section describes the agent's own
  situation and is simply untrue for a standalone run in the primary checkout. It is also
  sase-repo-local, not part of the globally-shipped note.

Both are edits to a canonical SASE memory note and therefore require the user's explicit
approval plus a `sase memory init` regeneration.

## 7. What not to do

**Do not solve this with hooks.** `docs/llms.md:279` records a deliberate reversal:
*"SASE does **not** install Claude Code hooks and does **not** write to the workspace's
`.claude/settings.local.json`; earlier releases did, through a `sase_claude_tool_hook`
console script that no longer ships."* A `SessionStart` `additionalContext` injection
would technically work for Claude Code and would keep the instruction files untouched,
but it reverses a settled decision, covers 1 of 7 providers, and puts the guidance
somewhere the user cannot see when it goes stale. The existing guarded hooks in the
user's chezmoi-managed `~/.claude/settings.json` are user-owned, and that is the right
boundary.

**Do not render two AGENTS.md variants.** Instruction files are static and committed; a
per-mode render would need a runtime selector at read time, which no provider offers.
This is the reason the guidance must live in errors and skill bodies rather than in
generated text.

**Do not add a "Standalone Mode" section to core memory.** It would be paid for on every
hosted turn by every agent in every adopting project — precisely the cost the user asked
to avoid — to serve the minority mode.

## 8. Open questions

1. **Is an unattributed memory read acceptable?** The audit trail exists for a reason.
   The counter-argument is that `sase repo open` already accepts `interactive` opens and
   nobody has objected, and that the current design produces *less* audit data, not more,
   because a standalone agent reads the raw file instead.
2. **Should `sase plan propose` work standalone?** The `PlanApproval` gate is durable and
   host-independent; only the SIGTERM handoff is hosted. A standalone propose could
   create the gate and return, letting ACE approve it later. This is a genuine feature
   decision, not a bug fix — worth its own plan.
3. **What is the correct predicate?** See §6.1. The monitored-child case
   (`SASE_ARTIFACTS_DIR` stripped, other `SASE_*` intact) needs an explicit answer.
4. **Should any of this be feature-flagged?** The identity fallbacks are small enough to
   land directly. A standalone `plan propose` probably warrants a flag.

## 9. Suggested sequencing

1. **Identity fallback** (§6.2) — 3 one-line changes plus tests. Unblocks reference
   memory and 13 skills' opening command. Ship first; it is independently valuable.
2. **Named predicate** (§6.1) — refactor the 10 checks behind one helper.
3. **Standalone-aware error messages** (§6.3) — attach to the predicate from step 2.
4. **Skill bodies and two skill descriptions** (§6.4).
5. **Core memory wording** (§6.5) — needs the user's explicit approval and
   `sase memory init`.
6. **Standalone `plan propose`** (§8.2) — separate decision, separate plan.

Steps 1–4 are all code and skill-template changes with no always-loaded context cost.
Only step 5 touches an instruction file, and it removes ambiguity without adding length.

## Appendix: reproducing the probe

```bash
# Strip every SASE_* variable, reproducing a bare agent-CLI environment.
cat > /tmp/nosase.sh <<'EOF'
#!/usr/bin/env bash
args=()
while IFS='=' read -r k _; do
  case "$k" in SASE_*) args+=(-u "$k");; esac
done < <(env)
exec env "${args[@]}" "$@"
EOF
chmod +x /tmp/nosase.sh

/tmp/nosase.sh sase memory read glossary:stitch -r probe   # fails
/tmp/nosase.sh sase memory show glossary:stitch            # works
/tmp/nosase.sh sase final context -f json                  # fails
/tmp/nosase.sh sase repo list                              # works

# Audit-log asymmetry
grep -ho '"agent_source": *"[^"]*"' ~/.sase/projects/*/repo_opens.jsonl   | sort | uniq -c
grep -ho '"agent_source": *"[^"]*"' ~/.sase/projects/*/memory_reads.jsonl | sort | uniq -c
```
