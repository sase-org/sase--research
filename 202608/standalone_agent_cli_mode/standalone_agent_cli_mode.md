---
create_time: 2026-08-25
updated_time: 2026-08-25
status: research
---

# Standalone Agent CLI Mode: Making SASE Projects Usable Without a SASE Agent

**Research question:** What would it take for a user who has fully adopted SASE in a
project to still run a supported agent CLI directly (`claude`, `codex`, `qwen`, …) in
that project — supporting as many SASE features as possible, and making the unsupported
ones self-evidently unavailable without growing the always-loaded instruction files?

**Scope:** SASE 0.16.0, 7 registered agent CLIs. This report consolidates two
independent research passes (`standalone_agent_cli_mode__a.md`, by `research.14.cdx`,
and `standalone_agent_cli_mode__b.md`, by `research.14.cld`) with a third verification
pass. Every empirical claim below was re-run in workspace `sase_24` with all `SASE_*`
variables stripped from the environment — exactly what a bare `claude` sees. Conflicts
between the two source reports are resolved in §8.

**Terminology.** This report uses **hosted** (the process was launched by SASE and
carries the host's environment) and **standalone** (the user launched the agent CLI
themselves). Report `__a` calls these "managed" and "direct"; the concepts are identical.

---

## Bottom line

Standalone usability is not blocked by architecture. It is blocked by **four unrelated
ad-hoc gates** — only one of which is load-bearing — and by **instruction and skill text
that describes hosted mode as if it were the only mode**.

The single most striking fact: **SASE already ships a first-class standalone launcher
and an installer for all seven agent CLIs**, and the commands its own launcher's
sessions are told to run then fail. This is a gap in a shipped feature, not a new
feature request.

Three recommendations, in descending value per unit of effort:

1. **Make it work.** `sase memory read` and `sase skill use` hard-fail standalone for no
   architectural reason. Both have a working fallback (`resolve_audit_identity`) living
   in the same module, already used in production by `sase repo open`,
   `sase artifact read`, and the ACE TUI. Two one-line changes remove the worst failure
   in the entire surface.
2. **Teach at the point of failure, not in the instruction file.** For the handful of
   features that genuinely cannot work standalone, the fallback belongs in the CLI's own
   error message. Cost is zero until the agent hits it, it is provider-neutral across all
   7 CLIs, and it cannot drift because it sits next to the gate it explains.
3. **Put mode-specific procedure in skill bodies, not `AGENTS.md`.** Skill bodies load on
   demand; only the ~30-word description is always in context. A `## Standalone` section
   in `/sase_final` costs a hosted agent nothing.

This satisfies the user's constraint almost exactly. The recommended instruction-file
change is **three words in one shipped template** (§6.5) — and it *shortens* ambiguity
rather than adding length.

---

## 1. Standalone use is already a shipped SASE workflow

Neither source report emphasized this, and it reframes the whole problem.

**`sase agent-cli`** manages installation and updates for every supported CLI:

```
CLI              BINARY    INSTALLED      LATEST         METHOD
Antigravity CLI  agy       1.1.20         unknown        self managed
Claude Code      claude    2.1.245        2.1.245        self managed
Codex CLI        codex     0.149.1        0.149.1        npm
Grok Build       grok      1.0.5          1.0.5          self managed
Muse Code        muse      0.2.1-R1215.1  0.2.1-R1215.1  self managed
OpenCode         opencode  1.18.23        1.18.23        npm
Qwen Code        qwen      0.22.0         0.22.1         npm           ↑
7/7 installed  ·  1 update available
```

**`sase tmux-agent`** launches them interactively, with a tmux key binding
(`bind A run "sase tmux-agent"`) that the command's own help text says a bare invocation
must not break. Its dry run is the crux:

```
$ sase tmux-agent claude -n
window: ai
directory: /home/bryan/projects/github/sase-org/sase
env: (none)
command: claude --dangerously-skip-permissions --effort xhigh
```

`env: (none)`, launched in the **primary checkout**. SASE's own standalone launcher
hands the agent zero SASE environment variables and drops it in the repo whose
`AGENTS.md` tells it to run commands that will fail. A hosted agent carries ~43 `SASE_*`
variables; this one carries none.

---

