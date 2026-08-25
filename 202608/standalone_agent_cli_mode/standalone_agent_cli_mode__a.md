# Making SASE Projects Safe and Useful in Direct Agent CLI Sessions

**Research date:** 2026-08-25  
**Scope:** Claude Code, Codex CLI, Qwen Code, OpenCode, Antigravity CLI, Grok
Build, and Muse Code as currently registered by SASE

## Executive summary

A fully initialized SASE project already gets the first half of direct-agent-CLI
compatibility right:

- `sase memory init` emits one `AGENTS.md` and byte-for-byte provider copies
  (`CLAUDE.md`, `GEMINI.md`, `QWEN.md`, and `OPENCODE.md`).
- `sase skill init` installs provider-rendered SASE skills into every supported CLI's
  global skill directory.
- All seven real provider CLIs currently registered by SASE can discover the relevant
  project instructions and global skills when launched directly.

The failure is at the execution-context boundary. The generated content often speaks
as though every reader is a SASE-managed, single-turn agent with an artifacts directory,
runner, workspace claim, and host finalizer. A direct CLI session has none of those.
Several ordinary SASE operations then fail before doing useful work:

- `sase memory read` requires an attributable SASE agent identity.
- The generated prelude on most SASE skills runs `sase skill use`, which has the same
  identity requirement.
- `sase final context` requires an artifacts directory and active finalizer-turn
  metadata.
- plan, questions, and pipe submission require `SASE_AGENT=1` and intentionally kill
  the managed agent runner after writing a handoff marker.

The recommended target is not to make a direct CLI pretend to be a SASE agent. It is to
make SASE commands distinguish two real execution modes:

1. **Managed agent mode:** the existing single-turn runner, handoffs, workspace claim,
   and host-owned finalizers remain authoritative.
2. **Direct CLI mode:** durable project features work, agent-runner-only commands
   return a successful no-op or a precise provider-native fallback, and SASE never
   silently auto-commits a user's long-lived checkout.

This can be achieved with almost no instruction-file growth. Most guidance should come
from context-sensitive CLI output and on-demand skill bodies. The root instructions
need only have a few existing overbroad phrases narrowed from “agents” to
“SASE-managed agents”; there should be no new “Direct CLI mode” section copied into
every prompt.

The most valuable first increment is:

1. Add one shared runtime-context resolver.
2. Let audited memory reads and skill-use logs record an external/direct actor.
3. Make `sase final context` a clear, read-only no-op outside a managed turn.
4. Give every managed-only command the same typed `managed_agent_required` diagnostic
   and a direct-session fallback.
5. Preserve explicit manual commits through the existing `sase_git_commit` /
   `sase stitch create` path.

That would make direct research, diagnosis, edits, verification, SASE memory access,
bead work, repository inspection, and explicitly requested quick commits practical.
Exact parity for post-response finalization, turn-killing handoffs, monitor follow-up,
and family piping requires an optional provider/session bridge or a SASE runner; those
features cannot be made reliable through prompt text alone.

## What “direct” means

This report uses three distinct contexts:

| Context | How it starts | SASE host owns the provider turn? | Expected completion |
| --- | --- | ---: | --- |
| Managed SASE agent | `sase run`, ACE, a gate, or another SASE launch surface | Yes | Declaration, host finalizers, or mechanical handoff |
| Direct agent CLI | User runs `claude`, `codex`, `qwen`, `opencode`, `agy`, `grok`, or `muse` in a SASE project | No | The provider's normal interactive/session behavior |
| Human CLI | User runs `sase ...` in a shell | No | Ordinary command result |

Direct agent CLI and human CLI are often indistinguishable to a short-lived `sase`
subprocess. That is acceptable for most baseline behavior: both are external to the
managed runner. Provider/session attribution can be best-effort initially and made
precise later through an optional bridge.