## 2. What a bare CLI actually sees

An adopting project's Tier 1 surface comes from one shipped template,
`src/sase/main/init_memory/templates/memory-sase.template.md`, rendered into
`sase/memory/sase.md` → `AGENTS.md` → every provider shim. **This is the entire
globally-shipped always-loaded SASE surface**; everything else in the sase repo's own
`AGENTS.md` is sase-repo-local memory that adopters never receive.

Verified against two other adopting projects (`actstat`, 139 lines; `bob-cli`, 162
lines), the shipped template renders four sections:

| Shipped section | Points at | Standalone result |
| --- | --- | --- |
| SASE Memory — "read reference memory with `/sase_memory_read`, **never by opening the file directly**" | `sase memory read` | **Hard fail** |
| Ephemeral `<project>_<N>` Workspace Directories *(conditional on `project_name`)* | — | **Factually false** in the primary checkout |
| Repositories — "agents MUST use your `/sase_repo` skill first" | `sase repo open` | Works |
| SASE Final Declaration — "Before any normal response … use your `/sase_final` skill as the last action" | `sase final context` | **Hard fail** |

**Two of the three skill-pointing directives name a command that refuses to run**, and
the fourth section is untrue for exactly the sessions SASE's own launcher creates.

### The worst failure: a prohibition paired with a broken permission

The memory directive is the most damaging, because the agent is told *not* to read
`sase/memory/*.md` directly and is handed a tool that answers:

```
sase memory read: memory reads require agent attribution; set SASE_AGENT_NAME,
or provide SASE_ARTIFACTS_DIR/agent_meta.json with a name
```

No stated fallback. A well-behaved agent has two options: violate the prohibition, or do
the work without the reference memory it was told it needed.

The live audit logs quantify how total this exclusion is:

| Log | `interactive` events | agent events |
| --- | --- | --- |
| `repo_opens.jsonl` | **48** | 5 897 |
| `memory_reads.jsonl` | **0** | 8 734 |

`sase repo open` has recorded 48 real human/standalone opens because it degrades.
`sase memory read` has recorded zero in 8 734 events, because it cannot.

### The skill audit prelude

Beyond the always-loaded surface, **13 of the 19 deployed `sase_*` skills** open their
body with `sase skill use <name> --reason "…"`, generated by `SKILL.frame.template.md`
whenever `log_skill_use` is not `false`. Standalone, the very first command of each of
those 13 skills errors out.

Usefully, **the opt-out knob already exists and is already in use**: 6 skills set
`log_skill_use: false` (`sase_memory_read`, `sase_monitor`, `sase_plan`, `sase_pipe`,
`sase_final`, `sase_repo`). One consequence matters for sequencing — because
`sase_memory_read` already opts out, reference memory is **single-gated**, so the
one-line identity fix in §6.2 fully unblocks it with no skill-template work.

### The runtime is already mode-aware; the text is not

The deployed Claude Code hooks in the user's chezmoi-managed `~/.claude/settings.json`
guard themselves on mode:

```
[PreToolUse] matcher='EnterPlanMode'
  [ -n "$SASE_AGENT" ] && printf '{…"permissionDecision":"deny",
    "permissionDecisionReason":"Plan mode is disabled. Use the /sase_plan skill instead."}'; exit 0
[PreToolUse] matcher='AskUserQuestion'
  [ -n "$SASE_AGENT" ] && printf '{…"AskUserQuestion is disabled. Use the /sase_questions skill instead."}'; exit 0
```

Plan mode and `AskUserQuestion` are therefore **only** disabled inside a SASE agent. A
bare `claude` keeps both native tools. But the always-loaded skill descriptions say
flatly *"Use instead of plan mode (which is disabled)"* and *"`AskUserQuestion` … is
disabled"*.

**The runtime is already mode-aware and correct; the instruction text is mode-blind and
wrong.** That gap is the cleanest illustration of the whole problem, and it is the
strongest argument that this is a text problem before it is a code problem.

---

## 3. Full standalone command inventory

All probes run with every `SASE_*` variable stripped, from the workspace root.

### Works standalone today

`sase repo list` · `sase repo path` · `sase repo open` · `sase memory show` ·
`sase memory list` · `sase agent list` · `sase agent-cli list` · `sase project current` ·
`sase bead list` · `sase bead task-type list` · `sase chat list` · `sase notify list` ·
`sase proc list` · `sase monitor list` · `sase plan list` · `sase plan validate` ·
`sase artifact list` · `sase prompt list` · `sase stitch list` · **`sase stitch create`** ·
`sase flag list` · `sase config show` · `sase var list` · `sase gate create` ·
`sase gate wait` · `sase doctor` · `sase run` · `sase tmux-agent` ·
`just check` / `just check-full`

That is most of the read surface and, importantly, the entire **commit** path and the
entire **gate** path.

### Fails standalone

| Command | Message | Gate mechanism |
| --- | --- | --- |
| `sase memory read` | `memory reads require agent attribution; set SASE_AGENT_NAME, …` | `require_agent_identity()` |
| `sase skill use` | `skill use logs require agent attribution; …` | `require_agent_identity()` |
| `sase final context` / `submit` | `sase final context requires SASE_ARTIFACTS_DIR` | `require_artifacts_dir()` + `_run_identity()` |
| `sase questions` | `Error: SASE_AGENT is unset` | `handoff_guard()` |
| `sase plan propose` | `Error: SASE_AGENT is unset` | `handoff_guard()` |
| `sase pipe` | `` `sase pipe` is only available inside a sase agent `` | `handoff_guard()` + custom message |
| `sase var set` | `must be run from inside a SASE agent (SASE_AGENT=1 is required)` | bare `os.environ` check |
| `sase artifact create` | `must be run from inside a SASE agent (SASE_AGENT=1 is required)` | bare `os.environ` check |
| `sase monitor start` | `no agent given and SASE_AGENT_NAME is unset; pass -a/--agent explicitly` | lane resolution |

Note the message-quality spread. `sase pipe` names the condition in the user's
vocabulary; `sase questions` says `SASE_AGENT is unset`, which is true and useless — it
describes an environment variable, not a situation. **None of the nine tells the agent
what to do instead.**

---

## 4. Root cause: there is no single "am I hosted?" predicate

The nine failures are produced by **four independently written mechanisms**:

1. `sase.agent.identity.require_agent_identity()` — raises unless `SASE_AGENT_NAME` or
   `agent_meta.json` resolves. Callers: `memory/cli_read.py:32`, `skills/cli_use.py:24`,
   `memory/proposals/identity.py:37`.
2. `sase.agent.pending_handoff_write.handoff_guard()` — requires `SASE_AGENT` **and**
   `SASE_ARTIFACTS_DIR`. Callers: `pipe_handler.py:230`, `plan_propose_handler.py:51`,
   `questions_command_handler.py:54`.
3. Bare `os.environ.get("SASE_AGENT")` comparisons, **spelled inconsistently** —
   `!= "1"` in `artifact_cli/create.py:16` and `main/var_handler.py:378`; truthiness in
   `monitor/handoff.py:33`, `launch_request.py:174`, `artifact_cli/read.py:272`.
4. `finalizers/declaration.py:_run_identity()` — requires `SASE_AGENT_TIMESTAMP`, a
   resolvable agent name, **and** `SASE_FINAL_TURN_NONCE`.

Because there is no shared predicate, there is no shared place to attach a fallback, a
message, or a policy. Every new agent-only command re-invents the check and re-invents
(or forgets) the error text. **The mode is real and is checked in ten places, but it is
not a named concept anywhere in the codebase.**

---

## 5. What SASE already gets right (the patterns to copy)

**Graceful audit identity.** `sase.agent.identity` ships two resolvers side by side.
`require_agent_identity()` raises; `resolve_audit_identity()` never does — it falls back
to an `interactive` identity stamped with the local username. Its docstring already names
the precedent:

> Unlike `require_agent_identity`, this never raises: a human shell with no agent
> attribution resolves to an `"interactive"` identity stamped with the local username,
> matching the convention already used by the artifact-read, repo-open, and
> artifact-consumption audit logs.

The `MemoryReadEvent` schema **already carries** `agent_source` (`memory/read_log.py:102`),
and `read_log.py:20` **already imports** `resolve_audit_identity`. `cli_read.py` simply
calls the raising resolver instead. The ACE TUI memory panel
(`ace/tui/modals/memory_panel_load.py:171`) already reads memory through
`resolve_audit_identity()`, so the graceful path is proven in production on this exact
data type.