The authoritative managed-mode test should not be a loose check for one environment
variable. It should validate the existing managed context as a unit: `SASE_AGENT`, the
artifacts directory, readable agent metadata, and, for finalization, the run ID and turn
nonce. An incomplete or stale environment should fail closed as an invalid managed
context rather than accidentally operating on another run.

## Evidence: project instructions and skills already reach direct CLIs

The local SASE implementation writes provider instruction files as byte-for-byte copies
of `AGENTS.md` (`src/sase/amd/_shared.py` and `src/sase/amd/constants.py`). In this
checkout, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `QWEN.md`, and `OPENCODE.md` have the
same SHA-256. This is a sound portability strategy: direct and managed launches see the
same durable project policy.

The provider-specific discovery routes are also largely correct:

| SASE provider | Direct instruction source | Generated global skill target | Evidence |
| --- | --- | --- | --- |
| Claude Code | `CLAUDE.md` | `~/.claude/skills/` | Claude loads project `CLAUDE.md` and personal skills. [Claude memory](https://code.claude.com/docs/en/memory), [Claude skills](https://code.claude.com/docs/en/slash-commands) |
| Codex CLI | `AGENTS.md` | `~/.codex/skills/` | Codex walks `AGENTS.md` from project root to cwd and uses progressively disclosed skills. [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Codex skills](https://learn.chatgpt.com/docs/build-skills) |
| Qwen Code | `QWEN.md` | `~/.qwen/skills/` | Qwen advertises personal `SKILL.md` files and supports explicit slash invocation. [Qwen skills](https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/) |
| OpenCode | `AGENTS.md` (its `OPENCODE.md` copy is unnecessary for current discovery) | `~/.config/opencode/skills/` | OpenCode uses project `AGENTS.md` and global skills. The installed `opencode debug skill` also lists SASE's underscore-named skills today. [OpenCode rules](https://opencode.ai/docs/rules), [OpenCode skills](https://opencode.ai/docs/skills) |
| Antigravity CLI | `GEMINI.md` and `AGENTS.md` | `~/.gemini/antigravity-cli/skills/` | Google's migration guide explicitly documents both context files and the new global skill path. [Antigravity migration](https://www.antigravity.google/docs/cli/gcli-migration/), [Antigravity plugins and skills](https://www.antigravity.google/docs/cli/plugins/) |
| Grok Build | `AGENTS.md` (also Claude-compatible files) | `~/.grok/skills/` | Grok walks the `AGENTS.md` family and loads user skills. [Grok skills and compatibility](https://docs.x.ai/build/features/skills-plugins-marketplaces) |
| Muse Code | `AGENTS.md` | `~/.config/muse/skills/` | The installed `muse init --dry-run` says Muse reads `AGENTS.md`; `muse skills --help` exposes list, inspect, validate, install, and imports. The SASE provider intentionally uses the Muse-native skill path. |

Versions inspected locally were Claude Code 2.1.245, Codex CLI 0.149.1, Qwen Code
0.22.0, OpenCode 1.18.23, Antigravity CLI 1.1.20, Grok Build 1.0.5, and Muse Code
0.2.1-R1215.1.

There are two caveats:

1. “Project adopted SASE” is not sufficient by itself if the user's global skills were
   never initialized. The project files can instruct an agent to use `/sase_final`
   while that provider has no corresponding skill. `sase doctor` should treat
   instruction-to-skill reachability as a direct-CLI readiness check.
2. Current OpenCode documentation specifies hyphen-only skill names, while SASE deploys
   underscore names such as `sase_final`. The installed OpenCode build currently lists
   and loads them, but this is a compatibility risk worth pinning with a provider smoke
   test rather than assuming it will remain accepted.

## Where direct sessions fail today

### 1. The instruction files describe managed-run facts as universal facts

The root instructions currently say, among other things:

- SASE runs agents “like you” from ephemeral `sase_<N>` workspaces.
- agents never create commits, branches, or PRs because completion is host-owned.
- `/sase_final` is mandatory before every normal response.
- long verification must use `/sase_monitor` because provider-native waiting does not
  work in SASE's single-turn model.

All of those claims are correct for a SASE-managed provider turn. None is universally
correct for a user-run CLI in a long-lived checkout. The distinction matters most for
the user's example: a direct Claude Code session explicitly asked to make a quick commit
may see both “agents never create commits” and an installed `/sase_git_commit` skill
which says an explicit user commit request is the condition under which it may commit.

The fix should be semantic narrowing, not a new explanatory section. For example:

- “SASE-managed agents run from ephemeral workspaces.”
- “Before ending a SASE-managed provider turn, use `/sase_final`.”
- “Host-owned completion applies to SASE-managed agents.”
- “Use `/sase_monitor` for long commands inside a SASE-managed turn.”

These replacements add essentially no prompt burden and remove the contradictions.

### 2. Reference memory is inaccessible

`sase memory read` resolves the requested note, requires an `AgentIdentity`, appends an
audit event, and only then prints the content (`src/sase/memory/cli_read.py` and
`src/sase/memory/read_log.py`). With no `SASE_AGENT_NAME`, `SASE_AGENT`, or artifacts
metadata, the command exits before emitting the memory.

This blocks more than optional context. The generated instructions explicitly forbid
opening reference memory directly, and skills such as `/sase_new_task` require memory
reads before acting. `sase memory show` is deliberately unaudited and documented for
humans, so telling agents to fall back to it would weaken the policy and require more
instruction text.

Direct reads should therefore remain `memory read` operations and get an external actor
record rather than being rejected.

### 3. Most skills fail in their generated audit prelude

Unless a skill opts out with `log_skill_use: false`, the generated frame tells the agent
to run this before doing anything else:

```bash
sase skill use <name> --reason "<reason>"
```

`sase skill use` also requires a SASE agent identity (`src/sase/skills/cli_use.py`).
Consequently, a direct agent can load a perfectly usable read-only skill such as
`/sase_project`, `/sase_chats`, `/sase_notify`, or `/sase_agents_status` and encounter a
failure before its first real command. The same applies to `/sase_git_commit`, even
though the commit wrapper itself is intentionally tolerant of a missing artifacts
directory.

The audit layer should accept direct actors. Disabling audit on every compatible skill
would lose useful observability and create a growing exception list.

### 4. Finalization has no host

`sase final context` currently requires `SASE_ARTIFACTS_DIR`, authenticated finalizer
plan data, a run timestamp, an agent identity, and a turn nonce
(`src/sase/finalizers/declaration.py`). A direct CLI has no host process waiting to
consume a declaration after the model returns, so manufacturing those values would be
misleading.

The correct direct behavior is a successful, read-only no-op response such as:

```json
{
  "schema_version": 1,
  "execution_mode": "direct_cli",
  "submission_required": false,
  "message": "No SASE host owns completion for this session. Do not auto-commit. If the user explicitly requested a commit, use /sase_git_commit; otherwise report the remaining working-tree state."
}
```

This lets the unchanged high-level instruction lead the agent to a command that tells
the truth at runtime. It must not create a nonce, artifacts directory, or other finalizer
state.

### 5. Handoff commands correctly require a runner, but their fallbacks are unclear

Plan proposal, questions, and pipe all call the same handoff guard, which rejects an
unset `SASE_AGENT` or artifacts directory (`src/sase/agent/pending_handoff_write.py`).
When managed, the commands write a marker and terminate the runner process group. That
behavior must not be emulated in a direct provider session.

The skills currently say the provider's native plan/question mechanism “is disabled,”
but that is only true for the SASE-managed launch configuration. A directly launched
CLI still has its native interaction model. Each managed-only command should return one
typed error with an actionable direct fallback, and provider-rendered skill text should
say the native feature is disabled **in a SASE-managed turn**.

### 6. Some features are already partially direct-compatible

The code contains useful precedents:

- `sase monitor start` only hands off and kills a runner when `SASE_AGENT` is set. It
  can start a detached process outside an agent, although follow-up targeting needs an
  explicit agent and cannot resume the same direct conversation
  (`src/sase/monitor/handoff.py`).
- Launch approvals already distinguish `agent_skill` from `cli` as their source, and
  request creation itself is not intrinsically tied to a current agent
  (`src/sase/agent/launch_request.py`).
- `sase_git_commit` writes per-agent invocation evidence only when an artifacts
  directory exists, then always delegates to `sase stitch create`. With neither a
  command-line type nor `SASE_COMMIT_METHOD`, it chooses the ordinary `create_commit`
  workflow (`src/sase/scripts/sase_git_commit`).
- Historical status, chat, notification, Patch, project, and variable reads generally
  operate on durable project data, not the current provider process. Their main direct
  obstacle is often the skill audit prelude rather than their underlying command.

These precedents argue for centralizing execution-context resolution instead of adding
one-off checks to every skill.

## Current and target capability matrix

| Capability | Direct session today | Baseline target | Exact managed parity possible without a bridge? |
| --- | --- | --- | ---: |
| Core memory / project rules | Works | Keep | Yes |
| Global SASE skill discovery | Works after `sase skill init` | Doctor verifies every provider target | Yes |
| Reference memory reads | Blocked by identity audit | Audit an external actor and print content | Yes |
| Skill-use audit | Blocked by identity audit | Audit an external actor | Yes |
| Project, Patch, chat, status, notification reads | Underlying commands mostly work; skill prelude may fail | Fully direct-safe | Yes |
| Bead and task workflows | Partially blocked by required memory/skill audit | Fully direct-safe with external attribution | Yes |
| SASE artifact reads/writes | Project operations can work; current-run attribution may not | Support durable project artifacts; omit unavailable run ownership | Mostly |
| Linked/external repo open | Requires workspace-specific knowledge in some paths | Allocate or select a direct-session repo checkout explicitly | Yes |
| Explicit manual commit | Wrapper path mostly works; skill audit fails and checkout may contain pre-existing work | Keep explicit-user-only policy and make audit work | Yes, except exact session authorship |
| Automatic final declaration | Errors | Successful no-op with explicit guidance | No host action to execute |
| Questions | Managed handoff errors | Use provider-native question tool, or bridge-backed SASE gate | No |
| Plan authoring/validation | Validation works; proposal handoff errors | Native plan mode plus optional SASE validation/archive | No automatic continuation |
| Custom gates | Durable gate machinery can be used, but waiting UX is not provider-integrated | Permit direct creation; document whether it blocks or returns an ID | Mostly |
| Long command monitor | Fire-and-forget can work | Preserve detached monitoring; use provider-native wait/resume for same session | No same-session reinjection |
| Launch another SASE agent | CLI-source launch request is possible | Expose a safe, user-authorized direct path | Yes for launching; no shared direct conversation |
| Pipe to successor / family continuation | Requires managed family and runner | Precise unsupported response; use provider-native resume/fork or start a SASE agent | No |
| Current-run output variables | Requires agent artifacts | Historical reads work; current writes require a direct-session store/bridge | No |
| Xprompt expansion on the user's original prompt | Only SASE launch preprocessing sees `#...` and `%...` | Optional provider hook/plugin; no silent interpretation in baseline direct mode | No |
| Post-response host finalizers and complete per-turn baseline | No host or start snapshot | Optional session bridge | No |

## Recommended design

### A. Add one shared execution-context API

Introduce a small domain object used by every SASE CLI entry point, for example
`ExecutionContext` with:

```text
mode: managed_agent | external
project: optional project identity
agent: optional authenticated AgentIdentity
provider: optional best-effort provider name
session_id: optional external-session identifier
artifacts_dir: optional authenticated path
capabilities: named booleans or enums
```

Expose it read-only as `sase runtime context --format json` (the exact command name is
less important than having one implementation). Agent-facing errors should carry a
stable code such as `managed_agent_required`, not require consumers to parse
“SASE_AGENT is unset.”

Commands should ask for the capability they need, not repeat environment checks:

- `require_managed_handoff()` for plan/questions/pipe.
- `require_finalizer_turn()` for declaration submission.
- `audit_actor()` for memory and skill logs; this may return a managed agent or an
  external actor.
- `current_checkout_kind()` for primary workspace, direct project checkout, or opened
  repo.

This also avoids treating a stale `SASE_AGENT=1` as sufficient authority.

### B. Generalize audit identity instead of disabling audit

Memory reads, skill uses, repo opens, bead reports, and artifact access are valuable to
audit in direct sessions. Extend their event actor from “must be a SASE agent” to a
tagged actor:

```json
{
  "kind": "external_cli",
  "name": "direct:claude:12345",
  "provider": "claude",
  "session_id": null,
  "artifacts_dir": null,
  "source": "process_ancestor"
}
```

The first implementation may use a conservative `external` name and no provider. A
best-effort parent-process lookup can enrich it on local Unix systems, but correctness
must not depend on recognizing a vendor executable. A later session bridge can supply a
stable provider session ID.

Event schemas should explicitly distinguish an external actor from a SASE agent rather
than placing synthetic values in `SASE_AGENT_NAME`. Reporter deduplication for task
beads must not collapse every direct session into one permanent pseudo-agent.

### C. Make managed-only commands self-describing

Use one diagnostic envelope and render it as concise text by default:

```json
{
  "code": "managed_agent_required",
  "command": "sase plan propose",
  "execution_mode": "external",
  "fallback": "Keep the validated plan in this checkout and use the provider's native plan workflow. To submit it to SASE, launch a SASE agent or run the user-facing plan command from ACE."
}
```

Recommended direct behavior by skill:

- `/sase_final`: call context; return immediately when submission is not required.
- `/sase_questions`: use the provider's native question tool outside managed mode.
- `/sase_plan`: provider-native plan mode is allowed outside managed mode; SASE plan
  validation remains usable, but proposal must not kill or pretend to resume the direct
  session.
- `/sase_monitor`: direct sessions may use provider-native background/wait facilities.
  SASE monitor remains available for detached fire-and-forget work or an explicitly
  targeted SASE follow-up.
- `/sase_pipe`: report that SASE family piping requires a managed agent; use the
  provider's resume/fork facility or explicitly launch a SASE agent.
- `/sase_run`: outside a managed agent, use the existing user/CLI launch path, with the
  same authorization expected of a human launch. Do not claim that `LaunchApproval` is
  required merely because the caller is a model.
- `/sase_var`: historical list/get remains available. Current-run set/get either uses a
  future direct-session store or reports that no run-scoped store exists.

The fallback belongs at the top of each on-demand skill body and in the command error.
It does not belong in the always-loaded root instructions.

### D. Treat direct completion conservatively

Direct mode has no host waiting after the assistant response and, without a session
bridge, no trustworthy working-tree baseline captured at session start. Therefore:

- `/sase_final` must never auto-commit in direct mode.
- A direct agent may use `/sase_git_commit` only on an explicit user request, preserving
  the skill's current authorization rule.
- The agent must inspect every dirty path before that commit. Pre-existing user work is
  especially plausible in the canonical checkout.
- SASE should eventually offer an include-only or baseline-aware direct commit scope;
  the managed stage-everything default is appropriate for an isolated SASE workspace
  but riskier in a long-lived direct checkout.
- If the user did not ask for a commit, the direct agent should report the remaining
  dirty state and stop normally.

This retains the user's “quick commit” workflow without weakening SASE's managed
host-owned-completion invariant. The invariant is scoped to managed runs, not imposed
on every process that happens to read a SASE project's instructions.

### E. Give direct repo opens an explicit checkout model

`/sase_repo` is useful in direct research and should remain mandatory for linked,
sidecar, different-project, and external repository access. It needs a checkout identity
that does not assume the caller owns a numbered SASE workspace.

Two reasonable implementations are:

1. A direct-session checkout under SASE's managed repo store, keyed by a generated
   external session ID and protected by the same occupancy rules as agent checkouts.
2. An explicit read-only shared checkout for research, upgraded to an isolated direct
   checkout before the first write.

The command should print which kind it returned. A direct session must never be told to
guess a live agent's workspace number, and it must not gain permission to edit another
agent's linked checkout merely because both belong to the same project.

### F. Add an optional direct-session bridge for high parity

Baseline direct mode should not depend on vendor hooks. An optional bridge can recover
features that need session lifecycle:

- register provider, session ID, cwd, and project at session start;
- capture git status and fingerprints before the first agent edit;
- maintain direct-session output variables and opened-repo obligations;
- expose SASE gates/questions as blocking tools whose answer returns to the same turn;
- import or point to the provider transcript;
- provide a stop event that can warn about unresolved SASE obligations.

A stdio MCP server is a promising common transport because the inspected CLIs broadly
support MCP and the server lifetime naturally supplies a session boundary. Provider
plugins/hooks are still needed for capabilities that MCP cannot provide, particularly
intercepting the original user prompt for xprompt expansion or executing something
after the model's final response. Claude, Qwen, Antigravity, Grok, and OpenCode all
document lifecycle hooks or plugin interception today; Muse and Codex should be verified
against their exact supported lifecycle contracts before treating one bridge as
universal. [Claude hooks](https://code.claude.com/docs/en/hooks), [Qwen hooks](https://qwenlm.github.io/qwen-code-docs/en/users/features/hooks/), [OpenCode plugins](https://opencode.ai/docs/plugins), [Grok hooks](https://docs.x.ai/build/features/skills-plugins-marketplaces)

The bridge should be optional because it adds provider configuration, lifecycle, and
failure modes. Direct-safe CLI behavior remains necessary even when the bridge is absent
or broken.

## What cannot be faithfully supported without supervision

The following are structural limits, not missing prompt instructions:

1. **Host-owned work after the answer.** Once a direct CLI returns its final response,
   no SASE runner necessarily exists to validate a declaration and execute finalizers.
2. **Mechanical continuation of the same conversation.** SASE plan/questions/monitor
   handoffs terminate one managed provider process and construct the next prompt. A
   shell command cannot portably inject a follow-up turn into an arbitrary direct CLI.
3. **Family piping.** A direct session is not a member of a SASE agent family and owns
   no SASE workspace claim to transfer.
4. **Exact per-turn authorship without a start event.** Looking at the working tree only
   at completion cannot distinguish edits made earlier by the user from edits made by
   the direct agent.
5. **Automatic xprompt preprocessing.** Direct providers receive the user's raw prompt
   before any SASE command runs. Expanding `#...` and `%...` requires a wrapper,
   provider hook/plugin, or the user explicitly asking SASE to expand and launch it.

These limitations should be reported by the command that encounters them. They do not
justify burdening every direct session with an always-loaded compatibility essay.

## Minimal instruction-file changes

The goal should be **no new section and no provider-specific fork**. The generated
provider files should remain identical copies so their behavior cannot drift.

The likely unavoidable edits are replacements in existing core memory:

| Existing concept | Narrowed concept |
| --- | --- |
| “SASE runs agents (like you) from ephemeral workspaces” | “SASE-managed agents run from ephemeral workspaces” |
| “Before any normal response that ends this SASE provider turn...” | “Before any normal response that ends a SASE-managed provider turn...” |
| “An agent never creates commits...” | “A SASE-managed agent never creates commits...” |
| “Run long commands only through `/sase_monitor`” | Scope the rule to a SASE-managed turn |

Everything else can live in:

- `sase runtime context` and command diagnostics;
- the first few lines of on-demand provider-rendered skills;
- doctor/readiness output for users;
- optional bridge configuration.

If absolutely zero `AGENTS.md` bytes may change, a no-op final context and excellent
errors will remove most failures. It will not remove the false workspace and commit
claims, so zero-byte change is a weaker result than four small wording substitutions.

## Suggested implementation sequence

### Phase 1: establish and test the boundary

1. Add the shared execution-context resolver and typed error model.
2. Add tests for a complete managed context, no SASE environment, partial/stale SASE
   environment, and a direct session inside a SASE project.
3. Inventory every generated skill and CLI command by required capability. Make the
   inventory a test fixture so new skills cannot accidentally assume a managed agent.

### Phase 2: make the high-value baseline direct-safe

1. Extend memory-read and skill-use audit events with external actors.
2. Make `sase final context` return the direct no-op envelope without writes.
3. Add common `managed_agent_required` handling to plan, questions, pipe, and current-run
   variable writes.
4. Update the provider-rendered plan/questions/monitor/pipe/run/var skill introductions
   with their managed/direct branch.
5. Apply the four semantic-narrowing edits to core memory and regenerate provider
   copies.

### Phase 3: preserve ordinary SASE project workflows

1. Make direct repo opens allocate a safe checkout without a guessed workspace number.
2. Verify beads, artifacts, notifications, Patches, project inspection, and chat/status
   skills end-to-end with external attribution.
3. Make `sase doctor` report, per installed provider, instruction discovery, skill
   directory health, missing SASE skills, and known naming incompatibilities.
4. Exercise explicit direct commits with clean, dirty, ahead, conflict, and
   pre-existing-unrelated-change cases. Decide whether direct mode requires an
   include-only commit option.

### Phase 4: optional bridge

Prototype one direct-session bridge with Claude Code or Codex, then validate the MCP or
plugin contract separately for every provider. Do not make baseline direct safety depend
on all providers reaching bridge parity at once.

## Acceptance scenarios

Run these against every real provider CLI, launched by its ordinary executable from a
fully initialized SASE project:

1. **Research only:** ask a question that requires reference memory. The agent uses the
   installed skill, the read is audited as external, and no identity error appears.
2. **Read-only SASE features:** ask for project, agent, Patch, chat, and notification
   status. Skill audit and underlying commands both work.
3. **Clarification:** ask an ambiguous question. The direct session uses its native
   question interaction (or an installed bridge), not `sase questions` runner handoff.
4. **Planning:** request a plan only. Native plan mode works; optional SASE validation
   works; no process-group kill or false promise of continuation occurs.
5. **Edit without commit request:** make a small edit. `/sase_final` returns direct
   no-op guidance, no commit is created, and the agent reports dirty state.
6. **Explicit quick commit:** start clean, ask for a small edit and commit. The agent
   uses `/sase_git_commit`, produces a conventional commit, pushes according to project
   policy, and `/sase_final` remains a no-op afterward.
7. **Pre-existing user work:** start with an unrelated dirty path, ask for another edit
   and commit. The unrelated path is not silently swept into the commit.
8. **Long test:** direct provider-native waiting/background behavior remains usable;
   `sase monitor` fire-and-forget does not kill the direct CLI.
9. **Managed regression:** launch the same tasks through SASE. Final declarations,
   handoffs, workspace ownership, monitor continuation, and host finalizers behave
   exactly as before.
10. **Missing global initialization:** remove one provider's SASE skills. Doctor names
    the missing target and the exact repair command before a project instruction can
    strand the agent on an unknown `/sase_*` skill.

## Conclusion

SASE does not need separate “direct” instruction files, and it should not weaken its
managed single-turn model. It needs a first-class external execution context.

Most of the useful project layer—memory, skills, audits, project and Patch inspection,
beads, artifacts, repositories, notifications, verification, and explicit commits—can
be supported directly. The existing instruction-copy and skill-deployment mechanisms
already provide a strong cross-provider distribution layer.

The remaining incompatibilities cluster around one assumption: that a SASE runner owns
the process and will act after the model returns. Make that assumption an explicit
capability checked by commands, keep direct completion conservative, and reserve a
session bridge for the smaller set of lifecycle features that genuinely need one.