**Graceful degradation to a non-agent default.** `bead.attribution.acting_agent_name()`
returns `None` rather than raising, so bead creation "degrades to the store owner instead
of failing". `sase_git_commit`'s invocation-marker writer is
`[[ -n "${SASE_ARTIFACTS_DIR:-}" ]] || return 0` (line 41), then always delegates to
`sase stitch create`, defaulting to the ordinary `create_commit` method when neither a
command-line type nor `SASE_COMMIT_METHOD` is set. `monitor/handoff.py` is documented as
"a no-op outside an agent process".

**Byte-identical provider distribution.** `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
`QWEN.md`, and `OPENCODE.md` share one SHA-256 in the primary checkout. Standalone and
hosted sessions see the same durable project policy across all providers — a sound
portability layer that should not be forked per mode (§7).

**An existing diagnostics framework.** `sase doctor` already registers ~60 checks across
grouped ids (`runtime.*`, `config.*`, `workspace.*`, …), including a deep
`config.skills.applied` check. Adding per-provider standalone-readiness checks is
incremental work in an existing framework, not new scaffolding.

---

## 6. Recommendations

### 6.1 Name the mode (foundation, small)

Add one predicate — e.g. `sase.agent.identity.in_hosted_run()` — and route all ten
existing checks through it. This is refactoring, not behavior change, but nothing else
here is maintainable without it: it is the only place a policy, a message, or a fallback
can be attached once.

Decide the definition deliberately. `SASE_AGENT` truthiness, `SASE_AGENT == "1"`, and
`SASE_ARTIFACTS_DIR` presence are used interchangeably today and are **not** equivalent —
`monitor/spawn.py:105` and `supervise.py:196` deliberately strip `SASE_ARTIFACTS_DIR`
while leaving other variables, so a monitored child sits in a fourth state none of the
current checks anticipates. The predicate should validate the hosted context **as a
unit** and fail closed on a partial or stale environment, rather than treating a
leftover `SASE_AGENT=1` as sufficient authority.

Report `__a` proposes going further: a full `ExecutionContext` object
(`mode`/`project`/`agent`/`provider`/`session_id`/`artifacts_dir`/`capabilities`) exposed
as `sase runtime context --format json`, with capability-named requirements
(`require_managed_handoff()`, `require_finalizer_turn()`, `audit_actor()`). That is the
right *end state* and the right shape for the error envelope in §6.3, but it should be
grown from the one-predicate refactor rather than landed as a prerequisite — otherwise
the highest-value fix (§6.2) waits on an architecture change it does not need.

### 6.2 Make the supportable things work (highest value, smallest diff)

- `memory/cli_read.py:32` — `require_agent_identity()` → `resolve_audit_identity()`
- `skills/cli_use.py:24` — same
- `memory/proposals/identity.py:37` — same, if unattributed proposals are acceptable

Each is one line. The event schema already carries `agent_source`, so `interactive` reads
land in `memory_reads.jsonl` and appear in `sase memory log` alongside agent reads —
**strictly more audit coverage than today's zero**, because a standalone agent currently
reads the raw file (unlogged) or goes without.

Verify with `sase memory log --agent <username>` and by confirming `memory_reads.jsonl`
gains `"agent_source": "interactive"` rows.

A **zero-code interim workaround** exists and is worth documenting today:
`SASE_AGENT_NAME=$USER claude` unblocks both commands (verified). It is a stopgap, not a
fix — it claims agent identity the session does not have and writes a fake agent name
into the audit log instead of an honest `interactive` one.

### 6.3 Teach at the point of failure (zero instruction-file cost)

For every command that stays hosted-only, the error must answer *"what do I do instead?"*
in one line:

```
sase questions: only available inside a sase agent.
  Standalone: use your CLI's own question/prompt tool, or create a durable
  gate with `sase gate create` and block on `sase gate wait`.

sase final context: only available inside a sase agent — there is no host
  finalizer to declare to. Standalone: commit directly with `/sase_git_commit`.

sase monitor start: no agent to hand off to. Standalone: run the command with
  your CLI's own background execution — SASE's single-turn constraint does not
  apply here.

sase var set: only available inside a sase agent — nothing downstream reads
  standalone output variables. Report the value in your reply instead.
```

**This is the highest-leverage idea in the research**, because it satisfies the user's
constraint exactly: cost is zero until the agent needs the information, it is
provider-neutral by construction, and it self-maintains — the guidance lives next to the
gate it explains, so it cannot drift the way a paragraph in `AGENTS.md` does.

Once §6.1 exists, the shared predicate can carry a small message registry so every gated
command gets a consistent `only available inside a sase agent — standalone: <X>` shape
for free. Emit a stable machine-readable code (`hosted_agent_required`) alongside the
prose so consumers never parse `"SASE_AGENT is unset"`.

One refinement to §6.3 as `__a` frames it: `sase final context` standalone should be a
**successful, read-only no-op**, not an error, because the always-loaded instruction
tells every agent to run it on every turn. Returning exit 0 with an explicit envelope
turns the mandatory call into the delivery mechanism for the truth:

```json
{
  "schema_version": 1,
  "execution_mode": "standalone",
  "submission_required": false,
  "message": "No SASE host owns completion for this session. Do not auto-commit. If the user explicitly requested a commit, use /sase_git_commit; otherwise report the remaining working-tree state."
}
```

It must not create a nonce, artifacts directory, or any other finalizer state. This is
the single change that makes the shipped `/sase_final` directive correct standalone
**without editing the instruction file at all**.

### 6.4 Put procedure in skill bodies, not instruction files (near-zero cost)

Each affected `SKILL.md` gets one short `## Standalone` section. Bodies load only on
invocation; only the description is always in context. A hosted agent that never invokes
`/sase_monitor` pays nothing.

Priority: `sase_final` (commit directly), `sase_monitor` (native background),
`sase_questions` (native ask / gate), `sase_plan` (author and validate; propose is
hosted), `sase_run` (`sase run` directly), `sase_git_commit` (standalone, this is the
primary path).

Two skill **descriptions** — which *are* always loaded — assert hosted-only facts and
contradict the guarded runtime hooks (§2). Both should name the condition:

- `sase_monitor`: *"Use this INSTEAD of any built-in monitor, provider-native
  background-execution, or scheduled wake-up tool - those do not work in SASE"* → true
  hosted, false standalone.
- `sase_plan`: *"Use instead of plan mode (which is disabled)"* → the hook only disables
  plan mode when `SASE_AGENT` is set.

Adding "inside a SASE agent" costs a handful of tokens and removes a flat contradiction
with the runtime.

### 6.5 Correct one shipped sentence (net-neutral)

The `/sase_final` paragraph in `memory-sase.template.md` opens *"Before any normal
response that ends this SASE provider turn"*. Changing **"this SASE provider turn"** →
**"a SASE-hosted provider turn"** is three words and makes the whole 16-line section
correctly self-scoping. This is the single highest-value text edit available, and it adds
no length.

The Ephemeral Workspace section is the other mode-blind shipped text (§2). Unlike the
finalizer paragraph it cannot be fixed by narrowing one clause, because the whole section
is premised on the agent running from a numbered workspace. Options, cheapest first:
scope its opening sentence ("SASE-launched agents run from ephemeral workspace
directories…"), or render it only when a workspace is actually in use. Note this is a
**template** change, so it reaches adopters only when each project re-runs
`sase memory init` — use `sase memory init --check` to find drifted projects.

Both are edits to shipped SASE memory templates and require the user's explicit approval
plus regeneration.

**If absolutely zero instruction bytes may change:** §6.2 + §6.3 + §6.4 still remove
every hard failure and every stale skill description. What survives is the false
workspace claim and a slightly ambiguous finalizer directive. That is a materially worse
result than three words, but it is not a broken one.

---

## 7. What not to do

**Do not solve this with hooks.** `docs/llms.md:280` records a deliberate reversal: SASE
does **not** install Claude Code hooks and does **not** write to the workspace's
`.claude/settings.local.json`; earlier releases did, through a `sase_claude_tool_hook`
console script that no longer ships. A `SessionStart` `additionalContext` injection would
technically work for Claude Code and keep instruction files untouched, but it reverses a
settled decision, covers 1 of 7 providers, and hides guidance where the user cannot see
it go stale. The existing guarded hooks in the user's chezmoi-managed
`~/.claude/settings.json` are **user-owned**, and that is the right boundary.

This does not rule out `__a`'s optional session bridge (§9) — a user-installed,
opt-in MCP server is a different thing from SASE writing provider hook config. The
distinction to preserve is *who owns the file*.

**Do not render two `AGENTS.md` variants.** Instruction files are static and committed;
a per-mode render needs a runtime selector at read time, which no provider offers. The
five byte-identical provider shims are an asset — forking them per mode would let
behavior drift silently.

**Do not add a "Standalone Mode" section to core memory.** It would be paid for on every
hosted turn by every agent in every adopting project — precisely the cost the user asked
to avoid — to serve the minority mode.

---

## 8. Conflicts between the source reports, resolved

| Claim | `__a` (cdx) | `__b` (cld) | Verified resolution |
| --- | --- | --- | --- |
| Provenance of "Ephemeral `<N>` workspaces" text | Treated as universal instruction text | "sase-repo-local, not part of the globally-shipped note" | **`__a` is right.** The section is in `memory-sase.template.md` under `{% if project_name %}` and renders in `actstat` and `bob-cli` as `actstat_<N>` / `bob-cli_<N>`. It **is** globally shipped, parameterized by project name. Fixing it is a global fix. |
| "Agents never create commits" / "use `/sase_monitor` for long commands" as instruction problems | Listed among the overbroad instruction claims | Not claimed | **`__b` is right by omission.** Both are sase-repo-local (`decisions`, `build_and_run`). Adopter `AGENTS.md` files contain **0** occurrences of host-owned-completion text and **0** references to `sase_monitor`. `__a`'s minimal-edit table overstates the shipped surface by half. |
| `sase monitor start` standalone | "can start a detached process outside an agent" | Hard-fails on lane resolution | **Both partly right.** Bare invocation fails (`no agent given and SASE_AGENT_NAME is unset`), but the message itself names the escape: `-a/--agent`. It is a lane-resolution default, not a hosted-only gate — the weakest of the nine failures and the easiest to make self-describing. |
| `/sase_git_commit` standalone readability | Skill "says an explicit user commit request is the condition under which it may commit" | "Left as-is, a standalone agent reads the pair as 'never commit'" | **`__a` is right.** The description's `unless the user explicitly asks you to commit` branch is unconditional and survives standalone. Worth clarifying that standalone makes it the *primary* path, but it is not currently a blocker. |
| `sase pipe` as the model to copy | Not claimed | "already does this correctly and is the model to copy" | **Overstated.** `pipe_handler.py:45` names the *condition* well (`only available inside a sase agent`) but offers no *fallback* — consistent with `__b`'s own later note that none of the nine says what to do instead. Copy pipe's phrasing, then add the missing second clause. |
| Fixing the audit gate | Extend event schema with a tagged `external_cli` actor (`kind`/`provider`/`session_id`/`source`) | Swap the resolver call; schema already supports it | **`__b` for the fix, `__a` for the follow-on.** `agent_source` already exists and `resolve_audit_identity` is already imported in `read_log.py` — ship the one-liners now. `__a`'s richer actor record is a worthwhile later refinement, and its warning matters: **task-bead reporter dedup must not collapse every standalone session into one permanent pseudo-agent.** |
| Session bridge / MCP | Recommends as optional Phase 4 | Recommends against hooks | **Not actually in conflict.** `__b` rejects *SASE-installed provider hooks*; `__a` proposes an *optional user-installed bridge*. Both hold: baseline standalone safety must never depend on it. |

Minor numeric notes: `__b`'s "41 `SASE_*` variables" measured 43 here (drifts by run
context); its "8 728 memory reads / 48 repo opens" measured 8 734 / 48. Its counts of
19 deployed skills and 13 with the audit prelude are exact. `__a`'s claim of five
byte-identical provider instruction files is exact.

---

## 9. Feature-by-feature verdict

| Feature | Verdict | Standalone answer |
| --- | --- | --- |
| Core memory / project rules | Works | — |
| Skill discovery (all 7 CLIs) | Works after `sase skill init` | Add a `doctor` reachability check |
| Reference memory read | **Supportable** | Fall back to `interactive` identity; log it |
| Skill-use logging | **Supportable** | Same |
| Memory proposals | **Supportable** | Same |
| Repo open / audit | Already works | — |
| Beads (read + write) | Already works | Attribution falls back to store owner |
| Gates | Already works, and works *better* | A standalone agent can block on `sase gate wait` inline; a hosted one cannot |
| Commit | Already works | `sase stitch create` via `/sase_git_commit` |
| Plans (author + validate) | Already works | `sase plan validate` needs nothing |
| Plan proposal | **Partly supportable** | The `PlanApproval` gate is durable and host-independent; only the SIGTERM handoff is hosted. Could create the gate and return |
| Monitors | **Substitutable** | The CLI's own background execution; the single-turn constraint does not exist standalone |
| Questions | **Substitutable** | The CLI's native ask tool (already permitted by the guarded hook), or `/sase_gate` + `sase gate wait` |
| Agent launch | **Substitutable** | `sase run` directly — which `/sase_run` already documents as the correct user-initiated path |
| Artifact create | **Partly supportable** | Needs a per-agent artifact record; synthesize an interactive one, or degrade to "keep the file and cite its path" |
| Output variables (`sase var set`) | **Unavailable** | Nothing consumes them; report the value in the reply |
| Turn pipe (`sase pipe`) | **Unavailable** | Agent-family concept with no standalone meaning; use `sase run` |
| Final declaration | **Unavailable** | Host-owned by decision (`decisions:host-owned-completion`); commit directly with `/sase_git_commit` |
| Xprompt expansion (`#…`, `%…`) | **Unavailable** | Only SASE launch preprocessing sees them; ask SASE to expand and launch |

Only four rows are genuinely unavailable, and `final` is unavailable *because of an
accepted architectural decision*, not an oversight. That is a small residue.

### Structural limits (not missing prompt text)

1. **Host-owned work after the answer.** No runner necessarily exists to validate a
   declaration and execute finalizers once a standalone CLI returns.
2. **Mechanical continuation of the same conversation.** SASE handoffs kill one provider
   process and construct the next prompt. A shell command cannot portably inject a
   follow-up turn into an arbitrary CLI.
3. **Family piping.** A standalone session is not in a SASE agent family and owns no
   workspace claim to transfer.
4. **Exact per-turn authorship.** Without a session-start snapshot, inspecting the
   working tree at the end cannot distinguish the user's earlier edits from the agent's.
5. **Automatic xprompt preprocessing.** Providers receive the raw prompt before any
   `sase` command runs.

These should be reported by the command that encounters them (§6.3), not pre-loaded into
every session.

### Commit safety: the one place to be conservative

Limit (4) has a practical consequence `__b` did not cover. Standalone sessions run in a
**long-lived checkout that may already be dirty** with the user's unrelated work, whereas
the hosted stage-everything default is safe in an isolated workspace. Therefore:

- `/sase_final` must never auto-commit standalone (guaranteed by the §6.3 no-op).
- `/sase_git_commit` remains explicit-user-request-only.
- The agent should inspect every dirty path before committing.
- SASE should consider an include-only / baseline-aware commit scope for standalone mode.
- If no commit was requested, report the remaining dirty state and stop.

---

## 10. Suggested sequencing

1. **Identity fallback** (§6.2) — 2–3 one-line changes plus tests. Unblocks reference
   memory and 13 skills' opening command. Ship first; independently valuable and
   unblocked by everything else.
2. **`sase final context` standalone no-op** (§6.3) — makes the mandatory shipped
   directive correct with zero instruction-file change. Highest value per byte.
3. **Named predicate** (§6.1) — route the ten checks through one helper; decide the
   monitored-child case explicitly.
4. **Standalone-aware error messages** (§6.3) — attach to the predicate from step 3, with
   a stable `hosted_agent_required` code.
5. **Skill bodies and the two skill descriptions** (§6.4).
6. **`sase doctor` standalone-readiness checks** — per provider: instruction discovery,
   skill directory health, missing `sase_*` skills. The check registry already exists.
7. **Shipped template wording** (§6.5) — needs explicit user approval plus
   `sase memory init`; use `--check` to find drifted adopters.
8. **Standalone `plan propose`** — separate decision, separate plan.
9. **Optional session bridge** (`__a` §F) — prototype against one provider; never a
   prerequisite for steps 1–7.

Steps 1–6 are code and skill-template changes with **no always-loaded context cost**.
Only step 7 touches an instruction file, and it removes ambiguity without adding length.

---

## 11. Open questions

1. **Is an unattributed memory read acceptable?** The audit trail exists for a reason.
   The counter-argument is that `sase repo open` already accepts 48 `interactive` opens
   and nobody has objected, and that the current design produces *less* audit data, not
   more, because a standalone agent reads the raw file instead. (Note `artifact_reads.jsonl`
   uses the graceful resolver but has recorded 0 interactive events — the fallback is
   correct but lightly exercised in practice.)
2. **What exactly is the predicate?** See §6.1. The monitored-child case
   (`SASE_ARTIFACTS_DIR` stripped, other `SASE_*` intact) needs an explicit answer.
3. **Should `sase plan propose` work standalone?** The gate is durable and
   host-independent; only the handoff is hosted. A genuine feature decision, not a bug fix.
4. **Should standalone commits use an include-only scope?** See §9.
5. **Should any of this be feature-flagged?** The identity fallbacks are small enough to
   land directly. Standalone `plan propose` probably warrants a flag.
6. **Provider drift risk:** OpenCode documents hyphen-only skill names while SASE deploys
   underscore names (`sase_final`). The installed build loads them today; worth pinning
   with a provider smoke test rather than assuming it holds.

---

## 12. Acceptance scenarios

Run against each real provider CLI, launched by its ordinary executable (or
`sase tmux-agent`) from a fully initialized SASE project:

1. **Research only** — a question requiring reference memory. The read is audited as
   `interactive`; no identity error appears.
2. **Read-only SASE features** — project, agent, Patch, chat, notification status. Skill
   prelude and underlying commands both work.
3. **Clarification** — an ambiguous question uses the CLI's native ask tool, not a
   handoff.
4. **Planning** — native plan mode works; `sase plan validate` works; no process-group
   kill and no false promise of continuation.
5. **Edit without commit request** — `/sase_final` returns the standalone no-op, no commit
   is created, dirty state is reported.
6. **Explicit quick commit** — from clean, edit + commit produces a conventional commit
   via `/sase_git_commit`; `/sase_final` stays a no-op afterward.
7. **Pre-existing user work** — an unrelated dirty path is *not* swept into the commit.
8. **Long test** — native background execution works; `sase monitor` does not kill the
   standalone CLI.
9. **Hosted regression** — the same tasks through SASE: declarations, handoffs, workspace
   ownership, and finalizers behave exactly as before.
10. **Missing global init** — remove one provider's SASE skills; `sase doctor` names the
    missing target and the repair command.

---

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
/tmp/nosase.sh sase monitor start -s A -S B -- echo hi     # fails: pass -a/--agent

# SASE's own standalone launcher: no SASE env, primary checkout
sase tmux-agent claude -n

# Audit-log asymmetry
grep -ho '"agent_source": *"[^"]*"' ~/.sase/projects/*/repo_opens.jsonl   | sort | uniq -c
grep -ho '"agent_source": *"[^"]*"' ~/.sase/projects/*/memory_reads.jsonl | sort | uniq -c

# Shipped vs sase-repo-local instruction surface
cat src/sase/main/init_memory/templates/memory-sase.template.md
grep -c "never creates commits\|sase_monitor" ~/projects/github/bbugyi200/actstat/AGENTS.md  # 0
```

---

## Source reports

- `standalone_agent_cli_mode__a.md` — `research.14.cdx` (codex/gpt-5.6-sol). Strongest on
  the seven-provider discovery matrix, the `ExecutionContext` end-state design, standalone
  commit safety in a long-lived checkout, and the optional session bridge.
- `standalone_agent_cli_mode__b.md` — `research.14.cld` (claude/opus). Strongest on
  empirical probing, the four-gate root cause, the audit-log asymmetry, the guarded-hooks
  contradiction, and the point-of-failure teaching strategy.
